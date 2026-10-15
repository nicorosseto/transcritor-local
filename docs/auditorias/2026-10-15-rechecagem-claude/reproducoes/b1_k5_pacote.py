"""Rechecagem de 15/10/2026. Rodar na raiz: python3.12 docs/auditorias/2026-10-15-rechecagem-claude/reproducoes/b1_k5_pacote.py

Rechecagem B1/K5: os casos de 2026-10-14/reproducoes.py e k05_k10_k17_pacote.py, adaptados à nova assinatura
de pacote.montar (raiz_capturas). Cada link vai na LINHA DE CABEÇALHO que o app escreve, para que o regex case e a
defesa testada seja o confinamento (não só o regex)."""
import os, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, ".")
from transcritor import markdown, ocr, pacote
from transcritor.transcricao import Paragrafo

def cab(alvo, t="00:00:10"):
    return f"> 🖼️ **Na tela [{t}]** · [captura]({alvo})\n> texto\n"

tmp = Path(tempfile.mkdtemp()); saida = tmp / "saida"
capt = saida / "capturas" / "Módulo 01"; capt.mkdir(parents=True)
md = saida / "transcricoes_md" / "Módulo 01" / "aula.md"; md.parent.mkdir(parents=True)
fora_txt = tmp / "fora.txt"; fora_txt.write_text("FORA")
fora_jpg = tmp / "fora.jpg"; fora_jpg.write_bytes(b"\xff\xd8FORA")
leg = capt / "área com espaço.jpg"; leg.write_bytes(b"\xff\xd8LEGITIMA")
raiz = saida / "capturas"
(capt / "atalho.jpg").symlink_to(fora_jpg)
os.link(fora_jpg, capt / "hardlink.jpg")           # hardlink: mesmo inode, fica "dentro" da pasta
(saida / "transcricoes_md" / "solto.jpg").write_bytes(b"\xff\xd8MD")  # imagem fora de capturas/, dentro da saída
(capt / "nao_imagem.txt").write_text("TXT")

casos = {
    "legitima": "../../capturas/M%C3%B3dulo%2001/%C3%A1rea%20com%20espa%C3%A7o.jpg",
    "dotdot_txt (Codex)": "../../../fora.txt",
    "dotdot_jpg": "../../../fora.jpg",
    "dotdot_por_dentro": "../../capturas/M%C3%B3dulo%2001/../../../fora.jpg",
    "absoluto": fora_jpg.as_posix(),
    "file_uri": "file://" + fora_jpg.as_posix(),
    "pct2e": "%2e%2e/%2e%2e/%2e%2e/fora.jpg",
    "barra_invertida": "..\\..\\..\\fora.jpg",
    "drive_windows": "C:/Windows/x.jpg",
    "unc": "\\\\servidor\\c$\\x.jpg",
    "symlink_para_fora": "../../capturas/M%C3%B3dulo%2001/atalho.jpg",
    "hardlink_para_fora": "../../capturas/M%C3%B3dulo%2001/hardlink.jpg",
    "imagem_na_saida_fora_de_capturas": "../solto.jpg",
    "nao_imagem_em_capturas": "../../capturas/M%C3%B3dulo%2001/nao_imagem.txt",
}
for nome, alvo in casos.items():
    md.write_text("# aula\n\n" + cab(alvo), encoding="utf-8")
    p = pacote.montar(md, saida / "pacote_para_ia", "x", raiz)
    with zipfile.ZipFile(str(p) + ".zip") as z:
        imgs = [n for n in z.namelist() if n.startswith("imagens/") and not n.endswith("/")]
        conteudo = [z.read(n)[:12] for n in imgs]
    print(f"{nome:34s} entrou no zip: {imgs} {conteudo}")

# K5 (a1): link no texto lido da tela (fora da linha de cabeçalho), via markdown.montar como no app
linha_slide = f"Exemplo de link: [captura]({fora_jpg.as_posix()}) clique para abrir a imagem"
conteudo, _ = markdown.montar(titulo="aula", origem="aula.mp4", duracao=60, modelo="small", preset="rapido",
                              paragrafos=[Paragrafo(0.0, "fala qualquer")],
                              telas=[markdown.Tela(10.0, ocr.limpar(linha_slide), leg)], destino=md)
markdown.salvar(conteudo, md)
p = pacote.montar(md, saida / "pacote_para_ia", "ocr", raiz)
with zipfile.ZipFile(str(p) + ".zip") as z:
    print("K5 a1 (link no texto de tela) zip:", z.namelist())
    print("   .md do pacote:", [l for l in z.read("ocr.md").decode().splitlines() if "captura" in l])
