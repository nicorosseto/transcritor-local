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
| N22 | Sem administrador, o `winget` instala o Tesseract em `%LOCALAPPDATA%\Programs\Tesseract-OCR` e muda só o PATH do usuário; o app só procurava em `Program Files` e no PATH antigo do processo | Corrigido no commit `51e3e15` (procura nessa pasta e relê o PATH do registro). Falta conferir no build novo |
| N23 | A caixa "Ler texto da tela" só avisa que falta o Tesseract ao clicar em Transcrever | A corrigir depois desta sessão: aviso em laranja com "Instalar agora" e diálogo ao marcar a caixa |
