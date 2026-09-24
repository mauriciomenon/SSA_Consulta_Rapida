# tests/test_import_cancellation.py
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.app_logic import run_importer_logic


@pytest.mark.parametrize("force_import", [True, False])
def test_should_cancel_stops_between_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, force_import: bool
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    for i in range(5):
        (docs_dir / f"file_{i}.xlsx").write_bytes(b"dummy")

    data_dir = tmp_path / "data"

    # Ensure path safety allowlist includes this tmp path.
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )

    insert_count = {"n": 0}
    progress_events = []

    def fake_extract_data_from_excel(file_path: str, *, should_cancel=None):
        assert should_cancel is not None
        # Minimal valid payload for _import_single_file validation rules.
        return pd.DataFrame(
            {
                "numero_ssa": [202500101],
                "data_cadastro": [pd.Timestamp("2025-01-01")],
                "situacao": ["TESTE"],
                "descricao_ssa": ["ok"],
            }
        )

    def fake_insert_dataframe_with_smart_upsert(
        df, db_path, table_name, *, metrics_out=None, should_cancel=None
    ):
        assert should_cancel is not None
        insert_count["n"] += 1
        if metrics_out is not None:
            metrics_out.update({"ssa_inserted": 1, "ssa_updated": 0})
        return True

    # Avoid real Excel parsing and DB writes: focus on cancellation + cache behavior.
    import core.app_logic as app_logic

    monkeypatch.setattr(
        app_logic.extractor, "extract_data_from_excel", fake_extract_data_from_excel
    )
    monkeypatch.setattr(
        app_logic.database,
        "insert_dataframe_with_smart_upsert",
        fake_insert_dataframe_with_smart_upsert,
    )

    cancel_flag = {"cancel": False}

    def progress_callback(event_type, data):
        progress_events.append((event_type, dict(data)))
        if event_type == "file_success" and not cancel_flag["cancel"]:
            cancel_flag["cancel"] = True

    def should_cancel() -> bool:
        return bool(cancel_flag["cancel"])

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=force_import,
        should_cancel=should_cancel,
        progress_callback=progress_callback,
    )

    assert updated is (not force_import)
    cache_path = data_dir / "file_cache.json"
    if force_import:
        assert not cache_path.exists()

    assert insert_count["n"] == 1
    assert progress_events
    file_success = next(
        data for event_type, data in progress_events if event_type == "file_success"
    )
    assert file_success["ssa_inserted"] == 1
    assert file_success["ssa_updated"] == 0
    assert progress_events[-1][0] == "finish"
    finish_payload = progress_events[-1][1]
    assert finish_payload["total"] == 5
    assert finish_payload["processed"] == 1
    assert "errors" in finish_payload
    assert finish_payload["errors"] == []

    from core import import_outcome

    outcome = import_outcome.get_last_import_outcome()
    assert outcome is not None
    assert outcome.cancel_requested is True
    assert outcome.status is (
        import_outcome.ImportStatus.CANCELLED
        if force_import
        else import_outcome.ImportStatus.UPDATED
    )
    assert outcome.blocking_error_count == 0
    assert outcome.primary_database_changed is (not force_import)
    assert outcome.report_path is not None
    with open(outcome.report_path, encoding="utf-8") as report_file:
        report = json.load(report_file)
    assert report["cancel_requested"] is True


def test_cancel_during_cache_scan_reports_no_database_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core import import_outcome
    from utils import path_safety

    monkeypatch.setattr(
        path_safety, "ALLOWED_ROOTS", list(path_safety.ALLOWED_ROOTS) + [tmp_path]
    )
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "large.xlsx").write_bytes(b"x" * (65536 * 4))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "file_cache.test.db.json"
    cache_file.write_text(json.dumps({"large.xlsx": "old_hash"}), encoding="utf-8")
    callback_calls = 0

    def should_cancel() -> bool:
        nonlocal callback_calls
        callback_calls += 1
        return callback_calls >= 4

    result = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        should_cancel=should_cancel,
    )

    outcome = import_outcome.get_last_import_outcome()
    assert result is False
    assert outcome is not None
    assert outcome.cancel_requested is True
    assert outcome.primary_database_changed is False
    assert outcome.report_path is not None
    report = json.loads(Path(outcome.report_path).read_text(encoding="utf-8"))
    assert report["reason"] == "file_discovery_cancelled_before_update"
    assert report["cancel_requested"] is True
    assert not (data_dir / "test.db").exists()
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {
        "large.xlsx": "old_hash"
    }


def test_cancel_during_upsert_is_classified_without_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import core.app_logic as app_logic

    file_path = tmp_path / "Consulta SSA - cancel.xlsx"
    file_path.write_bytes(b"x")
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: pd.DataFrame(
            {"numero_ssa": [202600001], "data_cadastro": ["2026-01-01"]}
        ),
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *_args, **_kwargs: None
    )
    seen_callback = []

    def _cancel_upsert(*_args, should_cancel=None, **_kwargs):
        seen_callback.append(should_cancel)
        raise InterruptedError("Upsert cancelado antes do commit")

    monkeypatch.setattr(
        app_logic.database, "insert_dataframe_with_smart_upsert", _cancel_upsert
    )

    def callback() -> bool:
        return False

    with pytest.raises(app_logic.ExtractionError) as exc_info:
        app_logic._import_single_file(
            str(file_path), str(tmp_path / "db.sqlite"), "ssa_table", callback
        )

    assert exc_info.value.error_code == "OPERATION_CANCELLED"
    assert seen_callback == [callback]
