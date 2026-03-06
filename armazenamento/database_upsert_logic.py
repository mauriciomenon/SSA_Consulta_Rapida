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
from __future__ import annotations

from typing import Any
import os
import pandas as pd
import logging
import re

from .numero_ssa_utils import _normalize_numero_ssa_value
from shared.date_utils import parse_any_date

# Lazy imports from database.py to avoid circular dependency (see line 303)

logger = logging.getLogger(__name__)
_INVALID_IDENTIFIER_CHARS_RE = re.compile(r"[^A-Za-z0-9_]+")
_VALID_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Constantes removidas (vindas do util central). Mantidas só se necessário futuro.


def _normalize_ssa_storage_value(value) -> str | None:
    normalized_int = _normalize_numero_ssa_value(value)
    if normalized_int is None:
        return None
    try:
        return str(int(normalized_int))
    except Exception:
        return None


def _validate_canonical_storage_ids(work_local: pd.DataFrame) -> None:
    for col in ("numero_ssa", "derivada_de"):
        if col not in work_local.columns:
            continue
        series = work_local[col].dropna().astype(str).str.strip()
        if series.str.contains(".", regex=False).any():
            raise ValueError(f"Non-canonical value detected in {col}; decimal artifact is not allowed")


def _infer_sql_type(series: pd.Series | None) -> str:
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
        if pd.api.types.is_float_dtype(non_null):
            return "REAL"
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
        if isinstance(col, str) and is_valid_identifier(col) and not _is_placeholder_column_name(col)
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
        logger.warning("Colunas dinamicas placeholder foram descartadas: %s", drop_columns)
        work = work.drop(columns=drop_columns, errors='ignore')

    if rename_map:
        logger.warning("Colunas dinamicas foram sanitizadas para SQL seguro: %s", rename_map)
        work = work.rename(columns=rename_map)

    # Enforce whitelist after dynamic rename/drop to avoid schema drift by env policy.
    final_work = apply_column_whitelist(work)

    missing_columns = [col for col in final_work.columns if col not in existing_columns]
    for col in missing_columns:
        sql_type = _infer_sql_type(final_work[col] if col in final_work.columns else None)
        logger.info("Adicionando coluna ausente '%s' ao schema (tipo %s)", col, sql_type)
        if not is_valid_identifier(col):
            raise ValueError(f"Invalid SQL identifier for column: {col}")
        if isinstance(db_path, str):
            db_module.ensure_column_exists(db_path, table_name, col, sql_type)
        else:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {sql_type}")  # noqa: S608
    return final_work


def _should_update_existing(existing_row: pd.Series, new_row: pd.Series) -> bool:
    existing_date = existing_row.get('data_cadastro')
    new_date = new_row.get('data_cadastro')
    try:
        def _parse(dt):  # evita E731 lambda
            if dt in (None, '') or (isinstance(dt, float) and pd.isna(dt)):
                return None
            parsed = parse_any_date(dt)
            if parsed is None:
                return None
            return pd.to_datetime(parsed, errors='coerce', format="%Y-%m-%d %H:%M:%S")

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
                n_val = getattr(n_dt, 'value', None)
                e_val = getattr(e_dt, 'value', None)
                if n_val is None or e_val is None:
                    return True
                return bool(n_val >= e_val)
            except Exception:  # pragma: no cover
                return True
        return True
    except Exception:  # pragma: no cover
        return True


def _resolve_upsert_config() -> tuple[dict[str, int], list[str], list[str]]:
    status_order_env = os.environ.get("SSA_STATUS_ORDER")
    status_order_list = (
        [s.strip() for s in status_order_env.split(',') if s.strip()]
        if status_order_env
        else ["ABERTO", "EM_ANALISE", "EM_EXECUCAO", "SCA", "STE"]
    )
    status_rank = {s: i for i, s in enumerate(status_order_list)}
    desc_cols_env = os.environ.get("SSA_DESC_COLUMNS")
    description_columns = [c.strip() for c in desc_cols_env.split(',') if c.strip()] if desc_cols_env else [
        "descricao_ssa", "descricao", "detalhes", "comentarios"
    ]
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


def _is_empty_upsert_value(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and (val.strip() == '' or val.strip().lower() in {"n/a", "na", "null", "-"}):
        return True
    return False


def _parse_upsert_dt(value: Any):
    try:
        if _is_empty_upsert_value(value):
            return None
        return pd.to_datetime(value, errors='coerce')
    except Exception:
        return None


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
        if col == 'numero_ssa':
            continue
        if col == 'situacao':
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
                if isinstance(new_val, str) and isinstance(old_val, str) and len(new_val) > len(old_val) + 10:
                    result[col] = new_val
            continue
        old_val = result.get(col)
        if _is_empty_upsert_value(old_val) and not _is_empty_upsert_value(new_val):
            result[col] = new_val
    if not isinstance(result, pd.Series):
        raise TypeError("Expected pd.Series from _merge_complement_row")
    return result


def _merge_preserve_existing_row(existing_row: pd.Series, new_row: pd.Series) -> pd.Series:
    incoming = new_row.reindex(existing_row.index, fill_value=None)
    empty_mask = incoming.apply(
        lambda value: pd.isna(value) or value in (None, '') or (isinstance(value, str) and value.strip() == '')
    )
    merged = existing_row.where(empty_mask, incoming)
    for col in new_row.index:
        if col not in merged.index:
            merged[col] = new_row[col]
    if not isinstance(merged, pd.Series):
        raise TypeError("Expected pd.Series from _merge_preserve_existing_row")
    return merged


def _persist_upsert_chunk(
    conn: Any,
    table_name: str,
    rows_to_persist: dict[Any, pd.Series],
    delete_keys: set[Any],
) -> None:
    in_transaction = getattr(conn, "in_transaction", None)
    if in_transaction is not None and not bool(in_transaction):
        raise RuntimeError("Upsert chunk requires active transaction on connection.")
    if delete_keys:
        placeholders = ", ".join(["?"] * len(delete_keys))
        conn.execute(
            f"DELETE FROM {table_name} WHERE numero_ssa IN ({placeholders})",  # noqa: S608
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
        persist_df.to_sql(table_name, conn, if_exists='append', index=False)


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
        merged_row = _merge_preserve_existing_row(existing_row, row)
        return merged_row, _should_update_existing(existing_row, row)

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


def _perform_upsert(has_ssa: pd.DataFrame, table_name: str, conn, *, chunk_size: int = 100) -> int:
    complementary_mode = os.environ.get("SSA_ENABLE_COMPLEMENTARY") == "1"
    status_rank, description_columns, date_columns = _resolve_upsert_config()
    os.environ.get("SSA_TERMINAL_STATUSES")  # leitura única (telemetria futura)

    total_upserted = 0
    for start in range(0, len(has_ssa), chunk_size):
        chunk = has_ssa.iloc[start:start + chunk_size]

        chunk_num_ssa: list[Any] = (
            chunk['numero_ssa']
            .dropna()
            .drop_duplicates()
            .tolist()
        )

        existing_by_ssa: dict[str, pd.Series] = {}
        if chunk_num_ssa:
            placeholders = ", ".join(["?"] * len(chunk_num_ssa))
            existing_chunk = pd.read_sql_query(
                f"SELECT * FROM {table_name} WHERE numero_ssa IN ({placeholders})",  # noqa: S608
                conn,
                params=chunk_num_ssa,
            )
            if not existing_chunk.empty and 'numero_ssa' in existing_chunk.columns:
                for existing_row_tuple in existing_chunk.itertuples(index=False, name=None):
                    existing_row = pd.Series(existing_row_tuple, index=existing_chunk.columns)
                    numero_val = existing_row.get('numero_ssa')
                    cache_key = _upsert_cache_key(numero_val)
                    if cache_key is None:
                        continue
                    existing_by_ssa[cache_key] = existing_row

        rows_to_persist: dict[str, pd.Series] = {}
        delete_keys: set[Any] = set()
        for row_tuple in chunk.itertuples(index=False, name=None):
            row = pd.Series(row_tuple, index=chunk.columns)
            numero_ssa = row['numero_ssa']
            cache_key = _upsert_cache_key(numero_ssa)
            if cache_key is None:
                continue
            existing_row = existing_by_ssa.get(cache_key)
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
                    delete_keys.add(existing_row.get('numero_ssa'))
                merged_cache_row = target_row.copy()
                rows_to_persist[cache_key] = merged_cache_row
                existing_by_ssa[cache_key] = merged_cache_row
                total_upserted += 1
        _persist_upsert_chunk(conn, table_name, rows_to_persist, delete_keys)
    return total_upserted


def prepare_dataframe_for_upsert(frame: pd.DataFrame) -> pd.DataFrame:
    work_local = frame.copy().reset_index(drop=True)
    if 'numero_ssa' in work_local.columns:
        work_local['numero_ssa'] = work_local['numero_ssa'].map(_normalize_ssa_storage_value)
    if 'derivada_de' in work_local.columns:
        work_local['derivada_de'] = work_local['derivada_de'].map(_normalize_ssa_storage_value)
    _validate_canonical_storage_ids(work_local)
    date_columns = [
        'data_cadastro',
        'prazo_limite',
        'data_limite',
        'desde',
        'desde_1',
        'desde_2',
        'ate',
        'ate_1',
        'ate_2',
        'data_inicio_programada',
        'data_programacao',
        'data_inicio_reprogramada',
        'data_reprogramacao',
        'instalacao_estimada',
        'executado',
        'concluido',
    ]
    def _to_string_date(val) -> str | None:
        try:
            if pd.isna(val) or val in (None, ''):
                return None
            val_str = str(val)
            iso_like = bool(re.match(r"^\d{4}-\d{2}-\d{2}", val_str))
            if iso_like:
                dt = pd.to_datetime(val_str, errors='coerce', dayfirst=False)
            else:
                dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
            if pd.isna(dt):
                return None
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:  # pragma: no cover
            return None
    for c in date_columns:
        if c in work_local.columns:
            try:
                work_local[c] = [_to_string_date(v) for v in work_local[c]]
            except Exception:  # pragma: no cover
                pass
    return work_local


def apply_column_whitelist(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtro de colunas baseado na variável de ambiente SSA_ALLOWED_COLUMNS.

    Mantido aqui para reutilização entre caminhos de inserção simples e smart upsert.
    Não altera DataFrame in-place; retorna cópia possivelmente reduzida.
    """
    wl = os.environ.get("SSA_ALLOWED_COLUMNS")
    if not wl:
        return df
    allowed = {c.strip() for c in wl.split(',') if c.strip()}
    if not allowed:
        return df
    drop_cols = [c for c in df.columns if c not in allowed]
    if drop_cols:
        logger.info("Colunas removidas por whitelist: %s", drop_cols)
        return df[[c for c in df.columns if c in allowed]]
    return df


def insert_dataframe_with_smart_upsert_impl(
    df: pd.DataFrame, db_path: str | Any, table_name: str
) -> bool:
    work = prepare_dataframe_for_upsert(df)
    work = apply_column_whitelist(work)
    from . import database as _db_mod  # lazy import evita circularidade
    conn_cm = None
    if hasattr(db_path, 'cursor'):  # conexão externa
        conn: Any = db_path
        close_after = False
    else:
        conn_cm = _db_mod.get_db_connection(db_path)
        conn = conn_cm.__enter__()
        close_after = True
    try:
        cursor = conn.cursor()  # type: ignore[attr-defined]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cursor.fetchall()}
        if table_name not in existing_tables:
            for alias in ("ssa_table", "ssas", "ssa_chamados"):
                if alias in existing_tables:
                    table_name = alias
                    break
        table_exists = table_name in existing_tables
        if not table_exists:
            logger.warning(
                "Tabela alvo '%s' ausente. Aplicando bootstrap de schema canonico antes do upsert.",
                table_name,
            )
            if isinstance(db_path, str):
                _db_mod.initialize_database(db_path, "config/schema.sql")
            else:
                cursor.execute("PRAGMA database_list")
                db_list = cursor.fetchall()
                main_db_path = None
                for row in db_list:
                    if len(row) >= 3 and row[1] == "main" and row[2]:
                        main_db_path = str(row[2])
                        break
                if not main_db_path:
                    logger.error(
                        "Nao foi possivel identificar caminho do DB principal para bootstrap de schema."
                    )
                    return False
                _db_mod.initialize_database(main_db_path, "config/schema.sql")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {r[0] for r in cursor.fetchall()}
            if table_name not in existing_tables:
                for alias in ("ssa_table", "ssas", "ssa_chamados"):
                    if alias in existing_tables:
                        table_name = alias
                        break
            table_exists = table_name in existing_tables
            if not table_exists:
                logger.error(
                    "Schema canonico aplicado, mas tabela alvo '%s' nao foi encontrada.",
                    table_name,
                )
                return False
        if table_exists:
            from .identifier_utils import is_valid_identifier  # local import to avoid cycles
            if not is_valid_identifier(table_name):
                raise ValueError(f"Invalid SQL identifier for table: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name})")  # noqa: S608
            existing_columns = {row[1] for row in cursor.fetchall()}
            work = _sync_dynamic_columns_and_schema(
                work=work,
                table_name=table_name,
                existing_columns=existing_columns,
                db_path=db_path,
                conn=conn,
                db_module=_db_mod,
            )
        if 'numero_ssa' not in work.columns:
            has_ssa = pd.DataFrame()
            no_ssa = work.copy()
        else:
            has_ssa = work[work['numero_ssa'].notna()].copy()
            no_ssa = work[work['numero_ssa'].isna()].copy()
        if hasattr(conn, "in_transaction") and not bool(conn.in_transaction):
            cursor.execute("BEGIN")
        if not no_ssa.empty:
            # Cálculo dinâmico do chunk size para evitar "too many SQL variables"
            chunk_size = min(500, max(1, 999 // len(no_ssa.columns))) if len(no_ssa.columns) > 0 else 500
            logger.debug(f"Chunk size calculado para inserção sem SSA: {chunk_size} linhas para {len(no_ssa.columns)} colunas")
            no_ssa.to_sql(table_name, conn, if_exists='append', index=False, chunksize=chunk_size)
            logger.info("Inseridos %s registros sem numero_ssa", len(no_ssa))
        if not has_ssa.empty:
            inserted = _perform_upsert(has_ssa, table_name, conn)
            logger.info("Processados %s registros com numero_ssa via upsert", inserted)
        conn.commit()  # type: ignore[attr-defined]
        logger.info("Inserção completada com sucesso")
        return True
    finally:
        if close_after and conn_cm is not None:
            try:
                conn_cm.__exit__(None, None, None)
            except Exception:  # pragma: no cover
                pass
