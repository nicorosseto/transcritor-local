"""Orquestrador: varre a pasta, sincroniza o registro, estima e executa o lote.

A interface (terminal ou janela) só conversa com esta classe e recebe eventos.
Assim, a mesma lógica serve para a CLI e para o app desktop.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from . import consolidacao, correcoes, markdown, midia, ocr, preparacao
from .config import EXTENSOES_VIDEO, Config
from .estimativa import Estimativa, estimar
from .registro import ERRO, OK, Linha, Registro, assinatura_da_linha, chave_padrao
from .transcricao import Cancelado, carregar_modelo, dispositivo_disponivel, transcrever
from .util import ManterAcordado, PastaEmUso, Trava


@dataclass
class Item:
    rel: str
    caminho: Path
    linha: Linha

    @property
    def duracao(self) -> float:
        return self.linha.duracao_s

    @property
    def status(self) -> str:
        return self.linha.status


@dataclass
class Evento:
    tipo: str            # lote_inicio | etapa | progresso | video_fim | video_erro | aviso | lote_fim
    dados: dict = field(default_factory=dict)


def modelo_baixado(nome: str) -> bool:
    """Separado para os testes poderem simular (não há download no ambiente de teste)."""
    return preparacao.estado_modelo(nome).baixado


def versao_motor() -> str:
    try:
        from importlib.metadata import version
        return f"faster-whisper {version('faster-whisper')} / ctranslate2 {version('ctranslate2')}"
    except Exception:
        return "desconhecida"


def listar_videos(pasta: Path) -> list[tuple[str, Path]]:
    """Busca recursiva. Ignora pastas ocultas e que começam com '_' (ex.: _rascunhos)."""
    achados = []
    for arq in pasta.rglob("*"):
        if not arq.is_file() or arq.suffix.lower() not in EXTENSOES_VIDEO:
            continue
        partes = arq.relative_to(pasta).parts
        if any(p.startswith((".", "_")) for p in partes[:-1]):
            continue
        achados.append((Path(*partes).as_posix(), arq))
    return sorted(achados, key=lambda x: x[0].lower())


NOME_PROJETO = "projeto.json"


class PastasMudaram(Exception):
    """As pastas na tela não são as que foram lidas (achado X3)."""


class ProjetoDeOutraOrigem(Exception):
    """A pasta de saída pertence a outra pasta de vídeos (achado X7)."""

    def __init__(self, registrada: str, atual: Path):
        self.registrada, self.atual = registrada, atual
        super().__init__(
            f"Esta pasta de saída já guarda as transcrições de outra pasta de vídeos:\n{registrada}\n\n"
            f"A pasta escolhida agora é:\n{atual}")


def _mesma_pasta(a, b) -> bool:
    def norm(x):
        try:
            x = Path(x).resolve()
        except OSError:
            x = Path(x).absolute()
        return os.path.normcase(str(x))
    return norm(a) == norm(b)


class Projeto:
    def __init__(self, cfg: Config, aceitar_nova_origem: bool = False):
        self.cfg = cfg
        cfg.pasta_saida.mkdir(parents=True, exist_ok=True)
        self.legado = self._identificar(aceitar_nova_origem)
        self.registro = Registro(cfg.arquivo_registro)
        self.itens: list[Item] = []
        self.ultima_sincronizacao: dict[str, int] = {}
        self._modelo = None
        self._modelo_nome = None
        self.dispositivo = dispositivo_disponivel(cfg.dispositivo)

    # ---------------------------------------------------------------- identidade
    def _identificar(self, aceitar_nova_origem: bool) -> bool:
        """Grava/confere projeto.json. Retorna True se a saída é de versão antiga (sem identidade)."""
        arq = self.cfg.pasta_saida / NOME_PROJETO
        atual = str(self.cfg.pasta_videos.resolve())
        dados: dict = {}
        if arq.is_file():
            try:
                dados = json.loads(arq.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                dados = {}
        registrada = dados.get("pasta_videos")
        legado = registrada is None
        if registrada and not _mesma_pasta(registrada, atual) and not aceitar_nova_origem:
            raise ProjetoDeOutraOrigem(registrada, self.cfg.pasta_videos)
        if registrada != atual:
            if registrada:
                dados.setdefault("origens_anteriores", []).append(registrada)
            dados["pasta_videos"] = atual
            dados.setdefault("criado_em", datetime.now().strftime("%d/%m/%Y %H:%M"))
            tmp = arq.with_suffix(".tmp")
            tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, arq)
        return legado

    def preparar_rodada(self, da_tela: Config) -> Config:
        """Aplica as opções da tela à rodada, recusando se as pastas não forem as lidas."""
        if not (_mesma_pasta(da_tela.pasta_videos, self.cfg.pasta_videos)
                and _mesma_pasta(da_tela.pasta_saida, self.cfg.pasta_saida)):
            raise PastasMudaram("As pastas mudaram desde a última leitura. Clique em \"Ler pasta\" de novo.")
        self.cfg = dataclasses.replace(
            self.cfg, preset=da_tela.preset, ocr=da_tela.ocr, vocabulario=list(da_tela.vocabulario),
            idioma=da_tela.idioma, dispositivo=da_tela.dispositivo, threads=da_tela.threads)
        return self.cfg

    # ---------------------------------------------------------------- caminhos
    def _chave(self, rel: str) -> str:
        linha = self.registro.linhas.get(rel)
        return linha.saida if linha is not None and linha.saida else chave_padrao(rel)

    def caminho_md(self, rel: str) -> Path:
        return self.cfg.pasta_md / (self._chave(rel) + ".md")

    def caminho_audio(self, rel: str) -> Path:
        return self.cfg.pasta_audio / (self._chave(rel) + ".mp3")

    def pasta_capturas(self, rel: str) -> Path:
        return self.cfg.pasta_capturas / self._chave(rel)

    def _mover_orfao(self, rel: str) -> None:
        md = self.caminho_md(rel)
        if md.is_file():
            destino = self.cfg.pasta_orfaos / (self._chave(rel) + ".md")
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(md), str(destino))

    # ---------------------------------------------------------------- varredura
    def escanear(self, ao_medir: Callable[[int, int], None] | None = None) -> list[Item]:
        videos = listar_videos(self.cfg.pasta_videos)
        self.ultima_sincronizacao = self.registro.sincronizar(
            videos, self.caminho_md, self._mover_orfao, permitir_importar=self.legado)
        self.itens = []
        for n, (rel, abs_) in enumerate(videos, 1):
            linha = self.registro.linhas[rel]
            if linha.duracao_s <= 0:
                linha.duracao_s = midia.duracao(abs_)
            if ao_medir:
                ao_medir(n, len(videos))
            self.itens.append(Item(rel, abs_, linha))
        self.registro.salvar()
        self.consolidar()  # a base reflete a pasta já na leitura (achado X11)
        return self.itens

    def estimar(self, itens: list[Item], com_ocr: bool | None = None) -> Estimativa:
        return estimar([i.duracao for i in itens], self.registro, self.cfg.preset,
                       self.dispositivo, self.cfg.ocr if com_ocr is None else com_ocr)

    def pendentes(self) -> list[Item]:
        return [i for i in self.itens if i.status != OK]

    # ---------------------------------------------------------------- execução
    def _garantir_modelo(self, emitir, cancelar=None):
        if self._modelo is not None and self._modelo_nome == self.cfg.modelo:
            return
        if not modelo_baixado(self.cfg.modelo):
            emitir("etapa", codigo="modelo", texto=f"Baixando o modelo de transcrição ({self.cfg.modelo})...")
            preparacao.baixar_modelo(self.cfg.modelo,
                                     lambda feito, total: emitir("download", feito=feito, total=total),
                                     cancelar)
        emitir("etapa", codigo="modelo", texto=f"Carregando o modelo {self.cfg.modelo}...")
        self._modelo, self.dispositivo = carregar_modelo(
            self.cfg.modelo, self.cfg.dispositivo, self.cfg.threads_efetivas)
        self._modelo_nome = self.cfg.modelo
        emitir("etapa", codigo="modelo", texto=f"Modelo pronto, rodando em: {self.dispositivo.upper()}")

    def _preparar_ocr(self, emitir) -> ocr.EstadoOCR | None:
        if not self.cfg.ocr:
            return None
        estado = ocr.verificar()
        if not estado.disponivel:
            emitir("aviso", texto=estado.mensagem + " Seguindo SEM leitura de tela.")
            return None
        if not estado.tem_portugues:
            emitir("etapa", codigo="modelo", texto="Baixando pacote de português do Tesseract (~2 MB)...")
            try:
                ocr.baixar_portugues()
                estado = ocr.verificar()
            except Exception as e:
                emitir("aviso", texto=f"Não consegui baixar o português do Tesseract ({e}). "
                                      "Seguindo SEM leitura de tela.")
                return None
        return estado

    def executar(self, itens: list[Item], ao_evento: Callable[[Evento], None],
                 parar_apos_atual: threading.Event | None = None,
                 cancelar: threading.Event | None = None) -> dict:
        self._resumo = {"ok": 0, "erro": 0, "cancelado": False, "parado": False}
        self._fim_emitido = False

        def repassar(ev: Evento):
            if ev.tipo == "lote_fim":
                self._fim_emitido = True
            ao_evento(ev)
        try:
            with Trava(self.cfg.pasta_saida), ManterAcordado():
                return self._executar(itens, repassar, parar_apos_atual, cancelar)
        except PastaEmUso as e:
            ao_evento(Evento("aviso", {"texto": str(e)}))
            resumo = dict(self._resumo, fatal=str(e))
        except Exception as e:  # nunca terminar em silêncio nem como "sucesso" (achado X16)
            resumo = dict(self._resumo, fatal=f"{type(e).__name__}: {e}")
            ao_evento(Evento("aviso", {"texto": f"Erro inesperado: {resumo['fatal']}"}))
        if not self._fim_emitido:
            ao_evento(Evento("lote_fim", resumo))
        return resumo

    def _executar(self, itens, ao_evento, parar_apos_atual, cancelar) -> dict:
        parar_apos_atual = parar_apos_atual or threading.Event()
        cancelar = cancelar or threading.Event()

        def emitir(tipo, **dados):
            ao_evento(Evento(tipo, dados))

        resumo = self._resumo
        estimativa_lote = self.estimar(itens)
        emitir("lote_inicio", total=len(itens), segundos_previstos=estimativa_lote.total,
               duracao_total=sum(i.duracao for i in itens))
        estado_ocr = self._preparar_ocr(emitir)
        regras, aviso_corr = correcoes.carregar(self.cfg.pasta_saida)
        if aviso_corr:
            emitir("aviso", texto=aviso_corr)
        compiladas = correcoes.compilar(regras)
        try:
            self._garantir_modelo(emitir, cancelar)
        except Exception as e:
            dica = ""
            texto = str(e).lower()
            if any(x in texto for x in ("403", "407", "proxy", "connection", "timed out", "resolve", "ssl")):
                dica = (" Parece problema de internet: o modelo precisa ser baixado UMA vez (até ~1,6 GB). "
                        "Redes corporativas (com proxy/firewall) costumam bloquear esse download; "
                        "tente em outra rede. Depois do primeiro download, funciona offline.")
            emitir("aviso", texto=f"Falha ao carregar o modelo: {e}.{dica}")
            resumo["erro"] = len(itens)
            resumo["fatal"] = f"Falha ao carregar o modelo: {e}"
            emitir("lote_fim", **resumo)
            return resumo

        video_restante = sum(i.duracao for i in itens)
        gasto_lote, feito_lote = 0.0, 0.0
        for n, item in enumerate(itens, 1):
            if parar_apos_atual.is_set():
                resumo["parado"] = True
                break
            emitir("video_inicio", indice=n, total=len(itens), rel=item.rel, duracao=item.duracao)
            t0 = time.perf_counter()
            try:
                audio = self.caminho_audio(item.rel)
                emitir("etapa", codigo="audio", texto="Extraindo o áudio...")
                assinatura = assinatura_da_linha(item.linha)
                if audio.exists() and item.linha.audio_de != assinatura:
                    audio.unlink()  # áudio de uma versão anterior do vídeo (achado X1)
                midia.extrair_audio(item.caminho, audio)
                item.linha.audio_de = assinatura
                emitir("etapa", codigo="transcricao", texto="Transcrevendo a fala...")
                array = midia.carregar_audio(audio)
                t_trans = time.perf_counter()

                def progresso(pos, total, _t=t_trans):
                    gasto = time.perf_counter() - _t
                    dados = {"pos": pos, "total": total, "rel": item.rel}
                    if gasto >= 30 and pos > 0:
                        vel = pos / gasto
                        vel_lote = (feito_lote + pos) / (gasto_lote + gasto)
                        falta_lote = max(0.0, video_restante - pos) / vel_lote
                        if estado_ocr is not None:
                            falta_lote *= 1 + (estimativa_lote.segundos_ocr /
                                               max(estimativa_lote.segundos_transcricao, 1))
                        dados.update(velocidade=vel, falta_video=(total - pos) / vel,
                                     falta_lote=falta_lote,
                                     termino=(datetime.now() + timedelta(seconds=falta_lote)))
                    emitir("progresso", **dados)

                paragrafos, dur = transcrever(
                    self._modelo, array, idioma=self.cfg.idioma, beam_size=self.cfg.beam_size,
                    vocabulario=self.cfg.vocabulario,
                    segundos_por_paragrafo=self.cfg.segundos_por_paragrafo,
                    ao_progredir=progresso, cancelar=cancelar)
                del array
                seg_trans = time.perf_counter() - t_trans
                trocas = 0
                for p in paragrafos:
                    p.texto, n_trocas = correcoes.aplicar(p.texto, compiladas)
                    trocas += n_trocas

                telas: list[markdown.Tela] = []
                seg_ocr = 0.0
                if estado_ocr is not None:
                    t_ocr = time.perf_counter()
                    telas = self._ler_telas(item, estado_ocr, emitir, cancelar)
                    seg_ocr = time.perf_counter() - t_ocr

                emitir("etapa", codigo="salvar", texto="Salvando a transcrição...")
                destino = self.caminho_md(item.rel)
                conteudo, palavras = markdown.montar(
                    titulo=Path(item.rel).stem, origem=item.rel, duracao=dur,
                    modelo=self.cfg.modelo, preset=self.cfg.preset,
                    paragrafos=paragrafos, telas=telas, destino=destino, correcoes=trocas)
                markdown.salvar(conteudo, destino)

                l = item.linha
                l.status, l.preset = OK, self.cfg.preset
                l.ocr = "sim" if estado_ocr is not None else "nao"
                l.duracao_s = dur or l.duracao_s
                l.transcrito_em = datetime.now().strftime("%d/%m/%Y %H:%M")
                l.seg_transcricao, l.seg_ocr = round(seg_trans, 1), round(seg_ocr, 1)
                l.velocidade = round(dur / seg_trans, 2) if seg_trans > 0 else 0.0
                l.palavras, l.capturas = palavras, len(telas)
                l.correcoes = trocas
                l.threads, l.dispositivo, l.motor = self.cfg.threads_efetivas, self.dispositivo, versao_motor()
                l.observacao = ""
                resumo["ok"] += 1
                emitir("video_fim", rel=item.rel, palavras=palavras, segundos=time.perf_counter() - t0,
                       velocidade=l.velocidade, telas=len(telas), correcoes=trocas)
                feito_lote += dur
                gasto_lote += seg_trans
            except Cancelado:
                resumo["cancelado"] = True
                emitir("aviso", texto=f"Cancelado no meio de {item.rel}. Este vídeo será refeito "
                                      "na próxima execução.")
                break
            except Exception as e:  # um vídeo ruim não derruba o lote
                item.linha.status = ERRO
                item.linha.observacao = str(e)[:300]
                resumo["erro"] += 1
                emitir("video_erro", rel=item.rel, erro=str(e))
            finally:
                video_restante -= item.duracao
                self.registro.salvar()
                if self.registro.aviso:
                    emitir("aviso", texto=self.registro.aviso)

        self.consolidar()
        emitir("lote_fim", **resumo)
        return resumo

    def _ler_telas(self, item: Item, estado: ocr.EstadoOCR, emitir, cancelar) -> list[markdown.Tela]:
        emitir("etapa", codigo="telas", texto="Procurando trocas de tela...")
        capturas = midia.extrair_capturas(item.caminho, self.pasta_capturas(item.rel), cancelar=cancelar)
        telas: list[markdown.Tela] = []
        ultimo = ""
        for i, (t, img) in enumerate(capturas, 1):
            if cancelar.is_set():
                raise Cancelado()
            emitir("progresso_telas", feito=i, total=len(capturas))
            texto = ocr.limpar(ocr.ler_imagem(estado, img))
            if not ocr.e_util(texto) or ocr.parecido(texto, ultimo):
                continue
            telas.append(markdown.Tela(t, texto, img))
            ultimo = texto
        return telas

    def consolidar(self) -> list[Path]:
        feitos = [(l.caminho, self.caminho_md(l.caminho)) for l in self.registro.ativos() if l.status == OK]
        return consolidacao.consolidar(feitos, self.cfg.pasta_base, self.cfg.max_palavras_por_base)
