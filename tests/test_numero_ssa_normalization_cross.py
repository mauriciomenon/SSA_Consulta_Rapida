#!/usr/bin/env python3
"""Regression test ensuring unified numero_ssa normalization across layers.

Covers equivalence between:
  * core.numero_ssa.normalize_strict
  * utils.robust_importer path cleaning
  * armazenamento.database._normalize_numero_ssa_value (legacy) when value is already valid

Edge cases: valid, invalid length, wrong year, extra chars, longer strings.
"""
from __future__ import annotations

import pandas as pd
import pytest

from core.numero_ssa import normalize_strict
from utils.robust_importer import _clean_numero_ssa_series
from armazenamento import database

CASES = [
    ("202512345", "202512345"),   # valid
    (202512345, "202512345"),      # int form
    ("2025-12345", "202512345"),  # dash accepted (different trailing digits)
    ("2025-22222", None),          # dash + identical trailing digits => invalid now
    ("202599999", "202599999"),    # upper boundary year accepted
    ("197912345", None),          # year too low
    ("205112345", None),          # year too high
    ("20251234", None),           # 8 digits
    ("2025123456", None),         # 10 digits -> reject
    ("XX202512345YY", None),      # contains letters -> invalid
]

@pytest.mark.parametrize("raw,expected", CASES)
def test_cross_layer_normalization(raw, expected):
    # Core strict
    assert normalize_strict(raw) == expected
    # Importer cleaning
    series, mask = _clean_numero_ssa_series(pd.Series([raw]))
    got = series.iloc[0] if mask.iloc[0] else None
    assert got == expected
    # Legacy int normalizer should match when expected not None
    legacy = database._normalize_numero_ssa_value(raw)
    if expected is None:
        assert legacy is None or str(legacy).zfill(9) != expected
    else:
        assert str(legacy).zfill(9) == expected
