"""Achados N1 a N6 do primeiro teste real no Windows (14/10/2026) e o formato "para IA".

Cada teste foi escrito ANTES da correção e falhou pelo motivo certo.
Registro do teste: docs/testes/2026-10-14-windows-p1.md
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import pytest

from conftest import criar_video, requer_ffmpeg
from transcritor import markdown, ocr
from transcritor.config import Config
from transcritor.markdown import Paragrafo, Tela
from transcritor.pipeline import Projeto

TEM_TESSERACT = shutil.which("tesseract") is not None
requer_tesseract = pytest.mark.skipif(not TEM_TESSERACT, reason="tesseract não instalado")


# --------------------------------------------------------------------------- N1
def _tsv(*palavras: tuple[str, float, tuple[int, int, int]]) -> str:
    """Monta um TSV no formato do Tesseract: (texto, confiança, (bloco, parágrafo, linha))."""
    cab = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    linhas = [cab, "1\t1\t0\t0\t0\t0\t0\t0\t640\t360\t-1\t"]
    for n, (texto, conf, (b, p, l)) in enumerate(palavras, 1):
        linhas.append(f"5\t1\t{b}\t{p}\t{l}\t{n}\t0\t0\t10\t10\t{conf}\t{texto}")
    return "\n".join(linhas) + "\n"


def test_n1_tsv_descarta_palavras_de_baixa_confianca_e_mantem_as_linhas():
    tsv = _tsv(("Faturamento", 92, (1, 1, 1)), ("total", 88, (1, 1, 1)),
               ("xqz", 12, (1, 1, 1)),
               ("Meta", 75, (1, 1, 2)), ("anual", 71, (1, 1, 2)),
               ("eE", 20, (2, 1, 1)), ("ao", 31, (2, 1, 1)))
    texto = ocr.texto_do_tsv(tsv)
    assert texto == "Faturamento total\nMeta anual"


def test_n1_tsv_sem_nenhuma_palavra_confiavel_e_vazio():
    assert ocr.texto_do_tsv(_tsv(("lixo", 10, (1, 1, 1)), ("ruido", 25, (1, 1, 1)))) == ""
    assert ocr.texto_do_tsv("") == ""


def _captura_pequena(destino: Path) -> tuple[Path, set[str]]:
    """Texto grande de 1920x1080 reduzido a 640x360: o que um screencast de baixa resolução entrega."""
    from PIL import Image, ImageDraw, ImageFont
    linhas = ["Faturamento total do periodo", "Vendas por regiao sudeste",
              "Margem media mensal consolidada", "Indicadores de desempenho comercial"]
    img = Image.new("RGB", (1920, 1080), "white")
    d = ImageDraw.Draw(img)
    fonte = ImageFont.load_default(size=20)
    for i, linha in enumerate(linhas):
        d.text((60, 90 + i * 36), linha, fill=(30, 30, 30), font=fonte)
    img.resize((640, 360), Image.Resampling.LANCZOS).save(destino)
    return destino, {p.lower() for l in linhas for p in l.split()}


@requer_tesseract
def test_n1_captura_de_baixa_resolucao_e_ampliada_antes_do_ocr(tmp_path):
    img, esperadas = _captura_pequena(tmp_path / "cap_000000.jpg")
    img = img.rename(tmp_path / "cap_000000.png")  # sem perdas: isola o efeito da ampliação
    estado = ocr.EstadoOCR(True, shutil.which("tesseract"), True, None, "", idiomas="eng")
    lidas = set(re.findall(r"[a-z]{3,}", ocr.ler_imagem(estado, img).lower()))
    acertos = len(esperadas & lidas)
    # sem ampliar, o Tesseract lê 0 de 16 palavras neste quadro; ampliado 2x e já filtrado, lê 4 a 6
    assert acertos >= 3, f"só {acertos} de {len(esperadas)} palavras lidas: {sorted(lidas)}"


@requer_tesseract
def test_n1_ampliacao_nao_altera_a_captura_nem_deixa_temporario(tmp_path):
    img, _ = _captura_pequena(tmp_path / "cap_000000.jpg")
    antes = img.read_bytes()
    estado = ocr.EstadoOCR(True, shutil.which("tesseract"), True, None, "", idiomas="eng")
    ocr.ler_imagem(estado, img)
    assert img.read_bytes() == antes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cap_000000.jpg"]


def test_n1_so_amplia_captura_estreita(tmp_path):
    from PIL import Image
    estreita, larga = tmp_path / "e.jpg", tmp_path / "l.jpg"
    Image.new("RGB", (640, 360), "white").save(estreita)
    Image.new("RGB", (1280, 720), "white").save(larga)
    caminho, temporario = ocr.preparar_imagem(estreita)
    try:
        assert temporario and caminho != estreita
        assert Image.open(caminho).size == (1280, 720)
    finally:
        caminho.unlink(missing_ok=True)
    caminho, temporario = ocr.preparar_imagem(larga)
    assert caminho == larga and not temporario


# --------------------------------------------------------------------------- N8
def _pasta_de_idiomas_do_app(destino: Path) -> Path:
    """Imita a pasta que o app cria ao baixar o português: só .traineddata, SEM a subpasta configs/."""
    import subprocess
    saida = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    origem = Path(re.search(r'in "(.*?)"', saida.stdout + saida.stderr).group(1))
    destino.mkdir()
    shutil.copy(origem / "eng.traineddata", destino / "eng.traineddata")
    return destino


@requer_tesseract
def test_n8_ocr_funciona_com_a_pasta_de_idiomas_do_app(tmp_path):
    """Na v0.1.5 o modo 'tsv' era procurado em <pasta>/configs/tsv; sem ele o Tesseract devolvia texto
    comum, o filtro lia como vazio e TODAS as capturas eram descartadas em silêncio."""
    img, esperadas = _captura_pequena(tmp_path / "cap_000000.jpg")
    estado = ocr.EstadoOCR(True, shutil.which("tesseract"), True, _pasta_de_idiomas_do_app(tmp_path / "idiomas"),
                           "", idiomas="eng")
    lidas = set(re.findall(r"[a-z]{3,}", ocr.ler_imagem(estado, img).lower()))
    assert len(esperadas & lidas) >= 3, sorted(lidas)


def test_n8_saida_que_nao_e_tsv_vira_erro_explicito_e_nao_texto_vazio(tmp_path, monkeypatch):
    import subprocess
    from PIL import Image
    img = tmp_path / "cap.jpg"
    Image.new("RGB", (640, 360), "white").save(img)
    monkeypatch.setattr(ocr, "rodar", lambda cmd, **k: subprocess.CompletedProcess(
        cmd, 0, stdout=b"texto comum, nao tsv\n", stderr=b"read_params_file: Can't open tsv"))
    estado = ocr.EstadoOCR(True, "x", True, None, "", idiomas="eng")
    with pytest.raises(ocr.ErroOCR, match="formato"):
        ocr.ler_imagem(estado, img)


def test_n8_cabecalho_diz_quando_o_ocr_rodou_e_nao_achou_nada(tmp_path):
    kw = dict(titulo="t", origem="t.mp4", duracao=60, modelo="m", preset="p",
              paragrafos=[Paragrafo(0, "Fala.")], destino=tmp_path / "t.md")
    md, _ = markdown.montar(telas=[], capturas_lidas=548, **kw)
    assert "nenhum texto aproveitável em 548 capturas" in md
    md, _ = markdown.montar(telas=[], **kw)
    assert "- **Texto de tela (OCR):** não\n" in md


@requer_ffmpeg
def test_n8_rodada_informa_quantas_capturas_foram_lidas(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4", [("Slide um\nIntroducao", 5), ("Slide dois\nMedidas", 5)],
                cores=[(255, 255, 255), (200, 230, 255)])
    chamadas = []
    monkeypatch.setattr(ocr, "verificar", lambda: ocr.EstadoOCR(True, "x", True, None, "", idiomas="eng"))
    monkeypatch.setattr(ocr, "ler_imagem", lambda estado, img: chamadas.append(img) or "")
    eventos = []
    proj = Projeto(Config(videos, saida, ocr=True))
    proj.executar(proj.escanear(), eventos.append)
    (fim,) = [e.dados for e in eventos if e.tipo == "video_fim"]
    assert fim["capturas_lidas"] == len(chamadas) > 0
    md = proj.caminho_md("a.mp4").read_text(encoding="utf-8")
    assert f"nenhum texto aproveitável em {len(chamadas)} capturas" in md


# --------------------------------------------------------------------------- N2 e N3
def _ocr_falso(monkeypatch, respostas: list[str]):
    """OCR simulado: devolve uma resposta por captura, na ordem."""
    monkeypatch.setattr(ocr, "verificar", lambda: ocr.EstadoOCR(True, "x", True, None, "", idiomas="eng"))
    fila = iter(respostas)
    monkeypatch.setattr(ocr, "ler_imagem", lambda estado, img: next(fila, ""))


TELA_A = "Faturamento total do periodo consolidado"
TELA_B = "Margem media mensal por regiao do pais"


@requer_ffmpeg
def test_n2_palavras_conta_so_a_fala_e_palavras_tela_conta_o_resto(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4",
                [("Slide um\nIntroducao", 5), ("Slide dois\nMedidas", 5), ("Slide tres\nFim", 5)],
                cores=[(255, 255, 255), (200, 230, 255), (255, 240, 200)])
    _ocr_falso(monkeypatch, [TELA_A, "", TELA_B])
    proj = Projeto(Config(videos, saida, ocr=True))
    proj.executar(proj.escanear(), lambda e: None)
    linha = proj.registro.linhas["a.mp4"]
    md = proj.caminho_md("a.mp4").read_text(encoding="utf-8")
    fala = " ".join(re.findall(r"\*\*\[\d\d:\d\d:\d\d\]\*\* (.*)", md))
    assert linha.palavras == len(fala.split()), "palavras deve contar só a fala"
    assert linha.palavras_tela == len(TELA_A.split()) + len(TELA_B.split())
    assert f"- **Palavras de fala:** {linha.palavras}" in md
    assert f"- **Palavras de texto de tela:** {linha.palavras_tela}" in md


@requer_ffmpeg
def test_n3_capturas_sem_uso_sao_apagadas_depois_do_ocr(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "a.mp4",
                [("Slide um\nIntroducao", 5), ("Slide dois\nMedidas", 5), ("Slide tres\nFim", 5)],
                cores=[(255, 255, 255), (200, 230, 255), (255, 240, 200)])
    _ocr_falso(monkeypatch, [TELA_A, "", TELA_B])
    proj = Projeto(Config(videos, saida, ocr=True))
    proj.executar(proj.escanear(), lambda e: None)
    md = proj.caminho_md("a.mp4").read_text(encoding="utf-8")
    citadas = set(re.findall(r"\(\.\./capturas/[^/]+/(cap_[^)]+\.jpg)\)", md))
    em_disco = {p.name for p in (saida / "capturas").rglob("*.jpg")}
    assert len(citadas) == 2
    assert em_disco == citadas, f"sobraram capturas sem uso: {sorted(em_disco - citadas)}"


# --------------------------------------------------------------------------- N7
def test_n7_md_antigo_com_espaco_no_link_tambem_funciona_na_base(tmp_path):
    """.md gerados até a v0.1.4 guardam o link com espaço cru; a base tem de corrigi-los também."""
    from transcritor import consolidacao
    saida = tmp_path / "saida"
    img = saida / "capturas" / "Módulo 01" / "aula 1" / "cap_000004.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"jpg")
    md = saida / "transcricoes_md" / "Módulo 01" / "aula 1.md"
    md.parent.mkdir(parents=True)
    md.write_text("fala\n\n> tela · [captura](../../capturas/Módulo 01/aula 1/cap_000004.jpg)", encoding="utf-8")
    base = saida / "base_consolidada"
    (gerado,) = consolidacao.consolidar([("Módulo 01/aula 1.mp4", md)], base, 1000)
    from urllib.parse import unquote
    link = gerado.read_text(encoding="utf-8").split("[captura](")[1].split(")")[0]
    assert (base / unquote(link)).resolve() == img.resolve(), link


@requer_ffmpeg
def test_n7_links_de_capturas_em_pasta_com_espaco_e_acento_funcionam_na_base_e_no_pacote(
        tmp_path, modelo_falso, monkeypatch):
    from urllib.parse import unquote
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "Módulo 01" / "aula 1.mp4",
                [("Slide um\nIntroducao", 5), ("Slide dois\nMedidas", 5)],
                cores=[(255, 255, 255), (200, 230, 255)])
    _ocr_falso(monkeypatch, [TELA_A, TELA_B])
    proj = Projeto(Config(videos, saida, ocr=True))
    proj.executar(proj.escanear(), lambda e: None)

    (base_md,) = (saida / "base_consolidada").glob("base_*.md")
    links = re.findall(r"\[captura\]\(([^)\n]+)\)", base_md.read_text(encoding="utf-8"))
    assert len(links) == 2
    assert all(" " not in l for l in links), "espaço quebra link Markdown: tem de ir codificado"
    assert all((base_md.parent / unquote(l)).is_file() for l in links), links

    (pasta,) = proj.gerar_pacotes()
    (md_pacote,) = pasta.glob("*.md")
    links = re.findall(r"\[captura\]\(([^)\n]+)\)", md_pacote.read_text(encoding="utf-8"))
    assert len(links) == 2 and all((pasta / unquote(l)).is_file() for l in links), links


# --------------------------------------------------------------------------- N5 e N6
def test_n5_resumo_sem_pendentes_nao_fala_em_minutos():
    from transcritor.gui.textos import resumo_da_leitura
    texto = resumo_da_leitura(concluidos=1, pendentes=0, segundos_pendentes=0)
    assert texto == "1 concluído(s) · nenhum pendente"
    assert "min" not in texto


def test_n5_resumo_com_pendentes_mostra_o_tempo():
    from transcritor.gui.textos import resumo_da_leitura
    assert resumo_da_leitura(2, 3, 5400) == "2 concluído(s) · 3 pendente(s), 1 h 30 min de vídeo"


def test_n8_coluna_texto_da_tela_nao_diz_lido_quando_nao_achou_nada():
    from transcritor.gui.textos import rotulo_tela
    assert rotulo_tela("sim", 100) == "lido (100)"
    assert rotulo_tela("sim", 0) == "nada encontrado"
    assert rotulo_tela("nao", 0) == "—" and rotulo_tela("falhou", 0) == "⚠ não lido"


def test_n6_rotulo_do_tesseract_avisa_do_download_do_portugues():
    from transcritor.gui.textos import rotulo_tesseract
    assert rotulo_tesseract(disponivel=True, tem_portugues=True) == "Tesseract pronto."
    sem_pt = rotulo_tesseract(disponivel=True, tem_portugues=False)
    assert "português" in sem_pt and "baixado" in sem_pt
    assert "não instalado" in rotulo_tesseract(disponivel=False, tem_portugues=False)


# --------------------------------------------------------------------------- cabeçalho "para IA"
def test_md_explica_como_ler_o_arquivo(tmp_path):
    md, _ = markdown.montar(
        titulo="t", origem="t.mp4", duracao=120, modelo="m", preset="p",
        paragrafos=[Paragrafo(0, "Fala um."), Paragrafo(60, "Fala dois.")],
        telas=[Tela(30, "Texto da tela aqui com letras suficientes", None)], destino=tmp_path / "t.md")
    cab = md.split("---")[0]
    assert "Como ler este arquivo" in cab
    assert "[hh:mm:ss]" in cab and "OCR" in cab
    assert "não há descrição" in cab.lower()
    assert "notebooklm" not in md.lower()


# --------------------------------------------------------------------------- pacote para IA
@requer_ffmpeg
def test_pacote_para_ia_tem_md_e_so_as_capturas_citadas(tmp_path, modelo_falso, monkeypatch):
    videos, saida = tmp_path / "v", tmp_path / "s"
    criar_video(videos / "Mod 1" / "aula.mp4",
                [("Slide um\nIntroducao", 5), ("Slide dois\nMedidas", 5), ("Slide tres\nFim", 5)],
                cores=[(255, 255, 255), (200, 230, 255), (255, 240, 200)])
    _ocr_falso(monkeypatch, [TELA_A, "", TELA_B])
    proj = Projeto(Config(videos, saida, ocr=True))
    proj.executar(proj.escanear(), lambda e: None)
    original = proj.caminho_md("Mod 1/aula.mp4").read_text(encoding="utf-8")

    pacotes = proj.gerar_pacotes()

    assert len(pacotes) == 1
    pasta = pacotes[0]
    assert pasta.parent == saida / "pacote_para_ia"
    mds = list(pasta.glob("*.md"))
    assert len(mds) == 1
    texto = mds[0].read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+\.jpg)\)", texto)
    assert len(links) == 2 and all((pasta / l).is_file() for l in links)
    assert {p.name for p in (pasta / "imagens").iterdir()} == {Path(l).name for l in links}
    assert proj.caminho_md("Mod 1/aula.mp4").read_text(encoding="utf-8") == original, "o .md original não muda"
    with zipfile.ZipFile(pasta.with_suffix(".zip")) as z:
        assert mds[0].name in z.namelist()
    # gerar de novo não acumula lixo nem falha
    assert proj.gerar_pacotes() == pacotes
    assert len(list(pasta.glob("*.md"))) == 1


def test_pacote_para_ia_sem_nada_concluido_nao_cria_pasta(tmp_path):
    proj = Projeto(Config(tmp_path / "v", tmp_path / "s"))
    assert proj.gerar_pacotes() == []
    assert not (tmp_path / "s" / "pacote_para_ia").exists()


# ----------------------------------------------------------------------------- N9: ruído do OCR


def test_n9_linhas_ilegiveis_somem_e_rotulos_curtos_ficam():
    bloco = "Compartilhar\nEs Ou ou mu ou\nvoe 8\nOpus 47\nCriar instruções para o projeto\n* SB* OD é"
    assert ocr.limpar(bloco).splitlines() == ["Compartilhar", "Opus 47", "Criar instruções para o projeto"]


def test_n9_bloco_dominado_por_ruido_e_descartado():
    ruido = "Oy o GD 4\nen há 3 do chat\npara Ge qu rem\nCara\nme en\nTe Ye"
    assert ocr.limpar(ruido + "\nCivilizações antigas que sumiram") == ""
    assert not ocr.e_util(ocr.limpar(ruido))


def test_n9_bloco_limpo_nao_muda():
    texto = "AGENTE ROTEIRISTA — Teoria conspiratória\nCrie um roteiro sobre uma teoria absurda"
    assert ocr.limpar(texto) == texto


# ----------------------------------------------------------------------------- N11: aprender com vídeos longos


def _linha(rel, dur, vel, seg_ocr=0.0):
    from transcritor.registro import Linha
    return Linha(rel, status="ok", preset="equilibrado", velocidade=vel, duracao_s=dur,
                 ocr="sim" if seg_ocr else "nao", seg_ocr=seg_ocr)


def test_n11_video_curto_nao_entra_na_estimativa(tmp_path):
    from transcritor.registro import Registro
    r = Registro(tmp_path / "r.csv")
    r.linhas["curto"] = _linha("curto", 42, 1.2, seg_ocr=30)
    assert r.velocidade_medida("equilibrado") is None
    assert r.ocr_por_hora_medido() is None
    r.linhas["longo"] = _linha("longo", 2200, 1.7, seg_ocr=350)
    assert abs(r.velocidade_medida("equilibrado") - 1.7) < 1e-9
    assert abs(r.ocr_por_hora_medido() - 350 / (2200 / 3600)) < 1e-6


def test_n11_velocidade_pesa_pela_duracao(tmp_path):
    from transcritor.registro import Registro
    r = Registro(tmp_path / "r.csv")
    r.linhas["a"] = _linha("a", 600, 1.0)    # 600 s de vídeo em 600 s
    r.linhas["b"] = _linha("b", 3600, 2.0)   # 3600 s de vídeo em 1800 s
    # total: 4200 s de vídeo em 2400 s reais = 1,75x (a mediana simples daria 1,5x)
    assert abs(r.velocidade_medida("equilibrado") - 1.75) < 1e-9
