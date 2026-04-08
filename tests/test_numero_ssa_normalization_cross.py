#!/usr/bin/env python3
"""Regression test ensuring unified numero_ssa normalization across layers.

Covers equivalence between:
  * core.numero_ssa.normalize_strict
  * utils.robust_importer path cleaning
  * armazenamento.database._normalize_numero_ssa_value (legacy) when value is already valid
  * armazenamento.database.normalize_numero_ssa_dataframe_storage (text storage path)

Edge cases: valid, invalid length, wrong year, extra chars, longer strings.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from armazenamento import database
from core.numero_ssa import normalize_relation_id, normalize_strict
from utils.robust_importer import _clean_numero_ssa_series

CASES = [
    ("202512345", "202512345"),  # valid
    (202512345, "202512345"),  # int form
    ("2025-12345", "202512345"),  # dash accepted (different trailing digits)
    ("2025-22222", None),  # dash + identical trailing digits => invalid now
    ("202599999", "202599999"),  # upper boundary year accepted
    ("197912345", None),  # year too low
    ("205112345", None),  # year too high
    ("20251234", None),  # 8 digits
    ("202600654", "202600654"),  # 9-digit numeric case from current export pattern
    ("XX202512345YY", None),  # contains letters -> invalid
]


@pytest.mark.parametrize("raw,expected", CASES)
def test_cross_layer_normalization(raw, expected):
    # Core strict
    assert normalize_strict(raw) == expected
    # Importer cleaning
    series, mask = _clean_numero_ssa_series(pd.Series([raw]))
    got = series.iloc[0] if mask.iloc[0] else None
    assert got == expected
    # Internal numeric legacy helper should still mirror the canonical value.
    legacy = database._normalize_numero_ssa_value(raw)
    if expected is None:
        assert legacy is None
    else:
        assert str(legacy).zfill(9) == expected

    frame = database.normalize_numero_ssa_dataframe_storage(
        pd.DataFrame({"numero_ssa": [raw]})
    )
    assert frame.iloc[0]["numero_ssa"] == expected


def test_cross_layer_overlong_value_is_rejected_with_log(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert normalize_strict("2025123456") is None
    assert database._normalize_numero_ssa_value("2025123456") is None

    assert "exceder 9 digitos" in caplog.text


def test_cross_layer_too_short_value_is_rejected_with_log(caplog) -> None:
    caplog.set_level(logging.WARNING)

    series, mask = _clean_numero_ssa_series(pd.Series(["123"]))

    assert normalize_strict("123") is None
    assert database._normalize_numero_ssa_value("123") is None
    assert database.normalize_numero_ssa("123") is None
    assert bool(mask.iloc[0]) is False
    assert pd.isna(series.iloc[0])
    assert "menos de 5 digitos" in caplog.text


def test_relation_normalization_rejects_text_and_decimal_artifacts() -> None:
    assert normalize_relation_id("100") == "100"
    assert normalize_relation_id("2025-12345") is None
    assert normalize_relation_id("2025-22222") is None
    assert normalize_relation_id("SSA-101") is None
    assert normalize_relation_id("ABC123") is None
    assert normalize_relation_id("ID 2026") is None
    assert normalize_relation_id("ssa 77") is None
    assert normalize_relation_id("121911787.0") is None
