"""Ponto de entrada do TranscritorLocal.exe.

--autoteste: confere, sem abrir janela, se tudo que o executável precisa está dentro dele
(usado pelo build automático no GitHub). Código de saída 0 = ok.
"""
import sys
import types


def _substituir_pyav() -> None:
    """O executável não leva o PyAV, que embute bibliotecas GPL (libx264, libx265; achado K2).

    O faster-whisper só importa o PyAV para decode_audio(), que o app nunca usa: o áudio é lido pelo
    FFmpeg (ADR-003). Um módulo vazio no lugar basta para o import; qualquer uso de verdade falha
    com uma mensagem clara em vez de um erro obscuro."""
    if "av" in sys.modules:
        return
    av = types.ModuleType("av")
    av.SUBSTITUTO_TRANSCRITOR = True

    def __getattr__(nome):
        # AttributeError (e não ImportError): hasattr(), repr() e o importlib dependem disso
        raise AttributeError(f"av.{nome}: o PyAV não vem no executável; o áudio é lido pelo FFmpeg (ADR-021).")
    av.__getattr__ = __getattr__
    sys.modules["av"] = av


if getattr(sys, "frozen", False):
    _substituir_pyav()

from transcritor.util import garantir_saidas_padrao  # noqa: E402

garantir_saidas_padrao()


def autoteste() -> int:
    import traceback
    try:
        import ctranslate2  # noqa: F401
        import customtkinter  # noqa: F401
        import faster_whisper  # noqa: F401
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        import numpy as np

        from transcritor import __version__, preparacao
        from transcritor.util import pasta_do_app
        ff = preparacao.FFMPEG
        assert len(ff["sha256"]) == 64 and ff["versao"] in ff["url"], "versão fixa do FFmpeg incompleta"
        if getattr(sys, "frozen", False):
            import av
            assert getattr(av, "SUBSTITUTO_TRANSCRITOR", False), "o PyAV verdadeiro entrou no executável"
            gpl = [p.name for p in pasta_do_app().rglob("*") if p.name.lower().startswith(("libx264", "libx265"))]
            assert not gpl, f"bibliotecas GPL no pacote: {gpl}"
            assert not (pasta_do_app() / "bin" / "ffmpeg.exe").exists(), "FFmpeg não deve vir no pacote"
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
