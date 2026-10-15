# Rechecagem dos bloqueios de 14/10: Codex, 15/10/2026

Resposta ao [pedido de rechecagem](../PEDIDO_RECHECAGEM_2026-10-15.md), sobre a `main` no commit `1c08ad3`. O relatório do Codex ficou no ambiente dele, sem commit; este arquivo registra o parecer que ele enviou ao responsável.

| Bloqueio | Veredito | Evidência citada |
|---|---|---|
| K1 | Resolvido | Botão bloqueado durante a leitura; releitura impede iniciar com a lista antiga |
| B1 / K5 | Resolvido | 8 testes passaram; arquivos externos não entraram nos pacotes |
| B2 / K2 | Resolvido com ressalva | Exclusão do PyAV e verificações do autoteste confirmadas. **Ressalva:** inspecionar o ZIP exato do Windows antes de publicá-lo |
| B3 / K7 | Resolvido | Workflow configura rascunho, pre-release, notas e hashes |
| C1 / K3 | Resolvido | Verificações atrasadas não sobrescrevem o estado atual; a abertura da Preparação também passou |

**Também:** 113 testes passaram, `pyflakes` sem apontamentos, N22 passou nas verificações disponíveis. Nenhum bloqueio novo, funcional ou de privacidade, no escopo examinado. Não alterou código nem leu a resposta do outro auditor.

**Como a ressalva é atendida:** o Release é criado como rascunho a partir da tag; antes de publicar, o responsável baixa o `.zip` anexado ao rascunho e confere que não há pasta `bin`, que `licencas/BIBLIOTECAS.txt` existe e que o app abre (ver [RETOMADA](../../RETOMADA.md)).
