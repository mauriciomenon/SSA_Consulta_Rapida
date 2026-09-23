"""Contract tests for responsavel option ranking and fingerprint budget.

Pipeline contracts; GUI menu wiring in test_scenario_responsavel_options_qt.py.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_domain_rules import (
    build_responsavel_sector_counts_by_column,
    generate_responsavel_sector_filter_cache_signature,
    normalize_nonempty_string_series,
    order_responsavel_values,
)
from gui.ssa.gui_filters_advanced_state import SECTOR_TO_DIV
from tests._helpers.contract_data_builders import (
    EXPECTED_RESP_EXEC_ORDER,
    build_advanced_filter_contract_df,
)


def test_order_responsavel_values_ranks_by_sector_then_name():
    df = build_advanced_filter_contract_df()
    counts_by_column = build_responsavel_sector_counts_by_column(
        df,
        resp_columns=["responsavel_execucao"],
    )
    sector_counts = counts_by_column.get("responsavel_execucao", {})
    ranked = order_responsavel_values(
        ["Exec C", "Exec A", "Exec B"],
        sector_counts,
        sector_to_div=SECTOR_TO_DIV,
    )
    persons = [person for person, _label in ranked]
    labels = [label for _person, label in ranked]

    assert persons == EXPECTED_RESP_EXEC_ORDER
    assert all(label for label in labels)
    assert any("IEE3" in label for label in labels)


def test_responsavel_signature_calls_hash_pandas_object_once():
    df = build_advanced_filter_contract_df()
    hash_calls = {"count": 0}
    original_hash = pd.util.hash_pandas_object

    def _spy_hash_pandas_object(*args, **kwargs):
        hash_calls["count"] += 1
        return original_hash(*args, **kwargs)

    with patch.object(pd.util, "hash_pandas_object", _spy_hash_pandas_object):
        signature = generate_responsavel_sector_filter_cache_signature(
            df,
            data_load_token=None,
            executor_include=["IEE3"],
        )

    assert hash_calls["count"] == 1
    assert isinstance(signature, tuple)
    assert signature[3] == ("IEE3",)


def test_responsavel_sector_counts_normalize_once_per_column_at_10k():
    df = pd.DataFrame(
        {
            "responsavel_execucao": [f"Exec {idx % 50:02d}" for idx in range(10_000)],
            "setor_executor": [f"SEC{idx % 10:02d}" for idx in range(10_000)],
            "setor_emissor": [f"EM{idx % 5:02d}" for idx in range(10_000)],
        }
    )
    normalize_calls = {"count": 0}
    original_normalize = normalize_nonempty_string_series

    def _spy_normalize(series: pd.Series) -> pd.Series:
        normalize_calls["count"] += 1
        return original_normalize(series)

    with patch(
        "gui.ssa.filter_domain_rules.normalize_nonempty_string_series",
        _spy_normalize,
    ):
        counts_by_column = build_responsavel_sector_counts_by_column(
            df,
            resp_columns=["responsavel_execucao"],
        )

    sector_counts = counts_by_column.get("responsavel_execucao", {})
    assert len(sector_counts) == 50
    assert normalize_calls["count"] == 3


def test_responsavel_signature_changes_when_executor_include_changes():
    df = build_advanced_filter_contract_df()
    first = generate_responsavel_sector_filter_cache_signature(
        df,
        data_load_token=None,
        executor_include=["IEE3"],
    )
    second = generate_responsavel_sector_filter_cache_signature(
        df,
        data_load_token=None,
        executor_include=["MEL4"],
    )
    assert first != second
