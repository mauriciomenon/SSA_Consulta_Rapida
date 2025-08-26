#!/usr/bin/env python3
"""
TESTE DIRETO DA CONSULTA DA CLI
"""
import sys
import os

# Adiciona o diretório raiz ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from armazenamento.database import get_connection
import pandas as pd

def testar_consulta_cli():
    print("🧪 TESTE DIRETO DA CONSULTA DA CLI")
    print("=" * 50)
    
    conn = get_connection()
    
    # Consulta que a CLI deveria estar fazendo
    print("\n📊 Testando consulta básica:")
    try:
        df = pd.read_sql_query("SELECT * FROM ssas LIMIT 5", conn)
        print(f"  ✅ Query OK: {len(df)} registros")
        print(f"  📋 Colunas: {list(df.columns)}")
        
        # Verifica se numero_ssa está lá
        if 'numero_ssa' in df.columns:
            print(f"  ✅ numero_ssa presente")
            print(f"  📊 Valores numero_ssa: {df['numero_ssa'].tolist()}")
        else:
            print(f"  ❌ numero_ssa AUSENTE!")
            
        # Verifica semana_cadastro
        if 'semana_cadastro' in df.columns:
            print(f"  ✅ semana_cadastro presente")
            print(f"  📊 Valores semana_cadastro: {df['semana_cadastro'].tolist()}")
        else:
            print(f"  ❌ semana_cadastro AUSENTE!")
            
    except Exception as e:
        print(f"  ❌ ERRO na consulta: {e}")
    
    # Testa consulta com filtro (como pt-100)
    print(f"\n🔍 Testando consulta com filtro 'pt-100':")
    try:
        query = """
        SELECT numero_ssa, situacao, semana_cadastro, descricao_ssa 
        FROM ssas 
        WHERE descricao_ssa LIKE '%pt-100%' 
        LIMIT 5
        """
        df_filtro = pd.read_sql_query(query, conn)
        print(f"  ✅ Query filtro OK: {len(df_filtro)} registros")
        
        for _, row in df_filtro.iterrows():
            print(f"  📋 SSA {row['numero_ssa']}: {row['situacao']} - {row['descricao_ssa'][:50]}...")
            
    except Exception as e:
        print(f"  ❌ ERRO na consulta filtro: {e}")
    
    conn.close()

if __name__ == "__main__":
    testar_consulta_cli()
