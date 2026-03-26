import logging
import re
from pathlib import Path
from typing import Any, cast

from gui import gui_ssa


class _DummyWindow:
    pass


def test_has_active_advanced_filters_uses_primary_handler(monkeypatch):
    dummy = _DummyWindow()

    def _primary(_self, _data):
        return "primary"

    monkeypatch.setattr(
        gui_ssa.ssa_gui_filters, "_has_active_advanced_filters", _primary, raising=False
    )
    result = gui_ssa.SSAMainWindow._has_active_advanced_filters(
        cast(Any, dummy), {"macro_filter": "x"}
    )
    assert result == "primary"


def test_has_active_advanced_filters_falls_back_to_ui_module(monkeypatch):
    dummy = _DummyWindow()
    monkeypatch.delattr(
        gui_ssa.ssa_gui_filters, "_has_active_advanced_filters", raising=False
    )
    result = gui_ssa.SSAMainWindow._has_active_advanced_filters(
        cast(Any, dummy), {"macro_filter": "x"}
    )
    assert result is True


def test_has_active_advanced_filters_returns_false_when_no_handler(monkeypatch, caplog):
    dummy = _DummyWindow()
    monkeypatch.delattr(
        gui_ssa.ssa_gui_filters, "_has_active_advanced_filters", raising=False
    )

    from gui.ssa import gui_filters_advanced_ui as ssa_gui_filters_ui

    monkeypatch.delattr(
        ssa_gui_filters_ui, "_has_active_advanced_filters", raising=False
    )
    with caplog.at_level(logging.WARNING):
        result = gui_ssa.SSAMainWindow._has_active_advanced_filters(
            cast(Any, dummy), {"macro_filter": "x"}
        )
    assert result is False
    assert any(
        "Advanced filters activity handler is unavailable" in rec.message
        for rec in caplog.records
    )


def test_gui_ssa_facade_symbols_are_exported_or_guarded():
    source = Path(gui_ssa.__file__).read_text(encoding="utf-8")
    referenced = sorted(
        set(re.findall(r"ssa_gui_filters\.([A-Za-z_][A-Za-z0-9_]*)", source))
    )
    guarded = set(
        re.findall(
            r'getattr\(ssa_gui_filters,\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*,\s*None\)',
            source,
        )
    )

    missing_and_unguarded = [
        name
        for name in referenced
        if not hasattr(gui_ssa.ssa_gui_filters, name) and name not in guarded
    ]
    assert not missing_and_unguarded, (
        "Facade methods in gui/gui_ssa.py reference missing symbols without guard: "
        + ", ".join(missing_and_unguarded)
    )
