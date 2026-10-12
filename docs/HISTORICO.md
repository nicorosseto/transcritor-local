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
