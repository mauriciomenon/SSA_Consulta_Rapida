import json
import os
import pathlib
import sqlite3
import subprocess
import sys

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = BASE / "scripts" / "migracao" / "backfill_reprocessar.py"


def _run(cmd: list[str]):
    os.environ.copy()
    return subprocess.run(
        [sys.executable, *cmd],
        cwd=BASE,
        capture_output=True,
        text=True,
    )


def test_backfill_no_files_creates_empty_report(tmp_path):
    report_path = tmp_path / "empty_report.json"
    res = _run(
        [
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--db",
            "data/ssas.db",
            "--dry-run",
            "--report-path",
            str(report_path),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert report_path.exists(), "Report file not created"
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_processed"] == 0


def test_backfill_limit_and_report(tmp_path):
    for index in range(3):
        frame = pd.DataFrame(
            {
                "numero_ssa": [f"20250000{index}"],
                "descricao_ssa": ["teste"],
                "data_cadastro": ["2026-01-01 10:00:00"],
            }
        )
        frame.to_excel(tmp_path / f"arq_{index}.xlsx", index=False)
    report_path = tmp_path / "report.json"
    res = _run(
        [
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--db",
            "data/ssas.db",
            "--dry-run",
            "--limit",
            "2",
            "--report-path",
            str(report_path),
        ]
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_processed"] == 2


def test_backfill_dry_run_reports_hierarchical_capture(tmp_path):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600201, None],
            "descricao_ssa": ["SSA pai", None],
            "data_cadastro": ["2026-01-01 10:00:00", None],
            "numero_desvios": ["Desvio #1", "Desvio #2"],
            "detalhe": ["pai", "filho"],
        }
    )
    frame.to_excel(tmp_path / "hierarchical.xlsx", index=False)
    report_path = tmp_path / "hierarchical_report.json"

    res = _run(
        [
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--dry-run",
            "--report-path",
            str(report_path),
        ]
    )

    assert res.returncode == 0, res.stderr
    data = json.loads(report_path.read_text())
    result = data["results"][0]
    assert result["rows_in"] == 2
    assert result["rows_out"] == 1
    assert result["extraction"] == {
        "payload_removed": 0,
        "hierarchical_rows_captured": 1,
        "hierarchical_records_captured": 2,
    }


def test_backfill_rejects_batch_limit_before_reset_or_import(tmp_path, monkeypatch):
    from scripts.migracao import backfill_reprocessar

    for index in range(2):
        (tmp_path / f"arq_{index}.xlsx").write_bytes(b"x")
    import_calls: list[str] = []
    reset_calls: list[str] = []
    monkeypatch.setattr("extracao.extractor.MAX_IMPORT_BATCH_FILES", 1)
    monkeypatch.setattr(
        backfill_reprocessar,
        "extract_data_from_excel",
        lambda path, **_kwargs: import_calls.append(path),
    )
    monkeypatch.setattr(
        backfill_reprocessar.database,
        "reset_database",
        lambda *_args, **_kwargs: reset_calls.append("reset"),
    )

    exit_code = backfill_reprocessar.main(["--dir", str(tmp_path), "--dry-run"])

    assert exit_code == 2
    assert import_calls == []
    assert reset_calls == []


def test_backfill_rejects_reset_before_discovery_or_database_change(
    tmp_path,
    monkeypatch,
):
    from scripts.migracao import backfill_reprocessar

    monkeypatch.setattr(
        backfill_reprocessar.database,
        "reset_database",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("reset_database must not run")
        ),
    )

    exit_code = backfill_reprocessar.main(
        ["--dir", str(tmp_path / "missing"), "--reset-db"]
    )

    assert exit_code == 2


def test_backfill_rejects_payload_loss_even_in_dry_run(tmp_path, monkeypatch):
    from scripts.migracao import backfill_reprocessar

    source_file = tmp_path / "unsafe.xlsx"
    source_file.write_bytes(b"xlsx")
    report_path = tmp_path / "unsafe_report.json"
    extracted = pd.DataFrame({"numero_ssa": ["202600203"]})
    extracted.attrs["row_count_before_invalid_filter"] = 2
    extracted.attrs["invalid_row_summary"] = {
        "payload_removed": 1,
        "hierarchical_rows_captured": 0,
    }
    extracted.attrs["ssa_event_records"] = []
    monkeypatch.setattr(
        backfill_reprocessar,
        "validate_excel_import_limits",
        lambda _paths: 0,
    )
    monkeypatch.setattr(
        backfill_reprocessar,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: extracted,
    )

    exit_code = backfill_reprocessar.main(
        [
            "--dir",
            str(tmp_path),
            "--dry-run",
            "--smart-upsert",
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 1
    data = json.loads(report_path.read_text())
    assert data["summary"]["files_failed"] == 1
    assert data["results"][0]["extraction"]["payload_removed"] == 1


def test_backfill_smart_upsert_confirms_events_and_source_metadata(
    tmp_path,
    monkeypatch,
):
    from scripts.migracao import backfill_reprocessar

    source_file = tmp_path / "hierarchical_11-08-2026_0315AM.xlsx"
    source_file.write_bytes(b"xlsx")
    report_path = tmp_path / "smart_report.json"
    event = {"record_order": 1}
    extracted = pd.DataFrame({"numero_ssa": ["202600204"]})
    extracted.attrs["row_count_before_invalid_filter"] = 1
    extracted.attrs["invalid_row_summary"] = {
        "payload_removed": 0,
        "hierarchical_rows_captured": 0,
    }
    extracted.attrs["ssa_event_records"] = [event]
    monkeypatch.setattr(
        backfill_reprocessar,
        "validate_excel_import_limits",
        lambda _paths: 0,
    )
    monkeypatch.setattr(
        backfill_reprocessar,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: extracted,
    )

    def _smart_upsert(frame, _db_path, _table, *, metrics_out):
        assert frame["arquivo_origem"].tolist() == [source_file.name]
        assert frame["data_planilha"].tolist() == ["2026-08-11T03:15:00"]
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
        backfill_reprocessar.database,
        "insert_dataframe_with_smart_upsert",
        _smart_upsert,
    )

    exit_code = backfill_reprocessar.main(
        [
            "--dir",
            str(tmp_path),
            "--smart-upsert",
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 0
    data = json.loads(report_path.read_text())
    assert data["summary"]["total_inserted"] == 1
    assert data["summary"]["total_updated"] == 0
    assert data["summary"]["total_events_processed"] == 1


def test_backfill_rejects_non_smart_write_before_extract(tmp_path, monkeypatch):
    from scripts.migracao import backfill_reprocessar

    monkeypatch.setattr(
        backfill_reprocessar,
        "extract_data_from_excel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("extract must not run without --smart-upsert")
        ),
    )

    exit_code = backfill_reprocessar.main(["--dir", str(tmp_path)])

    assert exit_code == 2


def test_backfill_persists_hierarchy_in_real_sqlite(tmp_path):
    from scripts.migracao import backfill_reprocessar

    source_file = tmp_path / "hierarchical_11-08-2026_0325AM.xlsx"
    db_path = tmp_path / "ssas.db"
    report_path = tmp_path / "report.json"
    pd.DataFrame(
        {
            "numero_ssa": ["202699008", None],
            "descricao_ssa": ["SSA pai", None],
            "data_cadastro": ["2026-08-11 03:25:00", None],
            "numero_desvios": ["Desvio #1", "Desvio #2"],
            "situacao_de_desvio": ["ADM", "AMP"],
            "arquivo_origem": ["forged_01-08-2026_0100AM.xlsx", None],
            "data_planilha": ["2026-08-01T01:00:00", None],
            "data_arquivo_origem": ["2026-08-01 01:00:00", None],
        }
    ).to_excel(source_file, index=False)
    backfill_reprocessar.database.initialize_database(
        str(db_path),
        str(BASE / "config" / "schema_unified.sql"),
    )

    exit_code = backfill_reprocessar.main(
        [
            "--dir",
            str(tmp_path),
            "--db",
            str(db_path),
            "--smart-upsert",
            "--report-path",
            str(report_path),
        ]
    )

    with sqlite3.connect(db_path) as conn:
        parent_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_table WHERE numero_ssa = ?",
            ("202699008",),
        ).fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM ssa_event_records WHERE numero_ssa = ?",
            ("202699008",),
        ).fetchone()[0]
        metadata = conn.execute(
            "SELECT arquivo_origem, data_planilha, data_arquivo_origem "
            "FROM ssa_table WHERE numero_ssa = ?",
            ("202699008",),
        ).fetchone()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert parent_count == 1
    assert event_count == 2
    assert metadata == (
        source_file.name,
        "2026-08-11T03:25:00",
        "2026-08-11 03:25:00",
    )
    assert report["summary"]["total_events_processed"] == 2
