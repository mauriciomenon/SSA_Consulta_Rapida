#!/usr/bin/env python3
import sqlite3

print("=== ANÁLISE DE PADRÕES SSA ===")

with sqlite3.connect("data/ssas.db") as conn:
    # Verificar distribuição de comprimentos
    cursor = conn.execute("""
        SELECT 
            LENGTH(CAST(numero_ssa AS TEXT)) as len,
            COUNT(*) as count,
            MIN(numero_ssa) as min_val,
            MAX(numero_ssa) as max_val
        FROM ssas 
        WHERE numero_ssa IS NOT NULL 
        GROUP BY LENGTH(CAST(numero_ssa AS TEXT))
        ORDER BY len
    """)
    
    print("Distribuição por comprimento:")
    results = cursor.fetchall()
    for len_val, count, min_val, max_val in results:
        print(f"  {len_val} dígitos: {count} registros (range: {min_val} - {max_val})")
    
    # Verificar se começam com anos válidos
    print(f"\nAnálise de anos (primeiros 4 dígitos):")
    cursor = conn.execute("""
        SELECT 
            SUBSTR(CAST(numero_ssa AS TEXT), 1, 4) as ano_prefix,
            COUNT(*) as count
        FROM ssas 
        WHERE numero_ssa IS NOT NULL 
            AND LENGTH(CAST(numero_ssa AS TEXT)) >= 4
        GROUP BY SUBSTR(CAST(numero_ssa AS TEXT), 1, 4)
        ORDER BY count DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    for ano, count in results:
        ano_int = int(ano) if ano.isdigit() else 0
        valido = "✅" if 1990 <= ano_int <= 2050 else "❌"
        print(f"  {ano}: {count} registros {valido}")
    
    # Casos específicos
    print(f"\nCasos específicos:")
    cursor = conn.execute("SELECT numero_ssa FROM ssas WHERE numero_ssa = 2513402")
    if cursor.fetchone():
        print(f"  2513402: ENCONTRADO no banco")
    
    # Verificar se há versões "corretas" similares
    cursor = conn.execute("SELECT numero_ssa FROM ssas WHERE CAST(numero_ssa AS TEXT) LIKE '%513402%'")
    results = cursor.fetchall()
    print(f"  Números contendo '513402': {len(results)}")
    for result in results:
        print(f"    {result[0]}")
