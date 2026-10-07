import sys

from .util import garantir_saidas_padrao

garantir_saidas_padrao()

if len(sys.argv) > 1 and sys.argv[1] == "--cli":
    from .cli import main
    sys.exit(main(sys.argv[2:]))
else:
    from .gui.app import main
    sys.exit(main())
