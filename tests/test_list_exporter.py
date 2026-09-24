from __future__ import annotations

import csv
from pathlib import Path
from threading import Event

import pandas as pd
import pytest
from PyQt6.QtCore import QThread
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication, QLabel

from gui.ssa import list_export_controller
from gui.ssa.list_exporter import (
    ListExportResult,
    resolve_export_columns,
    write_current_list_tsv,
)
from gui.workers.list_export_worker import ListExportWorker


def test_resolve_export_columns_prefers_visible_columns_in_dataframe_order_request():
    dataframe = pd.DataFrame(
        {
            "numero_ssa": [1],
            "situacao": ["ASE"],
            "ignored": ["x"],
        }
    )

    assert resolve_export_columns(dataframe, ["situacao", "missing", "numero_ssa"]) == [
        "situacao",
        "numero_ssa",
    ]


def test_resolve_export_columns_falls_back_to_dataframe_columns_when_none_visible():
    dataframe = pd.DataFrame(
        {"numero_ssa": [1], "situacao": ["ASE"], "descricao_ssa": ["A"]}
    )

    assert resolve_export_columns(dataframe, ["missing"]) == [
        "numero_ssa",
        "situacao",
        "descricao_ssa",
    ]


def test_write_current_list_tsv_formats_visible_columns(tmp_path):
    dataframe = pd.DataFrame(
        {
            "numero_ssa": [202600001],
            "situacao": ["ASE"],
            "hidden": ["no"],
        }
    )
    out_path = tmp_path / "lista.txt"

    result = write_current_list_tsv(dataframe, ["situacao", "numero_ssa"], str(out_path))

    assert result.path == str(out_path)
    assert result.rows == 1
    assert result.columns == 2
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "situacao\tnumero_ssa",
        "ASE\t202600001",
    ]


def test_write_current_list_tsv_rejects_empty_dataframe(tmp_path):
    out_path = tmp_path / "lista.txt"

    with pytest.raises(ValueError, match="No data to export"):
        write_current_list_tsv(pd.DataFrame(), [], str(out_path))

    assert not out_path.exists()


def test_export_preserves_negative_numbers_and_escapes_formula_text(tmp_path):
    dataframe = pd.DataFrame({
        "=cabecalho": [-1, -1.5, "-1", "=1+1", "+1", "@SOMA(A1)", "\t=1+1"],
    })
    out_path = tmp_path / "numeros.tsv"

    write_current_list_tsv(dataframe, list(dataframe.columns), str(out_path))

    with out_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    assert rows == [
        ["'=cabecalho"], ["-1"], ["-1.5"], ["'-1"], ["'=1+1"],
        ["'+1"], ["'@SOMA(A1)"], ["'\t=1+1"],
    ]
    assert dataframe.iloc[0, 0] == -1
    assert dataframe.columns.tolist() == ["=cabecalho"]


def test_export_sanitizes_formatter_output_without_changing_numeric_display(tmp_path):
    dataframe = pd.DataFrame({"valor": [-1, -2, -3, -4, -5, -6, "texto", -8]})
    out_path = tmp_path / "formatado.tsv"

    def formatter(frame):
        frame["valor"] = [
            "-1.00", "-2,50", "-3e+02", '=CMD("x")', "\t-5", "-6+CMD()",
            "-7", "@SOMA(A1)",
        ]
        return frame

    write_current_list_tsv(dataframe, ["valor"], str(out_path), formatter=formatter)

    with out_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    assert rows == [
        ["valor"], ["-1.00"], ["-2,50"], ["-3e+02"], ['\'=CMD("x")'],
        ["'\t-5"], ["'-6+CMD()"], ["'-7"], ["'@SOMA(A1)"],
    ]
    assert dataframe["valor"].tolist() == [-1, -2, -3, -4, -5, -6, "texto", -8]


def test_export_does_not_restore_numeric_text_after_row_reordering(tmp_path):
    dataframe = pd.DataFrame({"valor": [-1, "-1"]})
    out_path = tmp_path / "reordered.tsv"

    def formatter(frame):
        return frame.iloc[::-1].reset_index(drop=True)

    write_current_list_tsv(dataframe, ["valor"], str(out_path), formatter=formatter)

    with out_path.open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream, delimiter="\t")) == [
            ["valor"], ["'-1"], ["-1"],
        ]


def test_list_export_worker_writes_through_open_temp_stream(tmp_path, monkeypatch):
    output = tmp_path / "lista.tsv"
    from gui.workers import list_export_worker

    real_write = list_export_worker.write_current_list_tsv
    observed = []

    def observe_write(dataframe, columns, path, *, stream=None):
        observed.append(stream is not None and not stream.closed)
        return real_write(dataframe, columns, path, stream=stream)

    monkeypatch.setattr(list_export_worker, "write_current_list_tsv", observe_write)
    worker = ListExportWorker(pd.DataFrame({"numero_ssa": [202600001]}), [], str(output))
    worker.start()

    assert worker.wait(2000)
    assert observed == [True]
    assert output.read_text(encoding="utf-8").splitlines() == [
        "numero_ssa", "202600001",
    ]


def test_export_controller_uses_stable_dataframe_snapshot(tmp_path):
    dataframe = pd.DataFrame({"numero_ssa": [202600001], "situacao": ["ASE"]})
    out_path = tmp_path / "lista.txt"
    state = list_export_controller.ListExportState()
    state_during_custom_signal = []

    class _StatusLabel:
        def __init__(self) -> None:
            self.value = ""

        def setText(self, value) -> None:
            self.value = value

        def text(self) -> str:
            return self.value

    class _Window:
        def __init__(self) -> None:
            self.df_exibido = dataframe
            self.visible_columns = ["numero_ssa", "situacao"]
            self.status_label = _StatusLabel()

    class _Dialog:
        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return str(out_path), ""

    class _MessageBox:
        @staticmethod
        def information(*_args, **_kwargs):
            raise AssertionError("unexpected message")

    class _Signal:
        def __init__(self) -> None:
            self._callbacks = []

        def connect(self, callback, *_args, **_kwargs) -> None:
            self._callbacks.append(callback)

        def emit(self, *args) -> None:
            for callback in list(self._callbacks):
                callback(*args)

    class _Worker:
        def __init__(self, worker_df, visible_columns, path) -> None:
            self.worker_df = worker_df
            self.visible_columns = visible_columns
            self.path = path
            self.export_finished = _Signal()
            self.error_occurred = _Signal()
            self.finished = _Signal()

        def deleteLater(self) -> None:
            return None

        def start(self):
            window.df_exibido = pd.DataFrame(
                {"numero_ssa": [2], "situacao": ["MUTATED"]}
            )
            result = write_current_list_tsv(
                self.worker_df,
                self.visible_columns,
                self.path,
            )
            self.export_finished.emit(result)
            state_during_custom_signal.append(state.running)
            self.finished.emit()

    window = _Window()
    list_export_controller.export_current_list_tsv(
        window,
        state,
        file_dialog=_Dialog,
        message_box=_MessageBox,
        worker_cls=_Worker,
    )

    assert state.running is False
    assert state.worker is None
    assert state_during_custom_signal == [True]
    assert window.status_label.text() == (
        f"Status: Lista exportada: 1 linhas em {out_path}."
    )
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "numero_ssa\tsituacao",
        "202600001\tASE",
    ]


@pytest.mark.parametrize(
    ("failure_stage", "expected_message"),
    [
        ("start", "Falha ao iniciar a exportacao."),
        ("worker", "Falha ao exportar a lista."),
    ],
)
def test_export_controller_reports_failure_and_clears_state(
    tmp_path, failure_stage, expected_message
):
    output = tmp_path / "lista.tsv"
    messages = []
    state = list_export_controller.ListExportState()

    class _Window:
        df_exibido = pd.DataFrame({"numero_ssa": [1]})
        visible_columns = ["numero_ssa"]

    class _Dialog:
        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return str(output), ""

    class _MessageBox:
        @staticmethod
        def information(_window, title, message):
            messages.append((title, message))

    class _Signal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback, *_args, **_kwargs):
            self.callbacks.append(callback)

        def emit(self, *args):
            for callback in self.callbacks:
                callback(*args)

    class _Worker:
        def __init__(self, *_args):
            self.export_finished = _Signal()
            self.error_occurred = _Signal()
            self.finished = _Signal()

        def start(self):
            if failure_stage == "start":
                raise RuntimeError("worker start failed")
            self.error_occurred.emit("disk full")
            self.finished.emit()

    list_export_controller.export_current_list_tsv(
        _Window(), state, file_dialog=_Dialog, message_box=_MessageBox,
        worker_cls=_Worker,
    )

    assert state.running is False
    assert state.worker is None
    assert messages == [("Aviso", expected_message)]
    assert not output.exists()


def test_export_controller_updates_status_on_gui_thread(tmp_path):
    app = QApplication.instance() or QApplication([])
    output = tmp_path / "lista.tsv"
    state = list_export_controller.ListExportState()
    status_threads = []

    class _StatusLabel(QLabel):
        def setText(self, text):
            status_threads.append(QThread.currentThread())
            super().setText(text)

    class _Window:
        def __init__(self):
            self.df_exibido = pd.DataFrame({"numero_ssa": [1]})
            self.visible_columns = ["numero_ssa"]
            self.status_label = _StatusLabel()

    class _Dialog:
        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return str(output), ""

    class _MessageBox:
        @staticmethod
        def information(*_args, **_kwargs):
            raise AssertionError("unexpected error dialog")

    window = _Window()
    list_export_controller.export_current_list_tsv(
        window, state, file_dialog=_Dialog, message_box=_MessageBox,
    )
    worker = state.worker

    assert worker.wait(2000)
    app.processEvents()
    assert status_threads == [app.thread()]
    assert window.status_label.text() == (
        f"Status: Lista exportada: 1 linhas em {output}."
    )
    assert state.running is False
    assert state.worker is None


def test_list_export_cancel_does_not_publish_final_file(tmp_path, monkeypatch):
    output = tmp_path / "lista.tsv"
    output.write_text("original\n", encoding="utf-8")
    started = Event()
    release = Event()

    def _blocking_write(_dataframe, _columns, path, *, stream=None):
        started.set()
        assert release.wait(2.0)
        if stream is not None:
            stream.write("replacement\n")
        else:
            Path(path).write_text("replacement\n", encoding="utf-8")
        return ListExportResult(path=str(path), rows=1, columns=1)

    monkeypatch.setattr(
        "gui.workers.list_export_worker.write_current_list_tsv",
        _blocking_write,
    )
    worker = ListExportWorker(pd.DataFrame({"numero_ssa": [1]}), [], str(output))
    success_spy = QSignalSpy(worker.export_finished)

    worker.start()
    assert started.wait(1.0)
    worker.cancel()
    release.set()
    assert worker.wait(2000)

    assert len(success_spy) == 0
    assert output.read_text(encoding="utf-8") == "original\n"
    assert list(tmp_path.glob(".lista.tsv.*.tmp")) == []
