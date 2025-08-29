#!/usr/bin/env python3
import pandas as pd

print("🔍 ANÁLISE DETALHADA DOS ARQUIVOS EXCEL")
print("=" * 50)

# Testar diferentes formas de ler o Excel
arquivo = "docs_entrada/Consulta SSA - 14-07-2025_0343PM.xlsx"

try:
    print(f"📂 Analisando: {arquivo}")
    
    # Tentativa 1: Leitura padrão
    print("\n1️⃣ Leitura padrão:")
    df1 = pd.read_excel(arquivo)
    print(f"   📊 Colunas: {list(df1.columns)}")
    print(f"   📊 Shape: {df1.shape}")
    if len(df1) > 0:
        print(f"   📋 Primeira linha: {dict(df1.iloc[0])}")
    
    # Tentativa 2: Leitura sem header (tratando linha 0 como dados)
    print("\n2️⃣ Leitura sem header:")
    df2 = pd.read_excel(arquivo, header=None)
    print(f"   📊 Colunas: {list(df2.columns)}")
    print(f"   📊 Shape: {df2.shape}")
    if len(df2) > 0:
        print(f"   📋 Primeira linha: {list(df2.iloc[0])}")
        print(f"   📋 Segunda linha: {list(df2.iloc[1]) if len(df2) > 1 else 'N/A'}")
    
    # Tentativa 3: Leitura com header na linha 1
    print("\n3️⃣ Leitura com header na linha 1:")
    df3 = pd.read_excel(arquivo, header=1)
    print(f"   📊 Colunas: {list(df3.columns)}")
    print(f"   📊 Shape: {df3.shape}")
    if len(df3) > 0:
        print(f"   📋 Primeira linha: {dict(df3.iloc[0])}")
    
    # Tentativa 4: Leitura com header na linha 2
    print("\n4️⃣ Leitura com header na linha 2:")
    df4 = pd.read_excel(arquivo, header=2)
    print(f"   📊 Colunas: {list(df4.columns)}")
    print(f"   📊 Shape: {df4.shape}")
    if len(df4) > 0:
        print(f"   📋 Primeira linha: {dict(df4.iloc[0])}")
    
    # Verificar se existe uma estrutura válida
    print("\n🔍 VERIFICAÇÃO DE ESTRUTURA VÁLIDA:")
    
    for i, df in enumerate([df1, df2, df3, df4], 1):
        print(f"\nDataFrame {i}:")
        if 'numero_ssa' in df.columns:
            print("   ✅ Tem coluna 'numero_ssa'")
        elif any('numero' in str(col).lower() and 'ssa' in str(col).lower() for col in df.columns):
            matching_cols = [col for col in df.columns if 'numero' in str(col).lower() and 'ssa' in str(col).lower()]
            print(f"   🔍 Colunas similares a numero_ssa: {matching_cols}")
        else:
            print("   ❌ Não tem coluna numero_ssa")
        
        # Verificar se alguma linha contém dados válidos que pareçam números SSA
        for idx, row in df.head(10).iterrows():
            for col in df.columns:
                value = row[col]
                if pd.notna(value):
                    # Tentar converter para número
                    try:
                        num_val = int(float(str(value)))
                        if num_val > 100000:  # Números SSA típicos são grandes
                            print(f"   🎯 Possível numero_ssa encontrado na linha {idx}, coluna '{col}': {num_val}")
                            break
                    except:
                        pass
    
except Exception as e:
    print(f"❌ ERRO na análise: {e}")
    import traceback
    traceback.print_exc()
