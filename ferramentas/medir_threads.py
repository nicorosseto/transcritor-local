"""Mede a velocidade da transcrição com diferentes números de threads (pendência P17).

Uso (no PowerShell, na pasta do repositório ou do script antigo):
    python ferramentas/medir_threads.py "C:\\caminho\\do\\video_ou_audio.mp4"

O que faz:
  1. Recorta os primeiros 3 minutos do arquivo (com o FFmpeg).
  2. Transcreve esse trecho com 4, 6 e 12 threads (ou outros valores via --threads).
  3. Mostra a velocidade de cada um. Não grava nada fora de uma pasta temporária.

Dica: feche outros programas e não use o PC durante a medição (leva ~10 a 15 min).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Compara a velocidade do Whisper com diferentes threads.")
    p.add_argument("arquivo", type=Path, help="vídeo ou áudio de referência")
    p.add_argument("--threads", default="4,6,12", help="lista separada por vírgula (padrão: 4,6,12)")
    p.add_argument("--minutos", type=float, default=3.0, help="trecho a medir (padrão: 3)")
    p.add_argument("--modelo", default="large-v3-turbo")
    p.add_argument("--beam", type=int, default=1, help="1 = Equilibrado, 5 = Preciso")
    a = p.parse_args()

    if not a.arquivo.is_file():
        sys.exit(f"Arquivo não encontrado: {a.arquivo}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("FFmpeg não encontrado no PATH.")

    import numpy as np
    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as tmp:
        trecho = Path(tmp) / "trecho.wav"
        subprocess.run([ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-t", str(a.minutos * 60),
                        "-i", str(a.arquivo), "-vn", "-ac", "1", "-ar", "16000", str(trecho)], check=True)
        bruto = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(trecho),
                                "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                               capture_output=True, check=True).stdout
        audio = np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768.0
        dur = len(audio) / 16000

        print(f"CPU: {os.cpu_count()} threads lógicas | trecho: {dur / 60:.1f} min | "
              f"modelo {a.modelo}, beam {a.beam}\n")
        resultados = []
        for n in [int(x) for x in a.threads.split(",") if x.strip()]:
            modelo = WhisperModel(a.modelo, device="cpu", compute_type="int8", cpu_threads=n)
            modelo.transcribe(audio[:16000 * 5], language="pt", beam_size=a.beam)  # aquecimento
            t0 = time.perf_counter()
            segs, _ = modelo.transcribe(audio, language="pt", beam_size=a.beam, vad_filter=True,
                                        condition_on_previous_text=False)
            for _ in segs:
                pass
            gasto = time.perf_counter() - t0
            vel = dur / gasto
            resultados.append((n, gasto, vel))
            print(f"  {n:>2} threads: {gasto:6.1f} s  ->  velocidade {vel:.2f}x")
            del modelo

    melhor = max(resultados, key=lambda r: r[2])
    print(f"\nMelhor: {melhor[0]} threads ({melhor[2]:.2f}x). Copie estas linhas e mande para o Claude.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
