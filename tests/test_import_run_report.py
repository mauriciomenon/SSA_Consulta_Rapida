from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from armazenamento import database
from core import app_logic
from core import import_postprocess
from core import import_run_report


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _allow_tmp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )


def _mock_db_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_logic.database,
        "repair_database_if_needed",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )


def _init_minimal_ssa_db(db_path: Path, descricao: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa TEXT,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.execute("DELETE FROM ssa_table")
        conn.execute(
            """
            INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
            VALUES (?, ?, ?, ?)
            """,
            ("202500001", "OLD", "2025-01-01 00:00:00", descricao),
        )
        conn.commit()
    finally:
        conn.close()


def _read_descricao(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT descricao_ssa FROM ssa_table WHERE numero_ssa = ?",
            ("202500001",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return str(row[0])


def _init_runtime_ssa_db(db_path: Path) -> None:
    schema_path = _get_project_root() / "config" / "schema.sql"
    ok = database.initialize_database(str(db_path), str(schema_path))
    assert ok is True


def _read_ssa_state(
    db_path: Path,
    numero_ssa: str,
) -> tuple[str, str, str, str]:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT situacao, setor_executor, data_cadastro, arquivo_origem
            FROM ssa_table
            WHERE numero_ssa = ?
            """,
            (numero_ssa,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return (
        "" if row[0] is None else str(row[0]),
        "" if row[1] is None else str(row[1]),
        "" if row[2] is None else str(row[2]),
        "" if row[3] is None else str(row[3]),
    )


def _count_ssa_rows(db_path: Path, numero_ssa: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM ssa_table WHERE numero_ssa = ?",
            (numero_ssa,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return int(row[0])


def _build_ssa_import_df(
    *,
    numero_ssa: str,
    situacao: str,
    setor_executor: str,
    data_cadastro: str,
    descricao_ssa: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "numero_ssa": numero_ssa,
                "situacao": situacao,
                "setor_executor": setor_executor,
                "data_cadastro": data_cadastro,
                "descricao_ssa": descricao_ssa,
            }
        ]
    )


def _fake_extract_state_transition(file_path: str, should_cancel=None):  # noqa: ARG001
    marker = Path(file_path).read_text(encoding="utf-8")
    if marker == "old":
        return _build_ssa_import_df(
            numero_ssa="202500001",
            situacao="ADM",
            setor_executor="AAA1",
            data_cadastro="2025-01-01 00:00:00",
            descricao_ssa="ssa old",
        )
    return _build_ssa_import_df(
        numero_ssa="202500001",
        situacao="STE",
        setor_executor="BBB2",
        data_cadastro="2025-01-02 00:00:00",
        descricao_ssa="ssa new",
    )


def _fake_extract_state_transition_same_date(file_path: str, should_cancel=None):  # noqa: ARG001
    marker = Path(file_path).read_text(encoding="utf-8")
    if marker == "old":
        return _build_ssa_import_df(
            numero_ssa="202600654",
            situacao="ADM",
            setor_executor="IEE3",
            data_cadastro="2026-01-16 00:00:00",
            descricao_ssa="ssa old same date",
        )
    return _build_ssa_import_df(
        numero_ssa="202600654",
        situacao="STE",
        setor_executor="IEE3",
        data_cadastro="2026-01-16 00:00:00",
        descricao_ssa="ssa new same date",
    )


def _fake_extract_snapshot_conflict_by_filename(  # noqa: ARG001
    file_path: str, should_cancel=None
):
    name = Path(file_path).name
    if "25-03-2026" in name:
        return _build_ssa_import_df(
            numero_ssa="202600777",
            situacao="ADM",
            setor_executor="IEE3",
            data_cadastro="2026-03-27 00:00:00",
            descricao_ssa="snapshot antigo com data de cadastro maior",
        )
    return _build_ssa_import_df(
        numero_ssa="202600777",
        situacao="ADM",
        setor_executor="IEE3",
        data_cadastro="2026-03-26 00:00:00",
        descricao_ssa="snapshot novo com data de cadastro menor",
    )


def _fake_extract_generic_order_sensitive(file_path: str, should_cancel=None):  # noqa: ARG001
    name = Path(file_path).name.casefold()
    is_new = "new" in name
    return _build_ssa_import_df(
        numero_ssa="202600778",
        situacao="ADM",
        setor_executor="IEE3",
        data_cadastro="2026-03-26 00:00:00",
        descricao_ssa="payload_new" if is_new else "payload_old",
    )


def _write_real_ssa_excel(
    file_path: Path,
    *,
    numero_ssa: str,
    situacao: str,
    setor_executor: str,
    data_cadastro: str,
    descricao_ssa: str,
) -> None:
    df = pd.DataFrame(
        [
            {
                "Numero SSA": numero_ssa,
                "Situacao": situacao,
                "Setor Executor": setor_executor,
                "Emitida Em": data_cadastro,
                "Descricao": descricao_ssa,
            }
        ]
    )
    df.to_excel(file_path, index=False)


def _prepare_runtime_import_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"

    _allow_tmp_path(monkeypatch, tmp_path)
    _init_runtime_ssa_db(db_path)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_state_transition,
    )
    return docs_dir, data_dir, db_path


def test_run_importer_logic_writes_report_on_no_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "legado.xls").write_text("legacy", encoding="utf-8")
    data_dir = tmp_path / "data"

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is False
    assert "payload" in captured
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "no_changes"
    assert payload["result"] is False
    assert payload["counts"]["total_candidates"] == 0
    assert payload["counts"]["success_count"] == 0
    assert payload["counts"]["ignored_legacy_excel_count"] == 1
    assert payload["files"]["ignored_legacy_excel"] == ["legado.xls"]


def test_run_importer_logic_explicit_files_bypass_discovery_and_process_only_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("discovery nao deveria ser chamado no modo explicito")
        ),
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("derivadas discovery nao deveria rodar no modo explicito")
        ),
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    seen: list[str] = []
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda file_path, *args, **kwargs: (seen.append(str(file_path)) or True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
        explicit_files=[str(file_ok)],
    )

    assert updated is True
    assert seen == [str(file_ok)]


def test_run_importer_logic_writes_report_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")
    (docs_dir / "legado.xls").write_text("legacy", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake_success.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    assert "payload" in captured
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "updated"
    assert payload["result"] is True
    assert payload["counts"]["total_candidates"] == 1
    assert payload["counts"]["success_count"] == 1
    assert payload["counts"]["ignored_legacy_excel_count"] == 1
    assert payload["files"]["success"] == ["ok.xlsx"]
    assert payload["files"]["ignored_legacy_excel"] == ["legado.xls"]


def test_run_importer_logic_diff_processes_only_new_files_after_cache_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_old = docs_dir / "old.xlsx"
    file_old.write_text("old", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    first_seen: list[str] = []
    second_seen: list[str] = []

    def _import_first(file_path: str, *args, **kwargs) -> tuple[bool, int]:
        first_seen.append(Path(file_path).name)
        return True, 1

    monkeypatch.setattr(app_logic, "_import_single_file", _import_first)
    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )
    assert first_seen == ["old.xlsx"]

    file_new = docs_dir / "new.xlsx"
    file_new.write_text("new", encoding="utf-8")

    def _import_second(file_path: str, *args, **kwargs) -> tuple[bool, int]:
        second_seen.append(Path(file_path).name)
        return True, 1

    monkeypatch.setattr(app_logic, "_import_single_file", _import_second)
    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )
    assert second_seen == ["new.xlsx"]


def test_import_explicit_files_to_database_updates_existing_ssa_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert _read_ssa_state(db_path, "202500001") == (
        "ADM",
        "AAA1",
        "2025-01-01 00:00:00",
        "old.xlsx",
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "new.xlsx",
    )


def test_import_explicit_files_to_database_preserves_newer_state_against_older_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "new.xlsx",
    )


def test_import_explicit_files_to_database_same_date_does_not_downgrade_situacao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_state_transition_same_date,
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert _count_ssa_rows(db_path, "202600654") == 1
    assert _read_ssa_state(db_path, "202600654") == (
        "STE",
        "IEE3",
        "2026-01-16 00:00:00",
        "new.xlsx",
    )


def test_run_importer_logic_diff_reprocesses_modified_file_and_updates_existing_ssa(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    tracked_file = docs_dir / "tracked.xlsx"
    tracked_file.write_text("old", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )
    assert _read_ssa_state(db_path, "202500001") == (
        "ADM",
        "AAA1",
        "2025-01-01 00:00:00",
        "tracked.xlsx",
    )

    tracked_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )
    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "tracked.xlsx",
    )


def test_run_importer_logic_diff_reprocess_older_file_does_not_downgrade_existing_ssa(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    tracked_file = docs_dir / "tracked.xlsx"
    tracked_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    tracked_file.write_text("old", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "tracked.xlsx",
    )


def test_import_explicit_files_to_database_real_xlsx_batch_preserves_newest_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"

    _write_real_ssa_excel(
        old_file,
        numero_ssa="202500001",
        situacao="ADM",
        setor_executor="AAA1",
        data_cadastro="2025-01-01 00:00:00",
        descricao_ssa="ssa old real",
    )
    _write_real_ssa_excel(
        new_file,
        numero_ssa="202500001",
        situacao="STE",
        setor_executor="BBB2",
        data_cadastro="2025-01-02 00:00:00",
        descricao_ssa="ssa new real",
    )

    _allow_tmp_path(monkeypatch, tmp_path)
    _init_runtime_ssa_db(db_path)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file), str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "new.xlsx",
    )


def test_import_explicit_older_snapshot_cannot_override_newer_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    newer_file = docs_dir / "Consulta SSA - 26-03-2026_0237PM.xlsx"
    older_file = docs_dir / "Consulta SSA - 25-03-2026_0237PM.xlsx"
    newer_file.write_text("new", encoding="utf-8")
    older_file.write_text("old", encoding="utf-8")
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_snapshot_conflict_by_filename,
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(newer_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert (
        app_logic.import_explicit_files_to_database(
            [str(older_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202600777") == 1
    assert _read_ssa_state(db_path, "202600777") == (
        "ADM",
        "IEE3",
        "2026-03-26 00:00:00",
        "Consulta SSA - 26-03-2026_0237PM.xlsx",
    )


def test_import_explicit_generic_names_use_mtime_for_deterministic_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    old_file = docs_dir / "generic_old.xlsx"
    new_file = docs_dir / "generic_new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    now = time.time()
    os.utime(old_file, (now - 120, now - 120))
    os.utime(new_file, (now - 60, now - 60))

    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_generic_order_sensitive,
    )

    # Reversed input list should still end with newer mtime applied last.
    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file), str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202600778") == 1
    assert _read_ssa_state(db_path, "202600778") == (
        "ADM",
        "IEE3",
        "2026-03-26 00:00:00",
        "generic_new.xlsx",
    )


def test_import_explicit_generic_older_file_cannot_override_newer_via_data_arquivo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_runtime_import_update(tmp_path, monkeypatch)
    old_file = docs_dir / "generic_old.xlsx"
    new_file = docs_dir / "generic_new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    now = time.time()
    os.utime(old_file, (now - 120, now - 120))
    os.utime(new_file, (now - 60, now - 60))

    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_generic_order_sensitive,
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202600778") == 1
    assert _read_ssa_state(db_path, "202600778") == (
        "ADM",
        "IEE3",
        "2026-03-26 00:00:00",
        "generic_new.xlsx",
    )


def test_run_importer_logic_diff_real_xlsx_modified_file_updates_without_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    tracked_file = docs_dir / "tracked.xlsx"

    _allow_tmp_path(monkeypatch, tmp_path)
    _init_runtime_ssa_db(db_path)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )

    _write_real_ssa_excel(
        tracked_file,
        numero_ssa="202500001",
        situacao="STE",
        setor_executor="BBB2",
        data_cadastro="2025-01-02 00:00:00",
        descricao_ssa="ssa new real",
    )
    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    _write_real_ssa_excel(
        tracked_file,
        numero_ssa="202500001",
        situacao="ADM",
        setor_executor="AAA1",
        data_cadastro="2025-01-01 00:00:00",
        descricao_ssa="ssa old real",
    )
    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    assert _count_ssa_rows(db_path, "202500001") == 1
    assert _read_ssa_state(db_path, "202500001") == (
        "STE",
        "BBB2",
        "2025-01-02 00:00:00",
        "tracked.xlsx",
    )


def test_run_importer_logic_report_includes_file_phase_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    def _fake_import_single_file(
        file_path: str, db_path: str, *args, **kwargs
    ) -> tuple[bool, int]:
        metrics_out = kwargs.get("_metrics_out")
        if isinstance(metrics_out, dict):
            metrics_out.update(
                {
                    "file": "ok.xlsx",
                    "status": "success",
                    "durations": {
                        "extraction_seconds": 0.123,
                        "validation_seconds": 0.045,
                        "insert_seconds": 0.067,
                    },
                    "counts": {
                        "rows_extracted": 10,
                        "rows_before_invalid_filter": 12,
                        "rows_removed_invalid_identity": 2,
                        "rows_removed_required_validation": 1,
                        "rows_ready_for_insert": 7,
                        "rows_inserted": 7,
                    },
                    "invalid_identity_tracked": True,
                    "invalid_identity": {
                        "total_removed": 2,
                        "empty_removed": 1,
                        "payload_removed": 1,
                        "payload_columns_sample": [
                            "data_cadastro",
                            "responsavel_execucao",
                        ],
                    },
                }
            )
        return True, 7

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_fake_metrics.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["counts"]["rows_extracted_total"] == 10
    assert payload["counts"]["rows_removed_invalid_identity_total"] == 2
    assert payload["counts"]["rows_ready_for_insert_total"] == 7
    assert payload["counts"]["rows_inserted_total"] == 7
    assert payload["durations"]["sum_file_extraction_seconds"] == 0.123
    assert payload["durations"]["sum_file_validation_seconds"] == 0.045
    assert payload["durations"]["sum_file_insert_seconds"] == 0.067
    assert "run_file_processing_seconds" in payload["durations"]
    assert "run_success_cache_update_seconds" in payload["durations"]
    assert "run_postprocess_move_seconds" in payload["durations"]
    assert "run_deterministic_cache_update_seconds" in payload["durations"]
    assert payload["file_reports"] == [
        {
            "file": "ok.xlsx",
            "status": "success",
            "durations": {
                "extraction_seconds": 0.123,
                "validation_seconds": 0.045,
                "insert_seconds": 0.067,
            },
            "counts": {
                "rows_extracted": 10,
                "rows_before_invalid_filter": 12,
                "rows_removed_invalid_identity": 2,
                "rows_removed_required_validation": 1,
                "rows_ready_for_insert": 7,
                "rows_inserted": 7,
            },
            "invalid_identity_tracked": True,
            "invalid_identity": {
                "total_removed": 2,
                "empty_removed": 1,
                "payload_removed": 1,
                "payload_columns_sample": ["data_cadastro", "responsavel_execucao"],
            },
        }
    ]


def test_run_importer_logic_moves_processed_files_and_updates_cache_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_empty = docs_dir / "empty.xlsx"
    file_ok.write_text("placeholder-ok", encoding="utf-8")
    file_empty.write_text("placeholder-empty", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_load_import_discovery_settings",
        lambda: {
            "include_processadas": False,
            "processadas_subdir": "processadas",
            "ignore_subdirs": ["nosurvivor"],
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": True,
            "route_zero_survivor_to_nosurvivor": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok), str(file_empty)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )

    def _fake_import_single_file(
        file_path: str, db_path: str, *args, **kwargs
    ) -> tuple[bool, int]:
        if Path(file_path).name == "empty.xlsx":
            return True, 0
        return True, 5

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_for_deterministic_failures",
        lambda failed_files, cache_file, docs_dir: None,
    )

    captured_cache: dict[str, Any] = {}

    def _capture_cache_paths(
        processed_files: list[str], cache_file: str, docs_dir: str
    ) -> None:
        captured_cache["paths"] = list(processed_files)
        captured_cache["cache_file"] = cache_file
        captured_cache["docs_dir"] = docs_dir

    monkeypatch.setattr(app_logic, "_update_cache_after_import", _capture_cache_paths)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    moved_ok = docs_dir / "processadas" / "ok.xlsx"
    moved_empty = docs_dir / "processadas" / "nosurvivor" / "empty.xlsx"
    assert moved_ok.exists()
    assert moved_empty.exists()
    assert not file_ok.exists()
    assert not file_empty.exists()
    assert "paths" in captured_cache
    assert sorted(Path(p).name for p in cast(list[str], captured_cache["paths"])) == [
        "empty.xlsx",
        "ok.xlsx",
    ]
    assert str(moved_ok) in cast(list[str], captured_cache["paths"])
    assert str(moved_empty) in cast(list[str], captured_cache["paths"])


def test_run_importer_logic_full_rescan_disables_postprocess_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder-ok", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_load_import_discovery_settings",
        lambda: {
            "include_processadas": False,
            "processadas_subdir": "processadas",
            "ignore_subdirs": ["nosurvivor"],
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": True,
            "route_zero_survivor_to_nosurvivor": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_promote_full_rescan_candidate",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    move_called = {"value": False}

    def _capture_move(**kwargs: Any) -> dict[str, str]:
        move_called["value"] = True
        return {}

    monkeypatch.setattr(app_logic, "_apply_postprocess_file_moves", _capture_move)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert move_called["value"] is False
    assert file_ok.exists()


def test_run_importer_logic_full_rescan_enforces_subdir_policy_and_upsert_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder-ok", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    _mock_db_ok(monkeypatch)

    monkeypatch.setattr(
        app_logic,
        "_load_import_discovery_settings",
        lambda: {
            "include_processadas": True,
            "processadas_subdir": "processadas",
            "ignore_subdirs": [],
            "nosurvivor_subdir": "nosurvivor",
            "move_processed_after_import": True,
            "route_zero_survivor_to_nosurvivor": True,
            "upsert_short_circuit_policy": "all_short",
        },
    )

    captured: dict[str, Any] = {}

    def _capture_get_files_to_process(*args, **kwargs):
        captured["get_files_kwargs"] = dict(kwargs)
        return [str(file_ok)]

    def _capture_discover_derivadas(*args, **kwargs):
        captured["discover_kwargs"] = dict(kwargs)
        return []

    monkeypatch.setattr(
        app_logic, "_get_files_to_process", _capture_get_files_to_process
    )
    monkeypatch.setattr(
        app_logic, "_discover_derivadas_sheet_files", _capture_discover_derivadas
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, 1),
    )
    monkeypatch.setattr(
        app_logic,
        "_promote_full_rescan_candidate",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )
    move_called = {"value": False}

    def _capture_move(**kwargs: Any) -> dict[str, str]:
        move_called["value"] = True
        return {}

    monkeypatch.setattr(app_logic, "_apply_postprocess_file_moves", _capture_move)

    captured_policy: dict[str, Any] = {}

    def _capture_policy(policy: str | None) -> None:
        captured_policy["value"] = policy

    monkeypatch.setattr(
        app_logic.database,
        "configure_upsert_short_circuit_policy",
        _capture_policy,
    )

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert captured_policy["value"] == "all_short"
    assert captured["get_files_kwargs"]["include_processadas"] is True
    assert captured["discover_kwargs"]["include_processadas"] is True
    assert captured["get_files_kwargs"]["ignore_subdirs"] == ["nosurvivor"]
    assert captured["discover_kwargs"]["ignore_subdirs"] == ["nosurvivor"]
    assert move_called["value"] is False


def test_load_import_discovery_settings_invalid_upsert_policy_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import config_manager

    monkeypatch.setattr(
        config_manager,
        "load_settings",
        lambda: {
            "import_settings": {
                "include_processadas_in_full_rescan": False,
                "processadas_subdir": "processadas",
                "ignore_nosurvivor_in_full_rescan": True,
                "nosurvivor_subdir": "nosurvivor",
                "move_processed_after_import": False,
                "route_zero_survivor_to_nosurvivor": True,
                "upsert_short_circuit_policy": "invalida",
            }
        },
    )
    settings = app_logic._load_import_discovery_settings()
    assert settings["upsert_short_circuit_policy"] == "consulta_only"


def test_load_import_discovery_settings_falls_back_on_non_mapping_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import config_manager

    monkeypatch.setattr(config_manager, "load_settings", lambda: [])

    settings = app_logic._load_import_discovery_settings()

    assert settings["processadas_subdir"] == "processadas"
    assert settings["upsert_short_circuit_policy"] == "consulta_only"


def test_move_file_after_import_returns_original_on_move_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    source = docs_dir / "arquivo.xlsx"
    source.write_text("ok", encoding="utf-8")

    def _raise_move(src: str, dst: str) -> str:
        raise OSError("move blocked")

    monkeypatch.setattr(import_postprocess.shutil, "move", _raise_move)

    final_path = import_postprocess.move_file_after_import(
        file_path=str(source),
        docs_dir=str(docs_dir),
        destination_root=(docs_dir / "processadas").resolve(),
    )

    assert final_path == str(source)
    assert source.exists()


def test_write_import_run_report_returns_none_on_open_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "run_id": "test_run",
        "started_at": "2026-04-16T00:00:00",
        "finished_at": "2026-04-16T00:00:01",
    }

    def _raise_open(*args, **kwargs):
        raise ValueError("invalid path")

    monkeypatch.setattr(import_run_report, "open", _raise_open, raising=False)

    assert app_logic._write_import_run_report(payload) is None


def test_write_import_run_report_uses_runtime_root_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("SSA_RUNTIME_ROOT", str(runtime_root))
    payload = {
        "run_id": "runtime_run",
        "started_at": "2026-04-16T00:00:00",
        "finished_at": "2026-04-16T00:00:01",
    }

    report_path = app_logic._write_import_run_report(payload)

    assert report_path is not None
    assert Path(report_path) == runtime_root / "logs" / "import_run_runtime_run.json"
    assert Path(report_path).is_file()


def test_run_importer_logic_full_rescan_failure_preserves_primary_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_bad = docs_dir / "bad.xlsx"
    file_bad.write_text("placeholder", encoding="utf-8")
    primary_db = data_dir / "test.db"
    _init_minimal_ssa_db(primary_db, "primary_old")

    _allow_tmp_path(monkeypatch, tmp_path)

    def _fake_repair(db_path: str, *args, **kwargs) -> bool:
        path = Path(db_path)
        if not path.exists():
            _init_minimal_ssa_db(path, "candidate_seed")
        return True

    monkeypatch.setattr(app_logic.database, "repair_database_if_needed", _fake_repair)
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_bad)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            app_logic.ExtractionError("boom", error_code="MISSING_REQUIRED_COLUMNS")
        ),
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_full_rescan_failure.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert _read_descricao(primary_db) == "primary_old"
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "deterministic_rejections_only"
    assert payload["reason"] == "all_candidates_rejected_by_deterministic_rules"
    assert payload["counts"]["deterministic_failure_count"] == 1
    candidate_path = Path(str(payload["paths"]["candidate_db_path"]))
    assert candidate_path.exists()
    assert payload["paths"]["candidate_preserved"] is True
    assert payload["paths"]["working_db_path"] == str(candidate_path)


def test_run_importer_logic_full_rescan_success_promotes_candidate_at_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_ok = docs_dir / "ok.xlsx"
    file_ok.write_text("placeholder", encoding="utf-8")
    primary_db = data_dir / "test.db"
    _init_minimal_ssa_db(primary_db, "primary_old")

    _allow_tmp_path(monkeypatch, tmp_path)

    def _fake_repair(db_path: str, *args, **kwargs) -> bool:
        path = Path(db_path)
        if not path.exists():
            _init_minimal_ssa_db(path, "candidate_seed")
        return True

    monkeypatch.setattr(app_logic.database, "repair_database_if_needed", _fake_repair)
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *args, **kwargs: {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
        },
    )
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *args, **kwargs: [str(file_ok)],
    )
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )

    def _fake_import_single_file(
        file_path: str, db_path: str, *args, **kwargs
    ) -> tuple[bool, int]:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("DELETE FROM ssa_table")
            conn.execute(
                """
                INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
                VALUES (?, ?, ?, ?)
                """,
                ("202500001", "NEW", "2025-02-01 00:00:00", "candidate_new"),
            )
            conn.commit()
        finally:
            conn.close()
        return True, 1

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import_single_file)
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *args, **kwargs: None,
    )

    captured: dict[str, Any] = {}

    def _fake_write(payload: dict) -> str:
        captured["payload"] = payload
        return str(tmp_path / "import_run_full_rescan_success.json")

    monkeypatch.setattr(app_logic, "_write_import_run_report", _fake_write)

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert _read_descricao(primary_db) == "candidate_new"
    backups = sorted(data_dir.glob("test.db.full_rescan_backup_*"))
    assert backups
    assert _read_descricao(backups[-1]) == "primary_old"
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["paths"]["working_db_path"] == str(primary_db)
    assert payload["paths"]["promoted_backup_path"] is not None
    candidate_path = Path(str(payload["paths"]["candidate_db_path"]))
    assert not candidate_path.exists()
    assert payload["paths"]["candidate_preserved"] is False
