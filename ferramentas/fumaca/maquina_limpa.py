"""Fumaça: achados do teste em máquina limpa (Windows Sandbox).

N18: trocar a qualidade confere de novo o modelo (o cartão nunca mostra o modelo de outra qualidade).
N19: escolher a pasta de saída relê a pasta sozinho, sem apagar a lista.
N17: em tela pequena (1024x768) os botões e as colunas Duração/Status continuam à vista.

Uso: xvfb-run -a -s "-screen 0 1024x768x24" python3.12 ferramentas/fumaca/maquina_limpa.py"""
import sys, time, tempfile
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video
from transcritor.config import PRESETS
from transcritor.gui import app as A
from transcritor.gui.verificacao import Situacao

pedidos = []
def verificar_falso(preset, saida):
    pedidos.append(preset)
    time.sleep(0.3)  # a verificação real demora: dá tempo de trocar a qualidade no meio
    return Situacao(modelo=PRESETS[preset]["modelo"], modelo_baixado=False,
                    obrigatorios=["Modelo de transcrição"],
                    diagnostico=SimpleNamespace(itens=[], preset_recomendado="rapido", dispositivo="cpu"))
A.verificar = verificar_falso
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/a.mp4", [("a", 3)]); criar_video(tmp/"v/b.mp4", [("b", 3)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time()+seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)

# ---- N18
bombear(3, lambda: app.situacao)
assert app.situacao.modelo == "large-v3-turbo", app.situacao.modelo
rotulo = {v: k for k, v in A.ROTULO_PRESET.items()}
app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._opcoes_mudaram()
assert app.situacao is None, "o cartão antigo continuou valendo"
app.seg_preset.set(PRESETS["preciso"]["rotulo"]); app._opcoes_mudaram()   # troca rápida no meio
app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._opcoes_mudaram()
bombear(3, lambda: app.situacao and len(pedidos) >= 3)
bombear(1)
assert app.situacao.modelo == "small", app.situacao.modelo
app._mostrar_pagina("preparacao"); bombear(0.3)
textos = []
def coletar(w):
    for f in w.winfo_children():
        try: textos.append(f.cget("text"))
        except Exception: pass
        coletar(f)
coletar(app.painel_verif)
assert any("Rápido: small" in str(t) for t in textos), textos
assert any(str(t).startswith("Baixar small (~0,5 GB)") for t in textos), textos
assert not any("large-v3-turbo" in str(t) for t in textos), "ainda mostra o modelo do Equilibrado"
print("N18 OK")

# ---- N19
app._mostrar_pagina("videos")
escolhas = iter([str(tmp/"v"), str(tmp/"saida-escolhida")])
A.filedialog.askdirectory = lambda **k: next(escolhas)
app._escolher_videos()
app._escolher_saida()          # escolhida enquanto a primeira leitura ainda roda
bombear(8, lambda: app.projeto and app.projeto.cfg.pasta_saida == tmp/"saida-escolhida" and not app._lendo)
assert app.projeto is not None, "a lista sumiu depois de escolher a saída"
assert app.projeto.cfg.pasta_saida == tmp/"saida-escolhida", app.projeto.cfg.pasta_saida
assert len(app.itens) == 2
print("N19 OK")

# ---- N17
bombear(0.5)
larg = {c: app.tabela.column(c, "width") for c in ("sel", "video", "dur", "status")}
assert sum(larg.values()) <= app.tabela.winfo_width() + 12, (larg, app.tabela.winfo_width())
assert all(b.winfo_width() >= 80 for b in app.btns_marcar), [b.winfo_width() for b in app.btns_marcar]
print("N17 OK", app.winfo_width(), "px de janela,", larg)
app._fechar(); bombear(0.3)
print("MAQUINA LIMPA GUI OK")
