from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PyQt6.QtTest import QSignalSpy

from core import app_logic
from core.pai_import_service import import_prepared_pai_xlsx
from gui.ssa.pai_api_controller import _connect_worker
from gui.workers.pai_api_worker import PaiApiRefreshWorker


class _Signal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        for callback in tuple(self._callbacks):
            callback(*args)


def test_pai_import_cancelled_after_staging_never_calls_import(tmp_path: Path) -> None:
    source = tmp_path / "pai.xlsx"
    source.touch()
    cancelled = False
    db_path = tmp_path / "temp.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE imported_rows (id INTEGER PRIMARY KEY)")
    import_calls: list[tuple[Any, ...]] = []

    def should_cancel() -> bool:
        return cancelled

    def stage_files(**kwargs: Any) -> tuple[list[str], dict[str, int]]:
        nonlocal cancelled
        assert kwargs["should_cancel"] is should_cancel
        cancelled = True
        return [str(source)], {}

    def import_files(*args: Any, **kwargs: Any) -> bool:
        import_calls.append((args, kwargs))
        with sqlite3.connect(db_path) as connection:
            connection.execute("INSERT INTO imported_rows DEFAULT VALUES")
        return True

    request = SimpleNamespace(project_root=tmp_path)
    preview = SimpleNamespace(import_xlsx_path=source)

    with pytest.raises(InterruptedError, match="before database import"):
        import_prepared_pai_xlsx(
            cast(Any, request),
            cast(Any, preview),
            docs_dir=tmp_path,
            db_path=db_path,
            stage_files=stage_files,
            import_files=import_files,
            count_rows=lambda _path: 0,
            should_cancel=should_cancel,
        )

    assert import_calls == []
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM imported_rows").fetchone() == (0,)


def test_explicit_import_propagates_cancel_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    db_path = tmp_path / "data" / "temp.db"
    source = docs_dir / "pai.xlsx"
    source.touch()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        app_logic,
        "_resolve_import_targets",
        lambda _docs, _db: (docs_dir, db_path),
    )
    monkeypatch.setattr(
        app_logic,
        "_resolve_explicit_import_files",
        lambda _files, *, docs_dir_path: [str(source)],
    )

    def run_importer_logic(**kwargs: Any) -> bool:
        captured.update(kwargs)
        return True

    def should_cancel() -> bool:
        return False

    monkeypatch.setattr(app_logic, "run_importer_logic", run_importer_logic)

    assert app_logic.import_explicit_files_to_database(
        [source],
        docs_dir=str(docs_dir),
        db_path=str(db_path),
        should_cancel=should_cancel,
    )
    assert captured["should_cancel"] is should_cancel


def test_pai_terminal_signal_is_exactly_once_and_cancel_wins() -> None:
    successful = PaiApiRefreshWorker(cast(Any, object()))
    success_spy = QSignalSpy(successful.finished_success)
    error_spy = QSignalSpy(successful.finished_error)

    successful._finish()
    successful._finish("late error")
    successful.cancel()

    assert len(success_spy) == 1
    assert len(error_spy) == 0

    cancelled = PaiApiRefreshWorker(cast(Any, object()))
    cancelled_success_spy = QSignalSpy(cancelled.finished_success)
    cancelled_error_spy = QSignalSpy(cancelled.finished_error)

    cancelled.cancel()
    cancelled._finish()
    cancelled._finish("late error")

    assert len(cancelled_success_spy) == 0
    assert len(cancelled_error_spy) == 0


def test_pai_cancel_waits_for_started_fetch_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = PaiApiRefreshWorker(cast(Any, object()))
    started = Event()
    release = Event()
    generator_closed = Event()

    def fetch_preview(_request: Any) -> Any:
        started.set()
        assert release.wait(2.0)
        return object()

    monkeypatch.setattr(worker, "_fetch_sector_preview", fetch_preview)
    previews = worker._collect_sector_previews([cast(Any, object())])
    next(previews)
    assert started.wait(1.0)

    worker.cancel()

    def close_generator() -> None:
        previews.close()
        generator_closed.set()

    closer = Thread(target=close_generator)
    closer.start()
    assert not generator_closed.wait(0.05)

    release.set()
    assert generator_closed.wait(1.0)
    closer.join(timeout=1.0)
    assert closer.is_alive() is False


def test_pai_controller_releases_worker_only_on_native_finished() -> None:
    signals = {
        name: _Signal()
        for name in (
            "output_line",
            "error_line",
            "progress",
            "preview_ready",
            "import_decision_required",
            "finished_success",
            "finished_error",
            "finished",
        )
    }
    worker = SimpleNamespace(**signals)
    active: list[Any | None] = [worker]
    statuses: list[str] = []
    window = SimpleNamespace(
        active_pai_api_worker=lambda: active[0],
        set_active_pai_api_worker=lambda value: active.__setitem__(0, value) or True,
        set_pai_api_status=statuses.append,
    )

    _connect_worker(
        cast(Any, window),
        cast(Any, worker),
        qmessagebox=object(),
        reload_after_success=False,
    )

    worker.finished_error.emit("expected failure")
    assert active[0] is worker

    worker.finished.emit()
    assert active[0] is None
    assert statuses[-1].startswith("Status: Falha na SAM API")
