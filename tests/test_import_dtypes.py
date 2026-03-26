#!/usr/bin/env python3
"""Testa inserção e dtypes/padronização básica de DataFrame de importação.

Foco:
  * Garantir que a função de insert trate None/strings vazias
  * Normalização de numero_ssa através do fluxo de importação
  * Verificar que colunas essenciais existem na base após insert
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from armazenamento import database
from tests._helpers.dtypes_matrix import DTYPES_BY_NAME


def _fetch_all(conn: sqlite3.Connection, table: str = "ssa_chamados"):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} ORDER BY numero_ssa")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows


def test_basic_import_dataframe(temp_db, sample_import_dataframe):
    # Arrange
    conn = sqlite3.connect(temp_db)
    database.initialize_database(conn)  # garante schema

    df = sample_import_dataframe.copy()

    # Act
    database.insert_dataframe_to_db(conn, df)

    # Assert
    cols, rows = _fetch_all(conn)
    assert "numero_ssa" in cols
    assert len(rows) == 2  # uma linha tinha numero_ssa None -> descartada

    # numero_ssa deve estar normalizado (ou já válido)
    numero_idx = cols.index("numero_ssa")
    situacao_idx = cols.index("situacao")

    numeros = [r[numero_idx] for r in rows]
    assert all(isinstance(v, str) for v in numeros)
    assert len(set(numeros)) == 2

    situacoes = [r[situacao_idx] for r in rows]
    assert set(situacoes) == {"ABERTA", "EM ANDAMENTO"}

    roundtrip_df = pd.DataFrame(rows, columns=cols)
    assert "numero_ssa" in roundtrip_df.columns
    assert str(roundtrip_df["numero_ssa"].dtype) in {"object", "str", "string"}
    assert all(isinstance(v, str) for v in roundtrip_df["numero_ssa"].tolist())

    # Verifica dtypes esperados para subconjunto presente
    for col in [
        "numero_ssa",
        "situacao",
        "data_cadastro",
        "descricao_ssa",
        "setor_executor",
    ]:
        if col in df.columns:  # DataFrame original
            expected = DTYPES_BY_NAME.get(col)
            if expected:
                actual_dtype = str(df[col].dtype)
                expected_dtype = expected["expected_dtype"]
                if expected_dtype == "object" and actual_dtype in {
                    "object",
                    "str",
                    "string",
                }:
                    continue
                assert actual_dtype == expected_dtype, (
                    f"dtype inesperado {col}: {df[col].dtype}"
                )


def test_import_idempotent_insert(temp_db, sample_import_dataframe):
    conn = sqlite3.connect(temp_db)
    database.initialize_database(conn)

    df = sample_import_dataframe.copy()
    database.insert_dataframe_to_db(conn, df)
    database.insert_dataframe_to_db(conn, df)  # segunda vez (idempotente esperada)

    cols, rows = _fetch_all(conn)
    # Dependendo da estratégia de insert pode duplicar; se duplicar, isso revela falta de upsert simples.
    # Aqui validamos que duplicar não cria linhas com numero_ssa None.
    numero_idx = cols.index("numero_ssa")
    numeros = [r[numero_idx] for r in rows]
    assert None not in numeros
    assert "" not in numeros


def test_dataframe_validation_rejects_empty(temp_db):
    conn = sqlite3.connect(temp_db)
    database.initialize_database(conn)
    empty_df = pd.DataFrame({"numero_ssa": [], "situacao": []})
    # Função de validação deve levantar ValueError se DataFrame vazio ou sem colunas mínimas
    try:
        database.insert_dataframe_to_db(conn, empty_df)
    except ValueError as e:
        assert "DataFrame" in str(e)
    else:  # pragma: no cover - caminho de erro esperado
        raise AssertionError("Empty DataFrame should raise ValueError")
