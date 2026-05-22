from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest


class _StateSink:
    def __init__(self):
        self.calls = []
        self.value = None

    def setText(self, value):
        self.calls.append(("setText", value))
        self.value = value

    def setVisible(self, value):
        self.calls.append(("setVisible", bool(value)))
        self.value = bool(value)

    def setEnabled(self, value):
        self.calls.append(("setEnabled", bool(value)))
        self.value = bool(value)


class _DummyTimer:
    def stop(self):
        return None


def test_load_data_skips_modal_when_loader_missing_under_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gui import gui_ssa

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    db_path = tmp_path / "ssas.db"
    db_path.write_bytes(b"dummy")

    monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_path))
    monkeypatch.setattr(gui_ssa, "DataLoaderWorker", None)
    monkeypatch.setattr(
        gui_ssa.QMessageBox,
        "critical",
        lambda *a, **k: pytest.fail("QMessageBox.critical called"),
    )

    dummy = cast(Any, SimpleNamespace())
    dummy.status_label = _StateSink()
    dummy.progress_bar = _StateSink()
    dummy.load_button = _StateSink()
    dummy.search_button = _StateSink()
    dummy._debounce_timer = _DummyTimer()
    dummy._data_load_request_seq = 0
    dummy._active_data_load_request_id = None
    dummy.data_loader_thread = None

    dummy._invalidate_active_filter_request = lambda *a, **k: None
    dummy._cancel_active_filter_worker = lambda *a, **k: None

    gui_ssa.SSAMainWindow.load_data(dummy)

    assert dummy.status_label.value == "Status: Erro ao carregar dados."
    assert dummy.progress_bar.value is False
    assert dummy.load_button.value is True
    assert dummy.search_button.value is True


def test_load_data_handles_loader_constructor_failure_under_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gui import gui_ssa

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    db_path = tmp_path / "ssas.db"
    db_path.write_bytes(b"dummy")

    class _BrokenLoader:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError(f"cannot open {db_path}")

    monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_path))
    monkeypatch.setattr(gui_ssa, "DataLoaderWorker", _BrokenLoader)
    monkeypatch.setattr(
        gui_ssa.QMessageBox,
        "critical",
        lambda *a, **k: pytest.fail("QMessageBox.critical called"),
    )

    dummy = cast(Any, SimpleNamespace())
    dummy.status_label = _StateSink()
    dummy.progress_bar = _StateSink()
    dummy.load_button = _StateSink()
    dummy.search_button = _StateSink()
    dummy._debounce_timer = _DummyTimer()
    dummy._data_load_request_seq = 0
    dummy._active_data_load_request_id = None
    dummy.data_loader_thread = None

    dummy._invalidate_active_filter_request = lambda *a, **k: None
    dummy._cancel_active_filter_worker = lambda *a, **k: None

    gui_ssa.SSAMainWindow.load_data(dummy)

    assert dummy.status_label.value == "Status: Erro ao carregar dados."
    assert dummy.progress_bar.value is False
    assert dummy.load_button.value is True
    assert dummy.search_button.value is True
    assert dummy.data_loader_thread is None
