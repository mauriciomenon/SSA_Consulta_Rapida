import ast
import re
import warnings
from pathlib import Path

import pandas as pd

from gui.ssa import gui_filters_advanced_logic as adv_logic
from gui.ssa import gui_filters_advanced_ui as adv_ui
from gui.ssa.filter_domain_rules import (
    build_responsavel_sector_counts,
    order_responsavel_values,
    subset_by_sector_filters,
)
from gui.ssa.gui_filters_advanced_logic import (
    _apply_advanced_filters,
    _compute_years_from_data_cadastro,
)


class _DummyWindow:
    def __init__(self, filters: dict):
        self._advanced_filters = filters


def _normalize_ssa_series(series: pd.Series) -> pd.Series:
    return series.astype(str).fillna("").str.strip()


def _get_has_active_block(ui_source: str) -> str:
    has_active_block_match = re.search(
        r"def _has_active_advanced_filters\(.*?\):(?P<body>.*?)def _apply_advanced_filters_from_ui",
        ui_source,
        flags=re.S,
    )
    assert has_active_block_match is not None
    return has_active_block_match.group("body")


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


def _extract_assigned_literal_dict(source: str, variable_name: str) -> dict:
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == variable_name:
                value = ast.literal_eval(node.value)
                if isinstance(value, dict):
                    return value
    return {}


def _extract_column_group_filter_keys(source: str) -> set[str]:
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "column_groups":
                value = ast.literal_eval(node.value)
                if not isinstance(value, list):
                    return set()
                keys: set[str] = set()
                for item in value:
                    if not isinstance(item, tuple) or len(item) != 3:
                        continue
                    _, include_key, exclude_key = item
                    if isinstance(include_key, str):
                        keys.add(include_key)
                    if isinstance(exclude_key, str):
                        keys.add(exclude_key)
                return keys
    return set()


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


def test_apply_advanced_filters_applies_week_range_filter():
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


def test_apply_advanced_filters_derivada_all_ste_accepts_ses_as_terminal_state():
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
    ui_source = Path(adv_ui.__file__).read_text(encoding="utf-8")
    logic_source = Path(adv_ui.__file__.replace("_ui.py", "_logic.py")).read_text(
        encoding="utf-8"
    )

    produced_keys = set(re.findall(r'data\["([^"]+)"\]\s*=', ui_source))
    has_active_block = _get_has_active_block(ui_source)

    uncovered = sorted(
        key
        for key in produced_keys
        if key not in logic_source and f'data.get("{key}")' not in has_active_block
    )
    assert not uncovered, (
        f"Advanced filter keys without logic/active coverage: {', '.join(uncovered)}"
    )


def test_logic_and_detector_keys_are_produced_by_ui_or_marked_legacy():
    ui_source = Path(adv_ui.__file__).read_text(encoding="utf-8")
    logic_source = Path(adv_ui.__file__.replace("_ui.py", "_logic.py")).read_text(
        encoding="utf-8"
    )

    produced_keys = set(re.findall(r'data\["([^"]+)"\]\s*=', ui_source))
    has_active_block = _get_has_active_block(ui_source)
    detector_keys = set(re.findall(r'data\.get\("([^"]+)"\)', has_active_block))
    direct_logic_keys = set(re.findall(r'filters\.get\("([^"]+)"\)', logic_source))
    column_group_keys = _extract_column_group_filter_keys(logic_source)
    alias_map = _extract_assigned_literal_dict(logic_source, "key_aliases")
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
    ui_source = Path(adv_ui.__file__).read_text(encoding="utf-8")
    logic_source = Path(adv_ui.__file__.replace("_ui.py", "_logic.py")).read_text(
        encoding="utf-8"
    )
    produced_keys = set(re.findall(r'data\["([^"]+)"\]\s*=', ui_source))
    has_active_block = _get_has_active_block(ui_source)
    detector_keys = set(re.findall(r'data\.get\("([^"]+)"\)', has_active_block))

    logic_week_exclude_keys = set(
        re.findall(r'"(semana_(?:emissao|execucao)_exclude)"', logic_source)
    )
    explicit_noop_allowlist = {"semana_emissao_exclude", "semana_execucao_exclude"}

    assert logic_week_exclude_keys <= explicit_noop_allowlist
    assert explicit_noop_allowlist <= produced_keys
    not_in_detector = logic_week_exclude_keys - detector_keys
    assert not_in_detector <= explicit_noop_allowlist
