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

---

## ADR-013: Chave de saída fixa por vídeo e identidade do projeto

**Data:** 11/10/2026 · **Status:** aceita · **Origem:** achados X2 e X7 da [auditoria de 08/10/2026](auditorias/STATUS.md)

**Contexto.** O nome do `.md`, do `.mp3` e da pasta de capturas era derivado do caminho do vídeo **sem a extensão**: `aula.mp4` e `aula.mkv` escreviam no mesmo lugar. E nada ligava a pasta de saída à pasta de vídeos de origem: apontar outro curso para a mesma saída adotava transcrições alheias como "concluídas".

**Decisão.**
- Cada vídeo recebe, uma única vez, uma **chave de saída** gravada na coluna `saida` do `registro.csv`. O padrão continua sendo o nome sem extensão (compatível com saídas antigas). Só em caso de conflito a extensão entra no nome: `aula [mp4].md`. A chave nunca muda depois de atribuída, mesmo que surja um vídeo "irmão".
- A pasta de saída ganha um `projeto.json` com a pasta de vídeos de origem. Origem diferente exige confirmação explícita ("A pasta foi movida, continuar" na janela; `--pasta-movida` no terminal). As origens anteriores ficam registradas.
- Um `.md` existente só é adotado como concluído em saídas **sem** `projeto.json` (feitas por versões antigas).

**Alternativas descartadas.** Sempre incluir a extensão no nome (`aula.mp4.md`): quebraria a compatibilidade com todas as saídas existentes. ID numérico: nomes ilegíveis para quem navega na pasta.

---

## ADR-014: Threads de trabalho só falam com a interface pela fila

**Data:** 11/10/2026 · **Status:** aceita · **Origem:** X13 e X16; amplia a regra do ADR-012

- Threads de trabalho **não chamam nenhum método do Tk**, nem `.after()`. Para executar algo na interface, usam `App.na_interface(fn)`, que coloca um evento `chamar` na fila consumida pela thread principal. Um teste de guarda impede a volta de `.after(0, ...)`.
- Toda rodada termina com **exatamente um** `lote_fim`. Erro inesperado vira o campo `fatal`. O texto final vem de `gui/estado.py` (testável sem Tk), que nunca mostra sucesso sem nenhum vídeo concluído.

---

## ADR-015: Threads do Whisper = núcleos físicos

**Data:** 11/10/2026 · **Status:** aceita · **Origem:** P17

**Contexto.** A v0.1.1 passava `cpu_threads=os.cpu_count()`, que conta threads **lógicas** (12 no PC de referência, um Xeon de 6 núcleos com Hyper-Threading). O app ficou mais lento que o script v1, que usava o padrão do faster-whisper (4).

**Medição** (`ferramentas/medir_threads.py`, mesmo vídeo, 3 min de fala, `large-v3-turbo`, beam 1, PC sem uso):

| Threads | Tempo | Velocidade |
|---|---|---|
| 4 | 115,0 s | 1,57x |
| 6 | 115,3 s | 1,56x |
| 12 | 134,1 s | 1,34x |

**Decisão.** Padrão = núcleos físicos (`psutil.cpu_count(logical=False)`; sem essa informação, metade das threads lógicas). O valor escolhido pelo usuário em `threads` continua tendo prioridade.

**Por que não 4 fixo.** No PC de referência, 4 e 6 empatam, mas um processador com mais núcleos físicos ganharia com mais threads. Núcleos físicos é a regra que generaliza. A opção de deixar núcleos livres para usar o PC durante o lote continua prevista (P11).

**CPU híbrida (adendo, 11/10/2026).** Nos Intel de 12ª geração em diante, os núcleos eficientes (E-cores) são bem mais lentos, e o Whisper espera a thread mais lenta a cada passo. No Windows, o app lê a "classe de eficiência" de cada núcleo (`GetLogicalProcessorInformationEx`) e, se houver mais de uma, usa só os núcleos de desempenho. **Dedução, não medida**: não houve PC híbrido para testar. Se a leitura falhar, vale a regra dos núcleos físicos.

---

## ADR-016: Resultado parcial é um estado próprio

**Data:** 11/10/2026 · **Status:** aceita · **Origem:** X10, X12, X16

- Toda rodada termina em um de cinco estados (`transcritor/resultado.py`): **sucesso**, **parcial**, **interrompido**, **falha** e **vazio**. A janela e a CLI usam a mesma função.
- **Parcial** cobre vídeos com erro **e** vídeos cuja fala foi transcrita, mas a leitura da tela falhou. Nesse segundo caso, o vídeo fica concluído (refazer custaria a transcrição inteira), com `ocr = falhou` no registro e o motivo no `.md`.
- "Não havia texto na tela" e "o Tesseract falhou" são coisas diferentes: a segunda vira `ErroOCR`, nunca texto vazio.
- Códigos da CLI: 0 sucesso/vazio · 1 falha · 2 parcial · 3 interrompido · 130 Ctrl+C.

---

## ADR-017: Layout com barra lateral, preto e verde só no clicável

**Data:** 11/10/2026 · **Status:** aceita · **Origem:** revisão de interface do Codex (UX-01 a UX-11) e escolha do responsável entre três propostas ([referência](design/layout-aprovado.html))

**Decisão.**
- **Estrutura:** barra lateral com o projeto e três páginas (Vídeos, Resultados, Preparação do PC). A tela de trabalho continua sendo uma só: tabela, opções ao lado e uma **barra de ação** embaixo.
- **Barra de ação:** escolher a quantidade é obrigatório (ADR-007), agora com **cartões** que mostram o tempo estimado de cada opção (1, 3, 5, Todos) ao lado do botão "Transcrever N". Durante a rodada, a mesma barra vira o progresso (etapas, barra única e término previsto); no fim, mostra o resultado, com "Ver resultados" e "Nova rodada".
- **Cores** (`gui/tema.py`): fundo preto `#000`, textos brancos, barra lateral `#0A1612`, e **verde `#4FD18B` só no que é clicável ou selecionado**. Botões secundários são escuros com borda; o botão principal só fica verde quando dá para clicar.
- **Marca:** logotipo "da onda à linha" desenhado em código (`gui/marca.py`), usado na janela e no ícone do `.exe` (`packaging/icone.ico`).
- **Preparação do PC** deixou de ser uma janela por cima e virou página. O app abre nela sozinho quando falta algo obrigatório, e o item pisca na barra lateral.
- **Resultados:** página que lê o `registro.csv` (palavras, velocidade, texto da tela, data) e mostra o registro de atividades, antes escondido num painel recolhível.

**Fica de fora (v0.3):** vários projetos na barra lateral, tema claro, busca e filtro na tabela.

**Limitações conhecidas.**
- A tabela é um `ttk.Treeview`: não dá para colorir só a "pílula" de status, então a linha inteira muda de cor (verde rodando, vermelho erro, laranja arquivo mudou).
- Acessibilidade por leitor de tela segue limitada pelo Tkinter (contra-auditoria, seção 5).

---

## ADR-018: O `.md` é feito para qualquer IA, não só para uma

**Data:** 14/10/2026 · **Status:** aceita · **Origem:** teste real no Windows ([registro](testes/2026-10-14-windows-p1.md)) e pergunta do responsável sobre quem lê os arquivos

**Decisão.**
- **Cabeçalho "Como ler este arquivo"** em todo `.md` (`markdown.COMO_LER`): explica `[hh:mm:ss]`, os blocos "Na tela" (OCR, com erros possíveis) e o que **não** existe (descrição de imagens). Substitui o aviso antigo de "transcrição automática".
- **Palavras** passam a contar só a fala (`palavras`); o texto de tela vai em `palavras_tela`. O limite por arquivo da base consolidada continua contando tudo, porque é o texto inteiro que ocupa a janela da IA.
- **Pacote para IA** (`pacote.py`, botão em Resultados): uma pasta e um `.zip` por vídeo com o `.md` e **só** as capturas que ele cita, com os links reescritos para `imagens/`. O áudio, o registro e as capturas descartadas ficam de fora.
- **Links de captura** são escritos com espaços e parênteses codificados (`%20`), porque o espaço cru quebra o link em Markdown e quebrava a base consolidada de pastas como "Módulo 01" (N7). A base entende também os `.md` antigos.
- **OCR:** capturas com menos de 1280 px de largura são ampliadas 2x antes do Tesseract, e palavras com confiança abaixo de 50 são descartadas (`ocr.preparar_imagem`, `ocr.texto_do_tsv`). Capturas sem uso são apagadas na hora (N3).

**Consequências.** (+) Qualquer IA interpreta o arquivo sem instruções externas; o texto de tela fica legível em vídeos de baixa resolução. (−) O OCR de capturas estreitas leva ~1,8x mais tempo por imagem (+3 min por vídeo de 36 min neste PC). O limiar de confiança é **provisório** (medido em 2 quadros): revisar com mais vídeos (P3).

**Limitações conhecidas.** A IA reconstrói o que foi dito e o texto que apareceu; gráficos, pessoas e layout dependem da v0.2 (IA visual). Chat comum tem janela de contexto pequena: muitos vídeos exigem ferramenta que indexa fontes.

**Adendo (v0.1.6, N8).** O Tesseract é chamado com `-c tessedit_create_tsv=1`, nunca com a configuração `tsv`, porque a pasta de idiomas do app não tem `configs/`. Se a saída não for TSV, o OCR falha de forma explícita (`ErroOCR`); "imagem sem texto" e "formato errado" são casos diferentes e aparecem diferentes no `.md`, no log e em Resultados.

**Adendo (v0.1.7, N9).** Depois da confiança por palavra, `ocr.limpar` filtra por linha (60% das letras em palavras de 4+ letras) e descarta o bloco se menos de 40% das linhas forem legíveis. Confiança mínima mantida em 50 (medido: 60 perdia 3% das linhas boas).

---

## ADR-019: A tabela é a seleção; sem cartões de quantidade

**Data:** 14/10/2026 · **Status:** aceita · **Substitui** o ADR-007 na janela (o modo terminal mantém a pergunta de quantidade) · **Origem:** teste real no Windows

**Contexto.** O ADR-007 exigia escolher a quantidade antes de começar, porque a janela não tinha como limitar a rodada. Depois das caixas de seleção na tabela, a escolha ficou duplicada: com 2 vídeos marcados o botão seguia apagado até clicar em "Todos (2)", e o cartão "1" pegava o primeiro da lista, não o marcado.

**Decisão.** O botão é **Transcrever N**, com N igual ao número de marcados e o tempo estimado embaixo. A proteção contra rodada acidental é a confirmação, que lista até 5 vídeos, a quantidade e o tempo, centralizada sobre a janela. Os atalhos Pendentes, Todos e Nenhum ficam.

**Consequências.** (+) Um gesto a menos e nenhuma ambiguidade sobre quais vídeos rodam. (−) Quem deixa tudo marcado e clica rápido vê a confirmação como única barreira; por isso ela lista os vídeos.

**Adendo (v0.1.9, N13).** O cabeçalho "Como ler este arquivo" ganhou a instrução de avisar quando o conteúdo não puder ser lido, em vez de inventar. É uma mitigação: reduz o risco, não o elimina. O app não tem como saber o que a IA realmente abriu.


---

## ADR-020: SHA-256 no build enquanto o `.exe` não é assinado

**Data:** 14/10/2026 · **Status:** aceita (provisória até o P7) · **Origem:** o Chrome marcou o artefato como "perigoso" no teste real

**Decisão.** O build grava `SHA256.txt` ao lado do `.exe` e mostra o hash no resumo da execução, para conferir a integridade com `Get-FileHash`. Foi testado e removido um segundo artefato com zip protegido por senha: o responsável baixou o normal sem ele, e um `.exe` em zip com senha é justamente o padrão de distribuição de malware, o que prejudicaria a credibilidade de um repositório público.

**Consequências.** (+) Quem baixar consegue conferir o arquivo. (−) O aviso do Chrome/SmartScreen continua até a assinatura de código (P7); o README explica como abrir.

**Atualização (15/10/2026):** o `SHA256.txt` vem no mesmo zip e por isso só confere a cópia. O hash que vale é o da página do Release, que o build preenche sozinho com o do `.exe` e o do `.zip` (achados B3/K7).

## ADR-021: O `.zip` não redistribui binário GPL; o FFmpeg é baixado na primeira abertura

**Data:** 15/10/2026 · **Status:** aceita · **Origem:** auditorias de 14/10/2026 (B2 do Codex, K2 do Claude)

**Contexto.** O `.zip` levava o `ffmpeg.exe` da build "essentials" de gyan.dev (GPL v3, com bibliotecas externas) e, sem ninguém notar, o PyAV, cujas rodas para Windows embutem FFmpeg com libx264 e libx265 (GPL). A oferta de código-fonte apontava só para o FFmpeg "puro", o que não cobre o código-fonte correspondente dessas builds. As duas auditorias trataram isso como bloqueio do Release.

**Decisão.**
1. **PyAV fora do executável.** O faster-whisper só o importa para `decode_audio()`, que o app nunca chama: o áudio é lido pelo FFmpeg e entregue como array ([ADR-003](#adr-003)). No `.exe`, `packaging/entrada_janela.py` registra um módulo `av` vazio antes de tudo; qualquer uso dele falha com uma mensagem clara. O autoteste do build confere que o PyAV verdadeiro e as DLLs libx264/libx265 não entraram.
2. **FFmpeg baixado pelo usuário.** A Preparação do PC baixa, com um clique, a versão fixa (9.0.2) do GitHub do próprio distribuidor, confere o SHA-256 gravado em `preparacao.FFMPEG` e extrai só `ffmpeg.exe`, `ffprobe.exe` e a licença para a pasta do usuário, com um `ORIGEM.txt`. Quem distribui o FFmpeg continua sendo o distribuidor.

**Alternativas.** (a) Anexar ao Release o código-fonte completo das duas builds: trabalhoso (dezenas de bibliotecas, configuração da build) e fácil de errar. (b) Mandar instalar pelo `winget`: o Windows Sandbox e parte dos PCs não têm `winget`. (c) Build própria de FFmpeg LGPL: fora do alcance de um beta.

**Consequências.** (+) O `.zip` fica só com código MIT/BSD/Apache e similares; versão do FFmpeg fixada por hash (resolve a parte do X14 que fala do FFmpeg). (−) Primeiro uso baixa ~115 MB a mais; precisa de internet na primeira vez, como o modelo. (−) Trocar a versão do FFmpeg exige atualizar URL, tamanho e hash juntos.
