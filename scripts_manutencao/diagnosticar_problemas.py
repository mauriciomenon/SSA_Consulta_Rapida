#!/usr/bin/env python3
"""
DIAGNÓSTICO DOS ERROS DE IMPORTAÇÃO
"""

import os
import sys

import pandas as pd

# Adiciona o diretório raiz ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from extracao.extractor import (  # noqa: E402
    extract_data_from_excel,
    open_validated_excel_source,
)


def diagnosticar_arquivos_problematicos():
    print(" DIAGNÓSTICO DOS ARQUIVOS PROBLEMÁTICOS")
    print("=" * 60)

    # Arquivos que estão falhando
    arquivos_problema = [
        "Em Execução_15-08-2025_0416PM.xlsx",
        "Em Execução_15-08-2025_0417PM.xlsx",
        "Não Planejadas em Espera_15-08-2025_0410PM.xlsx",
        "Pendentes de Execução_15-07-2025_0224PM.xlsx",
        "Pendentes de Execução_15-08-2025_0416PM.xlsx",
        "Pendentes de Planejamento_15-08-2025_0411PM.xlsx",
        "SSAs Pendentes com Execução Parcial_15-08-2025_0416PM.xlsx",
    ]

    for arquivo in arquivos_problema:
        caminho = f"docs_entrada/{arquivo}"
        print(f"\nDIR Analisando: {arquivo}")

        try:
            # Tenta extrair usando nosso sistema
            df = extract_data_from_excel(caminho)

            print(f"  OK Extração OK: {len(df)} registros")
            print(f"  INFO Colunas: {len(df.columns)}")

            # Verifica índices duplicados
            if df.index.duplicated().any():
                duplicados = df.index.duplicated().sum()
                print(f"  WARN ÍNDICES DUPLICADOS: {duplicados}")
            else:
                print("  OK Índices únicos")

            # Verifica se tem colunas duplicadas
            if df.columns.duplicated().any():
                col_dup = df.columns[df.columns.duplicated()].tolist()
                print(f"  WARN COLUNAS DUPLICADAS: {col_dup}")
            else:
                print("  OK Colunas únicas")

            # Amostra
            if len(df) > 0:
                sample = df.iloc[0]
                numero_ssa = sample.get("numero_ssa", "N/A")
                situacao = sample.get("situacao", "N/A")
                print(f"  INFO Amostra: SSA {numero_ssa}, Situação {situacao}")

        except Exception as e:
            print(f"  ERR ERRO na extração: {e}")

            # Tenta ler diretamente com pandas para ver o problema
            try:
                with open_validated_excel_source(caminho) as source_stream:
                    df_raw = pd.read_excel(source_stream, header=1)
                print(f"  INFO Leitura direta: {len(df_raw)} registros")

                if df_raw.index.duplicated().any():
                    print("  WARN Índices duplicados na leitura direta!")

                if df_raw.columns.duplicated().any():
                    col_dup = df_raw.columns[df_raw.columns.duplicated()].tolist()
                    print(f"  WARN Colunas duplicadas: {col_dup}")

            except Exception as e2:
                print(f"  ERR ERRO na leitura direta: {e2}")


if __name__ == "__main__":
    diagnosticar_arquivos_problematicos()
