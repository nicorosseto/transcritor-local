"""Junta as transcrições em arquivos maiores: um conjunto por subpasta (módulo)."""

from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

RAIZ = "geral"


def _nome_seguro(texto: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", texto).strip() or RAIZ


def grupo(caminho_relativo: str) -> str:
    partes = caminho_relativo.split("/")
    return partes[0] if len(partes) > 1 else RAIZ


def consolidar(itens: list[tuple[str, Path]], pasta_base: Path, max_palavras: int) -> list[Path]:
    """itens: [(caminho_relativo_do_video, md)] já concluídos. Recria a base inteira.

    Transacional (achado X5): monta tudo numa pasta temporária ao lado e só então troca.
    Se algo falhar no meio, a base anterior fica intacta.
    """
    pasta_base.mkdir(parents=True, exist_ok=True)
    tmp = pasta_base.parent / f".{pasta_base.name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        nomes = _montar(itens, tmp, max_palavras, pasta_final=pasta_base)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    for antigo in pasta_base.glob("base_*.md"):
        if antigo.name not in nomes:
            antigo.unlink()
    gerados = []
    for nome in nomes:
        os.replace(tmp / nome, pasta_base / nome)
        gerados.append(pasta_base / nome)
    shutil.rmtree(tmp, ignore_errors=True)
    return gerados


_LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def _corrigir_links(texto: str, md: Path, destino_dir: Path) -> str:
    """Links relativos do .md individual passam a valer a partir da pasta da base (achado X8)."""
    def trocar(m: re.Match) -> str:
        alvo = m.group(2)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^#|^/", alvo):  # http:, file:, âncora, absoluto
            return m.group(0)
        absoluto = os.path.normpath(os.path.join(md.parent, alvo))
        novo = os.path.relpath(absoluto, destino_dir).replace("\\", "/")
        return f"{m.group(1)}{novo}{m.group(3)}"
    return _LINK.sub(trocar, texto)


def _palavras(texto: str) -> int:
    return len(texto.split())


def _fatiar(texto: str, limite: int) -> list[str]:
    """Divide um texto grande em pedaços de até `limite` palavras (achado X9).
    Corta entre parágrafos; só corta um parágrafo no meio se ele sozinho passar do limite."""
    pedacos: list[str] = []
    atual: list[str] = []
    contagem = 0
    for par in texto.split("\n\n"):
        n = _palavras(par)
        if n > limite:
            if atual:
                pedacos.append("\n\n".join(atual))
                atual, contagem = [], 0
            palavras = par.split()
            pedacos += [" ".join(palavras[i:i + limite]) for i in range(0, len(palavras), limite)]
            continue
        if atual and contagem + n > limite:
            pedacos.append("\n\n".join(atual))
            atual, contagem = [], 0
        atual.append(par)
        contagem += n
    if atual:
        pedacos.append("\n\n".join(atual))
    return pedacos


def _montar(itens: list[tuple[str, Path]], pasta: Path, max_palavras: int,
            pasta_final: Path | None = None) -> list[str]:
    destino_dir = pasta_final or pasta
    por_grupo: dict[str, list[Path]] = defaultdict(list)
    for rel, md in sorted(itens, key=lambda x: x[0].lower()):
        if md.is_file():
            por_grupo[grupo(rel)].append(md)

    nomes: list[str] = []
    for nome, mds in sorted(por_grupo.items()):
        cabecalho = f"# Base: {nome}\n\n"
        limite = max(1, max_palavras - _palavras(cabecalho))  # o cabeçalho conta no limite
        partes: list[list[str]] = [[]]
        contagem = 0
        for md in mds:
            texto = _corrigir_links(md.read_text(encoding="utf-8", errors="replace"), md, destino_dir)
            n = _palavras(texto)
            blocos = [texto] if n <= limite else _fatiar(texto, limite)
            for bloco in blocos:
                nb = _palavras(bloco)
                if partes[-1] and contagem + nb > limite:
                    partes.append([])
                    contagem = 0
                partes[-1].append(bloco)
                contagem += nb
        for i, blocos in enumerate(partes, 1):
            sufixo = f"_parte{i:02d}" if len(partes) > 1 else ""
            arquivo = f"base_{_nome_seguro(nome)}{sufixo}.md"
            (pasta / arquivo).write_text(cabecalho + "\n\n\n".join(blocos), encoding="utf-8")
            nomes.append(arquivo)
    return nomes
