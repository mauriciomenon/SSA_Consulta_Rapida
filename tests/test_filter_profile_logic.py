from __future__ import annotations

from gui.ssa.filter_profile_logic import filter_profile_is_custom


def test_filter_profile_is_custom_detects_changed_column_value() -> None:
    assert filter_profile_is_custom(
        current_filter_profile="p1",
        filter_profiles={"p1": {}},
        profile_base_filters={"columns": {"situacao": "AAT"}},
        active_column_filters={"situacao": "ASE"},
        column_to_or_group={},
        column_or_groups=[],
        exclude_ste_sca=False,
    )


def test_filter_profile_is_custom_accepts_matching_or_group() -> None:
    group = {
        "columns": ("setor_executor", "setor_emissor"),
        "values": ("IEE1", "IEE2"),
    }

    assert not filter_profile_is_custom(
        current_filter_profile="p1",
        filter_profiles={"p1": {}},
        profile_base_filters={
            "columns": {
                "setor_executor": "IEE1, IEE2",
                "setor_emissor": "IEE1, IEE2",
            },
            "or_groups": [group],
        },
        active_column_filters={
            "setor_executor": "IEE1, IEE2",
            "setor_emissor": "IEE1, IEE2",
        },
        column_to_or_group={
            "setor_executor": group,
            "setor_emissor": group,
        },
        column_or_groups=[group],
        exclude_ste_sca=False,
    )


def test_filter_profile_is_custom_detects_extra_filter() -> None:
    assert filter_profile_is_custom(
        current_filter_profile="p1",
        filter_profiles={"p1": {}},
        profile_base_filters={"columns": {"situacao": "AAT"}},
        active_column_filters={"situacao": "AAT", "setor_executor": "IEE1"},
        column_to_or_group={},
        column_or_groups=[],
        exclude_ste_sca=False,
    )


def test_filter_profile_is_custom_detects_missing_profile_definition() -> None:
    assert filter_profile_is_custom(
        current_filter_profile="missing",
        filter_profiles={},
        profile_base_filters={},
        active_column_filters={},
        column_to_or_group={},
        column_or_groups=[],
        exclude_ste_sca=False,
    )
