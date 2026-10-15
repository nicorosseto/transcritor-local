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

# Só a linha de cabeçalho que o app escreve ("> 🖼️ **Na tela [hh:mm:ss]** · [captura](...)"): um link
# parecido dentro do texto lido da tela não é seguido (achado B1/K5)
_CAPTURA = re.compile(r"^(> 🖼️ \*\*Na tela \[[0-9:]+\]\*\* · \[captura\]\()([^)\n]+)(\))", re.M)
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp"}


def nome_seguro(texto: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', " - ", texto).strip(" .-") or "video"


def _captura_permitida(alvo: str, md: Path, raiz_capturas: Path) -> Path | None:
    """Caminho real da captura, ou None se ela não puder entrar no pacote (achado B1/K5).

    Entra só uma imagem que, com links simbólicos e "..", fique de fato dentro da pasta de capturas
    do projeto. Caminho absoluto, endereço (http:, file:) ou qualquer coisa fora dela fica de fora."""
    alvo = unquote(alvo)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", alvo) or alvo.startswith(("/", "\\")) or os.path.isabs(alvo):
        return None
    try:
        origem = (md.parent / alvo).resolve(strict=True)
        raiz = raiz_capturas.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if origem.suffix.lower() not in EXTENSOES_IMAGEM or not origem.is_file():
        return None
    try:
        origem.relative_to(raiz)
    except ValueError:
        return None
    return origem


def montar(md: Path, destino_raiz: Path, nome: str, raiz_capturas: Path) -> Path:
    """Cria destino_raiz/<nome>/ (md + imagens/) e destino_raiz/<nome>.zip. Refaz do zero se já existe.

    Só copia imagens de dentro de raiz_capturas; um link para qualquer outro lugar fica como está no
    texto, sem levar o arquivo."""
    nome = nome_seguro(nome)
    pasta = destino_raiz / nome
    shutil.rmtree(pasta, ignore_errors=True)
    imagens = pasta / "imagens"
    imagens.mkdir(parents=True)
    usados: set[str] = set()

    def trocar(m: re.Match) -> str:
        origem = _captura_permitida(m.group(2), md, raiz_capturas)
        if origem is None:
            return m.group(0)  # captura que não existe mais ou fora da pasta de capturas: não entra
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
