# Pending Action Matrix

Fonte: docs/RECOVERY_BACKLOG.md
Total itens: 108

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

## 4. [pending] core/config_manager.py:549
- Item: **Silent Failure on Default Settings Creation** If the creation of a default configuration file fails (e.g., due to permission issues or disk errors), the error is only logged a...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.

## 5. [pending] core/config_manager.py:44
- Item: **Suppressed Exceptions in Atomic File Operations** In the `_atomic_write_json_file` function, exceptions during file descriptor closing and temporary file removal are suppresse...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.

## 6. [pending] extracao/extractor.py:259
- Item: After detecting the header row and extracting data, the function does not validate that all required columns are present in the resulting DataFrame. This could lead to downstrea...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.

## 7. [pending] extracao/extractor.py:306
- Item: The code loads column mappings with `_load_column_mappings()` and applies them to the DataFrame. If the mapping is empty (e.g., due to a loading error), columns will not be rena...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.

## 8. [pending] gui/cache/filter_cache.py:50
- Item: **Potential Exception Risk:** The method `result.copy()` is called without verifying that `result` is a valid DataFrame. If the cached object is not a DataFrame or is `None`, th...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 9. [pending] gui/cache/filter_cache.py:59
- Item: **Performance Concern:** The cache always stores a copy of the DataFrame (`result.copy()`) on every put. For large DataFrames, this can be expensive in both time and memory, esp...
- Solucao proposta: Trocar polling por bloqueio com timeout curto; parametrizar limites; medir antes/depois com metrica simples.

## 10. [resolved] gui/widgets/rescan_progress_dialog.py:143
- Item: The `reject` method allows the dialog to close immediately after a cancel request, even if the underlying rescan process has not yet stopped. This could lead to user confusion o...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: `reject()` atual mantem dialogo aberto na primeira tentativa de cancelamento e emite sinal de cancelamento uma vez.

## 11. [pending] gui/workers/rescan_worker.py:132
- Item: ### Potential Logger Handler Race Condition The logger handler is added and removed within the worker thread (lines 96, 130), but if multiple threads use the same logger ('ssa')...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 12. [pending] gui/workers/rescan_worker.py:143
- Item: ### Cancellation Responsiveness Depends on `run_importer_logic` The cancellation logic relies on `run_importer_logic` invoking the `should_cancel` callback frequently (line 107)...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.

## 13. [pending] interface/cli_enhancement_manager.py:134
- Item: **Potential Data Race in _save_settings:** The `_save_settings` method uses best-effort file locking via `_lock_file_if_possible`, but this approach may not reliably prevent con...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 14. [stale-doc] interface/command_handlers.py:28
- Item: **Overly broad exception handling in `_save_settings_handler`:** Catching all exceptions and only printing the error message does not allow for proper error tracking or programm...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: handler atual captura conjunto explicito, faz logger.exception e re-raise.

## 15. [pending] main.py:759
- Item: ### Critical Issue: Incomplete Failure Handling for Optimized and Legacy Import Modes If both the optimized import (`enable_optimized_import`) and the legacy import logic fail, ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 16. [pending] main.py:591
- Item: ### Performance Issue: Directory Listing in Debug Mode In the block that lists files in important directories (lines 569-605), if any of these directories contain a large number...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 17. [pending] scripts/run_pytest_stream_and_log.py:119
- Item: The warning about dropped lines is only emitted when `dropped_lines % 200 == 1`, which may result in infrequent warnings during periods of high output loss. This could obscure t...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 18. [pending] scripts/run_pytest_stream_and_log.py:84
- Item: The queue size for `line_queue` is hardcoded to 4096. This may not be optimal for all environments or workloads, potentially leading to unnecessary output loss or excessive memo...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 19. [pending] scripts/run_pytest_stream_and_log_v2.py:140
- Item: **Potential Data Race on `dropped_lines`** The `dropped_lines` variable is incremented in both the main thread and the reader thread without synchronization. This can lead to a ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 20. [pending] scripts/run_pytest_stream_and_log_v2.py:163
- Item: **Busy-Wait Loop for Sentinel Delivery** The loop that ensures the sentinel (`None`) is delivered to the queue (`while True: ... time.sleep(0.005)`) can result in unnecessary CP...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 21. [pending] tests/test_caching_atomic_save.py:30
- Item: **Missing test for concurrent writes:** The test `test_save_cache_is_atomic_and_does_not_corrupt_existing_file` only simulates a single failure mode (exception during write) and...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 22. [pending] tests/test_database_optimized_alias_views.py:15
- Item: The test does not handle errors that may occur during database initialization (e.g., missing or invalid 'config/schema.sql'). This could result in unclear test failures. **Recom...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 23. [pending] tests/test_database_optimized_alias_views.py:35
- Item: The test creates a database file but does not explicitly remove it after execution. This may leave residual files in the test environment, affecting test isolation and potential...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 24. [pending] tests/test_filter_cache_locking.py:28
- Item: **Insufficient Verification of Lock Usage** The assertion `assert spy.enter_count >= 1` (line 28) only verifies that the lock was entered at least once, but does not ensure that...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 25. [pending] tests/test_filter_error_skips_modal_in_pytest.py:30
- Item: The patch target `"gui.mixins.filter_gui_ssa_mixin.QMessageBox.critical"` is tightly coupled to the import path and structure of the module under test. If the import path or the...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 26. [pending] interface/cli_enhancement_manager.py:24
- Item: **suggestion (bug_risk):** File locking is applied to the temp file, so it doesnt actually coordinate concurrent writers on the real settings file. In `_save_settings`, locking ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 27. [pending] tests/test_import_cancellation.py:65
- Item: **suggestion (testing):** Fortalea o teste verificando tambm o payload final de progresso "finish" Como `run_importer_logic` agora normaliza e protege `progress_callback`, captu...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 28. [pending] tests/test_rescan_progress_dialog.py:28
- Item: **suggestion (testing):** Estenda as asseres para cobrir o estado da UI aps o cancelamento (texto de status e estados habilitado/desabilitado dos botes) Como `reject()` e `set_f...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 29. [pending] tests/test_rescan_worker_cleanup.py:27
- Item: **suggestion (testing):** Considere exercitar tambm o caminho de sucesso para comprovar que os handlers so liberados no caso sem erro Para validar completamente o novo cleanup n...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 30. [pending] interface/cli_enhancement_manager.py:100
- Item: O lock aplicado em _save_settings() est sendo feito no arquivo temporrio recm-criado. Isso no serializa gravaes concorrentes para o mesmo settings_file (cada processo trava seu ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 31. [pending] interface/cli_enhancement_manager.py:93
- Item: _lock_file_if_possible() usa flock LOCK_EX (bloqueante) em POSIX. Se outro processo ficar segurando o lock, essa chamada pode travar a CLI indefinidamente. Para manter 'best-eff...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 32. [resolved] armazenamento/database_optimized.py:237
- Item: existing_dict montado a partir de chunk_df['numero_ssa'] sem normalizao de tipo, mas has_ssa['numero_ssa'] foi normalizado para str. Como SQLite pode conter valores antigos com...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: lookup atual normaliza `numero_ssa` no chunk retornado e no conjunto consultado.

## 33. [pending] extracao/extractor.py:214
- Item: A anotao de retorno ainda est como Optional[pd.DataFrame], mas a funo agora retorna DataFrame (incluindo vazio) e levanta ExtractionError nos erros (no retorna None). Ajuste a a...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.

## 34. [pending] extracao/extractor.py:223
- Item: A docstring ainda diz que retorna None em caso de erro, mas o fluxo agora levanta ExtractionError (e retorna DataFrame vazio quando h cabealho mas sem linhas). Atualize a seo Re...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.

## 35. [pending] extracao/extractor.py:236
- Item: pd.ExcelFile() criado mas no fechado explicitamente. Para evitar vazamento de handle/arquivo (especialmente em loops de muitos arquivos), use um context manager (with pd.Excel...
- Solucao proposta: Validar colunas obrigatorias apos parse e falhar cedo com mensagem clara.

## 36. [pending] core/config_manager.py:443
- Item: load_display_mappings_integrity() passou a levantar RuntimeError se falhar ao restaurar o arquivo, alterando o comportamento anterior (que retornava DEFAULT_DISPLAY_MAPPINGS mes...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 37. [pending] core/config_manager.py:474
- Item: load_column_mappings_integrity() agora levanta RuntimeError ao falhar em restaurar o arquivo, o que pode interromper a aplicao em ambientes sem permisso de escrita. Para preserv...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 38. [pending] gui/workers/rescan_worker.py:125
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 1\. <b><i>rescanworker</i></b> exposes raw exception <code> R...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 39. [pending] gui/gui_ssa.py:6674
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 2\. Rescan thread may outlive app <code> Bug</code> <code> Re...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 40. [pending] core/config_manager.py:454
- Item: <img src="https://www.qodo.ai/wp-content/uploads/2025/12/v2-action-required.svg" height="20" alt="Action required"> 3\. Config restore can crash cli <code> Bug</code> <code> Rel...
- Solucao proposta: Fallback controlado: tentar restaurar, se falhar retornar defaults com aviso claro sem crash.

## 41. [pending] interface/cli_enhancement_manager.py:88
- Item: ![medium](https://www.gstatic.com/codereviewagent/medium-priority.svg) The file lock is being applied to the temporary file created by `mkstemp`. Since each process creates a un...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 42. [pending] core/app_logic.py:450
- Item: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes:\n\n1. `_import_single_file` now accepts `s...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 43. [pending] gui/mixins/filter_gui_ssa_mixin.py:343
- Item: <!-- metadata:{"confidence":9,"steps":[{"text":"","toolCalls":[{"toolName":"bash","input":{"command":"rg -n '^import os' gui/mixins/filter_gui_ssa_mixin.py; rg -n 'import os' gu...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 44. [pending] gui/gui_ssa.py:5094
- Item: <!-- metadata:{"confidence":7,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the key changes in this PR:\n\n1. Import of `atomic_write_j...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 45. [pending] main.py:487
- Item: <!-- metadata:{"confidence":8,"steps":[{"text":"","toolCalls":[{"toolName":"think","input":{"thought":"Let me analyze the diff carefully for issues:\n\n1. **Non-ASCII characters...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 46. [pending] extracao/extractor.py:214
- Item: **P1** | Confidence: High The function signature now includes a `should_cancel` callback. The related context shows the primary caller, `run_importer_logic` in `core/app_logic.p...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.

## 47. [resolved] armazenamento/database_optimized.py:167
- Item: **P1** | Confidence: High The addition of SQL identifier validation (`is_valid_identifier`) is a critical security improvement to prevent injection via the `table_name` paramete...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: validacao de identificador segue ativa e testada.

## 48. [pending] main.py:480
- Item: **P2** | Confidence: High Speculative: The validation logic for conflicting CLI flags `--skip-import` and `--force-rescan` is sound. However, the error message references `--res...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 49. [pending] core/app_logic.py:330
- Item: **[Contextual Comment]** _This comment refers to code near real line 325. Anchored to nearest_changed(328) line 328._ --- **P1** | Confidence: High `run_importer_logic` now has ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 50. [pending] gui/gui_ssa.py:6434
- Item: _ Potential issue_ | _ Critical_ <details> <summary> Analysis chain</summary> Script executed: ```shell #!/bin/bash # Get RescanWorker implementation to understand signal timin...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 51. [pending] scripts/run_pytest_stream_and_log_v2.py:195
- Item: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 155-167, the warning is enqueued before the real output. When the queue is fu...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 52. [pending] scripts/run_pytest_stream_and_log.py:153
- Item: _ Potential issue_ | _ Minor_ **Avoid warning line displacing real output after eviction.** On Line 116-128, the warning is enqueued before the real output. With a full queue, e...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

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

## 56. [pending] tests/test_open_docs_folder_nonblocking.py:32
- Item: _ Potential issue_ | _ Minor_ **Class attribute `called` may cause test isolation issues.** `DummyQDesktopServices.called` is a class-level list that persists across test runs i...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 57. [stale-doc] core/app_logic.py:185
- Item: The check for `if df is None:` at line 181-184 is dead code. The extractor function `extract_data_from_excel` has been updated to never return None - it either returns a DataFra...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: trecho `if df is None` nao esta presente no estado atual.

## 58. [pending] extracao/extractor.py:224
- Item: The return type annotation in the docstring (line 221-223) says `Optional[pd.DataFrame]` and mentions "ou None em caso de erro", but the function now never returns None - it eit...
- Solucao proposta: Alinhar assinatura, docstring e comportamento real no mesmo commit com teste de contrato.

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

## 62. [pending] scripts/run_pytest_stream_and_log_v2.py:176
- Item: In scripts/run_pytest_stream_and_log_v2.py, _safe_queue_put mutates dropped_lines (e.g., `dropped_lines += 1`) but the nested function never declares `nonlocal dropped_lines` (u...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 63. [resolved] gui/widgets/rescan_progress_dialog.py:147
- Item: RescanProgressDialog.reject() currently emits cancel_requested but never calls super().reject()/close()/hide() in the non-finished case. When this dialog is shown with exec(), t...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.
- Evidencia: segunda chamada de `reject()` fecha o dialogo (`QDialog.Rejected`) sem reemitir cancel.

## 64. [pending] gui/workers/rescan_worker.py:162
- Item: RescanWorker cleanup: the finally block wraps `_detach_logger()` in `suppress(Exception)`, but `_detach_logger()` performs multiple state updates (removeHandler, refcount decrem...
- Solucao proposta: Remover suppress silencioso; manter log com contexto e erro explicito de retorno/rethrow.

## 65. [resolved] gui/widgets/rescan_progress_dialog.py:131
- Item: In `set_finished`, when the rescan fails (`success == False`) and the `message` argument is empty, the error display (`self.error_text`) is not updated with any indication of fa...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `set_finished(False, "")` define mensagem padrao de erro e adiciona `ERRO FINAL` no painel.

## 66. [resolved] tests/test_rescan_progress_dialog.py:48
- Item: **Potential nondeterminism in event processing:** The tests rely on single calls to `QApplication.processEvents()` after dialog actions (e.g., `dlg.reject()`, `dlg.set_finished(...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.
- Evidencia: testes agora usam espera curta por condicao (`_spin_until`) em vez de um unico `processEvents()`.

## 67. [pending] scripts/run_pytest_stream_and_log.py:167
- Item: The `dropped_lines` variable is accessed without synchronization from multiple threads, creating a race condition. The reader thread (calling `_safe_queue_put`) and the main thr...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 68. [resolved] core/config_manager.py:453
- Item: After successfully writing the default mappings to the file, the function returns `DEFAULT_DISPLAY_MAPPINGS.copy()` instead of reading back the newly created file. This is incon...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `load_display_mappings_integrity()` reler arquivo restaurado antes do fallback em memoria; teste focado cobre contrato.

## 69. [pending] core/config_manager.py:485
- Item: After successfully writing the default mappings to the file, the function returns `DEFAULT_COLUMN_MAPPINGS.copy()` instead of reading back the newly created file. This is incons...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 70. [pending] gui/gui_ssa.py:4275
- Item: GLOBAL_RETIRED_DATA_LOADER_META[worker] is assigned twice consecutively. This looks like an accidental duplicate and makes it harder to reason about worker lifetime accounting; ...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 71. [pending] gui/widgets/rescan_progress_dialog.py:143
- Item: The dialog's Cancel action (reject override) only emits cancel_requested and keeps the modal dialog open until the user tries to close it a second time. This differs from the PR...
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.

## 72. [pending] scripts/run_pytest_stream_and_log_v2.py:158
- Item: In _safe_queue_put(None), the sentinel delivery path uses line_queue.put(..., timeout=0.2) and line_queue.get(..., timeout=0.2). This can still block the reader thread (even if ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 73. [pending] core/config_manager.py:86
- Item: **Potential File Descriptor Leak in `_atomic_copy_file`** If `os.close(fd)` fails inside the inner `try`/`except`, the file descriptor is never closed and will leak, as the `fin...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 74. [pending] scripts/run_pytest_stream_and_log.py:167
- Item: Race condition: The `dropped_lines` variable is accessed without synchronization from the reader thread. Multiple concurrent accesses at lines 115, 132, 136-137, 145-147 create ...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 75. [resolved] armazenamento/database_optimized.py:75
- Item: SQL injection risk: The PRAGMA statement uses f-string formatting with the table name without validation. While `_has_referencing_foreign_keys` is an internal function, the `tab...
- Solucao proposta: Aplicar allowlist de identificadores + validacao estrita + SQL parametrizado onde possivel.
- Evidencia: `_has_referencing_foreign_keys` valida identificadores e usa quote helper.

## 76. [pending] gui/gui_ssa.py:4386
- Item: Race condition on global worker retention lists: `GLOBAL_RETIRED_DATA_LOADER_WORKERS` and `GLOBAL_RETIRED_DATA_LOADER_META` are accessed from multiple SSAMainWindow instances wi...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 77. [pending] scripts/run_pytest_stream_and_log.py:167
- Item: The warn_count modulo check at line 142 and 154 can fire on the same count (when warn_count % 200 == 1). At line 138-148, if the second put_nowait succeeds after eviction, it em...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 78. [pending] scripts/run_pytest_stream_and_log_v2.py:209
- Item: The same duplicate warning issue exists here as in run_pytest_stream_and_log.py. The warn_count modulo check at line 184 and 196 can both trigger on the same count value, potent...
- Solucao proposta: Adicionar teste deterministico focado no risco real (concorrencia/cancel/io), evitando mock fragil excessivo.

## 79. [pending] gui/workers/rescan_worker.py:81
- Item: The _attach_logger and _detach_logger methods modify global state (_LOGGER_REFCOUNT, _LOGGER_PREV_LEVEL) but there's a risk if _attach_logger succeeds and then _detach_logger is...
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 80. [pending] interface/cli_enhancement_manager.py:118
- Item: The msvcrt.locking call at line 118 locks 4096 bytes, but the actual file size may be smaller or larger than 4096 bytes. The msvcrt.locking function locks a specific number of b...
- Solucao proposta: Padronizar lock por recurso real (lockfile), timeout nao bloqueante e secao critica minima.

## 81. [resolved] armazenamento/database_optimized.py:79
- Item: The _has_referencing_foreign_keys function uses dynamic SQL with f-string at line 77: f"PRAGMA foreign_key_list({table})". The table name comes from sqlite_master, which should ...
- Solucao proposta: Aplicar allowlist de identificadores + validacao estrita + SQL parametrizado onde possivel.
- Evidencia: tabela de PRAGMA passa por validacao e quoting estrito.

## 82. [pending] (sem local exato)
- Item: Melhorar GUI na aba filtros, mantendo layout base sem regressao visual.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 83. [pending] (sem local exato)
- Item: Implementar filtro/capacidade de `divisao` com cobertura de teste focada.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 84. [pending] (sem local exato)
- Item: `SSAMainWindow` class size/coupling remains structural backlog for dedicated sprint; no broad refactor in this stabilization slice.
- Solucao proposta: Opcao A: sprint exclusivo de modularizacao em slices pequenos. Opcao B: manter e extrair apenas helpers locais.
- Opcao:
  - A: sprint exclusivo de modularizacao em slices pequenos
  - B: manter e extrair apenas helpers locais.

## 85. [pending] (sem local exato)
- Item: limpeza ruff de baixo risco em `scripts/*` e `launchers/*`:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 86. [pending] (sem local exato)
- Item: limpeza ruff de baixo risco em testes utilitarios:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 87. [pending] (sem local exato)
- Item: reforco de testes:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 88. [pending] (sem local exato)
- Item: Baseline alto de ty em GUI core:
- Solucao proposta: Opcao A: sprint dedicado de ty por modulo. Opcao B: manter baseline e bloquear apenas regressao nova.
- Opcao:
  - A: sprint dedicado de ty por modulo
  - B: manter baseline e bloquear apenas regressao nova.

## 89. [pending] (sem local exato)
- Item: melhorias de concorrencia em wrappers de teste:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 90. [pending] (sem local exato)
- Item: melhorias de cancel/progresso:
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.

## 91. [pending] (sem local exato)
- Item: melhoria UX filtros:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 92. [pending] (sem local exato)
- Item: arquitetura de cache:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 93. [pending] (sem local exato)
- Item: Baseline restante de ty concentrada em:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 94. [pending] (sem local exato)
- Item: Maior bloco restante de ty e ruido de tipagem:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 95. [pending] (sem local exato)
- Item: Pendencias menores fora de fluxo principal:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 96. [pending] (sem local exato)
- Item: Bloco principal restante de ty:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 97. [pending] (sem local exato)
- Item: Bloco restante de tipagem ainda concentrado:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 98. [deferred] (sem local exato)
- Item: Profile optional virtualization path for very large pages (>2000 rows) in table render.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 99. [deferred] (sem local exato)
- Item: Add responsive preset memory per device width bucket.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 100. [deferred] (sem local exato)
- Item: Add integration-level smoke for tab rendering and API toggle permutations.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 101. [deferred] (sem local exato)
- Item: Streamlit god-module split (`dev_env/streamlit_app.py`) remains for dedicated refactor sprint.
- Solucao proposta: Manter patch minimo de UX/perf; adiar refatoracao estrutural para sprint dedicado.

## 102. [deferred] (sem local exato)
- Item: Evaluate optional row virtualization strategy for very large page sizes (>2000).
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 103. [deferred] (sem local exato)
- Item: Add runtime integration smoke for sidebar path validation and tab rendering permutations.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 104. [deferred] (sem local exato)
- Item: If future sprint needs user-resizable persistent widths, implement as explicit feature with dedicated tests.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 105. [deferred] (sem local exato)
- Item: Evaluate optional compact mode for very small screens (<1280 px) with hidden secondary controls.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 106. [deferred] (sem local exato)
- Item: Add lightweight telemetry for dataframe render time per width profile.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 107. [deferred] (sem local exato)
- Item: If needed, persist render telemetry across reruns/sessions for historical comparison.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 108. [deferred] (sem local exato)
- Item: Consider optional cap/window for telemetry history to limit long-session growth.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
