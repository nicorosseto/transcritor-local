"""K6 (e área 3): estimativa. 'Últimos 5' depois de reabrir o registro, vídeos curtos e divisões por zero.

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k06_estimativa.py
"""
import itertools, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
from transcritor import estimativa
from transcritor.registro import OK, Linha, Registro

tmp = Path(tempfile.mkdtemp())
reg = Registro(tmp / "registro.csv")
# 5 vídeos antigos (lentos, 1,0x, sem OCR) com nomes "z...", e o mais recente (rápido, 2,0x, com OCR) "a_nova"
for i in range(5):
    reg.linhas[f"z{i}.mp4"] = Linha(f"z{i}.mp4", status=OK, preset="equilibrado", duracao_s=600, velocidade=1.0,
                                     transcrito_em=f"0{i+1}/10/2026 10:00")
reg.linhas["a_nova.mp4"] = Linha("a_nova.mp4", status=OK, preset="equilibrado", duracao_s=600, velocidade=2.0,
                                 ocr="sim", seg_ocr=120, transcrito_em="14/10/2026 18:00")
print("na mesma sessão : velocidade", round(reg.velocidade_medida("equilibrado"), 3),
      "| OCR s/h", reg.ocr_por_hora_medido())
reg.salvar()
reg2 = Registro(tmp / "registro.csv")
print("depois de reabrir: velocidade", round(reg2.velocidade_medida("equilibrado"), 3),
      "| OCR s/h", reg2.ocr_por_hora_medido(), "| ordem:", list(reg2.linhas)[-5:])

# vídeos todos curtos (< 3 min): nunca aprende
reg3 = Registro(tmp / "r3.csv")
for i in range(20):
    reg3.linhas[f"c{i}.mp4"] = Linha(f"c{i}.mp4", status=OK, preset="equilibrado", duracao_s=170, velocidade=1.7)
e = estimativa.estimar([170] * 10, reg3, "equilibrado", "cpu", False)
print("20 vídeos de 2min50 já feitos a 1,7x -> estimativa usa", e.velocidade, "medida =", e.medida)

# varredura de bordas: nenhuma exceção (divisão por zero) esperada
vals = [0.0, 1e-9, 1.0, 180.0, 3600.0]
n = 0
for a, b, c, d, f in itertools.product(vals, repeat=5):
    estimativa.falta_da_rodada(a, b, c, None, f); estimativa.falta_da_rodada(a, b, c, d, f); n += 2
for feitas, total in itertools.product(range(0, 8), range(0, 8)):
    for g in vals:
        estimativa.ocr_restante_do_video(feitas, total, g, 600.0, 600.0); n += 1
for dur in ([], [0.0], [0.0, 0.0], [5.0]):
    for ocr in (False, True):
        estimativa.estimar(dur, Registro(tmp / "vazio.csv"), "equilibrado", "cpu", ocr); n += 1
print(f"bordas: {n} chamadas sem exceção")
