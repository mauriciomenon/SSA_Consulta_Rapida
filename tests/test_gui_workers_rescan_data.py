from __future__ import annotations

from pathlib import Path

from gui.ssa import gui_workers as ssa_gui_workers


class _Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot, *_args, **_kwargs):
        self._slots.append(slot)

    def emit(self, *args, **kwargs):
        for slot in list(self._slots):
            slot(*args, **kwargs)


class _StatusLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text: str) -> None:
        self.text = text


class _Window:
    def __init__(self):
        self._active_rescan_worker = None
        self.status_label = _StatusLabel()


class _DialogCancelAndFinish:
    def __init__(self, window):
        self.window = window
        self.cancel_requested = _Signal()

    def append_output(self, *_args, **_kwargs):
        return None

    def append_error(self, *_args, **_kwargs):
        return None

    def update_progress(self, *_args, **_kwargs):
        return None

    def set_finished(self, *_args, **_kwargs):
        return None

    def exec(self):
        self.cancel_requested.emit()
        worker = getattr(self.window, "_active_rescan_worker", None)
        if worker is not None:
            worker._running = False
            worker.finished.emit()
        return 0


class _DialogNoop:
    def __init__(self, _window):
        self.cancel_requested = _Signal()

    def append_output(self, *_args, **_kwargs):
        return None

    def append_error(self, *_args, **_kwargs):
        return None

    def update_progress(self, *_args, **_kwargs):
        return None

    def set_finished(self, *_args, **_kwargs):
        return None

    def exec(self):
        return 0


class _BaseWorker:
    def __init__(self, _main_py_path: str, _project_root: str):
        self._running = False
        self.stop_called = False
        self.output_line = _Signal()
        self.error_line = _Signal()
        self.progress = _Signal()
        self.finished_success = _Signal()
        self.finished_error = _Signal()
        self.finished = _Signal()

    def start(self):
        self._running = True

    def isRunning(self):
        return self._running

    def stop(self):
        self.stop_called = True

    def deleteLater(self):
        return None


class _WorkerStopRaises(_BaseWorker):
    def stop(self):
        self.stop_called = True
        raise RuntimeError("stop failed")


class _WorkerIsRunningRaises(_BaseWorker):
    def isRunning(self):
        raise RuntimeError("wrapped C/C++ object has been deleted")


def _build_main_py(tmp_path: Path) -> str:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return str(tmp_path)


def test_rescan_data_cancel_does_not_break_when_stop_raises(tmp_path):
    created_workers = []
    class _WorkerStopRaisesTracked(_WorkerStopRaises):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_workers.append(self)

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerStopRaisesTracked,
        rescan_dialog_cls=_DialogCancelAndFinish,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert created_workers
    assert created_workers[0].stop_called is True
    assert window.status_label.text == "Status: Cancelamento solicitado no reescaneamento."
    assert window._active_rescan_worker is None
    assert global_workers == []
    assert global_meta == {}


def test_rescan_data_releases_stale_worker_when_isrunning_raises_after_dialog(tmp_path):
    created_workers = []
    class _WorkerIsRunningRaisesTracked(_WorkerIsRunningRaises):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_workers.append(self)

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerIsRunningRaisesTracked,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert created_workers
    assert window._active_rescan_worker is None
    assert global_workers == []
    assert global_meta == {}
