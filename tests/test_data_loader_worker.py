import sqlite3
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste")

from gui.workers.data_loader_worker import DataLoaderWorker


def test_normalize_order_by_accepts_whitelisted_columns():
    worker = DataLoaderWorker("dummy.db", "ssa_table")
    clause = worker._normalize_order_by("numero_ssa DESC, situacao asc")
    assert clause == "numero_ssa DESC, situacao ASC"


def test_normalize_order_by_rejects_non_whitelisted_column():
    worker = DataLoaderWorker("dummy.db", "ssa_table")
    with pytest.raises(ValueError):
        worker._normalize_order_by("drop_table DESC")


def test_resolve_target_table_falls_back_to_ssa_table(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.commit()

    worker = DataLoaderWorker(str(db_path), "ssas")
    assert worker._resolve_target_table() == "ssa_table"


def test_run_builds_safe_paginated_query_and_emits_data():
    captured = {}
    emitted = []

    def fake_query(db_path, table_name, query):
        captured["query"] = query
        return pd.DataFrame({"numero_ssa": ["1"]})

    worker = DataLoaderWorker(
        "dummy.db",
        "ssa_table",
        limit=10,
        offset=5,
        order_by="numero_ssa DESC",
    )
    worker.data_loaded.connect(lambda df: emitted.append(df))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert emitted and not emitted[0].empty
    assert "ORDER BY numero_ssa DESC" in captured["query"]
    assert "LIMIT 10 OFFSET 5" in captured["query"]


def test_run_emits_error_for_invalid_order_by():
    errors = []
    worker = DataLoaderWorker(
        "dummy.db",
        "ssa_table",
        order_by="numero_ssa; DROP TABLE ssa_table",
    )
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    with patch("gui.workers.data_loader_worker.query_db") as query_mock:
        worker.run()

    assert errors
    query_mock.assert_not_called()
