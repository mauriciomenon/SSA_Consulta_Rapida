"""Contract tests for DataLoader SELECT * / LIMIT / OFFSET policy.

Cross-ref: gui/workers/data_loader_query.py (build_select_query).
Integration test would fail if OFFSET were ignored (len != 7, wrong first id).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from unittest.mock import patch

import pytest

from gui.workers.data_loader_processing import DEFAULT_UI_SORT_SPEC
from gui.workers.data_loader_query import (
    SQLITE_OFFSET_WITHOUT_LIMIT,
    build_select_query,
)
from gui.workers.data_loader_worker import DataLoaderWorker

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_offset_without_explicit_limit_adds_sqlite_cap():
    query, already_sorted = build_select_query(
        target_table="ssa_data",
        order_by=None,
        limit=None,
        offset=25,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )
    normalized = query.upper()
    assert f"LIMIT {SQLITE_OFFSET_WITHOUT_LIMIT}" in normalized
    assert " OFFSET 25" in normalized
    assert already_sorted is True


def test_zero_offset_omits_offset_clause():
    query, _already_sorted = build_select_query(
        target_table="ssa_data",
        order_by=None,
        limit=None,
        offset=0,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )
    normalized = query.upper()
    assert " OFFSET " not in normalized


def test_negative_limit_raises():
    with pytest.raises(ValueError, match="LIMIT nao pode ser negativo"):
        build_select_query(
            target_table="ssa_data",
            order_by=None,
            limit=-1,
            offset=None,
            default_sort_spec=DEFAULT_UI_SORT_SPEC,
        )


def test_negative_offset_raises():
    with pytest.raises(ValueError, match="OFFSET nao pode ser negativo"):
        build_select_query(
            target_table="ssa_data",
            order_by=None,
            limit=None,
            offset=-5,
            default_sort_spec=DEFAULT_UI_SORT_SPEC,
        )


def test_disallowed_order_column_raises():
    with pytest.raises(ValueError, match="nao permitida"):
        build_select_query(
            target_table="ssa_data",
            order_by="password ASC",
            limit=10,
            offset=0,
            default_sort_spec=DEFAULT_UI_SORT_SPEC,
        )


def test_data_loader_worker_sql_contains_offset_clause(tmp_path):
    db_path = tmp_path / "loader_offset_sql.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            "CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT, descricao_ssa TEXT)"
        )
        for idx in range(10):
            conn.execute(
                "INSERT INTO ssa_table VALUES (?, ?, ?)",
                (f"2026{idx:05d}", "APV", f"Desc {idx}"),
            )
        conn.commit()

    captured: dict[str, str] = {}

    def capture_query(_db_path, _table_name, query, **_kwargs):
        captured["query"] = query
        from armazenamento.database import query_db

        return query_db(str(db_path), "", query, raise_on_error=True)

    worker = DataLoaderWorker(str(db_path), "ssa_table", offset=3)
    with patch("gui.workers.data_loader_worker.query_db", side_effect=capture_query):
        worker.run()

    normalized = captured["query"].upper()
    assert f"LIMIT {SQLITE_OFFSET_WITHOUT_LIMIT}" in normalized
    assert " OFFSET 3" in normalized


def test_data_loader_worker_offset_skips_first_rows(tmp_path):
    db_path = tmp_path / "loader_offset.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            "CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT, descricao_ssa TEXT)"
        )
        for idx in range(10):
            conn.execute(
                "INSERT INTO ssa_table VALUES (?, ?, ?)",
                (f"2026{idx:05d}", "APV", f"Desc {idx}"),
            )
        conn.commit()

    worker = DataLoaderWorker(str(db_path), "ssa_table", offset=3)
    payloads: list = []
    worker.data_prepared.connect(payloads.append)
    worker.run()

    assert len(payloads) == 1
    loaded_ids = payloads[0].complete["numero_ssa"].astype(str).tolist()
    assert len(loaded_ids) == 7
    assert loaded_ids[0] == "202600006"
    assert loaded_ids == [
        "202600006",
        "202600005",
        "202600004",
        "202600003",
        "202600002",
        "202600001",
        "202600000",
    ]
    assert "202600009" not in loaded_ids
    assert "202600008" not in loaded_ids
    assert "202600007" not in loaded_ids
