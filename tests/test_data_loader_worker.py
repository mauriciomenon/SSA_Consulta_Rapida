import sqlite3
from contextlib import closing
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste")
from PyQt6.QtWidgets import QApplication

from gui.workers.data_loader_worker import DataLoaderWorker


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_normalize_order_by_accepts_whitelisted_columns():
    worker = DataLoaderWorker(":memory:", "ssa_table")
    clause = worker._normalize_order_by("numero_ssa DESC, situacao asc")
    assert clause == "numero_ssa DESC, situacao ASC"


def test_normalize_order_by_rejects_non_whitelisted_column():
    worker = DataLoaderWorker(":memory:", "ssa_table")
    with pytest.raises(ValueError):
        worker._normalize_order_by("drop_table DESC")


def test_resolve_target_table_falls_back_to_ssa_table(tmp_path):
    db_path = tmp_path / "test.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.commit()

    worker = DataLoaderWorker(str(db_path), "ssas")
    assert worker._resolve_target_table() == "ssa_table"


def test_run_builds_safe_paginated_query_and_emits_data():
    captured = {}
    emitted = []

    def fake_query(db_path, table_name, query, **kwargs):
        captured["query"] = query
        return pd.DataFrame({"numero_ssa": ["1"]})

    worker = DataLoaderWorker(
        ":memory:",
        "ssa_table",
        limit=10,
        offset=5,
        order_by="numero_ssa DESC",
    )
    worker.data_loaded.connect(lambda df: emitted.append(df))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert emitted and not emitted[0].empty
    assert emitted[0]["numero_ssa"].tolist() == ["1"]
    assert "ORDER BY numero_ssa DESC" in captured["query"]
    assert "LIMIT 10 OFFSET 5" in captured["query"]


def test_run_emits_error_for_invalid_order_by():
    errors = []
    worker = DataLoaderWorker(
        ":memory:",
        "ssa_table",
        order_by="numero_ssa; DROP TABLE ssa_table",
    )
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    with patch("gui.workers.data_loader_worker.query_db") as query_mock:
        worker.run()

    assert errors
    query_mock.assert_not_called()


def test_run_emits_error_when_query_fails():
    emitted = []
    errors = []
    worker = DataLoaderWorker(":memory:", "ssa_table")
    worker.data_loaded.connect(lambda df: emitted.append(df))
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    with patch(
        "gui.workers.data_loader_worker.query_db",
        side_effect=RuntimeError("db failure"),
    ):
        worker.run()

    assert emitted == []
    assert errors


def test_run_emits_empty_dataframe_without_error_for_empty_page():
    emitted = []
    errors = []
    worker = DataLoaderWorker(":memory:", "ssa_table", limit=10, offset=9999)
    worker.data_loaded.connect(lambda df: emitted.append(df))
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    with patch(
        "gui.workers.data_loader_worker.query_db",
        return_value=pd.DataFrame(columns=["numero_ssa"]),
    ):
        worker.run()

    assert errors == []
    assert len(emitted) == 1
    assert emitted[0].empty


def test_run_skips_query_when_interrupted_before_start():
    emitted = []
    errors = []
    worker = DataLoaderWorker(":memory:", "ssa_table")
    worker.data_loaded.connect(lambda df: emitted.append(df))
    worker.error_occurred.connect(lambda msg: errors.append(msg))
    worker.cancel()

    with patch("gui.workers.data_loader_worker.query_db") as query_mock:
        worker.run()

    assert emitted == []
    assert errors == []
    query_mock.assert_not_called()


def test_run_skips_emit_when_interrupted_after_query():
    emitted = []
    errors = []
    worker = DataLoaderWorker(":memory:", "ssa_table")
    worker.data_loaded.connect(lambda df: emitted.append(df))
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    def _fake_query(_db_path, _table_name, _query, **kwargs):
        worker.cancel()
        return pd.DataFrame({"numero_ssa": ["1"]})

    with patch("gui.workers.data_loader_worker.query_db", side_effect=_fake_query):
        worker.run()

    assert emitted == []
    assert errors == []
