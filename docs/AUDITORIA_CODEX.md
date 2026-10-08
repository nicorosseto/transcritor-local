# Briefing de auditoria independente (para o Codex ou outro revisor)

> **Para quem cola isto no Codex:** abra o repositório no Codex e peça:
> *"Leia `docs/AUDITORIA_CODEX.md` e execute a auditoria descrita, sem alterar código."*
> Depois, copie o relatório gerado e cole na conversa com o Claude para análise e correção.

> **Resultado disponível:** a auditoria de 08/10/2026 está salva em [auditorias/2026-10-08/README.md](auditorias/2026-10-08/README.md), com relatório técnico, revisão de interface, wireframe e evidências. O Claude pode consultar esses arquivos diretamente no repositório; o briefing abaixo permanece como referência do escopo original.

---

## 1. Seu papel

Você é um **revisor independente**. O código foi escrito por outra IA (Claude), junto com o dono do projeto. O objetivo é encontrar o que **nós não vimos**.

**Regras:**
1. **Não altere arquivos.** Entregue só o relatório. Correções serão aplicadas depois, com revisão.
2. **Evidência obrigatória:** cada achado precisa citar `arquivo:linha` e explicar como reproduzir ou por que acontece.
3. **Sem achados genéricos** ("adicionar mais testes", "usar type hints"). Só o que muda o comportamento, a segurança, a privacidade, a manutenção ou a experiência do usuário final.
4. As **pendências já conhecidas** estão em `docs/AUDITORIA.md` (P1 a P16). Não as repita. Se discordar da severidade ou da solução proposta para alguma, diga por quê.
5. Se algo for **intencional** segundo `docs/DECISOES.md`, só aponte se a justificativa estiver errada.

## 2. Contexto em 30 segundos

- **O quê:** app desktop (Windows) + CLI que transcreve pastas de vídeos para Markdown, 100% local (FFmpeg + faster-whisper + Tesseract opcional), para alimentar NotebookLM/Claude.
- **Usuário-alvo:** pessoa **sem conhecimento técnico**, PC comum, frequentemente **sem GPU NVIDIA**. PC de referência: Xeon E5-2620 v3, 16 GB, AMD RX 560 XT, Windows 10/11, Python 3.13 dentro do OneDrive.
- **Volume típico:** 40 vídeos, 30–60 min cada, lotes que rodam à noite (8–20 h de processamento).
- **Dados sensíveis:** cursos pagos e material de trabalho. **Nada pode sair do PC** além do download do modelo e do pacote de idioma do OCR.
- **Leitura essencial:** `README.md` → `docs/ARQUITETURA.md` → `docs/DECISOES.md` → `docs/AUDITORIA.md`.

## 3. Como rodar

```bash
pip install -e ".[dev]"      # requer ffmpeg no PATH; tesseract é opcional
pytest -q                    # 14 testes; usam um modelo Whisper FALSO (tests/conftest.py)
python -m transcritor        # GUI
python -m transcritor --cli --videos ./videos --saida ./saida
pyinstaller packaging/transcritor.spec --noconfirm
```

Os testes **não** baixam o modelo real. Se você tiver rede, rode também com um vídeo curto real.

## 4. Áreas de foco (em ordem de prioridade)

### 4.1 Integridade dos dados (`registro.py`, `pipeline.py`, `consolidacao.py`)
- O `registro.csv` pode ficar **inconsistente** com os `.md` em algum fluxo (cancelamento, erro no meio da gravação, vídeo removido durante o lote, duas varreduras seguidas)?
- `sincronizar()`: há um caminho em que um `.md` válido vai para `_orfaos` indevidamente ou em que um vídeo nunca sai de `substituido`/`erro`?
- `modificado_em` usa segundos inteiros. Em cópias entre discos (FAT/exFAT com resolução de 2 s, fuso horário/horário de verão), a mesma mídia pode virar "substituída" sem ter mudado?
- O que acontece se o usuário **mudar a pasta de vídeos** e mantiver a mesma pasta de saída?
- O CSV com `;` e vírgula decimal: algum campo (ex.: `observacao` com `;` ou quebra de linha vinda de uma mensagem de erro) quebra a leitura?

### 4.2 Concorrência e interface (`gui/app.py`)
- Algum widget do Tkinter é tocado **fora da thread principal**? (Era para tudo passar pela `queue`.)
- Fechar a janela **durante** um lote: o que acontece com a trava `.em_uso.lock`, com o vídeo atual e com o registro?
- Cliques rápidos em "Ler pasta" ou "Iniciar" podem disparar duas threads?
- `_atualizar_estimativa` é chamado com muita frequência? Pode travar a interface com centenas de vídeos?

### 4.3 Processos externos (`midia.py`, `ocr.py`, `util.py`)
- Caminhos com **acentos, espaços, `'`, `&`, emojis**, ou muito longos no Windows: alguma chamada do FFmpeg/Tesseract quebra?
- `extrair_capturas`: o pareamento entre os tempos do `showinfo` e os arquivos `tmp_%06d.jpg` é **sempre** 1:1 e na mesma ordem? Existe vídeo (VFR, streams múltiplos, faixa de capa/thumbnail embutida em MP4) em que isso desalinha?
- `carregar_audio`: com vídeo de 4 h ou mais, a memória (stdout inteiro + cópia float32) chega a ser problema? Há pico duplicado?
- `ocr.baixar_portugues`: falta validação de integridade (tamanho/hash) do arquivo baixado? Redirecionamentos do GitHub funcionam com `urllib`?

### 4.4 Empacotamento e Windows (`packaging/`, `.github/workflows/`)
- O `.spec` inclui tudo que o faster-whisper, o CTranslate2 e o onnxruntime precisam **no Windows** (DLLs MSVC, `libiomp5md.dll`, etc.)? Algo que funciona no Linux e quebraria no Windows?
- Os dois executáveis compartilhando `_internal/` com dois `Analysis` separados: há risco de conflito ou duplicação de binários?
- O `build-windows.yml` baixa o FFmpeg de URL "latest" sem fixar versão ou hash: risco de reprodutibilidade e de cadeia de suprimentos?
- `garantir_saidas_padrao()` cobre `tqdm`/`huggingface_hub` no modo janela, ou eles capturam o stream antes?

### 4.5 Qualidade da transcrição (`transcricao.py`)
- Os parâmetros (`vad_parameters`, `condition_on_previous_text=False`, `hotwords`) são adequados para **português**, com termos técnicos em inglês? Há armadilhas conhecidas de `hotwords` (ex.: o texto das dicas aparecendo na transcrição)?
- `segundos_por_paragrafo=60` corta frases ao meio? Vale cortar no fim de frase mais próximo?

### 4.6 Privacidade e segurança
- Existe **qualquer** chamada de rede além do download do modelo (Hugging Face) e do `tessdata` (GitHub)? Telemetria de alguma dependência?
- O `.gitignore` cobre todos os artefatos sensíveis (incluindo `transcritor.log` em `%LOCALAPPDATA%` e capturas)?
- Algum dado do usuário vai para o log com mais detalhe do que deveria?

### 4.7 Experiência do usuário leigo
- Qual é o **primeiro ponto** em que um usuário sem conhecimento técnico travaria, do download do `.zip` até o primeiro `.md`?
- As mensagens de erro dizem **o que fazer**, ou só o que aconteceu?

## 5. Formato do relatório (obrigatório)

Responda **exatamente** neste formato, em português:

```markdown
# Relatório de auditoria — Codex — DD/MM/AAAA

## Resumo
- Achados: N (🔴 x, 🟠 y, 🟡 z)
- Os 3 mais importantes, em uma linha cada

## Achados
| ID | Sev. | Área (4.x) | Arquivo:linha | Problema | Evidência / como reproduzir | Recomendação | Confiança |
|----|------|------------|---------------|----------|-----------------------------|--------------|-----------|
| X1 | 🔴 | 4.1 | transcritor/registro.py:123 | ... | ... | ... | alta/média/baixa |

## Discordâncias com docs/AUDITORIA.md e docs/DECISOES.md
| Item | Nossa posição | Sua posição | Por quê |

## Perguntas em aberto
(o que você não conseguiu verificar e o que seria preciso para verificar)
```

**Severidade:** 🔴 perda/corrupção de dados, vazamento, crash no fluxo principal · 🟠 comportamento errado com contorno, risco no Windows, UX que bloqueia o leigo · 🟡 melhoria relevante.

**Confiança:** *alta* = reproduziu ou é inequívoco no código · *média* = raciocínio forte, sem reprodução · *baixa* = suspeita.
