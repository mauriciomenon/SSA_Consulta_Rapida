from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

import armazenamento.database_optimized as database_optimized_module
from armazenamento.database_optimized import (
    _has_referencing_foreign_keys,
    _quote_identifier,
    insert_dataframe_optimized,
)


def test_has_referencing_foreign_keys_rejects_invalid_target_identifier() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child_refs (id INTEGER PRIMARY KEY, numero_ssa TEXT, "
            "FOREIGN KEY(numero_ssa) REFERENCES ssa_table(numero_ssa))"
        )
        conn.commit()

        assert _has_referencing_foreign_keys(conn, "ssa_table;drop") is False
    finally:
        conn.close()


def test_has_referencing_foreign_keys_detects_valid_reference() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child_refs (id INTEGER PRIMARY KEY, numero_ssa TEXT, "
            "FOREIGN KEY(numero_ssa) REFERENCES ssa_table(numero_ssa))"
        )
        conn.commit()

        assert _has_referencing_foreign_keys(conn, "ssa_table") is True
    finally:
        conn.close()


def test_insert_dataframe_optimized_rejects_invalid_table_identifier(tmp_path) -> None:
    db_path = str(tmp_path / "invalid_identifier.db")
    df = pd.DataFrame(
        {
            "numero_ssa": ["123456789"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["ok"],
        }
    )

    assert (
        insert_dataframe_optimized(df, db_path, table_name="ssa_table;drop_table")
        is False
    )


def test_quote_identifier_rejects_invalid_column_identifier() -> None:
    try:
        _quote_identifier("coluna-invalida")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_insert_dataframe_optimized_begins_immediate_transaction(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "immediate_transaction.db")
    statements: list[str] = []

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa TEXT PRIMARY KEY,
                data_cadastro TEXT,
                situacao TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    @contextmanager
    def _tracking_connection(path: str):
        tracked_conn = sqlite3.connect(path)
        tracked_conn.set_trace_callback(statements.append)
        try:
            yield tracked_conn
        finally:
            tracked_conn.close()

    monkeypatch.setattr(
        database_optimized_module, "get_db_connection", _tracking_connection
    )

    df = pd.DataFrame(
        {
            "numero_ssa": ["123456789"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["ok"],
        }
    )

    assert insert_dataframe_optimized(df, db_path, table_name="ssa_table") is True
    assert any(stmt.upper().startswith("BEGIN IMMEDIATE") for stmt in statements)


def test_insert_dataframe_optimized_preserves_columns_outside_batch(tmp_path) -> None:
    db_path = str(tmp_path / "preserve_existing_columns.db")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa TEXT PRIMARY KEY,
                data_cadastro TEXT,
                situacao TEXT,
                descricao_ssa TEXT,
                arquivo_origem TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ssa_table (
                numero_ssa,
                data_cadastro,
                situacao,
                descricao_ssa,
                arquivo_origem
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "202500222",
                "2025-01-01 00:00:00",
                "ANTIGA",
                "descricao-antiga",
                "origem-antiga.csv",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    df = pd.DataFrame(
        {
            "numero_ssa": ["202500222"],
            "data_cadastro": [pd.Timestamp("2025-01-02")],
            "situacao": ["NOVA"],
            "descricao_ssa": ["descricao-nova"],
        }
    )

    assert insert_dataframe_optimized(df, db_path, table_name="ssa_table") is True

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT descricao_ssa, situacao, arquivo_origem
            FROM ssa_table
            WHERE numero_ssa = ?
            """,
            ("202500222",),
        ).fetchone()
    finally:
        conn.close()

    assert row == ("descricao-nova", "NOVA", "origem-antiga.csv")
