"""Fumaça: cancelar no meio da rodada deixa a tabela coerente (achado N10). Modelo simulado e lento."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline
from transcritor.gui import app as A


class ModeloLento(ModeloFalso):
    def transcribe(self, audio, **kw):
        seg, info = super().transcribe(audio, **kw)
        def devagar():
            for s in seg:
                time.sleep(0.4)
                yield s
        return devagar(), info


m = ModeloLento()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
A.Dialogo.perguntar = lambda self: "ok"
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/a.mp4", [("a", 30)]); criar_video(tmp/"v/b.mp4", [("b", 30)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time()+seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(5, lambda: app.projeto)
app._escolher_qtd("todos")
app._iniciar()
bombear(30, lambda: app.tabela.set("a.mp4", "status") == A.ROTULO_PROCESSANDO)
bombear(1.5)
app.cancelar.set()
bombear(30, lambda: not app.rodando)
estados = {rel: app.tabela.set(rel, "status") for rel in ("a.mp4", "b.mp4")}
print(estados)
assert estados == {"a.mp4": A.STATUS_ROTULO["pendente"], "b.mp4": A.STATUS_ROTULO["pendente"]}, estados
app._fechar(); bombear(0.5)
print("CANCELAR GUI OK")
