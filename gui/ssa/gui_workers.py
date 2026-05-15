# gui/ssa/gui_workers.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: uses gui/workers and worker retention globals from gui/gui_ssa.py.
# Relation: owns load_data flow and worker cleanup; no layout changes.

from __future__ import annotations

import inspect
import os
import threading
import time
import uuid
from time import perf_counter

import pandas as pd

from gui.workers.data_loader_worker import DataLoaderWorker
from gui.workers.rescan_worker import RescanOutcome
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")
_GLOBAL_WORKERS_LOCK = threading.Lock()
# NOTE: worker retention uses window-local list plus global registry; keep behavior stable.
# Refactor to a manager class is tracked in docs/RECOVERY_BACKLOG.md.
# NOTE: global worker lists are capped by max_* to limit lock contention.

try:
    from PyQt6.QtCore import Qt as _Qt

    _QT_QUEUED = _Qt.ConnectionType.QueuedConnection
except Exception as exc:
    logger.debug(
        "Falha ao importar Qt.ConnectionType para conexao enfileirada: %s", exc
    )
    _QT_QUEUED = None

def _set_status_label_text(window, text: str, *, context: str) -> bool:
    status_label = getattr(window, "status_label", None)
    if status_label is None:
        logger.debug("status_label ausente ao atualizar status (%s).", context)
        return False
    if not hasattr(status_label, "setText"):
        logger.debug("status_label sem setText ao atualizar status (%s).", context)
        return False
    try:
        status_label.setText(text)
        return True
    except Exception as exc:
        logger.debug("Falha ao atualizar status_label (%s): %s", context, exc)
        return False


def _connect_signal(signal, slot, *, label: str) -> bool:
    if signal is None:
        logger.debug("Signal ausente para %s; pulando conexao.", label)
        return False
    if not hasattr(signal, "connect"):
        logger.debug("Signal invalido para %s; sem metodo connect.", label)
        return False
    try:
        if _QT_QUEUED is not None:
            try:
                signal.connect(slot, _QT_QUEUED)
            except TypeError:
                signal.connect(slot)
        else:
            signal.connect(slot)
        return True
    except Exception as exc:
        logger.debug("Falha ao conectar signal %s: %s", label, exc)
        return False


def _configure_operation_dialog(progress_dialog, operation_label: str) -> None:
    try:
        if hasattr(progress_dialog, "set_operation_label"):
            progress_dialog.set_operation_label(operation_label)
    except Exception as exc:
        logger.debug("Falha ao configurar rotulo da operacao no dialogo: %s", exc)


def _success_status_text(is_explicit_import: bool, outcome: RescanOutcome) -> str:
    if not is_explicit_import:
        return "Status: Reescaneamento concluido. Clique em 'Recarregar Dados' para atualizar."
    if outcome == RescanOutcome.UPDATED:
        return "Status: Importacao externa concluida."
    if outcome == RescanOutcome.REJECTIONS_ONLY:
        return "Status: Importacao externa concluida com rejeicoes de regra."
    return "Status: Importacao externa concluida sem alteracoes."


def _consolidation_status_text(outcome: RescanOutcome) -> str:
    if outcome == RescanOutcome.UPDATED:
        return "Status: Consolidacao de arquivos concluida."
    return "Status: Consolidacao de arquivos concluida sem alteracoes."


def _cancel_request_status_text(
    is_explicit_import: bool, operation_kind: str
) -> tuple[str, str]:
    if operation_kind == "consolidate":
        return (
            "Status: Cancelamento solicitado na consolidacao de arquivos.",
            "consolidate.cancel.requested",
        )
    if is_explicit_import:
        return (
            "Status: Cancelamento solicitado na importacao externa.",
            "explicit_import.cancel.requested",
        )
    return (
        "Status: Cancelamento solicitado no reescaneamento.",
        "rescan.cancel.requested",
    )


def _already_running_status_text(
    *, is_explicit_import: bool, operation_kind: str
) -> tuple[str, str]:
    if operation_kind == "consolidate":
        return (
            "Status: Consolidacao de arquivos ja em andamento.",
            "consolidate.already_running",
        )
    if is_explicit_import:
        return (
            "Status: Importacao externa ja em andamento.",
            "explicit_import.already_running",
        )
    return (
        "Status: Reescaneamento ja em andamento.",
        "rescan.already_running",
    )


def _build_rescan_worker(
    rescan_worker_cls,
    *,
    main_py_path: str,
    project_root: str,
    force_import: bool,
    explicit_files: tuple[str, ...],
    source_files: tuple[str, ...],
    db_path: str | None,
    operation_label: str,
    operation_kind: str,
):
    init_signature = inspect.signature(rescan_worker_cls.__init__)
    accepted_params = {
        name for name in init_signature.parameters.keys() if name != "self"
    }
    worker_kwargs = {}
    if "force_import" in accepted_params:
        worker_kwargs["force_import"] = force_import
    if "explicit_files" in accepted_params:
        worker_kwargs["explicit_files"] = explicit_files or None
    if "source_files" in accepted_params:
        worker_kwargs["source_files"] = source_files or None
    if "db_path" in accepted_params:
        worker_kwargs["db_path"] = db_path
    if "operation_label" in accepted_params:
        worker_kwargs["operation_label"] = operation_label
    if "operation_kind" in accepted_params:
        worker_kwargs["operation_kind"] = operation_kind
    return rescan_worker_cls(main_py_path, project_root, **worker_kwargs)


def _safe_disconnect(signal, label: str) -> None:
    if signal is None:
        return
    try:
        signal.disconnect()
    except Exception as exc:
        logger.debug("Falha ao desconectar %s: %s", label, exc)


def retain_data_loader_worker_until_finished(
    window,
    worker,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    if worker is None:
        return
    with _GLOBAL_WORKERS_LOCK:
        if getattr(window, "_retired_data_loader_workers", None) is None:
            window._retired_data_loader_workers = []
    now = perf_counter()
    prune_retired_data_loader_workers(
        window,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=max_global_workers,
        retired_ttl_sec=retired_ttl_sec,
        retired_force_wait_ms=retired_force_wait_ms,
        sip_module=sip_module,
    )
    with _GLOBAL_WORKERS_LOCK:
        retired = getattr(window, "_retired_data_loader_workers", None)
        if retired is None:
            retired = []
            window._retired_data_loader_workers = retired
        if worker in retired:
            if worker not in global_workers:
                global_workers.append(worker)
            global_meta[worker] = now
            return
        retired.append(worker)
        if worker not in global_workers:
            global_workers.append(worker)
        global_meta[worker] = now

    def _release_worker_ref(w=worker):
        try:
            with _GLOBAL_WORKERS_LOCK:
                retired_workers = getattr(window, "_retired_data_loader_workers", None)
                if retired_workers is not None and w in retired_workers:
                    retired_workers.remove(w)
                if w in global_workers:
                    global_workers.remove(w)
                global_meta.pop(w, None)
        except Exception as exc:
            logger.debug(
                "Falha ao liberar referencias de worker de carga finalizado: %s", exc
            )

    finished_signal = getattr(worker, "finished", None)
    if not _connect_signal(
        finished_signal, _release_worker_ref, label="data_loader.finished.cleanup"
    ):
        try:
            if hasattr(worker, "isRunning") and worker.isRunning():
                if hasattr(worker, "quit"):
                    worker.quit()
                if hasattr(worker, "wait"):
                    worker.wait(retired_force_wait_ms)
        except Exception as exc:
            logger.debug(
                "Falha ao encerrar worker de carga apos erro de conexao de sinal: %s",
                exc,
            )
        try:
            if hasattr(worker, "deleteLater"):
                worker.deleteLater()
        except Exception as exc:
            logger.debug(
                "Falha ao agendar deleteLater de worker apos erro de conexao de sinal: %s",
                exc,
            )
    destroyed_signal = getattr(worker, "destroyed", None)
    if destroyed_signal is not None:
        _connect_signal(
            destroyed_signal, _release_worker_ref, label="data_loader.destroyed.cleanup"
        )
    if finished_signal is not None and hasattr(worker, "deleteLater"):
        _connect_signal(
            finished_signal,
            worker.deleteLater,
            label="data_loader.finished.deleteLater",
        )
    prune_retired_data_loader_workers(
        window,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=max_global_workers,
        retired_ttl_sec=retired_ttl_sec,
        retired_force_wait_ms=retired_force_wait_ms,
        sip_module=sip_module,
    )


def is_data_loader_worker_alive(worker, sip_module) -> bool:
    if worker is None:
        return False
    if sip_module is None:
        return True
    try:
        return not sip_module.isdeleted(worker)
    except TypeError:
        return True
    except Exception as exc:
        logger.debug("Falha ao consultar estado de delecao do worker: %s", exc)
        return False


def is_data_loader_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception as exc:
        logger.debug("Falha ao consultar isRunning() do data loader worker: %s", exc)
        return False
    return True


def _classify_workers_for_ttl(
    workers: list,
    *,
    global_meta: dict,
    now: float,
    retired_ttl_sec: float,
    max_global_workers: int,
    is_running_fn,
) -> tuple[list, list]:
    # Classifica snapshot; nao altera lista de origem para evitar side-effects
    # fora da secao protegida por lock.
    running_workers: list = []
    expired_workers: list = []
    for worker in list(workers):
        if not is_running_fn(worker):
            global_meta.pop(worker, None)
            continue
        started_at = global_meta.get(worker, now)
        age = now - started_at
        if age > retired_ttl_sec:
            expired_workers.append(worker)
        running_workers.append(worker)
    if max_global_workers > 0 and len(running_workers) > max_global_workers:
        overflow_count = len(running_workers) - max_global_workers
        overflow_workers = sorted(
            running_workers,
            key=lambda candidate: float(global_meta.get(candidate, now)),
        )[:overflow_count]
        overflow_set = set(overflow_workers)
        for worker in overflow_workers:
            if worker not in expired_workers:
                expired_workers.append(worker)
        running_workers = [
            worker for worker in running_workers if worker not in overflow_set
        ]
    return running_workers, expired_workers


def _drop_orphaned_worker_meta(
    global_workers: list, global_meta: dict, protected_workers: set | None = None
) -> None:
    protected = protected_workers or set()
    for worker in list(global_meta.keys()):
        if worker not in global_workers and worker not in protected:
            global_meta.pop(worker, None)


def _process_expired_workers(
    expired_workers: list,
    *,
    now: float,
    global_workers: list,
    global_meta: dict,
    warn_message: str,
    stop_worker_fn,
    stop_error_log: str,
    skip_workers: set | None = None,
) -> set:
    removed_workers: set = set()
    skip = skip_workers or set()
    for worker in expired_workers:
        if worker in skip:
            continue
        logger.warning("%s [worker=%r]", warn_message, worker)
        try:
            stopped = bool(stop_worker_fn(worker))
        except Exception as exc:
            logger.debug(stop_error_log, exc)
            stopped = False
        if stopped:
            removed_workers.add(worker)
            with _GLOBAL_WORKERS_LOCK:
                if worker in global_workers:
                    global_workers.remove(worker)
                global_meta.pop(worker, None)
        else:
            with _GLOBAL_WORKERS_LOCK:
                global_meta[worker] = now
    return removed_workers


def _classify_and_update_global_workers_locked(
    *,
    global_workers: list,
    global_meta: dict,
    now: float,
    retired_ttl_sec: float,
    max_global_workers: int,
    is_running_fn,
    drop_orphaned_meta: bool = False,
) -> list:
    running_global, expired_global = _classify_workers_for_ttl(
        global_workers,
        global_meta=global_meta,
        now=now,
        retired_ttl_sec=retired_ttl_sec,
        max_global_workers=max_global_workers,
        is_running_fn=is_running_fn,
    )
    global_workers[:] = running_global
    if drop_orphaned_meta:
        _drop_orphaned_worker_meta(global_workers, global_meta)
    return expired_global


def prune_retired_data_loader_workers(
    window,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    now = perf_counter()
    removed_local = set()
    expired_local = []
    expired_global = []
    with _GLOBAL_WORKERS_LOCK:
        if (
            not getattr(window, "_retired_data_loader_workers", None)
            and not global_workers
        ):
            return
        retired_local = list(getattr(window, "_retired_data_loader_workers", []) or [])
        for w in retired_local:
            if not is_data_loader_worker_running(w, sip_module):
                global_meta.pop(w, None)
                removed_local.add(w)
                continue
            started_at = global_meta.get(w, now)
            age = now - started_at
            if age > retired_ttl_sec:
                expired_local.append(w)

        expired_global = _classify_and_update_global_workers_locked(
            global_workers=global_workers,
            global_meta=global_meta,
            now=now,
            retired_ttl_sec=retired_ttl_sec,
            max_global_workers=max_global_workers,
            is_running_fn=lambda worker: is_data_loader_worker_running(
                worker, sip_module
            ),
        )
    expired_all = list(
        dict.fromkeys(
            [
                *expired_local,
                *(worker for worker in expired_global if worker not in removed_local),
            ]
        )
    )

    def _stop_data_loader_worker(worker) -> bool:
        return cleanup_data_loader_worker(
            window,
            worker,
            wait_ms=retired_force_wait_ms,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )

    removed_by_ttl = _process_expired_workers(
        expired_all,
        now=now,
        global_workers=global_workers,
        global_meta=global_meta,
        warn_message="Data loader worker excedeu TTL; solicitando stop.",
        stop_worker_fn=_stop_data_loader_worker,
        stop_error_log="Falha ao encerrar data loader worker expirado: %s",
        skip_workers=removed_local,
    )
    removed_local.update(removed_by_ttl)
    with _GLOBAL_WORKERS_LOCK:
        retired_snapshot = set(
            getattr(window, "_retired_data_loader_workers", []) or []
        )
        if removed_local:
            retired_current = list(
                getattr(window, "_retired_data_loader_workers", []) or []
            )
            window._retired_data_loader_workers = [
                w for w in retired_current if w not in removed_local
            ]
            retired_snapshot = set(window._retired_data_loader_workers)
        _drop_orphaned_worker_meta(global_workers, global_meta, retired_snapshot)


def is_rescan_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception as exc:
        logger.debug("Falha ao consultar isRunning() do rescan worker: %s", exc)
        return False
    return True


def _enforce_global_worker_cap(
    global_workers: list, global_meta: dict, max_global_workers: int
) -> None:
    if len(global_workers) <= max_global_workers:
        return
    overflow = len(global_workers) - max_global_workers
    dropped_workers = global_workers[:overflow]
    global_workers[:] = global_workers[overflow:]
    for dropped_worker in dropped_workers:
        global_meta.pop(dropped_worker, None)


def retain_rescan_worker_global(
    worker,
    *,
    reason: str,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    sip_module,
) -> bool:
    try:
        if not is_data_loader_worker_alive(worker, sip_module):
            logger.debug(
                "RescanWorker invalido no closeEvent (%s); retencao global ignorada.",
                reason,
            )
            return False
        timestamp = perf_counter()
        with _GLOBAL_WORKERS_LOCK:
            if worker not in global_workers:
                global_workers.append(worker)
            global_meta[worker] = timestamp
            _enforce_global_worker_cap(global_workers, global_meta, max_global_workers)
        logger.debug(
            "RescanWorker retido globalmente durante closeEvent (%s).",
            reason,
        )
        return True
    except Exception as exc:
        logger.debug(
            "Falha ao reter RescanWorker globalmente no closeEvent (%s): %s",
            reason,
            exc,
        )
        return False


def cleanup_rescan_worker_on_close(
    window,
    worker,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    if worker is None:
        return
    retained_globally = retain_rescan_worker_global(
        worker,
        reason="pre-shutdown-transfer",
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=max_global_workers,
        sip_module=sip_module,
    )
    try:
        prune_retired_rescan_workers(
            window,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    except Exception as exc:
        logger.debug("Falha ao podar rescan workers apos retencao global: %s", exc)
    try:
        try:
            running_now = is_rescan_worker_running(worker, sip_module)
        except Exception as exc:
            running_now = True
            logger.debug(
                "Falha ao consultar estado inicial do RescanWorker no closeEvent (%s). Assumindo ativo para shutdown defensivo.",
                exc,
            )
        if running_now or retained_globally:
            try:
                if hasattr(worker, "stop"):
                    worker.stop()
            except Exception as exc:
                logger.debug(
                    "Falha ao solicitar stop do RescanWorker no closeEvent: %s",
                    exc,
                )
            try:
                if hasattr(worker, "quit"):
                    worker.quit()
            except Exception as exc:
                logger.debug(
                    "Falha ao solicitar quit do RescanWorker no closeEvent: %s",
                    exc,
                )
            try:
                worker.wait(1500)
            except Exception as exc:
                logger.debug("Falha ao aguardar RescanWorker no closeEvent: %s", exc)
            try:
                if is_rescan_worker_running(worker, sip_module):
                    try:
                        if hasattr(worker, "terminate"):
                            worker.terminate()
                            worker.wait(1500)
                    except Exception as exc:
                        logger.debug(
                            "Falha no fallback terminate do RescanWorker no closeEvent: %s",
                            exc,
                        )
                if is_rescan_worker_running(worker, sip_module):
                    retained_globally = retain_rescan_worker_global(
                        worker,
                        reason="still-running-after-shutdown",
                        global_workers=global_workers,
                        global_meta=global_meta,
                        max_global_workers=max_global_workers,
                        sip_module=sip_module,
                    )
            except Exception as exc:
                logger.debug(
                    "Falha ao checar/reter RescanWorker no closeEvent: %s", exc
                )
    except Exception as exc:
        logger.debug("Falha ao encerrar RescanWorker durante closeEvent: %s", exc)
    finally:
        if not retained_globally:
            retain_rescan_worker_global(
                worker,
                reason="fallback-finally",
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                sip_module=sip_module,
            )
        window._active_rescan_worker = None


def cleanup_window_workers_on_close(
    window,
    *,
    data_loader_workers: list,
    data_loader_meta: dict,
    max_data_loader_workers: int,
    rescan_workers: list,
    rescan_meta: dict,
    max_rescan_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    data_worker = getattr(window, "data_loader_thread", None)
    if data_worker is not None:
        try:
            cleanup_data_loader_worker(
                window,
                data_worker,
                wait_ms=3000,
                global_workers=data_loader_workers,
                global_meta=data_loader_meta,
                max_global_workers=max_data_loader_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha no cleanup do data loader durante closeEvent: %s", exc)
        finally:
            if getattr(window, "data_loader_thread", None) is data_worker:
                window.data_loader_thread = None

    filter_worker = getattr(window, "filter_thread", None)
    filter_worker_running = False
    if filter_worker is not None and hasattr(filter_worker, "isRunning"):
        try:
            filter_worker_running = bool(filter_worker.isRunning())
        except Exception as exc:
            filter_worker_running = True
            logger.debug(
                "Falha ao consultar estado do filter worker no closeEvent: %s",
                exc,
            )
    if filter_worker_running:
        try:
            window._cancel_active_filter_worker("closeEvent")
        except Exception as exc:
            logger.debug("Filter cleanup fallback in closeEvent: %s", exc)
            try:
                worker_for_fallback = filter_worker
                if worker_for_fallback is not None:
                    worker_for_fallback.quit()
                    worker_for_fallback.wait(3000)
            except Exception as fallback_exc:
                logger.debug(
                    "Falha no fallback de encerramento do filter worker: %s",
                    fallback_exc,
                )

    try:
        prune_retired_data_loader_workers(
            window,
            global_workers=data_loader_workers,
            global_meta=data_loader_meta,
            max_global_workers=max_data_loader_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    except Exception as exc:
        logger.debug("Falha ao podar workers aposentados no closeEvent: %s", exc)

    cleanup_rescan_worker_on_close(
        window,
        getattr(window, "_active_rescan_worker", None),
        global_workers=rescan_workers,
        global_meta=rescan_meta,
        max_global_workers=max_rescan_workers,
        retired_ttl_sec=retired_ttl_sec,
        retired_force_wait_ms=retired_force_wait_ms,
        sip_module=sip_module,
    )


def prune_retired_rescan_workers(
    window,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    now = perf_counter()
    expired_global = []
    with _GLOBAL_WORKERS_LOCK:
        expired_global = _classify_and_update_global_workers_locked(
            global_workers=global_workers,
            global_meta=global_meta,
            now=now,
            retired_ttl_sec=retired_ttl_sec,
            max_global_workers=max_global_workers,
            is_running_fn=lambda worker: is_rescan_worker_running(worker, sip_module),
            drop_orphaned_meta=True,
        )

    def _stop_rescan_worker(worker) -> bool:
        if hasattr(worker, "stop"):
            worker.stop()
        if hasattr(worker, "quit"):
            worker.quit()
        if hasattr(worker, "wait"):
            worker.wait(int(retired_force_wait_ms))
        if (
            hasattr(worker, "isRunning")
            and worker.isRunning()
            and hasattr(worker, "terminate")
        ):
            worker.terminate()
            worker.wait(int(retired_force_wait_ms))
        return not is_rescan_worker_running(worker, sip_module)

    _process_expired_workers(
        expired_global,
        now=now,
        global_workers=global_workers,
        global_meta=global_meta,
        warn_message="Rescan worker excedeu TTL; solicitando stop.",
        stop_worker_fn=_stop_rescan_worker,
        stop_error_log="Falha ao encerrar rescan worker expirado: %s",
    )


def cleanup_data_loader_worker(
    window,
    worker,
    *,
    wait_ms: int = 1500,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> bool:
    if worker is None:
        return True
    still_running = False
    try:
        _safe_disconnect(
            getattr(worker, "data_loaded", None), "data_loaded do worker de carga"
        )
        _safe_disconnect(
            getattr(worker, "error_occurred", None), "error_occurred do worker de carga"
        )
        _safe_disconnect(
            getattr(worker, "finished", None), "finished do worker de carga"
        )
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            elif hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            if is_data_loader_worker_running(worker, sip_module):
                worker.quit()
                if int(wait_ms or 0) > 0:
                    worker.wait(int(wait_ms))
            still_running = is_data_loader_worker_running(worker, sip_module)
        except Exception as exc:
            logger.warning(
                "Falha ao solicitar encerramento do worker de carga: %s", exc
            )
            still_running = True
        if still_running:
            retain_data_loader_worker_until_finished(
                window,
                worker,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
            return False
        try:
            worker.deleteLater()
        except Exception as exc:
            logger.debug("Falha ao chamar deleteLater no worker de carga: %s", exc)
    except Exception as exc:
        logger.warning("Falha durante cleanup do worker de carga: %s", exc)
        still_running = True
    finally:
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as prune_exc:
            logger.debug("Falha ao podar workers de carga apos cleanup: %s", prune_exc)
    return not still_running


def load_data(
    window,
    *,
    db_path: str,
    table_name: str,
    data_loader_cls,
    qmessagebox,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    try:
        prune_retired_data_loader_workers(
            window,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    except Exception as exc:
        logger.debug("Falha ao podar workers de carga antes de novo load: %s", exc)
    if not os.path.exists(db_path):
        missing_db_msg = (
            "Banco de dados nao encontrado. Execute o programa principal primeiro."
        )
        logger.warning("Banco de dados nao encontrado.")
        _set_status_label_text(
            window,
            "Status: Banco de dados nao encontrado.",
            context="load_data_missing_db",
        )
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        if qmessagebox is not None:
            qmessagebox.warning(window, "Erro", missing_db_msg)
        return

    try:
        if hasattr(window, "_invalidate_active_filter_request"):
            window._invalidate_active_filter_request("load_data_new_dataset")
    except Exception as exc:
        logger.warning("Falha ao invalidar request de filtro antes do load: %s", exc)
    try:
        if hasattr(window, "_cancel_active_filter_worker"):
            window._cancel_active_filter_worker("load_data_new_dataset")
    except Exception as exc:
        logger.warning("Falha ao cancelar worker de filtro antes do load: %s", exc)
    try:
        window._debounce_timer.stop()
    except Exception as exc:
        logger.debug("Falha ao parar debounce de filtro antes do load: %s", exc)

    request_id = int(getattr(window, "_data_load_request_seq", 0) or 0) + 1
    window._data_load_request_seq = request_id
    window._active_data_load_request_id = request_id

    _set_status_label_text(
        window,
        "Status: Carregando dados...",
        context="load_data.start",
    )
    window.progress_bar.setVisible(True)
    window.load_button.setEnabled(False)
    window.search_button.setEnabled(False)

    previous_worker = getattr(window, "data_loader_thread", None)
    if previous_worker is not None:
        cleanup_data_loader_worker(
            window,
            previous_worker,
            wait_ms=0,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
        if getattr(window, "data_loader_thread", None) is previous_worker:
            window.data_loader_thread = None

    if data_loader_cls is None:
        logger.error("DataLoaderWorker indisponivel para load_data")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug(
                "PYTEST_CURRENT_TEST set; skipping modal DataLoaderWorker error dialog."
            )
        else:
            if qmessagebox is not None:
                qmessagebox.critical(
                    window,
                    "Erro de Carregamento",
                    "Data loader indisponivel neste ambiente. Consulte os logs.",
                )
        _set_status_label_text(
            window,
            "Status: Erro ao carregar dados.",
            context="load_data.worker_missing",
        )
        window.progress_bar.setVisible(False)
        window.load_button.setEnabled(True)
        window.search_button.setEnabled(True)
        return

    try:
        worker = data_loader_cls(db_path, table_name)
    except Exception as exc:
        logger.error(
            "Falha ao instanciar DataLoaderWorker: %s", _mask_db_path(str(exc), db_path)
        )
        try:
            handler = getattr(window, "on_load_error", None)
            if callable(handler):
                handler(str(exc), request_id=request_id)
            else:
                on_load_error(
                    window,
                    str(exc),
                    request_id=request_id,
                    db_path=db_path,
                    qmessagebox=qmessagebox,
                    global_workers=global_workers,
                    global_meta=global_meta,
                    max_global_workers=max_global_workers,
                    retired_ttl_sec=retired_ttl_sec,
                    retired_force_wait_ms=retired_force_wait_ms,
                    sip_module=sip_module,
                )
        finally:
            progress_bar = getattr(window, "progress_bar", None)
            if progress_bar is not None and hasattr(progress_bar, "setVisible"):
                progress_bar.setVisible(False)
            load_button = getattr(window, "load_button", None)
            if load_button is not None and hasattr(load_button, "setEnabled"):
                load_button.setEnabled(True)
            search_button = getattr(window, "search_button", None)
            if search_button is not None and hasattr(search_button, "setEnabled"):
                search_button.setEnabled(True)
        return
    window.data_loader_thread = worker

    def _handle_data_loaded(df, rid=request_id):
        handler = getattr(window, "on_data_loaded", None)
        if callable(handler):
            return handler(df, request_id=rid)
        return on_data_loaded(window, df, request_id=rid)

    def _handle_load_error(msg, rid=request_id):
        try:
            handler = getattr(window, "on_load_error", None)
            if callable(handler):
                return handler(msg, request_id=rid)
            return on_load_error(
                window,
                msg,
                request_id=rid,
                db_path=db_path,
                qmessagebox=qmessagebox,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        finally:
            try:
                now = perf_counter()
                should_prune = False
                with _GLOBAL_WORKERS_LOCK:
                    last_prune = float(
                        getattr(window, "_last_data_loader_prune_ts", 0.0) or 0.0
                    )
                    if now - last_prune >= 1.0:
                        window._last_data_loader_prune_ts = now
                        should_prune = True
                if should_prune:
                    prune_retired_data_loader_workers(
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
                    "Falha ao podar workers de carga apos erro no handler: %s", exc
                )

    def _handle_load_finished(w=worker, rid=request_id):
        handler = getattr(window, "on_load_finished", None)
        if callable(handler):
            return handler(worker=w, request_id=rid)
        return on_load_finished(
            window,
            worker=w,
            request_id=rid,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )

    _connect_signal(
        worker.data_loaded, _handle_data_loaded, label="data_loader.data_loaded"
    )
    _connect_signal(
        worker.error_occurred, _handle_load_error, label="data_loader.error_occurred"
    )
    _connect_signal(
        worker.finished, _handle_load_finished, label="data_loader.finished"
    )
    _connect_signal(
        worker.finished, worker.deleteLater, label="data_loader.finished.deleteLater"
    )
    worker.start()
    with _GLOBAL_WORKERS_LOCK:
        if worker not in global_workers:
            global_workers.append(worker)
        global_meta[worker] = perf_counter()


def on_data_loaded(window, df: pd.DataFrame, request_id: int | None = None):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug(
            "Ignorando resultado de carga obsoleto (request_id=%s, active=%s)",
            request_id,
            active_id,
        )
        return
    attrs = getattr(df, "attrs", {})
    preprocessed_for_gui = bool(attrs.get("ssa_preprocessed_for_gui"))
    if preprocessed_for_gui:
        df_copy = df
    else:
        df_copy = df.copy()
        for ssa_col in ("numero_ssa", "derivada_de"):
            if ssa_col in df_copy.columns:
                try:
                    df_copy[ssa_col] = df_copy[ssa_col].map(
                        DataLoaderWorker._sanitize_ssa_like_value
                    )
                except Exception as exc:
                    logger.debug(
                        "Falha ao sanitizar coluna %s na carga de dados: %s",
                        ssa_col,
                        exc,
                    )
    window.df_completo = df_copy
    try:
        last_req = getattr(window, "_data_revision_request_id", None)
        if request_id is None or request_id != last_req:
            if hasattr(window, "_bump_data_revision"):
                window._bump_data_revision("data_loaded")
            else:
                window._data_revision = (
                    int(getattr(window, "_data_revision", 0) or 0) + 1
                )
            try:
                window._data_uuid = uuid.uuid4().hex
            except Exception as exc:
                logger.debug(
                    "Falha ao gerar UUID de dados; usando fallback textual: %s", exc
                )
                window._data_uuid = f"fallback-{time.time_ns()}-{int(getattr(window, '_data_revision', 0) or 0)}"
            window._data_revision_request_id = request_id
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar revisao de dados; resetando para baseline: %s", exc
        )
        window._data_revision = 1
    try:
        window.clear_filter_cache()
    except Exception as exc:
        logger.debug("Falha ao limpar cache de filtros apos recarga de dados: %s", exc)
    window._adv_options_dirty = True
    window._adv_values_cache = None
    window._responsavel_materialized_prefixes = set()
    window._mark_responsavel_dirty()
    try:
        timer = getattr(window, "_sector_debounce_timer", None)
        if timer is not None:
            timer.stop()
    except Exception as exc:
        logger.debug("Falha ao parar debounce de setor apos carga de dados: %s", exc)
    if preprocessed_for_gui:
        base = df
    else:
        base = DataLoaderWorker._build_initial_sorted_dataframe(df_copy)
    window.df_exibido = base
    window._df_last_search_filtered = window.df_completo
    window._widths_computed_for_df_hash = None
    try:
        if hasattr(window, "_reset_num_reprogramacoes_sort_cache"):
            window._reset_num_reprogramacoes_sort_cache()
    except Exception as exc:
        logger.debug("Falha ao resetar cache de sort de num_reprogramacoes: %s", exc)
    try:
        if hasattr(window, "_reset_mixed_text_sort_cache"):
            window._reset_mixed_text_sort_cache()
    except Exception as exc:
        logger.debug("Falha ao resetar cache de sort de texto misto: %s", exc)
    try:
        non_null_cols_attr = (
            attrs.get("ssa_non_null_cols") if preprocessed_for_gui else None
        )
        if isinstance(non_null_cols_attr, list):
            non_null_cols = {str(col) for col in non_null_cols_attr if str(col)}
        else:
            non_null_cols = set(DataLoaderWorker._build_non_null_columns(df_copy))
        window._non_null_cols_cache = non_null_cols
        window._non_null_cols_revision = int(getattr(window, "_data_revision", 0) or 0)
        try:
            df_copy.attrs["ssa_non_null_cols"] = sorted(non_null_cols)
        except Exception as exc:
            logger.debug(
                "Falha ao propagar attrs de colunas nao nulas para df_completo: %s",
                exc,
            )
    except Exception as exc:
        logger.debug("Falha ao calcular cache de colunas nao nulas apos carga: %s", exc)
    try:
        if hasattr(window, "column_selector") and window.column_selector is not None:
            canonical_provider = getattr(
                window, "_get_canonical_available_columns", None
            )
            if callable(canonical_provider):
                available_columns = canonical_provider()
                if available_columns:
                    window.column_selector.available_columns = list(available_columns)
            window.column_selector.set_selected_columns(
                getattr(window, "visible_columns", []) or []
            )
    except Exception as exc:
        logger.debug(
            "Falha ao sincronizar colunas disponiveis apos carga de dados: %s", exc
        )
    try:
        window.clear_filter_button.setEnabled(window._has_any_active_filters())
    except Exception as exc:
        logger.debug(
            "Falha ao avaliar filtros ativos; habilitando botao de limpeza por fallback: %s",
            exc,
        )
        window.clear_filter_button.setEnabled(True)
    window._refresh_after_filter_change()
    try:
        if getattr(window, "_active_filter_panel_kind", None) == "advanced":
            window._refresh_advanced_filter_options()
            window._adv_options_dirty = False
    except Exception as e:
        logger.warning("Falha ao atualizar opcoes de filtros avancados: %s", e)
    current_filter_profile = getattr(window, "current_filter_profile", None)
    profile_hint = (
        f" (perfil: {current_filter_profile})" if current_filter_profile else ""
    )
    try:
        window.update_filter_status_display(
            filtered_total=(
                len(window.df_exibido)
                if hasattr(window, "df_exibido") and window.df_exibido is not None
                else None
            ),
            original_total=(
                len(window.df_completo)
                if hasattr(window, "df_completo") and window.df_completo is not None
                else None
            ),
            search_text=None,
            suffix=(
                f"Pronto para filtrar{profile_hint}."
                if profile_hint
                else "Pronto para filtrar."
            ),
        )
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar status padrao de contagem no load_data_worker: %s",
            exc,
        )
        _set_status_label_text(
            window,
            f"Status: {len(window.df_exibido)} SSAs carregadas{profile_hint}. Pronto para filtrar.",
            context="on_data_loaded.fallback_update_filter_status_display",
        )


def _mask_db_path(error_msg: str, db_path: str | None) -> str:
    if not error_msg or not db_path:
        return error_msg
    try:
        msg = str(error_msg)
        raw = str(db_path)
        db_norm = os.path.normpath(raw)
        candidates = {
            raw,
            db_norm,
            raw.replace("\\", "/"),
            raw.replace("/", "\\"),
            db_norm.replace("\\", "/"),
            db_norm.replace("/", "\\"),
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            candidate_str = str(candidate)
            if candidate_str:
                msg = str(msg).replace(candidate_str, "<db_path>")
        return msg
    except Exception as exc:
        logger.debug(
            "Falha ao mascarar db_path em mensagem de erro; retornando texto bruto: %s",
            exc,
        )
        return error_msg


def on_load_error(
    window,
    error_msg: str,
    *,
    request_id: int | None = None,
    db_path: str | None = None,
    qmessagebox=None,
    global_workers: list | None = None,
    global_meta: dict | None = None,
    max_global_workers: int | None = None,
    retired_ttl_sec: float | None = None,
    retired_force_wait_ms: int | None = None,
    sip_module=None,
):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug(
            "Ignorando erro de carga obsoleto (request_id=%s, active=%s)",
            request_id,
            active_id,
        )
        return
    safe_error_msg = (
        "Nao foi possivel carregar os dados. Consulte os logs para detalhes tecnicos."
    )
    masked_error = _mask_db_path(error_msg, db_path)
    logger.error(
        "Erro no carregamento de dados (request_id=%s): %s", request_id, masked_error
    )
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.debug("PYTEST_CURRENT_TEST set; skipping modal load error dialog.")
    else:
        if qmessagebox is not None:
            qmessagebox.critical(window, "Erro de Carregamento", safe_error_msg)
    _set_status_label_text(
        window,
        "Status: Erro ao carregar dados.",
        context="on_load_error",
    )
    load_button = getattr(window, "load_button", None)
    if load_button is not None and hasattr(load_button, "setEnabled"):
        load_button.setEnabled(True)
    search_button = getattr(window, "search_button", None)
    if search_button is not None and hasattr(search_button, "setEnabled"):
        search_button.setEnabled(True)
    progress_bar = getattr(window, "progress_bar", None)
    if progress_bar is not None and hasattr(progress_bar, "setVisible"):
        progress_bar.setVisible(False)
    if global_workers is not None and global_meta is not None:
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=int(max_global_workers or 0),
                retired_ttl_sec=float(retired_ttl_sec or 0),
                retired_force_wait_ms=int(retired_force_wait_ms or 0),
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao podar workers de carga apos erro: %s", exc)


def on_load_finished(
    window,
    *,
    worker=None,
    request_id: int | None = None,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    active_id = getattr(window, "_active_data_load_request_id", None)
    is_stale = (
        request_id is not None and active_id is not None and request_id != active_id
    )
    target_worker = (
        worker if worker is not None else getattr(window, "data_loader_thread", None)
    )
    if is_stale:
        try:
            cleanup_data_loader_worker(
                window,
                target_worker,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        finally:
            if (
                target_worker is not None
                and getattr(window, "data_loader_thread", None) is target_worker
            ):
                window.data_loader_thread = None
            try:
                prune_retired_data_loader_workers(
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
                    "Falha ao podar workers de carga no cleanup de request obsoleto: %s",
                    exc,
                )
        return

    window.progress_bar.setVisible(False)
    window.load_button.setEnabled(True)
    window.search_button.setEnabled(True)
    status_label = getattr(window, "status_label", None)
    current_status_text = ""
    if status_label is not None:
        try:
            getter = getattr(status_label, "text", None)
            current_status_text = getter() if callable(getter) else str(getter or "")
        except Exception as exc:
            logger.debug("Falha ao ler status atual no fim da carga: %s", exc)
            current_status_text = ""
    if current_status_text == "Status: Carregando dados...":
        try:
            current_df = getattr(window, "df_exibido", None)
            current_count = int(len(current_df.index)) if current_df is not None else 0
        except Exception as exc:
            logger.debug("Falha ao calcular total de SSAs no fim da carga: %s", exc)
            current_count = 0
        _set_status_label_text(
            window,
            f"Status: {current_count} SSAs carregadas. Pronto para filtrar.",
            context="on_load_finished.loading_status_fallback",
        )
    try:
        cleanup_data_loader_worker(
            window,
            target_worker,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    finally:
        if (
            target_worker is not None
            and getattr(window, "data_loader_thread", None) is target_worker
        ):
            window.data_loader_thread = None
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao podar workers de carga no fim do load: %s", exc)


def rescan_data(
    window,
    *,
    project_root: str,
    rescan_worker_cls,
    rescan_dialog_cls,
    qmessagebox,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
    rescan_mode: str = "prompt",
    explicit_files: tuple[str, ...] | None = None,
    source_files: tuple[str, ...] | None = None,
    db_path: str | None = None,
    operation_label: str = "Reescaneamento",
    reload_on_success: bool = False,
    operation_kind: str = "import",
) -> None:
    normalized_mode = str(rescan_mode or "prompt").strip().lower()
    explicit_files_tuple = tuple(str(path) for path in explicit_files or ())
    source_files_tuple = tuple(str(path) for path in source_files or ())
    normalized_kind = str(operation_kind or "import").strip().lower() or "import"
    _ = reload_on_success
    is_explicit_import = bool(explicit_files_tuple or source_files_tuple)
    if is_explicit_import:
        normalized_mode = "explicit"
    if normalized_mode not in {"prompt", "diff", "full", "explicit"}:
        logger.warning(
            "Modo de reescaneamento invalido '%s'; usando prompt.",
            rescan_mode,
        )
        normalized_mode = "prompt"

    force_import = False
    if normalized_mode == "diff":
        force_import = False
    elif normalized_mode == "full":
        force_import = True
    elif normalized_mode == "explicit":
        force_import = False
    elif qmessagebox is not None and hasattr(qmessagebox, "StandardButton"):
        prompt = qmessagebox(window)
        prompt.setWindowTitle("Reescanear")
        prompt.setText("Escolha como atualizar os dados.")
        prompt.setInformativeText(
            "Atualizar Dados processa apenas arquivos novos ou alterados. "
            "Reescaneamento Completo recria o banco do zero e reprocessa tudo."
        )
        diff_btn = prompt.addButton(
            "Atualizar Dados", qmessagebox.ButtonRole.ActionRole
        )
        full_btn = prompt.addButton(
            "Reescaneamento Completo", qmessagebox.ButtonRole.ActionRole
        )
        cancel_btn = prompt.addButton(qmessagebox.StandardButton.Cancel)
        try:
            prompt.setDefaultButton(diff_btn)
        except (RuntimeError, TypeError, AttributeError) as exc:
            logger.debug(
                "Falha ao definir botao padrao no prompt de reescaneamento: %s", exc
            )
        prompt.exec()
        clicked = prompt.clickedButton()
        if clicked is None or clicked == cancel_btn:
            _set_status_label_text(
                window,
                "Status: Reescaneamento cancelado pelo usuario.",
                context="rescan.cancel.mode",
            )
            return
        force_import = clicked == full_btn
    else:
        logger.warning(
            "QMessageBox indisponivel em modo prompt; usando Atualizar Dados por seguranca."
        )

    try:
        prune_retired_rescan_workers(
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
            "Falha ao podar rescan workers antes de iniciar novo rescan: %s", exc
        )

    active_worker = getattr(window, "_active_rescan_worker", None)
    if active_worker is not None:
        try:
            if is_rescan_worker_running(active_worker, sip_module):
                running_text, running_context = _already_running_status_text(
                    is_explicit_import=is_explicit_import,
                    operation_kind=normalized_kind,
                )
                _set_status_label_text(
                    window,
                    running_text,
                    context=running_context,
                )
                return
        except Exception as exc:
            logger.debug("Falha ao checar worker ativo de reescaneamento: %s", exc)
        try:
            if getattr(window, "_active_rescan_worker", None) is active_worker:
                window._active_rescan_worker = None
        except Exception as exc:
            logger.debug(
                "Falha ao limpar referencia stale de worker ativo de reescaneamento: %s",
                exc,
            )

    main_py_path = os.path.join(project_root, "main.py")
    if not os.path.exists(main_py_path):
        logger.warning(
            "Arquivo main.py nao encontrado em '%s'. Prosseguindo com reescaneamento modular sem subprocess.",
            main_py_path,
        )
        main_py_path = "main.py"

    progress_dialog = rescan_dialog_cls(window)
    _configure_operation_dialog(progress_dialog, operation_label)
    try:
        window._active_rescan_dialog = progress_dialog
    except Exception as exc:
        logger.debug(
            "Falha ao registrar referencia do dialogo de reescaneamento: %s", exc
        )

    worker = _build_rescan_worker(
        rescan_worker_cls,
        main_py_path=main_py_path,
        project_root=project_root,
        force_import=force_import,
        explicit_files=explicit_files_tuple,
        source_files=source_files_tuple,
        db_path=db_path,
        operation_label=operation_label,
        operation_kind=normalized_kind,
    )
    window._active_rescan_worker = worker

    _connect_signal(
        worker.output_line, progress_dialog.append_output, label="rescan.output_line"
    )
    _connect_signal(
        worker.error_line, progress_dialog.append_error, label="rescan.error_line"
    )
    _connect_signal(
        worker.progress, progress_dialog.update_progress, label="rescan.progress"
    )

    cancelled = False

    def _release_worker_ref(*_args) -> None:
        try:
            if getattr(window, "_active_rescan_worker", None) is worker:
                window._active_rescan_worker = None
        except Exception as exc:
            logger.debug("Falha ao liberar referencia do RescanWorker: %s", exc)
        try:
            with _GLOBAL_WORKERS_LOCK:
                if worker in global_workers:
                    global_workers.remove(worker)
                global_meta.pop(worker, None)
        except Exception as exc:
            logger.debug(
                "Falha ao remover referencias globais do RescanWorker: %s", exc
            )

    def _release_dialog_ref(*_args) -> None:
        try:
            if getattr(window, "_active_rescan_dialog", None) is progress_dialog:
                window._active_rescan_dialog = None
        except Exception as exc:
            logger.debug(
                "Falha ao liberar referencia do dialogo de reescaneamento: %s", exc
            )

    def _prune_retired_workers_after_finish(*_args) -> None:
        try:
            prune_retired_rescan_workers(
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

    def on_success():
        nonlocal cancelled
        outcome = getattr(worker, "last_outcome", RescanOutcome.UPDATED)
        if not isinstance(outcome, RescanOutcome):
            try:
                outcome = RescanOutcome(str(outcome or RescanOutcome.UPDATED.value))
            except ValueError:
                outcome = RescanOutcome.UPDATED
        if cancelled:
            progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
            _set_status_label_text(
                window,
                (
                    "Status: Consolidacao de arquivos cancelada."
                    if normalized_kind == "consolidate"
                    else "Status: Importacao externa cancelada."
                    if is_explicit_import
                    else "Status: Reescaneamento cancelado."
                ),
                context=(
                    "consolidate.success.cancelled"
                    if normalized_kind == "consolidate"
                    else "explicit_import.success.cancelled"
                    if is_explicit_import
                    else "rescan.success.cancelled"
                ),
            )
            _release_worker_ref()
            _release_dialog_ref()
            return
        _release_worker_ref()
        progress_dialog.set_finished(True)
        _release_dialog_ref()
        should_reload_data = (
            outcome == RescanOutcome.UPDATED
            and normalized_kind != "consolidate"
            and hasattr(window, "load_data")
        )
        success_text = (
            _consolidation_status_text(outcome)
            if normalized_kind == "consolidate"
            else _success_status_text(is_explicit_import, outcome)
        )
        _set_status_label_text(
            window,
            success_text,
            context=(
                "consolidate.success.done"
                if normalized_kind == "consolidate"
                else "explicit_import.success.done"
                if is_explicit_import
                else "rescan.success.done"
            ),
        )
        if should_reload_data:
            try:
                window.load_data()
            except Exception as exc:
                logger.warning(
                    "Falha ao recarregar dados apos operacao concluida: %s", exc
                )

    def on_error(error_msg):
        nonlocal cancelled
        if cancelled or str(error_msg).strip().lower().startswith("processo cancelado"):
            cancelled = True
            progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
            _set_status_label_text(
                window,
                (
                    "Status: Consolidacao de arquivos cancelada."
                    if normalized_kind == "consolidate"
                    else "Status: Importacao externa cancelada."
                    if is_explicit_import
                    else "Status: Reescaneamento cancelado."
                ),
                context=(
                    "consolidate.error.cancelled"
                    if normalized_kind == "consolidate"
                    else "explicit_import.error.cancelled"
                    if is_explicit_import
                    else "rescan.error.cancelled"
                ),
            )
            _release_worker_ref()
            _release_dialog_ref()
            return
        progress_dialog.set_finished(False, error_msg)
        _release_dialog_ref()
        _set_status_label_text(
            window,
            (
                "Status: Erro na consolidacao de arquivos."
                if normalized_kind == "consolidate"
                else "Status: Erro na importacao externa."
                if is_explicit_import
                else "Status: Erro no reescaneamento."
            ),
            context=(
                "consolidate.error"
                if normalized_kind == "consolidate"
                else "explicit_import.error"
                if is_explicit_import
                else "rescan.error"
            ),
        )
        _release_worker_ref()

    _connect_signal(
        worker.finished_success, on_success, label="rescan.finished_success"
    )
    _connect_signal(worker.finished_error, on_error, label="rescan.finished_error")
    _connect_signal(
        worker.finished, _release_worker_ref, label="rescan.finished.release"
    )
    _connect_signal(
        worker.finished, _release_dialog_ref, label="rescan.finished.dialog_release"
    )
    _connect_signal(
        worker.finished,
        _prune_retired_workers_after_finish,
        label="rescan.finished.prune",
    )
    _connect_signal(
        worker.finished, worker.deleteLater, label="rescan.finished.deleteLater"
    )
    if hasattr(progress_dialog, "finished"):
        _connect_signal(
            progress_dialog.finished,
            _release_dialog_ref,
            label="rescan.dialog.finished.release",
        )

    def on_cancel_requested():
        nonlocal cancelled
        cancelled = True
        running = is_rescan_worker_running(worker, sip_module)
        cancel_text, cancel_context = _cancel_request_status_text(
            is_explicit_import, normalized_kind
        )
        _set_status_label_text(
            window,
            cancel_text,
            context=cancel_context,
        )
        if running:
            try:
                if hasattr(worker, "stop"):
                    worker.stop()
            except Exception as exc:
                logger.debug(
                    "Falha ao solicitar stop do RescanWorker no cancelamento: %s", exc
                )

    progress_dialog.cancel_requested.connect(on_cancel_requested)

    worker.start()
    if normalized_kind == "consolidate":
        _set_status_label_text(
            window,
            "Status: Consolidacao de arquivos em andamento.",
            context="consolidate.started",
        )
    elif not is_explicit_import:
        _set_status_label_text(
            window,
            "Status: Reescaneamento em andamento.",
            context="rescan.started",
        )
    with _GLOBAL_WORKERS_LOCK:
        if worker not in global_workers:
            global_workers.append(worker)
        global_meta[worker] = perf_counter()
    if hasattr(progress_dialog, "show_non_modal"):
        progress_dialog.show_non_modal()
    else:
        progress_dialog.show()
