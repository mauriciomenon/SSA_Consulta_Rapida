from __future__ import annotations

from core.config_update import resolve_default_filters_change


def test_regex_default_mode_allows_literal_search_markers():
    result = resolve_default_filters_change(
        "=C++, ^pre+, suffix$",
        effective_filter_mode="regex",
    )

    assert result["changed_default_filters"] is True
    assert result["new_default_filters"] == ["=C++", "^pre+", "suffix$"]
    assert result["unsafe_filters"] == []
