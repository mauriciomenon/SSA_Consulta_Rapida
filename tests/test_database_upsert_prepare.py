from __future__ import annotations

import pandas as pd

from armazenamento.database_upsert_logic import (
    prepare_dataframe_for_upsert,
    sanitize_textual_null_sentinels,
)


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


def test_prepare_dataframe_for_upsert_handles_non_unique_index_without_corruption() -> (
    None
):
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


def test_prepare_dataframe_for_upsert_rejects_letters_in_storage_ids() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": ["XX202500777.0YY", "202500777.0"],
            "derivada_de": ["XX202500123.0YY", "XX202500123.0YY"],
            "data_cadastro": ["01/01/2025", "01/01/2025"],
        }
    )

    out = prepare_dataframe_for_upsert(original)

    assert pd.isna(out.loc[0, "numero_ssa"])
    assert out.loc[1, "numero_ssa"] == "202500777"
    assert pd.isna(out.loc[0, "derivada_de"])
    assert pd.isna(out.loc[1, "derivada_de"])


def test_prepare_dataframe_for_upsert_rejects_unicode_letters_in_storage_ids() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": [
                "XX202500777.0YY",
                "AB202500777.0",
                "A202500777",
                "A202500777",
                "2025A0777",
                "Ä202500777",
                "202500777ß",
            ],
            "derivada_de": [
                "202500123",
                "202500123",
                "202500123",
                "Ä202500123",
                "202500123",
                "202500123",
                "202500123",
            ],
            "data_cadastro": ["01/01/2025"] * 7,
        }
    )

    out = prepare_dataframe_for_upsert(original)

    for idx in range(len(out.index)):
        assert pd.isna(out.loc[idx, "numero_ssa"])
    assert out.loc[0, "derivada_de"] == "202500123"
    assert out.loc[1, "derivada_de"] == "202500123"
    assert out.loc[2, "derivada_de"] == "202500123"
    assert pd.isna(out.loc[3, "derivada_de"])
    assert out.loc[4, "derivada_de"] == "202500123"
    assert out.loc[5, "derivada_de"] == "202500123"
    assert out.loc[6, "derivada_de"] == "202500123"


def test_prepare_dataframe_for_upsert_parses_excel_serial_dates() -> None:
    original = pd.DataFrame(
        {
            "numero_ssa": ["202500901"],
            "data_cadastro": [45658],
        }
    )

    out = prepare_dataframe_for_upsert(original)

    assert out.loc[0, "data_cadastro"] == "2025-01-01 00:00:00"


def test_sanitize_textual_null_sentinels_returns_same_frame_on_noop() -> None:
    original = pd.DataFrame(
        {
            "descricao_ssa": pd.Series(["valor", "texto"], dtype="string"),
            "setor_executor": ["Equipe A", "Equipe B"],
        }
    )

    out = sanitize_textual_null_sentinels(original)

    assert out is original
    assert list(out["descricao_ssa"]) == ["valor", "texto"]
    assert list(out["setor_executor"]) == ["Equipe A", "Equipe B"]


def test_sanitize_textual_null_sentinels_handles_dash_and_empty() -> None:
    original = pd.DataFrame(
        {
            "descricao_ssa": pd.Series(["-", "", "na", " ok "], dtype="string"),
            "setor_executor": ["-", "texto", "", "na"],
        }
    )

    out = sanitize_textual_null_sentinels(original)

    assert pd.isna(out.loc[0, "descricao_ssa"])
    assert pd.isna(out.loc[1, "descricao_ssa"])
    assert out.loc[2, "descricao_ssa"] == "na"
    assert out.loc[3, "descricao_ssa"] == " ok "
    assert pd.isna(out.loc[0, "setor_executor"])
    assert out.loc[1, "setor_executor"] == "texto"
    assert pd.isna(out.loc[2, "setor_executor"])
    assert out.loc[3, "setor_executor"] == "na"
