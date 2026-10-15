# Transcritor Local

Transforma uma pasta de vídeos (aulas, palestras, reuniões gravadas) em **arquivos Markdown pesquisáveis**, prontos para qualquer IA ler (Claude, ChatGPT, Gemini, NotebookLM e outras). Tudo roda **no seu PC**: nenhum vídeo, áudio ou texto é enviado para a internet.

![Tela do Transcritor Local](docs/img/app.png)

<details><summary>Outras telas: Vídeos, Resultados e Preparação do PC</summary>

![Vídeos](docs/img/videos.png)

![Resultados](docs/img/resultados.png)

![Preparação do PC](docs/img/verificar_pc.png)

</details>

> **Status: v0.1.14, beta.** Como foi testado:
> - 112 testes automatizados a cada mudança, no Linux e no Windows (Python 3.11 e 3.13); no Windows, os 4 testes de OCR são pulados porque o CI não tem o Tesseract. O `.exe` é gerado e conferido no GitHub Actions.
> - Duas auditorias independentes antes da publicação (Codex e uma sessão nova do Claude), com os bloqueios corrigidos ([status](docs/auditorias/STATUS.md)).
> - 5 rodadas de uso real num PC com Windows, só CPU (vídeo de 36 min, fala a ~1,7x, texto de tela, cancelar e retomar).
> - Primeiro uso numa [máquina limpa](docs/testes/2026-10-14-sandbox-maquina-limpa.md) (Windows Sandbox, sem nada instalado) e numa [máquina corporativa sem administrador](docs/testes/2026-10-15-maquina-corporativa.md) (fala a 4,6x a 6,4x num i7 de 13ª geração).
> - [Teste cego com três IAs](docs/testes/2026-10-14-ia-cega.md) sem nenhum contexto: entenderam os arquivos e nenhuma inventou conteúdo.
>
> O `.exe` ainda **não é assinado**, então o Chrome e o Windows SmartScreen podem avisar. Veja as [limitações conhecidas](#limitações-conhecidas) e o [Roadmap](docs/ROADMAP.md).

---

## Por que existe

Vídeos de 500 MB a 1 GB não cabem no upload de nenhuma IA, e "conversores de MP4 para texto" online cobram, limitam o tamanho ou exigem enviar o conteúdo para terceiros. Este projeto resolve isso localmente:

| Problema | Solução |
|---|---|
| Vídeo grande demais para upload | Extrai só o áudio (1 h de vídeo vira ~20 MB) |
| Transcrição paga | [Whisper](https://github.com/openai/whisper) open source via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), rodando na CPU |
| Conteúdo que aparece só na tela | Capturas de tela + OCR com [Tesseract](https://github.com/tesseract-ocr/tesseract) |
| Dezenas de vídeos, horas de processamento | Lotes controlados, estimativa de tempo, retomada automática |
| Conteúdo sigiloso ou protegido | 100% local; a internet só é usada para baixar o modelo na primeira vez |

## O que ele faz

- 🎙️ **Transcrição literal** com timestamps a cada ~1 min, em português (ou outro idioma)
- 🖼️ **Texto da tela (opcional):** detecta trocas de slide/tela e lê o texto via OCR, inserindo-o no ponto certo do `.md`
- 📁 **Subpastas espelhadas:** `videos/Módulo 01/aula.mp4` → `transcricoes_md/Módulo 01/aula.md`
- 📚 **Base consolidada por módulo**, em arquivos de até 400 mil palavras (configurável; cabe nas fontes do NotebookLM, de 500 mil)
- 📦 **Pacote para IA:** um clique gera, para cada vídeo, uma pasta e um `.zip` com o `.md` e só as capturas que ele cita, para anexar numa conversa
- 🧭 **Cabeçalho "Como ler este arquivo"** em todo `.md`, para qualquer IA interpretar certo o que é fala, o que é texto de tela e o que não existe (descrição de imagens)
- 🧾 **`registro.csv`** (abre no Excel/Power BI): detecta vídeo novo, **substituído**, **excluído** e com **erro**
- ⏱️ **Estimativa de tempo** que aprende a velocidade real do seu PC
- 🖥️ **Verificação de hardware:** diz o que ajuda, o que atrapalha e qual qualidade usar
- 🔤 **Vocabulário de dicas** para nomes que o Whisper erra (ex.: *Power BI, DAX, ChatGPT*)
- ✏️ **Correções automáticas** por projeto (`correcoes.json`): "Chatepte" → "ChatGPT", contadas no cabeçalho do `.md`
- 🧰 **Preparação guiada** na primeira abertura: verifica o PC, baixa o modelo com barra de progresso e ajuda a instalar o Tesseract
- 🛑 **Parar com segurança** após o vídeo atual; nada se perde; não deixa o PC suspender no meio

## Como funciona

```mermaid
flowchart LR
    V[🎬 Vídeos<br/>com subpastas] --> S[Varredura +<br/>registro.csv]
    S --> A[FFmpeg:<br/>extrai áudio]
    A --> W[faster-whisper:<br/>transcreve]
    S -. opcional .-> C[FFmpeg:<br/>capturas de tela]
    C --> O[Tesseract:<br/>OCR]
    W --> M[📝 .md por vídeo]
    O --> M
    M --> B[📚 Base consolidada<br/>por subpasta]
    B --> IA[Qualquer IA:<br/>Claude, ChatGPT, Gemini, NotebookLM]
```

Detalhes em [Arquitetura](docs/ARQUITETURA.md) e nas [Decisões técnicas](docs/DECISOES.md).

## Instalação

### Opção A: executável para Windows (recomendado para usuários comuns)

1. Baixe o `.zip` da versão mais recente em **Releases**
2. Descompacte em uma pasta **fora do OneDrive** (ex.: `C:\TranscritorLocal`). Dentro há um único programa, o `COMO_ABRIR.txt` e a pasta `licencas`
3. Abra `TranscritorLocal.exe`. Na primeira vez, a página **Preparação do PC** confere o PC e, com um clique em cada botão, baixa uma única vez:
   - o **FFmpeg**, programa que abre os vídeos (~115 MB). É a versão oficial fixa, baixada direto do distribuidor e conferida por SHA-256 antes de usar ([por que não vem no zip](docs/DECISOES.md#adr-021-o-zip-não-redistribui-binário-gpl-o-ffmpeg-é-baixado-na-primeira-abertura));
   - o **modelo de transcrição**: ~0,5 GB na qualidade **Rápido**, ~1,6 GB na **Equilibrado** e na **Preciso**
4. Para ler o texto da tela, instale o Tesseract pelo botão da mesma página

O Python já vem embutido. Como o app ainda não tem assinatura digital, o Chrome pode chamar o arquivo de perigoso (em `chrome://downloads`, escolha **Manter**) e o Windows pode exibir *"O Windows protegeu o computador"* (clique em **Mais informações → Executar assim mesmo**). Para conferir o arquivo, compare `Get-FileHash .\TranscritorLocal.exe` com o SHA-256 publicado na página do Release.

### Opção B: pelo código-fonte (Python 3.10+)

```powershell
winget install --id Gyan.FFmpeg -e          # FFmpeg (obrigatório)
winget install --id UB-Mannheim.TesseractOCR -e   # Tesseract (opcional, para texto da tela)
git clone https://github.com/nicorosseto/transcritor-local
cd transcritor-local
python -m pip install -r requirements.txt
python -m transcritor          # abre a janela
python transcrever.py          # ou: modo terminal, usando as pastas ./videos e ./saida
```

Passo a passo para iniciantes, incluindo solução de erros comuns: **[Guia do usuário](docs/GUIA_DO_USUARIO.md)**.

## O que sai

```
<pasta de saída>/
├── transcricoes_md/      um .md por vídeo, mesma estrutura de pastas
├── base_consolidada/     base_<subpasta>.md, para ferramentas que indexam muitas fontes
├── pacote_para_ia/       (botão "Pacote para IA") uma pasta e um .zip por vídeo: .md + imagens citadas
├── capturas/             imagens das trocas de tela (se o OCR estiver ligado)
├── audio_mp3/            áudio leve de cada vídeo (reaproveitável)
├── _orfaos/              transcrições de vídeos que foram removidos da pasta
└── registro.csv          histórico, status e velocidades (Excel/Power BI)
```

Exemplo de trecho gerado (conteúdo fictício):

```markdown
**[00:12:05]** Agora a gente vai criar a medida de total de vendas usando SUM...

> 🖼️ **Na tela [00:12:08]** · [captura](../../capturas/Modulo%2001/aula03/cap_001208.jpg)
> Total Vendas = SUM(Vendas[Valor])
```

## Usando com uma IA

| Situação | O que anexar |
|---|---|
| Quer que a IA entenda a fala | O `.md` do vídeo (pasta `transcricoes_md`) |
| Quer que a IA veja também slides, diagramas e telas | A pasta do **Pacote para IA** inteira: o `.md` e a pasta `imagens`, ou o `.zip` se a ferramenta abrir `.zip` |
| Muitos vídeos de um mesmo módulo | O arquivo da `base_consolidada` |

Todo `.md` começa com um bloco "Como ler este arquivo", que explica a fala, o texto de tela e as capturas, e pede à IA que avise quando não conseguir ler algo em vez de inventar. No [teste cego](docs/testes/2026-10-14-ia-cega.md), três IAs sem contexto entenderam as aulas, abriram as imagens por conta própria e não inventaram nada.

## Desempenho de referência

| PC | Qualidade | Vídeo | Velocidade medida |
|---|---|---|---|
| Xeon E5-2620 v3 (6C/12T, 2014), 16 GB, só CPU | Preciso (`large-v3-turbo`, beam 5) | 36:43 | **1,48x** (24:49) |
| O mesmo PC | Equilibrado (`large-v3-turbo`, beam 1) | 36:43 | **~1,7x** na fala; o texto de tela soma ~0,6 s por troca de tela |
| Windows Sandbox no mesmo PC, 4 GB de RAM | Rápido (`small`) | 2:48 | **4,3x** |

"1,7x" = 1,7 minuto de vídeo transcrito por minuto real. Placas **NVIDIA** aceleram 5x ou mais; placas AMD/Intel não são usadas pelo motor atual (ver [ADR-001](docs/DECISOES.md)).

## Limitações conhecidas

- Transcrição é **automática**: revise nomes próprios e termos técnicos. A qualidade **Rápido** erra mais; use a **Equilibrado** sempre que o PC tiver memória
- Não identifica **quem** fala (sem diarização)
- O OCR lê **texto**, mas não entende **ações** ("clicou em tal botão") nem gráficos. Texto sobre **fundo colorido** (caixas de diagrama) pode sair incompleto: por isso, anexe à IA o pacote com as imagens. A descrição por IA visual local está prevista para a [v0.2](docs/ROADMAP.md)
- O Tesseract (texto da tela) é instalado à parte; embuti-lo no app está no roadmap
- O `.exe` não tem assinatura digital e as dependências ainda não são fixadas por hash
- A lista completa, com status de cada item, está na [Auditoria](docs/AUDITORIA.md) e no [status das auditorias](docs/auditorias/STATUS.md)

## Privacidade e direitos autorais

- O processamento é local. Os únicos acessos à internet são downloads feitos uma vez: o FFmpeg (GitHub do distribuidor, ~115 MB, só no Windows), o modelo Whisper (Hugging Face) e o pacote de português do Tesseract (GitHub, ~2 MB).
- **Não publique transcrições de cursos pagos** nem de material de trabalho sem autorização. O `.gitignore` deste repositório bloqueia vídeos, áudios e saídas justamente para evitar isso.

## Documentação

| Documento | Conteúdo |
|---|---|
| [Guia do usuário](docs/GUIA_DO_USUARIO.md) | Instalação e uso passo a passo, erros comuns |
| [Arquitetura](docs/ARQUITETURA.md) | Módulos, fluxo de dados, eventos, registro |
| [Decisões técnicas (ADRs)](docs/DECISOES.md) | Por que cada escolha foi feita |
| [Histórico do projeto](docs/HISTORICO.md) | Como o projeto evoluiu e o que aprendemos |
| [Auditoria](docs/AUDITORIA.md) | Lacunas encontradas, corrigidas e pendentes |
| [Auditoria independente — Codex (08/10/2026)](docs/auditorias/2026-10-08/README.md) | Achados técnicos, evidências, revisão de interface e proposta de layout |
| [Status das auditorias](docs/auditorias/STATUS.md) | O que foi corrigido, em qual teste, e o que falta |
| [Registros dos testes](docs/testes/) | Rodadas reais no Windows, máquina limpa e teste cego com IAs |
| [Retomada](docs/RETOMADA.md) | Onde o projeto parou e qual é o próximo passo |
| [Roadmap](docs/ROADMAP.md) | Próximas versões |
| [Licenças de terceiros](docs/LICENCAS_TERCEIROS.md) | FFmpeg, Whisper, Tesseract e bibliotecas |

## Licença

[MIT](LICENSE). Componentes de terceiros têm licenças próprias, listadas em [LICENCAS_TERCEIROS.md](docs/LICENCAS_TERCEIROS.md).
