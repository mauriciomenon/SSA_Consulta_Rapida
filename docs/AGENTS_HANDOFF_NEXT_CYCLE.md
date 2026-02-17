# AGENTS Handoff For Next Cycle

This handoff is ready to reuse in the next conversation.

## Estado atual

- Branch `codex/import-review`, PR #31 aberto e em andamento (base `dev`, head `codex/import-review`).
- Backlog de follow-up em `docs/RECOVERY_BACKLOG.md`.
- Refactor gui em andamento: `gui/ssa/*` e `gui/qt_stubs.py` criados, facade em `gui/gui_ssa.py` mantido.
- Itens aprovados para este sprint (A/B/C): aplicados em `a01406cc` (lock global, mask de db_path, prune apos erro).
- Versionamento de icones app concluido em `e31d03a9`.
- addopts com ignore em `pyproject.toml` mantido por ora; sugerir remocao no relatorio final.

## Pendencias antes de fechar o PR

1. Rodar validacao por lote: `py_compile`, `ruff`, `ty`, `pytest` focado.
2. Responder comentarios do PR #31 com status dos itens aprovados (A/B/C) e decisoes de escopo (D/E).
3. Consolidar e push dos commits pendentes de documentacao.
4. Checar bots/checks e tratar apenas bloqueantes.
5. Registrar no relatorio final a sugestao de rever ignores em `pyproject.toml`.

## O que foi feito (resumo)

- Hardening de concorrencia e estado em fluxo async/filtros/workers.
- Correcoes pontuais em wrappers de teste com timeout/kill/cleanup mais robustos.
- Ajustes de testes para isolamento e regressao.
- Correcoes pequenas de qualidade em tipos e comportamento defensivo.
- Commits atomicos, com validacao a cada lote.

## Como foi feito (metodo)

- Ciclos curtos: diagnostico -> patch minimo -> validacao -> commit atomico -> push.
- Validacao tecnica por lote:
  - `py_compile`
  - `ruff`
  - `pytest` focado + suites sensiveis
- Recheque de PR/reviews/checks apos cada push.
- Sem refatoracao ampla fora de escopo.
- Sem mudanca de posicao de botoes/layout.

## Regras de execucao para o novo ciclo

1. Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: `py_compile`, `ruff`, `pytest` focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito.
6. Nao criar branch/PR novo sem autorizacao explicita.
7. Nao usar suppress/except vazio para esconder erro real.
8. Usar pip/pip3 para deps quando operar via uv.
9. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
10. Manter backlog de follow-up em `docs/RECOVERY_BACKLOG.md`.

## Objetivo do novo ciclo

- Manter o mesmo cuidado, com foco na refatoracao de `gui/gui_ssa.py` (SSAMainWindow) para reduzir acoplamento.
- Preservar layout e comportamento da GUI; refatoracao deve ser estrutural, nao visual.
- Fazer levantamento detalhado antes de mover metodos para novos modulos.

## Texto pronto para abrir a nova conversa

```text
Contexto: branch de recovery foi mergeada; manter mesma disciplina de qualidade.

Regras de execucao:
1. Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: py_compile, ruff, pytest focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito.
6. Nao criar branch/PR novo sem autorizacao explicita.
7. Nao usar suppress/except vazio para esconder erro real.
8. Usar pip/pip3 para deps quando operar via uv.
9. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
10. Manter backlog de follow-up em docs/RECOVERY_BACKLOG.md.

Objetivo do novo ciclo: manter o mesmo cuidado, mas com foco funcional novo.
Objetivo atual: refatorar gui/gui_ssa.py sem mudar layout, com levantamento detalhado antes.
```
