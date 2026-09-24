import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from filelock import Timeout

from scripts.migracao import migrar_para_unificado


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schema = tmp_path / "schema_unified.sql"
    schema.write_text(
        "CREATE TABLE IF NOT EXISTS ssa_table (\n"
        "    id INTEGER PRIMARY KEY,\n"
        "    extra TEXT\n"
        ");\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(migrar_para_unificado, "SCHEMA_PATH", schema)
    db = tmp_path / "ssas.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE ssa_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO ssa_table VALUES (1)")
        conn.commit()
    os.chmod(db, 0o600)
    return db


def test_migration_backup_is_private_and_contains_previous_schema(migration_db, tmp_path):
    migrar_para_unificado.migrate(migration_db)

    backups = list((tmp_path / "data").glob("ssas.db.backup_before_unified_*"))
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o600
    with closing(sqlite3.connect(backups[0])) as backup:
        assert [row[1] for row in backup.execute("PRAGMA table_info(ssa_table)")] == [
            "id"
        ]
        assert backup.execute("SELECT id FROM ssa_table").fetchall() == [(1,)]
    with closing(sqlite3.connect(migration_db)) as current:
        assert [row[1] for row in current.execute("PRAGMA table_info(ssa_table)")] == [
            "id",
            "extra",
        ]


def test_migration_refuses_concurrent_project_writer(migration_db, tmp_path):
    script = (
        "from armazenamento.database_lock import database_writer_lock\n"
        "with database_writer_lock(__import__('sys').argv[1]):\n"
        " print('ready', flush=True)\n"
        " input()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(migration_db)],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "ready"
        with pytest.raises(Timeout):
            migrar_para_unificado.migrate(migration_db)
        assert not (tmp_path / "data").exists()
        with closing(sqlite3.connect(migration_db)) as conn:
            assert [row[1] for row in conn.execute("PRAGMA table_info(ssa_table)")] == [
                "id"
            ]
    finally:
        assert process.stdin is not None
        process.stdin.write("\n")
        process.stdin.flush()
        process.wait(timeout=5)
