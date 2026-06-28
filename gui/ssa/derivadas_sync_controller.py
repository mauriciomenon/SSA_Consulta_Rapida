"""Manual derivadas sync orchestration for the SSA GUI."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable

from gui.ssa.derivadas_sync_job import (
    DERIVADAS_SYNC_PHASE_DB,
    DERIVADAS_SYNC_PHASE_SHEETS,
    execute_derivadas_sync_job as execute_derivadas_sync_job_headless,
)

DERIVADAS_SYNC_POLL_INTERVAL_MS = 500
DERIVADAS_SYNC_TIMEOUT_SEC = 30 * 60
DERIVADAS_SYNC_TIMEOUT_ERROR = "Timeout ao atualizar derivadas manualmente."
DERIVADAS_SYNC_DB_STATUS = "Status: Atualizando derivadas via DB..."
DERIVADAS_SYNC_SHEET_STATUS_TEMPLATE = (
    "Status: Atualizando derivadas via planilhas especiais ({count})..."
)


@dataclass
class DerivadasSyncState:
    running: bool = False
    thread: threading.Thread | None = None
    pending_result: dict[str, Any] | None = None
    phase_status: str = ""
    ui_state: dict[str, Any] = field(default_factory=dict)
    table_name: str = ""
    last_status_text: str = ""
    lock: threading.Lock | None = None

    def mark_started(self) -> None:
        self.running = True
        self.thread = None
        self.pending_result = None
        self.phase_status = ""
        self.ui_state = {}
        self.table_name = ""

    def mark_finished(self) -> None:
        thread = self.thread
        self.running = False
        self.thread = thread if _thread_alive(thread) else None
        self.pending_result = None
        self.phase_status = ""
        self.table_name = ""

    def mark_abandoned(self) -> None:
        self.pending_result = None
        self.thread = None
        self.running = False
        self.phase_status = ""
        self.ui_state = {}
        self.table_name = ""
        self.last_status_text = ""


@dataclass(frozen=True)
class DerivadasSyncUiRefs:
    message_parent: Any
    status_label: Any
    progress_bar: Any
    update_button: Any
    refresh_button_state: Callable[[], None] | None = None


@dataclass(frozen=True)
class DerivadasSyncDependencies:
    qmessagebox: Any
    qtimer: Any
    sip_module: Any
    thread_factory: Callable[..., threading.Thread]
    list_special_sheets: Callable[[], list[str]]
    resolve_table_name: Callable[[str], str]
    execute_job: Callable[..., dict[str, Any]]
    finalize_result: Callable[..., dict[str, Any]]
    sync_state_callback: Callable[[], None] | None
    logger: Any


def list_special_derivadas_sheets(project_root: str) -> list[str]:
    docs_path = os.path.join(project_root, "docs_entrada")
    if not os.path.isdir(docs_path):
        return []
    files: list[str] = []
    for base_name in os.listdir(docs_path):
        lowered = str(base_name).strip().casefold()
        if lowered.startswith("ssas derivadas e relacionadas") and lowered.endswith(
            ".xlsx"
        ):
            files.append(os.path.join(docs_path, base_name))
    return sorted(files, key=lambda path: os.path.basename(path).casefold())


def update_derivadas_from_sources(
    ui: DerivadasSyncUiRefs,
    state: DerivadasSyncState,
    *,
    db_path: str,
    deps: DerivadasSyncDependencies,
) -> dict[str, Any] | None:
    if not _precheck_db_path(ui, db_path, deps.qmessagebox):
        return None

    sync_lock = _ensure_derivadas_sync_lock(state)
    already_running = _begin_derivadas_sync(
        ui,
        state,
        db_path=db_path,
        sync_lock=sync_lock,
        sync_state_callback=deps.sync_state_callback,
    )
    if already_running is not None:
        return already_running

    try:
        special_files, table_name = _prepare_derivadas_sync_inputs(
            state,
            db_path=db_path,
            list_special_sheets=deps.list_special_sheets,
            resolve_table_name=deps.resolve_table_name,
            sync_state_callback=deps.sync_state_callback,
        )
    except Exception as exc:
        with sync_lock:
            state.running = False
            _sync_state(deps.sync_state_callback)
        error = str(exc)
        deps.logger.error("Falha ao preparar sync manual de derivadas: %s", error)
        _set_status_label(ui, state, "Status: Falha ao preparar derivadas.")
        return {"ok": False, "error": error, "db_path": db_path}

    previous_ui_state = _capture_previous_ui_state(ui)
    start_derivadas_sync_ui_state(
        ui, state, previous_ui_state, DERIVADAS_SYNC_DB_STATUS, deps.logger
    )

    if os.environ.get("PYTEST_CURRENT_TEST"):
        result = deps.execute_job(
            db_path=db_path,
            table_name=table_name,
            special_files=special_files,
        )
        return deps.finalize_result(
            ui.message_parent, result, previous_ui_state=previous_ui_state
        )

    with sync_lock:
        state.phase_status = DERIVADAS_SYNC_DB_STATUS
        state.ui_state = previous_ui_state
        _sync_state(deps.sync_state_callback)

    return _start_async_derivadas_sync(
        ui,
        state,
        db_path=db_path,
        table_name=table_name,
        special_files=special_files,
        sync_lock=sync_lock,
        qtimer=deps.qtimer,
        sip_module=deps.sip_module,
        thread_factory=deps.thread_factory,
        execute_job=deps.execute_job,
        finalize_result=deps.finalize_result,
        sync_state_callback=deps.sync_state_callback,
    )


def _precheck_db_path(ui: DerivadasSyncUiRefs, db_path: str, qmessagebox: Any) -> bool:
    if db_path and os.path.exists(db_path):
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    qmessagebox.warning(ui.message_parent, "Erro", f"Banco nao encontrado: {db_path}")
    return False


def _begin_derivadas_sync(
    ui: DerivadasSyncUiRefs,
    state: DerivadasSyncState,
    *,
    db_path: str,
    sync_lock: threading.Lock,
    sync_state_callback: Callable[[], None] | None,
) -> dict[str, Any] | None:
    with sync_lock:
        if state.running or _thread_alive(state.thread):
            _set_status_label(
                ui, state, "Status: Atualizacao de derivadas ja em andamento."
            )
            return {
                "ok": False,
                "reason": "already_running",
                "db_path": db_path,
                "table_name": str(state.table_name or ""),
            }
        _set_derivadas_sync_started(state)
        _sync_state(sync_state_callback)
    return None


def _prepare_derivadas_sync_inputs(
    state: DerivadasSyncState,
    *,
    db_path: str,
    list_special_sheets: Callable[[], list[str]],
    resolve_table_name: Callable[[str], str],
    sync_state_callback: Callable[[], None] | None,
) -> tuple[list[str], str]:
    special_files = list_special_sheets()
    table_name = resolve_table_name(db_path)
    state.table_name = table_name
    _sync_state(sync_state_callback)
    return special_files, table_name


def _start_async_derivadas_sync(
    ui: DerivadasSyncUiRefs,
    state: DerivadasSyncState,
    *,
    db_path: str,
    table_name: str,
    special_files: list[str],
    sync_lock: threading.Lock,
    qtimer: Any,
    sip_module: Any,
    thread_factory: Callable[..., threading.Thread],
    execute_job: Callable[..., dict[str, Any]],
    finalize_result: Callable[..., dict[str, Any]],
    sync_state_callback: Callable[[], None] | None,
) -> dict[str, Any]:
    started = monotonic()

    def _set_phase_status(text: str) -> None:
        with sync_lock:
            if state.running:
                state.phase_status = str(text or "")

    def _work() -> None:
        try:
            result = execute_job(
                db_path=db_path,
                table_name=table_name,
                special_files=special_files,
                status_callback=_set_phase_status,
            )
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        current_thread = threading.current_thread()
        with sync_lock:
            if state.running:
                state.pending_result = result
            elif state.thread is current_thread or not _thread_alive(state.thread):
                state.thread = None
        _sync_state(sync_state_callback)

    def _poll_delivery() -> None:
        if not _window_alive(ui.message_parent, sip_module):
            _clear_abandoned_derivadas_sync(state, sync_lock, sync_state_callback)
            return
        pending: dict[str, Any] | None
        with sync_lock:
            phase_status = str(state.phase_status or "")
            pending = state.pending_result
            if pending is not None:
                state.pending_result = None
        if phase_status and phase_status != state.last_status_text:
            _set_status_label(ui, state, phase_status)
        if pending is None:
            if monotonic() - started > DERIVADAS_SYNC_TIMEOUT_SEC:
                with sync_lock:
                    pending = state.pending_result
                    if pending is not None:
                        state.pending_result = None
                    state.mark_finished()
                _sync_state(sync_state_callback)
                result = pending or {"ok": False, "error": DERIVADAS_SYNC_TIMEOUT_ERROR}
                finalize_result(ui.message_parent, result)
                return
            if state.running:
                qtimer.singleShot(DERIVADAS_SYNC_POLL_INTERVAL_MS, _poll_delivery)
            return
        with sync_lock:
            state.mark_finished()
        _sync_state(sync_state_callback)
        finalize_result(ui.message_parent, pending)

    worker = thread_factory(target=_work, daemon=True)
    with sync_lock:
        if not state.running:
            return {
                "ok": False,
                "reason": "not_running",
                "db_path": db_path,
                "table_name": table_name,
            }
        state.thread = worker
        _sync_state(sync_state_callback)
    worker.start()
    qtimer.singleShot(DERIVADAS_SYNC_POLL_INTERVAL_MS, _poll_delivery)
    return {
        "ok": True,
        "started": True,
        "db_path": db_path,
        "table_name": table_name,
    }


def start_derivadas_sync_ui_state(
    ui: DerivadasSyncUiRefs,
    state: DerivadasSyncState,
    previous_ui_state: dict[str, Any],
    initial_status: str,
    logger: Any,
) -> None:
    try:
        if ui.update_button is not None:
            ui.update_button.setEnabled(False)
        if ui.progress_bar is not None:
            ui.progress_bar.setVisible(True)
            ui.progress_bar.setRange(0, 0)
        _set_status_label(ui, state, initial_status)
    except Exception as exc:
        logger.warning(
            "Falha ao preparar estado visual antes do sync manual de derivadas: %s",
            exc,
        )


def execute_derivadas_sync_job(
    *,
    db_path: str,
    table_name: str,
    special_files: list[str],
    sync_derivadas_fn: Callable[..., dict[str, Any]],
    scan_derivadas_consistency_fn: Callable[..., dict[str, Any]],
    status_callback=None,
) -> dict[str, Any]:
    def _status_from_phase(phase_name: str, payload: dict[str, Any]) -> None:
        if not callable(status_callback):
            return
        if phase_name == DERIVADAS_SYNC_PHASE_DB:
            status_callback(DERIVADAS_SYNC_DB_STATUS)
            return
        if phase_name == DERIVADAS_SYNC_PHASE_SHEETS:
            status_callback(
                DERIVADAS_SYNC_SHEET_STATUS_TEMPLATE.format(
                    count=int(payload.get("count", 0) or 0)
                )
            )

    return execute_derivadas_sync_job_headless(
        db_path=db_path,
        table_name=table_name,
        special_files=special_files,
        sync_derivadas_fn=sync_derivadas_fn,
        scan_derivadas_consistency_fn=scan_derivadas_consistency_fn,
        phase_callback=_status_from_phase,
    )


def finalize_derivadas_sync_result(
    ui: DerivadasSyncUiRefs,
    state: DerivadasSyncState,
    result: dict[str, Any],
    *,
    previous_ui_state: dict[str, Any] | None = None,
    qmessagebox: Any,
    logger: Any,
) -> dict[str, Any]:
    previous = previous_ui_state or state.ui_state or {}
    state.mark_finished()

    _restore_derivadas_sync_ui_state(ui, previous, logger)

    if bool(result.get("ok")):
        merged_edges = int(result.get("merged_edges", 0) or 0)
        db_edges = int(result.get("db_edges", 0) or 0)
        sheet_edges = int(result.get("sheet_edges", 0) or 0)
        _set_status_label(
            ui,
            state,
            "Status: Relacoes de derivadas atualizadas: "
            f"total={merged_edges}; banco={db_edges}; planilhas={sheet_edges}.",
        )
        try:
            if callable(ui.refresh_button_state):
                ui.refresh_button_state()
        except Exception as exc:
            logger.warning(
                "Falha ao atualizar estado do botao de derivadas apos sync manual: %s",
                exc,
            )
        return result

    error = str(result.get("error") or "Erro desconhecido")
    logger.error("Falha ao atualizar derivadas manualmente: %s", error)
    _set_status_label(ui, state, "Status: Falha ao atualizar derivadas.")
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        qmessagebox.critical(
            ui.message_parent, "Erro", f"Falha ao atualizar derivadas: {error}"
        )
    return result


def _ensure_derivadas_sync_lock(state: DerivadasSyncState) -> threading.Lock:
    sync_lock = getattr(state, "lock", None)
    if sync_lock is None:
        sync_lock = threading.Lock()
        state.lock = sync_lock
    return sync_lock


def _thread_alive(thread: threading.Thread | None) -> bool:
    if thread is None:
        return False
    is_alive = getattr(thread, "is_alive", None)
    return bool(callable(is_alive) and is_alive())


def _set_derivadas_sync_started(state: DerivadasSyncState) -> None:
    state.mark_started()


def _capture_previous_ui_state(ui: DerivadasSyncUiRefs) -> dict[str, Any]:
    previous_status = ui.status_label.text() if ui.status_label is not None else ""
    previous_progress_visible = (
        bool(ui.progress_bar.isVisible()) if ui.progress_bar is not None else False
    )
    previous_progress_range = (
        (ui.progress_bar.minimum(), ui.progress_bar.maximum())
        if ui.progress_bar is not None
        else (0, 0)
    )
    previous_progress_value = (
        int(ui.progress_bar.value()) if ui.progress_bar is not None else 0
    )
    previous_update_enabled = (
        bool(ui.update_button.isEnabled()) if ui.update_button is not None else True
    )
    return {
        "status": previous_status,
        "progress_visible": previous_progress_visible,
        "progress_range": previous_progress_range,
        "progress_value": previous_progress_value,
        "update_enabled": previous_update_enabled,
    }


def _window_alive(window: Any, sip_module: Any) -> bool:
    if window is None:
        return False
    if not hasattr(window, "metaObject"):
        return True
    if sip_module is None:
        return True
    try:
        return not sip_module.isdeleted(window)
    except Exception:
        return False


def _clear_abandoned_derivadas_sync(
    state: DerivadasSyncState,
    sync_lock: threading.Lock,
    sync_state_callback: Callable[[], None] | None,
) -> None:
    with sync_lock:
        state.mark_abandoned()
    _sync_state(sync_state_callback)


def _restore_derivadas_sync_ui_state(
    ui: DerivadasSyncUiRefs, previous: dict[str, Any], logger: Any
) -> None:
    try:
        if ui.update_button is not None:
            ui.update_button.setEnabled(bool(previous.get("update_enabled", True)))
        if ui.progress_bar is not None:
            ui.progress_bar.setVisible(bool(previous.get("progress_visible")))
            progress_range = previous.get("progress_range") or (0, 0)
            ui.progress_bar.setRange(progress_range[0], progress_range[1])
            ui.progress_bar.setValue(int(previous.get("progress_value", 0) or 0))
    except Exception as exc:
        logger.warning(
            "Falha ao restaurar estado visual do sync manual de derivadas: %s",
            exc,
        )


def _set_status_label(
    ui: DerivadasSyncUiRefs, state: DerivadasSyncState, text: str
) -> None:
    if ui.status_label is not None:
        ui.status_label.setText(text)
    state.last_status_text = text


def _sync_state(sync_state_callback: Callable[[], None] | None) -> None:
    if callable(sync_state_callback):
        sync_state_callback()
