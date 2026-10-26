"""Regressoes do contrato original da busca com re."""

import pandas as pd
import pytest

import shared  # noqa: F401  (BL-42: politica de armazenamento de str)
from core.regex_safety import is_safe_regex_pattern, safe_regex_contains
from core.search_filter import filter_dataframe, parse_search_terms

# BL-42: idiomas exigidos pelo dono: pt, es, en e acentos de de, fr, it (escapes mantem o arquivo ASCII).
PALAVRAS_ACENTUADAS = [
    "a\u00e7\u00e3o", "ni\u00f1o", "stra\u00dfe", "gar\u00e7on", "\u00e9l\u00e8ve", "citt\u00e0", "\u00fcber",
]
CASOS_UNICODE = [
    (r"^\w+$", "a\u0301", False),
    (r"\ba\b", "a\u0301", True),
    (r"^A\u00c7\u00c3O$", "a\u00e7\u00e3o", True),
    (r"\bman\w+o\b", "a manuten\u00e7\u00e3o foi", True),
    *[(r"^\w+$", palavra, True) for palavra in PALAVRAS_ACENTUADAS],
]


def test_dtype_str_padrao_usa_armazenamento_python():
    """Com ou sem pyarrow instalado, a busca roda no re do Python."""
    assert pd.get_option("mode.string_storage") == "python"
    dtype = pd.Series(["a\u00e7\u00e3o"]).dtype
    assert isinstance(dtype, pd.StringDtype) and dtype.storage == "python"


@pytest.mark.parametrize("dtype", ["object", pd.StringDtype(storage="python")])
@pytest.mark.parametrize(("padrao", "texto", "esperado"), CASOS_UNICODE)
def test_unicode_preserva_contrato_re_e_tipo_da_mascara(dtype, padrao, texto, esperado):
    serie = pd.Series([texto, None], index=[4, 4], name="texto", dtype=dtype)
    mascara = safe_regex_contains(serie, padrao)
    esperada = pd.Series(
        [esperado, False], index=serie.index, name=serie.name,
        dtype="boolean" if isinstance(dtype, pd.StringDtype) else bool,
    )
    pd.testing.assert_series_equal(mascara, esperada)


@pytest.mark.parametrize("negado", [False, True])
@pytest.mark.parametrize(("padrao", "texto", "esperado"), CASOS_UNICODE)
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


@pytest.mark.parametrize("padrao", [r"a*a*a*a*b", r"\w+\s+\w+\s+\w+\s+x", r"a{2,}b{1,}c+d*"])
def test_guarda_recusa_mais_de_tres_quantificadores_sem_limite(padrao):
    """MEM-22: 'a*a*a*a*a*a*b' passava e travava o worker (backtracking de grau alto)."""
    assert is_safe_regex_pattern(padrao) is False


@pytest.mark.parametrize("padrao", [r"bomba.*falha", r"a+b*c{2,}", r"[+-]?\d+,\d+", r"a{2,5}b{1,3}c+d*e?"])
def test_guarda_aceita_ate_tres_quantificadores_sem_limite(padrao):
    assert is_safe_regex_pattern(padrao) is True


def test_ponto_estrela_inicial_nao_muda_o_resultado():
    serie = pd.Series(["bomba com falha", "bomba ok", None, "linha 1\nbomba falha"], name="d")
    for padrao in (r".*bomba.*falha", r".*?bomba.*falha", r".*.*bomba.*falha"):
        assert safe_regex_contains(serie, padrao).tolist() == [True, False, False, True], padrao
    assert safe_regex_contains(serie, ".*").tolist() == [True, True, True, True]

