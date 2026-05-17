import sqlite3
from contextlib import closing
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication

from gui.workers.data_loader_processing import (
    prepare_dataframe_for_ui,
    sanitize_ssa_like_value,
)
from gui.workers.data_loader_worker import DataLoaderWorker


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_normalize_order_by_accepts_whitelisted_columns():
    worker = DataLoaderWorker(":memory:", "ssa_table")
    clause = worker._normalize_order_by("numero_ssa DESC, situacao asc")
    assert clause == '"numero_ssa" DESC, "situacao" ASC'


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


def test_resolve_target_table_accepts_second_legacy_alias(tmp_path):
    db_path = tmp_path / "test_second_alias.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.commit()

    worker = DataLoaderWorker(str(db_path), "ssa_chamados")
    assert worker._resolve_target_table() == "ssa_table"


def test_resolve_target_table_invalid_identifier_falls_back_to_canonical():
    worker = DataLoaderWorker(":memory:", 'ssa_table"; DROP TABLE ssa_table; --')
    assert worker._resolve_target_table() == "ssa_table"


def test_run_builds_safe_paginated_query_and_emits_data():
    captured = {}
    prepared = []

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
    worker.data_prepared.connect(lambda payload: prepared.append(payload))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert prepared and not prepared[0].complete.empty
    assert prepared[0].preprocessed_for_gui is True
    assert prepared[0].complete["numero_ssa"].tolist() == ["1"]
    assert prepared[0].complete.attrs.get("ssa_preprocessed_for_gui") is True
    assert "ssa_sanitized_df" not in prepared[0].complete.attrs
    assert isinstance(prepared[0].complete.attrs.get("ssa_non_null_cols"), list)
    assert 'ORDER BY "numero_ssa" DESC' in captured["query"]
    assert "LIMIT 10 OFFSET 5" in captured["query"]


def test_run_adds_deterministic_order_for_paginated_query_without_order_by():
    captured = {}
    emitted = []

    def fake_query(db_path, table_name, query, **kwargs):
        captured["query"] = query
        return pd.DataFrame({"numero_ssa": ["1"]})

    worker = DataLoaderWorker(":memory:", "ssa_table", limit=10, offset=5)
    worker.data_loaded.connect(lambda df: emitted.append(df))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert emitted and not emitted[0].empty
    assert f'ORDER BY {worker._build_default_ui_order_clause()}' in captured["query"]
    assert "LIMIT 10 OFFSET 5" in captured["query"]


def test_run_uses_positive_limit_placeholder_when_offset_has_no_limit():
    captured = {}
    emitted = []

    def fake_query(db_path, table_name, query, **kwargs):
        captured["query"] = query
        return pd.DataFrame({"numero_ssa": ["1"]})

    worker = DataLoaderWorker(":memory:", "ssa_table", offset=5)
    worker.data_loaded.connect(lambda df: emitted.append(df))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert emitted and not emitted[0].empty
    assert f"LIMIT {worker._SQLITE_OFFSET_WITHOUT_LIMIT} OFFSET 5" in captured["query"]
    assert "LIMIT -1" not in captured["query"]


def test_run_uses_business_default_order_for_full_load_without_order_by():
    captured = {}
    emitted = []

    def fake_query(db_path, table_name, query, **kwargs):
        captured["query"] = query
        return pd.DataFrame({"numero_ssa": ["202500005"], "situacao": ["APV"]})

    worker = DataLoaderWorker(":memory:", "ssa_table")
    worker.data_loaded.connect(lambda df: emitted.append(df))

    with patch("gui.workers.data_loader_worker.query_db", side_effect=fake_query):
        worker.run()

    assert emitted and not emitted[0].empty
    assert f'ORDER BY {worker._build_default_ui_order_clause()}' in captured["query"]


def test_prepare_dataframe_for_ui_preserves_custom_order_by_contract():
    source_df = pd.DataFrame(
        {
            "numero_ssa": ["202500003.0", "202500001.0", "202500002.0"],
            "derivada_de": [None, None, None],
            "situacao": ["SCA", "STE", "SCA"],
        }
    )

    prepared_df = prepare_dataframe_for_ui(source_df, order_by="situacao ASC")

    assert prepared_df["situacao"].tolist() == ["SCA", "STE", "SCA"]
    assert prepared_df["numero_ssa"].tolist() == [
        "202500003",
        "202500001",
        "202500002",
    ]


def test_prepare_dataframe_for_ui_default_order_keeps_non_ste_first_then_desc_ssa():
    source_df = pd.DataFrame(
        {
            "numero_ssa": [
                "202500001.0",
                "202500005.0",
                "202500004.0",
                "202500003.0",
            ],
            "derivada_de": [None, None, None, None],
            "situacao": ["STE", "APV", "STE", "AMP"],
        }
    )

    prepared_df = prepare_dataframe_for_ui(source_df)

    assert prepared_df["numero_ssa"].tolist() == [
        "202500005",
        "202500003",
        "202500004",
        "202500001",
    ]
    assert prepared_df["situacao"].tolist() == ["APV", "AMP", "STE", "STE"]


def test_prepare_dataframe_for_ui_sanitizes_and_attaches_attrs():
    source_df = pd.DataFrame(
        {
            "numero_ssa": ["202500002.0", 202500003.0, "SSA-202500001"],
            "derivada_de": ["202400001.0", None, "nan"],
            "situacao": ["STE", "SCA", "SCA"],
        }
    )

    prepared_df = prepare_dataframe_for_ui(source_df)

    assert prepared_df.attrs.get("ssa_preprocessed_for_gui") is True
    assert "ssa_sanitized_df" not in prepared_df.attrs
    assert "202500002" in prepared_df["numero_ssa"].tolist()
    assert "202500003" in prepared_df["numero_ssa"].tolist()
    assert "202400001" in prepared_df["derivada_de"].tolist()
    assert "" in prepared_df["derivada_de"].tolist()
    assert isinstance(prepared_df.attrs.get("ssa_non_null_cols"), list)
    assert set(prepared_df["situacao"].tolist()) == {"STE", "SCA"}


def test_sanitize_ssa_like_value_does_not_fold_unrelated_text_with_nine_digits():
    assert sanitize_ssa_like_value("Order 123-456-789") == "Order 123-456-789"
    assert sanitize_ssa_like_value("SSA-202500001") == "202500001"


def test_prepare_dataframe_for_ui_fallback_sort_matches_sqlite_integer_cast_prefix():
    source_df = pd.DataFrame(
        {
            "numero_ssa": ["2025-001", "SSA-202500001", "202500001.0", ""],
            "derivada_de": [None, None, None, None],
            "situacao": ["APV", "APV", "APV", "APV"],
        }
    )

    prepared_df = prepare_dataframe_for_ui(source_df)

    assert prepared_df["numero_ssa"].tolist() == [
        "202500001",
        "2025-001",
        "202500001",
        "",
    ]


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
