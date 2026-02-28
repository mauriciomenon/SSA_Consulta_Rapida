# Pending Action Matrix

Fonte: docs/RECOVERY_BACKLOG.md
Total itens: 108

## Update 2026-02-28 (streamlit slice: telemetry profile window cap)

1. Delivered minimal streamlit stabilization slice in `dev_env/streamlit_app.py`:
   - render telemetry now enforces a profile window cap to avoid unbounded growth in session state.
2. Added focused regression:
   - `tests/test_streamlit_filter_cache.py::test_update_render_telemetry_keeps_profile_window`.
3. Validation evidence:
   - `uv run python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
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
   - `uv run python -m py_compile` (touched files): pass
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
   - `uv run python -m py_compile tests/test_import_cancellation.py`: pass
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
   - `uv run python -m py_compile tests/test_database_optimized_alias_views.py`: pass
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
1. Resolve pending items with direct runtime risk first (`[pending]` rows).
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

## 9. [deferred] gui/cache/filter_cache.py:59
- Item: **Performance Concern:** The cache always stores a copy of the DataFrame (`result.copy()`) on every put. For large DataFrames, this can be expensive in both time and memory, esp...
- Solucao proposta: Trocar polling por bloqueio com timeout curto; parametrizar limites; medir antes/depois com metrica simples.
- Evidencia: deferred by explicit user decision (Opcao A) to avoid runtime behavior change in this sprint.

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

## 82. [deferred] (sem local exato)
- Item: Melhorar GUI na aba filtros, mantendo layout base sem regressao visual.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 83. [deferred] (sem local exato)
- Item: Implementar filtro/capacidade de `divisao` com cobertura de teste focada.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 84. [deferred] (sem local exato)
- Item: `SSAMainWindow` class size/coupling remains structural backlog for dedicated sprint; no broad refactor in this stabilization slice.
- Solucao proposta: Opcao A: sprint exclusivo de modularizacao em slices pequenos. Opcao B: manter e extrair apenas helpers locais.
- Opcao:
  - A: sprint exclusivo de modularizacao em slices pequenos
  - B: manter e extrair apenas helpers locais.

## 85. [deferred] (sem local exato)
- Item: limpeza ruff de baixo risco em `scripts/*` e `launchers/*`:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 86. [deferred] (sem local exato)
- Item: limpeza ruff de baixo risco em testes utilitarios:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

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

## 89. [deferred] (sem local exato)
- Item: melhorias de concorrencia em wrappers de teste:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 90. [deferred] (sem local exato)
- Item: melhorias de cancel/progresso:
- Solucao proposta: Garantir callback de cancel frequente + estado de UI consistente + teste de regressao de cancelamento.

## 91. [deferred] (sem local exato)
- Item: melhoria UX filtros:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 92. [deferred] (sem local exato)
- Item: arquitetura de cache:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 93. [deferred] (sem local exato)
- Item: Baseline restante de ty concentrada em:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 94. [deferred] (sem local exato)
- Item: Maior bloco restante de ty e ruido de tipagem:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 95. [deferred] (sem local exato)
- Item: Pendencias menores fora de fluxo principal:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 96. [deferred] (sem local exato)
- Item: Bloco principal restante de ty:
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.

## 97. [deferred] (sem local exato)
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

## 108. [resolved] (sem local exato)
- Item: Consider optional cap/window for telemetry history to limit long-session growth.
- Solucao proposta: Aplicar patch minimo com teste focado e registrar trade-off no backlog se nao bloquear release.
- Evidencia: `_update_render_telemetry` aplica janela maxima de perfis e remove perfis mais antigos; regressao focada adicionada em `tests/test_streamlit_filter_cache.py`.
