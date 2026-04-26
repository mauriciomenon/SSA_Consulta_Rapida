import sqlite3

conn = sqlite3.connect("data/ssas.db")
cursor = conn.cursor()

# Verificar duplicatas simples
cursor.execute("SELECT COUNT(*) FROM ssas")
total = cursor.fetchone()[0]

cursor.execute(
    "SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL AND numero_ssa != ''"
)
unique_ssas = cursor.fetchone()[0]

print("DIAGNÓSTICO RÁPIDO:")
print(f"Total de registros: {total:,}")
print(f"SSAs únicas: {unique_ssas:,}")
print(f"Possíveis duplicatas: {total - unique_ssas:,}")

# Verificar campos vazios críticos
cursor.execute("SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL OR numero_ssa = ''")
empty_ssa = cursor.fetchone()[0]

cursor.execute(
    "SELECT COUNT(*) FROM ssas WHERE semana_de_cadastro IS NULL OR semana_de_cadastro = '' OR semana_de_cadastro = '-'"
)
empty_week = cursor.fetchone()[0]

print("\nCAMPOS VAZIOS:")
print(f"SSAs sem número: {empty_ssa:,}")
print(f"SSAs sem semana de cadastro: {empty_week:,}")

# Verificar amostra de duplicatas
cursor.execute("""
SELECT numero_ssa, COUNT(*) as count
FROM ssas
WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
GROUP BY numero_ssa
HAVING COUNT(*) > 1
ORDER BY count DESC
LIMIT 5
""")

duplicates = cursor.fetchall()
if duplicates:
    print("\nTOP 5 SSAs MAIS DUPLICADAS:")
    for ssa, count in duplicates:
        print(f"  SSA {ssa}: {count} cópias")

conn.close()
