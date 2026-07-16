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
        self._active_rescan_dialog = None
        self.status_label = _StatusLabel()
        self.load_calls = 0

    def load_data(self) -> None:
        self.load_calls += 1
        self.status_label.setText("Status: Carregando dados...")


class _QuestionBox:
    class StandardButton:
        Yes = 1
        No = 2
        Cancel = 4

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def question(self, *args):
        self.calls.append(args)
        return self.answer


class _DialogCancelAndFinish:
    def __init__(self, window):
        self.window = window
        self.cancel_requested = _Signal()
        self.show_called = False
        self.show_non_modal_called = False

    def append_output(self, *_args, **_kwargs):
        return None

    def append_error(self, *_args, **_kwargs):
        return None

    def update_progress(self, *_args, **_kwargs):
        return None

    def set_finished(self, *_args, **_kwargs):
        return None

    def show(self):
        self.show_called = True
        self.cancel_requested.emit()
        worker = getattr(self.window, "_active_rescan_worker", None)
        if worker is not None:
            worker._running = False
            worker.finished.emit()

    def show_non_modal(self):
        self.show_non_modal_called = True
        self.show()


class _DialogNoop:
    def __init__(self, _window):
        self.cancel_requested = _Signal()
        self.show_called = False
        self.show_non_modal_called = False

    def append_output(self, *_args, **_kwargs):
        return None

    def append_error(self, *_args, **_kwargs):
        return None

    def update_progress(self, *_args, **_kwargs):
        return None

    def set_finished(self, *_args, **_kwargs):
        return None

    def show(self):
        self.show_called = True

    def show_non_modal(self):
        self.show_non_modal_called = True
        self.show()


class _DialogCancelNoFinish:
    def __init__(self, _window):
        self.cancel_requested = _Signal()
        self.show_called = False
        self.show_non_modal_called = False

    def append_output(self, *_args, **_kwargs):
        return None

    def append_error(self, *_args, **_kwargs):
        return None

    def update_progress(self, *_args, **_kwargs):
        return None

    def set_finished(self, *_args, **_kwargs):
        return None

    def show(self):
        self.show_called = True
        self.cancel_requested.emit()

    def show_non_modal(self):
        self.show_non_modal_called = True
        self.show()


class _BaseWorker:
    def __init__(self, _main_py_path: str, _project_root: str):
        self._running = False
        self.stop_called = False
        self.output_line = _Signal()
        self.error_line = _Signal()
        self.progress = _Signal()
        self.batch_completed = _Signal()
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
    assert (
        window.status_label.text == "Status: Cancelamento solicitado no reescaneamento."
    )
    assert window._active_rescan_worker is None
    assert window._active_rescan_dialog is None
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
    assert window._active_rescan_worker is created_workers[0]
    assert window._active_rescan_dialog is not None
    assert global_workers == [created_workers[0]]
    assert created_workers[0] in global_meta


def test_rescan_data_clears_inactive_active_worker_before_start(tmp_path):
    class _InactiveWorker:
        def isRunning(self):
            return False

    class _WorkerTracked(_BaseWorker):
        created = []

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _WorkerTracked.created.append(self)

    project_root = _build_main_py(tmp_path)
    window = _Window()
    window._active_rescan_worker = _InactiveWorker()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerTracked,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert _WorkerTracked.created
    assert window._active_rescan_worker is _WorkerTracked.created[0]


def test_rescan_data_sets_cancel_status_even_when_worker_not_running(tmp_path):
    class _WorkerNotRunning(_BaseWorker):
        def isRunning(self):
            return False

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerNotRunning,
        rescan_dialog_cls=_DialogCancelNoFinish,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert (
        window.status_label.text == "Status: Cancelamento solicitado no reescaneamento."
    )


def test_rescan_data_shows_progress_dialog_without_blocking(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}
    created_dialogs = []

    class _DialogTracked(_DialogNoop):
        def __init__(self, parent):
            super().__init__(parent)
            created_dialogs.append(self)

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogTracked,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert created_dialogs
    assert created_dialogs[0].show_called is True
    assert created_dialogs[0].show_non_modal_called is True
    assert window._active_rescan_dialog is created_dialogs[0]


def test_rescan_data_explicit_mode_does_not_set_started_status_on_main_label(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
    )

    assert window.status_label.text == ""


def test_rescan_data_explicit_cancel_uses_specific_status_text(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogCancelNoFinish,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
    )

    assert (
        window.status_label.text
        == "Status: Cancelamento solicitado na importacao externa."
    )


def test_rescan_data_explicit_success_without_updates_does_not_reload(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
        reload_on_success=True,
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.last_outcome = "no_changes"
    worker.finished_success.emit()

    assert window.load_calls == 0
    assert (
        window.status_label.text
        == "Status: Importacao externa concluida sem alteracoes."
    )


def test_rescan_data_explicit_selected_file_reloads_even_when_outcome_is_no_changes(
    tmp_path,
):
    class _WorkerWithExplicitFiles(_BaseWorker):
        def __init__(
            self,
            _main_py_path: str,
            _project_root: str,
            explicit_files: tuple[str, ...] | None = None,
        ):
            super().__init__(_main_py_path, _project_root)
            self.explicit_files = explicit_files

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerWithExplicitFiles,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
        reload_on_success=True,
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.last_outcome = "no_changes"
    worker.finished_success.emit()

    assert window.load_calls == 1
    assert window.status_label.text == "Status: Carregando dados..."


def test_rescan_data_explicit_success_with_updates_reloads_automatically(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
        reload_on_success=True,
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.last_outcome = "updated"
    worker.finished_success.emit()

    assert window.load_calls == 1
    assert window.status_label.text == "Status: Carregando dados..."


def test_rescan_data_reloads_once_per_completed_batch_without_final_duplicate(
    tmp_path,
):
    class _WorkerWithExplicitFiles(_BaseWorker):
        def __init__(
            self,
            _main_py_path: str,
            _project_root: str,
            explicit_files: tuple[str, ...] | None = None,
        ):
            super().__init__(_main_py_path, _project_root)
            self.explicit_files = explicit_files

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerWithExplicitFiles,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
        reload_on_success=True,
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.batch_completed.emit(1, 3)
    worker.batch_completed.emit(2, 3)
    worker.batch_completed.emit(3, 3)
    worker.last_outcome = "updated"
    worker.finished_success.emit()

    assert window.load_calls == 3


def test_rescan_data_retries_final_reload_after_later_batch_reload_failure(tmp_path):
    class _WindowWithSecondReloadFailure(_Window):
        def __init__(self):
            super().__init__()
            self.load_attempts = 0

        def load_data(self) -> None:
            self.load_attempts += 1
            if self.load_attempts == 2:
                raise RuntimeError("reload failure")
            super().load_data()

    class _WorkerWithExplicitFiles(_BaseWorker):
        def __init__(
            self,
            _main_py_path: str,
            _project_root: str,
            explicit_files: tuple[str, ...] | None = None,
        ):
            super().__init__(_main_py_path, _project_root)
            self.explicit_files = explicit_files

    project_root = _build_main_py(tmp_path)
    window = _WindowWithSecondReloadFailure()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerWithExplicitFiles,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_label="Importacao externa",
        reload_on_success=True,
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.batch_completed.emit(1, 2)
    worker.batch_completed.emit(2, 2)
    worker.last_outcome = "updated"
    worker.finished_success.emit()

    assert window.load_attempts == 3
    assert window.load_calls == 2


def test_rescan_data_full_success_with_updates_reloads_automatically(tmp_path):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="full",
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.last_outcome = "updated"
    worker.finished_success.emit()

    assert window.load_calls == 1
    assert window.status_label.text == "Status: Carregando dados..."


def test_rescan_data_consolidate_success_uses_consolidate_context(
    tmp_path, monkeypatch
):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}
    contexts: list[str] = []

    def _capture_status(_window, text: str, *, context: str) -> None:
        contexts.append(str(context))
        _window.status_label.setText(text)

    monkeypatch.setattr(ssa_gui_workers, "_set_status_label_text", _capture_status)

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_kind="consolidate",
        operation_label="Consolidacao",
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.last_outcome = "updated"
    worker.finished_success.emit()

    assert contexts[-1] == "consolidate.success.done"


def test_rescan_data_consolidate_error_uses_consolidate_context(tmp_path, monkeypatch):
    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}
    contexts: list[str] = []

    def _capture_status(_window, text: str, *, context: str) -> None:
        contexts.append(str(context))
        _window.status_label.setText(text)

    monkeypatch.setattr(ssa_gui_workers, "_set_status_label_text", _capture_status)

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_BaseWorker,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="explicit",
        explicit_files=("docs_entrada/a.xlsx",),
        operation_kind="consolidate",
        operation_label="Consolidacao",
    )

    worker = window._active_rescan_worker
    assert worker is not None
    worker.finished_error.emit("boom")

    assert contexts[-1] == "consolidate.error"


def test_rescan_data_diff_mode_skips_prompt_and_sets_force_import_false(tmp_path):
    captured_modes: list[bool] = []

    class _WorkerCaptureMode(_BaseWorker):
        def __init__(
            self, _main_py_path: str, _project_root: str, force_import: bool = True
        ):
            super().__init__(_main_py_path, _project_root)
            captured_modes.append(bool(force_import))

    class _MessageBoxShouldNotBeUsed:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Prompt nao deveria ser exibido em rescan_mode=diff")

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerCaptureMode,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=_MessageBoxShouldNotBeUsed,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="diff",
    )

    assert captured_modes == [False]


def test_rescan_data_full_mode_skips_prompt_and_sets_force_import_true(tmp_path):
    captured_modes: list[bool] = []

    class _WorkerCaptureMode(_BaseWorker):
        def __init__(
            self, _main_py_path: str, _project_root: str, force_import: bool = True
        ):
            super().__init__(_main_py_path, _project_root)
            captured_modes.append(bool(force_import))

    class _MessageBoxShouldNotBeUsed:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Prompt nao deveria ser exibido em rescan_mode=full")

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerCaptureMode,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=_MessageBoxShouldNotBeUsed,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="full",
    )

    assert captured_modes == [True]


def test_rescan_data_prompt_without_qmessagebox_uses_incremental_mode(tmp_path):
    captured_modes: list[bool] = []

    class _WorkerCaptureMode(_BaseWorker):
        def __init__(
            self, _main_py_path: str, _project_root: str, force_import: bool = True
        ):
            super().__init__(_main_py_path, _project_root)
            captured_modes.append(bool(force_import))

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerCaptureMode,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="prompt",
    )

    assert captured_modes == [False]


def test_rescan_data_passes_active_db_path_to_worker(tmp_path):
    captured_db_paths: list[str | None] = []
    active_db = tmp_path / "alternate" / "custom.sqlite"
    active_db.parent.mkdir()
    active_db.write_bytes(b"")

    class _WorkerCaptureDbPath(_BaseWorker):
        def __init__(
            self,
            _main_py_path: str,
            _project_root: str,
            db_path: str | None = None,
        ):
            super().__init__(_main_py_path, _project_root)
            captured_db_paths.append(db_path)

    project_root = _build_main_py(tmp_path)
    window = _Window()
    global_workers: list = []
    global_meta: dict = {}

    ssa_gui_workers.rescan_data(
        window,
        project_root=project_root,
        rescan_worker_cls=_WorkerCaptureDbPath,
        rescan_dialog_cls=_DialogNoop,
        qmessagebox=None,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=8,
        retired_ttl_sec=30.0,
        retired_force_wait_ms=10,
        sip_module=None,
        rescan_mode="diff",
        db_path=str(active_db),
    )

    assert captured_db_paths == [str(active_db)]


def test_classify_workers_for_ttl_expires_oldest_when_above_cap():
    workers = ["w1", "w2", "w3"]
    meta = {"w1": 100.0, "w2": 101.0, "w3": 102.0}

    running, expired = ssa_gui_workers._classify_workers_for_ttl(
        workers,
        global_meta=meta,
        now=120.0,
        retired_ttl_sec=60.0,
        max_global_workers=2,
        is_running_fn=lambda _worker: True,
    )

    assert running == ["w1", "w2", "w3"]
    assert expired == ["w1"]


def test_classify_workers_for_ttl_keeps_source_snapshot_immutable():
    workers = ["w1", "w2", "w3"]
    meta = {"w1": 100.0, "w2": 101.0, "w3": 102.0}

    running, expired = ssa_gui_workers._classify_workers_for_ttl(
        workers,
        global_meta=meta,
        now=120.0,
        retired_ttl_sec=60.0,
        max_global_workers=10,
        is_running_fn=lambda worker: worker != "w2",
    )

    assert running == ["w1", "w3"]
    assert expired == []
    assert workers == ["w1", "w2", "w3"]
    assert "w2" not in meta


def test_classify_and_update_global_workers_locked_updates_source_list():
    global_workers = ["w1", "w2", "w3"]
    meta = {"w1": 100.0, "w2": 101.0, "w3": 102.0}

    expired = ssa_gui_workers._classify_and_update_global_workers_locked(
        global_workers=global_workers,
        global_meta=meta,
        now=120.0,
        retired_ttl_sec=60.0,
        max_global_workers=10,
        is_running_fn=lambda worker: worker != "w2",
    )

    assert expired == []
    assert global_workers == ["w1", "w3"]
    assert "w2" not in meta


def test_prune_retired_rescan_workers_expires_oldest_when_above_cap(monkeypatch):
    class _Worker:
        def __init__(self, name: str):
            self.name = name
            self._running = True
            self.stop_called = False
            self.quit_called = False
            self.wait_calls = 0

        def isRunning(self):
            return self._running

        def stop(self):
            self.stop_called = True
            self._running = False

        def quit(self):
            self.quit_called = True

        def wait(self, _ms: int):
            self.wait_calls += 1

        def __repr__(self):
            return f"Worker({self.name})"

    monkeypatch.setattr(ssa_gui_workers, "perf_counter", lambda: 120.0)
    window = _Window()
    older = _Worker("older")
    newer = _Worker("newer")
    global_workers = [older, newer]
    global_meta = {older: 100.0, newer: 110.0}

    ssa_gui_workers.prune_retired_rescan_workers(
        window,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=1,
        retired_ttl_sec=60.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert global_workers == [newer]
    assert newer in global_meta
    assert older not in global_meta
    assert older.stop_called is True
    assert older.wait_calls == 0


def test_prune_retains_overflow_rescan_worker_that_does_not_stop(monkeypatch):
    class _Worker:
        def __init__(self, name: str):
            self.name = name
            self.stop_called = False
            self.quit_called = False

        def isRunning(self):
            return True

        def stop(self):
            self.stop_called = True

        def quit(self):
            self.quit_called = True

    monkeypatch.setattr(ssa_gui_workers, "perf_counter", lambda: 120.0)
    older = _Worker("older")
    newer = _Worker("newer")
    global_workers = [older, newer]
    global_meta = {older: 100.0, newer: 110.0}

    ssa_gui_workers.prune_retired_rescan_workers(
        _Window(),
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=1,
        retired_ttl_sec=60.0,
        retired_force_wait_ms=10,
        sip_module=None,
    )

    assert global_workers == [older, newer]
    assert older in global_meta
    assert older.stop_called is True
    assert older.quit_called is True


def test_filter_registry_keeps_running_workers_above_cap():
    from gui.ssa.filter_worker_lifecycle import DeferredFilterWorkerRegistry

    registry = DeferredFilterWorkerRegistry(max_workers=1)
    first = object()
    second = object()
    registry.add(first)
    registry.add(second)

    registry.prune(lambda _worker: True)

    assert registry.snapshot() == [first, second]
