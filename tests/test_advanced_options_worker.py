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
