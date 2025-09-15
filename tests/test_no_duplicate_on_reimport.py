#!/usr/bin/env python3
"""Testa que reimportar o mesmo lote não cria duplicatas de numero_ssa.

Isto cobre o cenário do antigo test_duplicate_protection em modo moderno.
"""
from __future__ import annotations

import sqlite3
import pandas as pd

from armazenamento import database


def test_no_duplicate_on_reimport(temp_db):
    base_df = pd.DataFrame(
        {
            "numero_ssa": ["202512345", "202512346"],
            "situacao": ["ABERTA", "ABERTA"],
            "data_cadastro": ["2025-01-01 09:00:00", "2025-01-01 09:05:00"],
            "descricao_ssa": ["Desc A", "Desc B"],
        }
    )

    database.insert_dataframe_with_smart_upsert(base_df, temp_db, "ssas")
    database.insert_dataframe_with_smart_upsert(base_df, temp_db, "ssas")  # reimporta igual

    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ssas")
    total = cur.fetchone()[0]
    assert total == 2  # nenhuma duplicata
