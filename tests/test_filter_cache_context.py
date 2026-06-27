from __future__ import annotations

from gui.ssa.filter_cache_context import (
    build_filter_cache_context,
    build_filter_cache_parts,
)


class _OpaqueFilterValue:
    pass


def test_filter_cache_context_includes_empty_active_advanced_state():
    inactive = build_filter_cache_context(
        {},
        {},
        advanced_filters_active=False,
        exclude_terminal_statuses=False,
    )
    active_empty = build_filter_cache_context(
        {},
        {},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )

    assert inactive == ""
    assert active_empty.startswith("sha256:")


def test_stable_advanced_payload_is_deterministic_for_sets_and_objects():
    first = build_filter_cache_parts(
        {},
        {"values": {"B", "A"}, "opaque": _OpaqueFilterValue()},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )
    second = build_filter_cache_parts(
        {},
        {"opaque": _OpaqueFilterValue(), "values": {"A", "B"}},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )

    assert first.advanced_payload == second.advanced_payload
    assert "0x" not in first.advanced_payload
