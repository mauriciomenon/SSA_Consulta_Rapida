"""Prepare a consistent SQLite backup before replacing a database file."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse


_SIDECARS = ("-wal", "-shm", "-journal")
_JOURNAL_MODES = frozenset({"delete", "truncate", "persist", "wal", "memory", "off"})


def _rw_sqlite_uri(db_path: str) -> str:
    uri = Path(db_path).expanduser().resolve().as_uri()
    parsed = urlparse(uri)
    if parsed.netloc not in ("", "localhost"):
        uri = f"file:////{parsed.netloc}{parsed.path}"
    return f"{uri}?mode=rw"


def restore_journal_mode(db_path: str, original_mode: str) -> None:
    if original_mode not in _JOURNAL_MODES:
        raise ValueError(f"Modo de journal SQLite inesperado: {original_mode}")
    if original_mode == "delete":
        return
    with closing(sqlite3.connect(_rw_sqlite_uri(db_path), uri=True, timeout=2)) as conn:
        result = conn.execute(f"PRAGMA journal_mode={original_mode}").fetchone()
        if result is None or str(result[0]).lower() != original_mode:
            raise sqlite3.OperationalError("Falha ao restaurar modo de journal SQLite")


def snapshot_database_for_replace(db_path: str, backup_path: str) -> str:
    """Leave the primary in place and create a self-contained backup.

    SQLite must finish recovery and leave no sidecar at the primary path
    before a different database file can be published there.
    """
    if any(os.path.lexists(f"{backup_path}{suffix}") for suffix in (*_SIDECARS, "")):
        raise FileExistsError(f"Backup ja existe: {backup_path}")
    backup_created = False
    original_mode = "delete"
    mode_changed = False
    try:
        with closing(
            sqlite3.connect(_rw_sqlite_uri(db_path), uri=True, timeout=2)
        ) as source:
            if source.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise sqlite3.DatabaseError("Banco principal falhou no quick_check")
            original = source.execute("PRAGMA journal_mode").fetchone()
            if original is None:
                raise sqlite3.DatabaseError("Modo de journal SQLite indisponivel")
            original_mode = str(original[0]).lower()
            mode = source.execute("PRAGMA journal_mode=DELETE").fetchone()
            if mode is None or str(mode[0]).lower() != "delete":
                raise sqlite3.OperationalError("Banco principal nao saiu do modo WAL")
            mode_changed = original_mode != "delete"
            fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(fd)
            backup_created = True
            with closing(
                sqlite3.connect(_rw_sqlite_uri(backup_path), uri=True)
            ) as backup:
                source.backup(backup)
                if backup.execute("PRAGMA quick_check").fetchone() != ("ok",):
                    raise sqlite3.DatabaseError("Backup falhou no quick_check")
        if any(os.path.lexists(f"{db_path}{suffix}") for suffix in _SIDECARS):
            raise sqlite3.OperationalError(
                "Banco principal manteve sidecar SQLite apos checkpoint"
            )
    except BaseException as exc:
        cleanup_errors: list[str] = []
        if backup_created:
            try:
                os.unlink(backup_path)
            except OSError as cleanup_exc:
                cleanup_errors.append(f"backup: {cleanup_exc}")
        if mode_changed:
            try:
                restore_journal_mode(db_path, original_mode)
            except (OSError, sqlite3.Error) as restore_exc:
                cleanup_errors.append(f"journal: {restore_exc}")
        if cleanup_errors:
            raise OSError(
                f"Falha ao preparar snapshot e restaurar estado: {'; '.join(cleanup_errors)}"
            ) from exc
        raise
    return original_mode
