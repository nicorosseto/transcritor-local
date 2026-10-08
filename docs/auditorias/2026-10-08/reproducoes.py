from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from transcritor.config import Config
from transcritor.pipeline import Projeto
from transcritor.registro import OK
from transcritor import midia, consolidacao, markdown, ocr
from transcritor.markdown import Tela
from transcritor.util import Trava

out={}
with TemporaryDirectory() as tmp:
    root=Path(tmp); videos=root/'videos'; videos.mkdir()
    v=videos/'aula.mp4'; v.write_bytes(b'primeiro')
    cfg=Config(videos,root/'saida')
    with patch('transcritor.pipeline.dispositivo_disponivel', return_value='cpu'), patch('transcritor.pipeline.midia.duracao',return_value=4):
        p=Projeto(cfg); p.escanear()
        md=p.caminho_md('aula.mp4'); md.parent.mkdir(parents=True); md.write_text('conteudo original')
        p.itens[0].linha.status=OK; p.registro.salvar()
        audio=p.caminho_audio('aula.mp4'); audio.parent.mkdir(parents=True); audio.write_bytes(b'audio antigo')
        v.write_bytes(b'video substituido muito maior'); p.escanear()
        with patch('transcritor.midia.rodar') as runner:
            midia.extrair_audio(v,audio)
            out['substituicao_audio']={'status':p.itens[0].status,'ffmpeg_chamado':runner.called,'cache':audio.read_text()}
        p.itens[0].linha.status=OK; p.registro.salvar(); md.unlink(); p.escanear()
        out['md_ausente']={'pendentes':len(p.pendentes()),'md_existe':md.exists()}
        out['colisao_extensoes']={'md':p.caminho_md('aula.mp4')==p.caminho_md('aula.mkv'),'audio':p.caminho_audio('aula.mp4')==p.caminho_audio('aula.mkv'),'capturas':p.pasta_capturas('aula.mp4')==p.pasta_capturas('aula.mkv')}
        other=root/'outros'; other.mkdir(); vv=other/'aula.mp4'; vv.write_bytes(v.read_bytes()); import os; os.utime(vv,(v.stat().st_atime,v.stat().st_mtime))
        md.write_text('transcricao da pasta anterior'); p2=Projeto(Config(other,cfg.pasta_saida)); p2.escanear()
        out['troca_raiz']={'status':p2.itens[0].status,'pendentes':len(p2.pendentes()),'texto':md.read_text()}
    base=root/'base'; base.mkdir(); old=base/'base_geral.md'; old.write_text('base anterior valida')
    bad=root/'invalido.md'; bad.write_bytes(b'\xff')
    try: consolidacao.consolidar([('aula.mp4',bad)],base,20)
    except UnicodeDecodeError: out['base_falha']={'base_anterior_existe':old.exists()}
    one=root/'one.md'; one.write_text(' '.join(['palavra']*30)); generated=consolidacao.consolidar([('aula.mp4',one)],base,10)
    out['limite_base']={'limite':10,'palavras_resultado':len(generated[0].read_text().split())}
    lock=root/'lock'; lock.mkdir()
    with Trava(lock):
        with Trava(lock): pass
        out['trava_reentrante']={'trava_existe_com_primeiro_contexto_ativo':(lock/'.em_uso.lock').exists()}
    image=cfg.pasta_capturas/'modulo/aula/cap.jpg'; image.parent.mkdir(parents=True); image.write_bytes(b'x')
    dest=cfg.pasta_md/'modulo/aula.md'; dest.parent.mkdir(parents=True,exist_ok=True)
    text,_=markdown.montar(titulo='aula',origem='modulo/aula.mp4',duracao=4,modelo='small',preset='rapido',paragrafos=[],telas=[Tela(0,'texto',image)],destino=dest)
    dest.write_text(text); files=consolidacao.consolidar([('modulo/aula.mp4',dest)],base,100)
    import re
    link=re.search(r'\[captura\]\((.*?)\)',files[0].read_text()).group(1)
    out['link_base']={'link':link,'resolve_no_original':(dest.parent/link).exists(),'resolve_na_base':(base/link).exists()}
    corrupted=root/'corrompido.mp4'; corrupted.write_bytes(b'nao e video')
    out['falha_capturas']={'resultado':midia.extrair_capturas(corrupted,root/'frames')}
    state=ocr.EstadoOCR(True,'/usr/bin/tesseract',True,None,'ok')
    out['falha_ocr']={'resultado':ocr.ler_imagem(state,root/'imagem-inexistente.png')}
print(json.dumps(out,ensure_ascii=False,indent=2))
