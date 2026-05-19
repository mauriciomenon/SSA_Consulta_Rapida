"""GUI orchestration for PAI API refresh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from core.pai_api_options import (
    PAI_API_AUTO_REFRESH_ENABLED_KEY,
    PAI_API_SETTINGS_KEY,
    normalize_pai_api_options,
    pai_api_options_error,
    update_pai_api_boolean_setting,
    update_pai_api_sector_setting,
)
from gui.workers.pai_api_worker import PaiApiRefreshWorker, PaiApiWorkerConfig
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

STATUS_API_DISABLED = "Status: API PAI desabilitada nas opcoes."
STATUS_API_SCRAP_DISABLED = "Status: Busca via scrap_report desabilitada nas opcoes."
STATUS_API_NO_SECTORS = "Status: Nenhum setor executor habilitado para API PAI."
STATUS_API_RUNNING = "Status: API PAI em andamento."
STATUS_API_ALREADY_RUNNING = "Status: API PAI ja esta em andamento."
STATUS_API_KEEP_CURRENT = "Status: API PAI concluida; dados atuais mantidos na tela."
STATUS_API_RELOAD = "Status: API PAI concluida; carregando dados atualizados."
STATUS_API_AUTO_ENABLED = "Status: Atualizacao automatica da API PAI habilitada."
STATUS_API_AUTO_DISABLED = "Status: Atualizacao automatica da API PAI desabilitada."
STATUS_API_AUTO_NOT_READY = "Status: Atualizacao automatica da API PAI nao esta pronta."


@dataclass(frozen=True)
class PaiApiRefreshContext:
    project_root: str
    docs_dir: str
    db_path: str
    qmessagebox: Any


class PaiApiWindowPort(Protocol):
    def pai_api_preferences(self) -> dict[str, Any]: ...
    def pai_api_refresh_context(self) -> PaiApiRefreshContext: ...
    def set_pai_api_status(self, text: str) -> None: ...
    def active_pai_api_worker(self) -> Any: ...
    def set_active_pai_api_worker(self, worker: Any | None) -> None: ...
    def active_pai_api_timer(self) -> Any: ...
    def set_active_pai_api_timer(self, timer: Any | None) -> None: ...
    def reload_pai_api_data(self) -> None: ...
    def confirm_pai_api_reload(self, qmessagebox: Any) -> bool: ...
    def _persist_gui_preferences(self) -> bool: ...


def set_pai_api_boolean_option(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    key: str,
    enabled: bool,
) -> bool:
    update_pai_api_boolean_setting(preferences, key, enabled)
    persisted, _active = _persist_and_sync(window, preferences)
    return persisted


def set_pai_api_sector_enabled(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    sector: str,
    enabled: bool,
) -> bool:
    clean_sector = str(sector or "").strip().upper()
    if not update_pai_api_sector_setting(preferences, clean_sector, enabled):
        window.set_pai_api_status(f"Status: Setor API PAI invalido: {clean_sector}")
        return False
    persisted, _active = _persist_and_sync(window, preferences)
    return persisted


def start_pai_api_refresh(
    window: PaiApiWindowPort,
    *,
    preferences: dict[str, Any],
    context: PaiApiRefreshContext,
    worker_cls: Any = PaiApiRefreshWorker,
    ask_reload: bool = True,
) -> bool:
    settings = preferences.get("gui_settings", {}).get(PAI_API_SETTINGS_KEY, {})
    options = normalize_pai_api_options(settings)
    options_error = pai_api_options_error(options)
    if options_error is not None:
        window.set_pai_api_status(_status_for_options_error(options_error))
        return False

    active_worker = window.active_pai_api_worker()
    if active_worker is not None and _worker_is_running(active_worker):
        window.set_pai_api_status(STATUS_API_ALREADY_RUNNING)
        return False

    output_dir = Path(context.project_root) / "tmp" / "pai_api_gui"
    worker = worker_cls(
        PaiApiWorkerConfig(
            project_root=Path(context.project_root),
            docs_dir=Path(context.docs_dir),
            db_path=Path(context.db_path),
            output_dir=output_dir,
            options=options,
        )
    )
    window.set_active_pai_api_worker(worker)
    _connect_worker(
        window,
        worker,
        qmessagebox=context.qmessagebox,
        ask_reload=ask_reload,
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
        timer.timeout.connect(
            lambda: start_pai_api_refresh(
                window,
                preferences=window.pai_api_preferences(),
                context=window.pai_api_refresh_context(),
                worker_cls=worker_cls,
                ask_reload=False,
            )
        )
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
        and bool(options.executor_sectors)
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
    ask_reload: bool,
) -> None:
    worker.output_line.connect(lambda text, *_args: logger.info("%s", text))
    worker.error_line.connect(lambda text, *_args: logger.warning("%s", text))
    worker.progress.connect(
        lambda _percent, message, *_args: window.set_pai_api_status(
            f"Status: {message}"
        )
    )
    worker.finished_success.connect(
        lambda: _finish_success(
            window,
            worker,
            qmessagebox=qmessagebox,
            ask_reload=ask_reload,
        )
    )
    worker.finished_error.connect(lambda message: _finish_error(window, worker, message))


def _finish_success(
    window: PaiApiWindowPort,
    worker: Any,
    *,
    qmessagebox: Any,
    ask_reload: bool,
) -> None:
    if window.active_pai_api_worker() is worker:
        window.set_active_pai_api_worker(None)
    if ask_reload and window.confirm_pai_api_reload(qmessagebox):
        window.set_pai_api_status(STATUS_API_RELOAD)
        window.reload_pai_api_data()
        return
    window.set_pai_api_status(STATUS_API_KEEP_CURRENT)


def _finish_error(
    window: PaiApiWindowPort,
    worker: Any,
    message: str,
) -> None:
    if window.active_pai_api_worker() is worker:
        window.set_active_pai_api_worker(None)
    logger.warning("Falha na API PAI: %s", message)
    window.set_pai_api_status(f"Status: Falha na API PAI: {_short_error_message(message)}")


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
    if message == "API PAI desabilitada nas opcoes.":
        return STATUS_API_DISABLED
    if message == "Busca via scrap_report desabilitada nas opcoes.":
        return STATUS_API_SCRAP_DISABLED
    if message == "Nenhum setor executor habilitado para API PAI.":
        return STATUS_API_NO_SECTORS
    return f"Status: {message}"


def _short_error_message(message: str, *, max_length: int = 88) -> str:
    text = " ".join(str(message or "").split())
    if not text:
        return "erro sem detalhe"
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def set_pai_api_auto_refresh_enabled(
    window: PaiApiWindowPort,
    preferences: dict[str, Any],
    enabled: bool,
) -> bool:
    update_pai_api_boolean_setting(
        preferences,
        PAI_API_AUTO_REFRESH_ENABLED_KEY,
        enabled,
    )
    persisted, active = _persist_and_sync(window, preferences)
    if enabled:
        window.set_pai_api_status(
            STATUS_API_AUTO_ENABLED if active else STATUS_API_AUTO_NOT_READY
        )
    else:
        window.set_pai_api_status(STATUS_API_AUTO_DISABLED)
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
    "set_pai_api_sector_enabled",
    "sync_pai_api_auto_refresh",
    "start_pai_api_refresh",
]
