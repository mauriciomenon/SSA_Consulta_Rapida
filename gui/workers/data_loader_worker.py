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
from shared.numero_ssa import normalize_strict, strip_canonical_decimal_artifact

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte seguro a paginação."""

    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)
    _DEFAULT_UI_STATUS_LAST = "STE"
    _SQLITE_INTEGER_PREFIX_RE = re.compile(r"^\s*([+-]?\d+)")
    _DEFAULT_UI_SORT_SPEC = (
        {
            "column": "situacao",
            "kind": "status_last",
            "last_value": "STE",
            "ascending": True,
            "temp_column": "__sort_situacao",
        },
        {
            "column": "numero_ssa",
            "kind": "sqlite_integer_prefix",
            "ascending": False,
            "temp_column": "__sort_numero_ssa",
        },
    )

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
        clause_parts = []
        for rule in cls._DEFAULT_UI_SORT_SPEC:
            column = str(rule["column"]).replace('"', '""')
            direction = "ASC" if bool(rule["ascending"]) else "DESC"
            if rule["kind"] == "status_last":
                last_value = str(rule["last_value"]).replace("'", "''")
                clause_parts.append(
                    f'CASE WHEN UPPER(CAST("{column}" AS TEXT)) = '
                    f"'{last_value}' THEN 1 ELSE 0 END {direction}"
                )
            elif rule["kind"] == "sqlite_integer_prefix":
                clause_parts.append(f'CAST("{column}" AS INTEGER) {direction}')
            else:
                raise ValueError(f"Regra de ordenacao default desconhecida: {rule}")
        return ", ".join(clause_parts)

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

    @staticmethod
    def _sanitize_ssa_like_value(value) -> str:
        try:
            canonical_value = strip_canonical_decimal_artifact(value)
        except Exception:
            return ""
        normalized_value = normalize_strict(canonical_value)
        if normalized_value is not None:
            return normalized_value
        if canonical_value is None:
            return ""
        try:
            if isinstance(canonical_value, float):
                if pd.isna(canonical_value):
                    return ""
                if canonical_value.is_integer():
                    return str(int(canonical_value))
                return str(canonical_value).strip()
        except (TypeError, ValueError):
            pass
        text = str(canonical_value).strip()
        if not text:
            return ""
        if text.lower() in {"nan", "none", "nat", "<na>"}:
            return ""
        folded_digits = re.sub(r"\D+", "", text)
        if len(folded_digits) == 9:
            return folded_digits
        return text

    @classmethod
    def _coerce_sqlite_integer_prefix_series(cls, values: pd.Series) -> pd.Series:
        return (
            values.astype(str)
            .str.extract(cls._SQLITE_INTEGER_PREFIX_RE, expand=False)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0)
            .astype("int64")
        )

    @classmethod
    def _build_initial_sorted_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        # Fallback raro para frames ja materializados fora do load SQL principal.
        # Deve espelhar a regra canonica aplicada por _build_default_ui_order_clause().
        base = df
        try:
            sort_columns = []
            ascending = []
            sort_assignments = {}
            for rule in cls._DEFAULT_UI_SORT_SPEC:
                source_column = str(rule["column"])
                temp_column = str(rule["temp_column"])
                sort_columns.append(temp_column)
                ascending.append(bool(rule["ascending"]))
                if source_column not in base.columns:
                    default_value = False if rule["kind"] == "status_last" else 0
                    sort_assignments[temp_column] = pd.Series(
                        [default_value] * len(base), index=base.index
                    )
                    continue
                source_series = base[source_column]
                if rule["kind"] == "status_last":
                    sort_assignments[temp_column] = (
                        source_series.astype(str)
                        .str.upper()
                        .eq(str(rule["last_value"]))
                    )
                elif rule["kind"] == "sqlite_integer_prefix":
                    sort_assignments[temp_column] = (
                        cls._coerce_sqlite_integer_prefix_series(source_series)
                    )
                else:
                    raise ValueError(
                        f"Regra de ordenacao default desconhecida: {rule}"
                    )
            base = (
                base.assign(**sort_assignments)
                .sort_values(
                    by=sort_columns,
                    ascending=ascending,
                    na_position="last",
                )
                .drop(columns=sort_columns)
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                "Falha na ordenacao inicial durante preprocessamento do DataLoaderWorker: %s",
                exc,
            )
        return base

    @staticmethod
    def _build_non_null_columns(df: pd.DataFrame) -> list[str]:
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

    def _prepare_dataframe_for_ui(
        self, df: pd.DataFrame, *, already_sorted_for_ui: bool = False
    ) -> pd.DataFrame:
        working_df = (
            df
            if self.order_by or already_sorted_for_ui
            else self._build_initial_sorted_dataframe(df)
        )
        sanitized_df = working_df
        for ssa_col in ("numero_ssa", "derivada_de"):
            if ssa_col in sanitized_df.columns:
                text_series = sanitized_df[ssa_col].astype("string")
                needs_sanitize = (
                    text_series.isna()
                    | text_series.str.contains(
                        r"^\s*$|^\s|\s$|\.0+$|[^0-9\s-]",
                        regex=True,
                        na=True,
                    )
                )
                if bool(needs_sanitize.any()):
                    sanitized_series = text_series.fillna("").copy()
                    sanitized_series.loc[needs_sanitize] = text_series.loc[
                        needs_sanitize
                    ].map(
                        self._sanitize_ssa_like_value
                    )
                    sanitized_df[ssa_col] = sanitized_series
                else:
                    sanitized_df[ssa_col] = text_series.fillna("")
        pre_sorted_df = sanitized_df
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
                df = self._prepare_dataframe_for_ui(
                    df, already_sorted_for_ui=already_sorted_for_ui
                )
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
