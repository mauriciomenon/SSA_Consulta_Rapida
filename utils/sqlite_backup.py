"""Backup SQLite com prazo e cancelamento entre passos de copia."""

from __future__ import annotations

import math
import sqlite3
import time
from collections.abc import Callable

_SQLITE_DONE = 101


def bounded_sqlite_backup(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    *,
    timeout: float = 30.0,
    cancel_check: Callable[[], bool] | None = None,
    pages: int = 128,
) -> None:
    """Limita repeticoes BUSY/LOCKED; preserva o busy_timeout da conexao."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise TimeoutError("Prazo do backup SQLite esgotado")
    deadline = time.monotonic() + timeout

    def check_progress(_status: int, _remaining: int, _total: int) -> None:
        if _status == _SQLITE_DONE:
            return
        if cancel_check is not None and cancel_check():
            raise InterruptedError("Backup SQLite cancelado")
        if time.monotonic() >= deadline:
            raise TimeoutError("Prazo do backup SQLite esgotado")

    check_progress(0, 0, 0)
    busy_timeout = int(source.execute("PRAGMA busy_timeout").fetchone()[0])
    target_timeout = int(target.execute("PRAGMA busy_timeout").fetchone()[0])
    source.execute("PRAGMA busy_timeout=0")
    try:
        target.execute("PRAGMA busy_timeout=0")
        source.backup(
            target,
            pages=min(pages, 128) if pages > 0 else 128,
            progress=check_progress,
            sleep=0.01,
        )
    finally:
        source.execute(f"PRAGMA busy_timeout={busy_timeout}")
        target.execute(f"PRAGMA busy_timeout={target_timeout}")
