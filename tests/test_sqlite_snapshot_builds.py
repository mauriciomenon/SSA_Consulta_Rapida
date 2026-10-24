"""CD-11 (parcial): as copias de banco dos scripts de build seguem uma regra so."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _make_db(path: Path, value: str) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE t (v TEXT)")
        conn.execute("INSERT INTO t VALUES (?)", (value,))
        conn.commit()


def _read(path: Path) -> str:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT v FROM t").fetchone()[0]


def test_snapshot_copies_consistent_db(tmp_path: Path) -> None:
    from armazenamento.sqlite_snapshot import snapshot_sqlite_file

    source, target = tmp_path / "src.db", tmp_path / "out" / "ssas.db"
    _make_db(source, "novo")
    target.parent.mkdir()

    snapshot_sqlite_file(source, target)

    assert _read(target) == "novo"
    assert sorted(p.name for p in target.parent.iterdir()) == ["ssas.db"]


def test_snapshot_refuses_target_with_sidecar(tmp_path: Path) -> None:
    from armazenamento.sqlite_snapshot import snapshot_sqlite_file

    source, target = tmp_path / "src.db", tmp_path / "ssas.db"
    _make_db(source, "novo")
    _make_db(target, "antigo")
    (tmp_path / "ssas.db-wal").write_bytes(b"")

    with pytest.raises(OSError, match="sidecar"):
        snapshot_sqlite_file(source, target)

    assert _read(target) == "antigo"
    assert not list(tmp_path.glob("ssas.db.*.tmp"))


def test_create_distribution_snapshot_keeps_target_with_sidecar(tmp_path: Path) -> None:
    from scripts import create_distribution

    source, target = tmp_path / "src.db", tmp_path / "ssas.db"
    _make_db(source, "novo")
    _make_db(target, "antigo")
    (tmp_path / "ssas.db-journal").write_bytes(b"")

    assert create_distribution._snapshot_sqlite_database(source, target) is False
    assert _read(target) == "antigo"


def test_build_scripts_use_the_shared_snapshot() -> None:
    for rel in (
        "scripts/copy_data_to_builds.py",
        "scripts/create_distribution.py",
        "launchers/build_multiplatform.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "snapshot_sqlite_file(" in text, rel
        assert ".as_uri()}?mode=ro" not in text, rel
    distribution = (ROOT / "scripts/create_distribution.py").read_text(encoding="utf-8")
    assert 'shutil.copy2(runtime_db, package_dir / "data" / "ssas.db")' not in distribution
