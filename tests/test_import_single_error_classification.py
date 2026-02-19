from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import core.app_logic as app_logic


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "numero_ssa": [123456789],
            "data_cadastro": [pd.Timestamp("2025-01-01")],
            "situacao": ["TESTE"],
            "descricao_ssa": ["ok"],
        }
    )


def test_import_single_file_preserves_database_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: _valid_df(),
    )
    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        lambda *args, **kwargs: {"is_valid": True, "violations": [], "invalid_by_column": {}, "issues": []},
    )
    monkeypatch.setattr(app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_logic.database, "insert_dataframe_with_smart_upsert", lambda *args, **kwargs: False)

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.DatabaseError, match="Erro ao inserir dados do arquivo"):
        app_logic._import_single_file(file_path, str(tmp_path / "db.sqlite"), "ssa_table")


def test_import_single_file_keeps_unexpected_error_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: _valid_df(),
    )
    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        lambda *args, **kwargs: {"is_valid": True, "violations": [], "invalid_by_column": {}, "issues": []},
    )
    monkeypatch.setattr(app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None)

    def _raise_unexpected(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_logic.database, "insert_dataframe_with_smart_upsert", _raise_unexpected)

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match="boom"):
        app_logic._import_single_file(file_path, str(tmp_path / "db.sqlite"), "ssa_table")
