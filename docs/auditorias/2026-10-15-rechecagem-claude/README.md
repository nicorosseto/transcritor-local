# Rechecagem dos bloqueios de 14/10: Claude, 15/10/2026

Resposta ao [pedido de rechecagem](../PEDIDO_RECHECAGEM_2026-10-15.md). Commit conferido: **`8ada040`** (`main`, v0.1.14). Escopo: `84c6ab1..8ada040` (11 commits; código em `97d0c71`, `7b510cf` e `51e3e15`). Não é auditoria completa: só os bloqueios de 14/10 e o que as correções podem ter aberto.

O código, os testes e os manifests **não foram alterados**; esta pasta só acrescenta o relatório e dois scripts de reprodução. A resposta do outro auditor **não foi lida** (até 15/10/2026 13:10, horário de São Paulo, ela não estava na `main`).

## Parecer

| Pergunta | Resposta |
|---|---|
| Release pre-release com o `.zip` | **Sim.** Os 5 bloqueios estão resolvidos. Antes de clicar em "Publicar" no rascunho, conferir o nome do arquivo e os SHA-256 no corpo (B3) e corrigir dois textos (B2 e B3). |
| Tornar o repositório **público** | **Sim, depois de apagar os artefatos antigos do Actions (R1).** Os artefatos dos builds 1 a 20 (até 14/10/2026 22:59, horário de São Paulo) ainda levam o FFmpeg GPL e o PyAV com libx264/libx265. Com o repositório público, qualquer conta logada no GitHub pode baixá-los: é a mesma redistribuição que o B2 bloqueou, por outro canal. |

## Os bloqueios, um por linha

| Achado | Veredito | Evidência |
|---|---|---|
| **K1** | ✅ **Resolvido** | `auditoria_k1.py`: as 3 partes OK (botão travado durante a leitura, releitura com a confirmação aberta cancela com o aviso "A lista mudou", rodada normal registra `ok` nos 3 vídeos). `k01_ler_pasta_e_transcrever.py` (normal e `--na-hora`): Transcrever fica `disabled`, `_iniciar` não abre diálogo, nenhum "Pronto!" falso, `registro.csv` e tabela coerentes. Pela leitura do código, `_iniciar` guarda o projeto antes dos diálogos (inclusive os de FFmpeg e Tesseract) e aborta se ele mudou. |
| **B1 = K5** | ✅ **Resolvido** | `pytest -k b1`: 8 passaram. Os casos das duas auditorias, adaptados à nova assinatura e postos na linha de cabeçalho que o app escreve (para testar o confinamento, não só o regex): `../`, `../` por dentro de `capturas/`, caminho absoluto, `file://`, `%2e%2e`, `\`, `C:/`, UNC, link simbólico para fora, imagem da saída fora de `capturas/` e arquivo que não é imagem **não entram**; a captura legítima com espaço e acento entra. Link no texto lido da tela (K5 a1) não é seguido e fica no `.md` sem o arquivo. Ver [`b1_k5_pacote.py`](reproducoes/b1_k5_pacote.py). |
| **B2 = K2** | ✅ **Resolvido com ressalva** (leitura técnica, não parecer jurídico) | **O `.zip` não leva binário GPL:** sem `bin/`, PyAV fora (`excludes`), FFmpeg baixado pelo usuário do GitHub do distribuidor. A URL fixada responde 200 com **114.768.076 bytes** e **SHA-256 `60f46726…2047ba`**, iguais ao gravado em `preparacao.FFMPEG`; a função real extrai só `ffmpeg.exe`, `ffprobe.exe` e a licença. O build Windows de `51e3e15` passou no autoteste. Pacote gerado com o mesmo `.spec` no Linux: sem `av/`, `av.libs/`, libx264 ou libx265. **A trava do autoteste funciona:** com o PyAV de volta, o autoteste falha com "bibliotecas GPL no pacote", e na roda Windows do PyAV as DLLs se chamam `libx264-165-*.dll` e `libx265-*.dll`, que a mesma busca por nome pega. **A abordagem resolve a questão da GPL para o `.zip`:** sem binário GPL, a obrigação de oferecer o código-fonte correspondente não nasce para o projeto; quem distribui o FFmpeg é o gyan.dev, cujo README dentro do zip aponta o commit-fonte e a configuração. **Ressalvas:** (1) os artefatos antigos (R1, abaixo); (2) a asserção `SUBSTITUTO_TRANSCRITOR` não prova nada: o substituto entra em `sys.modules` antes de tudo, e ela passou mesmo com o PyAV verdadeiro no pacote. A ADR-021 diz que o autoteste confere "o PyAV verdadeiro"; quem confere é a busca pelas DLLs. (3) `LICENCAS_TERCEIROS.md`, que vai no `.zip`, diz "**Desde a v0.1.13**, o `.zip` não redistribui nenhum binário GPL": é a v0.1.14. |
| **B3 = K7** | ✅ **Resolvido com ressalva** | **Leitura estática:** `draft: true`, `prerelease: true` e `body_path: release_corpo.md` no `softprops/action-gh-release@v2`. O corpo troca `TranscritorLocal-windows.zip` pelo nome real e `<preenchido na publicação>` pelo SHA-256 do `.exe`, e acrescenta a tabela com o SHA-256 do `.zip` e do `.exe`. **Não executado:** não há tag nem Release no repositório, e não havia `pwsh` aqui para rodar o passo. O rascunho é a rede de segurança: nada vai ao ar sem o autor publicar. **Ressalva:** as notas (que viram o corpo do Release) e o README dizem "**112** testes"; em `8ada040` são **113** (o do N22 entrou depois). |
| **C1 + K3** | ✅ **Resolvido** | `auditoria_c1.py`: com a verificação antiga terminando por último, o cartão mostra "Preciso: large-v3-turbo" e nunca "small". `k03`: cenário A pede as 3 verificações e termina em "✓ PC pronto"; cenário B termina em "Rápido: small", sem ficar preso em "Verificando o PC...". O roteiro do Codex (`gui_verificacao_atrasada.py`) agora falha em `assert iniciou.wait(2)`, o que é esperado: o painel não verifica mais por conta própria, e o caminho que tinha o defeito deixou de existir. A fumaça nova refaz o mesmo cenário no caminho único. A troca de qualidade ao abrir uma pasta (`_ler_pasta`) também passa por `_opcoes_mudaram`. |

## Achado novo que bloqueia

| ID | Sev. | Problema | Evidência | O que fazer |
|---|---|---|---|---|
| **R1** | 🔴 bloqueia **tornar o repositório público** (não bloqueia o Release) | Os artefatos `TranscritorLocal-windows` dos builds **1 a 20** (de 07/10 a 14/10/2026, commits `2aed2d1` a `97d0c71`) foram gerados pelo workflow que embutia o `ffmpeg.exe`/`ffprobe.exe` do gyan.dev e o PyAV com libx264/libx265, junto com a oferta de fonte que o B2/K2 julgou insuficiente. Eles **não expiraram** (`expired: false`; os de 14/10 vencem em 12–13/01/2027). Segundo a [documentação do GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts), quem está logado e tem leitura do repositório baixa artefatos, e repositório público dá leitura a todos. Não é defeito aberto pelas correções: é o B2 fora do `.zip` do Release. | Builds 19 (`837ef59`) e 20 (`97d0c71`): artefatos de **189,7 MB**, contra **82,0 MB** do build 23 (`51e3e15`, já sem FFmpeg); a diferença bate com `ffmpeg.exe` + `ffprobe.exe` + `av.libs`. O passo "Embutir FFmpeg" existe de `c9b001f` (v0.1) até ser retirado em `7b510cf`. Não abri esses artefatos: o host de download é bloqueado pela rede desta sessão. | Antes de mudar a visibilidade: em **Actions → Build Windows (.exe)**, abrir cada execução até a 20 e apagar o artefato (ícone de lixeira em "Artifacts"), ou apagar as execuções. Da 21 em diante não há FFmpeg nem PyAV. Conferir depois que a lista de artefatos ficou só com os da 21 em diante. |

## Privacidade antes de abrir o repositório

**Nada encontrado** nos 47 commits (todos alcançáveis da `main`, que é a única branch no remoto) nem nos arquivos atuais:

- **E-mails:** autor e committer só com `noreply` (GitHub do proprietário e `noreply@anthropic.com`); nenhum outro e-mail no conteúdo do histórico.
- **Caminhos:** só exemplos (`C:/Users/fulano`, `/Users/fulano`, `D:\Cursos\…`, `C:\Users\<nome>` dentro do relatório de 14/10). Nenhum `/home/<nome>` real.
- **Segredos:** nenhum padrão de token GitHub, Hugging Face, OpenAI, AWS, Slack, Google ou chave privada.
- **Vídeos e cursos:** nomes de vídeo só sintéticos (`a.mp4`, `aula.mp4`, `slides.mp4`…). Não encontrei nome de curso real; o nome removido anteriormente não está registrado em lugar nenhum, então procurei por padrões. O registro da máquina corporativa não traz nome de vídeo, empresa nem produtora.
- **Binários:** nenhum arquivo binário entrou no escopo; as imagens são as auditadas em 14/10.

**Decisões do autor, não defeitos** (já citadas no K20): um commit (`6f3147c`) tem o nome completo "Nícolas Novais Rosseto" como autor, e 45 mensagens trazem `Claude-Session: https://claude.ai/...`. Esta rechecagem foi enviada na branch `claude/clever-maxwell-mu6xlm`: mesclar a pasta na `main` e **apagar a branch** antes de abrir o repositório, como foi feito com as do K20.

## Observações que não bloqueiam

- **C1/K3, primeiro uso:** se a qualidade for trocada antes de a primeira verificação voltar, a Preparação deixa de abrir sozinha, porque o pedido de abrir fica no pedido descartado ([`c1_abrir_preparacao.py`](reproducoes/c1_abrir_preparacao.py)). Como o `.zip` não traz mais o FFmpeg, esse é o primeiro uso de todo mundo. O selo, a piscada do botão e o diálogo "Falta o FFmpeg" ao clicar Transcrever continuam levando à Preparação, e antes da correção esse caminho ficava preso em "Verificando o PC...". Para a v0.2: levar o `abrir` para o novo pedido.
- **B1:** um *hardlink* dentro de `capturas/` entra no pacote. É o mesmo arquivo com dois nomes, fisicamente dentro da pasta; criá-lo exige o mesmo acesso que copiar o arquivo para lá. Não é saída da pasta.
- **B2:** o cartão da Preparação e o `ORIGEM.txt` dizem "versão oficial". É a build de terceiros do gyan.dev (recomendada pelo site do FFmpeg), não uma build do projeto FFmpeg; "versão oficial do distribuidor" seria mais exato.
- **Scripts de 14/10:** os do pacote (`reproducoes.py` do Codex e `k05_k10_k17_pacote.py`) não rodam mais como estão, porque `pacote.montar` ganhou o parâmetro `raiz_capturas`. Por isso foram adaptados aqui, sem mudar os registros originais.

## Comandos e resultados

| Comando | Resultado |
|---|---|
| `python -m pip install -r requirements.txt pytest pyflakes` + `pip check` | ok, sem conflito |
| `python -m pytest -q` | **113 passed** em 33 s |
| `python -m pyflakes transcritor tests` | sem saída, código 0 |
| Fumaças sob Xvfb 1366x768: `auditoria_k1`, `auditoria_c1`, `ffmpeg_primeiro_uso`, `janela_basica`, `rodada_completa`, `rodada_tela_falha`, `pacote_para_ia`, `cancelar_rodada`, `acao_e_confirmacao`, `previsao_no_ocr`, `maquina_limpa`, `escala_do_windows` 1,25 e 1,5 | **todas código 0** |
| Reproduções de 14/10: `k01` (2 modos), `k03`, `gui_verificacao_atrasada` | ver tabela dos bloqueios |
| CI na ponta | "Testes" verde em `8ada040` (Linux e Windows, Python 3.11 e 3.13); "Build Windows" verde em `51e3e15`, último commit que muda o app |

Saídas em [`reproducoes/saidas.txt`](reproducoes/saidas.txt).

## Ambiente e limites

- Ubuntu 24.04, Python 3.12.3 com Tk 8.6, FFmpeg 6.1.1, Tesseract 5.3.4 (`por`, `eng`), Xvfb. Dependências resolvidas em 15/10/2026: faster-whisper 1.2.1, ctranslate2 4.8.3, av 19.0.1, customtkinter 6.0.0, onnxruntime 1.31.0, numpy 2.5.4, pillow 12.3.0, PyInstaller 6.22.3 (só para gerar o pacote, fora do repositório).
- **Sem Windows.** Não abri o artefato do build Windows: o download dele é bloqueado pela rede desta sessão. Isso foi suprido pelo log do build, pela roda Windows do PyAV e pelo pacote equivalente gerado no Linux. O teste do responsável na máquina corporativa ([registro](../../testes/2026-10-15-maquina-corporativa.md)) foi lido como evidência fornecida, não reproduzido.
- **B3 sem execução:** sem tag, o passo do Release nunca rodou. Conferir o rascunho antes de publicar.
- Modelo de transcrição simulado (o `ModeloFalso` dos testes); a verificação do PC foi simulada onde o script diz.
- Licenças: leitura técnica, não parecer jurídico.

## Como reproduzir

Na raiz do repositório, com as dependências do pedido, FFmpeg e Tesseract no `PATH`:

```bash
python3.12 docs/auditorias/2026-10-15-rechecagem-claude/reproducoes/b1_k5_pacote.py
xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-15-rechecagem-claude/reproducoes/c1_abrir_preparacao.py
```

Trava do PyAV no autoteste: copiar `packaging/transcritor.spec`, `entrada_janela.py` e `icone.ico` para uma pasta temporária, fixar `RAIZ` no caminho do repositório, tirar `"av"` de `excludes`, gerar com `pyinstaller <cópia>/transcritor.spec --distpath <tmp>` e rodar `TranscritorLocal --autoteste`. O resultado esperado é o código 1 com "bibliotecas GPL no pacote". Com o `.spec` original, o resultado é "autoteste ok".
