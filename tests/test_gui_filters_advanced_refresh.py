from __future__ import annotations

import pandas as pd

from gui.ssa.gui_filters_advanced_refresh import (
    get_cached_advanced_filter_option_values,
)


def test_advanced_option_values_cache_separates_same_shape_dataframes():
    cache = {}
    same_revision = object()
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
        data_load_token=same_revision,
        sort_sectors=lambda values: sorted(values),
    )
    second_values = get_cached_advanced_filter_option_values(
        cache,
        second_df,
        data_load_token=same_revision,
        sort_sectors=lambda values: sorted(values),
    )

    assert first_values.exec_vals == ["IEE1"]
    assert second_values.exec_vals == ["ZZZ9"]


def test_advanced_option_values_force_refresh_recomputes_same_dataframe():
    cache = {}
    same_revision = object()
    df = pd.DataFrame(
        {
            "setor_executor": ["IEE1"],
            "setor_emissor": ["MEL4"],
            "situacao": ["APV"],
        }
    )

    first_values = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=same_revision,
        sort_sectors=lambda values: sorted(values),
    )
    df.loc[0, "setor_executor"] = "ZZZ9"
    cached_values = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=same_revision,
        sort_sectors=lambda values: sorted(values),
    )
    refreshed_values = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=same_revision,
        sort_sectors=lambda values: sorted(values),
        force_refresh=True,
    )

    assert first_values.exec_vals == ["IEE1"]
    assert cached_values.exec_vals == ["IEE1"]
    assert refreshed_values.exec_vals == ["ZZZ9"]
