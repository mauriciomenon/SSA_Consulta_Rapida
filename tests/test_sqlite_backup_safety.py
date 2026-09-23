from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
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
