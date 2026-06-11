"""Lifecycle control for GUI filter workers."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

MAX_GLOBAL_RETIRED_FILTER_WORKERS = 64


def _is_deleted_qt_object_error(exc: Exception) -> bool:
    text = str(exc)
    return "wrapped C/C++ object" in text and "has been deleted" in text


def _is_disconnected_signal_error(exc: Exception) -> bool:
    text = str(exc).casefold()
    return "disconnect" in text and (
        "no connection" in text
        or "not connected" in text
        or "failed" in text
    )


class DeferredFilterWorkerRegistry:
    """Explicit registry for workers that outlive a filter request."""

    def __init__(self, max_workers: int = MAX_GLOBAL_RETIRED_FILTER_WORKERS):
        self.max_workers = int(max_workers)
        self._workers: OrderedDict[int, Any] = OrderedDict()

    def snapshot(self) -> list[Any]:
        return list(self._workers.values())

    def clear(self) -> None:
        self._workers.clear()

    def replace(self, workers: list[Any]) -> None:
        self._workers.clear()
        for worker in workers:
            self.add(worker)

    def contains(self, worker: Any) -> bool:
        return id(worker) in self._workers

    def add(self, worker: Any) -> None:
        self._workers[id(worker)] = worker

    def remove(self, worker: Any) -> None:
        self._workers.pop(id(worker), None)

    def prune(self, is_running: Callable[[Any], bool]) -> None:
        for worker_id, worker in list(self._workers.items()):
            if not is_running(worker):
                self._workers.pop(worker_id, None)
        while len(self._workers) > self.max_workers:
            self._workers.popitem(last=False)


class FilterWorkerLifecycle:
    """Owns cancellation and delayed release of filter worker references."""

    def __init__(
        self,
        logger: Any,
        connect_signal: Callable[..., bool],
        registry: DeferredFilterWorkerRegistry,
        get_active_worker: Callable[[], Any],
        clear_active_worker: Callable[[Any], None],
    ):
        self.logger = logger
        self._connect_signal = connect_signal
        self.registry = registry
        self._get_active_worker = get_active_worker
        self._clear_active_worker = clear_active_worker

    def deactivate_active(self, reason: str = "") -> None:
        worker = self._get_active_worker()
        if worker is None:
            return
        stopped = False
        handed_over = False
        try:
            stopped = self.cleanup(worker)
            handed_over = stopped or self.registry.contains(worker)
        except Exception as exc:
            self.logger.debug(
                "Falha ao cancelar worker ativo (%s): %s",
                reason or "sem_motivo",
                exc,
            )
            try:
                self.retain_until_finished(worker)
                handed_over = self.registry.contains(worker)
            except Exception as retain_exc:
                self.logger.warning(
                    "Falha ao reter worker ativo apos erro de desativacao: %s",
                    retain_exc,
                )
        finally:
            if handed_over or not self.is_running(worker):
                self._clear_active_worker(worker)
        if reason:
            status = "cancelado" if stopped else "retido_ate_finalizar"
            self.logger.debug("Worker anterior %s (%s)", status, reason)

    def retain_until_finished(self, worker: Any) -> None:
        if worker is None:
            return
        if self.registry.contains(worker):
            return
        self.registry.add(worker)

        if not self._connect_release_handlers(worker):
            self.registry.remove(worker)
            return
        try:
            self.prune()
        except Exception as exc:
            self.logger.debug(
                "Falha ao podar lista de workers de filtro aposentados: %s", exc
            )

    def _connect_release_handlers(self, worker: Any) -> bool:
        released = False

        def _release_worker_ref(*_args: Any, w: Any = worker) -> None:
            nonlocal released
            if released:
                return
            released = True
            try:
                self.registry.remove(w)
            except Exception as exc:
                self.logger.debug(
                    "Falha ao remover worker da lista global de aposentados: %s", exc
                )

        if not self._connect_signal(
            worker.finished,
            _release_worker_ref,
            label="filter_worker.finished.release",
        ):
            self.logger.debug(
                "Falha ao conectar release de worker finalizado; liberando referencia imediato."
            )
            return False
        if not self._connect_signal(
            worker.finished,
            worker.deleteLater,
            label="filter_worker.finished.deleteLater",
        ):
            self.logger.debug("Falha ao conectar deleteLater do worker de filtro.")
        destroyed_signal = getattr(worker, "destroyed", None)
        if destroyed_signal is not None:
            self._connect_signal(
                destroyed_signal,
                _release_worker_ref,
                label="filter_worker.destroyed.release",
            )
        return True

    def is_running(self, worker: Any) -> bool:
        if worker is None:
            return False
        try:
            if hasattr(worker, "isRunning"):
                return bool(worker.isRunning())
        except Exception as exc:
            self.logger.debug("Falha ao verificar estado do worker de filtro: %s", exc)
        return False

    def prune(self) -> None:
        self.registry.prune(self.is_running)

    def cleanup(self, worker: Any) -> bool:
        if worker is None:
            return True
        try:
            still_running = self._request_worker_stop(worker)
            if still_running:
                self.retain_until_finished(worker)
                return False
            self._disconnect_worker_signals(worker)
            try:
                worker.deleteLater()
            except Exception as exc:
                if _is_deleted_qt_object_error(exc):
                    self.registry.remove(worker)
                    return True
                self.logger.debug("Falha ao chamar deleteLater no worker de filtro: %s", exc)
            try:
                self.prune()
            except Exception as exc:
                self.logger.debug("Falha ao podar workers de filtro apos cleanup: %s", exc)
        except Exception as exc:
            if _is_deleted_qt_object_error(exc):
                self.registry.remove(worker)
                return True
            self.logger.warning("Falha durante cleanup do worker de filtro: %s", exc)
            return False
        return True

    def _disconnect_worker_signals(self, worker: Any) -> None:
        for signal_name in ("filter_finished", "error_occurred"):
            signal = getattr(worker, signal_name, None)
            if signal is None:
                continue
            try:
                signal.disconnect()
            except Exception as exc:
                if _is_deleted_qt_object_error(exc):
                    continue
                if isinstance(exc, (TypeError, RuntimeError)) and (
                    _is_disconnected_signal_error(exc)
                ):
                    continue
                self.logger.debug(
                    "Falha ao desconectar %s do worker de filtro: %s",
                    signal_name,
                    exc,
                )

    def _request_worker_stop(self, worker: Any) -> bool:
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            elif hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            if hasattr(worker, "isRunning") and worker.isRunning():
                worker.quit()
            return bool(hasattr(worker, "isRunning") and worker.isRunning())
        except Exception as exc:
            if _is_deleted_qt_object_error(exc):
                self.registry.remove(worker)
                return False
            self.logger.warning(
                "Falha ao solicitar encerramento do worker de filtro: %s", exc
            )
            return True
