"""Teste de fumaça: botão "Pacote para IA" e resumo sem pendentes. Modelo e OCR simulados."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tests")
from conftest import criar_video, ModeloFalso
from transcritor import ocr, pipeline
from transcritor.gui import app as A
m = ModeloFalso()
pipeline.carregar_modelo = lambda *a, **k: (m, "cpu")
pipeline.modelo_baixado = lambda n: True
A.modelo_baixado = lambda n: True
A.Dialogo.perguntar = lambda self: "ok"
A.App._verificacao_inicial = lambda self: None
ocr.verificar = lambda: ocr.EstadoOCR(True, "x", True, None, "", idiomas="eng")
textos = iter(["Faturamento total do periodo consolidado", "", "Margem media mensal por regiao do pais"])
ocr.ler_imagem = lambda estado, img: next(textos, "")
abertas = []
A.App._abrir_saida = lambda self, sub="": abertas.append(sub)
tmp = Path(tempfile.mkdtemp())
criar_video(tmp/"v/Módulo 01/aula 1.mp4", [("Slide um", 5), ("Slide dois", 5), ("Slide tres", 5)],
            cores=[(255, 255, 255), (200, 230, 255), (255, 240, 200)])
app = A.App()
def bombear(seg, ate=None):
    fim = time.time()+seg
    while time.time() < fim and not (ate and ate()):
        app.update(); time.sleep(0.03)
app._definir(app.ent_videos, str(tmp/"v")); app._definir(app.ent_saida, str(tmp/"s"))
app._ler_pasta(); bombear(5, lambda: app.projeto)
app.chk_ocr.select(); app._escolher_qtd("todos")
app._iniciar(); bombear(60, lambda: not app.rodando)
print(app.lbl_status.cget("text"))
app._ler_pasta(); bombear(10, lambda: "concluído" in app.lbl_resumo.cget("text"))
resumo = app.lbl_resumo.cget("text")
print("resumo:", resumo)
assert "nenhum pendente" in resumo and "min de vídeo" not in resumo
app._gerar_pacote(); bombear(1)
pacotes = sorted(p.name for p in (tmp/"s/pacote_para_ia").iterdir())
print("pacote:", pacotes, "| aberta:", abertas)
assert pacotes == ["Módulo 01 - aula 1", "Módulo 01 - aula 1.zip"] and abertas == ["pacote_para_ia"]
assert "palavras de fala" in app.lbl_res_resumo.cget("text")
app._fechar(); bombear(0.5)
print("PACOTE GUI OK")
