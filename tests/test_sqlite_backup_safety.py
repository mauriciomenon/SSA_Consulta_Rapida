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
    calls: list[tuple[str, str, str | None, str | None]] = []
    monkeypatch.setattr(
        gerenciar_banco,
        "reset_database",
        lambda path: calls.append(("reset", path, None, None)),
    )
    monkeypatch.setattr(
        gerenciar_banco,
        "clean_old_backups",
        lambda path, db_basename=None, scope_name=None: calls.append(
            ("clean", path, db_basename, scope_name)
        ),
    )
    monkeypatch.setattr(
        gerenciar_banco,
        "sanitize_data_folder",
        lambda path, db_basename=None, scope_name=None: calls.append(
            ("sanitize", path, db_basename, scope_name)
        ),
    )

    assert main_module._run_maintenance_action(
        Namespace(reset_db=True, clean_data=False), str(runtime_db)
    )
    assert main_module._run_maintenance_action(
        Namespace(reset_db=False, clean_data=True), str(runtime_db)
    )

    data_dir = str(runtime_db.parent)
    assert calls == [
        ("reset", str(runtime_db), None, None),
        ("clean", data_dir, "custom.db", "custom.db"),
        ("sanitize", data_dir, "custom.db", "custom.db"),
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
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
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


def test_main_clean_data_refuses_non_sqlite_target_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main as main_module
    from scripts_manutencao import gerenciar_banco

    foreign_dir = tmp_path / "documentos"
    foreign_dir.mkdir()
    fake_db = foreign_dir / "ssas.db"
    fake_db.write_bytes(b"not a sqlite file at all")
    monkeypatch.setattr(
        gerenciar_banco,
        "clean_old_backups",
        lambda _path: pytest.fail("limpeza nao pode varrer diretorio estranho"),
    )
    monkeypatch.setattr(
        gerenciar_banco,
        "sanitize_data_folder",
        lambda _path: pytest.fail("limpeza nao pode varrer diretorio estranho"),
    )

    with pytest.raises(SystemExit) as exit_info:
        main_module._run_maintenance_action(
            Namespace(reset_db=False, clean_data=True), str(fake_db)
        )

    assert exit_info.value.code == 1
    assert "Limpeza recusada" in capsys.readouterr().out


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_main_clean_data_refuses_symlink_db_in_foreign_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main as main_module
    from scripts_manutencao import gerenciar_banco

    foreign_dir = tmp_path / "documentos"
    foreign_dir.mkdir()
    real_db = foreign_dir / "real.db"
    with sqlite3.connect(real_db) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    link_db = foreign_dir / "ssas.db"
    link_db.symlink_to(real_db)
    monkeypatch.setattr(
        gerenciar_banco,
        "clean_old_backups",
        lambda _path: pytest.fail("limpeza nao pode seguir symlink"),
    )

    with pytest.raises(SystemExit) as exit_info:
        main_module._run_maintenance_action(
            Namespace(reset_db=False, clean_data=True), str(link_db)
        )

    assert exit_info.value.code == 1
    assert "Limpeza recusada" in capsys.readouterr().out


def test_sanitize_refuses_regular_file_at_data_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts_manutencao import gerenciar_banco

    target = tmp_path / "data"
    target.write_bytes(b"stray file")

    gerenciar_banco.sanitize_data_folder(str(target))

    assert "nao e diretorio" in capsys.readouterr().out
    assert target.is_file()


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_sanitize_refuses_symlinked_data_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts_manutencao import gerenciar_banco

    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    kept = real_dir / "usuario.bak"
    kept.write_bytes(b"keep")
    link = tmp_path / "data"
    link.symlink_to(real_dir, target_is_directory=True)

    gerenciar_banco.sanitize_data_folder(str(link))

    assert "symlink" in capsys.readouterr().out
    assert kept.exists()


def test_reset_database_creates_missing_parent_dir(tmp_path: Path) -> None:
    from scripts_manutencao import gerenciar_banco

    db_path = tmp_path / "instalacao_nova" / "data" / "ssas.db"

    gerenciar_banco.reset_database(str(db_path))

    assert db_path.is_file()
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA quick_check").fetchone() == ("ok",)


def test_clean_old_backups_stem_scope_preserves_foreign_files(
    tmp_path: Path,
) -> None:
    from scripts_manutencao import gerenciar_banco

    stale = 1_600_000_000
    db_artifact = tmp_path / "ssas.db.bak-20260101_000000_000000"
    foreign_backup = tmp_path / "backup_tese.sql"
    foreign_temp = tmp_path / "rascunho.bak"
    for path in (db_artifact, foreign_backup, foreign_temp):
        path.write_bytes(b"x")
        os.utime(path, (stale, stale))

    gerenciar_banco.clean_old_backups(
        str(tmp_path), days_to_keep=7, scope_name="ssas.db"
    )

    assert not db_artifact.exists()
    assert foreign_backup.exists()
    assert foreign_temp.exists()


def test_sanitize_stem_scope_preserves_foreign_temp_files(
    tmp_path: Path,
) -> None:
    from scripts_manutencao import gerenciar_banco

    db_temp = tmp_path / "ssas.db.tmp-123"
    hidden_staging = tmp_path / ".ssas.db.tmp-456"
    foreign_temp = tmp_path / "notas.tmp"
    foreign_bak = tmp_path / "tese.bak"
    for path in (db_temp, hidden_staging, foreign_temp, foreign_bak):
        path.write_bytes(b"x")

    gerenciar_banco.sanitize_data_folder(str(tmp_path), scope_name="ssas.db")

    assert not db_temp.exists()
    assert not hidden_staging.exists()
    assert foreign_temp.exists()
    assert foreign_bak.exists()


def test_clean_old_backups_protects_custom_named_active_db(tmp_path: Path) -> None:
    """Banco ativo com nome fora do literal ssas.db nao pode entrar na limpeza."""
    from scripts_manutencao import gerenciar_banco

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    active_db = data_dir / "ssas_backup_prod.db"
    with sqlite3.connect(active_db) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    stale = 1_600_000_000
    os.utime(active_db, (stale, stale))

    gerenciar_banco.clean_old_backups(
        str(data_dir), days_to_keep=7, db_basename="ssas_backup_prod.db"
    )
    gerenciar_banco.sanitize_data_folder(
        str(data_dir), db_basename="ssas_backup_prod.db"
    )

    assert active_db.is_file()
    assert not (data_dir / "backups" / active_db.name).exists()


def test_clean_old_backups_uses_db_basename_as_scope(tmp_path: Path) -> None:
    from scripts_manutencao import gerenciar_banco

    data_dir = tmp_path / "shared"
    data_dir.mkdir()
    own_backup = data_dir / "custom.db.bak-20260101_000000_000000"
    foreign_backup = data_dir / "backup_unrelated.db"
    for path in (own_backup, foreign_backup):
        path.write_bytes(b"x")
        os.utime(path, (1_600_000_000, 1_600_000_000))
    own_temp = data_dir / "custom.db.tmp-123"
    foreign_temp = data_dir / "other.tmp"
    own_temp.write_bytes(b"x")
    foreign_temp.write_bytes(b"x")

    gerenciar_banco.clean_old_backups(
        str(data_dir), days_to_keep=7, db_basename="custom.db"
    )
    gerenciar_banco.sanitize_data_folder(str(data_dir), db_basename="custom.db")

    assert not own_backup.exists()
    assert not own_temp.exists()
    assert foreign_backup.exists()
    assert foreign_temp.exists()


@pytest.mark.parametrize("db_name", ["live.tmp", "live.bak"])
def test_sanitize_preserves_active_db_with_temp_extension(
    tmp_path: Path, db_name: str
) -> None:
    from scripts_manutencao import gerenciar_banco

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    active_db = data_dir / db_name
    with sqlite3.connect(active_db) as conn:
        conn.execute("CREATE TABLE placeholder(x)")

    gerenciar_banco.sanitize_data_folder(
        str(data_dir), db_basename=active_db.name, scope_name=""
    )

    assert active_db.is_file()
    with sqlite3.connect(active_db) as conn:
        assert conn.execute("PRAGMA quick_check").fetchone() == ("ok",)


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_main_clean_data_refuses_symlinked_directory_before_cleanup(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main as main_module

    target = tmp_path / "shared"
    target.mkdir()
    with sqlite3.connect(target / "ssas.db") as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    foreign_backup = target / "backup_unrelated.db"
    foreign_backup.write_bytes(b"keep")
    os.utime(foreign_backup, (1_600_000_000, 1_600_000_000))
    link = tmp_path / "data"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(SystemExit) as exit_info:
        main_module._run_maintenance_action(
            Namespace(reset_db=False, clean_data=True), str(link / "ssas.db")
        )

    assert exit_info.value.code == 1
    assert foreign_backup.read_bytes() == b"keep"
    output = capsys.readouterr().out
    assert "Limpeza recusada" in output
    assert "Limpeza concluida" not in output


def test_main_clean_data_limits_custom_db_to_its_full_basename(
    tmp_path: Path,
) -> None:
    import main as main_module

    data_dir = tmp_path / "shared"
    data_dir.mkdir()
    db_path = data_dir / "foo.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    own_backup = data_dir / "foo.db.bak-20260101_000000_000000"
    own_temp = data_dir / "foo.db.tmp-123"
    foreign_backup = data_dir / "foobar_backup_old.db"
    foreign_temp = data_dir / "foobar.tmp"
    near_name = data_dir / "foo.dbx.tmp"
    same_prefix_backup = data_dir / "foo.db.other_backup_old.db"
    same_prefix_temp = data_dir / "foo.db.other.tmp"
    for path in (
        own_backup, own_temp, foreign_backup, foreign_temp, near_name,
        same_prefix_backup, same_prefix_temp,
    ):
        path.write_bytes(b"keep")
    for path in (own_backup, foreign_backup, same_prefix_backup):
        os.utime(path, (1_600_000_000, 1_600_000_000))

    assert main_module._run_maintenance_action(
        Namespace(reset_db=False, clean_data=True), str(db_path)
    )

    assert not own_backup.exists()
    assert not own_temp.exists()
    assert foreign_backup.read_bytes() == b"keep"
    assert foreign_temp.read_bytes() == b"keep"
    assert near_name.read_bytes() == b"keep"
    assert same_prefix_backup.read_bytes() == b"keep"
    assert same_prefix_temp.read_bytes() == b"keep"


def test_main_clean_data_scopes_explicit_ssa_db_path_named_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import main as main_module

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    foreign_backup = data_dir / "backup_unrelated.db"
    legacy_backup = data_dir / "ssas_backup_unrelated.db"
    emergency_backup = data_dir / "ssas_emergency_backup_unrelated.db"
    foreign_temp = data_dir / "notes.tmp"
    foreign_backup.write_bytes(b"keep")
    legacy_backup.write_bytes(b"keep")
    emergency_backup.write_bytes(b"keep")
    foreign_temp.write_bytes(b"keep")
    for path in (foreign_backup, legacy_backup, emergency_backup):
        os.utime(path, (1_600_000_000, 1_600_000_000))
    monkeypatch.setenv("SSA_DB_PATH", str(db_path))

    assert main_module._run_maintenance_action(
        Namespace(reset_db=False, clean_data=True), str(db_path)
    )

    assert foreign_backup.read_bytes() == b"keep"
    assert legacy_backup.read_bytes() == b"keep"
    assert emergency_backup.read_bytes() == b"keep"
    assert foreign_temp.read_bytes() == b"keep"


@pytest.mark.parametrize("bootstrap_sets_db_path", [False, True])
def test_main_clean_data_keeps_legacy_scope_for_runtime_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bootstrap_sets_db_path: bool
) -> None:
    import main as main_module

    monkeypatch.delenv("SSA_DB_PATH", raising=False)
    monkeypatch.setattr(main_module, "runtime_root", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "ssas.db"
    if bootstrap_sets_db_path:
        monkeypatch.setenv("SSA_DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE placeholder(x)")
    old_backup = data_dir / "backup_legacy.db"
    old_backup.write_bytes(b"old")
    os.utime(old_backup, (1_600_000_000, 1_600_000_000))

    assert main_module._run_maintenance_action(
        Namespace(reset_db=False, clean_data=True), str(db_path)
    )

    assert not old_backup.exists()
    assert db_path.is_file()


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_clean_accepts_symlinked_ancestor_with_regular_data_directory(
    tmp_path: Path,
) -> None:
    from scripts_manutencao import gerenciar_banco

    real_parent = tmp_path / "real_parent"
    data_dir = real_parent / "data"
    data_dir.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(real_parent, target_is_directory=True)
    old_backup = data_dir / "backup_legacy.db"
    old_backup.write_bytes(b"old")
    os.utime(old_backup, (1_600_000_000, 1_600_000_000))

    gerenciar_banco.clean_old_backups(str(alias / "data"))
    gerenciar_banco.sanitize_data_folder(str(alias / "data"))

    assert not old_backup.exists()
    assert (data_dir / "backups").is_dir()


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_clean_refuses_symlinked_backups_before_removing_files(tmp_path: Path) -> None:
    from scripts_manutencao import gerenciar_banco

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (data_dir / "backups").symlink_to(external, target_is_directory=True)
    local_backup = data_dir / "ssas.db.bak-20260101_000000_000000"
    external_backup = external / "ssas.db.bak-20260101_000000_000000"
    for path in (local_backup, external_backup):
        path.write_bytes(b"keep")
        os.utime(path, (1_600_000_000, 1_600_000_000))

    with pytest.raises(RuntimeError, match="symlink"):
        gerenciar_banco.clean_old_backups(str(data_dir))

    assert local_backup.read_bytes() == b"keep"
    assert external_backup.read_bytes() == b"keep"


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_sanitize_refuses_symlinked_backups_before_moving_files(
    tmp_path: Path,
) -> None:
    from scripts_manutencao import gerenciar_banco

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (data_dir / "backups").symlink_to(external, target_is_directory=True)
    local_backup = data_dir / "ssas_backup_old.db"
    local_backup.write_bytes(b"keep")

    gerenciar_banco.sanitize_data_folder(str(data_dir))

    assert local_backup.read_bytes() == b"keep"
    assert not (external / local_backup.name).exists()
