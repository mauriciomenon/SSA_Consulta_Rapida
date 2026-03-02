# Next Chat Migration Guide

Use this file to migrate context to a new chat without losing execution quality.

## CURRENT TRUTH 2026-03-01 02:20 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.27`.
- Runtime standard:
  1. use `uv run --python 3.13 ...` as first choice.
  2. fallback order: `3.12 -> 3.11 -> 3.10`.
  3. keep `requirements*.txt` as compatibility-only path.
- Compatibility matrix status:
  1. 3.10.18: pass
  2. 3.11.14: pass
  3. 3.12.11: pass
  4. 3.13.12: pass
- Focused gate used:
  1. `py_compile`, `ruff`, `ty`
  2. `pytest -q tests/test_open_docs_folder_nonblocking.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`
- GUI reference docs for continuity:
  1. `ANALISE_PROFUNDA_GUI.md`
  2. `GUI_SSA_REFACTOR_NOTES.md`

## CURRENT TRUTH 2026-02-28 23:46 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.27`.
- Release alignment status:
  1. streamlit deliveries from `v4.24.1` preserved.
  2. hardening package from `v4.25.0` preserved.
  3. metadata and docs aligned for pre-PR baseline `v4.27`.
- Working tree status:
  1. clean and synced with origin before pre-PR gates.
- Next execution order:
  1. run kluster on release/doc slice.
  2. run `py_compile`, `ruff`, `ty`, and focused `pytest`.
  3. commit atomic release/doc update and push.

## CURRENT TRUTH 2026-02-28 22:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint D status:
  1. P1 cache guard delivered in GUI + Streamlit cache paths.
  2. matrix item `9` moved to `resolved` (older deferred snapshots are historical only).
  3. stats now include `skipped_large_entries` and `max_entry_mb`.
- Optional P3 status:
  1. item `104` resolved: persistent width profile memory across sessions.
  2. item `107` resolved: render telemetry persistence across sessions.
- Streamlit colors/behavior follow-up:
  1. theme palettes + CSS variables implemented.
  2. runtime theme selector moved to header (always visible).
  3. selected theme now persists across sessions.
- Streamlit usability follow-up:
  1. situacao is always visible again and now includes quick mode + count labels.
  2. executor/emissor compacted to single-select (`(Todos)` fallback).
  3. quick "colunas exibidas" shortcut added in table tab.
  4. source controls moved to hidden advanced section in `Cache e API`.
  5. table render height is now dynamic per page row count.
  6. extra charts added (`Top executor`, `Top emissor`) under situacao distribution.
  7. presets renamed to business labels (`Operacao diaria`, `Analise completa`, `Minimo`).
  8. table metrics row expanded (`situacoes/executores/emissores distintos`).
- Item `92` status:
  1. resolved with cache architecture micro-refactor (shared helpers for get/store paths).
- Validation snapshot for Sprint D closeout:
  - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
  - focused `pytest -q tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: `40 passed`
- Deferred map (explicit, by difficulty):
  - structural (P2):
    1. `SSAMainWindow` split (`item 84`) - difficulty alta
    2. streamlit god-module split (`item 101`) - difficulty alta
- Retomada checklist (ordem de execucao):
  1. rodar `git status --short` e manter escopo minimo.
  2. selecionar somente item aprovado de risco real.
  3. apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. atualizar matrix/backlog/handoff no mesmo slice.
  5. manter blocos antigos somente como historico, sem usar como fonte de verdade.

## CURRENT TRUTH 2026-02-28 12:25 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.25.0`.
- Sprint status:
  1. pacote "25 graves v4" aplicado e validado.
  2. docs de handoff/matriz/backlog sincronizados para continuidade.
  3. release local incrementado em +0.1 (`4.24.0 -> 4.25.0`).
- Validation snapshot (ultimo pacote tecnico):
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest package: `30 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` no pacote tecnico: clean
- Retomada checklist (ordem de execucao):
  1. rodar `git status --short` e confirmar escopo local.
  2. escolher slice da fila ativa em `docs/PENDING_ACTION_MATRIX.md` por risco real.
  3. aplicar patch minimo no slice escolhido.
  4. apos editar: rodar kluster auto e corrigir `agent_todo_list`.
  5. executar gates: `py_compile`, `ruff`, `ty`, `pytest` focado.
  6. atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## CURRENT TRUTH 2026-02-28 04:40 - start from here

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

## CURRENT TRUTH 2026-02-28 04:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (20 graves v3):
  1. rescan dialog finish/cancel contract hardened for duplicate finish and running-cancel phase.
  2. rescan worker lifecycle hardened (pre-prune, stale active ref cleanup, deterministic cancel status, post-dialog prune).
  3. stream wrapper queue poll timeout configurable and faster deterministic loop exit conditions.
  4. sentinel path excluded from dropped-line accounting.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest (`rescan dialog + gui workers + stream guards`): `15 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## CURRENT TRUTH 2026-02-28 03:35 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 graves v2):
  1. rescan dialog cancel-close contract hardened.
  2. rescan worker active/stale/cap metadata handling hardened.
  3. stream wrapper dropped-line warning cadence and sentinel accounting hardened.
  4. focused regressions updated for dialog/worker/wrapper guards.
- Validation snapshot:
  - touched-scope `py_compile`, `ruff`, `ty`: pass
  - focused pytest (`rescan dialog + gui workers + stream guards`): `12 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## CURRENT TRUTH 2026-02-28 02:55 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package delivered (10 high-risk minimal fixes):
  1. dynamic GUI config path resolution API + loader usage in `gui/gui_config.py`.
  2. runtime/env path regressions in `tests/test_gui_main_configuration.py`.
  3. streamlit width-profile memory hardening and viewport fallback in `dev_env/streamlit_app.py`.
  4. streamlit snapshot clear idempotent guard + regressions in `tests/test_streamlit_filter_cache.py`.
  5. closeEvent rescan defensive shutdown hardening in `gui/gui_ssa.py` with focused regression in `tests/test_gui_filter_logic.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py tests/test_gui_filter_logic.py`: `150 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean

## CURRENT TRUTH 2026-02-28 02:05 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest sprint package (5 high-risk minimal slices) delivered:
  1. closeEvent rescan retention cap/meta hardening in `gui/gui_ssa.py`.
  2. canonical candidate regression + rescan cap regression in `tests/test_gui_filter_logic.py`.
  3. config fallback regression for missing `SSA_CONFIG_DIR` in `tests/test_gui_main_configuration.py`.
  4. unified API snapshot clear helper in `dev_env/streamlit_app.py`.
  5. streamlit API snapshot clear regression in `tests/test_streamlit_filter_cache.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: `145 passed, 1 skipped`
- Kluster snapshot:
  - `kluster_code_review_auto` runs in this package: clean
- Retomada checklist (ordem de execucao):
  1. validar `git status --short` e manter escopo minimo.
  2. escolher proximo slice aprovado na fila de risco real.
  3. apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## CURRENT TRUTH 2026-02-28 01:10 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered (requested order: item 2 then item 1):
  1. item 2: width-profile memory by width bucket in `dev_env/streamlit_app.py`.
  2. item 1: tabs/API smoke hardening with stable tab labels and API snapshot availability guard.
- Focused test scope:
  - `tests/test_streamlit_filter_cache.py` now includes bucket-memory and tabs/API smoke coverage.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched files: pass
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: `21 passed`
- Kluster snapshot:
  - `kluster_code_review_auto` on touched files: clean
- Retomada checklist (ordem de execucao):
  1. `git status --short` e confirmar escopo local antes de novo patch.
  2. Escolher o proximo item aprovado da fila streamlit (patch minimo).
  3. Apos editar: kluster auto -> `py_compile` -> `ruff` -> `ty` -> `pytest` focado.
  4. Atualizar `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md`.

## CURRENT TRUTH 2026-02-28 00:18 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest streamlit slice delivered:
  1. telemetry profile window cap in `dev_env/streamlit_app.py` to bound session-state growth.
  2. focused regression added in `tests/test_streamlit_filter_cache.py`.
- Validation snapshot:
  - `py_compile`, `ruff`, `ty` on touched streamlit files: pass
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: `16 passed`
- Queue status:
  1. matrix has no immediate `pending` rows.
  2. streamlit queue remains active for next approved deferred item.
- Important:
  - blocks below are historical context and must not override this top block.

## CURRENT TRUTH 2026-02-28 00:00 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest package delivered:
  1. kluster custom-rule alignment in `gui/gui_config.py`:
     - GUI config path now honors `SSA_CONFIG_DIR` with safe fallback.
  2. closeEvent lifecycle hardening in `gui/gui_ssa.py`:
     - active rescan worker now has defensive global-retention fallback in shutdown edge cases.
  3. focused regressions added:
     - `tests/test_gui_main_configuration.py` (`SSA_CONFIG_DIR` path resolution)
     - `tests/test_gui_filter_logic.py` (mid-shutdown `isRunning()` failure path)
- Validation snapshot (focused package scope):
  - `py_compile`, `ruff`, `ty`: pass
  - focused `pytest`: pass
- Current pending queue:
  1. no immediate `pending` in `docs/PENDING_ACTION_MATRIX.md`.
  2. streamlit stabilization queue remains separate.
- Important:
  - blocks below are historical context and must not override this top block.

## CURRENT TRUTH 2026-02-27 16:32 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Residual runtime group status:
  1. `39, 46, 49, 50, 70, 76` is now documented as `resolved` in `docs/PENDING_ACTION_MATRIX.md`.
  2. Functional closure is based on already-merged runtime/test slices:
     - rescan worker closeEvent shutdown hardening;
     - global data-loader retention/prune consistency with lock snapshot;
     - cancel contract reinforcement across importer and extractor.
- Current pending queue after closeout:
  1. no immediate `pending` in this matrix.
  2. streamlit stabilization queue (separate track).
  3. `9` moved to `deferred` by explicit user decision (Opcao A).
- Additional closure in this cycle:
  1. `27` resolved with full `finish` payload assertion in `tests/test_import_cancellation.py`.
  2. `22/23` resolved in `tests/test_database_optimized_alias_views.py` (explicit init success contract + explicit cleanup).
  3. `21` resolved by existing concurrent-write coverage in `tests/test_caching_atomic_save.py`.
  4. `24/25` resolved by current lock/modal test hardening.
  5. `9` deferred by explicit user decision (Opcao A), no runtime patch.
- Retomada checklist (ordem de execucao):
  1. Confirm scope with `git status --short`.
  2. Pick next approved slice from streamlit queue or another explicitly selected deferred item.
  3. After edits: run kluster auto first, then `py_compile`, `ruff`, `ty`, and focused `pytest`.
  4. Update `docs/PENDING_ACTION_MATRIX.md` and `docs/RECOVERY_BACKLOG.md` with slice evidence.
- Important:
  - blocks below are historical context and must not override this top block.

## CURRENT TRUTH 2026-02-27 15:53 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Current state from interrupted chat (local patch present, not committed):
  1. `gui/ssa/gui_filters_advanced_ui.py`:
     - action buttons container and sizing adjusted;
     - `_set_checkbox_checked_quietly` now keeps `QSignalBlocker` context and guarded manual unblock.
  2. `gui/mixins/filter_gui_ssa_mixin.py`:
     - add-column menu now builds deterministic ordered set with dedupe and duplicate-label disambiguation.
  3. `gui/widgets/column_manager_dialog.py`:
     - explicit `available_columns` no longer gets auto-polluted by full `display_map` reinjection.
  4. `gui/gui_ssa.py` + `gui/ssa/gui_workers.py`:
     - canonical menu candidate filter now uses cached non-null columns;
     - non-null cache is computed on data load and reused in UI candidate paths.
- Validation closeout for interrupted patch (done):
  - `uv run --python 3.13 python -m py_compile` on touched runtime files: pass
  - `uv run ruff check` on touched runtime files: pass
  - `uv run ty check` on touched runtime files: pass
  - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`:
    - `121 passed, 1 skipped`
  - kluster auto on touched runtime files: clean (no issues)
- Retomada checklist (ordem de execucao):
  1. Confirm local scope with `git status --short` and keep edits limited to expected files.
  2. Start next slice only with minimal patch over active filter/runtime scope.
  3. After any new edit, rerun kluster auto and local gates on touched scope.
  4. Keep non-blocking follow-ups in `docs/RECOVERY_BACKLOG.md`.
- Important:
  - sections below remain historical context and must not override this block.

## CURRENT TRUTH 2026-02-26 21:40 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.24.0`.
- Latest delivered slice:
  1. Added single synchronized height lock for the 3 lower panels:
     - `Detalhes da SSA Selecionada`
     - `Filtros Avancados`
     - `Filtros por Coluna`
  2. Height sync is now triggered on init, tab change, resize, and column-filter panel rebuild.
  3. Tab/bind sync was switched to deferred queue (`QTimer.singleShot(0, ...)`) to avoid layout thrashing.
  4. Added regression test to lock equal min/max heights after resize.
  5. Code evidence:
     - `gui/gui_ssa.py`: `_compute_bottom_panel_target_height`, `_queue_bottom_panel_height_sync`, `_sync_bottom_panel_heights`
     - `gui/mixins/tab_context_gui_ssa_mixin.py`: bind path now queues height sync
     - `gui/mixins/filter_gui_ssa_mixin.py`: column-filter rebuild re-applies height sync
     - `tests/test_gui_filter_logic.py`: `test_bottom_panels_keep_single_synced_height_after_resize`
- Validation snapshot:
  - `python -m py_compile` (touched files): pass
  - `ruff check` (touched files): pass
  - `ty check` (touched files): pass
  - `uv run pytest -q` full suite: `582 passed, 6 skipped, 11 subtests passed`
  - focused GUI tests:
    - `test_bottom_panels_keep_single_synced_height_after_resize`: pass
    - `test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows`: pass
- Important:
  - sections below remain historical context and must not override this block.

## CURRENT TRUTH 2026-02-26 17:05 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Latest delivered slice:
  1. Re-ran MD audit and refreshed active control docs only.
  2. Enforced consistent status counter in filter clear flows:
     - `Status: SSAs filtradas: N de M`.
  3. Unified footer button style in SSA column-filter panel:
     - `Adicionar filtro de coluna` == `Limpar todos filtros de colunas`.
- Latest validation snapshot:
  - `python -m py_compile` on touched files: pass
  - `ruff check` on touched files: pass
  - `ty check` on touched files: pass
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
    => `117 passed, 1 skipped`
- Important:
  - sections below remain historical context and must not override this block.

## CURRENT TRUTH 2026-02-26 14:07 - start from here

- Active branch: `codex/dev-filtros-stability`.
- Local release baseline: `4.22.0`.
- Latest delivered slice:
  1. Added regression tests for column-filter stability in `tests/test_gui_filter_logic.py`.
  2. Locked behavior for:
     - add-column menu candidate coverage + exclusion of legacy ghost aliases;
     - clear-all restore of default visible columns and hidden-line reset;
     - Apply/Hide controls present in default rows.
- Latest validation snapshot:
  - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py` => `97 passed, 1 skipped`.
  - `.venv/bin/python -m pytest -q tests/test_gui_main_configuration.py` => `12 passed`.
  - `.venv/bin/python -m pytest -q tests/test_display.py tests/test_streamlit_filter_cache.py` => `20 passed`.
- Important:
  - any references below to `codex/import-review` or `PR #31` are historical and non-operational.

## Update 2026-02-26 (sprint migration snapshot)

- Active branch: `codex/dev-filtros-stability`.
- Delivered in this cycle:
  - Sprint A closed (extractor contract ids `6,7,33,34,35,58`).
  - Sprint B closed (rescan ids `11,12,28,29,38,79`; `71` stale-doc).
  - Sprint C closed (cli lock ids `13,26,30,31,41,80`).
  - E closed: pytest ignores removed from `pyproject.toml` and former script-like test files converted to deterministic pytest tests.
- Pending priority queue:
  1. Main/config/gui residual group: `39, 42, 43, 44, 46, 49, 50, 70, 76`.
  2. Streamlit stabilization queue (separate track).
- Guardrail:
  - keep minimal patches and avoid broad refactor while closing high-impact semantic/security items first.

## Update 2026-02-26 (deep analysis refresh)

- Gate snapshot:
  - `py_compile`, `ruff`, `ty`: pass.
  - `flake8`: baseline debt still high (`E501`/spacing), many legacy files.
  - `mypy`: baseline debt still high (missing stubs and typing issues in GUI/data paths).
  - `pylama`: unavailable in current env (`ModuleNotFoundError: pkg_resources`), no deps changed.
- Kluster snapshot:
  - stream scripts (`run_pytest_stream_and_log*.py`) now highest practical priority due security/path handling and perf pressure.
  - `main.py`, `core/config_manager.py`, `gui/gui_ssa.py` findings are mostly medium and structural; keep for later slices/sprints.
- Practical next queue:
  1. Stream scripts mini-slice: delivered (path guard + buffered flush + shared runner).
  2. Main resilience mini-slice (Batch 11): delivered with deterministic fail-fast behavior.
  3. Main/config/gui residual group and streamlit stabilization queue.

## Update 2026-02-26 (batch11 resilience lock delivered)

- `main.py`:
  - optimized import failure now fails fast by default with full context logs;
  - no automatic legacy retry path (including `--force-rescan`) to keep predictable runtime.
- `tests/test_main_import_fallback.py`:
  - added fail-fast lock test without retry.
- Validation:
  - `py_compile`, `ruff`, `ty` pass on touched files.
  - `uv run pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py`: pass.

## Update 2026-02-26 (config restore fallback lock)

- Added focused regression tests in `tests/test_config_manager_mappings_integrity.py`:
  - restore write failure in `load_display_mappings_integrity` returns defaults in memory;
  - restore write failure in `load_column_mappings_integrity` returns defaults in memory.
- Validation:
  - `py_compile`, `ruff`, `ty` pass for touched files.
  - `uv run pytest -q tests/test_config_manager_mappings_integrity.py`: pass (`4 passed`).

## Update 2026-02-26 (stream scripts mini-slice delivered)

- Added shared helper `scripts/pytest_stream_common.py`.
- Both wrappers now use shared runtime path:
  - `scripts/run_pytest_stream_and_log.py`
  - `scripts/run_pytest_stream_and_log_v2.py`
- Added focused tests:
  - `tests/test_stream_log_wrapper_guards.py` (`4 passed`).

## OVERRIDE 2026-02-24 (ativo)

- Branch ativa para continuidade: `codex/dev-filtros-stability` (base `origin/dev`).
- Commits base desta rodada:
  - `1c56addb` fix(gui): stabilize advanced filters responsive grid and action buttons.
  - `06633471` fix(cli,db): harden config flow and maintenance schema targets.
  - `4adcf35b` fix(extracao): resolve tempo_excedido `m` ambiguity and add focused regression tests.
  - `resolved` fix(maintenance): avoid VACUUM-in-transaction and add script regression tests.
  - `resolved` test(db): add schema_manager identifier guard regression lock.
  - `resolved` fix(maintenance): harden analyze_db_integrity for empty-table and report consistency.
  - `resolved` perf(maintenance): refactor verify_database_integrity query flow.
  - `resolved` fix(cli): guard direct SSA search when `numero_ssa` is absent.
- Scope ativo:
  - estabilizacao de filtros avancados (resize/layout interno de botoes no painel de filtros avancados);
  - hardening pontual de CLI/schema/scripts de manutencao;
  - sem refactor amplo.
- Status de PR:
  - nenhum PR novo deve ser aberto sem autorizacao explicita do usuario.
- Nota de migracao:
  - secoes antigas com `codex/import-review` e PR `#31` abaixo ficam como historico de auditoria.
  - pendencias abertas foram separadas em duas filas no backlog:
    - `Pendencias longas`
    - `Pendencias para sprint exclusivo`

## Latest update 2026-02-24 (tempo_excedido)

- Parser update in `extracao/extractor.py`:
  - `m` interpreted as minutes.
  - months require explicit `mo`.
- Regression tests added in `tests/test_extracao.py`.
- Local validation for touched scope:
  - `python -m py_compile`, `ruff check`, `ty check`, `uv run pytest -q tests/test_extracao.py` all green.

## Latest update 2026-02-24 (maintenance scripts)

- `scripts_manutencao/limpar_banco.py` runtime fix:
  - `VACUUM` executes after `commit`, avoiding transaction error.
- logging aligned with local rule in same script:
  - `print()` replaced by robust logger calls.
- regression lock:
  - new `tests/test_scripts_manutencao_schema_targets.py` for `analyze_db_integrity` paths.

## Latest update 2026-02-24 (schema_manager guard lock)

- new `tests/test_schema_manager_identifier_guards.py`:
  - asserts invalid column identifiers are rejected with `ValueError`;
  - asserts valid missing columns are added.

## Latest update 2026-02-24 (analyze_db_integrity hardening)

- `scripts_manutencao/analyze_db_integrity.py`:
  - moved to robust logger outputs;
  - added `verify_database_integrity` entrypoint with compatibility alias;
  - fixed empty-table edge cases (`0` totals and `SUM NULL` handling);
  - aligned return payload with `stats_dict`.
- focused tests:
  - `tests/test_scripts_manutencao_schema_targets.py` validates aggregate empty-fields and empty-table no-crash path.

## Latest update 2026-02-24 (verify_database_integrity performance refactor)

- consolidated integrity metrics into one core SQL query;
- duplicate total now computed across full grouped set while keeping top-10 display;
- added guard before import-date query when `data_importacao` is not present;
- regression test expanded for duplicate-count correctness beyond top-10.

## Latest update 2026-02-24 (cli direct search guard)

- `interface/cli.py`:
  - avoids `KeyError` when `numero_ssa` column is absent in current dataframe;
  - uses exact match on normalized SSA and literal contains fallback with `regex=False`.
- focused regression:
  - `tests/test_cli_loop_missing_numero_ssa_guard.py`.

## Scope

- Branch: `codex/dev-filtros-stability`
- PR: sem PR ativo para esta branch neste momento
- Goal now: seguir com patches minimos de estabilidade e validar por slice.

## What to provide in the next chat

1. Current blocking errors/logs (if any).
2. External IA report in structured form:
   - `id`
   - `severity`
   - `file:line`
   - `evidence`
   - `impact`
   - `suggested fix`
3. Any new user decisions (scope approvals, deferrals).

## Latest intake status (2026-02-17)

- Completed:
  - Restored facade export contract for `_has_active_advanced_filters` in aggregated module.
  - Fixed broken regex in key-coverage test and added reverse contract check (`logic/detector -> UI or legacy`).
- Decision applied:
  - `responsavel_emissor` path B done: advanced filter flow removed/disabled in UI + logic detector.
- New validated input from modular rescan:
  - 75 files total, 64 processed, 11 errors.
  - all 11 errors are `SSAs Derivadas e Relacionadas_*.xlsx` rejected by main extractor required-column gate (`data_cadastro`, `descricao_ssa`).
  - these files are special derivadas source and should be handled by derivadas sync path, not main SSA extractor.
- Delivery status:
  - auto-trigger implemented in importer: special derivadas sheets are skipped from main extraction and synchronized by derivadas sync after import loop.
  - sync currently selects the latest special sheet by mtime and records special files in cache on successful sync.
- Additional delivery status:
  - user decision B applied for advanced filters: `responsavel_emissor` controls removed from UI panel assembly/context.
  - regression test added to keep `adv_responsavel_emissor_*` controls absent.
  - `Especificas...` derivadas button upgraded:
    - popup now shows DB materialized summary/top maes for visible SSAs (`ssa_derivada_summary`);
    - enable state now checks DB relations fallback when dataframe `derivada_de` has no valid values.
  - responsive grid regression fixed after removal of `responsavel_emissor` controls (`emis_resp_box` references removed).
  - advanced year execution filter cleanup:
    - dead `data_execucao` branch removed from logic;
    - behavior validated with test over `semana_executada` and `ano_execucao_values`.
  - legacy year keys migration hardened:
    - fixed precedence for `ano_execucao` + `ano_execucao_exclude=True`;
    - added tests for legacy `ano_emissao` and `ano_execucao` exclude path.
  - derivadas special ingest hardened:
    - importer now sends all detected special sheets to sync (not only latest by mtime);
    - `sync_derivadas` supports `sheet_files` and reports aggregated sheet stats.
- Keep backlog tracking in `docs/RECOVERY_BACKLOG.md` for non-blocking findings from the external report.

## Latest update (2026-02-18)

- Reliability hardening delivered after previous migration snapshot:
  - importer now blocks success when derivadas sync or consistency is not clean (`f9e69d86`);
  - sync pipeline now has internal post-materialization integrity gate (`474e980a`);
  - GUI manual derivadas update requires clean consistency scan (`5a50ea17`);
  - visual special parser now classifies root-only rows as informational (`6f4fcc7a`);
  - filter cache key now accepts advanced-filter context token (`ff266350`).
- Local data integrity check on `data/ssas.db` remains clean:
  - `scan`: `is_consistent=true`, all issue counts `0`.

## Mandatory execution protocol

1. Re-validate every external finding locally before patching.
2. Apply only minimal slices.
3. Run gate for each slice:

```bash
uv run --python 3.13 python -m py_compile <files>
uv run ruff check <files>
uv run ty check <files>
uv run pytest -q <focused-tests>
```

4. Commit atomically, push, check PR checks.
5. Update handoff docs after each meaningful slice:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/RECOVERY_BACKLOG.md`

## Writing guardrails (do not do)

1. Do not silence link/runtime warnings without fixing navigation behavior.
2. Do not claim completion if the reported user flow still fails.
3. Do not replace a functional bug with a generic fallback popup.
4. Do not close a slice without before/after evidence for the same user repro.
5. Do not optimize for "clean logs" over correct behavior.

## Mandatory gates for advanced filters

```bash
uv run pytest -q tests/test_gui_filters_facade_contract.py
uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
uv run pytest -q tests/test_gui_filters_advanced_logic.py
```

## Latest update (2026-02-18, mega sprint block 6)

- New slices delivered:
  - `1f213578`: derivadas sync now emits `sheet_file_reports` with per-file parse evidence and deduplicates relative/absolute file paths.
  - `ffd5d8ef`: importer derivadas phase now fails closed when any special sheet has no individual parse evidence.
  - `3daddd9f`: GUI `Atualizar Derivadas` now fails closed when any special sheet has no individual parse evidence.
  - `f7f7ead7`: derivadas CLI sync now supports `--special-docs-dir` to ingest all `SSAs Derivadas e Relacionadas_*.xlsx`.
  - `60adbd5a`: committed refreshed `data/ssas.db` after full derivadas sync with 11 special sheets.
- Operational run executed on 2026-02-18:
  - `sync_run_id=4`, actor `mega-sprint-special-sync`
  - `sheet_files_count=11`, `db_edges=3216`, `sheet_edges=1497`, `merged_edges=3547`
  - post-sync consistency: `is_consistent=true`

## Current execution status (2026-02-18, ready to migrate)

- Branch and PR:
  - `codex/import-review`, PR `#31` open.
- Latest commits on head:
  - `aa454a40` docs handoff package expanded (strict starter + migration payload).
  - `80a73363` details dialog baseline locked at `20/80` with migration guardrails.
  - `24024662` real split enforcement via `QSplitter`.
- Current PR checks snapshot:
  - external blocked by plan limit: `code/snyk`, `security/snyk`.
  - core static/security checks in pass (DeepScan, DeepSource, GitGuardian, Socket, semgrep, submit-pypi, cubic).

## Scope lock from user triage

- Do not execute in this cycle:
  1. remove `if df is None` defensive branch.
  2. add new lock layers in stream scripts.
  3. broad race-condition refactor in `gui/workers`.
- Lint policy for this cycle:
  - ignore `E501` findings.

## Latest update (2026-02-19, critical filters-tab overlap fix)

- Head commit for this fix: `d3d9410f`.
- Root cause:
  - vertical area allocation between main table and bottom panel in `Filtros` tab was not hard constrained for low-row scenarios.
- Minimal fix applied in `gui/gui_ssa.py`:
  - table min height set to `220`;
  - vertical stretch set to `6` (table) and `4` (bottom panel).
- Regression lock:
  - `tests/test_gui_filter_logic.py::test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows`.
- Validation evidence:
  - `py_compile`, `ruff`, `ty` green for touched scope;
  - focused pytest gates green, including advanced-filters suites;
  - runtime geometry matrix check reported no overlap in tested combinations.
- Rule for next chat:
  1. preserve `table min height + vertical stretch 6/4` unless user asks explicit layout change;
  2. if changing this area, provide before/after geometry evidence with numeric values.

## Latest update (2026-02-18, behavior and dialog baseline)

- Double-click details dialog (`gui/ssa/gui_details.py`) baseline is now:
  - split: `20/80` (left derivadas / right details),
  - min size: `700x650`,
  - fonts: left `12`, right `12`, labels `11`.
- Implementation detail that must be preserved:
  - split is enforced with `QSplitter` + explicit `setSizes` + stretch factors.
  - do not rely on ratio constants alone.
- Behavior rule for next IA:
  1. explain root cause before patching UI regressions;
  2. never claim visual fix without constraint validation;
  3. provide numeric before/after values in final report.

## Copy/paste starter for next chat

```text
Context:
- Continue on branch codex/import-review, PR #31.
- Keep minimal-risk patches only, no GUI layout changes.
- Ingest external IA report with local re-validation per finding.

Must follow:
1) Validate each finding with file:line evidence before editing.
2) Patch in atomic slices.
3) Run py_compile + ruff + ty + focused pytest on touched scope.
4) Push and check PR checks.
5) Update AGENTS_HANDOFF_NEXT_CYCLE.md and RECOVERY_BACKLOG.md.
6) For UI ratio fixes, validate layout constraints (`minimumWidth`, splitter/layout manager) and report exact values.

Input report:
<paste structured report here>
```

## Copy/paste full starter (strict mode)

```text
Trabalhe no repo /Users/menon/git/SSA_Consulta_Rapida

Contexto:
- Branch atual: codex/import-review
- PR alvo: #31 (base dev)
- Objetivo: fechar PR com estabilidade e patch minimo

Regras:
1. Nao criar branch nem PR novo.
2. Nao fazer refactor amplo.
3. Nao alterar layout GUI sem pedido explicito.
4. Manter dialogo de detalhes derivadas em baseline fixa:
   - split 20/80
   - min size 700x650
   - fontes: 12/12/11
   - usar QSplitter com sizes reais
5. Sem acentos/cedilha/emojis/emdash em codigo, docs e mensagens tecnicas.
6. Nao ocultar erro real com except vazio/suppress indevido.

Leitura obrigatoria antes de iniciar:
1. docs/AGENTS_HANDOFF_NEXT_CYCLE.md
2. docs/NEXT_CHAT_MIGRATION.md
3. docs/RECOVERY_BACKLOG.md
4. docs/QA_FACADE_FILTERS.md
5. AGENTS.md

Sequencia obrigatoria de ciclo:
1) evidenciar problema com arquivo:linha e repro
2) propor diff minimo antes de editar
3) implementar slice pequeno
4) validar local
5) commit atomico
6) push
7) checar checks e comentarios de PR
8) backlog para nao bloqueante

Fluxo por slice:
1) validar evidencia local (rg -n + nl -ba)
2) patch minimo
3) gate local
4) commit atomico
5) push
6) checar PR checks

Gate tecnico:
- uv run --python 3.13 python -m py_compile <files>
- uv run ruff check <files>
- uv run ty check <files>
- uv run pytest -q <tests focados>

Cuidados de seguranca e operacao:
1. Nao comitar segredos e arquivos locais de ambiente.
2. Nao usar comandos git destrutivos.
3. Nao esconder erro real com fallback generico.
4. Nao alterar schema/layout sem aprovacao explicita.
5. Se aparecer mudanca fora de escopo, pausar e confirmar com usuario.

Gate extra se tocar facade de filtros:
- uv run pytest -q tests/test_gui_filters_facade_contract.py
- uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters
- uv run pytest -q tests/test_gui_filters_advanced_logic.py

Status checks conhecido:
- code/snyk fail por limite de plano
- security/snyk fail por limite de plano
- restante: tratar somente bloqueio real de codigo

Relatorio final por slice:
- commit hash
- testes executados
- checks PR
- pendencias reais
```

## Latest update 2026-02-24 (gui invalid regex fallback guard)

- `gui/mixins/filter_gui_ssa_mixin.py`:
  - fallback de regex invalido em `_build_column_mask` agora usa busca literal (`regex=False`);
  - cobre ambos caminhos: token explicito `~...` e modo padrao `regex`.
- focused regression:
  - `tests/test_filter_regex_invalid_fallback.py` com 2 cenarios:
    - regex explicita invalida (`~abc[`);
    - regex invalida no modo default `regex` (`abc[`).

## Latest update 2026-02-24 (cli remove-filter non-lifo guard)

- `interface/cli.py`:
  - `_handle_remove_filter` reaplica da base apenas quando a remocao e fora de ordem;
  - mantem reaplicacao do estado anterior para remocao LIFO (otimizacao).
- focused regression:
  - `tests/test_cli_remove_filter_non_lifo.py`:
    - remove termo do meio e garante base state;
    - remove ultimo termo e garante previous state.

## Nova regra 2026-02-24 (error-handling e performance)

- Manter tratamento de erro sempre presente, mas cobrindo porcoes relevantes de fluxo.
- Evitar `if/try` em excesso a cada poucas linhas, pois isso degrada legibilidade e pode introduzir custo.
- Nao usar `try/except` vazio nem suppress que esconda erro real.
- Para cada captura de erro, exigir saida objetiva (log curto) e tratamento coerente (retorno/raise/rollback).
- Em cada patch, revisar custo computacional para evitar solucoes caras por seguranca excessiva.

## Latest update 2026-02-24 (cli config refresh and query guard)

- `interface/cli.py`:
  - novo helper local para refresh pos `c/config`, removendo bloco duplicado;
  - refresh completo apenas quando `default_filters` muda;
  - sem mudanca de `default_filters`, mantem dataframe atual e evita requery caro;
  - `get_ssa_query` aplica allowlist de tabela (`ssa_table` + aliases legados).
- focused regression:
  - `tests/test_cli_config_preserve_session.py` valida caminho com reload e sem reload;
  - `tests/test_cli_get_ssa_query_identifier_guard.py` valida bloqueio de tabela fora da allowlist.

## Latest update 2026-02-24 (cli clearall table consistency)

- `interface/cli.py`:
  - `clearall` agora respeita `table_name` recebido pelo loop (`get_ssa_query(table_name)`).
- focused regression:
  - `tests/test_cli_clearall_uses_table_name.py`.

## Latest update 2026-02-24 (cli pagination tracker prune)

- `interface/cli.py`:
  - pagination tracker now has a small local manager class for state ops;
  - prune runs after stack mutations to remove orphan tracker entries.
  - pagination state key is persisted in `df.attrs` to preserve state across dataframe copies.
- focused regression:
  - `tests/test_cli_pagination_tracker_prune.py` (including copy-preservation check).

## Latest update 2026-02-24 (cli enhancement settings lock and root)

- `interface/cli_enhancement_manager.py`:
  - logger now uses robust logger API;
  - project root now resolved via `_get_project_root()`;
  - settings save keeps lock only on lockfile (no lock on temp file);
  - if lock cannot be acquired, save aborts and write is skipped.
- focused regression:
  - `tests/test_cli_enhancement_manager_lock_usage.py`.

## Latest update 2026-02-24 (command handlers root-safe mappings cache)

- `interface/command_handlers.py`:
  - path for mapping files now resolves from project root helper;
  - module logger aligned to robust logger API;
  - mappings cache moved to a small dedicated manager in-module.
- focused regression:
  - `tests/test_command_handlers_project_root_mapping.py`.

## Latest update 2026-02-24 (command handlers save flow cleanup)

- `interface/command_handlers.py`:
  - extracted `_attempt_save_settings(...)` to remove repeated `try/except ... pass` blocks;
  - helper returns explicit boolean (success/failure) for clear semantics;
  - call sites now rollback local changes when save fails;
  - save error handling remains centralized in `_save_settings_handler`.

## Latest update 2026-02-24 (optimized upsert legacy decimal key normalization)

- `armazenamento/database_optimized.py`:
  - lookup chunk now matches both canonical and legacy decimal SSA keys;
  - update branch deletes matched legacy key aliases plus canonical key before reinserting normalized rows;
  - savepoint-safe batch insert now uses parameterized `executemany` instead of `to_sql` in `DELETE + INSERT` path.
- focused regression:
  - `tests/test_database_optimized_alias_views.py::test_optimized_upsert_replaces_legacy_decimal_key_without_duplicate`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ruff check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ty check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass (3 tests).
- deferred-by-scope:
  - kluster P4 quality concern about function size in `insert_dataframe_optimized` (requires dedicated refactor sprint, out of current minimal patch scope).

## Latest update 2026-02-24 (canonical write policy for SSA ids)

- `armazenamento/database_optimized.py`:
  - removed legacy read compatibility branch for `numero_ssa + ".0"`.
  - added `_validate_canonical_storage_ids(...)` to reject decimal artifacts in write path.
- tests:
  - removed legacy-runtime compatibility test from `tests/test_database_optimized_alias_views.py`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ruff check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `ty check armazenamento/database_optimized.py tests/test_database_optimized_alias_views.py`: pass.
  - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (canonical write parity in non-optimized upsert)

- `armazenamento/database_upsert_logic.py`:
  - added canonical storage normalization helper for SSA ids;
  - applied normalization to both `numero_ssa` and `derivada_de`;
  - added fail-fast canonical validation for storage id columns.
- tests:
  - added `tests/test_database_upsert_canonical_write.py`.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_database_upsert_canonical_write.py`: pass.
  - `uv run pytest -q tests/test_database_upsert_canonical_write.py tests/test_database_optimized_alias_views.py`: pass (3 tests).

## Latest update 2026-02-24 (upsert chunk dedupe perf)

- `armazenamento/database_upsert_logic.py`:
  - `chunk_num_ssa` now uses `dropna().drop_duplicates().tolist()` (removed manual O(n2) loop).
- tests:
  - `tests/test_db_reset_and_upsert.py`: added duplicate-in-chunk regression scenario.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_db_reset_and_upsert.py`: pass.
  - `uv run pytest -q tests/test_db_reset_and_upsert.py tests/test_database_upsert_canonical_write.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (prepare_dataframe_for_upsert copy-path perf)

- `armazenamento/database_upsert_logic.py`:
  - `prepare_dataframe_for_upsert` now uses `frame.copy().reset_index(drop=True)`.
- tests:
  - added `tests/test_database_upsert_prepare.py` for immutability + normalization lock.
- gate local deste slice:
  - `python -m py_compile armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `ruff check armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `ty check armazenamento/database_upsert_logic.py tests/test_database_upsert_prepare.py`: pass.
  - `uv run pytest -q tests/test_database_upsert_prepare.py tests/test_db_reset_and_upsert.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (logging mapping interpolation fix)

- files:
  - `main.py`
  - `dev_env/streamlit_app.py`
  - `tests/test_ascii_logging_filter.py`
- change:
  - ASCII logging filter keeps `dict` args intact for named interpolation (`%(name)s`) and keeps tuple path unchanged.
- gate local deste slice:
  - `python -m py_compile main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `ruff check main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `ty check main.py dev_env/streamlit_app.py tests/test_ascii_logging_filter.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- ops clarification:
  - legacy DB reset is operational/controlled; code path now enforces canonical write and validation for new writes.

## Latest update 2026-02-24 (streamlit cache fallback parity)

- `dev_env/streamlit_app.py`:
  - `get_cached_filter` and `cache_filter_result` now branch by `_use_session_state` and update proper stats backend.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit filter guards and telemetry)

- `dev_env/streamlit_app.py`:
  - column-presence guards added for `situacao`, `setor_executor`, `setor_emissor` filters;
  - slow-filter telemetry now uses logger instead of `st.info` per cache miss.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit import ui unblock)

- `dev_env/streamlit_app.py`:
  - removed `time.sleep(0.5)` from `_execute_import` finally block.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py`: pass.
  - `ty check dev_env/streamlit_app.py`: pass.
  - `uv run pytest -q tests/test_ascii_logging_filter.py`: pass (2 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit broad hardening cycle)

- `dev_env/streamlit_app.py`:
  - safe import fallback when `streamlit` is missing;
  - `StreamlitFilterCache` now uses centralized backend resolver;
  - cache get/put now supports `df_token` and `apply_all_filters_cached` computes token via `_compute_df_cache_token`;
  - token computation optimized with sample-only string conversion + memoization in `df.attrs`;
  - removed deprecated pandas CoW option assignment.
- tests:
  - added `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (4 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle: layout and broad improvements)

- `dev_env/streamlit_app.py`:
  - UI repositioning/layout expanded to tabs: `Filtros`, `Tabela`, `Exportacao`, `Cache e API`.
  - table rendering now paginates filtered data (`_paginate_dataframe`) before arrow conversion/render.
  - API fetch now manual via button; snapshot persisted in session state and clearable.
  - runtime detection strengthened and non-streamlit import fallback added.
  - cache backend logic centralized; cache keys now include lightweight memoized dataframe token.
  - removed deprecated pandas CoW option write.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (6 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v2)

- `dev_env/streamlit_app.py`:
  - filters tab now uses form submit/reset workflow (state stored in `session_state`);
  - introduced `_normalize_filter_selection(...)` to skip no-op full selections;
  - mixed-type safe `_build_filter_options(...)` sorting;
  - table tab now supports sorting before pagination;
  - rerun fallback supports `rerun` and `experimental_rerun` APIs.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py`.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_ascii_logging_filter.py`: pass (8 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v3)

- `dev_env/streamlit_app.py`:
  - fixed scope bug: table tab now renders regardless of API toggle state;
  - introduced width profile state (`Compacto/Padrao/Largo/XL`) for deterministic table width behavior;
  - replaced hardcoded table `column_config` with `_build_streamlit_column_config(...)` + `SimpleWidthManager`;
  - added fallback path in column-config builder when streamlit column API is unavailable.
- tests:
  - expanded `tests/test_streamlit_filter_cache.py` with width-bucket and column-config assertions.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (10 tests).
- kluster:
  - `kluster_code_review_auto`: clean (no issues).

## Latest update 2026-02-24 (streamlit long cycle v4)

- final scope delivered in this cycle:
  - table tab flow fix (no hidden coupling with API toggle);
  - width profile controls + deterministic width buckets from `SimpleWidthManager`;
  - path safety validation for sidebar file-system inputs;
  - cache token guard for zero-column frames;
  - width manager signature alignment in GUI table call site.
- regression/tests:
  - `tests/test_streamlit_filter_cache.py` now 11 passing tests.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ruff check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster progression:
  - intermediate P4/P3 findings resolved in-sequence;
  - final `kluster_code_review_auto`: clean.

## Latest update 2026-02-24 (streamlit long cycle v5 final)

- final width-manager decision for this cycle: deterministic signature without external override params.
- `gui/ssa/gui_table.py` updated to same deterministic call contract.
- final kluster state: clean after iterative fixes.

## Latest update 2026-02-25 (streamlit long cycle v6)

- layout/positioning expansion delivered in `dev_env/streamlit_app.py`:
  - filters form grouped by functional blocks;
  - table controls split in two rows and view mode toggle added;
  - export and cache/api tabs reorganized for faster scan and less crowding.
- behavioral scope unchanged for filter semantics and data processing.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Latest update 2026-02-25 (streamlit long cycle v7)

- delivered:
  - `Compacto` toggle in table controls;
  - compact caption behavior in table mode;
  - render telemetry by width profile in cache panel.
- gate local deste slice:
  - `python -m py_compile dev_env/streamlit_app.py`: pass.
  - `ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass.
  - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (11 tests).
- kluster:
  - `kluster_code_review_auto`: clean.

## Latest update 2026-02-25 (streamlit long cycle v7.1)

- follow-up cleanup in `dev_env/streamlit_app.py`:
  - extracted small helpers for table caption and render telemetry update.
- behavior unchanged; maintenance improved.

## Latest update 2026-02-25 (streamlit direct-run import fix)

- fixed startup path issue for direct invocation:
  - `/Users/menon/git/SSA_Consulta_Rapida/.venv/bin/python /Users/menon/git/SSA_Consulta_Rapida/dev_env/streamlit_app.py`
  - previous error `ModuleNotFoundError: No module named 'core'` is resolved.

## Latest update 2026-02-25 (streamlit tests)

- added regression tests for:
  - `_build_table_caption` in compact and non-compact modes;
  - `_update_render_telemetry` session-state accumulation.
- focused streamlit test suite now at 14 passing tests.

## Latest update 2026-02-25 (streamlit telemetry panel refinement)

- cache tab improvements:
  - profile picker for render telemetry;
  - dedicated button to clear telemetry state;
  - telemetry caption formatting centralized in helper.
- focused streamlit suite now 15 passing tests.

## Latest update 2026-02-25 (qwen config and batch01 start)

- created `docs/QWEN_CODE_DELEGATION_CONFIG.md` with setup, delegation rules, and validation contract.
- batch01 progress:
  - done ids 21, 22, 23.
- focused tests: 5 passed.

## Latest update 2026-02-25 (batch01 tests + qwen check delegation)

- batch01 completed for ids 24/25/27/28/29 with focused test-only patches.
- qwen delegation confirmed in practice for `ruff` + `ty` execution (with `-y`), followed by independent final validation by main agent.
- observed tradeoff: qwen helps reduce reasoning-token load for repetitive checks, but has higher per-call latency.

## Latest update 2026-02-25 (extractor batch02)

- scope delivered:
  - stabilized `read_report` return contract to avoid `NoneType` regressions in legacy callers.
  - primary Excel read in `read_report` now goes through `import_excel_robust`.
  - preserved compatibility with controlled fallback to `extract_data_from_excel` when robust output is empty.
- tests and checks:
  - `py_compile`, `ruff`, `ty` for touched files: pass.
  - focused test `tests/test_extracao.py`: 5 passed.
- risk note:
  - strict "robust-only everywhere" migration in full extraction stack is intentionally deferred to exclusive sprint (cross-module impact).

## Latest update 2026-02-25 (extractor batch02 follow-up)

- `read_report` ficou com caminho unico de ingestao via `import_excel_robust`.
- para evitar custo excessivo em arquivos grandes no caminho de resultado vazio, foi aplicado gate por tamanho com `SSA_READ_REPORT_FALLBACK_MAX_MB` (default 8).
- parse de env invalido agora cai para default com warning.
- suite focada `tests/test_extracao.py` em 7/7.

## Latest update 2026-02-25 (extractor batch02 cleanup)

- ajuste final: removido trecho de guard de fallback-size que ficou incoerente apos robust-only.
- estado final: `read_report` robust-only, sem fallback legado.

## Latest update 2026-02-25 (batch03 config path alignment)

- `config_manager` agora usa caminho resolvido por env (`SSA_CONFIG_DIR`) de forma consistente tambem em load/save/ensure.
- env de config agora passa por validacao de path safety, com fallback para `config` quando invalido.
- suite focada de config verde (5/5).

## Latest update 2026-02-25 (batch03 fail-fast)

- `ensure_default_settings` agora retorna erro explicito (RuntimeError agregado) quando falha em criar/copi ar arquivos de config.
- cobertura nova valida os dois caminhos de falha (copy e generation).
- status da suite focada de config: 7/7.

## Latest update 2026-02-25 (batch03 startup contract final)

- estado final de `ensure_default_settings`:
  - retorna lista de erros para diagnostico.
  - pode levantar `RuntimeError` quando `fail_fast=True`.
- `main` utiliza modo resiliente (`fail_fast=False`) com warning explicito.

## Latest update 2026-02-25 (batch03 final stabilization)

- `config_manager._atomic_copy_file` agora usa `NamedTemporaryFile(delete=False)`.
- `main` segue com `ensure_default_settings(fail_fast=False)` e warning de erros nao bloqueantes.
- suite focada de config permanece 7/7.

## Latest update 2026-02-25 (batch04 lock retry hardening)

- lock de settings da CLI enhancement recebeu retry limitado e nao bloqueante.
- comportamento em contencao: tenta poucas vezes e aborta sem travar a CLI.
- suite focada lock/atomic da CLI enhancement: 7/7.

## Latest update 2026-02-25 (batch04 windows lock retries)

- melhorias no lock Windows da CLI enhancement: `LK_NBLCK` com retry limitado e fail-fast para erro nao relacionado a lock.
- suite focada lock/atomic da CLI enhancement agora em 9/9.
- qwen foi usado para tarefas repetitivas de validacao; revisao final continuou sob controle do agente principal.

## Latest update 2026-02-25 (batch04 windows lock region normalization)

- lock Windows da CLI enhancement agora usa regiao fixa de 1 byte com retry limitado.
- erro nao relacionado a lock contention no backend Windows nao entra em retry.
- suite lock/atomic da CLI enhancement permaneceu verde em 9/9.

## Latest update 2026-02-26 (batch05+06 sync)

- batch05 (ids 3,14,54,55,57,59,61):
  - `id 3`/`id 59` tratados com patch minimo em `core/app_logic.py` para rastreabilidade de erro inesperado sem mudar fluxo.
  - `id 14/54/55/57/61` classificados como stale-doc com evidencia no codigo/testes atuais.
- batch06 (ids 1,2,32,47,60,75,81):
  - `id 60` recebeu hardening adicional em `armazenamento/database_optimized.py` com quoting estrito de tabela validada.
  - demais ids confirmados como cobertos no estado atual (rollback sem suppress, normalizacao, guardas de identificador).
- teste novo:
  - `tests/test_database_optimized_identifier_guards.py::test_insert_dataframe_optimized_rejects_invalid_table_identifier`
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - pytest focado:
    - `tests/test_import_single_error_classification.py`
    - `tests/test_database_optimized_identifier_guards.py`
    - `tests/test_database_optimized_alias_views.py`
    - `tests/test_command_handlers_save_settings.py`
    - `tests/test_rescan_progress_dialog.py`
    - `tests/test_main_skip_import.py`
    - resultado: 16 passed.

## Latest update 2026-02-26 (batch07.1 ids 53/68)

- id 53:
  - cobertura nova adicionada em `tests/test_caching.py` para garantir reenfileiramento quando `_safe_file_stat` retorna `None`.
- id 68:
  - confirmado contrato atual de `load_display_mappings_integrity` (releitura do arquivo restaurado antes de fallback em memoria).
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados com status `resolved`.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` em arquivos tocados: pass.
  - `pytest -q tests/test_caching.py tests/test_config_manager_mappings_integrity.py`: 8 passed.

## Latest update 2026-02-26 (batch07.2 id 66)

- id 66:
  - `tests/test_rescan_progress_dialog.py` mudou de `processEvents()` unico para espera curta por condicao (`_spin_until`) em pontos sensiveis.
  - objetivo: reduzir nondeterminism/flakiness sem alterar runtime.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - `pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: 6 passed.

## Latest update 2026-02-26 (batch08 id 64)

- id 64:
  - confirmado que cleanup de `gui/workers/rescan_worker.py` nao usa `suppress` e registra warning em falha de detach.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados para `resolved`.
- gate do ciclo:
  - `pytest -q tests/test_rescan_worker_cleanup.py`: 2 passed.

## Latest update 2026-02-26 (batch09-10 ids 62/67/69/72/74/77/78)

- scripts stream:
  - confirmados `nonlocal` correto, lock para contador compartilhado e caminho de sentinel nao bloqueante em v1/v2.
  - guard de warning duplicado (`warn_count != last_warned`) presente em v1/v2.
- config mappings:
  - `load_column_mappings_integrity()` confirmado com releitura de arquivo restaurado antes de fallback.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados para os ids acima.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos scripts de stream: pass.

## Latest update 2026-02-26 (batch11.1 id 8)

- id 8:
  - `FilterCache.put()` agora valida tipo e ignora valor nao-DataFrame sem levantar excecao.
  - docstring de `put()` alinhada ao contrato real.
  - logger do modulo migrado para `get_robust_logger()`.
- testes:
  - novo teste em `tests/test_filter_cache_locking.py` cobrindo entrada invalida.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `py_compile`, `ruff`, `ty` nos arquivos tocados: pass.
  - `pytest -q tests/test_filter_cache_locking.py tests/test_filter_worker.py`: 10 passed.

## Latest update 2026-02-26 (batch12 ids 4/5/73)

- ids 4/5:
  - confirmados como resolvidos pelo contrato atual de `ensure_default_settings` e `_atomic_write_json_file` (erro explicito, sem suppress silencioso).
- id 73:
  - confirmado como resolvido pelo uso de `NamedTemporaryFile(delete=False)` em `_atomic_copy_file`.
- docs:
  - `docs/PENDING_ACTION_MATRIX.md` e `docs/RECOVERY_BACKLOG.md` sincronizados.
- gate do ciclo:
  - `pytest -q tests/test_config_manager_atomic_save.py tests/test_config_manager_mappings_integrity.py tests/test_column_mappings_integrity.py`: 8 passed.

## Latest update 2026-02-26 (global summary + next steps)

- current matrix snapshot:
  - total=108
  - pending=65
  - resolved=27
  - stale-doc=5
  - deferred=11
- security:
  - `main` recebeu hotfix de dependencia (`pillow>=12.1.1` em manifests de build).
  - dependabot open alerts para pillow retornou `[]`.
- next execution queue:
  - extractor validation/contract: ids 6/7/33/34/35/58
  - rescan worker concurrency: ids 11/12/38/79
  - cli enhancement lock residual: ids 13/26/30/31/41/80
  - main fallback/debug resilience: ids 15/16/45/48

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

