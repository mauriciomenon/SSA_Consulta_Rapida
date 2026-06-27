"""Contract tests for FilterCache get/put mutation isolation."""

from __future__ import annotations

import pandas as pd

from gui.cache.filter_cache import FilterCache


def test_filter_cache_get_put_isolates_mutation():
    cache = FilterCache(max_size=2)
    source_df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    cache.put("df_small", [["x"]], "contains", source_df)
    source_df.loc[0, "a"] = 999
    source_df.loc[0, "b"] = "changed"

    cached_first = cache.get("df_small", [["x"]], "contains")

    assert cached_first is not None
    assert cached_first["a"].tolist() == [1, 2]
    assert cached_first["b"].tolist() == ["x", "y"]

    cached_first.loc[1, "a"] = 777
    cached_second = cache.get("df_small", [["x"]], "contains")

    assert cached_second is not None
    assert cached_second["a"].tolist() == [1, 2]
    assert cached_second["b"].tolist() == ["x", "y"]
