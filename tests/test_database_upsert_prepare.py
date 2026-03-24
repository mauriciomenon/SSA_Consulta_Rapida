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


def test_prepare_dataframe_for_upsert_sanitizes_textual_null_sentinels() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": ["202500777", "202500778"],
            "descricao_ssa": ["<NA>", " None "],
            "setor_executor": [" nan ", "MEL4"],
            "solicitante": ["na", " Equipe A "],
            "responsavel_programacao": [" null ", "n/a"],
        }
    )

    out = prepare_dataframe_for_upsert(original)

    assert original.loc[0, "descricao_ssa"] == "<NA>"
    assert pd.isna(out.loc[0, "descricao_ssa"])
    assert pd.isna(out.loc[1, "descricao_ssa"])
    assert pd.isna(out.loc[0, "setor_executor"])
    assert out.loc[1, "setor_executor"] == "MEL4"
    assert out.loc[0, "solicitante"] == "na"
    assert out.loc[1, "solicitante"] == " Equipe A "
    assert pd.isna(out.loc[0, "responsavel_programacao"])
    assert pd.isna(out.loc[1, "responsavel_programacao"])


def test_prepare_dataframe_for_upsert_handles_non_unique_index_without_corruption() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": ["202500880", "202500881", "202500882"],
            "descricao_ssa": ["<NA>", "texto", " None "],
        },
        index=[0, 0, 1],
    )

    out = prepare_dataframe_for_upsert(original)

    assert list(out["numero_ssa"]) == ["202500880", "202500881", "202500882"]
    assert pd.isna(out.loc[0, "descricao_ssa"])
    assert out.loc[1, "descricao_ssa"] == "texto"
    assert pd.isna(out.loc[2, "descricao_ssa"])
