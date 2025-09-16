#!/usr/bin/env python3
import sqlite3

print("=== SCHEMA DA TABELA SSAS ===")

with sqlite3.connect("data/ssas.db") as conn:
    # Obter schema da tabela
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ssas'")
    schema = cursor.fetchone()[0]

    print("SCHEMA COMPLETO:")
    print(schema)

    print("\n" + "="*50)

    # Testar ambas as queries
    print("\nTESTE 1 - Query com nome original:")
    try:
        cursor = conn.execute('SELECT "Número da SSA" FROM ssas LIMIT 3')
        results = cursor.fetchall()
        print(f"Sucesso: {len(results)} registros")
        for i, (ssa,) in enumerate(results):
            print(f"  [{i+1}] {ssa}")
    except Exception as e:
        print(f"Erro: {e}")

    print("\nTESTE 2 - Query com nome normalizado:")
    try:
        cursor = conn.execute('SELECT numero_ssa FROM ssas LIMIT 3')
        results = cursor.fetchall()
        print(f"Sucesso: {len(results)} registros")
        for i, (ssa,) in enumerate(results):
            print(f"  [{i+1}] {ssa}")
    except Exception as e:
        print(f"Erro: {e}")
