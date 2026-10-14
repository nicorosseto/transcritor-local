"""Leitura de texto nas capturas de tela (OCR) com o Tesseract, 100% local."""

from __future__ import annotations

import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .util import localizar_binario, nome_temporario, pasta_dados_usuario, rodar

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
        tmp = nome_temporario(arq, ".parcial")
        url = URL_PORTUGUES.replace("por.", f"{idioma}.")
        with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as f:
            f.write(resp.read())
        tmp.replace(arq)
    return destino


class ErroOCR(RuntimeError):
    """Falha técnica do Tesseract (diferente de "a imagem não tem texto"; achado X10)."""


LARGURA_MINIMA = 1280      # capturas mais estreitas são ampliadas 2x antes do OCR (achado N1)
CONFIANCA_MINIMA = 50.0    # abaixo disso o Tesseract mesmo duvida; descartadas (achado N1; valor provisório)


def preparar_imagem(imagem: Path) -> tuple[Path, bool]:
    """Devolve (imagem_para_o_ocr, é_temporária).

    O Tesseract lê mal texto pequeno: num vídeo 640x360 ele acertou 6% das palavras de um quadro;
    ampliando 2x (tons de cinza, Lanczos) passou a acertar 56%. Capturas largas seguem como estão.
    """
    from PIL import Image
    with Image.open(imagem) as img:
        if img.width >= LARGURA_MINIMA:
            return imagem, False
        ampliada = img.convert("L").resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
    temporaria = imagem.with_name(f"_ocr_{imagem.stem}.png")
    ampliada.save(temporaria)
    return temporaria, True


def texto_do_tsv(tsv: str, confianca_minima: float = CONFIANCA_MINIMA) -> str:
    """Monta o texto a partir da saída `tsv` do Tesseract, mantendo só palavras confiáveis.

    Cada linha do resultado é uma linha da imagem; linhas sem nenhuma palavra confiável somem."""
    linhas: dict[tuple[str, str, str], list[str]] = {}
    for bruta in tsv.splitlines()[1:]:
        c = bruta.split("\t", 11)
        if len(c) < 12 or c[0] != "5":  # nível 5 = palavra
            continue
        texto = c[11].strip()
        try:
            confianca = float(c[10])
        except ValueError:
            continue
        if texto and confianca >= confianca_minima:
            linhas.setdefault((c[2], c[3], c[4]), []).append(texto)
    return "\n".join(" ".join(palavras) for palavras in linhas.values())


def ler_imagem(estado: EstadoOCR, imagem: Path) -> str:
    if not estado.disponivel or not estado.executavel:
        raise ErroOCR("Tesseract indisponível")
    try:
        entrada, temporaria = preparar_imagem(imagem)
    except Exception as e:
        raise ErroOCR(f"Não consegui preparar a captura para o OCR: {e}") from e
    try:
        # Não usar a configuração "tsv": ela é procurada em <tessdata>/configs/, que a pasta de idiomas do
        # app não tem; o Tesseract avisava só no erro e devolvia texto comum (achado N8).
        cmd = [estado.executavel, str(entrada), "stdout", "-l", estado.idiomas, "--psm", "3",
               "-c", "tessedit_create_tsv=1"]
        if estado.pasta_tessdata:
            cmd[1:1] = ["--tessdata-dir", str(estado.pasta_tessdata)]
        try:
            r = rodar(cmd, capture_output=True, timeout=120)
        except Exception as e:
            raise ErroOCR(f"Tesseract não pôde ser executado: {e}") from e
        if r.returncode != 0:
            msg = r.stderr.decode("utf-8", errors="replace").strip().splitlines()
            raise ErroOCR("Tesseract falhou" + (f": {msg[-1]}" if msg else f" (código {r.returncode})"))
        saida = r.stdout.decode("utf-8", errors="replace").lstrip("\ufeff")
        if not saida.startswith("level\t"):  # nunca confundir "formato errado" com "sem texto na imagem"
            raise ErroOCR("A leitura do Tesseract veio em formato inesperado (não é TSV)")
        return texto_do_tsv(saida)
    finally:
        if temporaria:
            entrada.unlink(missing_ok=True)


# ----------------------------------------------------------------------------- limpeza

_LETRAS = re.compile(r"[A-Za-zÀ-ÿ]")


PROPORCAO_LINHAS_BOAS = 0.4   # bloco com menos linhas legíveis que isso é ruído (achado N9)


def linha_legivel(linha: str) -> bool:
    """Uma linha parece texto de verdade quando ao menos 60% das letras estão em palavras de 4+ letras.

    Pega o lixo típico do OCR em letra pequena ("Es Ou ou mu ou", "voe 8") e mantém rótulos curtos
    reais ("Compartilhar", "Opus 47", "FORMATO DE")."""
    letras = len(_LETRAS.findall(linha))
    if letras < 4:
        return False
    em_palavras = sum(len(w) for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", linha))
    return em_palavras / letras >= 0.6


def limpar(texto: str, max_chars: int = 1500) -> str:
    """Tira o lixo típico de OCR: linhas sem letras, linhas ilegíveis, espaços repetidos.

    Se a maioria das linhas for ilegível, o bloco inteiro é descartado (devolve "")."""
    candidatas = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        if len(_LETRAS.findall(linha)) >= 3:
            candidatas.append(linha)
    boas = [l for l in candidatas if linha_legivel(l)]
    if not boas or len(boas) / len(candidatas) < PROPORCAO_LINHAS_BOAS:
        return ""
    return "\n".join(boas)[:max_chars].rstrip()


def e_util(texto: str, minimo_letras: int = 25) -> bool:
    return len(_LETRAS.findall(texto)) >= minimo_letras


def _palavras(texto: str) -> set[str]:
    return {p.lower() for p in re.findall(r"[A-Za-zÀ-ÿ0-9]{3,}", texto)}


def parecido(a: str, b: str, limite: float = 0.7) -> bool:
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return False
    return len(pa & pb) / len(pa | pb) >= limite
