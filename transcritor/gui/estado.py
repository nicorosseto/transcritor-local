"""Traduz o resumo de uma rodada no estado final mostrado na tela (achado X16).

Fica fora do app.py para ser testável sem Tk. Regra: nunca "sucesso" sem nenhum sucesso.
"""

from __future__ import annotations


def resumo_final(d: dict) -> tuple[str, str]:
    """Retorna (nivel, texto). nivel: sucesso | parcial | interrompido | falha | vazio."""
    ok, erro = int(d.get("ok", 0)), int(d.get("erro", 0))
    plural = lambda n, s, p: f"{n} {s if n == 1 else p}"
    if d.get("fatal"):
        feito = f" {plural(ok, 'vídeo foi concluído', 'vídeos foram concluídos')} antes do erro." if ok else ""
        return "falha", f"A rodada parou por um erro: {d['fatal']}.{feito}"
    if d.get("cancelado") or d.get("parado"):
        motivo = "cancelada" if d.get("cancelado") else "parada"
        return "interrompido", (f"Rodada {motivo}: {plural(ok, 'concluído', 'concluídos')}"
                                + (f", {plural(erro, 'com erro', 'com erro')}" if erro else "")
                                + ". O restante continua pendente.")
    if ok == 0 and erro > 0:
        return "falha", f"Nenhum vídeo foi concluído; {plural(erro, 'teve erro', 'tiveram erro')}."
    if ok == 0:
        return "vazio", "Nada foi transcrito nesta rodada."
    if erro > 0:
        return "parcial", (f"{plural(ok, 'concluído', 'concluídos')} e {plural(erro, 'com erro', 'com erro')}. "
                           "Veja os erros na tabela; eles podem ser refeitos.")
    return "sucesso", f"Pronto! {plural(ok, 'vídeo transcrito', 'vídeos transcritos')}"
