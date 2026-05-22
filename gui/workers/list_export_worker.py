"""QThread worker for exporting the visible SSA list."""

from __future__ import annotations

import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from gui.ssa.list_exporter import write_current_list_tsv

logger = logging.getLogger(__name__)


class ListExportWorker(QThread):
    export_finished = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        dataframe: pd.DataFrame,
        visible_columns: list[str] | tuple[str, ...],
        path: str,
    ) -> None:
        super().__init__()
        self._dataframe = dataframe
        self._visible_columns = list(visible_columns)
        self._path = str(path)

    def run(self) -> None:
        try:
            result = write_current_list_tsv(
                self._dataframe,
                self._visible_columns,
                self._path,
            )
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.exception("Erro ao exportar lista atual")
            self.error_occurred.emit(str(exc))
            return
        self.export_finished.emit(result)
