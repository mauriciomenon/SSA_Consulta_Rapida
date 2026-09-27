"""Verifica prazo real, prazo sem progresso e cancelamento no backup."""

import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from utils.sqlite_backup import bounded_sqlite_backup


@pytest.mark.parametrize("action", ["timeout", "stall", "cancel"])
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
kwargs = {'timeout': 0.15} if action == 'timeout' else {
    'timeout': 5.0, 'stall_timeout': 0.15}
try:
    bounded_sqlite_backup(source, target, cancel_check=cancel, **kwargs)
except expected as exc:
    assert time.monotonic() - started < 1.5
    if action == 'stall':
        assert 'sem progresso' in str(exc)
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


def test_stall_deadline_only_renews_on_new_remaining_minimum() -> None:
    from utils.sqlite_backup import _progress_checker

    current = [0.0]
    check = _progress_checker(
        timeout=100.0,
        stall_timeout=5.0,
        cancel_check=None,
        now=lambda: current[0],
    )
    check(0, 100, 200)
    current[0] = 4.0
    check(0, 60, 200)
    current[0] = 8.0
    check(0, 90, 200)
    current[0] = 9.5
    with pytest.raises(TimeoutError, match="sem progresso"):
        check(0, 50, 200)


def test_stall_deadline_renews_when_remaining_beats_minimum() -> None:
    from utils.sqlite_backup import _progress_checker

    current = [0.0]
    check = _progress_checker(
        timeout=100.0,
        stall_timeout=5.0,
        cancel_check=None,
        now=lambda: current[0],
    )
    check(0, 100, 200)
    current[0] = 4.0
    check(0, 60, 200)
    current[0] = 8.0
    check(0, 40, 200)
    current[0] = 12.0
    check(0, 40, 200)
    current[0] = 13.5
    with pytest.raises(TimeoutError, match="sem progresso"):
        check(0, 40, 200)


def test_total_deadline_caps_progressing_backup() -> None:
    from utils.sqlite_backup import _progress_checker

    current = [0.0]
    check = _progress_checker(
        timeout=5.0,
        stall_timeout=100.0,
        cancel_check=None,
        now=lambda: current[0],
    )
    check(0, 100, 200)
    current[0] = 4.0
    check(0, 10, 200)
    current[0] = 5.5
    with pytest.raises(TimeoutError, match="Prazo total"):
        check(0, 5, 200)


def test_backup_rejects_invalid_deadlines() -> None:
    with (
        closing(sqlite3.connect(":memory:")) as source,
        closing(sqlite3.connect(":memory:")) as target,
    ):
        with pytest.raises(ValueError, match="timeout"):
            bounded_sqlite_backup(source, target, timeout=0)
        with pytest.raises(ValueError, match="stall_timeout"):
            bounded_sqlite_backup(source, target, stall_timeout=-1)


def test_cancellation_at_completion_boundary_reports_interruption() -> None:
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
        with pytest.raises(InterruptedError):
            bounded_sqlite_backup(source, target, cancel_check=cancelled)
        assert checks == 2


def test_backup_reports_timeout_when_completion_passes_deadline() -> None:
    with (
        closing(sqlite3.connect(":memory:")) as source,
        closing(sqlite3.connect(":memory:")) as target,
    ):
        source.execute("CREATE TABLE dados(value TEXT)")
        source.execute("INSERT INTO dados VALUES ('registro')")
        source.commit()
        with pytest.raises(TimeoutError, match="Prazo total"):
            bounded_sqlite_backup(source, target, timeout=1e-9)
