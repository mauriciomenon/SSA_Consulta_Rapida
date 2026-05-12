import pandas as pd

from core.app_logic import filter_dataframe
from interface.cli import _apply_default_filters


def make_df():
    return pd.DataFrame(
        {
            "col1": ["alpha", "prefixX", "endY", "exact", "mixed"],
            "col2": ["BETA", "noise", "tailY", "EXACT", "something pre and post"],
        }
    )


def test_default_mode_contains():
    df = make_df()
    settings = {
        "default_filters": ["pha"],  # should match 'alpha'
        "user_preferences": {"filter_mode_default": "contains"},
    }
    out = _apply_default_filters(df, settings)
    assert not out.empty
    assert "alpha" in out["col1"].tolist()


def test_default_mode_prefix():
    df = make_df()
    settings = {
        "default_filters": [
            "pre"
        ],  # should match 'prefixX' and row with 'something pre and post'
        "user_preferences": {"filter_mode_default": "prefix"},
    }
    out = _apply_default_filters(df, settings)
    # Only 'prefixX' should match as prefix across text columns
    assert "prefixX" in out["col1"].tolist()
    # Ensure 'alpha' (non-prefix) is excluded
    assert "alpha" not in out["col1"].tolist()


def test_default_mode_suffix():
    df = make_df()
    settings = {
        "default_filters": ["Y"],  # should match rows ending with Y (endY or tailY)
        "user_preferences": {"filter_mode_default": "suffix"},
    }
    out = _apply_default_filters(df, settings)
    # Either col1 == endY or col2 == tailY should select those rows
    assert any(val == "endY" for val in out["col1"].tolist()) or any(
        val == "tailY" for val in out["col2"].tolist()
    )


def test_default_mode_exact_case_insensitive():
    df = make_df()
    settings = {
        "default_filters": [
            "EXACT"
        ],  # exact mode ignores case; should match row where col1 == 'exact' or col2 == 'EXACT'
        "user_preferences": {"filter_mode_default": "exact"},
    }
    out = _apply_default_filters(df, settings)
    # The row with exact/EXACT should be present
    assert "exact" in out["col1"].tolist()


def test_default_mode_regex():
    df = make_df()
    settings = {
        "default_filters": ["^pre.*X$"],  # regex should match 'prefixX'
        "user_preferences": {"filter_mode_default": "regex"},
    }
    out = _apply_default_filters(df, settings)
    assert "prefixX" in out["col1"].tolist()


def test_explicit_regex_with_field_anchors_matches_single_column():
    df = make_df()
    out = filter_dataframe(df, ["~^pre.*X$"])
    assert out["col1"].tolist() == ["prefixX"]


def test_marker_overrides_default_mode_negative_suffix():
    df = make_df()
    # Start from a contains default but pass a negative suffix marker to exclude rows ending with Y
    settings = {
        "default_filters": ["!$Y"],
        "user_preferences": {"filter_mode_default": "contains"},
    }
    out = _apply_default_filters(df, settings)
    # Ensure rows with 'endY' or 'tailY' are excluded
    assert "endY" not in out["col1"].tolist()
    assert "tailY" not in out["col2"].tolist()
