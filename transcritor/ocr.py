"""Leitura de texto nas capturas de tela (OCR) com o Tesseract, 100% local."""

from __future__ import annotations

import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .util import localizar_binario, pasta_dados_usuario, rodar

URL_PORTUGUES = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/por.traineddata"
_CAMINHOS_WINDOWS = [Path(r"C:\Program Files\Tesseract-OCR"), Path(r"C:\Program Files (x86)\Tesseract-OCR")]


@dataclass
class EstadoOCR:
    disponivel: bool
    executavel: str | None
    tem_portugues: bool
    pasta_tessdata: Path | None   # None = usar a pasta padrão do Tesseract
    mensagem: str
    idiomas: str = "por+eng"


def _pasta_tessdata_app() -> Path:
    return pasta_dados_usuario() / "tessdata"


def _idiomas(exe: str, tessdata: Path | None) -> set[str]:
    cmd = [exe, "--list-langs"]
    if tessdata:
        cmd[1:1] = ["--tessdata-dir", str(tessdata)]
    try:
        r = rodar(cmd, capture_output=True, text=True, timeout=30)
    except Exception:
        return set()
    linhas = (r.stdout + "\n" + r.stderr).splitlines()
    return {l.strip() for l in linhas if l.strip() and " " not in l.strip() and ":" not in l}


def verificar() -> EstadoOCR:
    exe = localizar_binario("tesseract", _CAMINHOS_WINDOWS if sys.platform == "win32" else None)
    if not exe:
        return EstadoOCR(False, None, False, None,
                         "Tesseract não instalado. Instale com: winget install --id UB-Mannheim.TesseractOCR -e")
    instalados = _idiomas(exe, None)
    if "por" in instalados:
        return EstadoOCR(True, exe, True, None, "Tesseract com português pronto.",
                         "por+eng" if "eng" in instalados else "por")
    app_dir = _pasta_tessdata_app()
    if (app_dir / "por.traineddata").is_file():
        # a pasta do app precisa ter também o inglês para o modo "por+eng"
        return EstadoOCR(True, exe, True, app_dir, "Tesseract pronto (português na pasta do app).")
    return EstadoOCR(True, exe, False, None,
                     "Tesseract instalado, mas sem o pacote de português (será baixado: ~2 MB).")


def baixar_portugues() -> Path:
    """Baixa por.traineddata (e eng) para a pasta do usuário, sem precisar de administrador."""
    destino = _pasta_tessdata_app()
    destino.mkdir(parents=True, exist_ok=True)
    for idioma in ("por", "eng"):
        arq = destino / f"{idioma}.traineddata"
        if arq.is_file() and arq.stat().st_size > 100_000:
            continue
        tmp = arq.with_suffix(".parcial")
        url = URL_PORTUGUES.replace("por.", f"{idioma}.")
        with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as f:
            f.write(resp.read())
        tmp.replace(arq)
    return destino


def ler_imagem(estado: EstadoOCR, imagem: Path) -> str:
    if not estado.disponivel or not estado.executavel:
        return ""
    cmd = [estado.executavel, str(imagem), "stdout", "-l", estado.idiomas, "--psm", "3"]
    if estado.pasta_tessdata:
        cmd[1:1] = ["--tessdata-dir", str(estado.pasta_tessdata)]
    try:
        r = rodar(cmd, capture_output=True, timeout=120)
    except Exception:
        return ""
    return r.stdout.decode("utf-8", errors="replace")


# ----------------------------------------------------------------------------- limpeza

_LETRAS = re.compile(r"[A-Za-zÀ-ÿ]")


def limpar(texto: str, max_chars: int = 1500) -> str:
    """Tira o lixo típico de OCR: linhas sem letras, símbolos soltos, espaços repetidos."""
    linhas = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        if len(_LETRAS.findall(linha)) >= 3:
            linhas.append(linha)
    resultado = "\n".join(linhas)
    return resultado[:max_chars].rstrip()


def e_util(texto: str, minimo_letras: int = 25) -> bool:
    return len(_LETRAS.findall(texto)) >= minimo_letras


def _palavras(texto: str) -> set[str]:
    return {p.lower() for p in re.findall(r"[A-Za-zÀ-ÿ0-9]{3,}", texto)}


def parecido(a: str, b: str, limite: float = 0.7) -> bool:
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return False
    return len(pa & pb) / len(pa | pb) >= limite
