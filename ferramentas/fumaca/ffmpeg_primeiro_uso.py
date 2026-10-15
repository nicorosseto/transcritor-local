"""Fumaça: primeiro uso sem FFmpeg (ADR-021). A Preparação mostra "Baixar FFmpeg", baixa com barra,
confere o SHA-256, extrai na pasta do usuário e verifica de novo.

Usa um pacote falso servido por file:// (não baixa nada da internet).
Uso: xvfb-run -a -s "-screen 0 1366x768x24" python3.12 ferramentas/fumaca/ffmpeg_primeiro_uso.py"""
import hashlib, os, sys, tempfile, time, zipfile
from pathlib import Path
from types import SimpleNamespace
tmp = Path(tempfile.mkdtemp())
os.environ["XDG_DATA_HOME"] = str(tmp / "dados"); os.environ["LOCALAPPDATA"] = str(tmp / "dados")
sys.path.insert(0, ".")
from transcritor import preparacao
from transcritor.gui import app as A, verificacao as V
from transcritor.config import PRESETS

z = tmp / "ff.zip"
with zipfile.ZipFile(z, "w") as f:
    for n in ("bin/ffmpeg.exe", "bin/ffprobe.exe", "LICENSE"):
        f.writestr(f"ffmpeg-x/{n}", "x" * 300_000)
dados = z.read_bytes()
preparacao.FFMPEG.update(url=z.as_uri(), sha256=hashlib.sha256(dados).hexdigest(), tamanho=len(dados))
preparacao.ffmpeg_baixavel = lambda: True
A.App._verificacao_inicial = lambda self: None
def verificar(preset, saida):
    ok = (preparacao.pasta_ffmpeg() / "bin" / "ffmpeg.exe").is_file()
    return V.Situacao(modelo=PRESETS[preset]["modelo"], ffmpeg_ok=ok, ffmpeg_baixado=ok,
                      obrigatorios=[] if ok else ["FFmpeg"],
                      diagnostico=SimpleNamespace(itens=[], preset_recomendado="equilibrado", dispositivo="cpu"))
A.verificar = verificar
app = A.App()
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(.03)
app._rodar_verificacao(); bombear(3, lambda: app.situacao); app._mostrar_pagina("preparacao"); bombear(.3)
def botoes(w, acc):
    for f in w.winfo_children():
        try:
            if str(f.cget("text")).startswith("Baixar FFmpeg"): acc.append(f)
        except Exception: pass
        botoes(f, acc)
    return acc
b = botoes(app.painel_verif, [])
assert b, "sem botão Baixar FFmpeg"
print("botão:", b[0].cget("text"))
b[0].invoke()
bombear(10, lambda: app.situacao and app.situacao.ffmpeg_ok)
assert app.situacao.ffmpeg_ok, "não verificou de novo depois do download"
assert (preparacao.pasta_ffmpeg() / "ORIGEM.txt").is_file()
textos = []
def coletar(w):
    for f in w.winfo_children():
        try: textos.append(str(f.cget("text")))
        except Exception: pass
        coletar(f)
coletar(app.painel_verif)
assert any("Baixado pelo app" in t for t in textos), textos
print("FFmpeg baixado e reconhecido")
app._fechar(); bombear(.3)
print("FFMPEG PRIMEIRO USO GUI OK")
