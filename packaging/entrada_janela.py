"""Ponto de entrada do TranscritorLocal.exe (janela). Aceita --cli para o modo terminal."""
import sys

from transcritor.util import garantir_saidas_padrao

garantir_saidas_padrao()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from transcritor.cli import main as cli
        sys.exit(cli(sys.argv[2:]))
    from transcritor.gui.app import main
    sys.exit(main())
