#!/usr/bin/env python3
"""
TESTE ESPECÍFICO PARA PROBLEMAS DA CLI
"""
import sys
import os
import pandas as pd

# Adiciona o diretório raiz ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def teste_rapido_banco():
    print("🚨 TESTE RÁPIDO - PROBLEMA DA CLI")
    print("=" * 50)
    
    import sqlite3
    conn = sqlite3.connect('data/ssas.db')
    
    # Testa consulta específica que reproduz o problema da CLI
    print("\n🔍 Consulta com filtro 'pt-100' (como CLI fez):")
    
    query = """
    SELECT numero_ssa, situacao, semana_cadastro, descricao_ssa, localizacao_codigo, setor_executor 
    FROM ssas 
    WHERE LOWER(descricao_ssa) LIKE '%pt-100%' 
    LIMIT 10
    """
    
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    
    print(f"📊 Encontrados {len(rows)} registros:")
    for row in rows:
        numero_ssa = row[0] if row[0] is not None else "NULL"
        situacao = row[1] if row[1] is not None else "NULL"
        semana = row[2] if row[2] is not None else "NULL"
        desc = (row[3][:50] + "...") if row[3] else "NULL"
        loc = row[4] if row[4] is not None else "NULL"
        executor = row[5] if row[5] is not None else "NULL"
        
        print(f"  SSA: {numero_ssa} | Sit: {situacao} | Sem: {semana} | Loc: {loc} | Exec: {executor}")
        print(f"      Desc: {desc}")
        print()
    
    # Verifica se o problema é NULL vs valores reais
    print("🔍 Verificação de valores NULL:")
    check_query = """
    SELECT 
        COUNT(*) as total,
        COUNT(numero_ssa) as com_numero,
        COUNT(semana_cadastro) as com_semana
    FROM ssas 
    WHERE LOWER(descricao_ssa) LIKE '%pt-100%'
    """
    
    result = cursor.execute(check_query).fetchone()
    print(f"  Total registros: {result[0]}")
    print(f"  Com numero_ssa: {result[1]}")
    print(f"  Com semana_cadastro: {result[2]}")
    
    conn.close()

if __name__ == "__main__":
    teste_rapido_banco()
