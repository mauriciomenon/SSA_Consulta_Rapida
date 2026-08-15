from __future__ import annotations

from pathlib import Path
from typing import Any

import logging
import pytest

from core.pai_api_options import (
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
    PAI_API_DATA_SCOPES_KEY,
    PAI_API_ENABLED_KEY,
    PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES,
    PAI_API_SECTORS_KEY,
    PAI_API_SETTINGS_KEY,
)
from gui.ssa import pai_api_controller


class _Signal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        for callback in list(self._callbacks):
            callback(*args)


class _Timer:
    instances: list["_Timer"] = []

    def __init__(self, _parent: Any = None) -> None:
        self.timeout = _Signal()
        self.interval = 0
        self.single_shot = True
        self.active = False
        type(self).instances.append(self)

    def setSingleShot(self, value: bool) -> None:
        self.single_shot = bool(value)

    def setInterval(self, value: int) -> None:
        self.interval = int(value)

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


class _Window:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.worker: Any | None = None
        self.timer: Any | None = None
        self.preferences: dict[str, Any] = {}
        self.context: pai_api_controller.PaiApiRefreshContext | None = None
        self.persist_count = 0
        self.persist_result = True
        self.reload_count = 0
        self.confirm_count = 0
        self.last_decision_request: Any | None = None
        self.accept_workers = True

    def pai_api_preferences(self) -> dict[str, Any]:
        return self.preferences

    def pai_api_refresh_context(self) -> pai_api_controller.PaiApiRefreshContext:
        if self.context is None:
            raise AssertionError("pai api context not configured")
        return self.context

    def set_pai_api_status(self, text: str) -> None:
        self.statuses.append(text)

    def active_pai_api_worker(self) -> Any:
        return self.worker

    def set_active_pai_api_worker(self, worker: Any | None) -> bool:
        if worker is not None and not self.accept_workers:
            return False
        self.worker = worker
        return True

    def active_pai_api_timer(self) -> Any:
        return self.timer

    def set_active_pai_api_timer(self, timer: Any | None) -> None:
        self.timer = timer

    def reload_pai_api_data(self) -> None:
        self.reload_count += 1

    def confirm_pai_api_import(self, qmessagebox: Any, decision_request: Any) -> bool:
        _ = qmessagebox
        self.confirm_count += 1
        self.last_decision_request = decision_request
        return True

    def _persist_gui_preferences(self) -> bool:
        self.persist_count += 1
        return self.persist_result


class _Worker:
    def __init__(self, _config: Any) -> None:
        self.config = _config
        self.output_line = _Signal()
        self.error_line = _Signal()
        self.progress = _Signal()
        self.preview_ready = _Signal()
        self.import_decision_required = _Signal()
        self.finished_success = _Signal()
        self.finished_error = _Signal()
        self.finished = _Signal()
        self.started = False
        self.import_decision: bool | None = None

    def start(self) -> None:
        self.started = True

    def isRunning(self) -> bool:
        return self.started

    def set_import_decision(self, approved: bool) -> None:
        self.import_decision = bool(approved)


class _WorkerWithEmptySummary(_Worker):
    def summary(self) -> None:
        return None


def test_refresh_does_not_start_worker_when_ownership_is_rejected(
    tmp_path: Path,
) -> None:
    created_workers = []

    class _RejectedWorker(_Worker):
        def __init__(self, config: Any) -> None:
            super().__init__(config)
            created_workers.append(self)

    window = _Window()
    window.accept_workers = False
    preferences = _preferences(auto_enabled=False)

    assert not pai_api_controller.start_pai_api_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        worker_cls=_RejectedWorker,
    )

    assert window.worker is None
    assert len(created_workers) == 1
    assert created_workers[0].started is False


@pytest.fixture(autouse=True)
def _reset_timer_instances() -> None:
    _Timer.instances.clear()


def test_status_for_options_error_maps_xpath_disabled_message() -> None:
    assert (
        pai_api_controller._status_for_options_error(
            "Acesso via xpath/scrap_report desabilitado nas opcoes."
        )
        == "Status: Acesso via xpath/scrap_report desabilitado."
    )


def test_auto_refresh_timer_starts_when_enabled(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=True)
    window.preferences = preferences
    window.context = _context(tmp_path)

    assert pai_api_controller.initialize_pai_api_auto_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        qtimer_cls=_Timer,
    )

    assert window.timer is not None
    timer = window.timer
    assert timer.interval == PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES * 60 * 1000
    assert timer.isActive() is True


def test_auto_refresh_timeout_starts_worker_without_reload_prompt(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=True)
    window.preferences = preferences
    window.context = _context(tmp_path)
    pai_api_controller.initialize_pai_api_auto_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        qtimer_cls=_Timer,
        worker_cls=_Worker,
    )

    assert window.timer is not None
    timer = window.timer
    timer.timeout.emit()

    assert isinstance(window.worker, _Worker)
    assert window.worker.config.confirm_before_import is False
    assert window.worker.config.fetch_only is False
    window.worker.finished_success.emit()
    assert window.confirm_count == 0
    assert window.reload_count == 1


def test_finish_success_retains_worker_until_native_finished(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)

    assert pai_api_controller.start_pai_api_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        worker_cls=_WorkerWithEmptySummary,
        ask_reload=True,
    )

    assert isinstance(window.worker, _WorkerWithEmptySummary)
    worker = window.worker
    worker.finished_success.emit()

    assert window.worker is worker
    worker.finished.emit()
    assert window.worker is None
    assert window.reload_count == 1


def test_refresh_without_prompt_still_imports_by_default(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)

    assert pai_api_controller.start_pai_api_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        worker_cls=_Worker,
        ask_reload=False,
    )

    assert isinstance(window.worker, _Worker)
    assert window.worker.config.confirm_before_import is False
    assert window.worker.config.fetch_only is False
    window.worker.finished_success.emit()
    assert window.confirm_count == 0
    assert window.reload_count == 1


def test_manual_refresh_decision_imports_after_preview_confirmation(
    tmp_path: Path,
) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)

    assert pai_api_controller.start_pai_api_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        worker_cls=_Worker,
        ask_reload=True,
    )

    assert isinstance(window.worker, _Worker)
    decision_request = type(
        "DecisionRequest",
        (),
        {"normalized_rows": 3, "previewed_sectors": 1, "failed_sectors": 0},
    )()
    window.worker.import_decision_required.emit(decision_request)

    assert window.confirm_count == 1
    assert window.last_decision_request is decision_request
    assert window.worker.import_decision is True


def test_auto_refresh_timeout_does_not_spam_status_when_worker_is_running(
    tmp_path: Path,
) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=True)
    window.preferences = preferences
    window.context = _context(tmp_path)
    pai_api_controller.initialize_pai_api_auto_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        qtimer_cls=_Timer,
        worker_cls=_Worker,
    )

    assert window.timer is not None
    timer = window.timer
    timer.timeout.emit()
    status_count = len(window.statuses)
    timer.timeout.emit()

    assert len(window.statuses) == status_count


def test_set_auto_refresh_enabled_persists_and_starts_timer(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)
    pai_api_controller.initialize_pai_api_auto_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        qtimer_cls=_Timer,
    )

    assert pai_api_controller.set_pai_api_auto_refresh_enabled(
        window,
        preferences,
        True,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_AUTO_REFRESH_ENABLED_KEY] is True
    assert window.persist_count == 1
    assert window.timer is not None
    timer = window.timer
    assert timer.isActive() is True


def test_set_auto_refresh_enabled_persists_even_without_timer(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)

    assert pai_api_controller.set_pai_api_auto_refresh_enabled(
        window,
        preferences,
        True,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_AUTO_REFRESH_ENABLED_KEY] is True
    assert window.persist_count == 1
    assert window.timer is None
    assert window.statuses[-1] == pai_api_controller.STATUS_API_AUTO_NOT_READY


def test_set_boolean_option_rolls_back_when_persist_fails(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    preferences["gui_settings"][PAI_API_SETTINGS_KEY].pop(PAI_API_ENABLED_KEY, None)
    window.preferences = preferences
    window.context = _context(tmp_path)
    window.persist_result = False

    assert not pai_api_controller.set_pai_api_boolean_option(
        window,
        preferences,
        PAI_API_ENABLED_KEY,
        False,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert PAI_API_ENABLED_KEY not in settings
    assert window.statuses[-1] == pai_api_controller.STATUS_API_SAVE_FAILED


def test_set_auto_refresh_enabled_keeps_timer_off_when_persist_fails(
    tmp_path: Path,
) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)
    window.persist_result = False
    pai_api_controller.initialize_pai_api_auto_refresh(
        window,
        preferences=preferences,
        context=_context(tmp_path),
        qtimer_cls=_Timer,
    )

    assert not pai_api_controller.set_pai_api_auto_refresh_enabled(
        window,
        preferences,
        True,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_AUTO_REFRESH_ENABLED_KEY] is False
    assert window.persist_count == 1
    assert window.timer is not None
    assert window.timer.isActive() is False
    assert window.statuses[-1] == pai_api_controller.STATUS_API_SAVE_FAILED


def test_set_sector_enabled_rolls_back_when_persist_fails(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)
    window.persist_result = False
    preferences["gui_settings"][PAI_API_SETTINGS_KEY][PAI_API_SECTORS_KEY] = None

    assert not pai_api_controller.set_pai_api_sector_enabled(
        window,
        preferences,
        "MEL4",
        True,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_SECTORS_KEY] is None
    assert window.statuses[-1] == pai_api_controller.STATUS_API_SAVE_FAILED


def test_set_data_scope_enabled_rolls_back_when_persist_fails(tmp_path: Path) -> None:
    window = _Window()
    preferences = _preferences(auto_enabled=False)
    window.preferences = preferences
    window.context = _context(tmp_path)
    window.persist_result = False
    preferences["gui_settings"][PAI_API_SETTINGS_KEY][PAI_API_DATA_SCOPES_KEY] = None

    assert not pai_api_controller.set_pai_api_data_scope_enabled(
        window,
        preferences,
        "executadas",
        True,
    )

    settings = preferences["gui_settings"][PAI_API_SETTINGS_KEY]
    assert settings[PAI_API_DATA_SCOPES_KEY] is None
    assert window.statuses[-1] == pai_api_controller.STATUS_API_SAVE_FAILED


def test_pai_api_error_status_is_short() -> None:
    window = _Window()
    worker = _Worker(None)
    window.set_active_pai_api_worker(worker)
    long_error = "scrap_report sam-api-flow falhou " + ("x" * 200)

    pai_api_controller._finish_error(window, worker, long_error)

    assert window.worker is worker
    assert len(window.statuses[-1]) <= 120
    assert window.statuses[-1].endswith("...")


def test_pai_api_error_logs_short_warning_and_full_detail(caplog) -> None:
    window = _Window()
    worker = _Worker(None)
    window.set_active_pai_api_worker(worker)
    long_error = "scrap_report sam-api-flow falhou " + ("x" * 200)

    with caplog.at_level(logging.DEBUG, logger="gui.ssa.pai_api_controller"):
        pai_api_controller._finish_error(window, worker, long_error)

    warning_messages = [
        str(record.message)
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    info_messages = [
        str(record.message)
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]

    assert len(warning_messages) == 1
    assert "Falha na SAM API:" in warning_messages[0]
    assert warning_messages[0].endswith("...")
    assert len(info_messages) == 1
    assert info_messages[0] == f"Falha detalhada na SAM API: {long_error}"


def test_pai_api_sector_failure_logs_at_debug(caplog) -> None:
    with caplog.at_level(logging.DEBUG, logger="gui.ssa.pai_api_controller"):
        pai_api_controller._log_worker_error("setor IEE3: falha de teste")

    assert any(
        record.levelno == logging.DEBUG
        and "SAM API worker error: setor IEE3: falha de teste" in str(record.message)
        for record in caplog.records
    )


def _preferences(*, auto_enabled: bool) -> dict[str, Any]:
    return {
        "gui_settings": {
            PAI_API_SETTINGS_KEY: {
                PAI_API_ENABLED_KEY: True,
                PAI_API_AUTO_REFRESH_ENABLED_KEY: auto_enabled,
                PAI_API_SECTORS_KEY: ["IEE3"],
            }
        }
    }


def _context(tmp_path: Path) -> pai_api_controller.PaiApiRefreshContext:
    return pai_api_controller.PaiApiRefreshContext(
        project_root=str(tmp_path),
        docs_dir=str(tmp_path / "docs"),
        db_path=str(tmp_path / "ssas.db"),
        output_dir=str(tmp_path / "pai_api"),
        qmessagebox=None,
    )
