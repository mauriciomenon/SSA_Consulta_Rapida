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


def _successful_upsert(*args, metrics_out=None, **kwargs) -> bool:
    assert isinstance(metrics_out, dict)
    metrics_out.update({"ssa_inserted": 1, "ssa_updated": 0})
    return True


@pytest.fixture(autouse=True)
def _create_default_import_file(tmp_path: Path) -> None:
    (tmp_path / "input.xlsx").write_bytes(b"placeholder")


def test_import_single_file_fails_before_extraction_when_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def _extract_should_not_run(*args, **kwargs):
        nonlocal called
        called = True
        return _valid_df()

    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _extract_should_not_run,
    )
    missing_file = tmp_path / "missing.xlsx"

    with pytest.raises(app_logic.ExtractionError, match="nao encontrado") as exc_info:
        app_logic._import_single_file(
            str(missing_file), str(tmp_path / "db.sqlite"), "ssa_table"
        )

    assert getattr(exc_info.value, "error_code", None) == "MISSING_FILE"
    assert called is False


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


@pytest.mark.parametrize(
    ("exc_factory", "expected_pattern"),
    [
        (lambda: RuntimeError("boom"), "RuntimeError ao importar"),
        (lambda: TypeError("bad type"), "TypeError ao importar"),
        (lambda: ValueError("bad value"), "ValueError ao importar"),
    ],
)
def test_import_single_file_wraps_supported_runtime_shape_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exc_factory,
    expected_pattern: str,
) -> None:
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: _valid_df(),
    )

    def _raise_expected_validation(*args, **kwargs):
        raise exc_factory()

    monkeypatch.setattr(
        app_logic.database,
        "validate_dataframe_before_insert",
        _raise_expected_validation,
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError, match=expected_pattern):
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )


def test_import_single_file_tolerates_missing_is_valid_in_validation_report(
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
        _successful_upsert,
    )

    file_path = str(tmp_path / "input.xlsx")
    ok, count = app_logic._import_single_file(
        file_path, str(tmp_path / "db.sqlite"), "ssa_table"
    )

    assert ok is True
    assert count == 1


def test_import_single_file_rejects_upsert_success_without_ssa_metrics(
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
        lambda *args, **kwargs: True,
    )

    with pytest.raises(
        app_logic.ImportMetricsContractError,
        match="Upsert concluido sem metricas obrigatorias",
    ):
        app_logic._import_single_file(
            str(tmp_path / "input.xlsx"),
            str(tmp_path / "db.sqlite"),
            "ssa_table",
        )


def test_process_file_with_resilience_keeps_batch_running_on_internal_result_cast_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        lambda *args, **kwargs: (True, object()),
    )

    successful_files: list[str] = []
    successful_with_records: list[tuple[str, int]] = []
    critical_errors: list[tuple[str, str, str]] = []
    deterministic_failed: list[str] = []
    file_reports: list[dict[str, object]] = []
    progress_events: list[tuple[str, dict[str, object]]] = []

    action = app_logic._process_file_with_resilience(
        file_path=str(tmp_path / "input.xlsx"),
        base_name="input.xlsx",
        working_db_path=str(tmp_path / "db.sqlite"),
        table_name="ssa_table",
        should_cancel=None,
        candidate_db_path=None,
        successfully_processed_files=successful_files,
        successful_regular_files_with_records=successful_with_records,
        critical_errors=critical_errors,
        deterministic_failed_files=deterministic_failed,
        file_reports=file_reports,
        emit_progress=lambda event_type, data: progress_events.append(
            (event_type, data)
        ),
    )

    assert action == app_logic.FileProcessAction.CONTINUE
    assert successful_files == []
    assert successful_with_records == []
    assert deterministic_failed == []
    assert critical_errors == [
        ("unexpected", str(tmp_path / "input.xlsx"), "int() argument must be a string, a bytes-like object or a real number, not 'object'")
    ]
    assert file_reports == [
        {
            "file": "input.xlsx",
            "status": "unexpected_error",
            "error": "int() argument must be a string, a bytes-like object or a real number, not 'object'",
        }
    ]
    assert progress_events == [
        (
            "file_error",
            {
                "filename": "input.xlsx",
                "error": "int() argument must be a string, a bytes-like object or a real number, not 'object'",
            },
        )
    ]


def test_process_file_with_resilience_records_metrics_contract_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _raise_metrics_contract(*args, **kwargs):
        raise app_logic.ImportMetricsContractError(
            "Metricas SSA ausentes no resultado de input.xlsx",
            record_count=1,
        )

    monkeypatch.setattr(
        app_logic,
        "_import_single_file",
        _raise_metrics_contract,
    )

    successful_files: list[str] = []
    successful_with_records: list[tuple[str, int]] = []
    critical_errors: list[tuple[str, str, str]] = []
    file_reports: list[dict[str, object]] = []
    progress_events: list[tuple[str, dict[str, object]]] = []

    action = app_logic._process_file_with_resilience(
        file_path=str(tmp_path / "input.xlsx"),
        base_name="input.xlsx",
        working_db_path=str(tmp_path / "db.sqlite"),
        table_name="ssa_table",
        should_cancel=None,
        candidate_db_path=None,
        successfully_processed_files=successful_files,
        successful_regular_files_with_records=successful_with_records,
        critical_errors=critical_errors,
        deterministic_failed_files=[],
        file_reports=file_reports,
        emit_progress=lambda event_type, data: progress_events.append(
            (event_type, data)
        ),
    )

    assert action == app_logic.FileProcessAction.CONTINUE
    input_path = str(tmp_path / "input.xlsx")
    assert successful_files == [input_path]
    assert successful_with_records == [(input_path, 1)]
    assert critical_errors == [
        (
            "metrics_contract",
            input_path,
            "Metricas SSA ausentes no resultado de input.xlsx",
        )
    ]
    assert progress_events[-1] == (
        "file_error",
        {
            "filename": "input.xlsx",
            "error": "Metricas SSA ausentes no resultado de input.xlsx",
        },
    )
    assert file_reports == [
        {
            "file": "input.xlsx",
            "status": "metrics_contract_error",
            "records": 1,
            "error": "Metricas SSA ausentes no resultado de input.xlsx",
        }
    ]


def test_all_rows_rejected_progress_is_deterministic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _reject_all_rows(*args, **kwargs):
        raise app_logic.ExtractionError(
            "todas as linhas foram rejeitadas",
            error_code="ALL_ROWS_REJECTED",
        )

    monkeypatch.setattr(app_logic, "_import_single_file", _reject_all_rows)
    deterministic_failed: list[str] = []
    progress_events: list[tuple[str, dict[str, object]]] = []

    action = app_logic._process_file_with_resilience(
        file_path=str(tmp_path / "input.xlsx"),
        base_name="input.xlsx",
        working_db_path=str(tmp_path / "db.sqlite"),
        table_name="ssa_table",
        should_cancel=None,
        candidate_db_path=None,
        successfully_processed_files=[],
        successful_regular_files_with_records=[],
        critical_errors=[],
        deterministic_failed_files=deterministic_failed,
        file_reports=[],
        emit_progress=lambda event_type, data: progress_events.append(
            (event_type, data)
        ),
    )

    assert action == app_logic.FileProcessAction.CONTINUE
    assert deterministic_failed == [str(tmp_path / "input.xlsx")]
    assert progress_events[-1][1]["deterministic"] is True


@pytest.mark.parametrize(
    ("raised_exc", "expected_error"),
    [
        (KeyError("missing"), "'missing'"),
        (AttributeError("broken"), "broken"),
    ],
)
def test_process_file_with_resilience_keeps_batch_running_on_internal_runtime_attr_or_key_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raised_exc: Exception,
    expected_error: str,
) -> None:
    def _raise_internal(*args, **kwargs):
        raise raised_exc

    monkeypatch.setattr(app_logic, "_import_single_file", _raise_internal)

    successful_files: list[str] = []
    successful_with_records: list[tuple[str, int]] = []
    critical_errors: list[tuple[str, str, str]] = []
    deterministic_failed: list[str] = []
    file_reports: list[dict[str, object]] = []
    progress_events: list[tuple[str, dict[str, object]]] = []

    action = app_logic._process_file_with_resilience(
        file_path=str(tmp_path / "input.xlsx"),
        base_name="input.xlsx",
        working_db_path=str(tmp_path / "db.sqlite"),
        table_name="ssa_table",
        should_cancel=None,
        candidate_db_path=None,
        successfully_processed_files=successful_files,
        successful_regular_files_with_records=successful_with_records,
        critical_errors=critical_errors,
        deterministic_failed_files=deterministic_failed,
        file_reports=file_reports,
        emit_progress=lambda event_type, data: progress_events.append(
            (event_type, data)
        ),
    )

    assert action == app_logic.FileProcessAction.CONTINUE
    assert successful_files == []
    assert successful_with_records == []
    assert deterministic_failed == []
    assert critical_errors == [
        ("unexpected", str(tmp_path / "input.xlsx"), expected_error)
    ]
    assert file_reports == [
        {
            "file": "input.xlsx",
            "status": "unexpected_error",
            "error": expected_error,
        }
    ]
    assert progress_events == [
        (
            "file_error",
            {
                "filename": "input.xlsx",
                "error": expected_error,
            },
        )
    ]


def test_build_progress_emitter_keeps_reporting_after_callback_failure() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def _broken_callback(event_type: str, data: dict[str, object]) -> None:
        calls.append((event_type, data))
        raise RuntimeError("progress down")

    emitter = app_logic._build_progress_emitter(_broken_callback)

    emitter("first", {"step": 1})
    emitter("second", {"step": 2})

    assert calls == [("first", {"step": 1}), ("second", {"step": 2})]


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


def test_import_single_file_rejects_dataframe_emptied_by_identity_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rejected = pd.DataFrame()
    rejected.attrs["row_count_before_invalid_filter"] = 3
    rejected.attrs["invalid_row_summary"] = {"total_removed": 3}
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        lambda *args, **kwargs: rejected,
    )

    file_path = str(tmp_path / "input.xlsx")
    with pytest.raises(app_logic.ExtractionError) as exc_info:
        app_logic._import_single_file(
            file_path, str(tmp_path / "db.sqlite"), "ssa_table"
        )

    assert exc_info.value.error_code == "ALL_ROWS_REJECTED"


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
        _successful_upsert,
    )

    caplog.set_level("WARNING")
    file_path = str(tmp_path / "input.xlsx")
    ok, count = app_logic._import_single_file(
        file_path, str(tmp_path / "db.sqlite"), "ssa_table"
    )

    assert ok is True
    assert count == 1
    assert "Duplicidade exata no export atingiu 2 linha(s)" in caplog.text
    assert "Aviso de validacao [outra regra] atingiu 1 linha(s)" in caplog.text


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
        metrics_out = kwargs.get("metrics_out")
        assert isinstance(metrics_out, dict)
        metrics_out.update({"ssa_inserted": len(dataframe), "ssa_updated": 0})
        return True

    monkeypatch.setattr(
        app_logic.database, "validate_dataframe_before_insert", _fake_validate
    )
    monkeypatch.setattr(
        app_logic.database, "ensure_column_exists", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        app_logic.database, "insert_dataframe_with_smart_upsert", _fake_insert
    )

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
