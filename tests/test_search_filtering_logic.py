from __future__ import annotations

import pandas as pd

from core.app_logic import filter_dataframe, parse_search_terms


EXPECTED_SYSTEM_SSAS = ["1001", "1004"]


def _sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "descricao_servico": [
                "Sistema web",
                "Manutencao preventiva",
                None,
                "Sistema ERP",
                "Calibracao",
            ],
            "setor_executor": ["TI", None, "COMPRAS", "TI", "MANUTENCAO"],
            "numero_ssa": ["1001", "1002", "1003", "1004", "1005"],
        }
    )


def _ssa_numbers(result: pd.DataFrame) -> list[str]:
    return [str(value) for value in result["numero_ssa"].tolist()]


def test_search_ignores_nan_and_matches_schema_text_columns() -> None:
    result = filter_dataframe(_sample_dataframe(), ["sistema"])

    assert _ssa_numbers(result) == EXPECTED_SYSTEM_SSAS


def test_search_does_not_match_nan_string() -> None:
    result = filter_dataframe(_sample_dataframe(), ["nan"])

    assert result.empty


def test_prefix_search_matches_schema_text_columns() -> None:
    result = filter_dataframe(_sample_dataframe(), ["^Sistema"])

    assert _ssa_numbers(result) == EXPECTED_SYSTEM_SSAS


def test_multi_term_search_matches_same_rows() -> None:
    result = filter_dataframe(_sample_dataframe(), ["sistema", "TI"])

    assert _ssa_numbers(result) == EXPECTED_SYSTEM_SSAS


def test_duplicate_parsed_terms_keep_expected_result() -> None:
    terms = parse_search_terms(["sistema", "sistema"])
    result = filter_dataframe(_sample_dataframe(), terms)

    assert _ssa_numbers(result) == EXPECTED_SYSTEM_SSAS
