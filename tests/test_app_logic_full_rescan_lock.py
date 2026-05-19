from __future__ import annotations

import sqlite3
from pathlib import Path

from core.app_logic import _rotate_preexisting_database_for_full_rescan


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


def test_rotate_preexisting_database_for_full_rescan_without_external_lock(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    _build_wal_db(db_path)

    _rotate_preexisting_database_for_full_rescan(str(db_path))

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

    _rotate_preexisting_database_for_full_rescan(str(db_path))

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
