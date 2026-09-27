"""Recuperacao conserva o banco e invalida hashes de um estado posterior."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TypedDict

import pandas as pd
import pytest

from armazenamento import database_integrity
from core.app_logic import run_importer_logic
from core.import_errors import ImporterError
from core.import_outcome import ImportStatus, get_last_import_outcome


class ImportArguments(TypedDict):
    docs_dir: str
    data_dir: str
    extra_allowed_roots: list[str]


def _write_source(path: Path, numero: str) -> None:
    pd.DataFrame(
        {
            "numero_ssa": [numero],
            "descricao_ssa": ["Fonte de teste"],
            "data_cadastro": ["2026-09-01 08:00:00"],
        }
    ).to_excel(path, index=False)


def _rows(db: Path) -> list[str]:
    with closing(sqlite3.connect(db)) as conn:
        return [
            row[0]
            for row in conn.execute("SELECT numero_ssa FROM ssa_table ORDER BY numero_ssa")
        ]


@pytest.fixture
def recovery_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(tmp_path))
    docs = tmp_path / "docs_entrada"
    docs.mkdir()
    data = tmp_path / "data"
    args: ImportArguments = {
        "docs_dir": str(docs),
        "data_dir": str(data),
        "extra_allowed_roots": [str(tmp_path)],
    }
    _write_source(docs / "a.xlsx", "202640001")
    assert run_importer_logic(**args)
    db = data / "ssas.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute(
            "INSERT INTO ssa_table (numero_ssa, descricao_ssa, situacao, data_cadastro) "
            "VALUES ('202649999', 'Linha manual', 'ADM', '2026-09-01 08:00:00')"
        )
    assert database_integrity._create_integrity_snapshot(str(db), force=True)
    _write_source(docs / "b.xlsx", "202640002")
    assert run_importer_logic(**args)
    assert _rows(db) == ["202640001", "202640002", "202649999"]
    return docs, data, db, args


@pytest.mark.parametrize("missing", [False, True])
def test_restore_reimports_cached_sources_and_preserves_manual_rows(
    recovery_workspace, missing
):
    _docs, data, db, args = recovery_workspace
    if missing:
        db.unlink()
    else:
        db.write_bytes(b"Banco corrompido para teste")

    assert run_importer_logic(**args)

    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.UPDATED
    assert outcome.integrity_report["restored_from_snapshot"]
    assert outcome.processed_file_count == 2
    assert _rows(db) == ["202640001", "202640002", "202649999"]
    assert not list(data.glob("*.full_rescan_candidate_*"))
    assert not run_importer_logic(**args)
    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.NO_CHANGES


def test_recovery_marker_survives_restore_before_importer_resumes(recovery_workspace):
    _docs, data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")
    assert database_integrity.ensure_database_integrity(str(db))[0]
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()
    assert "b.xlsx" in json.loads((data / "file_cache.json").read_text())
    assert _rows(db) == ["202640001", "202649999"]

    assert run_importer_logic(**args)

    assert not marker.exists()
    assert _rows(db) == ["202640001", "202640002", "202649999"]


def test_fresh_database_creation_marks_cache_for_revalidation(recovery_workspace):
    _docs, data, db, args = recovery_workspace
    db.unlink()
    for snapshot in (data / "historico_backups").iterdir():
        snapshot.unlink()

    assert database_integrity.ensure_database_integrity(str(db))[0]
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()

    assert run_importer_logic(**args)

    assert not marker.exists()
    assert _rows(db) == ["202640001", "202640002"]


def test_recovery_keeps_explicit_scope_and_pending_sources_eligible(recovery_workspace):
    docs, data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")

    assert run_importer_logic(**args, explicit_files=[docs / "a.xlsx"])

    assert _rows(db) == ["202640001", "202649999"]
    cache = json.loads((data / "file_cache.json").read_text())
    assert set(cache) == {"a.xlsx"}
    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.processed_file_count == 1
    assert any("cobertura" in warning for warning in outcome.integrity_report["warnings"])
    assert run_importer_logic(**args)
    assert _rows(db) == ["202640001", "202640002", "202649999"]


@pytest.mark.parametrize("destination", [None, "processadas", "processadas/nosurvivor"])
def test_recovery_does_not_expand_discovery_or_recreate_missing_source(
    recovery_workspace, destination
):
    docs, _data, db, args = recovery_workspace
    source = docs / "b.xlsx"
    if destination is None:
        source.unlink()
    else:
        target_dir = docs / destination
        target_dir.mkdir(parents=True)
        source.rename(target_dir / source.name)
    db.write_bytes(b"Banco corrompido para teste")

    assert run_importer_logic(**args)

    assert _rows(db) == ["202640001", "202649999"]
    assert not source.exists()
    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.processed_file_count == 1
    assert any("cobertura" in warning for warning in outcome.integrity_report["warnings"])


def test_failed_cache_invalidation_keeps_marker_and_retries(recovery_workspace):
    _docs, data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")
    cache = data / "file_cache.json"
    saved_cache = data / "original_cache.json"
    cache.rename(saved_cache)
    cache.mkdir()

    with pytest.raises(ImporterError):
        run_importer_logic(**args)

    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()
    assert _rows(db) == ["202640001", "202649999"]
    cache.rmdir()
    saved_cache.rename(cache)
    assert run_importer_logic(**args)
    assert not marker.exists()
    assert _rows(db) == ["202640001", "202640002", "202649999"]


def test_cancel_after_cache_invalidation_keeps_sources_eligible(recovery_workspace):
    _docs, data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")
    assert database_integrity.ensure_database_integrity(str(db))[0]
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")

    assert not run_importer_logic(**args, should_cancel=lambda: not marker.exists())

    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.CANCELLED
    assert json.loads((data / "file_cache.json").read_text()) == {}
    assert run_importer_logic(**args)
    assert _rows(db) == ["202640001", "202640002", "202649999"]


def test_recovery_invalidates_only_selected_database_cache(recovery_workspace):
    _docs, data, db, args = recovery_workspace
    assert run_importer_logic(**args, db_name="alternate.db")
    other_cache = data / "file_cache.alternate.db.json"
    original = other_cache.read_bytes()
    db.write_bytes(b"Banco corrompido para teste")

    assert run_importer_logic(**args)

    assert other_cache.read_bytes() == original


def test_full_rescan_consumes_marker_without_extra_incremental_run(
    recovery_workspace,
):
    _docs, data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")
    assert database_integrity.ensure_database_integrity(str(db))[0]
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()

    assert run_importer_logic(**args, force_import=True)

    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.UPDATED
    assert not marker.exists()
    # Full rescan reconstroi o banco a partir das fontes; a linha manual
    # inserida direto no primario nao faz parte desse escopo.
    assert _rows(db) == ["202640001", "202640002"]

    assert not run_importer_logic(**args)
    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.NO_CHANGES
    assert outcome.processed_file_count == 0
    assert not marker.exists()


def test_failed_full_rescan_preserves_marker_for_next_incremental(
    recovery_workspace, monkeypatch: pytest.MonkeyPatch
):
    _docs, _data, db, args = recovery_workspace
    db.write_bytes(b"Banco corrompido para teste")
    assert database_integrity.ensure_database_integrity(str(db))[0]
    marker = Path(f"{db}{database_integrity.IMPORT_CACHE_RECOVERY_SUFFIX}")
    assert marker.is_file()

    import core.app_logic as app_logic
    from core.import_errors import DatabaseError

    def fail_promote(*_args: object, **_kwargs: object) -> None:
        raise DatabaseError("promocao simulada falhou")

    monkeypatch.setattr(app_logic, "_promote_full_rescan_candidate", fail_promote)
    assert not run_importer_logic(**args, force_import=True)

    # A rodada falhou antes da promocao: o primario continua sendo o
    # snapshot restaurado e o marcador precisa sobreviver para forcar a
    # revalidacao do cache no proximo incremental.
    assert marker.is_file()
    assert _rows(db) == ["202640001", "202649999"]

    assert run_importer_logic(**args)
    assert not marker.exists()
    assert _rows(db) == ["202640001", "202640002", "202649999"]


def test_recovery_recaches_deterministic_rejections_without_repeating_forever(
    recovery_workspace,
):
    docs, _data, db, args = recovery_workspace
    pd.DataFrame({"coluna_desconhecida": ["valor"]}).to_excel(
        docs / "rejected.xlsx", index=False
    )
    assert not run_importer_logic(**args)
    db.write_bytes(b"Banco corrompido para teste")

    assert run_importer_logic(**args)

    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.UPDATED
    assert outcome.deterministic_failure_count == 1
    assert not run_importer_logic(**args)
    outcome = get_last_import_outcome()
    assert outcome is not None
    assert outcome.status is ImportStatus.NO_CHANGES
    assert outcome.total_candidates == 0
