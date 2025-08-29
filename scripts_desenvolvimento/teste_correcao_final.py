#!/usr/bin/env python3
"""
Teste direto das funções CLI e GUI corrigidas
"""

import sqlite3
import pandas as pd

# Função CLI corrigida
def get_ssa_query_cli():
    return '''
    SELECT 
        numero_ssa,
        situacao,
        derivada_de,
        localizacao_codigo,
        descricao_localizacao,
        equipamento,
        semana_cadastro,
        data_cadastro,
        descricao_ssa,
        setor_emissor,
        setor_executor,
        solicitante,
        servico_origem,
        grau_prioridade_emissao,
        grau_prioridade_planejamento,
        execucao_simples,
        responsavel_programacao,
        semana_programada,
        responsavel_execucao,
        descricao_execucao
    FROM ssas
    LIMIT 10
    '''

print("=== TESTE QUERY CORRIGIDA ===")

with sqlite3.connect("data/ssas.db") as conn:
    try:
        query = get_ssa_query_cli()
        df = pd.read_sql_query(query, conn)
        
        print(f"✅ Query executada com sucesso!")
        print(f"📊 Registros retornados: {len(df)}")
        
        if 'numero_ssa' in df.columns:
            print(f"\n🎯 Números SSA encontrados:")
            for i, ssa in enumerate(df['numero_ssa'].head(5)):
                print(f"  [{i+1}] SSA: {ssa}")
        
        print(f"\n📋 Situações:")
        for i, situacao in enumerate(df['situacao'].head(5)):
            print(f"  [{i+1}] {situacao}")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
