"""Contract tests for advanced filter domain rules and visual column mapping."""

from __future__ import annotations

import pandas as pd

from gui.ssa import gui_filters_advanced_state_reader as adv_state_reader
from gui.ssa.filter_domain_rules import ADVANCED_FILTER_VISUAL_COLUMN_MAP
from gui.ssa.gui_filters_advanced_logic import _apply_advanced_filters
from gui.ssa.gui_filters_advanced_ui import (
    ADVANCED_RESPONSAVEL_MULTISELECT_SPECS,
    ADVANCED_STANDARD_MULTISELECT_SPECS,
    ADVANCED_YEAR_MULTISELECT_SPECS,
)
from tests._helpers.contract_data_builders import build_advanced_filter_contract_df


class _DummyWindow:
    def __init__(self, filters: dict):
        self._advanced_filters = filters


class _DummyCombo:
    def currentData(self):
        return None


def _normalize_ssa_series(series: pd.Series) -> pd.Series:
    return series.astype(str)


def _state_reader_collect_keys() -> set[str]:
    reader = adv_state_reader.AdvancedFilterStateReader(
        widget_context={"adv_macro_combo": _DummyCombo()},
        current_filters={},
        responsavel_state=type(
            "State",
            (),
            {"is_materialized": lambda _self, _prefix: True},
        )(),
        parse_week=lambda raw: int(raw) if raw else None,
    )
    return set(reader.collect())


def test_execution_year_filters_map_to_semana_executada_visually():
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["ano_execucao"] == ("semana_executada",)
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["ano_execucao_values"] == (
        "semana_executada",
    )
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["semana_execucao_inicio"] == (
        "semana_executada",
    )
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["semana_execucao_fim"] == (
        "semana_executada",
    )


def test_ano_execucao_values_filter_uses_semana_executada_column():
    window = _DummyWindow({"ano_execucao_values": [2025]})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "semana_executada": [202501, 202452, 202503],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )

    assert filtered["numero_ssa"].tolist() == ["202500001", "202500003"]


def test_semana_execucao_range_filter_uses_semana_executada():
    window = _DummyWindow({"semana_execucao_inicio": 202502})
    df = build_advanced_filter_contract_df()

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )

    assert set(filtered["numero_ssa"].astype(int).tolist()) == {
        202600002,
        202600003,
        202600004,
    }


def test_df_completo_options_include_execucao_years_from_semana_executada():
    from gui.ssa.gui_filters_advanced_refresh import collect_advanced_filter_option_values

    df = build_advanced_filter_contract_df()
    df = df.copy()
    df.loc[:, "semana_executada"] = [202501, 202602, 202703, 202804]
    values = collect_advanced_filter_option_values(df, sort_sectors=lambda items: items)

    assert values.execucao_years == [2028, 2027, 2026, 2025]
    assert "IEE3" in values.exec_vals
    assert "APV" in values.status_vals


def test_visual_map_keys_cover_state_reader_collect_output():
    reader_keys = _state_reader_collect_keys()
    visual_keys = set(ADVANCED_FILTER_VISUAL_COLUMN_MAP)
    non_visual_keys = {
        "macro_filter",
        "num_reprogramacoes_mode",
        "derivada_has",
        "derivada_all_ste",
        "derivada_is",
    }

    assert reader_keys - visual_keys - non_visual_keys == set()

    expected_widget_keys = {"num_reprogramacoes_values"}
    for spec in ADVANCED_STANDARD_MULTISELECT_SPECS + ADVANCED_RESPONSAVEL_MULTISELECT_SPECS:
        expected_widget_keys.add(spec.include_key)
        if spec.exclude_key is not None:
            expected_widget_keys.add(spec.exclude_key)
    for spec in ADVANCED_YEAR_MULTISELECT_SPECS:
        expected_widget_keys.add(f"{spec.base_key}_values")
        expected_widget_keys.add(f"{spec.base_key}_exclude_values")

    assert expected_widget_keys - visual_keys == set()


def test_collect_advanced_options_use_full_df_not_search_subset():
    """H4: option collection reflects df_completo scope, not active search subset."""
    from gui.ssa.gui_filters_advanced_refresh import collect_advanced_filter_option_values

    df_full = build_advanced_filter_contract_df()
    df_full = df_full.copy()
    df_full.loc[3, "setor_executor"] = "ONLY_IN_COMPLETO"
    df_subset = df_full.iloc[[0]].copy()

    def sort_sectors(values):
        return values

    subset_values = collect_advanced_filter_option_values(
        df_subset, sort_sectors=sort_sectors
    )
    full_values = collect_advanced_filter_option_values(
        df_full, sort_sectors=sort_sectors
    )

    assert "ONLY_IN_COMPLETO" not in subset_values.exec_vals
    assert "ONLY_IN_COMPLETO" in full_values.exec_vals


def test_reprogramacoes_filter_values_reduce_rows():
    from gui.ssa.gui_filters_advanced_logic import _apply_reprogramacoes_filter

    df = build_advanced_filter_contract_df()
    mask = pd.Series(True, index=df.index)
    filters = {
        "num_reprogramacoes_mode": "eq",
        "num_reprogramacoes_values": [2],
    }
    result_mask = _apply_reprogramacoes_filter(df, filters, mask)
    filtered = df[result_mask]
    assert len(filtered) == 2
    assert filtered["num_reprogramacoes"].tolist() == [2, 2]


def test_reprogramacoes_summary_entries_reference_widget_keys():
    from gui.ssa.filter_summary_advanced import build_advanced_summary_entries

    entries = build_advanced_summary_entries(
        {
            "num_reprogramacoes_mode": "eq",
            "num_reprogramacoes_values": [1, 2],
        }
    )
    assert entries
    removal_keys = {
        action["keys"][0]
        for entry in entries.values()
        for action in entry.get("actions", [])
        if action.get("kind") == "advanced_keys"
    }
    assert "num_reprogramacoes_values" in removal_keys
