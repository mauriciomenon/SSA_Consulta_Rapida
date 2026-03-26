from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.app_logic import run_importer_logic


def test_should_cancel_can_abort_before_db_insert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "file_0.xlsx").write_bytes(b"dummy")
    (docs_dir / "file_1.xlsx").write_bytes(b"dummy")

    data_dir = tmp_path / "data"

    # Ensure path safety allowlist includes this tmp path.
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )

    import core.app_logic as app_logic

    # Make integrity checks deterministic and cheap.
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

    # Avoid real Excel parsing: return a minimal valid DataFrame.
    def fake_extract_data_from_excel(file_path: str, *, should_cancel=None):
        assert should_cancel is not None
        return pd.DataFrame(
            {
                "numero_ssa": [123456789],
                "data_cadastro": [pd.Timestamp("2025-01-01")],
                "situacao": ["TESTE"],
                "descricao_ssa": ["ok"],
            }
        )

    monkeypatch.setattr(
        app_logic.extractor, "extract_data_from_excel", fake_extract_data_from_excel
    )

    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        lambda *a, **k: {
            "is_valid": True,
            "violations": [],
            "invalid_by_column": {},
            "issues": [],
        },
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *a, **k: None
    )

    insert_count = {"n": 0}

    def fake_insert_dataframe_with_smart_upsert(*args, **kwargs):
        insert_count["n"] += 1
        return True

    monkeypatch.setattr(
        app_logic.database,
        "insert_dataframe_with_smart_upsert",
        fake_insert_dataframe_with_smart_upsert,
    )

    cancel_calls = {"n": 0}

    def should_cancel() -> bool:
        # run_importer_logic consults should_cancel before each file (1),
        # _import_single_file consults after extraction/df copy (2),
        # then again before DB insert (3). We cancel at (3).
        cancel_calls["n"] += 1
        return cancel_calls["n"] >= 3

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
        should_cancel=should_cancel,
    )

    assert updated is False
    assert insert_count["n"] == 0
