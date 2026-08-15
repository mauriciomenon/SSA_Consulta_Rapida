from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any

from core.config_manager import atomic_write_json_file
from gui.gui_config import get_gui_main_preferences_path
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def persist_gui_preferences(gui_prefs: dict, *, retries: int = 1) -> bool:
    attempts = max(0, int(retries or 0)) + 1
    for attempt in range(attempts):
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
                gui_prefs,
                indent=2,
                ensure_ascii=False,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Falha ao persistir preferencias GUI (tentativa %s/%s): %s",
                attempt + 1,
                attempts,
                exc,
            )
    return False


class PreferencesWriter:
    def __init__(
        self,
        write_func: Callable[..., bool],
        *,
        debounce_seconds: float = 0.05,
        retries: int = 1,
    ) -> None:
        self._write_func = write_func
        self._debounce_seconds = debounce_seconds
        self._retries = retries
        self._lock = threading.Lock()
        self._queue: queue.Queue[dict[Any, Any] | None] = queue.Queue()
        self._stopped = False
        self._terminated = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="ssa-gui-prefs-writer",
            daemon=True,
        )
        self._thread.start()

    def persist_async(self, gui_prefs: dict) -> bool:
        """Queue a preferences write and return only the enqueue status."""
        with self._lock:
            if self._stopped:
                return False
            self._queue.put(_snapshot_preferences(gui_prefs))
            return True

    @property
    def is_stopped(self) -> bool:
        with self._lock:
            return self._stopped

    @property
    def is_terminated(self) -> bool:
        return self._terminated.is_set()

    def _run(self) -> None:
        try:
            while True:
                prefs_snapshot = self._queue.get()
                if prefs_snapshot is None:
                    self._queue.task_done()
                    return
                try:
                    prefs_snapshot, stop_after_write = self._drain_latest_snapshot(
                        prefs_snapshot
                    )
                    self._write_func(
                        prefs_snapshot,
                        retries=self._retries,
                    )
                finally:
                    self._queue.task_done()
                if stop_after_write:
                    return
        finally:
            self._terminated.set()

    def _drain_latest_snapshot(
        self, prefs_snapshot: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        stop_after_write = False
        while True:
            try:
                next_snapshot = self._queue.get(timeout=self._debounce_seconds)
            except queue.Empty:
                break
            if next_snapshot is None:
                stop_after_write = True
                self._queue.task_done()
                continue
            prefs_snapshot = next_snapshot
            self._queue.task_done()
        return prefs_snapshot, stop_after_write

    def shutdown(self, *, timeout: float | None = 1.0) -> None:
        with self._lock:
            if not self._stopped:
                self._stopped = True
                self._queue.put(None)
            thread = self._thread
        if timeout is None:
            thread.join()
            return
        thread.join(timeout=max(0.0, float(timeout)))


def _snapshot_preferences(gui_prefs: dict) -> dict:
    return {
        key: _snapshot_json_value(value)
        for key, value in gui_prefs.items()
    }


def _snapshot_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _snapshot_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_snapshot_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_snapshot_json_value(item) for item in value]
    return value


_GUI_PREFERENCES_WRITER_LOCK = threading.Lock()
_GUI_PREFERENCES_WRITER = PreferencesWriter(persist_gui_preferences, retries=1)


def _get_gui_preferences_writer() -> PreferencesWriter:
    global _GUI_PREFERENCES_WRITER
    with _GUI_PREFERENCES_WRITER_LOCK:
        if not _GUI_PREFERENCES_WRITER.is_stopped:
            return _GUI_PREFERENCES_WRITER
        if not _GUI_PREFERENCES_WRITER.is_terminated:
            return _GUI_PREFERENCES_WRITER
        _GUI_PREFERENCES_WRITER = PreferencesWriter(
            persist_gui_preferences,
            retries=1,
        )
        return _GUI_PREFERENCES_WRITER


def persist_gui_preferences_async(gui_prefs: dict) -> bool:
    """Queue GUI preferences for async persistence.

    The return value confirms only that the update was accepted by the writer.
    Disk write failures are logged by the background writer.
    """
    return _get_gui_preferences_writer().persist_async(gui_prefs)


def shutdown_gui_preferences_writer(*, timeout: float = 1.0) -> None:
    with _GUI_PREFERENCES_WRITER_LOCK:
        writer = _GUI_PREFERENCES_WRITER
    writer.shutdown(timeout=timeout)
