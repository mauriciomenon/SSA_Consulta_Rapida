"""Lógica de UPsert desacoplada de `database.py`.

Mantém a implementação original com pequenas adaptações para reduzir
acoplamento e permitir testes mais focados. Importado por `database.py` para
retrocompatibilidade (funções públicas não mudam de nome).

CIRCULAR DEPENDENCY MITIGATION:
This module is imported at top-level by database.py. To avoid circular import errors,
we use lazy imports (inside functions) when we need to import from database.py.
DO NOT add top-level imports from database.py - use lazy imports only.
"""
# Last modified: 2025-10-29T11:00:00 (circular import documentation)

# Module contract:
# - Owns schema sync for dynamic columns and the hot path for merge/upsert.
# - Any performance tuning here must be validated with sentinels and full rescan.
# - Keep `ssa_table` schema-first; do not derive canonical schema from DataFrames.
# - Related modules: armazenamento.database, armazenamento.database_validation.

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3 as _sqlite3_typehint
import sys
from typing import Any, Mapping, cast

import numpy as np
import pandas as pd

from shared.date_utils import parse_any_date
from shared.db_names import CANONICAL_SSA_TABLE
from utils.file_metadata import parse_datetime_from_filename

from .identifier_utils import quote_identifier as _quote_identifier
from .numero_ssa_utils import normalize_numero_ssa_storage

# Lazy imports from database.py to avoid circular dependency (see line 303)

logger = logging.getLogger(__name__)
_INVALID_IDENTIFIER_CHARS_RE = re.compile(r"[^A-Za-z0-9_]+")
_VALID_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_VALID_UPSERT_POLICIES = {"consulta_only", "no_short", "all_short"}
_RUNTIME_STATE: dict[str, str | None] = {"short_circuit_policy": None}
_SQLITE_IN_MAX_VARS = 900
_TEXTUAL_NULL_SENTINELS = {"", "<na>", "none", "nan", "null", "n/a", "-"}
_SSA_EVENT_RECORDS_DDL = """
CREATE TABLE IF NOT EXISTS ssa_event_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_ssa TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_order INTEGER NOT NULL CHECK (record_order > 0),
    record_label TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    arquivo_origem TEXT NOT NULL,
    data_planilha TEXT,
    data_arquivo_origem TEXT,
    source_sheet TEXT NOT NULL,
    source_row INTEGER NOT NULL CHECK (source_row > 0),
    UNIQUE (numero_ssa, record_type, record_order, payload_json)
)
"""
_SITUACAO_RANK = {
    # Waiting/planning states
    "AAD": 10,
    "AAT": 10,
    "ACC": 10,
    "ACS": 10,
    "ADI": 10,
    "ADM": 10,
    "AIM": 10,
    "AIP": 10,
    "AMP": 10,
    "APG": 10,
    "APL": 10,
    "APV": 10,
    "ASE": 10,
    "ASI": 10,
    "ASO": 10,
    "SAS": 12,
    # Execution states
    "SEE": 20,
    "SES": 20,
    "SPG": 20,
    "SRP": 20,
    # Final/terminal states
    "SAD": 30,
    "SCA": 30,
    "SCD": 30,
    "SCS": 30,
    "STE": 30,
}

# Constantes removidas (vindas do util central). Mantidas só se necessário futuro.


def _validate_canonical_storage_ids(work_local: pd.DataFrame) -> None:
    for col in ("numero_ssa", "derivada_de"):
        if col not in work_local.columns:
            continue
        series = work_local[col].dropna().astype(str).str.strip()
        if series.str.contains(".", regex=False).any():
            raise ValueError(
                f"Non-canonical value detected in {col}; decimal artifact is not allowed"
            )


def infer_sql_type(series: pd.Series | None) -> str:
    """Infer a SQLite column type from a pandas Series."""
    if series is None:
        return "TEXT"
    try:
        non_null = series.dropna()
    except Exception:  # pragma: no cover
        return "TEXT"
    if non_null.empty:
        return "TEXT"
    try:
        if pd.api.types.is_integer_dtype(non_null):
            return "INTEGER"
        if pd.api.types.is_bool_dtype(non_null):
            return "INTEGER"
        if pd.api.types.is_float_dtype(non_null):
            return "REAL"
        if pd.api.types.is_datetime64_any_dtype(non_null):
            return "TEXT"
    except Exception:  # pragma: no cover
        return "TEXT"
    return "TEXT"


def _is_placeholder_column_name(column_name: Any) -> bool:
    """Return True for empty/placeholder dynamic headers that should be ignored."""
    if column_name is None:
        return True
    if isinstance(column_name, float) and pd.isna(column_name):
        return True
    text = str(column_name).strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered in {"nan", "none", "null"}:
        return True
    return lowered.startswith("unnamed:")


def _sanitize_dynamic_column_name(
    column_name: Any,
    *,
    existing_columns: set[str],
    reserved_names: set[str],
    assigned_names: set[str],
) -> str | None:
    """Map dynamic column names to safe SQL identifiers with deterministic reuse."""
    if _is_placeholder_column_name(column_name):
        return None

    base = _INVALID_IDENTIFIER_CHARS_RE.sub("_", str(column_name).strip())
    base = base.strip("_").lower()
    if not base:
        return None
    if base in {"nan", "none", "null"}:
        return None
    if base[0].isdigit():
        base = f"c_{base}"

    if base in existing_columns and base not in reserved_names:
        assigned_names.add(base)
        return base

    candidate = base
    suffix = 1
    while (
        candidate in reserved_names
        or candidate in assigned_names
        or candidate in existing_columns
        or _VALID_IDENTIFIER_RE.fullmatch(candidate) is None
    ):
        candidate = f"{base}_{suffix}"
        suffix += 1
    assigned_names.add(candidate)
    return candidate


def _build_table_projection(conn: Any, quoted_table_name: str) -> str:
    rows = conn.execute(f"PRAGMA table_info({quoted_table_name})").fetchall()  # nosec B608
    columns = [str(row[1]) for row in rows if len(row) > 1 and row[1]]
    if not columns:
        raise ValueError(f"No columns found for table: {quoted_table_name}")
    return ", ".join(_quote_identifier(column) for column in columns)


def _coerce_sqlite_scalar(value: Any) -> Any:
    if isinstance(value, np.generic) and np.isscalar(value):
        scalar_value = cast(np.generic, value)
        value = scalar_value.item()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError, AttributeError):  # pragma: no cover
        return value
    return value


def sanitize_textual_null_sentinels(frame: pd.DataFrame) -> pd.DataFrame:
    sanitized: pd.DataFrame | None = None
    for col_idx, _col in enumerate(frame.columns):
        series = frame.iloc[:, col_idx]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            text_series = (
                series
                if pd.api.types.is_string_dtype(series)
                else series.astype("string")
            )
            sentinel_mask = (
                text_series.str.strip()
                .str.casefold()
                .isin(_TEXTUAL_NULL_SENTINELS)
                .to_numpy(dtype=bool, na_value=False)
            )
            if not sentinel_mask.any():
                continue
            if sanitized is None:
                sanitized = frame.copy()
            sanitized.iloc[:, col_idx] = series.where(~sentinel_mask, None)
    return sanitized if sanitized is not None else frame


def prepare_dataframe_for_storage(
    frame: pd.DataFrame,
    *,
    normalize_derivada: bool,
) -> pd.DataFrame:
    work_local = apply_column_whitelist(frame)
    work_local = sanitize_textual_null_sentinels(work_local).reset_index(drop=True)
    if "numero_ssa" in work_local.columns:
        work_local["numero_ssa"] = work_local["numero_ssa"].map(
            normalize_numero_ssa_storage
        )
    if normalize_derivada and "derivada_de" in work_local.columns:
        work_local["derivada_de"] = work_local["derivada_de"].map(
            normalize_numero_ssa_storage
        )
    return work_local


def _append_dataframe_rows(
    conn: Any,
    table_name: str,
    frame: pd.DataFrame,
    *,
    chunk_size: int | None = None,
) -> int:
    if frame.empty:
        return 0
    columns = [str(col) for col in frame.columns]
    if not columns:
        return 0
    effective_chunk_size = (
        int(chunk_size)
        if chunk_size and chunk_size > 0
        else max(1, min(500, 999 // len(columns)))
    )
    quoted_table = _quote_identifier(table_name)
    quoted_columns = ", ".join(_quote_identifier(col) for col in columns)
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = (
        f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})"  # nosec B608
    )
    cursor = conn.cursor()
    total_inserted = 0
    for start in range(0, len(frame), effective_chunk_size):
        chunk = frame.iloc[start : start + effective_chunk_size]
        rows = [
            tuple(_coerce_sqlite_scalar(value) for value in row)
            for row in chunk.itertuples(index=False, name=None)
        ]
        if not rows:
            continue
        try:
            cursor.executemany(insert_sql, rows)
        except Exception as exc:
            logger.error(
                "Falha no append em lote para '%s' (offset=%s, size=%s): %s",
                table_name,
                start,
                len(rows),
                exc,
            )
            raise
        total_inserted += len(rows)
    return total_inserted


def _begin_transaction_if_needed(conn: Any, *, context: str) -> None:
    in_transaction = getattr(conn, "in_transaction", None)
    if in_transaction is not None and bool(in_transaction):
        return
    try:
        conn.execute("BEGIN")
    except _sqlite3_typehint.OperationalError as exc:
        in_transaction_after_error = getattr(conn, "in_transaction", None)
        if in_transaction_after_error is not None and bool(in_transaction_after_error):
            logger.debug(
                "BEGIN ignorado em %s (transacao ja ativa apos erro): %s", context, exc
            )
            return
        logger.error("Falha ao iniciar transacao em %s: %s", context, exc)
        raise
    except Exception as exc:
        logger.error("Erro inesperado ao iniciar transacao em %s: %s", context, exc)
        raise


def _sync_dynamic_columns_and_schema(
    *,
    work: pd.DataFrame,
    table_name: str,
    existing_columns: set[str],
    db_path: str | Any,
    conn: Any,
    db_module: Any,
) -> pd.DataFrame:
    from .identifier_utils import is_valid_identifier

    rename_map: dict[str, str] = {}
    drop_columns: list[Any] = []
    reserved_names = {
        str(col)
        for col in work.columns
        if isinstance(col, str)
        and is_valid_identifier(col)
        and not _is_placeholder_column_name(col)
    }
    assigned_names: set[str] = set()
    ordered_columns = sorted(work.columns, key=lambda value: str(value).lower())
    for col in ordered_columns:
        if _is_placeholder_column_name(col):
            drop_columns.append(col)
            continue
        if col in existing_columns or is_valid_identifier(col):
            continue
        sanitized = _sanitize_dynamic_column_name(
            col,
            existing_columns=existing_columns,
            reserved_names=reserved_names,
            assigned_names=assigned_names,
        )
        if not sanitized:
            logger.warning(
                "Coluna dinamica invalida '%s' foi ignorada (nao foi possivel sanitizar identificador).",
                col,
            )
            drop_columns.append(col)
            continue
        rename_map[col] = sanitized
        reserved_names.add(sanitized)

    if drop_columns:
        logger.warning(
            "Colunas dinamicas placeholder foram descartadas: %s", drop_columns
        )
        work = work.drop(columns=drop_columns, errors="ignore")

    if rename_map:
        logger.warning(
            "Colunas dinamicas foram sanitizadas para SQL seguro: %s", rename_map
        )
        work = work.rename(columns=rename_map)

    # Enforce whitelist after dynamic rename/drop to avoid schema drift by env policy.
    final_work = apply_column_whitelist(work)

    missing_columns = [col for col in final_work.columns if col not in existing_columns]
    for col in missing_columns:
        sql_type = infer_sql_type(
            final_work[col] if col in final_work.columns else None
        )
        logger.info(
            "Adicionando coluna ausente '%s' ao schema (tipo %s)", col, sql_type
        )
        if not is_valid_identifier(col):
            raise ValueError(f"Invalid SQL identifier for column: {col}")
        if isinstance(db_path, str):
            db_module.ensure_column_exists(db_path, table_name, col, sql_type)
        else:
            conn.execute(
                f"ALTER TABLE {_quote_identifier(table_name)} "
                f"ADD COLUMN {_quote_identifier(col)} {sql_type}"
            )
    return final_work


def _should_update_existing(
    existing_row: pd.Series | Mapping[str, Any],
    new_row: pd.Series | Mapping[str, Any],
) -> bool:
    existing_date = existing_row.get("data_cadastro")
    new_date = new_row.get("data_cadastro")
    try:
        terminal_states = {"STE", "SCA"}

        def _status_code(value: Any) -> str:
            text = str(value or "").strip().upper()
            if not text:
                return ""
            return text.split(" - ", 1)[0].strip()

        def _situacao_rank(value: Any) -> int:
            code = _status_code(value)
            return _SITUACAO_RANK.get(code, 0)

        def _parse(dt):  # evita E731 lambda
            if dt in (None, "") or (isinstance(dt, float) and pd.isna(dt)):
                return None
            parsed = parse_any_date(dt)
            if parsed is None:
                return None
            return pd.to_datetime(parsed, errors="coerce", format="%Y-%m-%d %H:%M:%S")

        def _parse_snapshot_dt(
            planilha_dt_value: Any = None,
            origin_dt_value: Any = None,
            origin_name_value: Any = None,
        ) -> pd.Timestamp | None:
            for raw_value in (planilha_dt_value, origin_dt_value):
                parsed = parse_any_date(raw_value)
                if parsed is not None:
                    timestamp = pd.Timestamp(parsed)
                    if pd.isna(timestamp):
                        return None
                    return cast(pd.Timestamp, timestamp)
            raw = str(origin_name_value or "").strip()
            if not raw:
                return None
            parsed = parse_datetime_from_filename(raw)
            if parsed is None:
                return None
            timestamp = pd.Timestamp(parsed)
            if pd.isna(timestamp):
                return None
            return cast(pd.Timestamp, timestamp)

        existing_situacao = _status_code(existing_row.get("situacao"))
        if existing_situacao in terminal_states:
            return False

        existing_file_dt = _parse_snapshot_dt(
            existing_row.get("data_planilha"),
            existing_row.get("data_arquivo_origem"),
            existing_row.get("arquivo_origem"),
        )
        new_file_dt = _parse_snapshot_dt(
            new_row.get("data_planilha"),
            new_row.get("data_arquivo_origem"),
            new_row.get("arquivo_origem"),
        )
        has_file_context = any(
            parse_any_date(new_row.get(field)) is not None
            or str(new_row.get(field) or "").strip() != ""
            for field in ("data_planilha", "data_arquivo_origem", "arquivo_origem")
        )
        # Sem timestamp confiavel no arquivo novo: permitir apenas inserts.
        # Neste caminho (update) sempre bloqueia.
        if has_file_context and new_file_dt is None:
            return False
        if existing_file_dt is not None and new_file_dt is not None:
            if new_file_dt < existing_file_dt:
                return False
            if new_file_dt > existing_file_dt:
                return True

        e_dt = _parse(existing_date)
        n_dt = _parse(new_date)
        if e_dt is None and n_dt is None:
            return True
        if n_dt is None and e_dt is not None:
            return False
        if n_dt is not None and e_dt is None:
            return True
        if e_dt is not None and n_dt is not None:
            # Ambos preenchidos; tratar NaT separadamente
            e_is_nat = pd.isna(e_dt)
            n_is_nat = pd.isna(n_dt)
            if e_is_nat and n_is_nat:
                return True  # empate sem datas válidas => atualizar
            if n_is_nat and not e_is_nat:
                return False  # novo vazio, existente tem data
            if not n_is_nat and e_is_nat:
                return True  # novo tem data, existente vazio
            # Ambos válidos
            try:
                # Converter para nanos epoch se possível (evita mypy/pylance reclamação de NaTType)
                n_val = getattr(n_dt, "value", None)
                e_val = getattr(e_dt, "value", None)
                if n_val is None or e_val is None:
                    return True
                if n_val == e_val:
                    # Tie-breaker de estado para evitar regressao de situacao
                    # quando arquivos de mesma data chegam em ordem diferente.
                    new_rank = _situacao_rank(new_row.get("situacao"))
                    existing_rank = _situacao_rank(existing_row.get("situacao"))
                    if new_rank < existing_rank:
                        return False
                return bool(n_val >= e_val)
            except Exception:  # pragma: no cover
                return True
        return True
    except Exception:  # pragma: no cover
        return True


def _resolve_upsert_config() -> tuple[dict[str, int], list[str], list[str]]:
    status_order_env = os.environ.get("SSA_STATUS_ORDER")
    status_order_list = (
        [s.strip() for s in status_order_env.split(",") if s.strip()]
        if status_order_env
        else ["ABERTO", "EM_ANALISE", "EM_EXECUCAO", "SCA", "STE"]
    )
    status_rank = {s: i for i, s in enumerate(status_order_list)}
    desc_cols_env = os.environ.get("SSA_DESC_COLUMNS")
    description_columns = (
        [c.strip() for c in desc_cols_env.split(",") if c.strip()]
        if desc_cols_env
        else ["descricao_ssa", "descricao", "detalhes", "comentarios"]
    )
    date_columns = [
        "data_cadastro",
        "prazo_limite",
        "data_limite",
        "desde",
        "desde_1",
        "desde_2",
        "ate",
        "ate_1",
        "ate_2",
        "data_inicio_programada",
        "data_programacao",
        "data_inicio_reprogramada",
        "data_reprogramacao",
        "instalacao_estimada",
        "executado",
        "concluido",
    ]
    return status_rank, description_columns, date_columns


def _resolve_short_circuit_policy(policy_override: str | None = None) -> str:
    runtime_policy = _RUNTIME_STATE["short_circuit_policy"]
    policy = (
        (
            policy_override
            or runtime_policy
            or os.environ.get("SSA_UPSERT_SHORT_CIRCUIT_POLICY", "consulta_only")
        )
        .strip()
        .lower()
    )
    if not policy:
        return "consulta_only"
    if policy not in _VALID_UPSERT_POLICIES:
        logger.warning(
            "Politica de short-circuit invalida %s, usando consulta_only",
            policy,
        )
        return "consulta_only"
    return policy


def set_runtime_short_circuit_policy(policy: str | None) -> None:
    """Configura politica de short-circuit para o processo atual."""
    if policy is None:
        _RUNTIME_STATE["short_circuit_policy"] = None
        return
    normalized = str(policy).strip().lower()
    if not normalized:
        _RUNTIME_STATE["short_circuit_policy"] = None
        return
    if normalized not in _VALID_UPSERT_POLICIES:
        logger.warning(
            "Politica de short-circuit invalida '%s'; usando consulta_only",
            policy,
        )
        _RUNTIME_STATE["short_circuit_policy"] = "consulta_only"
        return
    _RUNTIME_STATE["short_circuit_policy"] = normalized


def _is_empty_upsert_value(val: Any) -> bool:
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError, AttributeError):  # pragma: no cover
        return (
            isinstance(val, str) and val.strip().casefold() in _TEXTUAL_NULL_SENTINELS
        )
    if isinstance(val, str) and val.strip().casefold() in _TEXTUAL_NULL_SENTINELS:
        return True
    return False


def _parse_upsert_dt(value: Any):
    try:
        if _is_empty_upsert_value(value):
            return None
        return pd.to_datetime(value, errors="coerce")
    except (TypeError, ValueError, AttributeError):
        return None


def _safe_parse_any_date(value: Any, column_name: str) -> Any:
    try:
        return parse_any_date(value)
    except (TypeError, ValueError, AttributeError) as exc:
        logger.debug(
            "Falha ao normalizar valor de data em %s; preservando valor original %r: %s",
            column_name,
            value,
            exc,
        )
        return value


def _merge_complement_row(
    existing_row: pd.Series,
    new_row: pd.Series,
    status_rank: dict[str, int],
    description_columns: list[str],
    date_columns: list[str],
) -> pd.Series:
    result = existing_row.copy()
    for col in new_row.index:
        new_val = new_row[col]
        if col == "numero_ssa":
            continue
        if col == "situacao":
            old_val = result.get(col)
            if _is_empty_upsert_value(old_val) and not _is_empty_upsert_value(new_val):
                result[col] = new_val
            else:
                old_rank = status_rank.get(str(old_val), -1)
                new_rank = status_rank.get(str(new_val), -1)
                if new_rank > old_rank:
                    result[col] = new_val
            continue
        if col in date_columns:
            old_dt = _parse_upsert_dt(result.get(col))
            new_dt = _parse_upsert_dt(new_val)
            if old_dt is None and new_dt is not None:
                result[col] = new_val
            elif old_dt is not None and new_dt is not None and new_dt > old_dt:
                result[col] = new_val
            continue
        if col in description_columns:
            old_val = result.get(col)
            if _is_empty_upsert_value(old_val) and not _is_empty_upsert_value(new_val):
                result[col] = new_val
            else:
                if (
                    isinstance(new_val, str)
                    and isinstance(old_val, str)
                    and len(new_val) > len(old_val) + 10
                ):
                    result[col] = new_val
            continue
        old_val = result.get(col)
        if _is_empty_upsert_value(old_val) and not _is_empty_upsert_value(new_val):
            result[col] = new_val
    if not isinstance(result, pd.Series):
        raise TypeError("Expected pd.Series from _merge_complement_row")
    return result


def _merge_overwrite_with_incoming_non_empty(
    existing_row: pd.Series, new_row: pd.Series
) -> pd.Series:
    incoming = new_row.reindex(existing_row.index, fill_value=None)
    empty_mask = incoming.apply(
        lambda value: (
            pd.isna(value)
            or value in (None, "")
            or (isinstance(value, str) and value.strip() == "")
        )
    )
    merged = existing_row.where(empty_mask, incoming)
    for col in new_row.index:
        if col not in merged.index:
            merged[col] = new_row[col]
    if not isinstance(merged, pd.Series):
        raise TypeError(
            "Expected pd.Series from _merge_overwrite_with_incoming_non_empty"
        )
    return merged


def _log_setor_executor_change_if_needed(
    existing_row: pd.Series,
    incoming_row: pd.Series,
    merged_row: pd.Series,
) -> None:
    existing_sector = existing_row.get("setor_executor")
    incoming_sector = incoming_row.get("setor_executor")
    merged_sector = merged_row.get("setor_executor")

    if _is_empty_upsert_value(existing_sector) or _is_empty_upsert_value(
        incoming_sector
    ):
        return

    existing_text = str(existing_sector).strip()
    incoming_text = str(incoming_sector).strip()
    merged_text = (
        "" if _is_empty_upsert_value(merged_sector) else str(merged_sector).strip()
    )

    if not existing_text or not incoming_text:
        return
    if existing_text == incoming_text or merged_text != incoming_text:
        return

    logger.info(
        "Upsert atualizou setor_executor para SSA %s: %s -> %s (data_cadastro=%s)",
        existing_row.get("numero_ssa"),
        existing_text,
        incoming_text,
        incoming_row.get("data_cadastro"),
    )


def _persist_ssa_event_records(
    conn: Any,
    records: list[dict[str, Any]],
    source_frame: pd.DataFrame,
) -> int:
    if not records:
        return 0

    source_metadata: dict[str, Any] = {}
    has_event_records_attr = "ssa_event_records" in source_frame.attrs
    event_records_attr = source_frame.attrs.pop("ssa_event_records", None)
    try:
        for column in ("arquivo_origem", "data_planilha", "data_arquivo_origem"):
            source_metadata[column] = None
            if column not in source_frame.columns:
                continue
            for value in source_frame[column].tolist():
                if not _is_empty_upsert_value(value):
                    source_metadata[column] = _coerce_sqlite_scalar(value)
                    break
    finally:
        if has_event_records_attr:
            source_frame.attrs["ssa_event_records"] = event_records_attr
    if _is_empty_upsert_value(source_metadata["arquivo_origem"]):
        raise ValueError("Hierarchical event records require arquivo_origem metadata")

    rows: list[tuple[Any, ...]] = []
    required_fields = {
        "numero_ssa",
        "record_type",
        "record_order",
        "record_label",
        "payload_json",
        "source_sheet",
        "source_row",
    }
    for record in records:
        missing_fields = required_fields.difference(record)
        if missing_fields:
            raise ValueError(
                f"Hierarchical event record is missing fields: {sorted(missing_fields)}"
            )
        numero_ssa = normalize_numero_ssa_storage(record["numero_ssa"])
        if numero_ssa is None:
            raise ValueError(
                f"Invalid numero_ssa in hierarchical event record: {record['numero_ssa']!r}"
            )
        record_order = int(record["record_order"])
        source_row = int(record["source_row"])
        if record_order <= 0 or source_row <= 0:
            raise ValueError("Hierarchical event order and source row must be positive")
        payload_json = str(record["payload_json"])
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Hierarchical event payload must be a JSON object")

        rows.append(
            (
                numero_ssa,
                str(record["record_type"]).strip(),
                record_order,
                str(record["record_label"]).strip(),
                payload_json,
                source_metadata["arquivo_origem"],
                source_metadata["data_planilha"],
                source_metadata["data_arquivo_origem"],
                str(record["source_sheet"]).strip(),
                source_row,
            )
        )

    conn.execute(_SSA_EVENT_RECORDS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ssa_event_records_lookup "
        "ON ssa_event_records (numero_ssa, record_type, record_order)"
    )
    conn.executemany(
        """
        INSERT INTO ssa_event_records (
            numero_ssa,
            record_type,
            record_order,
            record_label,
            payload_json,
            arquivo_origem,
            data_planilha,
            data_arquivo_origem,
            source_sheet,
            source_row
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (numero_ssa, record_type, record_order, payload_json)
        DO UPDATE SET
            record_label = excluded.record_label,
            arquivo_origem = excluded.arquivo_origem,
            data_planilha = excluded.data_planilha,
            data_arquivo_origem = excluded.data_arquivo_origem,
            source_sheet = excluded.source_sheet,
            source_row = excluded.source_row
        WHERE ssa_event_records.data_planilha IS NULL
           OR (
               excluded.data_planilha IS NOT NULL
               AND excluded.data_planilha >= ssa_event_records.data_planilha
           )
        """,
        rows,
    )
    return len(rows)


def _persist_upsert_chunk(
    conn: Any,
    table_name: str,
    rows_to_persist: dict[Any, pd.Series],
    delete_keys: set[Any],
) -> None:
    _begin_transaction_if_needed(conn, context="_persist_upsert_chunk")
    quoted_table_name = _quote_identifier(table_name)
    if delete_keys:
        placeholders = ", ".join(["?"] * len(delete_keys))
        conn.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            f"DELETE FROM {quoted_table_name} WHERE numero_ssa IN ({placeholders})",  # nosec B608
            list(delete_keys),
        )
    if rows_to_persist:
        rows_list: list[pd.Series] = []
        for row in rows_to_persist.values():
            if not isinstance(row, pd.Series):
                raise TypeError("rows_to_persist must contain pd.Series values.")
            rows_list.append(row.copy())
        all_columns = sorted({idx for row in rows_list for idx in row.index})
        normalized_rows = [row.reindex(all_columns) for row in rows_list]
        persist_df = pd.DataFrame(normalized_rows)
        for col in persist_df.columns:
            if persist_df[col].dtype == object:
                persist_df[col] = persist_df[col].map(_coerce_sqlite_scalar)
        _append_dataframe_rows(conn, table_name, persist_df)


def _prepare_upsert_target_row(
    row: pd.Series,
    existing_row: pd.Series | None,
    complementary_mode: bool,
    status_rank: dict[str, int],
    description_columns: list[str],
    date_columns: list[str],
) -> tuple[pd.Series, bool]:
    if existing_row is None:
        return row.copy(), True

    if not complementary_mode:
        if not _should_update_existing(existing_row, row):
            return existing_row.copy(), False
        merged_row = _merge_overwrite_with_incoming_non_empty(existing_row, row)
        if merged_row.equals(existing_row):
            return existing_row.copy(), False
        _log_setor_executor_change_if_needed(existing_row, row, merged_row)
        return merged_row, True

    merged_series = _merge_complement_row(
        existing_row,
        row,
        status_rank,
        description_columns,
        date_columns,
    )
    return merged_series, not merged_series.equals(existing_row)


def _upsert_cache_key(numero: Any) -> str | None:
    if pd.isna(numero):
        return None
    return str(numero).strip()


def _values_equal_for_exact_overlap(left: Any, right: Any) -> bool:
    if pd.isna(left):
        left = None
    elif isinstance(left, np.generic):
        left = left.item()
    if pd.isna(right):
        right = None
    elif isinstance(right, np.generic):
        right = right.item()
    return left == right


def _tuples_match_for_exact_overlap(
    left: tuple[Any, ...] | None,
    right: tuple[Any, ...],
) -> bool:
    if left is None or len(left) != len(right):
        return False
    return all(
        _values_equal_for_exact_overlap(left_value, right_value)
        for left_value, right_value in zip(left, right, strict=False)
    )


def _table_has_existing_ssa_rows(conn: Any, table_name: str) -> bool:
    quoted_table_name = _quote_identifier(table_name)
    cursor = conn.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        f"SELECT 1 FROM {quoted_table_name} WHERE numero_ssa IS NOT NULL LIMIT 1"  # nosec B608
    )
    return cursor.fetchone() is not None


def _resolve_upsert_chunk_size(row_count: int) -> int:
    if row_count <= 1000:
        return 100
    return 250


def _should_enable_exact_overlap_short_circuit(
    chunk: pd.DataFrame,
    *,
    policy: str | None = None,
    complementary_mode: bool = False,
) -> bool:
    if complementary_mode:
        return False
    resolved_policy = _resolve_short_circuit_policy(policy)
    if resolved_policy == "no_short":
        return False
    if resolved_policy == "all_short":
        if "arquivo_origem" not in chunk.columns:
            return False
        source_values = [
            str(value).strip().casefold()
            for value in chunk["arquivo_origem"].dropna().unique().tolist()
            if str(value).strip()
        ]
        return len(source_values) == 1

    if "arquivo_origem" not in chunk.columns:
        return False
    source_values = [
        str(value).strip().casefold()
        for value in chunk["arquivo_origem"].dropna().unique().tolist()
        if str(value).strip()
    ]
    return len(source_values) == 1 and source_values[0].startswith("consulta ssa")


def _load_existing_chunk_caches(
    conn: Any,
    quoted_table_name: str,
    chunk_num_ssa: list[Any],
    chunk_columns: list[str],
    numero_ssa_idx: int,
    *,
    enable_exact_overlap_short_circuit: bool,
) -> tuple[pd.DataFrame, dict[str, tuple[Any, ...]], dict[str, tuple[Any, ...]]]:
    if not chunk_num_ssa:
        return pd.DataFrame(), {}, {}
    existing_parts: list[pd.DataFrame] = []
    projection = _build_table_projection(conn, quoted_table_name)
    for start in range(0, len(chunk_num_ssa), _SQLITE_IN_MAX_VARS):
        query_ids = chunk_num_ssa[start : start + _SQLITE_IN_MAX_VARS]
        placeholders = ", ".join(["?"] * len(query_ids))
        part = pd.read_sql_query(
            f"SELECT {projection} FROM {quoted_table_name} WHERE numero_ssa IN ({placeholders})",  # nosec B608
            conn,
            params=query_ids,
        )
        if not part.empty:
            existing_parts.append(part)
    existing_chunk = (
        pd.concat(existing_parts, ignore_index=True, sort=False)
        if existing_parts
        else pd.DataFrame()
    )
    if existing_chunk.empty or "numero_ssa" not in existing_chunk.columns:
        return existing_chunk, {}, {}
    existing_raw_by_ssa: dict[str, tuple[Any, ...]] = {}
    existing_chunk_tuple_by_ssa: dict[str, tuple[Any, ...]] = {}
    existing_numero_ssa_idx = existing_chunk.columns.get_loc("numero_ssa")
    if not enable_exact_overlap_short_circuit:
        for existing_row_tuple in existing_chunk.itertuples(index=False, name=None):
            numero_val = existing_row_tuple[existing_numero_ssa_idx]
            cache_key = _upsert_cache_key(numero_val)
            if cache_key is None:
                continue
            existing_raw_by_ssa[cache_key] = tuple(existing_row_tuple)
        return existing_chunk, existing_raw_by_ssa, existing_chunk_tuple_by_ssa
    existing_chunk_for_compare = existing_chunk.reindex(columns=chunk_columns)
    compare_rows = existing_chunk_for_compare.itertuples(index=False, name=None)
    existing_row_pairs = zip(
        existing_chunk.itertuples(index=False, name=None), compare_rows, strict=False
    )
    for existing_row_tuple, compare_tuple in existing_row_pairs:
        numero_val = compare_tuple[numero_ssa_idx]
        cache_key = _upsert_cache_key(numero_val)
        if cache_key is None:
            continue
        existing_raw_by_ssa[cache_key] = tuple(existing_row_tuple)
        existing_chunk_tuple_by_ssa[cache_key] = tuple(compare_tuple)
    return existing_chunk, existing_raw_by_ssa, existing_chunk_tuple_by_ssa


def _load_existing_row_series(
    cache_key: str,
    existing_by_ssa: dict[str, pd.Series],
    existing_raw_by_ssa: dict[str, tuple[Any, ...]],
    existing_columns: pd.Index,
) -> pd.Series | None:
    existing_row = existing_by_ssa.get(cache_key)
    if existing_row is not None:
        return existing_row
    existing_raw = existing_raw_by_ssa.get(cache_key)
    if existing_raw is None:
        return None
    existing_row = pd.Series(existing_raw, index=existing_columns)
    existing_by_ssa[cache_key] = existing_row
    return existing_row


def _build_existing_series_cache(existing_chunk: pd.DataFrame) -> dict[str, pd.Series]:
    if existing_chunk.empty or "numero_ssa" not in existing_chunk.columns:
        return {}
    existing_by_ssa: dict[str, pd.Series] = {}
    for existing_row_tuple in existing_chunk.itertuples(index=False, name=None):
        existing_row = pd.Series(existing_row_tuple, index=existing_chunk.columns)
        numero_val = existing_row.get("numero_ssa")
        cache_key = _upsert_cache_key(numero_val)
        if cache_key is None:
            continue
        existing_by_ssa[cache_key] = existing_row
    return existing_by_ssa


def _collect_chunk_upsert_delta(
    chunk: pd.DataFrame,
    *,
    numero_ssa_idx: int,
    chunk_columns: list[str],
    existing_columns: pd.Index,
    existing_by_ssa: dict[str, pd.Series],
    existing_raw_by_ssa: dict[str, tuple[Any, ...]],
    existing_chunk_tuple_by_ssa: dict[str, tuple[Any, ...]],
    enable_exact_overlap_short_circuit: bool,
    complementary_mode: bool,
    status_rank: dict[str, int],
    description_columns: list[str],
    date_columns: list[str],
) -> tuple[dict[str, pd.Series], set[Any], int]:
    """Calcula delta de persistencia para um chunk sem executar IO no banco.

    Contrato:
    - decide somente comparacao/merge por linha;
    - atualiza caches em memoria do chunk atual;
    - nao faz DELETE/INSERT, nao abre transacao e nao valida schema.
    """
    rows_to_persist: dict[str, pd.Series] = {}
    delete_keys: set[Any] = set()
    changed_rows = 0
    for row_tuple in chunk.itertuples(index=False, name=None):
        numero_ssa = row_tuple[numero_ssa_idx]
        cache_key = _upsert_cache_key(numero_ssa)
        if cache_key is None:
            continue
        if enable_exact_overlap_short_circuit and _tuples_match_for_exact_overlap(
            existing_chunk_tuple_by_ssa.get(cache_key),
            tuple(row_tuple),
        ):
            continue
        existing_row = _load_existing_row_series(
            cache_key,
            existing_by_ssa,
            existing_raw_by_ssa,
            existing_columns,
        )
        row = pd.Series(row_tuple, index=chunk_columns)
        has_existing = existing_row is not None
        target_row, should_persist = _prepare_upsert_target_row(
            row,
            existing_row,
            complementary_mode,
            status_rank,
            description_columns,
            date_columns,
        )
        if not isinstance(target_row, pd.Series):
            raise TypeError("Expected pd.Series from _prepare_upsert_target_row")
        if should_persist:
            if has_existing and existing_row is not None:
                delete_keys.add(existing_row.get("numero_ssa"))
            merged_cache_row = target_row.copy()
            rows_to_persist[cache_key] = merged_cache_row
            existing_by_ssa[cache_key] = merged_cache_row
            if enable_exact_overlap_short_circuit:
                existing_chunk_tuple_by_ssa[cache_key] = tuple(
                    merged_cache_row.reindex(chunk_columns, fill_value=None).tolist()
                )
            changed_rows += 1
    return rows_to_persist, delete_keys, changed_rows


def _perform_upsert(
    has_ssa: pd.DataFrame,
    table_name: str,
    conn,
    *,
    chunk_size: int | None = None,
    metrics_out: dict[str, int] | None = None,
) -> int:
    complementary_mode = os.environ.get("SSA_ENABLE_COMPLEMENTARY") == "1"
    effective_policy = _resolve_short_circuit_policy()
    status_rank, description_columns, date_columns = _resolve_upsert_config()
    os.environ.get("SSA_TERMINAL_STATUSES")  # leitura única (telemetria futura)

    effective_chunk_size = (
        chunk_size
        if chunk_size is not None
        else _resolve_upsert_chunk_size(len(has_ssa))
    )
    total_upserted = 0
    inserted_keys: set[str] = set()
    updated_keys: set[str] = set()
    quoted_table_name = _quote_identifier(table_name)
    _begin_transaction_if_needed(conn, context="_perform_upsert")
    logger.debug(
        "Chunk size do upsert: %s para %s registros com numero_ssa",
        effective_chunk_size,
        len(has_ssa),
    )
    for start in range(0, len(has_ssa), effective_chunk_size):
        chunk = has_ssa.iloc[start : start + effective_chunk_size]
        chunk_columns = list(chunk.columns)
        numero_ssa_idx = chunk.columns.get_loc("numero_ssa")
        enable_exact_overlap_short_circuit = _should_enable_exact_overlap_short_circuit(
            chunk,
            policy=effective_policy,
            complementary_mode=complementary_mode,
        )

        chunk_num_ssa: list[Any] = (
            chunk["numero_ssa"].dropna().drop_duplicates().tolist()
        )

        existing_by_ssa: dict[str, pd.Series] = {}
        existing_chunk, existing_raw_by_ssa, existing_chunk_tuple_by_ssa = (
            _load_existing_chunk_caches(
                conn,
                quoted_table_name,
                chunk_num_ssa,
                chunk_columns,
                numero_ssa_idx,
                enable_exact_overlap_short_circuit=enable_exact_overlap_short_circuit,
            )
        )
        if existing_chunk.empty and len(chunk_num_ssa) == len(chunk):
            _append_dataframe_rows(conn, table_name, chunk)
            total_upserted += len(chunk)
            inserted_keys.update(
                cache_key
                for numero_ssa in chunk_num_ssa
                if (cache_key := _upsert_cache_key(numero_ssa)) is not None
            )
            logger.info(
                "Fast-path append de %s registros com numero_ssa unicos e ausentes no banco",
                len(chunk),
            )
            continue

        rows_to_persist, delete_keys, changed_rows = _collect_chunk_upsert_delta(
            chunk,
            numero_ssa_idx=numero_ssa_idx,
            chunk_columns=chunk_columns,
            existing_columns=existing_chunk.columns,
            existing_by_ssa=existing_by_ssa,
            existing_raw_by_ssa=existing_raw_by_ssa,
            existing_chunk_tuple_by_ssa=existing_chunk_tuple_by_ssa,
            enable_exact_overlap_short_circuit=enable_exact_overlap_short_circuit,
            complementary_mode=complementary_mode,
            status_rank=status_rank,
            description_columns=description_columns,
            date_columns=date_columns,
        )
        total_upserted += changed_rows
        persisted_keys = set(rows_to_persist)
        chunk_updated_keys = {
            cache_key
            for numero_ssa in delete_keys
            if (cache_key := _upsert_cache_key(numero_ssa)) is not None
        }
        updated_keys.update(chunk_updated_keys - inserted_keys)
        inserted_keys.update(persisted_keys - chunk_updated_keys)
        if rows_to_persist or delete_keys:
            _persist_upsert_chunk(conn, table_name, rows_to_persist, delete_keys)
    if metrics_out is not None:
        metrics_out["ssa_inserted"] = len(inserted_keys)
        metrics_out["ssa_updated"] = len(updated_keys)
    return total_upserted


def prepare_dataframe_for_upsert(frame: pd.DataFrame) -> pd.DataFrame:
    work_local = prepare_dataframe_for_storage(frame, normalize_derivada=True)
    _validate_canonical_storage_ids(work_local)
    date_columns = [
        "data_cadastro",
        "prazo_limite",
        "data_limite",
        "desde",
        "desde_1",
        "desde_2",
        "ate",
        "ate_1",
        "ate_2",
        "data_inicio_programada",
        "data_programacao",
        "data_inicio_reprogramada",
        "data_reprogramacao",
        "instalacao_estimada",
        "executado",
        "concluido",
    ]
    for c in date_columns:
        if c in work_local.columns:
            work_local[c] = work_local[c].map(
                lambda value, col=c: _safe_parse_any_date(value, col)
            )
    return work_local


def apply_column_whitelist(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtro de colunas baseado na variável de ambiente SSA_ALLOWED_COLUMNS.

    Mantido aqui para reutilização entre caminhos de inserção simples e smart upsert.
    Não altera DataFrame in-place; retorna cópia possivelmente reduzida.
    """
    wl = os.environ.get("SSA_ALLOWED_COLUMNS")
    if not wl:
        return df
    allowed = {c.strip() for c in wl.split(",") if c.strip()}
    if not allowed:
        return df
    drop_cols = [c for c in df.columns if c not in allowed]
    if drop_cols:
        logger.info("Colunas removidas por whitelist: %s", drop_cols)
        return df[[c for c in df.columns if c in allowed]]
    return df


def insert_dataframe_with_smart_upsert_impl(
    df: pd.DataFrame,
    db_path: str | Any,
    table_name: str,
    *,
    metrics_out: dict[str, int] | None = None,
) -> bool:
    has_event_records_attr = "ssa_event_records" in df.attrs
    event_records_raw = df.attrs.pop("ssa_event_records", [])
    if not isinstance(event_records_raw, list):
        if has_event_records_attr:
            df.attrs["ssa_event_records"] = event_records_raw
        raise TypeError("ssa_event_records DataFrame attr must be a list")
    event_records = event_records_raw
    try:
        work = prepare_dataframe_for_upsert(df)
    finally:
        if has_event_records_attr:
            df.attrs["ssa_event_records"] = event_records_raw
    if metrics_out is not None:
        metrics_out["ssa_inserted"] = 0
        metrics_out["ssa_updated"] = 0
        metrics_out["ssa_event_records_processed"] = 0
    from . import database as _db_mod  # lazy import evita circularidade

    conn: Any = None
    conn_cm = None
    external_savepoint_started = False
    if hasattr(db_path, "cursor"):  # conexão externa
        conn = cast(Any, db_path)
        close_after = False
    else:
        conn_cm = _db_mod.get_db_connection(db_path, write=True)
        conn = cast(Any, conn_cm.__enter__())
        close_after = True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cursor.fetchall()}
        table_name = _db_mod._resolve_target_table(  # pylint: disable=protected-access  # skipcq: PYL-W0212
            cast(_sqlite3_typehint.Connection, conn), table_name
        )
        table_exists = table_name in existing_tables
        if not table_exists:
            if not close_after:
                raise RuntimeError(
                    "Tabela alvo ausente em conexao externa; inicialize o schema "
                    "antes do upsert para preservar a transacao do chamador."
                )
            logger.warning(
                "Tabela alvo '%s' ausente. Aplicando bootstrap de schema canonico antes do upsert.",
                table_name,
            )
            if isinstance(db_path, str):
                _db_mod.initialize_database(db_path, "config/schema.sql")
            else:
                _db_mod.initialize_database(conn, "config/schema.sql")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {r[0] for r in cursor.fetchall()}
            table_name = _db_mod._resolve_target_table(  # pylint: disable=protected-access  # skipcq: PYL-W0212
                cast(_sqlite3_typehint.Connection, conn), table_name
            )
            table_exists = table_name in existing_tables
            if not table_exists:
                logger.error(
                    "Schema canonico aplicado, mas tabela alvo '%s' nao foi encontrada.",
                    table_name,
                )
                return False
        if not close_after:
            _begin_transaction_if_needed(
                conn, context="insert_dataframe_with_smart_upsert_impl"
            )
            conn.execute("SAVEPOINT ssa_smart_upsert")
            external_savepoint_started = True
        if table_name != CANONICAL_SSA_TABLE:
            logger.warning(
                "Upsert com tabela nao canonica resolvida para '%s'.",
                table_name,
            )
        if table_exists:
            from .identifier_utils import (
                is_valid_identifier,
            )  # local import to avoid cycles

            if not is_valid_identifier(table_name):
                raise ValueError(f"Invalid SQL identifier for table: {table_name}")
            cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"PRAGMA table_info({_quote_identifier(table_name)})"
            )
            existing_columns = {row[1] for row in cursor.fetchall()}
            work = _sync_dynamic_columns_and_schema(
                work=work,
                table_name=table_name,
                existing_columns=existing_columns,
                db_path=db_path,
                conn=conn,
                db_module=_db_mod,
            )
        if "numero_ssa" not in work.columns:
            has_ssa = pd.DataFrame()
            no_ssa = work.copy()
        else:
            has_ssa = work[work["numero_ssa"].notna()].copy()
            no_ssa = work[work["numero_ssa"].isna()].copy()
        if close_after:
            _begin_transaction_if_needed(
                conn, context="insert_dataframe_with_smart_upsert_impl"
            )
        if not no_ssa.empty:
            # Cálculo dinâmico do chunk size para evitar "too many SQL variables"
            chunk_size = (
                min(500, max(1, 999 // len(no_ssa.columns)))
                if len(no_ssa.columns) > 0
                else 500
            )
            logger.debug(
                "Chunk size calculado para insercao sem SSA: %s linhas para %s colunas",
                chunk_size,
                len(no_ssa.columns),
            )
            _append_dataframe_rows(conn, table_name, no_ssa, chunk_size=chunk_size)
            logger.info("Inseridos %s registros sem numero_ssa", len(no_ssa))
        if not has_ssa.empty:
            inserted = _perform_upsert(
                has_ssa,
                table_name,
                conn,
                metrics_out=metrics_out,
            )
            logger.info("Processados %s registros com numero_ssa via upsert", inserted)
        if event_records:
            processed_events = _persist_ssa_event_records(conn, event_records, df)
            if metrics_out is not None:
                metrics_out["ssa_event_records_processed"] = processed_events
            logger.info(
                "Processados %s registros hierarquicos em ssa_event_records",
                processed_events,
            )
        if external_savepoint_started:
            conn.execute("RELEASE SAVEPOINT ssa_smart_upsert")
            external_savepoint_started = False
        else:
            conn.commit()
        logger.info("Inserção completada com sucesso")
        return True
    except Exception:
        if external_savepoint_started:
            try:
                conn.execute("ROLLBACK TO SAVEPOINT ssa_smart_upsert")
                conn.execute("RELEASE SAVEPOINT ssa_smart_upsert")
            except Exception as rollback_exc:
                logger.warning(
                    "Falha no rollback do savepoint de upsert: %s", rollback_exc
                )
        elif (
            close_after
            and conn is not None
            and hasattr(conn, "in_transaction")
            and bool(conn.in_transaction)
        ):
            try:
                cast(_sqlite3_typehint.Connection, conn).rollback()
            except Exception as rollback_exc:
                logger.warning("Falha no rollback de upsert: %s", rollback_exc)
        raise
    finally:
        if close_after and conn_cm is not None:
            exc_type, exc_value, exc_tb = sys.exc_info()
            try:
                conn_cm.__exit__(exc_type, exc_value, exc_tb)
            except Exception as close_exc:  # pragma: no cover
                logger.warning("Falha ao fechar conexao de upsert: %s", close_exc)
