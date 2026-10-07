"""Estimativas de tempo. Começam conservadoras e passam a usar o que foi medido no PC."""

from __future__ import annotations

from dataclasses import dataclass

from .config import PRESETS
from .registro import Registro

OCR_SEG_POR_HORA_PADRAO = 600.0   # 10 min de OCR por hora de vídeo (conservador)
FATOR_GPU = 5.0


@dataclass
class Estimativa:
    segundos_transcricao: float
    segundos_ocr: float
    velocidade: float
    medida: bool          # True = baseada em execuções reais neste PC

    @property
    def total(self) -> float:
        return self.segundos_transcricao + self.segundos_ocr


def velocidade(registro: Registro, preset: str, dispositivo: str) -> tuple[float, bool]:
    medida = registro.velocidade_medida(preset)
    if medida:
        return medida, True
    base = PRESETS[preset]["velocidade_padrao_cpu"]
    return (base * FATOR_GPU if dispositivo == "cuda" else base), False


def estimar(duracoes_s: list[float], registro: Registro, preset: str, dispositivo: str,
            com_ocr: bool) -> Estimativa:
    vel, medida = velocidade(registro, preset, dispositivo)
    total_video = sum(duracoes_s)
    seg_ocr = 0.0
    if com_ocr:
        por_hora = registro.ocr_por_hora_medido() or OCR_SEG_POR_HORA_PADRAO
        seg_ocr = total_video / 3600 * por_hora
    return Estimativa(total_video / vel if vel > 0 else 0.0, seg_ocr, vel, medida)
