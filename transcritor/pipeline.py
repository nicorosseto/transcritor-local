"""Orquestrador: varre a pasta, sincroniza o registro, estima e executa o lote.

A interface (terminal ou janela) só conversa com esta classe e recebe eventos.
Assim, a mesma lógica serve para a CLI e para o app desktop.
"""

from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from . import consolidacao, markdown, midia, ocr
from .config import EXTENSOES_VIDEO, Config
from .estimativa import Estimativa, estimar
from .registro import ERRO, OK, Linha, Registro
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


class Projeto:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        cfg.pasta_saida.mkdir(parents=True, exist_ok=True)
        self.registro = Registro(cfg.arquivo_registro)
        self.itens: list[Item] = []
        self.ultima_sincronizacao: dict[str, int] = {}
        self._modelo = None
        self._modelo_nome = None
        self.dispositivo = dispositivo_disponivel(cfg.dispositivo)

    # ---------------------------------------------------------------- caminhos
    def caminho_md(self, rel: str) -> Path:
        return (self.cfg.pasta_md / rel).with_suffix(".md")

    def caminho_audio(self, rel: str) -> Path:
        return (self.cfg.pasta_audio / rel).with_suffix(".mp3")

    def pasta_capturas(self, rel: str) -> Path:
        return (self.cfg.pasta_capturas / rel).with_suffix("")

    def _mover_orfao(self, rel: str) -> None:
        md = self.caminho_md(rel)
        if md.is_file():
            destino = (self.cfg.pasta_orfaos / rel).with_suffix(".md")
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(md), str(destino))

    # ---------------------------------------------------------------- varredura
    def escanear(self, ao_medir: Callable[[int, int], None] | None = None) -> list[Item]:
        videos = listar_videos(self.cfg.pasta_videos)
        self.ultima_sincronizacao = self.registro.sincronizar(videos, self.caminho_md, self._mover_orfao)
        self.itens = []
        for n, (rel, abs_) in enumerate(videos, 1):
            linha = self.registro.linhas[rel]
            if linha.duracao_s <= 0:
                linha.duracao_s = midia.duracao(abs_)
            if ao_medir:
                ao_medir(n, len(videos))
            self.itens.append(Item(rel, abs_, linha))
        self.registro.salvar()
        return self.itens

    def estimar(self, itens: list[Item], com_ocr: bool | None = None) -> Estimativa:
        return estimar([i.duracao for i in itens], self.registro, self.cfg.preset,
                       self.dispositivo, self.cfg.ocr if com_ocr is None else com_ocr)

    def pendentes(self) -> list[Item]:
        return [i for i in self.itens if i.status != OK]

    # ---------------------------------------------------------------- execução
    def _garantir_modelo(self, emitir):
        if self._modelo is not None and self._modelo_nome == self.cfg.modelo:
            return
        emitir("etapa", texto=f"Carregando modelo {self.cfg.modelo} "
                              "(na primeira vez ele é baixado: até ~1,6 GB, pode demorar)...")
        self._modelo, self.dispositivo = carregar_modelo(
            self.cfg.modelo, self.cfg.dispositivo, self.cfg.threads_efetivas)
        self._modelo_nome = self.cfg.modelo
        emitir("etapa", texto=f"Modelo pronto, rodando em: {self.dispositivo.upper()}")

    def _preparar_ocr(self, emitir) -> ocr.EstadoOCR | None:
        if not self.cfg.ocr:
            return None
        estado = ocr.verificar()
        if not estado.disponivel:
            emitir("aviso", texto=estado.mensagem + " Seguindo SEM leitura de tela.")
            return None
        if not estado.tem_portugues:
            emitir("etapa", texto="Baixando pacote de português do Tesseract (~2 MB)...")
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
        try:
            with Trava(self.cfg.pasta_saida), ManterAcordado():
                return self._executar(itens, ao_evento, parar_apos_atual, cancelar)
        except PastaEmUso as e:
            ao_evento(Evento("aviso", {"texto": str(e)}))
            resumo = {"ok": 0, "erro": 0, "cancelado": False, "parado": False}
            ao_evento(Evento("lote_fim", resumo))
            return resumo

    def _executar(self, itens, ao_evento, parar_apos_atual, cancelar) -> dict:
        parar_apos_atual = parar_apos_atual or threading.Event()
        cancelar = cancelar or threading.Event()

        def emitir(tipo, **dados):
            ao_evento(Evento(tipo, dados))

        resumo = {"ok": 0, "erro": 0, "cancelado": False, "parado": False}
        estimativa_lote = self.estimar(itens)
        emitir("lote_inicio", total=len(itens), segundos_previstos=estimativa_lote.total,
               duracao_total=sum(i.duracao for i in itens))
        estado_ocr = self._preparar_ocr(emitir)
        try:
            self._garantir_modelo(emitir)
        except Exception as e:
            dica = ""
            texto = str(e).lower()
            if any(x in texto for x in ("403", "407", "proxy", "connection", "timed out", "resolve", "ssl")):
                dica = (" Parece problema de internet: o modelo precisa ser baixado UMA vez (até ~1,6 GB). "
                        "Redes corporativas (com proxy/firewall) costumam bloquear esse download; "
                        "tente em outra rede. Depois do primeiro download, funciona offline.")
            emitir("aviso", texto=f"Falha ao carregar o modelo: {e}.{dica}")
            resumo["erro"] = len(itens)
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
                emitir("etapa", texto="Extraindo áudio...")
                midia.extrair_audio(item.caminho, audio)
                emitir("etapa", texto="Transcrevendo...")
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

                telas: list[markdown.Tela] = []
                seg_ocr = 0.0
                if estado_ocr is not None:
                    t_ocr = time.perf_counter()
                    telas = self._ler_telas(item, estado_ocr, emitir, cancelar)
                    seg_ocr = time.perf_counter() - t_ocr

                destino = self.caminho_md(item.rel)
                conteudo, palavras = markdown.montar(
                    titulo=Path(item.rel).stem, origem=item.rel, duracao=dur,
                    modelo=self.cfg.modelo, preset=self.cfg.preset,
                    paragrafos=paragrafos, telas=telas, destino=destino)
                markdown.salvar(conteudo, destino)

                l = item.linha
                l.status, l.preset = OK, self.cfg.preset
                l.ocr = "sim" if estado_ocr is not None else "nao"
                l.duracao_s = dur or l.duracao_s
                l.transcrito_em = datetime.now().strftime("%d/%m/%Y %H:%M")
                l.seg_transcricao, l.seg_ocr = round(seg_trans, 1), round(seg_ocr, 1)
                l.velocidade = round(dur / seg_trans, 2) if seg_trans > 0 else 0.0
                l.palavras, l.capturas = palavras, len(telas)
                l.observacao = ""
                resumo["ok"] += 1
                emitir("video_fim", rel=item.rel, palavras=palavras, segundos=time.perf_counter() - t0,
                       velocidade=l.velocidade, telas=len(telas))
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
        emitir("etapa", texto="Capturando mudanças de tela...")
        capturas = midia.extrair_capturas(item.caminho, self.pasta_capturas(item.rel), cancelar=cancelar)
        telas: list[markdown.Tela] = []
        ultimo = ""
        for i, (t, img) in enumerate(capturas, 1):
            if cancelar.is_set():
                raise Cancelado()
            emitir("etapa", texto=f"Lendo texto da tela {i}/{len(capturas)}...")
            texto = ocr.limpar(ocr.ler_imagem(estado, img))
            if not ocr.e_util(texto) or ocr.parecido(texto, ultimo):
                continue
            telas.append(markdown.Tela(t, texto, img))
            ultimo = texto
        return telas

    def consolidar(self) -> list[Path]:
        feitos = [(l.caminho, self.caminho_md(l.caminho)) for l in self.registro.ativos() if l.status == OK]
        return consolidacao.consolidar(feitos, self.cfg.pasta_base, self.cfg.max_palavras_por_base)
