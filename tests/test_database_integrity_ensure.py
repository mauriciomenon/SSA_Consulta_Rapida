"""Contract tests for the single heavy integrity check (S12-integrity).

Regression: the full-rescan startup used to run the heavy
verify_database_integrity twice back to back (once inside
repair_database_if_needed, once explicitly). The contract now is one
heavy check on the happy path via ensure_database_integrity, which
returns (ok, report); a fresh check runs only when the database changed.
"""

import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento import database_integrity  # noqa: E402
from armazenamento.database import (  # noqa: E402
    ensure_database_integrity,
    initialize_database,
    repair_database_if_needed,
)

SCHEMA_FILE = os.path.join(project_root, "config", "schema_unified.sql")


def _healthy_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "ssas.db")
    initialize_database(db_path, SCHEMA_FILE)
    return db_path


def _counting_verify(monkeypatch: pytest.MonkeyPatch):
    counter = {"calls": 0}
    original = database_integrity.verify_database_integrity

    def counting(db_path, table_name):
        counter["calls"] += 1
        return original(db_path, table_name)

    monkeypatch.setattr(database_integrity, "verify_database_integrity", counting)
    return counter


def test_ensure_healthy_db_single_check_and_valid_report(tmp_path, monkeypatch):
    db_path = _healthy_db(tmp_path)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert counter["calls"] == 1


def test_ensure_bootstrap_missing_db_creates_and_reports(tmp_path, monkeypatch):
    db_path = str(tmp_path / "missing" / "ssas.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert os.path.exists(db_path)
    assert counter["calls"] == 2


def test_ensure_corrupted_db_returns_false_with_issues(tmp_path, monkeypatch):
    db_path = str(tmp_path / "corrupt.db")
    Path(db_path).write_bytes(b"this is not a sqlite database" * 64)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is False
    assert report["is_valid"] is False
    assert report["sqlite_corruption_confirmed"] is True
    assert report["issues"]
    assert counter["calls"] == 1


@pytest.mark.parametrize(
    ("error", "confirmed"),
    [
        (sqlite3.DatabaseError("file is not a database"), True),
        (sqlite3.DatabaseError("database disk image is malformed"), True),
        (sqlite3.OperationalError("database is locked"), False),
        (sqlite3.OperationalError("disk I/O error"), False),
        (sqlite3.OperationalError("unable to open database file"), False),
        (OSError("file is not a database"), False),
        (ValueError("database disk image is malformed"), False),
    ],
)
def test_sqlite_errors_without_codes_keep_corruption_classification(
    tmp_path, monkeypatch, error, confirmed
):
    db_path = _healthy_db(tmp_path)
    assert not hasattr(error, "sqlite_errorcode")

    def legacy_connection(_path):
        raise error

    monkeypatch.setattr(database_integrity, "_read_only_connection", legacy_connection)

    report = database_integrity.verify_database_integrity(db_path)

    assert report["sqlite_corruption_confirmed"] is confirmed
    assert report["verification_inconclusive"] is not confirmed


def test_repair_wrapper_keeps_boolean_contract(tmp_path):
    db_path = _healthy_db(tmp_path)

    assert repair_database_if_needed(db_path, SCHEMA_FILE) is True


def test_restore_returns_actual_schema_and_row_report(tmp_path, monkeypatch):
    db_path = _healthy_db(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600001', 'ADM', '2026-01-01 00:00:00')")
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    Path(db_path).write_bytes(b"corrupted SQLite" * 64)
    counter = _counting_verify(monkeypatch)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert report["restored_from_snapshot"] is True
    assert report["table_exists"] is True
    assert report["schema_valid"] is True
    assert report["missing_required_columns"] == []
    assert report["issues"] == []
    assert counter["calls"] == 2
    with closing(sqlite3.connect(db_path)) as conn, conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [("202600001",)]


def _seeded_db_with_snapshot(tmp_path: Path) -> str:
    """Banco saudavel com uma linha e snapshot forcado em historico_backups."""
    db_path = _healthy_db(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600001', 'ADM', '2026-01-01 00:00:00')")
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    return db_path


def test_locked_database_is_not_replaced_by_snapshot(tmp_path):
    db_path = _seeded_db_with_snapshot(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
            "VALUES ('202600002', 'ADM', '2026-01-02 00:00:00')"
        )
    original = Path(db_path).read_bytes()

    with closing(sqlite3.connect(db_path, isolation_level=None)) as locked_conn:
        locked_conn.execute("BEGIN EXCLUSIVE")
        try:
            ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)
        finally:
            locked_conn.execute("ROLLBACK")

    assert ok is False
    assert report["verification_inconclusive"] is True
    assert report["sqlite_corruption_confirmed"] is False
    assert "restored_from_snapshot" not in report
    assert Path(db_path).read_bytes() == original
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (2,)


def test_missing_database_restores_snapshot_with_repairable_data(tmp_path):
    db_path = _healthy_db(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
            "VALUES ('invalid', 'ADM', '2026-01-01 00:00:00')"
        )
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    Path(db_path).unlink()

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["restored_from_snapshot"] is True
    assert report["is_valid"] is False
    assert report["sqlite_integrity_ok"] is True
    assert report["schema_valid"] is True
    assert report["invalid_data"]["invalid_numero_ssa"] == 1
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchone() == (
            "invalid",
        )


def test_ensure_missing_db_restores_snapshot_instead_of_empty(tmp_path):
    """Delecao manual do .db: reaplica o snapshot, nao cria schema vazio."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(f"{db_path}{suffix}").unlink(missing_ok=True)
    assert not os.path.exists(db_path)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["restored_from_snapshot"] is True
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]


def test_ensure_zero_byte_db_restores_snapshot(tmp_path):
    """Arquivo truncado a 0 bytes (ex.: leitura que criou .db vazio ou
    disco cheio) segue a mesma politica de restauracao."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    Path(db_path).write_bytes(b"")

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["restored_from_snapshot"] is True
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]


def test_restore_prefers_snapshot_with_data_over_empty(tmp_path):
    """Um snapshot vazio (banco recem-inicializado) nao deve esconder
    snapshots mais antigos que contem dados."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("DELETE FROM ssa_table")
    # Snapshot mais recente, porem vazio.
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    Path(db_path).unlink()

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["restored_from_snapshot"] is True
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]


def test_restore_keeps_recency_among_snapshots_with_data(tmp_path):
    """Entre snapshots com dados vale o mais recente — um antigo com
    mais linhas nao pode ressuscitar registros removidos depois."""
    db_path = _healthy_db(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600001', 'ADM', '2026-01-01 00:00:00')")
        conn.execute("INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                     "VALUES ('202600002', 'ADM', '2026-01-02 00:00:00')")
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("DELETE FROM ssa_table WHERE numero_ssa = '202600002'")
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    Path(db_path).unlink()

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["restored_from_snapshot"] is True
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]


def test_orphan_forensic_sidecars_are_pruned(tmp_path):
    """Preserva evidencia recente sem principal e limita as familias antigas."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    backup_dir = Path(db_path).resolve().parent / "historico_backups"
    suffixes = ("-wal", "-shm", "-journal")
    limit = database_integrity.INTEGRITY_SNAPSHOT_MAX_COUNT
    for index in range(limit + 1):
        Path(db_path).unlink()
        for suffix in suffixes:
            Path(f"{db_path}{suffix}").write_bytes(f"{index}:{suffix}".encode())

        ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

        assert ok is True
        assert report["restored_from_snapshot"] is True
        leftovers = [
            path for path in backup_dir.iterdir()
            if ".corrupt_" in path.name and path.name.endswith(suffixes)
        ]
        assert len(leftovers) == min(index + 1, limit) * len(suffixes)
        contents = {path.read_bytes() for path in leftovers}
        assert all(f"{index}:{suffix}".encode() in contents for suffix in suffixes)
    assert all(not path.read_bytes().startswith(b"0:") for path in leftovers)


def _forensic_family(backup_dir: Path, db_name: str, timestamp: str, *, with_db: bool):
    base = backup_dir / f"{db_name}.corrupt_{timestamp}.db"
    members = []
    if with_db:
        base.write_bytes(b"db-" + timestamp.encode())
        members.append(base)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{base}{suffix}")
        sidecar.write_bytes(f"{timestamp}:{suffix}".encode())
        members.append(sidecar)
    return members


def test_prune_forensic_backups_orders_by_name_timestamp(tmp_path):
    """A ordem cronologica vem do timestamp validado do basename, nao do
    mtime: familias criadas em ordem inversa e com mtimes empatados sao
    podadas da mais antiga para a mais nova, e familia sem principal
    (so sidecars) conta na retencao."""
    db_path = _healthy_db(tmp_path)
    backup_dir = Path(db_path).resolve().parent / "historico_backups"
    backup_dir.mkdir(exist_ok=True)
    db_name = Path(db_path).name
    limit = database_integrity.INTEGRITY_SNAPSHOT_MAX_COUNT

    timestamps = [
        "20260101_000000_000004",
        "20260101_000000_000003",
        "20260101_000000_000002",
        "20260101_000000_000001",
    ]
    created = [
        _forensic_family(
            backup_dir, db_name, ts, with_db=(ts != "20260101_000000_000002")
        )
        for ts in timestamps
    ]
    # Mtimes empatados e identidade invertida em relacao ao nome: so o
    # timestamp do basename desempata de forma cronologica.
    fixed_ns = 1_700_000_000_000_000_000
    for members in created:
        for member in members:
            os.utime(member, ns=(fixed_ns, fixed_ns))

    database_integrity._prune_forensic_backups(db_path)

    remaining = sorted(
        path.name for path in backup_dir.iterdir() if ".corrupt_" in path.name
    )
    assert not any("_000001" in name or "_000002" in name for name in remaining)
    assert sum("_000003" in name for name in remaining) == 4
    assert sum("_000004" in name for name in remaining) == 4
    assert len(remaining) == limit * 4


def test_prune_forensic_backups_preserves_family_on_unlink_failure(
    tmp_path, monkeypatch
):
    """Falha ao remover um membro preserva o resto da familia como
    evidencia e nao impede a poda das demais familias excedentes."""
    db_path = _healthy_db(tmp_path)
    backup_dir = Path(db_path).resolve().parent / "historico_backups"
    backup_dir.mkdir(exist_ok=True)
    db_name = Path(db_path).name

    for index in range(4):
        _forensic_family(
            backup_dir, db_name, f"20260101_000000_00000{index + 1}", with_db=True
        )

    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self.name.endswith(".db") and "_000001" in self.name:
            raise OSError("falha simulada de remocao")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    database_integrity._prune_forensic_backups(db_path)

    monkeypatch.setattr(Path, "unlink", real_unlink)
    remaining = sorted(
        path.name for path in backup_dir.iterdir() if ".corrupt_" in path.name
    )
    # O principal da familia mais antiga e sempre o ultimo a ser removido:
    # a falha nele deixa o .db como evidencia apos os 3 sidecars ja terem
    # saido, sem depender da ordem do readdir; a segunda familia foi
    # podada por completo e as duas mais novas ficaram retidas.
    assert sum("_000001" in name for name in remaining) == 1
    assert any(name.endswith("_000001.db") for name in remaining)
    assert not any("_000002" in name for name in remaining)
    assert sum("_000003" in name for name in remaining) == 4
    assert sum("_000004" in name for name in remaining) == 4


def test_ensure_missing_db_without_snapshot_still_bootstraps(tmp_path):
    """Primeiro uso (sem snapshots): criacao inicial segue funcionando."""
    db_path = str(tmp_path / "fresh" / "ssas.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is True
    assert report["is_valid"] is True
    assert "restored_from_snapshot" not in report
    assert os.path.exists(db_path)


def test_prepare_working_database_runs_heavy_check_once(tmp_path, monkeypatch):
    from core import app_logic
    from armazenamento import database as database_module

    db_path = _healthy_db(tmp_path)
    counter = {"ensure": 0, "verify": 0}

    def fake_ensure(db_path_arg, schema_file="schema.sql", table_name="ssa_table"):
        counter["ensure"] += 1
        report = database_integrity.verify_database_integrity(db_path_arg, table_name)
        return bool(report["is_valid"]), report

    monkeypatch.setattr(database_module, "ensure_database_integrity", fake_ensure)
    monkeypatch.setattr(
        database_module,
        "verify_database_integrity",
        lambda *a, **k: counter.__setitem__("verify", counter["verify"] + 1)
        or {"is_valid": True, "issues": [], "warnings": []},
    )

    working, candidate, report = app_logic._prepare_working_database_for_import(
        data_dir=str(tmp_path / "data"),
        primary_db_path=db_path,
        run_id="test-run",
        force_import=False,
        table_name="ssa_table",
    )

    assert working == db_path
    assert candidate is None
    assert report["is_valid"] is True
    assert counter["ensure"] == 1
    assert counter["verify"] == 0


def test_restore_keeps_recovery_marker_when_sidecar_rollback_fails(
    tmp_path, monkeypatch
):
    """Rollback falho deixa o disco indeterminado: o marcador de
    recuperacao nao pode ser removido — ele forca a revalidacao do
    cache na proxima rodada."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    db = Path(db_path).resolve()
    db.write_bytes(b"banco corrompido com sidecar")
    sidecar = Path(f"{db}-wal")
    sidecar.write_bytes(b"wal quente")
    real_replace = database_integrity._replace_file_with_retry

    def flaky_replace(source, target):
        # Aborta a promocao do snapshot e a recomposicao do sidecar:
        # ambas as falhas levam ao retorno "critical".
        if Path(target) in {db, sidecar}:
            raise OSError("falha simulada na promocao/rollback")
        return real_replace(source, target)

    monkeypatch.setattr(
        database_integrity, "_replace_file_with_retry", flaky_replace
    )

    status = database_integrity._restore_latest_valid_snapshot_locked(
        str(db), "ssa_table"
    )

    assert status == "critical"
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()


def test_ensure_preserves_integrity_report_on_critical_restore(
    tmp_path, monkeypatch
):
    """O retorno 'critical' anexa a falha ao report original em vez de
    descartar os campos de diagnostico da verificacao inicial."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    Path(db_path).resolve().write_bytes(b"arquivo nao sqlite")
    monkeypatch.setattr(
        database_integrity,
        "_restore_latest_valid_snapshot_locked",
        lambda *args, **kwargs: "critical",
    )

    ok, report = ensure_database_integrity(db_path, SCHEMA_FILE)

    assert ok is False
    assert report["is_valid"] is False
    assert any(
        "estado em disco indeterminado" in issue for issue in report["issues"]
    )
    # Campos de diagnostico da verificacao original seguem presentes.
    assert "database_accessible" in report
    assert "sqlite_corruption_confirmed" in report


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_restore_replaces_invalid_recovery_marker(tmp_path):
    """Marcador plantado como symlink e descartado e recriado: o restore
    segue e o alvo do link nao e tocado."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    db = Path(db_path).resolve()
    db.write_bytes(b"corrompido")
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    decoy = tmp_path / "decoy.txt"
    decoy.write_text("conteudo do alvo")
    marker.symlink_to(decoy)

    status = database_integrity._restore_latest_valid_snapshot_locked(
        str(db), "ssa_table"
    )

    assert status == "restored"
    assert marker.is_file()
    assert not marker.is_symlink()
    assert decoy.read_text() == "conteudo do alvo"


@pytest.mark.skipif(os.name != "posix", reason="symlink sem privilegio no Windows")
def test_restore_refuses_symlinked_historico_backups(tmp_path):
    """historico_backups como symlink desviaria as copias forenses para
    fora da pasta de dados: ambiente adulterado bloqueia fail-closed."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    db = Path(db_path).resolve()
    backup_dir = db.parent / "historico_backups"
    backup_dir.rename(tmp_path / "historico_real")
    outside = tmp_path / "fora"
    outside.mkdir()
    backup_dir.symlink_to(outside, target_is_directory=True)
    db.write_bytes(b"corrompido")

    status = database_integrity._restore_latest_valid_snapshot_locked(
        str(db), "ssa_table"
    )

    assert status == "critical"
    assert not list(outside.iterdir())


def test_restore_continues_to_next_snapshot_when_marker_unlink_fails(
    tmp_path, monkeypatch
):
    """Falha ao remover o marcador criado na rodada nao pode abortar o
    loop de candidatos: o proximo snapshot valido ainda deve restaurar,
    e o marcador restante apenas forca uma revalidacao extra."""
    db_path = _seeded_db_with_snapshot(tmp_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
            "VALUES ('202600002', 'ADM', '2026-01-02 00:00:00')"
        )
    assert database_integrity._create_integrity_snapshot(db_path, force=True)
    db = Path(db_path).resolve()
    db.write_bytes(b"corrompido")
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")

    real_replace = database_integrity._replace_file_with_retry
    state = {"failed": False}

    def flaky_replace(source, target):
        if not state["failed"] and Path(target) == db:
            state["failed"] = True
            raise OSError("falha simulada na promocao")
        return real_replace(source, target)

    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self == marker:
            raise OSError("falha simulada no unlink do marcador")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(
        database_integrity, "_replace_file_with_retry", flaky_replace
    )
    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    status = database_integrity._restore_latest_valid_snapshot_locked(
        str(db), "ssa_table"
    )

    monkeypatch.setattr(Path, "unlink", real_unlink)
    assert status == "restored"
    assert marker.is_file()
    with closing(sqlite3.connect(str(db))) as conn:
        assert conn.execute("SELECT numero_ssa FROM ssa_table").fetchall() == [
            ("202600001",)
        ]
