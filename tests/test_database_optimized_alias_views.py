# tests/test_database_optimized_alias_views.py
from __future__ import annotations

from pathlib import Path

import pandas as pd

from armazenamento import database
from armazenamento.database_optimized import disable_optimized_import, enable_optimized_import


def test_optimized_insert_resolves_view_alias_ssas(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")

    database.initialize_database(db_path, "config/schema.sql")

    enable_optimized_import()
    try:
        df = pd.DataFrame(
            {
                "numero_ssa": ["123456789"],
                "data_cadastro": [pd.Timestamp("2025-01-01")],
                "situacao": ["TESTE"],
                "descricao_ssa": ["ok"],
            }
        )

        ok = database.insert_dataframe_with_smart_upsert(df, db_path, table_name="ssas")
        assert ok is True

        with database.get_db_connection(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        assert count == 1
    finally:
        disable_optimized_import()


def test_optimized_insert_normalizes_decimal_ssa_artifacts(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test_decimal.db")
    database.initialize_database(db_path, "config/schema.sql")

    enable_optimized_import()
    try:
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500777.0"],
                "derivada_de": ["202500123.0"],
                "data_cadastro": [pd.Timestamp("2025-01-01")],
                "situacao": ["TESTE"],
                "descricao_ssa": ["decimal-input"],
            }
        )

        ok = database.insert_dataframe_with_smart_upsert(df, db_path, table_name="ssas")
        assert ok is True

        with database.get_db_connection(db_path) as conn:
            row = conn.execute(
                "SELECT numero_ssa, derivada_de FROM ssa_table WHERE descricao_ssa = ?",
                ("decimal-input",),
            ).fetchone()

        assert row is not None
        assert row[0] == "202500777"
        assert row[1] == "202500123"
    finally:
        disable_optimized_import()
