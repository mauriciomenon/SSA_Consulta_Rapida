#!/usr/bin/env python3
"""
Script para verificar se o banco de dados tem dados reais ou placeholders
"""

import sqlite3
import os
import pandas as pd

def check_database():
    db_path = 'data/ssas.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)

        # Verificar se tabela existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ssas'")
        table_exists = cursor.fetchone()

        if table_exists:
            # Verificar algumas amostras de dados
            print('=== VERIFICAÇÃO DE DADOS REAIS vs PLACEHOLDERS ===')

            # Verificar colunas da tabela
            cursor.execute("PRAGMA table_info(ssas)")
            columns = cursor.fetchall()
            print("\nColunas disponíveis na tabela:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

            # Verificar algumas amostras de dados
            try:
                df = pd.read_sql_query('SELECT numero_ssa, semana_cadastro, descricao_execucao FROM ssas LIMIT 5', conn)
                print("\nAmostras de dados:")
                print(df.to_string(index=False))
            except Exception as e:
                print(f"Erro ao consultar dados: {e}")
                # Tentar com outras colunas
                try:
                    df = pd.read_sql_query('SELECT * FROM ssas LIMIT 2', conn)
                    print("\nPrimeiras 2 linhas completas:")
                    print(df.to_string(index=False))
                except Exception as e2:
                    print(f"Erro geral: {e2}")

            # Verificar total de registros
            cursor.execute('SELECT COUNT(*) FROM ssas')
            total = cursor.fetchone()[0]
            print(f'\nTotal de registros: {total}')

        else:
            print('Tabela ssas não existe no banco principal')

        conn.close()
    else:
        print('Banco principal data/ssas.db não existe')

if __name__ == "__main__":
    check_database()
