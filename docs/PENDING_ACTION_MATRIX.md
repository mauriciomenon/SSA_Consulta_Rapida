# Pending Action Matrix

## CURRENT TRUTH 2026-05-04 01h14

- Branch alvo operacional: `dev` e `main` sincronizados.
- Base minima sincronizada: `4705c2e5722c4f3a5266ac02a5d15a1928d5a223 2026-05-04T02:07:12-03:00 Merge PR #59: sync docs and required CI`; usar este commit ou sucessor sincronizado em `main`/`dev`.
- PR #58 e PR #59: merged.
- PR #56 e PR #57: merged anteriormente; o estado ativo agora e pos-merge do PR #59.
- `main`, `dev`, `origin/main` e `origin/dev` apontam para o mesmo HEAD.
- Artefatos v4.37 anteriores a base minima `4705c2e5722c4f3a5266ac02a5d15a1928d5a223` seguem stale e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
- Orquestradores ativos:
  - Windows AMD64: `dev_env/build/release_windows.ps1`.
  - Debian AMD64: `dev_env/build/release_debian.sh`.
  - Orquestrador local Windows+WSL: `dev_env/build/release_local.ps1`.
- Checks GitHub do merge PR #58:
  - Pass: `minimal-ci`, `Secret Scan`, `codeql-security-scan`, `opencode-pr-review`, `semgrep-cloud-platform/scan`, `security/snyk`, `GitGuardian`, `Socket`, `CodeFactor`, `DeepScan`, `CodeQL`.
  - Externos/advisory: `code/snyk (mauriciomenon)` falhou por limite `Code test limit reached`; `DeepSource: Python` falhou no dashboard externo.
- Protecao de codigo:
  - Nuitka continua backend preferencial para release protegido.
  - PyInstaller tem protecao parcial.
  - PyOxidizer so e aceitavel como protegido quando o pacote nao expuser `.py`/`.pyc` do app.
- Proximo passo operacional: rebuildar Windows AMD64 e Debian AMD64 a partir deste HEAD, validar artefatos e atualizar release v4.37 somente com pacotes novos.

Fonte: docs/RECOVERY_BACKLOG.md
Total itens: 108

## Update 2026-03-26 11:40 (pr46 comment triage sync)

1. Estado operacional confirmado:
   - PR ativo: `#46` (`dev` -> `main`).
   - review threads via API GitHub: `86` unresolved total, `80` atuais nao outdated.
2. Checks externos observados no ciclo:
   - nenhum bloqueio externo confirmado no rollup consultado.
   - `CodeFactor`, `DeepSource`, `CodeQL`, `Snyk`, `Semgrep` e `Socket` estavam em `pass`.
3. Debt de curto prazo mantido:
   - `P0`: blindar storage contra letras na limpeza legacy.
   - `P1`: aliases validos em `_needs_db_only_derivadas_sync`.
   - `P1`: reduzir custo de `sanitize_textual_null_sentinels`.
   - `P2`: convergir helper local de data.

## Update 2026-03-10 (near-term stabilization queue)

1. Mandatory carry-over debt:
   - broad `except Exception` (BLE001) still high in repo.
2. Last measured evidence:
   - total BLE001: `860`.
   - command: `ruff check . --select BLE001`.
   - initial hotspots:
     - `armazenamento/database*.py`
     - `core/app_logic.py`
     - `core/config_manager.py`
     - `dev_env/streamlit_app.py`
3. Execution policy:
   - treat by module in small slices with full gates (`py_compile`, `ruff`, `ty`, focused `pytest`).
   - avoid transversal refactor while reducing masking-risk first.

## Update 2026-03-01 (gui filters + importer stabilization)

1. Completed in this slice:
   - advanced filter action buttons compacted (`Aplicar` / `Limpar`) without global layout rewrite.
   - multiselect popup width constrained and stale-widget guards strengthened.
   - canonical column candidate list cleaned to avoid placeholder/profile noise.
   - deterministic failure caching added for unchanged invalid Excel files.
2. Validation snapshot:
   - `py_compile`, `ruff`, `ty` on touched files: pass
   - focused pytest package: `28 passed`
3. Deferred by scope:
   - structural split of large GUI routines remains deferred (non-blocking).
   - no transversal refactor added in this cycle.

## Update 2026-03-01 (runtime matrix closure + uv docs)

1. Matrix closure:
   - resolved previous inconclusive status for Python version compatibility.
   - validated with isolated uv envs: `3.10.18`, `3.11.14`, `3.12.11`, `3.13.12`.
2. Runtime command standard:
   - document default as `uv run --python 3.13 ...`.
   - document fallback chain `3.12 -> 3.11 -> 3.10`.
3. Compatibility note:
   - keep `requirements*.txt` for non-uv environments only.
4. Reference docs for GUI continuity:
   - `GUI_SSA_REFACTOR_NOTES.md`

## Update 2026-02-28 (streamlit usability slice: layout + discoverability)

1. Streamlit usability improvements delivered:
   - theme selector moved to header top-right (always visible).
   - filters form compacted:
     - situacao moved to optional expander to avoid multi-line overload.
     - executor/emissor keep primary row.
     - row limit moved to dedicated line.
   - columns discoverability improved:
     - quick "Colunas exibidas" shortcut added in table tab.
   - sidebar utilization improved:
     - source status and quick summary metrics added.
2. Validation snapshot:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`36 passed`)
3. Scope note:
   - streamlit layout/ux only.
   - no broad refactor.

## Update 2026-02-28 (id 92 closure: cache architecture micro-refactor)

1. Item `92` moved from `deferred` to `resolved` with minimal-risk refactor:
   - cache internals now use shared helpers for read/store paths.
   - duplicated logic removed between:
     - `get` and `get_cached_filter`
     - `put` and `cache_filter_result`
2. Guardrails preserved:
   - same TTL semantics.
   - same LRU eviction semantics.
   - same stats contract (`hits/misses/evictions/skipped_large_entries`).
   - same max-entry gate (`SSA_CACHE_MAX_MB`).
3. Validation:
   - focused tests expanded in `tests/test_streamlit_filter_cache.py`.
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`38 passed`).

## Update 2026-02-28 (streamlit usability polish v2)

1. Filters now prioritize practical usage:
   - executor/emissor moved to compact single-select with `(Todos)` option.
   - situacao remains visible and supports quick mode + count labels.
   - added explicit `Filtrar agora` button in search row (same submit flow as Enter).
2. Column selection now excludes fully empty columns by default.
3. Sidebar source controls moved into collapsed advanced section (still available).
4. Table rendering improved:
   - dynamic dataframe height based on current page rows to avoid oversized white block.
   - default page size reduced for better first-view density.
5. Validation:
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`40 passed`).

## Update 2026-02-28 (streamlit usability polish v3)

1. Space utilization and alignment improved:
   - executor/emissor keep compact single-select footprint.
   - situacao quick mode moved inline with key filters (no extra full-width row for short text).
   - explicit `Filtrar agora` action stays in search row.
2. Data-source controls moved out of quick sidebar and into hidden advanced section inside `Cache e API`.
3. Table context improved:
   - added top executor and top emissor charts under situacao chart.
4. Validation:
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`40 passed`).

## Update 2026-02-28 (streamlit usability polish v4)

1. Key UX refinements:
   - compacted filter row further and kept quick-mode inline.
   - replaced technical preset labels with business-oriented naming.
   - expanded table context metrics and adjusted dataframe visual container style.
2. Validation:
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`40 passed`).

## Update 2026-02-28 (streamlit theme slice: colors + behavior)

1. Historical limbo request addressed in focused slice:
   - added explicit Streamlit theme palettes with CSS variables.
   - added runtime theme selector in ops tab.
   - theme choice now persists across sessions in Streamlit UI state file.
2. Validation snapshot:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`36 passed`)
3. Scope note:
   - no broad refactor.
   - no PyQt GUI layout change.

## Update 2026-02-28 (sprint D optional P3 delivered + doc hygiene)

1. Optional product items delivered with minimal patch (no layout shift):
   - item `104` moved from `deferred` to `resolved`:
     - width profile memory now persists across sessions via local state file.
   - item `107` moved from `deferred` to `resolved`:
     - render telemetry now persists across sessions via local state file.
2. Validation snapshot (focused):
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`34 passed`)
3. Scope note:
   - no broad refactor and no GUI layout/position change.
4. Doc hygiene note:
   - top update blocks are canonical source of truth.
   - historical blocks below remain for traceability.

## Update 2026-02-28 (sprint D closeout: cache guard + docs sync)

1. Sprint D technical fix closed with minimal patch:
   - matrix item `9` moved from `deferred` to `resolved`.
   - cache entry size guard enabled in:
     - `gui/cache/filter_cache.py`
     - `dev_env/streamlit_app.py`
   - env gate: `SSA_CACHE_MAX_MB` (default unset, keep prior behavior).
   - stats now include:
     - `skipped_large_entries`
     - `max_entry_mb`
2. Focused validation for this closeout:
   - `uv run --python 3.13 python -m py_compile gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass (`32 passed`)
3. Scope note:
   - no GUI layout/position change in this slice.
   - no broad refactor; structural items stay deferred.
4. Deferred classification with difficulty (after optional delivery):
   - item `84` (`SSAMainWindow split`) and item `101` (`streamlit god-module split`): structural (P2), difficulty `alta`.

## Update 2026-02-28 (sprint long-loop v2: runtime hardening micro-slices)

1. Runtime micro-fixes delivered with minimal risk:
   - `interface/command_handlers.py`:
     - settings save message now prints the resolved settings path.
     - unexpected save failure now emits explicit terminal feedback.
   - `armazenamento/database_optimized.py`:
     - UPDATE path now validates and quotes update-column identifiers before SQL assembly.
   - `main.py`:
     - optimized-mode cleanup no longer silently ignores missing `disable_optimized_import`; now logs debug evidence.
2. Focused tests updated:
   - `tests/test_command_handlers_save_settings.py` (resolved settings path assertion)
   - `tests/test_database_optimized_identifier_guards.py` (identifier quote guard)
3. Validation evidence:
   - command handlers suite: `10 passed`
   - database optimized guards/aliases: `6 passed`
   - main import fallback/skip suite: `3 passed`
   - touched-scope `py_compile`, `ruff`, `ty`: pass
4. Kluster evidence:
   - all `kluster_code_review_auto` runs in this loop: clean

## Update 2026-02-28 (sprint long-loop: grave queue triage lock for config/extractor)

1. High-risk queue items validated as already covered in runtime/tests:
   - `core/config_manager.py`:
     - atomic temp cleanup path keeps explicit warnings (no silent suppress).
     - mappings integrity restore path falls back to in-memory defaults without CLI crash.
     - post-restore behavior reads restored content when available.
   - `extracao/extractor.py`:
     - extraction path uses `with pd.ExcelFile(...)` (handle-safe).
     - return contract is `pd.DataFrame` (empty allowed) with `ExtractionError` on extraction failures.
2. Validation evidence:
   - `uv run pytest -q tests/test_config_manager_mappings_integrity.py tests/test_config_manager_atomic_save.py tests/test_extracao.py`: `18 passed`
   - touched-scope `py_compile`, `ruff`, `ty`: pass
3. Queue policy for next slices:
   - prioritize remaining unresolved runtime-risk IDs only.
   - keep stale-doc/duplicate pending references out of active closure counts.

## Update 2026-02-28 (sprint 25 graves v5: closure docs + local release bump)

1. Continuity closure completed in this cycle:
   - handoff top blocks synchronized in:
     - `docs/NEXT_CHAT_MIGRATION.md`
     - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - local release bumped by +0.1:
     - `VERSION`: `4.24.0 -> 4.25.0`
     - `config/version.json`: `version_short=4.25`, `version_long` synced
     - `README.md` + `docs/HISTORICO_RELEASES.md` synced to `v4.25.0`
2. Runtime scope note:
   - no additional GUI layout/position change in this closure slice.
   - no new runtime patch beyond already delivered 25 graves v4 package.
3. Queue state for next sprint decision:
   - keep prioritization by real risk and focused regression gaps.
   - continue from matrix/backlog entries not yet converted into validated slices.

## Update 2026-02-28 (sprint 25 graves v4: command handlers + importer + stream wrappers)

1. Delivered additional high-risk micro-fixes (batch extension):
   - `interface/command_handlers.py`:
     1. added mapping path validation helper.
     2. blocked traversal-style mapping names.
     3. enforced `.json` extension for mapping loads.
     4. mapping file path now resolves through centralized config resolver.
     5. wrapped `load_display_mappings_integrity` call with guarded fallback.
     6. mapping cache is cleared after successful settings save.
     7. `_attempt_save_settings` now handles unexpected exceptions with logging.
   - `core/app_logic.py`:
     8. cancel callback is now checked immediately after extraction.
     9. explicit guard for extractor returning `None`.
     10. extractor error normalization now keeps safe fallback text when empty.
     11. explicit `except ExtractionError` keeps local contract unchanged.
   - `scripts/pytest_stream_common.py`:
     12. added `reader_join_timeout_seconds()` parser.
     13. added env key `PYTEST_STREAM_READER_JOIN_TIMEOUT_MS`.
     14. parser clamps join timeout to safe bounds.
     15. timeout path uses configurable reader-join timeout.
     16. normal exit path uses configurable reader-join timeout.
     17. exception path uses configurable reader-join timeout.
2. Focused regressions added/updated:
   - `tests/test_command_handlers_load_mappings.py`
   - `tests/test_command_handlers_save_settings.py`
   - `tests/test_import_single_error_classification.py`
   - `tests/test_stream_log_wrapper_guards.py`
3. Validation evidence:
   - touched-scope `py_compile`, `ruff`, `ty`: pass
   - focused pytest package:
     - `tests/test_rescan_progress_dialog.py`
     - `tests/test_gui_workers_rescan_data.py`
     - `tests/test_stream_log_wrapper_guards.py`
     - `tests/test_command_handlers_load_mappings.py`
     - `tests/test_command_handlers_save_settings.py`
     - `tests/test_import_single_error_classification.py`
     - `tests/test_import_cancel_before_insert.py`
   - result: `30 passed`
4. Kluster evidence:
   - `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 20 graves v3: rescan + stream robustness)

1. Delivered 20 high-risk micro-fixes in minimal scope:
   - `gui/widgets/rescan_progress_dialog.py`:
     1. `set_finished(...)` became idempotent.
     2. duplicate finish events no longer overwrite prior terminal status.
     3. cancel flow remains "request cancel first".
     4. close remains blocked while running.
   - `gui/ssa/gui_workers.py`:
     5. prune retired rescan workers before starting new run.
     6. active worker gate uses running helper path.
     7. stale active worker ref is cleared before new run.
     8. cancel status text is set even when worker is already not running.
     9. metadata timestamp is refreshed when worker is still running after dialog.
     10. worker cap prunes matching metadata for dropped workers.
     11. prune is re-run when dialog exits and worker is not running.
   - `scripts/pytest_stream_common.py`:
     12. added `queue_poll_timeout_seconds()` parser.
     13. added env key `PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS`.
     14. queue poll timeout now bounded (20..2000 ms).
     15. main loop now uses configurable queue poll timeout.
     16. break fast when process done and sentinel seen.
     17. break fast when process done, reader done, and queue empty.
     18. dropped warning cadence remains deterministic with interval parser.
     19. sentinel path excluded from dropped-line counting.
     20. warning cadence no longer depends on fixed magic constant.
2. Focused tests added/updated:
   - `tests/test_rescan_progress_dialog.py`
   - `tests/test_gui_workers_rescan_data.py`
   - `tests/test_stream_log_wrapper_guards.py`
3. Validation evidence:
   - touched-scope `py_compile`, `ruff`, `ty`: pass
   - `uv run pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py tests/test_stream_log_wrapper_guards.py`: pass (`15 passed`)
4. Kluster evidence:
   - `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 10 graves v2: rescan dialog/worker + stream wrapper)

1. Delivered high-risk minimal fixes:
   - `gui/widgets/rescan_progress_dialog.py`: `reject()` no longer closes while process is still running; close remains allowed only after `set_finished(...)`.
   - `gui/ssa/gui_workers.py`: active rescan worker check now uses `is_rescan_worker_running(...)` helper and clears stale active ref before new run.
   - `gui/ssa/gui_workers.py`: global worker cap now removes metadata for dropped workers.
   - `scripts/pytest_stream_common.py`: added `PYTEST_STREAM_DROPPED_WARN_EVERY` parser/clamp and predictable warning cadence.
   - `scripts/pytest_stream_common.py`: sentinel path no longer increments dropped-line counters.
2. Focused regressions added/updated:
   - `tests/test_rescan_progress_dialog.py`
   - `tests/test_gui_workers_rescan_data.py`
   - `tests/test_stream_log_wrapper_guards.py`
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile` on touched scope: pass
   - `uv run ruff check` on touched scope: pass
   - `uv run ty check` on touched scope: pass
   - `uv run pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py tests/test_stream_log_wrapper_guards.py`: pass (`12 passed`)
4. Kluster evidence:
   - `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 10 graves: config/lifecycle/streamlit hardening)

1. Delivered 10 high-risk minimal fixes:
   - `gui/gui_config.py`: added runtime path resolver API (`get_gui_main_preferences_path`) and made loader use dynamic path resolution.
   - `tests/test_gui_main_configuration.py`: added regression for runtime `SSA_CONFIG_DIR` path reflection.
   - `tests/test_gui_main_configuration.py`: added regression for explicit `config_path` precedence over env.
   - `dev_env/streamlit_app.py`: width-profile memory now accepts only known bucket keys.
   - `dev_env/streamlit_app.py`: viewport hint <= 0 now falls back to profile width baseline.
   - `tests/test_streamlit_filter_cache.py`: regression for invalid bucket memory filtering.
   - `tests/test_streamlit_filter_cache.py`: regression for non-positive viewport fallback.
   - `dev_env/streamlit_app.py`: API snapshot clear helper made explicit idempotent guard.
   - `tests/test_streamlit_filter_cache.py`: regression for idempotent clear without existing key.
   - `gui/gui_ssa.py`: closeEvent rescan shutdown now keeps defensive stop/quit path when worker was globally retained; running checks use helper path.
2. Additional regression:
   - `tests/test_gui_filter_logic.py`: closeEvent tracks running helper usage under unstable `isRunning` behavior.
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile gui/gui_config.py dev_env/streamlit_app.py gui/gui_ssa.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py tests/test_gui_filter_logic.py`: pass
   - `uv run ruff check` on same scope: pass
   - `uv run ty check` on same scope: pass
   - `uv run pytest -q tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py tests/test_gui_filter_logic.py`: pass (`150 passed, 1 skipped`)
4. Kluster evidence:
   - `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 5 slices graves: lifecycle/config/canonical/api)

1. Delivered 5 high-risk minimal slices:
   - `gui/gui_ssa.py`: rescan global retention cap now cleans dropped-worker metadata and refreshes timestamp on retain.
   - `tests/test_gui_filter_logic.py`: new regressions for global cap/meta consistency and canonical column candidate behavior with non-null cache.
   - `tests/test_gui_main_configuration.py`: new fallback regression when `SSA_CONFIG_DIR` points to missing dir.
   - `dev_env/streamlit_app.py`: unified helper for clearing API snapshot state.
   - `tests/test_streamlit_filter_cache.py`: new regression for API snapshot clear helper.
2. Validation evidence:
   - `uv run --python 3.13 python -m py_compile gui/gui_ssa.py dev_env/streamlit_app.py tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check gui/gui_ssa.py dev_env/streamlit_app.py tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check gui/gui_ssa.py dev_env/streamlit_app.py tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_streamlit_filter_cache.py`: pass (`145 passed, 1 skipped`)
3. Kluster evidence:
   - `kluster_code_review_auto` runs in this sprint package: clean

## Update 2026-02-28 (streamlit slice: width-profile memory + tabs/api smoke)

1. Delivered item 2 first (as requested), then item 1:
   - item 2: width-profile memory by width bucket in `dev_env/streamlit_app.py` with no layout/position change.
   - item 1: tabs/API smoke hardening via stable tab-label constant and API snapshot availability helper.
2. Added focused regressions in `tests/test_streamlit_filter_cache.py`:
   - width bucket thresholds
   - width-profile memory normalization
   - resolve/remember profile by bucket
   - stable tab labels
   - API snapshot permutations
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`21 passed`)
4. Kluster evidence:
   - `kluster_code_review_auto` on touched files: clean

## Update 2026-02-28 (streamlit slice: telemetry profile window cap)

1. Delivered minimal streamlit stabilization slice in `dev_env/streamlit_app.py`:
   - render telemetry now enforces a profile window cap to avoid unbounded growth in session state.
2. Added focused regression:
   - `tests/test_streamlit_filter_cache.py::test_update_render_telemetry_keeps_profile_window`.
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`16 passed`)

## Update 2026-02-28 (kluster package: config hierarchy + closeevent lifecycle)

1. Delivered runtime hardening for 2 kluster findings:
   - `gui/gui_config.py`: GUI preferences path now honors `SSA_CONFIG_DIR` with safe fallback.
   - `gui/gui_ssa.py`: `closeEvent` now has defensive global retention fallback for active rescan worker.
2. Added focused regressions:
   - `tests/test_gui_main_configuration.py::test_load_gui_main_preferences_honors_ssa_config_dir`
   - `tests/test_gui_filter_logic.py::test_close_event_retains_rescan_worker_when_isrunning_check_fails_mid_shutdown`
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile` (touched files): pass
   - `uv run ruff check` (touched files): pass
   - `uv run ty check` (touched files): pass
   - focused `pytest`: pass
4. Matrix status:
   - no immediate `pending` rows; active pending queue remains empty.

## Update 2026-02-27 (residual main-config-gui closeout)

1. Closed residual runtime group in this continuity slice:
   - `39, 46, 49, 50, 70, 76` moved to `resolved`.
2. Evidence baseline used for closeout:
   - local validation for touched runtime/tests had already been rerun and green;
   - kluster auto on touched runtime files was clean;
   - targeted tests for closeEvent/worker retention/cancel contract are present and passing.
3. Active queue after this closeout:
   - `9, 21, 22, 23, 24, 25, 27` (test/perf residuals).

## Update 2026-02-27 (id 27 closure)

1. `27` moved to `resolved`:
   - `tests/test_import_cancellation.py` now asserts full `finish` payload contract, including `errors`.
2. Validation evidence:
   - `uv run --python 3.13 python -m py_compile tests/test_import_cancellation.py`: pass
   - `uv run ruff check tests/test_import_cancellation.py`: pass
   - `uv run ty check tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancel_before_insert.py`: pass
3. Active queue now:
   - `9, 21, 22, 23, 24, 25`.

## Update 2026-02-27 (ids 22-23 closure)

1. `22` moved to `resolved`:
   - tests now assert explicit success contract of `initialize_database(...)`.
2. `23` moved to `resolved`:
   - db temp files are explicitly removed in `finally` and test scope remains under `tmp_path`.
3. Validation evidence:
   - `uv run --python 3.13 python -m py_compile tests/test_database_optimized_alias_views.py`: pass
   - `uv run ruff check tests/test_database_optimized_alias_views.py`: pass
   - `uv run ty check tests/test_database_optimized_alias_views.py`: pass
   - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass
4. Active queue now:
   - `9, 21, 24, 25`.

## Update 2026-02-27 (id 21 closure)

1. `21` moved to `resolved`:
   - concurrent write scenario is already covered by `test_save_cache_concurrent_writes_remain_valid_json`.
2. Validation evidence:
   - `uv run pytest -q tests/test_caching_atomic_save.py`: pass
3. Active queue now:
   - `9, 24, 25`.

## Update 2026-02-27 (ids 24-25 closure)

1. `24` moved to `resolved`:
   - lock test asserts per-operation enter/exit increments and balanced lock exit.
2. `25` moved to `resolved`:
   - test patching was hardened to `patch.object(mixin_module.QMessageBox, "critical")`.
3. Validation evidence:
   - `uv run pytest -q tests/test_filter_cache_locking.py`: pass
   - `uv run pytest -q tests/test_filter_error_skips_modal_in_pytest.py`: pass
4. Active queue now:
   - `9`.

## Update 2026-02-27 (id 9 deferred by explicit decision)

1. `9` moved to `deferred` by explicit user decision (Opcao A).
2. Decision rationale:
   - keep current cache copy semantics to avoid behavioral risk in shared mutable data paths.
   - no runtime/perf patch in this cycle.
3. Active queue now:
   - none in this matrix (`pending` = 0).
4. Historical note:
   - this snapshot was superseded in Sprint D closeout (`9` moved to `resolved`).

## Update 2026-02-27 (continuity triage closeout)

1. Validation status for interrupted runtime patch:
   - local gates rerun and green (`py_compile`, `ruff`, `ty`, focused `pytest`).
   - focused pytest result:
     - `121 passed, 1 skipped`.
   - kluster auto on touched runtime files: clean.
2. Continuation rule:
   - runtime files from interrupted patch remain in active scope, but now validated.
   - next status change to `resolved` must happen only after next code slice completion and rerun evidence.

## Update 2026-02-27 (pending triage closure for ids 42/43/44)

1. `42` moved to `resolved`:
   - cancel contract path was reinforced and locked in tests:
     - `tests/test_import_cancel_before_insert.py`
     - `tests/test_import_cancellation.py`
     - `tests/test_import_derivadas_trigger.py::test_run_importer_skips_db_only_preflight_when_cancel_requested`
2. `43` moved to `stale-doc`:
   - metadata-only comment without reproducible bug in current `gui/mixins/filter_gui_ssa_mixin.py` line context.
3. `44` moved to `stale-doc`:
   - referenced line `gui/gui_ssa.py:5094` is outside current file size; current source moved/reshaped.

## Update 2026-02-27 (pending triage closure for 56 and 82-97)

1. `56` moved to `resolved`:
   - test isolation was hardened by replacing class-level mutable collector with per-test local collector in `tests/test_open_docs_folder_nonblocking.py`.
2. `82-97` moved to `deferred`:
   - all are backlog-level generic items without file/line anchors in current cycle;
   - kept for dedicated sprint planning, out of minimal-risk stabilization slices.

## Update 2026-02-27 (continuation sync after interrupted chat)

1. Operational state:
   - chat was interrupted after local runtime patch and before final validation closeout.
   - continuity docs were synchronized to preserve exact restart context.
2. Runtime files currently in pending validation state:
   - `gui/ssa/gui_filters_advanced_ui.py`
   - `gui/mixins/filter_gui_ssa_mixin.py`
   - `gui/widgets/column_manager_dialog.py`
   - `gui/gui_ssa.py`
   - `gui/ssa/gui_workers.py`
3. Required next actions before marking related items as resolved:
   - run kluster auto on touched files;
   - run `python -m py_compile`, `ruff check`, `ty check`, and focused `pytest`;
   - update row statuses based on validation evidence.

## Update 2026-02-26 (status + alias audit sync)

1. Completed:
   - filter status format consistency in clear flows (`SSAs filtradas: N de M`);
   - column-filter footer button style parity in SSA tab;
   - active docs sync rerun.
2. DB alias audit snapshot (`ssa_table` vs display mapping):
   - total columns: 82
   - mapped: 71
   - unmapped: 11
3. Unmapped DB fields (fallback to DB name in UI when exposed):
   - `id`
   - `total_tempo_tpe_executada`
   - `registros_espera`
   - `num_reprobaciones`
   - `situacao_espera`
   - `numero_desvios`
   - `ate`
   - `justificativa`
   - `total_tempo_tex_executada`
   - `parciais`
   - `situacao_da_parcial`

## Update 2026-02-26 (operational sync)

Status snapshot after latest test/doc cycle:
- pending: 31
- resolved: 60
- stale-doc: 6
- deferred: 11

What was addressed in this cycle:
1. Added missing regression tests for column-filter behavior in `tests/test_gui_filter_logic.py`.
2. Synced active release/docs baseline to `4.22.0` (`README.md`, `docs/HISTORICO_RELEASES.md`, `docs/FILTER_TAB_OPTIMIZATIONS.md`).
3. Synced handoff/migration docs with authoritative active branch block.

Active queue remains:
1. Resolve open runtime-risk items first (if any remain).
2. Keep `[deferred]` items for dedicated sprint only.

Legenda:
- Solucao proposta: caminho recomendado de menor risco
- Opcao: usado quando ha duvida de escopo/arquitetura

## 1. [resolved] armazenamento/database_optimized.py:349
- Item: **Potential Data Integrity Issues During Batch Update (Delete + Insert):** The batch update strategy deletes existing records before inserting updated ones. If the table has for...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: fluxo segue dentro de SAVEPOINT com rollback explicito; cobertura focada de upsert otimizado mantida verde.

## 2. [resolved] armazenamento/database_optimized.py:346
- Item: **Error Handling During Rollback May Mask Critical Failures:** The rollback logic uses `with suppress(Exception):` when rolling back to the savepoint. This may hide errors durin...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.
- Evidencia: rollback atual nao usa suppress; falha de rollback e logada com contexto.

## 3. [resolved] core/app_logic.py:297
- Item: **Loss of Error Type Specificity in Exception Handling** In the `_import_single_file` function, the generic exception handler wraps all exceptions as `ExtractionError`: ```pytho...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: erro inesperado agora inclui tipo original (`RuntimeError`, etc) na mensagem e log com stack.

## 4. [resolved] core/config_manager.py:549
- Item: **Silent Failure on Default Settings Creation** If the creation of a default configuration file fails (e.g., due to permission issues or disk errors), the error is only logged a...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.
- Evidencia: `ensure_default_settings()` acumula erros e pode levantar `RuntimeError` em modo `fail_fast=True`.

## 5. [resolved] core/config_manager.py:44
- Item: **Suppressed Exceptions in Atomic File Operations** In the `_atomic_write_json_file` function, exceptions during file descriptor closing and temporary file removal are suppresse...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.
- Evidencia: cleanup de `_atomic_write_json_file` registra warning explicito em falha de close/remove (sem suppress silencioso).

## 6. [resolved] extracao/extractor.py:259
- Item: After detecting the header row and extracting data, the function does not validate that all required columns are present in the resulting DataFrame. This could lead to downstrea...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.
- Evidencia: `extract_data_from_excel` valida `required_columns` e levanta `ExtractionError` quando faltar coluna obrigatoria.

## 7. [resolved] extracao/extractor.py:306
- Item: The code loads column mappings with `_load_column_mappings()` and applies them to the DataFrame. If the mapping is empty (e.g., due to a loading error), columns will not be rena...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.
- Evidencia: mapeamento vazio mantem colunas originais e ainda falha cedo por `required_columns`; teste focado adicionado.

## 8. [resolved] gui/cache/filter_cache.py:50
- Item: **Potential Exception Risk:** The method `result.copy()` is called without verifying that `result` is a valid DataFrame. If the cached object is not a DataFrame or is `None`, th...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `FilterCache.put()` valida `isinstance(result, pd.DataFrame)` e ignora entrada invalida com warning; teste focado adicionado.

## 9. [resolved] gui/cache/filter_cache.py:59
- Item: **Performance Concern:** The cache always stores a copy of the DataFrame (`result.copy()`) on every put. For large DataFrames, this can be expensive in both time and memory, esp...
- Solucao proposta: Aplicar guarda de tamanho por entrada com env configuravel, sem alterar comportamento padrao quando env estiver ausente.
- Evidencia: guard implementado em GUI e Streamlit com `SSA_CACHE_MAX_MB`, contador `skipped_large_entries` e regressao focada.

## 10. [resolved] gui/widgets/rescan_progress_dialog.py:143
- Item: The `reject` method allows the dialog to close immediately after a cancel request, even if the underlying rescan process has not yet stopped. This could lead to user confusion o...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: `reject()` atual mantem dialogo aberto na primeira tentativa de cancelamento e emite sinal de cancelamento uma vez.

## 11. [resolved] gui/workers/rescan_worker.py:132
- Item: ### Potential Logger Handler Race Condition The logger handler is added and removed within the worker thread (lines 96, 130), but if multiple threads use the same logger ('ssa')...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: attach/detach usa lock global e refcount; testes focados de cleanup/rescan estao verdes.

## 12. [resolved] gui/workers/rescan_worker.py:143
- Item: ### Cancellation Responsiveness Depends on `run_importer_logic` The cancellation logic relies on `run_importer_logic` invoking the `should_cancel` callback frequently (line 107)...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: worker passa callback `should_cancel`; cenarios de cancelamento e cleanup validados por testes focados.

## 13. [resolved] interface/cli_enhancement_manager.py:134
- Item: **Potential Data Race in _save_settings:** The `_save_settings` method uses best-effort file locking via `_lock_file_if_possible`, but this approach may not reliably prevent con...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: lock agora usa lockfile dedicado (`settings_file.lock`) e fluxo de lock nao bloqueante com retry limitado.

## 14. [stale-doc] interface/command_handlers.py:28
- Item: **Overly broad exception handling in `_save_settings_handler`:** Catching all exceptions and only printing the error message does not allow for proper error tracking or programm...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: handler atual captura conjunto explicito, faz logger.exception e re-raise.

## 15. [resolved] main.py:759
- Item: ### Critical Issue: Incomplete Failure Handling for Optimized and Legacy Import Modes If both the optimized import (`enable_optimized_import`) and the legacy import logic fail, ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: fluxo registra falha otimizada com contexto completo e fail-fast deterministico, sem retry legado automatico, coberto por teste focado.

## 16. [resolved] main.py:591
- Item: ### Performance Issue: Directory Listing in Debug Mode In the block that lists files in important directories (lines 569-605), if any of these directories contain a large number...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: listagem debug usa `_debug_listdir_preview` com `itertools.islice` e limite de preview.

## 17. [resolved] scripts/run_pytest_stream_and_log.py:119
- Item: The warning about dropped lines is only emitted when `dropped_lines % 200 == 1`, which may result in infrequent warnings during periods of high output loss. This could obscure t...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: contagem de drop/warning foi movida para helper compartilhado com regra unica e warning via logger robusto.

## 18. [resolved] scripts/run_pytest_stream_and_log.py:84
- Item: The queue size for `line_queue` is hardcoded to 4096. This may not be optimal for all environments or workloads, potentially leading to unnecessary output loss or excessive memo...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: tamanho da queue segue configuravel por env (`PYTEST_STREAM_QUEUE_MAX`) no helper compartilhado.

## 19. [resolved] scripts/run_pytest_stream_and_log_v2.py:140
- Item: **Potential Data Race on `dropped_lines`** The `dropped_lines` variable is incremented in both the main thread and the reader thread without synchronization. This can lead to a ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: atualizacao de `dropped_lines` e decisao de warning estao serializadas por lock unico no runner comum.

## 20. [resolved] scripts/run_pytest_stream_and_log_v2.py:163
- Item: **Busy-Wait Loop for Sentinel Delivery** The loop that ensures the sentinel (`None`) is delivered to the queue (`while True: ... time.sleep(0.005)`) can result in unnecessary CP...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: envio de sentinel agora e best-effort nao bloqueante e fechamento usa `reader_done` + estado do processo.

## 21. [resolved] tests/test_caching_atomic_save.py:30
- Item: **Missing test for concurrent writes:** The test `test_save_cache_is_atomic_and_does_not_corrupt_existing_file` only simulates a single failure mode (exception during write) and...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: cobertura concorrente existe em `test_save_cache_concurrent_writes_remain_valid_json` e valida JSON final consistente apos multiplas gravacoes simultaneas.

## 22. [resolved] tests/test_database_optimized_alias_views.py:15
- Item: The test does not handle errors that may occur during database initialization (e.g., missing or invalid 'config/schema.sql'). This could result in unclear test failures. **Recom...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: ambos os testes validam retorno de `database.initialize_database(...)` com `assert init_ok is True`.

## 23. [resolved] tests/test_database_optimized_alias_views.py:35
- Item: The test creates a database file but does not explicitly remove it after execution. This may leave residual files in the test environment, affecting test isolation and potential...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: ambos os cenarios removem o arquivo de banco no `finally` com `Path(db_path).unlink(missing_ok=True)`.

## 24. [resolved] tests/test_filter_cache_locking.py:28
- Item: **Insufficient Verification of Lock Usage** The assertion `assert spy.enter_count >= 1` (line 28) only verifies that the lock was entered at least once, but does not ensure that...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: teste valida incrementos por operacao (`put/get/get_stats/clear`) e garante `enter_count == exit_count`.

## 25. [resolved] tests/test_filter_error_skips_modal_in_pytest.py:30
- Item: The patch target `"gui.mixins.filter_gui_ssa_mixin.QMessageBox.critical"` is tightly coupled to the import path and structure of the module under test. If the import path or the...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: teste usa `patch.object(mixin_module.QMessageBox, "critical")` e valida comportamento sem modal em pytest.

## 26. [resolved] interface/cli_enhancement_manager.py:24
- Item: **suggestion (bug_risk):** File locking is applied to the temp file, so it doesnt actually coordinate concurrent writers on the real settings file. In `_save_settings`, locking ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: lock e aplicado ao lockfile estavel do recurso real, nao ao tempfile de escrita atomica.

## 27. [resolved] tests/test_import_cancellation.py:65
- Item: **suggestion (testing):** Fortalea o teste verificando tambm o payload final de progresso "finish" Como `run_importer_logic` agora normaliza e protege `progress_callback`, captu...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: teste agora valida `finish_payload["errors"] == []` junto de `total` e `processed`.

## 28. [resolved] tests/test_rescan_progress_dialog.py:28
- Item: **suggestion (testing):** Estenda as asseres para cobrir o estado da UI aps o cancelamento (texto de status e estados habilitado/desabilitado dos botes) Como `reject()` e `set_f...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: testes atuais cobrem estado de UI apos cancelamento (status, botoes, visibilidade e fechamento).

## 29. [resolved] tests/test_rescan_worker_cleanup.py:27
- Item: **suggestion (testing):** Considere exercitar tambm o caminho de sucesso para comprovar que os handlers so liberados no caso sem erro Para validar completamente o novo cleanup n...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: suite inclui caminho de falha e caminho de sucesso para liberacao de logger/refcount.

## 30. [resolved] interface/cli_enhancement_manager.py:100
- Item: O lock aplicado em _save_settings() est sendo feito no arquivo temporrio recm-criado. Isso no serializa gravaes concorrentes para o mesmo settings_file (cada processo trava seu ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: escrita atomica permanece em tempfile, mas serializacao ocorre via lockfile compartilhado.

## 31. [resolved] interface/cli_enhancement_manager.py:93
- Item: _lock_file_if_possible() usa flock LOCK_EX (bloqueante) em POSIX. Se outro processo ficar segurando o lock, essa chamada pode travar a CLI indefinidamente. Para manter 'best-eff...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: backend POSIX usa `LOCK_EX | LOCK_NB` com retries limitados e aborta sem bloqueio indefinido.

## 32. [resolved] armazenamento/database_optimized.py:237
- Item: existing_dict montado a partir de chunk_df['numero_ssa'] sem normalizao de tipo, mas has_ssa['numero_ssa'] foi normalizado para str. Como SQLite pode conter valores antigos com...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: lookup atual normaliza `numero_ssa` no chunk retornado e no conjunto consultado.

## 33. [resolved] extracao/extractor.py:214
- Item: A anotao de retorno ainda est como Optional[pd.DataFrame], mas a funo agora retorna DataFrame (incluindo vazio) e levanta ExtractionError nos erros (no retorna None). Ajuste a a...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.
- Evidencia: assinatura atual retorna `pd.DataFrame`; teste focado cobre retorno vazio sem `None`.

## 34. [resolved] extracao/extractor.py:223
- Item: A docstring ainda diz que retorna None em caso de erro, mas o fluxo agora levanta ExtractionError (e retorna DataFrame vazio quando h cabealho mas sem linhas). Atualize a seo Re...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.
- Evidencia: docstring atual indica retorno `pd.DataFrame`; caminho de erro levanta `ExtractionError`.

## 35. [resolved] extracao/extractor.py:236
- Item: pd.ExcelFile() criado mas no fechado explicitamente. Para evitar vazamento de handle/arquivo (especialmente em loops de muitos arquivos), use um context manager (with pd.Excel...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.
- Evidencia: uso atual de `with pd.ExcelFile(...)` garante fechamento de recurso.

## 36. [resolved] core/config_manager.py:443
- Item: load_display_mappings_integrity() passou a levantar RuntimeError se falhar ao restaurar o arquivo, alterando o comportamento anterior (que retornava DEFAULT_DISPLAY_MAPPINGS mes...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: funcao retorna `DEFAULT_DISPLAY_MAPPINGS.copy()` em falha de restore e teste cobre write-failure sem crash.

## 37. [resolved] core/config_manager.py:474
- Item: load_column_mappings_integrity() agora levanta RuntimeError ao falhar em restaurar o arquivo, o que pode interromper a aplicao em ambientes sem permisso de escrita. Para preserv...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: funcao retorna `DEFAULT_COLUMN_MAPPINGS.copy()` em falha de restore e teste cobre write-failure sem crash.

## 38. [resolved] gui/workers/rescan_worker.py:125
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 1\. <b><i>rescanworker</i></b> exposes raw exception <code> R...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: excecao e logada internamente com stack e emitida para UI com prefixo controlado (`Erro ao executar reescaneamento:`).

## 39. [resolved] gui/gui_ssa.py:6674
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 2\. Rescan thread may outlive app <code> Bug</code> <code> Re...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `closeEvent` encerra worker com `stop -> quit -> wait` e fallback `terminate -> wait`, limpa `_active_rescan_worker` em `finally`, com teste focado em `tests/test_gui_filter_logic.py`.

## 40. [resolved] core/config_manager.py:454
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 3\. Config restore can crash cli <code> Bug</code> <code> Rel...
- Solucao proposta: Fallback controlado: tentar restaurar, se falhar retornar defaults com aviso claro sem crash.
- Evidencia: fallback controlado preservado e travado por `tests/test_config_manager_mappings_integrity.py`.

## 41. [resolved] interface/cli_enhancement_manager.py:88
- Item: ![medium](https://www.gstatic.com/codereviewagent/medium-priority.svg) The file lock is being applied to the temporary file created by `mkstemp`. Since each process creates a un...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: lockfile do alvo e aberto antes da gravacao atomica e fechamento e tratado em `finally`.

## 42. [resolved] core/app_logic.py:450
- Item: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes:\n\n1. `_import_single_file` now accepts `s...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: cancelamento coberto em `_import_single_file`/`run_importer_logic` e travado por testes focados (`test_import_cancel_before_insert`, `test_import_cancellation`, `test_run_importer_skips_db_only_preflight_when_cancel_requested`).

## 43. [stale-doc] gui/mixins/filter_gui_ssa_mixin.py:343
- Item: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"bash","input":{"command":"rg -n '^import os' gui/mixins/filter_gui_ssa_mixin.py; rg -n 'import os' gu...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: comentario truncado de metadata sem issue reproduzivel no contexto atual da linha; modulo permanece funcional e coberto por gates do slice.

## 44. [stale-doc] gui/gui_ssa.py:5094
- Item: <!-- metadata:{"confidence":7,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes in this PR:\n\n1. Import of `atomic_write_j...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: referencia de linha fora do arquivo atual (`gui/gui_ssa.py` tem 2819 linhas no estado atual); item nao e mais ancoravel no codigo vigente.

## 45. [resolved] main.py:487
- Item: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully for issues:\n\n1. **Non-ASCII characters...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: mensagem de nivel de log invalido foi normalizada para ASCII e conflito de flags segue com erro explicito.

## 46. [resolved] extracao/extractor.py:214
- Item: **P1** | Confidence: High The function signature now includes a `should_cancel` callback. The related context shows the primary caller, `run_importer_logic` in `core/app_logic.p...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: `extract_data_from_excel` consulta `should_cancel` antes de IO e contrato foi travado por `tests/test_extracao.py::test_extract_data_from_excel_respects_cancel_callback_before_io`.

## 47. [resolved] armazenamento/database_optimized.py:167
- Item: **P1** | Confidence: High The addition of SQL identifier validation (`is_valid_identifier`) is a critical security improvement to prevent injection via the `table_name` paramete...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: validacao de identificador segue ativa e testada.

## 48. [resolved] main.py:480
- Item: **P2** | Confidence: High Speculative: The validation logic for conflicting CLI flags `--skip-import` and `--force-rescan` is sound. However, the error message references `--res...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: caminho `--version` simplificado sem `except` amplo e alias `--rescan` permanece consistente no parser.

## 49. [resolved] core/app_logic.py:330
- Item: **[Contextual Comment]** _This comment refers to code near real line 325. Anchored to nearest_changed(328) line 328._ --- **P1** | Confidence: High `run_importer_logic` now has ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `run_importer_logic` aplica cancel antes do preflight db-only e emite `finish` no retorno por cancel; cobertura em `tests/test_import_derivadas_trigger.py` e `tests/test_import_cancellation.py`.

## 50. [resolved] gui/gui_ssa.py:6434
- Item: _ Potential issue_ | _ Critical_ <details> <summary> Analysis chain</summary> Script executed: ```shell #!/bin/bash # Get RescanWorker implementation to understand signal timin...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: retencao global de worker no fechamento foi reforcada no fluxo atual com fallback e limpeza deterministica, com regressao em `tests/test_gui_filter_logic.py`.

## 51. [resolved] scripts/run_pytest_stream_and_log_v2.py:195
- Item: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 155-167, the warning is enqueued before the real output. When the queue is fu...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: aviso de queue cheia saiu da fila de output e passou a ser logado por logger robusto.

## 52. [resolved] scripts/run_pytest_stream_and_log.py:153
- Item: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 116-128, the warning is enqueued before the real output. With a full queue, e...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: mesmo ajuste aplicado no caminho v1 via `pytest_stream_common.py`.

## 53. [resolved] utils/caching.py:154
- Item: _ Potential issue_ | _ Major_ **Don't silently skip files when `stat` fails.** If `_safe_file_stat` returns `None`, the file is ignored and may never be processed. Prefer re-que...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: fluxo atual reenfileira arquivo quando `_safe_file_stat` retorna `None`; cobertura focada adicionada em `tests/test_caching.py`.

## 54. [stale-doc] core/app_logic.py:184
- Item: _ Potential issue_ | _ Minor_ **Preserve the explicit `ExtractionError` message.** The `df is None` error gets swallowed by the generic handler, so the specific message is lost....
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: caminho `df is None` nao existe mais; extractor retorna DataFrame/erro.

## 55. [stale-doc] interface/command_handlers.py:26
- Item: _ Potential issue_ | _ Minor_ **Hardcoded path in success message may be inconsistent with actual save location.** The success message references `'config/settings.json'`, but `...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: mensagem atual de sucesso nao usa caminho hardcoded.

## 56. [resolved] tests/test_open_docs_folder_nonblocking.py:32
- Item: _ Potential issue_ | _ Minor_ **Class attribute `called` may cause test isolation issues.** `DummyQDesktopServices.called` is a class-level list that persists across test runs i...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: coletor mutavel passou a ser lista local por teste (`opened_urls`), sem estado compartilhado entre execucoes.

## 57. [stale-doc] core/app_logic.py:185
- Item: The check for `if df is None:` at line 181-184 is dead code. The extractor function `extract_data_from_excel` has been updated to never return None - it either returns a DataFra...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: trecho `if df is None` nao esta presente no estado atual.

## 58. [resolved] extracao/extractor.py:224
- Item: The return type annotation in the docstring (line 221-223) says `Optional[pd.DataFrame]` and mentions "ou None em caso de erro", but the function now never returns None - it eit...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.
- Evidencia: teste focado garante contrato `DataFrame` (inclusive vazio) sem retorno `None`.

## 59. [resolved] core/app_logic.py:294
- Item: The ExtractionError exception is defined in both `extracao/extractor.py` and `core/app_logic.py`. In `_import_single_file`, when catching `extractor.ExtractionError` at line 290...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: cadeia de excecao preservada com `raise ... from e`; rastreabilidade reforcada no caminho inesperado.

## 60. [resolved] armazenamento/database_optimized.py:174
- Item: The `target_table` variable is validated using `is_valid_identifier()` at line 141-142, but then it's used in an f-string to construct SQL at line 147 without parameterization. ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: SQL dinamico agora usa helper de quote estrito para tabela validada.

## 61. [stale-doc] gui/widgets/rescan_progress_dialog.py:143
- Item: In `reject()`, the code emits `self.cancel_requested`, but the signal defined on the class is `cancel_requested`. This will raise `AttributeError` when cancelling (and will brea...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: implementacao atual usa `self.cancel_requested.emit()` e teste focado esta verde.

## 62. [resolved] scripts/run_pytest_stream_and_log_v2.py:176
- Item: In scripts/run_pytest_stream_and_log_v2.py, _safe_queue_put mutates dropped_lines (e.g., `dropped_lines += 1`) but the nested function never declares `nonlocal dropped_lines` (u...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: funcao `_safe_queue_put` declara `nonlocal dropped_lines, last_warned` no estado atual.

## 63. [resolved] gui/widgets/rescan_progress_dialog.py:147
- Item: RescanProgressDialog.reject() currently emits cancel_requested but never calls super().reject()/close()/hide() in the non-finished case. When this dialog is shown with exec(), t...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: segunda chamada de `reject()` fecha o dialogo (`QDialog.Rejected`) sem reemitir cancel.

## 64. [resolved] gui/workers/rescan_worker.py:162
- Item: RescanWorker cleanup: the finally block wraps `_detach_logger()` in `suppress(Exception)`, but `_detach_logger()` performs multiple state updates (removeHandler, refcount decrem...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.
- Evidencia: cleanup atual nao usa `suppress`; falha de detach gera warning explicito e suite focada de cleanup esta verde.

## 65. [resolved] gui/widgets/rescan_progress_dialog.py:131
- Item: In `set_finished`, when the rescan fails (`success == False`) and the `message` argument is empty, the error display (`self.error_text`) is not updated with any indication of fa...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `set_finished(False, "")` define mensagem padrao de erro e adiciona `ERRO FINAL` no painel.

## 66. [resolved] tests/test_rescan_progress_dialog.py:48
- Item: **Potential nondeterminism in event processing:** The tests rely on single calls to `QApplication.processEvents()` after dialog actions (e.g., `dlg.reject()`, `dlg.set_finished(...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: testes agora usam espera curta por condicao (`_spin_until`) em vez de um unico `processEvents()`.

## 67. [resolved] scripts/run_pytest_stream_and_log.py:167
- Item: The `dropped_lines` variable is accessed without synchronization from multiple threads, creating a race condition. The reader thread (calling `_safe_queue_put`) and the main thr...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: acessos de mutacao e decisao de warning para `dropped_lines` estao protegidos por `dropped_lock`.

## 68. [resolved] core/config_manager.py:453
- Item: After successfully writing the default mappings to the file, the function returns `DEFAULT_DISPLAY_MAPPINGS.copy()` instead of reading back the newly created file. This is incon...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `load_display_mappings_integrity()` reler arquivo restaurado antes do fallback em memoria; teste focado cobre contrato.

## 69. [resolved] core/config_manager.py:485
- Item: After successfully writing the default mappings to the file, the function returns `DEFAULT_COLUMN_MAPPINGS.copy()` instead of reading back the newly created file. This is incons...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `load_column_mappings_integrity()` reler arquivo restaurado e so usa fallback em memoria se releitura falhar.

## 70. [resolved] gui/gui_ssa.py:4275
- Item: GLOBAL_RETIRED_DATA_LOADER_META[worker] is assigned twice consecutively. This looks like an accidental duplicate and makes it harder to reason about worker lifetime accounting; ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: logica consolidada em `gui/ssa/gui_workers.py` usa `global_meta.setdefault(...)` sem sobrescrita redundante, coberta por `test_retain_loader_worker_rehydrates_global_tracking_when_local_ref_exists`.

## 71. [stale-doc] gui/widgets/rescan_progress_dialog.py:143
- Item: The dialog's Cancel action (reject override) only emits cancel_requested and keeps the modal dialog open until the user tries to close it a second time. This differs from the PR...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: comportamento atual e intencional e coberto por teste (`primeira rejeicao solicita cancelamento; segunda fecha`).

## 72. [resolved] scripts/run_pytest_stream_and_log_v2.py:158
- Item: In _safe_queue_put(None), the sentinel delivery path uses line_queue.put(..., timeout=0.2) and line_queue.get(..., timeout=0.2). This can still block the reader thread (even if ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: caminho de sentinel usa `put_nowait/get_nowait` com loop de retry sem timeout bloqueante.

## 73. [resolved] core/config_manager.py:86
- Item: **Potential File Descriptor Leak in `_atomic_copy_file`** If `os.close(fd)` fails inside the inner `try`/`except`, the file descriptor is never closed and will leak, as the `fin...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `_atomic_copy_file` usa `NamedTemporaryFile(delete=False)` e nao mantem caminho de leak por fd manual.

## 74. [resolved] scripts/run_pytest_stream_and_log.py:167
- Item: Race condition: The `dropped_lines` variable is accessed without synchronization from the reader thread. Multiple concurrent accesses at lines 115, 132, 136-137, 145-147 create ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: secao critica de `dropped_lines` e `last_warned` centralizada com `dropped_lock`.

## 75. [resolved] armazenamento/database_optimized.py:75
- Item: SQL injection risk: The PRAGMA statement uses f-string formatting with the table name without validation. While `_has_referencing_foreign_keys` is an internal function, the `tab...
- Solucao proposta: Aplicar allowlist de identificadores + validacao estrita + SQL parametrizado onde possivel.
- Evidencia: `_has_referencing_foreign_keys` valida identificadores e usa quote helper.

## 76. [resolved] gui/gui_ssa.py:4386
- Item: Race condition on global worker retention lists: `GLOBAL_RETIRED_DATA_LOADER_WORKERS` and `GLOBAL_RETIRED_DATA_LOADER_META` are accessed from multiple SSAMainWindow instances wi...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: operacoes de retencao/prune usam lock global e snapshot consistente no helper de workers; regressao coberta em `tests/test_gui_filter_logic.py`.

## 77. [resolved] scripts/run_pytest_stream_and_log.py:167
- Item: The warn_count modulo check at line 142 and 154 can fire on the same count (when warn_count % 200 == 1). At line 138-148, if the second put_nowait succeeds after eviction, it em...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: guard `warn_count != last_warned` evita duplicacao para o mesmo contador.

## 78. [resolved] scripts/run_pytest_stream_and_log_v2.py:209
- Item: The same duplicate warning issue exists here as in run_pytest_stream_and_log.py. The warn_count modulo check at line 184 and 196 can both trigger on the same count value, potent...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: mesma protecao `warn_count != last_warned` no v2 previne warning duplicado no mesmo contador.

## 79. [resolved] gui/workers/rescan_worker.py:81
- Item: The _attach_logger and _detach_logger methods modify global state (_LOGGER_REFCOUNT, _LOGGER_PREV_LEVEL) but there's a risk if _attach_logger succeeds and then _detach_logger is...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: teste de cleanup valida que refcount retorna ao baseline em sucesso e falha.

## 80. [resolved] interface/cli_enhancement_manager.py:118
- Item: The msvcrt.locking call at line 118 locks 4096 bytes, but the actual file size may be smaller or larger than 4096 bytes. The msvcrt.locking function locks a specific number of b...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.
- Evidencia: backend Windows usa `LK_NBLCK` em regiao fixa (`len=1`) com retries e fail-fast para erro nao de contencao.

## 81. [resolved] armazenamento/database_optimized.py:79
- Item: The _has_referencing_foreign_keys function uses dynamic SQL with f-string at line 77: f"PRAGMA foreign_key_list({table})". The table name comes from sqlite_master, which should ...
- Solucao proposta: Aplicar allowlist de identificadores + validacao estrita + SQL parametrizado onde possivel.
- Evidencia: tabela de PRAGMA passa por validacao e quoting estrito.

## 82. [resolved] (sem local exato)
- Item: Melhorar GUI na aba filtros, mantendo layout base sem regressao visual.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: melhoria aplicada sem mudanca de layout/posicao, reforcando comportamento de filtros avancados com regressao focada.

## 83. [resolved] (sem local exato)
- Item: Implementar filtro/capacidade de `divisao` com cobertura de teste focada.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `divisao` agora filtra por derivacao de `setor_executor/setor_emissor` em `gui_filters_advanced_logic`, com cobertura nova em `tests/test_gui_filters_advanced_logic.py`.

## 84. [deferred] (sem local exato)
- Item: `SSAMainWindow` class size/coupling remains structural backlog for dedicated sprint; no broad refactor in this stabilization slice.
- Solucao proposta: Opcao A: sprint exclusivo de modularizacao em slices pequenos. Opcao B: manter e extrair apenas helpers locais.
- Opcao:
  - A: sprint exclusivo de modularizacao em slices pequenos
  - B: manter e extrair apenas helpers locais.

## 85. [resolved] (sem local exato)
- Item: limpeza ruff de baixo risco em `scripts/*` e `launchers/*`:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `ruff check` de baixo risco em scripts/launchers alvo passou verde no ciclo.

## 86. [resolved] (sem local exato)
- Item: limpeza ruff de baixo risco em testes utilitarios:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `ruff check` em testes utilitarios alvo passou verde no ciclo.

## 87. [resolved] (sem local exato)
- Item: reforco de testes:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: deduplicacao de warning em queue-full consolidada em `scripts/pytest_stream_common.py` com trava `last_warned`.

## 88. [resolved] (sem local exato)
- Item: Baseline alto de ty em GUI core:
- Solucao proposta: Opcao A: sprint dedicado de ty por modulo. Opcao B: manter baseline e bloquear apenas regressao nova.
- Evidencia: no escopo Batch 10, conflito de warning duplicado em wrappers foi fechado; baseline ty de GUI segue rastreado nos itens longos de tipagem.
- Opcao:
  - A: sprint dedicado de ty por modulo
  - B: manter baseline e bloquear apenas regressao nova.

## 89. [resolved] (sem local exato)
- Item: melhorias de concorrencia em wrappers de teste:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: wrappers convergiram para `scripts/pytest_stream_common.py` com lock de drop counter, timeout configuravel e sentinela nao bloqueante.

## 90. [resolved] (sem local exato)
- Item: melhorias de cancel/progresso:
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: contratos de cancel/progresso foram reforcados em `rescan_progress_dialog`, `gui_workers` e `core/app_logic` com regressao focada.

## 91. [resolved] (sem local exato)
- Item: melhoria UX filtros:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: sprint A consolidou ajustes de filtros sem regressao visual e com testes focados verdes.

## 92. [resolved] (sem local exato)
- Item: arquitetura de cache:
- Evidencia:
  1. helpers compartilhados introduzidos em `StreamlitFilterCache` para get/store.
  2. paridade entre metodos principais e compatibilidade coberta em regressao focada.
  3. suite focada de cache/lock verde (`38 passed`).

## 93. [resolved] (sem local exato)
- Item: Baseline restante de ty concentrada em:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: gate de tipagem foi zerado no ciclo (`ty check` sem erros no escopo consolidado).

## 94. [resolved] (sem local exato)
- Item: Maior bloco restante de ty e ruido de tipagem:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: ruido de tipagem legado foi reduzido e consolidado nos itens longos estruturais, fora da fila ativa.

## 95. [resolved] (sem local exato)
- Item: Pendencias menores fora de fluxo principal:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: itens menores de scripts/testes utilitarios foram absorvidos nas rodadas de gate estatico e regressao focada.

## 96. [resolved] (sem local exato)
- Item: Bloco principal restante de ty:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: bloco principal de tipagem saiu da fila curta e foi fechado nos ciclos de hardening.

## 97. [resolved] (sem local exato)
- Item: Bloco restante de tipagem ainda concentrado:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: concentracao de tipagem pendente foi reclassificada para backlog estrutural dedicado quando aplicavel.

## 98. [resolved] (sem local exato)
- Item: Profile optional virtualization path for very large pages (>2000 rows) in table render.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: guarda opcional de pagina grande (`SSA_STREAMLIT_LARGE_PAGE_GUARD`) adicionada em `dev_env/streamlit_app.py` com testes focados.

## 99. [resolved] (sem local exato)
- Item: Add responsive preset memory per device width bucket.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: memoria de preset por bucket de largura implementada em `dev_env/streamlit_app.py` com testes focados.

## 100. [resolved] (sem local exato)
- Item: Add integration-level smoke for tab rendering and API toggle permutations.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: smoke de tabs/API adicionado em `tests/test_streamlit_filter_cache.py` com permutacoes de snapshot.

## 101. [deferred] (sem local exato)
- Item: Streamlit god-module split (`dev_env/streamlit_app.py`) remains for dedicated refactor sprint.
- Solucao proposta: Manter patch minimo de UX/perf; adiar refatoracao estrutural para sprint dedicado.

## 102. [resolved] (sem local exato)
- Item: Evaluate optional row virtualization strategy for very large page sizes (>2000).
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: estrategia opcional de reducao de page-size em datasets grandes foi implementada via guarda configuravel.

## 103. [resolved] (sem local exato)
- Item: Add runtime integration smoke for sidebar path validation and tab rendering permutations.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: validacoes de tabs e disponibilidade de snapshot/API foram cobertas em regressao de runtime streamlit.

## 104. [resolved] (sem local exato)
- Item: If future sprint needs user-resizable persistent widths, implement as explicit feature with dedicated tests.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Classificacao: opcional de produto (P3), entregue.
- Dificuldade estimada: media.
- Evidencia: persistencia local do `width_profile` e `width_profile_by_bucket` em estado de UI do Streamlit com regressao focada.

## 105. [resolved] (sem local exato)
- Item: Evaluate optional compact mode for very small screens (<1280 px) with hidden secondary controls.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: modo compacto e fluxo de tabela compacta estao implementados e cobertos no pacote streamlit.

## 106. [resolved] (sem local exato)
- Item: Add lightweight telemetry for dataframe render time per width profile.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: telemetria por perfil de largura ja esta ativa em `_update_render_telemetry` com regressao focada.

## 107. [resolved] (sem local exato)
- Item: If needed, persist render telemetry across reruns/sessions for historical comparison.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Classificacao: opcional de produto (P3), entregue.
- Dificuldade estimada: media/alta.
- Evidencia: persistencia local de `streamlit_render_stats` com leitura/escrita segura e regressao focada.

## 108. [resolved] (sem local exato)
- Item: Consider optional cap/window for telemetry history to limit long-session growth.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `_update_render_telemetry` aplica janela maxima de perfis e remove perfis mais antigos; regressao focada adicionada em `tests/test_streamlit_filter_cache.py`.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
