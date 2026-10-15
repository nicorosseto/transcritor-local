"""K1: "Ler pasta" (releitura) e, durante a leitura, "Transcrever N" -> rodada termina com "Pronto!",
mas registro.csv, tabela, base consolidada e Pacote não registram os vídeos concluídos.

Diálogo de confirmação REAL (wait_window); o "clique" em Começar vem 2,5 s depois de ele abrir.
Modelo de transcrição simulado (o mesmo de ferramentas/fumaca/rodada_completa.py); o resto é o código real.
Com --na-hora, Começar é clicado com a leitura ainda rodando (aí a trava do X4 recusa a rodada).

Rodar na raiz do repositório:
  xvfb-run -a -s "-screen 0 1366x768x24" python3.12 docs/auditorias/2026-10-14-claude/reproducoes/k01_ler_pasta_e_transcrever.py
"""
import csv, functools, sys, time, tempfile
print = functools.partial(print, flush=True)
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import pipeline, midia
from transcritor.gui import app as A

NA_HORA = "--na-hora" in sys.argv
m = ModeloFalso()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
A.App._verificacao_inicial = lambda self: None

tmp = Path(tempfile.mkdtemp())
criar_video(tmp / "v/a.mp4", [("a", 4)]); criar_video(tmp / "v/b.mp4", [("b", 4)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time() + seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)

app._definir(app.ent_videos, str(tmp / "v")); app._definir(app.ent_saida, str(tmp / "s"))
app._ler_pasta(); bombear(10, lambda: app.projeto)
print("1a leitura:", [(i.rel, i.status) for i in app.itens])

# o usuário adiciona um vídeo e clica "Ler pasta"; medir o vídeo novo leva ~1 s
criar_video(tmp / "v/c.mp4", [("c", 4)])
dur_real = midia.duracao
midia.duracao = lambda p: (time.sleep(1.0), dur_real(p))[1]
app._ler_pasta(); bombear(0.2)
print("durante a leitura: _lendo =", app._lendo, "| botão Transcrever:", app.btn_iniciar.cget("state"),
      "|", app.btn_iniciar.cget("text").replace("\n", " "))

projeto_antes = app.projeto
def clicar_comecar():
    for w in app.winfo_children():
        if isinstance(w, A.Dialogo):
            print("  diálogo:", w.title(), "| leitura ainda rodando?", app._lendo)
            w._escolher("ok")
app.after(100 if NA_HORA else 2500, clicar_comecar)
def fechar_avisos():  # outros diálogos (ex.: "Não foi possível começar") são lidos e fechados
    for w in app.winfo_children():
        if isinstance(w, A.Dialogo) and w.title() != "Confirmar rodada":
            print("  diálogo:", w.title(), "->", w.botoes[-1][0], flush=True)
            w._escolher(w.botoes[-1][1])
    app.after(300, fechar_avisos)
app.after(300, fechar_avisos)
app._iniciar()  # abre a confirmação real e espera o clique
print("projeto trocado durante a confirmação:", app.projeto is not projeto_antes)
bombear(60, lambda: not app.rodando)
bombear(3, lambda: not app._lendo)
print("status final:", app.lbl_status.cget("text"))
print(".md gravados:", sorted(p.name for p in (tmp / "s/transcricoes_md").glob("*.md")))
with open(tmp / "s/registro.csv", encoding="utf-8-sig") as f:
    print("registro.csv:", [(r["caminho"], r["status"]) for r in csv.DictReader(f, delimiter=";")])
print("tabela:", {iid: app.tabela.set(iid, "status") for iid in app.tabela.get_children()})
print("base consolidada tem a fala?", any("frase" in p.read_text(encoding="utf-8")
                                         for p in (tmp / "s/base_consolidada").glob("*.md")))
app.destroy()
