from __future__ import annotations

import sqlite3
from contextlib import closing

from scripts.migracao.migrar_para_unificado import backup_database
from scripts_manutencao.limpar_banco import limpar_banco


def test_limpar_banco_creates_unique_backup_and_clears_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"

    writer = sqlite3.connect(db_path)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY, nome TEXT)")
    writer.execute("INSERT INTO ssa_table (nome) VALUES ('antes')")
    writer.commit()

    try:
        assert limpar_banco() is True
    finally:
        writer.close()

    backups = list(data_dir.glob("ssas_backup_antes_limpeza_final_*.db"))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0])) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0] == 1
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0] == 0


def test_migration_backup_includes_committed_wal_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    writer = sqlite3.connect(db_path)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE probe(value TEXT)")
    writer.execute("INSERT INTO probe(value) VALUES ('from_wal')")
    writer.commit()

    try:
        backup_path = backup_database(db_path)
    finally:
        writer.close()

    with closing(sqlite3.connect(backup_path)) as conn:
        assert conn.execute("SELECT value FROM probe").fetchone() == ("from_wal",)
