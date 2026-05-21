from __future__ import annotations

import pytest

from gui.ssa.filter_summary_removal import build_summary_removal_plan


def test_build_summary_removal_plan_collects_mixed_actions():
    plan = build_summary_removal_plan(
        [
            {"kind": "search"},
            {"kind": "dedicated_or"},
            {"kind": "exclude_ste_sca"},
            {"kind": "column", "column": "setor_emissor"},
            {"kind": "column_or_group", "column": "setor_executor"},
            {
                "kind": "advanced_keys",
                "keys": ["macro_filter", "setor_executor"],
            },
        ]
    )

    assert plan.clear_general_search_state is True
    assert plan.refresh_needed is True
    assert plan.sync_advanced_ui is True
    assert plan.clear_dedicated_or_text is True
    assert plan.clear_exclude_terminal_statuses is True
    assert plan.columns_to_reset == ["setor_emissor", "setor_executor"]
    assert plan.removal_advanced_keys == ["macro_filter", "setor_executor"]


def test_build_summary_removal_plan_deduplicates_columns_and_keys():
    plan = build_summary_removal_plan(
        [
            {"kind": "column", "column": "setor_executor"},
            {"kind": "column", "column": "setor_executor"},
            {"kind": "advanced_keys", "keys": ["macro_filter", "macro_filter"]},
        ]
    )

    assert plan.columns_to_reset == ["setor_executor"]
    assert plan.removal_advanced_keys == ["macro_filter"]


def test_build_summary_removal_plan_refreshes_after_dedicated_or_removal():
    plan = build_summary_removal_plan([{"kind": "dedicated_or"}])

    assert plan.clear_dedicated_or_text is True
    assert plan.refresh_needed is True


def test_build_summary_removal_plan_rejects_unknown_action():
    with pytest.raises(ValueError, match="nao suportada"):
        build_summary_removal_plan([{"kind": "unexpected"}])
