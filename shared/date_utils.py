"""Common date parsing utilities (serial Excel + textual) with neutral timezone.

Goals:
  * Single place for all parsing heuristics.
  * Excel serial numbers (epoch 1899-12-30) accepted when >= 1.
  * Support ISO first, then day-first fallback, then month-first.
  * Always return string in format 'YYYY-MM-DD HH:MM:SS' or None.
  * No timezone localization: treat naive datetimes as UTC-like neutral.
"""

from __future__ import annotations

import math
import numbers
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

import pandas as pd

__all__ = [
    "parse_any_date",
    "bulk_parse_dates",
    "parse_datetime_series_mixed",
    "format_datetime_series_for_storage",
    "format_current_timestamp",
]

EXCEL_EPOCH = "1899-12-30"
MIN_OPERATIONAL_YEAR = 1980
MAX_OPERATIONAL_YEAR = 2100

_ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")


def format_current_timestamp(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return the current neutral UTC timestamp with the shared date format policy."""
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime(fmt)


def parse_any_date(value) -> str | None:
    """Parse a scalar date.

    Excel serial values outside MIN_OPERATIONAL_YEAR..MAX_OPERATIONAL_YEAR are
    rejected to avoid converting identifiers or counters into dates.
    """
    if value is None:
        return None
    # Fast path for pandas NaT-like
    if isinstance(value, float) and math.isnan(value):  # noqa: PLR2004
        return None
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
            if not (MIN_OPERATIONAL_YEAR <= dt.year <= MAX_OPERATIONAL_YEAR):
                return None
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:  # pragma: no cover
            return None
    text = str(value).strip()
    if not text:
        return None
    # Strategy order
    strategies: list[bool] = []
    if _ISO_PREFIX.match(text):
        strategies.append(False)
    strategies.append(True)
    strategies.append(False)
    for dayfirst in strategies:
        dt = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    return None


def bulk_parse_dates(values: Iterable) -> list[str | None]:
    """Parse values (text or Excel serial) to storage strings or None."""
    return format_datetime_series_for_storage(pd.Series(values, dtype="object")).tolist()


def _is_excel_serial(value) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def parse_datetime_series_mixed(series: pd.Series) -> pd.Series:
    """Parse ISO strings, day-first strings and Excel serials into naive datetimes.

    Text rows are parsed one by one (format="mixed"), so the format of one row
    never decides the day/month order of another. Month-first is used only when
    the second slash field is > 12. Numeric values are Excel serials, kept only
    inside MIN_OPERATIONAL_YEAR..MAX_OPERATIONAL_YEAR.
    """
    if not isinstance(series, pd.Series):
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=True, utc=True)
        if hasattr(parsed, "tz_localize"):
            return parsed.tz_localize(None)
        return parsed
    numeric_mask = series.map(_is_excel_serial).astype(bool)
    text_series = series.astype(str).str.strip()
    iso_mask = text_series.str.match(
        r"^\d{4}-\d{2}-\d{2}"
        r"(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?"
        r"(?:Z|[+-]\d{2}:\d{2})?$",
        na=False,
    )
    slash_parts = text_series.str.extract(r"^(\d{1,2})/(\d{1,2})/\d{4}")
    slash_second = pd.to_numeric(slash_parts[1], errors="coerce")
    forced_month_first_mask = slash_second > 12
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    local_mask = ~iso_mask & ~forced_month_first_mask & ~numeric_mask
    if bool(local_mask.any()):
        parsed.loc[local_mask] = pd.to_datetime(
            series.loc[local_mask],
            errors="coerce",
            dayfirst=True,
            utc=True,
            format="mixed",
        ).dt.tz_localize(None)
    if bool(numeric_mask.any()):
        numeric_values = pd.to_numeric(series.loc[numeric_mask], errors="coerce")
        numeric_values = numeric_values[numeric_values > 0]
        serial = pd.to_datetime(
            numeric_values, errors="coerce", unit="D", origin=EXCEL_EPOCH
        )
        in_window = serial.dt.year.between(MIN_OPERATIONAL_YEAR, MAX_OPERATIONAL_YEAR)
        parsed.loc[serial.index[in_window]] = serial[in_window]
    if bool(forced_month_first_mask.any()):
        parsed.loc[forced_month_first_mask] = pd.to_datetime(
            series.loc[forced_month_first_mask],
            errors="coerce",
            dayfirst=False,
            utc=True,
        ).dt.tz_localize(None)
    if bool(iso_mask.any()):
        parsed.loc[iso_mask] = pd.to_datetime(
            series.loc[iso_mask],
            errors="coerce",
            dayfirst=False,
            utc=True,
            format="ISO8601",
        ).dt.tz_localize(None)
    return parsed


def format_datetime_series_for_storage(series: pd.Series) -> pd.Series:
    """Return storage-formatted datetime strings or None values."""
    parsed = pd.to_datetime(parse_datetime_series_mixed(series), errors="coerce")
    if not isinstance(parsed, pd.Series):
        parsed = pd.Series(parsed, index=getattr(series, "index", None))
    formatted = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").astype("object")
    return formatted.where(parsed.notna(), None)
