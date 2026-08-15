"""Lazy SSA series lookup for details rendering."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pandas as pd

DETAILS_SERIES_INDEX_CACHE_MAX_ENTRIES = 128


class DetailsSeriesIndex(Mapping[str, pd.Series]):
    def __init__(self, df: pd.DataFrame, row_positions: Mapping[str, int]) -> None:
        self._df = df
        self._row_positions = dict(row_positions)
        self._series_cache: dict[str, pd.Series] = {}

    def __getitem__(self, key: str) -> pd.Series:
        cached = self._series_cache.get(key)
        if cached is not None:
            return cached
        series = self._df.iloc[self._row_positions[key]]
        if len(self._series_cache) >= DETAILS_SERIES_INDEX_CACHE_MAX_ENTRIES:
            self._series_cache.pop(next(iter(self._series_cache)))
        self._series_cache[key] = series
        return series

    def __iter__(self) -> Iterator[str]:
        return iter(self._row_positions)

    def __len__(self) -> int:
        return len(self._row_positions)

    def get(self, key: str, default: Any = None) -> pd.Series | Any:
        position = self._row_positions.get(key)
        if position is None:
            return default
        return self[key]

    def get_position(self, key: str) -> int | None:
        return self._row_positions.get(key)
