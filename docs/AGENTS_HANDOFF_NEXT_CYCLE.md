# AGENTS Handoff For Next Cycle

This handoff is ready to reuse in the next conversation.

## CURRENT TRUTH 2026-02-28 21:20 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint D closeout status:
  1. cache size guard delivered in GUI cache and Streamlit cache.
  2. matrix item `9` moved to `resolved` (older deferred snapshots are historical only).
  3. cache stats now include `skipped_large_entries` and `max_entry_mb`.
- Optional P3 delivery status:
  1. item `104` resolved with persisted width profile memory across sessions.
  2. item `107` resolved with persisted render telemetry across sessions.
- Streamlit colors/behavior follow-up:
  1. explicit theme palettes with CSS variables implemented.
  2. runtime theme selector moved to header (always visible).
  3. selected theme now persists across sessions.
- Streamlit usability follow-up:
  1. situacao is always visible and now has quick mode + count labels.
  2. executor/emissor compacted to single-select with `(Todos)`.
  3. quick "colunas exibidas" shortcut now exists in table tab.
  4. sidebar source controls moved to collapsed advanced section.
  5. table render height now scales with page rows.
- Item `92` closure:
  1. cache architecture refactor completed with shared get/store helpers.
  2. stats/ttl/lru contract preserved and revalidated in focused tests.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused `pytest` (`tests/test_filter_cache_locking.py` + `tests/test_streamlit_filter_cache.py`): `40 passed`
- Deferred classification with difficulty:
  - structural (P2):
    1. `SSAMainWindow` split (`item 84`) - alta
    2. streamlit god-module split (`item 101`) - alta
- Retomada checklist:
  1. `git status --short`
  2. patch minimo no item aprovado
  3. kluster auto + fix de `agent_todo_list`
  4. `py_compile`, `ruff`, `ty`, `pytest` focado
  5. sync docs de continuidade no mesmo slice
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.
  - doc hygiene rule: do not promote older blocks above this one.

## CURRENT TRUTH 2026-02-28 12:25 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint closure state:
  1. "25 graves v4" concluido com patch minimo em command handlers/importer/stream wrappers.
  2. regressions focadas adicionadas e pacote tecnico validado.
  3. docs de continuidade e backlog sincronizados para proxima sessao.
  4. release local atualizado para `4.25.0`.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest package: `30 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in the package: clean
- Retomada checklist (ordem de execucao):
  1. `git status --short`
  2. selecionar proximo slice de risco real
  3. patch minimo
  4. kluster auto + fix de `agent_todo_list`
  5. `py_compile`, `ruff`, `ty`, `pytest` focado
  6. sync docs da trilha
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 04:40 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (25 graves v4):
  1. command-handlers mapping path safety + centralized config resolution + save-cache coherence.
  2. importer guardrails for early cancel and unexpected `None` extractor result.
  3. stream wrapper reader-join timeout configurability across timeout/normal/error paths.
  4. focused regressions added for command-handlers/importer/stream wrappers.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest package: `30 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 04:10 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (20 graves v3):
  1. rescan dialog finish/cancel contract hardened for duplicate finish and running-cancel phase.
  2. rescan worker lifecycle hardened (pre-prune, stale active ref cleanup, deterministic cancel status, post-dialog prune).
  3. stream wrapper queue poll timeout configurable and faster deterministic loop exit conditions.
  4. sentinel path excluded from dropped-line accounting.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest: `15 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 03:35 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 graves v2):
  1. rescan dialog cancel-close contract hardened.
  2. rescan worker active/stale/cap metadata handling hardened.
  3. stream wrapper dropped-line warning cadence and sentinel accounting hardened.
  4. focused regressions updated for dialog/worker/wrapper guards.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest: `12 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 02:55 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 high-risk minimal fixes):
  1. dynamic GUI config path resolver + loader usage in `gui/gui_config.py`.
  2. runtime/env and explicit-path regressions in `tests/test_gui_main_configuration.py`.
  3. streamlit memory/view width fallback hardening in `dev_env/streamlit_app.py`.
  4. streamlit snapshot clear idempotent guard + regressions in `tests/test_streamlit_filter_cache.py`.
  5. closeEvent rescan defensive shutdown hardening in `gui/gui_ssa.py` with regression in `tests/test_gui_filter_logic.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - focused `pytest`: `150 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 02:05 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (5 high-risk minimal slices):
  1. `gui/gui_ssa.py`: closeEvent rescan retention cap/meta hardening.
  2. `tests/test_gui_filter_logic.py`: regressions for rescan cap/meta + canonical candidates with non-null cache.
  3. `tests/test_gui_main_configuration.py`: regression for missing `SSA_CONFIG_DIR` fallback.
  4. `dev_env/streamlit_app.py`: unified API snapshot clear helper.
  5. `tests/test_streamlit_filter_cache.py`: regression for API snapshot clear helper.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - focused `pytest`: `145 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 01:10 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered in requested order:
  1. item 2 first: width-profile memory by width bucket in `dev_env/streamlit_app.py`.
  2. item 1 after: tabs/API smoke hardening (`MAIN_TAB_LABELS` + `_api_snapshot_available`).
- Focused tests added:
  - width bucket thresholds
  - width-profile memory normalize/resolve/remember
  - tab labels stability
  - API snapshot permutations
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: `21 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` on touched files: clean
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 00:18 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered:
  1. telemetry profile window cap in `dev_env/streamlit_app.py` to bound `streamlit_render_stats` growth.
  2. focused regression added in `tests/test_streamlit_filter_cache.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched streamlit files: pass
  - focused streamlit pytest: `16 passed`
- Queue status:
  1. no immediate `pending` rows in matrix.
  2. streamlit deferred queue remains the next track.
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-28 00:00 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest package delivered:
  1. config hierarchy alignment in `gui/gui_config.py`:
     - `gui_main_preferences.json` now resolves with `SSA_CONFIG_DIR` (safe fallback kept).
  2. rescan lifecycle hardening in `gui/gui_ssa.py::closeEvent`:
     - defensive global retention fallback added for active rescan worker in shutdown edge cases.
  3. focused regressions added:
     - `tests/test_gui_main_configuration.py` (`SSA_CONFIG_DIR` coverage)
     - `tests/test_gui_filter_logic.py` (intermittent `isRunning()` failure during close)
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - focused `pytest` on touched flows: pass
- Current pending queue:
  1. no immediate `pending` in matrix.
  2. streamlit stabilization queue remains separate.
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-27 16:32 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Residual main/config/gui queue closeout:
  1. `39, 46, 49, 50, 70, 76` moved to `resolved` in `docs/PENDING_ACTION_MATRIX.md`.
  2. Closure evidence comes from validated runtime/test slices already applied:
     - rescan closeEvent shutdown and deterministic active-ref cleanup;
     - global worker retention/prune consistency using lock snapshot;
     - cancel contract coverage in importer and extractor paths.
- Current pending queue:
  1. no immediate `pending` in this matrix.
  2. streamlit stabilization queue remains separate.
  3. `9` moved to `deferred` by explicit user decision (Opcao A).
- Additional closure in this cycle:
  1. `27` resolved by locking `finish` payload contract in `tests/test_import_cancellation.py`.
  2. `22/23` resolved in `tests/test_database_optimized_alias_views.py`.
  3. `21` resolved via existing concurrent-write test coverage in `tests/test_caching_atomic_save.py`.
  4. `24/25` resolved via current lock/modal regression tests.
  5. `9` deferred by explicit user decision (Opcao A), no runtime patch.
- Operational note:
  - this block is now the source of truth for continuation.
  - blocks below remain historical record.

## CURRENT TRUTH 2026-02-27 15:53 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Most recent state from interrupted chat:
  1. Local patch exists and is not committed yet.
  2. Touched runtime files:
     - `gui/ssa/gui_filters_advanced_ui.py`
     - `gui/mixins/filter_gui_ssa_mixin.py`
     - `gui/widgets/column_manager_dialog.py`
     - `gui/gui_ssa.py`
     - `gui/ssa/gui_workers.py`
  3. Functional deltas captured:
     - advanced action buttons sizing/container adjustments;
     - deterministic/deduplicated add-column menu composition;
     - explicit `available_columns` respected in column manager dialog;
     - non-null column cache computed on load and consumed by canonical candidate provider.
- Validation status:
  - interrupted patch validation rerun completed:
    - `uv run python -m py_compile` on touched runtime files: pass
    - `uv run ruff check` on touched runtime files: pass
    - `uv run ty check` on touched runtime files: pass
    - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`:
      - `121 passed, 1 skipped`
    - kluster auto on touched runtime files: clean
- Operational note:
  - blocks below are historical record and must not override this top block.

## CURRENT TRUTH 2026-02-26 21:40 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Most recent delivered slice:
  1. Added synchronized lower-panel height lock across:
     - details
     - advanced filters
     - column filters
  2. Bound sync to init/tab-change/resize/rebuild events.
  3. Applied deferred queue call on bind/tab paths to avoid layout thrash.
  4. Added regression test for equal min/max lower-panel heights after resize.
  5. Code evidence:
     - `gui/gui_ssa.py`: synchronized lower-panel height methods + init/tab/resize hooks
     - `gui/mixins/tab_context_gui_ssa_mixin.py`: deferred queue sync in bind
     - `gui/mixins/filter_gui_ssa_mixin.py`: rebuild hook for sync
     - `tests/test_gui_filter_logic.py`: regression lock for equal heights
- Validation evidence:
  - `python -m py_compile` pass
  - `ruff check` pass
  - `ty check` pass
  - `uv run pytest -q` => `582 passed, 6 skipped, 11 subtests passed`
- Operational note:
  - blocks below are historical record and must not override this top block.

## CURRENT TRUTH 2026-02-26 17:05 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Most recent delivered slice:
  1. MD audit rerun for active docs, preserving historical docs by design.
  2. Filter clear flows now keep unified status format:
     - `Status: SSAs filtradas: N de M`.
  3. SSA tab column-filter footer buttons now share same theme style.
- Validation evidence:
  - `python -m py_compile` pass (touched scope)
  - `ruff check` pass (touched scope)
  - `ty check` pass (touched scope)
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
    => `117 passed, 1 skipped`
- Operational note:
  - older sections below are historical record only.

## CURRENT TRUTH 2026-02-26 14:07 - authoritative block

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Most recent delivered slice:
  - new regression tests for column filters in `tests/test_gui_filter_logic.py`;
  - focus points: add-column menu candidates, clear-all defaults reset, Apply/Hide controls presence.
- Current validation evidence (latest run):
  - `python -m py_compile tests/test_gui_filter_logic.py` pass
  - `ruff check tests/test_gui_filter_logic.py` pass
  - `ty check tests/test_gui_filter_logic.py` pass
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py` pass (`97 passed, 1 skipped`)
  - `.venv/bin/python -m pytest -q tests/test_gui_main_configuration.py` pass
  - `.venv/bin/python -m pytest -q tests/test_display.py tests/test_streamlit_filter_cache.py` pass
- Operational rule:
  - references to `codex/import-review` and `PR #31` below are historical audit only.
  - do not use those sections as active execution source.

## Update 2026-02-26 (status real apos sprints A B C)

- Branch ativa: `codex/dev-filtros-stability`.
- Sprints fechados nesta rodada:
  - Sprint A: extractor contract/test closure (`ids 6,7,33,34,35,58`).
  - Sprint B: rescan worker/dialog closure (`ids 11,12,28,29,38,79`; id 71 stale-doc).
  - Sprint C: cli enhancement lock closure (`ids 13,26,30,31,41,80`).
  - E: pytest ignores removidos em `pyproject.toml` e arquivos script-like de teste convertidos para formato pytest deterministico.
- Regras mantidas:
  - patch minimo, sem refactor amplo fora do escopo;
  - sem mudanca estrutural de GUI fora do aprovado;
  - validacao focada por slice (`py_compile`, `ruff`, `ty`, `pytest` focado).
- Proximo foco recomendado:
  - grupo main/config/gui residual (`39, 42, 43, 44, 46, 49, 50, 70, 76`) antes de itens cosmeticos.

## Update 2026-02-26 (deep analysis consolidation)

- Deep gate summary:
  - pass: `py_compile`, `ruff`, `ty`.
  - fail baseline: `flake8`, `mypy` (legacy debt; not release blocker for this cycle).
  - `pylama` unavailable in current env (`pkg_resources` missing); no dependency change applied.
- Kluster manual summary:
  - high-priority actionable now: stream scripts (`scripts/run_pytest_stream_and_log.py` and `_v2.py`) for path handling and output perf behavior.
  - medium structural items (main/config/gui) remain tracked; keep out of broad refactor in this sprint.
- Execution order (next cycle):
  1. Stream scripts security/perf mini-slice (delivered in this cycle).
  2. Batch 11 resilience lock (delivered in this cycle).
  3. Main/config/gui residual group + streamlit stabilization queue.

## Update 2026-02-26 (batch11 resilience lock delivered)

- `main.py` updated to keep deterministic performance default:
  - optimized import failure logs full context and fails fast by default;
  - no automatic legacy retry path (including `--force-rescan`).
- `tests/test_main_import_fallback.py` now covers:
  - fail-fast without retry on optimized import runtime failure.
- Validation lock:
  - `py_compile`, `ruff`, `ty` on touched files: pass.
  - `uv run pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py`: pass.

## Update 2026-02-26 (config restore fallback lock)

- Added focused regression lock in `tests/test_config_manager_mappings_integrity.py`:
  - display mapping restore-write failure path returns defaults without crash;
  - column mapping restore-write failure path returns defaults without crash.
- Validation lock:
  - `py_compile`, `ruff`, `ty` on touched files: pass.
  - `uv run pytest -q tests/test_config_manager_mappings_integrity.py`: pass (`4 passed`).

## Update 2026-02-26 (stream scripts security/perf delivered)

- Added `scripts/pytest_stream_common.py` to centralize stream wrappers runtime logic.
- Hardened `--log` path handling through shared safe resolver.
- Reduced flush overhead by batch flush policy.
- Non-blocking sentinel delivery path now uses best-effort queue + reader_done signal.
- Focused validation lock added: `tests/test_stream_log_wrapper_guards.py`.

## Estado atual

- OVERRIDE 2026-02-24 (estado valido para proxima conversa):
  - Branch atual de trabalho: `codex/dev-filtros-stability` (base `origin/dev`).
  - Commits recentes deste ciclo:
    - `1c56addb` fix(gui): stabilize advanced filters responsive grid and action buttons.
    - `06633471` fix(cli,db): harden config flow and maintenance schema targets.
    - `4adcf35b` fix(extracao): resolve tempo_excedido `m` ambiguity and lock with focused tests.
    - `resolved` fix(maintenance): avoid VACUUM-in-transaction and add script regression tests.
    - `resolved` test(db): add schema_manager identifier guard regression lock.
    - `resolved` fix(maintenance): harden analyze_db_integrity for empty-table and report consistency.
    - `resolved` perf(maintenance): refactor verify_database_integrity query flow.
    - `resolved` fix(cli): guard direct SSA search when `numero_ssa` column is missing.
  - Scope atual:
    - estabilizacao de filtros avancados (resize/layout de grid e botoes internos);
    - hardening pontual CLI/schema/scripts de manutencao;
    - sem refactor amplo.
  - Validacao recente:
    - `py_compile`, `ruff`, `ty` em arquivos tocados: ok;
    - `uv run pytest` focado:
      - `tests/test_gui_filter_logic.py` (casos de resize): pass;
      - suites focadas de CLI/config/schema/db: pass.
      - `tests/test_extracao.py` (tempo_excedido parser): pass.
      - `tests/test_scripts_manutencao_schema_targets.py`: pass.
      - `tests/test_schema_manager_identifier_guards.py`: pass.
      - `tests/test_scripts_manutencao_schema_targets.py` (analyze_db_integrity + duplicate-count): pass.
      - `tests/test_cli_loop_missing_numero_ssa_guard.py`: pass.
  - Registro de controle obrigatorio:
    - `docs/RECOVERY_BACKLOG.md` atualizado com triagem kluster e itens deferidos.
    - `docs/NEXT_CHAT_MIGRATION.md` sincronizado com este branch/scope (override 2026-02-24).
    - controle de diario mantido em 3 arquivos: `AGENTS_HANDOFF_NEXT_CYCLE.md`, `RECOVERY_BACKLOG.md`, `NEXT_CHAT_MIGRATION.md`.
  - Triagem pendencias:
    - long-list consolidada em `RECOVERY_BACKLOG.md` (secao "Pendencias longas");
    - itens que exigem sprint exclusivo em `RECOVERY_BACKLOG.md` (secao "Pendencias para sprint exclusivo").
- Nota operacional:
  - Nao fechar branch antigo por automacao; encerramento de branch fica com o usuario.

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
  - Demais checks principais em `pass` (DeepScan, DeepSource, submit-pypi, GitGuardian, Socket, semgrep, cubic).

## Update 2026-02-19 (fix critico de geometria na aba Filtros)

- Commit: `d3d9410f` (head atual).
- Problema corrigido:
  - painel inferior (`Detalhes da SSA Selecionada` + `Filtros Avancados`) podia avancar na area da lista de SSAs em cenarios com poucas linhas apos filtro.
- Patch minimo aplicado em `gui/gui_ssa.py`:
  - `table_widget.setMinimumHeight(220)`;
  - `tab_layout.addWidget(table_widget, 6)`;
  - `tab_layout.addLayout(bottom_layout, 4)`.
- Regressao adicionada:
  - `tests/test_gui_filter_logic.py::test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows`.
- Evidencia de validacao local:
  - gate de arquivos tocados passou (`py_compile`, `ruff`, `ty`);
  - testes focados passaram (`gui_filter_logic` e suites de `advanced_filters`);
  - checagem de matriz de runtime (alturas 780/860/991/1080 x linhas 1/3/10/200) sem sobreposicao.
- Estado de checks apos push:
  - `code/snyk` e `security/snyk` seguem como bloqueio externo conhecido (limite de plano);
  - demais checks em execucao/fila no momento do snapshot.

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

1. Sem acentos/cedilha/emojis/emdash em codigo, docs e mensagens tecnicas.
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

## Update 2026-02-18 (dialogo detalhes derivadas)

- Causa raiz de regressao visual identificada:
  - proporcao no `QHBoxLayout` nao garantia largura real quando havia `minimumWidth` alto no painel esquerdo.
- Estado corrigido no codigo:
  - `gui/ssa/gui_details.py` usa `QSplitter` com `setSizes` e `setStretchFactor`.
  - proporcao atual: `20/80` (esquerda/direita).
  - tamanho minimo atual do dialogo: largura `700`, altura `650`.
  - fontes: painel esquerdo `12`, conteudo detalhes `12`, labels de campo `11`.
- Regra obrigatoria para proxima IA:
  1. Nao assumir resultado visual por leitura de ratio apenas.
  2. Sempre validar constraints reais (`minimumWidth`, `QSplitter/QLayout`, `setSizes`) antes de declarar pronto.
  3. Em cada ajuste visual, registrar causa raiz + valor final aplicado (arquivo:linha).

## Protocolo de comportamento para outra IA

1. Nao minimizar reclamacao de bug visual; tratar como regressao funcional ate reproduzir.
2. Nao declarar "corrigido" sem evidencia de antes/depois no mesmo fluxo reportado.
3. Nao esconder erro com fallback generico para "limpar log".
4. Sempre explicar causa raiz tecnica antes do patch.
5. Se existir ambiguidade de UI, confirmar valores finais numericos no proprio codigo.

## Texto pronto para abrir a nova conversa

```text
Contexto: branch de recovery foi mergeada; manter mesma disciplina de qualidade.

Regras de execucao:
1. Sem acentos/cedilha/emojis/emdash em codigo, docs e mensagens tecnicas.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: py_compile, ruff, pytest focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito (excecao ja aprovada: dialogo de detalhes de derivadas em `gui/ssa/gui_details.py` deve permanecer em 20/80).
6. Nao criar branch/PR novo sem autorizacao explicita.
7. Nao usar suppress/except vazio para esconder erro real.
8. Usar pip/pip3 para deps quando operar via uv.
9. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
10. Manter backlog de follow-up em docs/RECOVERY_BACKLOG.md.
11. Para ajustes visuais: validar `minimumWidth` e `QSplitter` antes de concluir que o ratio esta aplicado.

Objetivo do novo ciclo: manter o mesmo cuidado, mas com foco funcional novo.
Objetivo atual: fechar PR #31 com estabilidade, aplicar apenas patches minimos de risco real, e processar relatorios externos com validacao local obrigatoria.
```

## Pacote pronto completo (copiar e colar)

```text
Contexto atual:
- Repo: SSA_Consulta_Rapida
- Branch: codex/import-review
- PR: #31 (base dev)
- Estado checks: snyk code/security falham por limite de plano; resto majoritariamente verde

Escopo aprovado:
1) Patches minimos e atomicos.
2) Sem branch nova, sem PR novo.
3) Sem refactor amplo fora de risco real.
4) Sem alterar layout GUI, exceto dialogo de detalhes derivadas ja aprovado.

Baseline visual obrigatoria (nao mudar sem pedido):
- Arquivo: gui/ssa/gui_details.py
- Split real: 20/80 (esquerda/direita)
- Min dialog: 700x650
- Fonte esquerda: 12
- Fonte conteudo detalhes: 12
- Fonte labels: 11
- Implementacao: QSplitter + setSizes + stretch factors

Regras de comportamento obrigatorias:
1) Nao minimizar bug visual reportado pelo usuario.
2) Nao declarar corrigido sem repro antes/depois no mesmo fluxo.
3) Nao esconder erro real com fallback generico.
4) Nao assumir efeito visual por constante; validar constraints reais de layout.
5) Sempre reportar valores finais numericos (ratio, size, font).
6) Ler os docs obrigatorios antes de qualquer patch.

Leitura obrigatoria inicial (ordem):
1) docs/AGENTS_HANDOFF_NEXT_CYCLE.md
2) docs/NEXT_CHAT_MIGRATION.md
3) docs/RECOVERY_BACKLOG.md
4) docs/QA_FACADE_FILTERS.md
5) AGENTS.md (regras locais da sessao)

Ciclo minimo por slice (nao pular):
1) diagnostico com evidencia (rg -n + nl -ba + repro)
2) plano curto + diff previsto
3) patch minimo
4) gate tecnico local
5) commit atomico
6) push
7) checagem de PR checks
8) registrar pendencia nao bloqueante no backlog

Cuidados de seguranca e higiene:
1) Nao comitar arquivos locais/sensiveis (`.envrc`, `.python-version`, `config/secret_key`, db local fora do escopo).
2) Nao usar comandos destrutivos (`git reset --hard`, checkout destrutivo).
3) Nao introduzir suppress/except vazio.
4) Nao mascarar falha funcional com fallback silencioso.
5) Em duvida de escopo: perguntar antes de mexer.

Gate tecnico por slice:
- uv run python -m py_compile <files>
- uv run ruff check <files>
- uv run ty check <files>
- uv run pytest -q <focados>

Se tocar gui/gui_ssa.py ou gui/ssa/gui_filters_*:
- uv run pytest -q tests/test_gui_filters_facade_contract.py
- uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
- uv run pytest -q tests/test_gui_filters_advanced_logic.py

Entregavel de cada slice:
1) evidencia arquivo:linha
2) patch minimo
3) gate local
4) commit atomico
5) push
6) status checks PR
```

## Snapshot final para migracao (2026-02-18)

- Branch: `codex/import-review`
- PR: `#31`
- Head commit no momento: `250fc32c`
- Sequencia recente relevante:
  1. `250fc32c` docs(migration): finalize ready-to-migrate snapshot and strict starters
  2. `aa454a40` docs(handoff): expand next-chat package and strict execution rules
  3. `80a73363` fix(gui-details,docs): set 20/80 split and prepare strict next-chat handoff
- Bloqueio externo conhecido:
  - `code/snyk` e `security/snyk` por limite de plano.

## Update 2026-02-24 (gui invalid regex fallback guard)

- `resolved` fix(gui-filters): malformed regex fallback em `_build_column_mask` agora usa caminho literal com `regex=False`.
- `resolved` test(gui-filters): add `tests/test_filter_regex_invalid_fallback.py` para lock de regressao nos dois caminhos (`~token` e modo default `regex`).
- gate local deste slice:
  - `python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_filter_regex_invalid_fallback.py`: pass.
  - `ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_filter_regex_invalid_fallback.py`: pass.
  - `ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_filter_regex_invalid_fallback.py`: pass.
  - `uv run pytest -q tests/test_filter_regex_invalid_fallback.py`: pass.

## Update 2026-02-24 (cli remove-filter non-lifo guard)

- `resolved` fix(cli): `_handle_remove_filter` corrige remocao fora de ordem reaplicando do estado base.
- `resolved` perf(cli): remocao LIFO continua usando estado anterior para evitar custo desnecessario.
- `resolved` test(cli): add `tests/test_cli_remove_filter_non_lifo.py` cobrindo ambos os caminhos.
- gate local deste slice:
  - `python -m py_compile interface/cli.py tests/test_cli_remove_filter_non_lifo.py`: pass.
  - `ruff check interface/cli.py tests/test_cli_remove_filter_non_lifo.py`: pass.
  - `ty check interface/cli.py tests/test_cli_remove_filter_non_lifo.py`: pass.
  - `uv run pytest -q tests/test_cli_remove_filter_non_lifo.py`: pass.

## Nova regra 2026-02-24 (error-handling e performance)

- Tratamento de erro deve existir, mas por bloco funcional relevante, nao a cada poucas linhas.
- Evitar excesso de condicionais e `try/except` fragmentado que reduz legibilidade e custo de manutencao.
- Proibido `try/except` vazio e proibido esconder falha real.
- Cada tratamento deve ter saida clara: log objetivo e retorno/acao coerente com o fluxo.
- Em qualquer fix, validar que a solucao nao cria custo alto desnecessario (reprocessamento amplo, loops redundantes, fallback caro).

## Update 2026-02-24 (cli config refresh and query guard)

- `resolved` fix(cli): comando `c/config` agora usa refresh unico (sem duplicacao de bloco no loop).
- `resolved` perf(cli): requery da base ocorre apenas se `default_filters` mudou.
- `resolved` security(cli): `get_ssa_query` aplica allowlist para tabela canonica e aliases legados.
- `resolved` tests(cli):
  - `tests/test_cli_config_preserve_session.py` (2 cenarios: reload condicional e skip requery);
  - `tests/test_cli_get_ssa_query_identifier_guard.py`.
- gate local deste slice:
  - `python -m py_compile interface/cli.py tests/test_cli_config_preserve_session.py tests/test_cli_get_ssa_query_identifier_guard.py`: pass.
  - `ruff check interface/cli.py tests/test_cli_config_preserve_session.py tests/test_cli_get_ssa_query_identifier_guard.py`: pass.
  - `ty check interface/cli.py tests/test_cli_config_preserve_session.py tests/test_cli_get_ssa_query_identifier_guard.py`: pass.
  - `uv run pytest -q tests/test_cli_config_preserve_session.py tests/test_cli_get_ssa_query_identifier_guard.py`: pass.

## Update 2026-02-24 (cli clearall table consistency)

- `resolved` fix(cli): `_handle_clear_all_filters` now uses `get_ssa_query(table_name)`.
- `resolved` test(cli): add `tests/test_cli_clearall_uses_table_name.py`.
- gate local deste slice:
  - `python -m py_compile interface/cli.py tests/test_cli_clearall_uses_table_name.py`: pass.
  - `ruff check interface/cli.py tests/test_cli_clearall_uses_table_name.py`: pass.
  - `ty check interface/cli.py tests/test_cli_clearall_uses_table_name.py`: pass.
  - `uv run pytest -q tests/test_cli_clearall_uses_table_name.py`: pass.

## Update 2026-02-24 (cli pagination tracker prune)

- `resolved` fix(cli): prune orphan pagination entries after stack mutations.
- `resolved` quality(cli): local manager class now centralizes tracker state operations.
- `resolved` stability(cli): tracker key persisted in `df.attrs` to preserve state in dataframe copies.
- `resolved` test(cli): add/expand `tests/test_cli_pagination_tracker_prune.py`.
- gate local deste slice:
  - `python -m py_compile interface/cli.py tests/test_cli_pagination_tracker_prune.py`: pass.
  - `ruff check interface/cli.py tests/test_cli_pagination_tracker_prune.py`: pass.
  - `ty check interface/cli.py tests/test_cli_pagination_tracker_prune.py`: pass.
  - `uv run pytest -q tests/test_cli_pagination_tracker_prune.py`: pass (3 tests).

## Update 2026-02-24 (cli enhancement settings lock and root)

- `resolved` fix(cli): `_save_settings` keeps lock in lockfile write path (tempfile lock removed).
- `resolved` safety(cli): when lock acquisition fails, save aborts (no unlocked write).
- `resolved` quality(cli): module root resolution switched to `_get_project_root()`.
- `resolved` quality(cli): module logger switched to robust logger API.
- `resolved` test(cli): update/add `tests/test_cli_enhancement_manager_lock_usage.py`.
- gate local deste slice:
  - `python -m py_compile interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass.
  - `ruff check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass.
  - `ty check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass.
  - `uv run pytest -q tests/test_cli_enhancement_manager_lock_usage.py`: pass.

## Update 2026-02-24 (command handlers root-safe mappings cache)

- `resolved` fix(cli): mapping file path no longer depends on cwd.
- `resolved` quality(cli): command handlers logger now uses robust logger API.
- `resolved` perf(cli): mapping cache now uses dedicated in-module manager.
- `resolved` test(cli): add `tests/test_command_handlers_project_root_mapping.py`.
- gate local deste slice:
  - `python -m py_compile interface/command_handlers.py tests/test_command_handlers_project_root_mapping.py`: pass.
  - `ruff check interface/command_handlers.py tests/test_command_handlers_project_root_mapping.py`: pass.
  - `ty check interface/command_handlers.py tests/test_command_handlers_project_root_mapping.py`: pass.
  - `uv run pytest -q tests/test_command_handlers_project_root_mapping.py`: pass.

## Update 2026-02-24 (command handlers save flow cleanup)

- `resolved` quality(cli): repeated `try/except ... pass` save blocks replaced by `_attempt_save_settings(...)`.
- `resolved` behavior(cli): save error feedback/log remains centralized and menu flow preserved.
- `resolved` semantics(cli): helper now returns explicit boolean success/failure.
- `resolved` consistency(cli): menu changes now rollback when save fails.
- gate local deste slice:
  - `python -m py_compile interface/command_handlers.py`: pass.
  - `ruff check interface/command_handlers.py`: pass.
  - `ty check interface/command_handlers.py`: pass.
  - `uv run pytest -q tests/test_command_handlers_project_root_mapping.py`: pass.

## Update 2026-02-24 (optimized upsert legacy decimal key normalization)

- `resolved` fix(db-optimized): lookup now checks canonical and legacy decimal SSA variants (`value` and `value.0`).
- `resolved` fix(db-optimized): update delete-set now removes legacy decimal keys and canonical key before reinserting normalized row.
- `resolved` fix(db-optimized): replaced `to_sql` under savepoint in update branch with parameterized `executemany` to keep transaction semantics stable.
- `resolved` test(db-optimized): `tests/test_database_optimized_alias_views.py::test_optimized_upsert_replaces_legacy_decimal_key_without_duplicate`.
- `deferred` quality(P4): function-size/god-function concern in `insert_dataframe_optimized` intentionally left for exclusive refactor sprint.

## Update 2026-02-24 (canonical write policy for optimized upsert)

- `resolved` policy: canonical write is mandatory; no runtime legacy `*.0` lookup compatibility in optimized path.
- `resolved` validation: write flow now fails fast if normalized storage ids still contain decimal artifacts.
- `decision` operational: legacy data handling in this cycle should use controlled DB reset/migration.

## Update 2026-02-24 (canonical write policy in standard upsert path)

- `resolved` parity: non-optimized upsert now follows same canonical write rule used in optimized path.
- `resolved` validation: standard path rejects decimal artifacts in storage ids after normalization.
- `resolved` test: add dedicated regression for non-optimized canonical write persistence.

## Update 2026-02-24 (upsert chunk dedupe perf)

- `resolved` perf(upsert): removed O(n2) duplicate-key scan per chunk in standard upsert path.
- `resolved` regression: duplicate `numero_ssa` in same import chunk remains functionally correct.
- `scope` patch-minimo: no broad refactor in `_perform_upsert`.

## Update 2026-02-24 (prepare_dataframe_for_upsert copy-path perf)

- `resolved` perf(upsert): lighter dataframe copy path in `prepare_dataframe_for_upsert`.
- `resolved` regression: input immutability and canonical/date normalization output covered by focused test.

## Update 2026-02-24 (logging mapping interpolation and ops note)

- `resolved` semantic(logging): `_ASCIIOnlyFilter` now preserves mapping args used by named interpolation.
- `resolved` parity(logging): same fix in main and streamlit entrypoints.
- `ops-note` legacy reset: DB reset for legacy decimal artifacts remains controlled operational step; runtime code enforces canonical write only.

## Update 2026-02-24 (streamlit cache fallback parity)

- `resolved` stability(streamlit): compatibility cache methods now use the same backend selection logic as primary cache methods.
- `resolved` behavior parity: local fallback mode now tracks hits/misses/evictions correctly.
- `scope` patch-minimo: no UI/layout or filter semantics change.

## Update 2026-02-24 (streamlit filter guards)

- `resolved` stability(streamlit): no KeyError when optional filter columns are absent.
- `resolved` perf/ux(streamlit): removed per-miss `st.info` in hot filter path; now logs via logger.
- `scope` patch-minimo: no GUI layout/position changes.

## Update 2026-02-24 (streamlit import ui unblock)

- `resolved` perf/ux(streamlit): removed forced 0.5s delay at end of import action.
- `scope` patch-minimo: same import behavior, faster UI return.

## Update 2026-02-24 (streamlit broad hardening cycle)

- `resolved` resilience(streamlit): module now imports safely even when streamlit package is absent.
- `resolved` consistency(cache): backend selection logic is centralized and reused in all cache methods.
- `resolved` correctness(cache): keying now accepts lightweight dataframe token to reduce stale cache collisions.
- `resolved` maintenance: removed deprecated pandas CoW setting.
- `resolved` tests: new focused coverage for fallback cache backend and token behavior.

## Update 2026-02-24 (streamlit long cycle)

- `resolved` layout(streamlit): tabs introduced and table positioning updated with dedicated pagination controls.
- `resolved` ops(streamlit): API fetch is now manual/on-demand and snapshot-based.
- `resolved` stability(streamlit): safe import fallback when streamlit is unavailable + stronger runtime detection.
- `resolved` perf(cache): key token memoization + backend resolver reuse.
- `resolved` tests: extended streamlit cache helper coverage.

## Update 2026-02-24 (streamlit long cycle v2)

- `resolved` UX/perf(streamlit): filters now use form submit/reset (on-demand apply).
- `resolved` perf(streamlit): full multiselect selection collapses to no-op filter.
- `resolved` layout(streamlit): table toolbar expanded with sorting + paged controls.
- `resolved` stability(streamlit): rerun compatibility fallback for older streamlit APIs.
- `resolved` tests: streamlit helper coverage expanded for mixed types and filter normalization.

## Update 2026-02-24 (streamlit long cycle v3)

- `resolved` logic(streamlit): fixed table-tab flow so table rendering is no longer nested under `consult_api`.
- `resolved` layout(streamlit): table controls reorganized in two rows; width profile selector added.
- `resolved` perf/usability(streamlit): `SimpleWidthManager` now drives table `column_config` through `_build_streamlit_column_config(...)`.
- `resolved` stability(streamlit): safe fallback when `st.column_config` is unavailable.
- `resolved` tests: `tests/test_streamlit_filter_cache.py` expanded for width bucket and column-config behavior.

## Update 2026-02-24 (streamlit long cycle v4)

- `resolved` security(streamlit): sidebar paths now validated with `ensure_path_is_allowed` (`db_path` and `docs_dir`), with explicit stop on invalid path.
- `resolved` stability(cache-token): `_compute_df_cache_token` now handles DataFrame with zero columns before sample-column access.
- `resolved` width-manager rule alignment:
  - `SimpleWidthManager` now exposes `compute_streamlit_width_buckets(...)` with explicit priority for `descricao_ssa`/`descricao_execucao`.
  - `compute_optimal_widths` contract simplified to deterministic inputs only.
  - `gui/ssa/gui_table.py` updated to new `compute_optimal_widths` signature.
- `resolved` tests: `tests/test_streamlit_filter_cache.py` expanded and now passing with 11 tests.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - multiple re-check cycles in this slice; final `kluster_code_review_auto`: clean (no issues).

## Update 2026-02-24 (streamlit long cycle v5 final alignment)

- `resolved` width-manager contract: `compute_optimal_widths` voltou a assinatura deterministica minima (sem parametros externos de override).
- `resolved` compatibility call site: `gui/ssa/gui_table.py` alinhado ao contrato final.
- `resolved` compliance: final `kluster_code_review_auto` clean.

## Update 2026-02-25 (streamlit long cycle v6 layout expansion)

- `resolved` layout(filters): form reorganized in visual blocks (`Busca e origem`, `Selecao de filtros`, `Colunas e presets`).
- `resolved` layout(table): metrics compacted into top cards; controls split in primary/secondary toolbars.
- `resolved` layout(table): added `Visualizacao` mode (`Tabela` or `Tabela + grafico`) persisted in session state.
- `resolved` layout(export): reorganized into two panels (`Arquivos` and `Geracao e resumo`).
- `resolved` layout(ops): cache/API sections split in two columns with cleaner action placement.
- `scope` no business-rule changes in filtering logic.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Update 2026-02-25 (streamlit long cycle v7 compact mode + render telemetry)

- `resolved` layout(table): added `Compacto` mode in table toolbar to reduce on-screen noise.
- `resolved` usability(table): compact mode uses shorter runtime caption and hides verbose helper text.
- `resolved` perf-observability(streamlit): lightweight render telemetry for dataframe (last and average ms per width profile) stored in `session_state`.
- `scope` no filter business-rule change.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Update 2026-02-25 (streamlit long cycle v7.1 local decoupling)

- `resolved` maintainability(streamlit): extracted `_update_render_telemetry(...)` and `_build_table_caption(...)` from table block.
- `resolved` quality: reduced inline responsibility in `with tab_table` without changing behavior.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Update 2026-02-25 (streamlit import bootstrap fix for direct python run)

- `resolved` startup(streamlit): fixed `ModuleNotFoundError: core` when running `python dev_env/streamlit_app.py` directly.
- implementation detail:
  - added `_get_project_root()` helper;
  - ensured project root is added to `sys.path` before loading app modules;
  - switched app module loading to `importlib.import_module(...)` for stable direct-run bootstrap.
- validation:
  - direct run command now exits without import error.

## Update 2026-02-25 (streamlit test coverage expansion)

- `resolved` tests(streamlit): added focused coverage for table caption modes and render telemetry state updates.
- updated file: `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check tests/test_streamlit_filter_cache.py`: pass.
  - `ty check tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (14 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Update 2026-02-25 (streamlit telemetry panel refinement)

- `resolved` ops(streamlit): cache panel now supports telemetry profile selection and explicit telemetry clear action.
- `resolved` maintainability: extracted `_format_render_stats_line(...)` helper to keep ops block smaller.
- `resolved` tests: added focused assertion for telemetry line formatting.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (15 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Update 2026-02-25 (qwen delegation config + batch01 ids 21-23)

- `resolved` process: added dedicated qwen delegation config in `docs/QWEN_CODE_DELEGATION_CONFIG.md`.
- `resolved` tests(batch01):
  - id 21: added concurrent atomic-write test in `tests/test_caching_atomic_save.py`.
  - ids 22-23: schema precondition clarity + explicit db cleanup in `tests/test_database_optimized_alias_views.py`.
- gate local deste slice:
  - `python -m py_compile tests/test_caching_atomic_save.py tests/test_database_optimized_alias_views.py`: pass.
  - `ruff check tests/test_caching_atomic_save.py tests/test_database_optimized_alias_views.py`: pass.
  - `ty check tests/test_caching_atomic_save.py tests/test_database_optimized_alias_views.py`: pass.
  - `uv run pytest -q tests/test_caching_atomic_save.py tests/test_database_optimized_alias_views.py`: pass (5 tests).
- kluster:
  - final `kluster_code_review_auto`: clean.

## Update 2026-02-25 (batch01 ids 24/25/27/28/29 + qwen delegation)

- `resolved` batch01 tests:
  - id 24: stricter lock assertions in `tests/test_filter_cache_locking.py`.
  - id 25: less brittle patch target via module object in `tests/test_filter_error_skips_modal_in_pytest.py`.
  - id 27: finish payload assertions added in `tests/test_import_cancellation.py`.
  - id 28: post-cancel UI state assertions expanded in `tests/test_rescan_progress_dialog.py`.
  - id 29: success cleanup path added in `tests/test_rescan_worker_cleanup.py`.
- `resolved` qwen delegation in this slice:
  - qwen executed `ruff` and `ty` on the batch test set (`qwen -y ...`).
  - agent still performed final independent validation before commit gate.
- efficiency note (this slice):
  - qwen run (ruff+ty summary): ~44.4s wall-time end-to-end, very short output.
  - local direct gate remains lower latency; qwen is useful when bundling repeated triage/checklist tasks.
- gate local deste slice:
  - `python -m py_compile` on touched tests: pass.
  - `ruff check` on touched tests: pass.
  - `ty check` on touched tests: pass.
  - `uv run pytest -q` (batch tests): pass (9 tests).

## Update 2026-02-25 (extractor batch02 contract + robust primary path)

- `extracao/extractor.py`
  - `read_report` stabilized to always return `DataFrame` + `metadata`.
  - missing-file and fallback errors return empty DataFrame with explicit `stats_dict` error payload.
  - primary ingestion switched to `import_excel_robust`; compatibility fallback to legacy extractor only when robust output is empty.
- `tests/test_extracao.py`
  - added/updated regression for missing-file behavior to assert empty DataFrame + error metadata.
- gate local deste slice:
  - `python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  - `ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  - `ty check extracao/extractor.py tests/test_extracao.py`: pass.
  - `.venv/bin/python -m pytest -q tests/test_extracao.py`: pass (5 tests).
- kluster progression:
  - first run: 2 findings (P4 rule_3/rule_18).
  - second run: 1 finding (P4 rule_18).
  - third run: 2 findings (P3 Optional-return risk + P4 fallback clarification).
  - final run: clean.

## Update 2026-02-25 (extractor batch02 follow-up: robust-only + perf guard)

- `extracao/extractor.py`
  - `read_report` consolidado em ingestao robust-only (rule_18).
  - adicionado limite de custo para caminho de resultado vazio via `SSA_READ_REPORT_FALLBACK_MAX_MB` (default 8MB) com parse seguro de env invalido.
- `tests/test_extracao.py`
  - fixture e asserts alinhados ao contrato robust-only.
  - novos testes para limite de tamanho e env invalido.
- gate local:
  - `python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
  - `ruff check extracao/extractor.py tests/test_extracao.py`: pass.
  - `ty check extracao/extractor.py tests/test_extracao.py`: pass.
  - `.venv/bin/python -m pytest -q tests/test_extracao.py`: pass (7 tests).

## Update 2026-02-25 (extractor batch02 cleanup)

- cleanup aplicado apos revisao kluster:
  - removido guard de fallback por tamanho que ficou sem efeito apos consolidacao robust-only.
  - removidos testes associados ao guard descartado.
- contrato final deste ciclo:
  - `read_report` usa apenas `import_excel_robust` para ingestao.

## Update 2026-02-25 (config batch03 path alignment)

- `core/config_manager.py`
  - paths de settings/defaults em funcoes principais agora seguem `SSA_CONFIG_DIR` via `_resolve_config_path`.
  - validacao de seguranca adicionada em `_get_config_dir` usando `utils.path_safety.ensure_path_is_allowed`.
- `tests/test_config_manager_atomic_save.py`
  - atualizado para validar fluxo via env `SSA_CONFIG_DIR`.
- gate local:
  - `python -m py_compile core/config_manager.py tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: pass.
  - `ruff check` nos mesmos arquivos: pass.
  - `ty check` nos mesmos arquivos: pass.
  - `.venv/bin/python -m pytest -q tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: pass (5 tests).

## Update 2026-02-25 (config batch03 fail-fast)

- `core/config_manager.py`
  - `ensure_default_settings` passou para fail-fast agregado (erro consolidado no fim do ciclo de arquivos).
  - `_atomic_copy_file` nao segue com copia quando o `os.close` inicial falha.
  - logger do modulo migrado para `get_robust_logger().get_logger(__name__, "core")`.
- `tests/test_config_manager_atomic_save.py`
  - adicionados testes para garantir erro explicito em falha de copy e de generation no ensure.
- gate local:
  - `python -m py_compile core/config_manager.py tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: pass.
  - `ruff check` e `ty check` nos mesmos arquivos: pass.
  - `.venv/bin/python -m pytest -q tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: pass (7 tests).

## Update 2026-02-25 (config batch03 startup contract final)

- decisao final deste slice:
  - startup principal segue resiliente (`fail_fast=False` no `main`) com warning explicito e sem falha silenciosa.
  - helper de provisionamento preserva modo estrito (`fail_fast=True`) para uso dirigido.
- testes focados de config seguem verdes (7/7).

## Update 2026-02-25 (config batch03 final stabilization)

- fechamento do slice:
  - atomic copy simplificado com `NamedTemporaryFile` para manter operacao atomica sem caminho ambiguo de fd.
  - startup continua resiliente e observavel (warnings explicitos no `main` quando ensure retorna erros).
- gate final do slice: ruff/ty/py_compile ok + pytest config 7/7.

## Update 2026-02-25 (batch04 lock retry hardening)

- `interface/cli_enhancement_manager.py`
  - lock de escrita com retry limitado e nao bloqueante (sem travamento indefinido).
  - lock file em modo `a+`.
- `tests/test_cli_enhancement_manager_lock_usage.py`
  - novos testes de retry (busy->success e busy->fail).
- gate local deste slice:
  - py_compile/ruff/ty: pass.
  - pytest lock+atomic CLI enhancement: 7 passed.

## Update 2026-02-25 (batch04 windows lock retries)

- `interface/cli_enhancement_manager.py`
  - lock do backend Windows endurecido: `LK_NBLCK` + retry limitado.
  - retries restritos a erros de contencao; erro critico nao fica em loop.
- `tests/test_cli_enhancement_manager_lock_usage.py`
  - novos testes do caminho Windows (busy e erro critico).
- processo:
  - qwen executou checks repetitivos (ruff/ty/pytest); validacao final tambem executada diretamente pelo agente.

## Update 2026-02-25 (batch04 windows lock region normalization)

- `interface/cli_enhancement_manager.py`
  - lock Windows em byte unico (`len=1`) e `seek(0)` antes de lock.
  - fail-fast imediato para erro nao relacionado a lock contention.
- `tests/test_cli_enhancement_manager_lock_usage.py`
  - assert adicional para `lock_len == 1` no caminho Windows com retry.
- processo:
  - qwen executou checks repetitivos neste slice;
  - validacao final foi confirmada novamente com ruff/ty/pytest pelo agente principal.

## Update 2026-02-26 (batch05+06 semantic and db safety)

- arquivos alterados:
  - `core/app_logic.py`
    - erro inesperado em `_import_single_file` agora registra tipo original no log/mensagem (`<ErrorType> ao importar ...`) mantendo raise encadeado.
  - `armazenamento/database_optimized.py`
    - adicionado helper de quote estrito para identificador validado.
    - SQL dinamico para tabela alvo e PRAGMA de FK passou a usar identificador quoted validado.
  - `tests/test_database_optimized_identifier_guards.py`
    - novo teste para tabela invalida no insert otimizado.
  - `tests/test_command_handlers_save_settings.py`
    - ajuste de expectativa stale: quando save falha, toggle de visibilidade e desfeito.
- docs sincronizados:
  - `docs/PENDING_ACTION_MATRIX.md` (ids batch05/06 marcados como resolved/stale-doc com evidencia curta).
  - `docs/RECOVERY_BACKLOG.md` (update do ciclo adicionado).
- gate local do slice:
  - `py_compile` (arquivos tocados): pass.
  - `ruff check` (arquivos tocados): pass.
  - `ty check` (arquivos tocados): pass.
  - `pytest -q` focado: 16 passed.
- processo:
  - qwen usado para triagem/checklist rapido;
  - patch e validacao final executados pelo agente principal.

## Update 2026-02-26 (batch07.1 cache/config sync)

- arquivos alterados:
  - `tests/test_caching.py`
    - novo teste `test_get_files_to_process_requeues_when_stat_unavailable` para travar comportamento de reenfileirar quando `stat` falha.
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 53` e `id 68` sincronizados para `resolved` com evidencia.
  - `docs/RECOVERY_BACKLOG.md`
    - update do ciclo batch07.1 adicionado.
- validacao:
  - `py_compile tests/test_caching.py`: pass.
  - `ruff check tests/test_caching.py docs/PENDING_ACTION_MATRIX.md docs/RECOVERY_BACKLOG.md`: pass.
  - `ty check tests/test_caching.py`: pass.
  - `pytest -q tests/test_caching.py tests/test_config_manager_mappings_integrity.py`: 8 passed.
- processo:
  - kluster apontou 1 erro critico de escopo no teste novo (NameError), corrigido no mesmo slice e revalidado clean.

## Update 2026-02-26 (batch07.2 rescan test determinism)

- arquivos alterados:
  - `tests/test_rescan_progress_dialog.py`
    - adicionada espera curta por condicao (`_spin_until`) para reduzir flakiness de event loop em cenarios de cancel/finalizacao.
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 66` sincronizado para `resolved` com evidencia.
  - `docs/RECOVERY_BACKLOG.md`
    - update batch07.2 adicionado.
- validacao:
  - `py_compile tests/test_rescan_progress_dialog.py`: pass.
  - `ruff check tests/test_rescan_progress_dialog.py docs/PENDING_ACTION_MATRIX.md docs/RECOVERY_BACKLOG.md`: pass.
  - `ty check tests/test_rescan_progress_dialog.py`: pass.
  - `pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: 6 passed.

## Update 2026-02-26 (batch08 id64 matrix sync)

- docs alterados:
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 64` marcado como `resolved` com evidencia.
  - `docs/RECOVERY_BACKLOG.md`
    - update do ciclo batch08 adicionado.
- validacao:
  - `pytest -q tests/test_rescan_worker_cleanup.py`: 2 passed.
- escopo:
  - sem mudanca de runtime; apenas sincronizacao documental com evidencia de teste.

## Update 2026-02-26 (batch09-10 scripts/config matrix sync)

- docs alterados:
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 62/67/69/72/74/77/78` sincronizados para `resolved` com evidencia de estado atual.
  - `docs/RECOVERY_BACKLOG.md`
    - update de batch09/10 adicionado.
- validacao:
  - `py_compile scripts/run_pytest_stream_and_log.py scripts/run_pytest_stream_and_log_v2.py`: pass.
  - `ruff check` e `ty check` nos mesmos scripts: pass.
- escopo:
  - somente sincronizacao documental neste slice; runtime inalterado.

## Update 2026-02-26 (batch11.1 id8 filter_cache)

- arquivos alterados:
  - `gui/cache/filter_cache.py`
    - `put()` passou a validar tipo de entrada e ignorar nao-DataFrame com warning.
    - logger do modulo alinhado para `get_robust_logger()`.
    - docstring de `put()` alinhada ao contrato real.
  - `tests/test_filter_cache_locking.py`
    - teste novo para garantir que entrada invalida nao quebra o cache.
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 8` sincronizado para `resolved`.
  - `docs/RECOVERY_BACKLOG.md`
    - update batch11.1 adicionado.
- validacao:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - `pytest -q tests/test_filter_cache_locking.py tests/test_filter_worker.py`: 10 passed.
- processo:
  - kluster retornou 2 pontos P4 (docstring/logger), corrigidos no mesmo slice e revalidados clean.

## Update 2026-02-26 (batch12 config ids 4/5/73 sync)

- docs alterados:
  - `docs/PENDING_ACTION_MATRIX.md`
    - `id 4`, `id 5` e `id 73` sincronizados para `resolved` com evidencia.
  - `docs/RECOVERY_BACKLOG.md`
    - update batch12 adicionado.
- validacao:
  - `pytest -q tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: 8 passed.
- escopo:
  - ciclo documental com evidencia tecnica; sem mudanca de runtime.

## Update 2026-02-26 (handoff status + next queue)

- branch atual: `codex/dev-filtros-stability`
- matriz atual: `pending=65`, `resolved=27`, `stale-doc=5`, `deferred=11` (total 108)
- seguranca de dependencias:
  - hotfix aplicado em `main` com `pillow>=12.1.1` nos manifests de build.
  - dependabot open alerts para pillow: fechado (consulta API retornou lista vazia).
- proxima fila recomendada (ordem):
  - 1) extractor contract e required-columns (ids 6, 7, 33, 34, 35, 58)
  - 2) rescan worker concurrency/lifetime (ids 11, 12, 38, 79)
  - 3) cli enhancement lock residual (ids 13, 26, 30, 31, 41, 80)
  - 4) main flow fallback/debug listing (ids 15, 16, 45, 48)
- regra de execucao:
  - patch minimo por slice, gate local por slice, commit atomico, push, sync de docs.
