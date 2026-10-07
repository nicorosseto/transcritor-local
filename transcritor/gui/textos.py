"""Textos da interface, separados do código para facilitar revisão e tradução."""

COMO_USAR = """COMO USAR — em 5 passos

1) PASTA DOS VÍDEOS
   Clique em "Procurar" e escolha a pasta onde estão os vídeos.
   Pode ter subpastas (ex.: "Módulo 01", "Módulo 02"): elas serão
   respeitadas na saída. Pastas que começam com "_" são ignoradas.

2) PASTA DE SAÍDA
   Onde ficam as transcrições. Por padrão é criada ao lado da pasta
   de vídeos. Ela NÃO pode ficar dentro da pasta de vídeos.

3) ESCOLHA OS VÍDEOS
   Clique na caixinha da primeira coluna para marcar ou desmarcar.
   Vídeos já concluídos ficam desmarcados; marque de novo para refazer.

4) OPÇÕES
   • Qualidade: "Equilibrado" é o recomendado.
   • Ler texto da tela: lê slides, código e menus que aparecem no vídeo.
     Deixa o processo ~15–35% mais lento. Precisa do Tesseract.
   • Vocabulário: nomes que o Whisper costuma errar
     (ex.: Power BI, DAX, ChatGPT, Claude).
   • Processar nesta rodada: quantos dos vídeos marcados fazer agora.
     É obrigatório escolher: assim você controla quando o PC fica livre.

5) INICIAR
   Acompanhe a previsão de término. "Parar após o vídeo atual" para sem
   perder nada. "Cancelar agora" interrompe e o vídeo em andamento é
   refeito na próxima vez.

ONDE ESTÁ O RESULTADO
   transcricoes_md\\   → um .md por vídeo (mesma estrutura de pastas)
   base_consolidada\\  → um arquivo por subpasta, pronto para o NotebookLM/Claude
   registro.csv       → histórico (abre no Excel/Power BI)
   capturas\\          → imagens das telas (se a leitura de tela estiver ligada)

IMPORTANTE
   • Tudo roda no seu PC. Nenhum vídeo ou áudio é enviado para a internet.
     (A internet só é usada para baixar o modelo na primeira vez.)
   • Transcrição é automática: revise nomes próprios e termos técnicos.
   • Conteúdo de cursos pagos e dados de trabalho: não publique as
     transcrições sem autorização.
"""

SOBRE_IA_VISUAL = ("A descrição de telas por IA visual (Ollama, local) chega na versão 0.2. "
                   "As capturas salvas agora poderão ser reaproveitadas sem refazer a transcrição.")
