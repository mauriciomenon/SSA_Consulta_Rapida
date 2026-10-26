"""Copias da janela com o estado congelado: limite, dados, filtros e banco intocado."""

import os
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 dependency unavailable in test environment")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import app_menus, window_copies  # noqa: E402


class _FakeWindow:
    def __init__(self, copy_from=None, copy_number=0):
        self._window_copy_number = copy_number
        self.closed = False

    def close(self):
        self.closed = True


def test_copy_limit_and_number_reuse(monkeypatch):
    monkeypatch.setattr(window_copies, "_open_copies", [])
    opened = [window_copies.open_window_copy(object(), _FakeWindow) for _ in range(3)]
    assert [w._window_copy_number for w in opened] == [1, 2, 3]
    assert window_copies.open_window_copy(object(), _FakeWindow) is None

    window_copies.forget_window_copy(opened[1])
    again = window_copies.open_window_copy(object(), _FakeWindow)
    assert again._window_copy_number == 2

    window_copies.close_all_window_copies()
    assert all(w.closed for w in (opened[0], again, opened[2]))
    assert window_copies.open_copy_count() == 0


class TestGUIWindowCopies:
    @classmethod
    def setup_class(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self.load_calls = []
        self._load_patch = patch.object(
            SSAMainWindow, "load_data", lambda win: self.load_calls.append(win)
        )
        self._load_patch.start()
        self.main = SSAMainWindow()
        self.main._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        self.base_df = pd.DataFrame(
            {
                "numero_ssa": ["202500001", "202500002", "202500003"],
                "situacao": ["AAD", "STE", "AMP"],
                "derivada_de": ["", "202500001", ""],
                "descricao_ssa": ["Bomba A", "Bomba B", "Motor C"],
                "setor_executor": ["IEE3", "MEL4", "IEE3"],
            }
        )
        self.main.on_data_loaded(self.base_df.copy())
        self.load_calls.clear()

    def teardown_method(self):
        window_copies.close_all_window_copies()
        self.main.close()
        self._load_patch.stop()

    def test_copy_freezes_visible_rows_without_touching_database(self):
        self.main.search_input.setText("bomba")
        self.main.df_exibido = self.base_df.iloc[:2].copy()  # o que esta na tela

        copy_window = self.main.open_window_copy()

        assert copy_window is not None
        assert copy_window._is_window_copy is True
        assert self.load_calls == []  # nenhuma recarga do banco na copia
        assert sorted(copy_window.df_completo["numero_ssa"]) == ["202500001", "202500002"]
        assert copy_window.df_completo is not self.main.df_exibido
        assert "copia 1" in copy_window.windowTitle()
        assert "origem: bomba" in copy_window.windowTitle()
        assert app_menus.database_operation_in_progress(copy_window) is True
        assert app_menus.database_operation_in_progress(self.main) is False
        assert copy_window._database_operation_actions
        assert not any(a.isEnabled() for a in copy_window._database_operation_actions)

    def test_copy_restore_goes_back_to_frozen_rows_only(self):
        self.main.df_exibido = self.base_df.iloc[:2].copy()
        copy_window = self.main.open_window_copy()
        copy_window.df_exibido = copy_window.df_completo.iloc[:1].copy()  # filtro na copia

        copy_window.restore_frozen_copy_state()

        assert copy_window.search_input.text() == ""
        assert len(copy_window.df_completo) == 2  # nunca alem do congelado

    def test_main_close_closes_copies_and_limit_is_three(self):
        copies = [self.main.open_window_copy() for _ in range(3)]
        assert all(c is not None for c in copies)
        assert self.main.open_window_copy() is None
        window_copies.close_all_window_copies()
        assert window_copies.open_copy_count() == 0
