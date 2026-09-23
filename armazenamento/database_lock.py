"""Cross-process serialization for destructive SQLite maintenance and writes."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock

_LOCK_TIMEOUT_SECONDS = 15


def _lock_path(db_path: str) -> Path:
    normalized = os.path.normcase(os.path.realpath(os.fspath(db_path)))
    digest = hashlib.sha256(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()
    app_dir = Path(tempfile.gettempdir()) / "ssa_consulta_rapida"
    lock_dir = app_dir / "db_locks"
    for directory in (app_dir, lock_dir):
        directory.mkdir(mode=0o700, exist_ok=True)
        metadata = directory.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or (
                os.name == "nt"
                and metadata.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            )
            or (
                os.name == "posix"
                and (metadata.st_uid != os.getuid() or metadata.st_mode & 0o022)
            )
        ):
            raise PermissionError(f"Diretorio de locks inseguro: {directory}")
    return lock_dir / f"{digest}.lock"


@contextmanager
def database_writer_lock(
    db_path: str, *, timeout: float | None = None
) -> Iterator[None]:
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
    with lock.acquire(timeout=timeout):
        yield
