"""UI controller for exporting the current SSA list outside the GUI thread."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from gui.ssa.list_exporter import ListExportResult, resolve_export_columns
from gui.workers.list_export_worker import ListExportWorker

logger = logging.getLogger(__name__)


@dataclass
class ListExportState:
    running: bool = False
    worker: Any = None

    def clear(self) -> None:
        self.running = False
        self.worker = None


def export_current_list_tsv(
    window: Any,
    state: ListExportState,
    *,
    file_dialog: Any,
    message_box: Any,
    worker_cls: Any = ListExportWorker,
) -> None:
    dataframe = getattr(window, "df_exibido", None)
    if dataframe is None or dataframe.empty:
        message_box.information(window, "Aviso", "Nenhum dado para exportar.")
        return
    if state.running:
        message_box.information(window, "Aviso", "Exportacao em andamento.")
        return

    path = _choose_export_path(window, file_dialog)
    if not path:
        return

    visible_columns = list(getattr(window, "visible_columns", []) or [])
    export_columns = resolve_export_columns(dataframe, visible_columns)
    worker = worker_cls(dataframe.copy(deep=False), export_columns, path)
    state.running = True
    state.worker = worker

    def _on_success(result: Any) -> None:
        if isinstance(result, ListExportResult):
            logger.info(
                "Lista exportada para %s (%s linhas, %s colunas).",
                result.path,
                result.rows,
                result.columns,
            )

    def _on_error(error: str) -> None:
        logger.error("Falha ao exportar lista para arquivo: %s", error)
        message_box.information(window, "Aviso", "Falha ao exportar a lista.")

    def _on_finished() -> None:
        if state.worker is worker:
            state.clear()

    worker.export_finished.connect(_on_success)
    worker.error_occurred.connect(_on_error)
    if hasattr(worker, "finished"):
        worker.finished.connect(_on_finished)
        if hasattr(worker, "deleteLater"):
            worker.finished.connect(worker.deleteLater)
    worker.start()


def _choose_export_path(window: Any, file_dialog: Any) -> str:
    try:
        path, _ = file_dialog.getSaveFileName(
            window, "Exportar lista", "", "TSV Files (*.tsv);;Tab-Separated Text (*.txt)"
        )
    except Exception as exc:
        logger.warning("Falha ao abrir dialogo de exportacao: %s", exc)
        return ""
    return str(path or "")
