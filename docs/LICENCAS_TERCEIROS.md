# Licenças de terceiros

O Transcritor Local é MIT. Ele **usa** (e, no `.zip` para Windows, **distribui**) os componentes abaixo, cada um com a sua licença.

| Componente | Uso | Licença | Distribuído no .zip? |
|---|---|---|---|
| [FFmpeg](https://ffmpeg.org) (build "essentials" de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)) | Extração de áudio e imagens | GPL v3 (build com componentes GPL) | Sim, como programa separado em `bin/`, chamado por linha de comando. Licença em `licencas/FFmpeg-LICENSE.txt`. Código-fonte: [ffmpeg.org/download](https://ffmpeg.org/download.html) e a página da build |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Transcrição | MIT | Sim |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | Motor de inferência | MIT | Sim |
| Modelos Whisper (OpenAI), via Hugging Face | Pesos do modelo | MIT | Não: baixados na primeira execução |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Filtro de voz (VAD) | MIT | Sim |
| Silero VAD (incluído no faster-whisper) | Detecção de fala | MIT | Sim |
| [PyAV](https://github.com/PyAV-Org/PyAV) | Importado pelo faster-whisper | BSD-3-Clause (embute bibliotecas FFmpeg) | Sim |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | OCR (opcional) | Apache 2.0 | Não: instalado pelo usuário |
| [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) (por, eng) | Idiomas do OCR | Apache 2.0 | Não: baixado sob demanda |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Interface | MIT | Sim |
| [Pillow](https://python-pillow.org) | Imagens | MIT-CMU (HPND) | Sim |
| [NumPy](https://numpy.org) | Arrays de áudio | BSD-3-Clause | Sim |
| [psutil](https://github.com/giampaolo/psutil) | Hardware | BSD-3-Clause | Sim |
| Python + Tk/Tcl | Runtime | PSF / BSD-style | Sim |

> **FFmpeg (P8):** o build grava `licencas/FFmpeg-CODIGO-FONTE.txt` na pasta distribuída, com a versão exata e o endereço do código-fonte correspondente, além do texto da licença. Isso cobre a oferta de fonte da GPL para um programa chamado como processo separado; não é parecer jurídico. Quem quiser eliminar a questão pode usar o FFmpeg instalado no próprio PC.
