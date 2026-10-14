"""Montagem do .md final: cabeçalho, fala com timestamps e blocos "Na tela"."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .transcricao import Paragrafo
from .util import gravar_texto_atomico, hhmmss


COMO_LER = [
    "> **Como ler este arquivo (para pessoas e para qualquer IA):**",
    "> - `**[hh:mm:ss]**` abre um parágrafo de fala e marca onde ele começa no vídeo "
    "(uma marca a cada ~1 min).",
    "> - Blocos `🖼️ **Na tela [hh:mm:ss]**` são o texto lido da imagem do vídeo por OCR "
    "(slides, telas, legendas). Podem ter erros e linhas incompletas. Quando a fala disser "
    "\"aqui\", \"isto\" ou \"esse gráfico\", o bloco \"Na tela\" mais próximo costuma ser o que estava visível.",
    "> - Não há descrição de imagens, pessoas, cores ou gráficos: só o que foi dito e o texto "
    "que apareceu na tela.",
    "> - A fala é uma transcrição automática e literal; pode errar nomes próprios e termos técnicos.",
    "> - Se você não conseguir ler o conteúdo abaixo, diga isso em vez de inventar. "
    "Não descreva nada que não esteja escrito neste arquivo.",
]

_FALA = re.compile(r"^\*\*\[\d\d:\d\d:\d\d\]\*\* (.*)$", re.MULTILINE)


def palavras_de_fala(texto_md: str) -> int:
    """Conta só as palavras faladas de um .md já pronto (ignora cabeçalho e blocos 'Na tela')."""
    return sum(len(m.group(1).split()) for m in _FALA.finditer(texto_md))


def palavras_da_tela(telas: "list[Tela]") -> int:
    return sum(len(t.texto.split()) for t in telas)


def link_seguro(caminho: str) -> str:
    """Espaços e parênteses quebram links Markdown (achado N7): vão codificados."""
    return caminho.replace("%", "%25").replace(" ", "%20").replace("(", "%28").replace(")", "%29")


@dataclass
class Tela:
    inicio: float
    texto: str
    imagem: Path | None = None


def montar(*, titulo: str, origem: str, duracao: float, modelo: str, preset: str,
           paragrafos: list[Paragrafo], telas: list[Tela], destino: Path,
           correcoes: int = 0, falha_telas: str | None = None,
           capturas_lidas: int = 0) -> tuple[str, int]:
    """Gera o conteúdo; telas entram logo após o parágrafo que cobre o seu instante."""
    blocos: list[str] = []
    telas = sorted(telas, key=lambda t: t.inicio)
    i = 0
    for n, p in enumerate(paragrafos):
        prox = paragrafos[n + 1].inicio if n + 1 < len(paragrafos) else float("inf")
        blocos.append(f"**[{hhmmss(p.inicio)}]** {p.texto}")
        while i < len(telas) and telas[i].inicio < prox:
            blocos.append(_bloco_tela(telas[i], destino))
            i += 1
    while i < len(telas):  # telas sem fala nenhuma (vídeo mudo, por exemplo)
        blocos.append(_bloco_tela(telas[i], destino))
        i += 1

    corpo = "\n\n".join(blocos)
    palavras = sum(len(p.texto.split()) for p in paragrafos)  # só a fala (achado N2)
    cab = [
        f"# {titulo}",
        "",
        f"- **Arquivo de origem:** {origem}",
        f"- **Duração:** {hhmmss(duracao)}",
        f"- **Palavras de fala:** {palavras}",
        f"- **Palavras de texto de tela:** {palavras_da_tela(telas)}" if telas else None,
        f"- **Transcrito em:** {datetime.now():%d/%m/%Y}",
        f"- **Modelo:** faster-whisper {modelo} ({preset})",
        "- **Texto de tela (OCR):** " + _linha_ocr(telas, falha_telas, capturas_lidas),
        f"- **Correções automáticas:** {correcoes} (lista correcoes.json)" if correcoes else None,
        "",
        *COMO_LER,
        "",
        "---",
        "",
        "",
    ]
    return "\n".join(l for l in cab if l is not None) + corpo + "\n", palavras


def _linha_ocr(telas: list[Tela], falha: str | None, capturas_lidas: int) -> str:
    if telas:
        return f"sim, {len(telas)} trecho(s)" + (f"; com falhas ({falha})" if falha else "")
    if falha:
        return f"não lido por completo ({falha})"
    if capturas_lidas:
        return f"lido, nenhum texto aproveitável em {capturas_lidas} capturas"
    return "não"


def _bloco_tela(t: Tela, destino_md: Path) -> str:
    linhas = [f"> 🖼️ **Na tela [{hhmmss(t.inicio)}]**"]
    if t.imagem is not None:
        rel = os.path.relpath(t.imagem, destino_md.parent).replace("\\", "/")
        linhas[0] += f" · [captura]({link_seguro(rel)})"
    linhas += [f"> {l}" for l in t.texto.splitlines()]
    return "\n".join(linhas)


def salvar(conteudo: str, destino: Path) -> None:
    gravar_texto_atomico(destino, conteudo)
