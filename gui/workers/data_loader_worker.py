# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

from __future__ import annotations

import logging
import re
import sqlite3
from contextlib import closing

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from armazenamento.database import query_db
from armazenamento.identifier_utils import is_valid_identifier
from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte seguro a paginação."""

    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

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

    def _resolve_target_table(self) -> str:
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
                    return candidate
        except (sqlite3.Error, OSError) as exc:
            logger.debug("Falha ao resolver tabela alvo do DataLoaderWorker: %s", exc)

        fallback = candidates[0] if candidates else CANONICAL_SSA_TABLE
        sanitized_fallback = self._sanitize_identifier(fallback)
        return sanitized_fallback or CANONICAL_SSA_TABLE

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

    def _sanitize_ssa_like_value(self, value) -> str:
        if value is None:
            return ""
        try:
            if isinstance(value, float):
                if pd.isna(value):
                    return ""
                if value.is_integer():
                    return str(int(value))
                return str(value).strip()
        except (TypeError, ValueError):
            pass
        text = str(value).strip()
        if not text:
            return ""
        if text.lower() in {"nan", "none", "nat", "<na>"}:
            return ""
        if re.fullmatch(r"\d+\.0+", text):
            return text.split(".", 1)[0]
        return text

    def _build_initial_sorted_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        base = df
        try:
            if "situacao" in base.columns:
                is_ste = base["situacao"].astype(str).str.upper().eq("STE")
            else:
                is_ste = pd.Series([False] * len(base), index=base.index)
            if "numero_ssa" in base.columns:
                ssa_text = base["numero_ssa"].astype(str)
                ssa_digits = ssa_text.str.replace(r"\D+", "", regex=True)
                ssa_int = (
                    pd.to_numeric(ssa_digits, errors="coerce")
                    .fillna(-1)
                    .astype("int64")
                )
            else:
                ssa_int = pd.Series([-1] * len(base), index=base.index)
            base = (
                base.assign(__is_ste=is_ste, __ssa=ssa_int)
                .sort_values(
                    by=["__is_ste", "__ssa"],
                    ascending=[True, False],
                    na_position="last",
                )
                .drop(columns=["__is_ste", "__ssa"])
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                "Falha na ordenacao inicial durante preprocessamento do DataLoaderWorker: %s",
                exc,
            )
        return base

    def _build_non_null_columns(self, df: pd.DataFrame) -> list[str]:
        try:
            non_null_mask = df.notna().any(axis=0)
            return [str(col) for col in non_null_mask[non_null_mask].index.tolist()]
        except (TypeError, ValueError, AttributeError, KeyError) as exc:
            logger.debug(
                "Falha no calculo vetorizado de colunas nao nulas no DataLoaderWorker: %s",
                exc,
            )
            non_null_cols = []
            for col_name in df.columns:
                has_non_null = False
                try:
                    has_non_null = bool(df[col_name].notna().any())
                except (TypeError, ValueError, AttributeError, KeyError) as col_exc:
                    logger.debug(
                        "Falha ao verificar nullability da coluna '%s' no DataLoaderWorker: %s",
                        col_name,
                        col_exc,
                    )
                if has_non_null:
                    non_null_cols.append(str(col_name))
            return non_null_cols

    def _prepare_dataframe_for_ui(self, df: pd.DataFrame) -> pd.DataFrame:
        sanitized_df = df
        for ssa_col in ("numero_ssa", "derivada_de"):
            if ssa_col in sanitized_df.columns:
                sanitized_df[ssa_col] = sanitized_df[ssa_col].map(
                    self._sanitize_ssa_like_value
                )
        pre_sorted_df = (
            sanitized_df
            if self.order_by
            else self._build_initial_sorted_dataframe(sanitized_df)
        )
        non_null_cols = self._build_non_null_columns(sanitized_df)
        try:
            pre_sorted_df.attrs["ssa_preprocessed_for_gui"] = True
            pre_sorted_df.attrs["ssa_non_null_cols"] = non_null_cols
        except (AttributeError, TypeError, ValueError) as exc:
            logger.debug(
                "Falha ao anexar attrs de preprocessamento no DataLoaderWorker: %s", exc
            )
        return pre_sorted_df

    def run(self):
        try:
            if self._is_cancelled():
                return
            target_table = self._resolve_target_table()
            if not self._sanitize_identifier(target_table):
                raise ValueError("Tabela alvo invalida para DataLoaderWorker")
            query = f"SELECT * FROM {self._quote_identifier(target_table)}"

            order_clause = self._normalize_order_by(self.order_by)
            if order_clause:
                query += f" ORDER BY {order_clause}"
            elif self.limit is not None or int(self.offset or 0) > 0:
                query += f' ORDER BY {self._quote_identifier("numero_ssa")} DESC'

            if self.limit is not None:
                limit_int = int(self.limit)
                if limit_int < 0:
                    raise ValueError("LIMIT nao pode ser negativo")
                query += f" LIMIT {limit_int}"

            offset_int = int(self.offset or 0)
            if offset_int < 0:
                raise ValueError("OFFSET não pode ser negativo")
            if offset_int > 0:
                # SQLite exige LIMIT antes de OFFSET.
                if self.limit is None:
                    query += " LIMIT -1"
                query += f" OFFSET {offset_int}"

            if self._is_cancelled():
                return
            df = query_db(self.db_path, "", query, raise_on_error=True)
            if self._is_cancelled():
                return
            if not isinstance(df, pd.DataFrame):
                raise TypeError("query_db retornou tipo invalido para DataLoaderWorker")
            try:
                df = self._prepare_dataframe_for_ui(df)
            except (TypeError, ValueError, AttributeError, KeyError) as exc:
                logger.warning(
                    "Falha no preprocessamento do DataLoaderWorker; mantendo DataFrame bruto: %s",
                    exc,
                )
            # Resultado vazio eh valido com paginacao (pagina sem linhas).
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
