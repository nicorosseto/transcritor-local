"""K15: processo encerrado à força no meio da extração do áudio (Gerenciador de Tarefas, queda de energia,
janela fechada depois de 10 s): o temporário de nome único fica para sempre e o FFmpeg filho continua.

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k15_morte_no_meio.py
"""
import os, signal, subprocess, sys, time, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
video = tmp / "longo.mp4"
subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=1280x720:r=30:d=600",
                "-f", "lavfi", "-i", "sine=frequency=300:duration=600", "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-shortest", str(video)], check=True)
filho = subprocess.Popen([sys.executable, "-c", f"""
import sys; sys.path.insert(0, '.')
from pathlib import Path
from transcritor import midia
midia.extrair_audio(Path(r'{video}'), Path(r'{tmp}/saida/audio_mp3/aula.mp3'))
"""])
pasta = tmp / "saida/audio_mp3"
for _ in range(100):
    if pasta.exists() and any(pasta.iterdir()):
        break
    time.sleep(0.05)
time.sleep(0.3)
os.kill(filho.pid, signal.SIGKILL); filho.wait()
time.sleep(1.5)  # o ffmpeg filho continua sozinho
print("após matar o app:", [(p.name, p.stat().st_size) for p in pasta.iterdir()])
