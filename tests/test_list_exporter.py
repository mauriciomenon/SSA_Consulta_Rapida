from __future__ import annotations

from pathlib import Path
from threading import Event

import pandas as pd
import pytest
from PyQt6.QtTest import QSignalSpy

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


def test_export_controller_uses_stable_dataframe_snapshot(tmp_path):
    dataframe = pd.DataFrame({"numero_ssa": [202600001], "situacao": ["ASE"]})
    out_path = tmp_path / "lista.txt"
    state = list_export_controller.ListExportState()
    state_during_custom_signal = []

    class _Window:
        def __init__(self) -> None:
            self.df_exibido = dataframe
            self.visible_columns = ["numero_ssa", "situacao"]

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

        def connect(self, callback) -> None:
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
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "numero_ssa\tsituacao",
        "202600001\tASE",
    ]


def test_list_export_cancel_does_not_publish_final_file(tmp_path, monkeypatch):
    output = tmp_path / "lista.tsv"
    output.write_text("original\n", encoding="utf-8")
    started = Event()
    release = Event()

    def _blocking_write(_dataframe, _columns, path):
        started.set()
        assert release.wait(2.0)
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
