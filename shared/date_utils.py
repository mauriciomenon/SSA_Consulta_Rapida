"""Common date parsing utilities (serial Excel + textual) with neutral timezone.

Goals:
  * Single place for all parsing heuristics.
  * Excel serial numbers (epoch 1899-12-30) accepted when >= 1.
  * Support ISO first, then day-first fallback, then month-first.
  * Always return string in format 'YYYY-MM-DD HH:MM:SS' or None.
  * No timezone localization: treat naive datetimes as UTC-like neutral.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable
import pandas as pd
from datetime import timedelta
import re

__all__ = ["parse_any_date", "bulk_parse_dates", "parse_datetime_series_mixed"]

EXCEL_EPOCH = "1899-12-30"

_ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")

def parse_any_date(value) -> str | None:
    if value is None:
        return None
    # Fast path for pandas NaT-like
    try:
        import math
        if isinstance(value, float) and math.isnan(value):  # noqa: PLR2004
            return None
    except Exception:  # pragma: no cover
        pass
    # Numeric (Excel serial) detection
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Excel serial: pandas 3.0+ had intermittent issues with unit="d" metadata on some builds.
        # Implement manual epoch arithmetic for robustness.
        if value <= 0:
            return None
        try:
            base = datetime.fromisoformat(EXCEL_EPOCH)
            # Tolerate floats (fractional days) but round down to seconds.
            seconds = int(float(value) * 86400)
            dt = base + timedelta(seconds=seconds)
            # Sanity clamp: years wildly outside expected operational window (1980..2100) -> reject
            if not (1980 <= dt.year <= 2100):  # noqa: PLR2004
                return None
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:  # pragma: no cover
            return None
    text = str(value).strip()
    if not text:
        return None
    # Strategy order
    strategies = []
    if _ISO_PREFIX.match(text):
        strategies.append(dict(dayfirst=False))
    strategies.append(dict(dayfirst=True))
    strategies.append(dict(dayfirst=False))
    for opts in strategies:
        dt = pd.to_datetime(text, errors="coerce", **opts)
        if not pd.isna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    return None

def bulk_parse_dates(values: Iterable) -> list[str | None]:
    return [parse_any_date(v) for v in values]


def parse_datetime_series_mixed(series: pd.Series) -> pd.Series:
    """Parse series with mixed ISO and day-first strings without warning noise."""
    if not isinstance(series, pd.Series):
        return pd.to_datetime(series, errors="coerce", dayfirst=True)
    text_series = series.astype(str).str.strip()
    iso_mask = text_series.str.match(
        r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$",
        na=False,
    )
    ts_local = pd.to_datetime(series.where(~iso_mask), errors="coerce", dayfirst=True)
    if bool(iso_mask.any()):
        ts_iso = pd.to_datetime(series.where(iso_mask), errors="coerce", dayfirst=False)
        return ts_local.where(~iso_mask, ts_iso)
    return ts_local
