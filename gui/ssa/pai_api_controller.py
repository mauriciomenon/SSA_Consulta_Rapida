"""GUI orchestration for PAI API refresh."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from core.pai_api_options import (
    PAI_API_ENABLED_KEY,
    PAI_API_SCRAP_ENABLED_KEY,
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


class PaiApiWindowPort(Protocol):
    def set_pai_api_status(self, text: str) -> None: ...
    def active_pai_api_worker(self) -> Any: ...
    def set_active_pai_api_worker(self, worker: Any | None) -> None: ...
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
    return _persist_preferences(window)


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
    return _persist_preferences(window)


def start_pai_api_refresh(
    window: PaiApiWindowPort,
    *,
    preferences: dict[str, Any],
    project_root: str,
    docs_dir: str,
    db_path: str,
    qmessagebox: Any,
    worker_cls: type[PaiApiRefreshWorker] = PaiApiRefreshWorker,
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

    output_dir = Path(project_root) / "tmp" / "pai_api_gui"
    output_dir.mkdir(parents=True, exist_ok=True)
    worker = worker_cls(
        PaiApiWorkerConfig(
            project_root=Path(project_root),
            docs_dir=Path(docs_dir),
            db_path=Path(db_path),
            output_dir=output_dir,
            options=options,
        )
    )
    window.set_active_pai_api_worker(worker)
    _connect_worker(window, worker, qmessagebox=qmessagebox)
    worker.start()
    window.set_pai_api_status(STATUS_API_RUNNING)
    return True


def _connect_worker(
    window: PaiApiWindowPort,
    worker: PaiApiRefreshWorker,
    *,
    qmessagebox: Any,
) -> None:
    worker.output_line.connect(lambda text, *_args: logger.info("%s", text))
    worker.error_line.connect(lambda text, *_args: logger.warning("%s", text))
    worker.progress.connect(
        lambda _percent, message, *_args: window.set_pai_api_status(
            f"Status: {message}"
        )
    )
    worker.finished_success.connect(
        lambda: _finish_success(window, worker, qmessagebox=qmessagebox)
    )
    worker.finished_error.connect(lambda message: _finish_error(window, worker, message))


def _finish_success(
    window: PaiApiWindowPort,
    worker: PaiApiRefreshWorker,
    *,
    qmessagebox: Any,
) -> None:
    if window.active_pai_api_worker() is worker:
        window.set_active_pai_api_worker(None)
    if window.confirm_pai_api_reload(qmessagebox):
        window.set_pai_api_status(STATUS_API_RELOAD)
        window.reload_pai_api_data()
        return
    window.set_pai_api_status(STATUS_API_KEEP_CURRENT)


def _finish_error(
    window: PaiApiWindowPort,
    worker: PaiApiRefreshWorker,
    message: str,
) -> None:
    if window.active_pai_api_worker() is worker:
        window.set_active_pai_api_worker(None)
    window.set_pai_api_status(f"Status: Falha na API PAI: {message}")


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


def _persist_preferences(window: PaiApiWindowPort) -> bool:
    return bool(window._persist_gui_preferences())


__all__ = [
    "PAI_API_ENABLED_KEY",
    "PAI_API_SCRAP_ENABLED_KEY",
    "set_pai_api_boolean_option",
    "set_pai_api_sector_enabled",
    "start_pai_api_refresh",
]
