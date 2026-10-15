"""K13 e K14 (área 1): o que sobra em disco quando algo dá errado, e (controle) quanto o cancelamento demora
nas capturas. A parte (a') usa um nome de arquivo que não é UTF-8 válido: só dá para criar no Linux.

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k13_k14_sobras.py
"""
import os, subprocess, sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video
from transcritor import midia, ocr
from transcritor.config import Config
from transcritor.pipeline import Projeto
from transcritor.util import Cancelado, gravar_atomico

tmp = Path(tempfile.mkdtemp())

# (a) gravar_atomico só limpa o temporário em OSError
def escreve_e_falha(p):
    p.write_text("metade"); raise ValueError("erro que não é de disco")
try:
    gravar_atomico(tmp / "x.csv", escreve_e_falha)
except ValueError:
    pass
print("(a) sobras após erro não-OSError:", sorted(p.name for p in tmp.glob("x.csv.*")))

# (a') caso concreto: nome de arquivo que não é UTF-8 válido (Linux) derruba o registro.csv na leitura
v = tmp / "v"; v.mkdir()
criar_video(v / "ok.mp4", [("a", 2)])
os.rename(v / "ok.mp4", os.fsdecode(bytes(v) + b"/aula_\xe9.mp4"))  # 'é' em latin-1
s = tmp / "s"
try:
    Projeto(Config(v, s)).escanear()
    print("(a') leitura ok")
except Exception as e:
    print("(a') leitura falhou:", type(e).__name__, "| sobras:", sorted(p.name for p in s.glob("registro.csv.*")),
          "| trava:", (s / ".em_uso.lock").exists())

# (b) download do português interrompido deixa o .parcial
os.environ["XDG_DATA_HOME"] = str(tmp / "xdg")
class Resp:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): raise TimeoutError("rede caiu")
ocr.urllib.request.urlopen = lambda *a, **k: Resp()
try:
    ocr.baixar_portugues()
except Exception as e:
    print("(b) baixar_portugues falhou:", e, "| sobras:", sorted(p.name for p in (tmp / "xdg/TranscritorLocal/tessdata").iterdir()))

# (c) cancelar durante as capturas: latência e quadros que sobram
video = tmp / "estatico.mp4"
subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:s=1920x1080:r=2:d=1800",
                "-c:v", "libx264", "-preset", "ultrafast", "-g", "4", str(video)], check=True)
t0 = time.perf_counter(); midia.extrair_capturas(video, tmp / "cap0")
print(f"(c) capturas de 30 min de tela parada, sem cancelar: {time.perf_counter() - t0:.1f} s")
cancelar = threading.Event()
threading.Timer(0.5, cancelar.set).start()
t0 = time.perf_counter()
try:
    midia.extrair_capturas(video, tmp / "cap1", cancelar=cancelar)
except Cancelado:
    pass
print(f"(c) cancelado aos 0,5 s; extrair_capturas só devolveu aos {time.perf_counter() - t0:.1f} s")
criar_video(tmp / "slides.mp4", [(f"slide {i}", 5) for i in range(40)])
cancelar = threading.Event(); threading.Timer(1.0, cancelar.set).start()
try:
    midia.extrair_capturas(tmp / "slides.mp4", tmp / "cap2", cancelar=cancelar)
except Cancelado:
    pass
print("(c) sobras após cancelar no meio:", len(list((tmp / "cap2").glob("tmp_*.jpg"))), "tmp_*.jpg")
