"""Ponto de entrada do TranscritorLocal-terminal.exe."""
import sys

from transcritor.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
