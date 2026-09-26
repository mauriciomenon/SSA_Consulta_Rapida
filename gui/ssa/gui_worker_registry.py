# gui/ssa/gui_worker_registry.py
# Relation: worker retention primitives used by gui/ssa/gui_workers.py.

from __future__ import annotations

import threading
from typing import Callable

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")

GLOBAL_WORKERS_LOCK = threading.Lock()


def _classify_workers_for_ttl(
    workers: list,
    *,
    global_meta: dict,
    now: float,
    retired_ttl_sec: float,
    max_global_workers: int,
    is_running_fn: Callable[[object], bool],
) -> tuple[list, list]:
    running_workers: list = []
    expired_workers: list = []
    expired_set: set = set()
    for worker in list(workers):
        if not is_running_fn(worker):
            global_meta.pop(worker, None)
            continue
        started_at = global_meta.get(worker, now)
        age = now - started_at
        if age > retired_ttl_sec:
            expired_workers.append(worker)
            expired_set.add(worker)
        running_workers.append(worker)
    if max_global_workers > 0 and len(running_workers) > max_global_workers:
        overflow_count = len(running_workers) - max_global_workers
        overflow_workers = sorted(
            running_workers,
            key=lambda candidate: now - float(global_meta.get(candidate, now)),
            reverse=True,
        )[:overflow_count]
        expired_workers.extend(
            worker for worker in overflow_workers if worker not in expired_set
        )
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
    stop_worker_fn: Callable[[object], bool],
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
            with GLOBAL_WORKERS_LOCK:
                if worker in global_workers:
                    global_workers.remove(worker)
                global_meta.pop(worker, None)
        else:
            with GLOBAL_WORKERS_LOCK:
                global_meta[worker] = now
    return removed_workers


def _classify_and_update_global_workers_locked(
    *,
    global_workers: list,
    global_meta: dict,
    now: float,
    retired_ttl_sec: float,
    max_global_workers: int,
    is_running_fn: Callable[[object], bool],
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
