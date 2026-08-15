from __future__ import annotations

from pathlib import Path

import pandas as pd

from armazenamento import database


def test_non_optimized_upsert_writes_canonical_ssa_ids(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test_non_optimized_canonical.db")
    database.initialize_database(db_path, "config/schema.sql")
    database.set_optimized_mode(False)

    df = pd.DataFrame(
        {
            "numero_ssa": ["202500777.0"],
            "derivada_de": ["202500123.0"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["non-optimized-canonical"],
        }
    )

    ok = database.insert_dataframe_with_smart_upsert(df, db_path, table_name="ssas")
    assert ok is True

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT numero_ssa, derivada_de FROM ssa_table WHERE descricao_ssa = ?",
            ("non-optimized-canonical",),
        ).fetchone()

    assert row is not None
    assert str(row[0]) == "202500777"
    assert str(row[1]) == "202500123"


def test_non_optimized_upsert_does_not_clean_letters_into_canonical_ids(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "test_non_optimized_letters.db")
    database.initialize_database(db_path, "config/schema.sql")
    database.set_optimized_mode(False)

    df = pd.DataFrame(
        {
            "numero_ssa": ["XX202500777.0YY"],
            "derivada_de": ["XX202500123.0YY"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["non-optimized-letters"],
        }
    )

    ok = database.insert_dataframe_with_smart_upsert(df, db_path, table_name="ssas")
    assert ok is True

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT numero_ssa, derivada_de FROM ssa_table WHERE descricao_ssa = ?",
            ("non-optimized-letters",),
        ).fetchone()

    assert row is not None
    assert row[0] is None
    assert row[1] is None


def test_non_optimized_upsert_does_not_clean_unicode_letters_into_canonical_ids(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "test_non_optimized_unicode_letters.db")
    database.initialize_database(db_path, "config/schema.sql")
    database.set_optimized_mode(False)

    df = pd.DataFrame(
        {
            "numero_ssa": ["Ä202500777"],
            "derivada_de": ["ß202500123"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["non-optimized-unicode-letters"],
        }
    )

    ok = database.insert_dataframe_with_smart_upsert(df, db_path, table_name="ssas")
    assert ok is True

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT numero_ssa, derivada_de FROM ssa_table WHERE descricao_ssa = ?",
            ("non-optimized-unicode-letters",),
        ).fetchone()

    assert row is not None
    assert row[0] is None
    assert row[1] is None
