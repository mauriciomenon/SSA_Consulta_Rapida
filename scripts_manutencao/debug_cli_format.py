#!/usr/bin/env python3
"""
Debug: Por que CLI está mostrando "-" no lugar dos números SSA?
"""

import sqlite3
from contextlib import closing

import pandas as pd


def debug_ssa_formatting():
    """Debug da formatação de número SSA na CLI."""

    print("=== DEBUG: Formatação de SSA na CLI ===")

    # 1. Verificar dados no banco
    db_path = "data/ssas.db"

    with closing(sqlite3.connect(db_path)) as conn:
        # Consulta exata que a CLI faz
        query = """
        SELECT
            "Número da SSA" as numero_ssa,
            situacao,
            descricao_ssa
        FROM ssas
        LIMIT 10
        """

        df = pd.read_sql_query(query, conn)

        print("\n1. Dados brutos do banco (query CLI):")
        print(df[["numero_ssa"]].head())
        print(f"Tipos: {df['numero_ssa'].dtype}")
        print(f"Valores únicos (amostra): {df['numero_ssa'].unique()[:5]}")

        # 2. Testar normalize_ssa_number
        print("\n2. Testando normalize_ssa_number:")

        # Simular a função
        def normalize_ssa_number(ssa_value) -> str:
            """Cópia da função CLI."""
            if not ssa_value or str(ssa_value).strip() in ["", "nan", "None", "-"]:
                return "-"

            s = str(ssa_value).strip()

            # Remove caracteres não numéricos
            s = "".join(filter(str.isdigit, s))

            if not s:
                return "-"

            # Já com 9 dígitos
            if len(s) == 9:
                return s

            # 3-5 dígitos -> prefixa ano corrente 2025
            if len(s) <= 5:
                return f"2025{s.zfill(5)}"

            # 7-8 dígitos -> zfill para 9
            return s.zfill(9)

        print("Processando cada valor:")
        for i, valor in enumerate(df["numero_ssa"].head()):
            resultado = normalize_ssa_number(valor)
            print(f"  [{i}] '{valor}' -> '{resultado}'")

        # 3. Verificar se o problema é na query
        print("\n3. Verificando query alternativa:")

        query_alt = """
        SELECT
            numero_ssa,
            situacao,
            descricao_ssa
        FROM ssas
        WHERE numero_ssa IS NOT NULL
        LIMIT 10
        """

        df_alt = pd.read_sql_query(query_alt, conn)
        print(f"Query alternativa retornou {len(df_alt)} registros")
        if not df_alt.empty:
            print(df_alt[["numero_ssa"]].head())
            print(f"Tipos: {df_alt['numero_ssa'].dtype}")


if __name__ == "__main__":
    debug_ssa_formatting()
