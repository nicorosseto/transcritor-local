# Roadmap

## v0.1 (atual): transcrição + texto da tela
- [x] Motor modular com testes
- [x] App desktop e modo terminal
- [x] Subpastas, registro.csv, base por subpasta
- [x] OCR opcional com capturas
- [x] Verificação de hardware e estimativas que aprendem
- [x] Build automatizado do `.exe` no GitHub Actions
- [ ] Validação em Windows real (pendência P1)
- [ ] Medição do vocabulário e do beam 1 com o modelo real (P2)

## v0.2: IA visual local (segunda fase)
- Coluna "IA visual" na tabela: escolher **por vídeo**
- Aplicação sobre as capturas já salvas (sem refazer a transcrição)
- Ollama local + modelo de visão pequeno (candidatos: `qwen3-vl:2b` / `qwen3-vl:4b`), sem conta e sem nuvem
- Estimativa separada para a fase visual, aprendida no PC
- Detecção do Ollama e da RAM disponível no "Verificar PC"
- Calibração dos limiares de captura (P3) e progresso do download do modelo (P4)

## v0.3: acabamento e publicação
- Repositório público + Release assinada (P7)
- Testes de GUI no CI (P13)
- Modo "deixar o PC usável" (P11)
- Ícone e instalador (Inno Setup)

## Em pesquisa
- `whisper.cpp` com Vulkan para acelerar em **placas AMD** (ex.: RX 560 XT 8 GB)
- Diarização (quem fala)
- Resumo automático por vídeo como arquivo **separado** (o `.md` literal continua sendo a fonte da verdade)
