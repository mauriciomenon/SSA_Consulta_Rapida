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
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True
        try:
            self.requestInterruption()
        except RuntimeError as exc:
            logger.debug("Falha ao solicitar interrupcao do ListExportWorker: %s", exc)

    def _is_cancelled(self) -> bool:
        if self._cancel_requested:
            return True
        try:
            return bool(self.isInterruptionRequested())
        except RuntimeError:
            return False

    def run(self) -> None:
        if self._is_cancelled():
            return
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
        if self._is_cancelled():
            return
        self.export_finished.emit(result)
