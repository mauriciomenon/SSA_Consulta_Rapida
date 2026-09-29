#!/usr/bin/env python3
import sqlite3
from contextlib import closing

print("=== INVESTIGANDO FORMATAÇÃO SSA NA GUI ===")

with closing(sqlite3.connect("data/ssas.db")) as conn:
    # Verificar dados específicos
    cursor = conn.execute(
        "SELECT numero_ssa FROM ssas WHERE numero_ssa LIKE '%2513402%' LIMIT 5"
    )
    results = cursor.fetchall()

    print("1. Dados no banco (filtro 2513402):")
    for result in results:
        valor = result[0]
        print(f"   Valor: '{valor}' (tipo: {type(valor)}, len: {len(str(valor))})")

    # Verificar estrutura geral
    cursor = conn.execute(
        "SELECT numero_ssa FROM ssas WHERE numero_ssa IS NOT NULL LIMIT 10"
    )
    results = cursor.fetchall()

    print("\n2. Amostra geral de SSAs:")
    for i, result in enumerate(results):
        valor = result[0]
        print(f"   [{i + 1}] '{valor}' (len: {len(str(valor))})")

    # Verificar se há zeros à esquerda
    cursor = conn.execute(
        "SELECT numero_ssa FROM ssas WHERE numero_ssa LIKE '00%' LIMIT 5"
    )
    results = cursor.fetchall()

    print(f"\n3. SSAs com zeros à esquerda: {len(results)}")
    for result in results:
        valor = result[0]
        print(f"   '{valor}'")
