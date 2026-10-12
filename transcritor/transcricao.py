"""Transcrição com faster-whisper (Whisper rodando via CTranslate2)."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass

from .config import threads_padrao

# Silencia avisos inofensivos do Hugging Face no Windows (symlinks / token)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")


class Cancelado(Exception):
    """Usuário pediu para cancelar no meio de um vídeo."""


@dataclass
class Paragrafo:
    inicio: float
    texto: str


def dispositivo_disponivel(preferencia: str = "auto") -> str:
    if preferencia == "cpu":
        return "cpu"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def carregar_modelo(modelo: str, dispositivo: str = "auto", threads: int = 0):
    """Carrega o modelo (baixa ~0,5 a 1,6 GB na primeira vez). GPU que falha cai para CPU."""
    from faster_whisper import WhisperModel
    alvo = dispositivo_disponivel(dispositivo)
    if alvo == "cuda":
        try:
            return WhisperModel(modelo, device="cuda", compute_type="float16"), "cuda"
        except Exception:
            pass
    return (WhisperModel(modelo, device="cpu", compute_type="int8",
                         cpu_threads=threads or threads_padrao()), "cpu")


def transcrever(modelo, audio, *, idioma: str | None, beam_size: int, vocabulario: list[str],
                segundos_por_paragrafo: int, ao_progredir=None, cancelar=None):
    """Retorna (paragrafos, duracao_s). `ao_progredir(pos_s, total_s)` é chamado a cada trecho."""
    segmentos, info = modelo.transcribe(
        audio,
        language=idioma or None,
        beam_size=beam_size,
        vad_filter=True,                         # silêncio não chega ao modelo
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 400},
        condition_on_previous_text=False,        # evita loops de frase repetida
        hotwords=", ".join(vocabulario) if vocabulario else None,
    )
    paragrafos: list[Paragrafo] = []
    inicio, buffer = None, []
    for seg in segmentos:
        if cancelar is not None and cancelar.is_set():
            raise Cancelado()
        texto = seg.text.strip()
        if not texto:
            continue
        if inicio is None:
            inicio = seg.start
        buffer.append(texto)
        if seg.end - inicio >= segundos_por_paragrafo:
            paragrafos.append(Paragrafo(inicio, " ".join(buffer)))
            inicio, buffer = None, []
        if ao_progredir:
            ao_progredir(seg.end, info.duration)
    if buffer:
        paragrafos.append(Paragrafo(inicio or 0.0, " ".join(buffer)))
    if ao_progredir:
        ao_progredir(info.duration, info.duration)
    return paragrafos, info.duration
