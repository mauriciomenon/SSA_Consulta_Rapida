#!/usr/bin/env python3
"""
Teste de importação dos arquivos problemáticos com correções
"""

import os
import sys
import pandas as pd
import sqlite3
from pathlib import Path

# Adicionar paths necessários
sys.path.append(os.getcwd())

def teste_arquivo_problematico(arquivo_path):
    """Testa importação de um arquivo específico."""
    
    print(f"\n=== TESTANDO: {arquivo_path.name} ===")
    
    try:
        # 1. Ler o arquivo 
        print("📖 Lendo arquivo...")
        df = pd.read_excel(arquivo_path, header=1)
        print(f"   Linhas originais: {len(df)}")
        print(f"   Colunas: {len(df.columns)}")
        
        # 2. Verificar problemas de índice
        if df.index.duplicated().any():
            duplicados = df.index.duplicated().sum()
            print(f"⚠️  Índices duplicados: {duplicados}")
            df = df.reset_index(drop=True)
            print(f"   ✅ Índices corrigidos")
        
        # 3. Remover linhas completamente vazias
        linhas_antes = len(df)
        df = df.dropna(how='all')
        linhas_depois = len(df)
        if linhas_antes > linhas_depois:
            print(f"🧹 Removidas {linhas_antes - linhas_depois} linhas vazias")
        
        # 4. Verificar se há coluna similar a "Número da SSA"
        colunas_ssa = [col for col in df.columns if 'ssa' in str(col).lower() or 'número' in str(col).lower()]
        if colunas_ssa:
            print(f"🔍 Colunas SSA encontradas: {colunas_ssa[:3]}")
        
        # 5. Aplicar mapeamento simples de teste
        mapeamento = {
            'Número da SSA': 'numero_ssa',
            'Situação': 'situacao', 
            'Descrição da SSA': 'descricao_ssa'
        }
        
        df_mapeado = df.copy()
        for old_col, new_col in mapeamento.items():
            if old_col in df_mapeado.columns:
                df_mapeado = df_mapeado.rename(columns={old_col: new_col})
                print(f"   📝 Mapeado: {old_col} -> {new_col}")
        
        # 6. Verificar dados SSA
        if 'numero_ssa' in df_mapeado.columns:
            ssa_validos = df_mapeado['numero_ssa'].dropna()
            print(f"📊 SSAs válidos: {len(ssa_validos)}")
            if len(ssa_validos) > 0:
                print(f"   Amostra: {list(ssa_validos.head(3))}")
        
        print(f"✅ Arquivo processado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal."""
    
    # Garantir diretório correto
    os.chdir(r"c:\Users\menon\git\SSA_Consulta_Rapida")
    
    print("=== TESTE DE ARQUIVOS PROBLEMÁTICOS ===")
    
    # Lista de arquivos que estavam falhando
    arquivos_problema = [
        "Em Execução_15-08-2025_0416PM.xlsx",
        "Em Execução_15-08-2025_0417PM.xlsx",
        "SSAs Executadas_15-08-2025_0415PM.xlsx",
        "SSAs Pendentes com Execução Parcial_15-08-2025_0416PM.xlsx"
    ]
    
    docs_entrada = Path("docs_entrada")
    resultados = {}
    
    for arquivo in arquivos_problema:
        arquivo_path = docs_entrada / arquivo
        if arquivo_path.exists():
            sucesso = teste_arquivo_problematico(arquivo_path)
            resultados[arquivo] = sucesso
        else:
            print(f"\n❌ Arquivo não encontrado: {arquivo}")
            resultados[arquivo] = False
    
    # Resumo
    print(f"\n{'='*50}")
    print("📊 RESUMO DOS TESTES:")
    sucessos = sum(resultados.values())
    total = len(resultados)
    print(f"   ✅ Sucessos: {sucessos}/{total}")
    print(f"   ❌ Falhas: {total - sucessos}/{total}")
    
    for arquivo, sucesso in resultados.items():
        status = "✅" if sucesso else "❌"
        print(f"   {status} {arquivo}")

if __name__ == "__main__":
    main()
