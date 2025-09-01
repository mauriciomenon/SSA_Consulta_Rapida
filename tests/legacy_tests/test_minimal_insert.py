#!/usr/bin/env python3
"""
Teste para verificar por que a base não está sendo criada
"""
import sys
import os
import pandas as pd
from armazenamento.database import insert_data_in_database

def test_minimal_insert():
    print("=== TESTE DE INSERÇÃO MÍNIMA ===")
    
    # Criar DataFrame de teste simples
    test_data = {
        'numero_ssa': [12345],
        'descricao_ssa': ['Teste básico'],
        'situacao': ['Pendente'],
        'data_cadastro': ['2025-08-27']
    }
    
    df = pd.DataFrame(test_data)
    print(f"DataFrame de teste criado: {len(df)} registros")
    print(f"Colunas: {list(df.columns)}")
    
    # Tentar inserir
    print("\nTentando inserir dados de teste...")
    success = insert_data_in_database(df, 'ssa_data.db', 'ssa_table')
    
    if success:
        print("✅ Inserção bem-sucedida!")
        
        # Verificar resultado
        import sqlite3
        with sqlite3.connect('ssa_data.db') as conn:
            cursor = conn.cursor()
            
            # Listar tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Tabelas na base: {tables}")
            
            # Contar registros
            if tables:
                for table_name, in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    count = cursor.fetchone()[0]
                    print(f"Tabela {table_name}: {count} registros")
    else:
        print("❌ Falha na inserção")

if __name__ == "__main__":
    test_minimal_insert()
