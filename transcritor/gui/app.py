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
from ..resultado import resumo_final
from . import marca, tema, textos
from .componentes import Dialogo, Dica, piscar_barra_de_tarefas, som_aviso, som_sucesso
from .verificacao import PainelVerificacao, Situacao, verificar

MARCADO, DESMARCADO = "☑", "☐"
STATUS_ROTULO = {ST_OK: "✓ Concluído", "pendente": "○ Pendente", ST_ERRO: "! Erro (tentar de novo)",
                 SUBSTITUIDO: "↻ Arquivo mudou"}
ROTULO_TELA_FALHOU = "✓ Concluído · ⚠ tela não lida"
ROTULO_NA_FILA, ROTULO_PROCESSANDO = "… Na fila", "▶ Transcrevendo"
ROTULO_PRESET = {v["rotulo"]: k for k, v in PRESETS.items()}
ETAPAS = [("audio", "Áudio"), ("transcricao", "Transcrição"), ("telas", "Texto da tela"), ("salvar", "Salvar")]
COR_ATIVA, COR_FEITA, COR_ESPERA = tema.VERDE, tema.VERDE_ESCURO, tema.CINZA_ESCURO
VERDE, LARANJA, VERMELHO = tema.VERDE, tema.LARANJA, tema.VERMELHO


tempo_humano = textos.tempo_humano


def nome_do_projeto(pasta: Path) -> str:
    """'D:/Cursos/Power BI/videos' -> 'Power BI' (nomes genéricos usam a pasta de cima)."""
    genericos = {"videos", "vídeos", "video", "vídeo", "aulas", "gravacoes", "gravações"}
    if pasta.name.lower() in genericos and pasta.parent.name:
        return pasta.parent.name
    return pasta.name or str(pasta)


class App(ctk.CTk):
    def __init__(self):
        tema.aplicar_tema()
        super().__init__()
        self.title(f"Transcritor Local {__version__}")
        self.geometry("1240x780")
        self.minsize(1100, 680)  # cabe em telas de 1366x768
        marca.aplicar_icone(self)

        self.fila: queue.Queue = queue.Queue()
        self.projeto: Projeto | None = None
        self.itens: list[Item] = []
        self.marcados: set[str] = set()
        self.rodando = False
        self.parar = threading.Event()
        self.cancelar = threading.Event()
        self.situacao: Situacao | None = None
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
        """Layout aprovado em 11/10/2026: barra lateral + 3 páginas + barra de ação (ADR-017)."""
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # Fontes criadas UMA vez: objetos de fonte destruídos pelo coletor de lixo numa thread de
        # trabalho chamam o Tk fora da thread principal e TRAVAM o app (bug real, pego em teste).
        self.f_normal = ctk.CTkFont()
        self.f_negrito = ctk.CTkFont(weight="bold")
        self.f_titulo = ctk.CTkFont(size=22, weight="bold")
        self.f_pequena = ctk.CTkFont(size=11)
        self.f_qtd = ctk.CTkFont(size=12)
        self.f_principal = ctk.CTkFont(size=15, weight="bold")
        tema.estilo_tabela(self)

        self._montar_lateral()
        ctk.CTkFrame(self, fg_color=tema.LATERAL_BORDA, width=1, corner_radius=0).grid(row=0, column=1, sticky="ns")
        self.miolo = ctk.CTkFrame(self, fg_color=tema.PRETO, corner_radius=0)
        self.miolo.grid(row=0, column=2, sticky="nsew", padx=22, pady=(16, 18))
        self.miolo.grid_columnconfigure(0, weight=1)
        self.miolo.grid_rowconfigure(0, weight=1)
        self.paginas = {
            "videos": self._montar_pagina_videos(self.miolo),
            "resultados": self._montar_pagina_resultados(self.miolo),
        }
        self.painel_verif = PainelVerificacao(self.miolo, self, ao_mudar=lambda s: self._aplicar_situacao(s, False))
        self.paginas["preparacao"] = self.painel_verif
        for pg in self.paginas.values():
            pg.grid(row=0, column=0, sticky="nsew")
        self._mostrar_pagina("videos")
        self._log("Aplicativo aberto.")
        self._opcoes_mudaram()

    # ------------------------------------------------------------------ barra lateral
    def _montar_lateral(self):
        lat = ctk.CTkFrame(self, fg_color=tema.LATERAL, corner_radius=0, width=230)
        lat.grid(row=0, column=0, sticky="nsw")
        lat.grid_propagate(False)
        lat.grid_columnconfigure(0, weight=1)
        lat.grid_rowconfigure(5, weight=1)

        cab = ctk.CTkFrame(lat, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 18))
        img = marca.desenhar(72)
        self._img_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
        ctk.CTkLabel(cab, image=self._img_logo, text="").pack(side="left")
        ctk.CTkLabel(cab, text="Transcritor", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(cab, text=" local", font=ctk.CTkFont(size=16), text_color=tema.VERDE).pack(side="left")

        ctk.CTkLabel(lat, text="PROJETO", font=self.f_pequena, text_color=tema.CINZA, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=20)
        cartao = ctk.CTkFrame(lat, fg_color="#0F1E18", border_width=1, border_color=tema.LATERAL_BORDA,
                              corner_radius=10)
        cartao.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 14))
        self.lbl_proj_nome = ctk.CTkLabel(cartao, text="Nenhuma pasta", font=self.f_negrito, anchor="w")
        self.lbl_proj_nome.pack(fill="x", padx=12, pady=(10, 0))
        self.lbl_proj_det = ctk.CTkLabel(cartao, text="Escolha a pasta dos vídeos", text_color=tema.CINZA,
                                         anchor="w", font=self.f_pequena)
        self.lbl_proj_det.pack(fill="x", padx=12, pady=(0, 10))

        nav = ctk.CTkFrame(lat, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=10)
        self.nav, self.selos = {}, {}
        for chave, icone, texto in (("videos", "▤", "Vídeos"), ("resultados", "✓", "Resultados"),
                                    ("preparacao", "⚙", "Preparação do PC")):
            b = ctk.CTkButton(nav, text=f"{icone}   {texto}", anchor="w", height=40, corner_radius=8,
                              fg_color="transparent", hover_color=tema.LATERAL_ATIVO, text_color=tema.BRANCO,
                              command=lambda c=chave: self._mostrar_pagina(c))
            b.pack(fill="x", pady=2)
            selo = ctk.CTkLabel(b, text="", width=24, height=20, corner_radius=10, fg_color="#1F2A25",
                                text_color=tema.BRANCO, font=self.f_pequena)
            selo.bind("<Button-1>", lambda _e, c=chave: self._mostrar_pagina(c))
            self.nav[chave], self.selos[chave] = b, selo

        rod = ctk.CTkFrame(lat, fg_color="transparent")
        rod.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 16))
        ctk.CTkFrame(rod, fg_color=tema.LATERAL_BORDA, height=1).pack(fill="x", pady=(0, 12))
        self.lbl_lat_titulo = ctk.CTkLabel(rod, text="Verificando o PC...", anchor="w", font=self.f_negrito,
                                           text_color=tema.CINZA)
        self.lbl_lat_titulo.pack(fill="x")
        self.lbl_lat_det = ctk.CTkLabel(rod, text="", anchor="w", text_color=tema.CINZA, font=self.f_pequena)
        self.lbl_lat_det.pack(fill="x")
        self.pb_lat = ctk.CTkProgressBar(rod, height=6)
        self.pb_lat.set(0)
        self.lbl_lat_fim = ctk.CTkLabel(rod, text="", anchor="w", text_color=tema.CINZA, font=self.f_pequena)
        linha = ctk.CTkFrame(rod, fg_color="transparent")
        linha.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(linha, text="Ajuda", width=60, height=24, command=self._ajuda,
                      **tema.link()).pack(side="left")
        ctk.CTkLabel(linha, text=f"v{__version__}", text_color=tema.CINZA_ESCURO,
                     font=self.f_pequena).pack(side="right")
        self._lat_linha = linha

    def _mostrar_pagina(self, nome: str):
        self.pagina = nome
        self.paginas[nome].tkraise()
        for chave, b in self.nav.items():
            ativo = chave == nome
            b.configure(fg_color=tema.LATERAL_ATIVO if ativo else "transparent",
                        text_color=tema.VERDE if ativo else tema.BRANCO)
        if nome == "resultados":
            self._atualizar_resultados()
        elif nome == "preparacao" and self.situacao is not None:
            self.painel_verif.mostrar(self.situacao, self._preset(), self._pasta(self.ent_saida))

    def _selo(self, chave: str, n: int, cor: str = "#1F2A25", texto_cor: str = tema.BRANCO):
        selo = self.selos[chave]
        if n:
            selo.configure(text=str(n), fg_color=cor, text_color=texto_cor)
            selo.place(relx=1.0, x=-10, rely=0.5, anchor="e")
        else:
            selo.place_forget()

    def _atualizar_lateral(self):
        if self.projeto is not None:
            feitos = sum(1 for i in self.itens if i.status == ST_OK)
            self.lbl_proj_nome.configure(text=nome_do_projeto(self.projeto.cfg.pasta_videos))
            self.lbl_proj_det.configure(text=f"{len(self.itens)} vídeo(s) · {feitos} concluído(s)")
            self._selo("videos", len(self.itens) - feitos)
        else:
            self.lbl_proj_nome.configure(text="Nenhuma pasta")
            self.lbl_proj_det.configure(text="Escolha a pasta dos vídeos")
            self._selo("videos", 0)
        if self.rodando:
            return
        self.pb_lat.pack_forget()
        self.lbl_lat_fim.pack_forget()
        s = self.situacao
        if s is None:
            self.lbl_lat_titulo.configure(text="Verificando o PC...", text_color=tema.CINZA)
            self.lbl_lat_det.configure(text="")
        elif s.obrigatorios:
            self.lbl_lat_titulo.configure(text="⚠ Falta preparar o PC", text_color=tema.VERMELHO)
            self.lbl_lat_det.configure(text=", ".join(s.obrigatorios))
        else:
            disp = getattr(s.diagnostico, "dispositivo", "cpu").upper()
            self.lbl_lat_titulo.configure(text=f"✓ PC pronto · {disp}", text_color=tema.CINZA)
            self.lbl_lat_det.configure(text="Tesseract não instalado (opcional)" if s.opcionais else "")

    def _lateral_rodada(self, pct: float, detalhe: str, fim: str = ""):
        self.lbl_lat_titulo.configure(text="Rodada em andamento", text_color=tema.VERDE)
        self.lbl_lat_det.configure(text=detalhe, text_color=tema.BRANCO)
        if not self.pb_lat.winfo_ismapped():
            self.pb_lat.pack(fill="x", pady=(6, 4), before=self._lat_linha)
            self.lbl_lat_fim.pack(fill="x", before=self._lat_linha)
        self.pb_lat.set(pct)
        if fim:
            self.lbl_lat_fim.configure(text=fim)

    # ------------------------------------------------------------------ página: vídeos
    def _montar_pagina_videos(self, pai):
        pg = ctk.CTkFrame(pai, fg_color=tema.PRETO)
        pg.grid_columnconfigure(0, weight=1)
        pg.grid_rowconfigure(3, weight=1)

        topo = ctk.CTkFrame(pg, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(topo, text="Vídeos", font=self.f_titulo).pack(side="left")
        self.lbl_trava = ctk.CTkLabel(topo, text="🔒 travado durante a rodada", fg_color=tema.SUPERFICIE_2,
                                      corner_radius=12, text_color=tema.CINZA, font=self.f_pequena, height=26)

        pastas = ctk.CTkFrame(pg, fg_color="transparent")
        pastas.grid(row=1, column=0, sticky="ew", pady=(12, 2))
        pastas.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pastas, text="Origem", text_color=tema.CINZA, width=64, anchor="w").grid(row=0, column=0, sticky="w")
        self.ent_videos = ctk.CTkEntry(pastas, height=36,
                                       placeholder_text="Pasta com os vídeos (pode ter subpastas)")
        self.ent_videos.grid(row=0, column=1, sticky="ew", pady=4)
        self.btn_proc_videos = ctk.CTkButton(pastas, text="Escolher", width=96, height=36,
                                             command=self._escolher_videos, **tema.secundario())
        self.btn_proc_videos.grid(row=0, column=2, padx=(8, 0))
        self.btn_ler = ctk.CTkButton(pastas, text="Ler pasta", width=96, height=36, command=self._ler_pasta,
                                     **tema.secundario())
        self.btn_ler.grid(row=0, column=3, padx=(8, 0))
        Dica(self.btn_ler, "Lista os vídeos e mostra quais já foram transcritos. "
                           "Use de novo se você adicionar ou remover vídeos.")
        ctk.CTkLabel(pastas, text="Saída", text_color=tema.CINZA, width=64, anchor="w").grid(row=1, column=0, sticky="w")
        self.ent_saida = ctk.CTkEntry(pastas, height=36, placeholder_text="Onde salvar as transcrições")
        self.ent_saida.grid(row=1, column=1, sticky="ew", pady=4)
        self.btn_proc_saida = ctk.CTkButton(pastas, text="Escolher", width=96, height=36,
                                            command=self._escolher_saida, **tema.secundario())
        self.btn_proc_saida.grid(row=1, column=2, padx=(8, 0))
        ctk.CTkButton(pastas, text="Abrir", width=96, height=36, command=self._abrir_saida,
                      **tema.secundario()).grid(row=1, column=3, padx=(8, 0))
        # Trocar a pasta à mão invalida a leitura anterior (achado X3)
        for ent in (self.ent_videos, self.ent_saida):
            ent.bind("<KeyRelease>", lambda _e: self._pastas_mudaram())

        self.lbl_resumo = ctk.CTkLabel(pg, text="Comece escolhendo a pasta com os vídeos.", anchor="w",
                                       text_color=tema.CINZA, font=self.f_pequena)
        self.lbl_resumo.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        meio = ctk.CTkFrame(pg, fg_color="transparent")
        meio.grid(row=3, column=0, sticky="nsew")
        meio.grid_columnconfigure(0, weight=1)
        meio.grid_rowconfigure(0, weight=1)
        self._montar_tabela(meio)
        self._montar_opcoes(meio)
        self._montar_barra(pg)
        return pg

    def _montar_tabela(self, pai):
        tab = ctk.CTkFrame(pai, border_width=1, border_color=tema.BORDA, corner_radius=10)
        tab.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        cab = ctk.CTkFrame(tab, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))
        self.lbl_contagem = ctk.CTkLabel(cab, text="Nenhum vídeo listado", text_color=tema.CINZA)
        self.lbl_contagem.pack(side="left")
        self.btns_marcar = []
        for txt, fn, dica in (("Nenhum", self._desmarcar_todos, "Desmarca todos"),
                              ("Todos", self._marcar_todos, "Marca todos, inclusive os concluídos"),
                              ("Pendentes", self._marcar_pendentes, "Marca só o que falta transcrever")):
            b = ctk.CTkButton(cab, text=txt, width=86, height=28, command=fn, **tema.secundario())
            b.pack(side="right", padx=(6, 0))
            Dica(b, dica)
            self.btns_marcar.append(b)
        self.tabela = ttk.Treeview(tab, columns=("sel", "video", "dur", "status"), show="headings",
                                   selectmode="browse", style="Escuro.Treeview")
        for col, txt, larg, anc, est in (("sel", MARCADO, 40, "center", False), ("video", "Vídeo", 360, "w", True),
                                         ("dur", "Duração", 84, "center", False),
                                         ("status", "Status", 210, "w", False)):
            self.tabela.heading(col, text=txt, anchor=anc)
            self.tabela.column(col, width=larg, minwidth=larg if not est else 180, anchor=anc, stretch=est)
        self.tabela.tag_configure("rodando", foreground=tema.VERDE)
        self.tabela.tag_configure("erro", foreground=tema.VERMELHO)
        self.tabela.tag_configure("mudou", foreground=tema.LARANJA)
        self.tabela.tag_configure("feito", foreground=tema.CINZA)
        self.tabela.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        rolagem = ctk.CTkScrollbar(tab, command=self.tabela.yview)
        rolagem.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=(0, 10))
        self.tabela.configure(yscrollcommand=rolagem.set)
        self.tabela.bind("<Button-1>", self._clique_tabela)
        self.tabela.heading("sel", command=self._alternar_todos)
        self.tabela.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_info_video())

    def _montar_opcoes(self, pai):
        op = ctk.CTkScrollableFrame(pai, width=290, border_width=1, border_color=tema.BORDA, corner_radius=10,
                                    fg_color=tema.SUPERFICIE)
        op.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(op, text="Opções da rodada", font=self.f_negrito, anchor="w").pack(fill="x", padx=4, pady=(6, 8))
        self.seg_preset = ctk.CTkSegmentedButton(op, values=[v["rotulo"] for v in PRESETS.values()],
                                                 command=lambda _: self._opcoes_mudaram(), height=32)
        self.seg_preset.set(PRESETS["equilibrado"]["rotulo"])
        self.seg_preset.pack(fill="x", padx=4)
        self.lbl_preset = ctk.CTkLabel(op, text="", wraplength=270, justify="left", anchor="w",
                                       text_color=tema.CINZA, font=self.f_pequena)
        self.lbl_preset.pack(fill="x", padx=4, pady=(4, 12))

        self.chk_ocr = ctk.CTkCheckBox(op, text="Ler texto da tela", command=self._opcoes_mudaram)
        self.chk_ocr.pack(anchor="w", padx=4)
        Dica(self.chk_ocr, "Lê slides, código e menus que aparecem no vídeo e junta ao texto. "
                           "Precisa do Tesseract (veja Preparação do PC).")
        self.lbl_ocr = ctk.CTkLabel(op, text="", text_color=tema.CINZA, wraplength=270, justify="left",
                                    anchor="w", font=self.f_pequena)
        self.lbl_ocr.pack(fill="x", padx=4, pady=(2, 10))

        self.btn_vocab = ctk.CTkButton(op, text="▸  Vocabulário e correções", height=28,
                                       command=self._alternar_vocab, **tema.link())
        self.btn_vocab.pack(fill="x", padx=0)
        self.frm_vocab = ctk.CTkFrame(op, fg_color="transparent")
        ctk.CTkLabel(self.frm_vocab, text="Vocabulário de dicas", anchor="w").pack(fill="x", pady=(4, 0))
        self.ent_vocab = ctk.CTkEntry(self.frm_vocab, placeholder_text="Ex.: Power BI, DAX, ChatGPT, hook")
        self.ent_vocab.pack(fill="x", pady=2)
        ctk.CTkLabel(self.frm_vocab, text="Ajuda o Whisper a ouvir certo nomes e termos técnicos. Não garante.",
                     text_color=tema.CINZA, wraplength=260, justify="left", anchor="w",
                     font=self.f_pequena).pack(fill="x")
        ctk.CTkLabel(self.frm_vocab, text="Correções automáticas", anchor="w").pack(fill="x", pady=(10, 0))
        linha_corr = ctk.CTkFrame(self.frm_vocab, fg_color="transparent")
        linha_corr.pack(fill="x", pady=(2, 0))
        self.lbl_corr = ctk.CTkLabel(linha_corr, text="Leia uma pasta primeiro.", text_color=tema.CINZA,
                                     font=self.f_pequena)
        self.lbl_corr.pack(side="left")
        self.btn_corr = ctk.CTkButton(linha_corr, text="Editar lista", width=100, height=28, state="disabled",
                                      command=self._editar_correcoes, **tema.secundario())
        self.btn_corr.pack(side="right")
        Dica(self.btn_corr, "Troca o texto DEPOIS de transcrever, sempre: \"Chatepte\" vira \"ChatGPT\". "
                            "Só palavras inteiras. Cuidado com palavras reais (ex.: \"Hulk\").")

        ctk.CTkFrame(op, fg_color=tema.BORDA, height=1).pack(fill="x", padx=4, pady=(12, 10))
        self.lbl_info_tit = ctk.CTkLabel(op, text="VÍDEO SELECIONADO", text_color=tema.CINZA, anchor="w",
                                         font=self.f_pequena)
        self.lbl_info_tit.pack(fill="x", padx=4)
        self.lbl_info_nome = ctk.CTkLabel(op, text="Clique num vídeo da lista.", anchor="w", font=self.f_negrito,
                                          wraplength=270, justify="left")
        self.lbl_info_nome.pack(fill="x", padx=4)
        self.lbl_info_det = ctk.CTkLabel(op, text="", anchor="w", text_color=tema.CINZA, wraplength=270,
                                         justify="left", font=self.f_pequena)
        self.lbl_info_det.pack(fill="x", padx=4, pady=(0, 6))

    def _montar_barra(self, pg):
        self.barra = ctk.CTkFrame(pg, border_width=1, border_color=tema.BORDA, corner_radius=10)
        self.barra.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.barra.grid_columnconfigure(0, weight=1)

        # ---- modo "escolher a rodada"
        self.barra_acao = acao = ctk.CTkFrame(self.barra, fg_color="transparent")
        acao.grid_columnconfigure(0, weight=1)
        txt = ctk.CTkFrame(acao, fg_color="transparent")
        txt.grid(row=0, column=0, sticky="w", padx=(16, 8), pady=12)
        self.lbl_sel_resumo = ctk.CTkLabel(txt, text="Nenhuma pasta lida", font=self.f_negrito, anchor="w")
        self.lbl_sel_resumo.pack(fill="x")
        self.lbl_sel_det = ctk.CTkLabel(txt, text="Escolha a pasta dos vídeos para começar.", anchor="w",
                                        text_color=tema.CINZA, font=self.f_pequena, justify="left")
        self.lbl_sel_det.pack(fill="x")
        self.frm_qtd = ctk.CTkFrame(acao, fg_color="transparent")
        self.frm_qtd.grid(row=0, column=1, padx=4)
        self.btns_qtd: dict[str, ctk.CTkButton] = {}
        self._qtd: str | None = None
        self.btn_iniciar = ctk.CTkButton(acao, text="Transcrever", width=170, height=52, state="disabled",
                                         font=self.f_principal, command=self._iniciar)
        self.btn_iniciar.grid(row=0, column=2, padx=(8, 14), pady=12)
        self._estado_principal(False)

        # ---- modo "rodada em andamento / terminada"
        self.barra_rodada = rod = ctk.CTkFrame(self.barra, fg_color="transparent")
        rod.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(rod, text="", anchor="w", font=self.f_negrito, justify="left")
        self.lbl_status.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(12, 0))
        botoes = ctk.CTkFrame(rod, fg_color="transparent")
        botoes.grid(row=0, column=1, rowspan=2, sticky="ne", padx=14, pady=(10, 0))
        self.btn_parar = ctk.CTkButton(botoes, text="Parar após este vídeo", width=170, height=34,
                                       state="disabled", command=self._parar, **tema.secundario())
        Dica(self.btn_parar, "Termina o vídeo em andamento e para. Nada se perde.")
        self.btn_cancelar = ctk.CTkButton(botoes, text="Cancelar", width=100, height=34, state="disabled",
                                          command=self._cancelar, **tema.perigo())
        Dica(self.btn_cancelar, "Interrompe na hora. O vídeo em andamento será refeito na próxima vez.")
        self.btn_ver_resultado = ctk.CTkButton(botoes, text="Ver resultados", width=130, height=34,
                                               command=lambda: self._mostrar_pagina("resultados"),
                                               **tema.secundario())
        self.btn_nova = ctk.CTkButton(botoes, text="Nova rodada", width=120, height=34,
                                      command=self._mostrar_acao)
        linha_etapas = ctk.CTkFrame(rod, fg_color="transparent")
        linha_etapas.grid(row=1, column=0, sticky="w", padx=16, pady=(4, 0))
        self.lbl_etapas = {}
        for n, (cod, rot) in enumerate(ETAPAS):
            if n:
                ctk.CTkLabel(linha_etapas, text="·", text_color=tema.CINZA_ESCURO).pack(side="left", padx=6)
            lb = ctk.CTkLabel(linha_etapas, text=f"○ {rot}", text_color=COR_ESPERA)
            lb.pack(side="left")
            self.lbl_etapas[cod] = (lb, rot)
        self.pb = ctk.CTkProgressBar(rod, height=10)
        self.pb.set(0)
        self.pb.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 0))
        self.lbl_tempo = ctk.CTkLabel(rod, text="", anchor="w", text_color=tema.CINZA, font=self.f_pequena)
        self.lbl_tempo.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 10))
        self._mostrar_acao()

    def _estado_principal(self, ativo: bool):
        """Botão principal: verde só quando dá para clicar (verde = clicável)."""
        if ativo:
            self.btn_iniciar.configure(state="normal", fg_color=tema.VERDE, hover_color=tema.VERDE_ESCURO,
                                       text_color=tema.PRETO)
        else:
            self.btn_iniciar.configure(state="disabled", fg_color=tema.SUPERFICIE_2,
                                       text_color_disabled=tema.CINZA_ESCURO)

    def _mostrar_acao(self):
        if self.rodando:
            return
        self.barra_rodada.grid_remove()
        self.barra_acao.grid(row=0, column=0, sticky="ew", padx=2, pady=2)  # sem cobrir a borda
        self.barra.configure(border_color=tema.BORDA)
        self._atualizar_quantidades()

    def _mostrar_rodada(self, rodando: bool):
        self.barra_acao.grid_remove()
        self.barra_rodada.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.barra.configure(border_color=tema.VERDE if rodando else tema.BORDA, border_width=2 if rodando else 1)
        for b in (self.btn_parar, self.btn_cancelar, self.btn_ver_resultado, self.btn_nova):
            b.pack_forget()
        mostrar = (self.btn_parar, self.btn_cancelar) if rodando else (self.btn_ver_resultado, self.btn_nova)
        for b in mostrar:
            b.pack(side="left", padx=(8, 0))

    def _alternar_vocab(self):
        if self.frm_vocab.winfo_ismapped():
            self.frm_vocab.pack_forget()
            self.btn_vocab.configure(text="▸  Vocabulário e correções")
        else:
            self.frm_vocab.pack(fill="x", padx=4, after=self.btn_vocab)
            self.btn_vocab.configure(text="▾  Vocabulário e correções")

    def _mostrar_info_video(self):
        sel = self.tabela.selection()
        if self.rodando or not sel:
            return
        it = next((i for i in self.itens if i.rel == sel[0]), None)
        if it is None:
            return
        l = it.linha
        self.lbl_info_tit.configure(text="VÍDEO SELECIONADO")
        self.lbl_info_nome.configure(text=Path(it.rel).name)
        partes = [str(Path(it.rel).parent) if "/" in it.rel else "pasta principal", hhmmss(it.duracao)]
        if it.status == ST_OK:
            partes.append(f"{l.palavras:,} palavras".replace(",", "."))
            if l.transcrito_em:
                partes.append(f"transcrito em {l.transcrito_em}")
        else:
            partes.append(self._rotulo(it).lstrip("○!↻ ").lower())
        if l.observacao:
            partes.append(l.observacao)
        self.lbl_info_det.configure(text=" · ".join(partes))

    # ------------------------------------------------------------------ página: resultados
    def _montar_pagina_resultados(self, pai):
        pg = ctk.CTkFrame(pai, fg_color=tema.PRETO)
        pg.grid_columnconfigure(0, weight=1)
        pg.grid_rowconfigure(2, weight=1)
        topo = ctk.CTkFrame(pg, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(topo, text="Resultados", font=self.f_titulo).pack(side="left")
        ctk.CTkButton(topo, text="Abrir base consolidada", width=170, height=34,
                      command=lambda: self._abrir_saida("base_consolidada"), **tema.secundario()).pack(side="right")
        ctk.CTkButton(topo, text="Abrir pasta de saída", width=160, height=34, command=self._abrir_saida,
                      **tema.secundario()).pack(side="right", padx=(0, 8))
        self.btn_pacote = ctk.CTkButton(topo, text="Pacote para IA", width=130, height=34,
                                        command=self._gerar_pacote, **tema.secundario())
        self.btn_pacote.pack(side="right", padx=(0, 8))
        Dica(self.btn_pacote,
             "Cria, para cada vídeo concluído, uma pasta e um .zip com o .md e só as capturas que ele cita. "
             "É o que você anexa numa conversa com qualquer IA.")
        self.lbl_res_resumo = ctk.CTkLabel(pg, text="", anchor="w", text_color=tema.CINZA, justify="left")
        self.lbl_res_resumo.grid(row=1, column=0, sticky="ew", pady=(6, 10))
        cartao = ctk.CTkFrame(pg, border_width=1, border_color=tema.BORDA, corner_radius=10)
        cartao.grid(row=2, column=0, sticky="nsew")
        cartao.grid_columnconfigure(0, weight=1)
        cartao.grid_rowconfigure(0, weight=1)
        self.res_tabela = ttk.Treeview(cartao, columns=("video", "palavras", "vel", "tela", "data"),
                                       show="headings", selectmode="browse", style="Escuro.Treeview")
        for col, txt, larg, anc, est in (("video", "Vídeo", 340, "w", True), ("palavras", "Palavras", 90, "e", False),
                                         ("vel", "Velocidade", 90, "center", False),
                                         ("tela", "Texto da tela", 120, "center", False),
                                         ("data", "Transcrito em", 140, "center", False)):
            self.res_tabela.heading(col, text=txt, anchor=anc)
            self.res_tabela.column(col, width=larg, minwidth=larg if not est else 180, anchor=anc, stretch=est)
        self.res_tabela.tag_configure("falhou", foreground=tema.LARANJA)
        self.res_tabela.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        rol = ctk.CTkScrollbar(cartao, command=self.res_tabela.yview)
        rol.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=10)
        self.res_tabela.configure(yscrollcommand=rol.set)
        ctk.CTkLabel(pg, text="REGISTRO DE ATIVIDADES", text_color=tema.CINZA, font=self.f_pequena,
                     anchor="w").grid(row=3, column=0, sticky="ew", pady=(14, 4))
        self.log = ctk.CTkTextbox(pg, height=150, border_width=1, corner_radius=10,
                                  font=ctk.CTkFont(family=tema.FONTE_MONO, size=11))
        self.log.grid(row=4, column=0, sticky="ew")
        return pg

    def _atualizar_resultados(self):
        if not hasattr(self, "res_tabela"):
            return
        self.res_tabela.delete(*self.res_tabela.get_children())
        if self.projeto is None:
            self.lbl_res_resumo.configure(text="Leia uma pasta de vídeos para ver os resultados.")
            return
        feitos = [l for l in self.projeto.registro.ativos() if l.status == ST_OK]
        for l in feitos:
            self.res_tabela.insert("", "end", values=(
                l.caminho.replace("/", " / "), f"{l.palavras:,}".replace(",", "."),
                f"{l.velocidade:.1f}x".replace(".", ",") if l.velocidade else "—",
                textos.rotulo_tela(l.ocr, l.capturas), l.transcrito_em or "—"), tags=("falhou",) if l.ocr == "falhou" else ())
        palavras = sum(l.palavras for l in feitos)
        horas = sum(l.duracao_s for l in feitos)
        self.lbl_res_resumo.configure(
            text=(f"{len(feitos)} vídeo(s) concluído(s) · {palavras:,} palavras de fala · ".replace(",", ".")
                  + f"{tempo_humano(horas)} de vídeo transcrito.\n"
                    "Arquivos .md em transcricoes_md · base para a IA em base_consolidada · "
                    "para anexar numa conversa, use \"Pacote para IA\".") if feitos else
                 "Nenhum vídeo concluído ainda.")

    # ================================================================== utilidades
    def _log(self, texto: str):
        self.log.insert("end", f"[{datetime.now():%H:%M:%S}] {texto}\n")
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
            self._selo("preparacao", len(s.obrigatorios), cor="#5A1F1F", texto_cor=tema.VERMELHO)
        elif n:
            self._selo("preparacao", n)
        else:
            self._selo("preparacao", 0)
        self.lbl_ocr.configure(text="+15–35% de tempo · "
                               + textos.rotulo_tesseract(s.tesseract_ok, s.tesseract_portugues))
        self._atualizar_lateral()
        if getattr(self, "pagina", "") == "preparacao":
            self.painel_verif.mostrar(s, self._preset(), self._pasta(self.ent_saida))
        if s.obrigatorios:
            self._pulsar(6)
        if abrir and s.obrigatorios:
            self._log("Verificação: falta " + ", ".join(s.obrigatorios) + ". Abrindo a preparação.")
            self._abrir_verificacao()
            som_aviso(self)

    def _pulsar(self, vezes):
        """Pisca o item "Preparação do PC" para chamar atenção sem bloquear nada."""
        b = self.nav["preparacao"]
        if vezes <= 0 or getattr(self, "pagina", "") == "preparacao":
            self._mostrar_pagina(self.pagina) if hasattr(self, "pagina") else None
            return
        b.configure(fg_color="#3A2A10" if vezes % 2 else "transparent")
        self.after(350, lambda: self._pulsar(vezes - 1))

    def _abrir_verificacao(self):
        if self.situacao is None:
            self._rodar_verificacao(abrir_se_obrigatorio=True)
            self._log("Verificando o PC...")
        self._mostrar_pagina("preparacao")

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
        if self.rodando or getattr(self, "_lendo", False):  # uma leitura por vez (achado X4)
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
        self._lendo = True
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
        self._lendo = False
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
            self.lbl_corr.configure(text=f"{len(regras)} regra(s) ativa(s)", text_color=tema.CINZA)
        else:
            self.lbl_corr.configure(text="Nenhuma regra (opcional).", text_color=tema.CINZA)

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
            self.tabela.insert("", "end", iid=it.rel, tags=self._tags(it),
                               values=(sel, it.rel.replace("/", " / "), hhmmss(it.duracao), self._rotulo(it)))
        self._atualizar_quantidades()
        self._atualizar_lateral()

    @staticmethod
    def _tags(it: Item) -> tuple:
        return {ST_ERRO: ("erro",), SUBSTITUIDO: ("mudou",)}.get(it.status, ())

    @staticmethod
    def _rotulo(it: Item) -> str:
        if it.status == ST_OK and it.linha.ocr == "falhou":
            return ROTULO_TELA_FALHOU
        return STATUS_ROTULO.get(it.status, it.status)

    def _clique_tabela(self, ev):
        """Clique na caixinha (1ª coluna) marca/desmarca; no resto da linha, só seleciona."""
        if self.rodando or self.tabela.identify_region(ev.x, ev.y) != "cell":
            return
        linha = self.tabela.identify_row(ev.y)
        if not linha or self.tabela.identify_column(ev.x) != "#1":
            return
        self.marcados.symmetric_difference_update({linha})
        self.tabela.set(linha, "sel", MARCADO if linha in self.marcados else DESMARCADO)
        self._atualizar_quantidades()

    def _alternar_todos(self):
        if self.rodando or not self.itens:
            return
        (self._desmarcar_todos if len(self.marcados) == len(self.itens) else self._marcar_todos)()

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
        if not hasattr(self, "frm_qtd"):
            return
        n = len(self._selecionados())
        opcoes = [str(q) for q in (1, 3, 5) if q < n] + (["todos"] if n else [])
        if list(self.btns_qtd) != opcoes:
            for b in self.btns_qtd.values():
                b.destroy()
            self.btns_qtd = {}
            for chave in opcoes:
                b = ctk.CTkButton(self.frm_qtd, text="", width=92, height=52, font=self.f_qtd,
                                  command=lambda c=chave: self._escolher_qtd(c), **tema.secundario())
                b.pack(side="left", padx=4)
                self.btns_qtd[chave] = b
        if self._qtd not in opcoes:
            self._qtd = None
        self.lbl_contagem.configure(text=f"{len(self.itens)} vídeo(s) · {n} marcado(s)" if self.itens
                                    else "Nenhum vídeo listado")
        self._atualizar_estimativa()

    def _escolher_qtd(self, chave: str):
        if self.rodando:
            return
        self._qtd = chave
        self._atualizar_estimativa()

    def _quantidade(self) -> int:
        if self._qtd is None:
            return 0
        if self._qtd == "todos":
            return len(self._selecionados())
        return int(self._qtd)

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
        if s.get("ausentes"):
            extra.append(f"{s['ausentes']} sem transcrição (serão refeitos)")
        if s.get("registro_recuperado"):
            extra.append("registro recuperado da cópia de emergência")
        self.lbl_resumo.configure(
            text=textos.resumo_da_leitura(len(self.itens) - len(pend), len(pend), sum(i.duracao for i in pend))
                 + (f" · {', '.join(extra)}" if extra else ""))
        self._atualizar_lateral()

    # ================================================================== estimativa
    def _opcoes_mudaram(self):
        self.lbl_preset.configure(text=PRESETS[self._preset()]["descricao"])
        self._atualizar_estimativa()

    def _atualizar_estimativa(self):
        if not hasattr(self, "btn_iniciar"):
            return
        if not self.projeto:
            self.lbl_sel_resumo.configure(text="Nenhuma pasta lida")
            self.lbl_sel_det.configure(text="Escolha a pasta dos vídeos para começar.")
            self._estado_principal(False)
            return
        self.projeto.cfg.preset = self._preset()
        com_ocr = bool(self.chk_ocr.get())
        sel, rodada = self._selecionados(), self._rodada()
        self.lbl_sel_resumo.configure(
            text=f"{len(sel)} marcado(s) · {tempo_humano(sum(i.duracao for i in sel))} de vídeo" if sel
            else "Nenhum vídeo marcado")
        for chave, b in self.btns_qtd.items():
            q = len(sel) if chave == "todos" else int(chave)
            rot = f"Todos ({len(sel)})" if chave == "todos" else chave
            e = self.projeto.estimar(sel[:q], com_ocr)
            escolhido = chave == self._qtd
            b.configure(text=f"{rot}\n≈ {tempo_humano(e.total)}",
                        fg_color=tema.VERDE_FUNDO if escolhido else tema.SUPERFICIE_2,
                        border_color=tema.VERDE if escolhido else tema.BORDA_FORTE,
                        text_color=tema.BRANCO)
        if rodada:
            er = self.projeto.estimar(rodada, com_ocr)
            fim = (datetime.now() + timedelta(seconds=er.total)).strftime("%H:%M")
            base = "medida neste PC" if er.medida else "estimativa inicial"
            self.lbl_sel_det.configure(text=f"Esta rodada: ≈ {tempo_humano(er.total)}, término ~{fim} · "
                                            f"{er.velocidade:.1f}x ({base})".replace(".", ","))
            self.btn_iniciar.configure(text=f"Transcrever {len(rodada)}")
        else:
            self.lbl_sel_det.configure(text="Quantos vídeos nesta rodada? (obrigatório)" if sel
                                       else "Marque os vídeos na lista.")
            self.btn_iniciar.configure(text="Transcrever")
        self._estado_principal(bool(rodada) and not self.rodando)

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
        self.lbl_status.configure(text="Preparando a rodada...", text_color=tema.BRANCO)
        self._indice = 0
        for it in rodada:
            self.tabela.set(it.rel, "status", ROTULO_NA_FILA)
        self._lateral_rodada(0.0, f"0 de {len(rodada)} · 0%")
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
        self.btn_parar.configure(state="disabled", text="Para ao fim deste vídeo")
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
        for w in (self.btn_ler, self.seg_preset, self.chk_ocr, self.ent_vocab, self.ent_videos, self.ent_saida,
                  self.btn_proc_videos, self.btn_proc_saida, self.btn_corr, *self.btns_marcar,
                  *self.btns_qtd.values()):
            w.configure(state=estado)
        if sim:
            self.lbl_trava.pack(side="right")
        else:
            self.lbl_trava.pack_forget()
        self._mostrar_rodada(sim)
        self.btn_parar.configure(state="normal" if sim else "disabled", text="Parar após este vídeo")
        self.btn_cancelar.configure(state="normal" if sim else "disabled")
        self._estado_principal(False)

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
        if self.rodando:
            pct = self.pb.get()
            self._lateral_rodada(pct, f"{getattr(self, '_indice', 0)} de {self._total_rodada} · {pct:.0%}")

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
            self._lendo = False
            self.btn_ler.configure(state="normal")
            Dialogo(self, "Erro ao ler a pasta", d["erro"], [("Entendi", None, True)], icone="❌").perguntar()
        elif t == "escaneado":
            self._lendo = False
            self.projeto = d["projeto"]
            self.itens = self.projeto.itens
            self.marcados = {i.rel for i in self.itens if i.status != ST_OK}
            self.btn_ler.configure(state="normal")
            self._mostrar_acao()
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
            self._indice = d["indice"]
            self.lbl_status.configure(text=f"Processando {d['indice']} de {d['total']} · "
                                           f"{d['rel'].replace('/', ' / ')}", text_color=tema.BRANCO)
            self._etapa("audio")
            self.tabela.set(d["rel"], "status", ROTULO_PROCESSANDO)
            self.tabela.item(d["rel"], tags=("rodando",))
            self.tabela.see(d["rel"])
            self.lbl_info_tit.configure(text="EM ANDAMENTO")
            self.lbl_info_nome.configure(text=nome)
            self.lbl_info_det.configure(text=f"0:00 de {hhmmss(d['duracao'])}")
            self._avancar(0.0)
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
            self.lbl_info_det.configure(text=f"{hhmmss(d['pos'])} de {hhmmss(d['total'])}")
            if "falta_lote" in d:
                self.lbl_tempo.configure(
                    text=f"Rodada {self.pb.get():.0%} · faltam ~{tempo_humano(d['falta_lote'])} · término "
                         f"~{d['termino']:%H:%M} · velocidade {d['velocidade']:.1f}x".replace(".", ","))
                self.lbl_lat_fim.configure(text=f"término ~{d['termino']:%H:%M}")
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
                self.tabela.set(d["rel"], "status", ROTULO_TELA_FALHOU if d.get("falha_telas")
                                else STATUS_ROTULO[ST_OK])
                self.tabela.item(d["rel"], tags=())
                self.marcados.discard(d["rel"])
                self.tabela.set(d["rel"], "sel", DESMARCADO)
                self._log(f"Concluído: {d['rel']} — {d['palavras']} palavras, {d['velocidade']:.1f}x, "
                          f"{d['telas']} trecho(s) de tela"
                          + (f" (de {d['capturas_lidas']} capturas lidas)" if d.get("capturas_lidas") else "")
                          + f", {d.get('correcoes', 0)} correção(ões).")
            else:
                self._erros += 1
                self.tabela.set(d["rel"], "status", STATUS_ROTULO[ST_ERRO])
                self.tabela.item(d["rel"], tags=("erro",))
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
        nivel, frase = resumo_final(d)  # nunca "sucesso" sem nenhum sucesso (achados X16 e X10)
        icone, cor = {"sucesso": ("✓", tema.VERDE), "parcial": ("⚠", tema.LARANJA), "interrompido": ("⏸", tema.LARANJA),
                      "vazio": ("i", tema.LARANJA), "falha": ("✕", tema.VERMELHO)}[nivel]
        texto = f"{icone}  {frase}"
        if nivel == "sucesso":
            texto += f" · {self._palavras:,} palavras".replace(",", ".")
            self.pb.set(1.0)
        self.lbl_status.configure(text=texto, text_color=cor)
        self.lbl_tempo.configure(text=f"Duração da rodada: {tempo_humano(dur.total_seconds())}. "
                                      "Os arquivos estão na pasta de saída (botão Abrir).")
        self._log("Rodada encerrada." + ("" if d.get("fatal") else " Base consolidada atualizada."))
        if erro or nivel == "falha":
            self._log("Detalhes dos erros: veja as linhas acima e a coluna observacao do registro.csv.")
        self._rodar_verificacao()  # o modelo pode ter sido baixado nesta rodada
        self._preencher_tabela()  # vídeos que não terminaram voltam a "Pendente" (achado N10)
        self._atualizar_resumo()
        self._atualizar_quantidades()
        self._atualizar_resultados()
        self.lbl_info_tit.configure(text="ÚLTIMA RODADA")
        self.lbl_info_nome.configure(text={"sucesso": "Concluída", "parcial": "Concluída com avisos",
                                           "interrompido": "Interrompida", "vazio": "Nada feito",
                                           "falha": "Falhou"}[nivel])
        self.lbl_info_det.configure(text=f"{d.get('ok', 0)} concluído(s) · {erro} com erro · "
                                         f"{tempo_humano(dur.total_seconds())}")
        som_sucesso(self) if nivel == "sucesso" else som_aviso(self)
        piscar_barra_de_tarefas(self)

    # ================================================================== diálogos
    def _ajuda(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Como usar")
        janela.geometry("700x640")
        caixa = ctk.CTkTextbox(janela, wrap="word", font=ctk.CTkFont(family=tema.FONTE_MONO, size=12))
        caixa.pack(fill="both", expand=True, padx=10, pady=10)
        caixa.insert("end", textos.COMO_USAR + "\n" + textos.SOBRE_IA_VISUAL)
        caixa.configure(state="disabled")
        from .componentes import trazer_para_frente
        trazer_para_frente(janela, self)

    def _gerar_pacote(self):
        if self.projeto is None or self.rodando:
            return
        try:
            pacotes = self.projeto.gerar_pacotes()
        except Exception as e:
            Dialogo(self, "Pacote para IA", f"Não consegui criar o pacote: {e}", [("Entendi", None, True)],
                    icone="⚠️", som=False).perguntar()
            return
        if not pacotes:
            Dialogo(self, "Pacote para IA", "Ainda não há vídeo concluído para empacotar.",
                    [("Entendi", None, True)], icone="ℹ️", som=False).perguntar()
            return
        self._log(f"Pacote para IA: {len(pacotes)} pasta(s) e .zip em pacote_para_ia.")
        self._abrir_saida("pacote_para_ia")

    def _abrir_saida(self, sub: str = ""):
        p = self._pasta(self.ent_saida)
        if p and sub:
            p = p / sub
        if not p or not p.exists():
            Dialogo(self, "Pasta de saída", "Essa pasta ainda não existe. Ela é criada ao ler a pasta "
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
