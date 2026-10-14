"""Fumaça: a janela cabe na tela com a escala do Windows (N16).

Uso: xvfb-run -a -s "-screen 0 1920x1080x24" python3.12 ferramentas/fumaca/escala_do_windows.py 1.5
(escala 1.0, 1.25 ou 1.5; troque o tamanho da tela para simular outros monitores)."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import customtkinter as ctk
from conftest import criar_video
esc = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
ctk.set_widget_scaling(esc); ctk.set_window_scaling(esc)
from transcritor.gui import app as A
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/a.mp4", [("x", 4)])
app = A.App()
def bombear(s):
    f = time.time()+s
    while time.time() < f:
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s")); app._ler_pasta(); bombear(3)
tela_l, tela_a = app.winfo_screenwidth(), app.winfo_screenheight()
print(f"escala {esc}: tela {tela_l}x{tela_a}, janela {app.winfo_width()}x{app.winfo_height()}")
assert app.winfo_width() <= tela_l and app.winfo_height() <= tela_a - 100, "a janela não cabe na tela (barra de ação cortada)"
# a barra de ação (Transcrever) precisa estar dentro da janela
base_barra = app.btn_iniciar.winfo_rooty() + app.btn_iniciar.winfo_height()
assert base_barra <= tela_a - 40, f"botão Transcrever fora da tela: {base_barra} > {tela_a - 40}"
app._fechar(); bombear(0.3)
print("ESCALA GUI OK")
