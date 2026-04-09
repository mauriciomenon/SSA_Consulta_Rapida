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


def test_import_single_file_preserves_database_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
            "violations": [],
            "invalid_by_column": {},
            "issues": [],
        },
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        app_logic.database,
        "insert_dataframe_with_smart_upsert",
        lambda *args, **kwargs: False,
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(
        app_logic.DatabaseError, match="Erro ao inserir dados do arquivo"
    ):
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )


def test_import_single_file_keeps_unexpected_error_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
            "violations": [],
            "invalid_by_column": {},
            "issues": [],
        },
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None
    )

    def _raise_unexpected(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        app_logic.database, "insert_dataframe_with_smart_upsert", _raise_unexpected
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match="boom"):
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )


def test_import_single_file_raises_when_extractor_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: None,
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match="retornou None"):
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )


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
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        app_logic.database,
        "insert_dataframe_with_smart_upsert",
        lambda *args, **kwargs: True,
    )

    caplog.set_level("WARNING")
    file_path = str(tmp_path / "input.xlsx")
    ok, count = app_logic._import_single_file(
        file_path, str(tmp_path / "db.sqlite"), "ssa_table"
    )

    assert ok is True
    assert count == 1
    assert "Duplicidade exata no export atingiu 2 linha(s)" in caplog.text
    assert "Violacao de validacao [outra regra] atingiu 1 linha(s)" in caplog.text


def test_import_single_file_drops_invalid_numero_ssa_rows_before_insert(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["invalid", "202512346"],
            "data_cadastro": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")],
            "situacao": ["TESTE", "TESTE"],
            "descricao_ssa": ["bad", "good"],
        }
    )

    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: df.copy(),
    )

    captured = {"rows": None, "ssas": None}

    def _fake_validate(*_args, **_kwargs):
        return {
            "is_valid": True,
            "violations": [
                {
                    "rule": "invalid_numero_ssa",
                    "count": 1,
                    "severity": "warning",
                    "sample_ssa": ["invalid"],
                }
            ],
            "invalid_by_column": {"numero_ssa": [0]},
            "issues": [],
        }

    def _fake_insert(dataframe, *args, **kwargs):
        captured["rows"] = len(dataframe)
        captured["ssas"] = dataframe["numero_ssa"].astype(str).tolist()
        return True

    monkeypatch.setattr(app_logic.database, "validate_dataframe_before_insert", _fake_validate)
    monkeypatch.setattr(app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_logic.database, "insert_dataframe_with_smart_upsert", _fake_insert)

    file_path = str(tmp_path / "input.xlsx")
    ok, count = app_logic._import_single_file(
        file_path, str(tmp_path / "db.sqlite"), "ssa_table"
    )

    assert ok is True
    assert count == 1
    assert captured["rows"] == 1
    assert captured["ssas"] == ["202512346"]


def test_import_single_file_blocks_insert_when_missing_critical_column(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "numero_ssa": ["202500100"],
                "situacao": ["APV"],
                "descricao_ssa": ["Sem data de cadastro"],
            }
        ),
    )

    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        lambda *args, **kwargs: {
            "is_valid": False,
            "violations": [
                {
                    "rule": "missing_column_data_cadastro",
                    "column": "data_cadastro",
                    "severity": "error",
                    "count": 1,
                    "sample_ssa": ["202500100"],
                }
            ],
            "invalid_by_column": {},
            "issues": ["Coluna obrigatoria 'data_cadastro' ausente no DataFrame"],
        },
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None
    )

    def _fail_insert(*args, **kwargs):
        raise AssertionError("insert nao deveria ser chamado")

    monkeypatch.setattr(
        app_logic.database, "insert_dataframe_with_smart_upsert", _fail_insert
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(
        app_logic.ExtractionError, match="Coluna obrigatoria 'data_cadastro' ausente"
    ) as exc_info:
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )

    assert getattr(exc_info.value, "error_code", None) == "MISSING_REQUIRED_COLUMNS"
