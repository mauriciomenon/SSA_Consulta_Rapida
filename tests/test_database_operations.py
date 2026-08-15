from __future__ import annotations

import pandas as pd

from gui.ssa.database_operations import validate_database_candidate


def test_validate_database_candidate_raises_query_errors_explicitly():
    calls: list[dict[str, object]] = []

    def _query_db(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("db open failed")

    result = validate_database_candidate(
        "/tmp/candidate.db",
        table_name="ssa_table",
        query_db_fn=_query_db,
    )

    assert result == {
        "ok": False,
        "error": "db open failed",
        "db_file": "/tmp/candidate.db",
    }
    assert calls[0]["kwargs"] == {"raise_on_error": True}


def test_validate_database_candidate_accepts_non_empty_table():
    def _query_db(*args, **kwargs):
        return pd.DataFrame({"numero_ssa": ["202600001"]})

    result = validate_database_candidate(
        "/tmp/candidate.db",
        table_name="ssa_table",
        query_db_fn=_query_db,
    )

    assert result == {"ok": True, "db_file": "/tmp/candidate.db"}
