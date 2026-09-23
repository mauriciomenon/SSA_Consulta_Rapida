from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from core.import_database_rotation import (
    promote_full_rescan_candidate,
    prune_full_rescan_artifacts,
    register_full_rescan_artifact,
    rotate_preexisting_database_for_full_rescan,
)
from core.import_errors import DatabaseError


def _build_wal_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE ssa_table(id INTEGER PRIMARY KEY, value TEXT)")
        conn.executemany(
            "INSERT INTO ssa_table(value) VALUES (?)",
            [("a",), ("b",)],
        )
        conn.commit()
    finally:
        conn.close()


def _build_value_db(db_path: Path, value: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE ssa_table(id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO ssa_table(value) VALUES (?)", (value,))
        conn.commit()
    finally:
        conn.close()


def _read_value(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT value FROM ssa_table").fetchone()
    finally:
        conn.close()
    assert row is not None
    return str(row[0])


@pytest.mark.parametrize("marker_writable", [False, True])
def test_rotate_preexisting_database_for_full_rescan_without_external_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    marker_writable: bool,
) -> None:
    db_path = tmp_path / "ssas.db"
    _build_wal_db(db_path)
    original_open = Path.open

    def _open_with_marker_failure(path, *args, **kwargs):
        if path.name.startswith(".ssa-full-rescan-") and not marker_writable:
            raise PermissionError("registro bloqueado")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _open_with_marker_failure)

    rotate_preexisting_database_for_full_rescan(str(db_path))

    backups = sorted(
        p
        for p in tmp_path.glob("ssas.db.full_rescan_backup_*")
        if not p.name.endswith(("-wal", "-shm"))
    )
    assert len(backups) == 1
    assert not db_path.exists()
    markers = list(tmp_path.glob(".ssa-full-rescan-*.json"))
    assert bool(markers) is marker_writable
    if not marker_writable:
        assert "preservado sem novo registro de propriedade" in caplog.text

    conn = sqlite3.connect(backups[0])
    try:
        row = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()
    finally:
        conn.close()
    assert row is not None
    assert int(row[0]) == 2


def test_rotate_preexisting_database_for_full_rescan_moves_existing_sidecars(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    _build_wal_db(db_path)

    wal_sidecar = Path(f"{db_path}-wal")
    shm_sidecar = Path(f"{db_path}-shm")
    wal_sidecar.write_bytes(b"")
    shm_sidecar.write_bytes(b"")

    rotate_preexisting_database_for_full_rescan(str(db_path))

    backups = sorted(
        p
        for p in tmp_path.glob("ssas.db.full_rescan_backup_*")
        if not p.name.endswith(("-wal", "-shm"))
    )
    assert len(backups) == 1
    backup_path = backups[0]

    assert not wal_sidecar.exists()
    assert not shm_sidecar.exists()
    assert Path(f"{backup_path}-wal").exists()
    assert Path(f"{backup_path}-shm").exists()


def test_rotate_moves_journal_sidecar_out_of_primary_path(
    tmp_path: Path,
) -> None:
    """Um -journal quente do banco antigo nao pode ficar no caminho principal:
    apos a promocao o SQLite o aplicaria sobre o banco novo."""
    db_path = tmp_path / "ssas.db"
    _build_value_db(db_path, "primary_old")
    journal_sidecar = Path(f"{db_path}-journal")
    journal_sidecar.write_bytes(b"journal quente de crash")

    rotate_preexisting_database_for_full_rescan(str(db_path))

    backups = sorted(
        p
        for p in tmp_path.glob("ssas.db.full_rescan_backup_*")
        if not p.name.endswith(("-wal", "-shm", "-journal"))
    )
    assert len(backups) == 1
    backup_path = backups[0]

    # O caminho principal fica livre de -journal: o checkpoint/recovery do
    # SQLite consome um journal invalido e o placeholder de backup e inerte.
    assert not journal_sidecar.exists()
    assert Path(f"{backup_path}-journal").exists()


def test_promote_full_rescan_candidate_restores_primary_when_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    primary_db = tmp_path / "ssas.db"
    candidate_db = tmp_path / "ssas.db.full_rescan_candidate_test"
    _build_value_db(primary_db, "primary_old")
    _build_value_db(candidate_db, "candidate_new")

    def _replace_with_candidate_failure(source: str, target: str) -> None:
        if Path(source) == candidate_db and Path(target) == primary_db:
            raise PermissionError("simulated promotion failure")
        os.replace(source, target)

    monkeypatch.setattr(
        "core.import_database_rotation.replace_sqlite_file_with_retry",
        _replace_with_candidate_failure,
    )

    with pytest.raises(DatabaseError):
        promote_full_rescan_candidate(str(candidate_db), str(primary_db))

    assert primary_db.exists()
    assert _read_value(primary_db) == "primary_old"
    assert candidate_db.exists()
    assert _read_value(candidate_db) == "candidate_new"


def test_rotate_restores_primary_and_sidecars_when_sidecar_move_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    primary_db = tmp_path / "ssas.db"
    _build_value_db(primary_db, "primary_old")
    wal_sidecar = Path(f"{primary_db}-wal")
    shm_sidecar = Path(f"{primary_db}-shm")
    wal_sidecar.write_bytes(b"")
    shm_sidecar.write_bytes(b"")

    def _replace_with_shm_failure(source: str, target: str) -> None:
        if source.endswith("-shm") and ".full_rescan_backup_" in target:
            raise PermissionError("simulated sidecar failure")
        os.replace(source, target)

    monkeypatch.setattr(
        "core.import_database_rotation.replace_sqlite_file_with_retry",
        _replace_with_shm_failure,
    )

    with pytest.raises(DatabaseError, match="Banco e sidecars restaurados"):
        rotate_preexisting_database_for_full_rescan(str(primary_db))

    assert primary_db.exists()
    assert _read_value(primary_db) == "primary_old"
    assert wal_sidecar.exists()
    assert shm_sidecar.exists()
    assert not list(tmp_path.glob("ssas.db.full_rescan_backup_*"))


def _make_artifact(path: Path, age_seconds: float, *, owned: bool = True) -> Path:
    path.write_bytes(b"x")
    past = path.stat().st_mtime - age_seconds
    os.utime(path, (past, past))
    if owned and ".full_rescan_" in path.name:
        primary_name = path.name.split(".full_rescan_", 1)[0]
        register_full_rescan_artifact(str(path.with_name(primary_name)), str(path))
    return path


def test_prune_full_rescan_artifacts_keeps_newest_and_removes_sidecars(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    candidates = [
        _make_artifact(
            tmp_path / f"ssas.db.full_rescan_candidate_20260101_000000_00000{i}",
            age,
        )
        for i, age in enumerate((400, 300, 200, 100))
    ]
    backups = [
        _make_artifact(
            tmp_path / f"ssas.db.full_rescan_backup_20260101_000000_00000{i}",
            age,
        )
        for i, age in enumerate((300, 200, 100))
    ]
    old_wal = Path(f"{candidates[0]}-wal")
    old_journal = Path(f"{candidates[0]}-journal")
    old_wal.write_bytes(b"w")
    old_journal.write_bytes(b"j")

    prune_full_rescan_artifacts(str(db_path))

    remaining_candidates = sorted(
        tmp_path.glob("ssas.db.full_rescan_candidate_*")
    )
    remaining_backups = sorted(tmp_path.glob("ssas.db.full_rescan_backup_*"))
    assert remaining_candidates == [candidates[2], candidates[3]]
    assert remaining_backups == [backups[1], backups[2]]
    assert not old_wal.exists()
    assert not old_journal.exists()


def test_prune_full_rescan_artifacts_preserves_current_candidate(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    current = _make_artifact(
        tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000100", 1000
    )
    olders = [
        _make_artifact(
            tmp_path / f"ssas.db.full_rescan_candidate_20260101_000000_00000{i}",
            age,
        )
        for i, age in enumerate((500, 400, 300))
    ]

    prune_full_rescan_artifacts(str(db_path), preserve=str(current))

    remaining = sorted(tmp_path.glob("ssas.db.full_rescan_candidate_*"))
    # O candidato da rodada corrente (retry) nunca entra na poda; alem
    # dele ficam os 2 mais recentes.
    assert current in remaining
    assert olders[1] in remaining
    assert olders[2] in remaining
    assert olders[0] not in remaining


def test_prune_full_rescan_artifacts_ignores_unrelated_files(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssas.db"
    db_path.write_bytes(b"db")
    unrelated = [
        _make_artifact(tmp_path / "ssas.db", 10),
        _make_artifact(tmp_path / "ssas.db.backup_20260101_000000", 10),
        _make_artifact(tmp_path / "ssas.db.bak-20260101_000000", 10),
        _make_artifact(tmp_path / "other.db.full_rescan_candidate_x", 10),
        # Prefixo de artefato mas sufixo fora do formato de run_id: nome
        # ambiguo que a poda nao pode atribuir a um run deste banco.
        _make_artifact(tmp_path / "ssas.db.full_rescan_candidate_notas", 10),
        _make_artifact(
            tmp_path / "ssas.db.full_rescan_backup_relatorio", 10
        ),
        _make_artifact(
            tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000009",
            900,
            owned=False,
        ),
    ]

    prune_full_rescan_artifacts(str(db_path), keep=0)

    for path in unrelated:
        assert path.exists()


@pytest.mark.parametrize("failed_suffix", ["", "-wal"])
def test_prune_full_rescan_artifacts_survives_unlink_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failed_suffix: str,
) -> None:
    db_path = tmp_path / "ssas.db"
    for i in range(4):
        _make_artifact(
            tmp_path / f"ssas.db.full_rescan_candidate_20260101_000000_00000{i}",
            400 - i * 100,
        )
    oldest = tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000000"
    oldest_wal = Path(f"{oldest}-wal")
    oldest_wal.write_bytes(b"wal preservado se bloqueado")

    original_unlink = Path.unlink

    def _flaky_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == Path(f"{oldest}{failed_suffix}"):
            raise PermissionError("simulated locked artifact")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", _flaky_unlink)

    prune_full_rescan_artifacts(str(db_path))

    remaining = sorted(
        p for p in tmp_path.glob("ssas.db.full_rescan_candidate_*")
        if not p.name.endswith("-wal")
    )
    assert len(remaining) == 3  # 2 kept + 1 remocao que falhou
    assert oldest in remaining
    assert oldest_wal.exists() is bool(failed_suffix)
    assert (tmp_path / f".ssa-full-rescan-{oldest.name}.json").exists()


def test_prune_full_rescan_artifacts_does_not_match_other_db_names(
    tmp_path: Path,
) -> None:
    """Metacaracteres glob no nome do banco nao podem casar outro banco."""
    db_path = tmp_path / "ssas[1].db"
    for i in range(4):
        _make_artifact(
            tmp_path
            / f"ssas[1].db.full_rescan_candidate_20260101_000000_00000{i}",
            400 - i * 100,
        )
    _make_artifact(
        tmp_path / "ssas1.db.full_rescan_candidate_20260101_000000_000009", 10
    )

    prune_full_rescan_artifacts(str(db_path))

    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert "ssas1.db.full_rescan_candidate_20260101_000000_000009" in remaining
    own = [n for n in remaining if n.startswith("ssas[1].db.full_rescan_candidate_")]
    assert own == [
        "ssas[1].db.full_rescan_candidate_20260101_000000_000002",
        "ssas[1].db.full_rescan_candidate_20260101_000000_000003",
    ]


@pytest.mark.parametrize(
    "change", ["identity", "invalid_marker", "artifact_symlink", "marker_symlink", "sidecar_symlink"]
)
def test_prune_preserves_artifacts_without_verified_identity(tmp_path: Path, change: str) -> None:
    db_path = tmp_path / "ssas.db"
    artifact = _make_artifact(
        tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000001", 10
    )
    marker = tmp_path / f".ssa-full-rescan-{artifact.name}.json"
    target = tmp_path / "user-file.db"
    target.write_bytes(b"arquivo do usuario")
    if change == "identity":
        os.replace(target, artifact)
    elif change == "invalid_marker":
        marker.write_text("{}", encoding="utf-8")
    else:
        link = {
            "artifact_symlink": artifact,
            "marker_symlink": marker,
            "sidecar_symlink": Path(f"{artifact}-wal"),
        }[change]
        link.unlink(missing_ok=True)
        try:
            link.symlink_to(target)
        except OSError as exc:
            pytest.skip(f"Filesystem sem permissao para links simbolicos: {exc}")

    prune_full_rescan_artifacts(str(db_path), keep=0)

    assert artifact.exists()
    assert marker.exists()
    if change == "identity":
        assert artifact.read_bytes() == b"arquivo do usuario"
    else:
        assert target.read_bytes() == b"arquivo do usuario"


def test_prune_full_rescan_artifacts_preserves_unowned_orphan_sidecar(
    tmp_path: Path,
) -> None:
    """Sem principal verificavel, o sidecar orfao permanece preservado."""
    db_path = tmp_path / "ssas.db"
    orphan_wal = (
        tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000001-wal"
    )
    orphan_wal.write_bytes(b"w")
    kept = _make_artifact(
        tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000002", 10
    )
    Path(f"{kept}-wal").write_bytes(b"w")

    prune_full_rescan_artifacts(str(db_path))

    assert orphan_wal.exists()
    assert kept.exists()
    assert Path(f"{kept}-wal").exists()


@pytest.mark.parametrize("empty_wal", [False, True])
def test_rotate_aborts_preserving_journal_when_checkpoint_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    empty_wal: bool,
) -> None:
    """Checkpoint que falha com -journal presente aborta a rotacao em vez
    de deletar os dados de recuperacao."""
    import core.import_database_rotation as rotation

    db_path = tmp_path / "ssas.db"
    _build_value_db(db_path, "primary_old")
    journal_sidecar = Path(f"{db_path}-journal")
    journal_sidecar.write_bytes(b"journal quente")
    wal_sidecar = Path(f"{db_path}-wal")
    if empty_wal:
        wal_sidecar.write_bytes(b"")

    monkeypatch.setattr(
        rotation,
        "force_wal_checkpoint",
        lambda *args, **kwargs: sqlite3.OperationalError("simulated busy"),
    )

    with pytest.raises(DatabaseError):
        rotate_preexisting_database_for_full_rescan(str(db_path))

    assert db_path.exists()
    # Antes de qualquer abertura do banco: o SQLite apagaria o journal
    # invalido na primeira conexao.
    assert journal_sidecar.exists()
    if empty_wal:
        assert wal_sidecar.exists()
    assert _read_value(db_path) == "primary_old"
    assert not list(tmp_path.glob("ssas.db.full_rescan_backup_*"))


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_promote_full_rescan_candidate_restores_sidecars_when_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rollback_fails: bool,
) -> None:
    """Falha na promocao restaura o backup com todos os sidecars movidos:
    sem isso o primario recuperado perderia o -journal de recuperacao."""
    import core.import_database_rotation as rotation

    primary_db = tmp_path / "ssas.db"
    candidate_db = tmp_path / "ssas.db.full_rescan_candidate_20260101_000000_000001"
    _build_value_db(primary_db, "primary_old")
    _build_value_db(candidate_db, "candidate_new")
    journal_sidecar = Path(f"{primary_db}-journal")
    journal_sidecar.write_bytes(b"journal quente de crash")

    # Sem o toque do SQLite, o journal artificial sobrevive ate a etapa
    # de movimentacao e e arquivado junto com o backup.
    monkeypatch.setattr(
        rotation, "force_wal_checkpoint", lambda *args, **kwargs: None
    )

    def _replace_with_candidate_failure(source: str, target: str) -> None:
        if Path(target) == primary_db and (
            Path(source) == candidate_db or rollback_fails
        ):
            raise PermissionError("simulated promotion failure")
        os.replace(source, target)

    monkeypatch.setattr(
        rotation,
        "replace_sqlite_file_with_retry",
        _replace_with_candidate_failure,
    )

    with pytest.raises(DatabaseError):
        promote_full_rescan_candidate(str(candidate_db), str(primary_db))

    if rollback_fails:
        assert not primary_db.exists()
        backups = list(tmp_path.glob("ssas.db.full_rescan_backup_*"))
        principals = [p for p in backups if not p.name.endswith("-journal")]
        assert len(principals) == 1
        backup = principals[0]
        assert Path(f"{backup}-journal").read_bytes() == b"journal quente de crash"
        assert not journal_sidecar.exists()
        assert (tmp_path / f".ssa-full-rescan-{backup.name}.json").exists()
        assert _read_value(backup) == "primary_old"
        assert _read_value(candidate_db) == "candidate_new"
        return
    assert primary_db.exists()
    # Antes de qualquer abertura do banco: o SQLite apagaria o journal
    # invalido na primeira conexao.
    assert journal_sidecar.exists()
    assert journal_sidecar.read_bytes() == b"journal quente de crash"
    assert _read_value(primary_db) == "primary_old"
    assert candidate_db.exists()
    assert _read_value(candidate_db) == "candidate_new"
    assert not list(tmp_path.glob("ssas.db.full_rescan_backup_*"))
    assert not list(tmp_path.glob(".ssa-full-rescan-ssas.db.full_rescan_backup_*.json"))
