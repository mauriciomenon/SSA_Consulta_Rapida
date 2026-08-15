from __future__ import annotations

import pandas as pd

from gui.ssa.details_normalization import normalize_ssa_relation_series


def test_normalize_ssa_relation_series_preserves_series_name() -> None:
    series = pd.Series(["202600001.0", None], name="derivada_de")

    normalized = normalize_ssa_relation_series(series)

    assert normalized.name == "derivada_de"
    assert normalized.tolist() == ["202600001", ""]
