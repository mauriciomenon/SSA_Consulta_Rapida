from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest


class _StateSink:
    def __init__(self):
        self.calls = []
        self.text = None
        self.visible = None
        self.enabled = None

    def setText(self, value):
        self.calls.append(("setText", value))
        self.text = value

    def setVisible(self, value):
        self.calls.append(("setVisible", bool(value)))
        self.visible = bool(value)

    def setEnabled(self, value):
        self.calls.append(("setEnabled", bool(value)))
        self.enabled = bool(value)


class _DummyTimer:
    def stop(self):
        return None


class _ShowRecorder:
    def __init__(self) -> None:
        self.calls = 0
        self.visible = False

    def __call__(self) -> None:
        self.calls += 1
        self.visible = True


def _pytest_fail_qmessagebox(*_args, **_kwargs) -> None:
    pytest.fail("QMessageBox.critical called")


def _dummy_noop(*_args, **_kwargs) -> None:
    return None


def _visible_false() -> bool:
    return False


class _LoadDataDummy:
    def __init__(self) -> None:
        self.status_label = _StateSink()
        self.progress_bar = _StateSink()
        self.load_button = _StateSink()
        self.search_button = _StateSink()
        self._debounce_timer = _DummyTimer()
        self._data_load_request_seq = 0
        self._active_data_load_request_id = None
        self.data_loader_thread = None

    def _invalidate_active_filter_request(self, *_args, **_kwargs) -> None:
        return None

    def _cancel_active_filter_worker(self, *_args, **_kwargs) -> None:
        return None


class _StartupShowDummy:
    def __init__(self, recorder: _ShowRecorder) -> None:
        self._startup_show_pending = True
        self.show = recorder

    def isVisible(self) -> bool:
        return False

    def _refresh_quick_setor_executor_options(self) -> None:
        return None

    def _refresh_quick_situacao_buttons(self) -> None:
        return None

    def _sync_quick_setor_executor_combo_from_filters(self) -> None:
        return None

    def _sync_advanced_executor_ui_from_active_filter(self) -> None:
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
        _pytest_fail_qmessagebox,
    )

    dummy = cast(Any, _LoadDataDummy())

    gui_ssa.SSAMainWindow.load_data(dummy)

    assert dummy.status_label.text == "Status: Erro ao carregar dados."
    assert dummy.progress_bar.visible is False
    assert dummy.load_button.enabled is True
    assert dummy.search_button.enabled is True


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
        _pytest_fail_qmessagebox,
    )

    dummy = cast(Any, _LoadDataDummy())

    gui_ssa.SSAMainWindow.load_data(dummy)

    assert dummy.status_label.text == "Status: Erro ao carregar dados."
    assert dummy.progress_bar.visible is False
    assert dummy.load_button.enabled is True
    assert dummy.search_button.enabled is True
    assert dummy.data_loader_thread is None


def test_on_data_loaded_shows_hidden_startup_window_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui import gui_ssa
    from gui.ssa import gui_workers as ssa_gui_workers

    recorder = _ShowRecorder()

    def fake_worker_on_data_loaded(window, payload, request_id=None):  # noqa: ANN001,ARG001
        return None

    monkeypatch.setattr(
        ssa_gui_workers,
        "on_data_loaded",
        fake_worker_on_data_loaded,
    )

    dummy = cast(Any, _StartupShowDummy(recorder))

    gui_ssa.SSAMainWindow.on_data_loaded(dummy, pd.DataFrame())

    assert recorder.calls == 1
    assert getattr(dummy, "_startup_show_pending") is False


def test_on_load_error_shows_hidden_startup_window_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui import gui_ssa
    from gui.ssa import gui_workers as ssa_gui_workers

    recorder = _ShowRecorder()

    def fake_worker_on_load_error(
        window,
        error_msg,
        request_id=None,
        db_path=None,
        qmessagebox=None,
        sip_module=None,
        **kwargs,
    ):  # noqa: ANN001,ARG001
        return None

    monkeypatch.setattr(
        ssa_gui_workers,
        "on_load_error",
        fake_worker_on_load_error,
    )

    dummy = cast(Any, _StartupShowDummy(recorder))

    gui_ssa.SSAMainWindow.on_load_error(dummy, "boom")

    assert recorder.calls == 1
    assert getattr(dummy, "_startup_show_pending") is False


def test_refresh_data_from_api_forces_consulta_scope_without_mutating_preferences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gui import gui_ssa

    original_preferences = gui_ssa.copy.deepcopy(gui_ssa.GUI_MAIN_PREFERENCES)
    gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
    gui_settings["pai_api"] = {
        "enabled": True,
        "executor_sectors": ["IEE3"],
        "data_scopes": ["consulta", "executadas"],
    }
    captured: dict[str, Any] = {}

    def fake_start(window, *, preferences, context, ask_reload=True, reload_after_success=None, **_kwargs):  # noqa: ANN001
        captured["window"] = window
        captured["preferences"] = preferences
        captured["context"] = context
        captured["ask_reload"] = ask_reload
        captured["reload_after_success"] = reload_after_success
        return "started"

    class _ApiDummy:
        def _pai_api_refresh_context(self) -> str:
            return "ctx"

    monkeypatch.setattr(
        gui_ssa.ssa_pai_api_controller,
        "start_pai_api_refresh",
        fake_start,
    )

    try:
        result = gui_ssa.SSAMainWindow.refresh_data_from_api(cast(Any, _ApiDummy()))
    finally:
        gui_ssa.GUI_MAIN_PREFERENCES.clear()
        gui_ssa.GUI_MAIN_PREFERENCES.update(original_preferences)

    assert result == "started"
    assert captured["context"] == "ctx"
    assert captured["ask_reload"] is False
    assert captured["reload_after_success"] is True
    assert captured["preferences"]["gui_settings"]["pai_api"]["data_scopes"] == [
        "consulta"
    ]
    assert gui_settings["pai_api"]["data_scopes"] == ["consulta", "executadas"]
