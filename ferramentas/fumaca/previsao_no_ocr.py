"""Fumaça: durante o texto de tela, o % e o término previsto da rodada continuam andando (N15)."""
import sys, time, tempfile
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video
from transcritor.pipeline import Evento
from transcritor.gui import app as A
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/a.mp4", [("a", 4)])
app = A.App()
def bombear(seg):
    fim = time.time()+seg
    while time.time() < fim:
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(3)
# estado de uma rodada em andamento, no começo do OCR
app.rodando = True; app._com_ocr = True
app._dur_rodada, app._dur_feita, app._dur_atual, app._frac, app._indice, app._total_rodada = 2200.0, 0.0, 2200.0, 0.0, 1, 1
app.pb.set(0.83)
textos = []
for feito in (10, 200, 400, 540):
    d = {"feito": feito, "total": 548, "falta_lote": 360 - feito * 0.6,
         "termino": datetime.now() + timedelta(seconds=360 - feito * 0.6)}
    app._tratar(Evento("progresso_telas", d)); bombear(0.1)
    textos.append(app.lbl_tempo.cget("text")); print(textos[-1])
pcts = [int(t.split("Rodada ")[1].split("%")[0]) for t in textos]
assert pcts == sorted(pcts) and pcts[-1] > pcts[0] > 83 - 1, pcts
assert all("término ~" in t for t in textos)
app.rodando = False
app._fechar(); bombear(0.3)
print("PREVISAO GUI OK")
