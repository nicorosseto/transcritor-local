"""Regressões da fase 1 (auditoria de 08/10/2026). Cada teste leva o ID do achado.

Todos foram escritos ANTES da correção e falharam no commit c919adc; ver
docs/auditorias/STATUS.md.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest
from conftest import criar_video, requer_ffmpeg

from transcritor import consolidacao
from transcritor.config import Config
from transcritor.pipeline import Projeto
from transcritor.registro import OK, PENDENTE

RAIZ = Path(__file__).resolve().parent.parent


def _rodar(cfg: Config) -> tuple[Projeto, list]:
    proj = Projeto(cfg)
    eventos: list = []
    proj.executar(proj.escanear(), eventos.append)
    return proj, eventos


# --------------------------------------------------------------------------- X1
@requer_ffmpeg
def test_x1_video_substituido_reextrai_o_audio(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    v = criar_video(videos / "aula.mp4", [("curto", 4)])
    proj, _ = _rodar(Config(videos, saida))
    assert "frase 1" in proj.caminho_md("aula.mp4").read_text(encoding="utf-8")

    time.sleep(1.1)
    criar_video(v, [("longo", 8)])                      # mesmo nome, outro conteúdo
    proj2, _ = _rodar(Config(videos, saida))
    md = proj2.caminho_md("aula.mp4").read_text(encoding="utf-8")
    assert "frase 3" in md, "o .md novo foi feito com o áudio antigo (cache não invalidado)"


# --------------------------------------------------------------------------- X2
@requer_ffmpeg
def test_x2_mesmo_nome_com_extensoes_diferentes_nao_colide(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "aula.mp4", [("a", 4)])
    criar_video(videos / "aula.mkv", [("b", 8)])
    proj, _ = _rodar(Config(videos, saida))
    md_mp4, md_mkv = proj.caminho_md("aula.mp4"), proj.caminho_md("aula.mkv")
    assert md_mp4 != md_mkv
    assert proj.caminho_audio("aula.mp4") != proj.caminho_audio("aula.mkv")
    assert proj.pasta_capturas("aula.mp4") != proj.pasta_capturas("aula.mkv")
    assert "frase 1" in md_mp4.read_text(encoding="utf-8")
    assert "frase 3" in md_mkv.read_text(encoding="utf-8")
    assert "frase 3" not in md_mp4.read_text(encoding="utf-8")


@requer_ffmpeg
def test_x2_chave_de_saida_e_estavel_quando_surge_irmao(tmp_path, modelo_falso):
    """O primeiro vídeo mantém o nome de saída mesmo quando aparece outro com o mesmo nome."""
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "aula.mp4", [("a", 4)])
    proj, _ = _rodar(Config(videos, saida))
    antes = proj.caminho_md("aula.mp4")
    criar_video(videos / "aula.mkv", [("b", 4)])
    proj2 = Projeto(Config(videos, saida))
    proj2.escanear()
    assert proj2.caminho_md("aula.mp4") == antes
    assert proj2.registro.linhas["aula.mp4"].status == OK


# --------------------------------------------------------------------------- X3
def test_x3_rodada_recusa_pastas_diferentes_da_leitura(tmp_path):
    from transcritor.pipeline import PastasMudaram
    (tmp_path / "v").mkdir()
    proj = Projeto(Config(tmp_path / "v", tmp_path / "saida_a"))
    da_tela = Config(tmp_path / "v", tmp_path / "saida_b", preset="preciso")
    with pytest.raises(PastasMudaram):
        proj.preparar_rodada(da_tela)
    ok = proj.preparar_rodada(Config(tmp_path / "v", tmp_path / "saida_a", preset="preciso", ocr=True))
    assert ok.preset == "preciso" and ok.ocr and ok.pasta_saida == proj.cfg.pasta_saida


# --------------------------------------------------------------------------- X5
def test_x5_falha_na_consolidacao_preserva_base_anterior(tmp_path, monkeypatch):
    base = tmp_path / "base"
    base.mkdir()
    (base / "base_geral.md").write_text("base anterior valida", encoding="utf-8")
    md = tmp_path / "a.md"
    md.write_text("texto novo", encoding="utf-8")

    original = Path.write_text

    def quebra(self, *a, **k):
        if self.name.startswith("base_"):
            raise OSError("disco cheio (simulado)")
        return original(self, *a, **k)
    monkeypatch.setattr(Path, "write_text", quebra)
    with pytest.raises(OSError):
        consolidacao.consolidar([("a.mp4", md)], base, 100)
    monkeypatch.setattr(Path, "write_text", original)
    assert (base / "base_geral.md").read_text(encoding="utf-8") == "base anterior valida"


def test_x5_md_com_bytes_invalidos_nao_derruba_a_consolidacao(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (base / "base_geral.md").write_text("anterior", encoding="utf-8")
    ruim = tmp_path / "ruim.md"
    ruim.write_bytes(b"texto \xff quebrado")
    gerados = consolidacao.consolidar([("a.mp4", ruim)], base, 100)
    assert gerados and "texto" in gerados[0].read_text(encoding="utf-8")


# --------------------------------------------------------------------------- X6
@requer_ffmpeg
def test_x6_md_apagado_volta_a_pendente(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "aula.mp4", [("a", 4)])
    proj, _ = _rodar(Config(videos, saida))
    proj.caminho_md("aula.mp4").unlink()
    proj2 = Projeto(Config(videos, saida))
    proj2.escanear()
    assert [i.rel for i in proj2.pendentes()] == ["aula.mp4"]
    assert proj2.registro.linhas["aula.mp4"].status == PENDENTE


# --------------------------------------------------------------------------- X7
@requer_ffmpeg
def test_x7_saida_de_outra_origem_exige_confirmacao(tmp_path, modelo_falso):
    from transcritor.pipeline import ProjetoDeOutraOrigem
    a, b, saida = tmp_path / "curso_a", tmp_path / "curso_b", tmp_path / "saida"
    va = criar_video(a / "aula.mp4", [("a", 4)])
    _rodar(Config(a, saida))
    b.mkdir()
    vb = b / "aula.mp4"
    vb.write_bytes(va.read_bytes())
    os.utime(vb, (va.stat().st_atime, va.stat().st_mtime))   # mesma assinatura
    with pytest.raises(ProjetoDeOutraOrigem):
        Projeto(Config(b, saida))
    proj = Projeto(Config(b, saida), aceitar_nova_origem=True)
    proj.escanear()
    assert proj.cfg.pasta_videos == b


@requer_ffmpeg
def test_x7_nao_adota_md_so_por_existir_em_projeto_novo(tmp_path, modelo_falso):
    """Em projeto já identificado, um .md solto não vira 'concluído' sem ter sido feito aqui."""
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "a.mp4", [("a", 4)])
    proj, _ = _rodar(Config(videos, saida))
    criar_video(videos / "b.mp4", [("b", 4)])
    intruso = proj.caminho_md("b.mp4")
    intruso.write_text("texto de outra origem", encoding="utf-8")
    proj2 = Projeto(Config(videos, saida))
    proj2.escanear()
    assert proj2.registro.linhas["b.mp4"].status != OK


# --------------------------------------------------------------------------- X11
@requer_ffmpeg
def test_x11_ler_pasta_atualiza_a_base_consolidada(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "Mod/a.mp4", [("a", 4)])
    removido = criar_video(videos / "Mod/b.mp4", [("b", 8)])
    proj, _ = _rodar(Config(videos, saida))
    base = saida / "base_consolidada" / "base_Mod.md"
    assert "frase 3" in base.read_text(encoding="utf-8")
    removido.unlink()
    Projeto(Config(videos, saida)).escanear()               # só "Ler pasta", sem rodada
    assert "frase 3" not in base.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- X16
@requer_ffmpeg
def test_x16_erro_inesperado_vira_falha_fatal_explicita(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "a.mp4", [("a", 4)])
    proj = Projeto(Config(videos, saida))
    itens = proj.escanear()

    def explode(*a, **k):
        raise RuntimeError("falha inesperada (simulada)")
    monkeypatch.setattr(proj, "consolidar", explode)
    eventos: list = []
    resumo = proj.executar(itens, eventos.append)
    assert resumo.get("fatal") and "simulada" in resumo["fatal"]
    fim = [e for e in eventos if e.tipo == "lote_fim"]
    assert len(fim) == 1 and fim[0].dados.get("fatal")


def test_x16_tela_final_nunca_mostra_sucesso_sem_sucesso():
    from transcritor.gui.estado import resumo_final
    assert resumo_final({"ok": 0, "erro": 0, "fatal": "boom"})[0] == "falha"
    assert resumo_final({"ok": 0, "erro": 0})[0] != "sucesso"
    assert resumo_final({"ok": 0, "erro": 3})[0] == "falha"
    assert resumo_final({"ok": 2, "erro": 1})[0] == "parcial"
    assert resumo_final({"ok": 2, "erro": 0, "cancelado": True})[0] == "interrompido"
    assert resumo_final({"ok": 3, "erro": 0})[0] == "sucesso"


# --------------------------------------------------------------------------- X13
def test_x13_threads_de_trabalho_nao_tocam_o_tk():
    """Guarda de regressão: nada de .after() agendado a partir de threads de trabalho.
    A interface recebe tudo pela fila consumida na thread principal."""
    for nome in ("app.py", "verificacao.py"):
        fonte = (RAIZ / "transcritor" / "gui" / nome).read_text(encoding="utf-8")
        assert not re.search(r"\.after\(\s*0\s*,", fonte), f"{nome} agenda callback com after(0, ...)"
