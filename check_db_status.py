#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/ssas.db')
cursor = conn.cursor()

print("=== VERIFICAÇÃO DO BANCO ===")

# Verificar tabelas
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tabelas encontradas: {[t[0] for t in tables]}")

if tables:
    for table_name in [t[0] for t in tables]:
        print(f"\nEstrutura da tabela '{table_name}':")
        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Contar registros
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"  Total de registros: {count}")
        except Exception as e:
            print(f"  Erro ao contar registros: {e}")

conn.close()
