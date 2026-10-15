# Teste da v0.1.14 numa máquina corporativa (15/10/2026)

**Objetivo:** primeiro uso da v0.1.14 (FFmpeg baixado pelo app, PyAV fora do executável) num PC que não é o de desenvolvimento.

**Ambiente:** Windows corporativo **sem permissão de administrador**; Intel Core i7-13700 (8 núcleos de desempenho + 8 de eficiência, 24 threads), 32 GB de RAM, placas AMD e Intel (não aceleram o motor). Dois vídeos curtos de teste, sem dados de trabalho (8:58 e 2:48). Qualidade Equilibrado, sem leitura de tela.

## Resultado

| # | Passo | Resultado |
|---|---|---|
| 2 | Abrir a v0.1.14 | ✅ |
| 3 | **Baixar FFmpeg** pela Preparação | ✅ "Baixado pelo app (versão oficial 9.0.2)" |
| 4 | Modelo `large-v3-turbo` | ✅ |
| 4 | Tesseract pelo `winget` | ❌ "Instalado com êxito", mas o app não reconheceu (**N22**) |
| 5 | **Transcrever 2 vídeos sem o PyAV no executável** | ✅ Os dois concluídos com o modelo real. **Prova de que o app funciona sem o PyAV (ADR-021)** |
| 8 | Pacote para IA | ✅ Uma pasta e um `.zip` por vídeo, com o `.md` |
| N22 | Tesseract reconhecido no build com a correção | ✅ "Tudo pronto"; cartão "Instalado", sem administrador |
| OCR | Vídeo B com "Ler texto da tela" | ✅ O app baixou sozinho o português do Tesseract (~2 MB, N6); 4 capturas lidas, 2 trechos de tela no `.md`, imagens no pacote; 6,4x. **N21 se repete:** do diagrama de 7 caixas, o OCR leu só "GRAVAÇÃO" (mesmo resultado do Sandbox) |
| N19 | Trocar a pasta de saída | ✅ A pasta foi relida sozinha |
| K1 | Ler pasta com 55 vídeos e olhar o botão | ✅ Durante "Lendo a pasta e medindo as durações...", **Transcrever 55** e **Ler pasta** ficaram cinza (desabilitados) |

| Vídeo | Duração | Fala | Velocidade | Threads |
|---|---|---|---|---|
| A | 8:58 | 1.394 palavras em 1:57 | **4,6x** | 8 |
| B | 2:48 | 515 palavras em 0:34 | **4,9x** | 8 |

- **Threads:** 8 = só os núcleos de desempenho, como previsto para CPU híbrida (ADR-015). Rodada inteira: 2:41 para 11:46 de vídeo.
- **Qualidade Equilibrado × Rápido** (mesmo vídeo B, comparado com o teste em máquina limpa): o Equilibrado acertou os termos que o Rápido errou ("cortes" em vez de "escorte", "esteirinha" em vez de "esterinha", e o nome da produtora). Confirma a recomendação do README.
- **Previsão inicial:** ≈ 10 min contra 2:41 reais. Esperado no primeiro uso de um PC (não há medição anterior); durante a rodada, a previsão se corrigiu ("faltam ~1 min" aos 48%). Melhoria possível: estimativa inicial pelo número de núcleos de desempenho (v0.2).

## Achados

| ID | Achado | Situação |
|---|---|---|
| N21 | OCR lê só 1 das 7 caixas coloridas do diagrama | Limitação conhecida, igual nas duas máquinas; correção prevista na v0.2 (captura em cinza ampliada 2x leu as 7 caixas no teste de 14/10) |
| N22 | Sem administrador, o `winget` instala o Tesseract em `%LOCALAPPDATA%\Programs\Tesseract-OCR` e muda só o PATH do usuário; o app só procurava em `Program Files` e no PATH antigo do processo | Corrigido no commit `51e3e15` (procura nessa pasta e relê o PATH do registro) e **conferido no build** |
| N24 | A velocidade medida fica no `registro.csv` de cada pasta de saída: numa saída nova, no mesmo PC, a previsão volta à estimativa inicial (1,2x, quando o PC já tinha medido 4,6x a 6,4x) | v0.2: guardar a velocidade medida por PC, na pasta do usuário, e usar quando o projeto ainda não tem medição |
| N23 | A caixa "Ler texto da tela" só avisa que falta o Tesseract ao clicar em Transcrever | A corrigir depois desta sessão: aviso em laranja com "Instalar agora" e diálogo ao marcar a caixa |
