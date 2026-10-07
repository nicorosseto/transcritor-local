"""Junta as transcrições em arquivos maiores: um conjunto por subpasta (módulo)."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

RAIZ = "geral"


def _nome_seguro(texto: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", texto).strip() or RAIZ


def grupo(caminho_relativo: str) -> str:
    partes = caminho_relativo.split("/")
    return partes[0] if len(partes) > 1 else RAIZ


def consolidar(itens: list[tuple[str, Path]], pasta_base: Path, max_palavras: int) -> list[Path]:
    """itens: [(caminho_relativo_do_video, md)] já concluídos. Recria a pasta de base inteira."""
    pasta_base.mkdir(parents=True, exist_ok=True)
    for antigo in pasta_base.glob("base_*.md"):
        antigo.unlink()
    por_grupo: dict[str, list[Path]] = defaultdict(list)
    for rel, md in sorted(itens, key=lambda x: x[0].lower()):
        if md.is_file():
            por_grupo[grupo(rel)].append(md)

    gerados: list[Path] = []
    for nome, mds in sorted(por_grupo.items()):
        partes: list[list[str]] = [[]]
        contagem = 0
        for md in mds:
            texto = md.read_text(encoding="utf-8")
            n = len(texto.split())
            if partes[-1] and contagem + n > max_palavras:
                partes.append([])
                contagem = 0
            partes[-1].append(texto)
            contagem += n
        for i, blocos in enumerate(partes, 1):
            sufixo = f"_parte{i:02d}" if len(partes) > 1 else ""
            destino = pasta_base / f"base_{_nome_seguro(nome)}{sufixo}.md"
            destino.write_text(f"# Base: {nome}\n\n" + "\n\n\n".join(blocos), encoding="utf-8")
            gerados.append(destino)
    return gerados
