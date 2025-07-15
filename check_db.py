# check_db.py
import sqlite3
conn = sqlite3.connect('data/ssas.db')
# Conta quantas linhas agora existem na tabela 'ssa'
count = conn.execute("SELECT COUNT(*) FROM ssa").fetchone()[0]
print(f"Verificação: A tabela 'ssa' agora contém {count} registros.")
conn.close()
