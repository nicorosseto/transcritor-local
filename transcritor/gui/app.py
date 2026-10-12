"""App desktop (CustomTkinter). Toda a lógica vem de transcritor.pipeline; aqui é só interface.

O trabalho pesado roda em threads; elas mandam eventos por uma fila que a interface consome
a cada 150 ms (o Tkinter só pode ser tocado na thread principal).

Diretrizes seguidas (Microsoft, Windows UX): uma barra de progresso única por operação que só
avança; rótulo com verbo e reticências; tempo restante só quando confiável; diálogos com botões
de ação específicos; primeira abertura sem perguntas desnecessárias.
"""

from __future__ import annotations

import gc
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk

from .. import __version__, correcoes, ocr, preparacao
from ..config import NOME_ARQUIVO_CONFIG, PRESETS, Config, vocabulario_de_texto
from ..pipeline import Evento, Item, PastasMudaram, Projeto, ProjetoDeOutraOrigem, modelo_baixado
from ..registro import ERRO as ST_ERRO
from ..registro import OK as ST_OK
from ..registro import SUBSTITUIDO
from ..util import hhmmss
from . import textos
from .componentes import Dialogo, Dica, piscar_barra_de_tarefas, som_aviso, som_sucesso
from .estado import resumo_final
from .verificacao import JanelaVerificacao, Situacao, verificar

MARCADO, DESMARCADO = "☑", "☐"
STATUS_ROTULO = {ST_OK: "✅ concluído", "pendente": "⏳ pendente", ST_ERRO: "⚠️ erro (tentar de novo)",
                 SUBSTITUIDO: "🔄 arquivo mudou"}
ROTULO_PRESET = {v["rotulo"]: k for k, v in PRESETS.items()}
ETAPAS = [("audio", "Áudio"), ("transcricao", "Transcrição"), ("telas", "Texto da tela"), ("salvar", "Salvar")]
COR_ATIVA, COR_FEITA, COR_ESPERA = "#1f6aa5", "#2e7d32", "gray55"
VERDE, LARANJA, VERMELHO = "#2e7d32", "#c77700", "#c62828"


def tempo_humano(seg: float) -> str:
    """Sem falsa precisão: minutos para tempos longos (diretriz da Microsoft)."""
    seg = max(0, int(seg))
    if seg < 60:
        return "menos de 1 min"
    h, m = divmod(round(seg / 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        self.title(f"Transcritor Local {__version__}")
        self.geometry("1120x800")
        self.minsize(980, 700)

        self.fila: queue.Queue = queue.Queue()
        self.projeto: Projeto | None = None
        self.itens: list[Item] = []
        self.marcados: set[str] = set()
        self.rodando = False
        self.parar = threading.Event()
        self.cancelar = threading.Event()
        self.situacao: Situacao | None = None
        self._janela_verif = None
        self._baixando = False
        self._trabalho: threading.Thread | None = None

        # Coleta de lixo só na thread principal: se ela rodar numa thread de trabalho e destruir
        # objetos do Tk (fontes, imagens), o app trava. Padrão conhecido em Tkinter com threads.
        gc.disable()
        self._ciclos_fila = 0

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(150, self._consumir_fila)
        self.after(400, self._verificacao_inicial)

    # ================================================================== layout
    def _montar(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        # Fontes criadas UMA vez: objetos de fonte destruídos pelo coletor de lixo numa thread de
        # trabalho chamam o Tk fora da thread principal e TRAVAM o app (bug real, pego em teste).
        self.f_normal = ctk.CTkFont()
        self.f_negrito = negrito = ctk.CTkFont(weight="bold")

        # ---- cabeçalho
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        ctk.CTkLabel(cab, text="Transcritor Local", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(cab, text=f"  v{__version__} · tudo roda no seu PC", text_color="gray50").pack(side="left")
        ctk.CTkButton(cab, text="❓ Como usar", width=110, command=self._ajuda).pack(side="right", padx=(6, 0))
        self.btn_verif = ctk.CTkButton(cab, text="🖥 Verificar PC", width=150, command=self._abrir_verificacao)
        self.btn_verif.pack(side="right")
        self._cor_verif = self.btn_verif.cget("fg_color")
        Dica(self.btn_verif, "Confere se o seu PC tem tudo o que o app precisa (modelo de transcrição, "
                             "FFmpeg, Tesseract) e ajuda a baixar ou instalar o que faltar.")

        # ---- pastas
        topo = ctk.CTkFrame(self)
        topo.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        topo.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(topo, text="① Pasta dos vídeos", font=negrito).grid(row=0, column=0, padx=10, pady=6, sticky="w")
        self.ent_videos = ctk.CTkEntry(topo, placeholder_text="Escolha a pasta com os vídeos (pode ter subpastas)")
        self.ent_videos.grid(row=0, column=1, sticky="ew", pady=6)
        self.btn_proc_videos = ctk.CTkButton(topo, text="Procurar", width=100, command=self._escolher_videos)
        self.btn_proc_videos.grid(row=0, column=2, padx=8)
        ctk.CTkLabel(topo, text="② Pasta de saída", font=negrito).grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self.ent_saida = ctk.CTkEntry(topo, placeholder_text="Onde salvar as transcrições")
        self.ent_saida.grid(row=1, column=1, sticky="ew", pady=6)
        self.btn_proc_saida = ctk.CTkButton(topo, text="Procurar", width=100, command=self._escolher_saida)
        self.btn_proc_saida.grid(row=1, column=2, padx=8)
        # Trocar a pasta à mão invalida a leitura anterior (achado X3)
        for ent in (self.ent_videos, self.ent_saida):
            ent.bind("<KeyRelease>", lambda _e: self._pastas_mudaram())
        self.btn_ler = ctk.CTkButton(topo, text="Ler pasta", width=110, command=self._ler_pasta)
        self.btn_ler.grid(row=0, column=3, rowspan=2, padx=(0, 10))
        Dica(self.btn_ler, "Lista os vídeos e mostra quais já foram transcritos. "
                           "Use de novo se você adicionar ou remover vídeos.")

        self.lbl_resumo = ctk.CTkLabel(self, text="Comece pelo passo ①: escolha a pasta com os vídeos.",
                                       anchor="w", text_color="gray45")
        self.lbl_resumo.grid(row=2, column=0, sticky="ew", padx=18)

        # ---- meio: tabela + opções
        meio = ctk.CTkFrame(self, fg_color="transparent")
        meio.grid(row=3, column=0, sticky="nsew", padx=14, pady=4)
        meio.grid_columnconfigure(0, weight=1)
        meio.grid_columnconfigure(1, weight=0, minsize=400)
        meio.grid_rowconfigure(0, weight=1)

        tab = ctk.CTkFrame(meio)
        tab.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="③ Vídeos (clique na caixinha para marcar)", font=negrito,
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 4))
        estilo = ttk.Style()
        estilo.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.tabela = ttk.Treeview(tab, columns=("sel", "video", "dur", "status"), show="headings",
                                   selectmode="none")
        for col, txt, larg, anc, est in (("sel", "", 36, "center", False), ("video", "Vídeo", 380, "w", True),
                                         ("dur", "Duração", 80, "center", False),
                                         ("status", "Status", 170, "w", False)):
            self.tabela.heading(col, text=txt, anchor=anc)
            self.tabela.column(col, width=larg, minwidth=larg if not est else 200, anchor=anc, stretch=est)
        self.tabela.grid(row=1, column=0, sticky="nsew", padx=(8, 0))
        rolagem = ttk.Scrollbar(tab, orient="vertical", command=self.tabela.yview)
        rolagem.grid(row=1, column=1, sticky="ns", padx=(0, 8))
        self.tabela.configure(yscrollcommand=rolagem.set)
        self.tabela.bind("<Button-1>", self._clique_tabela)
        botoes = ctk.CTkFrame(tab, fg_color="transparent")
        botoes.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        self.btns_marcar = []
        for txt, fn in (("Marcar pendentes", self._marcar_pendentes), ("Marcar todos", self._marcar_todos),
                        ("Desmarcar todos", self._desmarcar_todos)):
            b = ctk.CTkButton(botoes, text=txt, width=130, fg_color="gray55", hover_color="gray45", command=fn)
            b.pack(side="left", padx=(0, 6))
            self.btns_marcar.append(b)

        direita = ctk.CTkFrame(meio, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_rowconfigure(0, weight=1)
        direita.grid_columnconfigure(0, weight=1)
        op = ctk.CTkScrollableFrame(direita, label_text="④ Opções", width=370, height=250)
        op.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(op, text="Qualidade", font=negrito).pack(anchor="w")
        self.seg_preset = ctk.CTkSegmentedButton(op, values=[v["rotulo"] for v in PRESETS.values()],
                                                 command=lambda _: self._opcoes_mudaram())
        self.seg_preset.set(PRESETS["equilibrado"]["rotulo"])
        self.seg_preset.pack(fill="x", pady=2)
        self.lbl_preset = ctk.CTkLabel(op, text="", wraplength=340, justify="left", text_color="gray50")
        self.lbl_preset.pack(anchor="w", pady=(0, 8))

        self.chk_ocr = ctk.CTkCheckBox(op, text="Ler texto da tela (slides, código, menus)",
                                       command=self._opcoes_mudaram)
        self.chk_ocr.pack(anchor="w", pady=2)
        self.lbl_ocr = ctk.CTkLabel(op, text="", text_color="gray50", wraplength=340, justify="left")
        self.lbl_ocr.pack(anchor="w")
        ctk.CTkCheckBox(op, text="Descrever telas com IA visual (em breve: v0.2)",
                        state="disabled").pack(anchor="w", pady=(8, 0))

        ctk.CTkLabel(op, text="Vocabulário de dicas", font=negrito).pack(anchor="w", pady=(12, 0))
        self.ent_vocab = ctk.CTkEntry(op, placeholder_text="Ex.: Power BI, DAX, ChatGPT, Claude, hook")
        self.ent_vocab.pack(fill="x", pady=2)
        ctk.CTkLabel(op, text="Ajuda o Whisper a OUVIR certo nomes e termos técnicos. Não garante.",
                     text_color="gray50", wraplength=340, justify="left").pack(anchor="w")

        ctk.CTkLabel(op, text="Correções automáticas", font=negrito).pack(anchor="w", pady=(12, 0))
        linha_corr = ctk.CTkFrame(op, fg_color="transparent")
        linha_corr.pack(fill="x")
        self.lbl_corr = ctk.CTkLabel(linha_corr, text="Leia uma pasta primeiro.", text_color="gray50")
        self.lbl_corr.pack(side="left")
        self.btn_corr = ctk.CTkButton(linha_corr, text="Editar lista", width=110, state="disabled",
                                      command=self._editar_correcoes)
        self.btn_corr.pack(side="right")
        Dica(self.btn_corr, "Troca o texto DEPOIS de transcrever, sempre: \"Chatepte\" vira \"ChatGPT\". "
                            "Só palavras inteiras. Cuidado com palavras reais (ex.: \"Hulk\").")

        ctk.CTkLabel(op, text="Processar nesta rodada (obrigatório)", font=negrito).pack(anchor="w", pady=(12, 0))
        self.opt_qtd = ctk.CTkOptionMenu(op, values=["Escolha..."], command=lambda _: self._atualizar_estimativa())
        self.opt_qtd.pack(fill="x", pady=2)

        caixa_est = ctk.CTkFrame(direita)
        caixa_est.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.lbl_estimativa = ctk.CTkLabel(caixa_est, text="A estimativa aparece aqui depois de ler a pasta.",
                                           justify="left", anchor="w", font=ctk.CTkFont(family="Consolas", size=12))
        self.lbl_estimativa.pack(fill="x", padx=10, pady=8)

        # ---- execução
        exe = ctk.CTkFrame(self)
        exe.grid(row=4, column=0, sticky="ew", padx=14, pady=(4, 4))
        exe.grid_columnconfigure(1, weight=1)
        self.btn_iniciar = ctk.CTkButton(exe, text="▶  INICIAR", width=170, height=44, state="disabled",
                                         font=ctk.CTkFont(size=15, weight="bold"), command=self._iniciar)
        self.btn_iniciar.grid(row=0, column=0, rowspan=3, padx=12, pady=12)
        self.lbl_status = ctk.CTkLabel(exe, text="Pronto para começar.", anchor="w",
                                       font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_status.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        linha_etapas = ctk.CTkFrame(exe, fg_color="transparent")
        linha_etapas.grid(row=1, column=1, sticky="w")
        self.lbl_etapas = {}
        for n, (cod, rot) in enumerate(ETAPAS):
            if n:
                ctk.CTkLabel(linha_etapas, text="›", text_color="gray60").pack(side="left", padx=4)
            lb = ctk.CTkLabel(linha_etapas, text=f"○ {rot}", text_color=COR_ESPERA)
            lb.pack(side="left")
            self.lbl_etapas[cod] = (lb, rot)
        self.pb = ctk.CTkProgressBar(exe, height=14)
        self.pb.set(0)
        self.pb.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=(4, 0))
        self.lbl_tempo = ctk.CTkLabel(exe, text="", anchor="w", text_color="gray45")
        self.lbl_tempo.grid(row=3, column=1, sticky="ew", pady=(0, 8))
        lado = ctk.CTkFrame(exe, fg_color="transparent")
        lado.grid(row=0, column=2, rowspan=4, padx=12)
        self.btn_parar = ctk.CTkButton(lado, text="⏸ Parar após o vídeo atual", width=200, state="disabled",
                                       command=self._parar)
        self.btn_parar.pack(pady=2)
        Dica(self.btn_parar, "Termina o vídeo em andamento e para. Nada se perde.")
        self.btn_cancelar = ctk.CTkButton(lado, text="✖ Cancelar agora", width=200, state="disabled",
                                          fg_color="#8a2a2a", hover_color="#6e1f1f", command=self._cancelar)
        self.btn_cancelar.pack(pady=2)
        Dica(self.btn_cancelar, "Interrompe na hora. O vídeo em andamento será refeito na próxima vez.")
        ctk.CTkButton(lado, text="📂 Abrir pasta de saída", width=200, command=self._abrir_saida).pack(pady=2)

        # ---- detalhes (log) recolhível
        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 10))
        rod.grid_columnconfigure(0, weight=1)
        self.btn_log = ctk.CTkButton(rod, text="▸ Mostrar detalhes técnicos (registro de atividades)",
                                     fg_color="transparent", text_color=("gray30", "gray75"),
                                     hover_color=("gray85", "gray25"), anchor="w", command=self._alternar_log)
        self.btn_log.grid(row=0, column=0, sticky="w")
        self.log = ctk.CTkTextbox(rod, height=120, font=ctk.CTkFont(family="Consolas", size=11))
        self._log_visivel = False
        self._log("Aplicativo aberto.")
        self._opcoes_mudaram()

    # ================================================================== utilidades
    def _log(self, texto: str):
        self.log.insert("end", f"[{datetime.now():%H:%M:%S}] {texto}\n")
        self.log.see("end")

    def _alternar_log(self):
        self._log_visivel = not self._log_visivel
        if self._log_visivel:
            self.log.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.btn_log.configure(text="▾ Esconder detalhes técnicos")
        else:
            self.log.grid_forget()
            self.btn_log.configure(text="▸ Mostrar detalhes técnicos (registro de atividades)")

    def _pasta(self, entrada) -> Path | None:
        t = entrada.get().strip().strip('"')
        return Path(t) if t else None

    def _cfg(self) -> Config | None:
        videos, saida = self._pasta(self.ent_videos), self._pasta(self.ent_saida)
        if not videos or not saida:
            return None
        cfg = Config.carregar(saida, videos)
        cfg.preset = ROTULO_PRESET[self.seg_preset.get()]
        cfg.ocr = bool(self.chk_ocr.get())
        cfg.vocabulario = vocabulario_de_texto(self.ent_vocab.get())
        return cfg

    def _definir(self, entrada, valor: str):
        entrada.delete(0, "end")
        entrada.insert(0, valor)

    def _preset(self) -> str:
        return ROTULO_PRESET[self.seg_preset.get()]

    # ================================================================== verificação do PC
    def _verificacao_inicial(self):
        self._rodar_verificacao(abrir_se_obrigatorio=True)

    def _rodar_verificacao(self, abrir_se_obrigatorio=False):
        preset, saida = self._preset(), self._pasta(self.ent_saida)

        def tarefa():
            s = verificar(preset, saida)
            self.fila.put(Evento("verificacao", {"situacao": s, "abrir": abrir_se_obrigatorio}))
        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicar_situacao(self, s: Situacao, abrir: bool):
        self.situacao = s
        n = s.total_pendencias
        if s.obrigatorios:
            self.btn_verif.configure(text=f"⚠ Verificar PC ({n})", fg_color=VERMELHO)
        elif n:
            self.btn_verif.configure(text=f"🖥 Verificar PC ({n})", fg_color=LARANJA)
        else:
            self.btn_verif.configure(text="✅ PC pronto", fg_color=self._cor_verif)
        self.lbl_ocr.configure(text="+15–35% de tempo. " + (
            "Tesseract instalado." if s.tesseract_ok else "Precisa do Tesseract (não instalado)."))
        if n:
            self._pulsar(6)
        if abrir and s.obrigatorios:
            self._log("Verificação: falta " + ", ".join(s.obrigatorios) + ". Abrindo a preparação.")
            self._abrir_verificacao()

    def _pulsar(self, vezes):
        """Pisca o botão para chamar atenção sem bloquear nada."""
        if vezes <= 0:
            self._aplicar_cor_verif()
            return
        atual = self.btn_verif.cget("fg_color")
        self.btn_verif.configure(fg_color="#f2b134" if atual != "#f2b134" else self._cor_pendencia())
        self.after(350, lambda: self._pulsar(vezes - 1))

    def _cor_pendencia(self):
        if self.situacao and self.situacao.obrigatorios:
            return VERMELHO
        if self.situacao and self.situacao.total_pendencias:
            return LARANJA
        return self._cor_verif

    def _aplicar_cor_verif(self):
        self.btn_verif.configure(fg_color=self._cor_pendencia())

    def _abrir_verificacao(self):
        if self._janela_verif is not None and self._janela_verif.winfo_exists():
            self._janela_verif.lift()
            self._janela_verif.focus_force()
            return
        if self.situacao is None:
            self._rodar_verificacao(abrir_se_obrigatorio=True)
            self._log("Verificando o PC...")
            return
        self._janela_verif = JanelaVerificacao(self, self.situacao, self._preset(), self._pasta(self.ent_saida),
                                               ao_mudar=lambda s: self._aplicar_situacao(s, False))

    def baixar_modelo(self, modelo, ao_progredir, ao_terminar):
        """Usado pela janela de verificação. ao_terminar(erro_ou_None) roda na thread da interface."""
        if self._baixando:
            return
        self._baixando = True

        def tarefa():
            erro = None
            try:
                preparacao.baixar_modelo(modelo, ao_progredir)
            except Exception as e:
                erro = str(e)
            self._baixando = False
            self.na_interface(lambda: ao_terminar(erro))
        threading.Thread(target=tarefa, daemon=True).start()

    def na_interface(self, fn) -> None:
        """Agenda fn na thread principal. Threads de trabalho NUNCA chamam o Tk direto (achado X13):
        nem .after(); tudo passa pela fila consumida em _consumir_fila."""
        self.fila.put(Evento("chamar", {"fn": fn}))

    # ================================================================== pastas
    def _pastas_mudaram(self):
        """Se as pastas na tela não são as da última leitura, descarta a leitura (achado X3)."""
        if self.projeto is None or self.rodando:
            return
        v, s = self._pasta(self.ent_videos), self._pasta(self.ent_saida)
        cfg = self.projeto.cfg
        if v == cfg.pasta_videos and s == cfg.pasta_saida:
            return
        self.projeto, self.itens, self.marcados = None, [], set()
        self._preencher_tabela()
        self.btn_iniciar.configure(state="disabled")
        self.lbl_resumo.configure(text="As pastas mudaram. Clique em \"Ler pasta\" para listar os vídeos.")

    def _sugerir_saida(self, pv: Path) -> Path:
        """Reaproveita uma saída já existente ao lado (ex.: a pasta 'saida' da versão antiga)."""
        for candidata in (pv.parent / "saida", pv.parent / f"{pv.name}_transcricoes"):
            if (candidata / "registro.csv").is_file() or (candidata / NOME_ARQUIVO_CONFIG).is_file() \
                    or (candidata / "transcricoes_md").is_dir():
                return candidata
        return pv.parent / f"{pv.name}_transcricoes"

    def _escolher_videos(self):
        p = filedialog.askdirectory(title="Pasta com os vídeos")
        if p:
            self._definir(self.ent_videos, p)
            self._pastas_mudaram()
            if not self.ent_saida.get().strip():
                self._definir(self.ent_saida, str(self._sugerir_saida(Path(p))))
            self._ler_pasta()

    def _escolher_saida(self):
        p = filedialog.askdirectory(title="Pasta de saída")
        if p:
            self._definir(self.ent_saida, p)
            self._pastas_mudaram()

    def _ler_pasta(self):
        if self.rodando:
            return
        videos, saida = self._pasta(self.ent_videos), self._pasta(self.ent_saida)
        if videos and not saida:
            saida = self._sugerir_saida(videos)
            self._definir(self.ent_saida, str(saida))
        if not videos or not saida:
            Dialogo(self, "Faltam pastas", "Escolha a pasta dos vídeos (passo ①) antes de ler.",
                    [("Entendi", None, True)], icone="ℹ️", som=False).perguntar()
            return
        cfg = Config.carregar(saida, videos)
        erros = cfg.validar()
        if erros:
            Dialogo(self, "Pastas inválidas", "\n".join(erros), [("Entendi", None, True)], icone="❌").perguntar()
            return
        if (saida / NOME_ARQUIVO_CONFIG).is_file():
            self.seg_preset.set(PRESETS[cfg.preset]["rotulo"])
            self.chk_ocr.select() if cfg.ocr else self.chk_ocr.deselect()
            self._definir(self.ent_vocab, ", ".join(cfg.vocabulario))
            self._opcoes_mudaram()
        self._escanear(cfg)

    def _escanear(self, cfg: Config, aceitar_nova_origem: bool = False):
        self.btn_ler.configure(state="disabled")
        self.lbl_resumo.configure(text="Lendo a pasta e medindo as durações...")

        def tarefa():
            try:
                proj = Projeto(cfg, aceitar_nova_origem=aceitar_nova_origem)
                proj.escanear(lambda n, t: self.fila.put(Evento("medindo", {"n": n, "t": t})))
                self.fila.put(Evento("escaneado", {"projeto": proj}))
            except ProjetoDeOutraOrigem as e:
                self.fila.put(Evento("outra_origem", {"erro": e, "cfg": cfg}))
            except Exception as e:
                self.fila.put(Evento("falha_leitura", {"erro": str(e)}))
        threading.Thread(target=tarefa, daemon=True).start()

    def _outra_origem(self, erro: ProjetoDeOutraOrigem, cfg: Config):
        """Saída de outro curso: não mistura sem o usuário confirmar (achado X7)."""
        self.btn_ler.configure(state="normal")
        self.lbl_resumo.configure(text="Escolha outra pasta de saída ou confirme que a pasta de vídeos foi movida.")
        r = Dialogo(self, "Pasta de saída de outro projeto",
                    f"{erro}\n\nSe forem vídeos diferentes, use outra pasta de saída para não misturar "
                    "transcrições. Se você só moveu ou renomeou a pasta de vídeos, pode continuar.",
                    [("Escolher outra saída", "outra", True),
                     ("A pasta foi movida, continuar", "mover", False),
                     ("Cancelar", None, False)]).perguntar()
        if r == "outra":
            self._escolher_saida()
        elif r == "mover":
            self._escanear(cfg, aceitar_nova_origem=True)

    def _atualizar_correcoes(self):
        saida = self._pasta(self.ent_saida)
        if not saida:
            return
        regras, aviso = correcoes.carregar(saida)
        self.btn_corr.configure(state="normal")
        if aviso:
            self.lbl_corr.configure(text="⚠️ arquivo com erro (será ignorado)", text_color=VERMELHO)
        elif regras:
            self.lbl_corr.configure(text=f"{len(regras)} regra(s) ativa(s)", text_color="gray50")
        else:
            self.lbl_corr.configure(text="Nenhuma regra (opcional).", text_color="gray50")

    def _editar_correcoes(self):
        saida = self._pasta(self.ent_saida)
        if not saida:
            return
        arq = correcoes.criar_modelo_se_faltar(saida)
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", str(arq)])
        else:
            subprocess.Popen(["xdg-open", str(arq)])
        self._log(f"Abrindo {arq.name} para edição. Salve o arquivo; vale para as próximas transcrições.")
        self.after(1500, self._atualizar_correcoes)

    # ================================================================== tabela
    def _preencher_tabela(self):
        self.tabela.delete(*self.tabela.get_children())
        for it in self.itens:
            sel = MARCADO if it.rel in self.marcados else DESMARCADO
            self.tabela.insert("", "end", iid=it.rel,
                               values=(sel, it.rel, hhmmss(it.duracao), STATUS_ROTULO.get(it.status, it.status)))
        self._atualizar_quantidades()

    def _clique_tabela(self, ev):
        if self.rodando:
            return
        linha = self.tabela.identify_row(ev.y)
        if not linha:
            return
        self.marcados.symmetric_difference_update({linha})
        self.tabela.set(linha, "sel", MARCADO if linha in self.marcados else DESMARCADO)
        self._atualizar_quantidades()

    def _marcar_pendentes(self):
        self.marcados = {i.rel for i in self.itens if i.status != ST_OK}
        self._preencher_tabela()

    def _marcar_todos(self):
        self.marcados = {i.rel for i in self.itens}
        self._preencher_tabela()

    def _desmarcar_todos(self):
        self.marcados = set()
        self._preencher_tabela()

    def _selecionados(self) -> list[Item]:
        return [i for i in self.itens if i.rel in self.marcados]

    def _atualizar_quantidades(self):
        n = len(self._selecionados())
        valores = ["Escolha..."]
        if n:
            valores += [str(q) for q in (1, 3, 5, 10) if q < n] + [f"Todos os marcados ({n})"]
        self.opt_qtd.configure(values=valores)
        if self.opt_qtd.get() not in valores:
            self.opt_qtd.set("Escolha...")
        self._atualizar_estimativa()

    def _quantidade(self) -> int:
        v = self.opt_qtd.get()
        if v.startswith("Todos"):
            return len(self._selecionados())
        return int(v) if v.isdigit() else 0

    def _rodada(self) -> list[Item]:
        return self._selecionados()[: self._quantidade()]

    def _atualizar_resumo(self):
        if not self.projeto:
            return
        pend = self.projeto.pendentes()
        s = self.projeto.ultima_sincronizacao
        extra = []
        if s.get("substituidos"):
            extra.append(f"{s['substituidos']} mudaram")
        if s.get("orfaos"):
            extra.append(f"{s['orfaos']} removidos (→ _orfaos)")
        if s.get("importados"):
            extra.append(f"{s['importados']} aproveitados de antes")
        self.lbl_resumo.configure(
            text=f"{len(self.itens)} vídeo(s) · {len(self.itens) - len(pend)} concluído(s) · "
                 f"{len(pend)} pendente(s) ({hhmmss(sum(i.duracao for i in pend))})"
                 + (f" · {', '.join(extra)}" if extra else ""))

    # ================================================================== estimativa
    def _opcoes_mudaram(self):
        self.lbl_preset.configure(text=PRESETS[self._preset()]["descricao"])
        self._atualizar_estimativa()

    def _atualizar_estimativa(self):
        if not self.projeto or not hasattr(self, "lbl_estimativa"):
            return
        self.projeto.cfg.preset = self._preset()
        com_ocr = bool(self.chk_ocr.get())
        sel, rodada = self._selecionados(), self._rodada()
        es, er = self.projeto.estimar(sel, com_ocr), self.projeto.estimar(rodada, com_ocr)
        fim = (datetime.now() + timedelta(seconds=er.total)).strftime("%d/%m %H:%M") if rodada else "—"
        base = "medida neste PC" if er.medida else "estimativa inicial (melhora após o 1º vídeo)"
        texto = (f"ESTIMATIVA\n"
                 f"Marcados:      {len(sel):>3} vídeo(s) · ≈ {tempo_humano(es.total)}\n"
                 f"Nesta rodada:  {len(rodada):>3} vídeo(s) · {hhmmss(sum(i.duracao for i in rodada))} de vídeo\n"
                 f"  transcrição    ≈ {tempo_humano(er.segundos_transcricao)}\n"
                 + (f"  texto da tela  ≈ {tempo_humano(er.segundos_ocr)}\n" if com_ocr else "")
                 + f"  TOTAL          ≈ {tempo_humano(er.total)}  (fim ~{fim})\n"
                 f"Velocidade: {er.velocidade:.1f}x · {base}")
        self.lbl_estimativa.configure(text=texto)
        self.btn_iniciar.configure(state="normal" if rodada and not self.rodando else "disabled")

    # ================================================================== execução
    def _verificar_antes_de_iniciar(self, cfg: Config) -> bool:
        """Bloqueios com explicação e saída clara (corrige o OCR que 'sumia' sem aviso)."""
        if cfg.ocr and not ocr.verificar().disponivel:
            r = Dialogo(self, "Tesseract não instalado",
                        "Você marcou \"Ler texto da tela\", mas o Tesseract (o leitor de texto) não está "
                        "instalado. Sem ele, só a fala seria transcrita.",
                        [("Instalar Tesseract", "instalar", True),
                         ("Continuar sem ler a tela", "seguir", False),
                         ("Cancelar", None, False)]).perguntar()
            if r == "instalar":
                self._abrir_verificacao()
                return False
            if r != "seguir":
                return False
            self.chk_ocr.deselect()
            cfg.ocr = False
            self._opcoes_mudaram()
        if not modelo_baixado(cfg.modelo):
            tam = str(round(preparacao.TAMANHO_APROX.get(cfg.modelo, 1.6e9) / 1e9, 1)).replace(".", ",")
            r = Dialogo(self, "Baixar o modelo de transcrição",
                        f"Antes da primeira transcrição, o app precisa baixar o modelo \"{cfg.modelo}\" "
                        f"(~{tam} GB, uma única vez). Depois disso, tudo funciona sem internet.\n\n"
                        "Redes corporativas costumam bloquear esse download; se falhar, tente em outra rede.",
                        [("Baixar e começar", "ok", True), ("Cancelar", None, False)], icone="⬇️",
                        som=False).perguntar()
            if r != "ok":
                return False
        return True

    def _iniciar(self):
        rodada = self._rodada()
        cfg = self._cfg()
        if not rodada or cfg is None or self.projeto is None:
            return
        if not self._verificar_antes_de_iniciar(cfg):
            return
        e = self.projeto.estimar(rodada, cfg.ocr)
        r = Dialogo(self, "Confirmar rodada",
                    f"Processar {len(rodada)} vídeo(s)? Tempo estimado: ≈ {tempo_humano(e.total)}.\n\n"
                    "O PC fica mais lento enquanto isso, e o app impede que ele entre em suspensão. "
                    "Pode deixar rodando sozinho.",
                    [("Começar", "ok", True), ("Cancelar", None, False)], icone="▶️", som=False).perguntar()
        if r != "ok":
            return
        try:
            cfg = self.projeto.preparar_rodada(cfg)  # mesmas pastas da leitura (achado X3)
        except PastasMudaram as ex:
            Dialogo(self, "As pastas mudaram", str(ex), [("Entendi", None, True)], icone="ℹ️").perguntar()
            self._pastas_mudaram()
            return
        cfg.salvar()
        self.parar.clear()
        self.cancelar.clear()
        self._modo_rodando(True)
        self._dur_rodada = sum(i.duracao for i in rodada) or 1.0
        self._dur_feita = 0.0
        self._dur_atual = 0.0
        self._frac = 0.0
        self._com_ocr = cfg.ocr
        self._feitos, self._erros, self._palavras, self._total_rodada = 0, 0, 0, len(rodada)
        self._inicio = datetime.now()
        self.pb.set(0)
        self.lbl_tempo.configure(text="Calculando o tempo restante...")
        self._log(f"Rodada iniciada: {len(rodada)} vídeo(s), qualidade {PRESETS[cfg.preset]['rotulo']}"
                  f"{', com leitura de tela' if cfg.ocr else ''}.")

        projeto = self.projeto

        def tarefa():
            try:
                projeto.executar(rodada, self.fila.put, self.parar, self.cancelar)
            except Exception as ex:  # executar já trata; isto é a última rede de proteção (achado X16)
                self.fila.put(Evento("aviso", {"texto": f"Erro inesperado: {ex}"}))
                self.fila.put(Evento("lote_fim", {"ok": 0, "erro": 0, "fatal": str(ex)}))
        self._trabalho = threading.Thread(target=tarefa, daemon=True)
        self._trabalho.start()

    def _parar(self):
        self.parar.set()
        self.btn_parar.configure(state="disabled", text="⏸ Vai parar ao fim deste vídeo")
        self._log("Pedido de parada recebido: termina o vídeo atual e para.")

    def _cancelar(self):
        r = Dialogo(self, "Cancelar agora?", "O vídeo em andamento será perdido e refeito na próxima vez. "
                                             "Os vídeos já concluídos estão salvos.",
                    [("Cancelar agora", "sim", True), ("Continuar rodando", None, False)]).perguntar()
        if r == "sim":
            self.cancelar.set()
            self._log("Cancelando...")

    def _modo_rodando(self, sim: bool):
        self.rodando = sim
        estado = "disabled" if sim else "normal"
        for w in (self.btn_ler, self.seg_preset, self.chk_ocr, self.ent_vocab, self.opt_qtd,
                  self.ent_videos, self.ent_saida, self.btn_proc_videos, self.btn_proc_saida,
                  self.btn_corr, *self.btns_marcar):
            w.configure(state=estado)
        self.btn_iniciar.configure(state="disabled" if sim else "normal")
        self.btn_parar.configure(state="normal" if sim else "disabled", text="⏸ Parar após o vídeo atual")
        self.btn_cancelar.configure(state="normal" if sim else "disabled")

    # ---- etapas e progresso
    def _etapa(self, ativa: str | None, concluidas: set[str] = frozenset()):
        for cod, (lb, rot) in self.lbl_etapas.items():
            if cod == "telas" and not getattr(self, "_com_ocr", False):
                lb.configure(text=f"— {rot}", text_color=COR_ESPERA, font=self.f_normal)
            elif cod in concluidas:
                lb.configure(text=f"✓ {rot}", text_color=COR_FEITA, font=self.f_normal)
            elif cod == ativa:
                lb.configure(text=f"▶ {rot}", text_color=COR_ATIVA, font=self.f_negrito)
            else:
                lb.configure(text=f"○ {rot}", text_color=COR_ESPERA, font=self.f_normal)

    def _avancar(self, frac_video: float):
        """Barra única da rodada, ponderada pela duração; nunca volta para trás."""
        self._frac = max(self._frac, frac_video)
        total = (self._dur_feita + self._frac * self._dur_atual) / self._dur_rodada
        self.pb.set(max(self.pb.get(), min(total, 1.0)))

    # ================================================================== eventos
    def _consumir_fila(self):
        try:
            while True:
                self._tratar(self.fila.get_nowait())
        except queue.Empty:
            pass
        except Exception as e:  # um erro de interface não pode parar o consumo da fila
            self._log(f"Erro na interface: {e}")
        self._ciclos_fila += 1
        if self._ciclos_fila % 40 == 0:  # ~6 s
            gc.collect()
        self.after(150, self._consumir_fila)

    def _tratar(self, ev: Evento):
        d, t = ev.dados, ev.tipo
        if t == "chamar":
            d["fn"]()
        elif t == "outra_origem":
            self._outra_origem(d["erro"], d["cfg"])
        elif t == "verificacao":
            self._aplicar_situacao(d["situacao"], d["abrir"])
        elif t == "medindo":
            self.lbl_resumo.configure(text=f"Medindo durações... {d['n']} de {d['t']}")
        elif t == "falha_leitura":
            self.btn_ler.configure(state="normal")
            Dialogo(self, "Erro ao ler a pasta", d["erro"], [("Entendi", None, True)], icone="❌").perguntar()
        elif t == "escaneado":
            self.projeto = d["projeto"]
            self.itens = self.projeto.itens
            self.marcados = {i.rel for i in self.itens if i.status != ST_OK}
            self.btn_ler.configure(state="normal")
            self._atualizar_resumo()
            self._preencher_tabela()
            self._atualizar_correcoes()
            self._log(f"Pasta lida: {len(self.itens)} vídeo(s).")
            if not self.itens:
                self.lbl_resumo.configure(text="Nenhum vídeo encontrado nessa pasta (nem nas subpastas).")
        elif t == "lote_inicio":
            self._log(f"Previsão da rodada: ≈ {tempo_humano(d['segundos_previstos'])}.")
        elif t == "download":
            if d["total"]:
                self.pb.set(min(d["feito"] / d["total"], 0.99))
            self.lbl_status.configure(text="Baixando o modelo de transcrição (só na primeira vez)...")
            self.lbl_tempo.configure(text=f"{d['feito'] / 1e6:,.0f} de ~{d['total'] / 1e6:,.0f} MB".replace(",", "."))
        elif t == "video_inicio":
            self._dur_atual, self._frac = d["duracao"], 0.0
            if self.pb.get() > 0 and self._feitos == 0 and self._dur_feita == 0:
                self.pb.set(0)  # a barra do download dá lugar à barra da rodada
            nome = Path(d["rel"]).name
            self.lbl_status.configure(text=f"Processando {nome} ({d['indice']} de {d['total']})...")
            self._etapa("audio")
            self.tabela.set(d["rel"], "status", "▶ processando")
            self.tabela.see(d["rel"])
            self._log(f"Início: {d['rel']} ({hhmmss(d['duracao'])})")
        elif t == "etapa":
            cod = d.get("codigo")
            if cod == "modelo":
                self.lbl_status.configure(text=d["texto"])
            elif cod == "audio":
                self._etapa("audio")
                self._avancar(0.01)
            elif cod == "transcricao":
                self._etapa("transcricao", {"audio"})
                self._avancar(0.03)
            elif cod == "telas":
                self._etapa("telas", {"audio", "transcricao"})
                self._avancar(0.83)
            elif cod == "salvar":
                self._etapa("salvar", {"audio", "transcricao", "telas"})
                self._avancar(0.99)
            self._log(d["texto"])
        elif t == "progresso":
            parte = 0.80 if self._com_ocr else 0.95
            if d["total"]:
                self._avancar(0.03 + parte * d["pos"] / d["total"])
            if "falta_lote" in d:
                self.lbl_tempo.configure(
                    text=f"Faltam ~{tempo_humano(d['falta_lote'])} para terminar a rodada · término previsto "
                         f"~{d['termino']:%H:%M} · velocidade {d['velocidade']:.1f}x")
        elif t == "progresso_telas":
            if d["total"]:
                self._avancar(0.83 + 0.15 * d["feito"] / d["total"])
        elif t in ("video_fim", "video_erro"):
            self._dur_feita += self._dur_atual
            self._dur_atual, self._frac = 0.0, 0.0
            self._avancar(0.0)
            self._feitos += 1
            if t == "video_fim":
                self._palavras += d["palavras"]
                self.tabela.set(d["rel"], "status", STATUS_ROTULO[ST_OK])
                self.marcados.discard(d["rel"])
                self.tabela.set(d["rel"], "sel", DESMARCADO)
                self._log(f"Concluído: {d['rel']} — {d['palavras']} palavras, {d['velocidade']:.1f}x, "
                          f"{d['telas']} trecho(s) de tela, {d.get('correcoes', 0)} correção(ões).")
            else:
                self._erros += 1
                self.tabela.set(d["rel"], "status", STATUS_ROTULO[ST_ERRO])
                self._log(f"ERRO em {d['rel']}: {d['erro']}")
        elif t == "aviso":
            self._log("AVISO: " + d["texto"])
            if "Falha ao carregar o modelo" in d["texto"] or "já está sendo usada" in d["texto"]:
                Dialogo(self, "Não foi possível começar", d["texto"], [("Entendi", None, True)],
                        icone="❌").perguntar()
        elif t == "lote_fim":
            self._fim_da_rodada(d)

    def _fim_da_rodada(self, d):
        self._modo_rodando(False)
        self._etapa(None, {"audio", "transcricao", "telas", "salvar"} if d.get("ok") else set())
        dur = datetime.now() - getattr(self, "_inicio", datetime.now())
        erro = d.get("erro", 0)
        nivel, frase = resumo_final(d)  # nunca "sucesso" sem nenhum sucesso (achado X16)
        icone, cor = {"sucesso": ("✅", VERDE), "parcial": ("⚠️", LARANJA), "interrompido": ("⏸", LARANJA),
                      "vazio": ("ℹ️", LARANJA), "falha": ("❌", VERMELHO)}[nivel]
        texto = f"{icone} {frase}"
        if nivel == "sucesso":
            texto += f" · {self._palavras:,} palavras".replace(",", ".")
            self.pb.set(1.0)
        self.lbl_status.configure(text=texto, text_color=cor)
        self.lbl_tempo.configure(text=f"Duração da rodada: {tempo_humano(dur.total_seconds())}. "
                                      "Resultado na pasta de saída (botão 📂).")
        self._log("Rodada encerrada." + ("" if d.get("fatal") else " Base consolidada atualizada."))
        self._rodar_verificacao()  # o modelo pode ter sido baixado nesta rodada
        if (erro or nivel == "falha") and not self._log_visivel:
            self._alternar_log()
        self._atualizar_resumo()
        self._atualizar_quantidades()
        som_sucesso(self) if nivel == "sucesso" else som_aviso(self)
        piscar_barra_de_tarefas(self)
        self.after(8000, lambda: self.lbl_status.configure(text_color=("gray10", "gray90")))

    # ================================================================== diálogos
    def _ajuda(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Como usar")
        janela.geometry("700x640")
        caixa = ctk.CTkTextbox(janela, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        caixa.pack(fill="both", expand=True, padx=10, pady=10)
        caixa.insert("end", textos.COMO_USAR + "\n" + textos.SOBRE_IA_VISUAL)
        caixa.configure(state="disabled")
        from .componentes import trazer_para_frente
        trazer_para_frente(janela, self)

    def _abrir_saida(self):
        p = self._pasta(self.ent_saida)
        if not p or not p.exists():
            Dialogo(self, "Pasta de saída", "A pasta de saída ainda não existe. Ela é criada ao ler a pasta "
                                            "de vídeos.", [("Entendi", None, True)], icone="ℹ️", som=False).perguntar()
            return
        if sys.platform == "win32":
            os.startfile(p)  # noqa: S606
        else:
            subprocess.run(["xdg-open", str(p)])

    def _fechar(self):
        if self.rodando:
            r = Dialogo(self, "Sair?", "Há uma rodada em andamento. O vídeo atual será perdido e refeito na "
                                       "próxima vez (os concluídos estão salvos).",
                        [("Sair mesmo assim", "sair", True), ("Continuar rodando", None, False)]).perguntar()
            if r != "sair":
                return
        self.cancelar.set()
        self.parar.set()
        self.lbl_status.configure(text="Encerrando com segurança (salvando o registro)...")
        self._aguardar_e_fechar(50)

    def _aguardar_e_fechar(self, tentativas: int):
        """Espera a thread de trabalho soltar a trava e salvar o registro (até ~10 s)."""
        if self._trabalho is not None and self._trabalho.is_alive() and tentativas > 0:
            self.after(200, lambda: self._aguardar_e_fechar(tentativas - 1))
            return
        self.destroy()


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
