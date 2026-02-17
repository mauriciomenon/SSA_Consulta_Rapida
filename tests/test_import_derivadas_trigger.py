from __future__ import annotations

from pathlib import Path

import pytest

from core.app_logic import run_importer_logic


def _patch_integrity_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic.database, "repair_database_if_needed", lambda *a, **k: True)
    monkeypatch.setattr(
        app_logic.database,
        "verify_database_integrity",
        lambda *a, **k: {
            "is_valid": True,
            "database_accessible": True,
            "table_exists": True,
            "schema_valid": True,
            "data_consistent": True,
            "disk_space_sufficient": True,
            "warnings": [],
            "issues": [],
        },
    )


def test_run_importer_triggers_derivadas_sync_for_special_sheets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    regular = docs_dir / "Consulta SSA - 13-02-2026_0121PM.xlsx"
    special_old = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0124PM.xlsx"
    special_new = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0137PM.xlsx"
    regular.write_bytes(b"x")
    special_old.write_bytes(b"x")
    special_new.write_bytes(b"x")
    special_old.touch()
    special_new.touch()

    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path])
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [str(regular), str(special_old), str(special_new)])

    imported_files: list[str] = []

    def _fake_import(file_path: str, *args, **kwargs):
        imported_files.append(file_path)
        return True, 3

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import)

    sync_calls: list[dict] = []

    def _fake_sync(**kwargs):
        sync_calls.append(kwargs)
        return {"merge_stats": {"merged_edges": 7}}

    monkeypatch.setattr(app_logic, "sync_derivadas", _fake_sync)

    cached_files: list[str] = []

    def _fake_cache_update(processed_files, cache_file, docs_dir):
        cached_files.extend(processed_files)

    monkeypatch.setattr(app_logic, "_update_cache_after_import", _fake_cache_update)

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    assert imported_files == [str(regular)]
    assert len(sync_calls) == 1
    assert "sheet_file" not in sync_calls[0] or sync_calls[0]["sheet_file"] is None
    assert sorted(sync_calls[0]["sheet_files"]) == sorted([str(special_old), str(special_new)])
    assert set(cached_files) == {str(regular), str(special_old), str(special_new)}


def test_run_importer_keeps_running_when_derivadas_sync_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path])
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [str(special)])
    monkeypatch.setattr(app_logic, "sync_derivadas", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("sync boom")))

    cache_calls = {"n": 0}
    monkeypatch.setattr(app_logic, "_update_cache_after_import", lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1))

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is False
    assert cache_calls["n"] == 0
