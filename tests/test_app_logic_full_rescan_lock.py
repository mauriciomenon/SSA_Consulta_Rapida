from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from core.import_database_rotation import (
    promote_full_rescan_candidate,
    rotate_preexisting_database_for_full_rescan,
)
from core.import_errors import DatabaseError


def _build_wal_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE ssa_table(id INTEGER PRIMARY KEY, value TEXT)")
        conn.executemany(
            "INSERT INTO ssa_table(value) VALUES (?)",
            [("a",), ("b",)],
        )
        conn.commit()
    finally:
        conn.close()


def _build_value_db(db_path: Path, value: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE ssa_table(id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO ssa_table(value) VALUES (?)", (value,))
        conn.commit()
    finally:
        conn.close()


def _read_value(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT value FROM ssa_table").fetchone()
    finally:
        conn.close()
    assert row is not None
    return str(row[0])


def test_rotate_preexisting_database_for_full_rescan_without_external_lock(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    _build_wal_db(db_path)

    rotate_preexisting_database_for_full_rescan(str(db_path))

    backups = sorted(
        p
        for p in tmp_path.glob("ssas.db.full_rescan_backup_*")
        if not p.name.endswith(("-wal", "-shm"))
    )
    assert len(backups) == 1
    assert not db_path.exists()

    conn = sqlite3.connect(backups[0])
    try:
        row = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()
    finally:
        conn.close()
    assert row is not None
    assert int(row[0]) == 2


def test_rotate_preexisting_database_for_full_rescan_moves_existing_sidecars(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    _build_wal_db(db_path)

    wal_sidecar = Path(f"{db_path}-wal")
    shm_sidecar = Path(f"{db_path}-shm")
    wal_sidecar.write_bytes(b"")
    shm_sidecar.write_bytes(b"")

    rotate_preexisting_database_for_full_rescan(str(db_path))

    backups = sorted(
        p
        for p in tmp_path.glob("ssas.db.full_rescan_backup_*")
        if not p.name.endswith(("-wal", "-shm"))
    )
    assert len(backups) == 1
    backup_path = backups[0]

    assert not wal_sidecar.exists()
    assert not shm_sidecar.exists()
    assert Path(f"{backup_path}-wal").exists()
    assert Path(f"{backup_path}-shm").exists()


def test_promote_full_rescan_candidate_restores_primary_when_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    primary_db = tmp_path / "ssas.db"
    candidate_db = tmp_path / "ssas.db.full_rescan_candidate_test"
    _build_value_db(primary_db, "primary_old")
    _build_value_db(candidate_db, "candidate_new")

    def _replace_with_candidate_failure(source: str, target: str) -> None:
        if Path(source) == candidate_db and Path(target) == primary_db:
            raise PermissionError("simulated promotion failure")
        os.replace(source, target)

    monkeypatch.setattr(
        "core.import_database_rotation.replace_sqlite_file_with_retry",
        _replace_with_candidate_failure,
    )

    with pytest.raises(DatabaseError):
        promote_full_rescan_candidate(str(candidate_db), str(primary_db))

    assert primary_db.exists()
    assert _read_value(primary_db) == "primary_old"
    assert candidate_db.exists()
    assert _read_value(candidate_db) == "candidate_new"
