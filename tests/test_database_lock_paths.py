from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from armazenamento import database_lock


@pytest.fixture
def lock_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(database_lock.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path / "ssa_consulta_rapida"


@pytest.mark.skipif(os.name != "posix", reason="Permissoes POSIX")
def test_lock_directories_are_private_and_lock_remains_reentrant(lock_root: Path) -> None:
    with database_lock.database_writer_lock("example.db", timeout=0):
        with database_lock.database_writer_lock("example.db", timeout=0):
            assert stat.S_IMODE(lock_root.stat().st_mode) == 0o700
            assert stat.S_IMODE((lock_root / "db_locks").stat().st_mode) == 0o700


@pytest.mark.parametrize("level", ("root", "locks"))
def test_lock_refuses_symlink_directory(lock_root: Path, level: str) -> None:
    destination = lock_root.parent / "external"
    destination.mkdir()
    symlink = lock_root
    if level == "locks":
        lock_root.mkdir(mode=0o700)
        symlink = lock_root / "db_locks"
    try:
        symlink.symlink_to(destination, target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows sem privilegio para criar symlink")
        raise

    with pytest.raises(PermissionError, match="Diretorio de locks inseguro"):
        database_lock._lock_path("example.db")
    assert not list(destination.iterdir())


@pytest.mark.skipif(os.name != "posix", reason="Permissoes POSIX")
@pytest.mark.parametrize("level", ("root", "locks"))
def test_lock_refuses_directory_writable_by_others(lock_root: Path, level: str) -> None:
    lock_root.mkdir(mode=0o700)
    directory = lock_root if level == "root" else lock_root / "db_locks"
    if level == "locks":
        directory.mkdir(mode=0o700)
    directory.chmod(0o777)
    with pytest.raises(PermissionError, match="Diretorio de locks inseguro"):
        database_lock._lock_path("example.db")
    assert stat.S_IMODE(directory.stat().st_mode) == 0o777


@pytest.mark.skipif(os.name != "posix", reason="Permissoes POSIX")
def test_lock_accepts_existing_owned_directory_without_other_write_access(lock_root: Path) -> None:
    lock_root.mkdir(mode=0o755)
    (lock_root / "db_locks").mkdir(mode=0o755)
    first = database_lock._lock_path("example.db")
    assert first == database_lock._lock_path(os.path.abspath("example.db"))
