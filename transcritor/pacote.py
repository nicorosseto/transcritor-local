"""Pacote para IA: o .md de um vídeo mais só as capturas que ele cita, numa pasta e num .zip.

Serve para anexar numa conversa com qualquer IA: o texto sozinho já se entende (cabeçalho "Como ler
este arquivo"); com as imagens, a IA também vê os slides citados. Fica fora o que não ajuda: o áudio,
o registro e as capturas que o OCR descartou.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

from .markdown import link_seguro

_CAPTURA = re.compile(r"(\[captura\]\()([^)\n]+)(\))")


def _nome_seguro(texto: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', " - ", texto).strip(" .-") or "video"


def montar(md: Path, destino_raiz: Path, nome: str) -> Path:
    """Cria destino_raiz/<nome>/ (md + imagens/) e destino_raiz/<nome>.zip. Refaz do zero se já existe."""
    nome = _nome_seguro(nome)
    pasta = destino_raiz / nome
    shutil.rmtree(pasta, ignore_errors=True)
    imagens = pasta / "imagens"
    imagens.mkdir(parents=True)
    usados: set[str] = set()

    def trocar(m: re.Match) -> str:
        origem = Path(os.path.normpath(os.path.join(md.parent, unquote(m.group(2)))))
        if not origem.is_file():
            return m.group(0)  # captura que não existe mais: mantém o link como está
        arquivo = origem.name
        n = 1
        while arquivo in usados:  # nomes iguais em vídeos diferentes não acontecem aqui, mas não custa
            arquivo = f"{origem.stem}_{n}{origem.suffix}"
            n += 1
        usados.add(arquivo)
        shutil.copy2(origem, imagens / arquivo)
        return f"{m.group(1)}{link_seguro('imagens/' + arquivo)}{m.group(3)}"

    texto = _CAPTURA.sub(trocar, md.read_text(encoding="utf-8", errors="replace"))
    (pasta / f"{nome}.md").write_text(texto, encoding="utf-8")
    if not usados:
        imagens.rmdir()
    zip_antigo = destino_raiz / f"{nome}.zip"
    zip_antigo.unlink(missing_ok=True)
    shutil.make_archive(str(destino_raiz / nome), "zip", root_dir=pasta)
    return pasta
