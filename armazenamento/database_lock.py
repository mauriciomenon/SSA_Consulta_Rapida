"""Cross-process serialization for destructive SQLite maintenance and writes."""

from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock

_LOCK_TIMEOUT_SECONDS = 15


def _lock_path(db_path: str) -> Path:
    normalized = os.path.normcase(os.path.realpath(os.fspath(db_path)))
    digest = hashlib.sha256(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()
    lock_dir = Path(tempfile.gettempdir()) / "ssa_consulta_rapida" / "db_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"{digest}.lock"


@contextmanager
def database_writer_lock(db_path: str) -> Iterator[None]:
    """Serialize project writers for one database across threads and processes."""
    if db_path == ":memory:":
        yield
        return
    lock = FileLock(
        _lock_path(db_path),
        timeout=_LOCK_TIMEOUT_SECONDS,
        mode=0o600,
        thread_local=True,
        is_singleton=True,
    )
    with lock:
        yield
