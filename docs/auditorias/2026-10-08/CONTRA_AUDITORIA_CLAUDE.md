# Contra-auditoria — Claude — 11/10/2026

Revisão crítica da [auditoria do Codex](RELATORIO.md) e da [revisão de interface](INTERFACE_E_LAYOUT.md), feita pelo agente que escreveu o código auditado. Por isso, este documento separa com cuidado o que foi **reproduzido**, o que foi **conferido no código** e o que é **opinião**.

- **Commit avaliado:** `c0c3415` (v0.1.1), o mesmo da auditoria do Codex. Nenhuma correção foi aplicada até a data deste documento.
- **Ambiente:** Linux, Python 3.13, FFmpeg 6.1, Tesseract 5; Whisper simulado. Windows físico, janela interativa e modelo real **não** foram testados aqui.

## 1. Parecer sobre a auditoria do Codex

| Critério | Avaliação |
|---|---|
| Evidências | **Fortes.** Cada achado aponta arquivo e linha; 10 vêm com script de reprodução |
| Honestidade sobre limites | **Alta.** Declara o que não testou (Windows, GUI, modelo real, egress, jurídico) |
| Severidades | **Algumas infladas** (X4, X5, X8, X9, X12) e **duas subestimadas** (X13, X16) |
| Cobertura | Boa em integridade e estado. Não investigou a **causa** da lentidão (P17) |
| Recomendações | Sensatas e alinhadas às decisões existentes (mantém CustomTkinter e ADR-007) |

**Conclusão:** a auditoria é confiável e útil. Os achados devem orientar a próxima versão. A recomendação de **não tratar a v0.1.1 como pronta para distribuição ampla** está correta.

## 2. Verificação independente

### 2.1 Reprodução

O script [`reproducoes.py`](reproducoes.py) foi executado no commit `c0c3415` (com `PYTHONPATH` na raiz do repositório). **Os 10 resultados foram idênticos** aos de [`evidencias.json`](evidencias.json).

### 2.2 Conferência no código dos achados marcados como "fluxo estático"

| ID | Conferência | Resultado |
|---|---|---|
| X3 | `gui/app.py:576` monta um `cfg` novo a partir dos campos; `:590` troca só `projeto.cfg`, mantendo `registro` e `itens` da leitura anterior | **Confirmado** |
| X4 | `_ler_pasta` (`gui/app.py:393`) retorna se `rodando`; portanto, **não** há segunda leitura durante a rodada. Uma segunda leitura é possível **durante outra leitura** (Procurar → `_ler_pasta`). A leitura não usa `Trava` | **Confirmado em parte** (cenário mais estreito que o descrito) |
| X11 | O tratador `escaneado` não chama `consolidar()` | **Confirmado** |
| X12 | `cli.py:178-184` descarta o resumo e retorna 0 | **Confirmado** |
| X13 | `self.after(...)` chamado de threads de trabalho em `gui/app.py:367`, `gui/verificacao.py:171` e `:198` | **Confirmado** |
| X15 | `Registro._ler()` só lê `registro.csv` | **Confirmado** |
| X16 | `gui/app.py:611` emite `lote_fim` com `ok=0, erro=0`; `_fim_da_rodada` cai no ramo de sucesso, enche a barra e `:782` toca o som de sucesso | **Confirmado** |

### 2.3 Correções que a documentação anterior dava como concluídas

O autor reconhece que estes itens de [`docs/AUDITORIA.md`](../../AUDITORIA.md) estavam **incompletos**:

| Item | Registro anterior | Situação real | Achado |
|---|---|---|---|
| C2 | Nomes iguais não colidem | Vale entre subpastas, não entre extensões | X2 |
| C3 | Vídeo excluído sai da base | Só na próxima rodada | X11 |
| C4 | Vídeo substituído é refeito | É refeito, mas com o **áudio antigo** em cache | X1 |
| C5 | Escrita atômica | Por arquivo, não por conjunto | X5, X15 |
| C12 | Trava impede duas execuções | Proteção parcial e reentrante | X4 |

## 3. Severidade: concordâncias e divergências

| ID | Codex | Claude | Justificativa da divergência |
|---|---|---|---|
| X1 | 🔴 | 🔴 | — |
| X3 | 🔴 | 🔴 | — |
| X16 | 🟠 | **🔴** | O usuário leigo é induzido a confiar num resultado inexistente; é falha de integridade percebida, não só de UX |
| X13 | 🟠 | **🔴** | O projeto já teve um **travamento real** (C19) da mesma família: Tk acessado fora da thread principal. A probabilidade não é teórica |
| X2 | 🔴 | 🟠 | Corrompe dados, mas exige mídias de mesmo nome e extensões diferentes na mesma pasta; correção barata, por isso deve entrar na fase 1 |
| X5 | 🔴 | 🟠 | A base consolidada é **derivada** e regenerável a partir dos `.md`; não há perda definitiva |
| X4 | 🔴 | 🟠 | Ver §2.2: cenário real é mais estreito |
| X6, X7, X10, X11 | 🟠 | 🟠 | — |
| X14 | 🟠 | 🟡 agora / 🟠 antes de publicar | Relevante para Release pública, não para uso privado |
| X15 | 🟠 | 🟡 | Depende de Excel aberto durante a gravação |
| X8 | 🟠 | 🟡 | NotebookLM e Claude não consomem as imagens da base |
| X9 | 🟠 | 🟡 | Exige um único vídeo com ~400 mil palavras (~40 h de fala) |
| X12 | 🟠 | 🟡 | O público-alvo usa a janela; relevante para automação |

As severidades acima ordenam o trabalho; nenhuma justifica deixar um achado sem correção.

## 4. Achado adicional: causa provável da lentidão (P17)

| Execução | Threads | Velocidade |
|---|---|---|
| Script v1 (padrão do faster-whisper) | **4** (`cpu_threads` padrão, documentado no próprio `WhisperModel`) | 1,48x |
| App v0.1.1 | **12** (`transcricao.py:47` força `os.cpu_count()`, que conta threads lógicas) | 1,22x |

Na CPU de referência (6 núcleos físicos, 12 lógicos, 2014), usar mais threads que núcleos físicos costuma piorar a inferência. **Hipótese não comprovada**: a mesma comparação teve outra diferença, porque o PC pode ter sido usado durante o teste. Validar com benchmark de 4, 6 e 12 threads no mesmo vídeo antes de mudar o padrão. Se confirmada, o padrão deve ser o número de **núcleos físicos**.

## 5. Revisão de interface

Concordo com UX-01 a UX-11. A **barra de ação com quantidade junto ao botão principal** é a melhor recomendação da revisão: resolve UX-04 sem violar o ADR-007.

Ressalvas:

1. O selo "PC pronto · CPU" do wireframe perde o **contador de pendências e o destaque** pedidos pelo usuário em 07/10/2026; mantê-los.
2. "Projeto: Curso Power BI" depende da identidade de projeto (X7). Implementar junto, não antes.
3. Testes com leitor de tela (NVDA): o Tkinter expõe pouca informação de acessibilidade. **Operação por teclado** é viável e deve ser meta; suporte completo a leitor de tela exigiria trocar de toolkit e fica fora do escopo da v0.x.
4. Busca e filtro na tabela: úteis, mas de baixa prioridade para acervos de dezenas de vídeos.

## 6. Plano revisado

| Fase | Conteúdo | Critério de aceite |
|---|---|---|
| 0 | Mesclar este pacote na `main`; benchmark de threads (§4) | Pacote acessível pela `main`; P17 com causa medida |
| 1 | X1, X3, X16, X13, X2, X5, X6, X7, X11 | Para cada ID: teste que **falha antes** e **passa depois**; script do Codex com resultado invertido onde aplicável |
| 2 | X4, X10, X15, X8, X9, X12 + documentação desatualizada (ADR-008, ROADMAP/P4, briefing) | Idem |
| 3 | Layout (seção 5), após estados estáveis | Capturas em 1366×768, escalas 125%/150%, temas claro e escuro, fluxo completo por teclado |
| Pré-publicação | X14, P1 (Windows físico), P7, P8 e a seção 7 | Ver seção 7 |

## 7. Repositório público: manter as auditorias?

### Recomendação

**Sim, manter as auditorias no repositório, mas só tornar o repositório público depois da fase 1 e dos ajustes abaixo.**

### Por que manter

| Benefício | Explicação |
|---|---|
| Portfólio | Mostra processo de engenharia real: revisão independente, reprodução, divergência fundamentada e correção rastreável. Isso é mais raro e mais valioso que o código em si |
| Transparência | Usuários sabem o que foi testado e o que não foi |
| Rastreabilidade | Cada ID (X1…X16) pode apontar para o commit e o teste que o corrigiram |

### Riscos e como tratá-los

| Risco | Gravidade | Tratamento |
|---|---|---|
| Publicar com defeitos de integridade conhecidos e não corrigidos | Média | Publicar **depois da fase 1**, com tabela de status por ID (corrigido em / teste / pendente) |
| Não são vulnerabilidades exploráveis | — | O app é local, sem servidor nem porta aberta; os achados afetam a integridade dos dados do próprio usuário, não terceiros. Expô-los não cria vetor de ataque |
| **E-mail pessoal nos commits** | Média | Os commits foram feitos com e-mail pessoal. Ao tornar o repositório público, ele fica visível no histórico. Usar o e-mail `noreply` do GitHub nos próximos commits e decidir se o histórico existente deve ser reescrito **antes** de publicar (reescrever depois não remove cópias já feitas) |
| Nome de curso pago citado na documentação ("vídeo de referência" em `HISTORICO.md` e `AUDITORIA.md`) | Baixa | Trocar por "vídeo de referência (36 min)". O conteúdo transcrito nunca foi versionado (`.gitignore`), mas **editar o arquivo não apaga o histórico**: vale a mesma decisão do item anterior |
| Detalhes do PC de referência (CPU, RAM, GPU) | Baixa | Inofensivos e úteis como benchmark; manter |
| `dependencias-instaladas.txt` e notas do ambiente do Codex | Baixa | Inofensivos; manter como registro histórico, já rotulados como tal |
| Licenças (FFmpeg GPL embutido, P8) | Média | Resolver P8 antes da primeira **Release** pública; o código-fonte em si não embute o FFmpeg |

### Formato sugerido na publicação

- Manter `docs/auditorias/AAAA-MM-DD/` como registro **imutável** de cada rodada.
- Criar `docs/auditorias/README.md` com índice e **status por ID**, que é o único arquivo que muda depois.
- No README principal, uma linha: "Auditado de forma independente; veja docs/auditorias".

---

*Documento escrito pelo Claude a pedido do responsável pelo projeto. O código não foi alterado nesta etapa.*
