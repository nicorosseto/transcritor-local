"""Componentes que o app precisa e que não vêm no .zip: FFmpeg, modelo Whisper e Tesseract (opcional).

O FFmpeg (GPL) é baixado na primeira abertura, direto do distribuidor, numa versão fixa e conferida
por SHA-256: o .zip do app não redistribui binário GPL (ADR-021, achados B2/K2 de 14/10/2026).

O modelo é baixado UMA vez do Hugging Face para o cache do usuário; depois tudo roda offline.
O progresso é medido pelo tamanho da pasta de cache (funciona com qualquer backend de download).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .util import Cancelado, gravar_atomico, nome_temporario, pasta_dados_usuario, rodar

# Tamanho aproximado de cada modelo (usado só se não der para consultar o Hub)
TAMANHO_APROX = {"small": 0.48e9, "medium": 1.53e9, "large-v3": 3.09e9, "large-v3-turbo": 1.62e9}
URL_TESSERACT = "https://github.com/UB-Mannheim/tesseract/wiki"

# FFmpeg para Windows: build "essentials" de gyan.dev (GPL v3), publicada no GitHub do próprio
# distribuidor. Versão e hash fixos: trocar de versão = atualizar os três campos juntos.
FFMPEG = {
    "versao": "9.0.2",
    "url": "https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip",
    "sha256": "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba",
    "tamanho": 114_768_076,
    "pagina": "https://www.gyan.dev/ffmpeg/builds/",
    "fonte": "https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz",
}
_FFMPEG_ARQUIVOS = ("bin/ffmpeg.exe", "bin/ffprobe.exe", "LICENSE")


def pasta_ffmpeg() -> Path:
    """Onde o FFmpeg baixado pelo app fica (pasta do usuário, sem precisar de administrador)."""
    return pasta_dados_usuario() / "ffmpeg"


def ffmpeg_baixavel() -> bool:
    """O download automático é só para Windows; no Linux e no macOS, o FFmpeg vem do sistema."""
    return sys.platform == "win32"


def baixar_ffmpeg(ao_progredir=None, cancelar: threading.Event | None = None, origem: dict | None = None) -> Path:
    """Baixa o FFmpeg fixado em FFMPEG, confere o SHA-256 e extrai ffmpeg.exe, ffprobe.exe e a licença.

    ao_progredir(baixado_bytes, total_bytes). Nada fica pela metade: o arquivo baixado é temporário e
    só é usado se o hash conferir. Retorna a pasta bin."""
    info = origem or FFMPEG
    destino = pasta_ffmpeg()
    destino.mkdir(parents=True, exist_ok=True)
    tmp = nome_temporario(destino / "ffmpeg.zip", ".parcial")
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(info["url"], timeout=60) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or info.get("tamanho") or 0)
            feito = 0
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise Cancelado()
                bloco = resp.read(1 << 20)
                if not bloco:
                    break
                f.write(bloco)
                h.update(bloco)
                feito += len(bloco)
                if ao_progredir:
                    ao_progredir(feito, total)
        if h.hexdigest() != info["sha256"]:
            raise RuntimeError("O FFmpeg baixado não confere com o esperado (SHA-256 diferente). "
                               "Pode ter sido um download corrompido: tente de novo.")
        with zipfile.ZipFile(tmp) as z:
            achados = {}
            for nome in z.namelist():
                for alvo in _FFMPEG_ARQUIVOS:
                    if nome.replace("\\", "/").endswith("/" + alvo):
                        achados[alvo] = nome
            faltam = [a for a in _FFMPEG_ARQUIVOS if a not in achados]
            if faltam:
                raise RuntimeError(f"O pacote do FFmpeg não tem: {', '.join(faltam)}.")
            for alvo, nome in achados.items():
                final = destino / ("LICENSE.txt" if alvo == "LICENSE" else alvo)
                dados = z.read(nome)
                gravar_atomico(final, lambda p, d=dados: p.write_bytes(d))
        texto = (f"FFmpeg {info['versao']} para Windows, build \"essentials\" de gyan.dev (licença GPL v3).\n"
                 f"Baixado pelo Transcritor Local de: {info['url']}\n"
                 f"SHA-256 conferido: {info['sha256']}\n"
                 f"Página do distribuidor: {info['pagina']}\n"
                 f"Código-fonte do FFmpeg desta versão: {info['fonte']}\n"
                 "O Transcritor Local (MIT) chama o FFmpeg como programa separado e não o redistribui.\n")
        gravar_atomico(destino / "ORIGEM.txt", lambda p: p.write_text(texto, encoding="utf-8"))
        return destino / "bin"
    finally:
        tmp.unlink(missing_ok=True)


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
