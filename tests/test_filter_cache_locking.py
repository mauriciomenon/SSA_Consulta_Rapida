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
    cache.put("df1", [["x"]], "contains", df)
    assert spy.enter_count >= 1

    hit = cache.get("df1", [["x"]], "contains")
    assert isinstance(hit, pd.DataFrame)

    stats = cache.get_stats()
    assert stats["hits"] >= 1

    cache.clear()
    assert spy.enter_count == spy.exit_count

