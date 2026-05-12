# tests/test_import_cancellation.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.app_logic import run_importer_logic


def test_should_cancel_stops_between_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    def fake_insert_dataframe_with_smart_upsert(df, db_path, table_name):
        insert_count["n"] += 1
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
        force_import=True,
        should_cancel=should_cancel,
        progress_callback=progress_callback,
    )

    assert updated is False
    cache_path = data_dir / "file_cache.json"
    assert not cache_path.exists()

    assert insert_count["n"] == 1
    assert progress_events
    assert progress_events[-1][0] == "finish"
    finish_payload = progress_events[-1][1]
    assert finish_payload["total"] == 5
    assert finish_payload["processed"] == 1
    assert "errors" in finish_payload
    assert finish_payload["errors"] == []
