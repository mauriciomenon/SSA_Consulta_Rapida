import os

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)

from unittest.mock import patch

import gui.mixins.filter_gui_ssa_mixin as mixin_module
from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin


class _DummyStatusLabel:
    def __init__(self) -> None:
        self.text_value = ""

    def setText(self, value: str) -> None:
        self.text_value = value


class _DummyWindow(FilterGUISSAMixin):
    def __init__(self) -> None:
        self.status_label = _DummyStatusLabel()


def test_on_filter_error_skips_modal_dialog_in_pytest(monkeypatch):
    # Be explicit even though pytest sets this env var.
    monkeypatch.setenv(
        "PYTEST_CURRENT_TEST", os.environ.get("PYTEST_CURRENT_TEST") or "1"
    )

    win = _DummyWindow()
    with patch.object(mixin_module.QMessageBox, "critical") as critical:
        win.on_filter_error("boom")

    assert critical.called is False
    assert win.status_label.text_value == "Status: Erro ao aplicar filtro."


def test_on_filter_error_shows_modal_dialog_outside_pytest(monkeypatch):
    """BL-39 achado 8: o ramo real (fora do pytest) mostra o dialogo "Erro de Filtro"."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    win = _DummyWindow()
    with patch.object(mixin_module.QMessageBox, "critical") as critical:
        win.on_filter_error("boom")

    critical.assert_called_once()
    assert critical.call_args.args[1:] == ("Erro de Filtro", "boom")
    assert win.status_label.text_value == "Status: Erro ao aplicar filtro."
