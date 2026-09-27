"""Regressoes do contrato original da busca com re."""

import pandas as pd
import pytest

from core.regex_safety import safe_regex_contains
from core.search_filter import filter_dataframe, parse_search_terms


@pytest.mark.parametrize("dtype", ["object", pd.StringDtype(storage="python")])
@pytest.mark.parametrize(
    ("padrao", "texto", "esperado"),
    [(r"^\w+$", "a\u0301", False), (r"^[a-z]+$", "\u0131", True), (r"\ba\b", "a\u0301", True)],
)
def test_unicode_preserva_contrato_re_e_tipo_da_mascara(dtype, padrao, texto, esperado):
    serie = pd.Series([texto, None], index=[4, 4], name="texto", dtype=dtype)
    mascara = safe_regex_contains(serie, padrao)
    esperada = pd.Series(
        [esperado, False], index=serie.index, name=serie.name,
        dtype="boolean" if isinstance(dtype, pd.StringDtype) else bool,
    )
    pd.testing.assert_series_equal(mascara, esperada)


@pytest.mark.parametrize("negado", [False, True])
@pytest.mark.parametrize(
    ("padrao", "texto", "esperado"),
    [(r"^\w+$", "a\u0301", False), (r"^[a-z]+$", "\u0131", True), (r"\ba\b", "a\u0301", True)],
)
def test_busca_integrada_preserva_unicode_e_negacao(negado, padrao, texto, esperado):
    quadro = pd.DataFrame({"descricao_ssa": [texto, "---"]}, index=[4, 8])
    termos = parse_search_terms(("!" if negado else "") + "~" + padrao)
    resultado = filter_dataframe(quadro, termos, search_columns=["descricao_ssa"])
    mascara = [not esperado, True] if negado else [esperado, False]
    pd.testing.assert_frame_equal(resultado, quadro.loc[mascara])


def test_regex_preserves_index_nulls_and_case_insensitive_matching():
    series = pd.Series(["Abc", None, "xx abc", "def"], index=[4, 4, 8, 9], name="text")
    result = safe_regex_contains(series, "^abc$")
    assert result.tolist() == [True, False, False, False]
    assert result.index.equals(series.index)
    assert result.name == series.name


def test_invalid_regex_keeps_literal_fallback_contract():
    series = pd.Series(["[abc", "other"])
    assert safe_regex_contains(series, "[abc", fallback_literal=True).tolist() == [True, False]
    assert safe_regex_contains(series, "[abc").tolist() == [False, False]
