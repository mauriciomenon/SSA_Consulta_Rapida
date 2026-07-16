"""Rescan worker signal lifecycle wiring."""

from __future__ import annotations

from time import perf_counter

from gui.ssa.gui_worker_registry import GLOBAL_WORKERS_LOCK
from gui.ssa.gui_worker_status import (
    cancel_request_status_text,
    consolidation_status_text,
    success_status_text,
)
from gui.workers.rescan_worker import RescanOutcome
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def connect_rescan_worker_lifecycle(
    window,
    worker,
    progress_dialog,
    *,
    reload_on_success: bool,
    is_explicit_import: bool,
    normalized_kind: str,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
    connect_signal,
    prune_retired_workers,
    is_worker_running,
    set_status_label_text,
) -> None:
    cancelled = False
    batch_reload_count = 0
    batch_reload_failed = False
    register_rescan_worker(
        worker,
        global_workers=global_workers,
        global_meta=global_meta,
    )

    def release_worker_ref(*_args) -> None:
        try:
            if getattr(window, "_active_rescan_worker", None) is worker:
                window._active_rescan_worker = None
        except Exception as exc:
            logger.debug("Falha ao liberar referencia do RescanWorker: %s", exc)
        try:
            with GLOBAL_WORKERS_LOCK:
                global_workers[:] = [
                    retained_worker
                    for retained_worker in global_workers
                    if retained_worker is not worker
                ]
                global_meta.pop(worker, None)
        except Exception as exc:
            logger.debug(
                "Falha ao remover referencias globais do RescanWorker: %s", exc
            )

    def release_dialog_ref(*_args) -> None:
        try:
            if getattr(window, "_active_rescan_dialog", None) is progress_dialog:
                window._active_rescan_dialog = None
        except Exception as exc:
            logger.debug(
                "Falha ao liberar referencia do dialogo de reescaneamento: %s", exc
            )

    def prune_retired_workers_after_finish(*_args) -> None:
        try:
            prune_retired_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug(
                "Falha ao podar rescan workers apos worker finalizado: %s", exc
            )

    def on_finished_successfully() -> None:
        outcome = _resolve_rescan_outcome(worker)
        if cancelled:
            _finish_rescan_as_cancelled(
                window,
                progress_dialog,
                is_explicit_import=is_explicit_import,
                normalized_kind=normalized_kind,
                set_status_label_text=set_status_label_text,
            )
            release_dialog_ref()
            return
        was_active_worker = getattr(window, "_active_rescan_worker", None) is worker
        progress_dialog.set_finished(True)
        release_dialog_ref()
        _finish_successful_rescan(
            window,
            outcome,
            allow_reload=was_active_worker
            and (batch_reload_count == 0 or batch_reload_failed),
            reload_on_success=reload_on_success,
            is_explicit_import=is_explicit_import,
            explicit_import_has_files=bool(getattr(worker, "explicit_files", ())),
            normalized_kind=normalized_kind,
            set_status_label_text=set_status_label_text,
        )

    def on_batch_completed(_current: int, _total: int) -> None:
        nonlocal batch_reload_count, batch_reload_failed
        if not reload_on_success or normalized_kind == "consolidate":
            return
        if getattr(window, "_active_rescan_worker", None) is not worker:
            return
        try:
            window.load_data()
            batch_reload_count += 1
            batch_reload_failed = False
        except Exception as exc:
            batch_reload_failed = True
            logger.warning(
                "Falha ao recarregar dados apos bloco de importacao: %s",
                exc,
            )

    def on_error(error_msg) -> None:
        nonlocal cancelled
        if cancelled or str(error_msg).strip().lower().startswith("processo cancelado"):
            cancelled = True
            _finish_cancelled_error(
                window,
                progress_dialog,
                is_explicit_import=is_explicit_import,
                normalized_kind=normalized_kind,
                set_status_label_text=set_status_label_text,
            )
            release_dialog_ref()
            return
        progress_dialog.set_finished(False, error_msg)
        release_dialog_ref()
        _finish_rescan_error(
            window,
            is_explicit_import=is_explicit_import,
            normalized_kind=normalized_kind,
            set_status_label_text=set_status_label_text,
        )

    def on_cancel_requested() -> None:
        nonlocal cancelled
        cancelled = True
        cancel_text, cancel_context = cancel_request_status_text(
            is_explicit_import, normalized_kind
        )
        set_status_label_text(window, cancel_text, context=cancel_context)
        if is_worker_running(worker, sip_module):
            try:
                if hasattr(worker, "stop"):
                    worker.stop()
            except Exception as exc:
                logger.debug(
                    "Falha ao solicitar stop do RescanWorker no cancelamento: %s", exc
                )

    connect_signal(
        worker.finished_success,
        on_finished_successfully,
        label="rescan.finished_success",
    )
    batch_completed_signal = getattr(worker, "batch_completed", None)
    if batch_completed_signal is not None:
        connect_signal(
            batch_completed_signal,
            on_batch_completed,
            label="rescan.batch_completed",
        )
    connect_signal(worker.finished_error, on_error, label="rescan.finished_error")
    connect_signal(
        worker.finished,
        release_worker_ref,
        label="rescan.finished.ref_cleanup",
    )
    connect_signal(
        worker.finished,
        release_dialog_ref,
        label="rescan.finished.dialog_release",
    )
    connect_signal(
        worker.finished,
        prune_retired_workers_after_finish,
        label="rescan.finished.prune",
    )
    connect_signal(worker.finished, worker.deleteLater, label="rescan.finished.deleteLater")
    if hasattr(progress_dialog, "finished"):
        connect_signal(
            progress_dialog.finished,
            release_dialog_ref,
            label="rescan.dialog.finished.release",
        )
    connect_signal(
        progress_dialog.cancel_requested,
        on_cancel_requested,
        label="rescan.dialog.cancel_requested",
    )


def register_rescan_worker(
    worker,
    *,
    global_workers: list,
    global_meta: dict,
) -> None:
    with GLOBAL_WORKERS_LOCK:
        if worker not in global_workers:
            global_workers.append(worker)
        global_meta[worker] = perf_counter()


def _resolve_rescan_outcome(worker) -> RescanOutcome:
    outcome = getattr(worker, "last_outcome", RescanOutcome.UPDATED)
    if isinstance(outcome, RescanOutcome):
        return outcome
    try:
        return RescanOutcome(str(outcome or RescanOutcome.UPDATED.value))
    except ValueError:
        return RescanOutcome.UPDATED


def _finish_rescan_as_cancelled(
    window,
    progress_dialog,
    *,
    is_explicit_import: bool,
    normalized_kind: str,
    set_status_label_text,
) -> None:
    progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
    set_status_label_text(
        window,
        _cancelled_status_text(is_explicit_import, normalized_kind),
        context=_status_context(
            normalized_kind,
            is_explicit_import=is_explicit_import,
            explicit_context="explicit_import.success.cancelled",
            rescan_context="rescan.success.cancelled",
            consolidate_context="consolidate.success.cancelled",
        ),
    )


def _finish_cancelled_error(
    window,
    progress_dialog,
    *,
    is_explicit_import: bool,
    normalized_kind: str,
    set_status_label_text,
) -> None:
    progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
    set_status_label_text(
        window,
        _cancelled_status_text(is_explicit_import, normalized_kind),
        context=_status_context(
            normalized_kind,
            is_explicit_import=is_explicit_import,
            explicit_context="explicit_import.error.cancelled",
            rescan_context="rescan.error.cancelled",
            consolidate_context="consolidate.error.cancelled",
        ),
    )


def _finish_successful_rescan(
    window,
    outcome: RescanOutcome,
    *,
    allow_reload: bool,
    reload_on_success: bool,
    is_explicit_import: bool,
    explicit_import_has_files: bool,
    normalized_kind: str,
    set_status_label_text,
) -> None:
    successful_import_outcome = outcome == RescanOutcome.UPDATED or (
        is_explicit_import
        and explicit_import_has_files
        and outcome == RescanOutcome.NO_CHANGES
    )
    should_reload_data = (
        allow_reload
        and reload_on_success
        and successful_import_outcome
        and normalized_kind != "consolidate"
        and hasattr(window, "load_data")
    )
    success_text = (
        consolidation_status_text(outcome)
        if normalized_kind == "consolidate"
        else success_status_text(is_explicit_import, outcome)
    )
    set_status_label_text(
        window,
        success_text,
        context=_status_context(
            normalized_kind,
            is_explicit_import=is_explicit_import,
            explicit_context="explicit_import.success.done",
            rescan_context="rescan.success.done",
            consolidate_context="consolidate.success.done",
        ),
    )
    if should_reload_data:
        try:
            window.load_data()
        except Exception as exc:
            logger.warning(
                "Falha ao recarregar dados apos operacao concluida: %s", exc
            )


def _finish_rescan_error(
    window,
    *,
    is_explicit_import: bool,
    normalized_kind: str,
    set_status_label_text,
) -> None:
    set_status_label_text(
        window,
        _error_status_text(is_explicit_import, normalized_kind),
        context=_status_context(
            normalized_kind,
            is_explicit_import=is_explicit_import,
            explicit_context="explicit_import.error",
            rescan_context="rescan.error",
            consolidate_context="consolidate.error",
        ),
    )


def _cancelled_status_text(is_explicit_import: bool, normalized_kind: str) -> str:
    if normalized_kind == "consolidate":
        return "Status: Consolidacao de arquivos cancelada."
    if is_explicit_import:
        return "Status: Importacao externa cancelada."
    return "Status: Reescaneamento cancelado."


def _error_status_text(is_explicit_import: bool, normalized_kind: str) -> str:
    if normalized_kind == "consolidate":
        return "Status: Erro na consolidacao de arquivos."
    if is_explicit_import:
        return "Status: Erro na importacao externa."
    return "Status: Erro no reescaneamento."


def _status_context(
    normalized_kind: str,
    *,
    is_explicit_import: bool,
    explicit_context: str,
    rescan_context: str,
    consolidate_context: str,
) -> str:
    if normalized_kind == "consolidate":
        return consolidate_context
    if is_explicit_import:
        return explicit_context
    return rescan_context
