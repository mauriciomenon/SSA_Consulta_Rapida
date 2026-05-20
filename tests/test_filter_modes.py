# ruff: noqa: E402
import os
import sys

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from core.app_logic import filter_dataframe


def _df():
    return pd.DataFrame(
        {
            "texto": [
                "Administração Geral",
                "ADMIN area",
                "Fechado em 2025",
                "aberto 2024-12",
                "cancelada por motivo X",
                "regex sample 123 abc",
            ],
            "num": [1, 2, 3, 4, 5, 6],
        }
    )


essential_contains = ["adm", "!cancelada"]


def test_contains_basic_and_negative():
    df = _df()
    out = filter_dataframe(df, essential_contains)
    assert len(out) == 2
    assert set(out["num"]) == {1, 2}


def test_prefix_and_suffix():
    df = _df()
    out_prefix = filter_dataframe(df, ["^adm"])
    assert set(out_prefix["num"]) == {1, 2}
    out_suffix = filter_dataframe(df, ["2025$"])
    assert set(out_suffix["num"]) == {3}


def test_exact_match_and_negative():
    df = _df()
    out_exact = filter_dataframe(df, ["=admin area"])
    assert set(out_exact["num"]) == {2}
    out_not_exact = filter_dataframe(df, ["!=admin area"])
    assert 2 not in set(out_not_exact["num"])


def test_regex_and_fallback():
    df = _df()
    out_regex = filter_dataframe(df, ["~\\d+ abc"])
    assert set(out_regex["num"]) == {6}
    out_fallback = filter_dataframe(df, ["~["])
    assert len(out_fallback) == 0


def test_regex_handles_duplicate_dataframe_index():
    df = _df()
    df.index = [1, 1, 2, 2, 3, 3]

    out_regex = filter_dataframe(df, ["~\\d+ abc"])
    assert set(out_regex["num"]) == {6}

    out_invalid = filter_dataframe(df, ["~["])
    assert len(out_invalid) == 0


def test_mixed_terms_and_negatives():
    df = _df()
    out = filter_dataframe(df, ["adm", "area$", "!geral"])
    assert set(out["num"]) == {2}
