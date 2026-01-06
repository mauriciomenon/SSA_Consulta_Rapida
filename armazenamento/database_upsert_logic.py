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
import pandas as pd  # type: ignore[import-not-found]
import logging
import re

from .numero_ssa_utils import _normalize_numero_ssa_value
from shared.date_utils import parse_any_date

# Lazy imports from database.py to avoid circular dependency (see line 303)

logger = logging.getLogger(__name__)

# Constantes removidas (vindas do util central). Mantidas só se necessário futuro.


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


def _perform_upsert(has_ssa: pd.DataFrame, table_name: str, conn, *, chunk_size: int = 100) -> int:  # type: ignore[no-untyped-def]
    complementary_mode = os.environ.get("SSA_ENABLE_COMPLEMENTARY") == "1"
    status_order_env = os.environ.get("SSA_STATUS_ORDER")
    status_order_list = (
        [s.strip() for s in status_order_env.split(',') if s.strip()]
        if status_order_env
        else ["ABERTO", "EM_ANALISE", "EM_EXECUCAO", "SCA", "STE"]
    )
    status_rank = {s: i for i, s in enumerate(status_order_list)}
    terminal_statuses_env = os.environ.get("SSA_TERMINAL_STATUSES")  # leitura única (telemetria futura)
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

    def _is_empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, float) and pd.isna(val):
            return True
        if isinstance(val, str) and (val.strip() == '' or val.strip().lower() in {"n/a", "na", "null", "-"}):
            return True
        return False

    def _parse_dt(v):
        try:
            if _is_empty(v):
                return None
            return pd.to_datetime(v, errors='coerce')
        except Exception:
            return None

    def _merge_complement(existing_row: pd.Series, new_row: pd.Series) -> pd.Series:
        result = existing_row.copy()
        for col in new_row.index:
            new_val = new_row[col]
            if col == 'numero_ssa':
                continue
            if col == 'situacao':
                old_val = result.get(col)
                if _is_empty(old_val) and not _is_empty(new_val):
                    result[col] = new_val
                else:
                    old_rank = status_rank.get(str(old_val), -1)
                    new_rank = status_rank.get(str(new_val), -1)
                    if new_rank > old_rank:
                        result[col] = new_val
                continue
            if col in date_columns:
                old_dt = _parse_dt(result.get(col))
                new_dt = _parse_dt(new_val)
                if old_dt is None and new_dt is not None:
                    result[col] = new_val
                elif old_dt is not None and new_dt is not None and new_dt > old_dt:
                    result[col] = new_val
                continue
            if col in description_columns:
                old_val = result.get(col)
                if _is_empty(old_val) and not _is_empty(new_val):
                    result[col] = new_val
                else:
                    if isinstance(new_val, str) and isinstance(old_val, str) and len(new_val) > len(old_val) + 10:
                        result[col] = new_val
                continue
            old_val = result.get(col)
            if _is_empty(old_val) and not _is_empty(new_val):
                result[col] = new_val
        return result

    total_inserted = 0
    for start in range(0, len(has_ssa), chunk_size):
        chunk = has_ssa.iloc[start:start + chunk_size]
        for _, row in chunk.iterrows():
            numero_ssa = row['numero_ssa']
            existing = pd.read_sql_query(
                f"SELECT * FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                conn,
                params=[numero_ssa],
            )
            if not complementary_mode:
                if existing.empty:
                    target_df = row.to_frame().T
                else:
                    old = existing.iloc[0]
                    merged = {}
                    for col in existing.columns:
                        new_val = row[col] if col in row.index else None
                        is_empty_new = (
                            pd.isna(new_val) or new_val in (None, '') or (isinstance(new_val, str) and new_val.strip() == '')
                        )
                        merged[col] = old[col] if is_empty_new else new_val
                    for col in row.index:
                        if col not in merged:
                            merged[col] = row[col]
                    target_df = pd.DataFrame([merged])
                if existing.empty or _should_update_existing(existing.iloc[0], row):
                    if not existing.empty:
                        conn.execute(
                            f"DELETE FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                            [numero_ssa],
                        )
                    target_df.to_sql(table_name, conn, if_exists='append', index=False)
                    total_inserted += 1
            else:
                if existing.empty:
                    target_df = row.to_frame().T
                    perform_update = True
                else:
                    old_row = existing.iloc[0]
                    merged_series = _merge_complement(old_row, row)
                    perform_update = not merged_series.equals(old_row)
                    target_df = merged_series.to_frame().T
                if perform_update:
                    if not existing.empty:
                        conn.execute(
                            f"DELETE FROM {table_name} WHERE numero_ssa = ?",  # noqa: S608
                            [numero_ssa],
                        )
                    target_df.to_sql(table_name, conn, if_exists='append', index=False)
                    total_inserted += 1
    return total_inserted


def prepare_dataframe_for_upsert(frame: pd.DataFrame) -> pd.DataFrame:
    work_local = pd.DataFrame(frame.values, columns=frame.columns).reset_index(drop=True)
    if 'numero_ssa' in work_local.columns:
        work_local['numero_ssa'] = work_local['numero_ssa'].apply(_normalize_numero_ssa_value)
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
    if 'numero_ssa' not in work.columns:
        has_ssa = pd.DataFrame()
        no_ssa = work.copy()
    else:
        has_ssa = work[work['numero_ssa'].notna()].copy()
        no_ssa = work[work['numero_ssa'].isna()].copy()
    from . import database as _db_mod  # lazy import evita circularidade
    conn_cm = None
    if hasattr(db_path, 'cursor'):  # conexão externa
        conn: Any = db_path  # type: ignore[assignment]
        close_after = False
    else:
        conn_cm = _db_mod.get_db_connection(db_path)  # type: ignore[arg-type]
        conn = conn_cm.__enter__()  # type: ignore[assignment]
        close_after = True
    try:
        cursor = conn.cursor()  # type: ignore[attr-defined]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cursor.fetchall()}
        if table_name not in existing_tables:
            for alias in ("ssa_table", "ssas", "ssa_chamados"):
                if alias in existing_tables:
                    table_name = alias  # type: ignore[assignment]
                    break
        table_exists = table_name in existing_tables
        if table_exists:
            from .identifier_utils import is_valid_identifier  # local import to avoid cycles
            if not is_valid_identifier(table_name):
                raise ValueError(f"Invalid SQL identifier for table: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name})")  # noqa: S608
            existing_columns = {row[1] for row in cursor.fetchall()}
            missing_columns = [col for col in work.columns if col not in existing_columns]
            for col in missing_columns:
                sql_type = _infer_sql_type(work[col] if col in work.columns else None)
                logger.info("Adicionando coluna ausente '%s' ao schema (tipo %s)", col, sql_type)
                if not is_valid_identifier(col):
                    raise ValueError(f"Invalid SQL identifier for column: {col}")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {sql_type}")  # noqa: S608
        if not no_ssa.empty:
            mode = 'append' if table_exists else 'replace'
            # Cálculo dinâmico do chunk size para evitar "too many SQL variables"
            chunk_size = min(500, max(1, 999 // len(no_ssa.columns))) if len(no_ssa.columns) > 0 else 500
            logger.debug(f"Chunk size calculado para inserção sem SSA: {chunk_size} linhas para {len(no_ssa.columns)} colunas")
            no_ssa.to_sql(table_name, conn, if_exists=mode, index=False, chunksize=chunk_size)
            logger.info("Inseridos %s registros sem numero_ssa", len(no_ssa))
            table_exists = True
        if not has_ssa.empty:
            if not table_exists:
                has_ssa.iloc[0:1].to_sql(table_name, conn, if_exists='replace', index=False)
                table_exists = True
                logger.info("Tabela criada com primeiro registro (numero_ssa)")
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
