"""Textos da interface, separados do código para facilitar revisão e tradução."""

COMO_USAR = """COMO USAR — em 5 passos

0) PRIMEIRA VEZ
   O app abre a tela "Verificar PC e preparar" se faltar algo. O principal é o
   modelo de transcrição (~1,6 GB), baixado UMA vez. Você NÃO precisa instalar
   Python nem FFmpeg: já vêm dentro do app. O botão "Verificar PC" (canto
   superior direito) fica laranja ou vermelho quando há algo pendente.

1) PASTA DOS VÍDEOS
   Clique em "Procurar" e escolha a pasta. Subpastas ("Módulo 01"...) são
   respeitadas na saída. Pastas que começam com "_" são ignoradas.

2) PASTA DE SAÍDA
   É sugerida automaticamente (e reaproveita uma saída que já exista ao lado).
   Ela NÃO pode ficar dentro da pasta de vídeos.

3) ESCOLHA OS VÍDEOS
   Clique na caixinha da primeira coluna. Os pendentes já vêm marcados.

4) OPÇÕES
   • Qualidade: "Equilibrado" é o recomendado.
   • Ler texto da tela: lê slides, código e menus (precisa do Tesseract).
   • Vocabulário de dicas: ajuda o Whisper a OUVIR certo (ex.: ChatGPT, DAX).
   • Correções automáticas: troca o texto DEPOIS ("Chatepte" -> "ChatGPT").
     Botão "Editar lista" abre o arquivo correcoes.json no Bloco de Notas.
   • Processar nesta rodada: quantos vídeos fazer agora (obrigatório).

5) INICIAR
   O painel mostra a etapa atual de cada vídeo (Áudio > Transcrição >
   Texto da tela > Salvar), uma barra única da rodada e o tempo restante.
   "Parar após o vídeo atual" não perde nada. Ao terminar, o app avisa com
   som e faz o ícone piscar na barra de tarefas.
   O registro técnico fica em "Mostrar detalhes técnicos".

ONDE ESTÁ O RESULTADO
   transcricoes_md\\   -> um .md por vídeo (mesma estrutura de pastas)
   base_consolidada\\  -> um arquivo por subpasta, pronto para NotebookLM/Claude
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
