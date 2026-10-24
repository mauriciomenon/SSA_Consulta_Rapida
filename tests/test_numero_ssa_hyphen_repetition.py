"""Explicit test for numero_ssa hyphen + repeated trailing digits rule.

Covers the business rule introduced in `core.numero_ssa.normalize_strict`:
  * Accept values like 2025-12345 (dash with non-identical trailing digits)
  * Reject values like 2025-22222 (dash with all 5 trailing digits identical)
"""

from __future__ import annotations

from core.numero_ssa import normalize_strict


def test_direct_normalize_strict_hyphen_cases():
    assert normalize_strict("2025-12345") == "202512345"
    assert normalize_strict("2025-22222") is None


