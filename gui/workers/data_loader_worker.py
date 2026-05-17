# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

from __future__ import annotations

import logging
import sqlite3

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from armazenamento.database import query_db
from gui.workers.data_loader_processing import (
    DEFAULT_UI_SORT_SPEC,
    DEFAULT_UI_STATUS_LAST,
    SQLITE_INTEGER_PREFIX_RE,
    LoadedDataFrames,
    prepare_loaded_payload,
)
from gui.workers.data_loader_repository import resolve_target_table
from gui.workers.data_loader_query import build_select_query

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte seguro a paginação."""

    data_prepared = pyqtSignal(object)
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)
    _DEFAULT_UI_STATUS_LAST = DEFAULT_UI_STATUS_LAST
    _SQLITE_INTEGER_PREFIX_RE = SQLITE_INTEGER_PREFIX_RE
    _DEFAULT_UI_SORT_SPEC = DEFAULT_UI_SORT_SPEC

    def __init__(self, db_path, table_name, limit=None, offset=0, order_by=None):
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True
        try:
            self.requestInterruption()
        except RuntimeError as exc:
            logger.debug("Falha ao solicitar interrupcao do DataLoaderWorker: %s", exc)

    def _is_cancelled(self) -> bool:
        if bool(getattr(self, "_cancel_requested", False)):
            return True
        try:
            return bool(self.isInterruptionRequested())
        except RuntimeError:
            return False

    def run(self):
        try:
            if self._is_cancelled():
                return
            target_table = resolve_target_table(self.db_path, self.table_name)
            query, already_sorted_for_ui = build_select_query(
                target_table=target_table,
                order_by=self.order_by,
                limit=self.limit,
                offset=self.offset,
                default_sort_spec=self._DEFAULT_UI_SORT_SPEC,
            )

            if self._is_cancelled():
                return
            df = query_db(self.db_path, "", query, raise_on_error=True)
            if self._is_cancelled():
                return
            if not isinstance(df, pd.DataFrame):
                raise TypeError("query_db retornou tipo invalido para DataLoaderWorker")
            try:
                loaded = prepare_loaded_payload(
                    df,
                    order_by=self.order_by,
                    already_sorted_for_ui=already_sorted_for_ui,
                )
                df = loaded.complete
            except (TypeError, ValueError, AttributeError, KeyError) as exc:
                logger.warning(
                    "Falha no preprocessamento do DataLoaderWorker; mantendo DataFrame bruto: %s",
                    exc,
                )
                loaded = LoadedDataFrames(
                    complete=df,
                    display=df,
                    preprocessed_for_gui=False,
                    attrs=dict(getattr(df, "attrs", {}) or {}),
                )
                df = loaded.complete
            # data_loaded is kept for legacy consumers; GUI uses data_prepared.
            prepared_receivers = int(self.receivers(self.data_prepared))
            legacy_receivers = int(self.receivers(self.data_loaded))
            if prepared_receivers > 0:
                self.data_prepared.emit(loaded)
            if legacy_receivers > 0:
                self.data_loaded.emit(df)
        except (
            sqlite3.Error,
            pd.errors.DatabaseError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            AttributeError,
            KeyError,
        ):
            logger.exception("Erro interno no DataLoaderWorker durante carregamento")
            self.error_occurred.emit("Falha ao carregar dados do banco.")
