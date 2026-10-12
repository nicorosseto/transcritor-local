"""Teste de fumaça da janela (ver README.md nesta pasta). Modelo de transcrição simulado."""
import sys, time, tempfile, threading
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from conftest import criar_video
from transcritor.gui import app as A
from transcritor.pipeline import Evento
respostas = []
A.Dialogo.perguntar = lambda self: respostas.pop(0) if respostas else None
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
va, vb, saida = tmp/"a", tmp/"b", tmp/"saida"
criar_video(va/"x.mp4", [("a", 3)]); criar_video(vb/"y.mp4", [("b", 3)])
app = A.App()
def bombear(seg):
    fim = time.time()+seg
    while time.time() < fim:
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(va)); app._definir(app.ent_saida, str(saida))
app._ler_pasta(); bombear(3)
assert app.projeto and len(app.itens) == 1, "leitura"
# X3: muda a pasta -> invalida
app._definir(app.ent_videos, str(vb)); app._pastas_mudaram()
assert app.projeto is None and str(app.btn_iniciar.cget("state")) == "disabled", "invalidação"
# X7: saída de outra origem -> diálogo; resposta "mover" relê aceitando
respostas.append("mover"); app._ler_pasta(); bombear(3)
assert app.projeto and app.itens[0].rel == "y.mp4", "outra origem aceita"
# X13: na_interface roda na thread principal
quem = []
threading.Thread(target=lambda: app.na_interface(lambda: quem.append(threading.current_thread() is threading.main_thread()))).start()
bombear(0.5); assert quem == [True], quem
# X16: lote_fim fatal não vira sucesso
app._modo_rodando(True); app._palavras = 0
app.fila.put(Evento("lote_fim", {"ok": 0, "erro": 0, "fatal": "boom"})); bombear(0.5)
txt = app.lbl_status.cget("text"); assert txt.startswith("✕") and "boom" in txt, txt
assert str(app.ent_videos.cget("state")) == "normal"
app._modo_rodando(True); assert str(app.ent_videos.cget("state")) == "disabled"; app._modo_rodando(False)
app._fechar(); bombear(0.5)
print("SMOKE GUI OK")
