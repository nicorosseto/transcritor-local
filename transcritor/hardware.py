"""Varredura do PC: diz o que ajuda, o que atrapalha e o que é recomendado."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .util import localizar_binario, rodar

OK, AVISO, ERRO, INFO = "ok", "aviso", "erro", "info"


@dataclass
class Item:
    nome: str
    valor: str
    nivel: str
    explicacao: str


@dataclass
class Diagnostico:
    itens: list[Item] = field(default_factory=list)
    preset_recomendado: str = "equilibrado"
    dispositivo: str = "cpu"
    pode_rodar: bool = True

    def add(self, *args):
        self.itens.append(Item(*args))


# ----------------------------------------------------------------------------- coleta

def nome_cpu() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    try:
        for linha in Path("/proc/cpuinfo").read_text().splitlines():
            if linha.startswith("model name"):
                return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "desconhecido"


def tem_avx2() -> bool | None:
    if sys.platform == "win32":
        try:
            import ctypes
            return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(40))  # PF_AVX2
        except Exception:
            return None
    try:
        return " avx2" in Path("/proc/cpuinfo").read_text()
    except OSError:
        return None


def nucleos() -> tuple[int, int]:
    try:
        import psutil
        return psutil.cpu_count(logical=False) or 0, psutil.cpu_count(logical=True) or 0
    except ImportError:
        n = os.cpu_count() or 0
        return n, n


def ram_gb() -> tuple[float, float]:
    try:
        import psutil
        m = psutil.virtual_memory()
        return m.total / 1024 ** 3, m.available / 1024 ** 3
    except ImportError:
        return 0.0, 0.0


def placas_video() -> list[dict]:
    """[{'nome': ..., 'fabricante': 'nvidia|amd|intel|outro', 'vram_gb': float|None}]"""
    placas: list[dict] = []
    if sys.platform == "win32":
        ps = ("Get-CimInstance Win32_VideoController | "
              "Select-Object Name,AdapterRAM | ConvertTo-Json -Compress")
        try:
            r = rodar(["powershell", "-NoProfile", "-Command", ps],
                      capture_output=True, text=True, timeout=30)
            dados = json.loads(r.stdout or "[]")
            if isinstance(dados, dict):
                dados = [dados]
            for d in dados:
                nome = (d.get("Name") or "").strip()
                vram = d.get("AdapterRAM")
                # AdapterRAM é um inteiro de 32 bits: placas com mais de 4 GB aparecem como 4 GB
                placas.append({"nome": nome, "fabricante": _fabricante(nome),
                               "vram_gb": (vram / 1024 ** 3) if vram else None})
        except Exception:
            pass
    else:
        lspci = shutil.which("lspci")
        if lspci:
            try:
                r = rodar([lspci], capture_output=True, text=True, timeout=10)
                for l in r.stdout.splitlines():
                    if "VGA" in l or "3D controller" in l:
                        nome = l.split(":", 2)[-1].strip()
                        placas.append({"nome": nome, "fabricante": _fabricante(nome), "vram_gb": None})
            except Exception:
                pass
    return placas


def _fabricante(nome: str) -> str:
    n = nome.lower()
    if "nvidia" in n or "geforce" in n or "quadro" in n or "rtx" in n:
        return "nvidia"
    if "amd" in n or "radeon" in n or n.startswith("rx"):
        return "amd"
    if "intel" in n:
        return "intel"
    return "outro"


def cuda_disponivel() -> bool:
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def disco_livre_gb(pasta: Path) -> float:
    alvo = pasta
    while not alvo.exists() and alvo != alvo.parent:
        alvo = alvo.parent
    try:
        return shutil.disk_usage(alvo).free / 1024 ** 3
    except OSError:
        return 0.0


# ----------------------------------------------------------------------------- avaliação

def diagnosticar(pasta_saida: Path | None = None) -> Diagnostico:
    d = Diagnostico()

    cpu = nome_cpu()
    fis, log = nucleos()
    avx2 = tem_avx2()
    nivel_cpu = OK if log >= 8 else (AVISO if log >= 4 else ERRO)
    d.add("Processador", f"{cpu} — {fis} núcleos / {log} threads", nivel_cpu,
          "É ele que faz a transcrição. Mais threads = mais rápido." if nivel_cpu == OK else
          "Poucos núcleos: a transcrição vai ser lenta. Prefira a predefinição Rápido.")
    if avx2 is False:
        d.add("Instruções AVX2", "ausente", AVISO,
              "Sem AVX2 a transcrição na CPU fica bem mais lenta.")
    elif avx2:
        d.add("Instruções AVX2", "presente", OK, "Acelera o Whisper na CPU.")

    total, livre = ram_gb()
    if total:
        nivel = OK if total >= 12 else (AVISO if total >= 8 else ERRO)
        d.add("Memória RAM", f"{total:.0f} GB (livre agora: {livre:.1f} GB)", nivel,
              {OK: "Suficiente para o modelo turbo e para a futura IA visual (uma de cada vez).",
               AVISO: "Dá para transcrever, mas feche outros programas. A IA visual ficará no limite.",
               ERRO: "Pouca memória: use a predefinição Rápido."}[nivel])
        if nivel == ERRO:
            d.preset_recomendado = "rapido"

    placas = placas_video()
    cuda = cuda_disponivel()
    if cuda:
        d.dispositivo = "cuda"
        d.add("Placa de vídeo", ", ".join(p["nome"] for p in placas) or "NVIDIA",
              OK, "NVIDIA com CUDA detectada: transcrição ~5x ou mais rápida.")
    elif any(p["fabricante"] == "nvidia" for p in placas):
        d.add("Placa de vídeo", ", ".join(p["nome"] for p in placas), AVISO,
              "Há uma NVIDIA, mas as bibliotecas CUDA não foram encontradas. Rodando na CPU. "
              "Veja 'Acelerar com NVIDIA' no guia.")
    elif placas:
        d.add("Placa de vídeo", ", ".join(p["nome"] for p in placas), INFO,
              "O motor de transcrição só usa placas NVIDIA. Esta placa não acelera; "
              "tudo roda na CPU (funciona normalmente, só mais devagar).")
    else:
        d.add("Placa de vídeo", "não identificada", INFO, "Tudo roda na CPU.")

    if pasta_saida is not None:
        livre_disco = disco_livre_gb(pasta_saida)
        nivel = OK if livre_disco >= 10 else (AVISO if livre_disco >= 3 else ERRO)
        d.add("Espaço em disco (saída)", f"{livre_disco:.0f} GB livres", nivel,
              "Modelo (~1,6 GB) + áudios (~20 MB/h) + capturas (~15 MB/h)." if nivel == OK else
              "Pouco espaço: libere disco antes de rodar um lote grande.")
        if nivel == ERRO:
            d.pode_rodar = False

    ff = localizar_binario("ffmpeg")
    d.add("FFmpeg", "encontrado" if ff else "NÃO encontrado", OK if ff else ERRO,
          "Extrai áudio e imagens dos vídeos." if ff else
          "Obrigatório. Instale com: winget install --id Gyan.FFmpeg -e")
    if not ff:
        d.pode_rodar = False

    from . import ocr
    est = ocr.verificar()
    d.add("Tesseract (texto da tela)", "pronto" if est.disponivel and est.tem_portugues else
          ("sem português" if est.disponivel else "não instalado"),
          OK if est.disponivel and est.tem_portugues else INFO, est.mensagem +
          ("" if est.disponivel else " (opcional: só é necessário para ler texto da tela)."))

    if sys.platform == "win32" and "onedrive" in str(Path(sys.executable)).lower():
        d.add("Python dentro do OneDrive", str(Path(sys.executable).parent), AVISO,
              "Funciona, mas a sincronização pode travar atualizações de bibliotecas. "
              "Pause o OneDrive ao instalar/atualizar.")
    return d
