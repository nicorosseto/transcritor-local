# Histórico do projeto

Como o projeto saiu de "preciso que uma IA entenda 40 vídeos" e chegou a um app desktop. Registrado porque os erros do caminho explicam as decisões do código.

## Linha do tempo (07/10/2026)

| Etapa | O que aconteceu | O que aprendemos |
|---|---|---|
| **1. O problema** | ~40 vídeos de 500 MB a 1 GB+. Nenhum chat aceita upload desse tamanho; conversores "MP4 para MD" online não funcionaram | Não existe "MP4 para MD": o caminho é **vídeo → áudio → texto**. E não é "treinar" a IA, é **dar fontes de consulta** (RAG/grounding) |
| **2. Pesquisa de rotas** | Três rotas avaliadas: NotebookLM com MP3 (sem código), **Whisper local** (escolhida), Groq (nuvem grátis, 25 MB por arquivo, 8 h/dia) | Local vence em privacidade e não depende de cota |
| **3. Script v1** | Script único: FFmpeg + faster-whisper + `.md` com timestamps + base consolidada | — |
| **4. Ambiente** | Python 3.13.3 já instalado (dentro do OneDrive); FFmpeg via winget; `pip install faster-whisper` OK | OneDrive sincronizando milhares de arquivos do pip pode travar a instalação: pausar antes |
| **5. 1º erro real** | `open() got an unexpected keyword argument 'metadata_errors'` | PyAV 19 removeu o parâmetro que o faster-whisper 1.2.1 usa → decodificar com FFmpeg ([ADR-003](DECISOES.md)). Erro reproduzido em ambiente idêntico antes de corrigir |
| **6. Previsão de tempo** | O usuário confundiu "posição / duração" com previsão | Adicionados velocidade, tempo restante do vídeo e do lote, e horário de término |
| **7. 1º resultado** | video_referencia.mp4: 36:43 em 24:49 (**1,48x**, beam 5), 7.136 palavras, qualidade boa | Erros concentrados em termos em inglês e marcas ("Hulk"→hook, "Chatipete"→ChatGPT) → vocabulário de dicas ([ADR-009](DECISOES.md)) |
| **8. Requisitos de lote** | Subpastas espelhadas, base por subpasta, limite obrigatório por rodada | Nomes iguais em pastas diferentes **colidiam** na v1 |
| **9. "Como ele sabe o que já fez?"** | Na v1, era só pelo nome do `.md` | Vídeo substituído era pulado; vídeo excluído continuava na base → `registro.csv` ([ADR-006](DECISOES.md)) |
| **10. Conteúdo visual** | Parte dos vídeos tem ações em tela | OCR agora; IA visual local depois, só nos vídeos escolhidos ([ADR-004](DECISOES.md)) |
| **11. Hardware** | Xeon E5-2620 v3 (6C/12T, AVX2), 16 GB DDR4 (rodando a 1866, limite da CPU), RX 560 XT 8 GB | A AMD não acelera o motor atual; com 16 GB, a IA visual 4B é viável, mas lenta (~1–2 min/captura, estimado) |
| **12. App + GitHub** | Motor refatorado em módulos, GUI, CLI, testes, build automatizado, docs | Ver lacunas encontradas abaixo |

## Bugs encontrados durante a construção da v0.1

Todos foram pegos por testes (automatizados ou de fumaça) **antes** de chegar ao usuário:

| # | Bug | Como foi pego | Correção |
|---|---|---|---|
| 1 | dHash 8x8 não distinguia slides de fundo claro (distância 3–5) | Teste `test_capturas_detectam_troca_de_slide` | dHash 16x16 |
| 2 | Subprocessos (ffmpeg) herdavam o teclado e "comiam" respostas do terminal | Teste de fumaça da CLI com respostas simuladas | `stdin=DEVNULL` em todos os subprocessos |
| 3 | Textos cortados e estimativa escondida no painel de opções | Captura de tela da GUI em display virtual | Layout com largura mínima e caixa de estimativa fixa |
| 4 | Resumo do topo não atualizava ao fim da rodada | Mesma captura | `_atualizar_resumo()` em `lote_fim` |
| 5 | Ponto de entrada do PyInstaller com import relativo | Build real do PyInstaller | `packaging/entrada_*.py` |
| 6 | Excluir o PyAV do pacote quebrava o carregamento do modelo | Execução do binário congelado | PyAV mantido no pacote |
| 7 | `.exe` de janela sem stdout/stderr derrubaria o download do modelo | Revisão do empacotamento | `garantir_saidas_padrao()` + exe de terminal separado |

## v0.1.1 (08/10/2026): o primeiro teste real no Windows

O usuário baixou o build do GitHub e rodou o vídeo de referência no próprio PC. O que o teste revelou:

| Achado | Correção |
|---|---|
| OCR marcado, mas não rodou: o Tesseract não estava instalado e o aviso se perdeu no log | Diálogo bloqueante antes de iniciar |
| Dois `.exe`: o de terminal "abriu uma tela preta e sumiu"; zip dentro de zip | Um `.exe`, um zip, `COMO_ABRIR.txt` |
| Em PC novo, ninguém explica que há um download de 1,6 GB | Tela "Verificar PC e preparar" com download e progresso |
| Linhas de log ("Extraindo áudio...") pareciam processo em andamento | Painel de etapas + log recolhível com horário |
| Janela "Verificar PC" abria atrás da principal | Modal, centralizada, com som |
| App 18% mais lento que o script | Diagnóstico no registro (P17) |
| Vocabulário vazio → mesmos erros de marcas | Correções automáticas por projeto (ADR-011) |

Durante a reconstrução da interface, um teste em display virtual pegou um **travamento** que congelaria o app no primeiro vídeo (C19): objetos de fonte do Tk destruídos pelo coletor de lixo numa thread de trabalho.

## v0.1.2 (11/10/2026): correções da auditoria independente (fase 1)

O Codex auditou a v0.1.1 de forma independente e encontrou 16 problemas (X1 a X16). O Claude revisou a auditoria, reproduziu os achados e reordenou as severidades ([contra-auditoria](auditorias/2026-10-08/CONTRA_AUDITORIA_CLAUDE.md)). A fase 1 corrigiu os nove que podiam **corromper ou esconder** resultados. Para cada um, o teste foi escrito antes da correção e falhou pelo motivo certo.

| Problema | Correção |
|---|---|
| Vídeo substituído era refeito com o **áudio antigo** em cache (X1) | O registro sabe de qual versão do vídeo veio o `.mp3` |
| `aula.mp4` e `aula.mkv` escreviam no mesmo `.md` (X2) | Chave de saída fixa por vídeo (ADR-013) |
| Trocar a pasta depois de "Ler pasta" misturava registro e saídas (X3) | Leitura descartada ao editar; rodada recusa pastas diferentes |
| Base consolidada era apagada antes de a nova ficar pronta (X5) | Troca só no fim, a partir de uma pasta temporária |
| `.md` apagado continuava "concluído" (X6) | Volta a pendente |
| Saída de outro curso era aceita em silêncio (X7) | `projeto.json` + confirmação |
| "Ler pasta" não atualizava a base (X11) | Atualiza |
| Threads de trabalho ainda agendavam no Tk (X13) | Só pela fila (ADR-014); fechamento seguro |
| Erro inesperado aparecia como **sucesso**, com som (X16) | Estado fatal explícito |

Status completo por ID: [auditorias/STATUS.md](auditorias/STATUS.md).

**Lentidão resolvida na mesma versão.** O usuário rodou o `medir_threads.py` no PC de referência: 4 threads = 1,57x, 6 = 1,56x, 12 = 1,34x. O app usava 12 (todas as threads lógicas). Com o padrão em núcleos físicos (ADR-015), a transcrição fica ~15% mais rápida, o que explica a diferença para o script v1.

## v0.1.3 (11/10/2026): auditoria fase 2

| Problema | Correção |
|---|---|
| A trava aceitava a mesma janela duas vezes e não era atômica (X4) | Criação exclusiva, sem reentrada; "Ler pasta" também trava |
| Falha do Tesseract ou do FFmpeg nas capturas parecia "sem texto na tela" (X10) | Erro explícito; rodada termina **parcial** e a tabela mostra "tela não lida" |
| Terminal saía com código 0 mesmo com tudo falhando (X12) | Códigos 0/1/2/3 |
| Cancelar não interrompia a extração do áudio (X13) | FFmpeg encerrado na hora |
| A cópia de emergência do registro (Excel aberto) era ignorada (X15) | Recuperada ao abrir |
| Links das capturas quebravam na base consolidada (X8) | Recalculados |
| Um vídeo enorme estourava o limite de palavras da base (X9) | Dividido entre parágrafos |

Com isso, 15 dos 16 achados da auditoria independente estão corrigidos; falta só o X14 (reprodutibilidade do build), previsto para antes de publicar.

## v0.1.4 (11/10/2026): novo layout

O responsável escolheu, entre três propostas, a navegação com barra lateral (proposta C), o esforço da proposta B e as cores da A, com fundo todo preto e verde só no que é clicável. Também aprovou o logotipo "da onda à linha" (ADR-017).

| Antes | Agora |
|---|---|
| Uma tela longa com cabeçalho, opções e um painel de log | Barra lateral + páginas Vídeos, Resultados e Preparação do PC |
| Quantidade num menu suspenso e estimativa num bloco de texto | Cartões 1 / 3 / 5 / Todos com o tempo de cada um, ao lado de "Transcrever N" |
| "Verificar PC" em janela por cima | Página própria, aberta sozinha quando falta algo obrigatório |
| Tema claro/escuro do sistema, azul | Preto, lateral `#0A1612`, verde `#4FD18B` só no clicável |
| Ícone padrão do Python | Logotipo na janela e no `.exe` |

As telas foram conferidas em 1366x768 com o modelo simulado (`ferramentas/capturar_telas.py`). **Ainda não foram vistas no Windows real.**

## v0.1.5 (14/10/2026): correções do primeiro teste real e formato para IA

Primeira rodada completa no Windows (1 vídeo de 36 min, Equilibrado, com OCR): **1,68x**, 27 min, base consolidada correta. O teste achou sete problemas, todos corrigidos com teste que falhava antes ([registro](testes/2026-10-14-windows-p1.md), [ADR-018](DECISOES.md)).

| ID | O que mudou |
|---|---|
| N1 | OCR amplia capturas estreitas 2x e descarta palavras de baixa confiança. Em 2 quadros com texto conhecido, a precisão foi de 48% e 4% para 79% e 73%; a cobertura, de 39% e 2% para 55% e 47% |
| N2 | `palavras` conta só a fala; nova coluna `palavras_tela` no `registro.csv` |
| N3 | Capturas que o OCR não aproveita são apagadas na hora (eram 82% do espaço) |
| N5, N6 | Resumo "nenhum pendente" e aviso de que o português do Tesseract será baixado |
| N7 | Links de captura em pastas com espaço quebravam na base consolidada; agora vão codificados e a base entende os `.md` antigos |
| — | Cabeçalho "Como ler este arquivo" e botão **Pacote para IA** |

**Lição:** o N7 só apareceu porque o pacote para IA exigiu links certos. O teste real achou o que os 51 testes automáticos não achavam (vídeo de baixa resolução e pastas com espaço no nome).

**Custo:** o OCR ficou ~1,8x mais lento por captura em vídeo estreito. **Ainda não foi visto no Windows real**: precisa de nova rodada.

## v0.1.6 (14/10/2026): o OCR da v0.1.5 não lia nada

A 2ª rodada no Windows (mesmo vídeo, pasta de saída nova, OCR ligado) mostrou a fala **100% idêntica** à da 1ª, `palavras` correto (~7.100) e a coluna `palavras_tela`, mas **0 trechos de tela** ([registro](testes/2026-10-14-windows-p1-rodada2.md)).

| ID | Causa | Correção |
|---|---|---|
| N8 | A v0.1.5 pedia ao Tesseract a configuração `tsv`, que ele procura em `<pasta de idiomas>/configs/`. A pasta do app (criada por `baixar_portugues`) só tem `por` e `eng`; o Tesseract avisava no erro, devolvia texto comum e o filtro descartava tudo sem avisar | `-c tessedit_create_tsv=1` (não depende de arquivo); saída que não começa com `level` vira `ErroOCR`; cabeçalho, log e Resultados dizem "nenhum texto aproveitável em N capturas" em vez de "sim, 0 trecho(s)" |

**Lição:** os testes da v0.1.5 usavam a pasta de idiomas do sistema (com `configs/`); o app usa a sua própria. Agora há teste com uma pasta de idiomas sem `configs/`, igual à do app, e o OCR nunca confunde "formato errado" com "imagem sem texto". Em 50 capturas reais, a versão corrigida achou 14 trechos úteis.

**Observações da rodada:** 30 min 10 s (fala 23 min 24 s, OCR 6 min 26 s); velocidade 1,57x contra 1,68x (causa não identificada: carga do PC ou ctranslate2 4.8.3 no lugar da 4.8.2, ver X14). Previsão de ~37 min repetiu, como esperado em pasta de saída nova (N4 segue por conferir).

## v0.1.7 (14/10/2026): limpeza do texto de tela

A 3ª rodada (v0.1.6) leu 91 trechos em 548 capturas, mas 31% das linhas eram lixo de OCR em letra pequena ([registro](testes/2026-10-14-windows-p1-rodada3.md)).

| ID | O que mudou |
|---|---|
| N9 | `ocr.limpar` descarta linhas em que menos de 60% das letras estão em palavras de 4+ letras (rótulos curtos reais como "Compartilhar" e "Opus 47" ficam) e descarta o bloco quando menos de 40% das linhas sobram. Sobre o `.md` real: 6.398 → 5.371 palavras de tela e 8 de 91 blocos descartados |

**Decisão com dados:** subir a confiança de 50 para 60 tirava 18 linhas de lixo, mas também 9 linhas boas (3%) em 31 capturas; o filtro de linha pega o lixo sem esse custo. Confiança continua em 50.

## v0.1.8 (14/10/2026): barra de ação simples e estimativa honesta

A 4ª rodada (v0.1.7, dois vídeos na mesma saída, com um Cancelar no meio) mostrou: texto de tela de 6.398 para 5.216 palavras (N9 ok), cancelar e refazer funcionando (MP3 reaproveitado), 28 min 15 s contra 37 previstos ([registro](testes/2026-10-14-windows-p1-rodada4.md)).

| ID | O que mudou |
|---|---|
| — | Os cartões 1/3/5/Todos saíram. O botão é **Transcrever N** (marcados na lista) com o tempo ao lado; a confirmação lista os vídeos ([ADR-019](DECISOES.md)) |
| N10 | Tabela repintada ao fim de uma rodada cancelada (ficava "Transcrevendo" e "Na fila") |
| N11 | A estimativa só aprende com vídeos de 3 min ou mais e pondera pela duração |
| N12 | Confirmação centralizada nos dois eixos, maior, com borda verde |
