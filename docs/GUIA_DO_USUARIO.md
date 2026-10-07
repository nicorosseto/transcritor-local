# Guia do usuário

Para quem nunca programou. Leva ~15 minutos para preparar o PC na primeira vez.

## 1. Escolha o caminho

| Caminho | Para quem | O que instalar |
|---|---|---|
| **A. Executável (.exe)** | Quem só quer usar | Nada além do app (o FFmpeg vem junto) |
| **B. Código-fonte (Python)** | Quem quer mexer no código | Python + FFmpeg + bibliotecas |

O Tesseract é **opcional** nos dois caminhos: só é necessário para ler o texto que aparece na tela.

---

## 2. Caminho A: executável

1. Em **Releases**, baixe `TranscritorLocal-vX.Y.Z-windows.zip`.
2. Descompacte em `C:\TranscritorLocal` (evite o OneDrive e a Área de Trabalho sincronizada).
3. Abra **`TranscritorLocal.exe`**.
4. Se aparecer "O Windows protegeu o computador": **Mais informações → Executar assim mesmo**. Isso ocorre porque o app não tem assinatura digital paga, não porque é perigoso. O código é aberto e está neste repositório.

> Existe também o `TranscritorLocal-terminal.exe`, para quem prefere o modo texto.

## 3. Caminho B: código-fonte

### 3.1 Python

Verifique se já tem Python no PowerShell:

```powershell
python --version
```

| Resultado | O que fazer |
|---|---|
| `Python 3.10` a `3.13` | Pronto, siga para o 3.2 |
| `3.14` ou mais novo | Provavelmente funciona; se a instalação das bibliotecas falhar, instale a 3.13 |
| Abriu a Microsoft Store / "não reconhecido" | Instale a **3.13** em python.org → "Windows installer (64-bit)" e **marque "Add python.exe to PATH"** |

### 3.2 FFmpeg (obrigatório)

```powershell
winget install --id Gyan.FFmpeg -e
```

**Feche e reabra o PowerShell** e confirme com `ffmpeg -version`.

### 3.3 Bibliotecas

Se o seu Python estiver dentro do **OneDrive**, pause a sincronização antes (ícone da nuvem → engrenagem → Pausar sincronização → 2 horas).

```powershell
cd C:\caminho\para\transcritor-local
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3.4 Abrir

```powershell
python -m transcritor            # janela
python transcrever.py            # terminal (usa as pastas .\videos e .\saida)
```

## 4. Tesseract (opcional: texto da tela)

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

O pacote de **português** é baixado automaticamente pelo app na primeira vez (~2 MB, na sua pasta de usuário, sem precisar de administrador). Para conferir, use o botão **🖥 Verificar PC**.

## 5. Usando o app

| Passo | Onde | O que fazer |
|---|---|---|
| ① | Pasta dos vídeos | **Procurar** → escolha a pasta. Subpastas são respeitadas; pastas que começam com `_` são ignoradas |
| ② | Pasta de saída | É sugerida automaticamente (`<pasta>_transcricoes`). Não pode ficar **dentro** da pasta de vídeos |
| ③ | Tabela | Clique na caixinha para marcar/desmarcar. Os pendentes já vêm marcados |
| ④ | Opções | Qualidade, texto da tela, vocabulário e **quantos vídeos nesta rodada** (obrigatório) |
| ▶ | Iniciar | Confirme a estimativa. Acompanhe o progresso e a previsão de término |

**Dicas de qualidade:**
- **Equilibrado** é o padrão recomendado. **Preciso** é ~1,5–2x mais lento. **Rápido** usa um modelo menor e erra mais termos técnicos.
- No **vocabulário**, coloque nomes que aparecem nos vídeos e que o Whisper costuma errar: `Power BI, DAX, ChatGPT, Claude, Gemini, hook`.
- A primeira estimativa é **conservadora**. Depois do primeiro vídeo, o app passa a usar a velocidade real do seu PC.

**Para lotes grandes:** escolha um número de vídeos que caiba em uma noite. O app impede o PC de suspender enquanto trabalha, mas **não desligue** o computador.

## 6. Levando para a IA

| Destino | O que subir |
|---|---|
| **NotebookLM** | Os arquivos de `transcricoes_md\` (um por fonte), para as respostas citarem o vídeo exato. Ou os de `base_consolidada\`, se passar de 50 vídeos |
| **Claude (Projetos)** | Os `.md` como conhecimento do projeto |

⚠️ **Material de trabalho ou sigiloso:** revise e anonimize os `.md` (nomes, matrículas, números de processo) **antes** de subir para qualquer IA na nuvem.

## 7. Problemas comuns

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| `python não é reconhecido` | Python fora do PATH | Reinstale marcando "Add to PATH", ou use `py` no lugar de `python` |
| Abre a Microsoft Store ao digitar `python` | Atalho do Windows | Configurações → Aplicativos → Aliases de execução → desligue `python.exe` e `python3.exe` |
| `FFmpeg não encontrado` | Terminal aberto antes da instalação | Feche e reabra o PowerShell |
| `unexpected keyword argument 'metadata_errors'` | PyAV novo incompatível com faster-whisper | Já resolvido nesta versão (o áudio é lido pelo FFmpeg) |
| Parece travado em "Carregando modelo" | Download de até ~1,6 GB na primeira vez | Aguarde. Depois funciona offline |
| `Falha ao carregar o modelo ... 403/proxy` | Rede corporativa bloqueando o download | Baixe o modelo uma vez em outra rede |
| Aviso sobre "symlinks" do Hugging Face | Limitação do Windows | Inofensivo (já silenciado) |
| `registro_PENDENTE_feche_o_excel.csv` | O `registro.csv` estava aberto no Excel | Feche o Excel e rode de novo |
| "Pasta de saída já está sendo usada" | Duas janelas na mesma saída | Feche a outra janela |
| Muito lento | CPU antiga ou poucos núcleos | Use **Rápido**; rode à noite |
| Vídeo com status "erro" | Arquivo corrompido ou sem áudio | Abra no player para conferir; ele é tentado de novo na próxima rodada |
| Caminho muito longo | Limite de 260 caracteres do Windows | Use nomes de pasta mais curtos ou ative "caminhos longos" no Windows |

## 8. Acelerar com NVIDIA (opcional)

Só para placas **NVIDIA**. Placas AMD e Intel não são usadas pelo motor atual.

```powershell
python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
```

Se o **Verificar PC** mostrar "NVIDIA com CUDA detectada", está pronto. Se a GPU falhar, o app volta para a CPU sozinho.
