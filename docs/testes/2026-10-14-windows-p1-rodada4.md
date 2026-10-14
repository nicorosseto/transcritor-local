# Teste real no Windows, 4ª rodada (14/10/2026)

**Versão:** 0.1.7 · vídeo de 36 min (baixa resolução) e um vídeo de teste de 42 s, mesma pasta de saída, Equilibrado, texto da tela ligado. Primeiro um **Cancelar** logo no início, depois a rodada completa.

| Item | Resultado |
|---|---|
| Cancelar no meio do 1º vídeo | Parou em 7 s; aviso "será refeito"; registro salvo; MP3 já extraído mantido |
| Refazer | MP3 reaproveitado (extração instantânea), modelo já carregado |
| Tabela depois de cancelar | **Defeito N10**: seguiu "Transcrevendo" / "Na fila" |
| Duração da rodada | 28 min 15 s contra 37 min previstos (+31%) |
| Velocidade | 42 s: 1,2x · 36 min: 1,7x (vídeo curto tem tempo fixo de partida) |
| Texto de tela (v0.1.7) | 80 trechos em 548 capturas (antes 91); 5.216 palavras (antes 6.398); `.md` de 84 KB (antes 90) |
| Links | 80 de 80 válidos, 80 imagens, todas citadas |
| Fala | 7.105 palavras, idêntica às rodadas anteriores |

## Achados

- **N10:** tabela com rótulos velhos após cancelar.
- **N11:** a estimativa aprendia com o vídeo de 42 s como se fosse de 36 min.
- **N12:** confirmação deslocada.
- Pedido: botão único no lugar dos cartões de quantidade (ADR-019).

## Ainda não testado

Parar após este vídeo, fechar a janela no meio, escalas 125%/150%, ícone na barra de tarefas.
