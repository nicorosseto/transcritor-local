"""Interface de terminal: diagnóstico, escolhas obrigatórias, confirmação e progresso."""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

from . import __version__
from .config import PRESETS, Config, vocabulario_de_texto
from .hardware import AVISO, ERRO, OK, diagnosticar
from .pipeline import Evento, Projeto, ProjetoDeOutraOrigem
from .resultado import codigo_saida, resumo_final
from .util import PastaEmUso, hhmmss

ICONE = {OK: "✅", AVISO: "⚠️ ", ERRO: "❌", "info": "ℹ️ "}


def perguntar(texto: str, validar, padrao: str | None = None):
    while True:
        try:
            resp = input(f"{texto}{f' [{padrao}]' if padrao else ''}: ").strip()
        except EOFError:
            sys.exit("\nEntrada encerrada. Nada foi feito.")
        if not resp and padrao is not None:
            resp = padrao
        try:
            return validar(resp)
        except ValueError as e:
            print(f"  ↳ {e}")


def _inteiro_entre(minimo: int, maximo: int):
    def v(s):
        if not s.isdigit() or not (minimo <= int(s) <= maximo):
            raise ValueError(f"Digite um número de {minimo} a {maximo}.")
        return int(s)
    return v


def _sim_nao(s):
    s = s.lower()
    if s in ("s", "sim", "y"):
        return True
    if s in ("n", "nao", "não", "no"):
        return False
    raise ValueError("Responda s ou n.")


def imprimir_diagnostico(cfg: Config) -> bool:
    d = diagnosticar(cfg.pasta_saida)
    print("\n=== Verificação do seu PC ===")
    for i in d.itens:
        print(f" {ICONE.get(i.nivel, '  ')} {i.nome}: {i.valor}")
        print(f"      {i.explicacao}")
    return d.pode_rodar


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="transcritor", description="Transcreve vídeos para Markdown, localmente.",
        epilog="Códigos de saída: 0 = concluído · 1 = falha · 2 = parcial (algum erro) · "
               "3 = parado/cancelado · 130 = Ctrl+C")
    p.add_argument("--videos", type=Path, default=Path("videos"), help="pasta com os vídeos (padrão: ./videos)")
    p.add_argument("--saida", type=Path, default=Path("saida"), help="pasta de resultados (padrão: ./saida)")
    p.add_argument("--pasta-movida", action="store_true",
                   help="confirma que a pasta de vídeos foi movida/renomeada e a saída é a mesma")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if not args.videos.exists():
        args.videos.mkdir(parents=True)
        print(f"Criei a pasta {args.videos.resolve()}. Coloque os vídeos nela (pode usar subpastas) e rode de novo.")
        return 0

    cfg = Config.carregar(args.saida.resolve(), args.videos.resolve())
    erros = cfg.validar()
    if erros:
        print("\n".join(f"❌ {e}" for e in erros))
        return 1

    print(f"Transcritor Local {__version__}")
    if not imprimir_diagnostico(cfg):
        print("\n❌ Corrija os itens marcados com ❌ antes de continuar.")
        return 1

    try:
        projeto = Projeto(cfg, aceitar_nova_origem=args.pasta_movida)
    except ProjetoDeOutraOrigem as e:
        print(f"\n❌ {e}\n\nUse outra pasta em --saida. Se você só moveu a pasta de vídeos, "
              "rode de novo com --pasta-movida.")
        return 1
    print("\nLendo a pasta de vídeos...")
    try:
        itens = projeto.escanear(lambda n, t: print(f"\r  medindo durações {n}/{t}", end="", flush=True))
    except PastaEmUso as e:
        print(f"\n❌ {e}")
        return 1
    print()
    s = projeto.ultima_sincronizacao
    pend = projeto.pendentes()
    print(f"\n{len(itens)} vídeo(s) | {len(itens) - len(pend)} prontos | {len(pend)} pendentes "
          f"| {hhmmss(sum(i.duracao for i in pend))} de vídeo pendente")
    for chave, rotulo in (("novos", "novos"), ("substituidos", "substituídos (serão refeitos)"),
                          ("orfaos", "removidos da pasta (transcrição movida para _orfaos)"),
                          ("importados", "já transcritos por versão anterior (aproveitados)")):
        if s.get(chave):
            print(f"  • {s[chave]} {rotulo}")
    if not pend:
        print("\nNada pendente. Base consolidada atualizada.")
        return 0

    # ---- escolhas obrigatórias
    print("\nQualidade:")
    chaves = list(PRESETS)
    for n, k in enumerate(chaves, 1):
        marca = " (atual)" if k == cfg.preset else ""
        print(f"  {n} = {PRESETS[k]['rotulo']}{marca}: {PRESETS[k]['descricao']}")
    cfg.preset = chaves[perguntar("Escolha", _inteiro_entre(1, len(chaves)),
                                  str(chaves.index(cfg.preset) + 1)) - 1]

    cfg.ocr = perguntar("Ler também o TEXTO que aparece na tela (slides, código)? s/n",
                        _sim_nao, "s" if cfg.ocr else "n")
    if cfg.ocr:
        from . import ocr as _ocr
        est = _ocr.verificar()
        if not est.disponivel:
            print(f"  ⚠️  {est.mensagem}")
            if not perguntar("  Continuar SEM ler o texto da tela? s/n", _sim_nao):
                print("Nada foi feito. Instale o Tesseract e rode de novo.")
                return 0
            cfg.ocr = False

    atual = ", ".join(cfg.vocabulario)
    print("\nVocabulário de dicas (nomes e termos que o Whisper costuma errar), separados por vírgula.")
    print("  Exemplo: Power BI, DAX, ChatGPT, Claude, hook")
    resp = input(f"  Vocabulário{f' [{atual}]' if atual else ''} (Enter mantém): ").strip()
    if resp:
        cfg.vocabulario = vocabulario_de_texto(resp)

    print("\nQuantos vídeos processar NESTA execução? (obrigatório)")
    opcoes = sorted({1, 3, 5, len(pend)} - {0})
    for q in [0] + [o for o in opcoes if o < len(pend)]:
        alvo = pend if q == 0 else pend[:q]
        e = projeto.estimar(alvo)
        rot = f"TODOS ({len(pend)})" if q == 0 else ("só o próximo" if q == 1 else f"os próximos {q}")
        print(f"  {q} = {rot:<14} ≈ {hhmmss(e.total)}")
    nota = "medida neste PC" if projeto.estimar(pend[:1]).medida else "estimativa inicial, ainda sem medição"
    print(f"  (velocidade usada: {projeto.estimar(pend[:1]).velocidade:.1f}x — {nota})")
    q = perguntar("Quantidade (0 = todos)", _inteiro_entre(0, len(pend)))
    selecionados = pend if q == 0 else pend[:q]
    e = projeto.estimar(selecionados)
    if not perguntar(f"\nProcessar {len(selecionados)} vídeo(s), ≈ {hhmmss(e.total)}. Confirmar? s/n", _sim_nao):
        print("Nada foi feito.")
        return 0
    cfg.salvar()

    # ---- execução
    print("\nDica: Ctrl+C cancela; o vídeo em andamento será refeito na próxima execução.\n")

    def ao_evento(ev: Evento):
        d = ev.dados
        if ev.tipo == "video_inicio":
            print(f"\n[{d['indice']}/{d['total']}] {d['rel']}  ({hhmmss(d['duracao'])})")
        elif ev.tipo == "etapa":
            print(f"    {d['texto']}".ljust(110))
        elif ev.tipo == "download":
            print(f"\r    baixando modelo: {d['feito'] / 1e6:,.0f} de ~{d['total'] / 1e6:,.0f} MB".replace(",", ".")
                  .ljust(60), end="", flush=True)
        elif ev.tipo == "progresso_telas":
            print(f"\r    lendo telas: {d['feito']}/{d['total']}".ljust(60), end="", flush=True)
        elif ev.tipo == "progresso":
            linha = f"\r    {hhmmss(d['pos'])} / {hhmmss(d['total'])}"
            if "velocidade" in d:
                linha += (f" | {d['velocidade']:.1f}x | este vídeo: falta ~{hhmmss(d['falta_video'])}"
                          f" | lote: ~{hhmmss(d['falta_lote'])} (fim ~{d['termino']:%d/%m %H:%M})")
            print(linha.ljust(120), end="", flush=True)
        elif ev.tipo == "video_fim":
            print(f"\n    ✅ {d['palavras']} palavras em {hhmmss(d['segundos'])} "
                  f"(velocidade {d['velocidade']:.1f}x, {d['telas']} trecho(s) de tela, "
                  f"{d.get('correcoes', 0)} correção(ões))")
        elif ev.tipo == "video_erro":
            print(f"\n    ❌ FALHOU: {d['erro']}")
        elif ev.tipo == "aviso":
            print(f"\n    ⚠️  {d['texto']}")
        elif ev.tipo == "lote_fim":
            print(f"\nFim: {resumo_final(d)[1]}\nRegistro: {cfg.arquivo_registro}")

    cancelar = threading.Event()
    try:
        resumo = projeto.executar(selecionados, ao_evento, cancelar=cancelar)
    except KeyboardInterrupt:
        cancelar.set()
        projeto.registro.salvar()
        print("\nInterrompido. O que já terminou está salvo.")
        return 130
    return codigo_saida(resumo)


if __name__ == "__main__":
    sys.exit(main())
