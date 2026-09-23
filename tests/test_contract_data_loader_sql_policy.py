"""Contract tests for DataLoader projection / LIMIT / OFFSET policy.

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
        select_columns=("numero_ssa", "situacao", "descricao_ssa"),
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
        select_columns=("numero_ssa", "situacao", "descricao_ssa"),
        order_by=None,
        limit=None,
        offset=0,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )
    normalized = query.upper()
    assert " OFFSET " not in normalized


@pytest.mark.parametrize(
    ("limit", "offset", "match"),
    [
        (-1, None, "LIMIT nao pode ser negativo"),
        (None, -5, "OFFSET nao pode ser negativo"),
    ],
)
def test_negative_limit_or_offset_raises(limit, offset, match):
    with pytest.raises(ValueError, match=match):
        build_select_query(
            target_table="ssa_data",
            select_columns=("numero_ssa", "situacao", "descricao_ssa"),
            order_by=None,
            limit=limit,
            offset=offset,
            default_sort_spec=DEFAULT_UI_SORT_SPEC,
        )


def test_disallowed_order_column_raises():
    with pytest.raises(ValueError, match="nao permitida"):
        build_select_query(
            target_table="ssa_data",
            select_columns=("numero_ssa", "situacao", "descricao_ssa"),
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
    assert "SELECT *" not in normalized
    assert normalized.startswith(
        'SELECT "NUMERO_SSA", "SITUACAO", "DESCRICAO_SSA", '
    )
    assert '0 AS "QTD_DERIVADAS" FROM "SSA_TABLE"' in normalized
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
    skipped = {f"2026{idx:05d}" for idx in range(10)} - set(loaded_ids)
    assert skipped == {"202600007", "202600008", "202600009"}


def test_build_select_query_limit_and_offset_combined():
    query, already_sorted = build_select_query(
        target_table="ssa_data",
        select_columns=("numero_ssa", "situacao", "descricao_ssa"),
        order_by="numero_ssa ASC",
        limit=5,
        offset=2,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )
    normalized = query.upper()
    assert " LIMIT 5" in normalized
    assert " OFFSET 2" in normalized
    assert already_sorted is False


def test_data_loader_worker_limit_and_offset_combined(tmp_path):
    db_path = tmp_path / "loader_limit_offset.db"
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

    worker = DataLoaderWorker(
        str(db_path), "ssa_table", limit=3, offset=2, order_by="numero_ssa ASC"
    )
    payloads: list = []
    worker.data_prepared.connect(payloads.append)
    worker.run()

    loaded_ids = payloads[0].complete["numero_ssa"].astype(str).tolist()
    assert len(loaded_ids) == 3
    assert loaded_ids == ["202600002", "202600003", "202600004"]
