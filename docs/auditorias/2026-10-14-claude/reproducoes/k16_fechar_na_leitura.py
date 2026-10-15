"""K16: fechar a janela durante a LEITURA não espera a thread (só a da rodada). A trava fica no disco com o
PID do processo que morreu; se esse PID for reaproveitado por outro programa, a pasta fica "em uso" até
alguém apagar .em_uso.lock à mão.

Rodar na raiz do repositório:
  xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k16_fechar_na_leitura.py
"""
import subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")

if len(sys.argv) > 1:  # processo filho: abre a janela, lê e fecha no meio da leitura (como main())
    from conftest import criar_video
    from transcritor import midia
    from transcritor.gui import app as A
    A.App._verificacao_inicial = lambda self: None
    tmp = Path(sys.argv[1])
    for n in "abc":
        criar_video(tmp / f"v/{n}.mp4", [(n, 2)])
    real = midia.duracao
    midia.duracao = lambda p: (time.sleep(1.0), real(p))[1]
    app = A.App()
    app._definir(app.ent_videos, str(tmp / "v")); app._definir(app.ent_saida, str(tmp / "s"))
    app._ler_pasta()
    def fechar():
        print("lendo:", app._lendo, "| trava no disco:", (tmp / "s/.em_uso.lock").exists(), flush=True)
        app._fechar()  # o usuário clica no X durante a leitura
    app.after(800, fechar)
    app.mainloop()
    sys.exit(0)

from transcritor.config import Config
from transcritor.pipeline import Projeto
tmp = Path(tempfile.mkdtemp())
subprocess.run([sys.executable, __file__, str(tmp)], check=True)
trava = tmp / "s/.em_uso.lock"
print("depois que o app saiu: trava =", repr(trava.read_text()) if trava.exists() else None)
vivo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # outro programa com o PID
trava.write_text(f"{vivo.pid} 0000")
try:
    Projeto(Config(tmp / "v", tmp / "s")).escanear()
    print("leu normalmente")
except Exception as e:
    print(f"trava com PID {vivo.pid} vivo (outro programa) -> {type(e).__name__}")
vivo.kill()
