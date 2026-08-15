from __future__ import annotations

import sqlite3

from scripts_manutencao.limpar_banco import limpar_banco


def test_limpar_banco_creates_unique_backup_and_clears_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY, nome TEXT)")
        conn.execute("INSERT INTO ssa_table (nome) VALUES ('antes')")
        conn.commit()

    assert limpar_banco() is True

    backups = list(data_dir.glob("ssas_backup_antes_limpeza_final_*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0] == 0
