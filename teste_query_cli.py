#!/usr/bin/env python3
"""
Teste direto da função CLI corrigida
"""

import sys
import os
sys.path.append(os.getcwd())

from interface.cli import get_ssa_query
import sqlite3
import pandas as pd

print("=== TESTE DA QUERY CLI CORRIGIDA ===")

# 1. Verificar se a query foi corrigida
query = get_ssa_query()
print("Query atual:")
print(query[:200] + "...")

# 2. Testar a query
with sqlite3.connect("data/ssas.db") as conn:
    try:
        df = pd.read_sql_query(query, conn)
        print(f"\nQuery executada com sucesso!")
        print(f"Registros retornados: {len(df)}")
        
        if 'numero_ssa' in df.columns:
            print(f"\nPrimeiros números SSA:")
            ssa_values = df['numero_ssa'].dropna().head(5)
            for i, ssa in enumerate(ssa_values):
                print(f"  [{i+1}] {ssa} (tipo: {type(ssa)})")
        else:
            print("\nERRO: Coluna numero_ssa não encontrada!")
            print(f"Colunas disponíveis: {list(df.columns)}")
            
    except Exception as e:
        print(f"ERRO na query: {e}")
        import traceback
        traceback.print_exc()
