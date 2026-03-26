#!/usr/bin/env python3
"""Check which columns actually exist in database."""

import sqlite3

db_path = "data/ssas.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Colunas que EXISTEM no banco:")
print("-" * 80)

cursor.execute("PRAGMA table_info(ssa_table)")
columns = cursor.fetchall()

for col in columns:
    col_id, name, dtype, notnull, default, pk = col
    print(f"{col_id:3d}. {name:40s} {dtype:15s}")

print()
print(f"Total: {len(columns)} colunas")
print()

# Check specifically for 'id' column
has_id = any(col[1] == "id" for col in columns)
print(f"Coluna 'id' existe? {has_id}")

conn.close()
