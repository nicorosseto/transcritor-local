# Pedido de rechecagem: bloqueios das auditorias de 14/10/2026

**Para:** os mesmos auditores das rodadas de 14/10 ([Codex](2026-10-14/README.md) e [Claude](2026-10-14-claude/README.md)).
**Objetivo:** confirmar se os bloqueios foram resolvidos na v0.1.14 e se a correção não abriu um problema novo. **Não** é uma auditoria completa de novo.

**Escopo:** `git log --reverse 84c6ab1..HEAD` (tudo depois do commit auditado em 14/10). Inclui também a correção N22 (Tesseract instalado sem administrador, `transcritor/util.py` e `transcritor/ocr.py`) e o registro do teste do responsável numa máquina corporativa ([docs/testes/2026-10-15-maquina-corporativa.md](../testes/2026-10-15-maquina-corporativa.md)), que já conferiu no Windows real: FFmpeg baixado pelo app, transcrição sem o PyAV, OCR, K1, C1/K3 e N22.

**Também, antes de o repositório ficar público:** confira se algum arquivo ou commit tem dado pessoal, nome de curso, nome real de vídeo de aula ou caminho da máquina do autor.

## O que conferir

| Achado | Onde está a correção | Como conferir |
|---|---|---|
| K1 | `transcritor/gui/app.py`: `_atualizar_estimativa`, `_escanear`, `_iniciar` | `xvfb-run -a -s "-screen 0 1366x768x24" python ferramentas/fumaca/auditoria_k1.py` e o script `2026-10-14-claude/reproducoes/k01_ler_pasta_e_transcrever.py` (agora `_iniciar` não abre diálogo durante a leitura) |
| B1 / K5 | `transcritor/pacote.py`: `_captura_permitida`, `_CAPTURA` | `pytest tests/test_auditoria_2026_10_14.py -k b1`; repetir os casos de `2026-10-14/reproducoes.py` e `k05_k10_k17_pacote.py` |
| B2 / K2 | `transcritor/preparacao.py` (`FFMPEG`, `baixar_ffmpeg`), `packaging/entrada_janela.py`, `packaging/transcritor.spec`, `.github/workflows/build-windows.yml`, [ADR-021](../DECISOES.md) | O artefato do build não tem `bin/`, nem `av.libs`, nem libx264/libx265; o autoteste do build confere isso. Avaliar se a abordagem (usuário baixa do distribuidor, versão fixa por SHA-256) resolve a questão da GPL para o `.zip` (leitura técnica) |
| B3 / K7 | `.github/workflows/build-windows.yml`, passos "Compactar" e "Criar o Release" | `draft: true`, `prerelease: true`, `body_path`, nome do zip nas notas e SHA-256 do `.exe` e do `.zip` |
| C1 / K3 | `transcritor/gui/app.py`: `_rodar_verificacao`, `_aplicar_situacao`, `_opcoes_mudaram`; `gui/verificacao.py`: `_reverificar` | `ferramentas/fumaca/auditoria_c1.py` e `2026-10-14-claude/reproducoes/k03_qualidade_durante_verificacao.py` |

Os demais achados corrigidos e os que ficaram para a v0.2 estão em [STATUS.md](STATUS.md).

## Comandos

```
python -m pip install -r requirements.txt pytest pyflakes
python -m pytest -q                       # 113 testes
python -m pyflakes transcritor tests
```

## Resposta

Uma linha por bloqueio: resolvido / resolvido com ressalva / não resolvido, com a evidência. Achado novo só se for bloqueio. Gravar em `docs/auditorias/2026-10-15-rechecagem-<auditor>/README.md`.
