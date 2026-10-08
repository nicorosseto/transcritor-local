# Auditoria do projeto (v0.1)

**Data:** 07/10/2026 · **Escopo:** ideia, arquitetura, código, empacotamento, privacidade e licenças.
**Método:** revisão do histórico de decisões, testes automatizados e de fumaça (CLI, GUI em display virtual, binário PyInstaller) e pesquisa em fontes externas (listadas no fim).

Severidade: 🔴 alta · 🟠 média · 🟡 baixa. Status: ✅ corrigido · ⏳ pendente · 📌 aceito (documentado).

## 1. Corrigido na v0.1

| # | Lacuna | Sev. | Status |
|---|---|---|---|
| C1 | PyAV 19 incompatível com faster-whisper 1.2.1 | 🔴 | ✅ ADR-003 |
| C2 | Vídeos com o mesmo nome em subpastas diferentes sobrescreviam o `.md` | 🔴 | ✅ estrutura espelhada |
| C3 | Vídeo excluído continuava na base enviada à IA | 🔴 | ✅ `_orfaos/` + registro |
| C4 | Vídeo substituído (mesmo nome) era pulado | 🔴 | ✅ tamanho + data |
| C5 | Interrupção deixava MP3/MD/CSV pela metade | 🟠 | ✅ escrita atômica |
| C6 | `registro.csv` aberto no Excel trava a gravação (Windows) | 🟠 | ✅ retentativa + cópia de segurança |
| C7 | Pasta de saída dentro da pasta de vídeos | 🟠 | ✅ validação |
| C8 | `.md` da versão anterior seria refeito (25 min perdidos) | 🟠 | ✅ importação automática |
| C9 | Subprocessos lendo o teclado do terminal | 🟠 | ✅ `stdin=DEVNULL` |
| C10 | `.exe` de janela sem stdout/stderr → falha no download do modelo | 🔴 | ✅ log + exe de terminal |
| C11 | PC suspendendo no meio de lote noturno | 🟠 | ✅ `SetThreadExecutionState` |
| C12 | Duas janelas gravando na mesma saída | 🟠 | ✅ trava por PID |
| C13 | Erro de rede no download do modelo, incompreensível para leigo | 🟡 | ✅ mensagem explicativa (proxy corporativo) |
| C14 | Detecção de troca de slide falhava em fundos claros | 🟠 | ✅ dHash 16x16 |

## 2. Pendências

| # | Lacuna / risco | Sev. | Próximo passo |
|---|---|---|---|
| P1 | **A janela (GUI) ainda não rodou em Windows real.** Já validado no CI Windows: os 14 testes do motor (Python 3.11 e 3.13), o build do PyInstaller e o `.exe` de terminal abrindo | 🔴 | Teste manual do `.zip` no PC de referência; depois, teste de GUI automatizado |
| P2 | Efeito do `hotwords` e velocidade do beam 1 **não medidos** com o modelo real (o ambiente de build não baixa modelos) | 🟠 | Rodar o vídeo de referência com e sem vocabulário e comparar os erros |
| P3 | Limiares de captura (4 s, 8 bits) não calibrados: vídeo com pessoa falando pode gerar muitas capturas | 🟠 | Medir capturas por hora em 3 tipos de vídeo; expor a "sensibilidade" na interface |
| P4 | Sem barra de progresso do **download do modelo** (até 1,6 GB): parece travado | 🟠 | Pré-baixar com `huggingface_hub` e progresso próprio |
| P5 | **NVIDIA no `.exe`**: as bibliotecas CUDA (cuBLAS/cuDNN 12) não vêm no pacote; `pip install nvidia-*` não alcança o Python embutido | 🟡 | Documentar a instalação do CUDA Toolkit 12 ou oferecer um build "GPU" separado |
| P6 | VRAM no Windows via `AdapterRAM` (32 bits) aparece limitada a 4 GB | 🟡 | Ler `HardwareInformation.qwMemorySize` no registro do Windows (só importa para a v0.2) |
| P7 | **SmartScreen/antivírus** em `.exe` sem assinatura (falsos positivos são comuns com PyInstaller) | 🟠 | Avaliar assinatura gratuita para projetos open source (ex.: SignPath) antes de tornar público |
| P8 | **FFmpeg GPL embutido**: exige distribuir a licença (feito) e indicar onde obter o código-fonte da build | 🟠 | Conferir o texto da build gyan.dev e adicionar o link do fonte em `LICENCAS_TERCEIROS.md` |
| P9 | Caminhos acima de 260 caracteres no Windows (subpastas profundas) | 🟡 | Teste com caminho longo; prefixo `\\?\` ou aviso na varredura |
| P10 | Áudio inteiro em memória (~230 MB/h) | 🟡 | Ok até ~10 h por arquivo com 16 GB; processar em blocos se necessário |
| P11 | GUI usa todos os threads → PC fica lento durante o lote | 🟡 | Opção "deixar o PC usável" (threads − 2) |
| P12 | Sem identificação de falantes (diarização) | 🟡 | Avaliar pyannote (pesado) ou deixar fora do escopo |
| P13 | Testes de GUI não rodam no CI | 🟡 | Job Linux com `xvfb-run` (o teste de fumaça já existe) |
| P14 | Estimativa de OCR padrão (10 min/h) é chute conservador | 🟡 | Substituída automaticamente após o 1º vídeo com OCR |
| P15 | Sem atualização automática | 🟡 | Verificar a última Release no GitHub ao abrir (opcional) |
| P16 | Alucinação residual em música/ruído de fundo | 🟡 | Avaliar `hallucination_silence_threshold` + `word_timestamps` (custo) |

## 3. Riscos de uso (não técnicos)

| Risco | Mitigação |
|---|---|
| Publicar transcrições de **curso pago** (direitos autorais) | `.gitignore` bloqueia saídas; README e app alertam |
| Subir material **de trabalho/sigiloso** para IA na nuvem depois de transcrever | Guia recomenda anonimizar antes; o processamento local não vaza nada |
| Confiar cegamente na transcrição | Aviso no cabeçalho de cada `.md` |
| Modelo de visão pequeno (v0.2) **inventar** descrições | Prever rótulo "descrição automática" e revisão humana |

## 4. Fontes consultadas

- [Whisper hallucination fix (LocalAimaster, 13/09/2026)](https://localaimaster.com/blog/whisper-hallucination-fix): causas e parâmetros anti-alucinação
- [CTranslate2 issue #1630](https://github.com/OpenNMT/CTranslate2/issues/1630): CTranslate2 4.x exige CUDA 12
- [faster-whisper issue #719](https://github.com/SYSTRAN/faster-whisper/issues/719): problemas de build do PyAV no Windows
- [UB Mannheim Tesseract wiki](https://github.com/UB-Mannheim/tesseract/wiki/Install-additional-language-and-script-models): idiomas adicionais
- [Discussão sobre falso positivo do PyInstaller (discuss.python.org)](https://discuss.python.org/t/pyinstaller-false-positive/43171)
- [whisper.cpp + Vulkan em AMD (maroonmed, 07/02/2026)](https://www.maroonmed.com/subtitle-edit-and-whisper-cpp-stt-on-amd-and-other-non-nvidia-gpus-with-vulkan/)
- [Ollama: Vulkan experimental (Phoronix, 15/10/2025)](https://www.phoronix.com/news/ollama-Experimental-Vulkan)
- [Modelos de visão locais por VRAM (LocalAimaster, 23/08/2026)](https://localaimaster.com/blog/best-local-vision-models)
- [Limites do NotebookLM 2026 (fast.io)](https://fast.io/resources/notebooklm-limits/)
- [Gemini API free tier 2026 (yingtu.ai)](https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026)

> Uma segunda auditoria, independente, está prevista com o Codex. Veja [AUDITORIA_CODEX.md](AUDITORIA_CODEX.md).
