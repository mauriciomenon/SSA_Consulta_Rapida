#!/usr/bin/env python3
"""
Teste rápido da interface CLI
"""
import sys
import os

# Adiciona o diretório raiz ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    print("🧪 Testando interface CLI...")
    
    # Importa as funções principais
    from interface.cli import load_initial_data
    from armazenamento.database import query_db
    
    # Testa carregamento de dados
    print("📊 Carregando dados iniciais...")
    df, filters = load_initial_data()
    
    print(f"✅ Dados carregados: {len(df)} registros")
    print(f"✅ Filtros aplicados: {filters}")
    
    # Testa consulta direta
    print("🔍 Testando consulta direta...")
    result = query_db("SELECT COUNT(*) FROM ssas")
    print(f"✅ Query funcionando: {result[0][0]} registros no banco")
    
    print("✅ INTERFACE CLI: FUNCIONANDO NORMALMENTE")
    
except Exception as e:
    print(f"❌ ERRO na interface CLI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
