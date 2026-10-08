# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: gera uma pasta (onedir) com TranscritorLocal.exe (um único executável).
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

# Um único executável, de janela. O modo terminal fica para quem roda pelo código-fonte
# (python transcrever.py): dois .exe na mesma pasta confundiam o usuário.
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="TranscritorLocal",
          console=False, icon=None)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="TranscritorLocal")
