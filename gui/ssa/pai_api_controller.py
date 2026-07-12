"""GUI orchestration for PAI API refresh."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Protocol

from core.pai_api_options import (
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
    PAI_API_DATA_SCOPES_KEY,
    PAI_API_SECTORS_KEY,
    PAI_API_SETTINGS_KEY,
    normalize_pai_api_options,
    pai_api_options_error,
    update_pai_api_boolean_setting,
    update_pai_api_data_scope_setting,
    update_pai_api_sector_setting,
)
from gui.ssa.pai_api_status_text import trim_pai_api_status_detail
from gui.workers.pai_api_worker import (
    PaiApiRefreshWorker,
    PaiApiWorkerConfig,
    format_decision_request_status,
    format_preview_status,
)
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

STATUS_API_DISABLED = "Status: SAM API desabilitada nas opcoes."
STATUS_API_SCRAP_DISABLED = "Status: Acesso via xpath/scrap_report desabilitado."
STATUS_API_NO_SECTORS = "Status: Nenhum setor executor habilitado para SAM API."
STATUS_API_RUNNING = "Status: SAM API em andamento."
STATUS_API_ALREADY_RUNNING = "Status: SAM API ja esta em andamento."
STATUS_API_KEEP_CURRENT = "Status: SAM API concluida; dados atuais mantidos na tela."
STATUS_API_RELOAD = "Status: SAM API concluida; carregando dados atualizados."
STATUS_API_AUTO_ENABLED = "Status: Atualizacao automatica da SAM API habilitada."
STATUS_API_AUTO_DISABLED = "Status: Atualizacao automatica da SAM API desabilitada."
STATUS_API_AUTO_NOT_READY = "Status: Atualizacao automatica da SAM API nao esta pronta."
STATUS_API_SAVE_FAILED = "Status: Preferencias da SAM API nao foram salvas."


@dataclass(frozen=True)
class PaiApiRefreshContext:
    project_root: str
    docs_dir: str
    db_path: str
    output_dir: str
    qmessagebox: Any


class PaiApiSignal(Protocol):
    def connect(self, callback: Any) -> None: ...


class PaiApiTimerPort(Protocol):
    timeout: PaiApiSignal

    def setSingleShot(self, value: bool) -> None: ...
    def setInterval(self, value: int) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def isActive(self) -> bool: ...


class PaiApiWorkerPort(Protocol):
    output_line: PaiApiSignal
    error_line: PaiApiSignal
    progress: PaiApiSignal
    preview_ready: PaiApiSignal
    import_decision_required: PaiApiSignal
    finished_success: PaiApiSignal
    finished_error: PaiApiSignal

    def start(self) -> None: ...
    def isRunning(self) -> bool: ...
    def set_import_decision(self, approved: bool) -> None: ...


class PaiApiWindowPort(Protocol):
    def pai_api_preferences(self) -> dict[str, Any]: ...
    def pai_api_refresh_context(self) -> PaiApiRefreshContext: ...
    def set_pai_api_status(self, text: str) -> None: ...
    def active_pai_api_worker(self) -> PaiApiWorkerPort | None: ...
    def set_active_pai_api_worker(self, worker: PaiApiWorkerPort | None) -> bool: ...
    def active_pai_api_timer(self) -> PaiApiTimerPort | None: ...
    def set_active_pai_api_timer(self, timer: PaiApiTimerPort | None) -> None: ...
    def reload_pai_api_data(self) -> None: ...
    def confirm_pai_api_import(self, qmessagebox: Any, decision_request: Any) -> bool: ...
    def _persist_gui_preferences(self) -> bool: ...


def set_pai_api_boolean_option(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    key: str,
    enabled: bool,
) -> bool:
    settings = preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY, {}
    )
    previous_missing = key not in settings
    previous_value = settings.get(key)
    update_pai_api_boolean_setting(preferences, key, enabled)
    persisted, _active = _persist_and_sync(window, preferences)
    if not persisted:
        if previous_missing:
            settings.pop(key, None)
        else:
            settings[key] = previous_value
        sync_pai_api_auto_refresh(window, preferences=preferences)
        window.set_pai_api_status(STATUS_API_SAVE_FAILED)
    return persisted


def set_pai_api_sector_enabled(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    sector: str,
    enabled: bool,
) -> bool:
    clean_sector = str(sector or "").strip().upper()
    settings = preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY, {}
    )
    previous_missing = PAI_API_SECTORS_KEY not in settings
    raw_previous_sectors = settings.get(PAI_API_SECTORS_KEY)
    previous_sectors = (
        list(raw_previous_sectors)
        if isinstance(raw_previous_sectors, list)
        else raw_previous_sectors
    )
    if not update_pai_api_sector_setting(preferences, clean_sector, enabled):
        window.set_pai_api_status(f"Status: Setor SAM API invalido: {clean_sector}")
        return False
    persisted, _active = _persist_and_sync(window, preferences)
    if not persisted:
        if previous_missing:
            settings.pop(PAI_API_SECTORS_KEY, None)
        else:
            settings[PAI_API_SECTORS_KEY] = previous_sectors
        sync_pai_api_auto_refresh(window, preferences=preferences)
        window.set_pai_api_status(STATUS_API_SAVE_FAILED)
    return persisted


def set_pai_api_data_scope_enabled(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    scope: str,
    enabled: bool,
) -> bool:
    clean_scope = str(scope or "").strip().casefold()
    settings = preferences.setdefault("gui_settings", {}).setdefault(
        PAI_API_SETTINGS_KEY, {}
    )
    previous_missing = PAI_API_DATA_SCOPES_KEY not in settings
    raw_previous_scopes = settings.get(PAI_API_DATA_SCOPES_KEY)
    previous_scopes = (
        list(raw_previous_scopes)
        if isinstance(raw_previous_scopes, list)
        else raw_previous_scopes
    )
    if not update_pai_api_data_scope_setting(preferences, clean_scope, enabled):
        window.set_pai_api_status(f"Status: Tipo SAM API invalido: {clean_scope}")
        return False
    persisted, _active = _persist_and_sync(window, preferences)
    if not persisted:
        if previous_missing:
            settings.pop(PAI_API_DATA_SCOPES_KEY, None)
        else:
            settings[PAI_API_DATA_SCOPES_KEY] = previous_scopes
        sync_pai_api_auto_refresh(window, preferences=preferences)
        window.set_pai_api_status(STATUS_API_SAVE_FAILED)
    return persisted


def start_pai_api_refresh(
    window: PaiApiWindowPort,
    *,
    preferences: dict[str, Any],
    context: PaiApiRefreshContext,
    worker_cls: Any = PaiApiRefreshWorker,
    ask_reload: bool = True,
    reload_after_success: bool | None = None,
    quiet_if_running: bool = False,
) -> bool:
    settings = preferences.get("gui_settings", {}).get(PAI_API_SETTINGS_KEY, {})
    options = normalize_pai_api_options(settings)
    options_error = pai_api_options_error(options)
    if options_error is not None:
        window.set_pai_api_status(_status_for_options_error(options_error))
        return False

    active_worker = window.active_pai_api_worker()
    if active_worker is not None and _worker_is_running(active_worker):
        if not quiet_if_running:
            window.set_pai_api_status(STATUS_API_ALREADY_RUNNING)
        return False

    should_reload = True if reload_after_success is None else reload_after_success
    worker = worker_cls(
        PaiApiWorkerConfig(
            project_root=Path(context.project_root),
            docs_dir=Path(context.docs_dir),
            db_path=Path(context.db_path),
            output_dir=Path(context.output_dir),
            options=options,
            confirm_before_import=ask_reload,
            fetch_only=not (ask_reload or should_reload),
        )
    )
    reset_for_start = getattr(worker, "reset_for_start", None)
    if callable(reset_for_start):
        reset_for_start()
    if not window.set_active_pai_api_worker(worker):
        return False
    _connect_worker(
        window,
        worker,
        qmessagebox=context.qmessagebox,
        reload_after_success=should_reload,
    )
    worker.start()
    window.set_pai_api_status(STATUS_API_RUNNING)
    return True


def initialize_pai_api_auto_refresh(
    window: PaiApiWindowPort,
    *,
    preferences: dict[str, Any],
    context: PaiApiRefreshContext,
    qtimer_cls: Any,
    worker_cls: Any = PaiApiRefreshWorker,
) -> bool:
    timer = window.active_pai_api_timer()
    if timer is None:
        timer = qtimer_cls(window)
        timer.setSingleShot(False)
        timer.timeout.connect(partial(_run_auto_refresh_timeout, window, worker_cls))
        window.set_active_pai_api_timer(timer)
    return sync_pai_api_auto_refresh(window, preferences=preferences)


def sync_pai_api_auto_refresh(
    window: PaiApiWindowPort,
    *,
    preferences: dict[str, Any],
) -> bool:
    timer = window.active_pai_api_timer()
    if timer is None:
        return False
    settings = preferences.get("gui_settings", {}).get(PAI_API_SETTINGS_KEY, {})
    options = normalize_pai_api_options(settings)
    interval_ms = options.auto_refresh_interval_minutes * 60 * 1000
    should_run = (
        options.enabled
        and options.scrap_report_enabled
        and options.auto_refresh_enabled
        and bool(options.all_executor_sectors)
    )
    if should_run:
        timer.setInterval(interval_ms)
        if not timer.isActive():
            timer.start()
        return True
    if timer.isActive():
        timer.stop()
    return False


def _connect_worker(
    window: PaiApiWindowPort,
    worker: PaiApiRefreshWorker,
    *,
    qmessagebox: Any,
    reload_after_success: bool,
) -> None:
    worker.output_line.connect(_log_worker_output)
    worker.error_line.connect(_log_worker_error)
    worker.progress.connect(partial(_set_worker_progress, window))
    worker.preview_ready.connect(partial(_set_worker_preview_status, window))
    worker.import_decision_required.connect(
        partial(_confirm_worker_import, window, worker, qmessagebox=qmessagebox)
    )
    worker.finished_success.connect(
        partial(
            _finish_success,
            window,
            worker,
            qmessagebox=qmessagebox,
            reload_after_success=reload_after_success,
        )
    )
    worker.finished_error.connect(partial(_finish_error, window, worker))


def _run_auto_refresh_timeout(
    window: PaiApiWindowPort,
    worker_cls: Any,
) -> bool:
    return start_pai_api_refresh(
        window,
        preferences=window.pai_api_preferences(),
        context=window.pai_api_refresh_context(),
        worker_cls=worker_cls,
        ask_reload=False,
        reload_after_success=True,
        quiet_if_running=True,
    )


def _log_worker_output(text: str, *_args: Any) -> None:
    logger.debug("SAM API worker output: %s", trim_pai_api_status_detail(text))


def _log_worker_error(text: str, *_args: Any) -> None:
    logger.debug("SAM API worker error: %s", trim_pai_api_status_detail(text))


def _set_worker_progress(
    window: PaiApiWindowPort,
    _percent: int,
    message: str,
    *_args: Any,
) -> None:
    window.set_pai_api_status(f"Status: {message}")


def _set_worker_preview_status(
    window: PaiApiWindowPort,
    preview: Any,
    *_args: Any,
) -> None:
    window.set_pai_api_status(f"Status: {format_preview_status(preview)}")


def _confirm_worker_import(
    window: PaiApiWindowPort,
    worker: PaiApiWorkerPort,
    decision_request: Any,
    *_args: Any,
    qmessagebox: Any,
) -> None:
    window.set_pai_api_status(f"Status: {format_decision_request_status(decision_request)}")
    worker.set_import_decision(window.confirm_pai_api_import(qmessagebox, decision_request))


def _finish_success(
    window: PaiApiWindowPort,
    worker: Any,
    *,
    qmessagebox: Any,
    reload_after_success: bool,
) -> None:
    partial_status = _worker_partial_status(worker)
    try:
        if _worker_import_skipped(worker):
            window.set_pai_api_status(partial_status or STATUS_API_KEEP_CURRENT)
            return
        if reload_after_success:
            window.set_pai_api_status(partial_status or STATUS_API_RELOAD)
            window.reload_pai_api_data()
            return
        window.set_pai_api_status(partial_status or STATUS_API_KEEP_CURRENT)
    finally:
        if window.active_pai_api_worker() is worker:
            window.set_active_pai_api_worker(None)


def _finish_error(
    window: PaiApiWindowPort,
    worker: Any,
    message: str,
) -> None:
    if window.active_pai_api_worker() is worker:
        window.set_active_pai_api_worker(None)
    short_message = _short_error_message(message)
    logger.warning("Falha na SAM API: %s", short_message)
    if short_message != message:
        logger.debug("Falha detalhada na SAM API: %s", message)
    window.set_pai_api_status(f"Status: Falha na SAM API: {short_message}")


def _worker_is_running(worker: Any) -> bool:
    is_running = getattr(worker, "isRunning", None)
    if not callable(is_running):
        return False
    try:
        return bool(is_running())
    except RuntimeError as exc:
        logger.debug("Falha ao consultar worker PAI ativo: %s", exc)
        return False


def _status_for_options_error(message: str) -> str:
    if message == "SAM API desabilitada nas opcoes.":
        return STATUS_API_DISABLED
    if message == "Acesso via xpath/scrap_report desabilitado nas opcoes.":
        return STATUS_API_SCRAP_DISABLED
    if message == "Nenhum setor executor habilitado para SAM API.":
        return STATUS_API_NO_SECTORS
    return f"Status: {message}"


def _short_error_message(
    message: str,
    *,
    max_length: int | None = None,
) -> str:
    if max_length is None:
        return trim_pai_api_status_detail(message)
    return trim_pai_api_status_detail(message, max_length=max_length)


def _worker_partial_status(worker: Any) -> str | None:
    summary_fn = getattr(worker, "summary", None)
    if not callable(summary_fn):
        return None
    summary = summary_fn()
    if summary is None:
        return None
    failed_count = int(getattr(summary, "failed_sectors", 0))
    if failed_count <= 0:
        return None
    imported_count = int(getattr(summary, "imported_sectors", 0))
    return (
        "Status: SAM API parcial; "
        f"{imported_count} setores importados; {failed_count} falharam."
    )


def _worker_import_skipped(worker: Any) -> bool:
    summary_fn = getattr(worker, "summary", None)
    if not callable(summary_fn):
        return False
    summary = summary_fn()
    if summary is None:
        return False
    return bool(getattr(summary, "import_skipped", False))


def set_pai_api_auto_refresh_enabled(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    enabled: bool,
) -> bool:
    settings = preferences.get("gui_settings", {}).get(PAI_API_SETTINGS_KEY, {})
    previous_enabled = bool(settings.get(PAI_API_AUTO_REFRESH_ENABLED_KEY, False))
    update_pai_api_boolean_setting(
        preferences,
        PAI_API_AUTO_REFRESH_ENABLED_KEY,
        enabled,
    )
    persisted = _persist_preferences(window)
    if not persisted:
        update_pai_api_boolean_setting(
            preferences,
            PAI_API_AUTO_REFRESH_ENABLED_KEY,
            previous_enabled,
        )
        sync_pai_api_auto_refresh(window, preferences=preferences)
        window.set_pai_api_status(STATUS_API_SAVE_FAILED)
        return False
    else:
        active = sync_pai_api_auto_refresh(window, preferences=preferences)
    if enabled:
        window.set_pai_api_status(
            STATUS_API_AUTO_ENABLED
            if persisted and active
            else STATUS_API_AUTO_NOT_READY
        )
        return persisted
    else:
        window.set_pai_api_status(
            STATUS_API_AUTO_DISABLED if persisted else STATUS_API_AUTO_NOT_READY
        )
    return persisted


def _persist_preferences(window: PaiApiWindowPort) -> bool:
    return bool(window._persist_gui_preferences())


def _persist_and_sync(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
) -> tuple[bool, bool]:
    persisted = _persist_preferences(window)
    active = sync_pai_api_auto_refresh(window, preferences=preferences)
    return persisted, active


__all__ = [
    "PaiApiRefreshContext",
    "initialize_pai_api_auto_refresh",
    "set_pai_api_auto_refresh_enabled",
    "set_pai_api_boolean_option",
    "set_pai_api_data_scope_enabled",
    "set_pai_api_sector_enabled",
    "sync_pai_api_auto_refresh",
    "start_pai_api_refresh",
]
