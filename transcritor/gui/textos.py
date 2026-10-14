"""Textos da interface, separados do código para facilitar revisão e tradução."""


def tempo_humano(seg: float) -> str:
    """Sem falsa precisão: minutos para tempos longos (diretriz da Microsoft)."""
    seg = max(0, int(seg))
    if seg < 60:
        return "menos de 1 min"
    h, m = divmod(round(seg / 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def resumo_da_leitura(concluidos: int, pendentes: int, segundos_pendentes: float) -> str:
    """Linha de resumo da página Vídeos (achado N5: sem pendentes não se fala em minutos)."""
    if not pendentes:
        return f"{concluidos} concluído(s) · nenhum pendente"
    return f"{concluidos} concluído(s) · {pendentes} pendente(s), {tempo_humano(segundos_pendentes)} de vídeo"


def rotulo_tela(ocr: str, trechos: int) -> str:
    """Coluna "Texto da tela" de Resultados: "lido" só quando algum texto foi aproveitado (achado N8)."""
    if ocr == "sim":
        return f"lido ({trechos})" if trechos else "nada encontrado"
    return {"nao": "—", "falhou": "⚠ não lido"}.get(ocr, ocr)


def rotulo_tesseract(disponivel: bool, tem_portugues: bool) -> str:
    """Achado N6: não dizer "pronto" sem avisar que o pacote de português ainda será baixado."""
    if not disponivel:
        return "precisa do Tesseract (não instalado)."
    if not tem_portugues:
        return "Tesseract pronto; o pacote de português (~2 MB) será baixado na 1ª rodada, com internet."
    return "Tesseract pronto."

COMO_USAR = """COMO USAR — em 5 passos

0) PRIMEIRA VEZ
   Se faltar algo, o app abre na página "Preparação do PC" (barra lateral).
   O principal é o modelo de transcrição (~1,6 GB), baixado UMA vez. Você NÃO
   precisa instalar Python nem FFmpeg: já vêm dentro do app. Enquanto houver
   pendência, o item "Preparação do PC" mostra um número e pisca.

1) ORIGEM (pasta dos vídeos)
   Na página "Vídeos", clique em "Escolher" e selecione a pasta. Subpastas
   ("Módulo 01"...) são respeitadas na saída. Pastas que começam com "_" são
   ignoradas. Se adicionar ou remover vídeos depois, clique em "Ler pasta".

2) SAÍDA
   É sugerida automaticamente (e reaproveita uma saída que já exista ao lado).
   Ela NÃO pode ficar dentro da pasta de vídeos. "Abrir" mostra a pasta.

3) ESCOLHA OS VÍDEOS
   Clique na caixinha da primeira coluna. Os pendentes já vêm marcados.
   Clique no nome para ver os detalhes do vídeo ao lado.

4) OPÇÕES DA RODADA
   • Qualidade: "Equilibrado" é o recomendado.
   • Ler texto da tela: lê slides, código e menus (precisa do Tesseract).
   • Vocabulário e correções: dicas para o Whisper OUVIR certo (ex.: ChatGPT,
     DAX) e trocas feitas DEPOIS ("Chatepte" -> "ChatGPT"). "Editar lista"
     abre o arquivo correcoes.json no Bloco de Notas.

5) TRANSCREVER
   Na barra de baixo, escolha quantos vídeos fazer agora (obrigatório). Cada
   cartão mostra o tempo estimado. Depois, clique em "Transcrever".
   A barra mostra a etapa (Áudio > Transcrição > Texto da tela > Salvar), o
   progresso e o término previsto. "Parar após este vídeo" não perde nada.
   Ao terminar, o app avisa com som e faz o ícone piscar na barra de tarefas.
   O registro de atividades fica na página "Resultados".

ONDE ESTÁ O RESULTADO
   transcricoes_md\\   -> um .md por vídeo (mesma estrutura de pastas)
   base_consolidada\\  -> um arquivo por subpasta, para ferramentas que indexam muitas fontes
   pacote_para_ia\\    -> (botão "Pacote para IA", em Resultados) pasta e .zip por vídeo: o .md
                          mais só as imagens que ele cita, para anexar numa conversa com qualquer IA
   registro.csv       -> histórico (abre no Excel/Power BI)
   correcoes.json     -> sua lista de correções
   capturas\\          -> imagens das telas (se a leitura de tela estiver ligada)

IMPORTANTE
   • Tudo roda no seu PC. A internet só é usada para baixar o modelo (1 vez).
   • Transcrição é automática: revise nomes próprios e termos técnicos.
   • Conteúdo de cursos pagos e dados de trabalho: não publique sem autorização.
"""

SOBRE_IA_VISUAL = ("A descrição de telas por IA visual (Ollama, local) chega na versão 0.2. "
                   "As capturas salvas agora poderão ser reaproveitadas sem refazer a transcrição.")
