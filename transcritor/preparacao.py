"""Componentes que o app precisa e que não vêm no .zip: modelo Whisper e Tesseract (opcional).

O modelo é baixado UMA vez do Hugging Face para o cache do usuário; depois tudo roda offline.
O progresso é medido pelo tamanho da pasta de cache (funciona com qualquer backend de download).
"""

from __future__ import annotations

import shutil
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from .util import rodar

# Tamanho aproximado de cada modelo (usado só se não der para consultar o Hub)
TAMANHO_APROX = {"small": 0.48e9, "medium": 1.53e9, "large-v3": 3.09e9, "large-v3-turbo": 1.62e9}
URL_TESSERACT = "https://github.com/UB-Mannheim/tesseract/wiki"


@dataclass
class EstadoModelo:
    nome: str
    baixado: bool
    tamanho_bytes: float


def _repo(nome: str) -> str:
    from faster_whisper.utils import _MODELS
    return _MODELS.get(nome, nome)


def _pasta_cache_repo(nome: str) -> Path:
    from huggingface_hub.constants import HF_HUB_CACHE
    return Path(HF_HUB_CACHE) / ("models--" + _repo(nome).replace("/", "--"))


def estado_modelo(nome: str) -> EstadoModelo:
    from faster_whisper.utils import download_model
    try:
        download_model(nome, local_files_only=True)
        baixado = True
    except Exception:
        baixado = False
    return EstadoModelo(nome, baixado, TAMANHO_APROX.get(nome, 1.6e9))


def _tamanho_pasta(p: Path) -> int:
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def baixar_modelo(nome: str, ao_progredir=None, cancelar: threading.Event | None = None) -> None:
    """Baixa o modelo mostrando progresso. ao_progredir(baixado_bytes, total_bytes)."""
    from faster_whisper.utils import download_model
    total = TAMANHO_APROX.get(nome, 1.6e9)
    erro: list[BaseException] = []

    def tarefa():
        try:
            download_model(nome)
        except BaseException as e:  # noqa: BLE001 - repassado para a thread principal
            erro.append(e)

    t = threading.Thread(target=tarefa, daemon=True)
    pasta = _pasta_cache_repo(nome)
    t.start()
    while t.is_alive():
        if cancelar is not None and cancelar.is_set():
            return  # a thread daemon termina com o app; o próximo download retoma o arquivo parcial
        if ao_progredir:
            # inclui partes já baixadas antes (download interrompido é retomado)
            ao_progredir(min(_tamanho_pasta(pasta), total * 0.99), total)
        time.sleep(1.0)
    if erro:
        raise erro[0]
    if ao_progredir:
        ao_progredir(total, total)


# ----------------------------------------------------------------------------- Tesseract

def winget_disponivel() -> bool:
    return sys.platform == "win32" and shutil.which("winget") is not None


def instalar_tesseract() -> str:
    """Abre uma janela do Windows com o instalador oficial via winget (o usuário vê e confirma).
    Sem winget, abre a página de download. Retorna uma frase para mostrar ao usuário."""
    if winget_disponivel():
        cmd = ("winget install --id UB-Mannheim.TesseractOCR -e "
               "--accept-package-agreements --accept-source-agreements")
        rodar(["cmd", "/c", "start", "Instalando Tesseract", "cmd", "/k", cmd], creationflags=0)
        return ("Abri uma janela preta com o instalador. Aceite o pedido de permissão do Windows, "
                "espere terminar e depois clique em \"Verificar de novo\".")
    webbrowser.open(URL_TESSERACT)
    return "Abri a página oficial de download no navegador. Instale e depois clique em \"Verificar de novo\"."
