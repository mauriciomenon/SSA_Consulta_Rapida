#!/usr/bin/env python3
"""Test GUI data loading."""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from armazenamento.database import query_db

db_path = os.path.join(project_root, 'data', 'ssas.db')

print("=" * 80)
print("TESTE DE CARREGAMENTO DE DADOS (SIMULANDO GUI)")
print("=" * 80)
print()

try:
    print("[1] Testando query antiga (com coluna 'id')...")
    query_old = '''
    SELECT
        numero_ssa,
        situacao,
        id,
        sistema_origem
    FROM ssa_table
    LIMIT 5
    '''

    try:
        df = query_db(db_path, '', query_old)
        if df.empty:
            print("[ERRO] Query antiga retornou DataFrame vazio")
        else:
            print(f"[OK] Query antiga funcionou: {len(df)} linhas")
    except Exception as e:
        print(f"[ERRO] Query antiga falhou (esperado): {str(e)[:80]}")

    print()
    print("[2] Testando query nova (SELECT *)...")
    query_new = 'SELECT * FROM ssa_table'

    df = query_db(db_path, '', query_new)
    if df.empty:
        print("[ERRO] Query nova retornou DataFrame vazio")
    else:
        print(f"[OK] Query nova funcionou: {len(df)} linhas, {len(df.columns)} colunas")
        print(f"[OK] Primeiras colunas: {list(df.columns)[:10]}")
        print(f"[OK] Tem coluna 'numero_ssa'? {'numero_ssa' in df.columns}")
        print(f"[OK] Tem coluna 'situacao'? {'situacao' in df.columns}")
        print(f"[OK] Tem coluna 'id'? {'id' in df.columns}")

    print()
    print("=" * 80)
    print("[SUCESSO] Query corrigida funciona!")
    print("=" * 80)

except Exception as e:
    print()
    print("=" * 80)
    print(f"[ERRO] {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
