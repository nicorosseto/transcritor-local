# Retomada: onde o projeto parou

Arquivo para continuar o trabalho numa próxima sessão (pessoa ou IA). Atualize ao fim de cada sessão.

**Última atualização:** 14/10/2026 · **Versão:** 0.1.10 · **Branch:** `main`

## 1. Estado atual

| Frente | Situação |
|---|---|
| Motor (transcrição, OCR, registro, base consolidada) | Estável. 76 testes automáticos (CI em Linux e Windows, Python 3.11 e 3.13) |
| Auditoria independente de 08/10/2026 (X1 a X16) | **15 de 16 corrigidos**, cada um com teste que falhava antes. Falta só o X14 (pré-publicação). Ver [auditorias/STATUS.md](auditorias/STATUS.md) |
| Lentidão (P17) | Resolvida: threads = núcleos físicos (ADR-015). No PC de referência, 1,34x virou ~1,57x no trecho medido |
| Layout aprovado (fase 3) | Implementado (ADR-017): barra lateral, preto, verde só no clicável, logotipo e ícone do `.exe`. Conferido em 1366x768 com modelo simulado |
| Teste real no Windows (P1) | 2 rodadas feitas em 14/10/2026. A 2ª achou o N8 (OCR não lia nada), **corrigido na v0.1.6**; a 3ª rodada confirmou o OCR (91 trechos) e a v0.1.7 limpa o ruído (N9); falta conferir a v0.1.7 (ver seção 2) |
| Formato para IA | Cabeçalho "Como ler este arquivo" em todo `.md` e botão **Pacote para IA** ([ADR-018](DECISOES.md)) |
| Build do `.exe` | Automático a cada push na `main` (GitHub Actions → "Build Windows (.exe)" → artefato `TranscritorLocal-windows`) |
| Repositório | Privado. Publicar só depois do teste no Windows e do X14 (contra-auditoria, seção 7) |

## 2. Teste do responsável no Windows (P1)

**1ª rodada (14/10/2026), v0.1.4:** funcionou (1 vídeo de 36 min, Equilibrado, com OCR): **1,68x**, 6 threads, 27 min, base consolidada com links válidos. Registro em [testes/2026-10-14-windows-p1.md](testes/2026-10-14-windows-p1.md).

**v0.1.5** corrigiu o que ela achou (N1, N2, N3, N5, N6, N7; o N4 é a previsão conservadora, conferir na 2ª rodada) e acrescentou o formato para IA. Detalhes no [STATUS.md](auditorias/STATUS.md).

**2ª rodada (v0.1.5):** fala 100% idêntica à da 1ª, mas 0 trechos de tela (N8). Registro em [testes/2026-10-14-windows-p1-rodada2.md](testes/2026-10-14-windows-p1-rodada2.md).

**3ª rodada (v0.1.6):** OCR leu 91 trechos; ChatGPT e Gemini entenderam o vídeo só pelo `.md` ([registro](testes/2026-10-14-windows-p1-rodada3.md)).

**4ª rodada (v0.1.7):** N9 funcionou (80 trechos), Cancelar e refazer ok, previsão 37 min contra 28 reais ([registro](testes/2026-10-14-windows-p1-rodada4.md)). A v0.1.8 trouxe botão único, confirmação centralizada, N10, N11, N12; a v0.1.9 (N13) responde ao Gemini que inventou um resumo: cabeçalho "não invente" e aviso sobre `.zip`.

**Próximo passo: 5ª rodada (em andamento) com a v0.1.10 ([Parar após este vídeo] já validado; Cancelar sem feedback virou N14), mais o teste do Gemini com o `.md` solto**, mesmo vídeo, pasta de saída nova. O build roda sozinho no push; se não rodar, GitHub → Actions → **Build Windows (.exe)** → **Run workflow** (branch `main`) e baixar o artefato `TranscritorLocal-windows`. O título da janela deve mostrar v0.1.10. Conferir:

| O que | Esperado |
|---|---|
| Mesmo vídeo de baixa resolução, com "Ler texto da tela" | Texto de tela legível (antes era ruído); OCR ~1,8x mais lento por captura (+3 min em 36 min de vídeo) |
| `registro.csv` | Coluna `palavras_tela`; `palavras` perto de 7.100 (só a fala) |
| Pasta `capturas` | Só as imagens citadas no `.md` |
| Previsão da rodada | Perto do tempo real (agora usa a velocidade medida no 1º vídeo) |
| Resultados → **Pacote para IA** | Pasta `pacote_para_ia` com `.md` e `imagens\` (e `.zip`); links abrem |
| Um `.md` anexado a uma IA qualquer | A IA explica o vídeo e entende o cabeçalho "Como ler este arquivo" |
| Ainda do roteiro | Parar, Cancelar, fechar a janela no meio, escalas 125%/150%, ícone na barra de tarefas |

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

**Se o Chrome bloquear o download ("arquivo perigoso"):** o `.exe` não tem assinatura digital (P7), e o PyInstaller costuma cair em falso positivo. Opções, nesta ordem: (1) `chrome://downloads` → **Manter arquivo perigoso**; (2) baixar com o Edge; (3) baixar o artefato **TranscritorLocal-windows-protegido** (zip com senha `transcritor`, abre no WinRAR ou 7-Zip). O build imprime o SHA-256 do `.exe` no resumo da execução e grava `SHA256.txt` na pasta, para conferir com `Get-FileHash`.

## 3. Depois do teste

| Ordem | Item | Referência |
|---|---|---|
| 1 | Fechar o P1: 2ª rodada no Windows com a v0.1.5 e o resto do roteiro; calibrar o limiar de confiança do OCR (P3) | seção 2 |
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
python3 -m pytest -q                                  # 76 testes do motor
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
