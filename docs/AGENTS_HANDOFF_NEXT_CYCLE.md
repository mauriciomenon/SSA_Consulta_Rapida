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
  - 2026-02-17 slice: `_has_active_advanced_filters` reexportado em `gui/ssa/gui_filters_advanced.py` e teste de cobertura corrigido/fortalecido em `tests/test_gui_filters_advanced_logic.py`.
  - 2026-02-17 triagem externa: `responsavel_emissor` decisao B aplicada (remocao/desativacao do fluxo em UI/logica de filtros avancados).
  - 2026-02-17 rescan evidence: 75 arquivos, 64 processados, 11 erros em `SSAs Derivadas e Relacionadas_*.xlsx` por colunas obrigatorias ausentes no extrator principal.
  - 2026-02-17 slice entregue: disparo automatico de sync de derivadas no `run_importer_logic` para planilhas especiais (`SSAs Derivadas e Relacionadas_*`), sem afrouxar validacao do extrator principal.
  - comportamento atual: planilhas especiais sao ignoradas no extrator principal; sync usa a planilha especial mais recente (mtime) e marca todas as especiais no cache quando o sync conclui.
- Checks atuais do PR:
  - `code/snyk (mauriciomenon)` falhando por limite de plano: `Code test limit reached`.
  - `security/snyk (mauriciomenon)` falhando por limite de plano: `You have used your limit of private tests`.
  - Demais checks principais em `pass` (DeepScan, DeepSource, submit-pypi, GitGuardian, Socket, cubic).

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

1. Manter ASCII em codigo; em docs tecnicos, permitir PT-BR normal. Nao usar emoji/emdash.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: `py_compile`, `ruff`, `pytest` focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito.
6. Nao criar branch/PR novo sem autorizacao explicita.
7. Nao usar suppress/except vazio para esconder erro real.
8. Usar pip/pip3 para deps quando operar via uv.
9. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
10. Manter backlog de follow-up em `docs/RECOVERY_BACKLOG.md`.

## Regras de escrita tecnica (NAO FAZER)

1. Nao "calcar" erro de runtime apenas removendo log/warning.
2. Nao declarar "corrigido" quando o fluxo funcional ainda falha.
3. Nao trocar erro visivel por fallback silencioso sem tratar causa raiz.
4. Nao abrir fluxo generico quando a acao e contextual (ex.: arvore deve usar SSA selecionada).
5. Nao fechar slice sem validar repro antes/depois do mesmo caso reportado pelo usuario.
6. Nao responder com justificativa defensiva; responder com evidencia objetiva (arquivo:linha + teste).

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

## Update 2026-02-17 (advanced filters)

- Applied user decision B for `responsavel_emissor`: advanced filter control flow removed from UI panel context/assembly.
- Added guard test to prevent reintroduction of `adv_responsavel_emissor_*` controls.
- Mandatory GUI filter gates executed and passing (`facade_contract`, `advanced_filters`, `advanced_logic`).
- Hardened derivadas panel button `Especificas...`:
  - now uses materialized derivadas summary from DB (`ssa_derivada_summary`) to show useful stats/top maes in popup;
  - button enable state now accepts DB-derived relations even when `derivada_de` series in the visible dataframe is empty.
- Fixed responsive grid regression after `responsavel_emissor` removal: no more `emis_resp_box` references in `_reorganize_advanced_filters_grid`.

## Update 2026-02-17 (advanced filters ano_execucao)

- Removed dead code path for `data_execucao` in year-execution filter logic.
- Year execution filtering now uses `semana_executada` path only, aligned with current schema/import.
- Added focused test for `ano_execucao_values` over `semana_executada`.
- Fixed legacy precedence for `ano_execucao` + `ano_execucao_exclude=True` to avoid include/exclude collision that could zero all rows.

## Update 2026-02-17 (import derivadas multi-sheet)

- Importer derivadas special sync no longer picks only the latest sheet.
- `sync_derivadas` now accepts `sheet_files` and merges edges from multiple special sheets in one sync cycle.
- `run_importer_logic` now forwards all detected `SSAs Derivadas e Relacionadas_*.xlsx` files.

## Update 2026-02-18 (mega sprint closure)

- Branch/head: `codex/import-review`
- New reliability commits:
  - `ff266350`: filter cache key supports advanced-filter context token.
  - `6f4fcc7a`: derivadas visual parser reduces invalid_parent noise on root-only rows.
  - `5a50ea17`: GUI manual derivadas update now validates consistency scan and fails closed.
  - `f9e69d86`: importer now fails closed when derivadas sync/consistency is not clean.
- Data integrity state validated on `data/ssas.db`:
  - `scan_derivadas_consistency`: `is_consistent=true`, all issue counts `0`.
  - latest materialization snapshot remained stable (`matrix_active=3547`, `summary_total=5460`).

## Update 2026-02-18 (mega sprint block 6)

- `1f213578`: `sync_derivadas` now returns `sheet_file_reports` with per-file parse evidence, plus path dedupe for relative/absolute duplicates.
- `ffd5d8ef`: importer derivadas sync now fails closed if any special sheet lacks individual parse evidence.
- `3daddd9f`: GUI `Atualizar Derivadas` now fails closed if any special sheet lacks individual parse evidence.
- `f7f7ead7`: CLI `sync` now supports `--special-docs-dir` for direct ingest of all special derivadas sheets in a folder.
- `60adbd5a`: committed refreshed `data/ssas.db` after full special-sheet sync run.
- Runtime evidence from executed full sync:
  - `sync_run_id=4`
  - actor: `mega-sprint-special-sync`
  - `sheet_files_count=11`, `db_edges=3216`, `sheet_edges=1497`, `merged_edges=3547`
  - post-sync consistency: `is_consistent=true`

## Status snapshot 2026-02-18 (for audit and delegation)

### Falhas graves (risco alto)

1. Tooling gate externo fora do codigo:
   - `code/snyk` e `security/snyk` continuam em fail por limite de plano, nao por regressao local.
2. Kluster indisponivel por rede durante slice atual:
   - chamadas recentes retornaram `ENOTFOUND api.kluster.ai`.
   - risco: quebra de protocolo de review automatico ate normalizar conectividade.

### Diretriz de triagem fixada pelo usuario

1. tratar como falso positivo neste ciclo:
   - remover `if df is None`;
   - adicionar novos locks em scripts;
   - abrir refactor amplo de race em `gui/workers`.
2. ignorar `E501` neste ciclo.

### Falhas intermediarias (risco medio)

1. Baseline de tipagem GUI ainda muito alto:
   - `uv run ty check gui/gui_ssa.py tests/test_gui_filter_logic.py` retorna ~301 diagnostics legados.
2. Backlog de concorrencia/cancelamento ainda aberto:
   - `gui/workers/rescan_worker.py`, `gui/widgets/rescan_progress_dialog.py`, `scripts/run_pytest_stream_and_log*.py`.

### Melhorias de clareza de codigo (baixo risco)

1. Logs de erro de sync foram melhorados para listar planilhas sem evidencia individual.
2. Contrato de sync agora tem sumario agregado de evidencia por arquivo (`sheet_evidence`).

### Condicoes de corrida conhecidas (pendente)

1. `scripts/run_pytest_stream_and_log.py` e `scripts/run_pytest_stream_and_log_v2.py`:
   - contadores compartilhados sem sincronizacao.
2. `interface/cli_enhancement_manager.py`:
   - lock em arquivo temporario nao serializa escritores concorrentes no alvo real.
3. `gui/workers/rescan_worker.py`:
   - cleanup com suppress em detach pode mascarar estado inconsistente.

### Erros de sincronizacao/dados

1. Fluxo de derivadas:
   - estado atual esta consistente (`scan is_consistent=true`).
   - hardening novo protege contra perda silenciosa por arquivo sem evidencia.
2. Pendencia operacional:
   - manter execucao periodica de sync + scan em banco real apos lotes novos de planilha.

### Codigo morto confirmado

1. `core/app_logic.py`:
   - trecho `if df is None` segue listado como dead code no backlog.
2. Pendencias adicionais em backlog devem ser tratadas por slice pequeno com teste.

### Linter status

1. `ruff` global:
   - ~277 erros no repo completo (muitos em scripts auxiliares e testes antigos).
2. `ty` global em GUI:
   - ~301 diagnostics no baseline de `gui/gui_ssa.py` + `tests/test_gui_filter_logic.py`.
3. Em arquivos tocados no slice de importer/derivadas:
   - `py_compile`, `ruff`, `ty`, `pytest` focado passaram.

## Sessao: tarefas faceis para outra IA (baixo risco, auditavel)

Objetivo:
- Delegar apenas tarefas simples e mecanicas, sem risco funcional alto.
- Proibido mexer em layout GUI e schema.

Escopo permitido:
1. Limpeza ruff em scripts auxiliares e testes utilitarios sem impacto de runtime.
2. Ajustes de mensagem/log e testes de cobertura de erro.
3. Refino de asserts em testes de cancelamento/progresso sem alterar fluxo principal.

Escopo proibido:
1. Nao alterar `gui/gui_ssa.py` fora de testes muito localizados.
2. Nao tocar pipeline de import principal sem teste focado.
3. Nao alterar schema SQL.

Pacote de tarefas delegaveis (ordem recomendada):
1. Ruff facil em scripts:
   - remover imports nao usados (`F401`), variaveis nao usadas (`F841`), f-strings sem placeholder (`F541`) em `scripts/*` e `launchers/*`.
2. Ruff facil em testes utilitarios:
   - mesmo padrao em `tests/verify_*`, `tests/test_verification_manual.py`, `tests/test_search_v_character.py`.
3. Testes de robustez de progresso:
   - fortalecer `tests/test_import_cancellation.py` com assert do evento final `finish`.
4. Testes de dialogo de rescan:
   - ampliar asserts em `tests/test_rescan_progress_dialog.py` para estado de botoes/status.
5. Testes de lock:
   - melhorar `tests/test_filter_cache_locking.py` para validar uso correto de lock, nao apenas enter_count.

Checklist de auditoria (eu audito depois):
1. Cada tarefa em commit atomico separado.
2. Gate por slice:
   - `uv run python -m py_compile <files>`
   - `uv run ruff check <files>`
   - `uv run ty check <files>`
   - `uv run pytest -q <tests focados>`
3. Nao aceitar refatoracao transversal.
4. Se tocar GUI filtros, rodar gates obrigatorios de facade/filtros.

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
