# Auditorias: índice e status por achado

Este é o **único arquivo que muda** depois de cada rodada. As pastas datadas são registros imutáveis.

| Rodada | Autor | Conteúdo |
|---|---|---|
| [2026-10-08](2026-10-08/README.md) | Codex (independente) | Achados X1 a X16, evidências, revisão de interface |
| [2026-10-08 · contra-auditoria](2026-10-08/CONTRA_AUDITORIA_CLAUDE.md) | Claude | Reprodução, severidades revisadas, hipótese da lentidão (P17) |
| [2026-10-11 · fase 1](2026-10-11-fase1/) | Claude | Script do Codex rodado de novo depois das correções |

Status: ✅ corrigido · ⏳ pendente · 🔎 em medição. Severidade da contra-auditoria.

## Fase 1 (v0.1.2, 11/10/2026)

Regra de aceite: cada teste foi escrito **antes** da correção e falhou no commit `c919adc` pelo motivo certo (12 de 13; o 13º protege a estabilidade do nome e já passava). Todos em [`tests/test_auditoria_fase1.py`](../../tests/test_auditoria_fase1.py).

| ID | Sev. | Status | O que mudou | Teste |
|---|---|---|---|---|
| X1 | 🔴 | ✅ | O `registro.csv` guarda de qual versão do vídeo veio o `.mp3` (`audio_de`). Se o vídeo mudou, o áudio é extraído de novo | `test_x1_video_substituido_reextrai_o_audio` |
| X3 | 🔴 | ✅ | Editar as pastas descarta a leitura anterior; a rodada só começa com as **mesmas** pastas lidas (`Projeto.preparar_rodada`); pastas e botões ficam travados durante a rodada | `test_x3_rodada_recusa_pastas_diferentes_da_leitura` + teste de fumaça da janela |
| X13 | 🔴 | ✅ | Nenhuma thread de trabalho toca o Tk: tudo passa pela fila (`App.na_interface`). Fechar a janela pede parada e espera até ~10 s a thread salvar o registro | `test_x13_threads_de_trabalho_nao_tocam_o_tk` (guarda de regressão) |
| X16 | 🔴 | ✅ | Erro inesperado vira estado **fatal** explícito, com um único `lote_fim`. A tela final usa `gui/estado.py`: nunca mostra sucesso sem sucesso; som de sucesso só em sucesso. CLI devolve código 1 em falha fatal | `test_x16_erro_inesperado_vira_falha_fatal_explicita`, `test_x16_tela_final_nunca_mostra_sucesso_sem_sucesso` |
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

## Fase 2 (pendente)

| ID | Sev. | Status | Próximo passo |
|---|---|---|---|
| X4 | 🟠 | ⏳ | Trava atômica (criação exclusiva), sem reentrada, cobrindo também a leitura |
| X10 | 🟠 | ⏳ | Distinguir "sem texto", "OCR indisponível" e "erro técnico"; conclusão parcial |
| X15 | 🟡 | ⏳ | Recuperar `registro_PENDENTE_feche_o_excel.csv` ao abrir |
| X8 | 🟡 | ⏳ | Recalcular links das capturas na base consolidada |
| X9 | 🟡 | ⏳ | Dividir também um vídeo maior que o limite |
| X12 | 🟡 | ⏳ (parcial) | Código 1 em falha fatal já entrou; falta distinguir falha parcial e cancelamento |
| X13 (resto) | — | ⏳ | A extração de áudio (FFmpeg) ainda não observa o cancelamento |

## Pré-publicação

| ID | Status | Próximo passo |
|---|---|---|
| X14 | ⏳ | Dependências travadas e hashes do FFmpeg, tessdata e modelo |
| P1, P7, P8 | ⏳ | Ver [AUDITORIA.md](../AUDITORIA.md) |
