from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from contextlib import closing
from pathlib import Path

import pytest
from filelock import Timeout

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "utils" / "fallback" / "emergency_import.py"
_SPEC = importlib.util.spec_from_file_location("emergency_import", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_module)
emergency_import = _module.emergency_import


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.execute("INSERT INTO ssa_table VALUES ('202600001')")
        conn.commit()
    finally:
        conn.close()


def test_force_archives_journal_and_wal_sidecars(tmp_path: Path) -> None:
    """Um -journal quente nao pode ficar no caminho: seria aplicado pelo
    SQLite sobre o banco recem-criado."""
    db = tmp_path / "x.db"
    _make_db(db)
    journal = Path(f"{db}-journal")
    journal.write_bytes(b"journal quente")
    wal = Path(f"{db}-wal")
    wal.write_bytes(b"wal pendente")

    assert emergency_import(str(db), force=True) is True

    names = {p.name for p in tmp_path.glob("x.db.bak-*")}
    assert any(name.endswith("-journal") for name in names)
    assert any(name.endswith("-wal") for name in names)
    assert not journal.exists()
    assert not wal.exists()
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()
    assert rows is not None


@pytest.mark.parametrize("relative", [False, True])
def test_force_preserves_database_symlink_and_archives_real_sidecars(
    tmp_path: Path, relative: bool
) -> None:
    target = tmp_path / "real.db"
    _make_db(target)
    alias = tmp_path / "alias.db"
    try:
        alias.symlink_to(target.name if relative else target)
    except OSError as exc:
        if os.name == "nt" and exc.winerror == 1314:
            pytest.skip("Criacao de symlink exige privilegio no Windows")
        raise
    subprocess.run(
        [sys.executable, "-c", """
import os
import sqlite3
import sys
conn = sqlite3.connect(sys.argv[1])
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA wal_autocheckpoint=0')
conn.execute("INSERT INTO ssa_table VALUES ('202600002')")
conn.commit()
os._exit(0)
""", str(target)],
        check=True,
    )
    wal = Path(f"{target}-wal")
    original_wal = wal.read_bytes()

    assert emergency_import(str(alias), force=True) is True

    assert alias.is_symlink()
    assert alias.resolve() == target
    backup = next(
        path for path in tmp_path.glob("real.db.bak-*")
        if not path.name.endswith(("-wal", "-shm", "-journal"))
    )
    assert backup.is_file() and not backup.is_symlink()
    assert Path(f"{backup}-wal").read_bytes() == original_wal
    assert not list(tmp_path.glob("alias.db.bak-*"))
    with closing(sqlite3.connect(backup)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",), ("202600002",)
        ]
    with closing(sqlite3.connect(alias)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (2,)


def test_force_rolls_back_moved_sidecars_when_db_move_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se o move do .db falha apos mover sidecars, os moves parciais sao
    revertidos — o banco antigo nao pode ficar sem seu WAL."""
    db = tmp_path / "x.db"
    _make_db(db)
    wal = Path(f"{db}-wal")
    wal.write_bytes(b"wal pendente")

    real_replace = os.replace

    def _fail_on_db_move(src, dst):
        if src == str(db):
            raise OSError("simulated archive failure")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _fail_on_db_move)

    with pytest.raises(OSError):
        emergency_import(str(db), force=True)

    assert db.exists()
    assert wal.exists() and wal.read_bytes() == b"wal pendente"
    assert not list(tmp_path.glob("x.db.bak-*"))


def test_force_refuses_concurrent_project_writer(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    _make_db(db)
    script = (
        "from armazenamento.database_lock import database_writer_lock\n"
        "with database_writer_lock(__import__('sys').argv[1]):\n"
        " print('ready', flush=True)\n"
        " input()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(db)],
        cwd=str(_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "ready"
        with pytest.raises(Timeout):
            emergency_import(str(db), force=True)
        with closing(sqlite3.connect(db)) as conn:
            assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
                ("202600001",)
            ]
        assert not list(tmp_path.glob("x.db.bak-*"))
    finally:
        assert process.stdin is not None
        process.stdin.write("\n")
        process.stdin.flush()
        process.wait(timeout=5)


def test_force_keeps_original_when_candidate_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "x.db"
    _make_db(db)

    def _fail_creation(cursor):
        raise OSError("simulated creation failure")

    monkeypatch.setattr(_module, "create_basic_table", _fail_creation)

    assert emergency_import(str(db), force=True) is False

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]
    assert not list(tmp_path.glob("x.db.bak-*"))
    assert not list(tmp_path.glob(".x.db.tmp-*"))


def test_force_restores_original_when_candidate_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "x.db"
    _make_db(db)
    wal = Path(f"{db}-wal")
    wal.write_bytes(b"wal pendente")
    real_replace = os.replace

    def _fail_candidate_publish(src, dst):
        if dst == str(db) and Path(src).name.startswith(".x.db.tmp-"):
            raise OSError("simulated publish failure")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _fail_candidate_publish)

    with pytest.raises(OSError, match="Falha ao publicar banco de teste"):
        emergency_import(str(db), force=True)

    assert db.exists()
    assert wal.read_bytes() == b"wal pendente"
    assert not list(tmp_path.glob("x.db.bak-*"))
    assert not list(tmp_path.glob(".x.db.tmp-*"))


def test_force_preserves_preexisting_backup_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "x.db"
    _make_db(db)

    class FixedDatetime:
        @staticmethod
        def now():
            return datetime(2026, 9, 24, 7, 45, 0, 123456)

    monkeypatch.setattr(_module, "datetime", FixedDatetime)
    backup = tmp_path / "x.db.bak-20260924_074500_123456"
    backup.write_bytes(b"backup preexistente")

    with pytest.raises(OSError, match="Backup de emergencia ja existe"):
        emergency_import(str(db), force=True)

    assert backup.read_bytes() == b"backup preexistente"
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]
    assert not list(tmp_path.glob(".x.db.tmp-*"))


def test_cli_exits_nonzero_when_db_exists_without_force(tmp_path: Path) -> None:
    """A recusa sem --force tem que sair com codigo != 0 para que
    automacoes nao tratem a falha como sucesso."""
    db = tmp_path / "x.db"
    db.write_bytes(b"db existente")

    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--db", str(db)],
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    assert db.read_bytes() == b"db existente"
    assert not list(tmp_path.glob("x.db.bak-*"))
