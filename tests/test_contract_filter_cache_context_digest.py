"""Contract tests for filter worker cache context digests."""

from __future__ import annotations

from gui.ssa.filter_cache_context import build_filter_cache_context


def test_exclude_terminal_changes_cache_context_without_column_filters():
    """Exclude-terminal alone produces a non-empty worker cache context digest."""
    empty = build_filter_cache_context(
        {},
        {},
        advanced_filters_active=False,
        exclude_terminal_statuses=False,
    )
    terminal_only = build_filter_cache_context(
        {},
        {},
        advanced_filters_active=False,
        exclude_terminal_statuses=True,
    )
    assert empty == ""
    assert terminal_only.startswith("sha256:")
    assert terminal_only != empty


def test_terminal_and_advanced_active_produce_distinct_contexts():
    terminal_only = build_filter_cache_context(
        {},
        {"setor_executor_values": {"IEE3"}},
        advanced_filters_active=False,
        exclude_terminal_statuses=True,
    )
    advanced_only = build_filter_cache_context(
        {},
        {"setor_executor_values": {"IEE3"}},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )
    both = build_filter_cache_context(
        {},
        {"setor_executor_values": {"IEE3"}},
        advanced_filters_active=True,
        exclude_terminal_statuses=True,
    )
    assert terminal_only != advanced_only
    assert both != terminal_only
    assert both != advanced_only


def test_identical_inputs_produce_stable_digest():
    filters = {"setor_executor_values": {"IEE3", "MEL4"}}
    first = build_filter_cache_context(
        {},
        filters,
        advanced_filters_active=True,
        exclude_terminal_statuses=True,
    )
    second = build_filter_cache_context(
        {},
        filters,
        advanced_filters_active=True,
        exclude_terminal_statuses=True,
    )
    assert first == second
    assert first.startswith("sha256:")


def test_column_filter_change_produces_distinct_digest():
    baseline = build_filter_cache_context(
        {"setor_executor": "IEE3"},
        {},
        advanced_filters_active=False,
        exclude_terminal_statuses=False,
    )
    changed = build_filter_cache_context(
        {"setor_executor": "MEL4"},
        {},
        advanced_filters_active=False,
        exclude_terminal_statuses=False,
    )
    assert baseline != changed
    assert baseline.startswith("sha256:")
    assert changed.startswith("sha256:")
