from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import threading
from argparse import Namespace
from contextlib import closing
from pathlib import Path

import pytest

from armazenamento.database_integrity import create_sqlite_backup


@pytest.mark.skipif(os.name != "posix", reason="Permissoes POSIX")
@pytest.mark.parametrize("operation", ["reset", "clear", "cleanup", "snapshot"])
@pytest.mark.parametrize("source_mode", [0o600, 0o640])
def test_backup_is_private_before_sqlite_opens_it(
    tmp_path: Path, operation: str, source_mode: int
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    source = data / "ssas.db"
    with closing(sqlite3.connect(source)) as conn:
        conn.executescript(
            "CREATE TABLE ssa_table(numero_ssa TEXT);"
            "INSERT INTO ssa_table VALUES ('202600001');"
            "CREATE TABLE ssas(id INTEGER PRIMARY KEY, numero_ssa TEXT, "
            "descricao_ssa TEXT, situacao TEXT, semana_cadastro TEXT);"
            "INSERT INTO ssas VALUES(1, '202600001', 'original', 'ASE', '202601');"
        )
    source.chmod(source_mode)
    script = r'''
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
operation = sys.argv[2]
checked = []

def inspect_backup(event, args):
    if event != "sqlite3.connect":
        return
    candidate = Path(args[0])
    if "backup" not in candidate.name and candidate.suffix != ".tmp":
        return
    assert candidate.is_file(), "Backup aberto sem precriacao privada"
    assert stat.S_IMODE(candidate.stat().st_mode) == 0o600
    checked.append(candidate)

sys.addaudithook(inspect_backup)
os.umask(0o022)
if operation == "reset":
    from scripts_manutencao.gerenciar_banco import reset_database
    reset_database()
elif operation == "clear":
    from scripts_manutencao.limpar_banco import limpar_banco
    assert limpar_banco()
elif operation == "cleanup":
    from scripts_manutencao.cleanup_emergency import emergency_cleanup
    assert emergency_cleanup() == (1, 1)
else:
    from armazenamento.database_integrity import _create_integrity_snapshot
    assert _create_integrity_snapshot("data/ssas.db", force=True)
assert checked
'''
    result = subprocess.run(
        [sys.executable, "-c", script, str(Path(__file__).resolve().parents[1]), operation],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    backups = [
        path for path in data.rglob("*")
        if path.is_file() and path.name != "ssas.db"
    ]
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == source_mode
    with closing(sqlite3.connect(backups[0])) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]


@pytest.mark.skipif(os.name != "posix", reason="Permissoes POSIX")
def test_backup_copies_read_only_source_with_escaped_filename(tmp_path: Path) -> None:
    source = tmp_path / "origem #?%.db"
    destination = tmp_path / "backup.db"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE probe(value TEXT)")
        conn.execute("INSERT INTO probe VALUES ('preservado')")
        conn.commit()
    source.chmod(0o400)

    create_sqlite_backup(source, destination)

    assert destination.stat().st_mode & 0o777 == 0o400
    with closing(sqlite3.connect(destination)) as conn:
        assert conn.execute("SELECT value FROM probe").fetchone() == ("preservado",)


@pytest.mark.parametrize("is_symlink", [False, True])
def test_backup_never_overwrites_existing_destination(
    tmp_path: Path, is_symlink: bool
) -> None:
    source = tmp_path / "source.db"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE probe(value TEXT)")
    existing = tmp_path / "existing.db"
    existing.write_bytes(b"conteudo anterior")
    destination = tmp_path / "backup.db"
    if is_symlink:
        try:
            destination.symlink_to(existing)
        except OSError as exc:
            if os.name == "nt" and exc.winerror == 1314:
                pytest.skip("Criacao de symlink exige privilegio no Windows")
            raise
    else:
        destination.write_bytes(b"backup anterior")

    with pytest.raises(FileExistsError):
        create_sqlite_backup(source, destination)

    assert existing.read_bytes() == b"conteudo anterior"
    assert destination.is_symlink() is is_symlink
    assert destination.read_bytes() == (
        b"conteudo anterior" if is_symlink else b"backup anterior"
    )


def test_backup_removes_only_its_partial_file_on_invalid_source(tmp_path: Path) -> None:
    source = tmp_path / "invalid.db"
    source.write_bytes(b"nao e sqlite")
    destination = tmp_path / "backup.db"

    with pytest.raises(sqlite3.DatabaseError):
        create_sqlite_backup(source, destination)

    assert source.read_bytes() == b"nao e sqlite"
    assert not destination.exists()


def test_maintenance_reset_preserves_backup_and_live_wal_reader(tmp_path: Path) -> None:
    from scripts_manutencao.gerenciar_banco import reset_database

    db = tmp_path / "ssas.db"
    with closing(sqlite3.connect(db)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE ssa_table(numero_ssa TEXT)")
        writer.execute("INSERT INTO ssa_table VALUES ('original')")
        writer.commit()

        reset_database(str(db))

        assert db.exists()
        assert Path(f"{db}-wal").exists()
        assert writer.execute("SELECT numero_ssa FROM ssa_table").fetchall() == []
        backups = list(tmp_path.glob("ssas.db.backup_before_reset_*"))
        assert len(backups) == 1
        with closing(sqlite3.connect(backups[0])) as backup:
            assert backup.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
                ("original",)
            ]
        with closing(sqlite3.connect(db)) as current:
            assert current.execute("PRAGMA quick_check").fetchone() == ("ok",)
            tables = {
                row[0]
                for row in current.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            assert {"ssa_table", "ssa_event_records"} <= tables


def test_maintenance_reset_keeps_original_when_backup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts_manutencao import gerenciar_banco

    db = tmp_path / "ssas.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE ssa_table(numero_ssa TEXT)")
        conn.execute("INSERT INTO ssa_table VALUES ('original')")
        conn.commit()

    def fail_backup(_source: Path, _target: str) -> None:
        raise sqlite3.OperationalError("backup failed")

    monkeypatch.setattr(gerenciar_banco, "create_sqlite_backup", fail_backup)
    with pytest.raises(sqlite3.OperationalError, match="backup failed"):
        gerenciar_banco.reset_database(str(db))

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("original",)
        ]


def test_maintenance_reset_refuses_orphan_sidecar_for_new_database(
    tmp_path: Path,
) -> None:
    from scripts_manutencao.gerenciar_banco import reset_database

    db = tmp_path / "new.db"
    wal = Path(f"{db}-wal")
    wal.write_bytes(b"preexisting")

    with pytest.raises(RuntimeError, match="sidecars SQLite preexistentes"):
        reset_database(str(db))

    assert not db.exists()
    assert wal.read_bytes() == b"preexisting"


def test_maintenance_reset_cleans_new_database_family_after_promotion_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts_manutencao import gerenciar_banco

    db = tmp_path / "new.db"
    real_connect = sqlite3.connect

    class FailingCandidate(sqlite3.Connection):
        def backup(self, target, *, pages=-1, progress=None, name="main", sleep=0.25):
            raise sqlite3.OperationalError("promotion failed")

    class SidecarOnClose(sqlite3.Connection):
        def close(self):
            super().close()
            Path(f"{db}-wal").write_bytes(b"created during promotion")
            Path(f"{db}-shm").write_bytes(b"created during promotion")

    def connect(path, *args, **kwargs):
        factory = FailingCandidate if path == ":memory:" else SidecarOnClose
        return real_connect(path, *args, factory=factory, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(gerenciar_banco.sqlite3, "connect", connect)
        with pytest.raises(sqlite3.OperationalError, match="promotion failed"):
            gerenciar_banco.reset_database(str(db))

    assert not db.exists()
    assert not Path(f"{db}-wal").exists()
    assert not Path(f"{db}-shm").exists()


def test_main_reset_does_not_report_success_after_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import main as main_module
    from scripts_manutencao import gerenciar_banco

    def fail_reset(_db_path: str) -> None:
        raise sqlite3.OperationalError("reset failed")

    monkeypatch.setattr(gerenciar_banco, "reset_database", fail_reset)
    with pytest.raises(sqlite3.OperationalError, match="reset failed"):
        main_module._run_maintenance_action(
            Namespace(reset_db=True, clean_data=False), "unused.db"
        )

    assert "resetado com sucesso" not in capsys.readouterr().out


def test_main_maintenance_targets_resolved_database_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import main as main_module
    from scripts_manutencao import gerenciar_banco

    runtime_db = tmp_path / "runtime" / "data" / "custom.db"
    runtime_db.parent.mkdir(parents=True)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        gerenciar_banco, "reset_database", lambda path: calls.append(("reset", path))
    )
    monkeypatch.setattr(
        gerenciar_banco, "clean_old_backups", lambda path: calls.append(("clean", path))
    )
    monkeypatch.setattr(
        gerenciar_banco,
        "sanitize_data_folder",
        lambda path: calls.append(("sanitize", path)),
    )

    assert main_module._run_maintenance_action(
        Namespace(reset_db=True, clean_data=False), str(runtime_db)
    )
    assert main_module._run_maintenance_action(
        Namespace(reset_db=False, clean_data=True), str(runtime_db)
    )

    data_dir = str(runtime_db.parent)
    assert calls == [
        ("reset", str(runtime_db)),
        ("clean", data_dir),
        ("sanitize", data_dir),
    ]
    assert not (cwd / "data").exists()


def test_main_clean_data_refuses_when_writer_lock_is_busy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main as main_module
    from armazenamento.database_lock import database_writer_lock
    from scripts_manutencao import gerenciar_banco

    db_path = tmp_path / "ssas.db"
    monkeypatch.setattr(
        gerenciar_banco,
        "clean_old_backups",
        lambda _path: pytest.fail("limpeza nao pode rodar com banco em uso"),
    )
    busy = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with database_writer_lock(str(db_path)):
            busy.set()
            release.wait(10)

    holder = threading.Thread(target=_hold)
    holder.start()
    try:
        assert busy.wait(10)
        with pytest.raises(SystemExit) as exit_info:
            main_module._run_maintenance_action(
                Namespace(reset_db=False, clean_data=True), str(db_path)
            )
        assert exit_info.value.code == 1
    finally:
        release.set()
        holder.join(10)

    output = capsys.readouterr().out
    assert "banco em uso" in output
    assert "Limpeza concluida" not in output


def test_clean_old_backups_expires_promotion_archives(tmp_path: Path) -> None:
    from scripts_manutencao import gerenciar_banco

    old_archive = tmp_path / "ssas.db.bak-20260101_000000_000000"
    old_sidecar = tmp_path / "ssas.db.bak-20260101_000000_000000-wal"
    recent_archive = tmp_path / "ssas.db.bak-20260920_000000_000000"
    primary = tmp_path / "ssas.db"
    unrelated = tmp_path / "notas.txt"
    for path in (old_archive, old_sidecar, recent_archive, primary, unrelated):
        path.write_bytes(b"x")
    stale = 1_600_000_000
    for path in (old_archive, old_sidecar, primary, unrelated):
        os.utime(path, (stale, stale))

    gerenciar_banco.clean_old_backups(str(tmp_path), days_to_keep=7)

    assert not old_archive.exists()
    assert not old_sidecar.exists()
    assert recent_archive.exists()
    assert primary.exists()
    assert unrelated.exists()
