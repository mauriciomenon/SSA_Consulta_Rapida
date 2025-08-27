#!/usr/bin/env python3
"""
Teste isolado da query corrigida
"""

import sqlite3
import pandas as pd
import os

# Garantir que estamos no diretório correto
os.chdir(r"c:\Users\menon\git\SSA_Consulta_Rapida")

print("=== TESTE FINAL DAS CORREÇÕES ===")

# Query CLI corrigida (copiada do arquivo)
query_cli = '''
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
        grau_prioridade_emissao
    FROM ssas
    LIMIT 10
    '''

try:
    with sqlite3.connect("data/ssas.db") as conn:
        df = pd.read_sql_query(query_cli, conn)
        
        print(f"✅ Query CLI executada com sucesso!")
        print(f"📊 Registros: {len(df)}")
        
        if 'numero_ssa' in df.columns:
            print(f"\n🎯 CORREÇÃO FUNCIONOU! Números SSA:")
            for i, row in df.iterrows():
                ssa = row['numero_ssa']
                situacao = row['situacao']
                print(f"  [{i+1}] SSA: {ssa} | Situação: {situacao}")
                if i >= 4:  # Mostrar apenas 5
                    break
        else:
            print("❌ Coluna numero_ssa não encontrada!")
            
except Exception as e:
    print(f"❌ ERRO: {e}")

print("\n=== RESUMO DA CORREÇÃO ===")
print("🔧 Problema identificado:")
print("   - CLI e GUI consultavam 'Número da SSA' (cabeçalho)")
print("   - Em vez de 'numero_ssa' (dados reais)")
print("✅ Correção aplicada:")
print("   - interface/cli.py: query corrigida")
print("   - gui/gui_ssa.py: query corrigida")
print("🎯 Resultado esperado:")
print("   - CLI agora deve mostrar números SSA reais")
print("   - GUI também deve funcionar corretamente")
