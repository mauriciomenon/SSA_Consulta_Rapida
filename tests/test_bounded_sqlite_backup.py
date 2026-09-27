"""Verifica prazo real e cancelamento com SQLite bloqueado."""

import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from utils.sqlite_backup import bounded_sqlite_backup


@pytest.mark.parametrize("action", ["timeout", "cancel"])
@pytest.mark.parametrize("locked_side", ["source", "target"])
def test_locked_backup_terminates_and_restores_connection_settings(
    tmp_path: Path, action: str, locked_side: str
) -> None:
    script = r'''
import sqlite3
import sys
import time
from pathlib import Path
from utils.sqlite_backup import bounded_sqlite_backup

root, action, locked_side = sys.argv[1:]
paths = {name: Path(root) / (name + '.db') for name in ('source', 'target')}
source = sqlite3.connect(paths['source'], timeout=5)
target = sqlite3.connect(paths['target'], timeout=3)
source.execute('CREATE TABLE dados(value TEXT)')
source.execute("INSERT INTO dados VALUES ('original')")
source.commit()
locker = sqlite3.connect(paths[locked_side])
locker.execute('BEGIN EXCLUSIVE')
started = time.monotonic()
cancel = (lambda: time.monotonic() - started > 0.08) if action == 'cancel' else None
expected = InterruptedError if action == 'cancel' else TimeoutError
try:
    bounded_sqlite_backup(source, target, timeout=0.15, cancel_check=cancel)
except expected:
    assert time.monotonic() - started < 1.5
else:
    raise AssertionError('backup deveria interromper')
assert source.execute('PRAGMA busy_timeout').fetchone() == (5000,)
assert target.execute('PRAGMA busy_timeout').fetchone() == (3000,)
locker.rollback()
locker.close()
bounded_sqlite_backup(source, target, timeout=1)
assert target.execute('SELECT value FROM dados').fetchall() == [('original',)]
source.close()
target.close()
'''
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), action, locked_side],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_backup_preserves_committed_wal_content(tmp_path: Path) -> None:
    with closing(sqlite3.connect(tmp_path / "source.db")) as source:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("CREATE TABLE dados(value TEXT)")
        source.execute("INSERT INTO dados VALUES ('preservado')")
        source.commit()
        with closing(sqlite3.connect(tmp_path / "copy.db")) as target:
            bounded_sqlite_backup(source, target)
            assert target.execute("SELECT value FROM dados").fetchall() == [
                ("preservado",)
            ]
            assert target.execute("PRAGMA quick_check").fetchone() == ("ok",)


def test_completed_backup_does_not_report_late_cancellation() -> None:
    checks = 0

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    with (
        closing(sqlite3.connect(":memory:")) as source,
        closing(sqlite3.connect(":memory:")) as target,
    ):
        for connection, value in ((source, "novo"), (target, "anterior")):
            connection.execute("CREATE TABLE dados(value TEXT)")
            connection.execute("INSERT INTO dados VALUES (?)", (value,))
            connection.commit()
        bounded_sqlite_backup(source, target, cancel_check=cancelled)
        assert target.execute("SELECT value FROM dados").fetchall() == [("novo",)]
        assert checks == 1
