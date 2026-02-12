from __future__ import annotations

import json
import sqlite3

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

