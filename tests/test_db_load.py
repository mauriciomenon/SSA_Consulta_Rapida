#!/usr/bin/env python3
"""Test database loading."""

import sqlite3
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

db_path = os.path.join(project_root, 'data', 'ssas.db')

print("=" * 80)
print("TESTE DE CARREGAMENTO DO BANCO DE DADOS")
print("=" * 80)
print()

try:
    # Teste 1: Arquivo existe?
    print("[1] Verificando se arquivo existe...")
    if not os.path.exists(db_path):
        print(f"[ERRO] Arquivo nao existe: {db_path}")
        sys.exit(1)
    else:
        size = os.path.getsize(db_path)
        print(f"[OK] Arquivo existe: {size:,} bytes")

    # Teste 2: Conectar
    print()
    print("[2] Tentando conectar...")
    conn = sqlite3.connect(db_path)
    print("[OK] Conexao estabelecida")

    # Teste 3: Verificar tabelas
    print()
    print("[3] Listando tabelas...")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    table_names = [t[0] for t in tables]
    print(f"[OK] Tabelas: {table_names}")

    # Teste 4: Contar registros
    print()
    print("[4] Contando registros...")
    for table_name in table_names:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count:,} registros")

    # Teste 5: Verificar tabela 'ssas'
    print()
    print("[5] Verificando tabela 'ssas'...")
    if 'ssas' in table_names:
        print("[OK] Tabela 'ssas' existe")

        # Testar SELECT
        cursor.execute("SELECT COUNT(*) FROM ssas")
        count = cursor.fetchone()[0]
        print(f"[OK] {count:,} registros na tabela ssas")

        # Testar pandas
        df = pd.read_sql_query("SELECT * FROM ssas LIMIT 5", conn)
        print(f"[OK] Pandas carregou {len(df)} linhas com {len(df.columns)} colunas")
        print(f"[OK] Colunas: {list(df.columns)[:10]}...")

    else:
        print("[ERRO] Tabela 'ssas' NAO EXISTE!")
        print(f"[INFO] Tabelas disponiveis: {table_names}")

    # Teste 6: Verificar tabela 'ssa_table'
    print()
    print("[6] Verificando tabela 'ssa_table'...")
    if 'ssa_table' in table_names:
        print("[OK] Tabela 'ssa_table' existe")
        cursor.execute("SELECT COUNT(*) FROM ssa_table")
        count = cursor.fetchone()[0]
        print(f"[OK] {count:,} registros na tabela ssa_table")

        df = pd.read_sql_query("SELECT * FROM ssa_table LIMIT 5", conn)
        print(f"[OK] Pandas carregou {len(df)} linhas com {len(df.columns)} colunas")
    else:
        print("[INFO] Tabela 'ssa_table' nao existe")

    conn.close()

    print()
    print("=" * 80)
    print("[SUCESSO] Todos os testes passaram")
    print("=" * 80)

except Exception as e:
    print()
    print("=" * 80)
    print(f"[ERRO] {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
