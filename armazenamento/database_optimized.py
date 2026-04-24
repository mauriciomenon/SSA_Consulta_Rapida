"""armazenamento/database_optimized.py

Versão otimizada das funções de banco de dados para importação rápida.
Focada em throughput (lotes, minimização de round-trips, pragmas de performance).

Mantém compatibilidade ao expor a função ``insert_dataframe_optimized`` e
facilitadores para ativar/desativar dinamicamente no módulo ``database``.

Refatoração de estilo para conformidade com flake8 (remoção de imports não usados,
quebras de linha longas, remoção de trailing whitespace).

CIRCULAR DEPENDENCY MITIGATION:
This module imports get_db_connection from database.py at top level (safe because
get_db_connection is defined early in database.py). The database.py module imports
insert_dataframe_optimized lazily (inside dispatcher function). This works but is
fragile - if get_db_connection moves lower in database.py, circular import will break.
"""
# Last modified: 2025-10-29T11:10:00 (circular import documentation)

from __future__ import annotations

import sqlite3
import time
from typing import Iterator

import pandas as pd

from shared.date_utils import (
    format_datetime_series_for_storage,
    parse_datetime_series_mixed,
)
from shared.db_names import CANONICAL_SSA_TABLE, LEGACY_SSA_TABLE_ALIASES
from utils.robust_logging import get_robust_logger

from .database import (
    get_db_connection,
)  # Top-level import (safe - defined early in database.py)
from .identifier_utils import is_valid_identifier
from .numero_ssa_utils import normalize_numero_ssa_storage
from .schema_manager import ensure_columns_exist

logger = get_robust_logger().get_logger(__name__, "core")


# ===== SQLITE LIMITS AND CHUNK HELPERS =====
SQLITE_MAX_VARIABLES = 999
SQLITE_SAFETY_EXTRA_COLUMNS = 1
SQLITE_DEFAULT_CHUNK_CAP = 500


def _quote_identifier(identifier: str) -> str:
    """Quote a validated SQL identifier."""
    if not is_valid_identifier(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{identifier}"'


def _validate_canonical_storage_ids(work: pd.DataFrame) -> None:
    """Fail fast if normalized storage ids still contain decimal artifacts."""
    for col in ("numero_ssa", "derivada_de"):
        if col not in work.columns:
            continue
        series = work[col].dropna().astype(str).str.strip()
        if series.str.contains(".", regex=False).any():
            raise ValueError(
                f"Non-canonical value detected in {col}; decimal artifact is not allowed"
            )


def _deduplicate_ssa_rows(
    df: pd.DataFrame, *, already_normalized: bool = False
) -> pd.DataFrame:
    """Keep only one row per numero_ssa, prioritizing the newest data_cadastro when available."""
    if "numero_ssa" not in df.columns or df.empty:
        return df
    if already_normalized:
        normalized_ssa = (
            df["numero_ssa"]
            .astype("object")
            .map(lambda v: None if v is None else (str(v).strip() or None))
        )
    else:
        normalized_ssa = df["numero_ssa"].map(normalize_numero_ssa_storage)
    valid_mask = normalized_ssa.notna()
    if not bool(valid_mask.any()):
        return df.iloc[0:0].copy()
    if bool(normalized_ssa[valid_mask].is_unique):
        dedup_df = df.loc[valid_mask].copy()
        dedup_df["numero_ssa"] = normalized_ssa.loc[valid_mask]
        return dedup_df

    dedup_df = df.loc[valid_mask].copy()
    dedup_df["numero_ssa"] = normalized_ssa.loc[valid_mask]
    if dedup_df.empty:
        return dedup_df
    if "data_cadastro" in dedup_df.columns:
        try:
            parsed = parse_datetime_series_mixed(dedup_df["data_cadastro"])
            dedup_df = dedup_df.assign(__sort_date=parsed).sort_values(
                "__sort_date",
                ascending=True,
                na_position="first",
            )
            dedup_df = dedup_df.drop(columns=["__sort_date"], errors="ignore")
        except Exception as exc:
            logger.debug("Falha ao ordenar deduplicacao por data_cadastro: %s", exc)
    dedup_df = dedup_df.drop_duplicates(subset=["numero_ssa"], keep="last")
    return dedup_df


def sqlite_safe_chunksize(num_columns: int, cap: int = SQLITE_DEFAULT_CHUNK_CAP) -> int:
    """Compute a safe chunksize for SQLite to avoid the 999 variables limit.

    Uses a small safety margin by adding SQLITE_SAFETY_EXTRA_COLUMNS to the
    column count and caps the chunk size to avoid overly large batches.
    """
    per_row_vars = max(1, num_columns + SQLITE_SAFETY_EXTRA_COLUMNS)
    return min(cap, max(1, SQLITE_MAX_VARIABLES // per_row_vars))


def _resolve_physical_table(conn, table_name: str) -> str:
    """Map legacy aliases to the canonical physical table when present."""
    try:
        normalized_name = str(table_name or "").strip().casefold()
        if normalized_name == CANONICAL_SSA_TABLE.casefold() or normalized_name in {
            alias.casefold() for alias in LEGACY_SSA_TABLE_ALIASES
        }:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (CANONICAL_SSA_TABLE,),
            )
            if cursor.fetchone():
                return CANONICAL_SSA_TABLE
        cursor = conn.execute(
            "SELECT name, type FROM sqlite_master WHERE name=?",
            (table_name,),
        )
        row = cursor.fetchone()
        if (
            row
            and row[1] == "view"
            and normalized_name
            in {alias.casefold() for alias in LEGACY_SSA_TABLE_ALIASES}
        ):
            cursor2 = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (CANONICAL_SSA_TABLE,),
            )
            if cursor2.fetchone():
                return CANONICAL_SSA_TABLE
    except Exception as exc:  # pragma: no cover
        logger.debug("Falha ao resolver tabela fisica para %s: %s", table_name, exc)
    return table_name


def _has_referencing_foreign_keys(conn, target_table: str) -> bool:
    """Check if any table defines foreign keys referencing target_table."""
    if not is_valid_identifier(target_table):
        logger.warning(
            "Identificador de tabela invalido para scan de FKs: %r", target_table
        )
        return False
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            if table == target_table:
                continue
            if not is_valid_identifier(table):
                continue
            try:
                quoted_table = _quote_identifier(table)
                fk_rows = conn.execute(
                    f"PRAGMA foreign_key_list({quoted_table})"
                ).fetchall()
            except Exception as exc:
                logger.warning(
                    "Falha ao inspecionar foreign keys da tabela %s: %s",
                    table,
                    exc,
                )
                continue
            for fk in fk_rows:
                if len(fk) > 2 and fk[2] == target_table:
                    return True
    except Exception as exc:  # pragma: no cover
        logger.debug(
            "Falha ao inspecionar foreign keys para %s: %s",
            target_table,
            exc,
        )
    return False


def _normalize_unique_ssa_values(ssa_values: pd.Series | list[object]) -> list[str]:
    """Normalize and deduplicate SSA identifiers preserving input order."""
    if isinstance(ssa_values, pd.Series):
        raw_values = ssa_values.tolist()
    else:
        raw_values = ssa_values
    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        numero = normalize_numero_ssa_storage(value)
        if not numero or numero in seen:
            continue
        seen.add(numero)
        normalized.append(numero)
    return normalized


def _iter_lookup_chunks_by_ssa(
    conn: sqlite3.Connection,
    *,
    target_table_sql: str,
    normalized_ssas: list[str],
    select_expr: str,
    initial_chunk_size: int = 500,
) -> Iterator[pd.DataFrame]:
    """Yield lookup result chunks with SQLite variables-limit fallback."""
    if not normalized_ssas:
        return
    max_lookup_params = max(1, SQLITE_MAX_VARIABLES - 100)
    lookup_chunk = min(initial_chunk_size, max_lookup_params)
    i = 0
    while i < len(normalized_ssas):
        chunk_ssas = normalized_ssas[i : i + lookup_chunk]
        if len(chunk_ssas) > max_lookup_params:
            chunk_ssas = chunk_ssas[:max_lookup_params]
        placeholders = ",".join(["?"] * len(chunk_ssas))
        query = (
            f"SELECT {select_expr} FROM {target_table_sql} "  # nosec B608  # skipcq: BAN-B608
            f"WHERE numero_ssa IN ({placeholders})"
        )
        try:
            chunk_df = pd.read_sql_query(query, conn, params=list(chunk_ssas))
        except (
            sqlite3.OperationalError,
            pd.errors.DatabaseError,
        ) as exc:
            if "too many sql variables" in str(exc).lower() and lookup_chunk > 1:
                lookup_chunk = max(1, lookup_chunk // 2)
                logger.warning(
                    "Ajustando chunk de lookup SSA para %s apos limite SQLite: %s",
                    lookup_chunk,
                    exc,
                )
                continue
            raise RuntimeError(
                f"Falha no lookup de SSAs (chunk={len(chunk_ssas)}): {exc}"
            ) from exc
        yield chunk_df
        i += len(chunk_ssas)


def _load_existing_ssa_payloads(
    conn: sqlite3.Connection,
    *,
    target_table_sql: str,
    has_ssa: pd.DataFrame,
) -> dict[str, dict[str, object | None]]:
    """Load existing rows metadata (date/situacao/source file) for incoming SSA ids."""
    existing_dict: dict[str, dict[str, object | None]] = {}
    unique_ssas = _normalize_unique_ssa_values(has_ssa["numero_ssa"])
    if not unique_ssas:
        return existing_dict

    has_arquivo_origem = False
    has_data_arquivo_origem = False
    has_data_planilha = False
    try:
        table_info = pd.read_sql_query(f"PRAGMA table_info({target_table_sql})", conn)
        names = table_info["name"].tolist() if "name" in table_info.columns else []
        has_arquivo_origem = "arquivo_origem" in {str(col).strip() for col in names}
        has_data_arquivo_origem = "data_arquivo_origem" in {
            str(col).strip() for col in names
        }
        has_data_planilha = "data_planilha" in {str(col).strip() for col in names}
    except Exception:
        has_arquivo_origem = False
        has_data_arquivo_origem = False
        has_data_planilha = False
    select_columns = ["numero_ssa", "data_cadastro", "situacao"]
    if has_arquivo_origem:
        select_columns.append("arquivo_origem")
    if has_data_arquivo_origem:
        select_columns.append("data_arquivo_origem")
    if has_data_planilha:
        select_columns.append("data_planilha")
    select_expr = ", ".join(select_columns)

    for chunk_df in _iter_lookup_chunks_by_ssa(
        conn,
        target_table_sql=target_table_sql,
        normalized_ssas=unique_ssas,
        select_expr=select_expr,
        initial_chunk_size=500,
    ):
        if not chunk_df.empty:
            chunk_df["numero_ssa"] = chunk_df["numero_ssa"].map(
                normalize_numero_ssa_storage
            )
            chunk_df = chunk_df[chunk_df["numero_ssa"].notna()]
            chunk_df = chunk_df.astype("object").where(pd.notna(chunk_df), None)
            chunk_columns = list(chunk_df.columns)
            for row_values in chunk_df.itertuples(index=False, name=None):
                current = dict(zip(chunk_columns, row_values))
                numero = str(current.get("numero_ssa") or "").strip()
                if not numero:
                    continue
                existing_dict[numero] = {
                    "data_cadastro": current.get("data_cadastro"),
                    "situacao": current.get("situacao"),
                    "arquivo_origem": current.get("arquivo_origem"),
                    "data_arquivo_origem": current.get("data_arquivo_origem"),
                    "data_planilha": current.get("data_planilha"),
                }

    return existing_dict


def _classify_upsert_rows(
    has_ssa: pd.DataFrame,
    existing_dict: dict[str, dict[str, object | None]],
) -> tuple[list[pd.Series], list[pd.Series]]:
    """Split incoming rows into insert and update groups using canonical rule."""
    from .database_upsert_logic import _should_update_existing

    to_insert: list[pd.Series] = []
    to_update: list[pd.Series] = []
    for _idx, row in has_ssa.iterrows():
        numero_ssa = row["numero_ssa"]
        if numero_ssa not in existing_dict:
            to_insert.append(row)
            continue
        existing_payload = existing_dict[numero_ssa]
        existing_row = {
            "data_cadastro": existing_payload.get("data_cadastro"),
            "situacao": existing_payload.get("situacao"),
            "arquivo_origem": existing_payload.get("arquivo_origem"),
            "data_arquivo_origem": existing_payload.get("data_arquivo_origem"),
            "data_planilha": existing_payload.get("data_planilha"),
        }
        incoming_row = {
            "data_cadastro": row.get("data_cadastro"),
            "situacao": row.get("situacao"),
            "arquivo_origem": row.get("arquivo_origem"),
            "data_arquivo_origem": row.get("data_arquivo_origem"),
            "data_planilha": row.get("data_planilha"),
        }
        if _should_update_existing(existing_row, incoming_row):
            to_update.append(row)
    return to_insert, to_update


def insert_dataframe_optimized(
    df: pd.DataFrame,
    db_path: str,
    table_name: str = "ssas",
) -> bool:
    """
    Versão OTIMIZADA da inserção de DataFrame com as seguintes melhorias:

    1. Operações em batch em vez de linha por linha
    2. Uso de índices temporários para acelerar consultas
    3. Configurações SQLite otimizadas para performance
    4. Redução de conversões desnecessárias
    5. Upsert em massa usando estratégias eficientes

    Args:
        df: DataFrame para inserir
    db_path: Caminho do banco de dados
    table_name: Nome da tabela (padrão: 'ssas')

    Returns:
        bool: True se sucesso, False se erro
    """
    if df is None or df.empty:
        logger.info("DataFrame vazio, nada para inserir")
        return True

    start_time = time.time()
    logger.info(f"Iniciando inserção otimizada de {len(df)} registros...")

    conn: sqlite3.Connection | None = None

    try:
        from .database_upsert_logic import prepare_dataframe_for_storage

        work = prepare_dataframe_for_storage(df, normalize_derivada=True)

        # Normalize SSA identifiers in storage path to avoid persisting decimal artifacts.
        _validate_canonical_storage_ids(work)

        # Converter datas de forma mais eficiente (vetorizada)
        date_columns = [
            "data_cadastro",
            "prazo_limite",
            "data_limite",
            "desde",
            "desde_1",
        ]
        for col in date_columns:
            if col in work.columns:
                work[col] = format_datetime_series_for_storage(work[col])

        with get_db_connection(db_path) as conn:
            target_table = _resolve_physical_table(conn, table_name)
            if not is_valid_identifier(target_table):
                raise ValueError(f"Invalid SQL identifier for table: {target_table!r}")

            # ensure_columns_exist commits on schema changes, so run it before the
            # explicit batch transaction to keep the import body atomic.
            ensure_columns_exist(conn, target_table, work)

            # ===== CONFIGURAÇÕES DE PERFORMANCE SQLITE =====
            logger.info("FIX APLICANDO OTIMIZAÇÕES SQLITE")
            conn.execute("PRAGMA journal_mode=WAL")  # Permite leituras concorrentes
            conn.execute(
                "PRAGMA synchronous=NORMAL"
            )  # Balanço entre segurança e velocidade
            conn.execute("PRAGMA cache_size=10000")  # Cache maior = menos I/O
            conn.execute("PRAGMA temp_store=MEMORY")  # Operações temporárias em RAM
            conn.execute("PRAGMA mmap_size=268435456")  # Memory-mapped I/O (256MB)
            conn.execute("BEGIN IMMEDIATE")

            # LOG: Verificar configurações aplicadas
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode")
            journal_mode = cur.fetchone()[0]
            cur.execute("PRAGMA cache_size")
            cache_size = cur.fetchone()[0]
            logger.info(
                f"OK Configurações aplicadas: journal_mode={journal_mode}, cache_size={cache_size}"
            )

            target_table_sql = _quote_identifier(target_table)

            # Criar índice temporário se não existir
            try:
                idx_stmt = f"CREATE INDEX IF NOT EXISTS idx_temp_numero_ssa ON {target_table_sql}(numero_ssa)"
                conn.execute(idx_stmt)
            except Exception as e:  # pragma: no cover - não crítico
                logger.warning("Aviso ao criar índice temporário: %s", e)

            # Separar registros com e sem SSA
            if "numero_ssa" in work.columns:
                has_ssa = work[work["numero_ssa"].notna()].copy()
                no_ssa = work[work["numero_ssa"].isna()].copy()
            else:
                has_ssa = pd.DataFrame()
                no_ssa = work.copy()

            total_inserted = 0

            # ===== INSERIR REGISTROS SEM SSA (APPEND SIMPLES) =====
            if not no_ssa.empty:
                safe_chunksize = sqlite_safe_chunksize(len(no_ssa.columns))
                # method='multi' ignora chunksize; usar chunksize seguro
                no_ssa.to_sql(
                    target_table,
                    conn,
                    if_exists="append",
                    index=False,
                    chunksize=safe_chunksize,
                )
                total_inserted += len(no_ssa)
                logger.info(f"[OK] Inseridos {len(no_ssa)} registros sem numero_ssa")

            # ===== ESTRATÉGIA OTIMIZADA PARA REGISTROS COM SSA =====
            if not has_ssa.empty:
                has_ssa = _deduplicate_ssa_rows(has_ssa, already_normalized=True)
                # Verificar se tabela existe antes de fazer SELECT
                try:
                    table_exists = pd.read_sql_query(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        conn,
                        params=[target_table],
                    )
                except (sqlite3.Error, pd.errors.DatabaseError) as exc:
                    logger.error(
                        "Falha ao verificar existencia da tabela alvo '%s': %s",
                        target_table,
                        exc,
                    )
                    return False

                # OTIMIZACAO CHAVE: lookup apenas das SSAs que precisamos
                lookup_start = time.time()
                existing_dict: dict[str, dict[str, object | None]] = {}
                if not table_exists.empty:
                    existing_dict = _load_existing_ssa_payloads(
                        conn,
                        target_table_sql=target_table_sql,
                        has_ssa=has_ssa,
                    )
                lookup_time = time.time() - lookup_start

                logger.info(
                    "Lookup de SSAs existentes: %s encontrados em %.3fs",
                    len(existing_dict),
                    lookup_time,
                )

                # Classificar registros em lotes (insert vs update)
                to_insert, to_update = _classify_upsert_rows(has_ssa, existing_dict)

                # ===== INSERÇÃO EM LOTE DE NOVOS REGISTROS =====
                if to_insert:
                    insert_df = pd.DataFrame(to_insert)
                    # Calcula chunksize dinamico centralizado para evitar limite de variaveis
                    safe_chunksize = sqlite_safe_chunksize(len(insert_df.columns))
                    # method='multi' ignora chunksize; usar chunksize seguro
                    insert_df.to_sql(
                        target_table,
                        conn,
                        if_exists="append",
                        index=False,
                        chunksize=safe_chunksize,
                    )
                    total_inserted += len(insert_df)
                    logger.info(
                        f"[OK] Inseridos {len(insert_df)} novos registros com SSA (chunksize={safe_chunksize})"
                    )

                # ===== ATUALIZAÇÃO EM LOTE (DELETE + INSERT é mais rápido que UPDATE) =====
                if to_update:
                    update_df = pd.DataFrame(to_update)

                    # Processar em chunks seguros para SQLite (centralizado)
                    CHUNK_SIZE = sqlite_safe_chunksize(len(update_df.columns))
                    logger.debug(
                        f"Chunk size calculado: {CHUNK_SIZE} linhas para {len(update_df.columns)} colunas"
                    )
                    savepoint_started = False
                    savepoint_released = False
                    try:
                        conn.execute("SAVEPOINT ssa_batch_update")
                        savepoint_started = True
                    except Exception as exc:
                        logger.error(
                            "Falha ao iniciar SAVEPOINT ssa_batch_update: %s", exc
                        )
                        raise
                    try:
                        update_columns = [
                            col
                            for col in update_df.columns
                            if col not in ("numero_ssa", "id")
                        ]
                        if not update_columns:
                            logger.info(
                                "Nenhuma coluna atualizavel encontrada; pulando atualizacao"
                            )
                        else:
                            ssa_list = _normalize_unique_ssa_values(
                                update_df["numero_ssa"]
                            )
                            existing_rows_by_ssa: dict[
                                str, dict[str, object | None]
                            ] = {}
                            for existing_chunk in _iter_lookup_chunks_by_ssa(
                                conn,
                                target_table_sql=target_table_sql,
                                normalized_ssas=ssa_list,
                                select_expr="*",
                                initial_chunk_size=CHUNK_SIZE,
                            ):
                                if existing_chunk.empty:
                                    continue
                                existing_chunk = existing_chunk.astype("object").where(
                                    pd.notna(existing_chunk), None
                                )
                                existing_chunk["numero_ssa"] = existing_chunk[
                                    "numero_ssa"
                                ].map(normalize_numero_ssa_storage)
                                existing_chunk = existing_chunk[
                                    existing_chunk["numero_ssa"].notna()
                                ]
                                existing_columns = list(existing_chunk.columns)
                                for row_values in existing_chunk.itertuples(
                                    index=False, name=None
                                ):
                                    existing_row = dict(
                                        zip(existing_columns, row_values)
                                    )
                                    numero_ssa = str(existing_row["numero_ssa"])
                                    existing_rows_by_ssa[numero_ssa] = existing_row

                            normalized_update_df = update_df.astype("object").where(
                                pd.notna(update_df), None
                            )
                            missing_existing_ssas = [
                                numero
                                for numero in ssa_list
                                if numero not in existing_rows_by_ssa
                            ]
                            if missing_existing_ssas:
                                raise RuntimeError(
                                    "Lookup incompleto no caminho delete+insert para SSAs: "
                                    f"{missing_existing_ssas[:5]}"
                                )
                            merged_rows: list[dict[str, object | None]] = []
                            update_columns_all = list(normalized_update_df.columns)
                            for row_values in normalized_update_df.itertuples(
                                index=False, name=None
                            ):
                                update_row = dict(zip(update_columns_all, row_values))
                                numero_ssa = update_row.get("numero_ssa")
                                if numero_ssa is None:
                                    continue
                                merged_row = existing_rows_by_ssa[
                                    str(numero_ssa)
                                ].copy()
                                merged_row.update(update_row)
                                merged_rows.append(merged_row)

                            if not merged_rows:
                                logger.info(
                                    "Nenhuma linha elegivel para reinsert apos merge"
                                )
                            else:
                                merged_df = pd.DataFrame(merged_rows)
                                insert_columns = list(merged_df.columns)
                                for i in range(0, len(ssa_list), CHUNK_SIZE):
                                    chunk_ssas = ssa_list[i : i + CHUNK_SIZE]
                                    if not chunk_ssas:
                                        continue
                                    ssa_placeholders = ",".join(["?"] * len(chunk_ssas))
                                    delete_query = (
                                        f"DELETE FROM {target_table_sql} "  # nosec B608  # skipcq: BAN-B608
                                        f"WHERE numero_ssa IN ({ssa_placeholders})"
                                    )
                                    conn.execute(delete_query, chunk_ssas)

                                for col in insert_columns:
                                    if not is_valid_identifier(col):
                                        raise ValueError(
                                            f"Invalid SQL identifier for column: {col!r}"
                                        )
                                quoted_columns = ", ".join(
                                    [_quote_identifier(col) for col in insert_columns]
                                )
                                value_placeholders = ", ".join(
                                    ["?"] * len(insert_columns)
                                )
                                insert_sql = (
                                    f"INSERT INTO {target_table_sql} ({quoted_columns}) "  # nosec B608  # skipcq: BAN-B608
                                    f"VALUES ({value_placeholders})"
                                )
                                insert_chunk_size = sqlite_safe_chunksize(
                                    len(insert_columns)
                                )
                                for i in range(0, len(merged_df), insert_chunk_size):
                                    chunk = merged_df.iloc[i : i + insert_chunk_size]
                                    normalized_chunk = (
                                        chunk[insert_columns]
                                        .astype("object")
                                        .where(pd.notna(chunk[insert_columns]), None)
                                    )
                                    params = list(
                                        normalized_chunk.itertuples(
                                            index=False, name=None
                                        )
                                    )
                                    if params:
                                        conn.executemany(insert_sql, params)
                                total_inserted += len(update_df)
                                logger.info(
                                    "[OK] Atualizados %s registros existentes via delete+insert",
                                    len(update_df),
                                )
                        if savepoint_started and not savepoint_released:
                            conn.execute("RELEASE SAVEPOINT ssa_batch_update")
                            savepoint_released = True
                    except Exception:
                        if savepoint_started and not savepoint_released:
                            try:
                                conn.execute("ROLLBACK TO SAVEPOINT ssa_batch_update")
                                conn.execute("RELEASE SAVEPOINT ssa_batch_update")
                                savepoint_released = True
                            except Exception as exc:
                                logger.error(
                                    "Falha ao finalizar rollback/release do SAVEPOINT ssa_batch_update: %s",
                                    exc,
                                )
                        raise

            # Commit explícito
            conn.commit()

            elapsed_time = time.time() - start_time
            rate = total_inserted / elapsed_time if elapsed_time > 0 else 0

            logger.info("[OK] Insercao otimizada concluida:")
            logger.info("   [STATS] %s registros processados", total_inserted)
            logger.info("   [TIME] %.2f segundos", elapsed_time)
            logger.info("   [RATE] %.1f registros/segundo", rate)

            return True

    except Exception as e:  # pragma: no cover - caminho de erro
        conn_ref = conn
        if conn_ref is not None:
            try:
                conn_ref.execute("SELECT 1")
                in_transaction = getattr(conn_ref, "in_transaction", False)
                if bool(in_transaction):
                    conn_ref.rollback()
            except sqlite3.ProgrammingError:
                logger.warning(
                    "Rollback ignorado no caminho otimizado: conexao ja encerrada."
                )
            except Exception as rollback_exc:
                logger.error(
                    "Falha ao executar rollback no caminho otimizado: %s",
                    rollback_exc,
                )
        logger.error("[ERRO] Erro na insercao otimizada: %s", e)
        return False


def enable_optimized_import():
    """
    Ativa o modo de importacao otimizada.
    Deve ser chamado antes de run_importer_logic().
    """
    from .database import set_optimized_mode

    set_optimized_mode(True)


def disable_optimized_import():
    """
    Desativa o modo de importacao otimizada.
    """
    from .database import set_optimized_mode

    set_optimized_mode(False)
