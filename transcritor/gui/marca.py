"""Logotipo "da onda à linha" desenhado em código (sem SVG para empacotar).

Duas barras verdes (a onda sonora) viram uma linha que clareia até o branco (o texto), seguida de
duas linhas de texto. Geometria na grade 64x64 aprovada em 11/10/2026.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

VERDE = (0x4F, 0xD1, 0x8B)
BRANCO = (0xFF, 0xFF, 0xFF)
FUNDO = (0x0A, 0x16, 0x12)
BORDA = (0x1D, 0x3A, 0x2E)
TRACO = 4.6


def _mistura(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def desenhar(tamanho: int = 64, fundo: bool = True) -> Image.Image:
    """Retorna o símbolo em RGBA, já suavizado (desenha 4x maior e reduz)."""
    k = 4 * tamanho / 64
    img = Image.new("RGBA", (round(64 * k), round(64 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if fundo:
        d.rounded_rectangle((0.75 * k, 0.75 * k, 63.25 * k, 63.25 * k), radius=15 * k,
                            fill=FUNDO + (255,), outline=BORDA + (255,), width=max(1, round(1.5 * k)))
    r = TRACO / 2 * k

    def ponto(x, y, cor, alfa=255):
        d.ellipse((x * k - r, y * k - r, x * k + r, y * k + r), fill=cor + (alfa,))

    def reta(x1, y1, x2, y2, cor, alfa=255, cor_fim=None, x_ini=None, x_fim=None):
        passos = max(2, int(max(abs(x2 - x1), abs(y2 - y1)) * 8))
        for i in range(passos + 1):
            t = i / passos
            x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            c = cor if cor_fim is None else _mistura(cor, cor_fim, (x - x_ini) / (x_fim - x_ini))
            ponto(x, y, c, alfa)

    reta(13, 27, 13, 37, VERDE)
    reta(21, 18, 21, 46, VERDE)
    # M29 41 V36 Q29 32 33 32 H47, com degradê verde -> branco no eixo x (29 a 47)
    grad = dict(cor_fim=BRANCO, x_ini=29, x_fim=47)
    reta(29, 41, 29, 36, VERDE, **grad)
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * 29 + 2 * (1 - t) * t * 29 + t ** 2 * 33
        y = (1 - t) ** 2 * 36 + 2 * (1 - t) * t * 32 + t ** 2 * 32
        ponto(x, y, _mistura(VERDE, BRANCO, (x - 29) / 18))
    reta(33, 32, 47, 32, VERDE, **grad)
    reta(37, 21, 51, 21, BRANCO)
    reta(37, 43, 49, 43, BRANCO, alfa=230)
    return img.resize((tamanho, tamanho), Image.Resampling.LANCZOS)


def salvar_ico(destino) -> None:
    """Ícone do .exe com os tamanhos que o Windows usa."""
    tamanhos = [16, 24, 32, 48, 64, 128, 256]
    desenhar(256).save(destino, format="ICO", sizes=[(s, s) for s in tamanhos])


def aplicar_icone(janela) -> None:
    """Ícone da janela (barra de título e barra de tarefas). No Windows, o CustomTkinter troca o
    ícone pelo dele ~200 ms depois de criar a janela, a menos que iconbitmap seja chamado."""
    try:
        if sys.platform == "win32":
            ico = Path(tempfile.gettempdir()) / "transcritor_local_icone.ico"
            if not ico.is_file():
                salvar_ico(ico)
            janela.after(250, lambda: janela.iconbitmap(str(ico)))
            janela.iconbitmap(str(ico))
        else:
            from PIL import ImageTk
            janela._icone_tk = ImageTk.PhotoImage(desenhar(64))
            janela.iconphoto(True, janela._icone_tk)
    except Exception:
        pass  # ícone é cosmético: nunca pode impedir o app de abrir
