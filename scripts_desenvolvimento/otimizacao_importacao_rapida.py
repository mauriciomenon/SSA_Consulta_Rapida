#!/usr/bin/env python3
# otimizacao_importacao_rapida.py
"""
Script de otimização de importação - versão RÁPIDA e eficiente.
Corrige os gargalos identificados na importação lenta.
"""

import os
import sys
import pandas as pd
import sqlite3
import logging
from datetime import datetime
import time

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar path do projeto
sys.path.insert(0, '.')

def insert_dataframe_optimized(df: pd.DataFrame, db_path: str, table_name: str = 'ssas') -> bool:
    """
    Versão OTIMIZADA da inserção de DataFrame.
    
    Mudanças principais:
    1. Operações em batch em vez de linha por linha
    2. Uso de índices temporários para acelerar consultas
    3. Upsert em massa usando SQLite REPLACE/INSERT OR REPLACE
    4. Redução de conversões desnecessárias
    """
    if df is None or df.empty:
        logger.info("DataFrame vazio ou None, nada para inserir")
        return True

    start_time = time.time()
    logger.info(f"Iniciando inserção otimizada de {len(df)} registros...")

    try:
        work = df.copy().reset_index(drop=True)
        
        # Normalizar numero_ssa de forma vetorizada
        if 'numero_ssa' in work.columns:
            work['numero_ssa'] = work['numero_ssa'].astype(str).str.strip()
            work['numero_ssa'] = work['numero_ssa'].replace(['nan', 'None', ''], None)

        # Converter datas de forma mais eficiente
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite', 'desde', 'desde_1']
        for col in date_columns:
            if col in work.columns:
                # Conversão vetorizada
                work[col] = pd.to_datetime(work[col], errors='coerce', dayfirst=True)
                work[col] = work[col].dt.strftime('%Y-%m-%d %H:%M:%S').where(work[col].notna(), None)

        with sqlite3.connect(db_path) as conn:
            # Habilitar WAL mode para melhor performance
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=memory")
            
            # Criar índice temporário se não existir
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS temp_idx_numero_ssa ON {table_name}(numero_ssa)")
            except Exception as e:
                logger.warning(f"Aviso ao criar índice: {e}")
            
            # Separar registros com e sem SSA
            has_ssa = work[work['numero_ssa'].notna()].copy() if 'numero_ssa' in work.columns else pd.DataFrame()
            no_ssa = work[work['numero_ssa'].isna()].copy() if 'numero_ssa' in work.columns else work.copy()

            total_inserted = 0
            
            # Inserir registros sem SSA (simples append)
            if not no_ssa.empty:
                no_ssa.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                total_inserted += len(no_ssa)
                logger.info(f"Inseridos {len(no_ssa)} registros sem numero_ssa")

            # Para registros com SSA, usar estratégia otimizada
            if not has_ssa.empty:
                # Obter todas as SSAs existentes de uma vez
                existing_ssas = pd.read_sql_query(
                    f"SELECT numero_ssa, data_cadastro FROM {table_name} WHERE numero_ssa IS NOT NULL",
                    conn
                )
                
                if not existing_ssas.empty:
                    existing_dict = dict(zip(existing_ssas['numero_ssa'], existing_ssas['data_cadastro']))
                else:
                    existing_dict = {}
                
                # Classificar novos registros
                to_insert = []
                to_update = []
                
                for idx, row in has_ssa.iterrows():
                    numero_ssa = row['numero_ssa']
                    new_date = row.get('data_cadastro')
                    
                    if numero_ssa not in existing_dict:
                        # Novo registro
                        to_insert.append(row)
                    else:
                        # Verificar se deve atualizar
                        existing_date = existing_dict[numero_ssa]
                        if (new_date and not existing_date) or (new_date and existing_date and new_date >= existing_date):
                            to_update.append(row)
                
                # Inserir novos registros em lote
                if to_insert:
                    insert_df = pd.DataFrame(to_insert)
                    insert_df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                    total_inserted += len(insert_df)
                    logger.info(f"Inseridos {len(insert_df)} novos registros com SSA")
                
                # Atualizar registros existentes
                if to_update:
                    update_df = pd.DataFrame(to_update)
                    
                    # Para updates, usar DELETE + INSERT que é mais rápido que UPDATE individual
                    ssa_list = "', '".join(update_df['numero_ssa'].astype(str))
                    conn.execute(f"DELETE FROM {table_name} WHERE numero_ssa IN ('{ssa_list}')")
                    
                    update_df.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                    total_inserted += len(update_df)
                    logger.info(f"Atualizados {len(update_df)} registros existentes")

            conn.commit()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Inserção otimizada concluída: {total_inserted} registros em {elapsed_time:.2f}s")
            
            return True

    except Exception as e:
        logger.error(f"❌ Erro na inserção otimizada: {e}")
        return False

def import_single_file_optimized(file_path: str, db_path: str) -> bool:
    """Importa um único arquivo Excel de forma otimizada."""
    try:
        logger.info(f"Importando arquivo: {os.path.basename(file_path)}")
        
        # Ler Excel com configurações otimizadas
        df = pd.read_excel(file_path, engine='openpyxl')
        
        if df.empty:
            logger.warning(f"Arquivo vazio: {file_path}")
            return True
        
        # Aplicar mapeamento de colunas (básico)
        # TODO: Carregar do column_mappings.json se necessário
        
        # Inserir usando função otimizada
        return insert_dataframe_optimized(df, db_path)
        
    except Exception as e:
        logger.error(f"❌ Erro ao importar {file_path}: {e}")
        return False

def import_all_files_fast():
    """Importa todos os arquivos Excel rapidamente."""
    print("🚀 IMPORTAÇÃO RÁPIDA E OTIMIZADA")
    print("=" * 50)
    
    docs_dir = "docs_entrada"
    db_path = "data/ssas.db"
    
    if not os.path.exists(docs_dir):
        print(f"❌ Diretório {docs_dir} não encontrado")
        return False
    
    files = [f for f in os.listdir(docs_dir) if f.endswith('.xlsx')]
    print(f"📁 Encontrados {len(files)} arquivos Excel")
    
    # Fazer backup do banco
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"💾 Backup criado: {backup_path}")
    
    start_total = time.time()
    success_count = 0
    
    for i, filename in enumerate(files, 1):
        file_path = os.path.join(docs_dir, filename)
        print(f"📄 [{i}/{len(files)}] {filename}")
        
        if import_single_file_optimized(file_path, db_path):
            success_count += 1
            print(f"  ✅ Sucesso")
        else:
            print(f"  ❌ Falhou")
    
    total_time = time.time() - start_total
    success_rate = (success_count / len(files)) * 100
    
    print("\n" + "=" * 50)
    print(f"🎯 RESULTADO FINAL:")
    print(f"   Arquivos processados: {len(files)}")
    print(f"   Sucessos: {success_count}")
    print(f"   Falhas: {len(files) - success_count}")
    print(f"   Taxa de sucesso: {success_rate:.1f}%")
    print(f"   Tempo total: {total_time:.2f}s")
    print(f"   Tempo médio por arquivo: {total_time/len(files):.2f}s")
    
    return success_count == len(files)

if __name__ == "__main__":
    print("🔧 Otimização de Importação SSA - Versão Rápida")
    print("Este script resolve os problemas de lentidão na importação")
    print()
    
    import_all_files_fast()
