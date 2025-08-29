# armazenamento/database_optimized.py
"""
Versão otimizada das funções de banco de dados para importação rápida.
Integra com o sistema existente mantendo compatibilidade.
"""

import sqlite3
import pandas as pd
import logging
import time
from typing import Optional
from contextlib import contextmanager

from .database import get_db_connection

logger = logging.getLogger(__name__)

def insert_dataframe_optimized(df: pd.DataFrame, db_path: str, table_name: str = 'ssas') -> bool:
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
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite', 'desde', 'desde_1']
        for col in date_columns:
            if col in work.columns:
                # Conversão vetorizada mais rápida
                work[col] = pd.to_datetime(work[col], errors='coerce', dayfirst=True)
                work[col] = work[col].dt.strftime('%Y-%m-%d %H:%M:%S').where(work[col].notna(), None)

        with get_db_connection(db_path) as conn:
            # ===== CONFIGURAÇÕES DE PERFORMANCE SQLITE =====
            conn.execute("PRAGMA journal_mode=WAL")        # Permite leituras concorrentes
            conn.execute("PRAGMA synchronous=NORMAL")      # Balanço entre segurança e velocidade  
            conn.execute("PRAGMA cache_size=10000")        # Cache maior = menos I/O
            conn.execute("PRAGMA temp_store=MEMORY")       # Operações temporárias em RAM
            conn.execute("PRAGMA mmap_size=268435456")     # Memory-mapped I/O (256MB)
            
            # Criar índice temporário se não existir
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_temp_numero_ssa ON {table_name}(numero_ssa)")
            except Exception as e:
                logger.warning(f"Aviso ao criar índice: {e}")
            
            # Separar registros com e sem SSA
            has_ssa = work[work['numero_ssa'].notna()].copy() if 'numero_ssa' in work.columns else pd.DataFrame()
            no_ssa = work[work['numero_ssa'].isna()].copy() if 'numero_ssa' in work.columns else work.copy()

            total_inserted = 0
            
            # ===== INSERIR REGISTROS SEM SSA (APPEND SIMPLES) =====
            if not no_ssa.empty:
                no_ssa.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                total_inserted += len(no_ssa)
                logger.info(f"✅ Inseridos {len(no_ssa)} registros sem numero_ssa")

            # ===== ESTRATÉGIA OTIMIZADA PARA REGISTROS COM SSA =====
            if not has_ssa.empty:
                # 🚀 OTIMIZAÇÃO CHAVE: Uma consulta para TODAS as SSAs existentes
                existing_ssas_df = pd.read_sql_query(
                    f"SELECT numero_ssa, data_cadastro FROM {table_name} WHERE numero_ssa IS NOT NULL",
                    conn
                )
                
                # Criar dicionário para lookup O(1) em vez de O(n) por linha
                existing_dict = {}
                if not existing_ssas_df.empty:
                    existing_dict = dict(zip(existing_ssas_df['numero_ssa'], existing_ssas_df['data_cadastro']))
                
                # Classificar registros em lotes
                to_insert = []
                to_update = []
                
                for idx, row in has_ssa.iterrows():
                    numero_ssa = row['numero_ssa']
                    new_date = row.get('data_cadastro')
                    
                    if numero_ssa not in existing_dict:
                        # Novo registro
                        to_insert.append(row)
                    else:
                        # Verificar se deve atualizar baseado na data
                        existing_date = existing_dict[numero_ssa]
                        should_update = False
                        
                        if new_date and not existing_date:
                            should_update = True
                        elif new_date and existing_date:
                            try:
                                if pd.to_datetime(new_date) >= pd.to_datetime(existing_date):
                                    should_update = True
                            except:
                                should_update = True  # Em caso de erro, atualizar
                        
                        if should_update:
                            to_update.append(row)
                
                # ===== INSERÇÃO EM LOTE DE NOVOS REGISTROS =====
                if to_insert:
                    insert_df = pd.DataFrame(to_insert)
                    insert_df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                    total_inserted += len(insert_df)
                    logger.info(f"✅ Inseridos {len(insert_df)} novos registros com SSA")
                
                # ===== ATUALIZAÇÃO EM LOTE (DELETE + INSERT é mais rápido que UPDATE) =====
                if to_update:
                    update_df = pd.DataFrame(to_update)
                    
                    # Estratégia: DELETE em lote + INSERT em lote
                    ssa_placeholders = ','.join(['?' for _ in update_df['numero_ssa']])
                    delete_query = f"DELETE FROM {table_name} WHERE numero_ssa IN ({ssa_placeholders})"
                    conn.execute(delete_query, list(update_df['numero_ssa']))
                    
                    # Inserir versões atualizadas
                    update_df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                    total_inserted += len(update_df)
                    logger.info(f"✅ Atualizados {len(update_df)} registros existentes")

            # Commit explícito
            conn.commit()
            
            elapsed_time = time.time() - start_time
            rate = total_inserted / elapsed_time if elapsed_time > 0 else 0
            
            logger.info(f"🚀 Inserção otimizada concluída:")
            logger.info(f"   📊 {total_inserted} registros processados")
            logger.info(f"   ⏱️  {elapsed_time:.2f} segundos")
            logger.info(f"   📈 {rate:.1f} registros/segundo")
            
            return True

    except Exception as e:
        logger.error(f"❌ Erro na inserção otimizada: {e}")
        return False

def enable_optimized_import():
    """
    Ativa o modo de importação otimizada substituindo a função padrão.
    Deve ser chamado antes de run_importer_logic().
    """
    # Substituir a função no módulo database
    import armazenamento.database as db_module
    
    # Backup da função original
    if not hasattr(db_module, '_original_insert_dataframe_with_smart_upsert'):
        db_module._original_insert_dataframe_with_smart_upsert = db_module.insert_dataframe_with_smart_upsert
    
    # Substituir pela versão otimizada
    db_module.insert_dataframe_with_smart_upsert = insert_dataframe_optimized
    
    logger.info("🚀 Modo de importação otimizada ATIVADO")

def disable_optimized_import():
    """
    Desativa o modo de importação otimizada restaurando a função original.
    """
    import armazenamento.database as db_module
    
    if hasattr(db_module, '_original_insert_dataframe_with_smart_upsert'):
        db_module.insert_dataframe_with_smart_upsert = db_module._original_insert_dataframe_with_smart_upsert
        logger.info("🔄 Modo de importação padrão RESTAURADO")
    else:
        logger.warning("⚠️  Função original não encontrada para restaurar")
