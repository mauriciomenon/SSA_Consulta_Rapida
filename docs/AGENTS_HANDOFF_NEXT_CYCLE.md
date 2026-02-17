# AGENTS Handoff For Next Cycle

This handoff is ready to reuse in the next conversation.

## Estado atual

- Branch `codex/import-review`, PR #31 aberto e em andamento (base `dev`, head `codex/import-review`).
- Backlog de follow-up em `docs/RECOVERY_BACKLOG.md`.
- Refactor gui em andamento: facade em `gui/gui_ssa.py`, modulo agregado em `gui/ssa/gui_filters_advanced.py`, e submodulos versionados:
  - `gui/ssa/gui_filters_advanced_ui.py`
  - `gui/ssa/gui_filters_advanced_logic.py`
  - `gui/ssa/gui_filters_advanced_state.py`
- Itens aprovados para este sprint (A/B/C): aplicados em `a01406cc` (lock global, mask de db_path, prune apos erro).
- Versionamento de icones app concluido em `e31d03a9`.
- Hardening incremental apos isso:
  - `a4f92668` remove suppress silencioso no cleanup temporario de `utils/caching.py`.
  - `4bee3b55` remove suppress silencioso ao listar `config` em `armazenamento/database.py`.
  - `50e49920` remove suppress silencioso no fallback de labels em `interface/table_printer.py`.
  - `28776b4c` remove suppress silencioso no parse de ano em `shared/numero_ssa.py`.
- addopts com ignore em `pyproject.toml` mantido por ora; sugerir remocao no relatorio final.
- Validacao local deve rodar via `uv run` para garantir ambiente correto (evitar falha de deps como pandas fora do venv).
- `ty` em `gui/gui_ssa.py` ainda aponta ruido estrutural de stubs/union PyQt; tratar em slice dedicado, sem misturar com hardening atual.
- Hardening recente em filtros avancados:
  - `44d2e131`: guard/fallback de `_has_active_advanced_filters` no facade.
  - `0d30eca6`: variacoes de regressao do facade.
  - `2a939f4f`: hardening de logica/UI/state de filtros avancados + testes dedicados.
  - `93f5ccf1`: fix de mapeamento de chaves/colunas de prioridade (`*_values` e `grau_prioridade_*`).
  - `5ced33d1`: teste de cobertura estatica de chaves UI vs logica/detector ativo.
- Checks atuais do PR:
  - `code/snyk (mauriciomenon)` falhando por limite de plano: `Code test limit reached`.
  - Demais checks principais em andamento (DeepScan, DeepSource, security/snyk, submit-pypi).

## Pendencias antes de fechar o PR

1. Rodar gate final por lote: `py_compile`, `ruff`, `ty`, `pytest` focado nos arquivos/slices tocados.
2. Rechecar bots/checks bloqueantes do PR #31 apos concluir pipeline atual.
3. Responder comentarios do PR #31 com status dos itens aprovados (A/B/C) e decisoes de escopo (D/E).
4. E) Manter addopts ignore em `pyproject.toml` neste ciclo; sugerir remocao e ajuste de testes no relatorio final do sprint.
5. Consolidar commits finais de doc/status do sprint.
6. Release `4.13`: manter em TODO (tag ja criada no merge do PR #30; publicacao de release pendente).
7. Atualizar titulo/descricao do PR #31 para refletir melhor o escopo entregue de hardening/refactor GUI.
8. Ingerir relatorio da outra IA com protocolo abaixo antes de novos patches.

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

## Regra adotada: facade de filtros avancados

- Contrato de modulo:
  - `gui/gui_ssa.py` pode chamar `ssa_gui_filters.<simbolo>` apenas se o simbolo estiver reexportado no modulo agregado `gui/ssa/gui_filters_advanced.py`.
  - Se o simbolo for opcional durante split/refactor, usar `getattr(..., None)` com fallback explicito e comportamento seguro.
- Gate obrigatorio por slice que tocar `gui/gui_ssa.py` ou `gui/ssa/gui_filters_*`:
  - `uv run pytest -q tests/test_gui_filters_facade_contract.py`
  - `uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters`
- Cobertura minima obrigatoria:
  - caminho principal do facade;
  - caminho de fallback;
  - caminho sem handler (degradacao segura).
  - cobertura de chaves UI para logica/detector ativo;
  - cobertura de alias de colunas/chaves (ex.: `solicitante` vs `responsavel_solicitante`, `grau_prioridade_*`).

## Protocolo de ingestao da outra IA

1. Receber relatorio bruto e reformatar em itens com:
   - `id`, `severidade`, `arquivo:linha`, `evidencia`, `impacto`, `repro`.
2. Validar cada item localmente antes de editar:
   - `rg -n` no arquivo alvo;
   - `nl -ba` para confirmar linha/contexto.
3. Classificar:
   - `acao agora` (bloqueante/alto risco),
   - `backlog` (nao bloqueante).
4. Implementar apenas patches minimos por slice.
5. Rodar gate tecnico por slice:
   - `uv run python -m py_compile ...`
   - `uv run ruff check ...`
   - `uv run ty check ...` (escopo tocado; aceitar baseline conhecido em `gui/gui_ssa.py`)
   - `uv run pytest -q` focado.
6. Commit atomico por slice, push, e rechecagem de bots/checks.
7. Atualizar `docs/RECOVERY_BACKLOG.md` com pendencias nao bloqueantes.

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
Objetivo atual: fechar PR #31 com estabilidade, aplicar apenas patches minimos de risco real, e processar relatorios externos com validacao local obrigatoria.
```
