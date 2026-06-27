from __future__ import annotations

import pandas as pd

from gui.ssa.gui_filters_advanced_refresh import (
    get_cached_advanced_filter_option_values,
)


def test_advanced_option_values_cache_separates_same_shape_dataframes():
    cache = {}
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
        data_load_token="same-token",
        sort_sectors=lambda values: sorted(values),
    )
    second_values = get_cached_advanced_filter_option_values(
        cache,
        second_df,
        data_load_token="same-token",
        sort_sectors=lambda values: sorted(values),
    )

    assert first_values.exec_vals == ["IEE1"]
    assert second_values.exec_vals == ["ZZZ9"]
