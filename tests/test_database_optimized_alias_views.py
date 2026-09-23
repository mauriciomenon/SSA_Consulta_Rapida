# tests/test_database_optimized_alias_views.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from armazenamento import database
from armazenamento.database_optimized import (
    disable_optimized_import,
    enable_optimized_import,
    insert_dataframe_optimized,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_optimized_insert_resolves_view_alias_ssas(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    schema_path = _get_project_root() / "config" / "schema.sql"
    if not schema_path.exists():
        pytest.fail(f"Schema ausente para setup de teste: {schema_path}")

    init_ok = database.initialize_database(db_path, str(schema_path))
    assert init_ok is True

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
        Path(db_path).unlink(missing_ok=True)


def test_optimized_insert_normalizes_decimal_ssa_artifacts(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test_decimal.db")
    schema_path = _get_project_root() / "config" / "schema.sql"
    if not schema_path.exists():
        pytest.fail(f"Schema ausente para setup de teste: {schema_path}")
    init_ok = database.initialize_database(db_path, str(schema_path))
    assert init_ok is True

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
        assert str(row[0]) == "202500777"
        assert str(row[1]) == "202500123"
    finally:
        disable_optimized_import()
        Path(db_path).unlink(missing_ok=True)


def test_optimized_insert_resolves_legacy_alias_without_view_object(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "canonical_only.db")

    with database.get_db_connection(db_path) as conn:
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

    df = pd.DataFrame(
        {
            "numero_ssa": ["202500111"],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["alias-sem-view"],
        }
    )

    assert insert_dataframe_optimized(df, db_path, table_name="ssas") is True

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa FROM ssa_table WHERE numero_ssa = ?",
            ("202500111",),
        ).fetchone()
        alias_table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ssas'"
        ).fetchone()[0]

    assert row == ("alias-sem-view",)
    assert alias_table_count == 0


def test_optimized_canonical_request_reuses_single_legacy_table(tmp_path: Path) -> None:
    db_path = str(tmp_path / "legacy_only.db")
    with database.get_db_connection(db_path) as conn:
        conn.execute(
            "CREATE TABLE ssas (numero_ssa TEXT PRIMARY KEY, data_cadastro TEXT, "
            "situacao TEXT, descricao_ssa TEXT)"
        )
        conn.commit()
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500112"],
            "data_cadastro": ["2025-01-01 00:00:00"],
            "situacao": ["STE"],
            "descricao_ssa": ["legacy-target"],
        }
    )

    assert insert_dataframe_optimized(df, db_path, table_name="ssa_table") is True

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT descricao_ssa FROM ssas WHERE numero_ssa='202500112'"
        ).fetchone()
        canonical_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ssa_table'"
        ).fetchone()
    assert row == ("legacy-target",)
    assert canonical_exists is None


def test_optimized_insert_same_date_does_not_downgrade_situacao(tmp_path: Path) -> None:
    db_path = str(tmp_path / "same_date_no_downgrade.db")
    schema_path = _get_project_root() / "config" / "schema.sql"
    if not schema_path.exists():
        pytest.fail(f"Schema ausente para setup de teste: {schema_path}")

    init_ok = database.initialize_database(db_path, str(schema_path))
    assert init_ok is True

    newer_or_equal = pd.DataFrame(
        {
            "numero_ssa": ["202600654"],
            "data_cadastro": ["2026-01-16 00:00:00"],
            "situacao": ["STE"],
            "descricao_ssa": ["estado terminal"],
        }
    )
    older_semantic = pd.DataFrame(
        {
            "numero_ssa": ["202600654"],
            "data_cadastro": ["2026-01-16 00:00:00"],
            "situacao": ["ADM"],
            "descricao_ssa": ["estado antigo"],
        }
    )

    assert (
        insert_dataframe_optimized(newer_or_equal, db_path, table_name="ssas") is True
    )
    assert (
        insert_dataframe_optimized(older_semantic, db_path, table_name="ssas") is True
    )

    with database.get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT situacao FROM ssa_table WHERE numero_ssa = ?",
            ("202600654",),
        ).fetchone()
    assert row is not None
    assert row[0] == "STE"
