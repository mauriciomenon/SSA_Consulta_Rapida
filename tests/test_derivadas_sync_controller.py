from __future__ import annotations

import threading
from typing import Any

import pytest

from gui.ssa import derivadas_sync_controller


class _ImmediateTimer:
    @staticmethod
    def singleShot(_msec: int, callback) -> None:
        callback()


class _QueuedTimer:
    callbacks: list[Any] = []

    @classmethod
    def singleShot(cls, _msec: int, callback) -> None:
        cls.callbacks.append(callback)


class _HungThread(threading.Thread):
    def __init__(self, target=None, daemon: bool | None = None, **_kwargs: Any) -> None:
        super().__init__(target=target, daemon=daemon)
        self._target = target

    def start(self) -> None:
        pass


class _AliveThread(threading.Thread):
    def __init__(self, target=None, daemon: bool | None = None, **_kwargs: Any) -> None:
        super().__init__(target=target, daemon=daemon)
        self.started = False
        self.alive = False

    def start(self) -> None:
        self.started = True
        self.alive = True

    def is_alive(self) -> bool:
        return self.alive


class _FailingStartThread(threading.Thread):
    def __init__(self, target=None, daemon: bool | None = None, **_kwargs: Any) -> None:
        super().__init__(target=target, daemon=daemon)

    def start(self) -> None:
        raise RuntimeError("can't start new thread")


@pytest.mark.parametrize("fail_constructor", [False, True])
def test_async_derivadas_start_failure_runs_finalize_to_restore_ui(
    tmp_path, fail_constructor
) -> None:
    """Falha na criacao ou partida restaura o estado e a UI."""
    def create_thread(**kwargs):
        if fail_constructor:
            raise RuntimeError("falha ao criar thread")
        return _FailingStartThread(**kwargs)

    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    state.ui_state = {"status": "before"}
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    finalized: list[dict[str, Any]] = []

    result = derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_ImmediateTimer,
        sip_module=None,
        thread_factory=create_thread,
        execute_job=lambda **_kwargs: pytest.fail("job must not run"),
        finalize_result=lambda _parent, value: finalized.append(value) or value,
        sync_state_callback=None,
    )

    assert result["ok"] is False
    assert result["reason"] == "start_failed"
    assert finalized == [result]
    assert state.thread is None
    assert state.running is False
    assert not sync_lock.locked()
    assert state.ui_state == {"status": "before"}


@pytest.mark.parametrize("stage", ["result", "timeout", "start"])
def test_async_derivadas_finalize_failure_releases_state(monkeypatch, tmp_path, stage):
    _QueuedTimer.callbacks.clear()
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    status = []
    ui = derivadas_sync_controller.DerivadasSyncUiRefs(
        message_parent=object(), status_label=None, progress_bar=None, update_button=None
    )
    times = iter([0.0, float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1)])
    monkeypatch.setattr(derivadas_sync_controller, "monotonic", lambda: next(times))

    def finalize(_parent, result):
        if stage == "result":
            return derivadas_sync_controller.finalize_derivadas_sync_result(
                ui, state, result, qmessagebox=None, logger=derivadas_sync_controller.logger
            )
        state.last_report = result
        raise ValueError("falha ao aplicar resultado")

    db_path = str(tmp_path / "ssas.db")
    result = derivadas_sync_controller._start_async_derivadas_sync(
        ui, state, db_path=db_path, table_name="ssas", special_files=[],
        sync_lock=sync_lock, qtimer=_QueuedTimer, sip_module=None,
        thread_factory=_FailingStartThread if stage == "start" else _AliveThread,
        execute_job=lambda **_kwargs: {}, finalize_result=finalize,
        sync_state_callback=lambda: status.append(state.running),
    )
    worker = state.thread
    if stage == "result":
        state.pending_result = {"ok": True, "merged_edges": "invalido"}
    if stage != "start":
        _QueuedTimer.callbacks.pop(0)()
        assert state.thread is worker
        assert isinstance(worker, _AliveThread) and worker.is_alive()
        if stage == "timeout":
            assert state.running is True
            assert state.cancel_event.is_set()
        worker.alive = False
        if stage == "timeout":
            _QueuedTimer.callbacks.pop(0)()
    else:
        assert result["ok"] is False
        assert result["reason"] == "finalize_failed"
    assert state.running is False
    assert state.last_report is None
    assert state.report_invalidated is True
    assert "Falha ao aplicar" in state.last_status_text
    assert not sync_lock.locked()

    assert derivadas_sync_controller._begin_derivadas_sync(
        ui, state, db_path=db_path, sync_lock=sync_lock,
        sync_state_callback=None,
    ) is None
    assert state.running is True
    assert state.report_invalidated is False
    _QueuedTimer.callbacks.clear()
    monkeypatch.setattr(derivadas_sync_controller, "monotonic", lambda: 0.0)
    retry = derivadas_sync_controller._start_async_derivadas_sync(
        ui, state, db_path=db_path, table_name="ssas", special_files=[],
        sync_lock=sync_lock, qtimer=_QueuedTimer, sip_module=None,
        thread_factory=_HungThread, execute_job=lambda **_kwargs: {},
        finalize_result=lambda _parent, result: derivadas_sync_controller.finalize_derivadas_sync_result(
            ui, state, result, qmessagebox=None, logger=derivadas_sync_controller.logger
        ), sync_state_callback=None,
    )
    state.pending_result = {"ok": True, "merged_edges": 1}
    _QueuedTimer.callbacks.pop(0)()
    assert retry["started"] is True
    assert state.running is False
    assert "total=1" in state.last_status_text


def test_async_derivadas_timeout_marks_state_finished_for_finalize_callback(
    monkeypatch,
    tmp_path,
) -> None:
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    state.ui_state = {"status": "before"}
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    finalized: list[tuple[dict[str, Any], bool]] = []
    monotonic_values = iter(
        [
            0.0,
            float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1),
        ]
    )
    monkeypatch.setattr(
        derivadas_sync_controller,
        "monotonic",
        lambda: next(monotonic_values),
    )

    result = derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_ImmediateTimer,
        sip_module=None,
        thread_factory=_HungThread,
        execute_job=lambda **_kwargs: pytest.fail(
            "_HungThread must not execute the sync job"
        ),
        finalize_result=lambda _parent, value: finalized.append(
            (value, state.running)
        )
        or value,
        sync_state_callback=None,
    )

    assert result["started"] is True
    assert finalized == [
        (
            {
                "ok": False,
                "error": derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_ERROR,
            },
            False,
        )
    ]
    assert state.running is False
    assert state.pending_result is None
    assert state.thread is None
    assert not sync_lock.locked()


def test_async_derivadas_timeout_delivers_result_that_arrives_during_timeout(
    monkeypatch,
    tmp_path,
) -> None:
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    worker_result = {"ok": True, "merged_edges": 1}
    finalized: list[dict[str, Any]] = []
    monotonic_calls = 0

    def _monotonic() -> float:
        nonlocal monotonic_calls
        monotonic_calls += 1
        if monotonic_calls == 1:
            return 0.0
        with sync_lock:
            state.pending_result = worker_result
        return float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1)

    monkeypatch.setattr(derivadas_sync_controller, "monotonic", _monotonic)

    result = derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_ImmediateTimer,
        sip_module=None,
        thread_factory=_HungThread,
        execute_job=lambda **_kwargs: pytest.fail(
            "_HungThread must not execute the sync job"
        ),
        finalize_result=lambda _parent, value: finalized.append(value) or value,
        sync_state_callback=None,
    )

    assert result["started"] is True
    assert finalized == [worker_result]
    assert state.running is False
    assert state.pending_result is None
    assert not sync_lock.locked()


def test_async_derivadas_discards_result_after_timeout(
    monkeypatch,
    tmp_path,
) -> None:
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    finalized: list[dict[str, Any]] = []
    workers: list[_HungThread] = []
    monotonic_values = iter(
        [
            0.0,
            float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1),
        ]
    )
    monkeypatch.setattr(
        derivadas_sync_controller,
        "monotonic",
        lambda: next(monotonic_values),
    )

    def _thread_factory(**kwargs: Any) -> _HungThread:
        worker = _HungThread(**kwargs)
        workers.append(worker)
        return worker

    result = derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_ImmediateTimer,
        sip_module=None,
        thread_factory=_thread_factory,
        execute_job=lambda **_kwargs: {"ok": True, "merged_edges": 1},
        finalize_result=lambda _parent, value: finalized.append(value) or value,
        sync_state_callback=None,
    )

    assert result["started"] is True
    assert finalized == [
        {
            "ok": False,
            "error": derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_ERROR,
        }
    ]

    assert workers[0]._target is not None
    workers[0]._target()

    assert len(finalized) == 1
    assert state.pending_result is None
    assert state.running is False


def test_async_derivadas_timeout_rejects_second_start_while_worker_alive(
    monkeypatch,
    tmp_path,
) -> None:
    _QueuedTimer.callbacks.clear()
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    finalized: list[dict[str, Any]] = []
    monotonic_values = iter(
        [
            0.0,
            float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1),
        ]
    )
    monkeypatch.setattr(
        derivadas_sync_controller,
        "monotonic",
        lambda: next(monotonic_values),
    )

    result = derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_QueuedTimer,
        sip_module=None,
        thread_factory=_AliveThread,
        execute_job=lambda **_kwargs: pytest.fail(
            "_AliveThread keeps the sync job running"
        ),
        finalize_result=lambda _parent, value: finalized.append(value) or value,
        sync_state_callback=None,
    )

    _QueuedTimer.callbacks.pop(0)()
    assert result["started"] is True
    assert finalized == []
    assert state.running is True
    assert state.cancel_event.is_set()
    assert state.thread is not None

    second = derivadas_sync_controller._begin_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        sync_lock=sync_lock,
        sync_state_callback=None,
    )

    assert second == {
        "ok": False,
        "reason": "already_running",
        "db_path": str(tmp_path / "ssas.db"),
        "table_name": "",
    }


def test_timeout_requests_cancellation_without_finalizing_live_worker(
    monkeypatch, tmp_path
) -> None:
    _QueuedTimer.callbacks.clear()
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    working = threading.Event()
    release = threading.Event()
    finalized: list[dict[str, Any]] = []
    times = iter([0.0, float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1)])
    monkeypatch.setattr(derivadas_sync_controller, "monotonic", lambda: next(times))

    def execute_job(**kwargs):
        working.set()
        assert release.wait(timeout=5)
        if kwargs["cancel_event"].is_set():
            kwargs["status_callback"]("Status: fase anterior terminou")
            return {"ok": False, "error": "cancelado"}
        return {"ok": True}

    derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(), status_label=None, progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"), table_name="ssa_table",
        special_files=[], sync_lock=sync_lock, qtimer=_QueuedTimer,
        sip_module=None, thread_factory=threading.Thread, execute_job=execute_job,
        finalize_result=lambda _parent, result: finalized.append(result) or result,
        sync_state_callback=None,
    )
    try:
        assert working.wait(timeout=5)
        _QueuedTimer.callbacks.pop(0)()
        assert state.running is True
        assert state.cancel_event.is_set()
        assert finalized == []
        release.set()
        assert state.thread is not None
        state.thread.join(timeout=5)
        assert not state.thread.is_alive()
        assert state.phase_status == "Status: Prazo esgotado; cancelando derivadas..."
        _QueuedTimer.callbacks.pop(0)()
        assert finalized == [{"ok": False, "error": "cancelado"}]
        assert state.running is False
    finally:
        release.set()
        if state.thread is not None:
            state.thread.join(timeout=5)
        _QueuedTimer.callbacks.clear()


def test_timeout_preserves_result_published_as_worker_exits(monkeypatch, tmp_path) -> None:
    _QueuedTimer.callbacks.clear()
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    finalized: list[dict[str, Any]] = []
    times = iter([0.0, float(derivadas_sync_controller.DERIVADAS_SYNC_TIMEOUT_SEC + 1)])
    monkeypatch.setattr(derivadas_sync_controller, "monotonic", lambda: next(times))

    derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(), status_label=None, progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"), table_name="ssa_table",
        special_files=[], sync_lock=sync_lock, qtimer=_QueuedTimer,
        sip_module=None, thread_factory=_AliveThread,
        execute_job=lambda **_kwargs: pytest.fail("fake worker does not execute"),
        finalize_result=lambda _parent, result: finalized.append(result) or result,
        sync_state_callback=None,
    )
    _QueuedTimer.callbacks.pop(0)()
    assert state.cancel_event.is_set()
    worker = state.thread
    assert isinstance(worker, _AliveThread)
    worker.alive = False
    original_thread_alive = derivadas_sync_controller._thread_alive
    published = False

    def _publish_on_exit(thread):
        nonlocal published
        if thread is worker and not published:
            with sync_lock:
                state.pending_result = {"ok": True, "marker": "real result"}
            published = True
        return original_thread_alive(thread)

    monkeypatch.setattr(derivadas_sync_controller, "_thread_alive", _publish_on_exit)
    _QueuedTimer.callbacks.pop(0)()

    assert finalized == [{"ok": True, "marker": "real result"}]
    assert state.running is False
    _QueuedTimer.callbacks.clear()


def test_derivadas_worker_does_not_call_gui_state_callback(tmp_path) -> None:
    state = derivadas_sync_controller.DerivadasSyncState()
    state.mark_started()
    sync_lock = derivadas_sync_controller._ensure_derivadas_sync_lock(state)
    callbacks: list[str] = []
    workers: list[_HungThread] = []

    def _thread_factory(**kwargs: Any) -> _HungThread:
        worker = _HungThread(**kwargs)
        workers.append(worker)
        return worker

    _QueuedTimer.callbacks.clear()
    derivadas_sync_controller._start_async_derivadas_sync(
        derivadas_sync_controller.DerivadasSyncUiRefs(
            message_parent=object(),
            status_label=None,
            progress_bar=None,
            update_button=None,
        ),
        state,
        db_path=str(tmp_path / "ssas.db"),
        table_name="ssa_table",
        special_files=[],
        sync_lock=sync_lock,
        qtimer=_QueuedTimer,
        sip_module=None,
        thread_factory=_thread_factory,
        execute_job=lambda **_kwargs: {"ok": True, "merged_edges": 1},
        finalize_result=lambda _parent, result: result,
        sync_state_callback=lambda: callbacks.append(threading.current_thread().name),
    )
    callback_count_before_work = len(callbacks)

    assert workers[0]._target is not None
    workers[0]._target()

    assert len(callbacks) == callback_count_before_work
    assert state.pending_result == {"ok": True, "merged_edges": 1}
