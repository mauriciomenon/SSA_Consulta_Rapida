"""QThread worker for exporting the visible SSA list."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from threading import Lock

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from gui.ssa.list_exporter import ListExportResult, write_current_list_tsv

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
        self._published = False
        self._state_lock = Lock()

    def cancel(self) -> None:
        with self._state_lock:
            if self._published:
                return
            self._cancel_requested = True
        try:
            self.requestInterruption()
        except RuntimeError as exc:
            logger.debug("Falha ao solicitar interrupcao do ListExportWorker: %s", exc)

    def _is_cancelled(self) -> bool:
        with self._state_lock:
            if self._cancel_requested:
                return True
        try:
            return bool(self.isInterruptionRequested())
        except RuntimeError:
            return False

    def run(self) -> None:
        if self._is_cancelled():
            return
        temp_path: Path | None = None
        try:
            final_path = Path(self._path).expanduser()
            with tempfile.NamedTemporaryFile(
                dir=final_path.parent,
                prefix=f".{final_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temp_path = Path(temporary.name)
            result = write_current_list_tsv(
                self._dataframe,
                self._visible_columns,
                str(temp_path),
            )
            with self._state_lock:
                if self._cancel_requested:
                    return
                os.replace(temp_path, final_path)
                temp_path = None
                self._published = True
            result = ListExportResult(
                path=str(final_path),
                rows=result.rows,
                columns=result.columns,
            )
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.exception("Erro ao exportar lista atual")
            if not self._is_cancelled():
                self.error_occurred.emit(str(exc))
            return
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "Falha ao remover arquivo temporario de exportacao: %s", exc
                    )
        if self._is_cancelled():
            return
        self.export_finished.emit(result)
