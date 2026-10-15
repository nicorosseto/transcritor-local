from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json, zipfile, subprocess
from transcritor import pacote, consolidacao, ocr, estimativa, midia
from transcritor.pipeline import Projeto, Item
from transcritor.config import Config
from transcritor.registro import Registro, Linha

out={}
with TemporaryDirectory() as tmp:
    root=Path(tmp); saida=root/'saida'; saida.mkdir()
    md=saida/'transcricoes_md'/'Módulo 01'/'aula.md'; md.parent.mkdir(parents=True)
    fora=root/'fora.txt'; fora.write_text('CONTEUDO SINTETICO FORA DA SAIDA')
    dentro=saida/'capturas'/'Módulo 01'/'área com espaço.png'; dentro.parent.mkdir(parents=True); dentro.write_bytes(b'IMAGEM SINTETICA')
    md.write_text('[captura](../../capturas/M%C3%B3dulo%2001/%C3%A1rea%20com%20espa%C3%A7o.png)\n[captura](../../../fora.txt)')
    pasta=pacote.montar(md,saida/'pacote_para_ia','aula')
    with zipfile.ZipFile(pasta.with_suffix('.zip')) as z:
        out['pacote_fora']={'arquivos':z.namelist(),'conteudo_externo_incluido':z.read('imagens/fora.txt').decode()=='CONTEUDO SINTETICO FORA DA SAIDA','link_interno_resolve':(pasta/'imagens'/'área com espaço.png').is_file() and 'imagens/área%20com%20espaço.png' in (pasta/'aula.md').read_text()}
    link=dentro.parent/'atalho.png'; link.symlink_to(fora)
    md.write_text('[captura](../../capturas/M%C3%B3dulo%2001/atalho.png)')
    pasta=pacote.montar(md,saida/'pacote_para_ia','symlink')
    out['pacote_symlink_fora']=(pasta/'imagens/atalho.png').read_text()=='CONTEUDO SINTETICO FORA DA SAIDA'
    md.write_text('PRIMEIRO VIDEO')
    primeiro=pacote.montar(md,saida/'pacote_para_ia','Mod/01/aula')
    md.write_text('SEGUNDO VIDEO')
    segundo=pacote.montar(md,saida/'pacote_para_ia','Mod - 01/aula')
    out['pacote_colisao_nomes']={'mesma_pasta':primeiro==segundo,'primeiro_conteudo_preservado':any('PRIMEIRO VIDEO' in p.read_text() for p in primeiro.glob('*.md'))}

    base=saida/'base_consolidada'; base.mkdir();(base/'base_velha.md').write_text('BASE ANTERIOR')
    fonte=saida/'origem.md'; fonte.write_text('NOVA BASE')
    try:
        with patch('transcritor.consolidacao.os.replace',side_effect=PermissionError('falha sintética ao publicar')):
            consolidacao.consolidar([('a.mp4',fonte)],base,400000)
    except PermissionError:pass
    out['consolidacao_falha_publicacao']={'base_anterior_existe':(base/'base_velha.md').exists(),'sobra_tmp':len(list(saida.glob('.base_consolidada*.tmp')))}

    class Resposta:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self):raise OSError('download interrompido sintético')
    dados=root/'dados'
    with patch('transcritor.ocr._pasta_tessdata_app',return_value=dados),patch('transcritor.ocr.urllib.request.urlopen',return_value=Resposta()):
        try:ocr.baixar_portugues()
        except OSError:pass
    out['download_ocr_interrompido']={'parciais_restantes':len(list(dados.glob('*.parcial')))}
    wav=root/'sintetico.wav'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.2',str(wav)],check=True)
    mp3=root/'som.mp3'
    with patch('pathlib.Path.replace',side_effect=PermissionError('falha sintética na publicação do MP3')):
        try:midia.extrair_audio(wav,mp3)
        except PermissionError:pass
    out['audio_falha_rename']={'parciais_restantes':len(list(root.glob('*.parcial.mp3')))}
    bloco='DAX\nSQL\nAPI\nCPU\nGPU\nETL\nGRAVAÇÃO'
    out['filtro_texto_tecnico']={'entrada':bloco,'saida':ocr.limpar(bloco),'rotulo_curto':'SQL API CPU GPU -> '+str(ocr.linha_legivel('SQL API CPU GPU'))}
    out['estimativas_limites']={'vazio':estimativa.estimar([],Registro(root/'r.csv'),'equilibrado','cpu',True).total,'vel_zero':estimativa.falta_da_rodada(30,0,600),'ocr_zero':estimativa.ocr_restante_do_video(0,0,0,600,30)}

    videos=root/'videos';videos.mkdir();v=videos/'a.mp4';v.write_bytes(b'VIDEO SINTETICO')
    proj=Projeto(Config(videos,root/'s_previsao',ocr=True))
    linha=Linha('a.mp4',saida='a',duracao_s=3600)
    proj.registro.linhas['a.mp4']=linha
    item=Item('a.mp4',v,linha)
    relogio=iter([0,0,1800]);estado=ocr.EstadoOCR(True,'tesseract',True,None,'',idiomas='eng')
    def fake_transcrever(*a,**kw):
        kw['ao_progredir'](1800,3600)
        return [],3600
    eventos=[]
    with patch.object(proj,'_garantir_modelo'),patch.object(proj,'_preparar_ocr',return_value=estado),patch.object(proj,'_ler_telas',return_value=([],None,0)),patch('transcritor.pipeline.midia.extrair_audio'),patch('transcritor.pipeline.midia.carregar_audio',return_value=None),patch('transcritor.pipeline.transcrever',side_effect=fake_transcrever),patch('transcritor.pipeline.time.perf_counter',side_effect=lambda:next(relogio,1800)):
        proj.executar([item],eventos.append)
    progresso=next(e.dados for e in eventos if e.tipo=='progresso')
    out['previsao_fala_mais_ocr']={'video_duracao':3600,'fala_pos':1800,'velocidade':progresso['velocidade'],'ocr_total_esperado':600,'previsao_emitida':progresso['falta_lote'],'previsao_fala_restante_mais_ocr_inteiro':2400}

print(json.dumps(out,ensure_ascii=False,indent=2))
