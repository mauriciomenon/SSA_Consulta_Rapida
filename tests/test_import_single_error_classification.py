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


def test_import_single_file_raises_when_extractor_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: None,
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match="retornou None"):
        app_logic._import_single_file(file_path, str(tmp_path / "db.sqlite"), "ssa_table")


def test_import_single_file_honors_cancel_before_empty_dataframe_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: pd.DataFrame(),
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match="operation cancelled"):
        app_logic._import_single_file(
            file_path,
            str(tmp_path / "db.sqlite"),
            "ssa_table",
            should_cancel=lambda: True,
        )


def test_import_single_file_logs_friendly_duplicate_labels(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: _valid_df(),
    )
    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        lambda *args, **kwargs: {
            "is_valid": True,
            "violations": [
                {
                    "rule": "duplicate_numero_ssa_exact",
                    "count": 2,
                    "severity": "warning",
                    "sample_ssa": ["202205845", "202205845"],
                },
                {
                    "rule": "outra_regra",
                    "count": 1,
                    "severity": "warning",
                    "sample_ssa": ["202500001"],
                },
            ],
            "invalid_by_column": {},
            "issues": [],
        },
    )
    monkeypatch.setattr(app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_logic.database, "insert_dataframe_with_smart_upsert", lambda *args, **kwargs: True)

    caplog.set_level("WARNING")
    file_path = str(tmp_path / "input.xlsx")
    ok, count = app_logic._import_single_file(file_path, str(tmp_path / "db.sqlite"), "ssa_table")

    assert ok is True
    assert count == 1
    assert "Duplicidade exata no export atingiu 2 linha(s)" in caplog.text
    assert "Regra outra_regra atingiu 1 linha(s)" in caplog.text
