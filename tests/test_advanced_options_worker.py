from __future__ import annotations

import pandas as pd

from gui.ssa.gui_filters_advanced_refresh import (
    get_cached_advanced_filter_option_values,
)
from gui.workers.advanced_options_worker import AdvancedOptionsWorker


def test_advanced_options_worker_does_not_mutate_source_cache() -> None:
    dataframe = pd.DataFrame(
        {
            "setor_executor": ["MEL4", "IEE3"],
            "setor_emissor": ["MEL3", "IEE3"],
            "situacao": ["APV", "STE"],
        }
    )
    source_cache = {"sentinel": "preserved"}
    delivered = []
    worker = AdvancedOptionsWorker(
        dataframe,
        {},
        source_cache,
        1,
        sorted,
        get_cached_fn=get_cached_advanced_filter_option_values,
    )
    worker.ui_state_ready.connect(delivered.append)

    worker.run()

    assert source_cache == {"sentinel": "preserved"}
    assert len(delivered) == 1
    assert worker.cache_snapshot()["values"] is delivered[0].values


def test_advanced_options_worker_cancel_before_calculation() -> None:
    calls = []
    delivered = []
    errors = []

    def calculate(*args, **kwargs):
        calls.append((args, kwargs))

    worker = AdvancedOptionsWorker(pd.DataFrame(), {}, {}, 1, sorted, calculate)
    worker.ui_state_ready.connect(delivered.append)
    worker.error_occurred.connect(errors.append)
    worker.cancel()

    worker.run()

    assert calls == []
    assert delivered == []
    assert errors == []


def test_advanced_options_worker_cancel_between_dataframe_passes() -> None:
    dataframe = pd.DataFrame(
        {
            "data_cadastro": ["2024-01-01"],
            "setor_executor": ["MEL4"],
            "setor_emissor": ["IEE3"],
        }
    )
    source_cache = {"sentinel": "preserved"}
    delivered = []
    errors = []
    sector_sort_calls = []

    def sort_sectors(values):
        sector_sort_calls.append(values)
        worker.cancel()
        return values

    worker = AdvancedOptionsWorker(
        dataframe,
        {},
        source_cache,
        1,
        sort_sectors,
        get_cached_fn=get_cached_advanced_filter_option_values,
    )
    worker.ui_state_ready.connect(delivered.append)
    worker.error_occurred.connect(errors.append)

    worker.run()

    assert sector_sort_calls == [["MEL4"]]
    assert source_cache == {"sentinel": "preserved"}
    assert worker.cache_snapshot() == source_cache
    assert delivered == []
    assert errors == []
