from __future__ import annotations

from pathlib import Path
from typing import Any

from core.pai_api_options import (
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
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
        self.reload_count = 0
        self.confirm_count = 0

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

    def set_active_pai_api_worker(self, worker: Any | None) -> None:
        self.worker = worker

    def active_pai_api_timer(self) -> Any:
        return self.timer

    def set_active_pai_api_timer(self, timer: Any | None) -> None:
        self.timer = timer

    def reload_pai_api_data(self) -> None:
        self.reload_count += 1

    def confirm_pai_api_reload(self, qmessagebox: Any) -> bool:
        _ = qmessagebox
        self.confirm_count += 1
        return True

    def _persist_gui_preferences(self) -> bool:
        self.persist_count += 1
        return True


class _Worker:
    def __init__(self, _config: Any) -> None:
        self.output_line = _Signal()
        self.error_line = _Signal()
        self.progress = _Signal()
        self.preview_ready = _Signal()
        self.finished_success = _Signal()
        self.finished_error = _Signal()
        self.started = False

    def start(self) -> None:
        self.started = True

    def isRunning(self) -> bool:
        return self.started


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
    assert timer.interval == 10 * 60 * 1000
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
    window.worker.finished_success.emit()
    assert window.confirm_count == 0
    assert window.reload_count == 0


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


def test_pai_api_error_status_is_short() -> None:
    window = _Window()
    worker = _Worker(None)
    window.set_active_pai_api_worker(worker)
    long_error = "scrap_report sam-api-flow falhou " + ("x" * 200)

    pai_api_controller._finish_error(window, worker, long_error)

    assert window.worker is None
    assert len(window.statuses[-1]) <= 120
    assert window.statuses[-1].endswith("...")


def _preferences(*, auto_enabled: bool) -> dict[str, Any]:
    return {
        "gui_settings": {
            PAI_API_SETTINGS_KEY: {
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
