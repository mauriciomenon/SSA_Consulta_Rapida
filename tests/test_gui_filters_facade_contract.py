from typing import Any, cast

from gui import gui_ssa


class _DummyWindow:
    pass


def test_has_active_advanced_filters_uses_primary_handler(monkeypatch):
    dummy = _DummyWindow()

    def _primary(_self, _data):
        return "primary"

    monkeypatch.setattr(gui_ssa.ssa_gui_filters, "_has_active_advanced_filters", _primary, raising=False)
    result = gui_ssa.SSAMainWindow._has_active_advanced_filters(cast(Any, dummy), {"macro_filter": "x"})
    assert result == "primary"


def test_has_active_advanced_filters_falls_back_to_ui_module(monkeypatch):
    dummy = _DummyWindow()
    monkeypatch.delattr(gui_ssa.ssa_gui_filters, "_has_active_advanced_filters", raising=False)
    result = gui_ssa.SSAMainWindow._has_active_advanced_filters(cast(Any, dummy), {"macro_filter": "x"})
    assert result is True
