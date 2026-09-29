from __future__ import annotations

from gui.ssa.filter_cache_context import (
    build_filter_cache_context,
    build_filter_cache_parts,
)
from gui.ssa.gui_filters_advanced_refresh import AdvancedFilterOptionValues


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


def test_advanced_filter_dataclass_values_affect_cache_context():
    first_values = AdvancedFilterOptionValues(
        exec_vals=["IEE3"],
        emis_vals=[],
        status_vals=["APV"],
        emissao_years=[2026],
        execucao_years=[],
        prio_emissao_vals=[],
        prio_planejamento_vals=[],
        reprog_vals=[1],
    )
    second_values = AdvancedFilterOptionValues(
        exec_vals=["MEL4"],
        emis_vals=[],
        status_vals=["APV"],
        emissao_years=[2026],
        execucao_years=[],
        prio_emissao_vals=[],
        prio_planejamento_vals=[],
        reprog_vals=[1],
    )

    first = build_filter_cache_parts(
        {},
        {"values": first_values},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )
    second = build_filter_cache_parts(
        {},
        {"values": second_values},
        advanced_filters_active=True,
        exclude_terminal_statuses=False,
    )

    assert "__non_json_type__" not in first.advanced_payload
    assert first.advanced_payload != second.advanced_payload
