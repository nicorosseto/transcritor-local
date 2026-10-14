# Teste real no Windows, 2ª rodada (14/10/2026)

**Versão:** 0.1.5 · **Vídeo:** o mesmo da 1ª rodada (36 min, baixa resolução) · **Modo:** Equilibrado, "Ler texto da tela" ligado, pasta de saída nova.

## Resultado

| Item | 1ª rodada (v0.1.4) | 2ª rodada (v0.1.5) |
|---|---|---|
| Duração | 27 min | 30 min 10 s (fala 23 min 24 s, OCR 6 min 26 s) |
| Velocidade da fala | 1,68x | 1,57x (causa não identificada) |
| Palavras de fala | ~7.100 | 7.105 |
| Fala entre as rodadas | referência | 100% idêntica (determinística, mesmo com ctranslate2 4.8.2 → 4.8.3) |
| Coluna `palavras_tela` | não existia | presente |
| Texto de tela | ruído | **0 trechos** (defeito N8) |
| Previsão inicial | ~37 min | ~37 min (esperado em pasta de saída nova; N4 por conferir) |
| Pasta `capturas` | 82% inútil | vazia (todas apagadas como sem uso) |

## Achado

**N8 (crítico):** o OCR descartava tudo. Causa e correção em [STATUS.md](../auditorias/STATUS.md) e no [ADR-018](../DECISOES.md). Corrigido na v0.1.6.

## Ainda não testado

N4 (estimativa com um 2º vídeo na mesma saída), Parar/Cancelar/fechar no meio da rodada, escalas 125%/150%, ícone na barra de tarefas, botão **Pacote para IA**.
