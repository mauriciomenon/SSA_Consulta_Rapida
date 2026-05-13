from __future__ import annotations

from gui.mixins import filter_gui_ssa_mixin as filter_mixin


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


class _SignalKeywordQueuedOnly:
    def __init__(self, queued_token):
        self.queued_token = queued_token
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.positional_typeerror_count = 0

    def connect(self, _slot, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args:
            self.positional_typeerror_count += 1
            raise TypeError("positional type not supported")
        if kwargs.get("type") is self.queued_token:
            return None
        raise AssertionError("unexpected fallback path for keyword queued signal")


def test_connect_filter_signal_prefers_positional_queued(monkeypatch):
    queued_token = object()
    signal = _SignalPositionalQueuedOnly(queued_token)
    monkeypatch.setattr(filter_mixin, "_FILTER_QT_QUEUED", queued_token, raising=True)

    connected = filter_mixin._connect_filter_signal(
        signal, lambda: None, label="test.positional"
    )

    assert connected is True
    assert len(signal.calls) == 1
    args, kwargs = signal.calls[0]
    assert args == (queued_token,)
    assert kwargs == {}


def test_connect_filter_signal_falls_back_to_keyword_queued(monkeypatch):
    queued_token = object()
    signal = _SignalKeywordQueuedOnly(queued_token)
    monkeypatch.setattr(filter_mixin, "_FILTER_QT_QUEUED", queued_token, raising=True)

    connected = filter_mixin._connect_filter_signal(
        signal, lambda: None, label="test.keyword"
    )

    assert connected is True
    assert len(signal.calls) == 2
    first_args, first_kwargs = signal.calls[0]
    second_args, second_kwargs = signal.calls[1]
    assert first_args == (queued_token,)
    assert first_kwargs == {}
    assert signal.positional_typeerror_count == 1
    assert second_args == ()
    assert second_kwargs == {"type": queued_token}


def test_connect_filter_signal_never_uses_python_type_as_connection(monkeypatch):
    class _SignalDefaultOnly:
        def __init__(self):
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def connect(self, _slot, *args, **kwargs):
            self.calls.append((args, kwargs))
            if args or kwargs:
                raise AssertionError("type object must not be used as connection type")

    signal = _SignalDefaultOnly()
    monkeypatch.setattr(filter_mixin, "_FILTER_QT_QUEUED", type, raising=True)

    connected = filter_mixin._connect_filter_signal(
        signal, lambda: None, label="test.type-object"
    )

    assert connected is True
    assert signal.calls == [((), {})]


def test_connect_filter_signal_returns_false_for_missing_signal():
    connected = filter_mixin._connect_filter_signal(
        None, lambda: None, label="test.none"
    )
    assert connected is False
