import sqlite3

import pandas as pd
import pytest

from armazenamento.schema_manager import ensure_columns_exist


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row[1] for row in rows}


def test_ensure_columns_exist_rejects_invalid_column_identifier() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        before = _table_columns(conn, "ssa_table")

        df = pd.DataFrame({'bad"name': ["x"]})
        with pytest.raises(ValueError, match="Invalid SQL identifier for column"):
            ensure_columns_exist(conn, "ssa_table", df)

        after = _table_columns(conn, "ssa_table")
        assert before == after


def test_ensure_columns_exist_adds_valid_missing_column() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        df = pd.DataFrame({"nova_coluna": [1, 2, 3]})

        ensure_columns_exist(conn, "ssa_table", df)

        cols = _table_columns(conn, "ssa_table")
        assert "nova_coluna" in cols


def test_ensure_columns_exist_maps_bool_column_to_integer() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        df = pd.DataFrame({"flag_ativo": [True, False]})

        ensure_columns_exist(conn, "ssa_table", df)

        row = conn.execute('PRAGMA table_info("ssa_table")').fetchall()[-1]
        assert row[1] == "flag_ativo"
        assert row[2] == "INTEGER"


def test_ensure_columns_exist_rolls_back_partial_schema_additions() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        df = pd.DataFrame({"nova_coluna": [1], 'bad"name': ["x"]})

        with pytest.raises(ValueError, match="Invalid SQL identifier for column"):
            ensure_columns_exist(conn, "ssa_table", df)

        assert "nova_coluna" not in _table_columns(conn, "ssa_table")
