#!/usr/bin/env python3
import pandas as pd
import sqlite3
import os
from pathlib import Path

print("🔧 CORREÇÃO RÁPIDA - PROBLEMA UNNAMED")

# Testar um arquivo específico
arquivo_teste = "docs_entrada/Consulta SSA - 14-07-2025_0343PM.xlsx"

try:
    print(f"📂 Testando: {arquivo_teste}")
    
    # Ler com index_col=False para evitar Unnamed
    df = pd.read_excel(arquivo_teste, index_col=False)
    print(f"📊 Colunas originais: {list(df.columns)}")
    
    # Identificar colunas Unnamed
    unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
    print(f"🔍 Colunas Unnamed encontradas: {unnamed_cols}")
    
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
        print(f"✅ Colunas Unnamed removidas")
    
    print(f"📊 Colunas finais: {list(df.columns)}")
    print(f"📊 Total de linhas: {len(df)}")
    
    # Teste de inserção simples
    if len(df) > 0:
        print("🔧 Testando inserção no banco...")
        
        # Limpar registros NaN problemáticos
        df_clean = df.dropna(how='all')
        
        if 'numero_ssa' in df_clean.columns:
            df_clean = df_clean[df_clean['numero_ssa'].notna()]
        
        print(f"📊 Registros limpos: {len(df_clean)}")
        
        if len(df_clean) > 0:
            # Testar inserção de apenas 1 registro
            test_row = df_clean.iloc[0:1]
            print(f"🧪 Testando com 1 registro: {dict(test_row.iloc[0])}")
            
            try:
                with sqlite3.connect('data/ssas.db') as conn:
                    test_row.to_sql('ssas', conn, if_exists='append', index=False)
                    print("✅ INSERÇÃO DE TESTE FUNCIONOU!")
            except Exception as e:
                print(f"❌ Erro na inserção: {e}")
    
    print("✅ TESTE CONCLUÍDO")
    
except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    import traceback
    traceback.print_exc()
