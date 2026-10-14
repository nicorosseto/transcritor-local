"""Peças reutilizáveis da interface: dica flutuante, diálogo modal e utilidades de janela."""

from __future__ import annotations

import sys
import tkinter as tk

import customtkinter as ctk

_FONTE = "Segoe UI" if sys.platform == "win32" else "Roboto"


class Dica:
    """Dica que aparece ao parar o mouse sobre um widget (tooltip)."""

    def __init__(self, widget, texto: str, atraso_ms: int = 450):
        self.widget, self.texto, self.atraso = widget, texto, atraso_ms
        self._id = None
        self._janela = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        widget.bind("<ButtonPress>", self._esconder, add="+")

    def _agendar(self, _=None):
        self._cancelar()
        self._id = self.widget.after(self.atraso, self._mostrar)

    def _cancelar(self):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None

    def _mostrar(self):
        if self._janela or not self.texto:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._janela = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(tw, text=self.texto, justify="left", wraplength=340, bg="#141414", fg="#FFFFFF",
                 relief="solid", borderwidth=1, padx=10, pady=7, font=(_FONTE, 9)).pack()

    def _esconder(self, _=None):
        self._cancelar()
        if self._janela:
            self._janela.destroy()
            self._janela = None


def centralizar(janela, pai) -> None:
    """Centraliza a janela no meio do pai (horizontal e vertical).

    Mede o tamanho PEDIDO pelo conteúdo: o CTkToplevel nasce com 200x200 e `winfo_width` devolvia isso,
    o que deixava a janela deslocada para a direita e para cima (achado N12)."""
    janela.update_idletasks()
    w, h = janela.winfo_reqwidth(), janela.winfo_reqheight()
    px, py = pai.winfo_rootx(), pai.winfo_rooty()
    pw, ph = pai.winfo_width(), pai.winfo_height()
    janela.geometry(f"{w}x{h}+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")


def trazer_para_frente(janela, pai) -> None:
    """Centraliza sobre o pai, torna modal e garante que apareça NA FRENTE (problema comum no Windows)."""
    janela.transient(pai)
    centralizar(janela, pai)

    def _frente():
        try:
            centralizar(janela, pai)  # o CustomTkinter reposiciona a janela logo após criar
            janela.lift()
            janela.attributes("-topmost", True)
            janela.focus_force()
            janela.grab_set()
            janela.after(300, lambda: janela.attributes("-topmost", False))
        except tk.TclError:
            pass
    janela.after(60, _frente)
    janela.after(250, lambda: _recentralizar(janela, pai))


def _recentralizar(janela, pai) -> None:
    try:
        if janela.winfo_exists():
            centralizar(janela, pai)
    except tk.TclError:
        pass


def piscar_barra_de_tarefas(janela, vezes: int = 5) -> None:
    """Faz o ícone na barra de tarefas piscar (Windows), como os avisos do sistema."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND), ("dwFlags", wintypes.DWORD),
                        ("uCount", wintypes.UINT), ("dwTimeout", wintypes.DWORD)]
        hwnd = ctypes.windll.user32.GetParent(janela.winfo_id())
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x3 | 0xC, vezes, 0)  # ALL | TIMERNOFG
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass


def som_aviso(janela) -> None:
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(0x30)  # MB_ICONEXCLAMATION: o "plim" de aviso do Windows
            return
        except Exception:
            pass
    janela.bell()


def som_sucesso(janela) -> None:
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(0x40)  # MB_ICONASTERISK
            return
        except Exception:
            pass
    janela.bell()


class Dialogo(ctk.CTkToplevel):
    """Diálogo modal com botões de ação específicos (diretriz da Microsoft: nada de "Sim/Não" genérico).

    botoes: [(texto, valor, destaque_bool)] — o último é sempre a opção segura (cancelar/fechar).
    """

    def __init__(self, pai, titulo: str, mensagem: str, botoes, icone: str = "⚠️", som: bool = True):
        super().__init__(pai, fg_color="#0A0A0A")
        self.title(titulo)
        self.resizable(False, False)
        self.resultado = None
        self.botoes = botoes
        quadro = ctk.CTkFrame(self, fg_color="#0A0A0A", border_width=2, border_color="#4FD18B", corner_radius=0)
        quadro.pack(fill="both", expand=True)  # borda verde: o diálogo se destaca do fundo preto
        topo = ctk.CTkFrame(quadro, fg_color="transparent")
        topo.pack(fill="both", expand=True, padx=22, pady=(22, 8))
        ctk.CTkLabel(topo, text=icone, font=ctk.CTkFont(size=30)).pack(side="left", anchor="n", padx=(0, 14))
        ctk.CTkLabel(topo, text=mensagem, justify="left", wraplength=480, anchor="w",
                     font=ctk.CTkFont(size=14)).pack(side="left", fill="x")
        barra = ctk.CTkFrame(quadro, fg_color="transparent")
        barra.pack(fill="x", padx=22, pady=(4, 20))
        for texto, valor, destaque in reversed(botoes):
            estilo = {} if destaque else dict(fg_color="#141414", hover_color="#1F1F1F", text_color="#FFFFFF",
                                              border_width=1, border_color="#3A3A3A")
            b = ctk.CTkButton(barra, text=texto, width=150, height=34,
                              command=lambda v=valor: self._escolher(v), **estilo)
            b.pack(side="right", padx=(8, 0))
        self.protocol("WM_DELETE_WINDOW", lambda: self._escolher(botoes[-1][1]))
        self.bind("<Escape>", lambda _: self._escolher(botoes[-1][1]))
        try:
            from .marca import aplicar_icone
            aplicar_icone(self)
        except Exception:
            pass
        trazer_para_frente(self, pai)
        if som:
            self.after(80, lambda: som_aviso(self))

    def _escolher(self, valor):
        self.resultado = valor
        self.grab_release()
        self.destroy()

    def perguntar(self):
        self.wait_window()
        return self.resultado
