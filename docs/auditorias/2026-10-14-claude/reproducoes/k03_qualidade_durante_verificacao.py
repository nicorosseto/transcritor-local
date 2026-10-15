"""K3: trocar a qualidade e VOLTAR (ou trocar logo ao abrir) antes da verificação terminar: a janela fica
presa em "Verificando o PC..." e a página Preparação mostra o modelo de OUTRA qualidade. Código real; só
a verificação é simulada com 0,3 s de atraso, como em ferramentas/fumaca/maquina_limpa.py.

Rodar na raiz: xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k03_qualidade_durante_verificacao.py"""
import sys, time
from types import SimpleNamespace
sys.path.insert(0, ".")
from transcritor.config import PRESETS
from transcritor.gui import app as A
from transcritor.gui.verificacao import Situacao

pedidos = []
def verificar_falso(preset, saida):
    pedidos.append(preset)
    time.sleep(0.3)
    return Situacao(modelo=PRESETS[preset]["modelo"], modelo_baixado=True,
                    diagnostico=SimpleNamespace(itens=[], preset_recomendado="equilibrado", dispositivo="cpu"))
A.verificar = verificar_falso
import transcritor.gui.verificacao as V
V.verificar = verificar_falso
app = A.App()
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)

# Cenário A: Equilibrado (pronto) -> Rápido -> Equilibrado, rápido (antes da 1ª verificação voltar)
bombear(3, lambda: app.situacao)
assert app.situacao.modelo == "large-v3-turbo"
app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._opcoes_mudaram()
app.seg_preset.set(PRESETS["equilibrado"]["rotulo"]); app._opcoes_mudaram()
bombear(4)
print("A: pedidos de verificação:", pedidos)
print("A: situacao:", app.situacao, "| lateral:", repr(app.lbl_lat_titulo.cget("text")))

# Cenário B: abrir o app e trocar a qualidade antes de a verificação inicial terminar
app.destroy(); pedidos.clear()
app = A.App()
bombear(0.5)  # a verificação inicial (Equilibrado) já foi disparada aos 400 ms
app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._opcoes_mudaram()
bombear(4)
print("B: pedidos de verificação:", pedidos)
print("B: situacao:", app.situacao, "| lateral:", repr(app.lbl_lat_titulo.cget("text")))
# a página Preparação, com situacao None, não redesenha; "Verificar de novo" usa o preset antigo do painel
app._mostrar_pagina("preparacao"); bombear(0.3)
print("B: painel.preset =", app.painel_verif.preset, "| qualidade na tela =", app._preset())
app.painel_verif._reverificar(); bombear(2)
print("B: depois de 'Verificar de novo': pedidos:", pedidos, "| situacao:", app.situacao)
textos = []
def coletar(w):
    for f in w.winfo_children():
        try: textos.append(str(f.cget("text")))
        except Exception: pass
        coletar(f)
coletar(app.painel_verif)
print("B: cartão do modelo no painel:", [t for t in textos if "Modelo de transcrição" in t])
app.destroy()
