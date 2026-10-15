"""Traduz o resumo de uma rodada no estado final (tela e código de saída do terminal).

Achados X16, X10 e X12. Regra: nunca "sucesso" sem nenhum sucesso, nem com parte faltando.
"""

from __future__ import annotations


def resumo_final(d: dict) -> tuple[str, str]:
    """Retorna (nivel, texto). nivel: sucesso | parcial | interrompido | falha | vazio."""
    ok, erro = int(d.get("ok", 0)), int(d.get("erro", 0))
    plural = lambda n, s, p: f"{n} {s if n == 1 else p}"
    if d.get("fatal"):
        feito = f" {plural(ok, 'vídeo foi concluído', 'vídeos foram concluídos')} antes do erro." if ok else ""
        return "falha", f"A rodada parou por um erro: {d['fatal']}.{feito}"
    reg = (" O registro.csv não pôde ser salvo; as transcrições estão na pasta de saída."
           if d.get("registro_nao_salvo") else "")  # aparece em todos os desfechos (achado K18)
    if d.get("cancelado") or d.get("parado"):
        motivo = "cancelada" if d.get("cancelado") else "parada"
        return "interrompido", (f"Rodada {motivo}: {plural(ok, 'concluído', 'concluídos')}"
                                + (f", {plural(erro, 'com erro', 'com erro')}" if erro else "")
                                + ". O restante continua pendente." + reg)
    if ok == 0 and erro > 0:
        return "falha", f"Nenhum vídeo foi concluído; {plural(erro, 'teve erro', 'tiveram erro')}."
    if ok == 0:
        return "vazio", "Nada foi transcrito nesta rodada."
    if erro > 0:
        return "parcial", (f"{plural(ok, 'concluído', 'concluídos')} e {plural(erro, 'com erro', 'com erro')}. "
                           "Veja os erros na tabela; eles podem ser refeitos." + reg)
    if d.get("registro_nao_salvo"):
        return "parcial", (f"{plural(ok, 'vídeo transcrito', 'vídeos transcritos')}, mas o registro.csv não "
                           "pôde ser salvo. As transcrições estão na pasta de saída.")
    if d.get("ocr_indisponivel") or d.get("telas_falharam"):
        motivo = d.get("ocr_indisponivel") or (
            f"falhou em {plural(int(d['telas_falharam']), 'vídeo', 'vídeos')}")
        return "parcial", (f"{plural(ok, 'vídeo transcrito', 'vídeos transcritos')}, mas o texto da tela "
                           f"não foi lido por completo ({motivo}). A fala está salva.")
    return "sucesso", f"Pronto! {plural(ok, 'vídeo transcrito', 'vídeos transcritos')}"


CODIGO_SAIDA = {"sucesso": 0, "vazio": 0, "falha": 1, "parcial": 2, "interrompido": 3}


def codigo_saida(d: dict) -> int:
    """Código de saída da CLI (achado X12): 0 ok · 1 falha · 2 parcial · 3 interrompido."""
    return CODIGO_SAIDA[resumo_final(d)[0]]
