import warnings

import pandas as pd
import pytest

from gui.ssa import gui_filters_advanced_logic as adv_logic
from gui.ssa import gui_filters_advanced_state_reader as adv_state_reader
from gui.ssa import gui_filters_advanced_ui as adv_ui
from gui.ssa.filter_domain_rules import (
    ADVANCED_FILTER_VISUAL_COLUMN_MAP,
    build_responsavel_sector_counts_by_column,
    build_responsavel_sector_counts,
    generate_responsavel_sector_filter_cache_signature,
    order_responsavel_values,
    subset_by_sector_filters,
)
from gui.ssa.gui_filters_advanced_logic import (
    _apply_advanced_filters,
    _compute_years_from_data_cadastro,
    _mask_any,
)
from gui.ssa.gui_filters_responsavel_state import (
    ResponsavelMaterializationState,
)
from tests.gui_filters_advanced_contract_helpers import (
    extract_assigned_literal_dict,
    extract_column_group_include_exclude_keys,
    extract_detector_filter_keys,
    extract_logic_filter_keys,
    extract_produced_filter_keys,
    extract_week_exclude_keys,
    get_has_active_block,
    read_advanced_filter_sources,
)


class _DummyWindow:
    def __init__(self, filters: dict):
        self._advanced_filters = filters


class _DummyCombo:
    def currentData(self):
        return "macro_x"


class _DeletedCheckbox:
    def isChecked(self):
        raise RuntimeError("wrapped C/C++ object of type QCheckBox has been deleted")

    def property(self, _name):
        return "stale"


class _CheckedValue:
    def __init__(self, value):
        self.value = value

    def isChecked(self):
        return True

    def property(self, _name):
        return self.value


class _DummyStateReaderWindow:
    def __init__(self):
        self._advanced_filters = {
            "solicitante": ["Alice"],
            "solicitante_exclude_values": ["Bob"],
            "responsavel_programacao": ["Carol"],
            "responsavel_programacao_exclude_values": ["Dan"],
            "responsavel_execucao": ["Eve"],
            "responsavel_execucao_exclude_values": ["Frank"],
        }
        self.responsavel_materialization_state = ResponsavelMaterializationState()
        self.adv_macro_combo = _DummyCombo()

    def _get_checked_values(self, source):
        return list(source or [])

    def _parse_week(self, raw: str):
        return int(raw) if raw else None


def _normalize_ssa_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _advanced_state_reader_output_keys() -> set[str]:
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


def test_order_responsavel_values_uses_domain_sector_rank():
    df = pd.DataFrame(
        {
            "solicitante": ["Andre", "Andre", "Bruna", "Caio"],
            "setor_executor": ["IEE1", "IEE1", "MEL4", "Z999"],
            "setor_emissor": ["", "", "", ""],
        }
    )
    counts = build_responsavel_sector_counts(df, "solicitante")

    ordered = order_responsavel_values(
        ["Caio", "Bruna", "Andre"],
        counts,
        sector_to_div={"IEE1": "SMIN", "MEL4": "SMME"},
    )

    assert ordered[0] == ("Andre", "SMIN / IEE1 - Andre")
    assert ordered[1] == ("Bruna", "SMME / MEL4 - Bruna")
    assert ordered[2] == ("Caio", "Z999 - Caio")


def test_single_responsavel_counts_use_multi_column_domain_path():
    df = pd.DataFrame(
        {
            "solicitante": ["Andre", "Andre", "Bruna", "Andre"],
            "setor_executor": ["IEE1", "IEE1", "MEL4", "IEE1"],
            "setor_emissor": ["", "IEE2", "MEL4", "IEE2"],
        }
    )

    single = build_responsavel_sector_counts(df, "solicitante")
    multi = build_responsavel_sector_counts_by_column(df, ["solicitante"])

    assert single == multi["solicitante"]
    assert single["Andre"] == {"IEE1": 3, "IEE2": 2}


def test_subset_by_sector_filters_applies_include_and_exclude_once():
    df = pd.DataFrame(
        {
            "numero_ssa": ["1", "2", "3", "4"],
            "setor_executor": ["IEE1", "IEE2", "MEL4", "IEE1"],
            "setor_emissor": ["MEL4", "IEE3", "MEL4", "IEE3"],
        }
    )

    filtered = subset_by_sector_filters(
        df,
        executor_include=["IEE1", "IEE2"],
        executor_exclude=["IEE2"],
        emissor_exclude=["MEL4"],
    )

    assert filtered["numero_ssa"].tolist() == ["4"]


def test_responsavel_sector_signature_tracks_in_place_sector_mutation():
    df = pd.DataFrame(
        {
            "solicitante": ["Ana", "Bia"],
            "setor_executor": ["IEE1", "MEL4"],
            "setor_emissor": ["", ""],
        }
    )

    before = generate_responsavel_sector_filter_cache_signature(
        df,
        data_load_token=None,
        executor_include=["IEE1"],
    )
    df.loc[0, "setor_executor"] = "IEE2"
    after = generate_responsavel_sector_filter_cache_signature(
        df,
        data_load_token=None,
        executor_include=["IEE1"],
    )

    assert after != before


def test_resolve_year_selection_sets_keeps_legacy_exclude_out_of_include():
    include, exclude = adv_state_reader.resolve_year_selection_sets(
        {"ano_execucao": 2025, "ano_execucao_exclude": True},
        values_key="ano_execucao_values",
        exclude_values_key="ano_execucao_exclude_values",
        legacy_value_key="ano_execucao",
        legacy_exclude_key="ano_execucao_exclude",
    )

    assert include == set()
    assert exclude == {"2025"}


def test_state_reader_skips_deleted_qt_checkbox_wrappers():
    reader = adv_state_reader.AdvancedFilterStateReader(
        widget_context={
            "adv_derivada_checks": [
                _DeletedCheckbox(),
                _CheckedValue("has"),
            ],
            "adv_macro_combo": _DummyCombo(),
        },
        current_filters={},
        responsavel_state=type(
            "State",
            (),
            {"is_materialized": lambda _self, _prefix: False},
        )(),
        parse_week=lambda raw: int(raw) if raw else None,
    )

    data = reader.collect()

    assert data["derivada_has"] is True
    assert data["derivada_all_ste"] is False
    assert data["derivada_is"] is False


def test_advanced_filter_state_reader_preserves_unmaterialized_responsaveis():
    window = _DummyStateReaderWindow()
    reader = adv_state_reader.AdvancedFilterStateReader(
        widget_context={"adv_macro_combo": window.adv_macro_combo},
        current_filters=window._advanced_filters,
        responsavel_state=type(
            "State",
            (),
            {"is_materialized": lambda _self, _prefix: False},
        )(),
        parse_week=window._parse_week,
    )

    data = reader.collect()

    assert data["solicitante"] == ["Alice"]
    assert data["solicitante_exclude_values"] == ["Bob"]
    assert data["responsavel_programacao"] == ["Carol"]
    assert data["responsavel_programacao_exclude_values"] == ["Dan"]
    assert data["responsavel_execucao"] == ["Eve"]
    assert data["responsavel_execucao_exclude_values"] == ["Frank"]
    assert data["macro_filter"] == "macro_x"


def test_apply_advanced_filters_applies_solicitante_filter_key():
    window = _DummyWindow({"solicitante": ["Alice"]})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["Alice", "Bob"],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["solicitante"].tolist() == ["Alice"]


def test_mask_any_raises_context_instead_of_returning_false():
    class BrokenMask:
        def any(self):
            raise ValueError("mask backend failed")

    with pytest.raises(RuntimeError, match="after reprogramacoes") as excinfo:
        _mask_any(BrokenMask(), "after reprogramacoes")

    assert isinstance(excinfo.value.__cause__, ValueError)


def test_apply_advanced_filters_accepts_legacy_solicitante_key_alias():
    window = _DummyWindow({"responsavel_solicitante": ["Alice"]})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["Alice", "Bob"],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["solicitante"].tolist() == ["Alice"]


def test_has_active_advanced_filters_detects_reprogramacoes_filter():
    data = {
        "num_reprogramacoes_mode": "eq",
        "num_reprogramacoes_values": ["2"],
    }

    assert adv_ui._has_active_advanced_filters(None, data) is True


def test_derivadas_tree_keeps_first_parent_for_duplicate_child(caplog):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202600101", "202600101"],
            "derivada_de": ["202600001", "202600002"],
        }
    )
    state = adv_logic.AdvancedFilterState(_DummyWindow({}))

    mae_filhas, filha_mae = adv_logic._build_derivadas_tree_core(
        df,
        "numero_ssa",
        "derivada_de",
        state,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
    )

    assert filha_mae["202600101"] == "202600001"
    assert mae_filhas["202600001"] == ["202600101"]
    assert "202600002" not in mae_filhas
    assert "Duplicate derivada child 202600101" in caplog.text


def test_apply_advanced_filters_emissao_week_keys_filter_cadastro_week_column():
    window = _DummyWindow(
        {"semana_emissao_inicio": 202501, "semana_emissao_fim": 202502}
    )
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "semana_cadastro": [202501, 202502, 202503],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["numero_ssa"].tolist() == ["202500001", "202500002"]


def test_apply_advanced_filters_applies_priority_filter_with_grau_columns():
    window = _DummyWindow({"prioridade_emissao_values": ["2"]})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "grau_prioridade_emissao": [1, 2, 3],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["numero_ssa"].tolist() == ["202500002"]


def test_apply_advanced_filters_applies_ano_execucao_from_semana_executada():
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


def test_advanced_execution_filters_map_to_semana_executada_visually():
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["ano_execucao"] == ("semana_executada",)
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["ano_execucao_values"] == (
        "semana_executada",
    )
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["ano_execucao_exclude_values"] == (
        "semana_executada",
    )
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["semana_execucao_inicio"] == (
        "semana_executada",
    )
    assert ADVANCED_FILTER_VISUAL_COLUMN_MAP["semana_execucao_fim"] == (
        "semana_executada",
    )


def test_apply_advanced_filters_supports_legacy_ano_emissao_key():
    window = _DummyWindow({"ano_emissao": 2025})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202400001", "202500002"],
            "data_cadastro": ["01/01/2025", "01/01/2024", "15/07/2025"],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["numero_ssa"].tolist() == ["202500001", "202500002"]


def test_compute_years_from_data_cadastro_handles_mixed_iso_and_dayfirst_without_warning():
    series = pd.Series(
        [
            "2026-02-25 16:16:50",
            "25/02/2026",
            "invalid",
        ]
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        years, notice = _compute_years_from_data_cadastro(series)

    assert years.iloc[0] == 2026
    assert years.iloc[1] == 2026
    assert pd.isna(years.iloc[2])
    assert notice == "ano_emissao_parse_skipped"
    assert not any("dayfirst=True" in str(item.message) for item in caught)


def test_apply_advanced_filters_supports_legacy_ano_execucao_exclude_flag():
    window = _DummyWindow({"ano_execucao": 2025, "ano_execucao_exclude": True})
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202400001", "202500002"],
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
    assert filtered["numero_ssa"].tolist() == ["202400001"]


def test_apply_advanced_filters_reprogramacoes_eq_lte_gte():
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003", "202500004"],
            "num_reprogramacoes": [0, 1, 2, 3],
        }
    )

    window_eq = _DummyWindow(
        {"num_reprogramacoes_mode": "eq", "num_reprogramacoes_values": ["2"]}
    )
    filtered_eq = _apply_advanced_filters(
        window_eq,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered_eq["numero_ssa"].tolist() == ["202500003"]

    window_lte = _DummyWindow(
        {"num_reprogramacoes_mode": "lte", "num_reprogramacoes_values": ["1"]}
    )
    filtered_lte = _apply_advanced_filters(
        window_lte,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered_lte["numero_ssa"].tolist() == ["202500001", "202500002"]

    window_gte = _DummyWindow(
        {"num_reprogramacoes_mode": "gte", "num_reprogramacoes_values": ["2"]}
    )
    filtered_gte = _apply_advanced_filters(
        window_gte,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered_gte["numero_ssa"].tolist() == ["202500003", "202500004"]


def test_apply_advanced_filters_derivada_all_ste_accepts_terminal_states():
    window = _DummyWindow({"derivada_all_ste": True})
    df = pd.DataFrame(
        {
            "numero_ssa": ["100", "101", "102", "200", "201"],
            "derivada_de": ["", "100", "100", "", "200"],
            "situacao": ["APV", "STE", "SES", "APV", "SCA"],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["numero_ssa"].tolist() == ["100"]


def test_apply_advanced_filters_derivada_all_ste_ignores_nullable_derivada_values():
    window = _DummyWindow({"derivada_all_ste": True})
    df = pd.DataFrame(
        {
            "numero_ssa": ["100", "101", "102", "103"],
            "derivada_de": ["", "100", pd.NA, None],
            "situacao": ["APV", "STE", "STE", "SES"],
        }
    )

    filtered = _apply_advanced_filters(
        window,
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered["numero_ssa"].tolist() == ["100"]


def test_apply_advanced_filters_derives_divisao_from_setor_columns(monkeypatch):
    monkeypatch.setattr(
        adv_logic,
        "SECTOR_TO_DIV",
        {
            "IEE3": "SMIN",
            "MEL3": "SMME",
        },
    )
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "setor_executor": ["IEE3", "MEL3", ""],
            "setor_emissor": ["", "", "IEE3"],
        }
    )

    filtered_include = _apply_advanced_filters(
        _DummyWindow({"divisao": ["SMIN"]}),
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered_include["numero_ssa"].tolist() == ["202500001", "202500003"]

    filtered_exclude = _apply_advanced_filters(
        _DummyWindow({"divisao_exclude_values": ["SMIN"]}),
        df,
        cache_token=1,
        normalize_ssa_series=_normalize_ssa_series,
        notice_callback=None,
    )
    assert filtered_exclude["numero_ssa"].tolist() == ["202500002"]


def test_advanced_filter_keys_from_ui_are_covered_by_logic_or_active_detector():
    sources = read_advanced_filter_sources()

    produced_keys = (
        extract_produced_filter_keys(sources.ui) | _advanced_state_reader_output_keys()
    )
    has_active_block = get_has_active_block(sources.ui)

    uncovered = sorted(
        key
        for key in produced_keys
        if key not in sources.logic and f'data.get("{key}")' not in has_active_block
    )
    assert not uncovered, (
        f"Advanced filter keys without logic/active coverage: {', '.join(uncovered)}"
    )


def test_logic_and_detector_keys_are_produced_by_ui_or_marked_legacy():
    sources = read_advanced_filter_sources()

    produced_keys = (
        extract_produced_filter_keys(sources.ui) | _advanced_state_reader_output_keys()
    )
    has_active_block = get_has_active_block(sources.ui)
    detector_keys = extract_detector_filter_keys(has_active_block)
    direct_logic_keys = extract_logic_filter_keys(sources.logic)
    column_group_keys = extract_column_group_include_exclude_keys(sources.logic)
    alias_map = extract_assigned_literal_dict(sources.logic, "key_aliases")
    alias_keys = set(alias_map.keys()) | set(alias_map.values())

    legacy_keys = {
        "ano_emissao",
        "ano_emissao_exclude",
        "ano_execucao",
        "ano_execucao_exclude",
        "derivada_all_ste",
        "responsavel_solicitante",
        "responsavel_solicitante_exclude_values",
        "divisao",
        "divisao_exclude_values",
    }

    consumed_keys = detector_keys | direct_logic_keys | column_group_keys | alias_keys
    uncovered = sorted(
        key
        for key in consumed_keys
        if key not in produced_keys and key not in legacy_keys
    )
    assert not uncovered, (
        f"Logic/detector keys without UI producer or legacy allowlist: {', '.join(uncovered)}"
    )


def test_week_exclude_contract_keys_are_explicit_noop_allowlist_only():
    sources = read_advanced_filter_sources()
    produced_keys = (
        extract_produced_filter_keys(sources.ui) | _advanced_state_reader_output_keys()
    )
    has_active_block = get_has_active_block(sources.ui)
    detector_keys = extract_detector_filter_keys(has_active_block)

    logic_week_exclude_keys = extract_week_exclude_keys(sources.logic)
    explicit_noop_allowlist = {"semana_emissao_exclude", "semana_execucao_exclude"}

    assert logic_week_exclude_keys <= explicit_noop_allowlist
    assert not (explicit_noop_allowlist & produced_keys)
    not_in_detector = logic_week_exclude_keys - detector_keys
    assert not_in_detector <= explicit_noop_allowlist
