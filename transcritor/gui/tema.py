"""Paleta e tema visual aprovados em 11/10/2026 (ADR-017).

Fundo preto, textos brancos, barra lateral em preto esverdeado, e verde SÓ no que é clicável ou
selecionado. O tema do CustomTkinter é ajustado em memória (sem arquivo .json para empacotar).
"""

from __future__ import annotations

import sys
from tkinter import ttk

import customtkinter as ctk

PRETO = "#000000"
SUPERFICIE = "#0B0B0B"       # cartões e painéis
SUPERFICIE_2 = "#141414"     # botões secundários, campos
BORDA = "#262626"
BORDA_FORTE = "#3A3A3A"
LATERAL = "#0A1612"          # barra lateral
LATERAL_BORDA = "#1D3A2E"
LATERAL_ATIVO = "#12301F"
VERDE = "#4FD18B"
VERDE_ESCURO = "#2FAE6A"
VERDE_FUNDO = "#0F2A1C"      # realce suave (linha selecionada, cartão escolhido)
BRANCO = "#FFFFFF"
CINZA = "#A3A3A3"
CINZA_ESCURO = "#6B6B6B"
LARANJA = "#F5B04B"
VERMELHO = "#F87171"

FONTE = "Segoe UI" if sys.platform == "win32" else "Roboto"
FONTE_MONO = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"


def aplicar_tema() -> None:
    """Deve ser chamado ANTES de criar a primeira janela."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    t = ctk.ThemeManager.theme

    def p(widget, **cores):
        for k, v in cores.items():
            t[widget][k] = v if v == "transparent" else [v, v]  # [claro, escuro]: o app é sempre escuro

    p("CTk", fg_color=PRETO)
    p("CTkToplevel", fg_color=PRETO)
    p("CTkFrame", fg_color=SUPERFICIE, top_fg_color=SUPERFICIE_2, border_color=BORDA)
    p("CTkButton", fg_color=VERDE, hover_color=VERDE_ESCURO, border_color=BORDA_FORTE,
      text_color=PRETO, text_color_disabled=CINZA_ESCURO)
    p("CTkLabel", text_color=BRANCO)
    p("CTkEntry", fg_color=SUPERFICIE, border_color=BORDA, text_color=BRANCO,
      placeholder_text_color=CINZA_ESCURO)
    t["CTkEntry"]["border_width"] = 1
    p("CTkCheckBox", fg_color=VERDE, border_color=BORDA_FORTE, hover_color=VERDE_ESCURO,
      checkmark_color=PRETO, text_color=BRANCO, text_color_disabled=CINZA_ESCURO)
    t["CTkCheckBox"]["border_width"] = 2
    p("CTkProgressBar", fg_color="#1F1F1F", progress_color=VERDE, border_color=BORDA)
    p("CTkSegmentedButton", fg_color=SUPERFICIE_2, selected_color=VERDE, selected_hover_color=VERDE_ESCURO,
      unselected_color=SUPERFICIE_2, unselected_hover_color="#1F1F1F", text_color=BRANCO,
      text_color_disabled=CINZA_ESCURO)
    p("CTkOptionMenu", fg_color=SUPERFICIE_2, button_color=SUPERFICIE_2, button_hover_color="#1F1F1F",
      text_color=BRANCO, text_color_disabled=CINZA_ESCURO)
    p("CTkScrollbar", button_color="#2A2A2A", button_hover_color=BORDA_FORTE)
    p("CTkTextbox", fg_color=SUPERFICIE, border_color=BORDA, text_color=BRANCO,
      scrollbar_button_color="#2A2A2A", scrollbar_button_hover_color=BORDA_FORTE)
    p("CTkScrollableFrame", label_fg_color=SUPERFICIE)
    p("DropdownMenu", fg_color=SUPERFICIE_2, hover_color="#1F1F1F", text_color=BRANCO)
    fonte = t["CTkFont"]  # o CustomTkinter já reduz este bloco à plataforma atual ao carregar o tema
    for bloco in [fonte] if "family" in fonte else [v for v in fonte.values() if isinstance(v, dict)]:
        bloco["family"] = FONTE


def secundario(**extra) -> dict:
    """Botão secundário: escuro com borda; o verde fica para a ação principal."""
    base = dict(fg_color=SUPERFICIE_2, hover_color="#1F1F1F", text_color=BRANCO, border_width=1,
                border_color=BORDA_FORTE)
    base.update(extra)
    return base


def perigo(**extra) -> dict:
    base = dict(fg_color=SUPERFICIE_2, hover_color="#2A1414", text_color=VERMELHO, border_width=1,
                border_color="#5A2A2A")
    base.update(extra)
    return base


def link(**extra) -> dict:
    """Texto clicável sem caixa (verde = clicável)."""
    base = dict(fg_color="transparent", hover_color=SUPERFICIE_2, text_color=VERDE, anchor="w")
    base.update(extra)
    return base


def estilo_tabela(raiz) -> None:
    est = ttk.Style(raiz)
    est.theme_use("clam")
    est.configure("Escuro.Treeview", background=PRETO, fieldbackground=PRETO, foreground=BRANCO,
                  bordercolor=BORDA, lightcolor=PRETO, darkcolor=PRETO, borderwidth=0,
                  rowheight=34, font=(FONTE, 10))
    est.map("Escuro.Treeview", background=[("selected", VERDE_FUNDO)], foreground=[("selected", BRANCO)])
    est.configure("Escuro.Treeview.Heading", background=PRETO, foreground=CINZA, relief="flat",
                  bordercolor=BORDA, lightcolor=PRETO, darkcolor=PRETO, font=(FONTE, 10))
    est.map("Escuro.Treeview.Heading", background=[("active", SUPERFICIE_2)])
    est.layout("Escuro.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    est.configure("Escuro.Vertical.TScrollbar", background="#2A2A2A", troughcolor=PRETO, bordercolor=PRETO,
                  arrowcolor=CINZA, lightcolor="#2A2A2A", darkcolor="#2A2A2A")
