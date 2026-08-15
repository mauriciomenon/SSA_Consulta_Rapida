"""Contract tests for DataLoaderWorker SELECT query construction."""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication

from gui.workers.data_loader_processing import DEFAULT_UI_SORT_SPEC
from gui.workers.data_loader_query import build_select_query
from gui.workers.data_loader_worker import DataLoaderWorker


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_build_select_query_without_limit_uses_select_star():
    query, already_sorted = build_select_query(
        target_table="ssa_data",
        order_by=None,
        limit=None,
        offset=None,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )

    normalized = query.upper()
    assert normalized.startswith("SELECT * FROM")
    assert " LIMIT " not in normalized
    assert " ORDER BY " in normalized
    assert "NUMERO_SSA" in normalized
    assert already_sorted is True


def test_build_select_query_with_limit_includes_limit_clause():
    query, already_sorted = build_select_query(
        target_table="ssa_data",
        order_by="numero_ssa DESC",
        limit=100,
        offset=0,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )

    assert "LIMIT 100" in query.upper()
    assert already_sorted is False


def test_data_loader_worker_e2e_sqlite_loads_full_table_without_limit(tmp_path):
    db_path = tmp_path / "loader_contract.db"
    row_count = 42
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            "CREATE TABLE ssa_table (numero_ssa TEXT, situacao TEXT, descricao_ssa TEXT)"
        )
        for idx in range(row_count):
            conn.execute(
                "INSERT INTO ssa_table VALUES (?, ?, ?)",
                (f"2026{idx:05d}", "APV" if idx % 2 == 0 else "STE", f"Desc {idx}"),
            )
        conn.commit()

    prepared_payloads: list = []
    worker = DataLoaderWorker(str(db_path), "ssa_table")
    worker.data_prepared.connect(prepared_payloads.append)
    worker.run()

    assert len(prepared_payloads) == 1
    payload = prepared_payloads[0]
    assert len(payload.complete) == row_count
    assert payload.preprocessed_for_gui is True
    expected_ids = {f"2026{idx:05d}" for idx in range(row_count)}
    assert set(payload.complete["numero_ssa"].astype(str)) == expected_ids
    assert payload.complete["numero_ssa"].astype(str).nunique() == row_count

    query, _already_sorted = build_select_query(
        target_table="ssa_table",
        order_by=None,
        limit=None,
        offset=None,
        default_sort_spec=DEFAULT_UI_SORT_SPEC,
    )
    assert " LIMIT " not in query.upper()
