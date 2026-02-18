#!/usr/bin/env python3
"""
Teste LEVE de verificação de importação - usa apenas 3 arquivos.
Para teste completo, use: python tests/run_import_verification.py
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, '.')

from core.app_logic import import_files_to_database
from armazenamento.database import get_db_connection, initialize_database
from extracao.extractor import extract_data_from_excel


def test_import_few_files():
    """Testa importação de apenas 3 arquivos (teste rápido)."""
    import gc
    import time
    
    docs_dir = "docs_entrada"
    
    # Verificar diretório
    assert os.path.exists(docs_dir), f"Diretório {docs_dir} não encontrado"
    
    files = [
        f for f in os.listdir(docs_dir)
        if f.endswith('.xlsx') and not f.strip().casefold().startswith('ssas derivadas e relacionadas')
    ]
    assert len(files) > 0, "Nenhum arquivo Excel encontrado"
    
    # Apenas 3 primeiros
    test_files = files[:3]
    print(f"DIR Testando com {len(test_files)} arquivos (de {len(files)} disponíveis)")
    
    # Criar diretório temporário com cópias dos arquivos
    temp_dir = tempfile.mkdtemp(prefix="test_import_verify_")
    temp_docs = os.path.join(temp_dir, "docs_entrada")
    os.makedirs(temp_docs)
    db_path = os.path.join(temp_dir, "test_ssas.db")
    
    try:
        # Copiar apenas os 3 arquivos de teste
        for f in test_files:
            src = os.path.join(docs_dir, f)
            dst = os.path.join(temp_docs, f)
            shutil.copy2(src, dst)
            print(f"  Copiado: {f}")
        
        # Executar importação
        print("RUN Iniciando importação...")
        success = import_files_to_database(temp_docs, db_path, force_import=True)
        assert success, "Falha na importação"
        print("OK Importação concluída")
        
        # Verificar banco - tabela é 'numero_ssa' não 'ssas'
        with get_db_connection(db_path) as conn:
            # Descobrir nome da tabela
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            table_name = tables[0] if tables else "numero_ssa"
            
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            print(f"INFO Total de registros: {total}")
            
            cursor = conn.execute(f"SELECT COUNT(DISTINCT numero_ssa) FROM {table_name} WHERE numero_ssa IS NOT NULL")
            unique = cursor.fetchone()[0]
            print(f" SSAs únicas: {unique}")
        
        assert total > 0, "Nenhum registro no banco"
        
    finally:
        # Forçar garbage collection para liberar handles
        gc.collect()
        time.sleep(0.1)
        
        # Limpar com retry
        for _ in range(3):
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.5)


def test_upsert_logic_limited():
    """Testa lógica de upsert com 1 arquivo apenas."""
    import gc
    import time
    
    docs_dir = "docs_entrada"
    
    assert os.path.exists(docs_dir), f"Diretório {docs_dir} não encontrado"
    
    files = [
        f for f in os.listdir(docs_dir)
        if f.endswith('.xlsx') and not f.strip().casefold().startswith('ssas derivadas e relacionadas')
    ]
    assert len(files) > 0, "Nenhum arquivo encontrado"
    
    # Usar apenas 1 arquivo
    test_file = files[0]
    file_path = os.path.join(docs_dir, test_file)
    
    print(f"INFO Testando upsert com: {test_file}")
    
    # Criar banco temporário
    temp_dir = tempfile.mkdtemp(prefix="test_upsert_")
    db_path = os.path.join(temp_dir, "test_ssas.db")
    schema_path = "config/schema.sql"
    
    try:
        from armazenamento.database import initialize_database, insert_dataframe_with_smart_upsert
        
        # Inicializar banco
        success = initialize_database(db_path, schema_path)
        assert success, "Falha ao inicializar banco"
        
        # Extrair dados
        df = extract_data_from_excel(file_path)
        assert df is not None and not df.empty, "Falha ao extrair dados"
        
        # Primeira inserção
        success1 = insert_dataframe_with_smart_upsert(df, db_path)
        assert success1, "Falha na primeira inserção"
        
        with get_db_connection(db_path) as conn:
            # Descobrir nome da tabela
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            table_name = tables[0] if tables else "numero_ssa"
            
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count1 = cursor.fetchone()[0]
        
        print(f"  Primeira inserção: {count1} registros")
        
        # Segunda inserção (mesmo arquivo - deve fazer upsert)
        success2 = insert_dataframe_with_smart_upsert(df, db_path)
        assert success2, "Falha na segunda inserção"
        
        with get_db_connection(db_path) as conn:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count2 = cursor.fetchone()[0]
        
        print(f"  Segunda inserção: {count2} registros")
        print(f"  Diferença: {count2 - count1}")
        
        # Upsert não deve duplicar
        assert count2 == count1, f"Upsert criou duplicatas: {count1} -> {count2}"
        print("OK Upsert funcionando corretamente")
        
    finally:
        # Forçar garbage collection para liberar handles
        gc.collect()
        time.sleep(0.1)
        
        # Limpar com retry
        for _ in range(3):
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.5)


if __name__ == "__main__":
    test_import_few_files()
    test_upsert_logic_limited()
