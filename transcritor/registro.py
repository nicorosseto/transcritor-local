"""registro.csv: memória do que já foi feito, e base das estimativas.

Um vídeo é identificado por caminho relativo + tamanho + data de modificação.
Isso permite detectar: vídeo novo, vídeo substituído (mesmo nome, outro conteúdo),
vídeo excluído (vira "órfão") e vídeo com erro (tentado de novo).

O CSV usa ';' e vírgula decimal para abrir direto no Excel/Power BI em português.
"""

from __future__ import annotations

import csv
import shutil
import statistics
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

from .util import ler_numero_br, numero_br

PENDENTE, OK, ERRO, ORFAO, SUBSTITUIDO = "pendente", "ok", "erro", "orfao", "substituido"


@dataclass
class Linha:
    caminho: str                 # relativo à pasta de vídeos, com "/"
    tamanho_bytes: int = 0
    modificado_em: str = ""      # ISO, do sistema de arquivos
    duracao_s: float = 0.0
    status: str = PENDENTE
    preset: str = ""
    ocr: str = "nao"             # sim | nao
    transcrito_em: str = ""      # DD/MM/AAAA HH:MM
    seg_transcricao: float = 0.0
    seg_ocr: float = 0.0
    velocidade: float = 0.0      # minutos de vídeo por minuto real (só a transcrição)
    palavras: int = 0
    capturas: int = 0
    correcoes: int = 0           # trocas feitas pela lista correcoes.json
    threads: int = 0             # diagnóstico de desempenho
    dispositivo: str = ""        # cpu | cuda
    motor: str = ""              # versões do faster-whisper/ctranslate2
    observacao: str = ""

    @property
    def concluido(self) -> bool:
        return self.status == OK


_NUMERICOS = {"duracao_s", "seg_transcricao", "seg_ocr", "velocidade"}
_INTEIROS = {"tamanho_bytes", "palavras", "capturas", "correcoes", "threads"}


def _assinatura(arquivo: Path) -> tuple[int, str]:
    st = arquivo.stat()
    return st.st_size, datetime.fromtimestamp(int(st.st_mtime)).isoformat()


class Registro:
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo
        self.linhas: dict[str, Linha] = {}
        self.aviso: str = ""
        self._ler()

    # ---------------------------------------------------------------- E/S
    def _ler(self) -> None:
        if not self.arquivo.is_file():
            return
        with open(self.arquivo, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter=";"):
                dados = {}
                for campo in fields(Linha):
                    v = row.get(campo.name, "")
                    if campo.name in _NUMERICOS:
                        dados[campo.name] = ler_numero_br(v)
                    elif campo.name in _INTEIROS:
                        dados[campo.name] = int(ler_numero_br(v))
                    else:
                        dados[campo.name] = v or campo.default
                if dados.get("caminho"):
                    self.linhas[dados["caminho"]] = Linha(**dados)

    def salvar(self) -> None:
        """Grava de forma atômica. Se o Excel estiver com o arquivo aberto (Windows trava),
        tenta de novo e, em último caso, grava uma cópia ao lado para não perder nada."""
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.arquivo.with_suffix(".tmp")
        nomes = [c.name for c in fields(Linha)]
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=nomes, delimiter=";")
            w.writeheader()
            for linha in sorted(self.linhas.values(), key=lambda l: l.caminho.lower()):
                d = asdict(linha)
                for k in _NUMERICOS:
                    d[k] = numero_br(d[k])
                w.writerow(d)
        for _ in range(5):
            try:
                tmp.replace(self.arquivo)
                self.aviso = ""
                return
            except PermissionError:
                time.sleep(1)
        copia = self.arquivo.with_name("registro_PENDENTE_feche_o_excel.csv")
        shutil.copyfile(tmp, copia)
        tmp.unlink(missing_ok=True)
        self.aviso = (f"O registro.csv parece aberto em outro programa (Excel?). "
                      f"Os dados foram salvos em {copia.name}; feche o arquivo e rode de novo.")

    # ---------------------------------------------------------------- sincronização
    def sincronizar(self, videos: list[tuple[str, Path]], caminho_md, mover_orfao) -> dict[str, int]:
        """Compara o que está na pasta com o registro.

        videos: [(caminho_relativo, caminho_absoluto)]
        caminho_md(rel) -> Path do .md esperado; mover_orfao(rel) move o .md para _orfaos.
        """
        contagem = {"novos": 0, "substituidos": 0, "orfaos": 0, "importados": 0}
        vistos = set()
        for rel, absoluto in videos:
            vistos.add(rel)
            tamanho, mod = _assinatura(absoluto)
            linha = self.linhas.get(rel)
            if linha is None or linha.status == ORFAO:
                linha = Linha(caminho=rel, tamanho_bytes=tamanho, modificado_em=mod)
                md = caminho_md(rel)
                if md.is_file():
                    # .md feito por versão antiga (sem registro): adota, não refaz
                    linha.status = OK
                    linha.observacao = "importado de execução anterior"
                    linha.palavras = len(md.read_text(encoding="utf-8", errors="ignore").split())
                    contagem["importados"] += 1
                else:
                    contagem["novos"] += 1
                self.linhas[rel] = linha
            elif (linha.tamanho_bytes, linha.modificado_em) != (tamanho, mod):
                if linha.status == OK:
                    linha.status = SUBSTITUIDO
                    linha.observacao = "arquivo mudou desde a última transcrição"
                    contagem["substituidos"] += 1
                linha.tamanho_bytes, linha.modificado_em = tamanho, mod
                linha.duracao_s = 0.0  # força medir de novo
        for rel, linha in self.linhas.items():
            if rel not in vistos and linha.status != ORFAO:
                mover_orfao(rel)
                linha.status = ORFAO
                linha.observacao = "vídeo removido da pasta; transcrição movida para _orfaos"
                contagem["orfaos"] += 1
        return contagem

    # ---------------------------------------------------------------- consultas
    def ativos(self) -> list[Linha]:
        return sorted((l for l in self.linhas.values() if l.status != ORFAO),
                      key=lambda l: l.caminho.lower())

    def pendentes(self) -> list[Linha]:
        return [l for l in self.ativos() if l.status != OK]

    def velocidade_medida(self, preset: str) -> float | None:
        """Mediana das últimas 5 velocidades reais para esta predefinição."""
        v = [l.velocidade for l in self.linhas.values()
             if l.status == OK and l.preset == preset and l.velocidade > 0]
        return statistics.median(v[-5:]) if v else None

    def ocr_por_hora_medido(self) -> float | None:
        """Segundos de OCR por hora de vídeo, medidos."""
        v = [l.seg_ocr / (l.duracao_s / 3600) for l in self.linhas.values()
             if l.status == OK and l.ocr == "sim" and l.seg_ocr > 0 and l.duracao_s > 0]
        return statistics.median(v[-5:]) if v else None
