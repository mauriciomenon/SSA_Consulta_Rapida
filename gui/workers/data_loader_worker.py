# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from armazenamento.database import query_db
from armazenamento.identifier_utils import is_valid_identifier
from gui.workers.data_loader_processing import (
    DEFAULT_UI_SORT_SPEC,
    DEFAULT_UI_STATUS_LAST,
    SQLITE_INTEGER_PREFIX_RE,
    SQLITE_OFFSET_WITHOUT_LIMIT,
    LoadedDataFrames,
    prepare_loaded_payload,
)
from gui.workers.data_loader_query import build_default_ui_order_clause
from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte seguro a paginação."""

    data_prepared = pyqtSignal(object)
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)
    _DEFAULT_UI_STATUS_LAST = DEFAULT_UI_STATUS_LAST
    _SQLITE_OFFSET_WITHOUT_LIMIT = SQLITE_OFFSET_WITHOUT_LIMIT
    _SQLITE_INTEGER_PREFIX_RE = SQLITE_INTEGER_PREFIX_RE
    _DEFAULT_UI_SORT_SPEC = DEFAULT_UI_SORT_SPEC
    _TABLE_RESOLUTION_CACHE: dict[tuple[str, str], str] = {}

    _ALLOWED_ORDER_COLUMNS = {
        "numero_ssa",
        "situacao",
        "data_cadastro",
        "semana_cadastro",
        "semana_programada",
        "semana_executada",
        "setor_emissor",
        "setor_executor",
        "descricao_ssa",
        "localizacao_codigo",
        "equipamento",
        "solicitante",
        "grau_prioridade_emissao",
        "grau_prioridade_planejamento",
        "derivada_de",
    }
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

    def _sanitize_identifier(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if not is_valid_identifier(text):
            return ""
        return text

    def _quote_identifier(self, value: str) -> str:
        identifier = str(value or "").replace('"', '""')
        return f'"{identifier}"'

    @classmethod
    def _build_default_ui_order_clause(cls) -> str:
        return build_default_ui_order_clause(cls._DEFAULT_UI_SORT_SPEC)

    def _resolve_target_table(self) -> str:
        cache_key = (str(self.db_path), str(self.table_name))
        cached_table = self._TABLE_RESOLUTION_CACHE.get(cache_key)
        if cached_table:
            return cached_table
        requested = self._sanitize_identifier(self.table_name)
        candidates = []
        if requested:
            candidates.append(requested)
        for name in ALL_SSA_TABLE_NAMES:
            if name not in candidates:
                candidates.append(name)

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
                ).fetchall()
                existing = {str(row[0]) for row in rows if row and row[0]}
            for candidate in candidates:
                if candidate in existing:
                    self._TABLE_RESOLUTION_CACHE[cache_key] = candidate
                    return candidate
        except (sqlite3.Error, OSError):
            logger.debug("Falha ao resolver tabela alvo do DataLoaderWorker.")

        fallback = candidates[0] if candidates else CANONICAL_SSA_TABLE
        sanitized_fallback = self._sanitize_identifier(fallback)
        resolved_fallback = sanitized_fallback or CANONICAL_SSA_TABLE
        self._TABLE_RESOLUTION_CACHE[cache_key] = resolved_fallback
        return resolved_fallback

    def _normalize_order_by(self, order_by: str | None) -> str | None:
        if not order_by:
            return None
        normalized_parts = []
        parts = [part.strip() for part in str(order_by).split(",") if part.strip()]
        if not parts:
            return None
        for part in parts:
            tokens = part.split()
            if len(tokens) == 1:
                col, direction = tokens[0], "ASC"
            elif len(tokens) == 2:
                col, direction = tokens[0], tokens[1].upper()
            else:
                raise ValueError(f"ORDER BY invalido: {part}")
            col = self._sanitize_identifier(col).lower()
            if col not in self._ALLOWED_ORDER_COLUMNS:
                raise ValueError(f"Coluna ORDER BY nao permitida: {col}")
            if direction not in {"ASC", "DESC"}:
                raise ValueError(f"Direcao ORDER BY invalida: {direction}")
            normalized_parts.append(f"{self._quote_identifier(col)} {direction}")
        return ", ".join(normalized_parts)

    def _build_select_query(self, target_table: str) -> tuple[str, bool]:
        query = f"SELECT * FROM {self._quote_identifier(target_table)}"  # nosec B608
        already_sorted_for_ui = False

        order_clause = self._normalize_order_by(self.order_by)
        if order_clause:
            query += f" ORDER BY {order_clause}"
        else:
            query += f" ORDER BY {self._build_default_ui_order_clause()}"
            already_sorted_for_ui = True

        if self.limit is not None:
            limit_int = int(self.limit)
            if limit_int < 0:
                raise ValueError("LIMIT nao pode ser negativo")
            query += f" LIMIT {limit_int}"

        offset_int = int(self.offset or 0)
        if offset_int < 0:
            raise ValueError("OFFSET nao pode ser negativo")
        if offset_int > 0:
            if self.limit is None:
                query += f" LIMIT {self._SQLITE_OFFSET_WITHOUT_LIMIT}"
            query += f" OFFSET {offset_int}"

        return query, already_sorted_for_ui

    def run(self):
        try:
            if self._is_cancelled():
                return
            target_table = self._resolve_target_table()
            if not self._sanitize_identifier(target_table):
                raise ValueError("Tabela alvo invalida para DataLoaderWorker")
            query, already_sorted_for_ui = self._build_select_query(target_table)

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
