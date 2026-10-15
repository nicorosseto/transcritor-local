"""K4 (e área 2): OCR com o Tesseract do sistema e com uma pasta de idiomas "do app" (só .traineddata, sem
configs/), e o filtro ocr.limpar diante de linhas reais de slide.

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k04_ocr.py
"""
import os, shutil, subprocess, sys, tempfile
os.environ.setdefault("XDG_DATA_HOME", tempfile.mkdtemp())  # não mexe na pasta do usuário
from pathlib import Path
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont
from transcritor import ocr

tmp = Path(tempfile.mkdtemp())
SLIDE = ["Introdução ao Power BI", "1. O que é DAX?", "2. Medidas e colunas", "SQL, API e ETL",
         "R$ 1.500 por mês", "Dia 3: o que é IA", "CALCULATE(SUM(Vendas[Valor]))"]
def slide(destino, largura):
    img = Image.new("RGB", (largura, int(largura * 9 / 16)), "white")
    d = ImageDraw.Draw(img); f = ImageFont.load_default(size=largura // 28)
    for i, l in enumerate(SLIDE):
        d.text((largura // 20, largura // 30 + i * largura // 18), l, fill="black", font=f)
    img.save(destino); return destino

exe = shutil.which("tesseract")
print("tesseract:", subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.splitlines()[0])
img_larga, img_estreita = slide(tmp / "larga.jpg", 1280), slide(tmp / "estreita.jpg", 640)

sistema = ocr.verificar()
print("verificar():", sistema.disponivel, sistema.tem_portugues, sistema.pasta_tessdata, sistema.idiomas)
app_dir = tmp / "tessdata_app"; app_dir.mkdir()
for l in ("por", "eng"):
    shutil.copy(f"/usr/share/tesseract-ocr/5/tessdata/{l}.traineddata", app_dir)
estado_app = ocr.EstadoOCR(True, exe, True, app_dir, "app")

for rotulo, est in (("sistema", sistema), ("pasta do app", estado_app)):
    for img in (img_larga, img_estreita):
        bruto = ocr.ler_imagem(est, img)
        print(f"[{rotulo} | {img.name}] TSV ok, {len(bruto.splitlines())} linhas brutas")
        print("   bruto :", bruto.splitlines())
        print("   limpo :", ocr.limpar(bruto).splitlines())

# N8: a configuração "tsv" antiga, na pasta do app sem configs/, devolvia texto comum
r = subprocess.run([exe, "--tessdata-dir", str(app_dir), str(img_larga), "stdout", "-l", "por+eng", "tsv"],
                   capture_output=True, text=True)
print("config 'tsv' antiga na pasta do app -> começa com 'level'?", r.stdout.startswith("level"), "| stderr:", r.stderr.strip()[:80])

# pasta do app só com por (inglês não baixado): verificar() diria "por+eng"
so_por = tmp / "so_por"; so_por.mkdir(); shutil.copy(app_dir / "por.traineddata", so_por)
try:
    t = ocr.ler_imagem(ocr.EstadoOCR(True, exe, True, so_por, "app"), img_larga)
    print("pasta do app sem eng: leu", len(t.splitlines()), "linhas (sem erro)")
except ocr.ErroOCR as e:
    print("pasta do app sem eng: ErroOCR:", e)

print("\nFiltro linha a linha (linha_legivel):")
for l in SLIDE + ["Es Ou ou mu ou", "voe 8"]:
    print(f"   {ocr.linha_legivel(l)!s:5}  {l}")
print("bloco inteiro do slide ->", ocr.limpar("\n".join(SLIDE)).splitlines())
lista = "Agenda\n1. O que é IA\n2. Uso no dia a dia\n3. Dúvidas\nSQL e BI"
print("bloco 'Agenda' ->", repr(ocr.limpar(lista)), "| e_util:", ocr.e_util(ocr.limpar(lista)))
