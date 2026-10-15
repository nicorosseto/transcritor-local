# Licenças de terceiros

O Transcritor Local é MIT. Ele **usa** os componentes abaixo, cada um com a sua licença. Desde a v0.1.13, o `.zip` para Windows **não redistribui nenhum binário GPL** ([ADR-021](DECISOES.md)): o FFmpeg é baixado pelo próprio usuário, na primeira abertura, direto do distribuidor, e o PyAV fica fora do executável.

| Componente | Uso | Licença | Distribuído no .zip? |
|---|---|---|---|
| [FFmpeg](https://ffmpeg.org) 9.0.2 (build "essentials" de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)) | Extração de áudio e imagens | GPL v3 | **Não.** O app baixa a versão fixa do GitHub do distribuidor ([GyanD/codexffmpeg](https://github.com/GyanD/codexffmpeg)), confere o SHA-256 e guarda em `%LOCALAPPDATA%\TranscritorLocal\ffmpeg`, com a licença e um `ORIGEM.txt` (versão, endereço, hash e link do código-fonte). É chamado como programa separado. No Linux e no macOS, usa o FFmpeg do sistema |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Transcrição | MIT | Sim |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | Motor de inferência | MIT | Sim |
| Modelos Whisper (OpenAI), via Hugging Face | Pesos do modelo | MIT | Não: baixados na primeira execução |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Filtro de voz (VAD) | MIT | Sim |
| Silero VAD (incluído no faster-whisper) | Detecção de fala | MIT | Sim |
| [PyAV](https://github.com/PyAV-Org/PyAV) | Importado pelo faster-whisper, nunca usado pelo app | BSD-3-Clause; as rodas para Windows embutem FFmpeg com libx264 e libx265 (GPL) | **Não.** Um módulo vazio ocupa o lugar dele no executável; o áudio é lido pelo FFmpeg ([ADR-003](DECISOES.md)). Quem roda pelo código-fonte instala o PyAV normalmente pelo `pip` |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | OCR (opcional) | Apache 2.0 | Não: instalado pelo usuário |
| [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) (por, eng) | Idiomas do OCR | Apache 2.0 | Não: baixado sob demanda |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Interface | MIT | Sim |
| [Pillow](https://python-pillow.org) | Imagens | MIT-CMU (HPND) | Sim |
| [NumPy](https://numpy.org) | Arrays de áudio | BSD-3-Clause | Sim |
| [psutil](https://github.com/giampaolo/psutil) | Hardware | BSD-3-Clause | Sim |
| Python + Tk/Tcl | Runtime | PSF / BSD-style | Sim |

**Textos das licenças no `.zip`:** a pasta `licencas/` traz a licença do app, esta tabela e `BIBLIOTECAS.txt`, gerado no build com o texto da licença (e o `NOTICE`, quando existe) de cada biblioteca Python do ambiente de build (achado K9). Conferido pelo build: se o arquivo sair vazio, o build falha.

Esta é uma leitura técnica das licenças, não um parecer jurídico.
