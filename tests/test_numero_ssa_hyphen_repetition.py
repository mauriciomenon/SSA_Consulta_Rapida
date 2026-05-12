"""Explicit test for numero_ssa hyphen + repeated trailing digits rule.

Covers the business rule introduced in `core.numero_ssa.normalize_strict`:
  * Accept values like 2025-12345 (dash with non-identical trailing digits)
  * Reject values like 2025-22222 (dash with all 5 trailing digits identical)

Also validates the importer path to ensure the cleaning layer applies the
same logic (no divergence between core and importer).
"""

from __future__ import annotations

import pandas as pd

from core.numero_ssa import normalize_strict
from utils.robust_importer import _clean_numero_ssa_series, import_excel_robust


def test_direct_normalize_strict_hyphen_cases():
    assert normalize_strict("2025-12345") == "202512345"
    assert normalize_strict("2025-22222") is None


def test_series_cleaner_hyphen_cases():
    series, mask = _clean_numero_ssa_series(pd.Series(["2025-12345", "2025-22222"]))
    assert series.iloc[0] == "202512345" and mask.iloc[0]
    assert series.iloc[1] is pd.NA or series.iloc[1] is None or not mask.iloc[1]


def test_importer_rejects_repetition(tmp_path):
    df = pd.DataFrame({"Nº SSA": ["2025-12345", "2025-22222"], "Situação": ["A", "B"]})
    file_path = tmp_path / "case.xlsx"
    df.to_excel(file_path, index=False)
    out_df, stats = import_excel_robust(str(file_path))
    # Only the non-repetition value should remain
    assert set(out_df["numero_ssa"].dropna().tolist()) == {"202512345"}
    # invalid rows count should be at least 1 (the repetition). Accept >=1 because blank filters may also count.
    assert stats.get("invalid_numero_ssa_rows", 0) >= 1
