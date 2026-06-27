"""Contract tests for responsavel option ranking and fingerprint budget."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from gui.ssa.filter_domain_rules import (
    build_responsavel_sector_counts_by_column,
    generate_responsavel_sector_filter_cache_signature,
    order_responsavel_values,
)
from gui.ssa.gui_filters_advanced_state import SECTOR_TO_DIV
from tests._helpers.contract_data_builders import build_advanced_filter_contract_df


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

    assert persons == ["Exec B", "Exec C", "Exec A"]
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
