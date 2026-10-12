"""Captura as telas do app em 1366x768 (ver ferramentas/fumaca/README.md). Modelo simulado."""
import sys, time, tempfile, subprocess
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline
from transcritor.gui import app as A
from transcritor.gui.componentes import Dialogo
SAIDA = Path(sys.argv[1])
class Lento(ModeloFalso):
    def transcribe(self, audio, **kw):
        segs, info = super().transcribe(audio, **kw)
        def devagar():
            for s in segs:
                time.sleep(1.2); yield s
        return devagar(), info
m = Lento()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
perguntas = []
A.Dialogo.perguntar = lambda self: (self.destroy(), "ok")[1]
tmp = Path(tempfile.mkdtemp()) / "Curso exemplo"
for rel, seg in [("Módulo 01/01 Abertura do curso.mp4", 8), ("Módulo 01/02 Conceitos básicos.mp4", 10),
                 ("Módulo 01/03 Primeiro exemplo.mp4", 6), ("Módulo 02/01 Ferramentas.mp4", 8),
                 ("Módulo 02/02 Exercício guiado.mp4", 6), ("Módulo 02/03 Revisão.mp4", 6),
                 ("Módulo 03/01 Estudo de caso.mp4", 6), ("Módulo 03/02 Encerramento.mp4", 6)]:
    criar_video(tmp / "videos" / rel, [("slide", seg)])
app = A.App()
app.geometry("1366x740+0+0")
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
def foto(nome):
    bombear(0.6)
    subprocess.run(["import", "-window", "root", str(SAIDA / f"{nome}.png")], check=True)
bombear(4, lambda: app.situacao is not None)
app._mostrar_pagina("videos"); foto("1_inicio")
app._definir(app.ent_videos, str(tmp / "videos")); app._definir(app.ent_saida, str(tmp / "transcricoes"))
app._ler_pasta(); bombear(10, lambda: app.projeto)
app._escolher_qtd("3")
app.tabela.selection_set(app.itens[3].rel)
foto("2_videos")
app._mostrar_pagina("preparacao"); foto("3_preparacao")
app._mostrar_pagina("videos")
app._iniciar(); bombear(9)
foto("4_rodando")
bombear(120, lambda: not app.rodando)
foto("5_fim")
app._mostrar_pagina("resultados"); foto("6_resultados")
app._mostrar_pagina("videos")
d = Dialogo(app, "Confirmar rodada", "Processar 3 vídeo(s)? Tempo estimado: ≈ 4 min.\n\nO PC fica mais lento "
            "enquanto isso, e o app impede que ele entre em suspensão.", [("Começar", "ok", True),
            ("Cancelar", None, False)], icone="▶️", som=False)
foto("7_dialogo"); d.destroy()
app._fechar(); bombear(0.5)
print("ok")
