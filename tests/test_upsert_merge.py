# tests/test_upsert_merge.py
"""Testa preservação de campos não-nulos no upsert (_perform_upsert).

Fluxo:
  1. Inserir linha inicial completa.
  2. Inserir linha com mesmo numero_ssa, data igual/mais recente, porém alguns campos vazios.
  3. Verificar que campos não-nulos antigos foram preservados.
"""
from __future__ import annotations

import sqlite3
import pandas as pd
from armazenamento import database


def _temp_db(tmp_path):
    db = tmp_path / "merge.db"
    database.initialize_database(str(db))
    return db


def test_upsert_preserves_non_null_fields(tmp_path):
    db_path = _temp_db(tmp_path)

    original = pd.DataFrame([
        {
            "numero_ssa": "202501234",
            "situacao": "ABERTA",
            "data_cadastro": "2025-09-10 10:00:00",
            "descricao_ssa": "Descricao Completa",
            "setor_executor": "SETOR X",
        }
    ])
    database.insert_dataframe_with_smart_upsert(original, str(db_path), "ssas")

    # Atualização: situacao muda, descricao_ssa vem vazia (não deve apagar), setor_executor None
    update = pd.DataFrame([
        {
            "numero_ssa": "202501234",
            "situacao": "EM ANDAMENTO",
            "data_cadastro": "2025-09-10 11:00:00",  # mais recente
            "descricao_ssa": "",  # vazio -> preservar anterior
            "setor_executor": None,  # None -> preservar
        }
    ])
    database.insert_dataframe_with_smart_upsert(update, str(db_path), "ssas")

    with sqlite3.connect(db_path) as conn:
        row = pd.read_sql_query("SELECT situacao, descricao_ssa, setor_executor FROM ssa_table WHERE numero_ssa='202501234'", conn).iloc[0]

    assert row['situacao'] == 'EM ANDAMENTO'
    assert row['descricao_ssa'] == 'Descricao Completa'  # preservado
    assert row['setor_executor'] == 'SETOR X'  # preservado
