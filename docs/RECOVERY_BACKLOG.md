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
