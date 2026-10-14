# Teste real no Windows, 3ª rodada (14/10/2026)

**Versão:** 0.1.6 · mesmo vídeo (36 min, baixa resolução), Equilibrado, texto da tela ligado, pasta de saída nova.

## Resultado

| Item | Resultado |
|---|---|
| Duração | 28 min 41 s (fala 22 min 53 s a 1,6x; OCR 5 min 39 s, ~0,6 s por captura) |
| Texto de tela | **91 trechos em 548 capturas** (antes: 0, defeito N8) |
| Pacote para IA | Pasta e `.zip` gerados; 91 de 91 links válidos; 91 imagens, todas citadas |
| Tamanho do `.md` | 90 KB; 7.105 palavras de fala e 6.398 de tela |
| Ruído | 31% das linhas de tela ilegíveis; 12 de 91 blocos majoritariamente ruído (achado N9) |

## Leitura por IA (só o `.md`, sem as imagens)

O `.md` foi anexado ao ChatGPT e ao Gemini, com o pedido de resumir a aula, listar os passos e dizer o que aparece na tela ao falar do agente roteirista.

| Critério | ChatGPT | Gemini |
|---|---|---|
| Resumo e passos da aula | Completo, com tempos | Completo |
| Ligou a fala ao "Na tela" mais próximo | Sim, tabela com tempos | Sim, por tempo |
| Normalizou erros de OCR pelo contexto | Sim, e avisou que normalizou | Sim |
| Entendeu que não havia imagens | Sim, avisou o limite da análise visual | Não avisou |

Conclusão: o `.md` basta para entender o conteúdo e a ordem da aula; o que falta é o visual (cores, layout), como o cabeçalho já avisa. O cabeçalho "Como ler este arquivo" funcionou: o ChatGPT citou o limite e os dois usaram os blocos "Na tela" como pretendido.

## Achado

**N9:** ruído no texto de tela. Corrigido na v0.1.7 ([STATUS](../auditorias/STATUS.md)).

## Ainda não testado

N4, Parar/Cancelar/fechar no meio da rodada, escalas 125%/150%, ícone na barra de tarefas.
