#!/usr/bin/env python3
"""
Debug: Como os números SSA estão chegando do Excel
"""

import os
from pathlib import Path

import pandas as pd


def debug_ssa_extraction():
    """Debug da extração de SSA do Excel."""

    print("=== DEBUG: EXTRAÇÃO DE SSA DO EXCEL ===")

    # Testar um arquivo específico
    docs_entrada = Path("docs_entrada")
    arquivo_teste = docs_entrada / "Todas as SSAs - 15-08-2025_0431PM.xlsx"

    if not arquivo_teste.exists():
        print(f"ERR Arquivo não encontrado: {arquivo_teste}")
        return

    print(f"FILE Testando: {arquivo_teste.name}")

    try:
        # 1. Ler sem qualquer processamento
        print("\n1. LEITURA BRUTA (sem processamento):")
        df_raw = pd.read_excel(arquivo_teste, header=1, dtype=str)

        # Procurar coluna SSA
        ssa_cols = [
            col
            for col in df_raw.columns
            if "ssa" in str(col).lower() or "número" in str(col).lower()
        ]
        print(f"   Colunas SSA encontradas: {ssa_cols}")

        if ssa_cols:
            col_ssa = ssa_cols[0]
            print(f"   Usando coluna: '{col_ssa}'")

            # Amostrar dados brutos
            sample = df_raw[col_ssa].dropna().head(5)
            print("   Dados BRUTOS (str):")
            for i, val in enumerate(sample):
                print(
                    f"     [{i + 1}] '{val}' (tipo: {type(val)}, len: {len(str(val))})"
                )

        # 2. Ler como números
        print("\n2. LEITURA COMO NÚMEROS:")
        df_num = pd.read_excel(arquivo_teste, header=1)

        if ssa_cols and ssa_cols[0] in df_num.columns:
            col_ssa = ssa_cols[0]
            sample_num = df_num[col_ssa].dropna().head(5)
            print("   Dados NUMÉRICOS:")
            for i, val in enumerate(sample_num):
                print(f"     [{i + 1}] {val} (tipo: {type(val)})")

        # 3. Aplicar pd.to_numeric
        print("\n3. APÓS pd.to_numeric:")
        if ssa_cols and ssa_cols[0] in df_raw.columns:
            col_ssa = ssa_cols[0]
            processed = pd.to_numeric(df_raw[col_ssa], errors="coerce")
            sample_proc = processed.dropna().head(5)
            print("   Dados PROCESSADOS:")
            for i, val in enumerate(sample_proc):
                print(f"     [{i + 1}] {val} (tipo: {type(val)})")

    except Exception as e:
        print(f"ERR ERRO: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    debug_ssa_extraction()
