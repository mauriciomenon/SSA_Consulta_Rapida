#!/usr/bin/env python3
"""
Debug dos arquivos que falham na importação
"""

import os
from pathlib import Path

import pandas as pd

from extracao.extractor import open_validated_excel_source


def investigar_arquivos_problematicos():
    """Investigar arquivos Excel que falham na importação."""

    print("=== INVESTIGAÇÃO DE ARQUIVOS PROBLEMÁTICOS ===")

    docs_entrada = Path("docs_entrada")
    problematicos = [
        "Em Execução_15-08-2025_0416PM.xlsx",
        "Em Execução_15-08-2025_0417PM.xlsx",
        "Não Planejadas em Espera_15-08-2025_0410PM.xlsx",
        "Pendentes de Execução_15-08-2025_0416PM.xlsx",
        "SSAs em Desvio na Programação_15-08-2025_0411PM.xlsx",
        "SSAs Executadas_15-08-2025_0415PM.xlsx",
        "SSAs Pendentes com Execução Parcial_15-08-2025_0416PM.xlsx",
    ]

    for arquivo in problematicos:
        arquivo_path = docs_entrada / arquivo
        if arquivo_path.exists():
            print(f"\nFILE Investigando: {arquivo}")
            try:
                # Ler apenas as primeiras linhas para ver a estrutura
                with open_validated_excel_source(arquivo_path) as source_stream:
                    df = pd.read_excel(source_stream, header=1, nrows=3)
                print(f"  OK Leitura OK: {len(df)} linhas de exemplo")
                print(f"  INFO Colunas ({len(df.columns)}): {list(df.columns)[:5]}...")

                # Verificar se há problemas de index
                if df.index.duplicated().any():
                    print("  WARN  PROBLEMA: Índices duplicados detectados")
                    duplicados = df.index.duplicated().sum()
                    print(f"     Total de duplicados: {duplicados}")

                # Verificar tamanho total
                with open_validated_excel_source(arquivo_path) as source_stream:
                    df_full = pd.read_excel(source_stream, header=1)
                print(f"  INFO Tamanho total: {len(df_full)} linhas")

                if df_full.index.duplicated().any():
                    print("   CONFIRMADO: Arquivo tem índices duplicados")
                    print(f"     Duplicados: {df_full.index.duplicated().sum()}")

            except Exception as e:
                print(f"  ERR ERRO ao ler arquivo: {e}")
        else:
            print(f"\nERR Arquivo não encontrado: {arquivo}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    investigar_arquivos_problematicos()
