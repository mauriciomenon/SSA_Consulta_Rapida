"""Contract tests for advanced filter option cache invalidation.

Pipeline contracts; GUI dirty-gate wiring in test_scenario_adv_options_dirty_gate_qt.py
and load-waste scenarios in test_scenario_adv_options_load_waste_qt.py.
"""

from __future__ import annotations

import pandas as pd

from gui.ssa.gui_filters_advanced_refresh import get_cached_advanced_filter_option_values
from tests._helpers.contract_data_builders import (
    EXPECTED_ADV_EXEC_VALS,
    EXPECTED_ADV_EXEC_VALS_WITH_ZZZ9,
    build_advanced_filter_contract_df,
)


def test_cache_miss_after_inplace_mutation_without_force_refresh():
    cache: dict = {}
    token = object()
    df = build_advanced_filter_contract_df()

    first = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
    )
    df.loc[0, "setor_executor"] = "ZZZ9"
    cached = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
    )

    assert first.exec_vals == EXPECTED_ADV_EXEC_VALS
    assert cached.exec_vals == EXPECTED_ADV_EXEC_VALS
    assert cached is first
    assert "ZZZ9" not in cached.exec_vals


def test_force_refresh_recomputes_after_inplace_mutation():
    cache: dict = {}
    token = object()
    df = build_advanced_filter_contract_df()

    get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
    )
    df.loc[0, "setor_executor"] = "ZZZ9"
    refreshed = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
        force_refresh=True,
    )

    assert refreshed.exec_vals == EXPECTED_ADV_EXEC_VALS_WITH_ZZZ9


def test_cache_separates_same_shape_different_dataframes():
    cache: dict = {}
    token = object()
    first_df = pd.DataFrame(
        {
            "setor_executor": ["IEE1"],
            "setor_emissor": ["MEL4"],
            "situacao": ["APV"],
        }
    )
    second_df = pd.DataFrame(
        {
            "setor_executor": ["ZZZ9"],
            "setor_emissor": ["MEL4"],
            "situacao": ["APV"],
        }
    )

    first_values = get_cached_advanced_filter_option_values(
        cache,
        first_df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
    )
    second_values = get_cached_advanced_filter_option_values(
        cache,
        second_df,
        data_load_token=token,
        sort_sectors=lambda values: sorted(values),
    )

    assert first_values.exec_vals == ["IEE1"]
    assert second_values.exec_vals == ["ZZZ9"]
    assert second_values is not first_values


def test_data_load_token_change_invalidates_cached_values():
    cache: dict = {}
    df = build_advanced_filter_contract_df()

    first_token = object()
    second_token = object()
    first = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=first_token,
        sort_sectors=lambda values: sorted(values),
    )
    second = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=second_token,
        sort_sectors=lambda values: sorted(values),
    )

    assert first.exec_vals == second.exec_vals
    assert second is not first
