#!/usr/bin/env python3
import sqlite3
import pandas as pd

# Debug simples
try:
    print("=== DEBUG CLI ===")

    with sqlite3.connect("data/ssas.db") as conn:
        # Query exata da CLI
        query = '''SELECT "Número da SSA" as numero_ssa FROM ssas LIMIT 5'''
        df = pd.read_sql_query(query, conn)

        print("Query CLI:")
        print(df)
        print(f"Tipo: {df['numero_ssa'].dtype}")
        print()

        # Query direta por coluna
        query2 = '''SELECT numero_ssa FROM ssas WHERE numero_ssa IS NOT NULL LIMIT 5'''
        df2 = pd.read_sql_query(query2, conn)

        print("Query direta:")
        print(df2)

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
