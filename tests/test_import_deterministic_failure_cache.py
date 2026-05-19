from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

import core.app_logic as app_logic
import extracao.extractor as extractor


def _patch_integrity_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_logic.database, "repair_database_if_needed", lambda *a, **k: True
    )
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


def test_import_single_file_preserves_extraction_error_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    xlsx_path = tmp_path / "bad.xlsx"
    xlsx_path.write_bytes(b"x")

    def _raise_extract(*_args, **_kwargs):
        raise extractor.ExtractionError(
            "Missing required columns after normalization: ['numero_ssa']",
            error_code="MISSING_REQUIRED_COLUMNS",
        )

    monkeypatch.setattr(app_logic.extractor, "extract_data_from_excel", _raise_extract)

    with pytest.raises(app_logic.ExtractionError) as excinfo:
        app_logic._import_single_file(
            str(xlsx_path),
            str(tmp_path / "db.sqlite"),
            "ssa_table",
        )

    assert excinfo.value.error_code == "MISSING_REQUIRED_COLUMNS"


def test_run_importer_updates_deterministic_failure_cache_by_error_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    bad_file = docs_dir / "Consulta SSA - bad.xlsx"
    bad_file.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )
    _patch_integrity_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic, "_get_files_to_process", lambda *a, **k: [str(bad_file)]
    )
    monkeypatch.setattr(
        app_logic, "_discover_derivadas_sheet_files", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *a, **k: (_ for _ in ()).throw(
            app_logic.ExtractionError(
                "Missing required columns after normalization: ['numero_ssa']",
                error_code="MISSING_REQUIRED_COLUMNS",
            )
        ),
    )

    deterministic_calls: list[list[str]] = []
    monkeypatch.setattr(
        app_logic,
        "_update_cache_for_deterministic_failures",
        lambda failed_files, cache_file, docs_dir: deterministic_calls.append(
            list(failed_files)
        ),
    )
    cache_after_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_after_calls.__setitem__("n", cache_after_calls["n"] + 1),
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        app_logic,
        "_write_import_run_report",
        lambda payload: captured.setdefault("payload", payload)
        or str(tmp_path / "report.json"),
    )

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is True
    assert deterministic_calls == [[str(bad_file)]]
    assert cache_after_calls["n"] == 0
    payload = cast(dict[str, Any], captured["payload"])
    assert payload["status"] == "deterministic_rejections_only"
    assert payload["reason"] == "all_candidates_rejected_by_deterministic_rules"


def test_run_importer_does_not_mark_cancelled_as_deterministic_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    cancelled_file = docs_dir / "Consulta SSA - cancel.xlsx"
    cancelled_file.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )
    _patch_integrity_ok(monkeypatch)
    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *a, **k: [str(cancelled_file)],
    )
    monkeypatch.setattr(
        app_logic, "_discover_derivadas_sheet_files", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *a, **k: (_ for _ in ()).throw(
            app_logic.ExtractionError(
                "operation cancelled",
                error_code="OPERATION_CANCELLED",
            )
        ),
    )

    deterministic_calls: list[list[str]] = []
    monkeypatch.setattr(
        app_logic,
        "_update_cache_for_deterministic_failures",
        lambda failed_files, cache_file, docs_dir: deterministic_calls.append(
            list(failed_files)
        ),
    )
    cache_after_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_after_calls.__setitem__("n", cache_after_calls["n"] + 1),
    )

    updated = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
        should_cancel=lambda: False,
    )

    assert updated is False
    assert deterministic_calls == [[]]
    assert cache_after_calls["n"] == 0


def test_discover_derivadas_sheet_files_returns_empty_on_listing_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_logic.caching,
        "get_all_xlsx_files",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("forced list failure")),
    )

    out = app_logic._discover_derivadas_sheet_files("/tmp/docs")

    assert out == []


def test_update_cache_for_deterministic_failures_tolerates_cache_merge_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], str, str]] = []

    def _explode(file_paths, cache_file, docs_dir):
        calls.append((list(file_paths), cache_file, docs_dir))
        raise RuntimeError("forced cache failure")

    monkeypatch.setattr(app_logic.caching, "update_cache_for_files", _explode)

    app_logic._update_cache_for_deterministic_failures(
        ["a.xlsx", "a.xlsx", "", "b.xlsx"],
        "/tmp/cache.json",
        "/tmp/docs",
    )

    assert calls == [(["a.xlsx", "b.xlsx"], "/tmp/cache.json", "/tmp/docs")]


def test_get_files_to_process_raises_cache_error_on_cache_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_logic.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(
        app_logic.caching,
        "get_files_to_process",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("cache broken")),
    )

    with pytest.raises(app_logic.CacheError, match="Falha na verificacao de arquivos"):
        app_logic._get_files_to_process("/tmp/docs", "/tmp/cache.json", False)


def test_update_cache_after_import_raises_cache_error_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_logic.caching,
        "update_cache_for_files",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("cache timeout")),
    )

    with pytest.raises(app_logic.CacheError, match="Falha ao atualizar o cache"):
        app_logic._update_cache_after_import(
            ["/tmp/a.xlsx"], "/tmp/cache.json", "/tmp/docs"
        )
