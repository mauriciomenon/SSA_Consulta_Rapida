from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pandas as pd

import armazenamento.database_optimized as database_optimized_module
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
    def _closing_connection(path: str):
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
