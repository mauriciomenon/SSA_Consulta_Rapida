"""Testes específicos para filtros combinados (AND/OU) da GUI principal."""

import os
import sqlite3
import sys
import time
from collections import Counter
from typing import Any, cast
from unittest.mock import patch

import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtCore import QPoint, QSize, Qt, QUrl  # noqa: E402
from PyQt6.QtGui import QCloseEvent, QFont, QResizeEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QLineEdit  # noqa: E402
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from gui.ssa import gui_table as ssa_gui_table  # noqa: E402
from gui.widgets.column_filter_dialog import ColumnFilterDialog  # noqa: E402
from gui.widgets.filter_help_dialog import FilterHelpDialog  # noqa: E402

ORIGINAL_LOAD_DATA = SSAMainWindow.load_data


class TestGUIFilterLogic:
    """Valida filtros com perfis OR e exclusões complementares."""

    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        os.environ["SSA_SYNC_FILTER"] = "1"
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        # Mantém o patch ativo para impedir agendamento de carregamentos reais
        self.window.show()

        # Dataset simplificado com combinação de executor/emissor e situações distintas
        self.base_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2, 3, 4, 5],
                "situacao": ["APV", "STE", "SCA", "AMP", "APV"],
                "derivada_de": ["", "", "", "", ""],
                "localizacao_codigo": ["LOC1", "LOC2", "LOC3", "LOC4", "LOC5"],
                "descricao_localizacao": ["Desc1"] * 5,
                "equipamento": ["EQ1"] * 5,
                "semana_cadastro": [202501] * 5,
                "semana_programada": [202503] * 5,
                "data_cadastro": ["2025-01-01"] * 5,
                "descricao_ssa": [
                    "Teste A",
                    "Teste B",
                    "Teste C",
                    "Teste D",
                    "Teste E",
                ],
                "setor_executor": ["IEE3", "OURO", "MEL4", "XYZ", "IEE2"],
                "setor_emissor": ["ABC", "IEE3", "MEL4", "MEL3", "XYZ"],
                "descricao_execucao": [
                    "Exec A",
                    "Exec B",
                    "Exec C",
                    "Exec D",
                    "Exec E",
                ],
                "solicitante": ["User1", "User2", "User3", "User4", "User5"],
            }
        )

        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())

    def teardown_method(self):
        self._load_patch.stop()
        self.window.close()
        try:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        except Exception:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = []
        try:
            filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS.clear()
        except Exception:
            filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS[:] = []

    def _extract_visible_ssa(self):
        return list(self.window.df_exibido["numero_ssa"])

    def _build_heavy_filters_df(self, rows: int = 1200) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "numero_ssa": list(range(100000, 100000 + rows)),
                "situacao": ["APV", "STE", "SCA", "AMP"] * (rows // 4)
                + ["APV"] * (rows % 4),
                "derivada_de": [""] * rows,
                "localizacao_codigo": [f"LOC{i % 250:04d}" for i in range(rows)],
                "descricao_localizacao": ["Desc"] * rows,
                "equipamento": [f"EQ{i % 350:04d}" for i in range(rows)],
                "semana_cadastro": [202501 + (i % 52) for i in range(rows)],
                "semana_programada": [202510 + (i % 52) for i in range(rows)],
                "data_cadastro": ["2025-01-01"] * rows,
                "descricao_ssa": [f"Descricao {i}" for i in range(rows)],
                "setor_executor": [f"SETOR_{i % 35:02d}" for i in range(rows)],
                "setor_emissor": [f"SETOR_{i % 35:02d}" for i in range(rows)],
                "descricao_execucao": [f"Execucao {i}" for i in range(rows)],
                "solicitante": [f"SOL_{i % 1500:04d}" for i in range(rows)],
                "responsavel_programacao": [
                    f"PROG_{i % 1700:04d}" for i in range(rows)
                ],
                "responsavel_execucao": [f"EXEC_{i % 1800:04d}" for i in range(rows)],
                "responsavel_emissor": [f"EMIS_{i % 1600:04d}" for i in range(rows)],
            }
        )

    def _get_column_filter_controls(self):
        controls = {}
        layout = getattr(self.window, "col_filters_list_layout", None)
        if not layout:
            return controls
        for i in range(layout.count()):
            item = layout.itemAt(i)
            row_widget = item.widget()
            if row_widget is None:
                continue
            row_layout = row_widget.layout()
            if row_layout is None or row_layout.count() < 5:
                continue
            label_widget = row_layout.itemAt(0).widget()
            edit_widget = row_layout.itemAt(1).widget()
            apply_widget = row_layout.itemAt(2).widget()
            clear_widget = row_layout.itemAt(3).widget()
            hide_widget = row_layout.itemAt(4).widget()
            if not isinstance(label_widget, QLabel):
                continue
            if not isinstance(edit_widget, QLineEdit):
                continue
            if not isinstance(apply_widget, QPushButton):
                continue
            if not isinstance(clear_widget, QPushButton):
                continue
            if not isinstance(hide_widget, QPushButton):
                continue
            controls[label_widget.text()] = (
                edit_widget,
                apply_widget,
                clear_widget,
                hide_widget,
            )
        return controls

    def test_column_selector_button_shows_visible_count_in_text(self):
        selector = getattr(self.window, "column_selector", None)
        assert selector is not None
        text = str(selector.manage_button.text() or "")
        assert text.startswith("Colunas Visiveis:")
        assert not hasattr(selector, "summary_label")

    def test_top_toolbar_hides_update_derivadas_button(self):
        button = getattr(self.window, "update_derivadas_button", None)
        assert button is not None
        assert button.isVisible() is False
        visible_named = [
            btn
            for btn in self.window.findChildren(QPushButton)
            if str(btn.text() or "") == "Atualizar Derivadas" and btn.isVisible()
        ]
        assert visible_named == []

    def test_search_and_pagination_rows_place_controls_in_expected_lines(self):
        main_ctx = self.window._tab_contexts[0]
        search_input = main_ctx["search_input"]
        search_button = main_ctx["search_button"]
        save_filter_button = main_ctx["save_filter_button"]
        filter_tags_widget = main_ctx["filter_tags_widget"]
        paginator = main_ctx["paginator"]
        column_selector = main_ctx["column_selector"]
        quick_label = main_ctx["quick_setor_executor_label"]
        quick_combo = main_ctx["quick_setor_executor_combo"]

        QApplication.processEvents()

        tooltip = str(save_filter_button.toolTip() or "")
        assert "somente o filtro atual da Pesquisa Geral" in tooltip
        assert abs(save_filter_button.geometry().y() - search_input.geometry().y()) <= 8
        assert (
            abs(filter_tags_widget.geometry().y() - save_filter_button.geometry().y())
            <= 8
        )
        assert filter_tags_widget.geometry().x() > save_filter_button.geometry().x()
        assert column_selector.geometry().y() > search_input.geometry().y()
        assert abs(column_selector.geometry().y() - paginator.geometry().y()) <= 10
        assert column_selector.geometry().x() > paginator.geometry().x()
        assert (column_selector.geometry().x() - paginator.geometry().right()) <= 40
        assert str(quick_label.text() or "") == "Setor Executor:"
        assert abs(quick_label.geometry().y() - quick_combo.geometry().y()) <= 6
        assert quick_label.geometry().x() < quick_combo.geometry().x()
        assert quick_combo.geometry().x() > column_selector.geometry().x()
        assert quick_combo.height() <= (search_button.height() + 2)
        assert quick_combo.height() >= 24
        parent_widget = quick_combo.parentWidget()
        assert parent_widget is not None
        right_gap = parent_widget.rect().right() - quick_combo.geometry().right()
        assert right_gap <= 24

    def test_search_help_texts_reflect_current_general_search_contract(self):
        main_ctx = self.window._tab_contexts[0]
        search_input = main_ctx["search_input"]
        col_indicator = main_ctx["col_filter_indicator"]
        search_help = main_ctx["search_help"]

        assert (
            str(search_input.placeholderText() or "")
            == "Termos separados por virgula; ! exclui termo"
        )
        tooltip = str(search_input.toolTip() or "")
        assert (
            "Todos os termos digitados devem ser satisfeitos na mesma linha." in tooltip
        )
        assert "condicao E" not in tooltip.casefold()
        assert "Busca superior: todos os termos digitados sao obrigatorios." in str(
            search_help.text() or ""
        )

        indicator_tooltip = str(col_indicator.toolTip() or "")
        assert "virgulas representam alternativas implicitas" in indicator_tooltip
        assert "logica OU" not in indicator_tooltip

    def test_filter_help_dialog_texts_separate_general_search_from_column_alternatives(
        self,
    ):
        dialog = FilterHelpDialog(self.window)
        browser = dialog.findChild(QtWidgets.QTextBrowser)
        assert browser is not None
        html = str(browser.toHtml() or "")

        assert "Pesquisa Geral" in html
        assert "todos os termos digitados sao obrigatorios" in html
        assert "virgulas representam alternativas implicitas" in html
        assert "logica OU - qualquer termo serve" not in html

    def test_setor_executor_order_prioritizes_smin_then_mel_then_alpha(self):
        ordered = SSAMainWindow._order_setor_executor_values(
            ["AAA", "ZZZ", "MEL3", "IEE4", "ABC", "IEE1", "MEL1"]
        )
        assert ordered == ["IEE1", "IEE4", "MEL1", "MEL3", "AAA", "ABC", "ZZZ"]

    def test_quick_setor_executor_combo_applies_filter_and_syncs_or_group_only(self):
        self.window._register_or_group(
            ["setor_executor", "setor_emissor"], ["IEE3", "MEL3"]
        )
        self.window._active_column_filters["setor_executor"] = "IEE3, MEL3"
        self.window._active_column_filters["setor_emissor"] = "IEE3, MEL3"
        advanced_before = dict(getattr(self.window, "_advanced_filters", {}) or {})
        self.window._build_column_filters_panel()
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        assert int(combo.maxVisibleItems()) == 14
        assert getattr(self.window, "persist_filter_config_checkbox", None) is None
        style_sheet = str(combo.styleSheet() or "")
        assert "combobox-popup: 0" in style_sheet
        mel4_idx = combo.findData("MEL4")
        assert mel4_idx >= 0
        assert str(combo.itemText(0)) == "Todos"
        assert str(combo.itemText(mel4_idx)) == "MEL4"
        assert "Setor Executor:" not in str(combo.currentText() or "")

        combo.setCurrentIndex(mel4_idx)
        QApplication.processEvents()
        assert str(combo.currentText() or "") == "MEL4"

        assert self.window._active_column_filters.get("setor_executor") == "MEL4"
        assert self.window._active_column_filters.get("setor_emissor") == "IEE3, MEL3"
        assert (
            dict(getattr(self.window, "_advanced_filters", {}) or {}) == advanced_before
        )

        self.window.main_tabs.setCurrentIndex(1)
        QApplication.processEvents()
        assert "MEL4" in str(getattr(self.window, "adv_executor_button").text() or "")
        self.window.main_tabs.setCurrentIndex(0)
        QApplication.processEvents()

        controls = self._get_column_filter_controls()
        setor_key = next(
            (
                key
                for key in controls.keys()
                if str(key or "").strip().casefold().startswith("setor executor")
            ),
            None,
        )
        assert setor_key is not None
        setor_input, _, _, _ = controls[setor_key]
        assert str(setor_input.text() or "").strip() == "MEL4"

    def test_quick_setor_executor_combo_journey_updates_cache_context_and_clear_global(
        self,
    ):
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None

        mel4_idx = combo.findData("MEL4")
        assert mel4_idx >= 0
        combo.setCurrentIndex(mel4_idx)
        QApplication.processEvents()

        first_context = self.window._build_filter_cache_context()
        assert '"setor_executor": "MEL4"' in first_context
        assert '"exclude_ste_sca": false' in first_context

        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()

        second_context = self.window._build_filter_cache_context()
        assert second_context != first_context
        assert '"setor_executor": "MEL4"' in second_context
        assert '"exclude_ste_sca": true' in second_context

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._build_filter_cache_context() == ""
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert str(combo.currentText() or "") == "Todos"

    def test_profile_or_filters_executor_or_emissor(self):
        """Perfil OR deve considerar executor ou emissor e refletir na UI."""
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)

        # Com OR restrito por coluna e AND entre colunas, apenas quem atende ambos entra (aqui só o 3)
        assert Counter(self._extract_visible_ssa()) == Counter([3])

        # Confirma sincronismo entre campos (Executor/Emissor)
        for col in ("setor_executor", "setor_emissor"):
            # Armazenamento interno usa virgulas para separar alternativas
            assert self.window._active_column_filters[col] == "IEE3, MEL3, MEL4"
        summary = getattr(self.window, "filters_summary_label", None)
        if summary is not None:
            # Nova logica: apenas virgulas, sem operadores OU
            assert "IEE3, MEL3, MEL4" in summary.text() or "Executor" in summary.text()
            assert col in self.window._column_to_or_group

        # Ajuste manual em um campo deve repercutir no par
        self.window._active_column_filters["setor_executor"] = "MEL4"
        self.window._sync_or_group_values("setor_executor", "MEL4")
        self.window._refresh_after_filter_change()
        assert self.window._active_column_filters["setor_emissor"] == "MEL4"
        assert Counter(self._extract_visible_ssa()) == Counter([3])

    def test_exclude_ste_sca_combined_with_or_group(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        # Com a nova semântica, somente o 3 está visível
        assert Counter(self._extract_visible_ssa()) == Counter([3])

        ses_row = pd.DataFrame(
            [
                {
                    "numero_ssa": 6,
                    "situacao": "SES",
                    "derivada_de": "",
                    "localizacao_codigo": "LOC6",
                    "descricao_localizacao": "Desc6",
                    "equipamento": "EQ1",
                    "semana_cadastro": 202501,
                    "semana_programada": 202503,
                    "data_cadastro": "2025-01-01",
                    "descricao_ssa": "Teste F",
                    "setor_executor": "MEL4",
                    "setor_emissor": "MEL4",
                    "descricao_execucao": "Exec F",
                    "solicitante": "User6",
                }
            ]
        )
        merged_df = pd.concat([self.window.df_completo, ses_row], ignore_index=True)
        self.window.df_completo = merged_df.copy()
        self.window.df_exibido = merged_df.copy()
        self.window._df_last_search_filtered = merged_df.copy()
        self.window.paginator.set_dataframe(merged_df.copy())
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)

        self.window._on_exclude_ste_sca_toggled(True)
        # Filtra linhas SCA/SES/STE (3 e 6 deverão sair)
        remaining = self._extract_visible_ssa()
        assert 3 not in remaining
        assert 6 not in remaining
        # Com base no filtro aplicado, nada resta após excluir SCA/SES/STE
        assert Counter(remaining) == Counter([])

    def test_macro_baixar_excludes_sad_sca_ses_ste_and_keeps_ste_or_ses_derivadas(
        self,
    ):
        macro_df = pd.DataFrame(
            {
                "numero_ssa": ["100", "101", "102", "200", "201", "202"],
                "situacao": ["APV", "STE", "SES", "APV", "SCA", "SAD"],
                "derivada_de": ["", "100", "100", "", "200", "200"],
                "localizacao_codigo": ["LOC1"] * 6,
                "descricao_localizacao": ["Desc"] * 6,
                "equipamento": ["EQ1"] * 6,
                "semana_cadastro": [202501] * 6,
                "semana_programada": [202503] * 6,
                "data_cadastro": ["2025-01-01"] * 6,
                "descricao_ssa": [
                    "Origem A",
                    "Filha STE",
                    "Filha SES",
                    "Origem B",
                    "Filha SCA",
                    "Filha SAD",
                ],
                "setor_executor": ["IEE3", "IEE3", "IEE3", "MEL4", "MEL4", "MEL4"],
                "setor_emissor": ["IEE3", "IEE3", "IEE3", "MEL4", "MEL4", "MEL4"],
                "descricao_execucao": [
                    "Exec A",
                    "Exec B",
                    "Exec C",
                    "Exec D",
                    "Exec E",
                    "Exec F",
                ],
                "solicitante": ["User1", "User2", "User3", "User4", "User5", "User6"],
            }
        )
        self.window.df_completo = macro_df.copy()
        self.window.df_exibido = macro_df.copy()
        self.window._df_last_search_filtered = macro_df.copy()
        self.window.paginator.set_dataframe(macro_df.copy())
        self.window.main_tabs.setCurrentIndex(1)
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()

        macro_idx = self.window.adv_macro_combo.findData("ssas_para_baixar")
        assert macro_idx >= 0

        self.window.adv_macro_combo.setCurrentIndex(macro_idx)
        self.window._on_macro_filter_changed()
        QApplication.processEvents()

        assert self.window._advanced_filters.get("derivada_all_ste") is True
        assert set(
            self.window._advanced_filters.get("situacao_exclude_values") or []
        ) == {"SAD", "SCA", "SES", "STE"}
        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == ["100"]

    def test_filters_summary_deduplicates_column_and_advanced_entries(self):
        self.window._active_column_filters["setor_executor"] = "IEE3"
        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True

        self.window._update_filters_summary()
        QApplication.processEvents()

        summary_text = str(self.window.filters_summary_label.text() or "")
        assert summary_text.count("Executor: IEE3") == 1

    def test_display_headers_mark_advanced_filter_columns_with_f(self):
        if "solicitante" not in self.window.visible_columns:
            self.window.visible_columns.append("solicitante")

        self.window._active_column_filters = {
            col: "" for col in self.window._column_filter_default_columns()
        }
        self.window._advanced_filters = {"solicitante": ["User1"]}
        self.window._advanced_filters_active = True

        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("solicitante")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text.startswith("[f] ")

    def test_clear_operations_preserve_group_structure(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        self.window._clear_single_column_filter("setor_executor", "IEE3, MEL3, MEL4")
        # Grupo deve ser removido para ambos os campos
        assert "setor_executor" not in self.window._active_column_filters
        assert "setor_emissor" not in self.window._active_column_filters

        # Reaplica valor manual e garante aplicação correta
        self.window._active_column_filters["setor_executor"] = "IEE3"
        self.window._sync_or_group_values("setor_executor", "IEE3")
        self.window._refresh_after_filter_change()
        # Com OR restrito por coluna e sincronismo no grupo (IEE3 em ambos), nenhum registro atende ambos
        assert Counter(self._extract_visible_ssa()) == Counter([])

        # Limpa todos e garante reset completo
        self.window._clear_all_column_filters()
        assert self.window._active_column_filters
        assert not any(
            str(v).strip() for v in self.window._active_column_filters.values()
        )
        self.window._refresh_after_filter_change()
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])

    def test_add_column_menu_includes_full_candidates_and_excludes_legacy_aliases(
        self, monkeypatch
    ):
        class _FakeAction:
            def __init__(self, text: str):
                self.text = text
                self.data_value = None
                self.checked = False

            def setCheckable(self, _state: bool):
                return None

            def setChecked(self, state: bool):
                self.checked = bool(state)

            def setData(self, value: str):
                self.data_value = value

            def data(self):
                return self.data_value

        class _FakeMenu:
            created_actions: list[_FakeAction] = []

            def __init__(self, _parent=None):
                self.actions: list[_FakeAction] = []

            def addAction(self, text: str):
                action = _FakeAction(text)
                self.actions.append(action)
                _FakeMenu.created_actions.append(action)
                return action

            def exec(self, _pos):
                return None

            def deleteLater(self):
                return None

        self.window.internal_to_display["No SSA"] = "No SSA"
        self.window.internal_to_display["Data Cadastro"] = "Data Cadastro"
        self.window.internal_to_display["numero_ssa"] = "Numero SSA"
        self.window.internal_to_display["registros_espera"] = "Registros Espera"
        self.window.internal_to_display["num_reprobaciones"] = "Num Reprobaciones"
        self.window.internal_to_display["situacao_espera"] = "Situacao Espera"
        self.window.internal_to_display["numero_desvios"] = "Numero Desvios"
        self.window.internal_to_display["ate"] = "Ate"
        self.window.internal_to_display["justificativa"] = "Justificativa"
        self.window.internal_to_display["parciais"] = "Parciais"
        self.window.internal_to_display["situacao_da_parcial"] = "Situacao Parcial"

        monkeypatch.setattr(QtWidgets, "QMenu", _FakeMenu)

        self.window._open_add_column_filter_menu()
        menu_columns = {action.data() for action in _FakeMenu.created_actions}

        assert "situacao" in menu_columns
        assert "numero_ssa" in menu_columns
        assert "descricao_execucao" in menu_columns
        assert "No SSA" not in menu_columns
        assert "Data Cadastro" not in menu_columns
        assert "registros_espera" not in menu_columns
        assert "num_reprobaciones" not in menu_columns
        assert "situacao_espera" not in menu_columns
        assert "numero_desvios" not in menu_columns
        assert "ate" not in menu_columns
        assert "justificativa" not in menu_columns
        assert "parciais" not in menu_columns
        assert "situacao_da_parcial" not in menu_columns

    def test_get_canonical_available_columns_keeps_active_filter_even_outside_non_null_cache(
        self,
    ):
        self.window.df_completo = pd.DataFrame(
            {
                "situacao": ["APV", "STE"],
                "descricao_ssa": [None, None],
                "coluna_zerada": [None, None],
            }
        )
        self.window.df_exibido = self.window.df_completo.copy()
        self.window._non_null_cols_cache = {"situacao"}
        self.window._active_column_filters = {"descricao_ssa": "teste"}

        columns = self.window._get_canonical_available_columns()

        assert "situacao" in columns
        assert "descricao_ssa" in columns
        assert "coluna_zerada" not in columns

    def test_clear_all_column_filters_restores_defaults_and_hidden_lines(self):
        self.window._active_column_filters = {
            "numero_ssa": "2026",
            "situacao": "STE",
        }
        self.window._hidden_column_filter_lines = {"descricao_ssa", "setor_executor"}
        self.window._build_column_filters_panel()

        self.window._clear_all_column_filters()

        default_cols = self.window._column_filter_default_columns()
        assert tuple(self.window._active_column_filters.keys()) == default_cols
        assert not any(
            str(v).strip() for v in self.window._active_column_filters.values()
        )
        assert self.window._hidden_column_filter_lines == set()

    def test_removing_visible_column_keeps_active_filter_row_visible(self):
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._build_column_filters_panel()
        QApplication.processEvents()

        label = (
            self.window._expand_column_alias_for_filter("descricao_ssa")
            if hasattr(self.window, "_expand_column_alias_for_filter")
            else self.window._resolve_column_display_name("descricao_ssa")
        )
        controls_before = self._get_column_filter_controls()
        assert label in controls_before
        assert "descricao_ssa" in self.window.visible_columns

        new_columns = [
            col for col in self.window.visible_columns if col != "descricao_ssa"
        ]
        self.window.on_columns_changed(new_columns)
        QApplication.processEvents()

        controls_after = self._get_column_filter_controls()
        assert "descricao_ssa" not in self.window.visible_columns
        assert label in controls_after
        assert self.window._active_column_filters["descricao_ssa"] == "Teste A"
        assert "descricao_ssa" not in self.window._hidden_column_filter_lines

    def test_default_column_filter_rows_show_apply_clear_and_hide_buttons(self):
        self.window._active_column_filters = {
            col: "" for col in self.window._column_filter_default_columns()
        }
        self.window._build_column_filters_panel()

        controls = self._get_column_filter_controls()
        for col in self.window._column_filter_default_columns():
            if hasattr(self.window, "_expand_column_alias_for_filter"):
                label = self.window._expand_column_alias_for_filter(col)
            else:
                label = self.window._resolve_column_display_name(col)
            assert label in controls
            _, apply_btn, clear_btn, hide_btn = controls[label]
            assert apply_btn.text() == "Aplicar"
            assert clear_btn.text() == "Limpar"
            assert hide_btn.text() == "Ocultar"
            assert not apply_btn.isHidden()
            assert not clear_btn.isHidden()
            assert not hide_btn.isHidden()

    def test_table_render_collapses_multiline_text_to_single_line(self):
        df = self.base_df.copy()
        df.loc[0, "descricao_ssa"] = "Linha A\nLinha B"
        df.loc[1, "descricao_ssa"] = "Linha C\\nLinha D"
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        col_idx = self.window._current_display_columns.index("descricao_ssa")
        item = self.window.table_widget.item(0, col_idx)
        assert item is not None
        assert "\n" not in item.text()
        assert "\r" not in item.text()
        assert "Linha A Linha B" in item.text()

        item_literal = self.window.table_widget.item(1, col_idx)
        assert item_literal is not None
        assert "\\n" not in item_literal.text()
        assert "Linha C Linha D" in item_literal.text()

    def test_refresh_after_filter_change_updates_filtered_status_counter(self):
        self.window._active_column_filters = {"situacao": "STE"}
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        status = self.window.status_label.text()
        assert "SSAs filtradas" in status
        assert "1 de 5" in status

    def test_set_filtered_count_status_accepts_suffix(self):
        self.window._set_filtered_count_status(
            "", filtered_total=2, original_total=5, suffix="Aviso: teste."
        )
        status = self.window.status_label.text()
        assert status == "Status: SSAs filtradas: 2 de 5. Aviso: teste."

    def test_apply_advanced_filters_notice_uses_count_status_helper(self, monkeypatch):
        self.window._pending_search_display = "Busca X"

        def _fake_refresh():
            callback = getattr(self.window, "_adv_notice_callback", None)
            if callable(callback):
                callback("derivada_empty")

        monkeypatch.setattr(self.window, "_refresh_after_filter_change", _fake_refresh)
        self.window._apply_advanced_filters_from_ui(store_only=False)
        status = self.window.status_label.text()
        assert "Status: SSAs filtradas:" in status
        assert "para 'Busca X'" in status
        assert "Aviso: nenhuma derivada encontrada para o filtro." in status

    def test_find_unmapped_alias_columns_reports_only_unmapped(self):
        self.window.internal_to_display["numero_ssa"] = "Numero SSA"
        missing = self.window._find_unmapped_alias_columns(
            ["numero_ssa", "descricao_ssa", "coluna_sem_alias", "#", "coluna_sem_alias"]
        )
        assert missing == ["coluna_sem_alias"]

    def test_general_search_and_or_display(self):
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.search_input.setText("Teste")
        self.window.initiate_filtering()
        QApplication.processEvents()

        # Busca geral com AND logic: termo unico retorna todos que contem 'Teste'
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert self.window.search_input.text() == "Teste"

        # Combinação com termo negativo utilizando AND
        self.window.search_input.setText("Teste A, !User2")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])
        assert self.window.search_input.text() == "Teste A, !User2"

    def test_column_widths_stability_during_cycles(self):
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        # Ajusta manualmente a largura de uma coluna e garante persistência pós-ciclos
        self.window.table_widget.setColumnWidth(1, 240)
        width_before = self.window.table_widget.columnWidth(1)

        # Aplica perfil OR, filtros gerais e limpa várias vezes
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        width_after_profile = self.window.table_widget.columnWidth(1)

        self.window.search_input.setText("Teste A, Teste D")
        self.window.initiate_filtering()
        QApplication.processEvents()
        width_after_search = self.window.table_widget.columnWidth(1)

        self.window._clear_all_column_filters()
        QApplication.processEvents()
        width_after_clear_columns = self.window.table_widget.columnWidth(1)

        self.window.clear_filter()
        QApplication.processEvents()
        width_after_clear_general = self.window.table_widget.columnWidth(1)

        # Larguras não devem ser zeradas; permitir pequenas variações entre ciclos
        assert width_before > 0
        assert width_after_profile > 0
        assert width_after_search > 0
        assert width_after_clear_columns > 0
        assert width_after_clear_general > 0

    def test_display_current_page_honors_page_number_parameter(self):
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.page_size = 2
        self.window.paginator.set_dataframe(self.base_df.copy())

        self.window.display_current_page(2)
        QApplication.processEvents()

        assert self.window.paginator.current_page == 2
        assert not self.window.df_para_tabela.empty
        assert int(self.window.df_para_tabela.iloc[0]["numero_ssa"]) == 3

    def test_filters_tab_layout_keeps_bottom_panel_below_table_with_few_rows(self):
        self.window.main_tabs.setCurrentIndex(1)
        QApplication.processEvents()

        tiny_df = self.base_df.iloc[:1].copy()
        self.window.df_completo = tiny_df.copy()
        self.window.df_exibido = tiny_df.copy()
        self.window._df_last_search_filtered = tiny_df.copy()
        self.window._tab_contexts[1]["paginator"].set_dataframe(tiny_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        ctx = self.window._tab_contexts[1]
        table = ctx["table_widget"]
        details = ctx["details_group"]
        adv = ctx["adv_filters_group"]

        table_top = table.mapToGlobal(QPoint(0, 0)).y()
        table_bottom = table_top + table.height() - 1
        bottom_top = min(
            details.mapToGlobal(QPoint(0, 0)).y(),
            adv.mapToGlobal(QPoint(0, 0)).y(),
        )

        assert table.minimumHeight() >= 220
        assert bottom_top > table_bottom

    def test_bottom_panels_keep_single_synced_height_after_resize(self):
        self.window.main_tabs.setCurrentIndex(0)
        QApplication.processEvents()
        self.window.resize(1520, 980)
        QApplication.processEvents()
        self.window._sync_bottom_panel_heights()
        QApplication.processEvents()

        groups = []
        for ctx in self.window._tab_contexts:
            for key in ("details_group", "adv_filters_group", "col_filters_group"):
                widget = ctx.get(key)
                if widget is None:
                    continue
                if widget in groups:
                    continue
                groups.append(widget)

        assert len(groups) >= 3
        min_heights = {int(g.minimumHeight()) for g in groups}
        max_heights = {int(g.maximumHeight()) for g in groups}
        assert len(min_heights) == 1
        assert len(max_heights) == 1
        synced_height = next(iter(min_heights))
        assert synced_height == next(iter(max_heights))
        assert 180 <= synced_height <= 360

    def test_clear_filter_button_reflects_active_filters(self):
        self.window.search_input.setText("")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is False

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is True

        self.window.clear_filter()
        QApplication.processEvents()
        assert self.window.search_input.text() == ""
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs(self):
        for ctx in self.window._tab_contexts:
            button = ctx.get("clear_filter_button")
            assert button is not None
            assert button.text() == "Limpar Busca"
            tooltip = str(button.toolTip() or "").casefold()
            assert "apenas a busca geral" in tooltip
            assert "coluna" in tooltip
            assert "avancados" in tooltip

    def test_search_buttons_route_to_tab_specific_handlers(self):
        main_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "main"
        )
        filters_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "filters"
        )
        main_ctx["clear_filter_button"].setEnabled(True)
        filters_ctx["clear_filter_button"].setEnabled(True)

        with (
            patch.object(self.window, "_on_general_search_apply_clicked") as apply_mock,
            patch.object(self.window, "_on_general_search_clear_clicked") as clear_mock,
        ):
            cast(Any, QTest).mouseClick(
                main_ctx["search_button"], Qt.MouseButton.LeftButton
            )
            cast(Any, QTest).mouseClick(
                filters_ctx["search_button"], Qt.MouseButton.LeftButton
            )
            cast(Any, QTest).mouseClick(
                main_ctx["clear_filter_button"], Qt.MouseButton.LeftButton
            )
            cast(Any, QTest).mouseClick(
                filters_ctx["clear_filter_button"], Qt.MouseButton.LeftButton
            )

        assert [call.args[0] for call in apply_mock.call_args_list] == [
            "main",
            "filters",
        ]
        assert [call.args[0] for call in clear_mock.call_args_list] == [
            "main",
            "filters",
        ]

    def test_clear_filter_clears_only_general_search_and_keeps_advanced_filters(self):
        self.window._advanced_filters = {
            "situacao": ["STE"],
            "setor_executor": ["IEE3"],
        }
        self.window._advanced_filters_active = True
        self.window._adv_options_dirty = False
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        with patch.object(
            self.window,
            "_refresh_after_filter_change",
            wraps=self.window._refresh_after_filter_change,
        ) as refresh_mock:
            self.window.clear_filter()
            QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._advanced_filters == {
            "situacao": ["STE"],
            "setor_executor": ["IEE3"],
        }
        assert self.window._advanced_filters_active is True
        assert self.window._adv_options_dirty is False
        assert refresh_mock.call_count >= 1

    def test_clear_filter_preserves_column_filters_and_result_set(self):
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])

        self.window.search_input.setText("Teste")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])

        self.window.clear_filter()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._active_column_filters["descricao_ssa"] == "Teste A"
        assert Counter(self._extract_visible_ssa()) == Counter([1])
        assert self.window.clear_filter_button.isEnabled() is True

    def test_clear_filter_preserves_exclude_ste_sca_state(self):
        self.window._on_exclude_ste_sca_toggled(True)
        self.window.search_input.setText("Teste")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1, 4, 5])

        self.window.clear_filter()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._exclude_ste_sca is True
        assert Counter(self._extract_visible_ssa()) == Counter([1, 4, 5])
        assert self.window.clear_filter_button.isEnabled() is True

    def test_refresh_after_filter_change_updates_clear_button_state(self):
        self.window.clear_filter_button.setEnabled(False)
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is True

        self.window._active_column_filters["descricao_ssa"] = ""
        self.window._exclude_ste_sca = False
        self.window._advanced_filters = {}
        self.window._advanced_filters_active = False
        for ctx in self.window._tab_contexts:
            ctx["search_input"].setText("")
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_filter_button_state_syncs_across_tabs_without_switch(self):
        buttons = []
        for ctx in self.window._tab_contexts:
            button = ctx.get("clear_filter_button")
            if button is not None:
                buttons.append(button)
        assert len(buttons) == 2
        assert all(button.isEnabled() is False for button in buttons)

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert all(button.isEnabled() is True for button in buttons)

        self.window.clear_filter()
        QApplication.processEvents()
        assert all(button.isEnabled() is False for button in buttons)

    def test_three_repeated_clear_search_clicks_offer_hard_reset(self):
        main_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "main"
        )
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        self.window.search_input.setText("Teste")
        self.window.initiate_filtering()
        QApplication.processEvents()

        with (
            patch.object(self.window, "_hard_reset_filters_state") as hard_reset_mock,
            patch(
                "gui.mixins.filter_gui_ssa_mixin.QMessageBox.question"
            ) as question_mock,
            patch.dict(
                os.environ, {"PYTEST_CURRENT_TEST": "", "SSA_NON_INTERACTIVE": ""}
            ),
        ):
            question_mock.return_value = QtWidgets.QMessageBox.StandardButton.Yes
            for _ in range(3):
                cast(Any, QTest).mouseClick(
                    main_ctx["clear_filter_button"], Qt.MouseButton.LeftButton
                )
                QApplication.processEvents()

        assert question_mock.call_count == 1
        hard_reset_mock.assert_called_once()

    def test_three_repeated_global_clear_clicks_offer_hard_reset(self):
        filters_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(1)
        QApplication.processEvents()
        self.window.search_input.setText("Teste")
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        with (
            patch.object(self.window, "_hard_reset_filters_state") as hard_reset_mock,
            patch(
                "gui.mixins.filter_gui_ssa_mixin.QMessageBox.question"
            ) as question_mock,
            patch.dict(
                os.environ, {"PYTEST_CURRENT_TEST": "", "SSA_NON_INTERACTIVE": ""}
            ),
        ):
            question_mock.return_value = QtWidgets.QMessageBox.StandardButton.Yes
            for _ in range(3):
                cast(Any, QTest).mouseClick(
                    filters_ctx["clear_all_filters_btn"], Qt.MouseButton.LeftButton
                )
                QApplication.processEvents()

        assert question_mock.call_count == 1
        hard_reset_mock.assert_called_once()

    def test_clear_advanced_filters_forces_refresh_when_pending_schedule(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True
        self.window._adv_options_dirty = False
        self.window._adv_options_scheduled = True

        with patch.object(
            self.window, "_refresh_advanced_filter_options", return_value=None
        ) as refresh_mock:
            self.window._clear_advanced_filters()
            QApplication.processEvents()

        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert self.window._adv_options_dirty is False
        refresh_mock.assert_called_once()

    def test_undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore(self):
        undo_buttons = []
        for ctx in self.window._tab_contexts:
            button = ctx.get("undo_filter_btn")
            if button is not None:
                undo_buttons.append(button)
        assert len(undo_buttons) == 2
        assert all(button.isEnabled() is False for button in undo_buttons)

        self.window._advanced_filters = {"situacao": ["STE"]}
        self.window._advanced_filters_active = True
        self.window._clear_advanced_filters()
        QApplication.processEvents()

        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert all(button.isEnabled() is True for button in undo_buttons)

        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window._advanced_filters == {"situacao": ["STE"]}
        assert self.window._advanced_filters_active is True
        assert all(button.isEnabled() is False for button in undo_buttons)

    def test_column_filter_buttons_flow(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        controls = self._get_column_filter_controls()
        if hasattr(self.window, "_expand_column_alias_for_filter"):
            emissor_label = self.window._expand_column_alias_for_filter("setor_emissor")
            executor_label = self.window._expand_column_alias_for_filter(
                "setor_executor"
            )
        else:
            emissor_label = self.window._resolve_column_display_name("setor_emissor")
            executor_label = self.window._resolve_column_display_name("setor_executor")
        assert emissor_label in controls
        assert executor_label in controls
        emissor_edit, emissor_apply, emissor_clear, emissor_hide = controls[
            emissor_label
        ]
        executor_edit, executor_apply, _, _ = controls[executor_label]
        assert emissor_clear.text() == "Limpar"
        assert "limpa o valor" in (emissor_clear.toolTip() or "").casefold()
        assert emissor_hide.text() == "Ocultar"
        assert (
            "somente quando o filtro da coluna estiver vazio"
            in (emissor_hide.toolTip() or "").casefold()
        )

        emissor_edit.setText("MEL3, MEL4")
        cast(Any, QTest).mouseClick(emissor_apply, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        # Armazenamento interno usa virgulas
        assert self.window._active_column_filters["setor_emissor"] == "MEL3, MEL4"
        assert self.window._active_column_filters["setor_executor"] == "MEL3, MEL4"

        # Ocultar deve ser bloqueado enquanto houver filtro ativo visivel
        emissor_edit.setText("")
        cast(Any, QTest).mouseClick(emissor_hide, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        controls_after = self._get_column_filter_controls()
        assert emissor_label in controls_after
        assert self.window._active_column_filters["setor_emissor"] == "MEL3, MEL4"
        assert self.window._active_column_filters["setor_executor"] == "MEL3, MEL4"
        assert "limpe o filtro" in str(self.window.status_label.text() or "").casefold()

        cast(Any, QTest).mouseClick(emissor_clear, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        cast(Any, QTest).mouseClick(emissor_hide, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        controls_after_hide = self._get_column_filter_controls()
        assert emissor_label not in controls_after_hide
        assert not str(
            self.window._active_column_filters.get("setor_emissor", "")
        ).strip()
        assert not str(
            self.window._active_column_filters.get("setor_executor", "")
        ).strip()

        executor_edit.setText("IEE3, MEL4")
        cast(Any, QTest).mouseClick(executor_apply, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert self.window._active_column_filters["setor_executor"] == "IEE3, MEL4"
        assert self.window._active_column_filters["setor_emissor"] == "IEE3, MEL4"

    def test_filter_cache_context_reflects_column_filters_exclude_and_clear(self):
        assert self.window._build_filter_cache_context() == ""

        self.window._active_column_filters["descricao_ssa"] = "Teste"
        first_context = self.window._build_filter_cache_context()
        assert '"descricao_ssa": "Teste"' in first_context
        assert '"exclude_ste_sca": false' in first_context

        self.window._on_exclude_ste_sca_toggled(True)
        second_context = self.window._build_filter_cache_context()
        assert second_context != first_context
        assert '"exclude_ste_sca": true' in second_context

        self.window._clear_all_filters_global()
        QApplication.processEvents()
        assert self.window._build_filter_cache_context() == ""

    def test_filters_summary_shows_exclude_ste_sca_as_active_restriction(self):
        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()

        summary_text = str(self.window.filters_summary_label.text() or "")

        assert "situacao!=SCA/SES/STE" in summary_text

    def test_column_filter_row_clear_button_clears_value_without_hiding_row(self):
        self.window._active_column_filters = {
            col: "" for col in self.window._column_filter_default_columns()
        }
        self.window._build_column_filters_panel()
        QApplication.processEvents()

        controls = self._get_column_filter_controls()
        label = (
            self.window._expand_column_alias_for_filter("descricao_ssa")
            if hasattr(self.window, "_expand_column_alias_for_filter")
            else self.window._resolve_column_display_name("descricao_ssa")
        )
        assert label in controls
        edit_widget, apply_btn, clear_btn, _hide_btn = controls[label]

        edit_widget.setText("Teste A")
        cast(Any, QTest).mouseClick(apply_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert self.window._active_column_filters["descricao_ssa"] == "Teste A"

        cast(Any, QTest).mouseClick(clear_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window._active_column_filters["descricao_ssa"] == ""
        controls_after = self._get_column_filter_controls()
        assert label in controls_after

    def test_data_cadastro_column_filter_accepts_display_date_on_first_apply(self):
        df = self.base_df.assign(
            data_cadastro=[
                "2025-01-01 08:00:00",
                "2025-01-02 09:00:00",
                "2025-01-02 10:00:00",
                "2025-03-01 11:00:00",
                "",
            ]
        ).copy()
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())

        self.window._activate_column_filter("data_cadastro")
        QApplication.processEvents()

        controls = self._get_column_filter_controls()
        label = (
            self.window._expand_column_alias_for_filter("data_cadastro")
            if hasattr(self.window, "_expand_column_alias_for_filter")
            else self.window._resolve_column_display_name("data_cadastro")
        )
        assert label in controls

        edit_widget, apply_btn, _clear_btn, _hide_btn = controls[label]
        edit_widget.setText("02/01/2025")
        cast(Any, QTest).mouseClick(apply_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window._active_column_filters["data_cadastro"] == "02/01/2025"
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == {2, 3}

    def test_data_cadastro_column_filter_negation_matches_display_date(self):
        df = self.base_df.assign(
            data_cadastro=[
                "2025-01-01 08:00:00",
                "2025-01-02 09:00:00",
                "2025-01-02 10:00:00",
                "2025-03-01 11:00:00",
                "",
            ]
        ).copy()
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())

        self.window._activate_column_filter("data_cadastro")
        QApplication.processEvents()

        controls = self._get_column_filter_controls()
        label = (
            self.window._expand_column_alias_for_filter("data_cadastro")
            if hasattr(self.window, "_expand_column_alias_for_filter")
            else self.window._resolve_column_display_name("data_cadastro")
        )
        assert label in controls

        edit_widget, apply_btn, _clear_btn, _hide_btn = controls[label]
        edit_widget.setText("!02/01/2025")
        cast(Any, QTest).mouseClick(apply_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window._active_column_filters["data_cadastro"] == "!02/01/2025"
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == {1, 4, 5}

    def test_build_column_mask_blocks_heavy_regex_patterns(self):
        series = pd.Series(["aaaaaaaaaaaa", "bbb"], dtype="string")
        mask = self.window._build_column_mask(series, "~(a+)+$")
        assert list(mask) == [False, False]

    def test_activate_column_filter_stores_undo_snapshot(self):
        self.window._last_filter_state = None
        self.window.search_input.setText("Marca")
        QApplication.processEvents()

        self.window._activate_column_filter("coluna_temporaria_teste")
        QApplication.processEvents()

        assert self.window._last_filter_state is not None
        snapshot = self.window._last_filter_state
        assert snapshot.get("search_text", "").strip() == "Marca"
        assert "coluna_temporaria_teste" not in (
            snapshot.get("active_column_filters") or {}
        )

    def test_deactivate_column_filter_stores_undo_snapshot(self):
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._last_filter_state = None
        QApplication.processEvents()

        self.window._deactivate_column_filter("descricao_ssa")
        QApplication.processEvents()

        assert self.window._last_filter_state is not None
        snapshot = self.window._last_filter_state
        assert (
            str(
                (snapshot.get("active_column_filters") or {}).get("descricao_ssa", "")
            ).strip()
            == "Teste A"
        )
        assert "descricao_ssa" not in self.window._active_column_filters

    @pytest.mark.skip(
        reason="exclude_ste_checkbox está oculto na UI atual; efeito funcional coberto por test_exclude_ste_sca_combined_with_or_group"
    )
    def test_exclude_checkbox_and_clear_filter_button(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        all_records = set(self._extract_visible_ssa())
        # Com o perfil aplicado na nova semântica, apenas 3 está visível antes do checkbox
        assert 3 in all_records

        cast(Any, QTest).mouseClick(
            self.window.exclude_ste_checkbox, Qt.MouseButton.LeftButton
        )
        QApplication.processEvents()
        remaining = set(self._extract_visible_ssa())
        assert 2 not in remaining and 3 not in remaining

        self.window.search_input.setText("Teste A, Teste D")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.search_input.text() == "Teste A, Teste D"

        assert self.window.clear_filter_button.isEnabled()
        self.window.clear_filter()
        QApplication.processEvents()
        assert self.window.search_input.text() == ""
        assert set(self._extract_visible_ssa()) == set(self.base_df["numero_ssa"])

    def test_persistent_filters_order(self):
        from unittest.mock import patch

        with patch("gui.gui_ssa.QMessageBox.information", return_value=None):
            self.window.persistent_filters = []
            self.window.search_input.setText("Zebra filtro")
            self.window.save_current_filter()
            self.window.search_input.setText("Alfa filtro")
            self.window.save_current_filter()

        names = [f["name"] for f in self.window.persistent_filters]
        assert names == sorted(names, key=lambda n: n.casefold())

    def test_advanced_filter_checks_survive_tab_switch(self):
        """Rebuild dos menus avançados deve persistir listas *_checks no tab_context."""
        self.window._adv_options_dirty = True
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        assert len(getattr(self.window, "adv_executor_checks", []) or []) > 0

        self.window.main_tabs.setCurrentIndex(0)
        QApplication.processEvents()
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        assert len(getattr(self.window, "adv_executor_checks", []) or []) > 0

    def test_refresh_advanced_options_does_not_eager_load_responsavel(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._advanced_filters = {
            "solicitante": ["User1", "User2"],
            "solicitante_exclude_values": ["User5"],
        }
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = None
        self.window._responsavel_filters_materialized = False
        self.window._responsavel_options_dirty = True

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True
        button = getattr(self.window, "adv_responsavel_solicitante_button", None)
        if button is None:
            button = getattr(self.window, "_adv_ctx", {}).get(
                "adv_responsavel_solicitante_button"
            )
        assert button is not None
        assert button.text().startswith(("Incluir:", "Diferente:"))

    def test_apply_advanced_filters_preserves_responsavel_when_not_materialized(self):
        self.window._advanced_filters = {
            "solicitante": ["User1"],
            "solicitante_exclude_values": ["User2"],
            "responsavel_programacao": ["ProgA"],
            "responsavel_programacao_exclude_values": ["ProgB"],
            "responsavel_execucao": ["ExecA"],
            "responsavel_execucao_exclude_values": ["ExecB"],
        }
        self.window._responsavel_materialized_prefixes = set()
        self.window._responsavel_filters_materialized = False

        self.window._apply_advanced_filters_from_ui(store_only=True)

        assert self.window._advanced_filters["solicitante"] == ["User1"]
        assert self.window._advanced_filters["solicitante_exclude_values"] == ["User2"]
        assert self.window._advanced_filters["responsavel_programacao"] == ["ProgA"]
        assert self.window._advanced_filters[
            "responsavel_programacao_exclude_values"
        ] == ["ProgB"]
        assert self.window._advanced_filters["responsavel_execucao"] == ["ExecA"]
        assert self.window._advanced_filters["responsavel_execucao_exclude_values"] == [
            "ExecB"
        ]
        assert "responsavel_emissor" not in self.window._advanced_filters
        assert "responsavel_emissor_exclude_values" not in self.window._advanced_filters

    def test_responsavel_emissor_controls_are_not_present_in_advanced_panel(self):
        assert getattr(self.window, "adv_responsavel_emissor_button", None) is None
        assert getattr(self.window, "adv_responsavel_emissor_menu", None) is None
        assert getattr(self.window, "adv_responsavel_emissor_checks", None) is None
        assert getattr(self.window, "adv_responsavel_emissor_exclude", None) is None

    def test_ensure_responsavel_options_materialized_runs_once_when_dirty(self):
        self.window._responsavel_filters_materialized = False
        self.window._responsavel_options_dirty = True

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self.window._ensure_responsavel_options_materialized()
            self.window._ensure_responsavel_options_materialized()

        assert refresh_mock.call_count == 1
        assert self.window._responsavel_filters_materialized is True
        assert self.window._responsavel_options_dirty is False

    def test_switch_to_filters_tab_does_not_materialize_responsavel_eagerly(self):
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = None
        self.window._responsavel_filters_materialized = False
        self.window._responsavel_options_dirty = True

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            filter_tab_idx = next(
                idx
                for idx, ctx in enumerate(self.window._tab_contexts)
                if ctx.get("tab_kind") == "filters"
            )
            self.window.main_tabs.setCurrentIndex(filter_tab_idx)
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True

    def test_switch_to_filters_tab_does_not_reapply_same_theme(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "main"
        )

        with patch.object(
            self.window, "apply_theme", wraps=self.window.apply_theme
        ) as apply_mock:
            self.window.main_tabs.setCurrentIndex(filter_tab_idx)
            QApplication.processEvents()
            # Switch away and back: after the first bind, the same theme should not be re-applied.
            self.window.main_tabs.setCurrentIndex(main_tab_idx)
            QApplication.processEvents()
            self.window.main_tabs.setCurrentIndex(filter_tab_idx)
            QApplication.processEvents()

        assert apply_mock.call_count == 1

    def test_filters_tab_switch_and_responsavel_materialization_smoke_latency(self):
        heavy_df = self._build_heavy_filters_df(rows=1200)
        self.window._active_data_load_request_id = 33
        self.window.on_data_loaded(heavy_df, request_id=33)
        QApplication.processEvents()

        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )

        t0 = time.perf_counter()
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()
        switch_ms = (time.perf_counter() - t0) * 1000.0

        assert self.window._responsavel_filters_materialized is False
        assert switch_ms < 3000.0

        target_prefix = "adv_responsavel_solicitante"
        t1 = time.perf_counter()
        self.window._ensure_responsavel_options_materialized(
            target_prefix=target_prefix
        )
        QApplication.processEvents()
        materialize_ms = (time.perf_counter() - t1) * 1000.0

        assert target_prefix in getattr(
            self.window, "_responsavel_materialized_prefixes", set()
        )
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True
        assert materialize_ms < 5000.0

    def test_theme_cycle_smoke_latency_on_filters_tab(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        current_theme = getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        other_theme = "windows7" if current_theme != "windows7" else "gruvbox"

        t0 = time.perf_counter()
        self.window.apply_theme(current_theme)
        QApplication.processEvents()
        same_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        self.window.apply_theme(other_theme)
        QApplication.processEvents()
        other_ms = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        self.window.apply_theme(current_theme)
        QApplication.processEvents()
        back_ms = (time.perf_counter() - t2) * 1000.0

        assert same_ms < 4000.0
        assert other_ms < 4000.0
        assert back_ms < 4000.0

    def test_apply_theme_reuses_cached_details_font_when_base_size_unchanged(self):
        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        first_font = getattr(self.window, "_details_text_small_font_cached", None)
        first_size = getattr(self.window, "_details_text_small_font_base_size", None)
        assert first_font is not None
        assert isinstance(first_size, (int, float))

        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        second_font = getattr(self.window, "_details_text_small_font_cached", None)
        second_size = getattr(self.window, "_details_text_small_font_base_size", None)
        assert second_font is first_font
        assert second_size == first_size

    def test_apply_theme_rebuilds_cached_details_font_when_base_font_changes(self):
        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        first_font = getattr(self.window, "_details_text_small_font_cached", None)
        assert first_font is not None

        base_font = self.window.details_group.font()
        base_font.setFamily("Courier New")
        base_font.setWeight(QFont.Weight.Black)
        self.window.details_group.setFont(base_font)

        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        second_font = getattr(self.window, "_details_text_small_font_cached", None)
        assert second_font is not None
        assert second_font is not first_font

    def test_apply_theme_skips_global_qss_rebuild_when_cached_theme_matches(self):
        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        assert getattr(self.window, "_last_global_theme_name", None) == "gruvbox"
        assert isinstance(getattr(self.window, "_last_global_theme_qss", None), str)
        self.window._current_theme = ""

        with patch("gui.helpers.build_global_widget_qss") as build_qss_mock:
            self.window.apply_theme("gruvbox")
            QApplication.processEvents()

        assert build_qss_mock.call_count == 0

    def test_repeated_filters_tab_and_theme_actions_keep_state_consistent(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "main"
        )
        current_theme = getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        other_theme = "windows7" if current_theme != "windows7" else "gruvbox"

        for i in range(5):
            self.window.main_tabs.setCurrentIndex(filter_tab_idx)
            QApplication.processEvents()
            if i % 2 == 0:
                self.window.apply_theme(other_theme)
            else:
                self.window.apply_theme(current_theme)
            QApplication.processEvents()
            self.window.main_tabs.setCurrentIndex(main_tab_idx)
            QApplication.processEvents()

        self.window.apply_theme(current_theme)
        QApplication.processEvents()
        assert getattr(self.window, "_current_theme", None) == current_theme
        assert self.window.main_tabs.currentIndex() == main_tab_idx

    def test_theme_switch_reapplies_on_tab_bind_for_inactive_tab(self):
        """Theme updates must re-style both tabs, even when switched after the change."""
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "main"
        )
        filters_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "filters"
        )
        main_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "main"
        )

        current_theme = getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        other_theme = "windows7" if current_theme != "windows7" else "gruvbox"

        initial_main_css = main_ctx["search_input"].styleSheet() or ""
        assert initial_main_css
        assert not (filters_ctx["search_label"].styleSheet() or "")

        # Switching to the filters tab should re-apply the current theme to that tab's widgets.
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()
        assert "font-weight" in (filters_ctx["search_label"].styleSheet() or "")

        # Apply a different theme while on filters tab, then switch back to main.
        self.window.apply_theme(other_theme)
        QApplication.processEvents()
        self.window.main_tabs.setCurrentIndex(main_tab_idx)
        QApplication.processEvents()

        # The main tab widgets must get re-themed on bind (previously could keep stale QSS).
        assert getattr(self.window, "_current_theme", None) == other_theme
        assert (main_ctx["search_input"].styleSheet() or "") != initial_main_css

    def test_switch_to_filters_tab_cancels_pending_search_debounce(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])

        # Agenda um novo filtro via debounce, mas troca para a aba Filtros antes do timeout.
        self.window.search_input.setText("Teste A, Teste D")
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        cast(Any, QTest).qWait(int(self.window._debounce_timer.interval()) + 80)
        QApplication.processEvents()

        # O dataset nao pode ser resetado por disparo tardio no contexto da aba errada.
        assert Counter(self._extract_visible_ssa()) == Counter([1])
        for ctx in self.window._tab_contexts:
            assert ctx["search_input"].text().strip() == "Teste A, Teste D"

    def test_general_search_debounce_uses_minimum_interval(self):
        assert int(self.window._debounce_timer.interval()) >= 1400

    def test_clear_filter_on_filters_tab_clears_search_in_all_tabs(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        main_ctx = next(
            ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "main"
        )
        assert main_ctx["search_input"].text().strip() == "Teste A"

        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window.clear_filter()
        QApplication.processEvents()

        for ctx in self.window._tab_contexts:
            assert ctx["search_input"].text().strip() == ""
        assert self.window.clear_filter_button.isEnabled() is False

    def test_filters_summary_shows_global_filters_on_both_tabs(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        self.window._active_column_filters["descricao_ssa"] = "Teste"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        main_summary = str(self.window.filters_summary_label.text() or "")
        assert "Busca: 'Teste A'" in main_summary
        assert "Descricao da SSA: Teste" in main_summary

        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        filters_summary = str(self.window.filters_summary_label.text() or "")
        assert "Busca: 'Teste A'" in filters_summary
        assert "Descricao da SSA: Teste" in filters_summary

    def test_on_filter_finished_uses_pending_search_display_for_status(self):
        self.window._active_filter_request_id = 31
        self.window._active_filter_search_request_id = 31
        self.window._active_filter_search_display = "Teste A"
        self.window.search_input.setText("")
        filtered = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(filtered)
        QApplication.processEvents()

        assert "para 'Teste A'" in self.window.status_label.text()

    def test_apply_search_display_skips_update_when_any_live_widget_has_focus(self):
        class _BrokenWidget:
            def hasFocus(self):
                raise RuntimeError("deleted")

            def blockSignals(self, _value):
                return None

            def setText(self, _value):
                return None

        class _FocusedWidget:
            def __init__(self):
                self.text_value = "manter"

            def hasFocus(self):
                return True

            def blockSignals(self, _value):
                return None

            def setText(self, value):
                self.text_value = value

        focused = _FocusedWidget()
        self.window._pending_search_display = "Nao deve sobrescrever"
        self.window._get_live_search_inputs_snapshot = lambda: [
            _BrokenWidget(),
            focused,
        ]

        self.window._apply_search_display()

        assert focused.text_value == "manter"
        assert self.window._pending_search_display == "Nao deve sobrescrever"

    def test_resize_event_reorganizes_advanced_grid_on_filters_tab(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        captured_widths = []
        with patch.object(
            self.window,
            "_reorganize_advanced_filters_grid",
            side_effect=lambda width: captured_widths.append(width),
        ):
            event = QResizeEvent(QSize(1280, 800), QSize(1200, 760))
            self.window.resizeEvent(event)

        assert captured_widths
        assert captured_widths[0] >= 0

    def test_resize_event_coalesces_width_recompute_with_restartable_timer(self):
        self.window._last_window_width = 900
        self.window._data_revision = 17
        self.window.df_exibido = self.base_df.copy()
        calls: list[int | None] = []

        with patch.object(
            self.window,
            "_recompute_column_widths_on_resize",
            side_effect=lambda expected_revision=None: calls.append(expected_revision),
        ):
            self.window.resizeEvent(QResizeEvent(QSize(980, 700), QSize(900, 700)))
            self.window.resizeEvent(QResizeEvent(QSize(1020, 700), QSize(980, 700)))
            self.window.resizeEvent(QResizeEvent(QSize(1080, 700), QSize(1020, 700)))
            debounce_ms = int(
                getattr(self.window._resize_recompute_timer, "interval", lambda: 300)()
            )
            cast(Any, QTest).qWait(debounce_ms + 80)

        assert calls == [17]

    def test_apply_theme_updates_tab_stylesheet_in_normal_flow(self):
        self.window.main_tabs.setStyleSheet("")

        self.window.apply_theme("gruvbox")
        QApplication.processEvents()

        tab_css = self.window.main_tabs.styleSheet()
        assert "QTabWidget::pane" in tab_css
        assert "QTabBar::tab:selected" in tab_css

    def test_apply_theme_switches_central_background_block_by_theme_family(self):
        central = self.window.centralWidget()
        assert central is not None

        central.setStyleSheet("")
        self.window.apply_theme("gruvbox")
        QApplication.processEvents()
        assert "SSA_MAIN_BG_START" in (central.styleSheet() or "")

        self.window.apply_theme("windows7")
        QApplication.processEvents()
        assert "SSA_MAIN_BG_START" not in (central.styleSheet() or "")

    def test_details_html_hides_internal_columns(self):
        series = self.base_df.iloc[0].copy()
        series["_norm_ssa"] = "INTERNAL_SENTINEL_NORM"
        series["_debug_value"] = "INTERNAL_SENTINEL_DEBUG"

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=False
        )

        assert "_norm_ssa" not in html
        assert "_debug_value" not in html
        assert "INTERNAL_SENTINEL_NORM" not in html
        assert "INTERNAL_SENTINEL_DEBUG" not in html

    def test_details_html_breaks_priority_emissao_label_in_two_lines(self):
        series = self.base_df.iloc[0].copy()
        series["grau_prioridade_emissao"] = "ALTA"

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=False
        )

        assert "Grau de Prioridade<br/>(Emissao):" in html

    def test_details_text_disables_automatic_link_navigation(self):
        details_text = self.window.details_text
        assert details_text.openExternalLinks() is False
        assert details_text.openLinks() is False

    def test_details_html_renders_derivadas_relations_block(self):
        series = self.base_df.iloc[0].copy()
        with patch(
            "gui.ssa.gui_details._get_derivadas_relations_info",
            return_value={
                "has_data": True,
                "parents": ["9000"],
                "children": ["1001", "1002", "1003"],
                "descendants_count": 5,
            },
        ):
            html = self.window._format_details_html(
                series, highlight_search_terms=False, linkify=True
            )

        assert "Relacoes de Derivadas" in html
        assert "Mae direta" in html
        assert "Filhas diretas (3)" in html
        assert "Descendentes (5)" in html
        assert "Abrir arvore completa" in html
        assert "derivadas:tree" in html
        assert "ssa-details:9000" in html

    def test_details_anchor_derivadas_tree_opens_popup(self):
        self.window._details_current_ssa = "12.19.117.87"
        with patch("gui.ssa.gui_details._show_derivadas_tree_for_ssa") as popup_mock:
            self.window._on_details_anchor_clicked(QUrl("derivadas:tree"))
        popup_mock.assert_called_once()
        assert popup_mock.call_args.args[0] is self.window
        assert popup_mock.call_args.args[1] == "12.19.117.87"

    def test_details_anchor_ssa_details_opens_details_dialog(self):
        with patch("gui.ssa.gui_details._open_details_dialog_for_ssa") as open_mock:
            self.window._on_details_anchor_clicked(QUrl("ssa-details:202500777"))
        open_mock.assert_called_once()
        assert open_mock.call_args.args[0] is self.window
        assert open_mock.call_args.args[1] == "202500777"

    def test_normalize_ssa_value_handles_decimal_float_artifact(self):
        assert self.window._normalize_ssa_value("121911787.0") == "121911787"
        assert self.window._normalize_ssa_value(121911787.0) == "121911787"

    def test_get_series_for_ssa_uses_index_label_and_returns_correct_row(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["100", "200", "300"],
                "descricao_ssa": ["A", "B", "C"],
            },
            index=[5, 2, 7],
        )
        self.window.df_exibido = df.copy()
        self.window.df_completo = df.copy()

        series = ssa_gui_details._get_series_for_ssa(self.window, "200")

        assert series is not None
        assert str(series.get("numero_ssa")) == "200"
        assert str(series.get("descricao_ssa")) == "B"

    def test_update_details_from_selection_skips_rerender_for_same_signature(self):
        self.window.display_current_page(1)
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()

        initial_ssa = self.window._details_current_ssa
        initial_html = self.window.details_text.toHtml()

        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details_mock:
            self.window.update_details_from_selection()
            assert update_details_mock.call_count == 0

            self.window.search_input.setText("Teste A")
            self.window.update_details_from_selection()
            assert update_details_mock.call_count == 1

        assert self.window._details_current_ssa == initial_ssa
        assert self.window.details_text.toHtml() != ""
        assert self.window.details_text.toHtml() != initial_html

    def test_jump_to_ssa_updates_details_before_deferred_selection(self, monkeypatch):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])

        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.page_size = 100
        self.window.paginator.set_dataframe(df.copy())

        scheduled = {}
        select_calls = []
        original_select_row = self.window.table_widget.selectRow

        def fake_single_shot(delay, callback):
            scheduled["delay"] = delay
            scheduled["callback"] = callback

        def spy_select_row(row):
            select_calls.append(row)
            return original_select_row(row)

        monkeypatch.setattr(ssa_gui_details.QTimer, "singleShot", fake_single_shot)
        monkeypatch.setattr(self.window.table_widget, "selectRow", spy_select_row)
        with patch.object(
            ssa_gui_details,
            "_update_details_from_series",
            wraps=ssa_gui_details._update_details_from_series,
        ) as update_details_mock:
            self.window._jump_to_ssa(target_ssa)

            assert self.window._details_current_ssa == df.iloc[target_pos]["numero_ssa"]
            assert select_calls == []
            assert scheduled["delay"] == 0
            assert update_details_mock.call_count == 1

            scheduled["callback"]()
            QApplication.processEvents()

            assert select_calls == [57]
            assert update_details_mock.call_count == 1
            selected_rows = self.window.table_widget.selectionModel().selectedRows()
            assert [idx.row() for idx in selected_rows] == [57]

    def test_jump_to_ssa_shows_target_details_without_intermediate_page_details(
        self, monkeypatch
    ):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])
        page_first_desc = str(df.iloc[100]["descricao_ssa"])
        target_desc = str(df.iloc[target_pos]["descricao_ssa"])

        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.page_size = 100
        self.window.paginator.set_dataframe(df.copy())

        scheduled = {}

        def fake_single_shot(delay, callback):
            scheduled["delay"] = delay
            scheduled["callback"] = callback

        monkeypatch.setattr(ssa_gui_details.QTimer, "singleShot", fake_single_shot)

        self.window._jump_to_ssa(target_ssa)

        details_html = str(self.window.details_text.toHtml() or "")
        assert str(self.window._details_current_ssa) == str(
            df.iloc[target_pos]["numero_ssa"]
        )
        assert target_desc in details_html
        assert page_first_desc not in details_html
        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert scheduled["delay"] == 0

        scheduled["callback"]()
        QApplication.processEvents()

        selected_rows = self.window.table_widget.selectionModel().selectedRows()
        assert [idx.row() for idx in selected_rows] == [57]

    def test_jump_to_ssa_waits_for_async_filter_when_target_is_outside_current_view(
        self,
    ):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])

        self.window._sync_filtering = False
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.iloc[:50].copy().reset_index(drop=True)
        self.window._df_last_search_filtered = self.window.df_exibido.copy()
        self.window.paginator.page_size = 50
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())

        self.window._jump_to_ssa(target_ssa)

        deadline = time.time() + 5.0
        resolved = False
        while time.time() < deadline:
            QApplication.processEvents()
            selected_rows = self.window.table_widget.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                row_series = self.window._get_series_from_row(row)
                row_ssa = str(row_series.get("numero_ssa"))
                if (
                    str(getattr(self.window, "_details_current_ssa", "")) == target_ssa
                    and row_ssa == target_ssa
                ):
                    resolved = True
                    break
            time.sleep(0.01)

        assert resolved is True
        assert str(getattr(self.window, "_details_current_ssa", "")) == target_ssa
        assert self.window.search_input.text() == f"={target_ssa}"
        assert getattr(self.window, "_pending_jump_to_ssa", None) is None

    def test_header_resize_updates_runtime_column_width_cache(self):
        self.window._current_display_columns = ["#", "descricao_ssa"]
        self.window._saved_gui_column_widths = {}
        self.window._gui_column_pixel_widths = {}

        self.window._on_header_section_resized(1, 100, 222)

        assert self.window._saved_gui_column_widths.get("descricao_ssa") == 222
        assert self.window._gui_column_pixel_widths.get("descricao_ssa") == 222

    def test_header_context_menu_apply_stores_undo_snapshot(self, monkeypatch):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def emit(self):
                for callback in list(self._callbacks):
                    callback()

        class _FakeAction:
            def __init__(self, text, _parent=None):
                self.text = text
                self.triggered = _FakeSignal()

        class _FakeMenu:
            def __init__(self, _parent=None):
                self._actions = []

            def addAction(self, action):
                self._actions.append(action)
                return action

            def exec(self, _global_pos):
                for action in self._actions:
                    if str(getattr(action, "text", "")).startswith("Filtrar "):
                        action.triggered.emit()
                        return action
                return None

        self.window._last_filter_state = None
        self.window._active_column_filters["situacao"] = ""
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)

        header = self.window.table_widget.horizontalHeader()
        logical_index = 2  # "#"(0), numero_ssa(1), situacao(2)
        pos = QPoint(header.sectionPosition(logical_index) + 2, 5)

        captured = {}

        def _fake_prompt(full_name, initial_value=""):
            captured["full_name"] = full_name
            captured["initial_value"] = initial_value
            return "STE"

        monkeypatch.setattr(self.window, "_prompt_column_filter_term", _fake_prompt)
        self.window.show_header_context_menu(pos)
        QApplication.processEvents()

        assert self.window._active_column_filters["situacao"] == "STE"
        assert self.window._last_filter_state is not None
        assert captured["full_name"] == "Situacao"
        assert captured["initial_value"] == ""
        snapshot_filters = (
            self.window._last_filter_state.get("active_column_filters") or {}
        )
        assert str(snapshot_filters.get("situacao", "")).strip() == ""

    def test_header_context_menu_exposes_best_fit_visible_action(self, monkeypatch):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def emit(self):
                for callback in list(self._callbacks):
                    callback()

        class _FakeAction:
            def __init__(self, text, _parent=None):
                self.text = text
                self.triggered = _FakeSignal()

        class _FakeMenu:
            def __init__(self, _parent=None):
                self._actions = []

            def addAction(self, action):
                self._actions.append(action)
                return action

            def exec(self, _global_pos):
                for action in self._actions:
                    if str(getattr(action, "text", "")).startswith(
                        "Best fit colunas visiveis"
                    ):
                        action.triggered.emit()
                        return action
                return None

        calls = {"count": 0}
        monkeypatch.setattr(
            self.window,
            "best_fit_visible_columns",
            lambda: calls.__setitem__("count", calls["count"] + 1),
        )
        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)

        self.window.display_current_page(1)
        QApplication.processEvents()

        header = self.window.table_widget.horizontalHeader()
        logical_index = 1  # "#"(0), "numero_ssa"(1)
        pos = QPoint(header.sectionPosition(logical_index) + 2, 5)
        self.window.show_header_context_menu(pos)

        assert calls["count"] == 1

    def test_header_context_menu_exposes_show_all_columns_by_affinity_action(
        self, monkeypatch
    ):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def emit(self):
                for callback in list(self._callbacks):
                    callback()

        class _FakeAction:
            def __init__(self, text, _parent=None):
                self.text = text
                self.triggered = _FakeSignal()

        class _FakeMenu:
            def __init__(self, _parent=None):
                self._actions = []

            def addAction(self, action):
                self._actions.append(action)
                return action

            def exec(self, _global_pos):
                for action in self._actions:
                    if str(getattr(action, "text", "")).startswith(
                        "Exibir todas colunas (afinidade)"
                    ):
                        action.triggered.emit()
                        return action
                return None

        calls = {"count": 0}
        monkeypatch.setattr(
            self.window,
            "_show_all_columns_by_affinity",
            lambda: calls.__setitem__("count", calls["count"] + 1),
        )
        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)

        self.window.display_current_page(1)
        QApplication.processEvents()

        header = self.window.table_widget.horizontalHeader()
        logical_index = 1
        pos = QPoint(header.sectionPosition(logical_index) + 2, 5)
        self.window.show_header_context_menu(pos)

        assert calls["count"] == 1

    def test_column_filter_dialog_shows_hint_and_minimum_width(self):
        dialog = ColumnFilterDialog(
            "Solicitante",
            "ABC",
            hint_text="Aceita termo, !termo para exclusao",
            min_width=420,
        )

        labels = [label.text() for label in dialog.findChildren(QLabel)]
        assert "Termo para 'Solicitante'" in labels
        assert "Aceita termo, !termo para exclusao" in labels
        assert dialog.minimumWidth() >= 420

    def test_show_all_columns_by_affinity_reorders_same_select_all_set(
        self, monkeypatch
    ):
        source = ["data_programacao", "descricao_execucao", "numero_ssa"]
        captured = {}
        monkeypatch.setattr(
            self.window, "_get_select_all_columns_from_selector", lambda: source.copy()
        )
        monkeypatch.setattr(
            self.window,
            "on_columns_changed",
            lambda cols: captured.setdefault("cols", cols),
        )

        self.window._show_all_columns_by_affinity()

        assert set(captured["cols"]) == set(source)
        assert captured["cols"] == [
            "numero_ssa",
            "data_programacao",
            "descricao_execucao",
        ]

    def test_on_header_clicked_preserves_column_widths_after_sort(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert "descricao_ssa" in self.window._current_display_columns
        descricao_index = self.window._current_display_columns.index("descricao_ssa")
        sort_index = self.window._current_display_columns.index("numero_ssa")

        self.window.table_widget.setColumnWidth(descricao_index, 333)
        self.window._saved_gui_column_widths["descricao_ssa"] = 333
        self.window._gui_column_pixel_widths["descricao_ssa"] = 333
        QApplication.processEvents()

        self.window.on_header_clicked(sort_index)
        QApplication.processEvents()

        assert self.window.table_widget.columnWidth(descricao_index) == 333

    def test_best_fit_width_guard_ignores_single_extreme_outlier(self):
        expanded_df = pd.concat(
            [self.base_df.copy() for _ in range(20)], ignore_index=True
        )
        expanded_df["descricao_ssa"] = ["Texto curto"] * len(expanded_df)

        self.window.df_completo = expanded_df.copy()
        self.window.df_exibido = expanded_df.copy()
        self.window._df_last_search_filtered = expanded_df.copy()
        self.window.paginator.set_dataframe(expanded_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()
        col_idx = self.window._current_display_columns.index("descricao_ssa")
        base_width = self.window._compute_best_fit_width_for_column(col_idx)
        assert base_width is not None

        with_outlier = expanded_df.copy()
        with_outlier.loc[len(with_outlier) - 1, "descricao_ssa"] = "X" * 5000
        self.window.df_completo = with_outlier.copy()
        self.window.df_exibido = with_outlier.copy()
        self.window._df_last_search_filtered = with_outlier.copy()
        self.window.paginator.set_dataframe(with_outlier.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()
        guarded_width = self.window._compute_best_fit_width_for_column(col_idx)
        assert guarded_width is not None

        assert guarded_width <= base_width + 40

    def test_best_fit_width_respects_predefined_max_for_long_columns(self):
        series = pd.Series(["X" * 4000] * 50)

        def _measure(value):
            return len(str(value)) * 7

        width = self.window.width_manager.compute_best_fit_width(
            series=series,
            header_text="Descricao da SSA",
            col_name="descricao_ssa",
            measure_text=_measure,
            baseline_px=None,
            sample_limit=200,
        )
        assert width <= self.window.width_manager.max_pixel_widths["descricao_ssa"]

    def test_compute_optimal_widths_keeps_hash_column_minimum_24(self):
        df = pd.DataFrame({"#": [1], "numero_ssa": ["202500001"]})
        widths = self.window.width_manager.compute_optimal_widths(
            df=df,
            available_width=220,
            column_order=["#", "numero_ssa"],
        )
        assert int(widths.get("#", 0)) == 24

    def test_table_header_uses_merged_default_alias_for_extra_column(self, monkeypatch):
        reduced_map = {"numero_ssa": "Numero SSA", "situacao": "Situacao"}
        monkeypatch.setattr(self.window, "display_map", reduced_map.copy())
        monkeypatch.setattr(self.window, "internal_to_display", reduced_map.copy())

        merged = gui_ssa.load_display_mappings()
        self.window.display_map = merged
        self.window.internal_to_display = dict(merged)

        df = self.base_df.assign(
            situacao_reprogramacao=["(SPG)"] * len(self.base_df)
        ).copy()
        if "situacao_reprogramacao" not in self.window.visible_columns:
            self.window.visible_columns.append("situacao_reprogramacao")
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        col_idx = self.window._current_display_columns.index("situacao_reprogramacao")
        header_item = self.window.table_widget.horizontalHeaderItem(col_idx)
        assert header_item is not None
        header_text = header_item.text()
        assert "situacao_reprogramacao" not in header_text.casefold()
        assert (
            "reprog" in header_text.casefold() or "reprogram" in header_text.casefold()
        )

    def test_flush_column_width_preferences_persists_changed_values(self, monkeypatch):
        self.window._saved_gui_column_widths = {"descricao_ssa": 222}
        calls = {"persist": 0}

        def _fake_persist():
            calls["persist"] += 1
            return True

        monkeypatch.setattr(self.window, "_persist_gui_preferences", _fake_persist)
        old_column_widths = dict(gui_ssa.GUI_MAIN_PREFERENCES.get("column_widths", {}))
        try:
            ssa_gui_table._flush_column_width_preferences(self.window)
            assert (
                gui_ssa.GUI_MAIN_PREFERENCES.get("column_widths", {}).get(
                    "descricao_ssa"
                )
                == 222
            )
            assert calls["persist"] == 1
        finally:
            gui_ssa.GUI_MAIN_PREFERENCES["column_widths"] = old_column_widths

    def test_build_derivadas_tree_html_uses_spaced_header_layout(self):
        with patch(
            "gui.ssa.gui_details._collect_derivadas_tree_data",
            return_value={
                "target": "202602147",
                "parents": ["202500111"],
                "children": [],
                "descendants": [],
                "ancestors": [],
                "direct_children_count": 0,
                "descendants_count": 0,
            },
        ):
            html = ssa_gui_details._build_derivadas_tree_html(self.window, "202602147")

        assert "Lista de derivadas:" in html
        assert '<b><a href="ssa-panel:202602147"' in html
        assert "SSA originaria" in html
        assert "SSA originaria:" not in html
        assert "202500111" in html
        assert "num0" not in html
        assert "SSAs derivadas diretas (0)" in html
        assert "SSAs derivadas de derivadas (0)" in html

    def test_exclude_toggle_syncs_checkbox_state_across_tabs(self):
        """Toggle programático deve manter estado interno e checkboxes em sincronia."""
        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()
        assert self.window._exclude_ste_sca is True
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                assert checkbox.isChecked() is True

        self.window._on_exclude_ste_sca_toggled(False)
        QApplication.processEvents()
        assert self.window._exclude_ste_sca is False
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                assert checkbox.isChecked() is False

    def test_clear_all_filters_global_resets_exclude_and_advanced_filters(self):
        self.window._exclude_ste_sca = True
        self.window._advanced_filters = {
            "situacao": ["STE"],
            "setor_executor": ["IEE3"],
        }
        self.window._advanced_filters_active = True
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                checkbox.setChecked(True)

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._exclude_ste_sca is False
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                assert checkbox.isChecked() is False
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_all_filters_global_resets_full_filter_state_matrix(self):
        self.window.search_input.setText("Teste A")
        self.window._active_column_filters["descricao_ssa"] = "Teste"
        self.window._on_exclude_ste_sca_toggled(True)
        self.window._advanced_filters = {"situacao": ["STE"]}
        self.window._advanced_filters_active = True
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        for ctx in self.window._tab_contexts:
            assert ctx["search_input"].text().strip() == ""
        assert all(
            not str(v).strip() for v in self.window._active_column_filters.values()
        )
        assert self.window._exclude_ste_sca is False
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_all_filters_global_restores_default_column_filter_keys(self):
        self.window._active_column_filters = {
            "situacao": "STE",
            "numero_ssa": "2026",
            "descricao_ssa": "Teste",
        }
        self.window._clear_all_filters_global()
        QApplication.processEvents()

        default_cols = self.window._column_filter_default_columns()
        assert tuple(self.window._active_column_filters.keys()) == default_cols
        assert not any(
            str(v).strip() for v in self.window._active_column_filters.values()
        )

    def test_clear_all_filters_global_resets_or_group_metadata(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        assert len(self.window._column_or_groups) >= 1
        assert len(self.window._column_to_or_group) >= 1

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._column_or_groups == []
        assert self.window._column_to_or_group == {}
        summary_text = str(self.window.filters_summary_label.text() or "").casefold()
        assert "executor ou emissor (ou)" not in summary_text

    def test_clear_all_filters_global_does_not_reapply_profile_on_selector_rebind(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        filtered_before_clear = Counter(self._extract_visible_ssa())

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        cleared_once = Counter(self._extract_visible_ssa())
        assert cleared_once == Counter([1, 2, 3, 4, 5])
        assert filtered_before_clear != cleared_once

        self.window._sync_bind_profile_selector()
        QApplication.processEvents()

        cleared_after_rebind = Counter(self._extract_visible_ssa())
        assert cleared_after_rebind == Counter([1, 2, 3, 4, 5])
        assert self.window.df_exibido.equals(self.base_df)

    def test_hard_reset_filters_state_resets_visual_and_internal_filter_state(self):
        self.window.search_input.setText("Teste A")
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._hidden_column_filter_lines = {"setor_executor"}
        self.window._register_or_group(
            ["setor_executor", "setor_emissor"], ["IEE3", "MEL4"]
        )
        self.window._dedicated_or_text = "IEE3, MEL4"
        self.window._advanced_filters = {"situacao": ["STE"]}
        self.window._advanced_filters_active = True
        self.window._exclude_ste_sca = True
        self.window.current_filter_profile = "perfil_teste"
        self.window._profile_base_filters = {"situacao": "STE"}
        self.window._last_filter_state = {"dummy": True}
        self.window._build_column_filters_panel()
        QApplication.processEvents()

        self.window._hard_reset_filters_state()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert (
            tuple(self.window._active_column_filters.keys())
            == self.window._column_filter_default_columns()
        )
        assert not any(
            str(v).strip() for v in self.window._active_column_filters.values()
        )
        assert self.window._hidden_column_filter_lines == set()
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert self.window._exclude_ste_sca is False
        assert self.window._last_filter_state is None
        assert self.window.current_filter_profile is None
        assert self.window._profile_base_filters == {}
        assert self.window._dedicated_or_text == ""
        assert (
            str(self.window.filters_summary_label.text() or "") == "Nenhum filtro ativo"
        )
        assert (
            "resetados completamente"
            in str(self.window.status_label.text() or "").casefold()
        )
        for ctx in self.window._tab_contexts:
            if not isinstance(ctx, dict):
                continue
            assert ctx["search_input"].text() == ""
            selector = ctx.get("profile_selector")
            if selector is not None:
                assert selector.currentIndex() == 0

    def test_build_derivadas_tree_normalizes_and_ignores_invalid_values(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["SSA-101", "102", "102", "103", "104", "", None],
                "derivada_de": ["100", "100", "100", "None", "nan", "100", "100"],
            }
        )

        mae_filhas, filha_mae = self.window._build_derivadas_tree(
            df, "numero_ssa", "derivada_de"
        )

        assert mae_filhas == {"100": ["101", "102"]}
        assert filha_mae == {"101": "100", "102": "100"}

    @pytest.mark.parametrize(
        ("numero_ssa_values", "derivada_de_values"),
        [
            (["1", "2", "3"], ["None", "nan", "   "]),
            (["1001", "1002"], ["", "None"]),
        ],
    )
    def test_update_derivadas_button_state_is_noop_without_specific_button(
        self, numero_ssa_values, derivada_de_values
    ):
        self.window._df_last_search_filtered = pd.DataFrame(
            {
                "numero_ssa": numero_ssa_values,
                "derivada_de": derivada_de_values,
            }
        )
        self.window._update_derivadas_button_state()
        assert "adv_derivadas_especificas_button" not in self.window._adv_ctx

    def test_update_derivadas_from_sources_runs_db_then_special_sync(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")
        special_a = str(
            tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0124PM.xlsx"
        )
        special_b = str(
            tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0137PM.xlsx"
        )

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(
            self.window,
            "_list_special_derivadas_sheets",
            lambda: [special_a, special_b],
        )

        sync_calls = []

        def _fake_sync(**kwargs):
            sync_calls.append(kwargs)
            current_files = list(kwargs.get("sheet_files") or [])
            return {
                "sheet_files": current_files,
                "sheet_file_reports": [
                    {
                        "sheet_file": current_file,
                        "has_parse_evidence": True,
                        "stats": {"accepted_edges": 2, "special_layout_detected": 1},
                    }
                    for current_file in current_files
                ],
                "merge_stats": {"merged_edges": 11},
                "db_stats": {"accepted_edges": 7},
                "sheet_stats": {"accepted_edges": 4},
            }

        monkeypatch.setattr(gui_ssa, "sync_derivadas", _fake_sync)
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": True,
                "issue_counts": {},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert len(sync_calls) == 2
        assert sync_calls[0]["include_db_source"] is True
        assert sync_calls[0]["actor"] == "gui-derivadas-db-phase"
        assert "sheet_files" not in sync_calls[0]
        assert sync_calls[1]["include_db_source"] is False
        assert sync_calls[1]["actor"] == "gui-derivadas-sheet-phase"
        assert sync_calls[1]["sheet_files"] == [special_a, special_b]
        assert self.window.update_derivadas_button.text() == "Atualizar Derivadas"
        assert "Derivadas atualizadas" in self.window.status_label.text()

    def test_update_derivadas_from_sources_runs_only_db_when_no_special_sheets(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [])

        sync_calls = []

        def _fake_sync(**kwargs):
            sync_calls.append(kwargs)
            return {
                "merge_stats": {"merged_edges": 5},
                "db_stats": {"accepted_edges": 5},
                "sheet_stats": {"accepted_edges": 0},
            }

        monkeypatch.setattr(gui_ssa, "sync_derivadas", _fake_sync)
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": True,
                "issue_counts": {},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert len(sync_calls) == 1
        assert sync_calls[0]["include_db_source"] is True
        assert sync_calls[0]["actor"] == "gui-derivadas-db-phase"
        assert "sheet_files" not in sync_calls[0]

    def test_update_derivadas_from_sources_preserves_progress_bar_visibility_when_hidden(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [])
        monkeypatch.setattr(
            gui_ssa,
            "sync_derivadas",
            lambda **kwargs: {
                "merge_stats": {"merged_edges": 3},
                "db_stats": {"accepted_edges": 3},
                "sheet_stats": {"accepted_edges": 0},
            },
        )
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": True,
                "issue_counts": {},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.progress_bar.setVisible(False)
        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert self.window.progress_bar.isVisible() is False

    def test_update_derivadas_from_sources_raises_on_inconsistent_scan(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [])
        monkeypatch.setattr(
            gui_ssa,
            "sync_derivadas",
            lambda **kwargs: {
                "merge_stats": {"merged_edges": 5},
                "db_stats": {"accepted_edges": 5},
                "sheet_stats": {"accepted_edges": 0},
            },
        )
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": False,
                "issue_counts": {"flag_mismatch_pairs": 1},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert "Falha ao atualizar derivadas" in self.window.status_label.text()

    def test_update_derivadas_from_sources_fails_when_special_sheet_has_no_individual_evidence(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")
        special_file = str(
            tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx"
        )

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(
            self.window, "_list_special_derivadas_sheets", lambda: [special_file]
        )

        def _fake_sync(**kwargs):
            if kwargs.get("include_db_source"):
                return {
                    "merge_stats": {"merged_edges": 5},
                    "db_stats": {"accepted_edges": 5},
                    "sheet_stats": {"accepted_edges": 0},
                }
            return {
                "sheet_files": [special_file],
                "sheet_stats": {"accepted_edges": 1, "special_layout_detected": 1},
                "sheet_file_reports": [
                    {
                        "sheet_file": special_file,
                        "has_parse_evidence": False,
                        "stats": {"accepted_edges": 0, "special_layout_detected": 0},
                    }
                ],
                "merge_stats": {"merged_edges": 5},
                "db_stats": {"accepted_edges": 5},
            }

        monkeypatch.setattr(gui_ssa, "sync_derivadas", _fake_sync)
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": True,
                "issue_counts": {},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert "Falha ao atualizar derivadas" in self.window.status_label.text()

    def test_update_derivadas_from_sources_async_path_delivers_result_and_resets_flags(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setattr(
            self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table"
        )
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [])
        monkeypatch.setattr(
            gui_ssa,
            "sync_derivadas",
            lambda **kwargs: {
                "merge_stats": {"merged_edges": 3},
                "db_stats": {"accepted_edges": 3},
                "sheet_stats": {"accepted_edges": 0},
            },
        )
        monkeypatch.setattr(
            gui_ssa,
            "scan_derivadas_consistency",
            lambda **kwargs: {
                "schema_ready": True,
                "is_consistent": True,
                "issue_counts": {},
            },
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        class _ImmediateTimer:
            @staticmethod
            def singleShot(_msec, callback):
                callback()

        class _InlineThread:
            def __init__(self, target=None, daemon=None, **_kwargs):
                self._target = target
                self.daemon = daemon

            def start(self):
                if self._target is not None:
                    self._target()

        monkeypatch.setattr(gui_ssa, "QTimer", _ImmediateTimer)
        monkeypatch.setattr(gui_ssa.threading, "Thread", _InlineThread)

        result = self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert result["ok"] is True
        assert result["started"] is True
        assert self.window._derivadas_sync_running is False
        assert self.window._derivadas_sync_thread is None
        assert "Derivadas atualizadas" in self.window.status_label.text()

    def test_resolve_derivadas_table_name_requires_schema_compatibility(self, tmp_path):
        db_file = tmp_path / "resolver.db"
        conn = sqlite3.connect(db_file)
        try:
            conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
            conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT, derivada_de TEXT)")
            conn.commit()
        finally:
            conn.close()

        resolved = self.window._resolve_derivadas_table_name(str(db_file))
        assert resolved == "ssa_table"

    def test_reorganize_advanced_filters_grid_handles_removed_emissor_responsavel_widget(
        self,
    ):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(1501)
        self.window._reorganize_advanced_filters_grid(1201)
        self.window._reorganize_advanced_filters_grid(800)
        assert self.window._adv_filters_main_grid.count() > 0

    def test_reorganize_advanced_filters_grid_allows_narrow_valid_width(self):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(90)
        assert self.window._adv_filters_layout_mode == "cols_4"

        grid = self.window._adv_filters_main_grid
        widgets = self.window._adv_filters_grid_widgets
        exec_resp_item = grid.itemAtPosition(3, 2)
        assert exec_resp_item is not None
        assert exec_resp_item.widget() is widgets["exec_resp_box"]

    def test_reorganize_advanced_filters_grid_ignores_non_positive_width_and_recomputes(
        self,
    ):
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(1501)
        assert str(self.window._adv_filters_layout_mode).startswith("cols_")
        previous_mode = self.window._adv_filters_layout_mode

        self.window._reorganize_advanced_filters_grid(0)
        assert self.window._adv_filters_layout_mode == previous_mode

        self.window._reorganize_advanced_filters_grid(800)
        assert self.window._adv_filters_layout_mode == "cols_4"

    def test_reprogramacoes_menu_builds_without_responsavel_materialized(self):
        self.window.df_completo = self.base_df.assign(
            num_reprogramacoes=[0, 1, 2, 2, 3]
        ).copy()
        self.window._adv_values_cache = {}
        self.window._responsavel_materialized_prefixes = set()
        self.window._advanced_filters = {
            "num_reprogramacoes_mode": "eq",
            "num_reprogramacoes_values": ["2"],
        }

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        checks = getattr(self.window, "adv_reprog_checks", [])
        assert checks, (
            "reprogramacoes checks should be materialized even before responsavel filters"
        )
        selected = self.window._get_checked_values(checks)
        assert "2" in selected

    def test_refresh_advanced_filter_options_excludes_na_literal_from_sector_values(
        self,
    ):
        nullable_df = self.base_df.assign(
            setor_executor=pd.Series(
                [pd.NA, "MEL4", "IEE3", "", "XYZ"], dtype="string"
            ),
            setor_emissor=pd.Series([pd.NA, "MEL4", "", "MEL3", "XYZ"], dtype="string"),
        ).copy()
        self.window.df_completo = nullable_df.copy()
        self.window.df_exibido = nullable_df.copy()
        self.window._df_last_search_filtered = nullable_df.copy()
        self.window.paginator.set_dataframe(nullable_df.copy())
        self.window._adv_values_cache = None
        self.window._advanced_filters = {"setor_executor": ["MEL4"]}
        filter_tab_idx = next(
            idx
            for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        executor_labels = [
            str(check.property("value") or "")
            for check in (getattr(self.window, "adv_executor_checks", []) or [])
        ]
        emissor_labels = [
            str(check.property("value") or "")
            for check in (getattr(self.window, "adv_emissor_checks", []) or [])
        ]
        assert "<NA>" not in executor_labels
        assert "<NA>" not in emissor_labels
        assert "MEL4" in executor_labels

    def test_on_header_clicked_sorts_num_reprogramacoes_mixed_types(self):
        mixed_df = self.base_df.assign(
            num_reprogramacoes=pd.Series(
                [2, "Reprogramacao #1", 0, "", None], dtype="object"
            )
        ).copy()
        if "num_reprogramacoes" not in self.window.visible_columns:
            self.window.visible_columns.append("num_reprogramacoes")
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window._df_last_search_filtered = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("num_reprogramacoes")

        self.window.on_header_clicked(logical_index)
        asc_vals = self.window.df_exibido["num_reprogramacoes"].tolist()
        assert asc_vals[:3] == [0, "Reprogramacao #1", 2]
        assert asc_vals[-2:] == ["", None]

        self.window.on_header_clicked(logical_index)
        desc_vals = self.window.df_exibido["num_reprogramacoes"].tolist()
        assert desc_vals[:3] == [2, "Reprogramacao #1", 0]
        assert desc_vals[-2:] == ["", None]

    def test_on_header_clicked_reuses_num_reprogramacoes_sort_cache(self):
        mixed_df = self.base_df.assign(
            num_reprogramacoes=pd.Series(
                [2, "Reprogramacao #1", 0, "", None], dtype="object"
            )
        ).copy()
        if "num_reprogramacoes" not in self.window.visible_columns:
            self.window.visible_columns.append("num_reprogramacoes")
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window._df_last_search_filtered = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("num_reprogramacoes")

        self.window.on_header_clicked(logical_index)
        cache_after_first = dict(self.window._num_reprog_sort_cache)
        assert isinstance(cache_after_first["keys_df"], pd.DataFrame)
        assert cache_after_first["keys_df"].index.equals(self.window.df_exibido.index)
        assert int(cache_after_first["source_len"]) == len(
            cache_after_first["keys_df"].index
        )

        self.window.on_header_clicked(logical_index)
        cache_after_second = dict(self.window._num_reprog_sort_cache)
        assert isinstance(cache_after_second["keys_df"], pd.DataFrame)
        assert cache_after_second["keys_df"].index.equals(self.window.df_exibido.index)
        assert int(cache_after_second["source_len"]) == len(
            cache_after_second["keys_df"].index
        )

    def test_column_filter_treats_nullable_text_as_empty_instead_of_na_literal(self):
        nullable_df = self.base_df.assign(
            setor_executor=pd.Series([pd.NA, "MEL4", ""], dtype="string"),
        ).copy()
        self.window.df_completo = nullable_df.copy()
        self.window.df_exibido = nullable_df.copy()
        self.window._df_last_search_filtered = nullable_df.copy()
        self.window.paginator.set_dataframe(nullable_df.copy())

        self.window._active_column_filters = {"setor_executor": "MEL4"}
        filtered = self.window._apply_column_filters(nullable_df)
        assert filtered["numero_ssa"].tolist() == [2]

        self.window._active_column_filters = {"setor_executor": "<NA>"}
        filtered_na_literal = self.window._apply_column_filters(nullable_df)
        assert filtered_na_literal.empty

    def test_advanced_filter_include_ignores_nullable_text_instead_of_na_literal(self):
        nullable_df = self.base_df.assign(
            setor_executor=pd.Series([pd.NA, "MEL4", "IEE3", ""], dtype="string"),
        ).copy()
        self.window.df_completo = nullable_df.copy()
        self.window.df_exibido = nullable_df.copy()
        self.window._df_last_search_filtered = nullable_df.copy()
        self.window.paginator.set_dataframe(nullable_df.copy())
        self.window._advanced_filters = {"setor_executor": ["MEL4"]}

        filtered = self.window._apply_advanced_filters(nullable_df)

        assert filtered["numero_ssa"].tolist() == [2]

    def test_num_reprogramacoes_sort_keys_treat_nullable_values_as_empty_text(self):
        mixed_df = self.base_df.assign(
            num_reprogramacoes=pd.Series(
                [2, pd.NA, "Reprogramacao #1", None, ""], dtype="object"
            )
        ).copy()

        sort_keys = self.window._build_num_reprogramacoes_sort_keys(mixed_df)

        assert sort_keys["__reprog_txt"].tolist() == [
            "2",
            "",
            "reprogramacao #1",
            "",
            "",
        ]
        assert sort_keys["__reprog_is_nan"].tolist() == [False, True, False, True, True]

    def test_num_reprogramacoes_sort_rebuilds_stale_cache_with_mismatched_index(self):
        mixed_df = self.base_df.assign(
            num_reprogramacoes=pd.Series(
                [2, "Reprogramacao #1", 0, "", None], dtype="object"
            )
        ).copy()
        if "num_reprogramacoes" not in self.window.visible_columns:
            self.window.visible_columns.append("num_reprogramacoes")
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        stale_keys = pd.DataFrame(
            {
                "__reprog_is_nan": [False],
                "__reprog_num": [0],
                "__reprog_txt": ["stale"],
            },
            index=[999999],
        )
        self.window._num_reprog_sort_cache = {
            "source_id": id(self.window.df_exibido),
            "source_len": len(self.window.df_exibido.index),
            "keys_df": stale_keys,
        }

        logical_index = self.window._current_display_columns.index("num_reprogramacoes")
        self.window.on_header_clicked(logical_index)

        cache = self.window._num_reprog_sort_cache
        assert isinstance(cache.get("source_id"), int)
        assert isinstance(cache["keys_df"], pd.DataFrame)
        assert cache["keys_df"].index.equals(self.window.df_exibido.index)

    def test_save_advanced_filters_default_is_noop_compat(self):
        self.window._advanced_filters = {"situacao": ["STE"]}
        self.window._save_advanced_filters_default()
        assert self.window._advanced_filters == {"situacao": ["STE"]}

    def test_on_filter_finished_ignores_stale_request(self):
        self.window._active_filter_request_id = 10
        original = self.window._df_last_search_filtered.copy()
        stale_df = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(stale_df, request_id=9)

        assert self.window._df_last_search_filtered.equals(original)

    def test_on_filter_finished_uses_request_scoped_search_display(self):
        self.window._active_filter_request_id = 22
        self.window._active_filter_search_request_id = 22
        self.window._active_filter_search_display = "Busca nova"
        filtered = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(filtered, request_id=22)

        assert "para 'Busca nova'" in self.window.status_label.text()

    def test_clear_filter_invalidates_pending_async_result(self):
        self.window._filter_request_seq = 20
        self.window._active_filter_request_id = 20
        self.window.progress_bar.setVisible(True)
        self.window.load_button.setEnabled(False)
        self.window.search_button.setEnabled(False)
        stale_df = self.base_df.iloc[:1].copy()

        self.window.search_input.setText("Teste A")
        self.window.clear_filter()
        QApplication.processEvents()

        assert self.window._active_filter_request_id == 21
        assert self.window.search_input.text() == ""
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

        self.window.on_filter_finished(stale_df, request_id=20)
        assert self.window._df_last_search_filtered.equals(self.base_df)

    def test_clear_filter_resets_async_search_display_state(self):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert self.window._active_filter_search_request_id is not None
        assert (
            str(getattr(self.window, "_active_filter_search_display", "") or "").strip()
            == "Teste A"
        )

        self.window.clear_filter()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._active_filter_search_request_id is None
        assert (
            str(getattr(self.window, "_active_filter_search_display", "") or "").strip()
            == ""
        )

    def test_clear_all_filters_global_invalidates_pending_async_result(self):
        self.window._filter_request_seq = 30
        self.window._active_filter_request_id = 30
        self.window.progress_bar.setVisible(True)
        self.window.load_button.setEnabled(False)
        self.window.search_button.setEnabled(False)
        self.window._active_column_filters["situacao"] = "STE"
        stale_df = self.base_df.iloc[:2].copy()

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._active_filter_request_id == 31
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

        self.window.on_filter_finished(stale_df, request_id=30)
        assert self.window.df_exibido.equals(self.base_df)

    def test_initiate_filtering_fallback_when_filter_worker_missing(self):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste A")

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", None):
            self.window.initiate_filtering()
            QApplication.processEvents()

        assert Counter(self._extract_visible_ssa()) == Counter([1])
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

    def test_initiate_filtering_cancels_previous_async_worker(self):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste")

        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

        class _FakeWorker:
            def __init__(self, *_args, **_kwargs):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = False

            def start(self):
                self.start_called = True
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _FakeWorker):
            self.window.initiate_filtering()
            first_worker = self.window.filter_thread
            assert first_worker.start_called is True

            self.window.search_input.setText("Teste A")
            self.window.initiate_filtering()
            second_worker = self.window.filter_thread

        assert second_worker is not first_worker
        assert first_worker.quit_called is True
        assert first_worker.wait_called_ms is None
        assert first_worker.deleted is True
        assert second_worker.start_called is True

    def test_initiate_filtering_aborts_when_critical_signal_connection_fails(self):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste")

        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

        class _FakeWorker:
            def __init__(self, *_args, **_kwargs):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = False

            def start(self):
                self.start_called = True
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        def _connect_side_effect(_signal, _slot, *, label):
            if label == "filter_worker.filter_finished":
                return False
            return True

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _FakeWorker):
            with patch(
                "gui.mixins.filter_gui_ssa_mixin._connect_filter_signal",
                side_effect=_connect_side_effect,
            ):
                self.window.initiate_filtering()

        assert self.window.filter_thread is None
        assert self.window.status_label.text() == "Status: Erro ao aplicar filtro."
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

    def test_retain_filter_worker_releases_immediately_when_release_hook_fails(self):
        class _FakeWorker:
            def __init__(self):
                self.finished = object()

            def deleteLater(self):
                return None

        worker = _FakeWorker()
        self.window._retired_filter_workers = []
        filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS[:] = []

        def _connect_side_effect(_signal, _slot, *, label):
            if label == "filter_worker.finished.release":
                return False
            return True

        with patch(
            "gui.mixins.filter_gui_ssa_mixin._connect_filter_signal",
            side_effect=_connect_side_effect,
        ):
            self.window._retain_filter_worker_until_finished(worker)

        assert worker not in self.window._retired_filter_workers
        assert worker not in filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS

    def test_close_event_cleans_filter_worker_with_centralized_cleanup(self):
        class _FakeSignal:
            def disconnect(self, _callback=None):
                return None

        class _FakeWorker:
            def __init__(self):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        worker = _FakeWorker()
        self.window.filter_thread = worker

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert worker.quit_called is True
        assert worker.wait_called_ms == 3000
        assert worker.deleted is True
        assert self.window.filter_thread is None

    def test_initiate_filtering_keeps_slow_previous_worker_retained_until_finished(
        self,
    ):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste")

        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowWorker:
            def __init__(self):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = True

            def start(self):
                self.start_called = True
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                # Simula worker que continua rodando após quit
                self._running = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return False

            def deleteLater(self):
                self.deleted = True

            def finish_now(self):
                self._running = False
                self.finished.emit()

        class _NewWorker:
            def __init__(self, *_args, **_kwargs):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self._running = False

            def start(self):
                self.start_called = True
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        previous_worker = _SlowWorker()
        self.window.filter_thread = previous_worker
        self.window._retired_filter_workers = []

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _NewWorker):
            self.window.initiate_filtering()

        assert previous_worker.quit_called is True
        assert previous_worker.wait_called_ms is None
        assert previous_worker in self.window._retired_filter_workers

        previous_worker.finish_now()
        assert previous_worker.deleted is True
        assert previous_worker not in self.window._retired_filter_workers

    def test_close_event_cleans_data_loader_worker(self):
        class _FakeSignal:
            def disconnect(self, _callback=None):
                return None

        class _FakeLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        worker = _FakeLoaderWorker()
        self.window.data_loader_thread = worker

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert worker.quit_called is True
        assert worker.wait_called_ms == 3000
        assert worker.deleted is True
        assert self.window.data_loader_thread is None

    def test_on_data_loaded_ignores_stale_request(self):
        original_df = self.window.df_completo.copy()
        stale_df = self.base_df.iloc[:1].copy()
        self.window._active_data_load_request_id = 10

        self.window.on_data_loaded(stale_df, request_id=9)

        assert self.window.df_completo.equals(original_df)

    def test_on_data_loaded_stops_pending_sector_timer(self):
        self.window._active_data_load_request_id = 12
        self.window._sector_debounce_timer.start()
        assert self.window._sector_debounce_timer.isActive() is True

        self.window.on_data_loaded(self.base_df.copy(), request_id=12)

        assert self.window._sector_debounce_timer.isActive() is False

    def test_on_data_loaded_syncs_clear_button_to_active_filters(self):
        self.window._active_data_load_request_id = 10
        self.window.search_input.setText("")
        self.window._exclude_ste_sca = False
        self.window._advanced_filters_active = False
        for key in list(self.window._active_column_filters.keys()):
            self.window._active_column_filters[key] = ""
        self.window.clear_filter_button.setEnabled(True)

        self.window.on_data_loaded(self.base_df.copy(), request_id=10)

        assert self.window.clear_filter_button.isEnabled() is False

    def test_on_data_loaded_keeps_clear_button_enabled_when_filters_active(self):
        self.window._active_data_load_request_id = 11
        self.window.search_input.setText("Teste")
        self.window.clear_filter_button.setEnabled(False)

        self.window.on_data_loaded(self.base_df.copy(), request_id=11)

        assert self.window.clear_filter_button.isEnabled() is True

    def test_on_data_loaded_sanitizes_decimal_ssa_artifacts(self):
        self.window._active_data_load_request_id = 21
        df = self.base_df.copy()
        df["numero_ssa"] = df["numero_ssa"].astype(object)
        df["derivada_de"] = df["derivada_de"].astype(object)
        df.loc[0, "numero_ssa"] = "202500777.0"
        df.loc[1, "numero_ssa"] = 202500778.0
        df.loc[0, "derivada_de"] = "202500001.0"

        self.window.on_data_loaded(df, request_id=21)

        assert self.window.df_completo.loc[0, "numero_ssa"] == "202500777"
        assert self.window.df_completo.loc[1, "numero_ssa"] == "202500778"
        assert self.window.df_completo.loc[0, "derivada_de"] == "202500001"

    def test_on_data_loaded_uses_preprocessed_attrs_from_worker(self):
        self.window._active_data_load_request_id = 22
        sorted_df = self.base_df.copy().iloc[::-1].copy()
        sanitized_df = self.base_df.copy()
        sanitized_df["numero_ssa"] = [
            "202500005",
            "202500004",
            "202500003",
            "202500002",
            "202500001",
        ]
        sorted_df.attrs["ssa_preprocessed_for_gui"] = True
        sorted_df.attrs["ssa_sanitized_df"] = sanitized_df
        sorted_df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "descricao_ssa",
        ]

        self.window.on_data_loaded(sorted_df, request_id=22)

        assert self.window.df_completo.equals(sanitized_df)
        assert self.window.df_exibido.iloc[0]["numero_ssa"] == "202500005"
        assert self.window.df_exibido.iloc[-1]["numero_ssa"] == "202500001"
        assert {"numero_ssa", "situacao", "descricao_ssa"}.issubset(
            self.window._non_null_cols_cache
        )

    def test_on_data_loaded_primes_num_reprogramacoes_sort_cache(self):
        self.window._active_data_load_request_id = 31
        df = self.base_df.copy()
        df["num_reprogramacoes"] = [2, "Reprogramacao #1", 0, "", None]

        self.window.on_data_loaded(df, request_id=31)

        cache = self.window._num_reprog_sort_cache
        assert isinstance(cache.get("source_id"), int)
        assert isinstance(cache["keys_df"], pd.DataFrame)
        assert int(cache["source_len"]) == len(cache["keys_df"].index)
        assert "__reprog_num" in cache["keys_df"].columns

    def test_on_load_error_ignores_stale_request(self):
        self.window._active_data_load_request_id = 10
        self.window.status_label.setText("Status: OK")

        with patch("gui.gui_ssa.QMessageBox.critical") as critical:
            self.window.on_load_error("erro", request_id=9)

        assert critical.called is False
        assert self.window.status_label.text() == "Status: OK"

    def test_on_filter_error_ignores_stale_request(self):
        self.window._active_filter_request_id = 10
        self.window.status_label.setText("Status: OK")

        with patch("gui.mixins.filter_gui_ssa_mixin.QMessageBox.critical") as critical:
            self.window.on_filter_error("erro", request_id=9)

        assert critical.called is False
        assert self.window.status_label.text() == "Status: OK"

    def test_on_load_finished_stale_request_only_cleans_stale_worker(self):
        class _FakeSignal:
            def disconnect(self, _callback=None):
                return None

        class _FakeLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        active_worker = object()
        stale_worker = _FakeLoaderWorker()
        self.window.data_loader_thread = active_worker
        self.window._active_data_load_request_id = 10
        self.window.progress_bar.setVisible(True)
        self.window.load_button.setEnabled(False)
        self.window.search_button.setEnabled(False)

        self.window.on_load_finished(worker=stale_worker, request_id=9)

        assert stale_worker.quit_called is True
        assert stale_worker.wait_called_ms == 1500
        assert stale_worker.deleted is True
        assert self.window.data_loader_thread is active_worker
        assert self.window.progress_bar.isVisible() is True
        assert self.window.load_button.isEnabled() is False
        assert self.window.search_button.isEnabled() is False

    def test_close_event_retains_slow_data_loader_globally_until_finished(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                # Simula worker que nao encerra imediatamente.
                self._running = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return False

            def deleteLater(self):
                self.deleted = True

            def finish_now(self):
                self._running = False
                self.finished.emit()

        worker = _SlowLoaderWorker()
        if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)
        self.window.data_loader_thread = worker

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert worker.quit_called is True
        assert worker.wait_called_ms == 3000
        assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS

        worker.finish_now()
        assert worker.deleted is True
        assert worker not in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS

    def test_close_event_retains_slow_filter_worker_globally_until_finished(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowFilterWorker:
            def __init__(self):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                # Simula worker que nao encerra imediatamente.
                self._running = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return False

            def deleteLater(self):
                self.deleted = True

            def finish_now(self):
                self._running = False
                self.finished.emit()

        worker = _SlowFilterWorker()
        if worker in filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS:
            filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS.remove(worker)
        self.window.filter_thread = worker

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert worker.quit_called is True
        assert worker.wait_called_ms == 3000
        assert worker in filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS

        worker.finish_now()
        assert worker.deleted is True
        assert worker not in filter_mixin.GLOBAL_RETIRED_FILTER_WORKERS

    def test_close_event_retains_slow_rescan_worker_globally_and_clears_active_ref(
        self,
    ):
        class _SlowRescanWorker:
            def __init__(self):
                self._running = True
                self.stop_called = False
                self.quit_called = False
                self.wait_calls = []
                self.terminate_called = False

            def isRunning(self):
                return self._running

            def stop(self):
                self.stop_called = True

            def quit(self):
                self.quit_called = True

            def wait(self, ms):
                self.wait_calls.append(ms)
                return False

            def terminate(self):
                self.terminate_called = True

        worker = _SlowRescanWorker()
        if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
        gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)
        self.window._active_rescan_worker = worker

        try:
            event = QCloseEvent()
            self.window.closeEvent(event)

            assert event.isAccepted() is True
            assert worker.stop_called is True
            assert worker.quit_called is True
            assert worker.wait_calls and worker.wait_calls[0] == 1500
            assert worker.terminate_called is True
            assert worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS
            assert self.window._active_rescan_worker is None
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
                gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)

    def test_close_event_retains_rescan_worker_when_isrunning_check_fails_mid_shutdown(
        self,
    ):
        class _FlakyRescanWorker:
            def __init__(self):
                self._running = True
                self._is_running_calls = 0
                self.stop_called = False
                self.quit_called = False
                self.wait_calls = []

            def isRunning(self):
                self._is_running_calls += 1
                if self._is_running_calls == 2:
                    raise RuntimeError("intermittent isRunning failure")
                return self._running

            def stop(self):
                self.stop_called = True

            def quit(self):
                self.quit_called = True

            def wait(self, ms):
                self.wait_calls.append(ms)
                return False

            def terminate(self):
                return None

        worker = _FlakyRescanWorker()
        if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
        gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)
        self.window._active_rescan_worker = worker

        try:
            event = QCloseEvent()
            self.window.closeEvent(event)

            assert event.isAccepted() is True
            assert worker.stop_called is True
            assert worker.quit_called is True
            assert worker.wait_calls and worker.wait_calls[0] == 1500
            assert worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS
            assert self.window._active_rescan_worker is None
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
                gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)

    def test_close_event_enforces_rescan_global_cap_and_meta_cleanup(self):
        class _RunningRescanWorker:
            def __init__(self):
                self.stop_called = False
                self.quit_called = False
                self.wait_calls = []

            def isRunning(self):
                return True

            def stop(self):
                self.stop_called = True

            def quit(self):
                self.quit_called = True

            def wait(self, ms):
                self.wait_calls.append(ms)
                return False

            def terminate(self):
                return None

        old_cap = gui_ssa.MAX_GLOBAL_RETIRED_RESCAN_WORKERS
        worker_old = _RunningRescanWorker()
        worker_new = _RunningRescanWorker()
        setattr(gui_ssa, "MAX_GLOBAL_RETIRED_RESCAN_WORKERS", 1)
        gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS[:] = [worker_old]
        gui_ssa.GLOBAL_RETIRED_RESCAN_META[worker_old] = 1.0
        self.window._active_rescan_worker = worker_new

        try:
            event = QCloseEvent()
            self.window.closeEvent(event)

            assert event.isAccepted() is True
            assert gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS == [worker_new]
            assert worker_old not in gui_ssa.GLOBAL_RETIRED_RESCAN_META
            assert worker_new in gui_ssa.GLOBAL_RETIRED_RESCAN_META
            assert self.window._active_rescan_worker is None
        finally:
            setattr(gui_ssa, "MAX_GLOBAL_RETIRED_RESCAN_WORKERS", old_cap)
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS[:] = []
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.clear()

    def test_close_event_uses_running_helper_when_worker_isrunning_is_unstable_after_wait(
        self, monkeypatch
    ):
        class _RescanWorkerUnstableAfterWait:
            def __init__(self):
                self._is_running_calls = 0
                self.stop_called = False
                self.quit_called = False
                self.wait_calls = []
                self.terminate_called = False

            def isRunning(self):
                self._is_running_calls += 1
                if self._is_running_calls >= 2:
                    raise RuntimeError("isRunning unstable after wait")
                return True

            def stop(self):
                self.stop_called = True

            def quit(self):
                self.quit_called = True

            def wait(self, ms):
                self.wait_calls.append(ms)
                return False

            def terminate(self):
                self.terminate_called = True

        worker = _RescanWorkerUnstableAfterWait()
        if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
        gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)
        self.window._active_rescan_worker = worker
        call_counter = {"count": 0}
        original_running_helper = self.window._is_rescan_worker_running

        def _tracked_running_helper(target):
            call_counter["count"] += 1
            return original_running_helper(target)

        monkeypatch.setattr(
            self.window, "_is_rescan_worker_running", _tracked_running_helper
        )

        try:
            event = QCloseEvent()
            self.window.closeEvent(event)

            assert event.isAccepted() is True
            assert worker.stop_called is True
            assert worker.quit_called is True
            assert call_counter["count"] >= 2
            assert self.window._active_rescan_worker is None
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS:
                gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.remove(worker)
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.pop(worker, None)

    def test_on_load_finished_current_request_cleans_worker_and_restores_ui(self):
        class _FakeSignal:
            def disconnect(self, _callback=None):
                return None

        class _FakeLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        worker = _FakeLoaderWorker()
        self.window.data_loader_thread = worker
        self.window._active_data_load_request_id = 11
        self.window.progress_bar.setVisible(True)
        self.window.load_button.setEnabled(False)
        self.window.search_button.setEnabled(False)

        self.window.on_load_finished(worker=worker, request_id=11)

        assert worker.quit_called is True
        assert worker.wait_called_ms == 1500
        assert worker.deleted is True
        assert self.window.data_loader_thread is None
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

    def test_on_filter_finished_skips_width_adjustments_when_table_widget_invalid(
        self, monkeypatch
    ):
        self.window._active_filter_request_id = 77
        self.window._active_filter_search_request_id = 77
        self.window._active_filter_search_display = "Teste"
        monkeypatch.setattr(self.window, "_refresh_after_filter_change", lambda: None)
        monkeypatch.setattr(self.window, "_apply_search_display", lambda: None)
        self.window.table_widget = None

        self.window.on_filter_finished(self.base_df.copy(), request_id=77)

        status = self.window.status_label.text()
        assert "Status: SSAs filtradas:" in status
        assert "para 'Teste'" in status

    def test_load_data_replaces_previous_loader_worker_and_tracks_request(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

        class _FakeLoaderWorker:
            def __init__(self, *_args, **_kwargs):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = False
                self.start_called = False
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False

            def isRunning(self):
                return self._running

            def start(self):
                self.start_called = True
                self._running = True

            def quit(self):
                self.quit_called = True
                self._running = False

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

            def deleteLater(self):
                self.deleted = True

        previous_worker = _FakeLoaderWorker()
        previous_worker._running = True
        self.window.data_loader_thread = previous_worker
        self.window._data_load_request_seq = 5
        self.window._active_data_load_request_id = 5

        with (
            patch("gui.gui_ssa.os.path.exists", return_value=True),
            patch("gui.gui_ssa.DataLoaderWorker", _FakeLoaderWorker),
        ):
            ORIGINAL_LOAD_DATA(self.window)

        new_worker = self.window.data_loader_thread
        assert new_worker is not previous_worker
        assert previous_worker.quit_called is True
        assert previous_worker.wait_called_ms is None
        assert previous_worker.deleted is True
        assert new_worker.start_called is True
        assert self.window._active_data_load_request_id == 6

    def test_load_data_cancels_filter_pipeline_and_stops_debounce(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

        class _FakeLoaderWorker:
            def __init__(self, *_args, **_kwargs):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self._running = False

            def isRunning(self):
                return self._running

            def start(self):
                self.start_called = True
                self._running = True

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        class _FakeFilterSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowFilterWorker:
            def __init__(self):
                self.filter_finished = _FakeFilterSignal()
                self.error_occurred = _FakeFilterSignal()
                self.finished = _FakeFilterSignal()
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return False

            def deleteLater(self):
                self.deleted = True

        self.window._filter_request_seq = 7
        self.window._active_filter_request_id = 7
        self.window.search_input.setText("Teste")
        self.window._on_search_text_changed("Teste")
        assert self.window._debounce_timer.isActive() is True

        previous_filter_worker = _SlowFilterWorker()
        self.window.filter_thread = previous_filter_worker
        self.window._retired_filter_workers = []

        with (
            patch("gui.gui_ssa.os.path.exists", return_value=True),
            patch("gui.gui_ssa.DataLoaderWorker", _FakeLoaderWorker),
        ):
            ORIGINAL_LOAD_DATA(self.window)

        assert self.window._active_filter_request_id == 8
        assert self.window.filter_thread is None
        assert self.window._debounce_timer.isActive() is False
        assert previous_filter_worker.quit_called is True
        assert previous_filter_worker.wait_called_ms is None
        assert previous_filter_worker in self.window._retired_filter_workers

    def test_load_data_keeps_slow_previous_worker_retained_until_finished(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.quit_called = False
                self.wait_called_ms = None
                self.deleted = False
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                # Simula worker que continua em execução após quit()
                self._running = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return False

            def deleteLater(self):
                self.deleted = True

            def finish_now(self):
                self._running = False
                self.finished.emit()

        class _NewLoaderWorker:
            def __init__(self, *_args, **_kwargs):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self.start_called = False
                self._running = False

            def isRunning(self):
                return self._running

            def start(self):
                self.start_called = True
                self._running = True

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        previous_worker = _SlowLoaderWorker()
        self.window.data_loader_thread = previous_worker
        self.window._retired_data_loader_workers = []

        with (
            patch("gui.gui_ssa.os.path.exists", return_value=True),
            patch("gui.gui_ssa.DataLoaderWorker", _NewLoaderWorker),
        ):
            ORIGINAL_LOAD_DATA(self.window)

        assert previous_worker.quit_called is True
        assert previous_worker.wait_called_ms is None
        assert previous_worker in self.window._retired_data_loader_workers

        previous_worker.finish_now()
        assert previous_worker not in self.window._retired_data_loader_workers
        assert previous_worker.deleted is True

    def test_repeated_load_data_handoffs_release_retired_workers(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowLoaderWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = True

            def wait(self, _ms):
                return False

            def deleteLater(self):
                return None

            def finish_now(self):
                self._running = False
                self.finished.emit()

        class _NewLoaderWorker:
            def __init__(self, *_args, **_kwargs):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = False

            def isRunning(self):
                return self._running

            def start(self):
                self._running = True

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        self.window._retired_data_loader_workers = []
        self.window._data_load_request_seq = 0
        slow_workers = []

        with (
            patch("gui.gui_ssa.os.path.exists", return_value=True),
            patch("gui.gui_ssa.DataLoaderWorker", _NewLoaderWorker),
        ):
            for _ in range(10):
                slow = _SlowLoaderWorker()
                slow_workers.append(slow)
                self.window.data_loader_thread = slow
                ORIGINAL_LOAD_DATA(self.window)
                assert slow in self.window._retired_data_loader_workers
                slow.finish_now()

        assert self.window._retired_data_loader_workers == []
        assert self.window._active_data_load_request_id == 10
        assert all(worker.quit_called for worker in slow_workers)

    def test_repeated_filter_handoffs_release_retired_workers(self):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste")

        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SlowFilterWorker:
            def __init__(self):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True
                self.quit_called = False

            def isRunning(self):
                return self._running

            def quit(self):
                self.quit_called = True
                self._running = True

            def wait(self, _ms):
                return False

            def deleteLater(self):
                return None

            def finish_now(self):
                self._running = False
                self.finished.emit()

        class _NewFilterWorker:
            def __init__(self, *_args, **_kwargs):
                self.filter_finished = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = False

            def isRunning(self):
                return self._running

            def start(self):
                self._running = True

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        self.window._retired_filter_workers = []
        self.window._filter_request_seq = 0
        slow_workers = []

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _NewFilterWorker):
            for _ in range(10):
                slow = _SlowFilterWorker()
                slow_workers.append(slow)
                self.window.filter_thread = slow
                self.window.initiate_filtering()
                assert slow in self.window._retired_filter_workers
                slow.finish_now()

        assert self.window._retired_filter_workers == []
        assert self.window._active_filter_request_id == 10
        assert all(worker.quit_called for worker in slow_workers)

    def test_restore_filter_state_syncs_exclude_checkbox_all_tabs(self):
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                checkbox.setChecked(False)
        self.window._exclude_ste_sca = False
        self.window._safe_store_last_filter_state("test_restore_sync")

        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()
        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window._exclude_ste_sca is False
        for ctx in self.window._tab_contexts:
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                assert checkbox.isChecked() is False

    def test_restore_last_filter_state_drops_hidden_lines_with_active_filters(self):
        self.window._active_column_filters["descricao_ssa"] = "Teste A"
        self.window._hidden_column_filter_lines = {"descricao_ssa"}
        self.window._on_exclude_ste_sca_toggled(True)
        self.window._safe_store_last_filter_state("test_restore_hidden_active")

        self.window._clear_all_filters_global()
        QApplication.processEvents()
        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window._active_column_filters["descricao_ssa"] == "Teste A"
        assert "descricao_ssa" not in self.window._hidden_column_filter_lines
        label = (
            self.window._expand_column_alias_for_filter("descricao_ssa")
            if hasattr(self.window, "_expand_column_alias_for_filter")
            else self.window._resolve_column_display_name("descricao_ssa")
        )
        assert label in self._get_column_filter_controls()
        assert "situacao!=SCA/SES/STE" in str(
            self.window.filters_summary_label.text() or ""
        )

    def test_clear_all_filters_global_stops_pending_debounce(self):
        self.window.search_input.setText("Teste")
        self.window._on_search_text_changed("Teste")
        assert self.window._debounce_timer.isActive() is True

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._debounce_timer.isActive() is False

    def test_clear_filter_cancels_active_filter_worker(self):
        with patch.object(self.window, "_cancel_active_filter_worker") as cancel_mock:
            self.window.clear_filter()

        cancel_mock.assert_called_once_with("clear_filter", wait_ms=0)

    def test_clear_all_filters_global_cancels_active_filter_worker(self):
        with patch.object(self.window, "_cancel_active_filter_worker") as cancel_mock:
            self.window._clear_all_filters_global()

        cancel_mock.assert_called_once_with("clear_all_filters_global", wait_ms=0)

    def test_schedule_sector_refresh_stops_pending_timer_when_not_materialized(self):
        self.window._responsavel_filters_materialized = False
        self.window._responsavel_options_dirty = False
        self.window._sector_debounce_timer.start()
        assert self.window._sector_debounce_timer.isActive() is True

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self.window._schedule_sector_options_refresh()
            cast(Any, QTest).qWait(
                int(self.window._sector_debounce_timer.interval()) + 80
            )
            QApplication.processEvents()

        assert self.window._responsavel_options_dirty is True
        assert self.window._sector_debounce_timer.isActive() is False
        assert refresh_mock.call_count == 0

    def test_sector_exclude_debounce_reuses_same_timer_instance(self):
        timer_before = self.window._sector_debounce_timer
        self.window._on_adv_sector_exclude_changed()
        QApplication.processEvents()

        assert self.window._sector_debounce_timer is timer_before

    def test_sector_selection_handler_blocks_reentrant_recursion(self):
        reentry_attempts = {"count": 0}

        def _recursive_apply():
            reentry_attempts["count"] += 1
            # Simula callback encadeado durante o processamento atual.
            self.window._on_adv_sector_selection_changed()

        with patch.object(
            self.window, "_apply_divisao_to_setor_checks", side_effect=_recursive_apply
        ) as apply_mock:
            with patch.object(
                self.window, "_schedule_sector_options_refresh"
            ) as schedule_mock:
                self.window._on_adv_sector_selection_changed()

        assert apply_mock.call_count == 1
        assert reentry_attempts["count"] == 1
        schedule_mock.assert_called_once()

    def test_prune_retired_loader_workers_removes_stale_refs_without_finished_signal(
        self,
    ):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SilentWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self._running = False

            def wait(self, _ms):
                return True

            def deleteLater(self):
                return None

        worker = _SilentWorker()
        self.window._retired_data_loader_workers = []
        if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)

        try:
            self.window._retain_data_loader_worker_until_finished(worker)
            assert worker in self.window._retired_data_loader_workers
            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS

            # Simula finalização silenciosa sem emissao de finished().
            worker._running = False
            self.window._prune_retired_data_loader_workers()

            assert worker not in self.window._retired_data_loader_workers
            assert worker not in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
                gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)

    def test_retain_loader_worker_rehydrates_global_tracking_when_local_ref_exists(
        self,
    ):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

            def emit(self, *args, **kwargs):
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _RunningWorker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _FakeSignal()
                self._running = True

            def isRunning(self):
                return self._running

            def quit(self):
                self._running = True

            def wait(self, _ms):
                return False

            def deleteLater(self):
                return None

        worker = _RunningWorker()
        self.window._retired_data_loader_workers = [worker]
        if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)
        gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.pop(worker, None)

        try:
            self.window._retain_data_loader_worker_until_finished(worker)

            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS
            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
                gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.pop(worker, None)
