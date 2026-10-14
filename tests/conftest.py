"""Fixtures: vídeos sintéticos (FFmpeg + Pillow) e um modelo Whisper falso, sem download."""

from __future__ import annotations

import shutil
import subprocess
import time
import types
from pathlib import Path

import pytest

TEM_FFMPEG = shutil.which("ffmpeg") is not None
requer_ffmpeg = pytest.mark.skipif(not TEM_FFMPEG, reason="ffmpeg não instalado")


def _frame(texto: str, destino: Path, cor=(255, 255, 255)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (640, 360), cor)
    d = ImageDraw.Draw(img)
    fonte = ImageFont.load_default(size=36)
    for i, linha in enumerate(texto.split("\n")):
        d.text((30, 40 + i * 50), linha, fill=(0, 0, 0), font=fonte)
    img.save(destino)


def criar_video(destino: Path, telas: list[tuple[str, float]], cores=None) -> Path:
    """Cria um vídeo com uma sequência de 'slides' (texto, segundos) e áudio senoidal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.parent / f".tmp_{destino.stem}"
    tmp.mkdir(exist_ok=True)
    lista = []
    for i, (texto, seg) in enumerate(telas):
        png = tmp / f"f{i}.png"
        cor = (cores[i] if cores else (255, 255, 255))
        _frame(texto, png, cor)
        lista.append(f"file '{png.as_posix()}'\nduration {seg}")
    lista.append(f"file '{(tmp / f'f{len(telas) - 1}.png').as_posix()}'")
    (tmp / "lista.txt").write_text("\n".join(lista), encoding="utf-8")  # ffmpeg lê a lista em UTF-8
    total = sum(s for _, s in telas)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(tmp / "lista.txt"), "-f", "lavfi", "-i", f"sine=frequency=300:duration={total}",
                    "-vf", "fps=10,format=yuv420p", "-g", "10", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", str(destino)], check=True)
    shutil.rmtree(tmp)
    return destino


class _Seg:
    def __init__(self, a, b, t):
        self.start, self.end, self.text = a, b, t


class ModeloFalso:
    """Imita WhisperModel.transcribe: um segmento a cada 2 s com texto previsível."""
    def __init__(self):
        self.chamadas = []

    def transcribe(self, audio, **kw):
        self.chamadas.append(kw)
        dur = len(audio) / 16000
        def gerar():
            for i in range(int(dur // 2)):
                time.sleep(0.02)  # simula trabalho (o relógio do Windows tem ~15 ms de resolução)
                yield _Seg(i * 2.0, min((i + 1) * 2.0, dur), f" frase {i}")
        return gerar(), types.SimpleNamespace(duration=dur)


@pytest.fixture
def modelo_falso(monkeypatch):
    from transcritor import pipeline
    m = ModeloFalso()
    monkeypatch.setattr(pipeline, "carregar_modelo", lambda *a, **k: (m, "cpu"))
    monkeypatch.setattr(pipeline, "modelo_baixado", lambda nome: True)
    return m


@pytest.fixture
def projeto_dir(tmp_path):
    return tmp_path / "videos", tmp_path / "saida"
