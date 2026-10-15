# Retomada: onde o projeto parou

Arquivo para continuar o trabalho numa próxima sessão (pessoa ou IA). Atualize ao fim de cada sessão.

**Última atualização:** 15/10/2026 · **Versão:** 0.1.14 · **Branch:** `main`

## 1. Estado atual (15/10/2026)

**Resumo:** a v0.1.14 tem todos os bloqueios das duas auditorias de pré-publicação corrigidos e testados aqui. **Falta só o teste do responsável no Windows (seção 1.1) e a decisão de publicar.** O repositório continua privado.

| Frente | Situação |
|---|---|
| Motor (transcrição, OCR, registro, base consolidada) | Estável. 112 testes automáticos (Linux e Windows, Python 3.11 e 3.13; no Windows, 4 de OCR pulados) e 13 fumaças de interface |
| Auditorias de 08/10 (X1 a X16) | 15 de 16 corrigidas; X14 parcial (FFmpeg fixado por hash; dependências Python na v0.2) |
| Auditorias de pré-publicação de 14/10 (Codex B1-B3/C1-C6, Claude K1-K20) | **Bloqueios corrigidos na v0.1.14** (K1, B1/K5, B2/K2, B3/K7) e mais 9 correções menores. O resto está na lista da v0.2. Tabela em [auditorias/STATUS.md](auditorias/STATUS.md) |
| Licenças | O `.zip` não leva binário GPL: FFmpeg baixado na primeira abertura com SHA-256 fixo; PyAV fora do executável ([ADR-021](DECISOES.md)) |
| Testes reais | 5 rodadas no PC do responsável, máquina limpa (Windows Sandbox) com a v0.1.13 e teste cego com 3 IAs ([testes/](testes/)) |
| Release | Workflow cria **rascunho** de **pre-release** ao subir uma tag `v*`, com as notas de `docs/release/<tag>.md` e os SHA-256 preenchidos. Notas da próxima: [release/v0.1.14.md](release/v0.1.14.md) |
| Repositório | Privado. Antes de abrir: apagar pelo site as branches `claude/funny-volta-uacma0`, `docs/auditoria-beta-v0.1.13`, `docs/auditoria-codex-2026-10-08` e `fix/auditoria-fase1` (o conteúdo das auditorias já está na `main`; o proxy desta sessão não deixou apagar) |

### 1.1 Próxima sessão: roteiro de testes do responsável

Estes testes são do responsável (combinado em 15/10/2026). O que mudou desde o último teste no Sandbox: o FFmpeg não vem mais no zip, o PyAV saiu do executável, e a interface ganhou as correções K1, C1/K3, B1.

| # | Onde | O que fazer | Esperado |
|---|---|---|---|
| 1 | GitHub | Apagar as 4 branches antigas (aba **Branches**) | Só `main` |
| 2 | Windows Sandbox novo | Baixar o artefato `TranscritorLocal-windows` do build mais recente da v0.1.14, abrir o `.exe` | Título "Transcritor Local 0.1.14"; pasta sem `bin/`; `licencas/` com `BIBLIOTECAS.txt` |
| 3 | Preparação do PC | Clicar em **Baixar FFmpeg** | Barra de progresso até ~115 MB, depois "Baixado pelo app (versão oficial 9.0.2)" |
| 4 | Preparação do PC | Rápido, baixar o modelo small; instalar o Tesseract | Como na v0.1.13 |
| 5 | Vídeos | Origem, depois saída; 2 vídeos curtos, com "Ler texto da tela" | Os dois concluídos; `.md` com fala e texto de tela. **Esta é a prova de que o app funciona sem o PyAV** |
| 6 | Vídeos | Clicar em **Ler pasta** e, logo em seguida, tentar clicar em **Transcrever** | Botão travado enquanto lê (K1) |
| 7 | Preparação do PC | Clicar em **Verificar de novo** e trocar a qualidade logo depois | O cartão do modelo acompanha a qualidade da tela (C1/K3) |
| 8 | Resultados | **Pacote para IA** | Pasta e `.zip` com o `.md` e as imagens |
| 9 | (opcional) Codex e Claude | Rechecagem só dos bloqueios: [pedido](auditorias/PEDIDO_RECHECAGEM_2026-10-15.md) | Sem bloqueio novo |

Passando, publicar: tornar o repositório público, criar a tag `v0.1.14` (o workflow cria o rascunho do Release), conferir a página e clicar em **Publicar**. Depois, o post do LinkedIn.

## 2. Teste do responsável no Windows (P1)

**1ª rodada (14/10/2026), v0.1.4:** funcionou (1 vídeo de 36 min, Equilibrado, com OCR): **1,68x**, 6 threads, 27 min, base consolidada com links válidos. Registro em [testes/2026-10-14-windows-p1.md](testes/2026-10-14-windows-p1.md).

**v0.1.5** corrigiu o que ela achou (N1, N2, N3, N5, N6, N7; o N4 é a previsão conservadora, conferir na 2ª rodada) e acrescentou o formato para IA. Detalhes no [STATUS.md](auditorias/STATUS.md).

**2ª rodada (v0.1.5):** fala 100% idêntica à da 1ª, mas 0 trechos de tela (N8). Registro em [testes/2026-10-14-windows-p1-rodada2.md](testes/2026-10-14-windows-p1-rodada2.md).

**3ª rodada (v0.1.6):** OCR leu 91 trechos; ChatGPT e Gemini entenderam o vídeo só pelo `.md` ([registro](testes/2026-10-14-windows-p1-rodada3.md)).

**4ª rodada (v0.1.7):** N9 funcionou (80 trechos), Cancelar e refazer ok, previsão 37 min contra 28 reais ([registro](testes/2026-10-14-windows-p1-rodada4.md)). A v0.1.8 trouxe botão único, confirmação centralizada, N10, N11, N12; a v0.1.9 (N13) responde ao Gemini que inventou um resumo: cabeçalho "não invente" e aviso sobre `.zip`.

**5ª rodada (v0.1.12):** Parar, Cancelar com feedback, fechar no meio e retomar ok ([registro](testes/2026-10-14-windows-p1-rodada5.md)).

**Máquina limpa (v0.1.12, Windows Sandbox):** primeiro uso do zero funcionou até a transcrição, mas achou N17 a N20; o N20 parava a rodada ([registro](testes/2026-10-14-sandbox-maquina-limpa.md)).

**Máquina limpa, repetição (v0.1.13):** ponta a ponta sem erro, com e sem OCR. **Teste cego com 3 IAs** (Haiku, Sonnet e Opus 5.5, sem contexto): nenhuma inventou conteúdo; o OCR perdeu o texto de um diagrama colorido (N21) ([registro](testes/2026-10-14-ia-cega.md)).

**Auditorias de pré-publicação (14/10) e v0.1.14 (15/10):** ver a seção 1. Para o histórico, a tabela abaixo é o roteiro da 5ª rodada:

| O que | Esperado |
|---|---|
| Mesmo vídeo de baixa resolução, com "Ler texto da tela" | Texto de tela legível (antes era ruído); OCR ~1,8x mais lento por captura (+3 min em 36 min de vídeo) |
| `registro.csv` | Coluna `palavras_tela`; `palavras` perto de 7.100 (só a fala) |
| Pasta `capturas` | Só as imagens citadas no `.md` |
| Previsão da rodada | Perto do tempo real (agora usa a velocidade medida no 1º vídeo) |
| Resultados → **Pacote para IA** | Pasta `pacote_para_ia` com `.md` e `imagens\` (e `.zip`); links abrem |
| Um `.md` anexado a uma IA qualquer | A IA explica o vídeo e entende o cabeçalho "Como ler este arquivo" |
| Ainda do roteiro | Escalas 125%/150% em monitor real (N16 corrigiu o que a simulação mostrou) e o log do N11 (relatado como ok). Parar, Cancelar, Sair mesmo assim (conferido no registro) e ícone na barra de tarefas já foram vistos ([rodada 5](testes/2026-10-14-windows-p1-rodada5.md)) |

Roteiro original do teste (1ª rodada):

1. Baixar o artefato do último build verde e extrair (um zip, um `TranscritorLocal.exe`).
2. Abrir. Se faltar o modelo, o app abre em **Preparação do PC**: baixar o modelo.
3. **Vídeos** → Origem: uma pasta real com subpastas. Conferir a lista, as durações e o nome do projeto na barra lateral.
4. Marcar 1 vídeo, escolher o cartão **1**, **Transcrever 1** em **Equilibrado**. Anotar a velocidade final (esperado: ~1,5x no PC de referência; antes era 1,22x).
5. Repetir com **Ler texto da tela** ligado, num vídeo com slides.
6. **Resultados**: conferir a tabela e o registro de atividades. **Abrir base consolidada**.
7. Testar **Parar após este vídeo**, **Cancelar** e fechar a janela no meio de uma rodada.
8. Conferir a aparência com escala do Windows em 125% e 150% e o ícone na barra de tarefas.
9. Mandar prints de qualquer coisa estranha. **Não colar dados sigilosos** (anonimizar nomes de arquivos de trabalho).

**Se o Chrome bloquear o download ("arquivo perigoso"):** o `.exe` não tem assinatura digital (P7), e o PyInstaller costuma cair em falso positivo. Opções, nesta ordem: (1) `chrome://downloads` → **Manter arquivo perigoso**; (2) baixar com o Edge.. O build imprime o SHA-256 do `.exe` no resumo da execução e grava `SHA256.txt` na pasta, para conferir com `Get-FileHash`.

## 3. Depois da publicação

| Ordem | Item | Referência |
|---|---|---|
| 1 | Post no LinkedIn (rascunho na conversa de 14/10; atualizar com as auditorias e o teste cego) | — |
| 2 | v0.2, OCR: filtro que não descarte siglas (C3/K4) e captura em cinza ampliada 2x para diagramas coloridos (N21) | ROADMAP.md |
| 3 | v0.2, robustez: previsão durante a fala (C2), base consolidada atômica (C5), estimativa (K6), sobras e trava (K15, K16), pacote fora da thread da interface (K19) | auditorias/STATUS.md |
| 4 | v0.2, build: dependências Python com hash e autoteste que abre a janela (K8, X14); Tesseract no CI do Windows (K12) | auditorias/STATUS.md |
| 5 | Embutir o Tesseract (Apache 2.0) e o português no zip | ROADMAP.md |
| 6 | P7: assinatura do `.exe` | AUDITORIA.md |
| 7 | Formatos de saída (HTML navegável primeiro) e IA visual local | ROADMAP.md |

## 4. Regras do projeto (combinadas com o responsável)

- **Privacidade:** nunca colocar e-mail pessoal, nome de curso, nomes de arquivos reais do responsável ou qualquer referência particular em commits ou arquivos. Commits usam o e-mail `noreply` do GitHub.
- **Correções:** teste que falha **antes**, correção depois; registrar o ID (X…, P…) no STATUS.md.
- **Documentação:** português do Brasil, datas DD/MM/AAAA, decisões novas viram ADR em [DECISOES.md](DECISOES.md), cada versão ganha uma seção no [HISTORICO.md](HISTORICO.md).
- **Pastas datadas em `docs/auditorias/`** são registros imutáveis; só o STATUS.md muda.
- **Antes de mudar algo grande**, mostrar o plano ao responsável e esperar a aprovação.

## 5. Comandos úteis (ambiente de desenvolvimento)

```
python3 -m pytest -q                                  # 112 testes do motor
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
