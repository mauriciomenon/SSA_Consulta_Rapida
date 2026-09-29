from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

import armazenamento.database_optimized as database_optimized_module
import armazenamento.database_upsert_logic as database_upsert_logic_module
from armazenamento.database_optimized import insert_dataframe_optimized


def test_insert_dataframe_optimized_ignores_rollback_on_closed_connection(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    db_path = str(tmp_path / "closed_connection_rollback.db")
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
    def _closing_connection(path: str, **_kwargs):
        tracked_conn = sqlite3.connect(path)
        try:
            yield tracked_conn
        finally:
            try:
                tracked_conn.close()
            except sqlite3.ProgrammingError:
                pass

    def _close_and_raise(conn_arg, *_args, **_kwargs):
        conn_arg.close()
        raise RuntimeError("forced closed connection failure")

    monkeypatch.setattr(
        database_optimized_module, "get_db_connection", _closing_connection
    )
    monkeypatch.setattr(
        database_optimized_module, "ensure_columns_exist", _close_and_raise
    )

    df = pd.DataFrame(
        {
            "numero_ssa": ["123456789"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["ok"],
        }
    )

    with caplog.at_level("WARNING", logger="armazenamento.database_optimized"):
        assert insert_dataframe_optimized(df, db_path, table_name="ssa_table") is False

    assert "Rollback ignorado no caminho otimizado: conexao ja encerrada." in caplog.text


def test_failure_after_no_ssa_insert_rolls_back_all_rows(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "rollback_after_no_ssa.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE ssa_table (numero_ssa TEXT PRIMARY KEY, situacao TEXT)"
        )

    def _fail_lookup(*_args, **_kwargs):
        raise RuntimeError("forced lookup failure after no-SSA insert")

    monkeypatch.setattr(
        database_optimized_module, "_load_existing_ssa_payloads", _fail_lookup
    )
    frame = pd.DataFrame(
        {
            "numero_ssa": [None, "202600001"],
            "situacao": ["STE", "SPG"],
        }
    )

    assert insert_dataframe_optimized(frame, db_path, "ssa_table") is False
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (0,)


def test_failure_after_new_ssa_insert_rolls_back_entire_batch(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "rollback_after_new_ssa.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE ssa_table ("
            "numero_ssa TEXT PRIMARY KEY, situacao TEXT, descricao_ssa TEXT)"
        )
        conn.execute(
            "INSERT INTO ssa_table VALUES ('202600001', 'STE', 'original')"
        )

    def _fail_merge(*_args, **_kwargs):
        raise RuntimeError("forced update failure after new-SSA insert")

    monkeypatch.setattr(
        database_upsert_logic_module,
        "_merge_overwrite_with_incoming_non_empty",
        _fail_merge,
    )
    frame = pd.DataFrame(
        {
            "numero_ssa": ["202600002", "202600001"],
            "situacao": ["SPG", "APG"],
            "descricao_ssa": ["new", "changed"],
        }
    )

    assert insert_dataframe_optimized(frame, db_path, "ssa_table") is False
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT numero_ssa, situacao, descricao_ssa "
            "FROM ssa_table ORDER BY numero_ssa"
        ).fetchall()
    assert rows == [("202600001", "STE", "original")]
