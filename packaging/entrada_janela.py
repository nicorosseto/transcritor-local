"""Ponto de entrada do TranscritorLocal.exe.

--autoteste: confere, sem abrir janela, se tudo que o executável precisa está dentro dele
(usado pelo build automático no GitHub). Código de saída 0 = ok.
"""
import sys

from transcritor.util import garantir_saidas_padrao

garantir_saidas_padrao()


def autoteste() -> int:
    import traceback
    try:
        import ctranslate2  # noqa: F401
        import customtkinter  # noqa: F401
        import faster_whisper  # noqa: F401
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        import numpy as np

        from transcritor import __version__
        from transcritor.util import localizar_binario
        assert localizar_binario("ffmpeg"), "ffmpeg não encontrado em bin/"
        assert localizar_binario("ffprobe"), "ffprobe não encontrado em bin/"
        get_speech_timestamps(np.zeros(16000, dtype="float32"), VadOptions())  # filtro de voz (onnx)
        print(f"autoteste ok: Transcritor Local {__version__}")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    from transcritor.gui.app import main
    sys.exit(main())
