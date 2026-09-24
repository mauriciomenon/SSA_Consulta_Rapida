from __future__ import annotations

import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from armazenamento import database_publication


def _rows(path: Path) -> list[tuple[str]]:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT value FROM sample ORDER BY value").fetchall()


def test_snapshot_includes_committed_wal_and_leaves_primary_visible(tmp_path: Path) -> None:
    db = tmp_path / "primary.db"
    backup = tmp_path / "primary.db.bak"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sample(value TEXT)")
        conn.execute("INSERT INTO sample VALUES ('before')")
        conn.commit()
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sqlite3, sys\n"
            "db = sqlite3.connect(sys.argv[1])\n"
            "db.execute('PRAGMA journal_mode=WAL')\n"
            "db.execute(\"INSERT INTO sample VALUES ('wal')\")\n"
            "db.commit()\n"
            "os._exit(0)\n",
            str(db),
        ],
        check=True,
    )
    assert Path(f"{db}-wal").stat().st_size > 0

    database_publication.snapshot_database_for_replace(str(db), str(backup))

    assert _rows(db) == [("before",), ("wal",)]
    assert _rows(backup) == [("before",), ("wal",)]
    assert not any(Path(f"{db}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal"))


def test_snapshot_never_creates_missing_primary(tmp_path: Path) -> None:
    db = tmp_path / "missing.db"
    backup = tmp_path / "backup.db"

    with pytest.raises(sqlite3.OperationalError):
        database_publication.snapshot_database_for_replace(str(db), str(backup))

    assert not db.exists()
    assert not backup.exists()


def test_snapshot_preserves_existing_backup(tmp_path: Path) -> None:
    db = tmp_path / "primary.db"
    backup = tmp_path / "backup.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sample(value TEXT)")
        conn.commit()
    backup.write_bytes(b"backup existente")

    with pytest.raises(FileExistsError):
        database_publication.snapshot_database_for_replace(str(db), str(backup))

    assert backup.read_bytes() == b"backup existente"
    assert db.exists()


def test_snapshot_refuses_active_wal_reader(tmp_path: Path) -> None:
    db = tmp_path / "primary.db"
    backup = tmp_path / "backup.db"
    with closing(sqlite3.connect(db)) as setup:
        setup.execute("PRAGMA journal_mode=WAL")
        setup.execute("CREATE TABLE sample(value TEXT)")
        setup.execute("INSERT INTO sample VALUES ('before')")
        setup.commit()
        with closing(sqlite3.connect(db)) as reader:
            reader.execute("BEGIN")
            assert reader.execute("SELECT value FROM sample").fetchall() == [
                ("before",)
            ]

            with pytest.raises(sqlite3.OperationalError):
                database_publication.snapshot_database_for_replace(str(db), str(backup))

            assert db.exists()
            assert not backup.exists()
            assert reader.execute("SELECT value FROM sample").fetchall() == [
                ("before",)
            ]


def test_snapshot_removes_only_its_partial_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "primary.db"
    backup = tmp_path / "backup.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sample(value TEXT)")
        conn.execute("INSERT INTO sample VALUES ('before')")
        conn.commit()
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    real_connect = sqlite3.connect

    def _fail_backup_connect(path, *args, **kwargs):
        if str(backup) in str(path):
            raise sqlite3.OperationalError("simulated backup failure")
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(database_publication.sqlite3, "connect", _fail_backup_connect)

    with pytest.raises(sqlite3.OperationalError, match="simulated backup failure"):
        database_publication.snapshot_database_for_replace(str(db), str(backup))

    assert db.exists()
    assert not backup.exists()
    assert _rows(db) == [("before",)]
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone() == ("wal",)
