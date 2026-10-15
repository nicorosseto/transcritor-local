"""Tudo que envolve o FFmpeg: duração, extração de áudio, decodificação e capturas de tela."""

from __future__ import annotations

import re
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

from .util import Cancelado, hhmmss, localizar_binario, nome_temporario, popen, rodar


class FFmpegAusente(RuntimeError):
    pass


MENSAGEM_SEM_FFMPEG = ("FFmpeg não encontrado. Baixe na página Preparação do PC (botão \"Baixar FFmpeg\")."
                       if sys.platform == "win32" else
                       "FFmpeg não encontrado. Instale pelo gerenciador de pacotes (ex.: sudo apt install ffmpeg).")


def ffmpeg() -> str:
    exe = localizar_binario("ffmpeg")
    if not exe:
        raise FFmpegAusente(MENSAGEM_SEM_FFMPEG)
    return exe


def ffprobe() -> str:
    exe = localizar_binario("ffprobe")
    if not exe:
        raise FFmpegAusente(MENSAGEM_SEM_FFMPEG)
    return exe


def duracao(arquivo: Path) -> float:
    """Duração em segundos (0.0 se não conseguir ler — arquivo corrompido, por exemplo)."""
    try:
        r = rodar([ffprobe(), "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo)],
                  capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (ValueError, OSError, FFmpegAusente):
        return 0.0
    except Exception:  # timeout e afins
        return 0.0


def extrair_audio(video: Path, destino: Path, cancelar=None) -> None:
    """Mono, 16 kHz, MP3 48 kbps: 1 h de vídeo vira ~20 MB. Reaproveita se já existir.

    Obedece ao cancelamento (achado X13): o FFmpeg é encerrado e nada fica pela metade."""
    if destino.exists() and destino.stat().st_size > 0:
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = nome_temporario(destino, ".parcial.mp3")  # nome único (achado N20)
    proc = popen([ffmpeg(), "-y", "-nostdin", "-loglevel", "error", "-i", str(video),
                  "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(tmp)],
                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                 encoding="utf-8", errors="replace")
    erros: list[str] = []
    leitor = threading.Thread(target=lambda: erros.extend(proc.stderr), daemon=True)
    leitor.start()
    while proc.poll() is None:
        if cancelar is not None and cancelar.is_set():
            proc.kill()
            proc.wait()
            leitor.join(2)
            tmp.unlink(missing_ok=True)
            raise Cancelado()
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    leitor.join(2)
    if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        msg = "".join(erros).strip().splitlines()
        raise RuntimeError("Falha ao extrair o áudio" + (f": {msg[-1]}" if msg else
                           " (o vídeo pode não ter trilha de áudio)."))
    try:
        tmp.replace(destino)  # só "vale" quando terminou: um corte no meio não deixa MP3 quebrado
    finally:
        tmp.unlink(missing_ok=True)  # se a troca falhar, o .parcial não fica para trás (achado C4)


def carregar_audio(audio: Path):
    """Decodifica com o próprio FFmpeg e devolve numpy float32 a 16 kHz.

    Evita o PyAV: versões novas (15+) quebram o faster-whisper 1.2.x
    ("unexpected keyword argument 'metadata_errors'").
    """
    import numpy as np
    r = rodar([ffmpeg(), "-nostdin", "-loglevel", "error", "-i", str(audio),
               "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
              capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


# ----------------------------------------------------------------------------- capturas

_PTS = re.compile(r"pts_time:\s*([0-9.]+)")


def _dhash(caminho: Path, tamanho: int = 16) -> int:
    from PIL import Image
    with Image.open(caminho) as img:
        g = img.convert("L").resize((tamanho + 1, tamanho), Image.Resampling.LANCZOS)
        px = g.tobytes()
    bits = 0
    for lin in range(tamanho):
        for col in range(tamanho):
            esq = px[lin * (tamanho + 1) + col]
            dir_ = px[lin * (tamanho + 1) + col + 1]
            bits = (bits << 1) | (1 if esq > dir_ else 0)
    return bits


def _distancia(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def extrair_capturas(video: Path, pasta: Path, intervalo_min: float = 4.0,
                     diferenca_min: int = 8, cancelar=None) -> list[tuple[float, Path]]:
    """Salva uma imagem sempre que a tela muda de verdade.

    1. Lê só os quadros-chave (-skip_frame nokey): muito mais rápido que decodificar tudo.
    2. mpdecimate descarta quadros quase iguais já no FFmpeg.
    3. Filtro próprio: no mínimo `intervalo_min` s entre capturas e diferença visual
       (dHash 16x16 = 256 bits; `diferenca_min` bits diferentes, ~3%).
    Retorna [(segundo, caminho_da_imagem), ...] em ordem.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.jpg"):
        antigo.unlink()
    padrao = pasta / "tmp_%06d.jpg"
    proc = popen([ffmpeg(), "-nostdin", "-hide_banner", "-skip_frame", "nokey",
                  "-i", str(video), "-an",
                  "-vf", "mpdecimate,scale='min(1280,iw)':-2,showinfo",
                  "-fps_mode", "passthrough", "-q:v", "4", str(padrao)],
                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                 text=True, encoding="utf-8", errors="replace")
    tempos: list[float] = []
    ultimas: deque[str] = deque(maxlen=5)
    assert proc.stderr is not None
    cancelado = False
    for linha in proc.stderr:
        if cancelar is not None and cancelar.is_set():
            proc.kill()
            cancelado = True
            break
        if "showinfo" in linha:
            m = _PTS.search(linha)
            if m:
                tempos.append(float(m.group(1)))
        elif linha.strip():
            ultimas.append(linha.strip())
    proc.wait()
    if cancelado:
        raise Cancelado()
    if proc.returncode != 0:  # erro técnico não pode virar "nenhuma troca de tela" (achado X10)
        for lixo in pasta.glob("tmp_*.jpg"):
            lixo.unlink(missing_ok=True)
        raise RuntimeError("Falha ao procurar trocas de tela" + (f": {ultimas[-1]}" if ultimas else ""))

    brutos = sorted(pasta.glob("tmp_*.jpg"))
    mantidos: list[tuple[float, Path]] = []
    ultimo_hash, ultimo_t = None, -1e9
    for t, img in zip(tempos, brutos):
        try:
            h = _dhash(img)
        except Exception:
            img.unlink(missing_ok=True)
            continue
        if (t - ultimo_t) < intervalo_min or (
                ultimo_hash is not None and _distancia(h, ultimo_hash) < diferenca_min):
            img.unlink(missing_ok=True)
            continue
        final = pasta / f"cap_{hhmmss(t).replace(':', '')}.jpg"
        n = 1
        while final.exists():
            final = pasta / f"cap_{hhmmss(t).replace(':', '')}_{n}.jpg"
            n += 1
        img.replace(final)
        mantidos.append((t, final))
        ultimo_hash, ultimo_t = h, t
    for sobra in pasta.glob("tmp_*.jpg"):  # quadros sem pts correspondente
        sobra.unlink(missing_ok=True)
    return mantidos
