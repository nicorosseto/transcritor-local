# Testes de fumaça da janela

Rodam a janela de verdade (CustomTkinter) com o modelo de transcrição **simulado**. Servem para conferir
o layout e os estados da interface sem baixar o modelo. Precisam de Linux com `xvfb-run` e Python com Tk
(no ambiente de desenvolvimento, `python3.12`). Rodar na raiz do repositório:

```
xvfb-run -a python3.12 ferramentas/fumaca/janela_basica.py      # pastas, troca de origem, fila, estado fatal
xvfb-run -a python3.12 ferramentas/fumaca/rodada_completa.py    # rodada com mp4 + mkv de mesmo nome
xvfb-run -a python3.12 ferramentas/fumaca/rodada_tela_falha.py  # OCR falhando -> rodada "parcial"
xvfb-run -a python3.12 ferramentas/fumaca/pacote_para_ia.py     # botão "Pacote para IA" e resumo sem pendentes
```

Capturas de tela de todos os estados, em 1366x768 (precisa do ImageMagick, comando `import`):

```
mkdir -p /tmp/telas && xvfb-run -a -s "-screen 0 1366x768x24" python3.12 ferramentas/capturar_telas.py /tmp/telas
```

`cancelar_rodada.py`: cancela no meio da rodada (modelo simulado e lento) e confere que a tabela volta a "Pendente" (N10).

`escala_do_windows.py`: simula escala 1.0/1.25/1.5 e confere que a janela e o botão Transcrever cabem na tela (N16). Passe a escala como argumento e o tamanho da tela no `xvfb-run -s`.
