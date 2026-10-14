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

## Fechar a janela no meio (v0.1.11, conferido pelo `registro.csv` enviado)

Janela fechada com **Sair mesmo assim** durante o 1º vídeo e reaberta nas mesmas pastas: os dois vídeos voltaram **Pendente**, sem `transcricoes_md`, sem capturas e **sem arquivo `.parcial`** em `audio_mp3`; só ficou o MP3 já completo do vídeo curto, que o app descarta e refaz por não ter a assinatura registrada. Comportamento correto.

## Relatado pelo responsável, sem log

N11 numa 2ª rodada na mesma pasta com um vídeo: "deu certo". Falta o log com a linha "Previsão da rodada" para anexar ao registro. Gemini com o `.md` solto: dispensado pelo responsável; o efeito do cabeçalho "não invente" **não foi verificado** (só o ChatGPT foi visto lendo corretamente).

## Ainda não testado

Escalas 125%/150% em monitor real (simuladas: N16).
