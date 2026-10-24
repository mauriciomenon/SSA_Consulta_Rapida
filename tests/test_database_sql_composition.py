"""BL-25: colunas lidas por pragma_table_info(?) parametrizado, sem SQL montado."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from armazenamento import database

ROOT = Path(__file__).resolve().parent.parent


def _make_db(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT)")
        conn.execute("CREATE VIEW ssas AS SELECT numero_ssa, situacao FROM ssa_table")
        conn.commit()


def test_explicit_select_lists_table_and_view_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "x.db"
    _make_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        assert (
            database._build_explicit_select_all_query(conn, "ssa_table")
            == 'SELECT "numero_ssa", "situacao" FROM "ssa_table"'
        )
        assert (
            database._build_explicit_select_all_query(conn, "ssas")
            == 'SELECT "numero_ssa", "situacao" FROM "ssas"'
        )


def test_ensure_column_exists_adds_once(tmp_path: Path) -> None:
    db_path = tmp_path / "x.db"
    _make_db(db_path)

    assert database.ensure_column_exists(str(db_path), "ssa_table", "nova", "TEXT") is True
    assert database.ensure_column_exists(str(db_path), "ssa_table", "nova", "TEXT") is False
    with closing(sqlite3.connect(db_path)) as conn:
        names = [row[1] for row in conn.execute("PRAGMA table_info(ssa_table)")]
    assert names == ["numero_ssa", "situacao", "nova"]


def test_no_formatted_table_info_pragma_left() -> None:
    source = (ROOT / "armazenamento" / "database.py").read_text(encoding="utf-8")
    assert 'f"PRAGMA table_info(' not in source
