import sys,time,threading,json
from types import SimpleNamespace
sys.path.insert(0,'.')
from transcritor.gui import app as A, verificacao as V
from transcritor.config import PRESETS
A.App._verificacao_inicial=lambda self:None
def situacao(preset):
    return V.Situacao(modelo=PRESETS[preset]['modelo'],modelo_baixado=False,obrigatorios=['Modelo'],diagnostico=SimpleNamespace(itens=[],preset_recomendado='rapido',dispositivo='cpu'))
liberar=threading.Event(); iniciou=threading.Event()
def lenta(preset,saida):
    iniciou.set();liberar.wait(10);return situacao(preset)
V.verificar=lenta
A.verificar=lambda preset,saida:situacao(preset)
app=A.App()
app.seg_preset.set(PRESETS['rapido']['rotulo']);app._aplicar_situacao(situacao('rapido'),False);app._mostrar_pagina('preparacao')
def bombear(seg):
    fim=time.monotonic()+seg
    while time.monotonic()<fim:app.update();time.sleep(.02)
app.painel_verif._reverificar();assert iniciou.wait(2)
app.seg_preset.set(PRESETS['preciso']['rotulo']);app._opcoes_mudaram();bombear(.6)
assert app.situacao.modelo=='large-v3-turbo'
liberar.set();bombear(.6)
textos=[]
def coletar(w):
    for f in w.winfo_children():
        try:textos.append(str(f.cget('text')))
        except Exception:pass
        coletar(f)
coletar(app.painel_verif)
cartoes=[t for t in textos if t.startswith('Modelo de transcrição') or t.startswith('Baixar ')]
out={'qualidade_atual':app.seg_preset.get(),'modelo_na_situacao':app.situacao.modelo,'cartoes_exibidos':cartoes}
assert any('Preciso: small' in t for t in cartoes),out
print(json.dumps(out,ensure_ascii=False,indent=2))
app._fechar()
