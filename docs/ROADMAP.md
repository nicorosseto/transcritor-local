# Roadmap

## v0.1 (atual): transcrição + texto da tela
- [x] Motor modular com testes
- [x] App desktop e modo terminal
- [x] Subpastas, registro.csv, base por subpasta
- [x] OCR opcional com capturas
- [x] Verificação de hardware e estimativas que aprendem
- [x] Build automatizado do `.exe` no GitHub Actions
- [~] Validação em Windows real (pendência P1): rodada completa feita em 14/10/2026 (1,68x, 27 min); achados N1 a N6 em [testes/2026-10-14-windows-p1.md](testes/2026-10-14-windows-p1.md); faltam Parar/Cancelar/fechar, escalas 125%/150% e a 2ª rodada
- [ ] Medição do vocabulário e do beam 1 com o modelo real (P2)

## v0.1.2: correções da auditoria (fase 1) ✅
- [x] X1, X2, X3, X5, X6, X7, X11, X13 e X16 ([status](auditorias/STATUS.md))
- [x] Lentidão (P17): threads = núcleos físicos, ~15% mais rápido no PC de referência

## v0.1.3: auditoria fase 2 ✅
- [x] X4, X10, X15, X8, X9, X12 e o restante do X13
- [x] CPU híbrida: só núcleos de desempenho (dedução; validar quando houver um PC desses)

## v0.1.4: novo layout aprovado ✅
- [x] Fundo preto, barra lateral `#0A1612`, verde só no que é clicável, logotipo "da onda à linha" e ícone do `.exe` (ADR-017)
- [ ] Conferir no Windows real (P1): escalas 125% e 150%, fluxo completo por teclado

## v0.1.5: teste real e formato para IA ✅
- [x] N1 a N3, N5 a N7 e o cabeçalho "Como ler este arquivo" ([ADR-018](DECISOES.md))
- [x] Botão **Pacote para IA** (pasta + `.zip` com o `.md` e só as capturas citadas)
- [x] N8 (v0.1.6): o OCR da v0.1.5 não lia nada com a pasta de idiomas do app; corrigido
- [x] N9 (v0.1.7): limpeza de linhas e blocos ilegíveis do OCR
- [ ] Conferir no Windows real (4ª rodada): OCR com texto de tela legível; calibrar o limiar de confiança (P3)

## v0.1.8 (planejada): ajustes de interface do teste real
- [x] N10: tabela repintada ao fim de uma rodada cancelada ; N11: estimativa só aprende com vídeos de 3 min ou mais, ponderada pela duração
- [x] N13 (v0.1.9): cabeçalho "diga que não leu em vez de inventar" e aviso sobre `.zip`
- [x] N14 (v0.1.10): feedback imediato ao cancelar e botões travados
- [ ] Conferir no Windows real (5ª rodada, v0.1.10): botão único, confirmação centralizada e previsão depois do 1º vídeo longo
Pedidos pelo responsável em 14/10/2026, a fazer **depois** da 4ª rodada no Windows:
- [x] **Barra de ação sem os cartões de quantidade (1, 3, 5, Todos).** A seleção é a tabela: botão único **Transcrever N** (N = marcados), com o tempo estimado ao lado. Substitui a regra de escolha obrigatória do ADR-007, que ficou redundante com as caixas de seleção; a proteção contra rodada acidental passa a ser só a confirmação (que já mostra quantidade e tempo). Manter os atalhos Pendentes / Todos / Nenhum
- [x] **Janela de confirmação centralizada sobre o app**, maior, com mais contraste (borda verde) e foco no botão **Começar**. Pop-up nativo do Windows descartado por ora: abre claro sobre um app preto e não segue o tema
 (segunda fase)
- Coluna "IA visual" na tabela: escolher **por vídeo**
- Aplicação sobre as capturas já salvas (sem refazer a transcrição)
- Ollama local + modelo de visão pequeno (candidatos: `qwen3-vl:2b` / `qwen3-vl:4b`), sem conta e sem nuvem
- Estimativa separada para a fase visual, aprendida no PC
- Detecção do Ollama e da RAM disponível no "Verificar PC"
- Calibração dos limiares de captura (P3) (o progresso do download, P4, já entrou na v0.1.1)

## v0.3: acabamento e publicação
- Repositório público + Release assinada (P7)
- Testes de GUI no CI (P13)
- Modo "deixar o PC usável" (P11)
- Ícone e instalador (Inno Setup)

## Formatos de saída (pesquisa de 11/10/2026)
O núcleo que os concorrentes oferecem é TXT, SRT e VTT; o diferencial deste app é juntar fala e texto da tela.
- **Primeiro:** página HTML única com busca, tempo clicável e capturas dos slides (o diferencial)
- **Depois:** SRT/VTT (modo próprio de segmentos curtos: até ~7 s, 2 linhas de até 42 caracteres), TXT, JSONL e CSV por segmento (`;` e vírgula decimal)
- **Mais tarde:** capítulos do YouTube a partir das trocas de slide, notas Obsidian, DOCX/PDF
- **Fora do escopo:** legenda gravada no vídeo, EPUB, Parquet
- Na interface: seção "Formatos de saída" com caixas de seleção; Markdown e base consolidada marcados por padrão

## Em pesquisa
- Busca local em todo o acervo (SQLite FTS5) abrindo o vídeo no minuto exato
- `whisper.cpp` com Vulkan para acelerar em **placas AMD** (ex.: RX 560 XT 8 GB)
- Diarização (quem fala)
- Resumo automático por vídeo como arquivo **separado** (o `.md` literal continua sendo a fonte da verdade)
