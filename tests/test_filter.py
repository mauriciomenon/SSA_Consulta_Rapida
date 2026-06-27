from __future__ import annotations

import pandas as pd

from core.app_logic import filter_dataframe, parse_search_terms


def test_parse_search_terms_preserves_single_literal_token():
    terms = parse_search_terms(["svp"])

    assert terms == [
        {
            "raw": "svp",
            "mode": "contains",
            "value": "svp",
            "negative": False,
            "group": 0,
        }
    ]


def test_filter_dataframe_matches_literal_token_without_alias_expansion():
    df = pd.DataFrame({"col1": ["svp", "test", "svp test", "SP", "s/p", "sp"]})

    filtered = filter_dataframe(df, ["svp"], ["col1"])

    assert filtered["col1"].tolist() == ["svp", "svp test"]
