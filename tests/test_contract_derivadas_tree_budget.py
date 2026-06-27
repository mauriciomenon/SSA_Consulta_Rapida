"""Contract tests for derivadas tree node budget limits."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from armazenamento.derivadas_queries import (
    DERIVADAS_FAMILY_NODE_LIMIT,
    build_family_payload_from_edges,
)
from gui.ssa.details_derivadas_model import normalize_tree_data
from gui.ssa.details_dialog_constants import DERIVADAS_GRAPH_MAX_DESCENDANTS
from gui.ssa.gui_filters_advanced_logic import (
    AdvancedFilterState,
    _build_derivadas_tree_core,
)
from tests._helpers.contract_data_builders import build_large_derivadas_chain


class _DummyWindow:
    def __init__(self) -> None:
        self._advanced_filters = {}


def _normalize_ssa_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def test_family_payload_truncates_large_family():
    df = build_large_derivadas_chain(total_nodes=150)
    edges = list(
        zip(df["derivada_de"].tolist(), df["numero_ssa"].tolist(), strict=False)
    )
    edges = [(parent, child) for parent, child in edges if parent]

    payload = build_family_payload_from_edges(
        "202600001",
        edges,
        max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
    )

    assert payload["family_truncated"] is True
    assert len(payload["family_descendants"]) <= DERIVADAS_GRAPH_MAX_DESCENDANTS


def test_normalize_tree_data_marks_partial_when_truncated():
    payload = {
        "parents": ["202600000"],
        "children": [],
        "family_roots": ["202600000"],
        "family_descendants": [
            {"ssa": f"2026{idx:05d}", "parent": "202600000"} for idx in range(2, 130)
        ],
        "family_truncated": True,
    }

    tree_data = normalize_tree_data(
        target="202600001",
        snapshot=None,
        fallback_children=[],
        direct_parent="202600000",
        local_payload=payload,
        related=[],
        target_status="APG",
    )

    assert tree_data["descendants_partial"] is True
    descendants = tree_data["descendants"]
    assert isinstance(descendants, list)
    assert len(descendants) == len(payload["family_descendants"])


def test_family_node_limit_constant_is_within_query_cap():
    assert DERIVADAS_GRAPH_MAX_DESCENDANTS <= DERIVADAS_FAMILY_NODE_LIMIT


def test_build_derivadas_tree_itertuples_budget_at_10k():
    df = build_large_derivadas_chain(total_nodes=10_000)
    state = AdvancedFilterState(_DummyWindow())
    itertuples_calls = {"count": 0}
    original_itertuples = pd.DataFrame.itertuples

    def _spy_itertuples(self, *args, **kwargs):
        itertuples_calls["count"] += 1
        return original_itertuples(self, *args, **kwargs)

    with patch.object(pd.DataFrame, "itertuples", _spy_itertuples):
        _build_derivadas_tree_core(
            df,
            "numero_ssa",
            "derivada_de",
            state,
            cache_token=1,
            normalize_ssa_series=_normalize_ssa_series,
        )

    assert itertuples_calls["count"] == 1
