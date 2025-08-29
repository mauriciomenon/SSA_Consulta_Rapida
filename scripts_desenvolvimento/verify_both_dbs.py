#!/usr/bin/env python3
import sqlite3

print("=== VERIFICAÇÃO DAS BASES DE DADOS ===")

# Verificar main.py
try:
    conn1 = sqlite3.connect('data/ssa_consulta_rapida.db')
    tables1 = conn1.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    count1 = conn1.execute('SELECT COUNT(*) FROM ssa_table').fetchone()[0]
    print(f"✅ main.py DB: {count1} registros, tabelas: {[t[0] for t in tables1]}")
    conn1.close()
except Exception as e:
    print(f"❌ main.py DB: ERRO - {e}")

# Verificar main_dev.py  
try:
    conn2 = sqlite3.connect('ssa_data.db')
    tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    count2 = conn2.execute('SELECT COUNT(*) FROM ssa_table').fetchone()[0]
    print(f"✅ main_dev.py DB: {count2} registros, tabelas: {[t[0] for t in tables2]}")
    conn2.close()
except Exception as e:
    print(f"❌ main_dev.py DB: ERRO - {e}")

print("\n=== RESULTADO ===")
print("Ambas as bases devem ter 1358 registros para funcionamento correto.")
