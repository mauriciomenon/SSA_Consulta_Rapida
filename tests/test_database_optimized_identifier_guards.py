from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

import armazenamento.database_optimized as database_optimized_module
import shared.date_utils as date_utils_module
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


def test_insert_dataframe_optimized_coerces_non_datetime_parse_result(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "coerce_non_datetime_parse_result.db")
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

    def _return_object_series(series):
        return pd.Series(["not-a-date"] * len(series), index=series.index)

    monkeypatch.setattr(
        date_utils_module,
        "parse_datetime_series_mixed",
        _return_object_series,
    )

    df = pd.DataFrame(
        {
            "numero_ssa": ["202600901"],
            "data_cadastro": ["not-a-date"],
            "situacao": ["STE"],
            "descricao_ssa": ["date parse fallback"],
        }
    )

    assert insert_dataframe_optimized(df, db_path, table_name="ssa_table") is True

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT data_cadastro, situacao, descricao_ssa
            FROM ssa_table
            WHERE numero_ssa = ?
            """,
            ("202600901",),
        ).fetchone()
    finally:
        conn.close()

    assert row == (None, "STE", "date parse fallback")


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
    def _tracking_connection(path: str, **_kwargs):
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


def test_insert_dataframe_optimized_releases_savepoint_after_rollback(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "savepoint_rollback_release.db")
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
        conn.execute(
            """
            INSERT INTO ssa_table (numero_ssa, data_cadastro, situacao, descricao_ssa)
            VALUES (?, ?, ?, ?)
            """,
            ("202600654", "2026-01-16 00:00:00", "ADM", "estado antigo"),
        )
        conn.commit()
    finally:
        conn.close()

    @contextmanager
    def _tracking_connection(path: str, **_kwargs):
        tracked_conn = sqlite3.connect(path)
        tracked_conn.set_trace_callback(statements.append)
        try:
            yield tracked_conn
        finally:
            tracked_conn.close()

    original_normalize = database_optimized_module._normalize_unique_ssa_values
    call_count = {"value": 0}

    def _explode_normalize(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] >= 2:
            raise RuntimeError("forced savepoint failure")
        return original_normalize(*args, **kwargs)

    monkeypatch.setattr(
        database_optimized_module, "get_db_connection", _tracking_connection
    )
    monkeypatch.setattr(
        database_optimized_module, "_normalize_unique_ssa_values", _explode_normalize
    )

    incoming = pd.DataFrame(
        {
            "numero_ssa": ["202600654"],
            "data_cadastro": [pd.Timestamp("2026-01-16")],
            "situacao": ["STE"],
            "descricao_ssa": ["estado final"],
        }
    )

    assert (
        insert_dataframe_optimized(incoming, db_path, table_name="ssa_table") is False
    )

    normalized_statements = [stmt.upper() for stmt in statements]
    assert any("SAVEPOINT SSA_BATCH_UPDATE" in stmt for stmt in normalized_statements)
    assert any(
        "ROLLBACK TO SAVEPOINT SSA_BATCH_UPDATE" in stmt
        for stmt in normalized_statements
    )
    assert any(
        "RELEASE SAVEPOINT SSA_BATCH_UPDATE" in stmt for stmt in normalized_statements
    )

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT situacao FROM ssa_table WHERE numero_ssa = ?",
            ("202600654",),
        ).fetchone()
    finally:
        conn.close()

    assert row == ("ADM",)


def test_insert_dataframe_optimized_aborts_when_update_lookup_is_incomplete(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "incomplete_update_lookup.db")
    statements: list[str] = []

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
                "202600777",
                "2026-01-01 00:00:00",
                "ADM",
                "descricao-antiga",
                "origem-antiga.csv",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    @contextmanager
    def _tracking_connection(path: str, **_kwargs):
        tracked_conn = sqlite3.connect(path)
        tracked_conn.set_trace_callback(statements.append)
        try:
            yield tracked_conn
        finally:
            tracked_conn.close()

    original_iter_lookup = database_optimized_module._iter_lookup_chunks_by_ssa

    def _drop_second_lookup(
        conn,
        *,
        target_table_sql,
        normalized_ssas,
        select_expr,
        initial_chunk_size=500,
    ):
        if select_expr == "*":
            yield pd.DataFrame(columns=["numero_ssa", "data_cadastro", "situacao"])
            return
        yield from original_iter_lookup(
            conn,
            target_table_sql=target_table_sql,
            normalized_ssas=normalized_ssas,
            select_expr=select_expr,
            initial_chunk_size=initial_chunk_size,
        )

    monkeypatch.setattr(
        database_optimized_module,
        "_iter_lookup_chunks_by_ssa",
        _drop_second_lookup,
    )
    monkeypatch.setattr(
        database_optimized_module, "get_db_connection", _tracking_connection
    )

    incoming = pd.DataFrame(
        {
            "numero_ssa": ["202600777"],
            "data_cadastro": [pd.Timestamp("2026-01-02")],
            "situacao": ["STE"],
            "descricao_ssa": ["descricao-nova"],
        }
    )

    assert (
        insert_dataframe_optimized(incoming, db_path, table_name="ssa_table") is False
    )

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT situacao, descricao_ssa, arquivo_origem
            FROM ssa_table
            WHERE numero_ssa = ?
            """,
            ("202600777",),
        ).fetchone()
    finally:
        conn.close()

    assert row == ("ADM", "descricao-antiga", "origem-antiga.csv")
    assert not any(
        stmt.upper().startswith('DELETE FROM "SSA_TABLE"')
        or stmt.upper().startswith("DELETE FROM SSA_TABLE")
        for stmt in statements
    )
