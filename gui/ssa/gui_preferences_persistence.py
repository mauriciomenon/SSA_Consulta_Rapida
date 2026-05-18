from __future__ import annotations

import copy
import queue
import threading
import time
from collections.abc import Callable

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
        self._queue: queue.Queue[dict | None] = queue.Queue()
        self._stopped = False
        self._thread = threading.Thread(
            target=self._run,
            name="ssa-gui-prefs-writer",
            daemon=True,
        )
        self._thread.start()

    def persist_async(self, gui_prefs: dict) -> None:
        with self._lock:
            if self._stopped:
                return
            self._queue.put(_snapshot_preferences(gui_prefs))

    def _run(self) -> None:
        while True:
            prefs_snapshot = self._queue.get()
            if prefs_snapshot is None:
                return
            time.sleep(self._debounce_seconds)
            stop_after_write = False
            while True:
                try:
                    next_snapshot = self._queue.get_nowait()
                except queue.Empty:
                    break
                if next_snapshot is None:
                    stop_after_write = True
                    break
                prefs_snapshot = next_snapshot
            self._write_func(prefs_snapshot, retries=self._retries)
            if stop_after_write:
                return

    def shutdown(self, *, timeout: float = 1.0) -> None:
        with self._lock:
            if not self._stopped:
                self._stopped = True
                self._queue.put(None)
            thread = self._thread
        thread.join(timeout=max(0.0, float(timeout)))


def _snapshot_preferences(gui_prefs: dict) -> dict:
    return copy.deepcopy(gui_prefs)


_GUI_PREFERENCES_WRITER = PreferencesWriter(persist_gui_preferences, retries=1)


def persist_gui_preferences_async(gui_prefs: dict) -> None:
    _GUI_PREFERENCES_WRITER.persist_async(gui_prefs)


def flush_gui_preferences_async(*, timeout: float = 1.0) -> None:
    _GUI_PREFERENCES_WRITER.shutdown(timeout=timeout)
