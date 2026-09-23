from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

from scripts import import_excel_file


def _extracted_frame(
    data: dict | None = None,
    *,
    rows_in: int | None = None,
    payload_removed: int = 0,
    events: list[dict] | None = None,
    hierarchical_rows_captured: int = 0,
) -> pd.DataFrame:
    frame = pd.DataFrame(data or {})
    event_records = list(events or [])
    frame.attrs["row_count_before_invalid_filter"] = (
        len(frame) if rows_in is None else rows_in
    )
    frame.attrs["invalid_row_summary"] = {
        "total_removed": payload_removed,
        "payload_removed": payload_removed,
        "hierarchical_rows_captured": hierarchical_rows_captured,
    }
    frame.attrs["ssa_event_records"] = event_records
    return frame


def test_import_excel_file_returns_2_when_file_is_missing(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.xlsx"

    result = import_excel_file.main(["--file", str(missing_file)])

    assert result == 2


def test_import_excel_file_allows_empty_dataframe_in_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "empty.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    observed = {}

    def _extract(_file_path, *, mappings_path):
        observed["mappings_path"] = Path(mappings_path)
        return _extracted_frame()

    monkeypatch.setattr(import_excel_file, "extract_data_from_excel", _extract)

    result = import_excel_file.main(["--file", str(source_file), "--dry-run"])

    assert result == 0
    assert observed["mappings_path"] == import_excel_file.DEFAULT_MAPPINGS_PATH


def test_import_excel_file_fails_empty_dataframe_without_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "empty.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(),
    )

    result = import_excel_file.main(["--file", str(source_file)])

    assert result == 4


def test_import_excel_file_rejects_reset_before_extract_or_database_change(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("extract should not run with --reset-db")
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "reset_database",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("reset_database must not run")
        ),
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--reset-db"]
    )

    assert result == 2


def test_import_excel_file_rejects_invalid_table_before_extract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("extract should not run for invalid table")
        ),
    )

    result = import_excel_file.main(["--file", str(source_file), "--table", "bad;sql"])

    assert result == 2


def test_import_excel_file_preserves_insert_failure_exit_code(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699001"]}
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: False,
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--table", "custom_ssas"]
    )

    assert result == 3


def test_import_excel_file_uses_scalar_count_after_insert(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    db_path = tmp_path / "ssas.db"
    source_file.write_text("payload", encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE custom_ssas (numero_ssa TEXT)")
        conn.executemany(
            "INSERT INTO custom_ssas VALUES (?)",
            [("202699001",), ("202699002",)],
        )
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699001"]}
        ),
    )
    def _simple_insert(frame, _db_path, _table):
        assert frame.columns.tolist() == ["numero_ssa"]
        return True

    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        _simple_insert,
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "query_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("query_db should not be used for row count")
        ),
    )

    result = import_excel_file.main(
        [
            "--file",
            str(source_file),
            "--db",
            str(db_path),
            "--table",
            "custom_ssas",
        ]
    )

    assert result == 0


def test_import_excel_file_rejects_simple_write_to_ssa_table(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699009"]}
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("simple SSA insert must not run")
        ),
    )

    result = import_excel_file.main(["--file", str(source_file)])

    assert result == 4


def test_import_excel_file_rejects_hierarchical_events_without_smart_upsert(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "hierarchical.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    event = {
        "numero_ssa": "202699003",
        "record_type": "numero_desvios",
        "record_order": 1,
    }
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699003"]},
            rows_in=2,
            events=[event],
            hierarchical_rows_captured=1,
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("simple insert must not run with events")
        ),
    )

    result = import_excel_file.main(["--file", str(source_file)])

    assert result == 4


def test_import_excel_file_rejects_payload_loss_even_in_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "unsafe.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699004"]},
            rows_in=2,
            payload_removed=1,
        ),
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--dry-run", "--smart-upsert"]
    )

    assert result == 4


def test_import_excel_file_allows_hierarchical_dry_run_without_smart_upsert(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "hierarchical-dry-run.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    event = {
        "numero_ssa": "202699006",
        "record_type": "numero_desvios",
        "record_order": 1,
    }
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699006"]},
            rows_in=2,
            events=[event],
            hierarchical_rows_captured=1,
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must not insert")
        ),
    )

    result = import_excel_file.main(["--file", str(source_file), "--dry-run"])

    assert result == 0


def test_import_excel_file_rejects_all_rows_removed_in_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "all-rejected.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(rows_in=1),
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--dry-run", "--smart-upsert"]
    )

    assert result == 4


def test_import_excel_file_rejects_missing_or_negative_rows_in_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "missing-row-count.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    extracted = _extracted_frame({"numero_ssa": ["202699010"]})
    extracted.attrs.pop("row_count_before_invalid_filter")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: extracted,
    )

    result = import_excel_file.main(["--file", str(source_file), "--dry-run"])

    assert result == 4

    extracted.attrs["row_count_before_invalid_filter"] = -1

    assert import_excel_file.main(["--file", str(source_file), "--dry-run"]) == 4


def test_import_excel_file_smart_upsert_confirms_events_and_source_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "hierarchical_11-08-2026_0310AM.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    event = {
        "numero_ssa": "202699005",
        "record_type": "numero_desvios",
        "record_order": 1,
    }
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699005"]},
            events=[event],
        ),
    )

    def _smart_upsert(frame, _db_path, _table, *, metrics_out):
        assert frame["arquivo_origem"].tolist() == [source_file.name]
        assert frame["data_planilha"].tolist() == ["2026-08-11T03:10:00"]
        assert frame.attrs["ssa_event_records"] == [event]
        metrics_out.update(
            {
                "ssa_inserted": 1,
                "ssa_updated": 0,
                "ssa_event_records_processed": 1,
            }
        )
        return True

    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_with_smart_upsert",
        _smart_upsert,
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "count_table_rows",
        lambda *_args, **_kwargs: 1,
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--smart-upsert"]
    )

    assert result == 0


def test_import_excel_file_rejects_missing_upsert_metrics(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "metrics_11-08-2026_0315AM.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: _extracted_frame(
            {"numero_ssa": ["202699011"]}
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_with_smart_upsert",
        lambda *_args, **_kwargs: True,
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--smart-upsert"]
    )

    assert result == 3


def test_import_excel_file_persists_hierarchy_in_real_sqlite(tmp_path: Path) -> None:
    source_file = tmp_path / "hierarchical_11-08-2026_0320AM.xlsx"
    older_source_file = tmp_path / "hierarchical_05-08-2026_0320AM.xlsx"
    db_path = tmp_path / "ssas.db"
    pd.DataFrame(
        {
            "numero_ssa": ["202699007", None],
            "descricao_ssa": ["SSA pai", None],
            "data_cadastro": ["2026-08-11 03:20:00", None],
            "numero_desvios": ["Desvio #1", "Desvio #2"],
            "situacao_de_desvio": ["ADM", "AMP"],
            "arquivo_origem": ["forged_01-08-2026_0100AM.xlsx", None],
            "data_planilha": ["2026-08-01T01:00:00", None],
            "data_arquivo_origem": ["2026-08-01 01:00:00", None],
        }
    ).to_excel(source_file, index=False)
    pd.DataFrame(
        {
            "numero_ssa": ["202699007", None],
            "descricao_ssa": ["OLDER", None],
            "data_cadastro": ["2026-08-05 03:20:00", None],
            "numero_desvios": ["Desvio #1", "Desvio #2"],
            "situacao_de_desvio": ["ADM", "AMP"],
        }
    ).to_excel(older_source_file, index=False)
    import_excel_file.database.initialize_database(
        str(db_path),
        str(import_excel_file.PROJECT_ROOT / "config" / "schema_unified.sql"),
    )

    newer_result = import_excel_file.main(
        [
            "--file",
            str(source_file),
            "--db",
            str(db_path),
            "--smart-upsert",
        ]
    )
    older_result = import_excel_file.main(
        [
            "--file",
            str(older_source_file),
            "--db",
            str(db_path),
            "--smart-upsert",
        ]
    )

    assert newer_result == 0
    assert older_result == 0
    with sqlite3.connect(db_path) as conn:
        parent = conn.execute(
            "SELECT descricao_ssa, arquivo_origem, data_planilha, "
            "data_arquivo_origem FROM ssa_table WHERE numero_ssa = ?",
            ("202699007",),
        ).fetchone()
        event_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_event_records WHERE numero_ssa = ?",
            ("202699007",),
        ).fetchone()[0]
    assert parent == (
        "SSA pai",
        source_file.name,
        "2026-08-11T03:20:00",
        "2026-08-11 03:20:00",
    )
    assert event_count == 2
