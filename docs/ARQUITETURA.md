# Arquitetura

## Visão geral

O projeto separa o **motor** (lógica, sem interface) das **interfaces** (terminal e janela). As duas interfaces conversam só com `pipeline.Projeto` e recebem **eventos**. Com isso, a mesma lógica é testada uma vez e servida por qualquer interface (inclusive uma futura web local).

```mermaid
flowchart TB
    subgraph Interfaces
        CLI[cli.py<br/>terminal]
        GUI[gui/app.py<br/>CustomTkinter]
    end
    subgraph Motor
        P[pipeline.Projeto<br/>orquestrador]
        R[registro.py<br/>registro.csv]
        E[estimativa.py]
        H[hardware.py]
        M[midia.py<br/>FFmpeg]
        T[transcricao.py<br/>faster-whisper]
        O[ocr.py<br/>Tesseract]
        MD[markdown.py]
        C[consolidacao.py]
    end
    CLI --> P
    GUI --> P
    CLI --> H
    GUI --> H
    P --> R & E & M & T & O & MD & C
    E --> R
```

## Módulos

| Módulo | Responsabilidade | Dependências externas |
|---|---|---|
| `config.py` | `Config` (dataclass), predefinições de qualidade, persistência em `transcritor_config.json` | — |
| `util.py` | Tempo `hh:mm:ss`, localização de binários (embutidos ou PATH), subprocessos sem janela e sem stdin, trava de pasta, impedir suspensão | `psutil` (opcional) |
| `midia.py` | Duração (ffprobe), extração de áudio, decodificação para numpy, capturas de tela | FFmpeg, Pillow, numpy |
| `transcricao.py` | Carregar modelo (GPU→CPU), transcrever em parágrafos, cancelamento | faster-whisper / CTranslate2 |
| `ocr.py` | Detectar Tesseract, baixar português, ler imagem, limpar e deduplicar texto | Tesseract |
| `registro.py` | Identidade dos vídeos, status, métricas, sincronização com a pasta | — |
| `estimativa.py` | Tempo previsto: padrão conservador → mediana medida | — |
| `markdown.py` | Montagem do `.md` com blocos "Na tela" no ponto certo | — |
| `consolidacao.py` | Bases por subpasta com divisão por limite de palavras | — |
| `hardware.py` | Diagnóstico com nível (ok/aviso/erro/info) e explicação | `psutil`, PowerShell (Windows) |
| `pipeline.py` | Varredura, sincronização, execução do lote, eventos | todos acima |

## Fluxo de um vídeo

```mermaid
sequenceDiagram
    participant UI as Interface
    participant P as Projeto
    participant FF as FFmpeg
    participant W as Whisper
    participant TS as Tesseract
    UI->>P: executar(itens, ao_evento, parar, cancelar)
    P->>P: Trava(pasta_saida) + ManterAcordado()
    P->>W: carregar_modelo (1x por lote)
    loop cada vídeo
        P-->>UI: video_inicio
        P->>FF: extrair_audio → .parcial.mp3 → .mp3
        P->>FF: carregar_audio → numpy float32 16 kHz
        P->>W: transcribe(vad, hotwords, beam)
        W-->>P: segmentos (progresso → UI)
        opt OCR ligado
            P->>FF: quadros-chave + mpdecimate + showinfo
            P->>P: dHash 16x16 + intervalo mínimo
            P->>TS: ler cada captura
        end
        P->>P: markdown.montar → .tmp → .md
        P->>P: registro.salvar (atômico)
        P-->>UI: video_fim / video_erro
    end
    P->>P: consolidar bases
    P-->>UI: lote_fim
```

## Eventos

| Tipo | Dados | Uso |
|---|---|---|
| `lote_inicio` | `total`, `segundos_previstos`, `duracao_total` | Cabeçalho da rodada |
| `etapa` | `texto` | Log ("Extraindo áudio...", "Lendo texto da tela 3/40...") |
| `video_inicio` | `indice`, `total`, `rel`, `duracao` | Linha atual / tabela |
| `progresso` | `pos`, `total`, `rel` + (após 30 s) `velocidade`, `falta_video`, `falta_lote`, `termino` | Barras e previsão |
| `video_fim` | `rel`, `palavras`, `segundos`, `velocidade`, `telas` | Marca concluído |
| `video_erro` | `rel`, `erro` | Marca erro, o lote continua |
| `aviso` | `texto` | Problemas não fatais |
| `lote_fim` | `ok`, `erro`, `cancelado`, `parado` | Libera a interface |

A GUI recebe os eventos de uma thread de trabalho por `queue.Queue` e os consome a cada 150 ms na thread principal, porque o Tkinter não é thread-safe.

## Identidade e estados (registro.csv)

Um vídeo é identificado por **caminho relativo + tamanho + data de modificação**.

```mermaid
stateDiagram-v2
    [*] --> pendente: vídeo novo
    [*] --> ok: .md já existia (importado)
    pendente --> ok: transcrito
    pendente --> erro: falhou
    erro --> ok: nova tentativa
    ok --> substituido: tamanho/data mudou
    substituido --> ok: retranscrito
    ok --> orfao: vídeo removido (.md → _orfaos)
    pendente --> orfao: vídeo removido
    orfao --> pendente: vídeo voltou
```

- O CSV usa `;` e vírgula decimal, para abrir corretamente no Excel/Power BI em português.
- A gravação é atômica (`.tmp` → `replace`). Se o Excel travar o arquivo, o app tenta 5 vezes e depois grava uma cópia `registro_PENDENTE_feche_o_excel.csv`.
- Apenas vídeos com status `ok` entram na base consolidada.

## Robustez

| Situação | Proteção |
|---|---|
| Queda/interrupção no meio | Áudio, `.md` e CSV são escritos em temporário e renomeados no fim |
| Vídeo corrompido | Exceção por vídeo: vira `erro`, o lote segue |
| Duas janelas na mesma saída | `Trava` com PID em `.em_uso.lock` |
| PC suspende à noite | `SetThreadExecutionState` (Windows) durante o lote |
| `.exe` sem console (stdout `None`) | `garantir_saidas_padrao()` redireciona para `transcritor.log` |
| ffmpeg "comendo" o teclado no terminal | Todos os subprocessos com `stdin=DEVNULL` |
| GPU NVIDIA com bibliotecas quebradas | Volta para CPU automaticamente |

## Empacotamento

- **PyInstaller onedir** (`packaging/transcritor.spec`): dois executáveis compartilhando `_internal/`: `TranscritorLocal.exe` (janela) e `TranscritorLocal-terminal.exe`.
- O workflow `build-windows.yml` gera o `.zip` no GitHub Actions (Windows), embute `ffmpeg.exe`/`ffprobe.exe` em `bin/` com as licenças e roda um teste de fumaça.
- `util.localizar_binario` procura primeiro em `<app>/bin`, depois no PATH.
