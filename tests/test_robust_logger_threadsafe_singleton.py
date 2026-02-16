import threading
import time

import utils.robust_logging as robust_logging


def test_get_robust_logger_is_thread_safe_singleton(monkeypatch):
    monkeypatch.setattr(robust_logging, "_robust_logger", None)

    created = {"count": 0}

    class _StubRobustLogger:
        def __init__(self, _config_path=None):
            created["count"] += 1
            # Widen race window for non-thread-safe implementations.
            time.sleep(0.05)

        def get_logger(self, *_args, **_kwargs):
            raise AssertionError("not used")

    monkeypatch.setattr(robust_logging, "RobustLogger", _StubRobustLogger)

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def _worker():
        try:
            barrier.wait(timeout=2.0)
            results.append(robust_logging.get_robust_logger("x"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=_worker)
    t2 = threading.Thread(target=_worker)
    t1.start()
    t2.start()
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)

    assert not t1.is_alive(), "t1 did not complete in time"
    assert not t2.is_alive(), "t2 did not complete in time"
    assert errors == []
    assert len(results) == 2
    assert results[0] is results[1]
    assert created["count"] == 1
