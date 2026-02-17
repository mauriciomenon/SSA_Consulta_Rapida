# GUI_SSA_REFACTOR_NOTES.md

Status: notes only, tracked during sprint, remove after. ASCII only.

## Goal
Refactor gui/gui_ssa.py into a gui/ssa/ subpackage with explicit file names,
preserving GUI layout and runtime behavior. Keep SSAMainWindow public API stable.

## Target layout (approved)
1. gui/gui_ssa.py - facade, stable imports, QT_AVAILABLE and stubs remain here.
2. gui/ssa/gui_theme.py - _get_theme_catalog, _resolve_startup_theme, apply_theme, _apply_macos_contrast, QSS helpers.
3. gui/ssa/gui_workers.py - _retain_*, _prune_*, load_data and callbacks.
4. gui/ssa/gui_filters_advanced.py - aggregated facade for advanced filters exports.
5. gui/ssa/gui_filters_advanced_ui.py - advanced filters UI state capture/sync.
6. gui/ssa/gui_filters_advanced_logic.py - DataFrame filtering logic and caches.
7. gui/ssa/gui_filters_advanced_state.py - shared constants/state cache helpers.
8. gui/ssa/gui_table.py - column widths, render, pagination.
9. gui/ssa/gui_details.py - details and highlight logic.

Rationale: file names carry the GUI tag to help manual editing across multiple files.

## Required header comments in new files
Each file must declare its relation to the others at the top. Template examples:

```text
# gui/ssa/gui_theme.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: depends on gui/helpers/theme_helpers.py and utils/themes.py.
# Relation: does not touch data loading or filters.
```

```text
# gui/ssa/gui_workers.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: uses gui/workers/DataLoaderWorker and globals in gui/gui_ssa.py.
# Relation: owns worker retention and load_data flow, no UI layout changes.
```

```text
# gui/ssa/gui_filters_advanced.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: builds advanced filter UI and applies advanced filters to DataFrame.
# Relation: interacts with FilterGUISSAMixin state but does not own basic search flow.
```

```text
# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: controls table render, column widths, and pagination helpers.
# Relation: does not modify filter state.
```

```text
# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: builds details HTML and highlight logic.
# Relation: uses gui/helpers/formatting_helpers.highlight_text where possible.
```

## Existing structure (key files)
1. gui/gui_ssa.py - single large module with SSAMainWindow and heavy state.
2. gui/mixins/filter_gui_ssa_mixin.py - filtering flow and worker orchestration.
3. gui/helpers/formatting_helpers.py - normalize_chunk_for_parse, format_search_display, highlight_text.
4. gui/helpers/theme_helpers.py - QSS builders.
5. gui/workers/data_loader_worker.py - data loading from SQLite.
6. gui/workers/filter_worker.py - filtering with cache.
7. gui/workers/rescan_worker.py - rescan pipeline.
8. gui/widgets/* - dialogs and widgets (column manager, paginator, rescan dialog).

## Module level items in gui/gui_ssa.py
1. QT_AVAILABLE and stub classes for headless mode.
2. Global worker retention lists:
   - GLOBAL_RETIRED_DATA_LOADER_WORKERS, GLOBAL_RETIRED_DATA_LOADER_META, MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS
   - GLOBAL_RETIRED_RESCAN_WORKERS, GLOBAL_RETIRED_RESCAN_META, MAX_GLOBAL_RETIRED_RESCAN_WORKERS
   - RETIRED_WORKER_TTL_SEC, RETIRED_WORKER_FORCE_WAIT_MS
3. DB_PATH, TABLE_NAME.
4. UI constants: DETAILS_DIALOG_*, HIGHLIGHT_*, MONO_FONT_FAMILY.
5. DIVISAO_SETORES, SECTOR_TO_DIV.
6. DETAIL_FIELD_PRIORITY, DETAIL_DISPLAY_OVERRIDES.
7. Helper functions: _is_widget_valid, load_display_mappings.

## SSAMainWindow state inventory (from __init__)
Data and filters:
- df_completo, df_exibido, df_para_tabela.
- display_map, internal_to_display, default_columns, visible_columns.
- filter_profiles, default_filter_profile, current_filter_profile.
- _profile_base_filters, _profile_lock, _profile_columns, _column_or_groups, _column_to_or_group.
- _exclude_ste_sca, _pending_search_display.
- sort_column, sort_ascending.
- _active_column_filters, _column_filter_inputs, _column_filter_labels.
- _pending_filter_focus.
- _df_last_search_filtered.
- _advanced_filters, _advanced_filters_active.
- _adv_options_dirty, _adv_sector_syncing, _adv_sector_handler_running.
- _last_derivada_origem.
- _responsavel_options_dirty, _responsavel_filters_materialized.
- _responsavel_all_prefixes, _responsavel_materialized_prefixes, _responsavel_dirty_prefixes.
- _menu_pre_show_hooks.

GUI config and theme:
- _current_theme, _highlight_bg_color, _highlight_text_color, _highlight_font_weight.
- _restored_page_size.
- _saved_gui_column_widths.
- _info_font.
- _week_label_style.

Managers and caches:
- width_manager (SimpleWidthManager), cache_manager (SimpleCacheManager).

Timers:
- _debounce_timer.
- _sector_debounce_timer.
- _sector_debounce_delay.

Workers:
- filter_thread (from mixin), data_loader_thread.
- _active_rescan_worker.

Tab context:
- _tab_contexts (created by _build_tab_content).

## SSAMainWindow TAB_WIDGET_ATTRS (UI widget attributes)
search_label, search_input, search_button, clear_filter_button, column_selector,
search_help, paginator, profile_selector, persistent_filters_layout,
filter_tags_widget, filter_tags_layout, exclude_ste_checkbox, col_filter_indicator,
filters_summary_frame, filters_summary_label, clear_all_filters_btn, export_list_btn,
undo_filter_btn, table_widget, details_group, details_text, col_filters_group,
col_filters_hint, col_filters_scroll, col_filters_container, col_filters_list_layout,
add_column_filter_btn, clear_all_btn, adv_filters_group, adv_executor_button,
adv_executor_menu, adv_executor_checks, adv_executor_exclude, adv_emissor_button,
adv_emissor_menu, adv_emissor_checks, adv_emissor_exclude, adv_divisao_button,
adv_divisao_menu, adv_divisao_checks, adv_divisao_exclude, adv_status_button,
adv_status_menu, adv_status_checks, adv_status_exclude, adv_year_emissao_button,
adv_year_emissao_menu, adv_year_emissao_checks, adv_year_execucao_button,
adv_year_execucao_menu, adv_year_execucao_checks, adv_week_emissao_start,
adv_week_emissao_end, adv_week_execucao_start, adv_week_execucao_end,
adv_prio_emissao_min, adv_prio_emissao_max, adv_prio_planejamento_min,
adv_prio_planejamento_max, adv_prazo_min, adv_prazo_max, adv_execucao_simples,
adv_execucao_simples_exclude, adv_execucao_parcial, adv_execucao_parcial_exclude,
adv_limite_vencido, adv_limite_vencido_exclude, adv_derivada_has_button,
adv_derivada_has_menu, adv_derivada_has_checks, adv_derivada_has_exclude,
adv_derivada_all_ste_button, adv_derivada_all_ste_menu, adv_derivada_all_ste_checks,
adv_derivada_all_ste_exclude, adv_responsavel_solicitante_button,
adv_responsavel_solicitante_menu, adv_responsavel_solicitante_checks,
adv_responsavel_solicitante_exclude, adv_responsavel_solicitante_box,
adv_responsavel_programacao_button, adv_responsavel_programacao_menu,
adv_responsavel_programacao_checks, adv_responsavel_programacao_exclude,
adv_responsavel_programacao_box, adv_responsavel_execucao_button,
adv_responsavel_execucao_menu, adv_responsavel_execucao_checks,
adv_responsavel_execucao_exclude, adv_responsavel_execucao_box,
adv_responsavel_emissor_button, adv_responsavel_emissor_menu,
adv_responsavel_emissor_checks, adv_responsavel_emissor_exclude,
adv_responsavel_emissor_box, adv_save_defaults_btn.

## Method map by domain
Theme and prefs:
- _get_theme_catalog, _get_theme_keys, _resolve_startup_theme, _persist_gui_preferences.
- apply_theme, toggle_theme_menu, _apply_macos_contrast.
Dependencies: utils/themes.py, gui/helpers/theme_helpers.py, GUI_MAIN_PREFERENCES.

UI and layout:
- init_ui, _build_tab_content, _bind_tab_context, _on_tab_changed.
- eventFilter, resizeEvent, _recompute_column_widths_on_resize, _apply_computed_widths_only, closeEvent.
Dependencies: Qt widgets, ColumnSelector, DataPaginator, ColumnManagerDialog.

Advanced filters UI:
- _make_multiselect_box, _attach_multiselect_menu, _update_multiselect_button,
  _rebuild_multiselect_menu, _sync_multiselect_checks.
- _build_advanced_filters_panel, _reorganize_advanced_filters_grid.
Dependencies: Qt widgets, TAB_WIDGET_ATTRS, DIVISAO_SETORES.

Advanced filters logic:
- _apply_advanced_filters_from_ui, _apply_advanced_filters.
- _sync_advanced_filter_ui, _refresh_advanced_filter_options.
- _clear_advanced_filters, _has_active_advanced_filters.
Dependencies: pandas, self.df_exibido, filter state.

Derivadas:
- _on_derivada_has_toggled, _on_derivada_all_ste_toggled.
- _show_derivadas_popup, _build_derivadas_tree, _update_derivadas_button_state.
- _get_derivadas_for_ssa, _filter_by_derivadas, _clear_derivadas_filter.
Dependencies: df_completo, df_exibido, format/display helpers.

Setor and responsavel:
- _sync_responsavel_flags, _mark_responsavel_dirty, _ensure_responsavel_options_materialized,
  _sync_responsavel_button_summaries.
- _schedule_sector_options_refresh, _collect_divisao_setores, _sector_sort_key,
  _sort_sectors, _sort_responsavel_values, _apply_divisao_to_setor_checks,
  _refresh_responsavel_options.
Dependencies: DIVISAO_SETORES, advanced filters UI.

Workers and data load:
- _retain_data_loader_worker_until_finished, _is_data_loader_worker_alive,
  _is_data_loader_worker_running, _prune_retired_data_loader_workers.
- _is_rescan_worker_running, _prune_retired_rescan_workers, _cleanup_data_loader_worker.
- load_data, on_data_loaded, on_load_error, on_load_finished.
Dependencies: gui/workers/DataLoaderWorker, global retention lists, df_completo.

Table and pagination:
- display_current_page, display_data.
- _force_column_widths, _ensure_nonzero_column_widths, _set_safe_width_for_col_index,
  _compute_gui_column_widths, _calculate_max_chars_for_column, _on_header_section_resized.
Dependencies: QTableWidget, SimpleWidthManager, GUI preferences.

## Controle de redundancia
Mantido conforme combinado. Nao removi nem alterei duplicacoes conhecidas. O foco foi apenas mover codigo. Vou seguir esse controle em todos os proximos slices.

## Slice details e highlight (aplicado)
Mudancas aplicadas:
- Mover detalhes/highlight/derivadas para gui/ssa/gui_details.py.
- Manter wrappers em gui/gui_ssa.py e configurar constantes via configure_details_constants.
- Sem mudanca de layout.

## Slice tema e menu (aplicado)
Mudancas aplicadas:
- Mover toggle_theme_menu e persistencia de preferencias para gui/ssa/gui_theme.py.
- Manter wrappers em gui/gui_ssa.py.
- Sem mudanca de layout.

## Slice workers (rescan) (aplicado)
Mudancas aplicadas:
- Mover rescan_data para gui/ssa/gui_workers.py.
- Manter wrapper em gui/gui_ssa.py.
- Sem mudanca de layout.

## QA gate and migration (active)

- Mandatory gate for any slice touching `gui/gui_ssa.py` or `gui/ssa/gui_filters_*`:
  - `uv run pytest -q tests/test_gui_filters_facade_contract.py`
  - `uv run pytest -q tests/test_gui_filter_logic.py -k advanced_filters`
  - `uv run pytest -q tests/test_gui_filters_advanced_logic.py`
- External IA reports must be treated as hints only.
- Every claim from external IA must be re-validated with local file/line evidence before editing.

Details and highlight:
- _normalize_highlight_term, _get_current_search_terms, _collect_highlight_terms,
  _highlight_text, _format_details_html.
- update_details_from_selection, _get_series_from_row, _normalize_ssa_value,
  _normalize_ssa_series.
Dependencies: gui/helpers/formatting_helpers.highlight_text (potential reuse).

UI actions and IO:
- on_header_clicked, show_header_context_menu, show_context_menu.
- copy_cell_value, copy_row_data, _export_current_list_txt.
- remove_column_by_index, auto_fit_column.
- rescan_data, open_docs_folder, load_other_database, remove_persistent_filter.

## Mixins, workers, widgets, helpers: relationship and redundancy map
Mixins:
- FilterGUISSAMixin owns the main filter flow and uses FilterWorker and FilterCache.
- It expects SSAMainWindow attributes to exist: search_input, status_label, progress_bar,
  load_button, search_button, clear_filter_button, df_completo, _debounce_timer,
  _advanced_filters, _active_column_filters, _filter_request_seq, _active_filter_request_id.
- Refactor must preserve attribute names and contracts or provide thin wrappers.

Workers:
- DataLoaderWorker performs DB read and emits data_loaded/error.
- FilterWorker performs filter and uses FilterCache.
- RescanWorker performs rescan and emits output/progress.
- gui/gui_ssa.py still maintains retention lists for worker lifetime. Do not remove.

Widgets:
- ColumnSelector, ColumnManagerDialog, DataPaginator, FilterHelpDialog, RescanProgressDialog.
- SSAMainWindow owns their instances, binds signals, and controls layout.

Helpers:
- formatting_helpers has normalize_chunk_for_parse, format_search_display, highlight_text.
- theme_helpers has QSS builders.

Redundancy hotspots that must be preserved or carefully untangled:
- highlight_text exists in helpers, while gui/gui_ssa.py has _highlight_text and _normalize_highlight_term.
- normalize_chunk_for_parse and format_search_display are used in mixin and in gui/gui_ssa.py.
- Filter logic split between mixin and gui/gui_ssa.py advanced filters.
- Worker cleanup logic exists both in gui/gui_ssa.py and inside worker classes.
- Tab context and per-tab UI duplication is intentional for consistent UX.

## Tests that pin public API (non exhaustive)
1. tests/test_gui_filter_logic.py - heavy use of SSAMainWindow, globals, and mixin behavior.
2. tests/test_gui_preferences_atomic_write.py - expects GUI_MAIN_PREFERENCES and atomic_write_json_file integration.
3. tests/test_open_docs_folder_nonblocking.py - expects open_docs_folder behavior and QT_AVAILABLE.
4. tests/test_gui_stability.py and tests/smoke_test_gui.py - require SSAMainWindow import and basic behavior.

## Constraints
1. No GUI layout changes.
2. Keep SSAMainWindow public API stable.
3. Keep QT_AVAILABLE and headless stubs in gui/gui_ssa.py.
4. Do not remove known redundancy without explicit validation.
5. Redundancy control statement (keep visible in every slice):
   "Controle de redundancia
   Mantido conforme combinado. Nao removi nem alterei duplicacoes conhecidas.
   O foco foi apenas mover codigo. Vou seguir esse controle em todos os proximos slices."

## Extraction plan (approved, refined)
1. Create gui/ssa/ package and empty modules with header comments.
2. Move theme methods to gui/ssa/gui_theme.py and keep wrappers in SSAMainWindow.
3. Move worker retention and load_data flow to gui/ssa/gui_workers.py with wrappers.
4. Move advanced filters UI and logic to gui/ssa/gui_filters_advanced.py.
5. Move table width and pagination methods to gui/ssa/gui_table.py.
6. Move details/highlight methods to gui/ssa/gui_details.py.
7. Update imports in gui/gui_ssa.py to use new modules.
8. Validate with py_compile, ruff, focused pytest per slice.

## Open questions to resolve during refactor
1. Should highlight_text be unified to helper function or keep local variant for GUI details?
2. Should tab context management move to its own module or stay in gui/gui_ssa.py?
3. Are there any hidden coupling points in tests that rely on method location?

## Controle de redundancia
Mantido conforme combinado. Nao removi nem alterei duplicacoes conhecidas. O foco foi apenas mover codigo. Vou seguir esse controle em todos os proximos slices.

Notas do slice (filtros avancados):
- gui/ssa/gui_filters_advanced.py inclui _is_widget_valid local para evitar import circular com gui/gui_ssa.py.
- Constantes DIVISAO_SETORES, SECTOR_TO_DIV e MONO_FONT_FAMILY sao injetadas via configure_adv_filters_constants.

Notas do slice (tabela):
- gui/ssa/gui_table.py agora contem renderizacao da tabela, paginacao e calculo de larguras.
- gui/gui_ssa.py expone wrappers para display_current_page e helpers de largura.

## Analise adicional (gui_filters_advanced.py)

Contexto:
- Arquivo segue grande e mistura UI, menus, cache e logica de filtros.
- Estrutura adotada: gui/ssa/ com modulos por responsabilidade.

Proposta de refactor dentro da estrutura atual (sem mudar layout):
1. gui/ssa/gui_filters_advanced_ui.py
   - build_advanced_filters_ui
   - _build_responsavel_filters
   - _build_year_emissao_filter
   - _build_reprog_filter
   - _build_derivadas_filter
   - helpers de menu e wiring de signals

2. gui/ssa/gui_filters_advanced_logic.py
   - _apply_advanced_filters
   - helpers de filtros (ano_emissao, semanas, reprogramacoes, derivadas)
   - manter assinaturas e comportamento para evitar regressao

3. gui/ssa/gui_filters_advanced_state.py
   - cache e estado: _adv_values_cache, _adv_year_emissao_cache, _adv_norm_cache
   - flags: _adv_options_dirty, _adv_sector_syncing, _responsavel_*_prefixes
   - funcoes de reset/refresh de cache

4. gui/qt_stubs.py
   - mover stubs de PyQt6 para um unico local (rule_21)

5. gui/ssa/gui_filters_advanced.py
   - manter facade com wrappers e imports dos submodulos
   - manter nomes publicos para compatibilidade com SSAMainWindow

Itens do review antigo - status:
- rule_35 logger robusto: atendido (get_robust_logger)
- import parse_any_date no topo: atendido
- parsing de ano_emissao vetorizado com cache: atendido
- reprogramacoes com selecao multipla: atendido (intervalo min-max)
- normalizacao SSA repetida: mitigado com cache por DataFrame
- derivada_all_ste com origins vazio: ainda pendente (mask &= False)
- rule_21 stubs PyQt6: pendente (planejado para gui/qt_stubs.py)
- modulo grande: pendente (refactor acima)

Controle de redundancia:
- Mantido conforme combinado. Nao removi nem alterei duplicacoes conhecidas.
- Ex: highlight_text, normalize_chunk_for_parse, format_search_display.


## Slice atual (refactor avancados e stubs Qt)
- gui/qt_stubs.py criado para centralizar stubs de PyQt6.
- gui/ssa/gui_filters_advanced.py virou facade com UI/logica em submodulos.
- gui/ssa/gui_filters_advanced_ui.py contem somente UI e wiring.
- gui/ssa/gui_filters_advanced_logic.py contem _apply_advanced_filters.
- gui/ssa/gui_filters_advanced_state.py contem constantes e helper de cache.
- gui/ssa/gui_table.py agora importa stubs de gui/qt_stubs.py.
- gui/ssa/gui_details.py e gui/ssa/gui_table.py usam parametro window em funcoes de modulo.

## Sprint status update (PR #31)
- Aprovado e concluido:
  - A) lock global para listas/meta de workers em `gui/ssa/gui_workers.py`.
  - B) mascara de `db_path` em mensagens de erro de carregamento.
  - C) prune apos fluxo de erro/cleanup para evitar retencao indefinida.
- Decisoes de escopo mantidas:
  - D) nao alterar `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` para path relativo neste momento.
  - E) manter ignores de testes em `pyproject.toml` por ora e sugerir revisao no relatorio final.
