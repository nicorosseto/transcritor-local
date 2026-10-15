"""K11: correcoes.json salvo em ANSI (cp1252) derruba a rodada inteira, apesar de "arquivo inválido não derruba nada".

Rodar na raiz do repositório:
  python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k11_correcoes_ansi.py
"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline
from transcritor.config import Config
m = ModeloFalso()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
tmp = Path(tempfile.mkdtemp())
criar_video(tmp / "v/a.mp4", [("a", 4)])
s = tmp / "s"; s.mkdir()
(s / "correcoes.json").write_bytes('{"trocar": {"inteligencia": "Inteligência"}}'.encode("cp1252"))
p = pipeline.Projeto(Config(tmp / "v", s)); itens = p.escanear()
r = p.executar(itens, lambda ev: None)
print("resumo:", {k: r[k] for k in ("ok", "erro", "fatal") if k in r})
