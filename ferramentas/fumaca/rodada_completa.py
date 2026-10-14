"""Teste de fumaça da janela (ver README.md nesta pasta). Modelo de transcrição simulado."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline
from transcritor.gui import app as A
m = ModeloFalso()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
A.Dialogo.perguntar = lambda self: "ok"
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/Mod/a.mp4", [("a", 4)]); criar_video(tmp/"v/Mod/a.mkv", [("b", 6)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time()+seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(5, lambda: app.projeto)
app._iniciar(); bombear(60, lambda: not app.rodando)
print(app.lbl_status.cget("text"))
print(sorted(p.name for p in (tmp/"s/transcricoes_md/Mod").iterdir()))
assert app.lbl_status.cget("text").startswith("✓")
app._fechar(); bombear(0.5)
print("RODADA GUI OK")
