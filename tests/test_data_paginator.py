"""Testes unitários para robustez de paginação da GUI."""

import os
import sys

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.widgets.data_paginator import DataPaginator  # noqa: E402


class TestDataPaginator:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_update_pagination_info_clamps_page_upper_bound(self):
        df = pd.DataFrame({"numero_ssa": list(range(1, 121))})
        paginator = DataPaginator(df, page_size=50)

        paginator.current_page = 5
        paginator.update_pagination_info()
        paginator.update_buttons()

        assert paginator.total_pages == 3
        assert paginator.current_page == 3
        assert paginator.page_info_label.text() == "3 de 3"
        assert paginator.prev_button.isEnabled() is True
        assert paginator.next_button.isEnabled() is False
        assert paginator.prev_button.text() == "◂"
        assert paginator.prev_button.toolTip() == "Pagina anterior"
        assert paginator.next_button.text() == "▸"
        assert paginator.next_button.toolTip() == "Proxima pagina"

    def test_update_pagination_info_clamps_page_lower_bound(self):
        df = pd.DataFrame({"numero_ssa": [1, 2, 3]})
        paginator = DataPaginator(df, page_size=10)

        paginator.current_page = 0
        paginator.update_pagination_info()
        paginator.update_buttons()

        assert paginator.total_pages == 1
        assert paginator.current_page == 1
        assert paginator.page_info_label.text() == "1 de 1"
        assert paginator.prev_button.isEnabled() is False
        assert paginator.next_button.isEnabled() is False

    def test_set_dataframe_emits_first_page_and_preserves_empty_schema(self):
        df = pd.DataFrame({"numero_ssa": [1, 2, 3], "situacao": ["APL", "STE", "APV"]})
        paginator = DataPaginator(df, page_size=2)
        seen_pages = []
        paginator.page_changed.connect(seen_pages.append)

        empty_df = df.iloc[0:0].copy()
        paginator.set_dataframe(empty_df)

        assert seen_pages == [1]
        current = paginator.get_current_slice()
        assert list(current.columns) == ["numero_ssa", "situacao"]
        assert current.empty is True

    def test_set_dataframe_can_update_without_emitting_page_changed(self):
        df = pd.DataFrame({"numero_ssa": [1, 2, 3], "situacao": ["APL", "STE", "APV"]})
        paginator = DataPaginator(df, page_size=2)
        seen_pages = []
        paginator.page_changed.connect(seen_pages.append)

        updated_df = pd.DataFrame({"numero_ssa": [4, 5], "situacao": ["APL", "APV"]})
        paginator.set_dataframe(updated_df, emit_page_changed=False)

        assert seen_pages == []
        assert paginator.current_page == 1
        assert paginator.total_pages == 1
        assert paginator.get_current_slice().equals(updated_df)
