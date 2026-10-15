"""Controle (área 4, não é achado): trocar a pasta de saída pelo botão Escolher durante a leitura termina com a
leitura da saída nova (o N19 funciona).

Rodar na raiz do repositório:
  xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-14-claude/reproducoes/controle_saida_trocada_na_leitura.py
"""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video
from transcritor import midia
from transcritor.gui import app as A
A.App._verificacao_inicial = lambda self: None
tmp = Path(tempfile.mkdtemp())
for n in "abc":
    criar_video(tmp / f"v/{n}.mp4", [(n, 2)])
real = midia.duracao
midia.duracao = lambda p: (time.sleep(0.7), real(p))[1]
app = A.App()
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp / "v")); app._definir(app.ent_saida, str(tmp / "saidaA"))
app._ler_pasta(); bombear(0.5)
A.filedialog.askdirectory = lambda **k: str(tmp / "saidaB")
app._escolher_saida()          # usuário troca a saída no meio da leitura
print("logo após trocar: projeto =", app.projeto, "| _lendo =", app._lendo)
bombear(15, lambda: app.projeto is not None and not app._lendo)
print("final: projeto.saida =", app.projeto.cfg.pasta_saida.name, "| campo =", Path(app.ent_saida.get()).name,
      "| itens:", len(app.itens))
print("saidaA criada e gravada mesmo assim:", sorted(p.name for p in (tmp / "saidaA").iterdir()))
app.destroy()
