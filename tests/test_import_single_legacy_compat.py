#!/usr/bin/env python3
"""Compat test substituindo antigo test_single_import.

Objetivo: garantir caminho mínimo de import (DataFrame sintético) usando API moderna.
Não acessa Excel real nem arquivos externos.
"""
from __future__ import annotations

import sqlite3
import pandas as pd

from armazenamento import database


def test_import_single_legacy_compat(temp_db):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202512345"],
            "situacao": ["ABERTA"],
            "data_cadastro": ["2025-01-01 10:00:00"],
            "descricao_ssa": ["Caso único"],
        }
    )

    ok = database.insert_dataframe_to_db(df, temp_db, "ssas")
    assert ok is True

    # Verifica persistência
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT numero_ssa, situacao FROM ssas")
    row = cur.fetchone()
    assert row == ("202512345", "ABERTA")
