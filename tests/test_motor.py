from __future__ import annotations

import os
import threading
import time

from conftest import criar_video, requer_ffmpeg

from transcritor import consolidacao, markdown, midia, ocr
from transcritor.config import Config, vocabulario_de_texto
from transcritor.estimativa import estimar
from transcritor.pipeline import Projeto, listar_videos
from transcritor.registro import OK, ORFAO, SUBSTITUIDO, Registro
from transcritor.transcricao import Paragrafo


def test_listar_videos_recursivo_e_ignora_pastas_especiais(tmp_path):
    for rel in ["a.mp4", "Mod 1/b.MKV", "Mod 1/sub/c.mov", "_rascunho/x.mp4", ".oculta/y.mp4", "nota.txt"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    rels = [r for r, _ in listar_videos(tmp_path)]
    assert rels == ["a.mp4", "Mod 1/b.MKV", "Mod 1/sub/c.mov"]


def test_vocabulario():
    assert vocabulario_de_texto("Power BI, DAX;ChatGPT\n hook ,") == ["Power BI", "DAX", "ChatGPT", "hook"]


def test_saida_dentro_de_videos_e_recusada(tmp_path):
    (tmp_path / "v").mkdir()
    cfg = Config(tmp_path / "v", tmp_path / "v" / "saida")
    assert any("dentro" in e for e in cfg.validar())


def test_markdown_insere_tela_no_paragrafo_certo(tmp_path):
    pars = [Paragrafo(0, "um"), Paragrafo(60, "dois"), Paragrafo(120, "tres")]
    telas = [markdown.Tela(75, "TEXTO DA TELA")]
    md, _ = markdown.montar(titulo="t", origem="t.mp4", duracao=180, modelo="m", preset="p",
                            paragrafos=pars, telas=telas, destino=tmp_path / "t.md")
    assert md.index("dois") < md.index("TEXTO DA TELA") < md.index("tres")
    assert "[00:01:15]" in md


def test_consolidacao_por_subpasta_e_divisao(tmp_path):
    itens = []
    for rel in ["Mod A/1.mp4", "Mod A/2.mp4", "Mod B/1.mp4", "solto.mp4"]:
        md = tmp_path / "md" / (rel + ".md")
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text("palavra " * 60, encoding="utf-8")
        itens.append((rel, md))
    gerados = consolidacao.consolidar(itens, tmp_path / "base", max_palavras=100)
    nomes = sorted(p.name for p in gerados)
    assert nomes == ["base_Mod A_parte01.md", "base_Mod A_parte02.md", "base_Mod B.md", "base_geral.md"]


def test_ocr_limpeza_e_similaridade():
    sujo = "  |||  \n Total Vendas = SUM(Vendas[Valor]) \n ~~ \n"
    assert ocr.limpar(sujo) == "Total Vendas = SUM(Vendas[Valor])"
    assert ocr.parecido("medida total vendas soma", "medida total vendas soma valor")
    assert not ocr.parecido("abc def ghi", "xyz uvw rst")


@requer_ffmpeg
def test_registro_detecta_novo_importado_substituido_orfao(tmp_path):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    a = criar_video(videos / "Mod/a.mp4", [("A", 2)])
    b = criar_video(videos / "b.mp4", [("B", 2)])
    cfg = Config(videos, saida)
    proj = Projeto(cfg)
    # simula um .md de versão antiga para b.mp4
    md_b = proj.caminho_md("b.mp4")
    md_b.parent.mkdir(parents=True, exist_ok=True)
    md_b.write_text("antigo", encoding="utf-8")
    proj.escanear()
    s = proj.ultima_sincronizacao
    assert s["novos"] == 1 and s["importados"] == 1
    assert proj.registro.linhas["b.mp4"].status == OK
    assert proj.registro.linhas["Mod/a.mp4"].duracao_s > 1

    # substitui b por outro conteúdo, apaga a
    time.sleep(1.1)
    criar_video(b, [("B novo", 3)])
    os.remove(a)
    proj2 = Projeto(cfg)
    proj2.escanear()
    s2 = proj2.ultima_sincronizacao
    assert s2["substituidos"] == 1 and s2["orfaos"] == 1
    assert proj2.registro.linhas["b.mp4"].status == SUBSTITUIDO
    assert proj2.registro.linhas["Mod/a.mp4"].status == ORFAO
    # registro relido do disco preserva tudo
    r = Registro(cfg.arquivo_registro)
    assert r.linhas["b.mp4"].status == SUBSTITUIDO


@requer_ffmpeg
def test_pipeline_completo_com_subpastas(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "Mod 1/aula.mp4", [("x", 6)])
    criar_video(videos / "Mod 2/aula.mp4", [("y", 4)])  # mesmo nome, outra pasta
    cfg = Config(videos, saida, vocabulario=["Power BI", "DAX"])
    proj = Projeto(cfg)
    itens = proj.escanear()
    eventos = []
    resumo = proj.executar(itens, eventos.append)
    assert resumo["ok"] == 2 and resumo["erro"] == 0
    md1, md2 = proj.caminho_md("Mod 1/aula.mp4"), proj.caminho_md("Mod 2/aula.mp4")
    assert md1.is_file() and md2.is_file() and md1 != md2
    assert "frase 0" in md1.read_text(encoding="utf-8")
    assert modelo_falso.chamadas[0]["hotwords"] == "Power BI, DAX"
    assert (saida / "base_consolidada" / "base_Mod 1.md").is_file()
    linhas = Registro(cfg.arquivo_registro).linhas
    assert linhas["Mod 1/aula.mp4"].status == OK and linhas["Mod 1/aula.mp4"].velocidade > 0
    tipos = [e.tipo for e in eventos]
    assert tipos[0] == "lote_inicio" and tipos[-1] == "lote_fim"
    # segunda varredura: nada pendente
    proj2 = Projeto(cfg)
    proj2.escanear()
    assert proj2.pendentes() == []


@requer_ffmpeg
def test_parar_apos_atual(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    for n in range(3):
        criar_video(videos / f"v{n}.mp4", [("x", 2)])
    proj = Projeto(Config(videos, saida))
    itens = proj.escanear()
    parar = threading.Event()

    def ao_evento(ev):
        if ev.tipo == "video_fim":
            parar.set()
    resumo = proj.executar(itens, ao_evento, parar_apos_atual=parar)
    assert resumo["ok"] == 1 and resumo["parado"]
    novo = Projeto(Config(videos, saida))
    novo.escanear()
    assert len(novo.pendentes()) == 2


@requer_ffmpeg
def test_video_corrompido_vira_erro_sem_derrubar_lote(tmp_path, modelo_falso):
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "bom.mp4", [("x", 2)])
    (videos / "ruim.mp4").write_bytes(b"isto nao e video")
    proj = Projeto(Config(videos, saida))
    resumo = proj.executar(proj.escanear(), lambda e: None)
    assert resumo == {"ok": 1, "erro": 1, "cancelado": False, "parado": False}
    assert proj.registro.linhas["ruim.mp4"].status == "erro"


def test_estimativa_usa_medicao(tmp_path):
    r = Registro(tmp_path / "r.csv")
    e0 = estimar([3600], r, "equilibrado", "cpu", com_ocr=False)
    assert not e0.medida and abs(e0.segundos_transcricao - 3600 / 1.2) < 1
    from transcritor.registro import Linha
    r.linhas["x"] = Linha("x", status=OK, preset="equilibrado", velocidade=2.0, duracao_s=600)
    e1 = estimar([3600], r, "equilibrado", "cpu", com_ocr=True)
    assert e1.medida and e1.segundos_transcricao == 1800 and e1.segundos_ocr > 0


@requer_ffmpeg
def test_capturas_detectam_troca_de_slide(tmp_path):
    v = criar_video(tmp_path / "slides.mp4",
                    [("Slide um\nIntroducao", 4), ("Slide dois\nMedidas DAX", 4), ("Slide tres\nFim", 4)],
                    cores=[(255, 255, 255), (200, 230, 255), (255, 240, 200)])
    caps = midia.extrair_capturas(v, tmp_path / "caps")
    assert 3 <= len(caps) <= 4, caps
    assert [round(t) for t, _ in caps][:3] == [0, 4, 8]


@requer_ffmpeg
def test_ocr_le_texto_da_captura(tmp_path):
    import shutil as sh
    import pytest
    exe = sh.which("tesseract")
    if not exe:
        pytest.skip("tesseract não instalado")
    v = criar_video(tmp_path / "s.mp4", [("Total Vendas\nMedida DAX", 3)])
    (t, img), *_ = midia.extrair_capturas(v, tmp_path / "caps")
    estado = ocr.EstadoOCR(True, exe, True, None, "", idiomas="eng")
    texto = ocr.limpar(ocr.ler_imagem(estado, img))
    assert "Total" in texto and "Vendas" in texto


def test_trava_impede_duas_execucoes(tmp_path):
    import pytest
    from transcritor.util import PastaEmUso, Trava
    (tmp_path / ".em_uso.lock").write_text("1")  # PID 1 sempre existe no Linux (init)
    if os.name != "nt":
        with pytest.raises(PastaEmUso):
            with Trava(tmp_path):
                pass
    (tmp_path / ".em_uso.lock").write_text(str(os.getpid()))  # trava do próprio processo: permitido
    with Trava(tmp_path):
        assert (tmp_path / ".em_uso.lock").exists()
    assert not (tmp_path / ".em_uso.lock").exists()


def test_correcoes_palavra_inteira_sem_maiusculas(tmp_path):
    from transcritor import correcoes
    regras = {"Chatepte": "ChatGPT", "Clode": "Claude", "chat EPT": "ChatGPT"}
    c = correcoes.compilar(regras)
    texto, n = correcoes.aplicar("O chatepte e o Clode. Clodes ficam. Usei chat EPT ontem.", c)
    assert texto == "O ChatGPT e o Claude. Clodes ficam. Usei ChatGPT ontem."
    assert n == 3


def test_correcoes_arquivo_invalido_nao_derruba(tmp_path):
    from transcritor import correcoes
    (tmp_path / "correcoes.json").write_text("{ isso não é json", encoding="utf-8")
    regras, aviso = correcoes.carregar(tmp_path)
    assert regras == {} and "erro de formato" in aviso
    arq = correcoes.criar_modelo_se_faltar(tmp_path / "novo")
    regras, aviso = correcoes.carregar(arq.parent)
    assert regras["Chatepte"] == "ChatGPT" and aviso == ""


def test_markdown_tem_linha_em_branco_apos_separador(tmp_path):
    md, _ = markdown.montar(titulo="t", origem="t.mp4", duracao=60, modelo="m", preset="p",
                            paragrafos=[Paragrafo(0, "oi")], telas=[], destino=tmp_path / "t.md")
    assert "---\n\n**[00:00:00]** oi" in md


def test_registro_le_csv_antigo_sem_colunas_novas(tmp_path):
    arq = tmp_path / "registro.csv"
    arq.write_text("caminho;tamanho_bytes;modificado_em;duracao_s;status;preset;ocr;transcrito_em;"
                   "seg_transcricao;seg_ocr;velocidade;palavras;capturas;observacao\n"
                   "a.mp4;10;2026-01-01T00:00:00;60,00;ok;preciso;nao;;30,00;0,00;2,00;100;0;\n",
                   encoding="utf-8-sig")
    r = Registro(arq)
    assert r.linhas["a.mp4"].velocidade == 2.0 and r.linhas["a.mp4"].threads == 0


@requer_ffmpeg
def test_pipeline_aplica_correcoes_e_registra_diagnostico(tmp_path, modelo_falso):
    import json
    videos, saida = tmp_path / "videos", tmp_path / "saida"
    criar_video(videos / "a.mp4", [("x", 4)])
    saida.mkdir()
    (saida / "correcoes.json").write_text(json.dumps({"trocar": {"frase": "sentença"}}), encoding="utf-8")
    proj = Projeto(Config(videos, saida))
    proj.executar(proj.escanear(), lambda e: None)
    md = proj.caminho_md("a.mp4").read_text(encoding="utf-8")
    assert "sentença 0" in md and "Correções automáticas:** 2" in md
    l = Registro(saida / "registro.csv").linhas["a.mp4"]
    assert l.correcoes == 2 and l.threads > 0 and l.dispositivo == "cpu"
