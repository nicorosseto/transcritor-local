"""Regressões da fase 2 (auditoria de 08/10/2026). Cada teste leva o ID do achado.

Escritos ANTES da correção; falharam no commit 1b8b073. Ver docs/auditorias/STATUS.md.
"""

from __future__ import annotations

import os
import threading
import time

import pytest
from conftest import criar_video, requer_ffmpeg

from transcritor import consolidacao, midia, ocr
from transcritor.config import Config
from transcritor.pipeline import Projeto
from transcritor.registro import OK, Registro
from transcritor.util import PastaEmUso, Trava


# --------------------------------------------------------------------------- X4
def test_x4_trava_nao_e_reentrante(tmp_path):
    with Trava(tmp_path):
        with pytest.raises(PastaEmUso):
            with Trava(tmp_path):
                pass
        assert (tmp_path / ".em_uso.lock").exists(), "a segunda entrada apagou a trava da primeira"


def test_x4_trava_e_atomica_entre_threads(tmp_path):
    """Várias threads tentando ao mesmo tempo: só uma pode entrar."""
    entraram, barreira = [], threading.Barrier(8)

    def tentar():
        barreira.wait()
        try:
            with Trava(tmp_path):
                entraram.append(1)
                time.sleep(0.2)
        except PastaEmUso:
            pass
    ts = [threading.Thread(target=tentar) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(entraram) == 1


def test_x4_leitura_da_pasta_respeita_a_trava(tmp_path):
    (tmp_path / "v").mkdir()
    proj = Projeto(Config(tmp_path / "v", tmp_path / "s"))
    with Trava(tmp_path / "s"):
        with pytest.raises(PastaEmUso):
            proj.escanear()


# --------------------------------------------------------------------------- X8
def test_x8_links_das_capturas_funcionam_na_base(tmp_path):
    saida = tmp_path / "saida"
    img = saida / "capturas" / "modulo" / "aula" / "cap.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"jpg")
    md = saida / "transcricoes_md" / "modulo" / "aula.md"
    md.parent.mkdir(parents=True)
    md.write_text("fala\n\n> tela · [captura](../../capturas/modulo/aula/cap.jpg)", encoding="utf-8")
    base = saida / "base_consolidada"
    (gerado,) = consolidacao.consolidar([("modulo/aula.mp4", md)], base, 1000)
    texto = gerado.read_text(encoding="utf-8")
    link = texto.split("[captura](")[1].split(")")[0]
    assert (base / link).resolve() == img.resolve(), link


# --------------------------------------------------------------------------- X9
def test_x9_video_maior_que_o_limite_tambem_e_dividido(tmp_path):
    md = tmp_path / "um.md"
    md.write_text(" ".join(["palavra"] * 30), encoding="utf-8")
    gerados = consolidacao.consolidar([("aula.mp4", md)], tmp_path / "base", 10)
    assert len(gerados) > 1
    for g in gerados:
        assert len(g.read_text(encoding="utf-8").split()) <= 10, g.name
    total = sum(g.read_text(encoding="utf-8").count("palavra") for g in gerados)
    assert total == 30, "perdeu texto ao dividir"


def test_x9_divide_por_paragrafo_quando_possivel(tmp_path):
    md = tmp_path / "um.md"
    paragrafos = [f"**[00:0{i}:00]** " + " ".join([f"p{i}"] * 6) for i in range(6)]
    md.write_text("\n\n".join(paragrafos), encoding="utf-8")
    gerados = consolidacao.consolidar([("aula.mp4", md)], tmp_path / "base", 20)
    for g in gerados:
        for linha in g.read_text(encoding="utf-8").split("\n\n")[1:]:
            assert linha.startswith("**["), "parágrafo cortado no meio sem necessidade"


# --------------------------------------------------------------------------- X10
@requer_ffmpeg
def test_x10_falha_do_ffmpeg_nas_capturas_e_erro_nao_lista_vazia(tmp_path):
    ruim = tmp_path / "ruim.mp4"
    ruim.write_bytes(b"isto nao e um video")
    with pytest.raises(RuntimeError):
        midia.extrair_capturas(ruim, tmp_path / "caps")


def test_x10_falha_tecnica_do_ocr_e_erro_nao_texto_vazio(tmp_path):
    estado = ocr.EstadoOCR(True, "/caminho/que/nao/existe/tesseract", True, None, "", idiomas="eng")
    with pytest.raises(ocr.ErroOCR):
        ocr.ler_imagem(estado, tmp_path / "nao_existe.jpg")


@requer_ffmpeg
def test_x10_rodada_com_ocr_que_falha_termina_parcial(tmp_path, modelo_falso, monkeypatch):
    from transcritor.gui.estado import resumo_final
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("Slide um com bastante texto legivel aqui", 4)])
    monkeypatch.setattr(ocr, "verificar", lambda: ocr.EstadoOCR(True, "x", True, None, "", idiomas="eng"))

    def quebra(*a, **k):
        raise ocr.ErroOCR("tesseract travou (simulado)")
    monkeypatch.setattr(ocr, "ler_imagem", quebra)
    proj = Projeto(Config(videos, saida, ocr=True))
    resumo = proj.executar(proj.escanear(), lambda e: None)
    linha = proj.registro.linhas["a.mp4"]
    assert linha.status == OK, "a fala foi transcrita; não deve ser descartada"
    assert linha.ocr == "falhou" and "tela" in linha.observacao
    assert resumo_final(resumo)[0] == "parcial"
    assert "não" in proj.caminho_md("a.mp4").read_text(encoding="utf-8").split("Texto de tela")[1].split("\n")[0]


@requer_ffmpeg
def test_x10_ocr_pedido_mas_indisponivel_nao_e_sucesso_completo(tmp_path, modelo_falso, monkeypatch):
    from transcritor.gui.estado import resumo_final
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("a", 4)])
    monkeypatch.setattr(ocr, "verificar", lambda: ocr.EstadoOCR(False, None, False, None, "Tesseract ausente"))
    proj = Projeto(Config(videos, saida, ocr=True))
    resumo = proj.executar(proj.escanear(), lambda e: None)
    assert proj.registro.linhas["a.mp4"].ocr == "falhou"
    assert resumo_final(resumo)[0] == "parcial"


# --------------------------------------------------------------------------- X12
@requer_ffmpeg
@pytest.mark.parametrize("cenario, codigo", [("sucesso", 0), ("parcial", 2), ("falha", 1)])
def test_x12_codigo_de_saida_da_cli(tmp_path, modelo_falso, monkeypatch, cenario, codigo):
    from transcritor import cli
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("a", 4)])
    if cenario != "sucesso":
        (videos / "quebrado.mp4").write_bytes(b"lixo")
    if cenario == "falha":
        (videos / "a.mp4").unlink()
    monkeypatch.setattr(cli, "imprimir_diagnostico", lambda cfg: True)
    respostas = iter(["2", "n", "", "0", "s"])
    monkeypatch.setattr("builtins.input", lambda *a: next(respostas))
    assert cli.main(["--videos", str(videos), "--saida", str(saida)]) == codigo


# --------------------------------------------------------------------------- X13
@requer_ffmpeg
def test_x13_extracao_de_audio_obedece_ao_cancelamento(tmp_path):
    from transcritor.util import Cancelado
    v = criar_video(tmp_path / "longo.mp4", [("a", 30)])
    cancelar = threading.Event()
    cancelar.set()
    t0 = time.perf_counter()
    with pytest.raises(Cancelado):
        midia.extrair_audio(v, tmp_path / "a.mp3", cancelar=cancelar)
    assert time.perf_counter() - t0 < 5
    assert not (tmp_path / "a.mp3").exists()


# --------------------------------------------------------------------------- X15
def test_x15_registro_pendente_e_recuperado_ao_abrir(tmp_path):
    arq = tmp_path / "registro.csv"
    r = Registro(arq)
    from transcritor.registro import Linha
    r.linhas["a.mp4"] = Linha("a.mp4", saida="a")
    r.salvar()
    r.linhas["a.mp4"].status = OK
    r.linhas["a.mp4"].palavras = 123
    pendente = tmp_path / "registro_PENDENTE_feche_o_excel.csv"
    arq.rename(tmp_path / "x.csv")
    r.salvar()                                  # grava o estado novo
    arq.rename(pendente)                        # ...como se o Excel tivesse bloqueado
    (tmp_path / "x.csv").rename(arq)            # o principal ficou com o estado antigo
    os.utime(arq, (time.time() - 60, time.time() - 60))

    r2 = Registro(arq)
    assert r2.linhas["a.mp4"].status == OK and r2.linhas["a.mp4"].palavras == 123
    assert "recuperado" in r2.aviso.lower()
    r2.salvar()
    assert not pendente.exists()


# --------------------------------------------------------------------------- híbrido
def test_cpu_hibrida_usa_so_nucleos_de_desempenho():
    from transcritor.config import _nucleos_de_desempenho
    assert _nucleos_de_desempenho([1, 1, 1, 1, 1, 1, 0, 0, 0, 0]) == 6   # 6 P + 4 E
    assert _nucleos_de_desempenho([0] * 6) is None                      # não híbrida
    assert _nucleos_de_desempenho([]) is None
