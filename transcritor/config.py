"""Configuração do transcritor e predefinições de qualidade."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .util import gravar_texto_atomico

EXTENSOES_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg"}

# Predefinições em linguagem simples. Velocidades padrão são CONSERVADORAS (CPU);
# depois da primeira execução, o programa usa a velocidade medida no próprio PC.
PRESETS = {
    "rapido": {
        "rotulo": "Rápido",
        "descricao": "Modelo menor. Mais veloz, erra mais nomes e termos técnicos.",
        "modelo": "small",
        "beam_size": 1,
        "velocidade_padrao_cpu": 2.0,
    },
    "equilibrado": {
        "rotulo": "Equilibrado",
        "descricao": "Melhor custo-benefício. Recomendado para a maioria dos casos.",
        "modelo": "large-v3-turbo",
        "beam_size": 1,
        "velocidade_padrao_cpu": 1.2,
    },
    "preciso": {
        "rotulo": "Preciso",
        "descricao": "Busca mais ampla. Um pouco mais exato, cerca de 1,5x a 2x mais lento.",
        "modelo": "large-v3-turbo",
        "beam_size": 5,
        "velocidade_padrao_cpu": 0.8,
    },
}

NOME_ARQUIVO_CONFIG = "transcritor_config.json"


def _nucleos_de_desempenho(classes: list[int]) -> int | None:
    """Recebe a "classe de eficiência" de cada núcleo físico (Windows). Em CPU híbrida (Intel 12ª
    geração em diante), os núcleos de desempenho (P-cores) têm a classe mais alta. Retorna quantos
    são, ou None se a CPU não for híbrida."""
    if not classes or len(set(classes)) < 2:
        return None
    return classes.count(max(classes))


def _classes_de_eficiencia_windows() -> list[int]:
    """GetLogicalProcessorInformationEx(RelationProcessorCore): um registro por núcleo físico."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    tamanho = wintypes.DWORD(0)
    k32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(tamanho))
    if not tamanho.value:
        return []
    buf = ctypes.create_string_buffer(tamanho.value)
    if not k32.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(tamanho)):
        return []
    classes, pos, dados = [], 0, buf.raw
    while pos + 10 <= tamanho.value:
        relacao = int.from_bytes(dados[pos:pos + 4], "little")
        tam = int.from_bytes(dados[pos + 4:pos + 8], "little")
        if tam <= 0:
            break
        if relacao == 0:              # RelationProcessorCore
            classes.append(dados[pos + 9])  # Flags (1 byte) + EfficiencyClass (1 byte)
        pos += tam
    return classes


def threads_padrao() -> int:
    """Núcleos FÍSICOS, não threads lógicas (P17).

    Medido em 11/10/2026 no PC de referência (6 núcleos / 12 threads), 3 min de fala, beam 1:
    4 threads = 1,57x · 6 = 1,56x · 12 = 1,34x. Passar dos núcleos físicos deixa o Whisper ~15% mais lento.
    Em CPU híbrida no Windows, só os núcleos de desempenho (dedução, não medido; ver ADR-015).
    """
    try:
        import psutil
        fisicos = psutil.cpu_count(logical=False)
    except Exception:
        fisicos = None
    if not fisicos:
        fisicos = max(1, (os.cpu_count() or 8) // 2)  # sem psutil: supõe 2 threads por núcleo
    if os.name == "nt":
        try:  # CPU híbrida: os núcleos eficientes (E-cores) atrasam todas as threads
            p_cores = _nucleos_de_desempenho(_classes_de_eficiencia_windows())
            if p_cores:
                return p_cores
        except Exception:
            pass
    return max(1, fisicos)


@dataclass
class Config:
    pasta_videos: Path
    pasta_saida: Path
    preset: str = "equilibrado"
    idioma: str | None = "pt"
    dispositivo: str = "auto"            # auto | cpu | cuda
    threads: int = 0                     # 0 = automático (núcleos físicos, ver threads_padrao)
    vocabulario: list[str] = field(default_factory=list)
    ocr: bool = False
    segundos_por_paragrafo: int = 60
    max_palavras_por_base: int = 400_000  # NotebookLM aceita 500 mil por fonte

    # ---------- derivados ----------
    @property
    def modelo(self) -> str:
        return PRESETS[self.preset]["modelo"]

    @property
    def beam_size(self) -> int:
        return PRESETS[self.preset]["beam_size"]

    @property
    def threads_efetivas(self) -> int:
        return self.threads if self.threads > 0 else threads_padrao()

    @property
    def pasta_audio(self) -> Path:
        return self.pasta_saida / "audio_mp3"

    @property
    def pasta_md(self) -> Path:
        return self.pasta_saida / "transcricoes_md"

    @property
    def pasta_capturas(self) -> Path:
        return self.pasta_saida / "capturas"

    @property
    def pasta_base(self) -> Path:
        return self.pasta_saida / "base_consolidada"

    @property
    def pasta_pacote(self) -> Path:
        return self.pasta_saida / "pacote_para_ia"

    @property
    def pasta_orfaos(self) -> Path:
        return self.pasta_saida / "_orfaos"

    @property
    def arquivo_registro(self) -> Path:
        return self.pasta_saida / "registro.csv"

    # ---------- validação ----------
    def validar(self) -> list[str]:
        erros = []
        if self.preset not in PRESETS:
            erros.append(f"Predefinição desconhecida: {self.preset}")
        if not self.pasta_videos.is_dir():
            erros.append(f"A pasta de vídeos não existe: {self.pasta_videos}")
        try:
            saida = self.pasta_saida.resolve()
            videos = self.pasta_videos.resolve()
            if saida == videos or videos in saida.parents:
                erros.append("A pasta de saída não pode ficar dentro da pasta de vídeos.")
        except OSError:
            pass
        return erros

    # ---------- persistência (salva na pasta de saída) ----------
    def salvar(self) -> None:
        self.pasta_saida.mkdir(parents=True, exist_ok=True)
        dados = asdict(self)
        dados["pasta_videos"] = str(self.pasta_videos)
        dados["pasta_saida"] = str(self.pasta_saida)
        gravar_texto_atomico(self.pasta_saida / NOME_ARQUIVO_CONFIG,
                             json.dumps(dados, ensure_ascii=False, indent=2))

    @classmethod
    def carregar(cls, pasta_saida: Path, pasta_videos: Path | None = None) -> "Config":
        arq = pasta_saida / NOME_ARQUIVO_CONFIG
        dados = {}
        if arq.is_file():
            try:
                dados = json.loads(arq.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                dados = {}
        campos = {f for f in cls.__dataclass_fields__}
        dados = {k: v for k, v in dados.items() if k in campos}
        dados["pasta_saida"] = pasta_saida
        dados["pasta_videos"] = Path(pasta_videos or dados.get("pasta_videos") or ".")
        cfg = cls(**dados)
        if cfg.preset not in PRESETS:
            cfg.preset = "equilibrado"
        return cfg


def vocabulario_de_texto(texto: str) -> list[str]:
    """'Power BI, DAX; ChatGPT' -> ['Power BI', 'DAX', 'ChatGPT']"""
    partes = [p.strip() for p in texto.replace(";", ",").replace("\n", ",").split(",")]
    return [p for p in partes if p]
