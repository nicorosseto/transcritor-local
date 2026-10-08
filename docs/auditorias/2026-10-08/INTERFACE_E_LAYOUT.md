# Auditoria de interface e proposta de layout — Transcritor Local

Escopo: inspeção estática de `transcritor/gui/app.py`, `componentes.py`, `verificacao.py` e capturas `docs/img/app.png` e `verificar_pc.png`. As capturas representam documentação, não execução visual atual. Não houve alteração de fontes nem ensaio com leitor de tela/display nesta revisão. Severidades expressam impacto no usuário, não conformidade certificada.

## Parecer

O aplicativo tem uma base coerente para transcrição desktop: linguagem portuguesa simples, seleção de lotes, indicação de etapas, estimativa explicitamente aproximada, distinção entre parar ao fim e cancelar, diagnóstico de dependências e log recolhível. A prioridade é garantir coerência entre projeto, seleção e destino antes de investir no acabamento. O layout atual expõe opções demais e esconde uma escolha obrigatória dentro de um painel rolável. A combinação visual de CustomTkinter com Treeview nativo merece validação em Windows e nos dois temas.

## Achados priorizados

| ID | Prioridade | Evidência | Impacto e recomendação |
|---|---|---|---|
| UX-01 | Alta | `app.py:277`, `app.py:387`, `app.py:590`; `pipeline.py:76`, `pipeline.py:85` | Alterar pasta de saída depois de ler vídeos modifica somente o campo; iniciar troca `projeto.cfg`, mas mantém registro e itens construídos anteriormente. Os Markdown podem ir ao destino novo e o registro ao destino anterior. Edição manual da origem também deixa itens antigos. Invalidar scan ao mudar caminhos e reconstruir projeto antes de permitir iniciar; manter um snapshot de configuração por execução. |
| UX-02 | Alta | `app.py:627`, `app.py:111`, `app.py:115`, `app.py:469` | Durante execução ficam habilitados entradas e botões das pastas, seleção em massa e editor de correções. A tabela bloqueia clique individual, mas não ações em massa. O caminho visível pode divergir do destino real; cliques Procurar podem editar campos mesmo que leitura seja impedida. Bloquear todos os controles que alteram contexto, preservar ações de consulta e abrir a saída do snapshot em execução. |
| UX-03 | Alta | `app.py:141`, `app.py:152`, `app.py:459`; `componentes.py:18` | Marcação é um glifo numa Treeview com `selectmode="none"` e handler de mouse. Não há comando por Espaço para alternar item focado nem seleção individual explícita por teclado. Dicas dependem do mouse. Implementar foco por linha, Espaço, selecionar todos/desmarcar com atalhos e ajuda também em FocusIn; validar leitor de tela no sistema alvo. |
| UX-04 | Média | `app.py:164`, `app.py:200`, `app.py:486`, `app.py:542` | Quantidade obrigatória começa em "Escolha..." e fica no fim do painel rolável; botão iniciar pode estar desabilitado sem explicar qual requisito falta. Seleção inicial de pendentes não habilita a ação. Exibir resumo junto ao botão: "Selecione a quantidade desta rodada"; manter escolha explícita obrigatória conforme ADR-007 e oferecer Todos como opção. |
| UX-05 | Média | `app.py:60`, `app.py:129`, `app.py:143`, `app.py:149` | Janela mínima 980×700, painel direito mínimo 400, colunas têm mínimo agregado 486; não existe scrollbar horizontal. Margens reduzem área útil e nomes/subpastas e status podem ficar truncados. Tornar opções recolhíveis, permitir rolagem horizontal e mostrar nome completo por foco/detalhe. Validar 1366×768 com escala de 125%/150% e 1024×768. |
| UX-06 | Média | `app.py:37`, `app.py:747`, `app.py:750` | Erro aparece como status genérico; detalhes dependem do log técnico de lote. Não existe ação contextual por vídeo para copiar erro, abrir resultado ou repetir somente falhas. Acrescentar painel de detalhe com mensagem clara, causa quando conhecida e "Tentar novamente". Não chamar conteúdo gerado de válido sem checar existência do resultado. |
| UX-07 | Média | `app.py:757`, `app.py:771`, `app.py:782` | Som de sucesso é usado também em cancelamento, parada e falha total. No erro inesperado `_iniciar` emite lote_fim com ok=0/erro=0 (`app.py:609`), que produz "Rodada concluída · 0 vídeos". Diferenciar finalização com sucesso, interrupção e falha; produzir estado explícito de falha fatal. |
| UX-08 | Média | `app.py:139`, `app.py:172`, `app.py:225`, `verificacao.py:18` | Treeview recebe fonte/altura, mas não tema sincronizado; há vários cinzas fixos e cores fixas de sucesso/alerta em tema system. Algumas combinações podem ter contraste insuficiente em tema escuro. Não foi medido contraste ao vivo. Usar pares light/dark e verificar 4,5:1 para texto normal, 3:1 para texto grande e limites de controles como referência. |
| UX-09 | Média | `verificacao.py:151`, `verificacao.py:163`, `componentes.py:120`, `componentes.py:126` | Títulos dos cartões não têm wrap; barra de download e textos usam larguras fixas; diálogos não redimensionam. Identificadores de CPU, erros extensos ou escala de fonte podem extravasar. Adotar grid, wrap dependente da largura e áreas roláveis para mensagens grandes. |
| UX-10 | Baixa | `app.py:180`; captura app.png | Checkbox desabilitado de IA visual promete versão futura e ocupa espaço do fluxo atual. Mover roadmap para ajuda/sobre, evitando aparentar recurso disponível. |
| UX-11 | Baixa | `app.py:136`, `app.py:459` | Instrução manda clicar "na caixinha", mas handler alterna a linha inteira sem checar coluna. Um clique para ler nome/status pode mudar seleção. Definir comportamento intencional e consistente: linha abre detalhes, caixa/Espaço marca; ou dizer "clique no vídeo para marcar". |
| UX-12 | Baixa | `app.py:798`, `app.py:807`, `app.py:438` | Abrir saída/editor chama aplicativos externos sem tratamento de falha e usa xdg-open para toda plataforma não Windows. Informar erro acionável e respeitar plataforma suportada. Não assumir suporte macOS sem teste. |

## Direção de layout para o agente frontend

Manter aplicação desktop e CustomTkinter nesta evolução. Uma migração web/Electron adicionaria distribuição e integração com arquivos sem resolver integridade de dados. Priorizar utilitário de trabalho, com uma ação primária e opções avançadas sob demanda.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Transcritor Local                  [PC pronto] [Ajuda]              │
│ Projeto: Curso Power BI            [Trocar projeto]                 │
├────────────────────────────────────────────────────────────────────┤
│ Origem  /Cursos/Power BI                 [Escolher] [Atualizar]     │
│ Saída   /Cursos/Power BI_transcricoes    [Escolher] [Abrir]         │
├─────────────────────────────────────────┬──────────────────────────┤
│ Vídeos                                  │ Configuração             │
│ [Buscar vídeo...] [Todos ▾]              │ Qualidade                │
│ 24 vídeos · 16 pendentes · 8 concluídos  │ [Rápido|Equilibrado|...]  │
│ [✓] Vídeo              Duração  Estado  │ Descrição e memória      │
│ [✓] Módulo 01/aula...  00:12:30 Pendente │ [ ] Ler texto da tela    │
│ [ ] Módulo 02/aula...  00:20:00 Pronto   │ Disponibilidade e custo  │
│                                         │ [▸ Opções avançadas]     │
│ Selecionar: [Pendentes] [Todos] [Nenhum] │ Vocabulário / correções  │
│ [Detalhe do vídeo selecionado]          │                          │
├─────────────────────────────────────────┴──────────────────────────┤
│ Rodada: 16 selecionados · 2h10 de vídeo · aproximadamente 45 min    │
│ Quantidade [Escolher quantidade ▾]           [Transcrever vídeos]   │
├────────────────────────────────────────────────────────────────────┤
│ Processando aula 3 de 16 · Transcrevendo áudio                      │
│ [██████████████────────────────────────]  38%                      │
│ ~28 min restantes  [Parar ao fim do vídeo] [Cancelar]               │
│ [▸ Registro de atividades]                                        │
└────────────────────────────────────────────────────────────────────┘
```

Em janela estreita, o painel de configuração vira seção recolhível acima do rodapé e a tabela ocupa a largura; a quantidade e ação primária nunca dependem da rolagem lateral. Rolagem horizontal da tabela é apenas contingência para conteúdos extensos, não requisito para executar a tarefa principal. Estado vazio ensina "Escolha uma pasta para encontrar os vídeos". Estado sem resultados explica formatos aceitos. Resultado concluído mostra "Abrir transcrição", "Abrir base consolidada", total de falhas e próxima ação. Separar preparação/download do progresso de transcrição: hoje a mesma barra reinicia após download (`app.py:697`), contradizendo visualmente a promessa de progresso monotônico.

Sistema visual sugerido: espaçamento de 8/16/24 px; texto base 14–16 px, títulos 18–22 px; altura de linha de tabela 32–36 px; comandos 36–40 px; uma cor azul para ação primária, secundárias neutras, cancelamento em estilo de alerta reservado. Estados sempre combinam texto e símbolo; ícones consistentes vetoriais em lugar de emojis dependentes da fonte. Dar tratamento claro/escuro à Treeview e preservar preferências de tema.

## Critérios de aceite e plano

1. **Integridade do fluxo (P0):** impedir iniciar com scan obsoleto, pasta inválida ou configuração misturada. Ao trocar saída A por B, todos os resultados e registro pertencem ao projeto B; durante execução a origem/destino visíveis coincidem com o snapshot. Depende das correções backend identificadas pela auditoria principal.
2. **Estados e feedback (P1):** botão primário explica bloqueios; erro fatal não comunica sucesso; download tem progresso separado; falhas têm detalhe por vídeo e repetição dirigida. Estado "Concluído" depende de resultados existentes e consistentes, considerando os problemas de cache, colisão de extensões e saídas ausentes encontrados na revisão backend.
3. **Layout e produtividade (P1):** quantidade e CTA sempre visíveis; filtros por estado, busca por caminho, opções avançadas recolhíveis, resultado acessível por item.
4. **Acessibilidade (P1):** percorrer o fluxo só com teclado; foco visível, Espaço na marcação, Escape seguro nos diálogos, texto legível sem depender de cor, dicas acessíveis por foco. Testar NVDA/Windows e verificar árvore de acessibilidade antes de declarar suporte. Se toolkit não expuser controles adequadamente, avaliar substituição pontual de widgets ou toolkit, com prova de conceito.
5. **Validação visual (P2):** Windows alvo, temas claro/escuro, escalas 100/125/150/200%, nomes longos/Unicode, diretórios profundos, mensagens extensas, lista grande, sem modelos, sem OCR, disco insuficiente, cancelamento durante download/transcrição/OCR. Medir contraste e ajustar largura adaptativa; não afirmar conformidade só pela inspeção de código.

Entrega recomendada ao especialista: primeiro mapa de estados e wireframe aprovado tecnicamente pelo fluxo, depois protótipo dos estados vazio/configurado/processando/falha/concluído, por fim implementação incremental. Não há necessidade de alteração das fontes para esta auditoria; o plano é uma proposta, não um redesign já implementado.
