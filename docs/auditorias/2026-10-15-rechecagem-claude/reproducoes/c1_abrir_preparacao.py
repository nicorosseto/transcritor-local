"""Rechecagem de 15/10/2026. Rodar na raiz:
  xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-15-rechecagem-claude/reproducoes/c1_abrir_preparacao.py

Primeiro uso sem FFmpeg (o caso de todo .zip desde a v0.1.14): a verificação inicial pede para abrir a
Preparação. Se a qualidade for trocada antes de ela voltar, a Preparação ainda abre sozinha?"""
import sys, time
from types import SimpleNamespace
sys.path.insert(0, ".")
from transcritor.config import PRESETS
from transcritor.gui import app as A
from transcritor.gui.verificacao import Situacao
def falso(preset, saida):
    time.sleep(0.3)
    return Situacao(modelo=PRESETS[preset]["modelo"], ffmpeg_ok=False, obrigatorios=["FFmpeg"],
                    diagnostico=SimpleNamespace(itens=[], preset_recomendado="equilibrado", dispositivo="cpu"))
A.verificar = falso
for trocar in (False, True):
    app = A.App()
    def bombear(seg):
        fim = time.time() + seg
        while time.time() < fim:
            app.update(); time.sleep(0.03)
    bombear(0.5)
    if trocar:
        app.seg_preset.set(PRESETS["rapido"]["rotulo"]); app._opcoes_mudaram()
    bombear(2)
    print(f"trocou a qualidade no meio={trocar}: página={app.pagina!r} | selo obrigatório={len(app.situacao.obrigatorios) if app.situacao else None}")
    app.destroy()
