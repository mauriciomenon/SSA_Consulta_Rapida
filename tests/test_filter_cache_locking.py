import pandas as pd

from gui.cache.filter_cache import FilterCache


class _SpyLock:
    def __init__(self) -> None:
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self):
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exit_count += 1
        return False


def test_filter_cache_uses_lock_for_all_mutations_and_reads():
    spy = _SpyLock()
    cache = FilterCache(max_size=2, lock=spy)

    df = pd.DataFrame({"a": [1, 2]})

    assert spy.enter_count == 0
    before_put = spy.enter_count
    cache.put("df1", [["x"]], "contains", df)
    assert spy.enter_count == before_put + 1
    assert spy.enter_count == spy.exit_count

    before_get = spy.enter_count
    hit = cache.get("df1", [["x"]], "contains")
    assert isinstance(hit, pd.DataFrame)
    assert spy.enter_count == before_get + 1
    assert spy.enter_count == spy.exit_count

    before_stats = spy.enter_count
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert spy.enter_count == before_stats + 1

    before_clear = spy.enter_count
    cache.clear()
    assert spy.enter_count == before_clear + 1
    assert spy.enter_count == spy.exit_count


def test_filter_cache_put_ignores_non_dataframe_result():
    cache = FilterCache(max_size=2)

    cache.put("df1", [["x"]], "contains", None)  # type: ignore[arg-type]

    stats = cache.get_stats()
    assert stats["size"] == 0
    assert cache.get("df1", [["x"]], "contains") is None
