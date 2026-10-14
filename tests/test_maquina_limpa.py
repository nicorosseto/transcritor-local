"""Achados do teste em máquina limpa (Windows Sandbox, 14/10/2026): N17 a N20.

N20: no Sandbox, criar de novo um arquivo com o nome de um que acabou de ser renomeado
(registro.tmp) falhava com "No such file or directory", e isso derrubava a rodada inteira.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import criar_video, requer_ffmpeg
from transcritor import util
from transcritor.config import Config
from transcritor.pipeline import Projeto
from transcritor.registro import OK, Linha, Registro
from transcritor.resultado import resumo_final


# --------------------------------------------------------------------------- N20: gravação
def _bloquear_nome_reusado(monkeypatch):
    """Imita o Sandbox: um nome de temporário que já foi renomeado não pode ser criado de novo."""
    usados: set[str] = set()
    replace_real = os.replace

    def replace(src, dst):
        replace_real(src, dst)
        usados.add(Path(src).name)

    abrir_real = open

    def abrir(caminho, modo="r", *a, **k):
        if "w" in modo and Path(caminho).name in usados:
            raise FileNotFoundError(2, "No such file or directory", str(caminho))
        return abrir_real(caminho, modo, *a, **k)

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr("builtins.open", abrir)
    return usados


def test_n20_registro_salva_varias_vezes_mesmo_sem_poder_reusar_o_temporario(tmp_path, monkeypatch):
    usados = _bloquear_nome_reusado(monkeypatch)
    r = Registro(tmp_path / "registro.csv")
    r.linhas["a.mp4"] = Linha("a.mp4", saida="a")
    for palavras in (1, 2, 3):
        r.linhas["a.mp4"].palavras = palavras
        r.salvar()
    assert len(usados) == 3  # um temporário diferente por gravação
    assert Registro(tmp_path / "registro.csv").linhas["a.mp4"].palavras == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_n20_gravacao_tenta_de_novo_depois_de_um_erro_de_disco(tmp_path, monkeypatch):
    replace_real, falhas = os.replace, [1]

    def replace(src, dst):
        if falhas:
            falhas.pop()
            raise FileNotFoundError(2, "No such file or directory", str(src))
        replace_real(src, dst)
    monkeypatch.setattr(os, "replace", replace)
    destino = tmp_path / "x.json"
    util.gravar_atomico(destino, lambda p: p.write_text("ok", encoding="utf-8"), espera=0)
    assert destino.read_text(encoding="utf-8") == "ok"
    assert not list(tmp_path.glob("*.tmp"))  # a tentativa que falhou não deixa sobra


def test_n20_gravacao_desiste_com_o_ultimo_erro(tmp_path):
    def escrever(p):
        raise FileNotFoundError(2, "No such file or directory", str(p))
    with pytest.raises(FileNotFoundError):
        util.gravar_atomico(tmp_path / "x.json", escrever, tentativas=2, espera=0)


def test_n20_temporarios_tem_nomes_unicos(tmp_path):
    nomes = {util.nome_temporario(tmp_path / "registro.csv").name for _ in range(50)}
    assert len(nomes) == 50
    assert all(n.startswith("registro.csv.") and n.endswith(".tmp") for n in nomes)


@requer_ffmpeg
def test_n20_rodada_inteira_funciona_sem_reusar_temporarios(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("x", 3)])
    criar_video(videos / "b.mp4", [("y", 3)])
    proj = Projeto(Config(videos, saida))
    itens = proj.escanear()
    _bloquear_nome_reusado(monkeypatch)
    resumo = proj.executar(itens, lambda e: None)
    assert resumo_final(resumo)[0] == "sucesso", resumo
    reg = Registro(saida / "registro.csv")
    assert {l.status for l in reg.linhas.values()} == {OK}


@requer_ffmpeg
def test_n20_falha_ao_salvar_o_registro_nao_derruba_a_rodada(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("x", 3)])
    criar_video(videos / "b.mp4", [("y", 3)])
    proj = Projeto(Config(videos, saida))
    itens = proj.escanear()
    salvar_real, falhas = proj.registro.salvar, [1]

    def salvar():
        if falhas:
            falhas.pop()
            raise FileNotFoundError(2, "No such file or directory", "registro.tmp")
        salvar_real()
    monkeypatch.setattr(proj.registro, "salvar", salvar)
    eventos = []
    resumo = proj.executar(itens, eventos.append)
    assert resumo["ok"] == 2 and not resumo.get("fatal"), resumo
    assert resumo_final(resumo)[0] == "sucesso"  # a falha foi recuperada no vídeo seguinte
    assert any("tento de novo" in e.dados.get("texto", "") for e in eventos if e.tipo == "aviso")
    reg = Registro(saida / "registro.csv")
    assert {l.status for l in reg.linhas.values()} == {OK}


@requer_ffmpeg
def test_n20_registro_que_nunca_salva_vira_parcial_e_nao_erro_fatal(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("x", 3)])
    proj = Projeto(Config(videos, saida))
    itens = proj.escanear()

    def salvar():
        raise FileNotFoundError(2, "No such file or directory", "registro.tmp")
    monkeypatch.setattr(proj.registro, "salvar", salvar)
    resumo = proj.executar(itens, lambda e: None)
    nivel, texto = resumo_final(resumo)
    assert nivel == "parcial" and "registro.csv" in texto
    assert proj.caminho_md("a.mp4").is_file()  # a transcrição não se perde


def test_n20_consolidacao_nao_reusa_a_pasta_temporaria(tmp_path):
    from transcritor import consolidacao
    md = tmp_path / "md" / "a.md"
    md.parent.mkdir()
    md.write_text("# a\n\ntexto", encoding="utf-8")
    base = tmp_path / "base"
    (tmp_path / ".base.abcd1234.tmp").mkdir()  # sobra de uma execução interrompida
    consolidacao.consolidar([("a.mp4", md)], base, 400000)
    consolidacao.consolidar([("a.mp4", md)], base, 400000)
    assert list(base.glob("base_*.md"))
    assert not list(tmp_path.glob(".base*.tmp"))
