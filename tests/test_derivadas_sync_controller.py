from __future__ import annotations

import threading
from typing import Any

import pytest

from gui.ssa import derivadas_sync_controller


class _ImmediateTimer:
    @staticmethod
    def singleShot(_msec: int, callback) -> None:
        callback()


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
        qtimer=_ImmediateTimer,
        sip_module=None,
        thread_factory=_AliveThread,
        execute_job=lambda **_kwargs: pytest.fail(
            "_AliveThread keeps the sync job running"
        ),
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
    assert state.running is False
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
