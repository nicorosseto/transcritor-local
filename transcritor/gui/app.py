"""App desktop (CustomTkinter). Toda a lógica vem de transcritor.pipeline; aqui é só interface.

O trabalho pesado roda numa thread separada; ela manda eventos por uma fila e a
interface consome a fila a cada 150 ms (o Tkinter não pode ser tocado fora da thread principal).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from .. import __version__
from ..config import NOME_ARQUIVO_CONFIG, PRESETS, Config, vocabulario_de_texto
from ..hardware import AVISO, ERRO, OK, diagnosticar
from ..pipeline import Evento, Item, Projeto
from ..registro import ERRO as ST_ERRO
from ..registro import OK as ST_OK
from ..registro import SUBSTITUIDO
from ..util import hhmmss
from . import textos

MARCADO, DESMARCADO = "☑", "☐"
STATUS_ROTULO = {ST_OK: "✅ concluído", "pendente": "⏳ pendente", ST_ERRO: "⚠️ erro (tentar de novo)",
                 SUBSTITUIDO: "🔄 arquivo mudou"}
ICONE = {OK: "✅", AVISO: "⚠️", ERRO: "❌", "info": "ℹ️"}
ROTULO_PRESET = {v["rotulo"]: k for k, v in PRESETS.items()}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        self.title(f"Transcritor Local {__version__}")
        self.geometry("1100x760")
        self.minsize(900, 640)

        self.fila: queue.Queue = queue.Queue()
        self.projeto: Projeto | None = None
        self.itens: list[Item] = []
        self.marcados: set[str] = set()
        self.rodando = False
        self.parar = threading.Event()
        self.cancelar = threading.Event()

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(150, self._consumir_fila)

    # ================================================================== layout
    def _montar(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(self)
        topo.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        topo.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(topo, text="① Pasta dos vídeos").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.ent_videos = ctk.CTkEntry(topo, placeholder_text="Escolha a pasta com os vídeos")
        self.ent_videos.grid(row=0, column=1, sticky="ew", pady=6)
        ctk.CTkButton(topo, text="Procurar", width=100, command=self._escolher_videos).grid(row=0, column=2, padx=8)
        ctk.CTkLabel(topo, text="② Pasta de saída").grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.ent_saida = ctk.CTkEntry(topo, placeholder_text="Onde salvar as transcrições")
        self.ent_saida.grid(row=1, column=1, sticky="ew", pady=6)
        ctk.CTkButton(topo, text="Procurar", width=100, command=self._escolher_saida).grid(row=1, column=2, padx=8)
        self.btn_ler = ctk.CTkButton(topo, text="Ler pasta", width=120, command=self._ler_pasta)
        self.btn_ler.grid(row=0, column=3, rowspan=2, padx=8)

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="ew", padx=12)
        self.lbl_resumo = ctk.CTkLabel(barra, text="Escolha a pasta dos vídeos e clique em \"Ler pasta\".")
        self.lbl_resumo.pack(side="left")
        ctk.CTkButton(barra, text="❓ Como usar", width=110, command=self._ajuda).pack(side="right", padx=4)
        ctk.CTkButton(barra, text="🖥 Verificar PC", width=120, command=self._verificar_pc).pack(side="right", padx=4)

        meio = ctk.CTkFrame(self)
        meio.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)
        meio.grid_columnconfigure(0, weight=3)
        meio.grid_columnconfigure(1, weight=0, minsize=400)
        meio.grid_rowconfigure(0, weight=1)

        # ---- tabela de vídeos
        tab = ctk.CTkFrame(meio)
        tab.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        estilo = ttk.Style()
        estilo.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        self.tabela = ttk.Treeview(tab, columns=("sel", "video", "dur", "status"), show="headings",
                                   selectmode="none")
        for col, txt, larg, anc in (("sel", "③", 40, "center"), ("video", "Vídeo", 360, "w"),
                                    ("dur", "Duração", 80, "center"), ("status", "Status", 170, "w")):
            self.tabela.heading(col, text=txt)
            self.tabela.column(col, width=larg, anchor=anc, stretch=(col == "video"))
        self.tabela.grid(row=0, column=0, sticky="nsew")
        rolagem = ttk.Scrollbar(tab, orient="vertical", command=self.tabela.yview)
        rolagem.grid(row=0, column=1, sticky="ns")
        self.tabela.configure(yscrollcommand=rolagem.set)
        self.tabela.bind("<Button-1>", self._clique_tabela)
        botoes = ctk.CTkFrame(tab, fg_color="transparent")
        botoes.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for txt, fn in (("Marcar pendentes", self._marcar_pendentes), ("Marcar todos", self._marcar_todos),
                        ("Desmarcar todos", self._desmarcar_todos)):
            ctk.CTkButton(botoes, text=txt, width=130, command=fn).pack(side="left", padx=3)

        # ---- opções e estimativa
        direita = ctk.CTkFrame(meio, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew", padx=(3, 6), pady=6)
        direita.grid_rowconfigure(0, weight=1)
        direita.grid_columnconfigure(0, weight=1)
        op = ctk.CTkScrollableFrame(direita, label_text="④ Opções", width=370, height=260)
        op.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(op, text="Qualidade", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.seg_preset = ctk.CTkSegmentedButton(op, values=[v["rotulo"] for v in PRESETS.values()],
                                                 command=lambda _: self._opcoes_mudaram())
        self.seg_preset.set(PRESETS["equilibrado"]["rotulo"])
        self.seg_preset.pack(fill="x", pady=(2, 2))
        self.lbl_preset = ctk.CTkLabel(op, text="", wraplength=340, justify="left", text_color="gray")
        self.lbl_preset.pack(anchor="w", pady=(0, 8))

        self.chk_ocr = ctk.CTkCheckBox(op, text="Ler texto da tela (slides, código, menus)",
                                       command=self._opcoes_mudaram)
        self.chk_ocr.pack(anchor="w", pady=4)
        ctk.CTkLabel(op, text="+15–35% de tempo. Precisa do Tesseract (veja Verificar PC).",
                     text_color="gray", wraplength=340, justify="left").pack(anchor="w")
        ctk.CTkCheckBox(op, text="Descrever telas com IA visual (em breve: v0.2)",
                        state="disabled").pack(anchor="w", pady=(8, 0))

        ctk.CTkLabel(op, text="Vocabulário de dicas", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(12, 0))
        self.ent_vocab = ctk.CTkEntry(op, placeholder_text="Ex.: Power BI, DAX, ChatGPT, Claude")
        self.ent_vocab.pack(fill="x", pady=2)

        ctk.CTkLabel(op, text="Processar nesta rodada (obrigatório)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(12, 0))
        self.opt_qtd = ctk.CTkOptionMenu(op, values=["Escolha..."], command=lambda _: self._atualizar_estimativa())
        self.opt_qtd.pack(fill="x", pady=2)

        caixa_est = ctk.CTkFrame(direita)
        caixa_est.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.lbl_estimativa = ctk.CTkLabel(caixa_est, text="Leia uma pasta para ver a estimativa.",
                                           justify="left", anchor="w",
                                           font=ctk.CTkFont(family="Consolas", size=12))
        self.lbl_estimativa.pack(fill="x", padx=10, pady=8)

        # ---- execução
        exe = ctk.CTkFrame(self)
        exe.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 6))
        exe.grid_columnconfigure(1, weight=1)
        self.btn_iniciar = ctk.CTkButton(exe, text="▶  INICIAR", width=160, height=36, state="disabled",
                                         command=self._iniciar)
        self.btn_iniciar.grid(row=0, column=0, rowspan=2, padx=8, pady=8)
        self.lbl_atual = ctk.CTkLabel(exe, text="Aguardando.", anchor="w")
        self.lbl_atual.grid(row=0, column=1, sticky="ew")
        self.pb_video = ctk.CTkProgressBar(exe)
        self.pb_video.set(0)
        self.pb_video.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.lbl_lote = ctk.CTkLabel(exe, text="", anchor="w")
        self.lbl_lote.grid(row=2, column=1, sticky="ew")
        self.pb_lote = ctk.CTkProgressBar(exe)
        self.pb_lote.set(0)
        self.pb_lote.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))
        lado = ctk.CTkFrame(exe, fg_color="transparent")
        lado.grid(row=0, column=2, rowspan=4, padx=8)
        self.btn_parar = ctk.CTkButton(lado, text="⏸ Parar após o vídeo atual", state="disabled",
                                       command=self._parar)
        self.btn_parar.pack(pady=2, fill="x")
        self.btn_cancelar = ctk.CTkButton(lado, text="✖ Cancelar agora", state="disabled",
                                          fg_color="#8a2a2a", hover_color="#6e1f1f", command=self._cancelar)
        self.btn_cancelar.pack(pady=2, fill="x")
        ctk.CTkButton(lado, text="📂 Abrir pasta de saída", command=self._abrir_saida).pack(pady=2, fill="x")

        self.log = ctk.CTkTextbox(self, height=90)
        self.log.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        self._log("Bem-vindo! Comece pelo passo ① lá em cima. Dúvidas: botão \"Como usar\".")
        self._opcoes_mudaram()

    # ================================================================== utilidades
    def _log(self, texto: str):
        self.log.insert("end", texto + "\n")
        self.log.see("end")

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

    # ================================================================== pastas
    def _escolher_videos(self):
        p = filedialog.askdirectory(title="Pasta com os vídeos")
        if p:
            self._definir(self.ent_videos, p)
            if not self.ent_saida.get().strip():
                pv = Path(p)
                self._definir(self.ent_saida, str(pv.parent / f"{pv.name}_transcricoes"))
            self._ler_pasta()

    def _escolher_saida(self):
        p = filedialog.askdirectory(title="Pasta de saída")
        if p:
            self._definir(self.ent_saida, p)

    def _ler_pasta(self):
        if self.rodando:
            return
        videos, saida = self._pasta(self.ent_videos), self._pasta(self.ent_saida)
        if not videos or not saida:
            messagebox.showinfo("Faltam pastas", "Escolha a pasta dos vídeos e a pasta de saída.")
            return
        cfg = Config.carregar(saida, videos)
        erros = cfg.validar()
        if erros:
            messagebox.showerror("Pastas inválidas", "\n".join(erros))
            return
        # preenche as opções salvas da última vez nessa pasta de saída (se houver)
        if (saida / NOME_ARQUIVO_CONFIG).is_file():
            self.seg_preset.set(PRESETS[cfg.preset]["rotulo"])
            self.chk_ocr.select() if cfg.ocr else self.chk_ocr.deselect()
            self._definir(self.ent_vocab, ", ".join(cfg.vocabulario))
            self._opcoes_mudaram()
        self.btn_ler.configure(state="disabled")
        self.lbl_resumo.configure(text="Lendo a pasta e medindo as durações...")

        def tarefa():
            try:
                proj = Projeto(cfg)
                proj.escanear(lambda n, t: self.fila.put(Evento("medindo", {"n": n, "t": t})))
                self.fila.put(Evento("escaneado", {"projeto": proj}))
            except Exception as e:
                self.fila.put(Evento("falha_leitura", {"erro": str(e)}))
        threading.Thread(target=tarefa, daemon=True).start()

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
        if linha in self.marcados:
            self.marcados.discard(linha)
        else:
            self.marcados.add(linha)
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

    # ================================================================== estimativa
    def _opcoes_mudaram(self):
        self.lbl_preset.configure(text=PRESETS[ROTULO_PRESET[self.seg_preset.get()]]["descricao"])
        self._atualizar_estimativa()

    def _atualizar_estimativa(self):
        if not self.projeto or not hasattr(self, "lbl_estimativa"):
            return
        self.projeto.cfg.preset = ROTULO_PRESET[self.seg_preset.get()]
        com_ocr = bool(self.chk_ocr.get())
        sel, rodada = self._selecionados(), self._rodada()
        es, er = self.projeto.estimar(sel, com_ocr), self.projeto.estimar(rodada, com_ocr)
        dur_sel, dur_rod = sum(i.duracao for i in sel), sum(i.duracao for i in rodada)
        from datetime import datetime, timedelta
        fim = (datetime.now() + timedelta(seconds=er.total)).strftime("%d/%m %H:%M") if rodada else "—"
        base = "medida neste PC" if er.medida else "estimativa inicial (melhora após o 1º vídeo)"
        texto = (f"ESTIMATIVA\n"
                 f"Marcados:      {len(sel):>3} vídeo(s) | {hhmmss(dur_sel)} | ≈ {hhmmss(es.total)}\n"
                 f"Nesta rodada:  {len(rodada):>3} vídeo(s) | {hhmmss(dur_rod)}\n"
                 f"  transcrição  ≈ {hhmmss(er.segundos_transcricao)}\n"
                 + (f"  texto da tela≈ {hhmmss(er.segundos_ocr)}\n" if com_ocr else "")
                 + f"  TOTAL        ≈ {hhmmss(er.total)}  (fim ~{fim})\n"
                 f"Velocidade: {er.velocidade:.1f}x — {base}")
        self.lbl_estimativa.configure(text=texto)
        self.btn_iniciar.configure(state="normal" if rodada and not self.rodando else "disabled")

    # ================================================================== execução
    def _iniciar(self):
        rodada = self._rodada()
        cfg = self._cfg()
        if not rodada or cfg is None or self.projeto is None:
            return
        e = self.projeto.estimar(rodada, cfg.ocr)
        if not messagebox.askyesno("Confirmar",
                                   f"Processar {len(rodada)} vídeo(s)?\nTempo estimado: ≈ {hhmmss(e.total)}\n\n"
                                   "O PC vai ficar mais lento enquanto isso."):
            return
        cfg.salvar()
        self.projeto.cfg = cfg
        self.parar.clear()
        self.cancelar.clear()
        self._modo_rodando(True)
        self._total_rodada = len(rodada)
        self._feitos = 0

        def tarefa():
            try:
                self.projeto.executar(rodada, self.fila.put, self.parar, self.cancelar)
            except Exception as ex:
                self.fila.put(Evento("aviso", {"texto": f"Erro inesperado: {ex}"}))
                self.fila.put(Evento("lote_fim", {"ok": 0, "erro": 0}))
        threading.Thread(target=tarefa, daemon=True).start()

    def _parar(self):
        self.parar.set()
        self.btn_parar.configure(state="disabled", text="⏸ Vai parar ao fim deste vídeo")
        self._log("Pedido de parada recebido: termina o vídeo atual e para.")

    def _cancelar(self):
        if messagebox.askyesno("Cancelar agora?", "O vídeo em andamento será perdido e refeito na "
                                                  "próxima vez. Os já concluídos estão salvos. Cancelar?"):
            self.cancelar.set()
            self._log("Cancelando...")

    def _modo_rodando(self, sim: bool):
        self.rodando = sim
        estado = "disabled" if sim else "normal"
        for w in (self.btn_ler, self.seg_preset, self.chk_ocr, self.ent_vocab, self.opt_qtd):
            w.configure(state=estado)
        self.btn_iniciar.configure(state="disabled" if sim else "normal")
        self.btn_parar.configure(state="normal" if sim else "disabled", text="⏸ Parar após o vídeo atual")
        self.btn_cancelar.configure(state="normal" if sim else "disabled")

    # ================================================================== eventos
    def _consumir_fila(self):
        try:
            while True:
                self._tratar(self.fila.get_nowait())
        except queue.Empty:
            pass
        self.after(150, self._consumir_fila)

    def _tratar(self, ev: Evento):
        d = ev.dados
        t = ev.tipo
        if t == "medindo":
            self.lbl_resumo.configure(text=f"Medindo durações... {d['n']}/{d['t']}")
        elif t == "falha_leitura":
            self.btn_ler.configure(state="normal")
            messagebox.showerror("Erro ao ler a pasta", d["erro"])
        elif t == "escaneado":
            self.projeto = d["projeto"]
            self.itens = self.projeto.itens
            self.marcados = {i.rel for i in self.itens if i.status != ST_OK}
            self.btn_ler.configure(state="normal")
            self._atualizar_resumo()
            self._preencher_tabela()
            if not self.itens:
                self._log("Nenhum vídeo encontrado nessa pasta (nem nas subpastas).")
        elif t == "lote_inicio":
            self._log(f"Iniciando {d['total']} vídeo(s) — previsão ≈ {hhmmss(d['segundos_previstos'])}.")
        elif t == "video_inicio":
            self.lbl_atual.configure(text=f"[{d['indice']}/{d['total']}] {d['rel']}")
            self.pb_video.set(0)
            self.tabela.set(d["rel"], "status", "▶ processando")
            self.tabela.see(d["rel"])
        elif t == "etapa":
            self._log("   " + d["texto"])
        elif t == "progresso":
            if d["total"]:
                self.pb_video.set(min(1.0, d["pos"] / d["total"]))
            txt = f"{hhmmss(d['pos'])} / {hhmmss(d['total'])}"
            if "velocidade" in d:
                txt += (f"   |   {d['velocidade']:.1f}x   |   falta neste vídeo ~{hhmmss(d['falta_video'])}"
                        f"   |   rodada termina ~{d['termino']:%d/%m %H:%M}")
            self.lbl_lote.configure(text=txt)
        elif t in ("video_fim", "video_erro"):
            self._feitos += 1
            self.pb_lote.set(self._feitos / max(self._total_rodada, 1))
            if t == "video_fim":
                self.tabela.set(d["rel"], "status", STATUS_ROTULO[ST_OK])
                self.marcados.discard(d["rel"])
                self.tabela.set(d["rel"], "sel", DESMARCADO)
                self._log(f"✅ {d['rel']}: {d['palavras']} palavras, {d['velocidade']:.1f}x, "
                          f"{d['telas']} trecho(s) de tela")
            else:
                self.tabela.set(d["rel"], "status", STATUS_ROTULO[ST_ERRO])
                self._log(f"❌ {d['rel']}: {d['erro']}")
        elif t == "aviso":
            self._log("⚠️ " + d["texto"])
        elif t == "lote_fim":
            self._modo_rodando(False)
            self.lbl_atual.configure(text=f"Fim: {d.get('ok', 0)} concluído(s), {d.get('erro', 0)} com erro.")
            self._log("Rodada encerrada. Base consolidada atualizada.")
            self._atualizar_resumo()
            self._atualizar_quantidades()

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
            text=f"{len(self.itens)} vídeo(s) | {len(self.itens) - len(pend)} concluídos | "
                 f"{len(pend)} pendentes ({hhmmss(sum(i.duracao for i in pend))})"
                 + (f" | {', '.join(extra)}" if extra else ""))

    # ================================================================== diálogos
    def _verificar_pc(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Verificação do PC")
        janela.geometry("720x520")
        caixa = ctk.CTkTextbox(janela, wrap="word")
        caixa.pack(fill="both", expand=True, padx=10, pady=10)
        caixa.insert("end", "Verificando...\n")

        def tarefa():
            d = diagnosticar(self._pasta(self.ent_saida))
            linhas = []
            for i in d.itens:
                linhas.append(f"{ICONE.get(i.nivel, '')} {i.nome}: {i.valor}\n     {i.explicacao}\n")
            linhas.append(f"\nRecomendação: qualidade \"{PRESETS[d.preset_recomendado]['rotulo']}\", "
                          f"rodando em {d.dispositivo.upper()}.")
            if not d.pode_rodar:
                linhas.append("\n❌ Há itens obrigatórios faltando (marcados com ❌).")
            texto = "\n".join(linhas)
            self.after(0, lambda: (caixa.delete("1.0", "end"), caixa.insert("end", texto)))
        threading.Thread(target=tarefa, daemon=True).start()

    def _ajuda(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Como usar")
        janela.geometry("680x620")
        caixa = ctk.CTkTextbox(janela, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        caixa.pack(fill="both", expand=True, padx=10, pady=10)
        caixa.insert("end", textos.COMO_USAR + "\n" + textos.SOBRE_IA_VISUAL)
        caixa.configure(state="disabled")

    def _abrir_saida(self):
        p = self._pasta(self.ent_saida)
        if not p or not p.exists():
            messagebox.showinfo("Pasta de saída", "A pasta de saída ainda não existe.")
            return
        if sys.platform == "win32":
            os.startfile(p)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p)])


    def _fechar(self):
        if self.rodando and not messagebox.askyesno(
                "Sair?", "Há uma rodada em andamento. O vídeo atual será perdido e refeito na "
                         "próxima vez (os concluídos estão salvos). Sair mesmo assim?"):
            return
        self.cancelar.set()
        self.after(300, self.destroy)


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
