from __future__ import annotations

import pandas as pd

from armazenamento.database_upsert_logic import prepare_dataframe_for_upsert


def test_prepare_dataframe_for_upsert_normalizes_and_preserves_input() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": ["202500777.0"],
            "derivada_de": ["202500123.0"],
            "data_cadastro": ["01/01/2025"],
        }
    )

    out = prepare_dataframe_for_upsert(original)

    assert original.loc[0, "numero_ssa"] == "202500777.0"
    assert original.loc[0, "derivada_de"] == "202500123.0"
    assert out.loc[0, "numero_ssa"] == "202500777"
    assert out.loc[0, "derivada_de"] == "202500123"
    assert out.loc[0, "data_cadastro"] == "2025-01-01 00:00:00"
