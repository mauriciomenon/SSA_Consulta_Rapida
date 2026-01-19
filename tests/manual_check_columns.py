#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("data/ssas.db")
cursor = conn.cursor()

# Verificar se as novas colunas existem
colunas_novas = [
    "registros_espera",
    "num_reprobaciones",
    "situacao_espera",
    "numero_desvios",
    "ate",
    "justificativa",
    "total_tempo_tex_executada",
    "parciais",
    "situacao_da_parcial",
]

cursor.execute("PRAGMA table_info(ssas)")
columns = [col[1] for col in cursor.fetchall()]

print("Verificação das novas colunas:")
for coluna in colunas_novas:
    existe = coluna in columns
    status = "OK EXISTE" if existe else "ERR FALTA"
    print(f"  {coluna}: {status}")

conn.close()
