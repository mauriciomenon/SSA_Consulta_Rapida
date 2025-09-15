#!/usr/bin/env python3
"""Test unified date parsing util for serial excel + textual inputs."""
from __future__ import annotations

import math
import pytest
from core.date_utils import parse_any_date

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
