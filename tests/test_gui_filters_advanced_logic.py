import pandas as pd
import re
from pathlib import Path

from gui.ssa.gui_filters_advanced_logic import _apply_advanced_filters
from gui.ssa import gui_filters_advanced_ui as adv_ui


class _DummyWindow:
    def __init__(self, filters: dict):
        self._advanced_filters = filters


def _normalize_ssa_series(series: pd.Series) -> pd.Series:
    return series.astype(str).fillna("").str.strip()


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
    window = _DummyWindow({"semana_emissao_inicio": 202501, "semana_emissao_fim": 202502})
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


def test_advanced_filter_keys_from_ui_are_covered_by_logic_or_active_detector():
    ui_source = Path(adv_ui.__file__).read_text(encoding="utf-8")
    logic_source = Path(adv_ui.__file__.replace("_ui.py", "_logic.py")).read_text(encoding="utf-8")

    produced_keys = set(re.findall(r'data\\["([^"]+)"\\]\\s*=', ui_source))
    has_active_block_match = re.search(
        r"def _has_active_advanced_filters\\(.*?\\):(?P<body>.*?)def _apply_advanced_filters_from_ui",
        ui_source,
        flags=re.S,
    )
    assert has_active_block_match is not None
    has_active_block = has_active_block_match.group("body")

    uncovered = sorted(
        key for key in produced_keys if key not in logic_source and f'data.get("{key}")' not in has_active_block
    )
    assert not uncovered, f"Advanced filter keys without logic/active coverage: {', '.join(uncovered)}"
