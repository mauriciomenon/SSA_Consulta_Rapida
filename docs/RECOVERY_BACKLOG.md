# Recovery Backlog

This file tracks post-merge hardening and cleanup for the recovery branch.
Scope is split by priority to keep delivery safe and incremental.

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
  - Keep E tracked: revisit `pyproject.toml` test ignores and repair affected tests in a dedicated slice.
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

## Execution model

- Use atomic commits per topic.
- Keep rollback easy by changing one concern at a time.
- Prefer low-risk defensive changes first, then structural cleanup.

## Review tracking (source PR 31)

Ordered list from PR review threads. Status uses pending/resolved.

1. [pending] armazenamento/database_optimized.py:349 :: **Potential Data Integrity Issues During Batch Update (Delete + Insert):** The batch update strategy deletes existing records before inserting updated ones. If the table has for...
2. [pending] armazenamento/database_optimized.py:346 :: **Error Handling During Rollback May Mask Critical Failures:** The rollback logic uses `with suppress(Exception):` when rolling back to the savepoint. This may hide errors durin...
3. [pending] core/app_logic.py:297 :: **Loss of Error Type Specificity in Exception Handling** In the `_import_single_file` function, the generic exception handler wraps all exceptions as `ExtractionError`: ```pytho...
4. [pending] core/config_manager.py:549 :: **Silent Failure on Default Settings Creation** If the creation of a default configuration file fails (e.g., due to permission issues or disk errors), the error is only logged a...
5. [pending] core/config_manager.py:44 :: **Suppressed Exceptions in Atomic File Operations** In the `_atomic_write_json_file` function, exceptions during file descriptor closing and temporary file removal are suppresse...
6. [pending] extracao/extractor.py:259 :: After detecting the header row and extracting data, the function does not validate that all required columns are present in the resulting DataFrame. This could lead to downstrea...
7. [pending] extracao/extractor.py:306 :: The code loads column mappings with `_load_column_mappings()` and applies them to the DataFrame. If the mapping is empty (e.g., due to a loading error), columns will not be rena...
8. [pending] gui/cache/filter_cache.py:50 :: **Potential Exception Risk:** The method `result.copy()` is called without verifying that `result` is a valid DataFrame. If the cached object is not a DataFrame or is `None`, th...
9. [pending] gui/cache/filter_cache.py:59 :: **Performance Concern:** The cache always stores a copy of the DataFrame (`result.copy()`) on every put. For large DataFrames, this can be expensive in both time and memory, esp...
10. [pending] gui/widgets/rescan_progress_dialog.py:143 :: The `reject` method allows the dialog to close immediately after a cancel request, even if the underlying rescan process has not yet stopped. This could lead to user confusion o...
11. [pending] gui/workers/rescan_worker.py:132 :: ### Potential Logger Handler Race Condition The logger handler is added and removed within the worker thread (lines 96, 130), but if multiple threads use the same logger ('ssa')...
12. [pending] gui/workers/rescan_worker.py:143 :: ### Cancellation Responsiveness Depends on `run_importer_logic` The cancellation logic relies on `run_importer_logic` invoking the `should_cancel` callback frequently (line 107)...
13. [pending] interface/cli_enhancement_manager.py:134 :: **Potential Data Race in _save_settings:** The `_save_settings` method uses best-effort file locking via `_lock_file_if_possible`, but this approach may not reliably prevent con...
14. [pending] interface/command_handlers.py:28 :: **Overly broad exception handling in `_save_settings_handler`:** Catching all exceptions and only printing the error message does not allow for proper error tracking or programm...
15. [pending] main.py:759 :: ### Critical Issue: Incomplete Failure Handling for Optimized and Legacy Import Modes If both the optimized import (`enable_optimized_import`) and the legacy import logic fail, ...
16. [pending] main.py:591 :: ### Performance Issue: Directory Listing in Debug Mode In the block that lists files in important directories (lines 569-605), if any of these directories contain a large number...
17. [pending] scripts/run_pytest_stream_and_log.py:119 :: The warning about dropped lines is only emitted when `dropped_lines % 200 == 1`, which may result in infrequent warnings during periods of high output loss. This could obscure t...
18. [pending] scripts/run_pytest_stream_and_log.py:84 :: The queue size for `line_queue` is hardcoded to 4096. This may not be optimal for all environments or workloads, potentially leading to unnecessary output loss or excessive memo...
19. [pending] scripts/run_pytest_stream_and_log_v2.py:140 :: **Potential Data Race on `dropped_lines`** The `dropped_lines` variable is incremented in both the main thread and the reader thread without synchronization. This can lead to a ...
20. [pending] scripts/run_pytest_stream_and_log_v2.py:163 :: **Busy-Wait Loop for Sentinel Delivery** The loop that ensures the sentinel (`None`) is delivered to the queue (`while True: ... time.sleep(0.005)`) can result in unnecessary CP...
21. [pending] tests/test_caching_atomic_save.py:30 :: **Missing test for concurrent writes:** The test `test_save_cache_is_atomic_and_does_not_corrupt_existing_file` only simulates a single failure mode (exception during write) and...
22. [pending] tests/test_database_optimized_alias_views.py:15 :: The test does not handle errors that may occur during database initialization (e.g., missing or invalid 'config/schema.sql'). This could result in unclear test failures. **Recom...
23. [pending] tests/test_database_optimized_alias_views.py:35 :: The test creates a database file but does not explicitly remove it after execution. This may leave residual files in the test environment, affecting test isolation and potential...
24. [pending] tests/test_filter_cache_locking.py:28 :: **Insufficient Verification of Lock Usage** The assertion `assert spy.enter_count >= 1` (line 28) only verifies that the lock was entered at least once, but does not ensure that...
25. [pending] tests/test_filter_error_skips_modal_in_pytest.py:30 :: The patch target `"gui.mixins.filter_gui_ssa_mixin.QMessageBox.critical"` is tightly coupled to the import path and structure of the module under test. If the import path or the...
26. [pending] interface/cli_enhancement_manager.py:24 :: **suggestion (bug_risk):** File locking is applied to the temp file, so it doesnt actually coordinate concurrent writers on the real settings file. In `_save_settings`, locking ...
27. [pending] tests/test_import_cancellation.py:65 :: **suggestion (testing):** Fortalea o teste verificando tambm o payload final de progresso "finish" Como `run_importer_logic` agora normaliza e protege `progress_callback`, captu...
28. [pending] tests/test_rescan_progress_dialog.py:28 :: **suggestion (testing):** Estenda as asseres para cobrir o estado da UI aps o cancelamento (texto de status e estados habilitado/desabilitado dos botes) Como `reject()` e `set_f...
29. [pending] tests/test_rescan_worker_cleanup.py:27 :: **suggestion (testing):** Considere exercitar tambm o caminho de sucesso para comprovar que os handlers so liberados no caso sem erro Para validar completamente o novo cleanup n...
30. [pending] interface/cli_enhancement_manager.py:100 :: O lock aplicado em _save_settings() est sendo feito no arquivo temporrio recm-criado. Isso no serializa gravaes concorrentes para o mesmo settings_file (cada processo trava seu ...
31. [pending] interface/cli_enhancement_manager.py:93 :: _lock_file_if_possible() usa flock LOCK_EX (bloqueante) em POSIX. Se outro processo ficar segurando o lock, essa chamada pode travar a CLI indefinidamente. Para manter 'best-eff...
32. [pending] armazenamento/database_optimized.py:237 :: existing_dict  montado a partir de chunk_df['numero_ssa'] sem normalizao de tipo, mas has_ssa['numero_ssa'] foi normalizado para str. Como SQLite pode conter valores antigos com...
33. [pending] extracao/extractor.py:214 :: A anotao de retorno ainda est como Optional[pd.DataFrame], mas a funo agora retorna DataFrame (incluindo vazio) e levanta ExtractionError nos erros (no retorna None). Ajuste a a...
34. [pending] extracao/extractor.py:223 :: A docstring ainda diz que retorna None em caso de erro, mas o fluxo agora levanta ExtractionError (e retorna DataFrame vazio quando h cabealho mas sem linhas). Atualize a seo Re...
35. [pending] extracao/extractor.py:236 :: pd.ExcelFile()  criado mas no  fechado explicitamente. Para evitar vazamento de handle/arquivo (especialmente em loops de muitos arquivos), use um context manager (with pd.Excel...
36. [pending] core/config_manager.py:443 :: load_display_mappings_integrity() passou a levantar RuntimeError se falhar ao restaurar o arquivo, alterando o comportamento anterior (que retornava DEFAULT_DISPLAY_MAPPINGS mes...
37. [pending] core/config_manager.py:474 :: load_column_mappings_integrity() agora levanta RuntimeError ao falhar em restaurar o arquivo, o que pode interromper a aplicao em ambientes sem permisso de escrita. Para preserv...
38. [pending] gui/workers/rescan_worker.py:125 :: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 1\. <b><i>rescanworker</i></b> exposes raw exception <code> R...
39. [pending] gui/gui_ssa.py:6674 :: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 2\. Rescan thread may outlive app <code> Bug</code> <code> Re...
40. [pending] core/config_manager.py:454 :: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 3\. Config restore can crash cli <code> Bug</code> <code> Rel...
41. [pending] interface/cli_enhancement_manager.py:88 :: ![medium](https://www.gstatic.com/codereviewagent/medium-priority.svg) The file lock is being applied to the temporary file created by `mkstemp`. Since each process creates a un...
42. [pending] core/app_logic.py:450 :: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes:\n\n1. `_import_single_file` now accepts `s...
43. [resolved] scripts/run_pytest_stream_and_log_v2.py:158 :: <!-- metadata:{"confidence":9,"steps":[{"text":"Looking at the changed code, I need to understand the new `_safe_queue_put` logic and verify potential issues.","toolCalls":[{"to...
44. [resolved] extracao/extractor.py:214 :: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully for issues:\n\n1. **Import changes**: Re...
45. [pending] gui/mixins/filter_gui_ssa_mixin.py:343 :: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"bash","input":{"command":"rg -n '^import os' gui/mixins/filter_gui_ssa_mixin.py; rg -n 'import os' gu...
46. [resolved] interface/cli_enhancement_manager.py:88 :: <!-- metadata:{"confidence":9,"steps":[{"text":"Looking at the diff, I need to analyze the new atomic write pattern with file locking in `_save_settings` and the `_lock_file_if_...
47. [resolved] utils/caching.py:153 :: <!-- metadata:{"confidence":7,"steps":[{"text":"Looking at the diff, I'll analyze the key changes: atomic write, safe file stat, updated cache format with metadata fast-path, an...
48. [pending] gui/gui_ssa.py:5094 :: <!-- metadata:{"confidence":7,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes in this PR:\n\n1. Import of `atomic_write_j...
49. [resolved] scripts/run_pytest_stream_and_log.py:136 :: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully.\n\nThe changes replace a blocking `_saf...
50. [resolved] core/config_manager.py:9 :: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully:\n\n1. New `_atomic_write_json_file` fun...
51. [pending] main.py:487 :: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully for issues:\n\n1. **Non-ASCII characters...
52. [pending] extracao/extractor.py:214 :: **P1** | Confidence: High The function signature now includes a `should_cancel` callback. The related context shows the primary caller, `run_importer_logic` in `core/app_logic.p...
53. [pending] armazenamento/database_optimized.py:167 :: **P1** | Confidence: High The addition of SQL identifier validation (`is_valid_identifier`) is a critical security improvement to prevent injection via the `table_name` paramete...
54. [pending] main.py:480 :: **P2** | Confidence: High Speculative: The validation logic for conflicting CLI flags `--skip-import` and `--force-rescan` is sound. However, the error message references `--res...
55. [pending] core/app_logic.py:330 :: **[Contextual Comment]** _This comment refers to code near real line 325. Anchored to nearest_changed(328) line 328._ --- **P1** | Confidence: High `run_importer_logic` now has ...
56. [pending] gui/gui_ssa.py:6434 :: _ Potential issue_ | _ Critical_ <details> <summary> Analysis chain</summary>  Script executed: ```shell #!/bin/bash # Get RescanWorker implementation to understand signal timin...
57. [pending] scripts/run_pytest_stream_and_log_v2.py:195 :: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 155-167, the warning is enqueued before the real output. When the queue is fu...
58. [pending] scripts/run_pytest_stream_and_log.py:153 :: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 116-128, the warning is enqueued before the real output. With a full queue, e...
59. [pending] utils/caching.py:154 :: _ Potential issue_ | _ Major_ **Don't silently skip files when `stat` fails.** If `_safe_file_stat` returns `None`, the file is ignored and may never be processed. Prefer re-que...
60. [pending] core/app_logic.py:184 :: _ Potential issue_ | _ Minor_ **Preserve the explicit `ExtractionError` message.** The `df is None` error gets swallowed by the generic handler, so the specific message is lost....
61. [pending] interface/command_handlers.py:26 :: _ Potential issue_ | _ Minor_ **Hardcoded path in success message may be inconsistent with actual save location.** The success message references `'config/settings.json'`, but `...
62. [pending] tests/test_open_docs_folder_nonblocking.py:32 :: _ Potential issue_ | _ Minor_ **Class attribute `called` may cause test isolation issues.** `DummyQDesktopServices.called` is a class-level list that persists across test runs i...
63. [resolved] interface/cli_enhancement_manager.py:73 :: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the code structure carefully.\n\nThe `_save_settings` metho...
64. [pending] core/app_logic.py:185 :: The check for `if df is None:` at line 181-184 is dead code. The extractor function `extract_data_from_excel` has been updated to never return None - it either returns a DataFra...
65. [pending] extracao/extractor.py:224 :: The return type annotation in the docstring (line 221-223) says `Optional[pd.DataFrame]` and mentions "ou None em caso de erro", but the function now never returns None - it eit...
66. [pending] core/app_logic.py:294 :: The ExtractionError exception is defined in both `extracao/extractor.py` and `core/app_logic.py`. In `_import_single_file`, when catching `extractor.ExtractionError` at line 290...
67. [pending] armazenamento/database_optimized.py:174 :: The `target_table` variable is validated using `is_valid_identifier()` at line 141-142, but then it's used in an f-string to construct SQL at line 147 without parameterization. ...
68. [pending] gui/widgets/rescan_progress_dialog.py:143 :: In `reject()`, the code emits `self.cancel_requested`, but the signal defined on the class is `cancel_requested`. This will raise `AttributeError` when cancelling (and will brea...
69. [resolved] gui/widgets/rescan_progress_dialog.py:147 :: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the changes carefully:\n\n1. Early-return guards in `append...
70. [resolved] tests/test_rescan_progress_dialog.py:31 :: <!-- metadata:{"confidence":10,"steps":[]} --> P2: Tautological assertion: `assert dlg.isVisible() in (True, False)` always passes since `isVisible()` returns a `bool`. This pro...
71. [pending] scripts/run_pytest_stream_and_log_v2.py:176 :: In scripts/run_pytest_stream_and_log_v2.py, _safe_queue_put mutates dropped_lines (e.g., `dropped_lines += 1`) but the nested function never declares `nonlocal dropped_lines` (u...
72. [pending] gui/widgets/rescan_progress_dialog.py:147 :: RescanProgressDialog.reject() currently emits cancel_requested but never calls super().reject()/close()/hide() in the non-finished case. When this dialog is shown with exec(), t...
73. [pending] gui/workers/rescan_worker.py:162 :: RescanWorker cleanup: the finally block wraps `_detach_logger()` in `suppress(Exception)`, but `_detach_logger()` performs multiple state updates (removeHandler, refcount decrem...
74. [resolved] scripts/run_pytest_stream_and_log_v2.py:138 :: <!-- metadata:{"confidence":10,"steps":[{"text":"","toolCalls":[{"toolName":"bash","input":{"command":"rg -n nonlocal scripts/run_pytest_stream_and_log_v2.py"}},{"toolName":"bas...
75. [pending] gui/widgets/rescan_progress_dialog.py:131 :: In `set_finished`, when the rescan fails (`success == False`) and the `message` argument is empty, the error display (`self.error_text`) is not updated with any indication of fa...
76. [pending] tests/test_rescan_progress_dialog.py:48 :: **Potential nondeterminism in event processing:** The tests rely on single calls to `QApplication.processEvents()` after dialog actions (e.g., `dlg.reject()`, `dlg.set_finished(...
77. [pending] scripts/run_pytest_stream_and_log.py:167 :: The `dropped_lines` variable is accessed without synchronization from multiple threads, creating a race condition. The reader thread (calling `_safe_queue_put`) and the main thr...
78. [pending] core/config_manager.py:453 :: After successfully writing the default mappings to the file, the function returns `DEFAULT_DISPLAY_MAPPINGS.copy()` instead of reading back the newly created file. This is incon...
79. [pending] core/config_manager.py:485 :: After successfully writing the default mappings to the file, the function returns `DEFAULT_COLUMN_MAPPINGS.copy()` instead of reading back the newly created file. This is incons...
80. [pending] gui/gui_ssa.py:4275 :: GLOBAL_RETIRED_DATA_LOADER_META[worker] is assigned twice consecutively. This looks like an accidental duplicate and makes it harder to reason about worker lifetime accounting; ...
81. [pending] gui/widgets/rescan_progress_dialog.py:143 :: The dialog's Cancel action (reject override) only emits cancel_requested and keeps the modal dialog open until the user tries to close it a second time. This differs from the PR...
82. [pending] scripts/run_pytest_stream_and_log_v2.py:158 :: In _safe_queue_put(None), the sentinel delivery path uses line_queue.put(..., timeout=0.2) and line_queue.get(..., timeout=0.2). This can still block the reader thread (even if ...
83. [pending] core/config_manager.py:86 :: **Potential File Descriptor Leak in `_atomic_copy_file`** If `os.close(fd)` fails inside the inner `try`/`except`, the file descriptor is never closed and will leak, as the `fin...
84. [pending] scripts/run_pytest_stream_and_log.py:167 :: Race condition: The `dropped_lines` variable is accessed without synchronization from the reader thread. Multiple concurrent accesses at lines 115, 132, 136-137, 145-147 create ...
85. [pending] armazenamento/database_optimized.py:75 :: SQL injection risk: The PRAGMA statement uses f-string formatting with the table name without validation. While `_has_referencing_foreign_keys` is an internal function, the `tab...
86. [pending] gui/gui_ssa.py:4386 :: Race condition on global worker retention lists: `GLOBAL_RETIRED_DATA_LOADER_WORKERS` and `GLOBAL_RETIRED_DATA_LOADER_META` are accessed from multiple SSAMainWindow instances wi...
87. [pending] scripts/run_pytest_stream_and_log.py:167 :: The warn_count modulo check at line 142 and 154 can fire on the same count (when warn_count % 200 == 1). At line 138-148, if the second put_nowait succeeds after eviction, it em...
88. [pending] scripts/run_pytest_stream_and_log_v2.py:209 :: The same duplicate warning issue exists here as in run_pytest_stream_and_log.py. The warn_count modulo check at line 184 and 196 can both trigger on the same count value, potent...
89. [pending] gui/workers/rescan_worker.py:81 :: The _attach_logger and _detach_logger methods modify global state (_LOGGER_REFCOUNT, _LOGGER_PREV_LEVEL) but there's a risk if _attach_logger succeeds and then _detach_logger is...
90. [pending] interface/cli_enhancement_manager.py:118 :: The msvcrt.locking call at line 118 locks 4096 bytes, but the actual file size may be smaller or larger than 4096 bytes. The msvcrt.locking function locks a specific number of b...
91. [pending] armazenamento/database_optimized.py:79 :: The _has_referencing_foreign_keys function uses dynamic SQL with f-string at line 77: f"PRAGMA foreign_key_list({table})". The table name comes from sqlite_master, which should ...

## Updates 2026-02-17 (slice: advanced filters responsavel_emissor)

- [resolved] UI/logic flow `responsavel_emissor` removed from advanced filters panel assembly.
- [resolved] Regression test added to lock behavior: `tests/test_gui_filter_logic.py::test_responsavel_emissor_controls_are_not_present_in_advanced_panel`.
- [note] Scope decision B confirmed by user: do not add DB column `responsavel_emissor`; keep `solicitante` as supported field.

## Updates 2026-02-17 (slice: derivadas button util)

- [resolved] `Especificas...` popup now includes DB materialized derivadas summary for visible SSAs (`ssa_derivada_summary`).

## Updates 2026-02-18 (user TODO queue)

- [pending] Melhorar GUI na aba filtros, mantendo layout base sem regressao visual.
- [pending] Implementar filtro/capacidade de `divisao` com cobertura de teste focada.
- [resolved] `Especificas...` enable state now also checks DB relations, not only dataframe `derivada_de` values.
- [resolved] Fixed responsive grid crash risk after removal of `responsavel_emissor` controls (`_reorganize_advanced_filters_grid` no longer references `emis_resp_box`).

## Updates 2026-02-18 (details dialog split reliability)

- [resolved] Derivadas/details split in double-click dialog is now real 20/80, not only nominal ratio:
  - moved from `QHBoxLayout` ratio-only approach to `QSplitter` with explicit sizes/stretches.
  - reduced left pane minimum width to allow shrink behavior.
  - enforced initial 20/80 using dialog minimum width.
- [resolved] Dialog visual baseline now fixed:
  - min size `700x650`;
  - left panel font `12`;
  - right details font `12`;
  - field-label font `11`.

## Updates 2026-02-19 (filters-tab overlap safety)

- [resolved] Critical visual overlap in `Filtros` tab:
  - bottom region no longer invades SSA list area when result set is small.
  - fix shipped in `d3d9410f` with minimal geometry constraints (`table min height 220`, vertical stretch `6/4`).
  - regression test added for geometry guard in `tests/test_gui_filter_logic.py`.
- [pending, non-blocking] PR checks monitoring:
  - keep treating `code/snyk` and `security/snyk` as external plan-limit noise unless provider status changes;
  - re-check remaining queued checks after pipeline settles, and act only on real code blockers.

## Updates 2026-02-19 (slice: tab context mixin hardening)

- [resolved] Removed fixed `TAB_CONTEXT_WIDGET_ATTRS` list in tab context mixin; bind now uses runtime context keys while skipping tab metadata.
- [resolved] `_sync_bind_theme_and_render` now persists `_last_render_key` only after `display_current_page` succeeds.
- [pending] `SSAMainWindow` class size/coupling remains structural backlog for dedicated sprint; no broad refactor in this stabilization slice.
- [rule] Any future UI ratio change must include constraint validation (`minimumWidth` + layout manager behavior), not ratio constants only.

## Updates 2026-02-17 (slice: dead code ano_execucao)

- [resolved] Removed unreachable `data_execucao` branch from advanced year execution filter.
- [resolved] Added regression test for `ano_execucao_values` using `semana_executada`.
- [resolved] Fixed legacy key precedence for `ano_execucao` with exclude flag (`ano_execucao_exclude=True`) and added migration coverage tests.

## Updates 2026-02-17 (slice: derivadas special multi-sheet)

- [resolved] Importer derivadas special flow now processes all detected special sheets in a single sync call.
- [resolved] `sync_derivadas` now supports `sheet_files` list and aggregates sheet stats.
- [resolved] Added coverage for multi-sheet merge behavior in `tests/test_derivadas_sync.py`.

## Updates 2026-02-18 (mega sprint reliability)

- [resolved] Import now blocks success when derivadas sync evidence is invalid or consistency scan is not clean.
  - commit: `f9e69d86`
  - files: `core/app_logic.py`, `tests/test_import_derivadas_trigger.py`
- [resolved] Derivadas sync now enforces post-materialization integrity gate inside transaction.
  - commit: `474e980a`
  - files: `armazenamento/derivadas_sync.py`, `tests/test_derivadas_sync.py`
- [resolved] GUI manual "Atualizar Derivadas" now requires consistency scan clean state after sync.
  - commit: `5a50ea17`
  - files: `gui/gui_ssa.py`, `tests/test_gui_filter_logic.py`
- [resolved] Special visual derivadas parser now treats root-only rows as informational, reducing invalid_parent noise.
  - commit: `6f4fcc7a`
  - files: `armazenamento/derivadas_sync.py`, `tests/test_derivadas_sync.py`
- [resolved] Filter cache key now supports advanced filter context token to avoid stale reuse across state changes.
  - commit: `ff266350`
  - files: `gui/cache/filter_cache.py`, `gui/workers/filter_worker.py`, `gui/mixins/filter_gui_ssa_mixin.py`, `tests/test_filter_worker.py`

## Updates 2026-02-18 (mega sprint block 6)

- [resolved] Per-file derivadas parse evidence report added in sync output (`sheet_file_reports`) with path dedupe.
  - commit: `1f213578`
  - files: `armazenamento/derivadas_sync.py`, `tests/test_derivadas_sync.py`
- [resolved] Importer derivadas phase now rejects special-sheet runs without individual evidence.
  - commit: `ffd5d8ef`
  - files: `core/app_logic.py`, `tests/test_import_derivadas_trigger.py`
- [resolved] GUI manual derivadas update now rejects special-sheet runs without individual evidence.
  - commit: `3daddd9f`
  - files: `gui/gui_ssa.py`, `tests/test_gui_filter_logic.py`
- [resolved] CLI sync now supports `--special-docs-dir` for full special-sheet ingest in one command.
  - commit: `f7f7ead7`
  - files: `scripts/derivadas_cli.py`, `tests/test_derivadas_cli.py`
- [resolved] Full sync run persisted in tracked DB snapshot.
  - commit: `60adbd5a`
  - file: `data/ssas.db`
  - runtime evidence: `sync_run_id=4`, `sheet_files_count=11`, `db_edges=3216`, `sheet_edges=1497`, `merged_edges=3547`, consistency clean.

- [note] `uv run ty check gui/gui_ssa.py tests/test_gui_filter_logic.py` still reports a large pre-existing GUI typing baseline (301 diagnostics); this slice did not expand scope to full GUI typing cleanup.

## Delegacao simples para outra IA (audit-safe)

Objetivo:
- Escoar backlog de baixo risco sem quebrar fluxo estavel.

Lotes simples (permitidos):
1. [pending] limpeza ruff de baixo risco em `scripts/*` e `launchers/*`:
   - F401, F841, F541, E401/E402 em arquivos de ferramenta.
2. [pending] limpeza ruff de baixo risco em testes utilitarios:
   - `tests/verify_*`, `tests/test_verification_manual.py`, `tests/test_search_v_character.py`.
3. [pending] reforco de testes:
   - `tests/test_import_cancellation.py` evento `finish`.
   - `tests/test_rescan_progress_dialog.py` asserts de estado.
   - `tests/test_filter_cache_locking.py` assert semantico de lock.

Nao delegar:
1. Mudancas estruturais em `gui/gui_ssa.py`.
2. Mudancas de schema.
3. Mudancas em import principal sem suite focada completa.

Criterio de aceite da delegacao:
1. Commits atomicos por lote.
2. Gate por lote verde (`py_compile`, `ruff`, `ty`, `pytest` focado).
3. Sem alteracao de layout GUI.

### Pendencias reais restantes (objetivas)

1. [pending-blocked] Snyk code/security em PR:
   - bloqueio externo por limite de plano, nao regressao de codigo.
2. [pending] Baseline alto de ty em GUI core:
   - foco futuro em `gui/gui_ssa.py` com slice dedicado.
3. [pending] melhorias de concorrencia em wrappers de teste:
   - `scripts/run_pytest_stream_and_log*.py`.
4. [pending] melhorias de cancel/progresso:
   - `gui/widgets/rescan_progress_dialog.py`, `gui/workers/rescan_worker.py`.
5. [pending] melhoria UX filtros:
   - item `divisao` e refinamento da aba de filtros (sem quebrar layout).
6. [pending] arquitetura de cache:
   - revisar possivel decomposicao de `core/cache_manager.py` (P4 kluster "god class"), mantendo interface unificada e sem regressao.

### Nao regredir (guardrails)

1. Dialogo de detalhes derivadas deve ficar em 20/80 real.
2. Nao remover validacoes fail-closed de sync de derivadas.
3. Nao reintroduzir `responsavel_emissor` em advanced filters.

### Estado de migracao pronto

1. [resolved] Prompt curto e prompt completo para nova conversa adicionados em:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
2. [resolved] Baseline de UI sensivel documentada com valores numericos:
   - split `20/80`, min `700x650`, fonts `12/12/11`.

## Decisao de triagem (2026-02-18, lock de escopo)

Itens marcados como falso positivo neste ciclo (nao fazer):
1. nao remover `if df is None` em `core/app_logic.py` (manter defesa explicita).
2. nao adicionar novos locks em scripts de stream neste ciclo.
3. nao abrir refactor de race em `gui/workers/*` neste ciclo.

Regra de lint para este ciclo:
1. ignorar `E501` (linhas longas) nas triagens e lotes simples.
2. priorizar apenas erros com impacto funcional ou seguranca real.

## Update 2026-02-18 (codex/import-review)

1. [resolved] Ty baseline caiu com slices de baixo risco:
   - `457 -> 300 diagnostics` no gate global.
   - commits: `977f0dda`, `8c8aa860`.
2. [resolved] Ajuste pontual de parent Qt em dialogo de ajuda de filtros:
   - commit: `5b09c7c0`.
3. [pending] Baseline restante de ty concentrada em:
   - `gui/gui_ssa.py` (fallback headless ainda gera ruido estatico).
   - arquivos de teste/dev (`tests/*`, `dev_env/streamlit_app.py`).
4. [pending-nonblocking] Refactor estrutural adiado em teste legacy:
   - `tests/automated_system_tests.py` com classe ampla (`AutomatedSystemTester`).
   - manter patch minimo neste sprint e quebrar responsabilidades em ciclo dedicado.
5. [pending-blocked] checks externos:
   - `code/snyk` e `security/snyk` continuam limitados por plano.

## Update 2026-02-19 (codex/import-review)

1. [resolved] Ty baseline reduziu com slices focados em testes utilitarios:
   - `204 -> 177 diagnostics` no gate global `uv run ty check .`.
   - commits: `7cea46ac`, `b3b75fd9`, `45cc0f79`.
2. [resolved] Gate estatico em arquivos criticos segue verde:
   - `uv run ruff check armazenamento/database.py gui/ssa/gui_filters_advanced_ui.py`.
   - `uv run ty check armazenamento/database.py gui/ssa/gui_filters_advanced_ui.py`.
3. [pending] Maior bloco restante de ty e ruido de tipagem:
   - `gui/gui_ssa.py` (tipagem PyQt dinamica e fallbacks de runtime).
   - `gui/gui_ssa_dev.py`, `gui/ssa/gui_theme.py`.
4. [pending] Pendencias menores fora de fluxo principal:
   - `launchers/convert_icon.py` (deps opcionais `PIL` e `cairosvg`).
   - `scripts/run_all_tests.py` e wrappers `run_pytest_*`.
5. [pending-blocked] checks externos continuam sem acao local:
   - `code/snyk` por limite de plano.

## Update 2026-02-19 (codex/import-review - ty slices extra)

1. [resolved] Ty baseline continuou caindo em slices pequenos:
   - `177 -> 155 diagnostics` no gate global `uv run ty check .`.
   - commits: `1af18fd2`, `37d02707`, `5e66e2fb`, `2f49ec5f`, `46c1f2a6`.
2. [resolved] Ajustes de risco baixo aplicados:
   - launcher CLI usando entrypoint correto (`start_cli_loop`).
   - narrowing do patch de import PyOxidizer para escopo `pandas`.
   - tipagem defensiva em `gui/gui_ssa_dev.py`.
   - imports opcionais tipados em `launchers/convert_icon.py`.
   - narrowing de `QApplication.instance()` em `gui/ssa/gui_theme.py`.
3. [pending] Bloco principal restante de ty:
   - `gui/gui_ssa.py` (`128 diagnostics` no arquivo; tipagem PyQt + fallback headless).
4. [pending-blocked] checks externos sem acao local:
   - `code/snyk` fail por limite de plano.
   - `security/snyk` fail por limite de plano.

## Update 2026-02-19 (codex/import-review - gui typing hardening)

1. [resolved] Ty baseline reduziu novamente com slices em launcher/main/gui:
   - `155 -> 113 diagnostics` no gate global `uv run ty check .`.
   - commits: `5e66e2fb`, `2f49ec5f`, `46c1f2a6`, `8948c85d`, `b23d97ec`, `8fe3ed2c`.
2. [resolved] Correcoes de risco real e estabilidade:
   - guarda de `clipboard` e `QInputDialog` em `gui/gui_ssa.py`.
   - stubs headless Qt mais consistentes para execucao sem PyQt6.
   - import patch de PyOxidizer limitado a `pandas`.
3. [pending] Bloco restante de tipagem ainda concentrado:
   - `gui/gui_ssa.py` (`86 diagnostics` no arquivo).
   - alvo futuro: reduzir sem refactor amplo de layout/arquitetura.
4. [pending-blocked] checks externos:
   - `code/snyk` e `security/snyk` continuam bloqueados por limite de plano.

## Update 2026-02-19 (codex/import-review - ty errors zerados)

1. [resolved] Ty global sem erros:
   - `113 -> 28 diagnostics` no gate global.
   - `uv run ty check . --output-format concise` nao retorna mais `error[...]`.
2. [resolved] Tipagem de `gui/gui_ssa.py` estabilizada sem alterar layout:
   - `86 -> 1 diagnostic` (restou somente warning `unsupported-base`).
   - commits principais: `50031a1e`, `7cab4edb`, `1ba5b0d7`.
3. [pending-nonblocking] warning residual:
   - `gui/gui_ssa.py`: `unsupported-base` no mixin em ambiente headless/stub.
4. [pending-blocked] checks externos:
   - `code/snyk` limite de plano.
   - `security/snyk` limite de plano.

## Update 2026-02-19 (codex/import-review - ty warnings zerados)

1. [resolved] Gate estatico local zerado para tipagem:
   - `uv run ty check . --output-format concise` -> `All checks passed`.
   - warnings removidos com patch minimo (unused type ignore + `utcnow` deprecated).
2. [resolved] Gates tecnicos dos arquivos tocados estao verdes:
   - `uv run python -m py_compile ...`
   - `uv run ruff check ...`
   - `uv run ty check . --output-format concise`
   - `uv run pytest -q tests/test_main_skip_import.py tests/test_normalization_rules.py tests/test_numero_ssa_hyphen_repetition.py tests/test_numero_ssa_normalization_cross.py tests/test_robust_importer.py`
3. [pending-nonblocking] melhoria estrutural adiada (fora de escopo do patch minimo):
   - `armazenamento/database_validation.py`: funcao `validate_dataframe_before_insert` segue com alta complexidade ciclom.
   - tratar em sprint dedicado com refactor controlado e cobertura de regressao.
4. [pending-blocked] checks externos sem acao local:
   - `code/snyk` limite de plano.
   - `security/snyk` limite de plano.

## Update 2026-02-19 (codex/import-review - risk patch runtime)

1. [resolved] Correcao de risco em validacao de caminho:
   - `utils/path_safety.py`: `ensure_path_is_allowed('')` agora falha com `PathSafetyError`.
   - repro anterior retornava cwd; comportamento inseguro removido.
2. [resolved] Correcao de mascaramento de erro real no backfill:
   - `main.py`: retry de import para backfill agora so ocorre quando `ModuleNotFoundError` e do proprio modulo alvo.
   - erro interno de dependencia volta a propagar corretamente.
3. [resolved] Diagnostico operacional melhor no bootstrap CLI:
   - `launchers/cli_entry.py`: adicionada saida explicita para excecao inesperada no startup.
4. [resolved] Regressao coberta:
   - novo teste `tests/test_path_safety.py` validando rejeicao de string vazia e espacos.
5. [pending-blocked] checks externos sem acao local:
   - `code/snyk` limite de plano.
   - `security/snyk` limite de plano.

## Update 2026-02-19 (codex/import-review - legacy setup module hardening)

1. [resolved] Mitigacao de execucao de modulo externo via env:
   - `utils/setup_project_structure.py` bloqueia `SSA_LEGACY_SETUP_MODULE` fora da raiz do projeto por padrao.
   - opt-in explicito disponivel via `SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE=1`.
2. [resolved] Cobertura de regressao adicionada:
   - `tests/test_setup_project_structure.py` valida bloqueio padrao e fluxo opt-in.
3. [resolved] Repro de seguranca validado localmente:
   - modulo temporario externo nao e executado sem opt-in (side effect bloqueado).
4. [pending-blocked] checks externos sem acao local:
   - `code/snyk` limite de plano.
   - `security/snyk` limite de plano.

## Update 2026-02-19 (codex/import-review - distribution packaging guard)

1. [resolved] Protecao no empacotamento ZIP:
   - `scripts/create_distribution.py` agora valida existencia do executavel antes de `copy2`.
   - erro fica explicito e evita stacktrace generico de arquivo ausente.
2. [resolved] Relatorio final de empacotamento mais claro:
   - quando ZIP nao e criado, log explicita `ZIP: Nao criado`.
3. [resolved] Cobertura de regressao adicionada:
   - `tests/test_create_distribution.py` valida retorno `None` + log esperado quando `exe` ausente.
4. [pending-blocked] checks externos sem acao local:
   - `code/snyk` limite de plano.
   - `security/snyk` limite de plano.

## Update 2026-02-19 (codex/import-review - gui workers structural follow-up)

1. [pending-nonblocking] item estrutural identificado por revisao automatica:
   - `gui/ssa/gui_workers.py`: funcao `on_data_loaded` concentra responsabilidades de sanitizacao, estado e atualizacao de UI.
   - impacto atual: nao bloqueia funcionamento, mas aumenta custo de manutencao e teste.
2. [next-sprint] tratar em sprint dedicado, sem mexer em layout:
   - extrair bloco de processamento de dataframe para helper puro.
   - manter `on_data_loaded` como coordenador de fluxo/UI.
3. [scope-note] fora do patch minimo desta rodada:
   - nenhuma refatoracao ampla aplicada agora para evitar risco de regressao.

## Update 2026-02-24 (kluster triage after filtros stability slice)

1. [resolved] CLI config command bug fixed with low-risk patch:
   - `interface/cli.py`: removed `display_map = handle_config_command()` in single-char command flow.
   - behavior now matches full command flow (`c` and `config` do the same refresh/reset path).
2. [resolved] dynamic schema DDL hardening:
   - `armazenamento/schema_manager.py`: table lookup switched to parameterized query.
   - added strict identifier validation for dynamic columns before `ALTER TABLE`.
   - table/column identifiers now quoted through helper in DDL/PRAGMA paths.
3. [resolved] maintenance scripts aligned with canonical table and schema fields:
   - `scripts_manutencao/analyze_db_integrity.py`: switched to `ssa_table` and current field names.
   - `scripts_manutencao/verificar_integridade.py`: switched to `ssa_table`.
   - `scripts_manutencao/limpar_banco.py`: switched to `ssa_table`.
4. [pending-nonblocking] defer to next sprint (requires design/spec confirmation):
   - `extracao/extractor.py`: ambiguity of `m` in `_normalize_tempo_excedido_value` (`minutes` vs `months`).
   - action: decide canonical token set (`m` vs `mi` vs `mo`) before changing parser behavior.
5. [pending-nonblocking] defer to dedicated refactor sprint (outside minimal-risk scope):
   - God class split in `gui/gui_ssa.py` + `gui/mixins/filter_gui_ssa_mixin.py`.
   - config path/source unification between `core/config_manager.py` and `gui/gui_config.py`.
6. [pending-blocked] external check noise and plan limits:
   - keep Snyk plan-limit failures as external blocker with no local code fix.

## Update 2026-02-24 (control docs sync)

1. [resolved] diario de ciclo sincronizado para continuidade segura:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` atualizado com status do override 2026-02-24.
   - `docs/NEXT_CHAT_MIGRATION.md` atualizado com contexto ativo em `codex/dev-filtros-stability`.
2. [resolved] risco de migracao com contexto antigo reduzido:
   - contexto de `codex/import-review` e PR `#31` mantido apenas como historico.
3. [pending-nonblocking] manter disciplina de update ao fechar cada slice:
   - registrar sempre em `AGENTS_HANDOFF_NEXT_CYCLE.md`, `RECOVERY_BACKLOG.md` e `NEXT_CHAT_MIGRATION.md`.

## Update 2026-02-24 (tempo_excedido parser ambiguity fix)

1. [resolved] semantic fix with minimal risk in parser:
   - `extracao/extractor.py`: `_normalize_tempo_excedido_value` now maps `m` to minutes and keeps months as explicit `mo`.
   - reason: avoids contradictory interpretation in common duration inputs (example `1h 30m`).
2. [resolved] regression coverage added:
   - `tests/test_extracao.py`: added focused checks for `1h 30m`, `15mi`, and `2mo 5d`.
3. [scope-note] no broad refactor applied:
   - only parser token mapping and targeted tests changed.

## Update 2026-02-24 (maintenance scripts runtime stability)

1. [resolved] runtime failure fixed in maintenance cleanup:
   - `scripts_manutencao/limpar_banco.py`: `VACUUM` now runs after `commit` to avoid transaction error.
2. [resolved] logging rule aligned with minimal change:
   - `scripts_manutencao/limpar_banco.py`: replaced `print()` usage with robust logger calls.
3. [resolved] regression tests added for script targets and execution:
   - `tests/test_scripts_manutencao_schema_targets.py` validates:
     - `analyze_db_integrity.py` uses `ssa_table` and runs on canonical schema.

## Update 2026-02-24 (schema_manager identifier guard regression lock)

1. [resolved] added focused tests for SQL identifier hardening:
   - `tests/test_schema_manager_identifier_guards.py`
2. [resolved] verified expected behavior:
   - invalid dynamic column name raises `ValueError`;
   - valid missing column is added successfully.

## Update 2026-02-24 (analyze_db_integrity hardening)

1. [resolved] fixed semantic/report consistency in integrity analyzer:
   - `scripts_manutencao/analyze_db_integrity.py` now aggregates `empty_fields` with complete-empty-record checks.
2. [resolved] fixed empty-table safety:
   - no division-by-zero during percentage calc;
   - `SUM(...)` null results now normalized to zero.
3. [resolved] logging and maintenance contract alignment:
   - migrated script output to robust logger;
   - exposed `verify_database_integrity` + compatibility alias `analyze_database_integrity`;
   - integrated `repair_database_if_needed` wrapper to call core repair flow only when needed.
4. [resolved] focused regression tests for this script:
   - `tests/test_scripts_manutencao_schema_targets.py` now locks:
     - aggregate empty-fields flag behavior;
     - empty-table no-crash behavior.

## Update 2026-02-24 (verify_database_integrity performance refactor)

1. [resolved] reduced query round-trips in integrity analyzer:
   - merged core metrics into one query (`total_records`, critical empty counts, complete-empty records).
2. [resolved] duplicate aggregation fixed and optimized:
   - top-10 listing preserved while `duplicate_count` now reflects total duplicates across all groups.
3. [resolved] import-date check avoids exception path when column is absent:
   - `PRAGMA table_info` check before date query.
4. [resolved] regression lock expanded:
   - `tests/test_scripts_manutencao_schema_targets.py` validates duplicate-count correctness beyond top-10 sample.

## Pendencias longas (triagem kluster consolidada 2026-02-24)

1. [pending-long] `armazenamento/database_upsert_logic.py`:
   - row-by-row upsert (`iterrows`) e merge por linha; custo alto em lotes grandes.
2. [pending-long] `interface/cli.py`:
   - estado de paginacao baseado em `id(df)`;
   - risco de perda de estado em copias e crescimento do tracker.
3. [pending-long] `interface/cli.py`:
   - fluxo `-x` (remove termo) com comportamento inconsistente em ordem nao-recente.
4. [pending-long] `interface/cli.py`:
   - busca por SSA apos falha de carga pode cair em `KeyError` sem guarda dedicada.
5. [pending-long] `core/app_logic.py` + filtros:
   - semantica de delimitador por virgula diverge entre busca geral e filtros por coluna.
6. [pending-long] regex/filtros:
   - falta de salvaguarda para regex de usuario com custo alto (ReDoS/latencia).
7. [pending-long] `interface/table_printer.py`:
   - formatacao/sanitizacao eager no dataframe inteiro antes de paginacao.
8. [pending-long] `utils/robust_importer.py`:
   - funcao monolitica com IO + heuristica + relatorio acoplados.
9. [pending-long] `main.py`:
   - funcao `main` extensa com multiplas responsabilidades.
10. [pending-long] `core/config_manager.py` / `gui/gui_config.py`:
    - duplicacao de mapeamentos e possivel divergencia de path/config.

## Pendencias para sprint exclusivo (fora de patch minimo)

1. [next-sprint-exclusive] God Class GUI:
   - `gui/gui_ssa.py` + `gui/mixins/filter_gui_ssa_mixin.py`.
   - objetivo: split por responsabilidades sem alterar layout.
2. [next-sprint-exclusive] Circular deps em `armazenamento`:
   - mapear grafo de imports e reduzir acoplamento sem quebrar startup.
3. [next-sprint-exclusive] Arquitetura CLI:
   - separar loop principal, parser, estado e dispatch (`start_cli_loop`).
4. [next-sprint-exclusive] Threading/performance GUI filtros:
   - geracao de opcoes e aplicacao de filtros com pontos sincronos na UI thread.
5. [next-sprint-exclusive] Unificacao de config path/source:
   - consolidar caminho canonico e remover duplicacao core/gui.
6. [next-sprint-exclusive] Refactor de manutencao/migracao:
   - parser de schema em scripts de migracao com estrategia robusta e testavel.

## Update 2026-02-24 (cli keyerror guard after load failure)

1. [resolved] fixed crash risk in direct SSA search path:
   - `interface/cli.py`: guard added for missing `numero_ssa` column before direct SSA lookup.
2. [resolved] security/performance hardening in same path:
   - direct contains now uses `regex=False` when fallback search is needed;
   - exact match is used when strict normalized SSA is available.
3. [resolved] regression lock:
   - `tests/test_cli_loop_missing_numero_ssa_guard.py` validates no crash when dataframe lacks `numero_ssa`.

## Update 2026-02-24 (invalid regex fallback hardening in GUI column filter)

1. [resolved] fixed unsafe fallback for invalid regex token in GUI column filter:
   - `gui/mixins/filter_gui_ssa_mixin.py` now uses literal fallback with `regex=False`
     in both explicit `~regex` and default `regex` mode when pattern compilation fails.
2. [resolved] avoided crash/unsafe path on malformed user regex:
   - invalid patterns no longer re-enter regex evaluation in fallback path.
3. [resolved] regression lock:
   - `tests/test_filter_regex_invalid_fallback.py` validates fallback behavior in both modes.

## Update 2026-02-24 (cli remove-filter non-lifo consistency)

1. [resolved] fixed semantic inconsistency in `-x <termo>`:
   - `interface/cli.py` now reapplies from base state when removing non-last term.
2. [resolved] preserved performance for common LIFO removal:
   - when removed term is only the trailing term, reapply uses previous stack state.
3. [resolved] regression lock:
   - `tests/test_cli_remove_filter_non_lifo.py` covers non-lifo and lifo branches.

## Update 2026-02-24 (governanca ativa para sprint de qualidade)

1. [active-rule] equilibrio entre error-handling e performance:
   - manter tratamento de erro por bloco funcional relevante, sem excesso de `if/try` fragmentado;
   - exigir saida objetiva e tratamento coerente para cada erro capturado;
   - evitar fallback caro e reprocessamento amplo como efeito colateral de hardening.

## Update 2026-02-24 (cli config refresh com custo controlado)

1. [resolved] config refresh sem reset cego de sessao:
   - `interface/cli.py` centraliza refresh pos-config em helper local e remove duplicacao de blocos.
2. [resolved] custo controlado no refresh:
   - recarrega estado inicial apenas quando `default_filters` mudou;
   - quando nao mudou, reaproveita dataframe atual e apenas re-renderiza.
3. [resolved] seguranca na query estrutural:
   - `get_ssa_query` agora aceita apenas `ssa_table` e aliases legados (`ssas`, `ssa_chamados`).
4. [resolved] regression lock:
   - `tests/test_cli_config_preserve_session.py` cobre reload condicional por mudanca de `default_filters`;
   - `tests/test_cli_get_ssa_query_identifier_guard.py` cobre bloqueio de tabela fora da allowlist.

## Update 2026-02-24 (cli clearall table consistency)

1. [resolved] fixed table consistency in clearall flow:
   - `_handle_clear_all_filters` now calls `get_ssa_query(table_name)`.
2. [resolved] regression lock:
   - `tests/test_cli_clearall_uses_table_name.py` validates `clearall` uses provided table and alias mapping.

## Update 2026-02-24 (cli pagination tracker prune)

1. [resolved] reduced stale pagination state risk:
   - added prune of orphan entries when `results_stack` changes.
2. [resolved] manager encapsulation without broad refactor:
   - pagination tracker operations moved to a dedicated local manager class in CLI module.
3. [resolved] reduced state loss on dataframe copies:
   - tracker key now persists in `df.attrs`, avoiding strict dependence on `id(df)`.
4. [resolved] regression lock:
   - `tests/test_cli_pagination_tracker_prune.py` (including copy-preservation scenario).

## Update 2026-02-24 (cli enhancement settings lock and root rule)

1. [resolved] lock behavior clarified in settings save:
   - lock is applied on lockfile; temp-file lock was removed to avoid redundant lock path.
   - when lock acquisition fails, save is aborted (no unlocked write path).
2. [resolved] project-root rule alignment:
   - `interface/cli_enhancement_manager.py` now uses `_get_project_root()`.
3. [resolved] robust logging alignment:
   - module logger switched to `get_robust_logger().get_logger(__name__, "cli")`.
4. [resolved] regression lock:
   - `tests/test_cli_enhancement_manager_lock_usage.py`.

## Update 2026-02-24 (command handlers root-safe mappings cache)

1. [resolved] cwd-independent mapping path:
   - `interface/command_handlers.py` now resolves config path from project root helper.
2. [resolved] robust logger alignment:
   - module logger now uses `get_robust_logger().get_logger(__name__, "cli")`.
3. [resolved] mapping cache manager:
   - added lightweight manager to avoid repeated mapping loads in config menus.
4. [resolved] regression lock:
   - `tests/test_command_handlers_project_root_mapping.py`.

## Update 2026-02-24 (command handlers save flow cleanup)

1. [resolved] reduced repeated error branches in config menu handlers:
   - repeated `try/except ... pass` blocks replaced by `_try_save_settings(...)`.
2. [resolved] behavior preserved:
   - menu keeps running on save failure, while user feedback/log remains centralized in `_save_settings_handler`.
3. [resolved] helper semantics clarified:
   - helper renamed to `_attempt_save_settings` and now returns explicit boolean success/failure.
4. [resolved] save-failure rollback in menu actions:
   - when persistence fails, local menu mutations are reverted to avoid misleading transient state.

## Update 2026-02-24 (optimized upsert legacy decimal key normalization)

1. [resolved] fixed legacy key match in optimized lookup path:
   - `armazenamento/database_optimized.py` now queries both canonical `numero_ssa` and legacy `numero_ssa + ".0"` variants during chunked lookup.
2. [resolved] fixed duplicate risk on legacy decimal keys during update path:
   - delete set now includes both canonical and matched legacy storage keys before reinserting normalized rows.
3. [resolved] fixed savepoint failure in `DELETE + INSERT` branch:
   - replaced `to_sql` inside savepoint with parameterized `executemany` insert batches.
4. [resolved] focused regression lock:
   - `tests/test_database_optimized_alias_views.py::test_optimized_upsert_replaces_legacy_decimal_key_without_duplicate`.
5. [pending-long] kluster quality note (P4):
   - `insert_dataframe_optimized` remains large and multi-responsibility.
   - deferred by scope policy (no broad refactor in this sprint); keep for dedicated architecture sprint.

## Update 2026-02-24 (policy shift: canonical write only for SSA ids)

1. [resolved] removed legacy read-compat in optimized upsert path:
   - lookup/update now uses only canonical `numero_ssa` keys.
2. [resolved] enforced write validation for canonical storage ids:
   - added fail-fast validation in `insert_dataframe_optimized` after normalization;
   - decimal artifacts in `numero_ssa`/`derivada_de` are rejected in write path.
3. [resolved] kept performance-oriented batch paths:
   - canonical lookup chunk and `executemany` update/insert paths preserved.
4. [decision] migration strategy for this cycle:
   - legacy cleanup to be handled by controlled DB reset/migration, not runtime compatibility branches.

## Update 2026-02-24 (canonical write policy extended to non-optimized upsert)

1. [resolved] extended canonical write enforcement to non-optimized import path:
   - `armazenamento/database_upsert_logic.py` now normalizes `numero_ssa` and `derivada_de` to canonical storage format.
2. [resolved] explicit validation in standard upsert path:
   - fail-fast validation rejects decimal artifacts after normalization in storage id columns.
3. [resolved] regression lock:
   - `tests/test_database_upsert_canonical_write.py` validates canonical persistence in non-optimized mode.

## Update 2026-02-24 (upsert chunk dedupe performance - minimal patch)

1. [resolved] reduced O(n2) dedupe in `_perform_upsert` chunk preparation:
   - replaced manual loop+`any(...)` with pandas `dropna().drop_duplicates().tolist()`.
2. [resolved] behavior lock for duplicate key in same chunk:
   - expanded `tests/test_db_reset_and_upsert.py` with duplicate `numero_ssa` scenario.
3. [scope] no architecture refactor:
   - change limited to chunk key preparation only.

## Update 2026-02-24 (prepare_dataframe_for_upsert copy-path perf)

1. [resolved] reduced overhead in dataframe preparation for standard upsert:
   - replaced `pd.DataFrame(frame.values, columns=frame.columns)` with `frame.copy()`.
2. [resolved] behavior lock:
   - added focused test to ensure input dataframe is not mutated and normalized output remains canonical.
3. [scope] minimal patch only:
   - no flow/algorithm refactor beyond copy-path change.

## Update 2026-02-24 (logging mapping-args interpolation fix)

1. [resolved] fixed semantic bug in ASCII logging filter:
   - preserved mapping-style `record.args` (`dict`) instead of forcing tuple conversion.
2. [resolved] consistency applied in both entrypoints:
   - `main.py` and `dev_env/streamlit_app.py` now share the same mapping-aware behavior.
3. [resolved] regression lock:
   - `tests/test_ascii_logging_filter.py` covers mapping args and tuple args.
4. [operational-note] legacy DB reset policy:
   - canonical-write enforcement is in code paths; legacy cleanup reset remains an explicit operational action, not an automatic runtime mutation.

## Update 2026-02-24 (streamlit cache compatibility fallback fix)

1. [resolved] fixed fallback inconsistency in compatibility cache methods:
   - `get_cached_filter` and `cache_filter_result` now respect active backend (`session_state` or local fallback).
2. [resolved] reduced non-runtime fragility:
   - cache stats and eviction counters now update in local fallback path as well.
3. [scope] minimal patch:
   - no layout/UI changes and no filter algorithm changes.

## Update 2026-02-24 (streamlit filter guard + ui-noise reduction)

1. [resolved] guard against missing filter columns in streamlit path:
   - `apply_all_filters_cached` now checks column presence before `isin(...)` filters.
2. [resolved] reduced UI noise/perf overhead on cache miss telemetry:
   - replaced `st.info` per miss with structured logger message.
3. [scope] no layout changes:
   - patch limited to runtime filter safety and telemetry behavior.

## Update 2026-02-24 (streamlit import flow ui unblock)

1. [resolved] removed artificial UI blocking after import action:
   - deleted `time.sleep(0.5)` from `_execute_import` finalization path.
2. [impact] responsiveness improvement:
   - progress placeholder is now cleared immediately after import flow ends.
3. [scope] minimal change:
   - no import semantics/layout changes.

## Update 2026-02-24 (streamlit broad hardening cycle)

1. [resolved] streamlit import resilience for non-streamlit environments:
   - `dev_env/streamlit_app.py` now falls back to local stub when `streamlit` package is unavailable.
2. [resolved] cache backend consistency:
   - centralized backend resolution in `StreamlitFilterCache` to avoid session/local divergence across methods.
3. [resolved] cache stale-hit reduction with low-overhead token:
   - added `df_token` support to cache get/put keying;
   - token uses lightweight head/tail sampling and memoizes on `df.attrs`.
4. [resolved] pandas deprecation cleanup:
   - removed deprecated `pd.options.mode.copy_on_write` assignment.
5. [resolved] regression coverage for fallback/cache token:
   - `tests/test_streamlit_filter_cache.py`.

## Update 2026-02-24 (streamlit long cycle: layout + runtime hardening)

1. [resolved] broader layout/positioning update in streamlit UI:
   - replaced monolithic single-flow rendering with tabs (`Filtros`, `Tabela`, `Exportacao`, `Cache e API`).
   - table area now uses explicit pagination controls (page size + page number).
2. [resolved] API fetch behavior improved:
   - API access changed from automatic-per-rerun to manual action button in `Cache e API` tab.
   - latest API snapshot persisted in `session_state` until explicit refresh/clear.
3. [resolved] runtime hardening:
   - safe fallback stub when `streamlit` package is missing.
   - improved runtime detection (`st.runtime.exists()` when available).
4. [resolved] cache consistency/performance:
   - unified backend resolver reused across all cache methods.
   - cache key includes lightweight `df_token` with memoization in `df.attrs`.
5. [resolved] maintenance/perf cleanup:
   - removed deprecated pandas CoW option assignment.
6. [resolved] expanded focused tests:
   - `tests/test_streamlit_filter_cache.py` now covers fallback cache methods, token differentiation, option builder and pagination helper.

## Update 2026-02-24 (streamlit long cycle v2: applied filters workflow + sortable paged table)

1. [resolved] filter workflow moved to explicit form submit/reset:
   - filter changes now apply on demand (no per-keystroke heavy rerun).
   - reset action restores defaults and reruns safely.
2. [resolved] full-selection normalization for multiselect filters:
   - selecting all values now collapses to no-op filter to avoid unnecessary `isin(...)` passes.
3. [resolved] robust mixed-type options:
   - filter option builder now sorts by string key and tolerates mixed types.
4. [resolved] table usability/layout improvements:
   - sortable table (`Ordenar por` + `Desc`) before pagination;
   - pagination controls reorganized in table toolbar.
5. [resolved] stability guard for rerun API compatibility:
   - `st.rerun()` with fallback to `st.experimental_rerun()`.
6. [resolved] regression expansion:
   - `tests/test_streamlit_filter_cache.py` now covers mixed-type options and normalized full selection behavior.

## Update 2026-02-24 (streamlit pending after long cycle v3)

1. [deferred][P4][streamlit/perf] Profile optional virtualization path for very large pages (>2000 rows) in table render.
   - reason: current cycle prioritized stable layout/flow fix with low-risk patch.
2. [deferred][P4][streamlit/usability] Add responsive preset memory per device width bucket.
   - reason: requires broader UX validation and should run in dedicated UI sprint.
3. [deferred][P4][streamlit/tests] Add integration-level smoke for tab rendering and API toggle permutations.
   - reason: needs streamlit runtime harness beyond current focused unit scope.

## Update 2026-02-24 (post streamlit long cycle v4)

1. [deferred][P4][architecture] Streamlit god-module split (`dev_env/streamlit_app.py`) remains for dedicated refactor sprint.
   - rationale: this cycle prioritized functional/layout/security fixes with minimal risk and rollback-friendly slices.
2. [deferred][P4][streamlit/perf] Evaluate optional row virtualization strategy for very large page sizes (>2000).
3. [deferred][P4][streamlit/tests] Add runtime integration smoke for sidebar path validation and tab rendering permutations.

## Update 2026-02-24 (streamlit long cycle final note)

1. [note] Width manager override semantics intentionally fixed to deterministic baseline in this cycle.
2. [deferred][P4] If future sprint needs user-resizable persistent widths, implement as explicit feature with dedicated tests.

## Update 2026-02-25 (post streamlit long cycle v6)

1. [deferred][P4][streamlit/usability] Evaluate optional compact mode for very small screens (<1280 px) with hidden secondary controls.
2. [deferred][P4][streamlit/perf] Add lightweight telemetry for dataframe render time per width profile.
