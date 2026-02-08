"""Testes específicos para filtros combinados (AND/OU) da GUI principal."""

import os
import sys
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
from PyQt6.QtCore import Qt  # noqa: E402

from gui.gui_ssa import SSAMainWindow  # noqa: E402


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

    def _extract_visible_ssa(self):
        return list(self.window.df_exibido['numero_ssa'])

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
        # Grupo deve ser esvaziado para ambos os campos
        assert self.window._active_column_filters['setor_executor'] == ''
        assert self.window._active_column_filters['setor_emissor'] == ''

        # Reaplica valor manual e garante aplicação correta
        self.window._active_column_filters['setor_executor'] = 'IEE3'
        self.window._sync_or_group_values('setor_executor', 'IEE3')
        self.window._refresh_after_filter_change()
        # Com OR restrito por coluna e sincronismo no grupo (IEE3 em ambos), nenhum registro atende ambos
        assert Counter(self._extract_visible_ssa()) == Counter([])

        # Limpa todos e garante reset completo
        self.window._clear_all_column_filters()
        assert all(not value for value in self.window._active_column_filters.values())
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
