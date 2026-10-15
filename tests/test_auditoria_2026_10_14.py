"""Achados das auditorias de 14/10/2026 (Codex: B1-B3, C1-C6; Claude: K1-K20) corrigidos antes da beta.

Os achados de interface (K1, C1, K3) têm fumaças em ferramentas/fumaca/auditoria_k1.py e auditoria_c1.py.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from transcritor import correcoes, markdown, ocr, pacote, util
from transcritor.registro import Linha, Registro
from transcritor.resultado import resumo_final


def _md_com_captura(saida: Path, link: str, extra: str = "") -> Path:
    md = saida / "transcricoes_md" / "Mod 1" / "aula.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("# aula\n\n**[00:00:00]** fala\n\n"
                  f"> 🖼️ **Na tela [00:00:10]** · [captura]({link})\n> texto\n{extra}", encoding="utf-8")
    return md


def _captura(saida: Path) -> Path:
    img = saida / "capturas" / "Mod 1" / "aula" / "cap_000010.jpg"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"\xff\xd8 jpeg falso")
    return img


def _conteudo_zip(pasta: Path) -> list[str]:
    with zipfile.ZipFile(pasta.with_suffix(".zip")) as z:
        return sorted(z.namelist())


# --------------------------------------------------------------------------- B1 / K5
def test_b1_pacote_leva_a_captura_legitima(tmp_path):
    saida = tmp_path / "s"
    _captura(saida)
    md = _md_com_captura(saida, "../../capturas/Mod%201/aula/cap_000010.jpg")
    pasta = pacote.montar(md, saida / "pacote_para_ia", "aula", saida / "capturas")
    assert "imagens/cap_000010.jpg" in _conteudo_zip(pasta)


@pytest.mark.parametrize("link", [
    "../../../fora.txt",                 # ../ para fora da saída
    "../../../fora.jpg",                 # imagem, mas fora da pasta de capturas
    "__ABSOLUTO__",                      # caminho absoluto
    "%2e%2e/%2e%2e/%2e%2e/fora.jpg",     # ../ codificado
    "file:///etc/passwd",                # endereço
])
def test_b1_pacote_recusa_arquivo_de_fora_das_capturas(tmp_path, link):
    saida = tmp_path / "s"
    _captura(saida)
    for nome in ("fora.txt", "fora.jpg"):
        (tmp_path / nome).write_text("CONFIDENCIAL", encoding="utf-8")
    if link == "__ABSOLUTO__":
        link = (tmp_path / "fora.jpg").as_posix()
    md = _md_com_captura(saida, link)
    pasta = pacote.montar(md, saida / "pacote_para_ia", "aula", saida / "capturas")
    assert [n for n in _conteudo_zip(pasta) if n.startswith("imagens/") and n != "imagens/"] == []


def test_b1_pacote_ignora_link_dentro_do_texto_lido_da_tela(tmp_path):
    saida = tmp_path / "s"
    (tmp_path / "segredo.jpg").write_text("CONFIDENCIAL", encoding="utf-8")
    # um slide que mostra um link Markdown: vira texto de tela, não cabeçalho de captura
    md = _md_com_captura(saida, "nada.jpg", extra=f"> [captura]({(tmp_path / 'segredo.jpg').as_posix()})\n")
    (saida / "capturas").mkdir(parents=True)
    pasta = pacote.montar(md, saida / "pacote_para_ia", "aula", saida / "capturas")
    assert not any("segredo" in n for n in _conteudo_zip(pasta))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="sem links simbólicos")
def test_b1_pacote_recusa_link_simbolico_que_sai_das_capturas(tmp_path):
    saida = tmp_path / "s"
    img = _captura(saida)
    fora = tmp_path / "fora.jpg"
    fora.write_text("CONFIDENCIAL", encoding="utf-8")
    img.unlink()
    try:
        img.symlink_to(fora)
    except OSError:
        pytest.skip("o sistema não deixou criar o link simbólico")
    md = _md_com_captura(saida, "../../capturas/Mod%201/aula/cap_000010.jpg")
    pasta = pacote.montar(md, saida / "pacote_para_ia", "aula", saida / "capturas")
    assert "imagens/cap_000010.jpg" not in _conteudo_zip(pasta)


# --------------------------------------------------------------------------- K17 / C6
def test_k17_nomes_que_colidem_ganham_sufixo(tmp_path):
    from transcritor.config import Config
    from transcritor.pipeline import Projeto
    from transcritor.registro import OK
    proj = Projeto(Config(tmp_path / "v", tmp_path / "s"))
    for rel, chave in (("Mod 1/aula.mp4", "Mod 1/aula"), ("Mod 1 - aula.mp4", "Mod 1 - aula")):
        proj.registro.linhas[rel] = Linha(rel, status=OK, saida=chave)
        md = proj.caminho_md(rel)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(f"# {rel}\n", encoding="utf-8")
    pastas = proj.gerar_pacotes()
    assert len(pastas) == 2 and len({p.name for p in pastas}) == 2
    assert all(p.with_suffix(".zip").is_file() for p in pastas)


# --------------------------------------------------------------------------- K10
@pytest.mark.parametrize("nome", ["Curso C#", "Aula #3", "O que é?"])
def test_k10_link_com_jogo_da_velha_e_interrogacao(tmp_path, nome):
    link = markdown.link_seguro(f"../capturas/{nome}/cap_000010.jpg")
    assert "#" not in link and "?" not in link
    from urllib.parse import unquote
    assert unquote(link) == f"../capturas/{nome}/cap_000010.jpg"


# --------------------------------------------------------------------------- K11
def test_k11_correcoes_em_ansi_nao_derrubam_a_rodada(tmp_path):
    (tmp_path / correcoes.NOME_ARQUIVO).write_bytes('{"trocar": {"Chatepte": "ChatGPT", "voc\xea": "você"}}'
                                                     .encode("cp1252"))
    regras, aviso = correcoes.carregar(tmp_path)
    assert regras.get("Chatepte") == "ChatGPT" and aviso == ""


def test_k11_correcoes_com_bytes_invalidos_viram_aviso(tmp_path):
    (tmp_path / correcoes.NOME_ARQUIVO).write_bytes(b'{"trocar": \x81\x8d\x8f\x90\x9d')
    regras, aviso = correcoes.carregar(tmp_path)
    assert regras == {} and "ignorado" in aviso


# --------------------------------------------------------------------------- K13 / K14 / C4
def test_k13_erro_que_nao_e_de_disco_nao_deixa_temporario(tmp_path):
    def escrever(p):
        p.write_text("meio", encoding="utf-8")
        raise UnicodeEncodeError("utf-8", "x", 0, 1, "teste")
    with pytest.raises(UnicodeEncodeError):
        util.gravar_atomico(tmp_path / "registro.csv", escrever)
    assert list(tmp_path.iterdir()) == []


def test_k14_download_do_idioma_interrompido_nao_deixa_parcial(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr, "_pasta_tessdata_app", lambda: tmp_path)

    class Resposta:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): raise ConnectionResetError("caiu")
    monkeypatch.setattr(ocr.urllib.request, "urlopen", lambda *a, **k: Resposta())
    with pytest.raises(ConnectionResetError):
        ocr.baixar_portugues()
    assert not list(tmp_path.glob("*.parcial"))


# --------------------------------------------------------------------------- K18
def test_k18_copia_pendente_presa_nao_vira_falso_registro_nao_salvo(tmp_path, monkeypatch):
    r = Registro(tmp_path / "registro.csv")
    r.linhas["a.mp4"] = Linha("a.mp4", saida="a")
    r.pendente.write_text("velho", encoding="utf-8")
    os.utime(r.pendente, (1, 1))  # mais antiga que o registro que será salvo
    unlink_real = Path.unlink

    def unlink(self, missing_ok=False):
        if self.name == Registro.NOME_PENDENTE:
            raise PermissionError("aberto no Excel")
        return unlink_real(self, missing_ok=missing_ok)
    monkeypatch.setattr(Path, "unlink", unlink)
    r.salvar()  # não levanta
    assert (tmp_path / "registro.csv").is_file()
    assert "foi salvo" in r.aviso


@pytest.mark.parametrize("resumo", [{"ok": 1, "erro": 1, "registro_nao_salvo": "x"},
                                    {"ok": 1, "cancelado": True, "registro_nao_salvo": "x"}])
def test_k18_registro_nao_salvo_aparece_em_qualquer_desfecho(resumo):
    assert "registro.csv" in resumo_final(resumo)[1]
