from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import scripts.derivadas_cli as derivadas_cli
from scripts.derivadas_cli import main


def _seed_cli_data(db_path: str) -> None:
    rows = [
        ("202500001", None),
        ("202500002", "202500001"),
        ("202500003", "202500002"),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [(numero_ssa, derivada_de, f"SSA {numero_ssa}") for numero_ssa, derivada_de in rows],
        )
        conn.commit()


def test_cli_sync_verify_only_json(temp_db, capsys):
    _seed_cli_data(temp_db)
    rc = main(["--db", temp_db, "--output", "json", "sync", "--verify-only"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["verify_only"] is True
    assert parsed["merge_stats"]["merged_edges"] == 2


def test_cli_sync_and_info(temp_db, capsys):
    _seed_cli_data(temp_db)
    rc_sync = main(["--db", temp_db, "--output", "json", "sync"])
    assert rc_sync == 0
    _ = capsys.readouterr()

    rc_info = main(["--db", temp_db, "--output", "json", "info", "202500001", "--with-lineage", "--depth", "5"])
    assert rc_info == 0
    out_info = capsys.readouterr().out
    parsed_info = json.loads(out_info)
    assert parsed_info["profile"]["ssa"] == "202500001"
    assert len(parsed_info["descendants"]) >= 2


def test_cli_parents_and_top(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    assert main(["--db", temp_db, "--output", "json", "parents", "202500003"]) == 0
    parsed_parents = json.loads(capsys.readouterr().out)
    assert parsed_parents["parents"] == ["202500002"]

    assert main(["--db", temp_db, "--output", "json", "top", "--metric", "descendants", "--limit", "1"]) == 0
    parsed_top = json.loads(capsys.readouterr().out)
    assert parsed_top["rows"]
    assert parsed_top["rows"][0]["ssa"] == "202500001"


def test_cli_scan_reports_consistent_after_sync(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    assert main(["--db", temp_db, "--output", "json", "scan"]) == 0
    parsed_scan = json.loads(capsys.readouterr().out)
    assert parsed_scan["is_consistent"] is True
    assert parsed_scan["issue_counts"]["fingerprint_mismatch"] == 0
    assert parsed_scan["graph_fingerprint"]


def test_cli_heal_repairs_inconsistent_flags(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    with sqlite3.connect(temp_db) as conn:
        conn.execute("UPDATE ssa_derivada_matrix SET source_flags = 0 WHERE active = 1")
        conn.commit()

    assert main(["--db", temp_db, "--output", "json", "heal"]) == 0
    parsed_heal = json.loads(capsys.readouterr().out)
    assert parsed_heal["healed"] is True
    assert parsed_heal["after"]["is_consistent"] is True


def test_cli_maintenance_interval_guard(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    assert main(["--db", temp_db, "--output", "json", "maintenance", "--min-interval-seconds", "3600"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ran"] is False
    assert parsed["reason"] == "interval_guard"


def test_cli_maintenance_scan_only_when_auto_heal_disabled(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            UPDATE ssa_derivada_matrix
            SET source_flags = 0
            WHERE parent_ssa = '202500001' AND child_ssa = '202500002'
            """
        )
        conn.commit()

    assert (
        main(
            [
                "--db",
                temp_db,
                "--output",
                "json",
                "maintenance",
                "--min-interval-seconds",
                "0",
                "--no-auto-heal",
            ]
        )
        == 0
    )
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ran"] is True
    assert parsed["scan_only"] is True
    assert parsed["is_consistent"] is False
    assert parsed["scan"]["issue_counts"]["flag_mismatch_pairs"] >= 1


def test_cli_sync_requires_one_enabled_source(temp_db):
    _seed_cli_data(temp_db)
    with pytest.raises(ValueError, match="at least one source"):
        main(["--db", temp_db, "--output", "json", "sync", "--no-db-source"])


def test_cli_schema_scan_reports_missing_on_fresh_db(temp_db, capsys):
    assert main(["--db", temp_db, "--output", "json", "schema-scan"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["is_ready"] is False
    assert "ssa_derivada_matrix" in parsed["missing_tables"]


def test_cli_snapshot_returns_hierarchy_payload(temp_db, capsys):
    _seed_cli_data(temp_db)
    assert main(["--db", temp_db, "--output", "json", "sync"]) == 0
    _ = capsys.readouterr()

    assert main(["--db", temp_db, "--output", "json", "snapshot", "202500001", "--depth", "5"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ssa"] == "202500001"
    assert parsed["children_count"] == 1
    assert parsed["hierarchy_profile"]["descendants_count"] >= 1


def test_cli_sync_accepts_sheet_files_glob(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    first = tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0124PM.xlsx"
    second = tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0137PM.xlsx"
    first.write_bytes(b"x")
    second.write_bytes(b"y")

    captured: dict = {}

    def _fake_sync_derivadas(**kwargs):
        captured.update(kwargs)
        return {"verify_only": False, "merge_stats": {"merged_edges": 0}}

    monkeypatch.setattr(derivadas_cli, "sync_derivadas", _fake_sync_derivadas)

    rc = main(
        [
            "--db",
            "data/ssas.db",
            "--output",
            "json",
            "sync",
            "--sheet-files-glob",
            str(tmp_path / "SSAs Derivadas e Relacionadas_*.xlsx"),
            "--no-db-source",
        ]
    )

    assert rc == 0
    assert captured["include_db_source"] is False
    assert captured["sheet_files"] == [str(first), str(second)]
