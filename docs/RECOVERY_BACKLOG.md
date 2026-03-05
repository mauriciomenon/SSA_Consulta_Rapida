# Recovery Backlog

This file tracks post-merge hardening and cleanup for the recovery branch.
Scope is split by priority to keep delivery safe and incremental.

## Update 2026-03-05 (safe reapply from clean base, d4 excluded)

Session timestamp:
1. start: `2026-03-05 08:37:14 -0300`
2. end: `2026-03-05 08:40:47 -0300`

Delivered in this slice:
1. created clean replay branch from fixed base `bf78666e`.
2. replayed approved commits only:
   - `9601ffb8`
   - `a87c72d7`
   - `88de4155`
   - `8400fe42`
   - `df65682c`
   - `6899894b`
   - `956c0f4a`
3. explicitly excluded `d4c2c5ca` from replay.

Validation:
1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "num_reprogramacoes or best_fit or show_all_columns_by_affinity or data_cadastro_column_filter_accepts_display_date_on_first_apply"`: `7 passed`.
5. kluster auto in replay cycle: clean -> clean -> clean.

Decision and scope:
1. this replay is `STABILITY_PATCH` + `DOC_SYNC` only.
2. no DB schema/data mutation in this cycle.
3. short-term deferred item: evaluate controlled reimplementation of `d4c2c5ca` requirements in separate slice (do not replay raw commit).

## Update 2026-03-04 (sprint7 stability: width guardrails + sort stability + show-all affinity)

Session timestamp:
1. start: `2026-03-04 10:11:48 -0300`
2. end: `2026-03-04 10:29:08 -0300`

Delivered in this slice:
1. added predefined max width guardrails for long columns:
   - `descricao_ssa`
   - `descricao_execucao`
   - `solicitante`
2. stabilized sort behavior to preserve current column widths after asc/desc sort:
   - avoids lateral "runaway" width effect after header click.
3. added header context action:
   - `Exibir todas colunas (afinidade)`
4. new affinity model (`coluna -> score desc`) introduced for ordered "show all" flow.
5. action contract aligned to existing selector:
   - source columns come from same select-all base (`ColumnSelector` available list/order).

Validation:
1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or header_context_menu_exposes_show_all_columns_by_affinity_action or show_all_columns_by_affinity_reorders_same_select_all_set or on_header_clicked_preserves_column_widths_after_sort or best_fit_width_respects_predefined_max_for_long_columns or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `7 passed`.
5. kluster auto in this slice: clean across all touched files.

Decision and scope:
1. this is a `STABILITY_PATCH` with no GUI layout/position change.
2. no DB/schema/data mutation.
3. affinity ranking is now explicit and reusable for future column-order flows.

## Update 2026-03-04 (sprint6 hotfix: data_cadastro column filter trigger consistency)

Session timestamp:
1. start: `2026-03-04 09:53:38 -0300`
2. end: `2026-03-04 10:01:00 -0300`

Delivered in this slice:
1. root cause fixed in `gui/mixins/filter_gui_ssa_mixin.py`:
   - column-filter comparison used raw `data_cadastro` values (`YYYY-MM-DD HH:MM:SS`) only;
   - table displays dates as `DD/MM/YYYY`, causing user-visible mismatch and apparent delayed application.
2. `_apply_column_filters` now supports date display matching for slash-based terms:
   - keeps raw comparison path;
   - adds OR match against cached `DD/MM/YYYY` projection for date-like columns.
3. added helper methods for maintainability/performance:
   - `_should_match_date_display_filter(...)`
   - `_get_column_filter_date_display_series(...)` with per-DataFrame cache.
4. added regression `tests/test_gui_filter_logic.py::test_data_cadastro_column_filter_accepts_display_date_on_first_apply`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "data_cadastro_column_filter_accepts_display_date_on_first_apply or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_filter_button_state_syncs_across_tabs_without_switch"`: `4 passed`.
5. kluster auto in this slice: issue(P4,P4) -> clean -> clean -> clean.

Decision and scope:
1. this is a `HOTFIX_BLOCKER` in filter consistency path only.
2. no GUI layout/positioning change.
3. no DB schema/data mutation.

## Update 2026-03-04 (sprint5 canonical reprogramacoes numeric lane)

Session timestamp:
1. start: `2026-03-04 09:40:56 -0300`
2. end: `2026-03-04 09:44:37 -0300`

Delivered in this slice:
1. added `gui/ssa/reprogramacoes_numeric.py` with canonical helper for numeric extraction:
   - `total_de_reprogramacoes` as primary source;
   - fallback numeric parse of `num_reprogramacoes`;
   - final digit extraction fallback for legacy text rows.
2. `gui/gui_ssa.py`: robust sort for `num_reprogramacoes` now uses the shared helper.
3. `gui/ssa/gui_filters_advanced_logic.py` and `gui/ssa/gui_filters_advanced_ui.py`: advanced reprogramacoes filter/cache now use the same helper, avoiding divergent conversions.
4. `gui/gui_ssa.py`: best-fit baseline probe now guarded (`sizeHintForColumn` only when `rowCount <= 500`) to avoid O(R*C) UI cost on large tables.
5. added focused regressions:
   - `tests/test_gui_filters_advanced_logic.py::test_apply_advanced_filters_reprogramacoes_prefers_total_de_reprogramacoes_when_available`
   - `tests/test_gui_filter_logic.py::test_reprogramacoes_menu_uses_total_de_reprogramacoes_with_legacy_text_values`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py -k "reprogramacoes or on_header_clicked_sorts_num_reprogramacoes_mixed_types or best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action"`: `8 passed`.
5. kluster auto in this slice: clean -> clean -> clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` without DB schema or layout change.
2. legacy text (`Reprogramacao #1`) remains accepted as input artifact; runtime now normalizes numeric behavior consistently.
3. `situacao_reprogramacao` (`(SPG)`) remains informational/legacy in this sprint and is not promoted to active filter logic.
4. deferred note kept active: legacy non-ASCII content in old scripts/tests is not globally normalized in this slice to avoid transversal high-risk edits.

## Update 2026-03-04 (sprint4 best-fit calibration against real Qt auto-fit)

Session timestamp:
1. start: `2026-03-04 09:21:19 -0300`
2. end: `2026-03-04 09:27:28 -0300`

Delivered in this slice:
1. `gui/simple_width_manager.py`: best-fit algorithm recalibrated from synthetic `"W"*N` estimate to sampled real-text pixel widths.
2. added baseline clamp against Qt real auto-fit (`sizeHintForColumn`) to avoid width over-expansion.
3. reduced sampling pressure (`sample_limit` default now `800`) and added measurement cache to reduce repeated font-metric calls.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action or table_header_uses_merged_default_alias_for_extra_column"`: `3 passed`.
5. kluster auto in this slice: issue(P4 intent/perf) -> clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` for width behavior only.
2. no GUI layout/positioning change.
3. dedicated follow-up slice opened next for `num_reprogramacoes`/`total_de_reprogramacoes`/`situacao_reprogramacao` evidence and risk handling.

## Update 2026-03-04 (sprint3 display-label merge hardening for table and add-columns)

Session timestamp:
1. start: `2026-03-04 09:02:15 -0300`
2. end: `2026-03-04 09:11:13 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: initialization now always uses canonical `load_display_mappings()` merge path.
2. guarantees merged aliases (`DEFAULT_DISPLAY_MAPPINGS` + `column_display_names` + `display_mappings`) are applied to:
   - table headers
   - add-column/filter selectors that rely on `internal_to_display`.
3. `tests/test_gui_filter_logic.py`: added regression `test_table_header_uses_merged_default_alias_for_extra_column`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "table_header_uses_merged_default_alias_for_extra_column or on_header_clicked_sorts_num_reprogramacoes_mixed_types or header_context_menu_exposes_best_fit_visible_action"`: `3 passed`.
5. kluster auto in this slice: clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` in display-label lane only (no DB/runtime schema mutation).
2. no GUI layout/positioning change.
3. next step remains label curation refinement (if needed) and separate DB-saneamento sprint.

## Update 2026-03-04 (sprint2 best-fit visible columns via width manager)

Session timestamp:
1. start: `2026-03-04 08:31:10 -0300`
2. end: `2026-03-04 08:39:30 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: added header context-menu action `Best fit colunas visiveis`.
2. `gui/gui_ssa.py`: added reusable orchestration methods:
   - `_compute_best_fit_width_for_column`
   - `_best_fit_column_width`
   - `best_fit_visible_columns`
3. `gui/simple_width_manager.py`: added centralized `compute_best_fit_width(...)` with anti-outlier guard.
4. `gui/gui_ssa.py`: `auto_fit_column` now reuses best-fit path first.
5. `tests/test_gui_filter_logic.py`: added regressions:
   - `test_header_context_menu_exposes_best_fit_visible_action`
   - `test_best_fit_width_guard_ignores_single_extreme_outlier`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `3 passed`.
5. kluster auto in this slice: clarification(P4 centralize width logic) -> issue(P3 map contract) -> issue(P4 pandas constructor compatibility) -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` focused on reusable best-fit behavior only.
2. no GUI layout/positioning change.
3. db/runtime schema migration remains deferred to next sprint lane.

## Update 2026-03-04 (sprint1 hotfix: robust sort for num_reprogramacoes)

Session timestamp:
1. start: `2026-03-04 08:24:32 -0300`
2. end: `2026-03-04 08:28:21 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: added `_sort_num_reprogramacoes_robust` and routed header sort for `num_reprogramacoes` to mixed-type-safe path.
2. `tests/test_gui_filter_logic.py`: added regression `test_on_header_clicked_sorts_num_reprogramacoes_mixed_types`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "on_header_clicked_sorts_num_reprogramacoes_mixed_types or reprogramacoes_menu_builds_without_responsavel_materialized"`: `2 passed`.
5. kluster auto in this slice: clean -> clean.

Decision and scope:
1. this is a `HOTFIX_BLOCKER` for active runtime warning/failure in column sort.
2. no GUI layout/positioning change.
3. next prioritized slice remains sprint2 (`best fit all visible columns` with anti-outlier guard + label cleanup).

## Update 2026-03-04 (release snapshot v4.29 + baseline promote to v4.30)

Session timestamp:
1. start: `2026-03-04 08:14:11 -0300`
2. end: `2026-03-04 08:22:31 -0300`

Delivered in this slice:
1. created GitHub tag `v4.29` on commit `bf78666e`.
2. created GitHub release `SSA Consulta Rapida v4.29` as pre-sprint stable snapshot.
3. promoted local baseline metadata to `4.30` (`VERSION` + `config/version.json`).
4. synchronized active release docs to `4.30`.

Validation:
1. `gh release view v4.29`: published.
2. `git tag -l v4.29`: present.

Decision and scope:
1. this is a `DOC_SYNC` + release housekeeping slice before runtime changes.
2. runtime bug fix (`num_reprogramacoes` mixed-type sorting) remains prioritized for next slice.

## Update 2026-03-04 (post-merge environment cleanup and branch hygiene)

Session timestamp:
1. start: `2026-03-04 07:50:00 -0300`
2. end: `2026-03-04 07:50:20 -0300`

Delivered in this slice:
1. `.gitignore`: added `config/gui_main_preferences.json` to repository ignore policy.
2. local git index: applied `skip-worktree` to `config/gui_main_preferences.json` to stop local noise for tracked preference changes.
3. branch hygiene (local): removed all branches except `dev` and `main`.
4. branch hygiene (remote): removed non-core remote branches; remaining refs are `origin/main` and `origin/dev` (plus `origin/HEAD` pointer).
5. stash triage: `stash@{0}` inspected; contains only `config/gui_main_preferences.json` and `data/ssas.db`.

Validation:
1. `git branch --list`: only `dev`, `main`.
2. `git fetch --prune && git branch -r`: only `origin/main`, `origin/dev`, `origin/HEAD -> origin/main`.
3. `git status --short`: local residue from `config/gui_main_preferences.json` neutralized by `skip-worktree`.

Decision and scope:
1. this is a `STABILITY_PATCH` for environment hygiene only; no runtime behavior change.
2. no GUI layout/positioning changes.
3. pending explicit user confirmation: final action for `stash@{0}` (recommended path: drop).

## Update 2026-03-04 (PR #43 comments triage: real bugs fixed, noise deferred)

Session timestamp:
1. start: `2026-03-04 06:27:03 -0300`
2. end: `2026-03-04 06:29:30 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets OR-group metadata via `_reset_or_groups()`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: `_mk_remove_line` no longer uses broad silent `except Exception`.
3. `gui/gui_ssa.py`: `debounce_delay` parsing now catches only `(TypeError, ValueError)` and logs explicit fallback.
4. `gui/mixins/tab_context_gui_ssa_mixin.py`: removed duplicated `_sync_clear_filter_button_state()` call in bind flow.
5. `tests/test_gui_filter_logic.py`: added regression `test_clear_all_filters_global_resets_or_group_metadata`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_or_group_metadata or clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_button_state_syncs_across_tabs_without_switch or undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore"`: `5 passed`
5. kluster auto review run in this slice: clean -> clean -> clean -> clean

PR comment status mapping:
1. fixed now (`BUG_REAL`): stale OR-group metadata after global clear.
2. fixed now (`BUG_REAL`): broad/no-log fallback in debounce parse.
3. fixed now (`BUG_REAL`): silent broad `except` in `_mk_remove_line`.
4. fixed now (`BUG_REAL`): duplicated cross-tab clear-button sync call in bind.
5. deferred (`DECISAO_INTENCIONAL`): make debounce floor configurable now; current fixed floor is approved policy for this lane.
6. deferred (`NAO_BLOQUEANTE_DEFERIDO`): wide cleanup of broad `except` patterns across legacy GUI path (outside this minimal slice).
7. rejected (`FALSO_POSITIVO`): speculative suggestions with weak/no anchored evidence (regex over-restriction claims without reproducible regression).

Decision and scope:
1. this is a `STABILITY_PATCH` focused on real, reproducible PR findings only.
2. no layout/positioning changes.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (tab-specific search handlers and regex guard hardening)

Session timestamp:
1. start: `2026-03-04 01:40:00 -0300`
2. end: `2026-03-04 01:44:21 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: search controls now route through dedicated per-tab handlers (`main`/`filters`) for `Aplicar` and `Limpar Busca`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: added dedicated handler methods `_on_general_search_apply_clicked` and `_on_general_search_clear_clicked`.
3. `gui/mixins/filter_gui_ssa_mixin.py`: strengthened regex safety guard in `_build_column_mask` (`meta_char_count` and alternation+quantifier blocking).
4. `tests/test_gui_filter_logic.py`: added regression `test_search_buttons_route_to_tab_specific_handlers`.
5. `tests/test_gui_filter_logic.py`: added regression `test_build_column_mask_blocks_heavy_regex_patterns`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "search_buttons_route_to_tab_specific_handlers or clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or clear_filter_button_state_syncs_across_tabs_without_switch or build_column_mask_blocks_heavy_regex_patterns"`: `4 passed`
5. kluster auto review run in this slice: clean -> issue(P4 regex safety) -> clean

Decision and scope:
1. this is a `STABILITY_PATCH` focused on handler identity per tab and safety hardening for regex filter path.
2. no layout/positioning change.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (cross-tab sync for undo button state)

Session timestamp:
1. start: `2026-03-04 01:20:00 -0300`
2. end: `2026-03-04 01:39:47 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: added centralized helpers to sync `undo_filter_btn` enabled-state across all tab contexts.
2. `gui/mixins/filter_gui_ssa_mixin.py`: `_update_undo_button_state` now updates all tab undo buttons, not only active tab.
3. `tests/test_gui_filter_logic.py`: added regression `test_undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore or clear_advanced_filters_forces_refresh_when_pending_schedule or test_header_context_menu_apply_stores_undo_snapshot"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` for undo-state consistency and advanced-filter undo coverage.
2. no layout/positioning changes.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (cross-tab sync for clear-search button state)

Session timestamp:
1. start: `2026-03-04 00:27:39 -0300`
2. end: `2026-03-04 01:02:15 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: added central helpers to sync `clear_filter_button` state across all tab contexts.
2. `gui/mixins/filter_gui_ssa_mixin.py`: replaced single-widget `clear_filter_button.setEnabled(...)` calls with shared cross-tab sync.
3. `gui/mixins/tab_context_gui_ssa_mixin.py`: bind step now uses shared clear-button sync method.
4. `tests/test_gui_filter_logic.py`: added regression `test_clear_filter_button_state_syncs_across_tabs_without_switch`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter_button_state_syncs_across_tabs_without_switch or clear_filter_button_reflects_active_filters or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` for state consistency only; no layout or positioning change.
2. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (clear-search button wording clarity)

Session timestamp:
1. start: `2026-03-04 00:23:12 -0300`
2. end: `2026-03-04 00:25:01 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: changed clear-search button text from `Limpar Filtro` to `Limpar Busca`.
2. `gui/gui_ssa.py`: added explicit tooltip clarifying that only general search is cleared.
3. `tests/test_gui_filter_logic.py`: added regression `test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or test_clear_filter_clears_only_general_search_and_keeps_advanced_filters or test_clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
5. kluster auto review run in this slice: clean -> clean

Decision and scope:
1. this is a low-risk `STABILITY_PATCH` for UX wording clarity only; no filter logic behavior change.
2. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.
3. evidence commit: `182c51b0` (`STABILITY_PATCH`: clear-search button wording clarity).

## Update 2026-03-04 (tooltip encoding fix and column-filter 3-button row)

Session timestamp:
1. start: `2026-03-04 00:08:50 -0300`
2. end: `2026-03-04 00:14:10 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: fixed corrupted week tooltip text and simplified to `Semana ISO atual`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: column-filter row now has `Aplicar`, `Limpar`, `Ocultar`.
3. `gui/mixins/filter_gui_ssa_mixin.py`: `Limpar` clears current column value and reapplies filters without hiding the row.
4. `gui/widgets/filter_help_dialog.py`: help text updated to reflect `Aplicar + Limpar + Ocultar`.
5. `tests/test_gui_filter_logic.py`: updated control parser and added regression `test_column_filter_row_clear_button_clears_value_without_hiding_row`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "default_column_filter_rows_show_apply_clear_and_hide_buttons or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `5 passed`
5. kluster auto review run in this slice: clean

Diagnostic scan:
1. global scan for mojibake patterns in `*.py` completed.
2. no remaining mojibake pattern found in touched runtime/test files after this patch.
3. deferred note (approved): "existem muitos caracteres nao-ASCII legados em scripts/tests antigos (texto PT-BR), mas isso nao e necessariamente erro de codificacao; normalizei apenas erros reais neste slice para evitar mudanca transversal de alto risco."
4. where to clean in future controlled slice:
   - `scripts_manutencao/*.py`
   - `tests/teste_*.py`
   - legacy CLI/script text blocks under `interface/cli.py` and `interface/command_handlers.py`

Decision and scope:
1. this is a `STABILITY_PATCH` focused on user-visible filter button behavior and encoding fix in GUI tooltip.
2. no change in startup/import policy or out-of-scope modules.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (global clear baseline consistency in filter buttons)

Session timestamp:
1. start: `2026-03-04 00:00:27 -0300`
2. end: `2026-03-04 00:07:25 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets column filters using `_column_filter_default_columns()` instead of hardcoded subset.
2. `tests/test_gui_filter_logic.py`: added regression `test_clear_all_filters_global_restores_default_column_filter_keys`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_all_filters_global_resets_exclude_and_advanced_filters"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` to remove inconsistent reset behavior between related clear actions.
2. runtime outside filter-clear path unchanged.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Evidence commit:
1. `98269107` (`STABILITY_PATCH`: global clear baseline consistency).

## Update 2026-03-03 (follow-up regression for header context-menu undo path)

Session timestamp:
1. start: `2026-03-03 23:55:05 -0300`
2. end: `2026-03-03 23:59:04 -0300`

Delivered in this slice:
1. added direct regression in `tests/test_gui_filter_logic.py` to validate header context-menu apply path stores undo snapshot end-to-end.

Validation:
1. `uv run --python 3.13 python -m py_compile tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_header_context_menu_apply_stores_undo_snapshot"`: `1 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a test-only `STABILITY_PATCH` follow-up to close previously deferred coverage gap.
2. runtime behavior unchanged in this slice.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Evidence commit:
1. `22bbd3dc` (`STABILITY_PATCH`: header context-menu undo regression test).

## Update 2026-03-03 (filter buttons stability hardening on feature branch)

Session timestamp:
1. start: `2026-03-03 23:46:42 -0300`
2. end: `2026-03-03 23:53:25 -0300`

Delivered in this slice:
1. fixed high-risk stale async state after `clear_filter` by resetting request-scoped search markers in `gui/mixins/filter_gui_ssa_mixin.py`.
2. raised effective general-search debounce floor to `1400 ms` in `gui/gui_ssa.py` to encourage explicit `Aplicar`.
3. completed undo snapshot coverage for column filter activation/deactivation and header context-menu apply path.
4. aligned help text to real column-filter controls (`Aplicar` + `Ocultar`) in `gui/widgets/filter_help_dialog.py`.
5. added focused regressions in `tests/test_gui_filter_logic.py` for stale state clear path, debounce floor, and undo snapshots in column filter entry points.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter or debounce or activate_column_filter_stores_undo_snapshot or deactivate_column_filter_stores_undo_snapshot"`: `15 passed, 1 skipped`
5. kluster auto review runs in this slice: clean -> clean -> clean -> clean

Decision and scope:
1. this is a `STABILITY_PATCH` focused on filter-state consistency and undo coverage with minimal behavioral changes.
2. branch used by explicit approval: `codex/fix-filter-buttons-state-sync`.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Deferred non-blocking:
1. add a direct regression for the full Qt header context-menu interaction path that asserts undo snapshot behavior end-to-end (current coverage validates internal entry points and data path).

Evidence commit:
1. `2c7982b1` (`STABILITY_PATCH`: runtime + tests for filter-state hardening).

## Update 2026-03-03 (slice G targeted regression coverage for A/B/C)

Session timestamp:
1. start: `2026-03-03 22:20:26 -0300`
2. end: `2026-03-03 22:24:33 -0300`

Delivered in this slice:
1. `tests/test_app_logic_full_rescan_lock.py`: added regression to assert sidecar move (`-wal`/`-shm`) into full-rescan backup path.
2. `tests/test_import_deterministic_failure_cache.py`: added regression to assert `OPERATION_CANCELLED` does not mark deterministic failed file list.
3. `tests/test_cli_enhancement_manager_lock_usage.py`: added regression to assert lock file created by current process is removed when lock acquisition fails.

Validation:
1. `uv run --python 3.13 python -m py_compile tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
2. `uv run --python 3.13 ruff check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
3. `uv run --python 3.13 ty check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: `14 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. this is a test-only `STABILITY_PATCH` slice; runtime behavior unchanged.
2. local residues remain unchanged by policy: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-03 (slice F control-doc current-truth normalization)

Session timestamp:
1. start: `2026-03-03 22:16:00 -0300`
2. end: `2026-03-03 22:17:56 -0300`

Delivered in this slice:
1. `docs/NEXT_CHAT_MIGRATION.md`: normalized heading model to keep exactly one `CURRENT TRUTH` block at top and reclassified older `CURRENT TRUTH` sections as `HISTORICAL SNAPSHOT`.
2. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`: normalized heading model to keep exactly one `CURRENT TRUTH` block at top and reclassified older `CURRENT TRUTH` sections as `HISTORICAL SNAPSHOT`.
3. top blocks in migration/handoff now record this normalization as the active doc state.

Validation:
1. structural grep check: `NEXT_CHAT_MIGRATION.md` has `1` `CURRENT TRUTH` heading.
2. structural grep check: `AGENTS_HANDOFF_NEXT_CYCLE.md` has `1` `CURRENT TRUTH` heading.
3. runtime files unchanged in this slice.

Decision and scope:
1. this is a docs-only `DOC_SYNC` slice, no runtime/test/gui code edits.
2. local residues remain unchanged by policy: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-03 (sprint E controlled technical debt in gui table)

Delivered in this slice:
1. Removed dead helper `_calculate_max_chars_for_column` from `gui/ssa/gui_table.py`.
2. Removed dead facade pass-through `_calculate_max_chars_for_column` from `gui/gui_ssa.py`.
3. No visual/layout/position behavior changed.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_table.py gui/gui_ssa.py`: pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_table.py gui/gui_ssa.py`: pass
3. `uv run --python 3.13 ty check gui/ssa/gui_table.py gui/gui_ssa.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_table_render_resilience.py tests/test_gui_filter_logic.py -k "display_current_page or column_width"`: `5 passed, 109 deselected`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint E closed as low-risk debt cleanup with dead code removal only.
2. Runtime behavior outside removed dead symbols unchanged.

## Update 2026-03-03 (sprint D docs consistency and portability)

Delivered in this slice:
1. `docs/OHMYOPENCODE_MANUAL.md`: replaced local hardcoded path with `$HOME` for portability.
2. `docs/OPENCODE_CONFIG.md`: aligned Gemini model identifier in provider list to match table usage (`google/antigravity-gemini-3-pro`).
3. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`: replaced fixed `--python 3.13` examples with `--python $PY_RUNTIME` and added explicit fallback chain (`3.13 -> 3.12 -> 3.11 -> 3.10`).

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py interface/cli_enhancement_manager.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py interface/cli_enhancement_manager.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py interface/cli_enhancement_manager.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_import_deterministic_failure_cache.py`: `11 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint D closed as docs-only (`DOC_SYNC`) with no runtime code edits.
2. GUI layout/position unchanged.

Deferred (next slices):
1. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint B structured extraction classification)

Delivered in this slice:
1. `ExtractionError` now supports structured `error_code` in both `core/app_logic.py` and `extracao/extractor.py`.
2. Import loop in `core/app_logic.py` now classifies extraction outcomes by `error_code` (no substring matching for deterministic failure detection).
3. Added focused tests in `tests/test_import_deterministic_failure_cache.py`:
   - preserve extractor `error_code` when normalized into core layer;
   - update deterministic-failure cache by `MISSING_REQUIRED_COLUMNS` code path.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_deterministic_failure_cache.py tests/test_extracao.py tests/test_import_derivadas_trigger.py`: `24 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint B closed with minimal runtime change in extraction error contract and deterministic cache trigger.
2. No GUI layout or position change in this slice.

Deferred (next slices):
1. Sprint D: docs-only portability and consistency cleanup.
2. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint C lock-file TOCTOU hardening)

Delivered in this slice:
1. `interface/cli_enhancement_manager.py` lock-file creation now uses atomic open-first flow (`O_EXCL`) with explicit fallback when lock file already exists.
2. Removal of lock file on lock acquisition failure remains restricted to files created by the current process.
3. Added focused race regression in `tests/test_cli_enhancement_manager_lock_usage.py` to validate no removal of preexisting lock file during lock contention failure.

Validation:
1. `uv run --python 3.13 python -m py_compile interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
2. `uv run --python 3.13 ruff check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
3. `uv run --python 3.13 ty check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`: `10 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint C closed as `BUG_REAL` with minimal patch in lock path and focused regression.
2. Runtime outside CLI settings lock path unchanged.

Deferred (next slices):
1. Sprint B: structured extraction error classification and deterministic-failure cache test coverage.
2. Sprint D: docs-only portability and consistency adjustments.
3. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint A lock checkpoint hotfix)

Delivered in this slice:
1. `core/app_logic.py` full-rescan DB preparation now runs `PRAGMA wal_checkpoint(TRUNCATE)` without explicit `BEGIN IMMEDIATE` in the same block, avoiding self-lock during checkpoint.
2. Added focused regression `tests/test_app_logic_full_rescan_lock.py` to validate WAL checkpoint + DB rotation path without external lock contention.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py`: `1 passed`
5. kluster auto review runs in this slice: clean -> clean (no issues, no agent_todo_list)

Decision and scope:
1. Sprint A is closed as `BUG_REAL` with minimal patch in runtime + focused test.
2. No GUI layout/position change in this slice.

Deferred (next slices):
1. Sprint C: review TOCTOU path in `interface/cli_enhancement_manager.py`.
2. Sprint B: migrate extraction deterministic-failure classification from message substring to structured signal.
3. Sprint D/E: docs portability consistency and controlled technical debt cleanup.

## Update 2026-03-03 (control files hard-sync for next chat)

Delivered in this slice:
1. all operational rules negotiated in chat were persisted into repository control docs (no longer chat-only).
2. `AGENTS.md` now includes explicit XP+SDLC flow, slice contract, scope protocol, change categories, PR comment policy, git stash policy, timestamp policy, and tooling policy.
3. kluster detailed mandatory block was restored in full after regression introduced by full-file overwrite.

Traceability:
1. initial consolidation commit: `e3c7cdcb`.
2. kluster block full restore commit: `ce0d3fc1`.
3. control-file sync commit: this slice (DOC_SYNC).

Operational rule reinforced:
1. conversation outputs must be mirrored into control files for continuity.
2. chat log is historical evidence, but repository control files are the authoritative migration source.

Deferred follow-up (non-blocking):
1. unify old duplicated `CURRENT TRUTH` blocks in migration docs into a single active block + historical snapshots only.

## Update 2026-03-03 (startup import policy + rescan modes)

Delivered in this slice:
1. startup import is disabled by default in `main.py`; app starts using current DB state.
2. full rescan now recreates DB from zero by rotating current `ssas.db` to timestamped backup and then reimporting all files.
3. derivadas auto-sync now runs only in full import flows (`force_import=True`) or manual GUI action (`Atualizar Derivadas`).
4. GUI `Reescanear` now offers explicit mode choice:
   - `Diff (hash)`: process only changed files.
   - `Full (zera e reprocessa)`: recreate DB and reimport all.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_derivadas_trigger.py tests/test_derivadas_sync.py tests/test_gui_workers_rescan_data.py`: `35 passed`

Deferred long-term item (do not implement in this slice):
1. background import into a separate candidate DB file and user prompt to switch when ready:
   - run import without blocking normal usage;
   - on success, show prompt like `Novo banco pronto. Deseja usar agora?`;
   - keep current DB untouched until explicit user confirmation.

## Update 2026-03-02 (golden release 2 baseline)

Decision logged for this cycle:
1. mark current advanced-filter behavior as `golden release 2` official recovery baseline.
2. from this point, changes in advanced filters must be minimal and theme-consistent only.
3. no geometry expansion or broad layout refactor is allowed in this lane.
4. target for this slice:
   - consistent theme application across all advanced-filter controls;
   - centered `Cancelar` and `Fechar` footer actions in multiselect popup.

## Update 2026-03-01 (gui filters stability + importer noise control)

Delivered in this slice:
1. `core/app_logic.py`:
   - fixed indentation regression in derivadas error progress path.
   - added deterministic-failure cache mark for extraction errors with message:
     `missing required columns after normalization`.
   - kept dedicated derivadas phase trigger behavior compatible with existing tests.
2. `gui/ssa/gui_filters_advanced_ui.py`:
   - reduced effective width budget for `Aplicar` and `Limpar`.
   - removed visual separator between action buttons and kept compact spacing.
   - constrained multiselect popup width by trigger width + screen cap.
   - hardened parent traversal and checkbox mutual-exclusion callbacks against stale Qt objects.
3. `gui/gui_ssa.py`:
   - canonical column candidate source cleaned to avoid profile placeholder noise.
   - active column candidates now come from visible/default/current + rendered/filled filters.
4. `gui/ssa/gui_theme.py`:
   - advanced filter options refresh is triggered when theme changes on filters tab.
5. `scripts/env/direnv_common.sh`:
   - ensure `${VIRTUAL_ENV}/bin` is prepended to `PATH` when active.
   - refresh shell command cache after path exports.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_derivadas_trigger.py tests/test_import_cancellation.py tests/test_gui_filters_advanced_logic.py`: `28 passed`

Deferred (non-blocking, structural):
1. further breakup of `_rebuild_multiselect_menu` (out of scope for minimal stability patch).
2. wider `SSAMainWindow` responsibility split (tracked as structural work, no refactor in this slice).

## Update 2026-03-01 (streamlit single-file policy note)

Decision logged for this cycle:
1. `dev_env/streamlit_app.py` remains intentionally centralized due explicit sidequest policy (single-file Streamlit scope).
2. deferred (non-blocking) technical debt:
   - extract CSS/theme helpers only when policy allows;
   - extract advanced-filter helper registry only when policy allows.
3. current priority remains functional stability and regression prevention in the existing single-file workflow.

## Update 2026-03-01 (v4.27 uv-first + matrix)

Delivered in this slice:
1. release bump:
   - `VERSION` -> `4.27`
   - `config/version.json` -> `v4.27`
2. runtime compatibility completed (previously inconclusive):
   - isolated uv environments validated in 3.10, 3.11, 3.12, 3.13
   - result: all pass for focused gates/tests
3. docs normalization:
   - uv-first command format standardized to `uv run --python 3.13 ...`
   - fallback policy explicitly documented (`3.12 -> 3.11 -> 3.10`)
   - `requirements*.txt` kept as compatibility path.
4. GUI continuity docs added:
   - `ANALISE_PROFUNDA_GUI.md`
   - `GUI_SSA_REFACTOR_NOTES.md`
5. local directories clarified for operations:
   - `.uv-matrix`: isolated uv virtualenvs used for multi-version validation.
   - `.alma-snapshots`: local snapshot/cache artifacts, not runtime source.
   - `launchers/*`: build/packaging scripts and platform configs.
   - `.venv`: default local development virtualenv.

## Update 2026-02-28 (release alignment v4.27)

Delivered in this pre-PR slice:
1. release metadata aligned to `v4.27`:
   - `VERSION`
   - `config/version.json`
2. release docs aligned to remove drift between `v4.24.1`, `v4.25.0`, and current baseline:
   - `README.md`
   - `docs/HISTORICO_RELEASES.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs_saida/CHANGELOG_IMPLEMENTACOES.md`
3. scope note:
   - no streamlit code/layout changes.
   - no hardening logic changes.

## Update 2026-02-28 (id 92 closed + situacao quick usability)

Delivered in this streamlit micro-slice:
1. Cache architecture item (`92`) closed:
   - shared internal helpers now centralize get/store behavior in `StreamlitFilterCache`.
   - duplicated logic removed with contract preserved.
2. Filters usability adjusted per feedback:
   - situacao no longer hidden; now always visible.
   - added quick mode selector (`Manual`, `Todas`, `Abertas`, `Executadas`, `Nenhuma`).
   - situacao entries now show count labels.
3. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `38 passed`

## Update 2026-02-28 (streamlit usability polish v2)

Delivered in this follow-up slice:
1. executor/emissor compacted to single-select controls with `(Todos)` option.
2. search row now includes explicit `Filtrar agora` submit button.
3. source path controls moved to collapsed advanced section in sidebar.
4. table render height now adapts to current page row count.
5. column picker now omits fully empty columns by default.
6. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability polish v3)

Delivered in this follow-up:
1. source controls removed from quick sidebar and moved to hidden advanced section in `Cache e API`.
2. situacao quick mode moved inline with core filters for denser layout.
3. additional chart context added in table view (`Top executor`, `Top emissor`).
4. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability polish v4)

Delivered in this pass:
1. improved compactness in key filter row and moved quick mode inline.
2. renamed presets/actions to business labels.
3. expanded table context metrics and adjusted dataframe surface styling.
4. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability slice: layout + discoverability)

Delivered in this streamlit-focused slice:
1. Theme visibility:
   - theme selector moved to header (top-right), no longer hidden in ops tab.
2. Filters usability:
   - situacao moved to optional expander to avoid tall multi-line chips by default.
   - setor executor/emissor kept in main filter row.
   - limit rows moved to dedicated line.
3. Table discoverability:
   - quick shortcut for "colunas exibidas" added directly in table tab.
4. Sidebar utilization:
   - source snapshot and quick metrics added.
5. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `36 passed`

## Update 2026-02-28 (streamlit theme slice: colors + behavior)

Delivered in this focused streamlit slice:
1. Added visual theme system with explicit palettes and CSS variable mapping.
2. Added runtime theme selector in Streamlit ops tab.
3. Added persistence for selected theme in Streamlit UI state file.
4. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `36 passed`
5. Scope:
   - no broad refactor and no PyQt GUI layout change.

## Update 2026-02-28 (sprint D optional P3 delivered + doc hygiene)

Delivered in this optional slice:
1. Matrix optional items delivered with minimal risk:
   - item `104` resolved: width profile persistence across sessions (`width_profile` + `width_profile_by_bucket`).
   - item `107` resolved: render telemetry persistence across sessions (`streamlit_render_stats`).
2. Validation evidence:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`34 passed`)
3. Scope note:
   - no GUI layout/position change.
   - no broad refactor.
4. Doc hygiene note:
   - top blocks in matrix/backlog/handoff/migration are canonical.
   - older blocks remain as historical trace.

## Update 2026-02-28 (sprint D closeout: cache guard + optional scope map)

Delivered in this closeout slice:
1. Sprint D P1 fix marked done:
   - matrix item `9` is now `resolved` (was deferred in older snapshot).
   - cache size guard implemented in:
     - `gui/cache/filter_cache.py`
     - `dev_env/streamlit_app.py`
   - env gate: `SSA_CACHE_MAX_MB` (default unset keeps prior behavior).
   - cache stats now expose `skipped_large_entries` and `max_entry_mb`.
2. Focused validation evidence:
   - `uv run --python 3.13 python -m py_compile gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass (`32 passed`)
3. Optional product items in this block are now superseded by a later delivery update:
   - persistent user-resizable widths (item `104`) now resolved.
   - telemetry persistence across sessions (item `107`) now resolved.
4. Structural items kept deferred for dedicated sprint:
   - `SSAMainWindow` split and streamlit god-module split: P2, difficulty alta.

## Update 2026-02-28 (sprints A+B+C delivered with minimal risk)

Delivered in this cycle:
1. Sprint A:
   - divisao filtering capability hardened in advanced logic without layout change.
   - focused regression added in `tests/test_gui_filters_advanced_logic.py`.
2. Sprint B:
   - low-risk ruff cleanup scope validated green for selected scripts/launchers/tests.
3. Sprint C:
   - optional large-page guard for streamlit (`SSA_STREAMLIT_LARGE_PAGE_GUARD`) added.
   - focused regression added in `tests/test_streamlit_filter_cache.py`.
4. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `40 passed`.
5. Matrix result:
   - deferred queue reduced and structural-only deferred items preserved for dedicated sprints.

## Update 2026-02-28 (queue compression to <=20)

Delivered in this triage-only slice:
1. Removed duplicate legacy review-tracking block from this backlog file.
2. Kept `docs/PENDING_ACTION_MATRIX.md` as the canonical active status source.
3. Reclassified historical deferred duplicates that are already delivered in recent streamlit/typing/runtime slices.
4. Result in canonical matrix:
   - `pending`: 0
   - `deferred`: 16
   - open queue total: 16 (<=20 target reached)

## Update 2026-02-28 (sprint long-loop v2: runtime hardening micro-slices)

Delivered in this loop:
1. `interface/command_handlers.py`
   - save success/error feedback now references resolved settings path.
   - unexpected save exception now surfaces terminal feedback.
2. `armazenamento/database_optimized.py`
   - update branch with FK references now quotes/validates update columns before SQL generation.
3. `main.py`
   - optimized cleanup path now logs debug when disable hook import is unavailable.
4. Tests:
   - `tests/test_command_handlers_save_settings.py`
   - `tests/test_database_optimized_identifier_guards.py`
   - focused regression suites for command handlers, db optimized, and main import fallback.
5. Validation:
   - `py_compile`, `ruff`, `ty`: pass on touched scope.
   - focused pytest:
     - command handlers: `10 passed`
     - db optimized: `6 passed`
     - main fallback/skip: `3 passed`
6. Kluster:
   - all auto review runs in this loop: clean.

## Update 2026-02-28 (sprint long-loop: config/extractor grave queue verification)

Delivered in this verification slice:
1. Confirmed and locked severe-path behavior already implemented in runtime:
   - `core/config_manager.py`:
     - atomic write/copy cleanup logs failures explicitly.
     - mappings integrity restore keeps safe fallback to defaults in memory.
   - `extracao/extractor.py`:
     - extraction handle lifecycle is context-managed via `with pd.ExcelFile(...)`.
     - extraction return/raise contract aligned with current importer flow.
2. Validation:
   - `uv run pytest -q tests/test_config_manager_mappings_integrity.py tests/test_config_manager_atomic_save.py tests/test_extracao.py`: `18 passed`
   - `uv run --python 3.13 python -m py_compile core/config_manager.py extracao/extractor.py`: pass
   - `uv run ruff check ...`: pass
   - `uv run ty check core/config_manager.py extracao/extractor.py`: pass
3. Operational effect:
   - reduced active severe queue noise by separating already-covered items from unresolved runtime work.

## Update 2026-02-28 (sprint 25 graves v5: closure docs + release bump)

Delivered in this closure slice:
1. Continuity docs synchronized:
   - `docs/NEXT_CHAT_MIGRATION.md` received a new top `CURRENT TRUTH` block.
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` received a new top authoritative block.
2. Local release bumped by +0.1:
   - `VERSION` now `4.25.0`.
   - `config/version.json` updated to `version_short=4.25`.
   - `README.md` and `docs/HISTORICO_RELEASES.md` aligned to `v4.25.0`.
3. Scope guard:
   - no GUI layout/position change in this slice.
   - no broad refactor; docs and release metadata only.

## Update 2026-02-28 (sprint 25 graves v4: command handlers + importer + stream wrappers)

Delivered in this sprint extension:
1. `interface/command_handlers.py`
   - mapping path validation and centralized path resolution.
   - guarded fallback for `display_mappings` loading failures.
   - mapping cache clear after save and broader save fallback guard.
2. `core/app_logic.py`
   - early cancel check immediately after extraction.
   - explicit guard for unexpected `None` from extractor.
   - extractor error normalization with non-empty fallback message.
3. `scripts/pytest_stream_common.py`
   - configurable reader thread join timeout via env.
   - timeout/normal/exception paths now share the configured join timeout.
4. Tests:
   - `tests/test_command_handlers_load_mappings.py`
   - `tests/test_command_handlers_save_settings.py`
   - `tests/test_import_single_error_classification.py`
   - `tests/test_stream_log_wrapper_guards.py`
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest package: `30 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 20 graves v3: rescan + stream robustness)

Delivered in this sprint package:
1. `gui/widgets/rescan_progress_dialog.py`
   - finish path is now idempotent under duplicated signals.
   - dialog close remains blocked during running cancel phase.
2. `gui/ssa/gui_workers.py`
   - start path now prunes retired rescan workers before active checks.
   - stale active worker refs are cleared before spawning a new worker.
   - cancel status is deterministic even if worker already stopped.
   - post-dialog running path refreshes metadata timestamp and cap cleanup remains consistent.
   - post-dialog non-running path now re-prunes retired workers.
3. `scripts/pytest_stream_common.py`
   - queue poll timeout is now configurable via `PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS`.
   - loop exit conditions were tightened to avoid unnecessary waits after process completion.
   - sentinel path does not increase dropped-line counters.
4. Focused tests updated:
   - `tests/test_rescan_progress_dialog.py`
   - `tests/test_gui_workers_rescan_data.py`
   - `tests/test_stream_log_wrapper_guards.py`
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `15 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 10 graves v2: rescan dialog/worker + stream wrapper)

Delivered in this sprint package:
1. `gui/widgets/rescan_progress_dialog.py`
   - cancel now keeps dialog open until process completion; no premature close while running.
2. `gui/ssa/gui_workers.py`
   - active-worker gate now uses robust running helper and clears stale active ref before start.
   - global worker cap now drops matching metadata entries.
3. `scripts/pytest_stream_common.py`
   - added dropped-warning interval parser (`PYTEST_STREAM_DROPPED_WARN_EVERY`) with bounds.
   - warning cadence made deterministic (`1` then each configured interval).
   - sentinel path excluded from dropped-line accounting.
4. Tests:
   - updated/added focused coverage in `tests/test_rescan_progress_dialog.py`, `tests/test_gui_workers_rescan_data.py`, `tests/test_stream_log_wrapper_guards.py`.
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `12 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 10 graves: config/lifecycle/streamlit hardening)

Delivered in this sprint package:
1. `gui/gui_config.py`
   - runtime path resolver API added and loader now resolves GUI config path dynamically.
2. `tests/test_gui_main_configuration.py`
   - runtime env path reflection regression (`SSA_CONFIG_DIR`).
   - explicit `config_path` precedence regression over env.
3. `dev_env/streamlit_app.py`
   - width-profile memory now ignores unknown bucket keys.
   - non-positive viewport hints now fallback to profile baseline width.
   - API snapshot clear helper now has explicit idempotent guard.
4. `tests/test_streamlit_filter_cache.py`
   - regressions for invalid bucket filtering, non-positive viewport fallback, and idempotent API snapshot clear.
5. `gui/gui_ssa.py` + `tests/test_gui_filter_logic.py`
   - closeEvent rescan shutdown keeps defensive stop/quit path when worker is globally retained.
   - regression verifies running-helper path under unstable `isRunning` behavior.
6. Validation:
   - `py_compile`, `ruff`, `ty`: pass on touched scope.
   - focused `pytest`: `150 passed, 1 skipped`.
7. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 5 slices graves: lifecycle/config/canonical/api)

Delivered in this sprint package:
1. `gui/gui_ssa.py`
   - closeEvent rescan retention now enforces cap with metadata cleanup for dropped workers.
   - retain path now refreshes worker timestamp on each retain operation.
2. `tests/test_gui_filter_logic.py`
   - new coverage for rescan global cap/meta consistency.
   - new coverage for canonical available columns keeping active filter columns when outside non-null cache.
3. `tests/test_gui_main_configuration.py`
   - new fallback regression for missing `SSA_CONFIG_DIR`.
4. `dev_env/streamlit_app.py` + `tests/test_streamlit_filter_cache.py`
   - centralized API snapshot clear helper and focused regression.
5. Validation:
   - `py_compile`: pass
   - `ruff`: pass
   - `ty`: pass
   - focused `pytest`: `145 passed, 1 skipped`
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (streamlit width-profile memory + tabs/api smoke)

Delivered in this streamlit slice:
1. Item 2 delivered first:
   - added width-profile memory by width bucket in `dev_env/streamlit_app.py` (`width_profile_by_bucket`).
   - no GUI layout/position changes.
2. Item 1 delivered after item 2:
   - stabilized tab labels via `MAIN_TAB_LABELS`.
   - added `_api_snapshot_available(...)` helper and used it in API snapshot render gate.
3. Focused tests added in `tests/test_streamlit_filter_cache.py`:
   - width bucket thresholds
   - width-profile memory normalize/resolve/remember
   - stable tab labels
   - API snapshot permutations
4. Validation:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`21 passed`)
5. Kluster:
   - `kluster_code_review_auto` on touched files: clean

## Update 2026-02-28 (streamlit telemetry profile window cap)

Delivered in this streamlit slice:
1. Added bounded profile window for render telemetry stats in `dev_env/streamlit_app.py`.
2. Added focused regression in `tests/test_streamlit_filter_cache.py`.
3. Validation:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`16 passed`)

## Update 2026-02-28 (kluster package closeout: config hierarchy + closeevent lifecycle)

Delivered in this package:
1. `gui/gui_config.py` now resolves GUI preferences path with `SSA_CONFIG_DIR` (safe fallback kept).
2. `gui/gui_ssa.py::closeEvent` now has defensive global-retention fallback for active rescan worker.
3. Focused regressions added:
   - `tests/test_gui_main_configuration.py::test_load_gui_main_preferences_honors_ssa_config_dir`
   - `tests/test_gui_filter_logic.py::test_close_event_retains_rescan_worker_when_isrunning_check_fails_mid_shutdown`
4. Focused validation:
   - `uv run --python 3.13 python -m py_compile` (touched files): pass
   - `uv run ruff check` (touched files): pass
   - `uv run ty check` (touched files): pass
   - focused `pytest`: pass

## Update 2026-02-27 (residual main-config-gui closeout)

Delivered in this doc slice:
1. Closed residual runtime group in control docs:
   - `39, 46, 49, 50, 70, 76` now marked `resolved` in `docs/PENDING_ACTION_MATRIX.md`.
2. Synced top authoritative blocks for continuation:
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
3. Kept scope strictly documentation-only (no runtime code edits).

Operational next step:
1. Continue with minimal slices from active residual queue:
   - none (matrix pending queue is now empty).
2. Keep streamlit stabilization as separate track.
3. Item `9` status in this historical block is superseded by Sprint D closeout (`resolved`).

## Update 2026-02-27 (id 27 testing closure)

Delivered in this minimal slice:
1. Closed matrix item `27` by reinforcing the cancellation progress contract test.
2. Test update:
   - `tests/test_import_cancellation.py` now asserts `finish_payload["errors"] == []`.
3. Validation:
   - `uv run --python 3.13 python -m py_compile tests/test_import_cancellation.py`: pass
   - `uv run ruff check tests/test_import_cancellation.py`: pass
   - `uv run ty check tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancel_before_insert.py`: pass

## Update 2026-02-27 (ids 22-23 testing closure)

Delivered in this minimal slice:
1. Closed matrix items `22` and `23` in `tests/test_database_optimized_alias_views.py`.
2. Test update:
   - explicit `initialize_database(...)` success assertion in both tests.
   - explicit db-file cleanup in `finally` remains in place.
3. Validation:
   - `uv run --python 3.13 python -m py_compile tests/test_database_optimized_alias_views.py`: pass
   - `uv run ruff check tests/test_database_optimized_alias_views.py`: pass
   - `uv run ty check tests/test_database_optimized_alias_views.py`: pass
   - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass

## Update 2026-02-27 (id 21 testing closure)

Delivered in this minimal slice:
1. Closed matrix item `21` based on existing concurrent-write test coverage.
2. Evidence:
   - `tests/test_caching_atomic_save.py::test_save_cache_concurrent_writes_remain_valid_json`.
3. Validation:
   - `uv run pytest -q tests/test_caching_atomic_save.py`: pass

## Update 2026-02-27 (ids 24-25 testing closure)

Delivered in this minimal slice:
1. Closed matrix items `24` and `25` using existing hardened regression tests.
2. Evidence:
   - lock coverage: `tests/test_filter_cache_locking.py`
   - modal skip coverage: `tests/test_filter_error_skips_modal_in_pytest.py`
3. Validation:
   - `uv run pytest -q tests/test_filter_cache_locking.py`: pass
   - `uv run pytest -q tests/test_filter_error_skips_modal_in_pytest.py`: pass

## Update 2026-02-27 (id 9 deferred by decision)

Delivered in this doc slice:
1. Matrix item `9` moved from `pending` to `deferred`.
2. Rationale:
   - explicit user decision (Opcao A) to avoid runtime behavior change in current sprint.
3. Historical note:
   - status later superseded in 2026-02-28 Sprint D closeout (`resolved`).

## Update 2026-02-27 (continuity triage validation closeout)

Delivered in this doc-only slice:
1. Ran continuity triage for interrupted runtime patch scope.
2. Local validation rerun completed and green:
   - `uv run --python 3.13 python -m py_compile` (touched runtime files)
   - `uv run ruff check` (touched runtime files)
   - `uv run ty check` (touched runtime files)
   - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
     - `121 passed, 1 skipped`
3. kluster auto rerun on touched runtime files returned clean (no issues).

Operational next step:
1. Continue with next minimal runtime slice only.
2. Keep same gate sequence after any new edit.

## Update 2026-02-27 (interrupted handoff sync for continuation)

Delivered in this doc-only slice:
1. Added top authoritative continuity blocks in:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
2. Captured interrupted runtime patch evidence for active filter stability work:
   - `gui/ssa/gui_filters_advanced_ui.py`
   - `gui/mixins/filter_gui_ssa_mixin.py`
   - `gui/widgets/column_manager_dialog.py`
   - `gui/gui_ssa.py`
   - `gui/ssa/gui_workers.py`
3. Added explicit restart order for the next chat before any new slice.

Pending before closing runtime slice:
1. Run kluster auto on touched files and resolve findings with minimal patch.
2. Run local gates on touched scope:
   - `python -m py_compile`
   - `ruff check`
   - `ty check`
   - focused `pytest`
3. Update pending matrix status after verification outcome.

## Update 2026-02-26 (lower panel single height lock)

Delivered in this slice:
1. Implemented single synchronized height lock for all 3 lower panels:
   - details panel
   - advanced filters panel
   - column filters panel
2. Added centralized methods in main window:
   - `_compute_bottom_panel_target_height()`
   - `_queue_bottom_panel_height_sync()`
   - `_sync_bottom_panel_heights()`
3. Hooked sync in:
   - initial UI build (`singleShot`)
   - tab change
   - resize event
   - column-filter panel rebuild
4. Added regression lock test:
   - `tests/test_gui_filter_logic.py::test_bottom_panels_keep_single_synced_height_after_resize`

Validation:
1. `python -m py_compile` pass.
2. `ruff check` pass.
3. `ty check` pass.
4. focused pytest pass.
5. full `uv run pytest -q` pass (`582 passed, 6 skipped, 11 subtests passed`).
6. Code evidence:
   - `gui/gui_ssa.py`: centralized sync methods and resize/tab/init hooks.
   - `gui/mixins/tab_context_gui_ssa_mixin.py`: deferred queue sync on bind.
   - `gui/mixins/filter_gui_ssa_mixin.py`: sync call after column-filter panel rebuild.
   - `tests/test_gui_filter_logic.py`: equal-height regression test.

Notes:
1. This slice does not change horizontal distribution policy.
2. Remaining visual tuning is limited to future micro-adjustments if required by user screenshots.

## Update 2026-02-26 (md audit + ssa tab consistency)

Delivered in this slice:
1. General MD audit re-run:
   - active operational docs refreshed;
   - version-specific/historical docs preserved by design.
2. GUI status consistency in filter flows:
   - clear search and clear-all paths now use `Status: SSAs filtradas: N de M`.
3. Column-filter footer button styling consistency:
   - `Adicionar filtro de coluna` and `Limpar todos filtros de colunas` now share the same theme style.
4. Validation gate executed for touched scope:
   - `python -m py_compile` pass
   - `ruff check` pass
   - `ty check` pass
   - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
     => `117 passed, 1 skipped`.
5. Structural note from kluster kept deferred:
   - `FilterGUISSAMixin` monolith split remains out of scope for this stabilization slice and stays in dedicated refactor sprint queue.
6. Compatibility-null fields policy applied in GUI selectors:
   - hidden from add-column-filter and column manager offerings:
     `registros_espera`, `num_reprobaciones`, `situacao_espera`, `numero_desvios`,
     `ate`, `justificativa`, `parciais`, `situacao_da_parcial`.
   - kept in DB for compatibility only.
7. Long-term pending:
   - investigate ingestion/data lineage for compatibility-null fields to determine if they are expected-null
     or import defects before any schema cleanup decision.

## Update 2026-02-26 (md audit + gui table/status hardening)

Delivered in this slice:
1. Global MD audit executed with separation:
   - updated active docs;
   - preserved version-specific/historical docs for consultation.
2. GUI table rendering now normalizes multiline cell text to single line before paint, avoiding clipping in fixed row height.
3. Filter status now reports consistent counter format:
   - `Status: SSAs filtradas: N de M ...`
4. Added/updated focused tests in `tests/test_gui_filter_logic.py` for:
   - multiline text rendering without newline clipping;
   - filtered status counter consistency.

MD scope decision:
1. Maintained as historical by design:
   - release-specific notes (`docs/RELEASE_NOTES_*`, historical release files);
   - handoff archives with explicit top status pointers.
2. Updated as active:
   - `README.md`, `docs/HISTORICO_RELEASES.md`, `docs/FILTER_TAB_OPTIMIZATIONS.md`,
     `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`, `docs/NEXT_CHAT_MIGRATION.md`,
     `docs/PENDING_ACTION_MATRIX.md`, `docs/GUI_PYQT6_REGRAS_GERAIS.md`,
     `docs/QWEN_CODE_DELEGATION_CONFIG.md`.

Deferred (non-blocking, dedicated sprint only):
1. `gui/mixins/filter_gui_ssa_mixin.py` remains structurally large.
2. Scope split into managers/resolvers is intentionally deferred to dedicated refactor sprint to avoid transversal risk in this stabilization cycle.

## Update 2026-02-26 (column filter regression tests lock)

Delivered in this slice:
1. Added focused regression tests in `tests/test_gui_filter_logic.py`:
   - `test_add_column_menu_includes_full_candidates_and_excludes_legacy_aliases`
   - `test_clear_all_column_filters_restores_defaults_and_hidden_lines`
   - `test_default_column_filter_rows_show_apply_and_hide_buttons`
2. Locked previously uncovered behavior for:
   - full add-column candidate menu;
   - legacy ghost alias exclusion (`No SSA`, `Data Cadastro`);
   - clear-all restoring default visible rows with empty values;
   - hidden line reset on clear-all.

Validation:
1. `python -m py_compile tests/test_gui_filter_logic.py` pass.
2. `ruff check tests/test_gui_filter_logic.py` pass.
3. `ty check tests/test_gui_filter_logic.py` pass.
4. `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py` pass (`97 passed, 1 skipped`).
5. Related suites:
   - `.venv/bin/python -m pytest -q tests/test_gui_main_configuration.py` pass.
   - `.venv/bin/python -m pytest -q tests/test_display.py tests/test_streamlit_filter_cache.py` pass.

## Update 2026-02-26 (GUI column filter alias hardening)

Delivered in this slice:
1. Removed legacy invalid alias keys from GUI main preferences:
   - dropped `Numero da SSA`/`No SSA` legacy key path.
   - dropped `Data Cadastro` legacy key path.
2. Hardened GUI preferences merge to ignore only known legacy invalid keys, without blocking custom valid keys.
3. Hardened add-column-filter menu to avoid showing legacy ghost aliases while preserving valid internal `numero_ssa`.
4. Kept DB schema unchanged; verified `ssa_table`/`ssas` contain `numero_ssa` and do not contain `No SSA`.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched Python files.
2. focused pytest:
   - `tests/test_gui_filter_logic.py -k "clear_all_column_filters or column_filter or add_column_filter"` => pass
   - `tests/test_gui_config.py` => pass
3. kluster auto: clean after final patch set.

Non-blocking deferred item:
1. `config/gui_poc_preferences.json` still contains legacy non-internal display-mapping keys (`Numero da SSA`, `Semana de Cadastro`, `Data Cadastro`, `Descricao Execucao`).
2. This file is not part of the active main GUI runtime path; schedule cleanup in dedicated low-risk config slice to keep parity.

## Update 2026-02-26 (sprints A B C delivered on codex/dev-filtros-stability)

- Sprint A delivered (extractor contract hardening):
  - ids closed: `6, 7, 33, 34, 35, 58`
  - evidence: focused extractor contract tests added and passing.
- Sprint B delivered (rescan worker/dialog hardening):
  - ids closed: `11, 12, 28, 29, 38, 79`
  - id `71` moved to `stale-doc` by expected behavior with explicit tests.
- Sprint C delivered (cli enhancement lock/write consistency):
  - ids closed: `13, 26, 30, 31, 41, 80`
  - evidence: lockfile-based serialization, bounded nonblocking retries, and atomic write path validated in focused tests.

Current next queue (post A/B/C):
1. Main/config/gui residual pending group: closed (`39, 46, 49, 50, 70, 76` resolved; `42` resolved; `43/44` stale-doc).
2. Active residual queue now: `9, 21, 22, 23, 24, 25, 27`.
3. Streamlit stabilization queue (separate track, approved by user).

## Update 2026-02-26 (deep analysis snapshot: kluster + lint/type gate)

Validation snapshot (no runtime code changes in this slice):
1. `py_compile`: pass.
2. `ruff check .`: pass.
3. `ty check .`: pass.
4. `flake8`:
   - full repo run produced heavy noise from `.venv` and generated trees;
   - targeted run confirms large style baseline debt (mainly `E501` and spacing).
5. `mypy`:
   - baseline type debt remains (missing stubs and typed-union issues on GUI/data modules).
6. `pylama`:
   - failed in current environment due missing `pkg_resources` (no dependency change applied by request).

Kluster manual review snapshot (chat `8fyr5a0z7ot`):
1. `scripts/run_pytest_stream_and_log.py`: P3 perf, P4 semantic/quality/perf, and P4 security path handling.
2. `scripts/run_pytest_stream_and_log_v2.py`: P3 security path handling plus P4 semantic/quality/perf.
3. `main.py`: P4 semantic/quality/perf (god function and logging overhead observations).
4. `core/config_manager.py`: P4 semantic/quality suggestions.
5. `gui/gui_ssa.py`: P3 quality (god class) plus P4 semantic/perf observations.

Pending horizon after deep analysis:
1. Curto prazo (bloqueante/alto risco, patch minimo):
   - add path traversal guard for `--log` in `scripts/run_pytest_stream_and_log.py` and `_v2.py`;
   - adjust flush policy in stream scripts to reduce I/O overhead without changing timeout/cancel semantics.
2. Medio prazo (alto impacto, media complexidade):
   - close remaining Batch 09/10 behavior points with focused tests (queue-full, warning dedupe, sentinel delivery).
   - harden `main.py` semantics only in minimal slices (no broad refactor).
3. Longo prazo (sprint exclusivo):
   - `SSAMainWindow` structural decomposition.
   - broad mypy/flake8 baseline cleanup across GUI and data layers.

Next execution steps (recommended order):
1. Stream scripts security/perf mini-slice (2 files + focused tests).
2. Stream scripts residual behavior lock (Batch 09/10 completion).
3. Main flow resilience slice (Batch 11).
4. Keep structural refactors in dedicated sprint only.

## Update 2026-02-26 (stream scripts security/perf mini-slice delivered)

Files changed:
1. `scripts/pytest_stream_common.py` (new shared runtime helper).
2. `scripts/run_pytest_stream_and_log.py` (now consumes shared runner).
3. `scripts/run_pytest_stream_and_log_v2.py` (now consumes shared runner).
4. `tests/test_stream_log_wrapper_guards.py` (new focused guards).

Delivered in this slice:
1. `--log` path guard hardened with shared validation and explicit deny outside `local_ai_private`.
2. flush policy changed to batched strategy (`PYTEST_STREAM_FLUSH_EVERY`, bounded) to avoid flush-per-line overhead.
3. stream runtime duplication reduced by centralizing queue/timeout/process-tree handling into shared helper.
4. sentinel handling changed to non-blocking best-effort path; main loop now closes by process state + reader_done signal.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `pytest -q tests/test_stream_log_wrapper_guards.py` green (`4 passed`).
3. kluster residual after fixes:
   - `scripts/pytest_stream_common.py::run_streaming_pytest` flagged as structural complexity (`god function`).
   - decision: defer to dedicated refactor sprint (non-blocking for current security/perf patch).

## Update 2026-02-26 (batch11 main resilience delivered)

Files changed:
1. `main.py`
2. `tests/test_main_import_fallback.py`

Delivered:
1. optimized import failure now has explicit context logging and deterministic fail-fast by default.
2. no automatic legacy retry is attempted, including `--force-rescan`, avoiding duplicated heavy reprocess.
3. `--version` path simplified (no broad `except`).
4. log-level invalid message normalized to ASCII.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py` green (`3 passed`).
3. kluster auto for `main.py` + focused test returned clean.

## Update 2026-02-26 (config mappings restore fallback lock)

Files changed:
1. `tests/test_config_manager_mappings_integrity.py`

Delivered:
1. added regression lock for `load_display_mappings_integrity` when restore write fails.
2. added regression lock for `load_column_mappings_integrity` when restore write fails.
3. both paths are asserted to return in-memory defaults without crash.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `uv run pytest -q tests/test_config_manager_mappings_integrity.py` green (`4 passed`).
3. kluster auto clean.

## Update 2026-02-25 (approved execution marker: filtros avancados ui stabilization)

Status:
1. user approved execution plan before code edits.
2. next implementation will run in 4 slices with minimal scope drift and focused validation.

Approved scope for next slice:
1. prevent advanced filters panel from stealing table reading area.
2. replace fixed breakpoint layout policy (wide/mid/narrow) with continuous responsive distribution.
3. restore reprogramacoes behavior in initial refresh and apply flow.
4. more aggressive control redesign in advanced filters panel:
   - ste control migration from checkbox to toggle-style button.
   - stronger cleanup of button width policy to remove fragile fixed-width behavior.

## Current sprint status snapshot (PR 31)

- Operational:
  - `gh pr checks 31` voltou a responder.
  - estado atual:
    - `code/snyk (mauriciomenon)` falha por limite de plano (`Code test limit reached`).
    - `security/snyk (mauriciomenon)` falha por limite de plano (`You have used your limit of private tests`).
    - demais checks principais em `pass` (DeepScan, DeepSource, submit-pypi, GitGuardian, Socket, cubic).
- Delivered hardening slices (low risk, no GUI layout change):
  - `utils/caching.py`: removed silent suppress in temp cleanup, added explicit warnings.
  - `armazenamento/database.py`: removed silent suppress in config listing fallback, added explicit warning.
  - `interface/table_printer.py`: removed silent suppress in label normalization fallback, added explicit debug log.
  - `shared/numero_ssa.py`: replaced silent year-parse suppress with explicit `try/except ValueError`.
- Remaining sprint recommendation (kept as pending by decision):
  - E delivered: removed pytest ignores from `pyproject.toml` and converted legacy script-like files into deterministic tests.
  - Ty warning cleanup (non-blocking): remove legacy unused `type: ignore` comments in `armazenamento/database.py` in a dedicated low-risk slice, after PR #31 stabilization.

- Quality hardening adopted for advanced-filters facade:
  - Fixed runtime contract break where `gui/gui_ssa.py` expected symbol `_has_active_advanced_filters` from aggregated module.
  - Added guarded fallback path in facade and regression tests for primary/fallback/no-handler flows.
  - Added direct logic coverage for:
    - `solicitante` include/exclude compatibility (`solicitante` and legacy `responsavel_solicitante`);
    - `num_reprogramacoes` activation detection in `_has_active_advanced_filters`;
    - week-range filter path with explicit nonlocal mask update.
    - priority key/column mapping (`prioridade_*_values` and dataset `grau_prioridade_*`).
  - Added static key coverage test to prevent UI-key drift against logic/active detector.
  - New dedicated docs for this flow:
    - `docs/QA_FACADE_FILTERS.md`
    - `docs/NEXT_CHAT_MIGRATION.md`

- External IA intake workflow (active):
  - Accept report only with `arquivo:linha` evidence.
  - Re-validate every finding locally with `rg -n` and `nl -ba`.
  - Patch in atomic slices only.
  - Keep non-blocking findings in this backlog.

## External IA intake snapshot (2026-02-17)

- Revalidated findings with local evidence:
  - `RPT-P1-02` confirmed: `_has_active_advanced_filters` missing in aggregated exports.
  - `RPT-P1-01` confirmed: `responsavel_emissor` key exists in UI/logic but column is missing in `config/schema.sql`.
  - `RPT-P2-06` confirmed: coverage test was one-way and also had invalid regex under Python 3.13.
- Action now completed:
  - Re-exported `_has_active_advanced_filters` in `gui/ssa/gui_filters_advanced.py`.
  - Fixed regex and added reverse key-coverage guard in `tests/test_gui_filters_advanced_logic.py`.
- Decision applied:
  - `RPT-P1-01` resolved with path B:
    - removed/disabled `responsavel_emissor` advanced-filter flow from UI/logic detector.
    - kept backward-safe UI context attrs only to avoid tab binding regressions.
- Deferred to backlog (non-blocking in current slice):
  - `RPT-P2-03` dead branch `data_execucao` in year execucao filter.
  - `RPT-P2-04` `semana_*_exclude` hardcoded false in UI.
  - `RPT-P2-05` add dedicated migration tests for legacy `ano_*` keys.
  - `RPT-P3-07` evaluate cache key extension to include advanced filters context.
  - `RPT-P3-08` nomenclature normalization for priority keys/columns.

## Rescan evidence snapshot (2026-02-17)

- Input from latest modular rescan:
  - total files: 75
  - processed successfully: 64
  - errors: 11
- All 11 errors are from `SSAs Derivadas e Relacionadas_*.xlsx` with:
  - `Missing required columns after normalization: ['data_cadastro', 'descricao_ssa']`
- New action item (high priority):
  - keep main importer strict required columns for regular SSA sheets.
  - done: automatic derivadas sync trigger now consumes `SSAs Derivadas e Relacionadas_*.xlsx` through `armazenamento/derivadas_sync.py` (sheet source), not through main SSA extractor gate.
  - done: trigger runs after import loop; special files are skipped from main extractor and handled by derivadas sync.
  - current behavior: when multiple special sheets are present, importer picks the latest file by mtime for sync and marks all special files in cache on successful sync.

## P0 blockers

- Clear legacy `CHANGES_REQUESTED` state from old bot reviews on PR #25.
- Define repo policy for external check waivers when provider plan limits are hit.

## P1 hardening targets

- SSAMainWindow God Class (gui/gui_ssa.py ~6k lines):
  - Split UI layout, filtering/controller logic, and theming into separate modules.
  - Plan refactor in a dedicated sprint; avoid cross-cutting changes in this PR.
  - Define seams for unit tests before extraction to reduce regression risk.
- Derivadas c2 follow-up (db and related tools only):
  - Keep derivadas sync/maintenance decoupled from import flow; trigger via `scripts/derivadas_cli.py` or scheduler only.
  - Add controlled runbook for `scripts/derivadas_cli.py sync --full-rebuild` with rollback notes.
  - Validate external sheet column aliases (`parent_ssa`, `child_ssa`, `relation_label`) against real files.
  - Add focused regression test for mixed-source conflict reporting (db vs sheet) with stable fixtures.
  - Add migration smoke check for legacy `ssa_derivada_matrix` variants before enabling auto-sync broadly.
- Extract shared process termination helper for:
  - `scripts/run_pytest_stream_and_log.py`
  - `scripts/run_pytest_stream_and_log_v2.py`
  - `scripts/run_pytest_with_timeout.py`
  - `scripts/run_pytest_with_timeout_v2.py`
- Reduce broad `except Exception` in pytest wrapper scripts where specific exceptions are known.
- Start timeout clock at process start (`Popen`) for wrapper consistency.
- Improve fallback hash in `gui/workers/filter_worker.py` to include columns in fallback path.
- Revisit `concat + drop_duplicates` in `gui/workers/filter_worker.py` for large DataFrame performance.
- Standardize log levels and use `logger.exception` where traceback is required in `gui/gui_ssa.py`.
- Plan transversal `except ... pass` cleanup in GUI code, no layout changes.
- Add stronger user-facing diagnostics for config fallback cases in `gui/gui_config.py`.
- Validate worker retention strategy in long runs and add simple retention telemetry.
- Refactor `gui/ssa/gui_theme.py` (apply_theme muito grande) em sprint dedicado, sem mudar layout.
- Revisar cleanup/retention em `gui/ssa/gui_workers.py` (fluxo complexo) em sprint dedicado.
- Tratar diagnosticos estruturais de `ty` em `gui/gui_ssa.py` (stubs/headless e unions PyQt), com estrategia de tipagem dedicada e sem mexer em layout.

## P2 cleanup and consistency

- Align dependency declarations between `pyproject.toml` and `requirements*.txt`.
- Revisit `requires-python >=3.13` and confirm minimum supported version.
- Remove redundant imports and unused logger references in import verification scripts.
- Normalize success/failure contract in `tests/run_import_detailed.py`.
- Improve `.gitignore` pattern tests in `tests/test_release_artifact_guard.py`.
- Add integration tests for stream wrapper edge cases:
  - full queue,
  - closed pipe while reader is active,
  - forced timeout with kill escalation.
- Mark performance-sensitive tests explicitly to reduce CI flakiness.
- Revisit smoke GUI fixture isolation to prevent accidental real `load_data` execution.
- Define bot review cadence to reduce duplicate noise in large PRs.
- Reassess active review apps and disable redundant ones.
- Add merge checklist in PR template:
  - known risks,
  - accepted waivers,
  - mandatory follow-up links.
- Rever `pyproject.toml` addopts com ignores de testes e considerar remocao para ampliar cobertura (sugestao para relatorio final do sprint atual).
- Ajustar seletor "Configurar colunas visiveis" para sempre exibir nomes amigaveis (display names) em vez de nomes internos de coluna quando disponiveis.
- Centralizar persistencia de largura de coluna em fluxo unico (manager/config), evitando logica espalhada entre cache local de GUI e manipuladores de tabela.

## Execution model

- Use atomic commits per topic.
- Keep rollback easy by changing one concern at a time.
- Prefer low-risk defensive changes first, then structural cleanup.

## Review tracking (source PR 31)

This legacy section was replaced by the canonical active queue in docs/PENDING_ACTION_MATRIX.md.
Historical review-thread entries were removed here to avoid duplicate pending counts.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.
- Pendencia nao bloqueante: extrair a funcao `_rebuild_multiselect_menu` em blocos menores (layout/estilo/eventos) sem alterar comportamento visual.

## Atualizacao 2026-03-03 (pre-entrega PR, pendencias nao bloqueantes)
- Revisar parametrizacao de `docs_dir/data_dir/db_name/table_name` em `gui/workers/rescan_worker.py` para reduzir hardcode e facilitar teste.
- Revisar classificacao de falhas deterministicas em `core/app_logic.py` para migrar de substring de mensagem para codigo/sinal explicito.
- Padronizar instalacao de dependencias de desenvolvimento (`dependency-groups` vs `optional-dependencies`) e documentar comando oficial de `uv`.
- Nota de politica vigente: sync automatico de derivadas permanece restrito a rescan full/forcado e acao manual dedicada.
- Corrigir botao/fluxo de limpeza da pesquisa geral: apos `Enter` em pesquisa geral, o termo anterior nao esta sendo limpo de forma consistente.

## Atualizacao 2026-03-03 (pos-merge PR42 no branch dev - triagem de reviews)
- Contexto:
  - PR #42 foi aceito e mergeado em `dev`.
  - Esta secao registra triagem tecnica dos comentarios Copilot/Cubic pos-merge.

- Confirmado como bug real (prioridade alta para proximo ciclo):
  - `core/app_logic.py`:
    - `BEGIN IMMEDIATE` seguido de `PRAGMA wal_checkpoint(TRUNCATE)` no mesmo bloco pode falhar por lock no checkpoint.
    - Acao: separar checkpoint da transacao explicita e validar com teste focado de lock.

- Confirmado como decisao intencional (nao corrigir agora):
  - `core/app_logic.py`:
    - `auto_derivadas_sync_enabled = bool(force_import)` e gate de sync pos-import.
    - Politica atual mantida: sync automatico de derivadas somente em full rescan/forcado ou acao manual (`Atualizar Derivadas`).
    - Acao opcional futura: adicionar log explicito quando houver planilha de derivadas em import incremental e sync for pulado por politica.

- Pendencias nao bloqueantes (deferidas):
  - `core/app_logic.py`: substituir classificacao por substring de erro por codigo/sinal estruturado em `ExtractionError`.
  - `armazenamento/database_upsert_logic.py` vs `armazenamento/database_optimized.py`: centralizar normalizacao/validacao canonica de SSA para evitar drift.
  - `core/app_logic.py`: adicionar teste unitario cobrindo cache de falha deterministica e skip em execucao seguinte sem mudanca de hash/mtime.
  - `AGENTS.md`: trocar caminho absoluto do backlog por caminho relativo de repo.
  - `docs/OHMYOPENCODE_MANUAL.md`: trocar `/Users/menon/...` por `$HOME/...` para portabilidade.
  - `docs/OPENCODE_CONFIG.md`: alinhar nome de modelo Gemini entre secoes para evitar identificador inconsistente.
  - `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`: documentar fallback runtime sem hardcode fixo em `--python 3.13`.
  - `interface/cli_enhancement_manager.py`: revisar TOCTOU em lock-file (`exists` + `open` nao atomico).
  - `docs/ARQUITETURA_IMPORTACAO.md`: remover recomendacao incorreta de `pd.read_excel(..., chunksize=...)`.
  - `gui/ssa/gui_table.py`: avaliar remocao de helper morto (`_calculate_max_chars_for_column`) ou reuso explicito.
