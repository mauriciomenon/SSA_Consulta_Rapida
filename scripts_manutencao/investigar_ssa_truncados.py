#!/usr/bin/env python3
"""
Investigar por que SSAs estão truncados - análise dos arquivos originais
"""

import os
import sys
from pathlib import Path

import pandas as pd

# Configurar ambiente - Usar caminho relativo para ser multiplataforma
project_root = Path(__file__).parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

from extracao.extractor import open_validated_excel_source  # noqa: E402


def investigar_ssa_truncados():
    """Investigar por que SSAs chegam truncados no banco."""

    print("=== INVESTIGAÇÃO: SSAs TRUNCADOS ===")
    print("Problema: Banco tem 2513402 (7 dígitos)")
    print("Esperado: 202513402 (9 dígitos - ano + número)")
    print()

    # 1. Examinar alguns arquivos Excel originais
    docs_entrada = Path("docs_entrada")
    arquivos_teste = [
        "Todas as SSAs - 15-08-2025_0431PM.xlsx",
        "SSAs Executadas_15-08-2025_0416PM.xlsx",
        "Em Execução_15-08-2025_0416PM.xlsx",
    ]

    for arquivo in arquivos_teste:
        arquivo_path = docs_entrada / arquivo
        if arquivo_path.exists():
            print(f"\nFILE ANALISANDO: {arquivo}")
            try:
                # Ler com header=0 e header=1 para comparar
                print("   INFO Header=0 (primeira linha):")
                with open_validated_excel_source(arquivo_path) as source_stream:
                    df0 = pd.read_excel(source_stream, header=0, nrows=3)
                cols_relevantes = [
                    col
                    for col in df0.columns
                    if "ssa" in str(col).lower() or "número" in str(col).lower()
                ]
                print(f"      Colunas SSA: {cols_relevantes}")
                if cols_relevantes:
                    col_ssa = cols_relevantes[0]
                    amostras = df0[col_ssa].dropna().head(3).tolist()
                    print(f"      Amostras: {amostras}")

                print("   INFO Header=1 (segunda linha):")
                with open_validated_excel_source(arquivo_path) as source_stream:
                    df1 = pd.read_excel(source_stream, header=1, nrows=3)
                cols_relevantes = [
                    col
                    for col in df1.columns
                    if "ssa" in str(col).lower() or "número" in str(col).lower()
                ]
                print(f"      Colunas SSA: {cols_relevantes}")
                if cols_relevantes:
                    col_ssa = cols_relevantes[0]
                    amostras = df1[col_ssa].dropna().head(3).tolist()
                    print(f"      Amostras: {amostras}")

                    # Verificar se são números completos
                    for i, amostra in enumerate(amostras):
                        if isinstance(amostra, (int, float)):
                            digitos = len(str(int(amostra)))
                            print(f"         [{i + 1}] {amostra} -> {digitos} dígitos")
                        else:
                            print(f"         [{i + 1}] {amostra} -> {type(amostra)}")

            except Exception as e:
                print(f"   ERR ERRO: {e}")
        else:
            print(f"\nERR Arquivo não encontrado: {arquivo}")

    # 2. Verificar o mapeamento de colunas
    print("\nINFO VERIFICANDO MAPEAMENTO DE COLUNAS:")
    try:
        with open("config/column_mappings.json", "r", encoding="utf-8") as f:
            import json

            mappings = json.load(f)

        if "numero_ssa" in mappings:
            print(f"   Mapeamento numero_ssa: {mappings['numero_ssa']}")
        else:
            print("   ERR 'numero_ssa' não encontrado no mapeamento")

    except Exception as e:
        print(f"   ERR Erro ao ler mapeamentos: {e}")

    print("\n" + "=" * 50)
    print("DONE OBJETIVO DA INVESTIGAÇÃO:")
    print("   • Determinar se Excel tem 7 ou 9 dígitos")
    print("   • Verificar se problema é na importação")
    print("   • Corrigir processo para preservar 9 dígitos")


if __name__ == "__main__":
    investigar_ssa_truncados()
