#!/usr/bin/env python3
# ruff: noqa: E402
"""Quick test of import corrections."""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("TESTE RAPIDO DAS CORRECOES DE IMPORTACAO")
print("=" * 80)

# Test 1: Check table creation
print("\n[TEST 1] Testando criacao de tabela quando nao existe...")

import pandas as pd

from armazenamento.database_optimized import insert_dataframe_optimized

# Create test data
test_df = pd.DataFrame(
    {
        "numero_ssa": ["TEST001", "TEST002"],
        "data_cadastro": ["2025-01-01", "2025-01-02"],
        "descricao_ssa": ["Teste 1", "Teste 2"],
    }
)

# Try to insert when table doesn't exist
try:
    result = insert_dataframe_optimized(test_df, "data/ssas.db", "ssa_table")
    if result:
        print("  [OK] Dados inseridos com sucesso em tabela nova")
    else:
        print("  [ERRO] Falha ao inserir dados")
except Exception as e:
    print(f"  [ERRO] Excecao: {e}")

# Test 2: Check data was inserted
print("\n[TEST 2] Verificando se dados foram inseridos...")

from armazenamento.database import query_db

df = query_db("data/ssas.db", "ssas")
if df is not None and len(df) == 2:
    print(f"  [OK] {len(df)} registros encontrados no banco")
else:
    print(
        f"  [ERRO] Esperado 2 registros, encontrado {len(df) if df is not None else 0}"
    )

# Test 3: Check second insert (table exists)
print("\n[TEST 3] Testando segunda insercao (tabela existe)...")

test_df2 = pd.DataFrame(
    {
        "numero_ssa": ["TEST003"],
        "data_cadastro": ["2025-01-03"],
        "descricao_ssa": ["Teste 3"],
    }
)

try:
    result = insert_dataframe_optimized(test_df2, "data/ssas.db", "ssa_table")
    if result:
        print("  [OK] Dados inseridos com sucesso em tabela existente")
    else:
        print("  [ERRO] Falha ao inserir dados")
except Exception as e:
    print(f"  [ERRO] Excecao: {e}")

# Verify total
df = query_db("data/ssas.db", "ssas")
if df is not None and len(df) == 3:
    print(f"  [OK] Total de {len(df)} registros no banco")
else:
    print(
        f"  [ERRO] Esperado 3 registros, encontrado {len(df) if df is not None else 0}"
    )

print("\n" + "=" * 80)
print("[CONCLUIDO] Testes rapidos completos")
print("=" * 80)
