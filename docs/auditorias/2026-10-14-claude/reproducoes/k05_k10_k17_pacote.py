"""K5, K17 e K10: Pacote para IA. (a) arquivo de FORA da pasta de saída entra no .zip quando o .md tem um link
[captura](...) apontando para fora (texto de tela lido pelo OCR ou link editado); (b) colisão de nomes de
pacote; (c) links com espaço, acento, parênteses e '#'.

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k05_k10_k17_pacote.py
"""
import sys, tempfile, zipfile
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, ".")
from transcritor import markdown, ocr, pacote
from transcritor.transcricao import Paragrafo

tmp = Path(tempfile.mkdtemp())
saida = tmp / "saida"; md_dir = saida / "transcricoes_md"; md_dir.mkdir(parents=True)
segredo = tmp / "fora_da_saida" / "segredo.txt"; segredo.parent.mkdir(); segredo.write_text("CONFIDENCIAL")

# (a1) texto de tela que o OCR leu de um slide (ex.: aula sobre Markdown) contendo um link de captura
linha_slide = f"Exemplo de link: [captura]({segredo.as_posix()}) clique para abrir a imagem"
print("(a) ocr.limpar mantém a linha do slide?", ocr.limpar(linha_slide) == linha_slide,
      "| e_util:", ocr.e_util(ocr.limpar(linha_slide)))
destino = md_dir / "aula.md"
conteudo, _ = markdown.montar(titulo="aula", origem="aula.mp4", duracao=60, modelo="small", preset="rapido",
                              paragrafos=[Paragrafo(0.0, "fala qualquer")],
                              telas=[markdown.Tela(10.0, ocr.limpar(linha_slide), None)], destino=destino)
markdown.salvar(conteudo, destino)
p = pacote.montar(destino, saida / "pacote_para_ia", "aula")
with zipfile.ZipFile(str(p) + ".zip") as z:
    print("(a1) zip:", z.namelist(), "| conteúdo copiado:", [z.read(n).decode() for n in z.namelist() if n.startswith("imagens/")])

# (a2) link relativo com ../ editado no .md
destino2 = md_dir / "aula2.md"
destino2.write_text("> 🖼️ **Na tela [00:00:10]** · [captura](../../fora_da_saida/segredo.txt)\n", encoding="utf-8")
p2 = pacote.montar(destino2, saida / "pacote_para_ia", "aula2")
with zipfile.ZipFile(str(p2) + ".zip") as z:
    print("(a2) zip:", z.namelist())

# (b) colisão: chave 'Mod 1/aula' e chave 'Mod 1 - aula' (vídeo na raiz com esse nome)
m1 = md_dir / "Mod 1" / "aula.md"; m1.parent.mkdir(); m1.write_text("# Mod 1/aula\nTEXTO DO MÓDULO 1\n", encoding="utf-8")
m2 = md_dir / "Mod 1 - aula.md"; m2.write_text("# Mod 1 - aula\nOUTRO VÍDEO\n", encoding="utf-8")
r1 = pacote.montar(m1, saida / "pacote_para_ia", "Mod 1/aula")
r2 = pacote.montar(m2, saida / "pacote_para_ia", "Mod 1 - aula")
print("(b) mesmo destino:", r1 == r2, r1.name, "| conteúdo final:", (r1 / f"{r1.name}.md").read_text(encoding="utf-8").splitlines()[1])

# (c) link de captura com espaço, acento, parênteses e '#'
for chave in ("Módulo 01/Aula (1) – introdução", "Aula #3"):
    img = saida / "capturas" / chave / "cap_000010.jpg"; img.parent.mkdir(parents=True, exist_ok=True); img.write_bytes(b"jpg")
    d = md_dir / (chave + ".md"); d.parent.mkdir(parents=True, exist_ok=True)
    bloco = markdown._bloco_tela(markdown.Tela(10.0, "texto", img), d)
    alvo = bloco.splitlines()[0].split("](")[1][:-1]
    u = urlsplit(alvo)
    print(f"(c) {chave!r}: link={alvo!r} -> caminho que um leitor de Markdown abre={u.path!r} fragmento={u.fragment!r}",
          "| existe:", (d.parent / __import__('urllib.parse').parse.unquote(u.path)).is_file())
