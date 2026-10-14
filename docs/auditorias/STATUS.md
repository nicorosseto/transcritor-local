# Auditorias: índice e status por achado

Este é o **único arquivo que muda** depois de cada rodada. As pastas datadas são registros imutáveis.

| Rodada | Autor | Conteúdo |
|---|---|---|
| [2026-10-08](2026-10-08/README.md) | Codex (independente) | Achados X1 a X16, evidências, revisão de interface |
| [2026-10-08 · contra-auditoria](2026-10-08/CONTRA_AUDITORIA_CLAUDE.md) | Claude | Reprodução, severidades revisadas, hipótese da lentidão (P17) |
| [2026-10-11 · fase 1](2026-10-11-fase1/) | Claude | Script do Codex rodado de novo depois das correções |
| [2026-10-11 · fase 2](2026-10-11-fase2/) | Claude | Idem, depois da fase 2 |

Status: ✅ corrigido · ⏳ pendente · 🔎 em medição. Severidade da contra-auditoria.

## Fase 1 (v0.1.2, 11/10/2026)

Regra de aceite: cada teste foi escrito **antes** da correção e falhou no commit `c919adc` pelo motivo certo (12 de 13; o 13º protege a estabilidade do nome e já passava). Todos em [`tests/test_auditoria_fase1.py`](../../tests/test_auditoria_fase1.py).

| ID | Sev. | Status | O que mudou | Teste |
|---|---|---|---|---|
| X1 | 🔴 | ✅ | O `registro.csv` guarda de qual versão do vídeo veio o `.mp3` (`audio_de`). Se o vídeo mudou, o áudio é extraído de novo | `test_x1_video_substituido_reextrai_o_audio` |
| X3 | 🔴 | ✅ | Editar as pastas descarta a leitura anterior; a rodada só começa com as **mesmas** pastas lidas (`Projeto.preparar_rodada`); pastas e botões ficam travados durante a rodada | `test_x3_rodada_recusa_pastas_diferentes_da_leitura` + teste de fumaça da janela |
| X13 | 🔴 | ✅ | Nenhuma thread de trabalho toca o Tk: tudo passa pela fila (`App.na_interface`). Fechar a janela pede parada e espera até ~10 s a thread salvar o registro | `test_x13_threads_de_trabalho_nao_tocam_o_tk` (guarda de regressão) |
| X16 | 🔴 | ✅ | Erro inesperado vira estado **fatal** explícito, com um único `lote_fim`. A tela final usa `resultado.py`: nunca mostra sucesso sem sucesso; som de sucesso só em sucesso. CLI devolve código 1 em falha fatal | `test_x16_erro_inesperado_vira_falha_fatal_explicita`, `test_x16_tela_final_nunca_mostra_sucesso_sem_sucesso` |
| X2 | 🟠 | ✅ | Cada vídeo ganha uma **chave de saída** fixa (`saida`). `aula.mp4` e `aula.mkv` geram `aula.md` e `aula [mp4].md`, e o primeiro nunca muda de nome ([ADR-013](../DECISOES.md)) | `test_x2_mesmo_nome_com_extensoes_diferentes_nao_colide`, `test_x2_chave_de_saida_e_estavel_quando_surge_irmao` |
| X5 | 🟠 | ✅ | Base consolidada montada numa pasta temporária e trocada só no fim; falha no meio preserva a base anterior. `.md` com bytes inválidos não derruba mais | `test_x5_falha_na_consolidacao_preserva_base_anterior`, `test_x5_md_com_bytes_invalidos_nao_derruba_a_consolidacao` |
| X6 | 🟠 | ✅ | Vídeo "concluído" sem `.md` volta a pendente, com observação no registro | `test_x6_md_apagado_volta_a_pendente` |
| X7 | 🟠 | ✅ | `projeto.json` na saída guarda a pasta de vídeos de origem. Outra origem exige confirmação ("A pasta foi movida" / `--pasta-movida`). `.md` solto só é adotado em saídas de versões antigas | `test_x7_saida_de_outra_origem_exige_confirmacao`, `test_x7_nao_adota_md_so_por_existir_em_projeto_novo` |
| X11 | 🟠 | ✅ | "Ler pasta" já atualiza a base consolidada | `test_x11_ler_pasta_atualiza_a_base_consolidada` |

### Script do Codex, antes e depois

| Cenário | Antes (`2026-10-08/evidencias.json`) | Depois (`2026-10-11-fase1/evidencias_depois.json`) |
|---|---|---|
| `md_ausente` (X6) | 0 pendentes | **1 pendente** ✅ |
| `troca_raiz` (X7) | aceito como OK com texto de outra origem | **bloqueado até confirmar** ✅ |
| `base_falha` (X5) | exceção e base anterior apagada | **sem exceção**, base preservada ✅ |
| `substituicao_audio` (X1) | FFmpeg não chamado | igual, **por desenho**: o script chama `midia.extrair_audio` isolada; a invalidação fica no orquestrador e é provada pelo teste X1 de ponta a ponta |
| `colisao_extensoes` (X2) | caminhos iguais | igual, **por desenho**: o script consulta `aula.mkv` sem ele existir no registro; com os dois arquivos na pasta, o teste X2 prova caminhos distintos |
| `limite_base`, `trava_reentrante`, `link_base`, `falha_capturas`, `falha_ocr` | — | sem mudança: são X9, X4, X8 e X10 (fase 2) |

### Desempenho (P17)

| Threads | Velocidade (3 min de fala, beam 1, PC de referência 6C/12T) |
|---|---|
| 4 | **1,57x** |
| 6 | 1,56x |
| 12 (padrão até a v0.1.1) | 1,34x |

✅ Hipótese da contra-auditoria confirmada. O padrão agora é o número de **núcleos físicos** ([ADR-015](../DECISOES.md)); teste em `tests/test_desempenho.py`.

## Fase 2 (v0.1.3, 11/10/2026)

Mesma regra: testes em [`tests/test_auditoria_fase2.py`](../../tests/test_auditoria_fase2.py), escritos antes e falhando no commit `1b8b073` (14 de 16; os outros 2 protegem comportamentos que já existiam: código 0 em sucesso e divisão por parágrafo).

| ID | Sev. | Status | O que mudou | Teste |
|---|---|---|---|---|
| X4 | 🟠 | ✅ | Trava criada de forma atômica (`O_EXCL`), sem reentrada, só apagada por quem a criou; trava abandonada é retomada. "Ler pasta" também usa a trava, e a janela não dispara duas leituras | `test_x4_trava_nao_e_reentrante`, `test_x4_trava_e_atomica_entre_threads`, `test_x4_leitura_da_pasta_respeita_a_trava` |
| X10 | 🟠 | ✅ | Erro do FFmpeg nas capturas e erro do Tesseract viram falha explícita, não "sem texto". A fala é salva; o vídeo fica "✅ concluído · ⚠️ tela não lida", com motivo no `.md` e no registro (`ocr = falhou`), e a rodada termina **parcial**. OCR pedido mas indisponível também é parcial | 4 testes `test_x10_*` |
| X12 | 🟡 | ✅ | CLI: 0 concluído · 1 falha · 2 parcial · 3 parado/cancelado · 130 Ctrl+C (`resultado.codigo_saida`) | `test_x12_codigo_de_saida_da_cli` (3 cenários) |
| X13 (resto) | — | ✅ | A extração de áudio obedece ao cancelamento: o FFmpeg é encerrado e o `.mp3` parcial apagado | `test_x13_extracao_de_audio_obedece_ao_cancelamento` |
| X15 | 🟡 | ✅ | Ao abrir, a cópia `registro_PENDENTE_feche_o_excel.csv` mais nova é recuperada (aviso no resumo) e apagada no próximo salvamento | `test_x15_registro_pendente_e_recuperado_ao_abrir` |
| X8 | 🟡 | ✅ | Links das capturas reescritos para valer a partir da pasta da base | `test_x8_links_das_capturas_funcionam_na_base` |
| X9 | 🟡 | ✅ | Vídeo maior que o limite é dividido entre parágrafos (palavra a palavra só se um parágrafo sozinho passar do limite); o cabeçalho conta no limite | `test_x9_*` |
| Híbrido | — | ✅ (dedução) | Em CPU Intel híbrida no Windows, threads = núcleos de desempenho ([ADR-015](../DECISOES.md)). Lógica testada; a leitura da CPU no Windows não pôde ser testada sem o hardware | `test_cpu_hibrida_usa_so_nucleos_de_desempenho` |

### Script do Codex depois da fase 2 (`2026-10-11-fase2/evidencias_depois.json`)

| Cenário | Antes | Depois |
|---|---|---|
| `limite_base` (X9) | 33 palavras com limite 10 | **10** ✅ |
| `trava_reentrante` (X4) | 2ª entrada aceita e trava apagada | **2ª entrada recusada**, trava preservada ✅ |
| `link_base` (X8) | não resolve na base | **resolve na base** ✅ |
| `falha_capturas` (X10) | lista vazia | **erro explícito** ✅ |
| `falha_ocr` (X10) | texto vazio | **erro explícito** ✅ |

Todos os 16 achados da auditoria de 08/10/2026 estão corrigidos, exceto X14 (pré-publicação).

## Teste real no Windows (v0.1.5 a v0.1.8, 14/10/2026)

Achados do primeiro teste fora do ambiente de desenvolvimento. Testes em [`tests/test_teste_real_p1.py`](../../tests/test_teste_real_p1.py), escritos antes e falhando no commit `6ec55eb`. Registro: [testes/2026-10-14-windows-p1.md](../testes/2026-10-14-windows-p1.md).

| ID | Sev. | Status | O que mudou |
|---|---|---|---|
| N1 | 🟠 | ✅ (limiar provisório) | OCR amplia capturas estreitas e filtra por confiança. Calibrar o limiar com mais vídeos |
| N2 | 🟡 | ✅ | `palavras` = fala; `palavras_tela` à parte |
| N3 | 🟡 | ✅ | Capturas sem uso apagadas |
| N4 | 🟡 | ✅ (v0.1.8) | Previsão inicial conservadora por desenho; o aprendizado foi corrigido no N11 |
| N5, N6 | ⚪ | ✅ | Textos da interface |
| N7 | 🟠 | ✅ | Links de captura com espaço (achado no caminho) |
| N12 | ⚪ | ✅ (v0.1.8) | Confirmação aparecia deslocada e para cima: o `CTkToplevel` nasce com 200x200 e a centralização media isso. Agora usa o tamanho real, centraliza nos dois eixos e ganhou borda verde |
| N11 | 🟡 | ✅ (v0.1.8) | Estimativa aprendia com um vídeo de 42 s (1,2x) como se valesse tanto quanto um de 36 min (1,7x). Agora ignora vídeos com menos de 3 min e pondera pela duração (e o OCR por hora também). Fecha o N4 |
| N10 | 🟡 | ✅ (v0.1.8) | Depois de **Cancelar** (ou Parar), a tabela seguia mostrando "Transcrevendo" e "Na fila" em vídeos que não terminaram. Agora é repintada ao fim da rodada. Reproduzido por `ferramentas/fumaca/cancelar_rodada.py` |
| N9 | 🟡 | ✅ (v0.1.7) | Ruído no texto de tela: 31% das linhas lidas eram lixo ("Es Ou ou mu ou"). `ocr.limpar` descarta linhas ilegíveis e blocos dominados por ruído; confiança segue 50 (60 perdia 3% de linhas boas) |
| N8 | 🔴 | ✅ (v0.1.6) | OCR da v0.1.5 descartava **todo** o texto de tela com a pasta de idiomas do app (sem `configs/tsv`). Agora usa `-c tessedit_create_tsv=1` e falha de forma explícita se a saída não for TSV |

## Pré-publicação

| ID | Status | Próximo passo |
|---|---|---|
| X14 | ⏳ | Dependências travadas e hashes do FFmpeg, tessdata e modelo |
| P1, P7, P8 | ⏳ | Ver [AUDITORIA.md](../AUDITORIA.md) |
