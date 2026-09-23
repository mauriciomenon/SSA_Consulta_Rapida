from __future__ import annotations

import pandas as pd
import pytest

import core.search_filter as search_filter
from core.app_logic import filter_dataframe, parse_search_terms
from core.search_filter_constants import (
    FILTER_SOURCE_REVISION_ATTR,
    FILTER_SOURCE_TOKEN_ATTR,
)


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


def test_normalized_search_cache_reuses_stable_source_across_shallow_copies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataframe = _sample_dataframe()
    dataframe.attrs[FILTER_SOURCE_REVISION_ATTR] = ("load-1", 1)
    dataframe.attrs[FILTER_SOURCE_TOKEN_ATTR] = "source-1"
    search_filter._NORMALIZED_SEARCH_CACHE.clear()
    original = search_filter._build_normalized_columns
    calls = 0

    def _counted_build(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(search_filter, "_build_normalized_columns", _counted_build)

    first = filter_dataframe(dataframe.copy(deep=False), ["sistema"])
    second = filter_dataframe(dataframe.copy(deep=False), ["sistema"])

    assert _ssa_numbers(first) == EXPECTED_SYSTEM_SSAS
    assert _ssa_numbers(second) == EXPECTED_SYSTEM_SSAS
    assert calls == 1


def test_grouped_search_uses_positions_with_duplicate_index() -> None:
    dataframe = pd.DataFrame(
        {
            "descricao_servico": ["Sistema web", "Calibracao", "Compras"],
            "numero_ssa": ["1001", "1002", "1003"],
        },
        index=[7, 7, 8],
    )
    terms = [
        {"value": "sistema", "mode": "contains", "negative": False, "group": 1},
        {"value": "compras", "mode": "contains", "negative": False, "group": 2},
    ]

    result = filter_dataframe(
        dataframe,
        terms,
        search_columns=["descricao_servico"],
    )

    assert _ssa_numbers(result) == ["1001", "1003"]
