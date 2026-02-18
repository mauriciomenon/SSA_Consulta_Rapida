"""Testes específicos para filtros combinados (AND/OU) da GUI principal."""

import os
import sqlite3
import sys
import time
from collections import Counter

import pandas as pd
import pytest
from unittest.mock import patch

pytest.importorskip('PyQt6', reason='Dependência PyQt6 indisponível no ambiente de teste')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit, QLabel  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtCore import Qt, QSize  # noqa: E402
from PyQt6.QtGui import QCloseEvent, QResizeEvent  # noqa: E402

from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui import gui_ssa  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402

ORIGINAL_LOAD_DATA = SSAMainWindow.load_data


class TestGUIFilterLogic:
    """Valida filtros com perfis OR e exclusões complementares."""

    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        os.environ['SSA_SYNC_FILTER'] = '1'
        self._load_patch = patch.object(SSAMainWindow, 'load_data', lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        # Mantém o patch ativo para impedir agendamento de carregamentos reais
        self.window.show()

        # Dataset simplificado com combinação de executor/emissor e situações distintas
        self.base_df = pd.DataFrame({
            'numero_ssa': [1, 2, 3, 4, 5],
            'situacao': ['APV', 'STE', 'SCA', 'AMP', 'APV'],
            'derivada_de': ['', '', '', '', ''],
            'localizacao_codigo': ['LOC1', 'LOC2', 'LOC3', 'LOC4', 'LOC5'],
            'descricao_localizacao': ['Desc1'] * 5,
            'equipamento': ['EQ1'] * 5,
            'semana_cadastro': [202501] * 5,
            'semana_programada': [202503] * 5,
            'data_cadastro': ['2025-01-01'] * 5,
            'descricao_ssa': ['Teste A', 'Teste B', 'Teste C', 'Teste D', 'Teste E'],
            'setor_executor': ['IEE3', 'OURO', 'MEL4', 'XYZ', 'IEE2'],
            'setor_emissor': ['ABC', 'IEE3', 'MEL4', 'MEL3', 'XYZ'],
            'descricao_execucao': ['Exec A', 'Exec B', 'Exec C', 'Exec D', 'Exec E'],
            'solicitante': ['User1', 'User2', 'User3', 'User4', 'User5']
        })

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
        return list(self.window.df_exibido['numero_ssa'])

    def _build_heavy_filters_df(self, rows: int = 1200) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "numero_ssa": list(range(100000, 100000 + rows)),
                "situacao": ["APV", "STE", "SCA", "AMP"] * (rows // 4) + ["APV"] * (rows % 4),
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
                "responsavel_programacao": [f"PROG_{i % 1700:04d}" for i in range(rows)],
                "responsavel_execucao": [f"EXEC_{i % 1800:04d}" for i in range(rows)],
                "responsavel_emissor": [f"EMIS_{i % 1600:04d}" for i in range(rows)],
            }
        )

    def _get_column_filter_controls(self):
        controls = {}
        layout = getattr(self.window, 'col_filters_list_layout', None)
        if not layout:
            return controls
        for i in range(layout.count()):
            item = layout.itemAt(i)
            row_widget = item.widget()
            if row_widget is None:
                continue
            row_layout = row_widget.layout()
            if row_layout is None or row_layout.count() < 4:
                continue
            label_widget = row_layout.itemAt(0).widget()
            edit_widget = row_layout.itemAt(1).widget()
            apply_widget = row_layout.itemAt(2).widget()
            clear_widget = row_layout.itemAt(3).widget()
            if not isinstance(label_widget, QLabel):
                continue
            if not isinstance(edit_widget, QLineEdit):
                continue
            if not isinstance(apply_widget, QPushButton):
                continue
            if not isinstance(clear_widget, QPushButton):
                continue
            controls[label_widget.text()] = (edit_widget, apply_widget, clear_widget)
        return controls

    def test_profile_or_filters_executor_or_emissor(self):
        """Perfil OR deve considerar executor ou emissor e refletir na UI."""
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)

        # Com OR restrito por coluna e AND entre colunas, apenas quem atende ambos entra (aqui só o 3)
        assert Counter(self._extract_visible_ssa()) == Counter([3])

        # Confirma sincronismo entre campos (Executor/Emissor)
        for col in ('setor_executor', 'setor_emissor'):
            # Armazenamento interno usa virgulas para separar alternativas
            assert self.window._active_column_filters[col] == 'IEE3, MEL3, MEL4'
        summary = getattr(self.window, 'filters_summary_label', None)
        if summary is not None:
            # Nova logica: apenas virgulas, sem operadores OU
            assert "IEE3, MEL3, MEL4" in summary.text() or "Executor" in summary.text()
            assert col in self.window._column_to_or_group

        # Ajuste manual em um campo deve repercutir no par
        self.window._active_column_filters['setor_executor'] = 'MEL4'
        self.window._sync_or_group_values('setor_executor', 'MEL4')
        self.window._refresh_after_filter_change()
        assert self.window._active_column_filters['setor_emissor'] == 'MEL4'
        assert Counter(self._extract_visible_ssa()) == Counter([3])

    def test_exclude_ste_sca_combined_with_or_group(self):
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)
        # Com a nova semântica, somente o 3 está visível
        assert Counter(self._extract_visible_ssa()) == Counter([3])

        self.window._on_exclude_ste_sca_toggled(True)
        # Filtra linhas STE/SCA (2 e 3 deverão sair)
        remaining = self._extract_visible_ssa()
        assert 3 not in remaining
        # Com base no filtro aplicado, nada resta após excluir SCA/STE
        assert Counter(remaining) == Counter([])

    def test_clear_operations_preserve_group_structure(self):
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)
        self.window._clear_single_column_filter('setor_executor', 'IEE3, MEL3, MEL4')
        # Grupo deve ser removido para ambos os campos
        assert 'setor_executor' not in self.window._active_column_filters
        assert 'setor_emissor' not in self.window._active_column_filters

        # Reaplica valor manual e garante aplicação correta
        self.window._active_column_filters['setor_executor'] = 'IEE3'
        self.window._sync_or_group_values('setor_executor', 'IEE3')
        self.window._refresh_after_filter_change()
        # Com OR restrito por coluna e sincronismo no grupo (IEE3 em ambos), nenhum registro atende ambos
        assert Counter(self._extract_visible_ssa()) == Counter([])

        # Limpa todos e garante reset completo
        self.window._clear_all_column_filters()
        assert not self.window._active_column_filters
        self.window._refresh_after_filter_change()
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])

    def test_general_search_and_or_display(self):
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.search_input.setText('Teste')
        self.window.initiate_filtering()
        QApplication.processEvents()

        # Busca geral com AND logic: termo unico retorna todos que contem 'Teste'
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert self.window.search_input.text() == 'Teste'

        # Combinação com termo negativo utilizando AND
        self.window.search_input.setText('Teste A, !User2')
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])
        assert self.window.search_input.text() == 'Teste A, !User2'

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
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)
        QApplication.processEvents()
        width_after_profile = self.window.table_widget.columnWidth(1)

        self.window.search_input.setText('Teste A, Teste D')
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

    def test_clear_filter_button_reflects_active_filters(self):
        self.window.search_input.setText('')
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is False

        self.window.search_input.setText('Teste A')
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is True

        self.window.clear_filter()
        QApplication.processEvents()
        assert self.window.search_input.text() == ''
        assert self.window.clear_filter_button.isEnabled() is False

    def test_column_filter_buttons_flow(self):
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)
        QApplication.processEvents()
        controls = self._get_column_filter_controls()
        assert 'Emissor' in controls
        emissor_edit, emissor_apply, emissor_clear = controls['Emissor']
        executor_edit, executor_apply, _ = controls['Executor']

        emissor_edit.setText('MEL3, MEL4')
        QTest.mouseClick(emissor_apply, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        # Armazenamento interno usa virgulas
        assert self.window._active_column_filters['setor_emissor'] == 'MEL3, MEL4'
        assert self.window._active_column_filters['setor_executor'] == 'MEL3, MEL4'

        # "Remover linha" agora apenas oculta a linha, não limpa o valor
        emissor_edit.setText('')
        QTest.mouseClick(emissor_clear, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        # Verifica que a linha do Emissor foi removida da exibição
        controls_after = self._get_column_filter_controls()
        assert 'Emissor' not in controls_after
        # Valores permanecem iguais (grupo ainda ativo)
        assert self.window._active_column_filters['setor_emissor'] == 'MEL3, MEL4'
        assert self.window._active_column_filters['setor_executor'] == 'MEL3, MEL4'

        executor_edit.setText('IEE3, MEL4')
        QTest.mouseClick(executor_apply, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert self.window._active_column_filters['setor_executor'] == 'IEE3, MEL4'
        assert self.window._active_column_filters['setor_emissor'] == 'IEE3, MEL4'

    @pytest.mark.skip(reason="exclude_ste_checkbox está oculto na UI atual; efeito funcional coberto por test_exclude_ste_sca_combined_with_or_group")
    def test_exclude_checkbox_and_clear_filter_button(self):
        self.window._apply_filter_profile('IEE3 + MEL3 + MEL4', refresh=True)
        QApplication.processEvents()
        all_records = set(self._extract_visible_ssa())
        # Com o perfil aplicado na nova semântica, apenas 3 está visível antes do checkbox
        assert 3 in all_records

        QTest.mouseClick(self.window.exclude_ste_checkbox, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        remaining = set(self._extract_visible_ssa())
        assert 2 not in remaining and 3 not in remaining

        self.window.search_input.setText('Teste A, Teste D')
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.search_input.text() == 'Teste A, Teste D'

        assert self.window.clear_filter_button.isEnabled()
        self.window.clear_filter()
        QApplication.processEvents()
        assert self.window.search_input.text() == ''
        assert set(self._extract_visible_ssa()) == set(self.base_df['numero_ssa'])

    def test_persistent_filters_order(self):
        from unittest.mock import patch

        with patch('gui.gui_ssa.QMessageBox.information', return_value=None):
            self.window.persistent_filters = []
            self.window.search_input.setText('Zebra filtro')
            self.window.save_current_filter()
            self.window.search_input.setText('Alfa filtro')
            self.window.save_current_filter()

        names = [f['name'] for f in self.window.persistent_filters]
        assert names == sorted(names, key=lambda n: n.casefold())

    def test_advanced_filter_checks_survive_tab_switch(self):
        """Rebuild dos menus avançados deve persistir listas *_checks no tab_context."""
        self.window._adv_options_dirty = True
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
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
            idx for idx, ctx in enumerate(self.window._tab_contexts)
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

        with patch.object(self.window, "_refresh_responsavel_options", wraps=self.window._refresh_responsavel_options) as refresh_mock:
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True
        button = getattr(self.window, "adv_responsavel_solicitante_button", None)
        if button is None:
            button = getattr(self.window, "_adv_ctx", {}).get("adv_responsavel_solicitante_button")
        assert button is not None
        assert "inc" in button.text()

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
        assert self.window._advanced_filters["responsavel_programacao_exclude_values"] == ["ProgB"]
        assert self.window._advanced_filters["responsavel_execucao"] == ["ExecA"]
        assert self.window._advanced_filters["responsavel_execucao_exclude_values"] == ["ExecB"]
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

        with patch.object(self.window, "_refresh_responsavel_options", wraps=self.window._refresh_responsavel_options) as refresh_mock:
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

        with patch.object(self.window, "_refresh_responsavel_options", wraps=self.window._refresh_responsavel_options) as refresh_mock:
            filter_tab_idx = next(
                idx for idx, ctx in enumerate(self.window._tab_contexts)
                if ctx.get("tab_kind") == "filters"
            )
            self.window.main_tabs.setCurrentIndex(filter_tab_idx)
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True

    def test_switch_to_filters_tab_does_not_reapply_same_theme(self):
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "main"
        )

        with patch.object(self.window, "apply_theme", wraps=self.window.apply_theme) as apply_mock:
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
            idx for idx, ctx in enumerate(self.window._tab_contexts)
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
        self.window._ensure_responsavel_options_materialized(target_prefix=target_prefix)
        QApplication.processEvents()
        materialize_ms = (time.perf_counter() - t1) * 1000.0

        assert target_prefix in getattr(self.window, "_responsavel_materialized_prefixes", set())
        assert self.window._responsavel_filters_materialized is False
        assert self.window._responsavel_options_dirty is True
        assert materialize_ms < 5000.0

    def test_theme_cycle_smoke_latency_on_filters_tab(self):
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
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

    def test_repeated_filters_tab_and_theme_actions_keep_state_consistent(self):
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
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
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        main_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "main"
        )
        filters_ctx = next(ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "filters")
        main_ctx = next(ctx for ctx in self.window._tab_contexts if ctx.get("tab_kind") == "main")

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
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QTest.qWait(int(self.window._debounce_timer.interval()) + 80)
        QApplication.processEvents()

        # O dataset nao pode ser resetado por disparo tardio no contexto da aba errada.
        assert Counter(self._extract_visible_ssa()) == Counter([1])

    def test_clear_filter_on_filters_tab_clears_search_in_all_tabs(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        main_ctx = next(
            ctx for ctx in self.window._tab_contexts
            if ctx.get("tab_kind") == "main"
        )
        assert main_ctx["search_input"].text().strip() == "Teste A"

        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window.clear_filter()
        QApplication.processEvents()

        for ctx in self.window._tab_contexts:
            assert ctx["search_input"].text().strip() == ""
        assert self.window.clear_filter_button.isEnabled() is False

    def test_resize_event_reorganizes_advanced_grid_on_filters_tab(self):
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        captured_widths = []
        with patch.object(self.window, "_reorganize_advanced_filters_grid", side_effect=lambda width: captured_widths.append(width)):
            event = QResizeEvent(QSize(1280, 800), QSize(1200, 760))
            self.window.resizeEvent(event)

        assert captured_widths
        assert captured_widths[0] >= 0

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

        html = self.window._format_details_html(series, highlight_search_terms=False, linkify=False)

        assert "_norm_ssa" not in html
        assert "_debug_value" not in html
        assert "INTERNAL_SENTINEL_NORM" not in html
        assert "INTERNAL_SENTINEL_DEBUG" not in html

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
        self.window._advanced_filters = {"situacao": ["STE"], "setor_executor": ["IEE3"]}
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

    def test_build_derivadas_tree_normalizes_and_ignores_invalid_values(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["SSA-101", "102", "102", "103", "104", "", None],
                "derivada_de": ["100", "100", "100", "None", "nan", "100", "100"],
            }
        )

        mae_filhas, filha_mae = self.window._build_derivadas_tree(df, "numero_ssa", "derivada_de")

        assert mae_filhas == {"100": ["101", "102"]}
        assert filha_mae == {"101": "100", "102": "100"}

    def test_update_derivadas_button_state_ignores_invalid_values(self):
        btn = getattr(self.window, "adv_derivadas_especificas_button", None)
        if btn is None:
            btn = self.window._adv_ctx["adv_derivadas_especificas_button"]

        self.window._df_last_search_filtered = pd.DataFrame(
            {
                "numero_ssa": ["1", "2", "3"],
                "derivada_de": ["None", "nan", "   "],
            }
        )
        self.window._update_derivadas_button_state()
        assert btn.isEnabled() is False

        self.window._df_last_search_filtered = pd.DataFrame(
            {
                "numero_ssa": ["1", "2"],
                "derivada_de": ["None", "1001"],
            }
        )
        self.window._update_derivadas_button_state()
        assert btn.isEnabled() is True

    def test_update_derivadas_from_sources_runs_db_then_special_sync(self, monkeypatch, tmp_path):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")
        special_a = str(tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0124PM.xlsx")
        special_b = str(tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0137PM.xlsx")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table")
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [special_a, special_b])

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
            lambda **kwargs: {"schema_ready": True, "is_consistent": True, "issue_counts": {}},
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

    def test_update_derivadas_from_sources_runs_only_db_when_no_special_sheets(self, monkeypatch, tmp_path):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table")
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
            lambda **kwargs: {"schema_ready": True, "is_consistent": True, "issue_counts": {}},
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
        monkeypatch.setattr(self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table")
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
            lambda **kwargs: {"schema_ready": True, "is_consistent": True, "issue_counts": {}},
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.progress_bar.setVisible(False)
        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert self.window.progress_bar.isVisible() is False

    def test_update_derivadas_from_sources_raises_on_inconsistent_scan(self, monkeypatch, tmp_path):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table")
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
        special_file = str(tmp_path / "SSAs Derivadas e Relacionadas_13-02-2026_0131PM.xlsx")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        monkeypatch.setattr(self.window, "_resolve_derivadas_table_name", lambda _db_path: "ssa_table")
        monkeypatch.setattr(self.window, "_list_special_derivadas_sheets", lambda: [special_file])

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
            lambda **kwargs: {"schema_ready": True, "is_consistent": True, "issue_counts": {}},
        )
        monkeypatch.setattr(self.window, "_update_derivadas_button_state", lambda: None)

        self.window.update_derivadas_from_sources()
        QApplication.processEvents()

        assert "Falha ao atualizar derivadas" in self.window.status_label.text()

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

    def test_update_derivadas_button_state_uses_materialized_summary_when_series_is_empty(self, tmp_path):
        btn = getattr(self.window, "adv_derivadas_especificas_button", None)
        if btn is None:
            btn = self.window._adv_ctx["adv_derivadas_especificas_button"]

        db_path = tmp_path / "derivadas_summary.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE ssa_derivada_summary (
                    ssa TEXT PRIMARY KEY,
                    direct_parents_count INTEGER,
                    direct_children_count INTEGER,
                    ancestors_count INTEGER,
                    descendants_count INTEGER,
                    has_cycle INTEGER
                )
                """
            )
            conn.execute(
                """
                INSERT INTO ssa_derivada_summary (
                    ssa, direct_parents_count, direct_children_count, ancestors_count, descendants_count, has_cycle
                ) VALUES ('1001', 0, 3, 0, 3, 0)
                """
            )
            conn.commit()

        self.window._df_last_search_filtered = pd.DataFrame(
            {
                "numero_ssa": ["1001", "1002"],
                "derivada_de": ["", "None"],
            }
        )
        with patch.object(gui_ssa, "DB_PATH", str(db_path)):
            self.window._update_derivadas_button_state()
        assert btn.isEnabled() is True

    def test_reorganize_advanced_filters_grid_handles_removed_emissor_responsavel_widget(self):
        filter_tab_idx = next(
            idx for idx, ctx in enumerate(self.window._tab_contexts)
            if ctx.get("tab_kind") == "filters"
        )
        self.window.main_tabs.setCurrentIndex(filter_tab_idx)
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(1501)
        self.window._reorganize_advanced_filters_grid(1201)
        self.window._reorganize_advanced_filters_grid(800)
        assert self.window._adv_filters_main_grid.count() > 0

    def test_save_advanced_filters_default_keeps_snapshot_immutable(self):
        from gui import gui_ssa

        original_settings = dict(gui_ssa.GUI_MAIN_PREFERENCES.get("gui_settings", {}))
        try:
            self.window._advanced_filters = {"situacao": ["STE"]}
            with patch.object(self.window, "_apply_advanced_filters_from_ui", return_value=None), patch.object(self.window, "_persist_gui_preferences", return_value=None):
                self.window._save_advanced_filters_default()
            self.window._advanced_filters["situacao"].append("SCA")

            saved = gui_ssa.GUI_MAIN_PREFERENCES["gui_settings"]["advanced_filters_default"]["situacao"]
            assert saved == ["STE"]
        finally:
            gui_ssa.GUI_MAIN_PREFERENCES["gui_settings"] = original_settings

    def test_on_filter_finished_ignores_stale_request(self):
        self.window._active_filter_request_id = 10
        original = self.window._df_last_search_filtered.copy()
        stale_df = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(stale_df, request_id=9)

        assert self.window._df_last_search_filtered.equals(original)

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

    def test_initiate_filtering_keeps_slow_previous_worker_retained_until_finished(self):
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

    def test_on_load_error_ignores_stale_request(self):
        self.window._active_data_load_request_id = 10
        self.window.status_label.setText("Status: OK")

        with patch("gui.gui_ssa.QMessageBox.critical") as critical:
            self.window.on_load_error("erro", request_id=9)

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

        with patch("gui.gui_ssa.os.path.exists", return_value=True), patch("gui.gui_ssa.DataLoaderWorker", _FakeLoaderWorker):
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

        with patch("gui.gui_ssa.os.path.exists", return_value=True), patch("gui.gui_ssa.DataLoaderWorker", _FakeLoaderWorker):
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

        with patch("gui.gui_ssa.os.path.exists", return_value=True), patch("gui.gui_ssa.DataLoaderWorker", _NewLoaderWorker):
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

        with patch("gui.gui_ssa.os.path.exists", return_value=True), patch("gui.gui_ssa.DataLoaderWorker", _NewLoaderWorker):
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

        with patch.object(self.window, "_refresh_responsavel_options", wraps=self.window._refresh_responsavel_options) as refresh_mock:
            self.window._schedule_sector_options_refresh()
            QTest.qWait(int(self.window._sector_debounce_timer.interval()) + 80)
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

        with patch.object(self.window, "_apply_divisao_to_setor_checks", side_effect=_recursive_apply) as apply_mock:
            with patch.object(self.window, "_schedule_sector_options_refresh") as schedule_mock:
                self.window._on_adv_sector_selection_changed()

        assert apply_mock.call_count == 1
        assert reentry_attempts["count"] == 1
        schedule_mock.assert_called_once()

    def test_prune_retired_loader_workers_removes_stale_refs_without_finished_signal(self):
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
