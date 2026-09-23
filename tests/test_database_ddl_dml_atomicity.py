"""DDL+DML atomicity contract tests (S5a, IMP-03).

Dynamic column ALTER TABLE and the data insert used to run in separate
transactions: ensure_column_exists opened its own connection and
committed, so a failure in the subsequent DML left the new column
committed in the schema with zero rows. The savepoint now wraps both.
"""

import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento import database  # noqa: E402

SCHEMA_FILE = os.path.join(project_root, "config", "schema_unified.sql")


def columns(db_path: Path, table: str = "ssa_table") -> list[str]:
    with sqlite3.connect(str(db_path)) as conn:
        return [
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table})")  # nosec B608
        ]


def row_count(db_path: Path, table: str = "ssa_table") -> int:
    with sqlite3.connect(str(db_path)) as conn:
        return conn.execute(  # nosec B608
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / "ssas.db"
    database.initialize_database(str(db_path), SCHEMA_FILE)
    return db_path


def base_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "numero_ssa": ["202680001"],
            "descricao_ssa": ["s5a test"],
            "data_cadastro": ["2026-09-01 08:00:00"],
            "setor_emissor": ["IEE1"],
            "setor_executor": ["IEE3"],
            "situacao": ["APV"],
            "nome paciente": ["Joao"],  # dynamic column (space sanitized)
        }
    )


def test_failed_dml_rolls_back_dynamic_column(db):
    """IMP-03 regression: ALTER TABLE and DML must be atomic."""
    schema_before = set(columns(db))

    with patch.object(
        database._up,
        "_append_dataframe_rows",
        side_effect=RuntimeError("simulated DML failure"),
    ):
        result = database.insert_dataframe_with_smart_upsert(
            base_df(), str(db), "ssa_table"
        )

    assert result is False, "upsert must fail when the DML fails"
    schema_after = set(columns(db))
    assert schema_after == schema_before, (
        f"DDL leaked: new columns {schema_after - schema_before} "
        "remained in schema after DML failure"
    )
    assert row_count(db) == 0


def test_successful_import_persists_dynamic_column_with_data(db):
    database.insert_dataframe_with_smart_upsert(base_df(), str(db), "ssa_table")

    schema_after = set(columns(db))
    assert "nome_paciente" in schema_after, (
        "sanitized dynamic column must be present after successful import"
    )
    assert row_count(db) == 1
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT nome_paciente FROM ssa_table WHERE numero_ssa='202680001'"
        ).fetchone()
    assert row is not None and row[0] == "Joao"


def test_external_connection_rollback_undoes_ddl_and_dml(db):
    """External connection: savepoint rollback undoes both ALTER and INSERT."""
    schema_before = set(columns(db))
    with sqlite3.connect(str(db)) as conn:
        conn.execute("BEGIN")
        try:
            database.insert_dataframe_with_smart_upsert(
                base_df(), conn, "ssa_table"
            )
        except Exception:
            conn.rollback()
            raise
        # Simulate caller aborting after the upsert returned
        conn.rollback()

    schema_after = set(columns(db))
    assert schema_after == schema_before, (
        "savepoint rollback must undo the ALTER TABLE"
    )
    assert row_count(db) == 0
