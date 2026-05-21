from __future__ import annotations

import pandas as pd

from core.dataframe_fingerprint import build_dataframe_filter_hash
from core.dataframe_fingerprint import sample_dataframe_for_fingerprint


def test_dataframe_filter_hash_distinguishes_column_separator_collisions() -> None:
    first = pd.DataFrame([[1, 2]], columns=["a", "b\x1fc"])
    second = pd.DataFrame([[1, 2]], columns=["a\x1fb", "c"])

    assert build_dataframe_filter_hash(first) != build_dataframe_filter_hash(second)


def test_dataframe_fingerprint_sample_covers_middle_rows_for_25_rows() -> None:
    dataframe = pd.DataFrame({"value": list(range(25))})

    sampled = sample_dataframe_for_fingerprint(dataframe)
    values = sampled["value"].tolist()

    assert values[:8] == list(range(8))
    assert values[-8:] == list(range(17, 25))
    assert sum(8 <= value <= 16 for value in values) == 8
