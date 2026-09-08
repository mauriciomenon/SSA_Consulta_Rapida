"""Regressions for concurrent outcome ownership and partial batches."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from core import import_outcome


@pytest.fixture(autouse=True)
def isolated_import_outcome(monkeypatch):
    monkeypatch.setattr(import_outcome._OUTCOME_CONTEXT, "outcome", None, raising=False)


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("failure_batch", [1, 2])
def test_worker_retains_partial_outcome_when_importer_raises(
    monkeypatch, explicit, failure_batch
):
    from PyQt6.QtWidgets import QApplication
    from extracao import extractor
    from gui.workers import rescan_worker

    app = QApplication.instance() or QApplication([])
    assert app is not None
    worker = rescan_worker.RescanWorker(
        main_py_path="main.py", project_root=".",
        explicit_files=("first.xlsx", "second.xlsx") if explicit else None,
    )
    monkeypatch.setattr(extractor, "MAX_IMPORT_BATCH_FILES", 1)
    monkeypatch.setattr(worker, "_prepare_import_inputs", lambda: (True, None))
    monkeypatch.setattr(worker, "_count_database_rows", lambda: 1)
    monkeypatch.setattr(worker, "_attach_logger", lambda: None)
    calls = 0

    def importer(**kwargs):
        nonlocal calls
        calls += 1
        failed = calls == failure_batch or not explicit
        import_outcome.record_import_outcome(import_outcome.build_import_outcome(
            raw_status="importer_error" if failed else "no_changes",
            legacy_result=False, run_id=str(calls), reason="failure after commit",
            primary_db_path="db", working_db_path="db",
            primary_database_actually_changed=failed,
        ))
        if failed:
            raise RuntimeError("failure after commit")
        return False

    monkeypatch.setattr(rescan_worker, "run_importer_logic", importer)
    errors = []
    worker.finished_error.connect(errors.append)
    worker.run()
    assert errors and "failure after commit" in errors[0]
    assert worker._last_import_outcome is not None
    assert worker._last_import_outcome.status is import_outcome.ImportStatus.IMPORTER_ERROR
    assert worker._last_import_outcome.primary_database_changed


@pytest.mark.parametrize("invalid_root", [False, True])
def test_exception_before_record_does_not_reuse_thread_outcome(monkeypatch, invalid_root):
    from gui.workers import rescan_worker

    previous = import_outcome.build_import_outcome(
        raw_status="updated", legacy_result=True, run_id="old",
        reason="", primary_db_path="db", working_db_path="db",
    )
    import_outcome.record_import_outcome(previous)
    worker = rescan_worker.RescanWorker(main_py_path="main.py", project_root=".")
    worker._last_import_outcome = previous
    if invalid_root:
        worker.project_root = object()

    def importer(**kwargs):
        raise ValueError("invalid preflight path")

    monkeypatch.setattr(rescan_worker, "run_importer_logic", importer)
    with pytest.raises((ValueError, TypeError)):
        worker._run_import_operation()
    assert worker._last_import_outcome is None


def test_each_thread_reads_its_own_completed_invocation():
    barrier = Barrier(2)

    def run(run_id):
        outcome = import_outcome.build_import_outcome(
            raw_status="updated", legacy_result=True, run_id=run_id,
            reason="", primary_db_path=run_id, working_db_path=run_id,
        )
        import_outcome.record_import_outcome(outcome)
        barrier.wait(timeout=5)
        return import_outcome.get_last_import_outcome()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["first", "second"]))
    assert [outcome.run_id for outcome in results] == ["first", "second"]


@pytest.mark.parametrize("statuses", [
    ("updated", "no_changes"), ("updated", "import_busy"),
    ("updated", "importer_error"), ("importer_error", "updated"),
])
def test_batches_preserve_changes_and_blocking_status(monkeypatch, statuses):
    from PyQt6.QtWidgets import QApplication
    from extracao import extractor
    from gui.workers.rescan_worker import RescanOutcome, RescanWorker

    app = QApplication.instance() or QApplication([])
    assert app is not None
    worker = RescanWorker(main_py_path="main.py", project_root=".",
                          explicit_files=("first.xlsx", "second.xlsx"))
    monkeypatch.setattr(extractor, "MAX_IMPORT_BATCH_FILES", 1)
    monkeypatch.setattr(worker, "_prepare_import_inputs", lambda: (True, None))
    monkeypatch.setattr(worker, "_count_database_rows", lambda: 1)
    monkeypatch.setattr(worker, "_attach_logger", lambda: None)
    monkeypatch.setattr(worker, "_detach_logger", lambda: None)
    status_iter = iter(statuses)
    errors = []
    worker.finished_error.connect(errors.append)

    def import_batch():
        status = next(status_iter)
        worker._last_import_outcome = import_outcome.build_import_outcome(
            raw_status=status, legacy_result=status == "updated", run_id=status,
            reason="test", primary_db_path="db", working_db_path="db",
        )
        return status == "updated"

    monkeypatch.setattr(worker, "_run_import_operation", import_batch)
    worker.run()
    assert worker._last_import_outcome.primary_database_changed
    assert worker.last_outcome is RescanOutcome.UPDATED
    assert bool(errors) is any(status in {"import_busy", "importer_error"} for status in statuses)


def test_concurrent_launchers_keep_their_own_exit_codes():
    import logging
    from launchers.cli_entry import _execute_import_and_report

    barrier = Barrier(2)

    def execute(status):
        def importer(**kwargs):
            import_outcome.record_import_outcome(import_outcome.build_import_outcome(
                raw_status=status, legacy_result=True, run_id=status,
                reason="", primary_db_path="db", working_db_path="db",
            ))
            barrier.wait(timeout=5)
            return True

        return _execute_import_and_report(
            importer, docs_dir="docs", data_dir="data", runtime_base=".",
            logger=logging.getLogger(__name__),
        )["exit_code"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, ["updated", "import_busy"]))
    assert results == [0, 1]


def test_promotion_log_names_actual_blocking_error(monkeypatch, caplog):
    from core import app_logic

    monkeypatch.setattr(app_logic, "_update_cache_for_deterministic_failures", lambda *a: None)
    with caplog.at_level("ERROR"):
        result = app_logic._finalize_import_run_outcome(
            successfully_processed_files=["ok.xlsx"],
            successful_regular_files_with_records=[("ok.xlsx", 1)],
            deterministic_failed_files=["rejected.xlsx"],
            critical_errors=[("extraction", "missing.xlsx", "missing file"),
                             ("validation", "rejected.xlsx", "bad columns")],
            file_reports=[], files_to_process=["ok.xlsx", "missing.xlsx", "rejected.xlsx"],
            sync_materialized=False, candidate_db_path="candidate.db",
            working_db_path="candidate.db", primary_db_path="primary.db",
            table_name="ssa_table", docs_dir="docs", cache_file="cache",
            move_processed_after_import=False, discovery_settings={}, phase_durations={},
        )
    assert result["status"] == "candidate_incomplete"
    assert "['extraction']" in caplog.text
    assert "validation" not in caplog.text


def test_streamlit_reports_partial_update_as_error():
    import ast
    from pathlib import Path
    from unittest.mock import MagicMock

    source = ast.parse((Path(__file__).parents[1] / "dev_env/streamlit_app.py").read_text())
    classification = next(
        node for node in ast.walk(source)
        if isinstance(node, ast.If)
        and "_import_outcome.is_blocking_status" in ast.unparse(node.test)
    )
    outcome = import_outcome.build_import_outcome(
        raw_status="updated_partial", legacy_result=True, run_id="partial",
        reason="partial error", primary_db_path="db", working_db_path="db",
    )
    streamlit = MagicMock()
    exec(compile(ast.Module(body=[classification], type_ignores=[]), "streamlit-status", "exec"), {
        "st": streamlit, "outcome": outcome, "status": outcome.status,
        "status_value": outcome.status.value, "_import_outcome": import_outcome, "ok": True,
    })
    streamlit.error.assert_called_once()
    streamlit.success.assert_not_called()
    assert "parciais" in streamlit.error.call_args.args[0]


@pytest.mark.parametrize("changed", [False, True])
@pytest.mark.parametrize("batch_reloaded", [False, True])
def test_late_cancel_after_success_reloads_committed_changes(changed, batch_reloaded):
    from types import SimpleNamespace
    from gui.ssa.gui_rescan_lifecycle import connect_rescan_worker_lifecycle
    from gui.workers.rescan_worker import RescanOutcome
    from tests.test_gui_workers_rescan_data import _BaseWorker, _DialogNoop, _Window

    window = _Window()
    worker = _BaseWorker("main.py", ".")
    dialog = _DialogNoop(window)
    window._active_rescan_worker = worker
    window._active_rescan_dialog = dialog
    connect_rescan_worker_lifecycle(
        window, worker, dialog, reload_on_success=True, is_explicit_import=False,
        normalized_kind="import", global_workers=[], global_meta={}, max_global_workers=8,
        retired_ttl_sec=30, retired_force_wait_ms=10, sip_module=None,
        connect_signal=lambda signal, slot, **kwargs: signal.connect(slot),
        prune_retired_workers=lambda *args, **kwargs: None,
        is_worker_running=lambda target, _sip: target.isRunning(),
        set_status_label_text=lambda target, text, **kwargs: target.status_label.setText(text),
    )
    setattr(worker, "last_outcome", RescanOutcome.UPDATED if changed else RescanOutcome.NO_CHANGES)
    setattr(worker, "_last_import_outcome", SimpleNamespace(primary_database_changed=changed))
    if batch_reloaded:
        worker.batch_completed.emit(1, 1)
    worker._running = False
    dialog.cancel_requested.emit()
    worker.finished_success.emit()

    assert window.load_calls == int(batch_reloaded or changed)
    assert "cancelado" in window.status_label.text.lower()


def test_diff_snapshot_restore_without_files_marks_changed_and_reloads_gui(tmp_path):
    import sqlite3
    from contextlib import closing
    from PyQt6.QtWidgets import QApplication
    from armazenamento.database import initialize_database
    from armazenamento import database_integrity
    from gui.workers.rescan_worker import RescanOutcome, RescanWorker
    from gui.ssa.gui_rescan_lifecycle import connect_rescan_worker_lifecycle
    from tests.test_gui_workers_rescan_data import _DialogNoop, _Window

    app = QApplication.instance() or QApplication([])
    assert app is not None
    (tmp_path / "docs_entrada").mkdir()
    data = tmp_path / "data"
    data.mkdir()
    db_path = data / "ssas.db"
    initialize_database(str(db_path), "config/schema_unified.sql")
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600001', 'ADM', '2026-01-01 00:00:00')")
    assert database_integrity._create_integrity_snapshot(str(db_path), force=True)
    db_path.write_bytes(b"corrupted SQLite" * 64)
    worker = RescanWorker(main_py_path=str(tmp_path / "main.py"),
                          project_root=str(tmp_path), db_path=str(db_path), force_import=False)
    window = _Window()
    dialog = _DialogNoop(window)
    window._active_rescan_worker = worker
    window._active_rescan_dialog = dialog
    connect_rescan_worker_lifecycle(
        window, worker, dialog, reload_on_success=True, is_explicit_import=False,
        normalized_kind="import", global_workers=[], global_meta={}, max_global_workers=8,
        retired_ttl_sec=30, retired_force_wait_ms=10, sip_module=None,
        connect_signal=lambda signal, slot, **kwargs: signal.connect(slot),
        prune_retired_workers=lambda *args, **kwargs: None,
        is_worker_running=lambda target, _sip: target.isRunning(),
        set_status_label_text=lambda target, text, **kwargs: target.status_label.setText(text),
    )
    worker.run()

    outcome = worker._last_import_outcome
    assert outcome is not None and outcome.primary_database_changed
    assert outcome.integrity_report["restored_from_snapshot"] is True
    assert outcome.legacy_result is False
    assert worker.last_outcome is RescanOutcome.UPDATED
    assert window.load_calls == 1
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [("202600001",)]


def test_arrow_numeric_failure_logs_cause_and_keeps_string_fallback(monkeypatch, caplog):
    import ast
    import logging
    from pathlib import Path
    from typing import Any
    import pandas as pd

    source = ast.parse((Path(__file__).parents[1] / "dev_env/streamlit_app.py").read_text())
    definitions: list[ast.stmt] = [node for node in source.body if isinstance(node, ast.FunctionDef)
                   and node.name in {"ensure_arrow_compatible", "_json_if_arrow_cell"}]
    namespace: dict[str, Any] = {"pd": pd, "Any": Any, "logger": logging.getLogger("arrow_fallback_test")}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "arrow_fallback", "exec"), namespace)

    def numeric_failure(*args, **kwargs):
        raise ValueError("numeric conversion repro")

    monkeypatch.setattr(pd, "to_numeric", numeric_failure)
    frame = pd.DataFrame({"mixed": pd.Series([1, 2, "bad"], dtype="object")})
    with caplog.at_level(logging.WARNING, logger="arrow_fallback_test"):
        result = namespace["ensure_arrow_compatible"](frame)
    assert result["mixed"].tolist() == ["1", "2", "bad"]
    assert frame["mixed"].tolist() == [1, 2, "bad"]
    assert "mixed" in caplog.text
    assert "numeric conversion repro" in caplog.text
