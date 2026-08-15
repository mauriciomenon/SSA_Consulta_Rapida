"""Qt thread primitives with a headless fallback for worker tests.

The fallback does not emulate Qt queued connections or object affinity.
Fallback signal slots run synchronously on the emitting thread.
"""

from __future__ import annotations

import threading
from typing import Any, cast

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except Exception:

    class _SignalInstance:
        def __init__(self) -> None:
            self._slots: list[Any] = []
            self._lock = threading.RLock()

        def connect(self, slot, *_args, **_kwargs):
            with self._lock:
                self._slots.append(slot)

        def emit(self, *args, **kwargs):
            with self._lock:
                slots = list(self._slots)
            for slot in slots:
                slot(*args, **kwargs)

    class _SignalDescriptor:
        is_qt_signal_fallback = True

        def __set_name__(self, _owner, name):
            self._name = name

        def __get__(self, instance, _owner):
            if instance is None:
                return self
            signal = instance.__dict__.get(self._name)
            if signal is None:
                signal = _SignalInstance()
                instance.__dict__[self._name] = signal
            return signal

    def _fallback_pyqt_signal(*_args, **_kwargs):
        return _SignalDescriptor()

    class _FallbackQThread:
        def __init__(self, *_args, **_kwargs) -> None:
            self._running = False
            self._thread = None
            _initialize_fallback_signals(self)

        def start(self) -> None:
            if self._running:
                return

            def _target() -> None:
                self._running = True
                try:
                    self.run()
                finally:
                    self._running = False

            thread = threading.Thread(target=_target, daemon=True)
            self._thread = thread
            thread.start()

        def run(self) -> None:
            return None

        def isRunning(self) -> bool:
            return bool(self._running)

        def wait(self, timeout_ms: int | None = None) -> bool:
            thread = self._thread
            if thread is None:
                return True
            timeout = None if timeout_ms is None else max(timeout_ms, 0) / 1000
            thread.join(timeout)
            return not thread.is_alive()

    pyqtSignal = cast(Any, _fallback_pyqt_signal)
    QThread = cast(Any, _FallbackQThread)


def _initialize_fallback_signals(instance: object) -> None:
    for cls in type(instance).mro():
        for name, value in vars(cls).items():
            if getattr(value, "is_qt_signal_fallback", False):
                getattr(instance, name)
