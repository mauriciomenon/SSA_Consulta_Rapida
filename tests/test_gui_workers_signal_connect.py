from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from gui.ssa import gui_workers
from gui.workers.data_loader_worker import DataLoaderWorker


class _SignalPositionalQueuedOnly:
    def __init__(self, queued_token):
        self.queued_token = queued_token
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def connect(self, _slot, *args, **kwargs):
        self.calls.append((args, kwargs))
        if kwargs:
            raise TypeError("keyword type not supported")
        if len(args) == 1 and args[0] is self.queued_token:
            return None
        raise AssertionError("unexpected fallback path for positional queued signal")


class _SignalPlainFallbackOnly:
    def __init__(self, queued_token):
        self.queued_token = queued_token
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def connect(self, _slot, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args:
            raise TypeError("positional type not supported")
        if not kwargs:
            return None
        raise AssertionError("unexpected fallback path for keyword queued signal")


def test_connect_signal_prefers_positional_queued(monkeypatch):
    queued_token = object()
    signal = _SignalPositionalQueuedOnly(queued_token)
    monkeypatch.setattr(gui_workers, "_QT_QUEUED", queued_token, raising=True)

    connected = gui_workers._connect_signal(
        signal, lambda: None, label="test.positional"
    )

    assert connected is True
    assert len(signal.calls) == 1
    args, kwargs = signal.calls[0]
    assert args == (queued_token,)
    assert kwargs == {}


def test_connect_signal_falls_back_to_plain_connect(monkeypatch):
    queued_token = object()
    signal = _SignalPlainFallbackOnly(queued_token)
    monkeypatch.setattr(gui_workers, "_QT_QUEUED", queued_token, raising=True)

    connected = gui_workers._connect_signal(signal, lambda: None, label="test.plain")

    assert connected is True
    assert len(signal.calls) == 2
    first_args, first_kwargs = signal.calls[0]
    second_args, second_kwargs = signal.calls[1]
    assert first_args == (queued_token,)
    assert first_kwargs == {}
    assert second_args == ()
    assert second_kwargs == {}


def test_sanitize_ssa_like_value_handles_broken_str() -> None:
    class _BrokenStr:
        def __str__(self) -> str:
            raise RuntimeError("broken str")

    assert DataLoaderWorker._sanitize_ssa_like_value(_BrokenStr()) == ""


def test_load_data_missing_db_without_status_label_under_pytest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    missing_db = tmp_path / "missing.db"

    warning_calls: list[tuple[object, str, str]] = []

    class _MessageBoxStub:
        @staticmethod
        def warning(window, title, message):
            warning_calls.append((window, title, message))

    dummy_window = SimpleNamespace()

    gui_workers.load_data(
        dummy_window,
        db_path=str(missing_db),
        table_name="ssas",
        data_loader_cls=object,
        qmessagebox=_MessageBoxStub,
        global_workers=[],
        global_meta={},
        max_global_workers=8,
        retired_ttl_sec=5.0,
        retired_force_wait_ms=0,
        sip_module=None,
    )

    assert warning_calls == []
