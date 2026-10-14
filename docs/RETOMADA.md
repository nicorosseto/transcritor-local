# Retomada: onde o projeto parou

Arquivo para continuar o trabalho numa próxima sessão (pessoa ou IA). Atualize ao fim de cada sessão.

**Última atualização:** 14/10/2026 · **Versão:** 0.1.4 · **Branch:** `main`

## 1. Estado atual

| Frente | Situação |
|---|---|
| Motor (transcrição, OCR, registro, base consolidada) | Estável. 51 testes automáticos passando no CI (Linux e Windows, Python 3.11 e 3.13) |
| Auditoria independente de 08/10/2026 (X1 a X16) | **15 de 16 corrigidos**, cada um com teste que falhava antes. Falta só o X14 (pré-publicação). Ver [auditorias/STATUS.md](auditorias/STATUS.md) |
| Lentidão (P17) | Resolvida: threads = núcleos físicos (ADR-015). No PC de referência, 1,34x virou ~1,57x no trecho medido |
| Layout aprovado (fase 3) | Implementado (ADR-017): barra lateral, preto, verde só no clicável, logotipo e ícone do `.exe`. Conferido em 1366x768 com modelo simulado |
| Build do `.exe` | Automático a cada push na `main` (GitHub Actions → "Build Windows (.exe)" → artefato `TranscritorLocal-windows`) |
| Repositório | Privado. Publicar só depois do teste no Windows e do X14 (contra-auditoria, seção 7) |

## 2. Teste do responsável no Windows (P1): primeira rodada feita em 14/10/2026

**Resultado:** a rodada completa funcionou (1 vídeo de 36 min, Equilibrado, com OCR): **1,68x**, 6 threads, 27 min no total, base consolidada com todos os links válidos. Registro completo em [testes/2026-10-14-windows-p1.md](testes/2026-10-14-windows-p1.md).

Achados novos (nenhum quebra a rodada), em ordem de prioridade:

| ID | Sev. | Resumo |
|---|---|---|
| N1 | 🟠 | OCR quase ilegível em vídeo 640x360: ampliar a captura (2x a 3x) antes do Tesseract e filtrar palavras de baixa confiança |
| N2 | 🟡 | "Palavras" conta fala + texto de tela (12.197 contra ~7.100 de fala): separar `palavras` e `palavras_tela` |
| N3 | 🟡 | 448 de 548 capturas ficam sem uso em disco: apagar as não usadas depois do OCR |
| N4 | 🟡 | Previsão inicial 37% acima do real: conferir se converge na 2ª rodada |
| N5, N6 | ⚪ | Texto "0 pendente(s), menos de 1 min" e rótulo "Tesseract pronto" antes do download do português |

**Próximo passo:** o responsável aprova o plano de correção de N1 a N3 e N5/N6 (teste que falha antes, correção depois). Antes de fechar o N1, medir o ganho em mais de 1 quadro e com o pacote `por`. Ainda faltam do roteiro: Parar, Cancelar, fechar a janela no meio, escalas 125%/150%, ícone na barra de tarefas e a estimativa da 2ª rodada.

Roteiro original do teste:

1. Baixar o artefato do último build verde e extrair (um zip, um `TranscritorLocal.exe`).
2. Abrir. Se faltar o modelo, o app abre em **Preparação do PC**: baixar o modelo.
3. **Vídeos** → Origem: uma pasta real com subpastas. Conferir a lista, as durações e o nome do projeto na barra lateral.
4. Marcar 1 vídeo, escolher o cartão **1**, **Transcrever 1** em **Equilibrado**. Anotar a velocidade final (esperado: ~1,5x no PC de referência; antes era 1,22x).
5. Repetir com **Ler texto da tela** ligado, num vídeo com slides.
6. **Resultados**: conferir a tabela e o registro de atividades. **Abrir base consolidada**.
7. Testar **Parar após este vídeo**, **Cancelar** e fechar a janela no meio de uma rodada.
8. Conferir a aparência com escala do Windows em 125% e 150% e o ícone na barra de tarefas.
9. Mandar prints de qualquer coisa estranha. **Não colar dados sigilosos** (anonimizar nomes de arquivos de trabalho).

## 3. Depois do teste

| Ordem | Item | Referência |
|---|---|---|
| 1 | Corrigir N1 a N6 (teste de 14/10/2026) e fechar o resto do roteiro do P1 | [testes/2026-10-14-windows-p1.md](testes/2026-10-14-windows-p1.md) |
| 2 | X14: travar dependências e conferir hashes (FFmpeg, tessdata, modelo) | STATUS.md |
| 3 | P7 (assinatura do `.exe` / SmartScreen) e P8 (licença do FFmpeg) | AUDITORIA.md |
| 4 | Tornar o repositório público | contra-auditoria, seção 7 |
| 5 | Formatos de saída: HTML navegável primeiro, depois SRT/VTT, TXT, JSONL/CSV | ROADMAP.md |
| 6 | v0.2: IA visual local | ROADMAP.md |

## 4. Regras do projeto (combinadas com o responsável)

- **Privacidade:** nunca colocar e-mail pessoal, nome de curso, nomes de arquivos reais do responsável ou qualquer referência particular em commits ou arquivos. Commits usam o e-mail `noreply` do GitHub.
- **Correções:** teste que falha **antes**, correção depois; registrar o ID (X…, P…) no STATUS.md.
- **Documentação:** português do Brasil, datas DD/MM/AAAA, decisões novas viram ADR em [DECISOES.md](DECISOES.md), cada versão ganha uma seção no [HISTORICO.md](HISTORICO.md).
- **Pastas datadas em `docs/auditorias/`** são registros imutáveis; só o STATUS.md muda.
- **Antes de mudar algo grande**, mostrar o plano ao responsável e esperar a aprovação.

## 5. Comandos úteis (ambiente de desenvolvimento)

```
python3 -m pytest -q                                  # 51 testes do motor
python3 -m pyflakes transcritor tests ferramentas     # lint
xvfb-run -a python3.12 ferramentas/fumaca/rodada_completa.py      # janela de verdade, modelo simulado
xvfb-run -a -s "-screen 0 1366x768x24" python3.12 ferramentas/capturar_telas.py /tmp/telas
PYTHONPATH=. python3 docs/auditorias/2026-10-11-fase2/reproducoes_depois.py   # script do Codex
```

No Windows do responsável: `python ferramentas/medir_threads.py "C:\caminho\do\video.mp4"` mede a velocidade com 4, 6 e 12 threads.

## 6. Onde está cada coisa

| Assunto | Arquivo |
|---|---|
| Layout e logotipo aprovados (referência visual) | [design/](design/) |
| Paleta e tema da janela | `transcritor/gui/tema.py` |
| Logotipo e ícone | `transcritor/gui/marca.py`, `packaging/icone.ico` |
| Estado final da rodada (janela e terminal) | `transcritor/resultado.py` |
| Identidade do projeto e chave de saída | `transcritor/pipeline.py` (`projeto.json`), `transcritor/registro.py` (coluna `saida`) |
| Pesquisa de formatos de exportação | [ROADMAP.md](ROADMAP.md), seção "Formatos de saída" |
