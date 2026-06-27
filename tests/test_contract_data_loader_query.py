"""Contract tests for DataLoaderWorker SELECT query construction."""

from __future__ import annotations

from gui.workers.data_loader_processing import DEFAULT_UI_SORT_SPEC
from gui.workers.data_loader_query import build_select_query


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
