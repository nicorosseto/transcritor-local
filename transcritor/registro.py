"""registro.csv: memória do que já foi feito, e base das estimativas.

Um vídeo é identificado por caminho relativo + tamanho + data de modificação.
Isso permite detectar: vídeo novo, vídeo substituído (mesmo nome, outro conteúdo),
vídeo excluído (vira "órfão"), transcrição apagada (volta a pendente) e vídeo com erro.

Cada vídeo tem uma "chave de saída" fixa (coluna `saida`), atribuída uma vez: é o nome
usado no .md, no .mp3 e na pasta de capturas. Assim `aula.mp4` e `aula.mkv` na mesma
pasta não colidem, e o nome não muda se um vídeo "irmão" aparecer depois (achado X2).

O CSV usa ';' e vírgula decimal para abrir direto no Excel/Power BI em português.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

from .markdown import palavras_de_fala
from .util import gravar_atomico, ler_numero_br, numero_br

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
    palavras: int = 0            # só a fala (achado N2)
    palavras_tela: int = 0       # texto lido da tela (OCR)
    capturas: int = 0
    saida: str = ""              # chave de saída fixa (sem extensão), ex.: "Mod 1/aula"
    audio_de: str = ""           # assinatura do vídeo quando o .mp3 foi extraído (achado X1)
    correcoes: int = 0           # trocas feitas pela lista correcoes.json
    threads: int = 0             # diagnóstico de desempenho
    dispositivo: str = ""        # cpu | cuda
    motor: str = ""              # versões do faster-whisper/ctranslate2
    observacao: str = ""

    @property
    def concluido(self) -> bool:
        return self.status == OK


MIN_APRENDER_S = 180.0   # vídeos mais curtos não entram nas estimativas (achado N11)

_NUMERICOS = {"duracao_s", "seg_transcricao", "seg_ocr", "velocidade"}
_INTEIROS = {"tamanho_bytes", "palavras", "palavras_tela", "capturas", "correcoes", "threads"}


def _assinatura(arquivo: Path) -> tuple[int, str]:
    st = arquivo.stat()
    return st.st_size, datetime.fromtimestamp(int(st.st_mtime)).isoformat()


def assinatura_da_linha(linha: Linha) -> str:
    return f"{linha.tamanho_bytes}|{linha.modificado_em}"


def chave_padrao(rel: str) -> str:
    """'Mod 1/aula.mp4' -> 'Mod 1/aula' (o que versões anteriores usavam)."""
    return str(Path(rel).with_suffix("").as_posix())


class Registro:
    NOME_PENDENTE = "registro_PENDENTE_feche_o_excel.csv"
    TENTATIVAS = 5

    def __init__(self, arquivo: Path):
        self.arquivo = arquivo
        self.linhas: dict[str, Linha] = {}
        self.aviso: str = ""
        self.pendente = arquivo.with_name(self.NOME_PENDENTE)
        self._ler(self._origem())

    # ---------------------------------------------------------------- E/S
    def _origem(self) -> Path:
        """Se uma gravação anterior caiu na cópia de emergência (Excel aberto), ela é o estado
        mais novo: recupera dela (achado X15). A cópia some no próximo salvamento bem-sucedido."""
        if self.pendente.is_file() and (not self.arquivo.is_file() or
                                        self.pendente.stat().st_mtime >= self.arquivo.stat().st_mtime):
            self.aviso = (f"Recuperado o registro de {self.pendente.name} (gravado quando o registro.csv "
                          "estava aberto em outro programa).")
            return self.pendente
        return self.arquivo

    def _ler(self, origem: Path) -> None:
        if not origem.is_file():
            return
        with open(origem, encoding="utf-8-sig", newline="") as f:
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
                    linha = Linha(**dados)
                    if not linha.saida:  # registro de versão anterior
                        linha.saida = chave_padrao(linha.caminho)
                    self.linhas[linha.caminho] = linha

    def _texto_csv(self) -> str:
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=[c.name for c in fields(Linha)], delimiter=";")
        w.writeheader()
        for linha in sorted(self.linhas.values(), key=lambda l: l.caminho.lower()):
            d = asdict(linha)
            for k in _NUMERICOS:
                d[k] = numero_br(d[k])
            w.writerow(d)
        return buf.getvalue()

    def salvar(self) -> None:
        """Grava de forma atômica, com temporário de nome único e novas tentativas (achado N20).
        Se o Excel estiver com o arquivo aberto (Windows trava), grava uma cópia ao lado para não
        perder nada (achado X15). Outros erros de disco sobem para quem chamou decidir."""
        texto = self._texto_csv()

        def escrever(caminho: Path) -> None:
            with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
                f.write(texto)
        try:
            gravar_atomico(self.arquivo, escrever, tentativas=self.TENTATIVAS)
        except PermissionError:
            gravar_atomico(self.pendente, escrever, tentativas=2)
            self.aviso = (f"O registro.csv parece aberto em outro programa (Excel?). "
                          f"Os dados foram salvos em {self.pendente.name}; feche o arquivo e rode de novo.")
            return
        self.aviso = ""
        self.pendente.unlink(missing_ok=True)  # já incorporada

    # ---------------------------------------------------------------- sincronização
    def _chave_livre(self, rel: str) -> str:
        em_uso = {l.saida.lower() for c, l in self.linhas.items() if c != rel and l.status != ORFAO}
        base = chave_padrao(rel)
        if base.lower() not in em_uso:
            return base
        ext = Path(rel).suffix.lstrip(".").lower() or "video"
        candidato, n = f"{base} [{ext}]", 2
        while candidato.lower() in em_uso:
            candidato, n = f"{base} [{ext} {n}]", n + 1
        return candidato

    def sincronizar(self, videos: list[tuple[str, Path]], caminho_md, mover_orfao,
                    permitir_importar: bool = True) -> dict[str, int]:
        """Compara o que está na pasta com o registro.

        videos: [(caminho_relativo, caminho_absoluto)]
        caminho_md(rel) -> Path do .md esperado; mover_orfao(rel) move o .md para _orfaos.
        permitir_importar: adotar .md já existente de um vídeo novo (só para saídas criadas por
        versões antigas, sem identidade de projeto; ver achado X7).
        """
        contagem = {"novos": 0, "substituidos": 0, "orfaos": 0, "importados": 0, "ausentes": 0}
        vistos = set()
        for rel, absoluto in videos:
            vistos.add(rel)
            tamanho, mod = _assinatura(absoluto)
            linha = self.linhas.get(rel)
            if linha is None or linha.status == ORFAO:
                linha = Linha(caminho=rel, tamanho_bytes=tamanho, modificado_em=mod)
                self.linhas[rel] = linha
                linha.saida = self._chave_livre(rel)
                md = caminho_md(rel)
                if permitir_importar and md.is_file():
                    # .md feito por versão antiga (sem registro): adota, não refaz
                    linha.status = OK
                    linha.observacao = "importado de execução anterior"
                    linha.palavras = (palavras_de_fala(texto := md.read_text(encoding="utf-8", errors="ignore"))
                                      or len(texto.split()))
                    contagem["importados"] += 1
                else:
                    contagem["novos"] += 1
            elif (linha.tamanho_bytes, linha.modificado_em) != (tamanho, mod):
                if linha.status == OK:
                    linha.status = SUBSTITUIDO
                    linha.observacao = "arquivo mudou desde a última transcrição"
                    contagem["substituidos"] += 1
                linha.tamanho_bytes, linha.modificado_em = tamanho, mod
                linha.duracao_s = 0.0  # força medir de novo
            elif linha.status == OK and not caminho_md(rel).is_file():
                linha.status = PENDENTE
                linha.observacao = "transcrição não encontrada na pasta de saída; será refeita"
                contagem["ausentes"] += 1
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

    def _para_aprender(self, preset: str | None = None) -> list[Linha]:
        """Últimos 5 vídeos concluídos que servem de amostra: com pelo menos MIN_APRENDER_S de duração.

        Vídeo curto tem tempo fixo de partida (1,2x num de 42 s contra 1,7x num de 36 min) e envenenava
        a estimativa (achado N11)."""
        v = [l for l in self.linhas.values()
             if l.status == OK and l.duracao_s >= MIN_APRENDER_S and (preset is None or l.preset == preset)]
        return v[-5:]

    def velocidade_medida(self, preset: str) -> float | None:
        """Velocidade ponderada pela duração dos últimos 5 vídeos longos (minutos de vídeo por minuto real)."""
        v = [l for l in self._para_aprender(preset) if l.velocidade > 0]
        if not v:
            return None
        return sum(l.duracao_s for l in v) / sum(l.duracao_s / l.velocidade for l in v)

    def ocr_por_hora_medido(self) -> float | None:
        """Segundos de OCR por hora de vídeo, medidos (ponderado pela duração)."""
        v = [l for l in self._para_aprender() if l.ocr == "sim" and l.seg_ocr > 0]
        if not v:
            return None
        return sum(l.seg_ocr for l in v) / (sum(l.duracao_s for l in v) / 3600)
