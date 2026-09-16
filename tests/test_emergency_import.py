from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

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
