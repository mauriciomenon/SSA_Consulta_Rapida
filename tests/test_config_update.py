from __future__ import annotations

from core.config_update import resolve_default_filters_change


def test_regex_default_mode_allows_literal_search_marker_edges():
    raw_filters = "^, $, =, ^$, = ,  ^term, , suffix$"
    result = resolve_default_filters_change(
        raw_filters,
        effective_filter_mode="regex",
    )

    assert result["changed_default_filters"] is True
    assert result["new_default_filters"] == ["^", "$", "=", "^$", "=", "^term", "suffix$"]
    assert result["unsafe_filters"] == []


def test_default_filter_change_parses_marker_and_plain_terms_in_non_regex_modes():
    for mode in ("contains", "prefix", "suffix", "exact"):
        result = resolve_default_filters_change(
            "plain, =202600001, ^pre, suffix$, !neg, -old",
            effective_filter_mode=mode,
        )

        assert result["changed_default_filters"] is True
        assert result["new_default_filters"] == [
            "plain",
            "=202600001",
            "^pre",
            "suffix$",
            "!neg",
            "-old",
        ]
        assert result["unsafe_filters"] == []


def test_default_filter_change_blocks_forced_unsafe_regex():
    result = resolve_default_filters_change(
        "~(a+)+, safe",
        effective_filter_mode="contains",
    )

    assert result["changed_default_filters"] is False
    assert result["new_default_filters"] is None
    assert result["unsafe_filters"] == ["~(a+)+"]


def test_default_filter_change_handles_empty_and_adjacent_commas():
    result = resolve_default_filters_change(
        " , alpha,, beta, ",
        effective_filter_mode="contains",
    )

    assert result["changed_default_filters"] is True
    assert result["new_default_filters"] == ["alpha", "beta"]
    assert result["unsafe_filters"] == []
