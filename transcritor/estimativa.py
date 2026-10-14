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


def ocr_restante_do_video(feitas: int, total: int, segundos_gastos: float, ocr_por_hora: float,
                          duracao: float) -> float:
    """Segundos que faltam de OCR no vídeo em andamento (achado N15).

    Com 5 capturas lidas ou mais, usa o ritmo medido nesta mesma rodada; antes disso, a estimativa por hora."""
    if total <= 0:
        return ocr_por_hora / 3600 * duracao
    if feitas >= 5 and segundos_gastos > 0:
        return max(0, total - feitas) * segundos_gastos / feitas
    return ocr_por_hora / 3600 * duracao * max(0, total - feitas) / total


def falta_da_rodada(video_restante: float, velocidade_lote: float, ocr_por_hora: float,
                    ocr_do_video_atual: float | None = None, video_depois: float = 0.0) -> float:
    """Segundos que faltam na rodada, contando fala E texto de tela.

    Na fala: o que falta de áudio de todos os vídeos ÷ velocidade + o OCR de todos eles (inclusive o atual
    inteiro). No OCR: o que falta do vídeo atual (`ocr_do_video_atual`) + fala e OCR dos próximos
    (`video_depois`, em segundos de vídeo). A fórmula antiga multiplicava só a fala restante, e no fim da
    fala isso dava zero: a previsão travava em "menos de 1 min" enquanto o OCR ainda rodava."""
    vel = velocidade_lote if velocidade_lote > 0 else 1.0
    if ocr_do_video_atual is None:  # ainda na fala
        return video_restante / vel + ocr_por_hora / 3600 * video_restante
    return ocr_do_video_atual + video_depois / vel + ocr_por_hora / 3600 * video_depois

