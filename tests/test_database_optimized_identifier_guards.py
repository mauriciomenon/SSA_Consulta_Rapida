from __future__ import annotations

import sqlite3

from armazenamento.database_optimized import _has_referencing_foreign_keys


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
