# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: gera uma pasta (onedir) com TranscritorLocal.exe.
# "onedir" abre mais rápido e costuma disparar menos falsos positivos de antivírus que "onefile".
# Uso (na raiz do repositório):  pyinstaller packaging/transcritor.spec --noconfirm

import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH vem do PyInstaller)

datas = []
datas += collect_data_files("faster_whisper")   # modelo do filtro de voz (silero_vad .onnx)
datas += collect_data_files("customtkinter")    # temas e fontes da interface
binaries = []
binaries += collect_dynamic_libs("ctranslate2")  # motor do Whisper
binaries += collect_dynamic_libs("onnxruntime")  # usado pelo filtro de voz

a = Analysis(
    ["entrada_janela.py"],
    pathex=[RAIZ],
    binaries=binaries,
    datas=datas,
    hiddenimports=["transcritor.gui.app", "transcritor.cli", "psutil"],
    excludes=["torch", "tensorflow", "matplotlib"],  # PyAV fica: o faster-whisper o importa ao carregar (ADR-003)
    noarchive=False,
)
pyz = PYZ(a.pure)

# Dois executáveis na mesma pasta, compartilhando as bibliotecas:
#   TranscritorLocal.exe          -> janela (sem console)
#   TranscritorLocal-terminal.exe -> modo terminal (precisa de console para perguntar/mostrar progresso)
exe_janela = EXE(pyz, a.scripts, [], exclude_binaries=True, name="TranscritorLocal",
                 console=False, icon=None)

b = Analysis(["entrada_terminal.py"], pathex=[RAIZ], binaries=[], datas=[],
             hiddenimports=["transcritor.cli"], excludes=["torch", "tensorflow", "matplotlib"])
exe_terminal = EXE(PYZ(b.pure), b.scripts, [], exclude_binaries=True,
                   name="TranscritorLocal-terminal", console=True, icon=None)

coll = COLLECT(exe_janela, exe_terminal, a.binaries, a.datas, b.binaries, b.datas,
               strip=False, upx=False, name="TranscritorLocal")
