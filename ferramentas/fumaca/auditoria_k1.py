"""Fumaça: K1 (auditoria de 14/10). Uma releitura da pasta não pode trocar o projeto por baixo de uma rodada.

1. Durante a leitura, o botão Transcrever fica travado e _iniciar não faz nada.
2. Se a pasta for relida com a confirmação aberta, a rodada não começa e o usuário é avisado.
3. Depois disso, uma rodada normal registra os vídeos como concluídos no registro.csv.

Uso: xvfb-run -a -s "-screen 0 1366x768x24" python3.12 ferramentas/fumaca/auditoria_k1.py"""
import csv, sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline, midia
from transcritor.gui import app as A
m = ModeloFalso()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/a.mp4", [("a", 4)]); criar_video(tmp/"v/b.mp4", [("b", 4)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(10, lambda: app.projeto)

# 1. releitura lenta: botão travado
criar_video(tmp/"v/c.mp4", [("c", 4)])
dur_real = midia.duracao
midia.duracao = lambda p: (time.sleep(0.8), dur_real(p))[1]
app._ler_pasta(); bombear(0.2)
assert app._lendo and app.btn_iniciar.cget("state") == "disabled", app.btn_iniciar.cget("state")
antes = app.projeto
app._iniciar(); bombear(0.2)
assert not app.rodando, "rodada começou durante a leitura"
bombear(15, lambda: not app._lendo)
assert app.btn_iniciar.cget("state") == "normal"
print("K1.1 OK: Transcrever travado durante a leitura")

# 2. releitura com a confirmação aberta
vistos = []
def durante_confirmacao():
    for w in app.winfo_children():
        if isinstance(w, A.Dialogo) and w.title() == "Confirmar rodada":
            app._ler_pasta()                     # algo relê a pasta com o diálogo aberto
            app.after(150, lambda: esperar_e_clicar(w))
            return
    app.after(100, durante_confirmacao)
def esperar_e_clicar(w):
    if app._lendo:
        app.after(100, lambda: esperar_e_clicar(w)); return
    w._escolher("ok")
def fechar_avisos():
    for w in app.winfo_children():
        if isinstance(w, A.Dialogo) and w.title() != "Confirmar rodada":
            vistos.append(w.title()); w._escolher(w.botoes[-1][1])
    app.after(200, fechar_avisos)
app.after(100, durante_confirmacao); app.after(200, fechar_avisos)
app._iniciar(); bombear(1)
assert "A lista mudou" in vistos, vistos
assert not app.rodando
print("K1.2 OK: releitura durante a confirmação cancela a rodada com aviso")

# 3. rodada normal registra tudo
midia.duracao = dur_real
def clicar():
    for w in app.winfo_children():
        if isinstance(w, A.Dialogo) and w.title() == "Confirmar rodada":
            w._escolher("ok"); return
    app.after(100, clicar)
app.after(100, clicar)
app._iniciar(); bombear(60, lambda: not app.rodando and app._feitos >= 3)
bombear(1)
with open(tmp/"s/registro.csv", encoding="utf-8-sig") as f:
    st = {r["caminho"]: r["status"] for r in csv.DictReader(f, delimiter=";")}
assert set(st.values()) == {"ok"}, st
print("K1.3 OK: registro.csv", st)
app._fechar(); bombear(0.3)
print("AUDITORIA K1 GUI OK")
