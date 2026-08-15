from __future__ import annotations

from pathlib import Path

import pytest

from core.app_logic import run_importer_logic


def _patch_integrity_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.app_logic as app_logic

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
    monkeypatch.setattr(
        app_logic,
        "scan_derivadas_consistency",
        lambda *a, **k: {
            "schema_ready": True,
            "is_consistent": True,
            "issue_counts": {
                "missing_source_pairs": 0,
                "source_without_matrix_pairs": 0,
                "flag_mismatch_pairs": 0,
                "invalid_matrix_pairs": 0,
                "closure_self_rows": 0,
                "summary_missing_nodes": 0,
                "summary_extra_nodes": 0,
                "fingerprint_mismatch": 0,
            },
        },
    )


def test_run_importer_triggers_derivadas_sync_for_special_sheets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic,
        "_get_files_to_process",
        lambda *a, **k: [str(regular), str(special_old), str(special_new)],
    )

    imported_files: list[str] = []

    def _fake_import(file_path: str, *args, **kwargs):
        imported_files.append(file_path)
        metrics_out = kwargs.get("_metrics_out")
        assert isinstance(metrics_out, dict)
        metrics_out.update(
            {"counts": {"ssa_inserted": 3, "ssa_updated": 0}}
        )
        return True, 3

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import)

    sync_calls: list[dict] = []

    def _fake_sync(**kwargs):
        current_files = list(kwargs.get("sheet_files") or [])
        sync_calls.append(kwargs)
        return {
            "merge_stats": {"merged_edges": 7},
            "sheet_files": current_files,
            "sheet_stats": {"accepted_edges": 7, "special_layout_detected": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": current_file,
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 3, "special_layout_detected": 1},
                }
                for current_file in current_files
            ],
        }

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
    assert sync_calls[0]["actor"] == "importer-derivadas-sync"
    assert "sheet_file" not in sync_calls[0] or sync_calls[0]["sheet_file"] is None
    assert sorted(sync_calls[0]["sheet_files"]) == sorted(
        [str(special_old), str(special_new)]
    )
    assert set(cached_files) == {str(regular), str(special_old), str(special_new)}


def test_run_importer_keeps_running_when_derivadas_sync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic, "_get_files_to_process", lambda *a, **k: [str(special)]
    )
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("sync boom")),
    )

    cache_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert cache_calls["n"] == 0


def test_run_importer_runs_dedicated_derivadas_phase_even_without_regular_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    import_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *a, **k: import_calls.__setitem__("n", import_calls["n"] + 1),
    )

    sync_calls: list[dict] = []

    def _fake_sync(**kwargs):
        current_files = list(kwargs.get("sheet_files") or [])
        sync_calls.append(kwargs)
        return {
            "merge_stats": {"merged_edges": 2},
            "sheet_files": current_files,
            "sheet_stats": {"accepted_edges": 2, "special_layout_detected": 1},
            "sheet_file_reports": [
                {
                    "sheet_file": current_file,
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 2, "special_layout_detected": 1},
                }
                for current_file in current_files
            ],
        }

    monkeypatch.setattr(app_logic, "sync_derivadas", _fake_sync)

    cached_files: list[str] = []
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda processed_files, *a, **k: cached_files.extend(processed_files),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert import_calls["n"] == 0
    assert len(sync_calls) == 1
    assert sync_calls[0]["include_db_source"] is True
    assert sync_calls[0]["actor"] == "importer-derivadas-sync"
    assert sync_calls[0]["sheet_files"] == [str(special)]
    assert cached_files == [str(special)]


def test_run_importer_rejects_special_sync_without_parse_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": [],
            "sheet_stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "merge_stats": {"merged_edges": 0},
        },
    )

    cache_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert cache_calls["n"] == 0


def test_run_importer_runs_db_only_derivadas_sync_for_regular_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    regular = docs_dir / "Consulta SSA - 13-02-2026_0121PM.xlsx"
    regular.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic, "_get_files_to_process", lambda *a, **k: [str(regular)]
    )
    def _fake_import(*args, **kwargs):
        metrics_out = kwargs.get("_metrics_out")
        assert isinstance(metrics_out, dict)
        metrics_out.update(
            {"counts": {"ssa_inserted": 5, "ssa_updated": 0}}
        )
        return True, 5

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import)

    sync_calls: list[dict] = []

    def _fake_sync(**kwargs):
        sync_calls.append(kwargs)
        return {
            "sheet_files": list(kwargs.get("sheet_files") or []),
            "db_stats": {"accepted_edges": 3},
            "sheet_stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "merge_stats": {"merged_edges": 3},
        }

    monkeypatch.setattr(app_logic, "sync_derivadas", _fake_sync)

    cached_files: list[str] = []
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda processed_files, *a, **k: cached_files.extend(processed_files),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert len(sync_calls) == 1
    assert sync_calls[0]["include_db_source"] is True
    assert sync_calls[0]["actor"] == "importer-derivadas-sync"
    assert "sheet_files" not in sync_calls[0]
    assert cached_files == [str(regular)]


def test_db_only_derivadas_sync_progress_does_not_report_zero_sheet_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda **kwargs: (
            True,
            [],
            {
                "db_stats": {"accepted_edges": 4},
                "merge_stats": {"merged_edges": 4},
            },
        ),
    )
    events: list[tuple[str, dict]] = []

    app_logic._run_optional_derivadas_sync(
        auto_derivadas_sync_enabled=True,
        successfully_processed_files=["Consulta SSA.xlsx"],
        derivadas_sheet_files=[],
        db_only_derivadas_sync=True,
        should_cancel=None,
        working_db_path="ssa.db",
        table_name="ssa_table",
        docs_dir="docs_entrada",
        critical_errors=[],
        emit_progress=lambda event, payload: events.append((event, payload)),
    )

    success_events = [payload for event, payload in events if event == "file_success"]
    assert success_events
    assert success_events[-1]["records"] == 4
    assert "0 arquivos" not in success_events[-1]["filename"]
    assert "banco atual" in success_events[-1]["filename"]


def test_run_importer_runs_special_derivadas_sync_for_explicit_file_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    regular = docs_dir / "Consulta SSA - 13-02-2026_0121PM.xlsx"
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0137PM.xlsx"
    regular.write_bytes(b"x")
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(app_logic, "_import_single_file", lambda *a, **k: (True, 2))

    sync_calls: list[dict] = []
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: sync_calls.append(kwargs)
        or {
            "sheet_files": list(kwargs.get("sheet_files") or []),
            "db_stats": {"accepted_edges": 2},
            "sheet_stats": {"accepted_edges": 1, "special_layout_detected": 1},
            "merge_stats": {"merged_edges": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": str(special),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 1, "special_layout_detected": 1},
                }
            ],
        },
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
        explicit_files=[str(regular), str(special)],
    )

    assert updated is True
    assert len(sync_calls) == 1
    assert sync_calls[0]["actor"] == "importer-derivadas-sync"
    assert sorted(sync_calls[0]["sheet_files"]) == [str(special)]


def test_needs_db_only_derivadas_sync_returns_false_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic.database,
        "get_db_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    assert app_logic._needs_db_only_derivadas_sync("/tmp/ssa.db", "ssa_table") is False


def test_run_optional_derivadas_sync_marks_blocking_error_on_runtime_error() -> None:
    import core.app_logic as app_logic

    critical_errors: list[tuple[str, str, str]] = []
    progress_events: list[tuple[str, dict[str, object]]] = []

    def _emit_progress(event_type: str, data: dict[str, object]) -> None:
        progress_events.append((event_type, data))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            app_logic,
            "_run_derivadas_sync_phase",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("sync down")),
        )

        sync_materialized, blocking_error, synced_files = (
            app_logic._run_optional_derivadas_sync(
                auto_derivadas_sync_enabled=True,
                successfully_processed_files=["/tmp/regular.xlsx"],
                derivadas_sheet_files=[],
                db_only_derivadas_sync=False,
                should_cancel=None,
                working_db_path="/tmp/ssa.db",
                table_name="ssa_table",
                docs_dir="/tmp/docs",
                critical_errors=critical_errors,
                emit_progress=_emit_progress,
            )
        )

    assert sync_materialized is False
    assert blocking_error is True
    assert synced_files == []
    assert critical_errors == [("derivadas_sync", "/tmp/docs", "sync down")]
    assert progress_events == [
        (
            "file_error",
            {
                "filename": "SSAs Derivadas e Relacionadas",
                "error": "sync down",
            },
        )
    ]


def test_run_importer_accepts_db_materialization_when_special_sheet_has_no_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": list(kwargs.get("sheet_files") or []),
            "db_stats": {"accepted_edges": 2},
            "sheet_stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "merge_stats": {"merged_edges": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": str(special),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 0, "special_layout_detected": 1},
                }
            ],
        },
    )

    cache_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert cache_calls["n"] == 0


def test_run_importer_runs_db_only_sync_when_preflight_requires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic, "_needs_db_only_derivadas_sync", lambda *a, **k: True
    )

    sync_calls: list[dict] = []
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: sync_calls.append(kwargs)
        or {
            "sheet_files": [],
            "db_stats": {"accepted_edges": 4},
            "sheet_stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "merge_stats": {"merged_edges": 4},
        },
    )

    cache_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is True
    assert len(sync_calls) == 1
    assert sync_calls[0]["include_db_source"] is True
    assert sync_calls[0]["actor"] == "importer-derivadas-sync"
    assert "sheet_files" not in sync_calls[0]
    assert cache_calls["n"] == 0


def test_run_importer_skips_db_only_preflight_when_cancel_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "_needs_db_only_derivadas_sync",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("preflight should not run after cancel")
        ),
    )

    progress_events: list[tuple[str, dict]] = []

    def _progress(event_type: str, data: dict) -> None:
        progress_events.append((event_type, dict(data)))

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
        should_cancel=lambda: True,
        progress_callback=_progress,
    )

    assert updated is False
    assert progress_events
    assert progress_events[0][0] == "start"
    assert progress_events[-1][0] == "finish"
    assert progress_events[-1][1]["total"] == 0
    assert progress_events[-1][1]["processed"] == 0


def test_run_importer_skips_db_only_sync_when_preflight_not_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic, "_needs_db_only_derivadas_sync", lambda *a, **k: False
    )

    sync_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: sync_calls.__setitem__("n", sync_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert sync_calls["n"] == 0


def test_run_importer_blocks_success_when_derivadas_consistency_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    regular = docs_dir / "Consulta SSA - 13-02-2026_0121PM.xlsx"
    regular.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic, "_get_files_to_process", lambda *a, **k: [str(regular)]
    )
    def _fake_import(*args, **kwargs):
        metrics_out = kwargs.get("_metrics_out")
        assert isinstance(metrics_out, dict)
        metrics_out.update(
            {"counts": {"ssa_inserted": 3, "ssa_updated": 0}}
        )
        return True, 3

    monkeypatch.setattr(app_logic, "_import_single_file", _fake_import)
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": [],
            "db_stats": {"accepted_edges": 3},
            "sheet_stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "merge_stats": {"merged_edges": 3},
        },
    )
    scan_calls = {"n": 0}

    def _fake_scan(*args, **kwargs):
        scan_calls["n"] += 1
        return {
            "schema_ready": True,
            "is_consistent": False,
            "issue_counts": {"flag_mismatch_pairs": 1},
        }

    monkeypatch.setattr(app_logic, "scan_derivadas_consistency", _fake_scan)

    cache_calls = {"n": 0}
    monkeypatch.setattr(
        app_logic,
        "_update_cache_after_import",
        lambda *a, **k: cache_calls.__setitem__("n", cache_calls["n"] + 1),
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert cache_calls["n"] == 0
    assert scan_calls["n"] == 1


def test_run_importer_reports_consistency_issue_counts_in_progress_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": [str(special)],
            "db_stats": {"accepted_edges": 2},
            "sheet_stats": {"accepted_edges": 1, "special_layout_detected": 1},
            "merge_stats": {"merged_edges": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": str(special),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 1, "special_layout_detected": 1},
                }
            ],
        },
    )
    monkeypatch.setattr(
        app_logic,
        "scan_derivadas_consistency",
        lambda *a, **k: {
            "schema_ready": True,
            "is_consistent": False,
            "issue_counts": {"flag_mismatch_pairs": 2, "summary_missing_nodes": 1},
        },
    )

    events: list[tuple[str, dict]] = []

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
        progress_callback=lambda event, payload: events.append((event, payload)),
    )

    assert updated is False
    file_errors = [payload for event, payload in events if event == "file_error"]
    assert file_errors
    assert "flag_mismatch_pairs" in file_errors[-1]["error"]


def test_run_importer_rejects_special_sheet_without_individual_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": [str(special)],
            "sheet_stats": {"accepted_edges": 1, "special_layout_detected": 1},
            "merge_stats": {"merged_edges": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": str(special),
                    "has_parse_evidence": False,
                    "stats": {"accepted_edges": 0, "special_layout_detected": 0},
                }
            ],
        },
    )

    events: list[tuple[str, dict]] = []
    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
        progress_callback=lambda event, payload: events.append((event, payload)),
    )

    assert updated is False
    file_errors = [payload for event, payload in events if event == "file_error"]
    assert file_errors
    assert "files_without_evidence=" in file_errors[-1]["error"]
    assert special.name in file_errors[-1]["error"]


def test_run_importer_rejects_special_sheet_when_aggregate_evidence_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    special = docs_dir / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
    special.write_bytes(b"x")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    _patch_integrity_ok(monkeypatch)

    import core.app_logic as app_logic

    monkeypatch.setattr(app_logic, "_get_files_to_process", lambda *a, **k: [])
    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {
            "sheet_files": [str(special)],
            "sheet_stats": {"accepted_edges": 1, "special_layout_detected": 1},
            "merge_stats": {"merged_edges": 2},
            "sheet_file_reports": [
                {
                    "sheet_file": str(special),
                    "has_parse_evidence": True,
                    "stats": {"accepted_edges": 1, "special_layout_detected": 1},
                }
            ],
            "sheet_evidence": {
                "files_total": 1,
                "files_with_evidence": 0,
                "files_without_evidence": [str(special)],
                "is_complete": False,
            },
        },
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=False,
    )

    assert updated is False
