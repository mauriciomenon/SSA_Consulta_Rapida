from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime

import pytest

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


def test_limpar_banco_keeps_rows_when_backup_fails(tmp_path, monkeypatch, caplog):
    from scripts_manutencao import limpar_banco as module

    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO ssa_table DEFAULT VALUES")
        conn.commit()

    def fail_backup(*_args):
        raise OSError("backup unavailable")

    monkeypatch.setattr(module, "create_sqlite_backup", fail_backup)
    assert limpar_banco() is False
    assert "backup unavailable" in caplog.text
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (1,)


def test_limpar_banco_keeps_rows_and_existing_backup_on_collision(
    tmp_path, monkeypatch
):
    from scripts_manutencao import limpar_banco as module

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 2, 3, 4, 5, 123456)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "datetime", FixedDatetime)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO ssa_table DEFAULT VALUES")
        conn.commit()
    backup_path = data_dir / "ssas_backup_antes_limpeza_final_20260102_030405_123456.db"
    backup_path.write_bytes(b"existing backup")

    assert limpar_banco() is False
    assert backup_path.read_bytes() == b"existing backup"
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (1,)


def test_limpar_banco_reports_vacuum_failure_after_committed_delete(
    tmp_path, monkeypatch: pytest.MonkeyPatch, caplog
):
    from scripts_manutencao import limpar_banco as module

    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO ssa_table DEFAULT VALUES")
        conn.commit()

    original_connect = sqlite3.connect

    class FailingVacuumCursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            if sql == "VACUUM":
                raise sqlite3.OperationalError("vacuum unavailable")
            return super().execute(sql, parameters)

    class FailingVacuumConnection(sqlite3.Connection):
        def cursor(self, factory=FailingVacuumCursor):
            return super().cursor(factory)

    with monkeypatch.context() as patcher:
        patcher.setattr(
            module.sqlite3,
            "connect",
            lambda *args, **kwargs: original_connect(
                *args, factory=FailingVacuumConnection, **kwargs
            ),
        )
        assert limpar_banco() is True

    assert "Registros removidos; otimizacao VACUUM pendente" in caplog.text
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (0,)
    backups = list(data_dir.glob("ssas_backup_antes_limpeza_final_*.db"))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0])) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (1,)
