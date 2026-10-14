# Teste em máquina limpa: Windows Sandbox (14/10/2026)

**Objetivo:** ver o app como alguém que baixa do GitHub e nunca teve Python, FFmpeg, Tesseract ou modelo no PC. Último teste antes de deixar o repositório público.

**Ambiente:** Windows Sandbox (Área Restrita do Windows) no Windows 10 Pro 22H2 do PC de referência. O Sandbox recebe só 4 GB de RAM, não tem `winget` nem antivírus e começa vazio a cada abertura. Versão testada: v0.1.12 (build do commit `d044758`). Vídeos de teste: dois vídeos curtos, sem dados de trabalho (2:48 e 0:42).

## Roteiro e resultado

| # | Passo | Resultado |
|---|---|---|
| 1 | Extrair o zip | ✅ `licencas/FFmpeg-CODIGO-FONTE.txt` presente, com versão, link do código-fonte e licença (P8) |
| 2 | Abrir o `.exe` sem Python | ✅ Abre; FFmpeg "já vem dentro do app" |
| 3 | SmartScreen | Não apareceu: arquivo copiado com Ctrl+C/Ctrl+V perde a marca de "veio da internet". O aviso já tinha sido visto no download pelo Chrome |
| 4 | Preparação do PC | ✅ Detectou 4 GB de RAM e recomendou **Rápido**. ❌ Ao trocar para Rápido, o cartão mostrou "Rápido: large-v3-turbo (~1,6 GB)" e baixou o modelo errado; depois pediu o small (N18) |
| 5 | Tesseract sem `winget` | ✅ Abriu a página oficial no navegador; instalação manual ok; "Verificar de novo" reconheceu |
| 6 | Lista de vídeos em tela pequena | ❌ Botão "Pendentes" espremido e colunas Duração/Status fora da vista (N17) |
| 7 | Escolher origem e depois saída | ❌ A lista lida sumia ao escolher a saída; o app criou uma pasta `videos_transcricoes` não pedida (N19) |
| 8 | Transcrever 2 vídeos, Rápido + OCR | ✅ Fala a 4,2x e OCR com 3 trechos; `.md` correto. ❌ A rodada parou no fim do 1º vídeo: `FileNotFoundError ... registro.tmp` (N20) |
| 9 | Repetir com o 2º vídeo e "Ler pasta" | ❌ Mesmo erro, sempre no `registro.tmp` |

## N20: diagnóstico

| Horário | Gravação do `registro.tmp` em `saida-sandbox` | Resultado |
|---|---|---|
| 20:01 | 1ª criação nessa pasta (leitura) | ✅ |
| 20:02 | 2ª criação, fim do 1º vídeo | ❌ |
| 20:08 | 3ª, fim do vídeo da 2ª rodada | ❌ |
| 20:15 | 4ª, "Ler pasta" | ❌ |

Os `.md` gravaram no mesmo segundo porque cada um usou um temporário com nome nunca usado. O menu de Segurança do Windows do Sandbox não tem "Proteção contra vírus e ameaças", o que descarta antivírus.

**Confirmação independente do app (PowerShell no Sandbox):**

```
New-Item "$env:USERPROFILE\Desktop\saida-sandbox\registro.tmp"   → Could not find file ... FileNotFoundException
New-Item "$env:USERPROFILE\Desktop\saida-sandbox\teste-novo.tmp" → criado
```

Conclusão: no sistema de arquivos do Sandbox, um nome que acabou de ser renomeado não pode ser criado de novo naquela pasta. O defeito do app era duplo: reusar sempre o mesmo nome de temporário e deixar uma falha de gravação do registro derrubar a rodada inteira.

## Correções (v0.1.13)

| ID | Correção | Cobertura |
|---|---|---|
| N17 | Cabeçalho da lista em grid (encolhe o texto, não os botões); colunas mais estreitas e a do nome encolhe ao redimensionar | `ferramentas/fumaca/maquina_limpa.py` em tela 1024x768 |
| N18 | Trocar a qualidade descarta a verificação anterior e confere de novo; verificação atrasada de outra qualidade é ignorada; botão diz "Baixar small (~0,5 GB)" | `maquina_limpa.py` (inclui troca rápida Rápido → Preciso → Rápido) |
| N19 | Escolher a saída relê a pasta sozinho; se a saída mudar durante uma leitura, relê com as pastas atuais | `maquina_limpa.py` |
| N20 | `util.gravar_atomico`: temporário com nome único por gravação, novas tentativas em qualquer erro de disco; usado em registro, `.md`, `projeto.json`, config; áudio, idiomas do Tesseract e base consolidada também com nomes únicos. Falha ao salvar o registro vira aviso e nova tentativa no vídeo seguinte; se nunca salvar, a rodada termina "parcial" (não "erro fatal") | `tests/test_maquina_limpa.py` (8 testes; um deles imita o Sandbox e falha no código antigo) |

Também: o painel "Última rodada" dizia "Falhou · 0 com erro"; agora diz "parou por um erro".

**Fica em aberto:** a pasta sugerida (`<vídeos>_transcricoes`) ainda é criada quando se escolhe a origem antes da saída. Inofensiva, mas não pedida.

## Próximo passo

Baixar o build da v0.1.13 e repetir o roteiro num Sandbox novo (o Sandbox apaga tudo ao fechar): escolher Rápido antes de baixar o modelo, origem e saída, rodada com os dois vídeos e OCR, e um segundo "Ler pasta" no fim.
