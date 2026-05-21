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
