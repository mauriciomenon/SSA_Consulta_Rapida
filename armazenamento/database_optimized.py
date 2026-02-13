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

import logging
import time
from contextlib import suppress
import pandas as pd  # type: ignore[import-not-found]

from .database import get_db_connection  # Top-level import (safe - defined early in database.py)
from .identifier_utils import is_valid_identifier
from .schema_manager import ensure_columns_exist

logger = logging.getLogger(__name__)


# ===== SQLITE LIMITS AND CHUNK HELPERS =====
SQLITE_MAX_VARIABLES = 999
SQLITE_SAFETY_EXTRA_COLUMNS = 1
SQLITE_DEFAULT_CHUNK_CAP = 500


def sqlite_safe_chunksize(num_columns: int, cap: int = SQLITE_DEFAULT_CHUNK_CAP) -> int:
    """Compute a safe chunksize for SQLite to avoid the 999 variables limit.

    Uses a small safety margin by adding SQLITE_SAFETY_EXTRA_COLUMNS to the
    column count and caps the chunk size to avoid overly large batches.
    """
    per_row_vars = max(1, num_columns + SQLITE_SAFETY_EXTRA_COLUMNS)
    return min(cap, max(1, SQLITE_MAX_VARIABLES // per_row_vars))


def _resolve_physical_table(conn, table_name: str) -> str:
    """Map legacy view aliases (ssas/ssa_chamados) to the physical table when present."""
    try:
        cursor = conn.execute(
            "SELECT name, type FROM sqlite_master WHERE name=?",
            (table_name,),
        )
        row = cursor.fetchone()
        if row and row[1] == "view":
            cursor2 = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ssa_table'"
            )
            if cursor2.fetchone():
                return "ssa_table"
    except Exception as exc:  # pragma: no cover
        logger.debug("Falha ao resolver tabela fisica para %s: %s", table_name, exc)
    return table_name


def insert_dataframe_optimized(
    df: pd.DataFrame,
    db_path: str,
    table_name: str = 'ssas',
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

    try:
        work = df.copy().reset_index(drop=True)

        # Normalizar numero_ssa de forma vetorizada
        if 'numero_ssa' in work.columns:
            work['numero_ssa'] = work['numero_ssa'].astype(str).str.strip()
            work['numero_ssa'] = work['numero_ssa'].replace(['nan', 'None', ''], None)

        # Converter datas de forma mais eficiente (vetorizada)
        date_columns = [
            'data_cadastro',
            'prazo_limite',
            'data_limite',
            'desde',
            'desde_1',
        ]
        for col in date_columns:
            if col in work.columns:
                work[col] = pd.to_datetime(work[col], errors='coerce', dayfirst=True)
                work[col] = (
                    work[col]
                    .dt.strftime('%Y-%m-%d %H:%M:%S')
                    .where(work[col].notna(), None)
                )

        with get_db_connection(db_path) as conn:
            # ===== CONFIGURAÇÕES DE PERFORMANCE SQLITE =====
            logger.info("FIX APLICANDO OTIMIZAÇÕES SQLITE")
            conn.execute("PRAGMA journal_mode=WAL")        # Permite leituras concorrentes
            conn.execute("PRAGMA synchronous=NORMAL")      # Balanço entre segurança e velocidade
            conn.execute("PRAGMA cache_size=10000")        # Cache maior = menos I/O
            conn.execute("PRAGMA temp_store=MEMORY")       # Operações temporárias em RAM
            conn.execute("PRAGMA mmap_size=268435456")     # Memory-mapped I/O (256MB)

            # LOG: Verificar configurações aplicadas
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode")
            journal_mode = cur.fetchone()[0]
            cur.execute("PRAGMA cache_size")
            cache_size = cur.fetchone()[0]
            logger.info(f"OK Configurações aplicadas: journal_mode={journal_mode}, cache_size={cache_size}")

            target_table = _resolve_physical_table(conn, table_name)
            if not is_valid_identifier(target_table):
                raise ValueError(f"Invalid SQL identifier for table: {target_table!r}")

            # Criar índice temporário se não existir
            try:
                idx_stmt = (
                    f"CREATE INDEX IF NOT EXISTS idx_temp_numero_ssa ON {target_table}(numero_ssa)"
                )
                conn.execute(idx_stmt)
            except Exception as e:  # pragma: no cover - não crítico
                logger.warning("Aviso ao criar índice temporário: %s", e)

            # Separar registros com e sem SSA
            if 'numero_ssa' in work.columns:
                has_ssa = work[work['numero_ssa'].notna()].copy()
                no_ssa = work[work['numero_ssa'].isna()].copy()
            else:
                has_ssa = pd.DataFrame()
                no_ssa = work.copy()

            total_inserted = 0

            # ===== GARANTIR QUE TODAS AS COLUNAS EXISTEM =====
            # Adicionar colunas faltantes antes de inserir
            ensure_columns_exist(conn, target_table, work)

            # ===== INSERIR REGISTROS SEM SSA (APPEND SIMPLES) =====
            if not no_ssa.empty:
                safe_chunksize = sqlite_safe_chunksize(len(no_ssa.columns))
                # method='multi' ignora chunksize; usar chunksize seguro
                no_ssa.to_sql(target_table, conn, if_exists='append', index=False, chunksize=safe_chunksize)
                total_inserted += len(no_ssa)
                logger.info(f"[OK] Inseridos {len(no_ssa)} registros sem numero_ssa")

            # ===== ESTRATÉGIA OTIMIZADA PARA REGISTROS COM SSA =====
            if not has_ssa.empty:
                # Verificar se tabela existe antes de fazer SELECT
                table_exists = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    conn,
                    params=(target_table,),
                )

                # OTIMIZACAO CHAVE: lookup apenas das SSAs que precisamos, em chunks
                lookup_start = time.time()
                existing_dict = {}
                if not table_exists.empty:
                    unique_ssas = (
                        has_ssa['numero_ssa']
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    if unique_ssas:
                        # Respeita limite de variaveis do SQLite (999). Usamos margem.
                        lookup_chunk = max(1, SQLITE_MAX_VARIABLES - 50)
                        for i in range(0, len(unique_ssas), lookup_chunk):
                            chunk_ssas = unique_ssas[i:i + lookup_chunk]
                            placeholders = ",".join(["?"] * len(chunk_ssas))
                            query = (
                                f"SELECT numero_ssa, data_cadastro FROM {target_table} "
                                f"WHERE numero_ssa IN ({placeholders})"
                            )
                            chunk_df = pd.read_sql_query(query, conn, params=chunk_ssas)
                            if not chunk_df.empty:
                                existing_dict.update(
                                    dict(zip(chunk_df['numero_ssa'], chunk_df['data_cadastro']))
                                )
                lookup_time = time.time() - lookup_start

                logger.info(
                    "Lookup de SSAs existentes: %s encontrados em %.3fs",
                    len(existing_dict),
                    lookup_time,
                )

                # Classificar registros em lotes
                to_insert = []
                to_update = []

                for idx, row in has_ssa.iterrows():
                    numero_ssa = row['numero_ssa']
                    new_date = row.get('data_cadastro')

                    if numero_ssa not in existing_dict:
                        to_insert.append(row)
                        continue
                    # Verificar se deve atualizar baseado na data
                    existing_date = existing_dict[numero_ssa]
                    should_update = False
                    if new_date and not existing_date:
                        should_update = True
                    elif new_date and existing_date:
                        try:
                            if pd.to_datetime(new_date) >= pd.to_datetime(existing_date):
                                should_update = True
                        except Exception:  # pragma: no cover - caminho raro
                            should_update = True
                    if should_update:
                        to_update.append(row)

                # ===== INSERÇÃO EM LOTE DE NOVOS REGISTROS =====
                if to_insert:
                    insert_df = pd.DataFrame(to_insert)
                    # Calcula chunksize dinamico centralizado para evitar limite de variaveis
                    safe_chunksize = sqlite_safe_chunksize(len(insert_df.columns))
                    # method='multi' ignora chunksize; usar chunksize seguro
                    insert_df.to_sql(target_table, conn, if_exists='append', index=False, chunksize=safe_chunksize)
                    total_inserted += len(insert_df)
                    logger.info(f"[OK] Inseridos {len(insert_df)} novos registros com SSA (chunksize={safe_chunksize})")

                # ===== ATUALIZAÇÃO EM LOTE (DELETE + INSERT é mais rápido que UPDATE) =====
                if to_update:
                    update_df = pd.DataFrame(to_update)

                    # Processar em chunks seguros para SQLite (centralizado)
                    CHUNK_SIZE = sqlite_safe_chunksize(len(update_df.columns))
                    logger.debug(f"Chunk size calculado: {CHUNK_SIZE} linhas para {len(update_df.columns)} colunas")
                    ssa_list = list(update_df['numero_ssa'])
                    try:
                        conn.execute("SAVEPOINT ssa_batch_update")
                        for i in range(0, len(ssa_list), CHUNK_SIZE):
                            chunk_ssas = ssa_list[i:i + CHUNK_SIZE]
                            ssa_placeholders = ','.join(['?'] * len(chunk_ssas))
                            delete_query = (
                                f"DELETE FROM {target_table} WHERE numero_ssa IN ({ssa_placeholders})"
                            )
                            conn.execute(delete_query, chunk_ssas)

                        # Inserir versões atualizadas com chunk size dinâmico centralizado
                        # method='multi' ignora chunksize; usar chunksize seguro
                        update_df.to_sql(target_table, conn, if_exists='append', index=False, chunksize=CHUNK_SIZE)
                        conn.execute("RELEASE SAVEPOINT ssa_batch_update")
                        total_inserted += len(update_df)
                        logger.info(f"[OK] Atualizados {len(update_df)} registros existentes")
                    except Exception:
                        with suppress(Exception):
                            conn.execute("ROLLBACK TO SAVEPOINT ssa_batch_update")
                            conn.execute("RELEASE SAVEPOINT ssa_batch_update")
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
