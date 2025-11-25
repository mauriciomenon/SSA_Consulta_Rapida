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
import pandas as pd  # type: ignore[import-not-found]

from .database import get_db_connection  # Top-level import (safe - defined early in database.py)
from .schema_manager import ensure_columns_exist

logger = logging.getLogger(__name__)


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
            logger.info("🔧 APLICANDO OTIMIZAÇÕES SQLITE")
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
            logger.info(f"✅ Configurações aplicadas: journal_mode={journal_mode}, cache_size={cache_size}")

            # Criar índice temporário se não existir
            try:
                idx_stmt = (
                    f"CREATE INDEX IF NOT EXISTS idx_temp_numero_ssa ON {table_name}(numero_ssa)"
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
            ensure_columns_exist(conn, table_name, work)

            # ===== INSERIR REGISTROS SEM SSA (APPEND SIMPLES) =====
            if not no_ssa.empty:
                no_ssa.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                total_inserted += len(no_ssa)
                logger.info(f"[OK] Inseridos {len(no_ssa)} registros sem numero_ssa")

            # ===== ESTRATÉGIA OTIMIZADA PARA REGISTROS COM SSA =====
            if not has_ssa.empty:
                # Verificar se tabela existe antes de fazer SELECT
                table_exists = pd.read_sql_query(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'",
                    conn
                )

                # OTIMIZACAO CHAVE: Uma consulta para TODAS as SSAs existentes
                lookup_start = time.time()
                existing_ssas_df = pd.DataFrame()  # Vazio por padrao

                if not table_exists.empty:
                    # Tabela existe, fazer lookup
                    existing_ssas_df = pd.read_sql_query(
                        (
                            f"SELECT numero_ssa, data_cadastro FROM {table_name} "
                            "WHERE numero_ssa IS NOT NULL"
                        ),
                        conn,
                    )
                lookup_time = time.time() - lookup_start
                
                # Criar dicionário para lookup O(1) em vez de O(n) por linha
                existing_dict = {}
                if not existing_ssas_df.empty:
                    existing_dict = dict(zip(existing_ssas_df['numero_ssa'], existing_ssas_df['data_cadastro']))
                
                logger.info(f"🔍 Lookup de SSAs existentes: {len(existing_ssas_df)} encontrados em {lookup_time:.3f}s")

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
                    # Calcula chunksize dinamico para evitar "too many SQL variables"
                    # SQLite tem limite de ~999 variaveis. Com 82 colunas: 999/82 = ~12 linhas seguras
                    # CRITICAL: method='multi' IGNORA chunksize - removido
                    num_cols = len(insert_df.columns)
                    safe_chunksize = max(1, 999 // (num_cols + 1))  # +1 margem de seguranca
                    insert_df.to_sql(table_name, conn, if_exists='append', index=False, chunksize=safe_chunksize)
                    total_inserted += len(insert_df)
                    logger.info(f"[OK] Inseridos {len(insert_df)} novos registros com SSA (chunksize={safe_chunksize})")

                # ===== ATUALIZAÇÃO EM LOTE (DELETE + INSERT é mais rápido que UPDATE) =====
                if to_update:
                    update_df = pd.DataFrame(to_update)

                    # 🔧 FIX: Processar em chunks para evitar "too many SQL variables"
                    # SQLite tem limite padrão de 999 variáveis por query
                    # Cálculo dinâmico: 999 variáveis ÷ 35 colunas ≈ 28 linhas por chunk
                    CHUNK_SIZE = min(500, max(1, 999 // len(update_df.columns)))  # Chunk size adaptável
                    logger.debug(f"Chunk size calculado: {CHUNK_SIZE} linhas para {len(update_df.columns)} colunas")
                    ssa_list = list(update_df['numero_ssa'])
                    
                    for i in range(0, len(ssa_list), CHUNK_SIZE):
                        chunk_ssas = ssa_list[i:i + CHUNK_SIZE]
                        ssa_placeholders = ','.join(['?'] * len(chunk_ssas))
                        delete_query = (
                            f"DELETE FROM {table_name} WHERE numero_ssa IN ({ssa_placeholders})"
                        )
                        conn.execute(delete_query, chunk_ssas)

                    # Inserir versões atualizadas com chunk size dinâmico
                    # CRITICAL: method='multi' IGNORA chunksize - removido
                    update_df.to_sql(table_name, conn, if_exists='append', index=False, chunksize=CHUNK_SIZE)
                    total_inserted += len(update_df)
                    logger.info(f"[OK] Atualizados {len(update_df)} registros existentes")

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
