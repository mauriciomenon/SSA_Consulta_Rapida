"""Pequena verificação manual da whitelist de colunas.

Uso esperado:
  SSA_ALLOWED_COLUMNS="numero_ssa,situacao,data_cadastro" \
    python scripts/check_whitelist_demo.py

Confere se coluna extra é removida antes da inserção.
"""
from __future__ import annotations
import os
import pandas as pd
from armazenamento.database import initialize_database, insert_dataframe_to_db, query_db

def main():
    wl = os.environ.get("SSA_ALLOWED_COLUMNS")
    if not wl:
        print("Defina SSA_ALLOWED_COLUMNS antes de rodar.")
        return
    db = "data/whitelist_demo.db"
    initialize_database(db)
    df = pd.DataFrame([
        {"numero_ssa":"202512345","situacao":"ABERTA","data_cadastro":"2025-09-10","col_extra":123}
    ])
    df.columns = df.columns.str.strip()
    allowed_columns = {column.strip() for column in wl.split(",") if column.strip()}
    df = df[[column for column in df.columns if column in allowed_columns]]
    insert_dataframe_to_db(df, db, "ssas", if_exists="append")
    out = query_db(db, "ssas")
    print("DataFrame inserido (colunas):", list(out.columns))
    if "col_extra" in out.columns:
        raise SystemExit("Whitelist falhou: col_extra ainda presente")
    required_columns = {"numero_ssa", "situacao", "data_cadastro"}
    if not required_columns.issubset(out.columns):
        missing = sorted(required_columns.difference(out.columns))
        raise SystemExit(f"Whitelist incompleto: colunas obrigatorias ausentes {missing}")
    print("OK: whitelist aplicou corretamente.")

if __name__ == "__main__":
    main()
