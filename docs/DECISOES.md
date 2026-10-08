# Decisões técnicas (ADRs)

Formato curto: contexto → decisão → consequências. Datas em DD/MM/AAAA.

---

## ADR-001: Transcrição local com faster-whisper na CPU

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** O conteúdo pode ser sigiloso (trabalho) ou protegido (cursos). As APIs gratuitas de transcrição têm limite de arquivo (25 MB) e cota diária, e enviam o áudio para terceiros. O PC de referência não tem NVIDIA (AMD RX 560 XT).

**Decisão.** Usar `faster-whisper` (CTranslate2) local, com `int8` na CPU e `float16` na GPU NVIDIA quando houver. Modelo padrão: `large-v3-turbo`.

**Consequências.** (+) Gratuito, privado, offline após o primeiro download. (−) Lento em CPU antiga (1,48x medido). Placas AMD/Intel não aceleram. A alternativa `whisper.cpp` com Vulkan pode usar AMD, mas fica registrada como pesquisa futura ([Roadmap](ROADMAP.md)).

---

## ADR-002: Extrair o áudio para MP3 mono 16 kHz antes de transcrever

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** Vídeos de 1 GB contêm imagem que o Whisper não usa. Decodificar o vídeo inteiro a cada tentativa custa tempo.

**Decisão.** O FFmpeg gera um MP3 mono 16 kHz a 48 kbps (~20 MB/h), guardado em `audio_mp3/` e reaproveitado.

**Consequências.** (+) Retentativas rápidas; o MP3 também serve para subir direto no NotebookLM. (−) Ocupa disco (~0,8 GB para 40 h).

---

## ADR-003: Decodificar o áudio com FFmpeg, não com PyAV

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** No primeiro teste real, o faster-whisper 1.2.1 com PyAV 19.0.1 falhou com `open() got an unexpected keyword argument 'metadata_errors'`. O PyAV removeu esse parâmetro em versões recentes.

**Decisão.** O FFmpeg decodifica para PCM 16-bit via pipe, e o array numpy é passado ao `transcribe`, que assim não chama o PyAV.

**Consequências.** (+) Imune a mudanças da API do PyAV; uma dependência a menos no caminho crítico. (−) O PyAV continua instalado, porque o faster-whisper o importa ao carregar (excluí-lo do PyInstaller quebrou o build, detectado em teste). (−) O áudio inteiro fica em memória (~230 MB/h em float32); aceitável com 8 GB ou mais.

---

## ADR-004: Texto de tela com capturas + Tesseract; IA visual fica para a v0.2

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** Parte do conteúdo está só na tela. As opções eram: (1) capturas, (2) OCR, (3) modelo de visão local (Ollama + Qwen3-VL), (4) Gemini API.

**Decisão.** v0.1 entrega (1) + (2) como opção. O (3) entra na v0.2 como segunda fase, aplicada só aos vídeos escolhidos, reaproveitando as capturas já salvas. O (4) foi descartado: cota não publicada (poderia esgotar no meio de um lote) e, no plano gratuito, o conteúdo pode ser usado para melhorar produtos do Google.

**Consequências.** (+) Custo baixo (+15–35% de tempo, estimado). (−) O OCR lê texto, mas não entende ações nem gráficos. Estimativa para a IA visual na CPU de referência: ~1–2 min por captura, viável só para poucos vídeos.

---

## ADR-005: Detecção de troca de tela em três filtros

**Data:** 07/10/2026 · **Status:** aceita (calibrar com vídeos reais)

**Decisão.** (a) `-skip_frame nokey`: lê só os quadros-chave (rápido); (b) `mpdecimate`: descarta quadros quase iguais; (c) dHash **16x16** com ≥ 8 bits diferentes e intervalo mínimo de 4 s.

**Por quê 16x16.** Em teste com slides de fundo claro, o dHash 8x8 deu distância 3–5 entre slides diferentes (abaixo de qualquer limiar útil); o 16x16 deu 15.

**Consequências.** Vídeos com pessoa falando (muito movimento) podem gerar capturas demais. O OCR descarta as sem texto, mas cada uma custa ~1 s. Os limiares precisam ser calibrados em vídeos reais (pendência P3 da [Auditoria](AUDITORIA.md)).

---

## ADR-006: registro.csv com identidade por caminho + tamanho + data

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** A primeira versão detectava "já feito" só pelo nome do `.md`. Falhas: um vídeo substituído com o mesmo nome era pulado, e um vídeo excluído continuava na base enviada à IA.

**Decisão.** CSV com status e métricas; ao sumir o vídeo, o `.md` vai para `_orfaos/` (nunca é apagado). Hash de conteúdo foi descartado: ler 1 GB por vídeo a cada varredura é caro demais para pouco ganho (só ajudaria a detectar renomeações).

**Consequências.** (+) Abre no Excel/Power BI, e as estimativas aprendem com o histórico. (−) Renomear ou mover um vídeo causa uma nova transcrição.

---

## ADR-007: Quantidade por rodada obrigatória, perguntada (não editada no código)

**Data:** 07/10/2026 · **Status:** aceita

**Contexto.** O usuário pediu um limite obrigatório de vídeos por execução. Editar uma constante no código a cada rodada é arriscado para iniciantes e não obriga nada de fato.

**Decisão.** CLI e GUI **exigem** a escolha antes de iniciar, mostrando a estimativa de cada opção.

---

## ADR-008: App desktop com CustomTkinter + PyInstaller onedir

**Data:** 07/10/2026 · **Status:** aceita

**Alternativas.** Web local (Streamlit/Gradio): exige terminal aberto e porta local. PySide6/Qt: mais pesado, LGPL. Electron: outro ecossistema.

**Decisão.** CustomTkinter (sobre o Tkinter, já incluído no Python), empacotado em onedir com dois `.exe` (janela e terminal). O build roda no GitHub Actions (Windows).

**Consequências.** (+) Leve, sem servidor, `.zip` portátil. onedir abre mais rápido e costuma ter menos falsos positivos de antivírus que onefile. (−) Sem assinatura digital: o SmartScreen avisa na primeira execução.

---

## ADR-009: Vocabulário via `hotwords`

**Data:** 07/10/2026 · **Status:** aceita (medir efeito)

**Contexto.** No teste real, "hook" saiu como "Hulk", "ChatGPT" como "Chatipete", "Claude" como "Cloude" e "Gemini" como "Jimenae".

**Decisão.** Passar a lista do usuário em `hotwords` (parâmetro do faster-whisper ≥ 1.0) em vez de `initial_prompt`, que condiciona o estilo e pode induzir repetição.

**Consequências.** O efeito real em português ainda precisa ser medido (pendência P2).

---

## ADR-010: Parâmetros anti-alucinação

**Data:** 07/10/2026 · **Status:** aceita

`vad_filter=True` (o silêncio não chega ao modelo), `condition_on_previous_text=False` (quebra loops de repetição) e o *fallback* de temperatura padrão mantido (desligá-lo é causa conhecida de loops). `hallucination_silence_threshold` não é usado, porque exigiria `word_timestamps=True` e mais processamento. Fica reavaliável.

---

## ADR-011: Dica (antes) e correção (depois) são mecanismos separados

**Data:** 08/10/2026 · **Status:** aceita

**Contexto.** Não existe um dicionário de correção "universal" validado para Whisper: os erros dependem do sotaque, do assunto e do áudio. Apps como MacWhisper, Superwhisper e OpenWhispr dão a cada usuário a própria lista. O guia da OpenAI mostra que listas de termos no prompt corrigem só parte dos nomes, e que revisar por LLM é mais confiável, porém pode inventar texto.

**Decisão.** `hotwords` (dica, antes) + `correcoes.json` por projeto (troca determinística, depois, só palavra inteira, sem diferenciar maiúsculas). O total de trocas vai para o cabeçalho do `.md` e para o `registro.csv`. A revisão por LLM fica fora do app; a IA que lê o `.md` já entende boa parte dos erros pelo contexto.

---

## ADR-012: Experiência no Windows segue as diretrizes da Microsoft

**Data:** 08/10/2026 · **Status:** aceita

- **Primeira abertura sem perguntas:** a tela de preparação só abre sozinha quando falta algo **obrigatório**; itens opcionais viram selo + piscada no botão "Verificar PC".
- **Barra de progresso única** por rodada, ponderada pela duração dos vídeos, que **nunca volta**; etapas mostradas como texto (Áudio › Transcrição › Texto da tela › Salvar), não como barras duplas.
- **Tempo restante** só depois de 30 s de medição, sem falsa precisão ("1 h 20 min").
- **Diálogos** com botões de ação específicos ("Instalar Tesseract", "Continuar sem ler a tela"), sempre com uma saída segura.
- **Conclusão** sinalizada com som do sistema e ícone piscando na barra de tarefas, para lotes que rodam sem ninguém olhando.
- **Um único executável** na distribuição; o modo terminal é para quem usa o código-fonte.

**Regra técnica derivada:** nenhum objeto do Tk pode ser criado em loop nem destruído fora da thread principal. O app desativa a coleta automática de lixo e a executa periodicamente na thread da interface (ver C19 na Auditoria).
