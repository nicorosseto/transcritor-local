"""Fumaça: botão único Transcrever N (sem cartões) e confirmação centralizada (v0.1.8, N12)."""
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
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
for nome in ("a", "b", "c"):
    criar_video(tmp/f"v/{nome}.mp4", [(nome, 4)])
app = A.App()
app.geometry("1200x760+50+30")
def bombear(seg, ate=None):
    fim = time.time()+seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(5, lambda: app.projeto)
assert not hasattr(app, "btns_qtd")
texto = app.btn_iniciar.cget("text"); print(repr(texto))
assert texto.startswith("Transcrever 3\n≈"), texto
app._clique_tabela  # marcado/desmarcado direto
app.marcados.discard("c.mp4"); app._atualizar_quantidades(); bombear(0.2)
assert app.btn_iniciar.cget("text").startswith("Transcrever 2\n"), app.btn_iniciar.cget("text")
assert app.btn_iniciar.cget("state") == "normal"
app.marcados.clear(); app._atualizar_quantidades()
assert app.btn_iniciar.cget("state") == "disabled"
# confirmação centralizada
app.update(); app.update_idletasks()
d = A.Dialogo(app, "Confirmar rodada", "Processar 2 vídeo(s)? Tempo estimado: ≈ 1 min.\n\n• a.mp4\n• b.mp4\n\nO PC fica mais lento.",
              [("Começar", "ok", True), ("Cancelar", None, False)], icone="▶️", som=False)
bombear(1.0)
cx = d.winfo_rootx() + d.winfo_width()/2; cy = d.winfo_rooty() + d.winfo_height()/2
px = app.winfo_rootx() + app.winfo_width()/2; py = app.winfo_rooty() + app.winfo_height()/2
print("desvio do centro:", round(cx-px), round(cy-py), "tam", d.winfo_width(), d.winfo_height())
assert abs(cx-px) <= 4 and abs(cy-py) <= 4
d.destroy()
app._fechar(); bombear(0.5)
print("ACAO GUI OK")
