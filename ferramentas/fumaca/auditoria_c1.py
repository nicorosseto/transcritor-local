"""Fumaça: C1 (auditoria do Codex, 14/10). "Verificar de novo" lenta + troca de qualidade no meio:
o cartão nunca mostra o modelo de outra qualidade quando a verificação antiga termina por último.

Uso: xvfb-run -a -s "-screen 0 1366x768x24" python3.12 ferramentas/fumaca/auditoria_c1.py"""
import sys, time, threading
from types import SimpleNamespace
sys.path.insert(0, ".")
from transcritor.gui import app as A, verificacao as V
from transcritor.config import PRESETS
A.App._verificacao_inicial = lambda self: None
def situacao(preset):
    return V.Situacao(modelo=PRESETS[preset]["modelo"], modelo_baixado=False, obrigatorios=["Modelo"],
                      diagnostico=SimpleNamespace(itens=[], preset_recomendado="rapido", dispositivo="cpu"))
liberar, iniciou, chamadas = threading.Event(), threading.Event(), []
def verificar(preset, saida):
    chamadas.append(preset)
    if len(chamadas) == 1:          # a primeira ("Verificar de novo" em Rápido) demora
        iniciou.set(); liberar.wait(10)
    return situacao(preset)
A.verificar = verificar
app = A.App()
def bombear(seg):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        app.update(); time.sleep(.02)
app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._verif_modelo = "small"
app._aplicar_situacao(situacao("rapido"), False); app._mostrar_pagina("preparacao")
app.painel_verif._reverificar(); assert iniciou.wait(2)
app.seg_preset.set(PRESETS["preciso"]["rotulo"]); app._opcoes_mudaram(); bombear(.6)
assert app.situacao.modelo == "large-v3-turbo", app.situacao
liberar.set(); bombear(.8)
textos = []
def coletar(w):
    for f in w.winfo_children():
        try: textos.append(str(f.cget("text")))
        except Exception: pass
        coletar(f)
coletar(app.painel_verif)
cartoes = [t for t in textos if t.startswith(("Modelo de transcrição", "Baixar "))]
assert app.situacao.modelo == "large-v3-turbo", app.situacao
assert not any("small" in t for t in cartoes), cartoes
assert any("Preciso: large-v3-turbo" in t for t in cartoes), cartoes
print("C1 OK:", cartoes)
app._fechar(); bombear(.3)
print("AUDITORIA C1 GUI OK")
