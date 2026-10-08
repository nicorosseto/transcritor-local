"""Montagem do .md final: cabeçalho, fala com timestamps e blocos "Na tela"."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .transcricao import Paragrafo
from .util import hhmmss


@dataclass
class Tela:
    inicio: float
    texto: str
    imagem: Path | None = None


def montar(*, titulo: str, origem: str, duracao: float, modelo: str, preset: str,
           paragrafos: list[Paragrafo], telas: list[Tela], destino: Path,
           correcoes: int = 0) -> tuple[str, int]:
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
    palavras = len(corpo.split())
    cab = [
        f"# {titulo}",
        "",
        f"- **Arquivo de origem:** {origem}",
        f"- **Duração:** {hhmmss(duracao)}",
        f"- **Palavras:** {palavras:,}".replace(",", "."),
        f"- **Transcrito em:** {datetime.now():%d/%m/%Y}",
        f"- **Modelo:** faster-whisper {modelo} ({preset})",
        f"- **Texto de tela (OCR):** {'sim, ' + str(len(telas)) + ' trecho(s)' if telas else 'não'}",
        f"- **Correções automáticas:** {correcoes} (lista correcoes.json)" if correcoes else None,
        "",
        "> Transcrição automática e literal da fala. Pode conter erros em nomes próprios e termos técnicos.",
        "",
        "---",
        "",
        "",
    ]
    return "\n".join(l for l in cab if l is not None) + corpo + "\n", palavras


def _bloco_tela(t: Tela, destino_md: Path) -> str:
    linhas = [f"> 🖼️ **Na tela [{hhmmss(t.inicio)}]**"]
    if t.imagem is not None:
        rel = os.path.relpath(t.imagem, destino_md.parent).replace("\\", "/")
        linhas[0] += f" · [captura]({rel})"
    linhas += [f"> {l}" for l in t.texto.splitlines()]
    return "\n".join(linhas)


def salvar(conteudo: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(destino)
