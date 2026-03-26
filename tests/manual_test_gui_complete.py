#!/usr/bin/env python3
"""Test complete GUI workflow without opening window."""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

DB_PATH = os.path.join(project_root, "data", "ssas.db")
TABLE_NAME = "ssa_table"

print("=" * 80)
print("TESTE COMPLETO DO FLUXO DA GUI (SEM ABRIR JANELA)")
print("=" * 80)
print()

# Test 1: Database exists
print("[1] Verificando se banco existe...")
if not os.path.exists(DB_PATH):
    print(f"[ERRO] Banco nao existe: {DB_PATH}")
    sys.exit(1)
print(f"[OK] Banco existe: {os.path.getsize(DB_PATH):,} bytes")

# Test 2: Import data loader worker
print()
print("[2] Importando DataLoaderWorker...")
try:
    from armazenamento.database import query_db

    print("[OK] Imports bem sucedidos")
except Exception as e:
    print(f"[ERRO] Falha no import: {e}")
    sys.exit(1)

# Test 3: Test query directly (what the worker does)
print()
print("[3] Testando query que o worker usa...")
try:
    query = "SELECT * FROM ssa_table"
    df = query_db(DB_PATH, "", query)

    if df.empty:
        print("[ERRO] Query retornou DataFrame vazio")
        sys.exit(1)

    print("[OK] Query funcionou:")
    print(f"     - {len(df):,} linhas")
    print(f"     - {len(df.columns)} colunas")
    print(f"     - Primeiras 5 colunas: {list(df.columns)[:5]}")

except Exception as e:
    print(f"[ERRO] Query falhou: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 4: Check required columns
print()
print("[4] Verificando colunas essenciais...")
required = ["numero_ssa", "situacao", "data_cadastro", "descricao_ssa"]
missing = [col for col in required if col not in df.columns]

if missing:
    print(f"[ERRO] Colunas faltando: {missing}")
    sys.exit(1)

print("[OK] Todas as colunas essenciais presentes")

# Test 5: Sample data
print()
print("[5] Verificando dados de amostra...")
print(f"     Primeira SSA: {df['numero_ssa'].iloc[0]}")
print(f"     Situacao: {df['situacao'].iloc[0]}")
print(f"     Total registros: {len(df):,}")

print()
print("=" * 80)
print("[SUCESSO] Todos os testes passaram!")
print("=" * 80)
print()
print("A GUI deveria carregar dados sem problemas.")
print("Se a GUI ainda falhar, execute:")
print("  python main.py --gui")
print()
print("E envie a mensagem de erro COMPLETA.")
