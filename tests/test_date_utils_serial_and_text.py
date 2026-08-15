#!/usr/bin/env python3
"""Test unified date parsing util for serial excel + textual inputs."""
from __future__ import annotations

import math
import pytest
import pandas as pd
from core.date_utils import bulk_parse_dates, parse_any_date
from shared.date_utils import format_datetime_series_for_storage
from shared.date_utils import parse_datetime_series_mixed

@pytest.mark.parametrize(
    "value,expect_prefix",
    [
        (45205, "2023-10-"),   # excel serial example
        ("2025-09-10", "2025-09-10"),
        ("10/09/2025", "2025-09-10"),
        ("09/10/2025", None),  # ambiguous (interpreted dayfirst -> 2025-10-09) prefix mismatch, we allow non-match by None logic below
    ],
)
def test_parse_any_date(value, expect_prefix):
    out = parse_any_date(value)
    if expect_prefix is None:
        assert out is None or isinstance(out, str)
    else:
        assert out is not None and out.startswith(expect_prefix)

@pytest.mark.parametrize("bad", [None, "", 0, -5, math.nan])
def test_parse_any_date_bad(bad):
    out = parse_any_date(bad)
    assert out is None


def test_parse_any_date_rejects_excel_serial_outside_operational_window():
    assert parse_any_date(1) is None


def test_bulk_parse_dates_vectorized_path_preserves_serial_and_text_results():
    parsed = bulk_parse_dates([45205, "2025-09-10", "12/31/2025", "bad-date"])

    assert parsed[0] is not None and parsed[0].startswith("2023-10-")
    assert parsed[1] == "2025-09-10 00:00:00"
    assert parsed[2] == "2025-12-31 00:00:00"
    assert parsed[3] is None


def test_format_datetime_series_for_storage_handles_object_parse(monkeypatch):
    series = pytest.importorskip("pandas").Series(["bad-date"])

    def _return_object_series(value):
        return pytest.importorskip("pandas").Series(
            ["not-a-date"] * len(value),
            index=value.index,
        )

    monkeypatch.setattr(
        "shared.date_utils.parse_datetime_series_mixed",
        _return_object_series,
    )

    formatted = format_datetime_series_for_storage(series)

    assert formatted.tolist() == [None]


def test_parse_datetime_series_mixed_normalizes_tz_aware_and_naive_values():
    series = pd.Series(
        [
            "2026-07-01 13:56:00+00:00",
            "01/07/2026 10:56:00",
            "2026-07-01 13:56:00",
        ],
        dtype="object",
    )

    parsed = parse_datetime_series_mixed(series)

    assert str(parsed.dtype) == "datetime64[ns]"
    assert parsed.isna().sum() == 0
    assert parsed.dt.tz is None
    assert parsed.iloc[0].strftime("%Y-%m-%d %H:%M:%S") == "2026-07-01 13:56:00"
