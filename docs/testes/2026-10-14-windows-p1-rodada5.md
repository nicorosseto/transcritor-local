# Teste real no Windows, 5ª rodada (14/10/2026)

**Versões:** 0.1.9 (rodada completa e diálogo de saída) e 0.1.10 (Cancelar) · mesmos dois vídeos, pasta de saída nova, Equilibrado, texto da tela ligado.

| Item | Resultado |
|---|---|
| Botão único **Transcrever N** e confirmação centralizada | Funcionaram (prints) |
| Rodada completa | 28 min 06 s contra 37 min previstos (+32%; previsão inicial de pasta nova, como esperado) |
| Velocidade | 42 s: 1,3x · 36 min: 1,7x |
| Fala / OCR | 21 min 37 s / 5 min 35 s (548 capturas); 80 trechos de tela; 7.105 palavras |
| **Parar após este vídeo** | Funcionou |
| **Cancelar** (v0.1.10) | Feedback imediato e botões travados: funcionou |
| **Fechar a janela no meio** | Apareceu "Sair? Há uma rodada em andamento..." com **Sair mesmo assim** / **Continuar rodando**, centralizado e com borda verde: comportamento esperado |
| Ícone na barra de tarefas | Aparece o logotipo do app (print) |
| **N15** | "Rodada 83%" e término vencido parados durante o texto de tela: corrigido na v0.1.11 |

## Ainda não testado

Confirmar o fim do **Sair mesmo assim** (processos encerrados, vídeo refeito na reabertura), N11 numa 2ª rodada na mesma pasta, escalas 125%/150%, Gemini com o `.md` solto.
