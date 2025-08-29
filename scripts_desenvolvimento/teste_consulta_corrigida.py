#!/usr/bin/env python3
import sqlite3

print("=== TESTE CONSULTA CORRIGIDA ===")

with sqlite3.connect("data/ssas.db") as conn:
    # Teste 1: Query corrigida
    cursor = conn.execute("SELECT numero_ssa, situacao FROM ssas WHERE numero_ssa IS NOT NULL LIMIT 5")
    results = cursor.fetchall()
    
    print("Consulta corrigida:")
    for i, (ssa, situacao) in enumerate(results):
        print(f"  [{i+1}] SSA: {ssa}, Situação: {situacao}")
    
    print(f"\nTotal encontrado: {len(results)} registros")
    
    # Teste 2: Verificar se a query antiga falharia
    try:
        cursor = conn.execute('SELECT "Número da SSA" FROM ssas LIMIT 1')
        print("\nQUERY ANTIGA AINDA FUNCIONA - PROBLEMA PERSISTE")
    except Exception as e:
        print(f"\nQuery antiga FALHA (esperado): {e}")
