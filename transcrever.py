"""Atalho para o modo terminal, com as pastas 'videos' e 'saida' ao lado deste arquivo.

Uso:  python transcrever.py
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from transcritor.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--videos", str(AQUI / "videos"), "--saida", str(AQUI / "saida"), *sys.argv[1:]]))
