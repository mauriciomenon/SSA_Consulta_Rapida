from __future__ import annotations

import os
import sqlite3

from armazenamento.database import verify_database_integrity


def test_verify_database_integrity_rejects_injection_like_table_identifier(tmp_path) -> None:
    db_path = os.path.join(tmp_path, "invalid_table_identifier.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    report = verify_database_integrity(
        db_path,
        table_name='ssa_table" WHERE 1=1 --',
    )

    assert report["is_valid"] is False
    assert "Invalid SQL identifier" in str(report["issues"])
    assert report["database_accessible"] is False
