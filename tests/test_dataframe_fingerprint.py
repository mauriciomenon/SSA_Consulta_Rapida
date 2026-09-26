from __future__ import annotations

import pandas as pd
import pytest

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


def test_dataframe_filter_hash_covers_unsampled_rows() -> None:
    first = pd.DataFrame({"value": list(range(80))})
    second = first.copy()
    second.loc[30, "value"] = 9999

    assert build_dataframe_filter_hash(first) != build_dataframe_filter_hash(second)


def test_dataframe_filter_hash_includes_index_values() -> None:
    first = pd.DataFrame({"value": [1, 2]}, index=[10, 20])
    second = pd.DataFrame({"value": [1, 2]}, index=[30, 40])

    assert build_dataframe_filter_hash(first) != build_dataframe_filter_hash(second)


def test_dataframe_filter_hash_fallback_uses_content(monkeypatch) -> None:
    first = pd.DataFrame({"value": [1, 2, 3]})
    second = pd.DataFrame({"value": [1, 999, 3]})

    def fail_hash(*args, **kwargs):
        raise TypeError("forced hash failure")

    monkeypatch.setattr(pd.util, "hash_pandas_object", fail_hash)

    assert build_dataframe_filter_hash(first) != build_dataframe_filter_hash(second)


@pytest.mark.parametrize("values", [[1, 2], [[1], [2]]])
def test_dataframe_filter_hash_includes_revision(values) -> None:
    dataframe = pd.DataFrame({"value": values})
    dataframe.attrs["ssa_data_revision"] = 1
    first_hash = build_dataframe_filter_hash(dataframe)

    dataframe.attrs["ssa_data_revision"] = 2

    assert first_hash != build_dataframe_filter_hash(dataframe)
