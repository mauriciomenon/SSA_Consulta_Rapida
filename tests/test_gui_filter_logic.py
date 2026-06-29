"""Testes específicos para filtros combinados (AND/OU) da GUI principal."""

import copy
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from collections import Counter, OrderedDict
from types import SimpleNamespace
from typing import Any, Literal, TypedDict, cast
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

from core import app_logic  # noqa: E402
from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, QSize, Qt, QTimer, QUrl  # noqa: E402
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QFont, QMouseEvent, QResizeEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QLineEdit  # noqa: E402
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QGroupBox, QSpinBox  # noqa: E402
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QScrollArea  # noqa: E402

from gui import gui_ssa  # noqa: E402
from gui.gui_config import COLUMN_HEADER_LABEL_VARIANTS  # noqa: E402
from gui.gui_config import DEFAULT_COLUMN_DISPLAY_NAMES  # noqa: E402
from gui.gui_config import DEFAULT_COLUMN_WIDTHS  # noqa: E402
from gui.gui_ssa import SSAMainWindow  # noqa: E402
from gui.mixins import filter_gui_ssa_mixin as filter_mixin  # noqa: E402
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from gui.ssa import details_derivadas_model  # noqa: E402
from gui.ssa import filter_aliases  # noqa: E402
from gui.ssa import filter_domain_rules  # noqa: E402
from gui.ssa import gui_filters_advanced_layout as advanced_layout  # noqa: E402
from gui.ssa import gui_filters_advanced_ui as advanced_ui  # noqa: E402
from gui.ssa import gui_filters_multiselect_menu as advanced_menu  # noqa: E402
from gui.ssa import gui_table as ssa_gui_table  # noqa: E402
from gui.ssa.gui_filters_advanced_specs import (  # noqa: E402
    ADVANCED_RESPONSAVEL_MULTISELECT_SPECS,
    ADVANCED_STANDARD_MULTISELECT_SPECS,
    ADVANCED_YEAR_MULTISELECT_SPECS,
)
from gui.ssa import gui_workers as ssa_gui_workers  # noqa: E402
from gui.ssa.filter_profile_logic import (  # noqa: E402
    NormalizedFilterProfile,
    NormalizedOrGroup,
)
from gui.ssa.filter_summary_presenter import SUMMARY_BUTTON_POOL_LIMIT  # noqa: E402
from gui.widgets.column_filter_dialog import ColumnFilterDialog  # noqa: E402
from gui.widgets.column_manager_dialog import ColumnManagerDialog  # noqa: E402
from gui.widgets.filter_help_dialog import FilterHelpDialog  # noqa: E402
from utils.themes import get_theme_roles  # noqa: E402

ORIGINAL_LOAD_DATA = SSAMainWindow.load_data


def test_snapshot_search_text_logs_deleted_widget_runtime_error(caplog):
    from gui.ssa.filter_search_undo_controller import _snapshot_search_text

    class _BrokenWindow:
        @property
        def _active_filter_search_display(self):
            raise RuntimeError("wrapped C/C++ object has been deleted")

    with caplog.at_level("DEBUG"):
        assert _snapshot_search_text(_BrokenWindow()) == ""

    assert "Falha ao capturar texto de busca para snapshot" in caplog.text
    assert "wrapped C/C++ object has been deleted" in caplog.text


def test_refresh_derivadas_theme_continues_after_context_and_dead_dialog(
    monkeypatch, caplog
):
    class _DeadDialog:
        def __getattribute__(self, name):
            if name == "_ssa_details_dialog_presenter":
                raise RuntimeError("wrapped C/C++ object has been deleted")
            return super().__getattribute__(name)

    class _Presenter:
        def __init__(self):
            self.refreshed = False

        def refresh_after_theme(self):
            self.refreshed = True

    live_presenter = _Presenter()
    live_dialog = SimpleNamespace(_ssa_details_dialog_presenter=live_presenter)
    window = SimpleNamespace(
        _details_current_series_for_derivadas=pd.Series({"numero_ssa": "1"}),
        _details_current_derivadas_font_family="monospace",
        _details_context_state={
            "current_ssa": "1",
            "entries": [{"ssa": "1", "series": pd.Series({"numero_ssa": "1"})}],
        },
        _open_details_dialogs=[_DeadDialog(), live_dialog],
    )

    monkeypatch.setattr(
        ssa_gui_details,
        "_update_main_details_derivadas_panel",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ssa_gui_details,
        "_render_derivadas_context_entry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with caplog.at_level("WARNING"):
        ssa_gui_details.refresh_derivadas_views_after_theme(window)

    assert live_presenter.refreshed is True
    assert "Failed to refresh derivadas context entry after theme" in caplog.text


class _RetiredWorkerGlobalsSnapshot(TypedDict):
    data_loader_workers: list[Any]
    data_loader_meta: dict[Any, Any]
    rescan_workers: list[Any]
    rescan_meta: dict[Any, Any]
    filter_workers: list[Any]
    max_data_loader_workers: Literal[64]
    max_rescan_workers: Literal[8]
    max_filter_workers: Literal[64]


class TestGUIFilterLogic:
    """Valida filtros com perfis OR e exclusões complementares."""

    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self._ssa_sync_filter_was_set = "SSA_SYNC_FILTER" in os.environ
        self._ssa_sync_filter_snapshot = os.environ.get("SSA_SYNC_FILTER")
        os.environ["SSA_SYNC_FILTER"] = "1"
        self._gui_main_preferences_snapshot = copy.deepcopy(
            gui_ssa.GUI_MAIN_PREFERENCES
        )
        self._retired_worker_globals_snapshot: _RetiredWorkerGlobalsSnapshot = {
            "data_loader_workers": list(gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS),
            "data_loader_meta": dict(gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META),
            "rescan_workers": list(gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS),
            "rescan_meta": dict(gui_ssa.GLOBAL_RETIRED_RESCAN_META),
            "filter_workers": [],
            "max_data_loader_workers": gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            "max_rescan_workers": gui_ssa.MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            "max_filter_workers": filter_mixin.MAX_GLOBAL_RETIRED_FILTER_WORKERS,
        }
        gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.clear()
        gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.clear()
        gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS.clear()
        gui_ssa.GLOBAL_RETIRED_RESCAN_META.clear()
        self._saved_filters_tmpdir = tempfile.TemporaryDirectory()
        self._saved_filters_path = os.path.join(
            self._saved_filters_tmpdir.name, "gui_saved_filters.json"
        )
        self._saved_filters_path_patch = patch.object(
            filter_mixin,
            "get_gui_saved_filters_path",
            lambda: self._saved_filters_path,
        )
        self._saved_filters_path_patch.start()
        self._load_patch = patch.object(SSAMainWindow, "load_data", lambda self: None)
        self._load_patch.start()
        self.window = SSAMainWindow()
        self.window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
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

    def _panel_context(self) -> dict[str, Any]:
        return self.window._filter_panel_context

    def _iter_panel_contexts(self):
        yield self._panel_context()

    def _column_filter_cache_token(self, df: pd.DataFrame) -> str:
        cached = self.window._column_filter_frame_tokens[id(df)]
        cached_ref, cache_token = cached
        assert cached_ref() is df
        return cache_token

    def _set_filter_panel_tab(self, panel: str) -> dict[str, Any]:
        target_index = 1 if panel in {"filters", "advanced"} else 0
        ctx = self._panel_context()
        tab_bar = ctx["filter_panel_tab_bar"]
        tab_bar.setCurrentIndex(target_index)
        QApplication.processEvents()
        return ctx

    def _load_responsavel_filter_contract_df(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "numero_ssa": [202600001, 202600002, 202600003, 202600004],
                "situacao": ["APV", "STE", "APV", "SCA"],
                "derivada_de": ["", "", "", ""],
                "localizacao_codigo": ["LOC1", "LOC2", "LOC3", "LOC4"],
                "descricao_localizacao": ["Desc"] * 4,
                "equipamento": ["EQ1"] * 4,
                "semana_cadastro": [202501, 202601, 202501, 202701],
                "semana_programada": [202503] * 4,
                "semana_executada": [202501, 202502, 202503, 202504],
                "data_cadastro": [
                    "2025-01-01",
                    "2026-01-01",
                    "2025-05-01",
                    "2027-01-01",
                ],
                "descricao_ssa": ["Teste A", "Teste B", "Teste C", "Teste D"],
                "setor_executor": ["IEE3", "IEE3", "MEL4", "MEL4"],
                "setor_emissor": ["ABC", "XYZ", "ABC", "MEL4"],
                "descricao_execucao": ["Exec A", "Exec B", "Exec C", "Exec D"],
                "solicitante": ["Sol A", "Sol B", "Sol A", "Sol C"],
                "responsavel_programacao": ["Prog A", "Prog B", "Prog A", "Prog C"],
                "responsavel_execucao": ["Exec A", "Exec B", "Exec A", "Exec C"],
                "num_reprogramacoes": [0, 1, 2, 2],
                "grau_prioridade_emissao": [1, 2, 1, 3],
                "grau_prioridade_planejamento": [2, 2, 3, 1],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self._set_filter_panel_tab("filters")
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        return df

    def _toggle_responsavel_filter_value(
        self,
        *,
        prefix: str,
        value: str,
        exclude: bool = False,
    ):
        self.window._ensure_responsavel_options_materialized(target_prefix=prefix)
        QApplication.processEvents()
        checks_attr = f"{prefix}_exclude_checks" if exclude else f"{prefix}_checks"
        checks = getattr(self.window, checks_attr, []) or []
        target = next(
            check
            for check in checks
            if str(check.property("value") or "") == value
        )
        target.setChecked(True)
        QApplication.processEvents()
        return target

    def _toggle_advanced_multiselect_value(
        self,
        *,
        prefix: str,
        value: str,
        exclude: bool = False,
    ):
        checks_attr = f"{prefix}_exclude_checks" if exclude else f"{prefix}_checks"
        checks = getattr(self.window, checks_attr, []) or []
        target = next(
            check
            for check in checks
            if str(check.property("value") or "") == value
        )
        target.setChecked(True)
        QApplication.processEvents()
        self._wait_until_timer_inactive(self.window._advanced_apply_timer)
        return target

    def _assert_filter_result_contract(
        self,
        *,
        filter_key: str,
        expected_ssas: set[int],
        expected_visual_column: str | None = "",
    ):
        assert set(self.window.df_exibido["numero_ssa"].astype(int).tolist()) == (
            expected_ssas
        )
        assert self.window._advanced_filters_active is True
        if expected_visual_column is not None:
            visual_column = expected_visual_column or filter_key
            assert visual_column in self.window._get_visual_filter_columns()
        status_text = str(self.window.filtered_status_label.text() or "")
        assert f"{len(expected_ssas)} de {len(self.window.df_completo)} SSAs" in (
            status_text
        )

    def _assert_multiselect_button_reflects_value(
        self,
        *,
        prefix: str,
        value: str,
        exclude: bool = False,
    ):
        button = getattr(self.window, f"{prefix}_button")
        tooltip = str(button.toolTip() or "")
        assert value in tooltip
        if exclude:
            assert "Diferente:" in tooltip
        else:
            assert "Incluir:" in tooltip
        assert button.isEnabled() is True

    def teardown_method(self):
        try:
            self._load_patch.stop()
            self._saved_filters_path_patch.stop()
            for dialog in list(getattr(self.window, "_open_details_dialogs", [])):
                dialog.close()
            self.window.close()
        finally:
            self._saved_filters_tmpdir.cleanup()
            gui_ssa.GUI_MAIN_PREFERENCES.clear()
            gui_ssa.GUI_MAIN_PREFERENCES.update(self._gui_main_preferences_snapshot)
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS[:] = (
                self._retired_worker_globals_snapshot["data_loader_workers"]
            )
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.clear()
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.update(
                self._retired_worker_globals_snapshot["data_loader_meta"]
            )
            gui_ssa.GLOBAL_RETIRED_RESCAN_WORKERS[:] = (
                self._retired_worker_globals_snapshot["rescan_workers"]
            )
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.clear()
            gui_ssa.GLOBAL_RETIRED_RESCAN_META.update(
                self._retired_worker_globals_snapshot["rescan_meta"]
            )
            gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS = (
                self._retired_worker_globals_snapshot["max_data_loader_workers"]
            )
            gui_ssa.MAX_GLOBAL_RETIRED_RESCAN_WORKERS = (
                self._retired_worker_globals_snapshot["max_rescan_workers"]
            )
            if self._ssa_sync_filter_was_set:
                os.environ["SSA_SYNC_FILTER"] = str(self._ssa_sync_filter_snapshot)
            else:
                os.environ.pop("SSA_SYNC_FILTER", None)

    def _extract_visible_ssa(self):
        return list(self.window.df_exibido["numero_ssa"])

    def _first_persistent_filter_tag_button(self):
        for i in range(self.window.filter_tags_layout.count()):
            tag_item = self.window.filter_tags_layout.itemAt(i)
            tag_widget = tag_item.widget() if tag_item else None
            tag_layout = tag_widget.layout() if tag_widget else None
            if tag_layout is None:
                continue
            tag_button_item = tag_layout.itemAt(0)
            tag_button = tag_button_item.widget() if tag_button_item else None
            if isinstance(tag_button, QPushButton):
                return tag_button
        return None

    def _persistent_filter_tag_button_pairs(self):
        pairs = []
        for i in range(self.window.filter_tags_layout.count()):
            tag_item = self.window.filter_tags_layout.itemAt(i)
            tag_widget = tag_item.widget() if tag_item else None
            tag_layout = tag_widget.layout() if tag_widget else None
            if tag_layout is None:
                continue
            tag_button_item = tag_layout.itemAt(0)
            remove_button_item = tag_layout.itemAt(1)
            tag_button = tag_button_item.widget() if tag_button_item else None
            remove_button = (
                remove_button_item.widget() if remove_button_item else None
            )
            if isinstance(tag_button, QPushButton) and isinstance(
                remove_button, QPushButton
            ):
                pairs.append((tag_button, remove_button))
        return pairs

    def _wait_until_timer_inactive(self, timer: QTimer, timeout_ms: int = 1000) -> None:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while timer.isActive() and time.monotonic() < deadline:
            QApplication.processEvents()
            cast(Any, QTest).qWait(10)
        QApplication.processEvents()
        elapsed = time.monotonic() - (deadline - (timeout_ms / 1000))
        assert timer.isActive() is False, (
            "timeout waiting for timer to stop: "
            f"timer={timer!r} active={timer.isActive()} "
            f"timeout_ms={timeout_ms} deadline={deadline:.3f} elapsed={elapsed:.3f}"
        )

    def _build_realistic_base_df_50(self) -> pd.DataFrame:
        snapshot_path = os.path.join(
            project_root,
            "tests",
            "fixtures",
            "gui_filter_realistic_50.json",
        )
        with open(snapshot_path, encoding="utf-8") as handle:
            snapshot_rows = json.load(handle)
        return pd.DataFrame(snapshot_rows)

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
            if item is None:
                continue
            row_widget = item.widget()
            if row_widget is None:
                continue
            row_layout = row_widget.layout()
            if row_layout is None or row_layout.count() < 5:
                continue
            row_items = [row_layout.itemAt(index) for index in range(5)]
            if any(row_item is None for row_item in row_items):
                continue
            label_widget, edit_widget, apply_widget, clear_widget, hide_widget = [
                row_item.widget() for row_item in row_items if row_item is not None
            ]
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

    def test_column_selector_button_keeps_internal_summary_and_stays_out_of_top_toolbar(
        self,
    ):
        selector = getattr(self.window, "column_selector", None)
        assert selector is not None
        text = str(selector.manage_button.text() or "")
        assert text.startswith("Colunas Visiveis:")
        assert selector.isVisible() is False
        assert not hasattr(selector, "summary_label")

    def test_top_toolbar_omits_update_derivadas_button(self):
        button = getattr(self.window, "update_derivadas_button", None)
        assert button is None
        visible_named = [
            btn
            for btn in self.window.findChildren(QPushButton)
            if str(btn.text() or "") == "Atualizar Derivadas" and btn.isVisible()
        ]
        assert visible_named == []

    def test_top_toolbar_exposes_sam_button_and_filtered_status_box(self):
        sam_button = getattr(self.window, "open_sam_button", None)
        generate_button = getattr(self.window, "load_button", None)
        load_xls_button = getattr(self.window, "api_button", None)
        filtered_status = getattr(self.window, "filtered_status_label", None)
        rescan_button = getattr(self.window, "rescan_button", None)

        assert sam_button is not None
        assert str(sam_button.text() or "") == "Abrir SAM"
        assert generate_button is not None
        assert str(generate_button.text() or "") == "Gerar xls"
        assert load_xls_button is not None
        assert str(load_xls_button.text() or "") == "Carregar xls"
        toolbar = getattr(self.window, "_top_toolbar_layout", None)
        assert toolbar is not None
        assert [toolbar.itemAt(index).widget() for index in range(3)] == [
            sam_button,
            generate_button,
            load_xls_button,
        ]
        assert filtered_status is not None
        assert str(filtered_status.text() or "") == "0 de 0 SSAs"
        assert rescan_button is not None
        assert rescan_button.isVisible() is False

    def test_search_and_filter_summary_place_controls_in_expected_order(self):
        main_ctx = self._panel_context()
        search_input = main_ctx["search_input"]
        quick_search_box = main_ctx["quick_search_box"]
        search_button = main_ctx["search_button"]
        clear_filter_button = main_ctx["clear_filter_button"]
        save_filter_button = main_ctx["save_filter_button"]
        filter_tags_widget = main_ctx["filter_tags_widget"]
        paginator = main_ctx["paginator"]
        column_selector = main_ctx["column_selector"]
        quick_label = main_ctx["quick_setor_executor_label"]
        quick_combo = main_ctx["quick_setor_executor_combo"]
        quick_box = main_ctx["quick_setor_executor_box"]
        quick_situacao_label = main_ctx["quick_situacao_label"]
        quick_situacao_scroll = main_ctx["quick_situacao_scroll"]
        filters_summary_frame = main_ctx["filters_summary_frame"]
        clear_all_filters_btn = main_ctx["clear_all_filters_btn"]
        export_list_btn = main_ctx["export_list_btn"]
        undo_filter_btn = main_ctx["undo_filter_btn"]
        theme_button = getattr(self.window, "theme_button", None)
        preferences_button = getattr(self.window, "preferences_button", None)
        status_progress_box = getattr(self.window, "status_progress_box", None)
        filtered_status_label = getattr(self.window, "filtered_status_label", None)
        week_label = getattr(self.window, "week_label", None)

        QApplication.processEvents()

        tooltip = str(save_filter_button.toolTip() or "")
        assert "search_label" not in main_ctx
        assert str(save_filter_button.text() or "") == "Salvar Filtros"
        assert str(export_list_btn.text() or "") == "Exportar Lista"
        assert str(search_button.text() or "") == "↵"
        assert str(clear_filter_button.text() or "") == "⌫"
        assert str(undo_filter_btn.text() or "") == "↺"
        assert "QFrame#quickSearchBox" in str(quick_search_box.styleSheet() or "")
        assert "border:0" in str(search_button.styleSheet() or "")
        assert "background:transparent" in str(search_button.styleSheet() or "")
        assert "border:0" in str(clear_filter_button.styleSheet() or "")
        assert "background:transparent" in str(clear_filter_button.styleSheet() or "")
        assert "color:" in str(save_filter_button.styleSheet() or "")
        assert "busca" in tooltip.casefold()
        assert "filtros por texto" in tooltip
        assert "filtros por selecao" in tooltip
        assert 0 < filter_tags_widget.maximumWidth() <= 280
        assert str(clear_all_filters_btn.text() or "") == "⌫"
        assert save_filter_button.parentWidget() is not filters_summary_frame
        assert export_list_btn.parentWidget() is not filters_summary_frame
        assert undo_filter_btn.parentWidget() is not filters_summary_frame
        search_row_x = {
            "undo": undo_filter_btn.mapToGlobal(undo_filter_btn.rect().topLeft()).x(),
            "box": quick_search_box.mapToGlobal(quick_search_box.rect().topLeft()).x(),
            "clear": clear_filter_button.mapToGlobal(
                clear_filter_button.rect().topLeft()
            ).x(),
            "input": search_input.mapToGlobal(search_input.rect().topLeft()).x(),
            "apply": search_button.mapToGlobal(search_button.rect().topLeft()).x(),
            "export": export_list_btn.mapToGlobal(export_list_btn.rect().topLeft()).x(),
            "save": save_filter_button.mapToGlobal(
                save_filter_button.rect().topLeft()
            ).x(),
        }
        assert search_row_x["undo"] < search_row_x["box"]
        assert search_row_x["clear"] < search_row_x["input"] < search_row_x["apply"]
        assert search_row_x["box"] < search_row_x["export"] < search_row_x["save"]
        summary_layout = filters_summary_frame.layout()
        assert summary_layout is not None
        assert summary_layout.itemAt(0).widget() is clear_all_filters_btn
        assert summary_layout.itemAt(1).layout() is not None
        assert (
            filter_tags_widget.mapToGlobal(filter_tags_widget.rect().topLeft()).x()
            > search_input.mapToGlobal(search_input.rect().topLeft()).x()
        )
        search_y = search_input.mapToGlobal(search_input.rect().topLeft()).y()
        summary_y = filters_summary_frame.mapToGlobal(
            filters_summary_frame.rect().topLeft()
        ).y()
        paginator_y = paginator.mapToGlobal(paginator.rect().topLeft()).y()
        assert search_y < summary_y < paginator_y
        assert theme_button is not None
        assert preferences_button is not None
        assert status_progress_box is not None
        assert filtered_status_label is not None
        assert week_label is not None
        assert str(preferences_button.text() or "") == "Preferencias"
        assert column_selector.isVisible() is False
        assert not getattr(paginator, "show_page_size_controls", True)
        page_size_label = getattr(paginator, "page_size_label", None)
        assert page_size_label is not None
        assert page_size_label.parentWidget() is None
        assert "font-size: 11px" in str(paginator.page_info_label.styleSheet() or "")
        assert (
            preferences_button.mapToGlobal(preferences_button.rect().topLeft()).x()
            < theme_button.mapToGlobal(theme_button.rect().topLeft()).x()
        )
        assert (
            status_progress_box.mapToGlobal(status_progress_box.rect().topLeft()).x()
            > self.window.api_button.mapToGlobal(self.window.api_button.rect().topLeft()).x()
        )
        assert (
            filtered_status_label.mapToGlobal(filtered_status_label.rect().topLeft()).x()
            > status_progress_box.mapToGlobal(status_progress_box.rect().topRight()).x()
        )
        assert (
            week_label.mapToGlobal(week_label.rect().topLeft()).x()
            > filtered_status_label.mapToGlobal(filtered_status_label.rect().topRight()).x()
        )
        assert str(quick_label.text() or "") == "Setor Executor:"
        assert quick_situacao_label.isVisible() is False
        assert str(quick_situacao_label.text() or "") == ""
        quick_label_pos = quick_label.mapToGlobal(quick_label.rect().topLeft())
        quick_combo_pos = quick_combo.mapToGlobal(quick_combo.rect().topLeft())
        quick_box_pos = quick_box.mapToGlobal(quick_box.rect().topLeft())
        assert abs(quick_label_pos.y() - quick_combo_pos.y()) <= 6
        assert quick_label_pos.x() < quick_combo_pos.x()
        assert quick_box_pos.x() > paginator.mapToGlobal(paginator.rect().topLeft()).x()
        assert quick_combo_pos.x() > paginator.mapToGlobal(paginator.rect().topLeft()).x()
        assert quick_combo.height() <= 28
        assert quick_combo.height() >= 20
        assert quick_combo.maximumWidth() <= 86
        assert quick_combo.minimumWidth() <= 74
        assert quick_box.width() <= 186
        assert quick_situacao_scroll.widgetResizable() is True
        assert quick_situacao_scroll.height() <= 24
        assert quick_situacao_scroll.horizontalScrollBarPolicy().name.endswith(
            "AsNeeded"
        )
        quick_scroll_style = str(quick_situacao_scroll.styleSheet() or "")
        assert "QScrollBar:horizontal" in quick_scroll_style
        assert "height: 4px" in quick_scroll_style
        parent_widget = quick_combo.parentWidget()
        assert parent_widget is not None
        right_gap = parent_widget.rect().right() - quick_combo.geometry().right()
        assert right_gap <= 24

    def test_filter_panel_uses_local_tab_bar_without_duplicate_main_pages(self):
        main_ctx = self._panel_context()
        filters_ctx = self._panel_context()

        assert self.window.main_tabs.currentIndex() == 0
        assert self.window.main_tabs.count() == 1
        assert self.window.main_tabs.tabBar().isVisible() is False
        assert main_ctx["filters_panel_group"] is filters_ctx["filters_panel_group"]
        assert main_ctx["filters_panel_stack"] is filters_ctx["filters_panel_stack"]
        assert "col_filters_hint" not in main_ctx
        details_tab_bar = main_ctx["details_tab_bar"]
        assert details_tab_bar.usesScrollButtons() is False
        assert details_tab_bar.minimumWidth() >= 244
        assert main_ctx["details_title"].isVisible() is False
        tab_bar = main_ctx["filter_panel_tab_bar"]
        title = main_ctx["filter_panel_title"]
        clear_selection_filters_btn = main_ctx["clear_selection_filters_btn"]
        stack = main_ctx["filters_panel_stack"]

        assert isinstance(tab_bar, QtWidgets.QTabBar)
        assert tab_bar.count() == 2
        assert tab_bar.tabText(0) == "Por texto"
        assert tab_bar.tabText(1) == "Selecao"
        assert tab_bar.height() <= 22
        tab_css = str(tab_bar.styleSheet() or "")
        assert "QTabBar::tab:selected" in tab_css
        assert "font-weight:700;" in tab_css
        assert "QTabBar::tab:!selected" in tab_css
        assert "font-weight:400;" in tab_css
        assert stack.currentIndex() == 1
        assert str(title.text() or "") == "Filtros por Selecao"
        assert str(clear_selection_filters_btn.text() or "") == "x"
        assert clear_selection_filters_btn.width() <= 24
        assert clear_selection_filters_btn.isVisible() is False
        assert getattr(self.window, "_active_filter_panel_kind", None) == "advanced"

        self.window._advanced_filters = {"situacao": ["SAD"]}
        self.window._advanced_filters_active = True
        self.window._sync_selection_filters_clear_button()
        QApplication.processEvents()
        assert clear_selection_filters_btn.isVisible() is True
        cast(Any, QTest).mouseClick(
            clear_selection_filters_btn, Qt.MouseButton.LeftButton
        )
        QApplication.processEvents()
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert clear_selection_filters_btn.isVisible() is False

        tab_bar.setCurrentIndex(1)
        QApplication.processEvents()

        assert self.window.main_tabs.currentIndex() == 0
        assert stack.currentIndex() == 1
        assert str(title.text() or "") == "Filtros por Selecao"
        assert getattr(self.window, "_active_filter_panel_kind", None) == "advanced"

        tab_bar.setCurrentIndex(0)
        QApplication.processEvents()

        assert self.window.main_tabs.currentIndex() == 0
        assert stack.currentIndex() == 0
        assert str(title.text() or "") == "Filtros por Texto"
        assert getattr(self.window, "_active_filter_panel_kind", None) == "columns"

    def test_only_quick_situacao_uses_compact_font_on_macos(self, monkeypatch):
        monkeypatch.setattr(gui_ssa.sys, "platform", "darwin")

        darwin_window = SSAMainWindow()
        darwin_window._filter_worker_registry = filter_mixin.DeferredFilterWorkerRegistry()
        darwin_window.df_completo = self.base_df.copy()
        darwin_window.df_exibido = self.base_df.copy()
        darwin_window._df_last_search_filtered = self.base_df.copy()
        darwin_window.paginator.set_dataframe(self.base_df.copy())
        darwin_window.display_current_page(1)
        darwin_window._refresh_quick_situacao_buttons()
        darwin_window.show()
        QApplication.processEvents()

        try:
            toolbar_font = getattr(darwin_window, "_toolbar_compact_font", None)
            assert toolbar_font is not None
            compact_size = toolbar_font.pointSizeF()
            base_size = darwin_window.font().pointSizeF()
            assert compact_size == pytest.approx(9.0)

            default_font_widgets = [
                darwin_window.quick_setor_executor_label,
                darwin_window.quick_setor_executor_combo,
                darwin_window.status_label,
                darwin_window.week_label,
                darwin_window.filtered_status_label,
                darwin_window.api_button,
                darwin_window.preferences_button,
                darwin_window.theme_button,
            ]
            for widget in default_font_widgets:
                assert widget.font().pointSizeF() == pytest.approx(base_size)

            buttons = getattr(darwin_window, "quick_situacao_buttons", None)
            assert isinstance(buttons, dict)
            assert buttons
            for button in buttons.values():
                assert button.font().pointSizeF() < base_size

            assert darwin_window.quick_setor_executor_combo.maximumWidth() <= 86
            assert darwin_window.quick_setor_executor_box.width() <= 186
        finally:
            darwin_window.close()
            darwin_window.deleteLater()
            QApplication.processEvents()

    def test_preferred_ui_font_family_uses_platform_order(self, monkeypatch):
        monkeypatch.setattr(
            gui_ssa.QFontDatabase,
            "families",
            lambda: ["Arial", "Helvetica", "Segoe UI", "DejaVu Sans"],
        )

        gui_ssa._preferred_ui_font_family.cache_clear()
        monkeypatch.setattr(gui_ssa.sys, "platform", "darwin")
        assert gui_ssa._preferred_ui_font_family() == "Helvetica"

        gui_ssa._preferred_ui_font_family.cache_clear()
        monkeypatch.setattr(gui_ssa.sys, "platform", "win32")
        assert gui_ssa._preferred_ui_font_family() == "Segoe UI"

        gui_ssa._preferred_ui_font_family.cache_clear()
        monkeypatch.setattr(gui_ssa.sys, "platform", "linux")
        assert gui_ssa._preferred_ui_font_family() == "DejaVu Sans"
        gui_ssa._preferred_ui_font_family.cache_clear()

    def test_preferred_application_font_replaces_sans_serif_alias(self, monkeypatch):
        app = cast(Any, QApplication.instance() or QApplication([]))
        original_font = QFont(app.font())
        alias_font = QFont(original_font)
        alias_font.setFamily("Sans Serif")
        app.setFont(alias_font)
        monkeypatch.setattr(gui_ssa, "_preferred_ui_font_family", lambda: "Helvetica")

        try:
            assert gui_ssa._apply_preferred_application_font() == "Helvetica"
            assert app.font().family() == "Helvetica"
        finally:
            app.setFont(original_font)

    def test_derivadas_panel_exposes_navigation_tooltips(self):
        main_ctx = self._panel_context()
        details_tree_text = main_ctx["details_tree_text"]
        details_graph_label = main_ctx["details_graph_label"]

        assert "Clique em uma SSA" in str(details_tree_text.toolTip() or "")
        assert str(details_graph_label.toolTip() or "") == "Clique abre detalhes"

    def test_preferences_dialog_exposes_runtime_controls_and_column_entry(self, monkeypatch):
        selector = getattr(self.window, "column_selector", None)
        assert selector is not None
        selector_calls: list[str] = []

        def _fake_open_dialog():
            selector_calls.append("open")

        monkeypatch.setattr(selector, "open_dialog", _fake_open_dialog)

        captured: dict[str, Any] = {}

        class _Screen:
            @staticmethod
            def availableGeometry() -> QRect:
                return QRect(0, 0, 1280, 720)

        monkeypatch.setattr(
            gui_ssa.QApplication,
            "primaryScreen",
            staticmethod(lambda: _Screen()),
        )

        def _fake_exec(dialog):
            captured["dialog_size"] = (dialog.width(), dialog.height())
            captured["dialog_max_size"] = (
                dialog.maximumWidth(),
                dialog.maximumHeight(),
            )
            labels = [widget.text() for widget in dialog.findChildren(QLabel)]
            checks = {
                str(widget.objectName() or ""): widget.text()
                for widget in dialog.findChildren(QCheckBox)
            }
            buttons = {
                str(widget.objectName() or ""): widget
                for widget in dialog.findChildren(QPushButton)
            }
            width_spins = {
                str(widget.objectName() or ""): widget.value()
                for widget in dialog.findChildren(QSpinBox)
                if str(widget.objectName() or "").startswith("preferencesColumnWidthSpin_")
            }
            captured["labels"] = labels
            captured["checks"] = checks
            captured["buttons"] = [widget.text() for widget in buttons.values()]
            captured["width_spins"] = width_spins
            captured["groups"] = [
                widget.title()
                for widget in dialog.findChildren(QGroupBox)
            ]
            footer_label = dialog.findChild(QLabel, "preferencesFooterLabel")
            captured["footer"] = str(footer_label.text() or "") if footer_label else ""
            captured["footer_style"] = (
                str(footer_label.styleSheet() or "") if footer_label else ""
            )
            captured["has_widths_scroll"] = (
                dialog.findChild(QScrollArea, "preferencesColumnWidthsScroll")
                is not None
            )
            scroll = dialog.findChild(QScrollArea, "preferencesContentScroll")
            assert scroll is not None
            content = scroll.widget()
            assert content is not None
            content_layout = content.layout()
            captured["content_layout_type"] = type(content_layout).__name__
            captured["group_order"] = []
            if isinstance(content_layout, QtWidgets.QVBoxLayout):
                for index in range(content_layout.count()):
                    item = content_layout.itemAt(index)
                    widget = item.widget() if item is not None else None
                    if isinstance(widget, QGroupBox):
                        captured["group_order"].append(str(widget.objectName() or ""))
            columns_button = buttons.get("preferencesColumnsButton")
            assert columns_button is not None
            columns_button.click()
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert selector_calls == ["open"]
        assert captured["dialog_size"] == (860, 520)
        assert captured["dialog_max_size"][0] >= 860
        assert captured["dialog_max_size"][1] >= 520
        assert captured["labels"][:7] == [
            "Tema",
            "Modo da busca",
            "Debounce ms",
            "Linhas por pagina",
            "Largura da janela",
            "Altura da janela",
            "Alinhamento da tabela",
        ]
        assert captured["labels"][7:9] == [
            "Cache de filtros",
            "Colunas exibidas",
        ]
        assert "Colunas" in captured["buttons"]
        assert "Validar segredo no cofre" in captured["buttons"]
        assert "Gravar segredo no cofre" in captured["buttons"]
        assert "SAM API" in captured["groups"]
        assert "Interface" in captured["groups"]
        assert "Tabela e colunas exibidas" in captured["groups"]
        assert "Cache e comportamento" in captured["groups"]
        assert "Larguras de colunas" in captured["groups"]
        assert "Usuario SAM" in captured["labels"]
        assert "Chave do cofre" in captured["labels"]
        assert "Senha SAM para gravar no cofre" in captured["labels"]
        assert "Setores extras (SAM API)" in captured["labels"]
        assert any(
            name.startswith("preferencesColumnWidthSpin_")
            for name in captured["width_spins"]
        )
        assert (
            captured["checks"]["preferencesAutoLoadCheck"]
            == "Carregar dados do banco ao iniciar"
        )
        assert (
            captured["checks"]["preferencesShowProgressCheck"]
            == "Mostrar progresso na barra superior"
        )
        assert (
            captured["checks"]["preferencesPaiApiSecureRequiredCheck"]
            == "Exigir cofre do sistema"
        )
        assert (
            captured["checks"]["preferencesDoubleClickDetailsCheck"]
            == "Duplo clique abre detalhes"
        )
        assert captured["content_layout_type"] == "QVBoxLayout"
        assert captured["group_order"] == [
            "preferencesInterfaceGroup",
            "preferencesTableGroup",
            "preferencesBehaviorGroup",
            "preferencesPaiApiGroup",
        ]
        assert "Restaurar padrao" in captured["buttons"]
        assert captured["footer"].startswith("Versao ")
        assert len(captured["footer"].split(" | ")) == 5
        assert "font-weight:600" in captured["footer_style"]
        assert any(
            "Consulta REST nao exige credencial" in label
            for label in captured["labels"]
        )
        assert captured["has_widths_scroll"] is False

    def test_preferences_dialog_uses_full_width_internal_grids(self, monkeypatch):
        captured: dict[str, Any] = {}

        def _fake_exec(dialog):
            scroll = dialog.findChild(QScrollArea, "preferencesContentScroll")
            assert scroll is not None
            widths_group = dialog.findChild(QGroupBox, "preferencesColumnWidthsGroup")
            assert widths_group is not None
            widths_layout = widths_group.layout()
            assert widths_layout is not None
            support = dialog.findChild(
                QLabel, "preferencesPaiApiExtraSectorsValidationLabel"
            )
            info = dialog.findChild(QLabel, "preferencesPaiApiSecurityInfoLabel")
            assert support is not None
            assert info is not None
            first_column_fields = [
                dialog.findChild(QComboBox, "preferencesThemeCombo"),
                dialog.findChild(QSpinBox, "preferencesPageSizeSpin"),
                dialog.findChild(QComboBox, "preferencesAlignmentCombo"),
            ]
            assert all(widget is not None for widget in first_column_fields)
            first_item = widths_layout.itemAt(0)
            assert first_item is not None
            captured["widths_alignment"] = int(first_item.alignment())
            captured["support_style"] = str(support.styleSheet() or "")
            captured["info_style"] = str(info.styleSheet() or "")
            captured["first_column_right_edges"] = [
                int(widget.geometry().x() + widget.geometry().width())
                for widget in first_column_fields
                if widget is not None
            ]
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert captured["widths_alignment"] == 0
        assert len(set(captured["first_column_right_edges"])) == 1
        assert not re.search(
            r"(^|;)\s*color:\s*palette\(mid\)\s*(;|$)",
            captured["support_style"],
        )
        assert not re.search(
            r"(^|;)\s*color:\s*palette\(mid\)\s*(;|$)",
            captured["info_style"],
        )
        assert "color:" in captured["support_style"]
        assert "color:" in captured["info_style"]

    def test_preferences_dialog_applies_runtime_settings(self, monkeypatch):
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_mode = gui_settings.get("default_filter_mode")
        previous_delay = gui_settings.get("debounce_delay")
        previous_cache = gui_settings.get("filter_cache_size")
        previous_page_size = gui_settings.get("page_size")
        previous_window_width = gui_settings.get("window_width")
        previous_window_height = gui_settings.get("window_height")
        previous_auto_load = gui_settings.get("auto_load")
        previous_progress = gui_settings.get("show_progress_bar")
        previous_sort = gui_settings.get("enable_column_sorting")
        previous_show_details = gui_settings.get("show_details_panel")
        previous_double_click = gui_settings.get("enable_double_click_details")
        previous_cache_enabled = gui_settings.get("cache_enabled")
        previous_cache_auto_clear = gui_settings.get("cache_auto_clear")
        previous_pai_api = copy.deepcopy(gui_settings.get("pai_api"))
        previous_column_widths = copy.deepcopy(gui_ssa.GUI_MAIN_PREFERENCES.get("column_widths"))
        previous_saved_widths = copy.deepcopy(getattr(self.window, "_saved_gui_column_widths", {}))
        previous_runtime_widths = copy.deepcopy(getattr(self.window, "_gui_column_pixel_widths", {}))
        paginator = getattr(self.window, "paginator", None)
        assert paginator is not None
        clear_calls: list[str] = []
        refresh_calls: list[str] = []

        def _fake_clear_filter_cache():
            clear_calls.append("clear")

        def _fake_initialize_refresh():
            refresh_calls.append("refresh")

        monkeypatch.setattr(self.window, "clear_filter_cache", _fake_clear_filter_cache)
        monkeypatch.setattr(
            self.window,
            "initialize_pai_api_auto_refresh",
            _fake_initialize_refresh,
        )

        def _fake_exec(dialog):
            search_mode_combo = dialog.findChild(
                QComboBox, "preferencesSearchModeCombo"
            )
            debounce_spin = dialog.findChild(QSpinBox, "preferencesDebounceSpin")
            page_size_spin = dialog.findChild(QSpinBox, "preferencesPageSizeSpin")
            window_width_spin = dialog.findChild(QSpinBox, "preferencesWindowWidthSpin")
            window_height_spin = dialog.findChild(QSpinBox, "preferencesWindowHeightSpin")
            cache_size_spin = dialog.findChild(QSpinBox, "preferencesCacheSizeSpin")
            auto_load_check = dialog.findChild(QCheckBox, "preferencesAutoLoadCheck")
            show_progress_check = dialog.findChild(
                QCheckBox, "preferencesShowProgressCheck"
            )
            column_sorting_check = dialog.findChild(
                QCheckBox, "preferencesColumnSortingCheck"
            )
            show_details_check = dialog.findChild(
                QCheckBox, "preferencesShowDetailsCheck"
            )
            double_click_check = dialog.findChild(
                QCheckBox, "preferencesDoubleClickDetailsCheck"
            )
            cache_enabled_check = dialog.findChild(
                QCheckBox, "preferencesCacheEnabledCheck"
            )
            cache_auto_clear_check = dialog.findChild(
                QCheckBox, "preferencesCacheAutoClearCheck"
            )
            api_enabled_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiEnabledCheck"
            )
            api_scrap_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiScrapCheck"
            )
            api_auto_refresh_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiAutoRefreshCheck"
            )
            api_interval_spin = dialog.findChild(
                QSpinBox, "preferencesPaiApiIntervalSpin"
            )
            api_limit_spin = dialog.findChild(QSpinBox, "preferencesPaiApiLimitSpin")
            api_years_spin = dialog.findChild(QSpinBox, "preferencesPaiApiYearsSpin")
            api_base_url_edit = dialog.findChild(
                QLineEdit, "preferencesPaiApiBaseUrlEdit"
            )
            api_username_edit = dialog.findChild(
                QLineEdit, "preferencesPaiApiUsernameEdit"
            )
            api_secret_service_edit = dialog.findChild(
                QLineEdit, "preferencesPaiApiSecretServiceEdit"
            )
            api_secure_required_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiSecureRequiredCheck"
            )
            descricao_width_spin = dialog.findChild(
                QSpinBox, "preferencesColumnWidthSpin_descricao_ssa"
            )
            assert search_mode_combo is not None
            assert debounce_spin is not None
            assert page_size_spin is not None
            assert window_width_spin is not None
            assert window_height_spin is not None
            assert cache_size_spin is not None
            assert auto_load_check is not None
            assert show_progress_check is not None
            assert column_sorting_check is not None
            assert show_details_check is not None
            assert double_click_check is not None
            assert cache_enabled_check is not None
            assert cache_auto_clear_check is not None
            assert api_enabled_check is not None
            assert api_scrap_check is not None
            assert api_auto_refresh_check is not None
            assert api_interval_spin is not None
            assert api_limit_spin is not None
            assert api_years_spin is not None
            assert api_base_url_edit is not None
            assert api_username_edit is not None
            assert api_secret_service_edit is not None
            assert api_secure_required_check is not None
            assert descricao_width_spin is not None

            search_mode_combo.setCurrentIndex(
                search_mode_combo.findData("regex")
            )
            debounce_spin.setValue(950)
            page_size_spin.setValue(80)
            window_width_spin.setValue(1320)
            window_height_spin.setValue(910)
            cache_size_spin.setValue(70)
            auto_load_check.setChecked(True)
            show_progress_check.setChecked(False)
            column_sorting_check.setChecked(False)
            show_details_check.setChecked(False)
            double_click_check.setChecked(False)
            cache_enabled_check.setChecked(False)
            cache_auto_clear_check.setChecked(True)
            api_enabled_check.setChecked(False)
            api_scrap_check.setChecked(False)
            api_auto_refresh_check.setChecked(True)
            api_interval_spin.setValue(15)
            api_limit_spin.setValue(150)
            api_years_spin.setValue(2)
            api_base_url_edit.setText("https://sam.internal/rest/SSA_API")
            api_username_edit.setText("sam.user")
            api_secret_service_edit.setText("scrap_report.sam.alt")
            api_secure_required_check.setChecked(False)
            descricao_width_spin.setValue(365)
            for checkbox in dialog.findChildren(QCheckBox):
                object_name = str(checkbox.objectName() or "")
                if object_name.startswith("preferencesPaiApiScope_"):
                    checkbox.setChecked(object_name == "preferencesPaiApiScope_executadas")
                if object_name.startswith("preferencesPaiApiSector_"):
                    checkbox.setChecked(object_name == "preferencesPaiApiSector_MEL4")
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        with patch.object(self.window, "resize", wraps=self.window.resize) as resize_mock:
            self.window._open_preferences_dialog()

        expected_runtime_width, expected_runtime_height = (
            self.window._fit_window_size_to_screen(1320, 910)
        )

        assert gui_settings.get("default_filter_mode") == "regex"
        assert getattr(self.window, "_cached_default_mode", None) == "regex"
        assert gui_settings.get("debounce_delay") == 950
        assert self.window._debounce_timer.interval() == 950
        assert gui_settings.get("filter_cache_size") == 70
        assert gui_settings.get("page_size") == 80
        assert gui_settings.get("window_width") == 1320
        assert gui_settings.get("window_height") == 910
        assert gui_settings.get("auto_load") is True
        assert gui_settings.get("show_progress_bar") is False
        assert gui_settings.get("enable_column_sorting") is False
        assert gui_settings.get("show_details_panel") is False
        assert gui_settings.get("enable_double_click_details") is False
        assert gui_settings.get("cache_enabled") is False
        assert gui_settings.get("cache_auto_clear") is True
        assert getattr(self.window, "_restored_page_size", None) == 80
        assert getattr(self.window, "_restored_window_width", None) == 1320
        assert getattr(self.window, "_restored_window_height", None) == 910
        assert paginator.page_size == 80
        assert getattr(self.window, "_show_progress_bar_enabled", None) is False
        assert getattr(self.window, "_column_sorting_enabled", None) is False
        assert getattr(self.window, "_details_panel_enabled", None) is False
        assert getattr(self.window, "_double_click_details_enabled", None) is False
        assert self.window.progress_bar.maximumWidth() == 0
        assert self.window.progress_bar.isVisible() is False
        assert self.window.details_group.isVisible() is False
        resize_mock.assert_any_call(expected_runtime_width, expected_runtime_height)
        assert self.window.table_widget.horizontalHeader().sectionsClickable() is False
        assert clear_calls == ["clear"]
        assert refresh_calls == ["refresh"]
        pai_api_settings = gui_settings.get("pai_api") or {}
        assert pai_api_settings.get("enabled") is False
        assert pai_api_settings.get("scrap_report_enabled") is False
        assert pai_api_settings.get("auto_refresh_enabled") is True
        assert pai_api_settings.get("auto_refresh_interval_minutes") == 15
        assert pai_api_settings.get("executor_sectors") == ["MEL4"]
        assert pai_api_settings.get("data_scopes") == ["executadas"]
        assert pai_api_settings.get("limit") == 150
        assert pai_api_settings.get("number_of_years") == 2
        assert pai_api_settings.get("base_url") == "https://sam.internal/rest/SSA_API"
        assert pai_api_settings.get("sam_username") == "sam.user"
        assert pai_api_settings.get("secret_service") == "scrap_report.sam.alt"
        assert pai_api_settings.get("secure_required") is False
        assert gui_ssa.GUI_MAIN_PREFERENCES.get("column_widths", {}).get("descricao_ssa") == 365
        assert getattr(self.window, "_saved_gui_column_widths", {}).get("descricao_ssa") == 365
        assert getattr(self.window, "_gui_column_pixel_widths", {}).get("descricao_ssa") == 365

        gui_settings["default_filter_mode"] = previous_mode
        gui_settings["debounce_delay"] = previous_delay
        gui_settings["filter_cache_size"] = previous_cache
        gui_settings["page_size"] = previous_page_size
        gui_settings["window_width"] = previous_window_width
        gui_settings["window_height"] = previous_window_height
        gui_settings["auto_load"] = previous_auto_load
        gui_settings["show_progress_bar"] = previous_progress
        gui_settings["enable_column_sorting"] = previous_sort
        gui_settings["show_details_panel"] = previous_show_details
        gui_settings["enable_double_click_details"] = previous_double_click
        gui_settings["cache_enabled"] = previous_cache_enabled
        gui_settings["cache_auto_clear"] = previous_cache_auto_clear
        gui_settings["pai_api"] = previous_pai_api
        gui_ssa.GUI_MAIN_PREFERENCES["column_widths"] = previous_column_widths
        self.window._saved_gui_column_widths = previous_saved_widths
        self.window._gui_column_pixel_widths = previous_runtime_widths

    def test_preferences_dialog_secret_buttons_delegate_to_provider(self, monkeypatch):
        validate_calls: list[tuple[str, str]] = []
        store_calls: list[tuple[str, str, str]] = []
        info_messages: list[str] = []
        warning_messages: list[str] = []

        monkeypatch.setattr(
            gui_ssa,
            "run_pai_scrap_report_secret_validate",
            lambda **kwargs: validate_calls.append(
                (kwargs["username"], kwargs["secret_service"])
            ),
        )
        monkeypatch.setattr(
            gui_ssa,
            "run_pai_scrap_report_secret_set",
            lambda **kwargs: store_calls.append(
                (kwargs["username"], kwargs["secret_service"], kwargs["password"])
            ),
        )
        monkeypatch.setattr(
            QMessageBox,
            "information",
            lambda *_args: info_messages.append(str(_args[2] if len(_args) > 2 else "")),
        )
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *_args: warning_messages.append(str(_args[2] if len(_args) > 2 else "")),
        )

        def _fake_exec(dialog):
            username = dialog.findChild(QLineEdit, "preferencesPaiApiUsernameEdit")
            secret_service = dialog.findChild(
                QLineEdit, "preferencesPaiApiSecretServiceEdit"
            )
            password = dialog.findChild(QLineEdit, "preferencesPaiApiPasswordEdit")
            executadas_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiScope_executadas"
            )
            validate_button = dialog.findChild(
                QPushButton, "preferencesPaiApiValidateSecretButton"
            )
            store_button = dialog.findChild(
                QPushButton, "preferencesPaiApiStoreSecretButton"
            )
            assert username is not None
            assert secret_service is not None
            assert password is not None
            assert executadas_check is not None
            assert validate_button is not None
            assert store_button is not None
            executadas_check.setChecked(True)
            username.setText("usr")
            secret_service.setText("scrap_report.sam")
            validate_button.click()
            password.setText("x")
            store_button.click()
            assert password.text() == ""
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert validate_calls == [("usr", "scrap_report.sam")]
        assert store_calls == [("usr", "scrap_report.sam", "x")]
        assert warning_messages == []
        assert any("validado" in message.lower() for message in info_messages)
        assert any("gravado" in message.lower() for message in info_messages)

    def test_preferences_dialog_secret_buttons_require_identity(self, monkeypatch):
        def _fake_exec(dialog):
            username = dialog.findChild(QLineEdit, "preferencesPaiApiUsernameEdit")
            secret_service = dialog.findChild(
                QLineEdit, "preferencesPaiApiSecretServiceEdit"
            )
            executadas_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiScope_executadas"
            )
            validate_button = dialog.findChild(
                QPushButton, "preferencesPaiApiValidateSecretButton"
            )
            store_button = dialog.findChild(
                QPushButton, "preferencesPaiApiStoreSecretButton"
            )
            assert username is not None
            assert secret_service is not None
            assert executadas_check is not None
            assert validate_button is not None
            assert store_button is not None
            username.clear()
            secret_service.clear()
            executadas_check.setChecked(True)
            assert validate_button.isEnabled() is False
            assert store_button.isEnabled() is False
            username.setText("usr")
            assert validate_button.isEnabled() is False
            assert store_button.isEnabled() is False
            secret_service.setText("scrap_report.sam")
            assert validate_button.isEnabled() is True
            assert store_button.isEnabled() is True
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

    def test_apply_progress_bar_preference_does_not_force_idle_visibility(self):
        self.window.progress_bar.setVisible(False)

        self.window._apply_progress_bar_preference(True)

        assert getattr(self.window, "_show_progress_bar_enabled", None) is True
        assert self.window.progress_bar.maximumWidth() == 24
        assert self.window.progress_bar.isVisible() is False

    def test_preferences_dialog_keeps_other_changes_when_page_size_save_fails(
        self, monkeypatch
    ):
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_mode = gui_settings.get("default_filter_mode")

        def _fake_save_page_size_pref(_new_size: int):
            return False

        def _fake_exec(dialog):
            search_mode_combo = dialog.findChild(
                QComboBox, "preferencesSearchModeCombo"
            )
            page_size_spin = dialog.findChild(QSpinBox, "preferencesPageSizeSpin")
            assert search_mode_combo is not None
            assert page_size_spin is not None
            search_mode_combo.setCurrentIndex(search_mode_combo.findData("exact"))
            page_size_spin.setValue(90)
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(self.window, "_save_page_size_pref", _fake_save_page_size_pref)
        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert gui_settings.get("default_filter_mode") == "exact"
        assert getattr(self.window, "_cached_default_mode", None) == "exact"
        assert "persistencia falhou" in str(self.window.status_label.text() or "")

        gui_settings["default_filter_mode"] = previous_mode

    def test_preferences_dialog_blocks_invalid_extra_sectors_before_save(
        self, monkeypatch
    ):
        warnings: list[str] = []
        previous_extra = copy.deepcopy(
            gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
            .setdefault("pai_api", {})
            .get("executor_sectors_extra")
        )

        def _fake_warning(*args):  # noqa: ANN002, ANN003
            warnings.append(str(args[2] if len(args) > 2 else ""))

        def _fake_exec(dialog):
            extra_edit = dialog.findChild(
                QLineEdit, "preferencesPaiApiExtraSectorsEdit"
            )
            extra_status = dialog.findChild(
                QLabel, "preferencesPaiApiExtraSectorsValidationLabel"
            )
            assert extra_edit is not None
            assert extra_status is not None
            extra_edit.setText("BAD TOKEN, M*")
            assert "invalidos" in str(extra_status.text() or "").lower()
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(QDialog, "exec", _fake_exec)
        monkeypatch.setattr(QMessageBox, "warning", _fake_warning)

        self.window._open_preferences_dialog()

        assert any("Corrija os Setores extras" in msg for msg in warnings)
        current_extra = (
            gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
            .setdefault("pai_api", {})
            .get("executor_sectors_extra")
        )
        assert current_extra == previous_extra

    def test_preferences_dialog_redirects_wheel_to_outer_scroll(self, monkeypatch):
        captured: dict[str, Any] = {}

        class _FakeDelta:
            def y(self) -> int:
                return 120

        class _FakeWheelEvent:
            def type(self):
                return QEvent.Type.Wheel

            def angleDelta(self):
                return _FakeDelta()

        def _fake_exec(dialog):
            content_scroll = dialog.findChild(QScrollArea, "preferencesContentScroll")
            page_size_spin = dialog.findChild(QSpinBox, "preferencesPageSizeSpin")
            assert content_scroll is not None
            assert page_size_spin is not None
            scroll_bar = content_scroll.verticalScrollBar()
            scroll_bar.setRange(0, 200)
            scroll_bar.setSingleStep(25)
            scroll_bar.setValue(50)
            assert bool(page_size_spin.property("ignoreWheelInput")) is True
            captured["handled"] = self.window.eventFilter(
                page_size_spin, _FakeWheelEvent()
            )
            captured["scroll_value"] = scroll_bar.value()
            captured["spin_value"] = page_size_spin.value()
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert captured["handled"] is True
        assert captured["scroll_value"] == 25
        assert captured["spin_value"] == 50

    def test_preferences_dialog_redirects_wheel_from_line_edit_to_outer_scroll(
        self, monkeypatch
    ):
        captured: dict[str, Any] = {}

        class _FakeDelta:
            def y(self) -> int:
                return -120

        class _FakeWheelEvent:
            def type(self):
                return QEvent.Type.Wheel

            def angleDelta(self):
                return _FakeDelta()

        def _fake_exec(dialog):
            content_scroll = dialog.findChild(QScrollArea, "preferencesContentScroll")
            page_size_spin = dialog.findChild(QSpinBox, "preferencesPageSizeSpin")
            assert content_scroll is not None
            assert page_size_spin is not None
            line_edit = page_size_spin.lineEdit()
            assert line_edit is not None
            scroll_bar = content_scroll.verticalScrollBar()
            scroll_bar.setRange(0, 200)
            scroll_bar.setSingleStep(25)
            scroll_bar.setValue(50)
            assert bool(line_edit.property("ignoreWheelInput")) is True
            captured["handled"] = self.window.eventFilter(
                line_edit, _FakeWheelEvent()
            )
            captured["scroll_value"] = scroll_bar.value()
            captured["spin_value"] = page_size_spin.value()
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert captured["handled"] is True
        assert captured["scroll_value"] == 75
        assert captured["spin_value"] == 50

    def test_preferences_dialog_warns_when_secure_storage_is_relaxed(
        self, monkeypatch
    ):
        captured: dict[str, str] = {}

        def _fake_exec(dialog):
            executadas_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiScope_executadas"
            )
            scrap_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiScrapCheck"
            )
            secure_check = dialog.findChild(
                QCheckBox, "preferencesPaiApiSecureRequiredCheck"
            )
            info_label = dialog.findChild(
                QLabel, "preferencesPaiApiSecurityInfoLabel"
            )
            assert executadas_check is not None
            assert scrap_check is not None
            assert secure_check is not None
            assert info_label is not None
            scrap_check.setChecked(True)
            executadas_check.setChecked(True)
            secure_check.setChecked(False)
            captured["info_text"] = str(info_label.text() or "")
            captured["info_style"] = str(info_label.styleSheet() or "")
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert "reduz a garantia" in captured["info_text"]
        assert "#d6a35a" in captured["info_style"]

    def test_preferences_theme_combo_uses_list_view_popup(self, monkeypatch):
        captured: dict[str, str] = {}

        def _fake_exec(dialog):
            combo = dialog.findChild(QComboBox, "preferencesThemeCombo")
            assert combo is not None
            captured["combo_style"] = str(combo.styleSheet() or "")
            captured["view_type"] = type(combo.view()).__name__
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert "combobox-popup: 0" in captured["combo_style"]
        assert captured["view_type"] == "QListView"

    def test_preferences_theme_combo_popup_does_not_use_delayed_clamp(
        self, monkeypatch
    ):
        clamp_calls: list[tuple[str, str, bool]] = []
        timer_delays: list[int] = []

        def _fake_base_show_popup(_self) -> None:
            return None

        def _fake_single_shot(delay, callback) -> None:
            timer_delays.append(int(delay))
            callback()

        def _fake_clamp(combo_box, popup) -> None:
            clamp_calls.append(
                (
                    str(combo_box.objectName() or ""),
                    type(popup).__name__,
                    popup is not None,
                )
            )

        def _fake_exec(dialog):
            combo = dialog.findChild(QComboBox, "preferencesThemeCombo")
            assert combo is not None
            combo.showPopup()
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QComboBox, "showPopup", _fake_base_show_popup)
        monkeypatch.setattr(gui_ssa.QTimer, "singleShot", _fake_single_shot)
        monkeypatch.setattr(
            gui_ssa.ssa_gui_theme_dialog,
            "clamp_theme_popup_to_screen",
            _fake_clamp,
        )
        monkeypatch.setattr(QDialog, "exec", _fake_exec)

        self.window._open_preferences_dialog()

        assert clamp_calls == []
        assert timer_delays == []

    def test_details_derivadas_tab_refreshes_when_selection_changes(self, monkeypatch):
        df = pd.DataFrame(
            {
                "numero_ssa": [1, 2],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "1"],
                "descricao_ssa": ["Teste A", "Teste B"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        def _fake_svg_deps():
            return object()

        monkeypatch.setattr(
            ssa_gui_details,
            "load_svg_render_dependencies",
            _fake_svg_deps,
        )

        def _fake_graph_html(_window, data, **_kwargs):
            return f"<svg><text>{data.get('target', '')}</text></svg>"

        def _fake_render_graph_svg_pixmap(**kwargs):
            kwargs["graph_label"].setText(kwargs["graph_svg"])
            return True

        monkeypatch.setattr(ssa_gui_details, "_build_derivadas_graph_html", _fake_graph_html)
        monkeypatch.setattr(
            ssa_gui_details,
            "render_graph_svg_pixmap",
            _fake_render_graph_svg_pixmap,
        )

        ctx = self._panel_context()
        ctx["details_tab_bar"].setCurrentIndex(1)
        QApplication.processEvents()

        self.window.table_widget.selectRow(0)
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert ctx["details_stack"].currentIndex() == 1
        assert "1" in str(self.window.details_tree_text.toPlainText() or "")
        assert "1" in str(self.window.details_graph_label.text() or "")
        assert self.window.details_graph_label.isVisible() is True

        self.window.table_widget.selectRow(1)
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert "Teste B" in str(self.window.details_text.toHtml() or "")
        assert "2" in str(self.window.details_tree_text.toPlainText() or "")
        assert "2" in str(self.window.details_graph_label.text() or "")

    def test_details_derivadas_tab_with_relations_uses_graph_and_index(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202600001", "202600002"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202600001"],
                "descricao_ssa": ["Teste A", "Teste B"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda *_args, **_kwargs: {
                "target": "202600001",
                "target_status": "APV",
                "parents": [],
                "children": [{"ssa": "202600002", "situacao": "STE"}],
                "ancestors": [],
                "descendants": [{"ssa": "202600002", "situacao": "STE"}],
                "family_roots": ["202600001"],
                "family_descendants": [
                    {"ssa": "202600002", "parent": "202600001", "situacao": "STE"}
                ],
                "related": [],
                "family_truncated": False,
            },
        )
        def _fake_svg_deps():
            return object()

        monkeypatch.setattr(
            ssa_gui_details,
            "load_svg_render_dependencies",
            _fake_svg_deps,
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_build_derivadas_graph_html",
            lambda _window, data, **_kwargs: (
                f"<svg><text>{data.get('target', '')}</text></svg>"
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "render_graph_svg_pixmap",
            lambda **kwargs: kwargs["graph_label"].setText(kwargs["graph_svg"]) or True,
        )

        ctx = self._panel_context()
        ctx["details_tab_bar"].setCurrentIndex(1)
        self.window.table_widget.selectRow(0)
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert "202600001 (APV)" in str(
            self.window.details_tree_text.toPlainText() or ""
        )
        assert "202600002 (STE)" in str(
            self.window.details_tree_text.toPlainText() or ""
        )
        assert "202600001" in str(self.window.details_graph_label.text() or "")

    def test_main_details_derivadas_panel_does_not_build_full_ssa_index(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202600001", "202600002"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202600001"],
                "descricao_ssa": ["Teste A", "Teste B"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda *_args, **_kwargs: {
                "target": "202600001",
                "target_status": "APV",
                "parents": [],
                "children": [{"ssa": "202600002", "situacao": "STE"}],
                "ancestors": [],
                "descendants": [{"ssa": "202600002", "situacao": "STE"}],
                "family_roots": ["202600001"],
                "family_descendants": [
                    {"ssa": "202600002", "parent": "202600001", "situacao": "STE"}
                ],
                "related": [],
                "family_truncated": False,
            },
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_window_ssa_series_index",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("full index should not be built")
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "load_svg_render_dependencies",
            lambda: object(),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_build_derivadas_graph_html",
            lambda _window, data, **_kwargs: (
                f"<svg><text>{data.get('target', '')}</text></svg>"
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "render_graph_svg_pixmap",
            lambda **kwargs: kwargs["graph_label"].setText(kwargs["graph_svg"]) or True,
        )

        ctx = self._panel_context()
        ctx["details_tab_bar"].setCurrentIndex(1)
        self.window.table_widget.selectRow(0)
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert "202600001 (APV)" in str(
            self.window.details_tree_text.toPlainText() or ""
        )
        assert "202600001" in str(self.window.details_graph_label.text() or "")

    def test_collect_derivadas_tree_data_prefers_local_family_before_snapshot(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": [1, 2],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "1"],
                "descricao_ssa": ["Teste A", "Teste B"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()

        monkeypatch.setattr(
            ssa_gui_details.details_data_provider,
            "get_db_mtime",
            lambda _path: 1,
        )
        monkeypatch.setattr(
            ssa_gui_details.details_data_provider,
            "load_derivadas_snapshot",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("nao deveria consultar snapshot com familia local pronta")
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_cached_derivadas_family_edges",
            lambda *_args, **_kwargs: [("1", "2")],
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_derivadas_for_ssa",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("nao deveria usar fallback sem familia local")
            ),
        )

        tree_data = ssa_gui_details._collect_derivadas_tree_data(self.window, "1")

        assert tree_data["target"] == "1"
        assert tree_data["children"]
        assert tree_data["descendants"]

    def test_resolve_ssa_series_candidates_uses_positions_with_duplicate_index(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100135", "202100186", "202100187"],
                "situacao": ["STE", "SES", "APG"],
                "descricao_ssa": ["Mae", "Selecionada", "Irma"],
            },
            index=[0, 0, 1],
        )
        self.window.df_exibido = df
        self.window.df_completo = df

        resolved = ssa_gui_details._resolve_ssa_series_candidates(
            self.window,
            ["202100186"],
        )

        assert resolved["202100186"]["situacao"] == "SES"
        assert resolved["202100186"]["descricao_ssa"] == "Selecionada"

    def test_resolve_ssa_series_candidates_uses_display_normalization(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202512345"],
                "situacao": ["STE"],
                "descricao_ssa": ["Com hifen canonico"],
            }
        )
        self.window.df_exibido = df
        self.window.df_completo = df

        resolved = ssa_gui_details._resolve_ssa_series_candidates(
            self.window,
            ["2025-12345"],
        )

        assert resolved["202512345"]["situacao"] == "STE"
        assert resolved["202512345"]["descricao_ssa"] == "Com hifen canonico"

    def test_find_series_position_by_ssa_uses_cached_index_first(self, monkeypatch):
        details_df = pd.DataFrame(
            {
                "numero_ssa": ["202600101", "202600102"],
                "situacao": ["APG", "STE"],
            }
        )
        cached_index = ssa_gui_details._get_df_ssa_series_index(self.window, details_df)

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_df_ssa_series_index",
            lambda *_args, **_kwargs: cached_index,
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_cached_normalized_series",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("lookup must use DetailsSeriesIndex first")
            ),
        )

        position, matched = ssa_gui_details._find_series_position_by_ssa(
            self.window, details_df, "202600102"
        )

        assert position == 1
        assert str(matched.get("numero_ssa")) == "202600102"

    def test_details_derivadas_tab_skips_graph_render_without_relations(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": [1],
                "situacao": ["APV"],
                "derivada_de": [""],
                "descricao_ssa": ["Teste sem derivadas"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.setattr(
            ssa_gui_details,
            "render_graph_svg_pixmap",
            lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("nao deveria renderizar grafo sem relacoes")
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda *_args, **_kwargs: details_derivadas_model.normalize_tree_data(
                target="1",
                snapshot=None,
                fallback_children=[],
                direct_parent="",
                local_payload=None,
                related=[],
                target_status="",
            ),
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_window_ssa_series_index",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("nao deveria montar indice global sem relacoes")
            ),
        )

        ctx = self._panel_context()
        ctx["details_tab_bar"].setCurrentIndex(1)
        self.window.table_widget.selectRow(0)
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert str(self.window.details_graph_label.text() or "") == "Sem SSAs Derivadas."
        assert self.window.details_graph_label.isVisible() is True

    def test_column_filters_panel_is_populated_on_startup(self):
        main_ctx = self._panel_context()
        container = main_ctx["col_filters_container"]

        labels = [
            str(label.text() or "")
            for label in container.findChildren(QLabel)
            if str(label.text() or "").strip()
        ]

        assert "Desc. SSA" in labels
        assert "Set. Exec." in labels
        assert "Set. Emis." in labels
        assert "Desc. Exec." in labels
        assert "Loc." not in labels
        assert "Sem. Cad." in labels
        assert "Sem. Prog." in labels
        assert "Sem. Exec." in labels

    def test_advanced_filters_reprogramacoes_controls_are_compact(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        reprog_mode = self.window.adv_reprog_mode
        reprog_button = self.window.adv_reprog_button

        assert reprog_mode.maximumWidth() <= 126
        sem_dados_width = reprog_button.fontMetrics().horizontalAdvance("Sem dados")
        assert sem_dados_width + 16 <= reprog_button.maximumWidth() <= 104
        assert reprog_mode.maximumHeight() <= 24
        assert reprog_button.maximumHeight() <= 24
        assert str(reprog_button.toolTip() or "") in {"Nº", "Nenhum dado disponivel"}

    def test_search_help_texts_reflect_current_general_search_contract(self):
        main_ctx = self._panel_context()
        search_input = main_ctx["search_input"]
        col_indicator = main_ctx["col_filter_indicator"]
        search_help = main_ctx["search_help"]

        assert (
            str(search_input.placeholderText() or "")
            == "Termos cumulativos separados por virgula; ! exclui termo"
        )
        tooltip = str(search_input.toolTip() or "")
        assert "virgulas separam termos cumulativos" in tooltip
        assert (
            "Todos os termos digitados devem ser satisfeitos na mesma linha." in tooltip
        )
        assert "colunas relevantes da GUI" in tooltip
        assert "condicao E" not in tooltip.casefold()
        assert "Use termos positivos e ! para excluir." in str(search_help.text() or "")

        indicator_tooltip = str(col_indicator.toolTip() or "")
        assert "Busca rapida" in indicator_tooltip
        assert "termos cumulativos" in indicator_tooltip
        assert "Filtros por texto" in indicator_tooltip
        assert "alternativas dentro da mesma coluna" in indicator_tooltip

    def test_filter_help_dialog_texts_separate_general_search_from_column_alternatives(
        self,
    ):
        dialog = FilterHelpDialog(self.window)
        browser = dialog.findChild(QtWidgets.QTextBrowser)
        assert browser is not None
        html = str(browser.toHtml() or "")

        assert "Busca" in html
        assert "todos os termos digitados sao obrigatorios" in html
        assert "virgulas representam alternativas implicitas" in html
        assert "logica OU - qualquer termo serve" not in html

    def test_setor_executor_order_prioritizes_smin_then_mel_then_alpha(self):
        ordered = SSAMainWindow._order_setor_executor_values(
            ["AAA", "ZZZ", "MEL3", "IEE4", "ABC", "IEE1", "MEL1", "IEE3"]
        )
        assert ordered == ["IEE3", "IEE1", "IEE4", "MEL1", "MEL3", "AAA", "ABC", "ZZZ"]

    def test_setor_order_is_shared_between_quick_and_advanced_filters(self):
        values = ["MEG2", "IEE4", "MEL3", "ILA2", "IEE1", "MEL1"]

        quick_order = SSAMainWindow._order_setor_executor_values(values)
        advanced_order = self.window._sort_sectors(values)

        assert quick_order == advanced_order
        assert quick_order == ["IEE1", "IEE4", "MEL1", "MEL3", "ILA2", "MEG2"]

    def test_setor_order_uses_full_priority_before_alpha_tail(self):
        values = [
            "XYZ",
            "MEL2",
            "IEE4",
            "IEE1",
            "MEL4",
            "AAA",
            "MEL1",
            "IEE2",
            "MEL3",
            "IEE3",
        ]

        ordered = SSAMainWindow._order_setor_executor_values(values)

        assert ordered == [
            "IEE3",
            "IEE1",
            "IEE2",
            "IEE4",
            "MEL1",
            "MEL2",
            "MEL3",
            "MEL4",
            "AAA",
            "XYZ",
        ]

    def test_quick_setor_executor_combo_applies_executor_filter_only(self, monkeypatch):
        self.window._register_or_group(
            ["setor_executor", "setor_emissor"], ["IEE3", "MEL3"]
        )
        self.window._active_column_filters["setor_executor"] = "IEE3, MEL3"
        self.window._active_column_filters["setor_emissor"] = "IEE3, MEL3"
        self.window._build_column_filters_panel()
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        assert int(combo.maxVisibleItems()) == 14
        assert getattr(self.window, "persist_filter_config_checkbox", None) is None
        style_sheet = str(combo.styleSheet() or "")
        assert "combobox-popup: 0" in style_sheet
        assert "QComboBox:hover" in style_sheet
        assert "border:1px solid" in style_sheet
        assert not re.search(r"border\s*:\s*2px\s+solid", style_sheet)
        mel4_idx = combo.findData("MEL4")
        assert mel4_idx >= 0
        assert str(combo.itemText(0)) == "Todos"
        assert str(combo.itemText(mel4_idx)) == "MEL4"
        assert "Setor Executor:" not in str(combo.currentText() or "")

        rebuild_calls = 0

        def _count_rebuild():
            nonlocal rebuild_calls
            rebuild_calls += 1

        monkeypatch.setattr(self.window, "_build_column_filters_panel", _count_rebuild)

        combo.setCurrentIndex(mel4_idx)
        QApplication.processEvents()
        assert str(combo.currentText() or "") == "MEL4"

        assert self.window._active_column_filters.get("setor_executor") == "MEL4"
        assert self.window._active_column_filters.get("setor_emissor") == "IEE3, MEL3"
        assert self.window._advanced_filters.get("setor_executor") == ["MEL4"]
        assert "setor_executor_exclude_values" not in self.window._advanced_filters
        assert self.window._advanced_filters_active is True

        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        assert "MEL4" in str(getattr(self.window, "adv_executor_button").text() or "")
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        controls = self._get_column_filter_controls()
        if hasattr(self.window, "_expand_column_alias_for_filter"):
            setor_key = self.window._expand_column_alias_for_filter("setor_executor")
        else:
            setor_key = self.window._resolve_column_display_name("setor_executor")
        assert setor_key in controls
        setor_input, _, _, _ = controls[setor_key]
        assert str(setor_input.text() or "").strip() == "MEL4"
        assert rebuild_calls == 0

    def test_quick_situacao_buttons_apply_filter_without_rebuilding_panel(
        self, monkeypatch
    ):
        self.window._active_column_filters["situacao"] = ""
        self.window._build_column_filters_panel()
        self.window._refresh_quick_situacao_buttons()
        buttons = getattr(self.window, "quick_situacao_buttons", None)
        values = getattr(self.window, "quick_situacao_values", None)
        assert isinstance(buttons, dict)
        assert values == ["AMP", "APV", "SCA", "STE"]
        assert bool(getattr(self.window, "quick_situacao_box").isVisible()) is True

        rebuild_calls = 0
        refresh_calls = 0

        def _count_rebuild():
            nonlocal rebuild_calls
            rebuild_calls += 1

        def _count_refresh():
            nonlocal refresh_calls
            refresh_calls += 1

        monkeypatch.setattr(self.window, "_build_column_filters_panel", _count_rebuild)
        monkeypatch.setattr(self.window, "_refresh_after_filter_change", _count_refresh)

        buttons["APV"].setChecked(True)
        QApplication.processEvents()
        assert self.window._active_column_filters.get("situacao") == "APV"
        assert rebuild_calls == 0
        assert refresh_calls == 1
        assert "qlineargradient" in str(buttons["APV"].styleSheet() or "")
        assert "font-weight:800" in str(buttons["APV"].styleSheet() or "")

        buttons["STE"].setChecked(True)
        QApplication.processEvents()
        assert self.window._active_column_filters.get("situacao") == "APV, STE"
        assert rebuild_calls == 0
        assert refresh_calls == 2
        assert "qlineargradient" in str(buttons["STE"].styleSheet() or "")
        assert "stop:0" in str(buttons["STE"].styleSheet() or "")
        assert "font-weight:800" in str(buttons["STE"].styleSheet() or "")
        assert "qlineargradient" not in str(buttons["AMP"].styleSheet() or "")

    def test_advanced_situacao_selection_marks_quick_button(self):
        self.window._active_column_filters["situacao"] = ""
        self.window._advanced_filters = {"situacao": ["STE"]}
        self.window._advanced_filters_active = True

        self.window._refresh_quick_situacao_buttons()

        buttons = getattr(self.window, "quick_situacao_buttons", {})
        assert buttons["STE"].isChecked() is True
        assert buttons["APV"].isChecked() is False

    def test_advanced_situacao_exclude_does_not_mark_positive_quick_button(self):
        self.window._active_column_filters["situacao"] = ""
        self.window._advanced_filters = {
            "situacao": ["STE"],
            "situacao_exclude_values": ["APV"],
        }
        self.window._advanced_filters_active = True

        self.window._refresh_quick_situacao_buttons()

        buttons = getattr(self.window, "quick_situacao_buttons", {})
        assert buttons["STE"].isChecked() is False
        assert buttons["APV"].isChecked() is False

    def test_advanced_situacao_positive_applies_and_marks_quick_button(self):
        self._set_filter_panel_tab("filters")
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        status_checks = getattr(self.window, "adv_status_checks", [])
        ste_checks = [
            checkbox
            for checkbox in status_checks
            if str(checkbox.property("value") or "") == "STE"
        ]
        assert len(ste_checks) == 1

        ste_checks[0].setChecked(True)
        self.window._apply_advanced_filters_from_ui()
        QApplication.processEvents()

        assert set(self.window.df_exibido["situacao"].astype(str)) == {"STE"}
        buttons = getattr(self.window, "quick_situacao_buttons", {})
        assert buttons["STE"].isChecked() is True
        assert str(self.window._active_column_filters.get("situacao") or "") == ""

    def test_advanced_situacao_exclude_applies_without_positive_quick_mark(self):
        self._set_filter_panel_tab("filters")
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        status_exclude_checks = getattr(self.window, "adv_status_exclude_checks", [])
        ste_checks = [
            checkbox
            for checkbox in status_exclude_checks
            if str(checkbox.property("value") or "") == "STE"
        ]
        assert len(ste_checks) == 1

        ste_checks[0].setChecked(True)
        self.window._apply_advanced_filters_from_ui()
        QApplication.processEvents()

        assert "STE" not in set(self.window.df_exibido["situacao"].astype(str))
        buttons = getattr(self.window, "quick_situacao_buttons", {})
        assert all(not button.isChecked() for button in buttons.values())

    def test_quick_situacao_click_clears_advanced_exclude_and_applies_filter(self):
        self.window._advanced_filters = {"situacao_exclude_values": ["STE"]}
        self.window._advanced_filters_active = True
        self.window._active_column_filters["situacao"] = ""
        self.window._refresh_quick_situacao_buttons()
        buttons = getattr(self.window, "quick_situacao_buttons", {})

        cast(Any, QTest).mouseClick(buttons["STE"], Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert self.window._active_column_filters.get("situacao") == "STE"
        assert set(self.window.df_exibido["situacao"].astype(str)) == {"STE"}
        assert buttons["STE"].isChecked() is True

    def test_search_exclusion_and_quick_situacao_keep_result_and_visual_sync(self):
        scenario_df = self.base_df.copy()
        scenario_df.loc[4, "situacao"] = "STE"
        scenario_df.loc[4, "localizacao_codigo"] = "G097F001"
        self.window.df_completo = scenario_df.copy()
        self.window.df_exibido = scenario_df.copy()
        self.window._df_last_search_filtered = scenario_df.copy()
        self.window.paginator.set_dataframe(scenario_df.copy())

        self.window.search_input.setText("!G097")
        self.window.initiate_filtering()
        QApplication.processEvents()
        self.window._refresh_quick_situacao_buttons()
        buttons = getattr(self.window, "quick_situacao_buttons", {})

        cast(Any, QTest).mouseClick(buttons["STE"], Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window.search_input.text() == "!G097"
        assert self.window._active_column_filters.get("situacao") == "STE"
        assert buttons["STE"].isChecked() is True
        assert set(self.window.df_exibido["situacao"].astype(str)) == {"STE"}
        assert not self.window.df_exibido["localizacao_codigo"].astype(str).str.contains(
            "G097", case=False
        ).any()

    def test_quick_setor_executor_clears_existing_advanced_exclusions(self):
        self.window._advanced_filters = {
            "setor_executor_exclude_values": ["MEL3"],
        }
        self.window._active_column_filters["setor_executor"] = "IEE1"

        self.window._sync_advanced_executor_filter_from_active_filters(
            clear_exclude=True
        )

        assert self.window._advanced_filters["setor_executor"] == ["IEE1"]
        assert "setor_executor_exclude_values" not in self.window._advanced_filters

    def test_quick_setor_executor_all_clears_existing_advanced_exclusions(self):
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        self.window._advanced_filters = {
            "setor_executor_exclude_values": ["MEL3"],
        }
        mel4_idx = combo.findData("MEL4")
        assert mel4_idx >= 0
        combo.setCurrentIndex(mel4_idx)
        QApplication.processEvents()

        combo.setCurrentIndex(0)
        QApplication.processEvents()

        assert "setor_executor" not in self.window._advanced_filters
        assert "setor_executor_exclude_values" not in self.window._advanced_filters

    def test_quick_setor_executor_direct_clear_removes_existing_exclusions(self):
        self.window._advanced_filters = {
            "setor_executor": ["MEL4"],
            "setor_executor_exclude_values": ["MEL3"],
        }
        self.window._active_column_filters["setor_executor"] = ""

        self.window._sync_advanced_executor_filter_from_active_filters(
            clear_exclude=True
        )

        assert "setor_executor" not in self.window._advanced_filters
        assert "setor_executor_exclude_values" not in self.window._advanced_filters

    def test_apply_advanced_executor_syncs_back_to_quick_combo_and_active_filters(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        target = next(
            check
            for check in (getattr(self.window, "adv_executor_checks", []) or [])
            if str(check.property("value") or "") == "IEE3"
        )
        target.setChecked(True)

        self.window._apply_advanced_filters_from_ui(store_only=True)
        self.window._sync_quick_setor_executor_combo_from_filters()
        QApplication.processEvents()

        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        assert self.window._advanced_filters.get("setor_executor") == ["IEE3"]
        assert self.window._active_column_filters.get("setor_executor") == "IEE3"
        assert str(combo.currentData() or "") == "IEE3"

    def test_advanced_executor_sync_preserves_other_active_filters_in_place(self):
        active_filters = self.window._active_column_filters
        active_filters["situacao"] = "ADM"
        self.window._advanced_filters = {"setor_executor": ["IEE1", "IEE2"]}

        self.window._sync_active_executor_filter_from_advanced_filters()

        assert self.window._active_column_filters is active_filters
        assert self.window._active_column_filters["situacao"] == "ADM"
        assert self.window._active_column_filters["setor_executor"] == "IEE1, IEE2"

    def test_sync_quick_setor_executor_combo_reuses_existing_options(self, monkeypatch):
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        assert combo.findData("IEE3") >= 0

        called = {"count": 0}

        def _unexpected_populate(*_args, **_kwargs):
            called["count"] += 1
            raise AssertionError("combo should reuse existing options")

        monkeypatch.setattr(
            self.window,
            "_populate_quick_setor_executor_combo",
            _unexpected_populate,
        )

        self.window._active_column_filters["setor_executor"] = "IEE3"
        self.window._sync_quick_setor_executor_combo_from_filters()
        QApplication.processEvents()

        assert called["count"] == 0
        assert str(combo.currentData() or "") == "IEE3"
        assert str(combo.currentText() or "") == "IEE3"

    def test_sync_quick_setor_executor_combo_repopulates_when_value_missing(
        self, monkeypatch
    ):
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None

        populate_calls: list[str] = []
        original_populate = self.window._populate_quick_setor_executor_combo

        def _tracked_populate(target_combo, selected_value: str = ""):
            populate_calls.append(str(selected_value))
            return original_populate(target_combo, selected_value=selected_value)

        monkeypatch.setattr(
            self.window,
            "_populate_quick_setor_executor_combo",
            _tracked_populate,
        )

        self.window._active_column_filters["setor_executor"] = "SETOR_INEXISTENTE"
        self.window._sync_quick_setor_executor_combo_from_filters()
        QApplication.processEvents()

        assert populate_calls
        assert set(populate_calls) == {"SETOR_INEXISTENTE"}
        assert str(combo.currentData() or "") == ""

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
        assert first_context.startswith("sha256:")

        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()

        second_context = self.window._build_filter_cache_context()
        assert second_context != first_context
        assert second_context.startswith("sha256:")

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._build_filter_cache_context() == ""
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert str(combo.currentText() or "") == "Todos"

    def test_profile_filters_executor_or_emissor(self):
        """Perfil Executor/Emissor deve aplicar grupo OU na UI."""
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)

        # O grupo Executor/Emissor usa OU: qualquer coluna do grupo pode bater.
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4])

        # Confirma sincronismo entre campos (Executor/Emissor)
        for col in ("setor_executor", "setor_emissor"):
            # Armazenamento interno usa virgulas para separar alternativas
            assert self.window._active_column_filters[col] == "IEE3, MEL3, MEL4"
        summary = getattr(self.window, "filters_summary_label", None)
        if summary is not None:
            summary_text = str(summary.toolTip() or "")
            summary_buttons = [
                str(button.text() or "")
                for button in self.window.filters_summary_items_widget.findChildren(
                    QPushButton
                )
            ]
            assert "IEE3, MEL3, MEL4" in summary_text
            assert any("Exec" in text for text in summary_buttons)
            assert {
                "setor_executor",
                "setor_emissor",
            }.issubset(self.window._column_to_or_group)

        # Ajuste manual em um campo deve repercutir no par
        self.window._active_column_filters["setor_executor"] = "MEL4"
        self.window._sync_or_group_values("setor_executor", "MEL4")
        self.window._refresh_after_filter_change()
        assert self.window._active_column_filters["setor_emissor"] == "MEL4"
        assert Counter(self._extract_visible_ssa()) == Counter([3])

        self.window._sync_or_group_values("setor_executor", "IEE3, !MEL4")
        self.window._refresh_after_filter_change()
        assert self.window._active_column_filters["setor_emissor"] == "IEE3, !MEL4"
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2])

    def test_profile_empty_or_group_keeps_specific_column_value(self):
        normalized = NormalizedFilterProfile(
            columns=OrderedDict([("setor_executor", "IEE3")]),
            or_groups=(
                NormalizedOrGroup(
                    columns=("setor_executor", "setor_emissor"),
                    values=(),
                ),
            ),
            profile_columns=("setor_executor", "setor_emissor"),
        )

        self.window._apply_normalized_filter_profile(
            profile_name="empty-or-group",
            normalized=normalized,
            update_selector=False,
            refresh=False,
            base_profile_name=None,
        )

        assert self.window._active_column_filters["setor_executor"] == "IEE3"
        assert self.window._active_column_filters["setor_emissor"] == ""

    def test_exclude_ste_sca_combined_with_or_group(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4])

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
        # Filtra linhas SCA/SES/STE mantendo o grupo OU ativo.
        remaining = self._extract_visible_ssa()
        assert 2 not in remaining
        assert 3 not in remaining
        assert 6 not in remaining
        assert Counter(remaining) == Counter([1, 4])

    def test_macro_baixar_excludes_sad_sca_ses_ste_and_keeps_parent_ssa(
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
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()

        macro_idx = self.window.adv_macro_combo.findData("ssas_para_baixar")
        assert macro_idx >= 0

        self.window.adv_macro_combo.setCurrentIndex(macro_idx)
        self.window._on_macro_filter_changed()
        QApplication.processEvents()

        assert "Diferente: SAD, SCA, SES, STE" in self.window.adv_status_button.toolTip()

        self.window._apply_advanced_filters_from_ui()
        QApplication.processEvents()

        assert self.window._advanced_filters.get("derivada_all_ste") is True
        assert set(
            self.window._advanced_filters.get("situacao_exclude_values") or []
        ) == {"SAD", "SCA", "SES", "STE"}
        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == ["100"]

    def test_macro_baixar_filters_immediately_when_selected(self):
        macro_df = pd.DataFrame(
            {
                "numero_ssa": ["202600100", "202600101"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202600100"],
                "localizacao_codigo": ["LOC1", "LOC2"],
                "descricao_localizacao": ["Desc1", "Desc2"],
                "equipamento": ["EQ1", "EQ2"],
                "semana_cadastro": [202501, 202501],
                "semana_programada": [202503, 202503],
                "data_cadastro": ["2025-01-01", "2025-01-01"],
                "descricao_ssa": ["Origem", "Filha"],
                "setor_executor": ["IEE3", "IEE3"],
                "setor_emissor": ["IEE3", "IEE3"],
                "descricao_execucao": ["Exec A", "Exec B"],
                "solicitante": ["User1", "User2"],
            }
        )
        self.window.df_completo = macro_df.copy()
        self.window.df_exibido = macro_df.copy()
        self.window._df_last_search_filtered = macro_df.copy()
        self.window.paginator.set_dataframe(macro_df.copy())
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()

        macro_idx = self.window.adv_macro_combo.findData("ssas_para_baixar")
        assert macro_idx >= 0

        self.window.adv_macro_combo.setCurrentIndex(macro_idx)
        self.window._on_macro_filter_changed()
        QApplication.processEvents()
        timer = getattr(self.window, "_advanced_apply_timer", None)
        assert timer is not None
        self._wait_until_timer_inactive(timer)

        assert self.window._advanced_filters.get("macro_filter") == "ssas_para_baixar"
        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == [
            "202600100"
        ]

    def test_details_html_uses_display_label_for_situacao_da_parcial(self):
        series = pd.Series(
            {
                "numero_ssa": "202600001",
                "situacao_da_parcial": "Pendente",
            }
        )

        html = ssa_gui_details._format_details_html(self.window, series)

        assert "Situacao da Parcial" in html
        assert "situacao_da_parcial" not in html

    def test_filters_summary_deduplicates_column_and_advanced_entries(self):
        self.window._active_column_filters["setor_executor"] = "IEE3"
        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True

        self.window._update_filters_summary()
        QApplication.processEvents()

        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert str(self.window.filters_summary_label.text() or "") == ""
        assert self.window.filters_summary_label.isVisible() is False
        assert summary_buttons.count("Exec: IEE3") == 1

    def test_filters_summary_buttons_remove_search_with_confirmation(self):
        self.window._sync_filtering = True
        self.window.search_input.setText("MEL3")
        self.window.initiate_filtering()
        QApplication.processEvents()
        self.window._update_filters_summary()
        QApplication.processEvents()
        assert self.window._df_last_search_filtered is not self.window.df_completo

        summary_widget = getattr(self.window, "filters_summary_items_widget", None)
        assert summary_widget is not None
        buttons = summary_widget.findChildren(QPushButton)
        search_button = next(
            btn for btn in buttons if "Busca: 'MEL3'" in str(btn.text() or "")
        )

        with patch(
            "gui.mixins.filter_gui_ssa_mixin.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ) as question_mock:
            cast(Any, QTest).mouseClick(search_button, Qt.MouseButton.LeftButton)
            QApplication.processEvents()

        question_mock.assert_called_once()
        assert self.window.search_input.text() == ""
        assert self.window._df_last_search_filtered is self.window.df_completo
        assert len(self.window.df_exibido) == len(self.window.df_completo)

    def test_filters_summary_buttons_remove_exclude_ste_sca_with_confirmation(self):
        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()

        summary_widget = getattr(self.window, "filters_summary_items_widget", None)
        assert summary_widget is not None
        buttons = summary_widget.findChildren(QPushButton)
        situacao_exclude_button = next(
            btn for btn in buttons if "situacao!=SCA/SES/STE" in str(btn.text() or "")
        )

        with patch(
            "gui.mixins.filter_gui_ssa_mixin.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ):
            cast(Any, QTest).mouseClick(
                situacao_exclude_button, Qt.MouseButton.LeftButton
            )
            QApplication.processEvents()

        assert self.window._exclude_ste_sca is False

    def test_filters_summary_buttons_use_single_line_theme_chip_style(self):
        self.window.search_input.setText("Teste A")
        self.window._update_filters_summary()
        QApplication.processEvents()

        summary_widget = getattr(self.window, "filters_summary_items_widget", None)
        assert summary_widget is not None
        buttons = summary_widget.findChildren(QPushButton)
        search_button = next(
            btn for btn in buttons if "Busca: 'Teste A'" in str(btn.text() or "")
        )

        css = str(search_button.styleSheet() or "")
        assert str(search_button.text() or "") == "Busca: 'Teste A'"
        assert "font-size:12px" in css
        assert "font-weight:600" in css
        assert search_button.height() == 22

    def test_filters_summary_buttons_compact_font_before_scroll(self):
        self.window.search_input.setText("Texto muito longo " * 8)
        self.window._active_column_filters["descricao_ssa"] = "Filtro longo " * 8
        self.window._advanced_filters = {"setor_executor": ["IEE1", "IEE2", "IEE3"]}
        self.window._advanced_filters_active = True
        self.window._update_filters_summary()
        QApplication.processEvents()

        buttons = self.window.filters_summary_items_widget.findChildren(QPushButton)
        visible_buttons = [button for button in buttons if button.isVisible()]

        assert len(visible_buttons) >= 2
        assert all(
            re.search(r"font-size\s*:\s*11px", str(button.styleSheet() or ""))
            for button in visible_buttons
        )

    def test_advanced_selection_panel_geometry_keeps_last_row_visible(self):
        context = self._panel_context()
        tab_bar = context["filter_panel_tab_bar"]
        tab_bar.setCurrentIndex(1)
        self.window.resize(1200, 918)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(
            self.window.adv_filters_group.width()
        )
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        scroll = state.controls_scroll
        viewport_height = scroll.viewport().height()
        adv_group_height = int(self.window.adv_filters_group.height())
        visible_widgets = [
            widget
            for widget in state.grid_widgets.values()
            if widget is not None and widget.isVisible()
        ]
        widget_bottoms = []

        assert visible_widgets
        for widget in visible_widgets:
            assert (
                advanced_layout.LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT
                <= widget.height()
                <= advanced_layout.LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT + 8
            )
            contents_top = int(widget.contentsRect().top())
            contents_bottom = int(widget.contentsRect().bottom()) + 1
            min_child_top = contents_top + 2
            for child in widget.findChildren(
                QtWidgets.QWidget,
                options=Qt.FindChildOption.FindDirectChildrenOnly,
            ):
                if child.isVisible():
                    assert int(child.geometry().y()) >= min_child_top
                    assert int(child.geometry().bottom()) <= contents_bottom
            widget_bottoms.append(widget.geometry().y() + widget.geometry().height())

        for control in state.metric_controls:
            if control is not None and control.isVisible():
                assert control.height() >= int(control.fontMetrics().height()) + 4

        for key in ("sol_box", "prog_box", "exec_resp_box"):
            widget = state.grid_widgets.get(key)
            assert widget is not None
            assert widget.isVisible()
            assert widget.geometry().y() + widget.geometry().height() <= viewport_height - 4

        bottom_gap = viewport_height - max(widget_bottoms)
        assert bottom_gap >= 4
        expected_scroll_min = max(80, adv_group_height - 4)
        expected_scroll_max = adv_group_height
        assert expected_scroll_max >= expected_scroll_min
        assert expected_scroll_min <= scroll.height() <= expected_scroll_max
        assert scroll.verticalScrollBar().maximum() == 0
        assert "action_box" not in state.grid_widgets

    def test_quick_setor_executor_style_uses_theme_roles_without_fixed_yellow(self):
        self.window.apply_theme("mint-light")
        QApplication.processEvents()

        roles = dict(getattr(self.window, "_current_theme_roles", {}) or {})
        style = str(self.window.quick_setor_executor_combo.styleSheet() or "")

        assert "#ffcc00" not in style
        assert "#fabd2f" not in style
        assert roles["input_border_focus"] in style
        assert roles["input_bg"] in style

    def test_column_filter_text_input_style_uses_panel_theme_roles(self, monkeypatch):
        roles = {
            "panel_text": "#102030",
            "panel_bg": "#eaf4f1",
            "label_color": "#667788",
            "input_text": "#eeeeee",
            "input_bg": "#202020",
            "input_border": "#a0b0c0",
            "input_border_focus": "#009688",
            "input_placeholder": "#708080",
        }
        monkeypatch.setattr(filter_mixin, "get_theme_roles", lambda _theme: roles)
        label = QLabel("Desc. SSA")
        field = QLineEdit()

        self.window._current_theme = "test-panel-filter"
        self.window._apply_filter_widget_theme(label, field)

        label_style = str(label.styleSheet() or "")
        field_style = str(field.styleSheet() or "")
        assert "color:#102030" in label_style
        assert "color:#eeeeee" in field_style
        assert "QLineEdit#columnFilterInput" in field_style
        assert "background-color:#eaf4f1" in field_style
        assert "background-color:#202020" not in field_style
        assert "#a0b0c0" in field_style
        assert "#009688" in field_style

    def test_header_reorder_updates_visible_columns_order(self):
        if "solicitante" not in self.window.visible_columns:
            self.window.visible_columns.append("solicitante")
        self.window.display_current_page(1)
        QApplication.processEvents()

        header = self.window.table_widget.horizontalHeader()
        situacao_index = self.window._current_display_columns.index("situacao")
        situacao_visual_index = header.visualIndex(situacao_index)
        header.moveSection(situacao_visual_index, 1)
        QApplication.processEvents()

        assert self.window.visible_columns[0] == "situacao"
        assert self.window.visible_columns[1] == "numero_ssa"

    def test_details_constants_place_localizacao_after_descricao(self):
        priority = list(gui_ssa.DETAIL_FIELD_PRIORITY)
        assert priority.index("descricao_ssa") < priority.index("localizacao_codigo")
        assert (
            priority.index("localizacao_codigo") == priority.index("descricao_ssa") + 1
        )
        assert gui_ssa.DETAIL_DISPLAY_OVERRIDES["localizacao_codigo"] == "Localizacao"

    def test_details_html_renders_localizacao_label(self):
        series = pd.Series(
            {
                "numero_ssa": "1",
                "situacao": "APV",
                "descricao_ssa": "Teste A",
                "localizacao_codigo": "LOC1",
            }
        )
        html = ssa_gui_details._format_details_html(self.window, series)
        descricao_pos = html.index("Descricao da SSA:")
        localizacao_pos = html.index("Localizacao:")
        assert localizacao_pos > descricao_pos

    def test_details_html_uses_fixed_table_layout(self):
        series = pd.Series(
            {
                "numero_ssa": "202600023",
                "situacao": "APG",
                "descricao_ssa": (
                    "Texto longo para validar quebra controlada e coluna fixa sem "
                    "mudar a divisao entre rotulo e valor"
                ),
            }
        )

        html = ssa_gui_details._format_details_html(self.window, series)

        assert 'margin: 0' in html
        assert '<table width="100%"' in html
        assert "width: 100%" in html
        assert "table-layout: fixed" in html
        assert "<colgroup>" in html
        assert "width: 18%;" in html
        assert "width: 82%;" in html
        assert "overflow-wrap: anywhere" in html
        assert "word-break: break-word" in html

    def test_update_details_from_series_uses_details_group_font_family(
        self, monkeypatch
    ):
        captured = {}

        def _fake_format(_window, _series, **kwargs):
            captured["font_family"] = kwargs.get("font_family")
            return "<html><body>ok</body></html>"

        monkeypatch.setattr(ssa_gui_details, "_format_details_html", _fake_format)

        series = pd.Series({"numero_ssa": "202600023", "situacao": "APG"})
        ssa_gui_details._update_details_from_series(self.window, series)

        assert captured["font_family"] == self.window.details_group.font().family()

    def test_details_frame_fingerprint_cache_tracks_in_place_dataframe_changes(self):
        self.window._data_uuid = "uuid-1"
        self.window._data_revision = 1
        df = pd.DataFrame({"numero_ssa": ["1"]})

        first_fingerprint = ssa_gui_details._get_details_frame_fingerprint(
            self.window,
            df,
        )
        df.loc[0, "numero_ssa"] = "2"
        second_fingerprint = ssa_gui_details._get_details_frame_fingerprint(
            self.window,
            df,
        )

        assert first_fingerprint
        assert second_fingerprint
        assert first_fingerprint != second_fingerprint

    def test_advanced_panel_context_exposes_emissor_before_executor(self):
        _ = self._panel_context()
        grid_widgets = self.window._advanced_filter_panel_state.grid_widgets
        keys = list(grid_widgets.keys())
        assert keys.index("emis_box") < keys.index("exec_box")

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

    def test_display_headers_ignore_boolean_false_in_advanced_filter_columns(self):
        if "solicitante" not in self.window.visible_columns:
            self.window.visible_columns.append("solicitante")

        self.window._active_column_filters = {
            col: "" for col in self.window._column_filter_default_columns()
        }
        self.window._advanced_filters = {"solicitante": False}
        self.window._advanced_filters_active = True

        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("solicitante")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert not header_text.startswith("[f] ")

    def test_column_header_label_variants_cover_display_names_with_three_slots(self):
        assert set(COLUMN_HEADER_LABEL_VARIANTS) == set(DEFAULT_COLUMN_DISPLAY_NAMES)
        for variants in COLUMN_HEADER_LABEL_VARIANTS.values():
            assert set(variants) == {"short", "medium", "long"}

    def test_select_adaptive_header_label_prefers_longest_variant_that_fits(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )

        long_label = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            140,
            False,
        )
        medium_label = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            100,
            False,
        )
        short_label = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            50,
            False,
        )

        assert long_label == "Numero da SSA"
        assert medium_label == "Numero SSA"
        assert short_label == "SSA"

    def test_select_adaptive_header_label_keeps_shortest_fallback_below_minimum_width(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )

        label = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            8,
            False,
        )

        assert label == "SSA"

    def test_select_adaptive_header_label_reserves_space_for_filter_prefix(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )

        no_filter = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            100,
            False,
        )
        with_filter = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            100,
            True,
        )

        assert no_filter == "Numero SSA"
        assert with_filter == "SSA"

    def test_select_adaptive_header_label_preserves_runtime_custom_alias(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window.internal_to_display["numero_ssa"] = "Meu SSA"

        label = ssa_gui_table._select_adaptive_header_label(
            self.window,
            "numero_ssa",
            200,
            False,
        )

        assert label == "Meu SSA"

    def test_display_current_page_applies_adaptive_header_label_after_widths(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window._adaptive_header_label_width_cache = {}
        self.window._adaptive_header_label_signatures = {}
        self.window._saved_gui_column_widths["numero_ssa"] = 100

        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("numero_ssa")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text == "Numero SSA"

    def test_display_current_page_right_aligns_table_cells_by_default(self):
        gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {}).pop(
            "table_cell_alignment", None
        )

        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("numero_ssa")
        item = self.window.table_widget.item(0, logical_index)

        assert item is not None
        assert int(item.textAlignment()) & int(Qt.AlignmentFlag.AlignRight)

    def test_display_current_page_accepts_left_table_cell_alignment(self):
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_alignment = gui_settings.get("table_cell_alignment")
        gui_settings["table_cell_alignment"] = "left"

        try:
            self.window.display_current_page(1)
            QApplication.processEvents()

            logical_index = self.window._current_display_columns.index("numero_ssa")
            item = self.window.table_widget.item(0, logical_index)

            assert item is not None
            assert int(item.textAlignment()) & int(Qt.AlignmentFlag.AlignLeft)
        finally:
            gui_settings["table_cell_alignment"] = previous_alignment or "right"

    def test_display_current_page_accepts_right_table_cell_alignment(self):
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_alignment = gui_settings.get("table_cell_alignment")
        gui_settings["table_cell_alignment"] = "right"

        try:
            self.window.display_current_page(1)
            QApplication.processEvents()

            logical_index = self.window._current_display_columns.index("numero_ssa")
            item = self.window.table_widget.item(0, logical_index)

            assert item is not None
            assert int(item.textAlignment()) & int(Qt.AlignmentFlag.AlignRight)
        finally:
            gui_settings["table_cell_alignment"] = previous_alignment or "right"

    def test_display_current_page_keeps_long_text_columns_left_aligned(self):
        gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        previous_alignment = gui_settings.get("table_cell_alignment")
        gui_settings["table_cell_alignment"] = "right"

        try:
            self.window.display_current_page(1)
            QApplication.processEvents()

            logical_index = self.window._current_display_columns.index("descricao_ssa")
            item = self.window.table_widget.item(0, logical_index)

            assert item is not None
            assert int(item.textAlignment()) & int(Qt.AlignmentFlag.AlignLeft)
        finally:
            gui_settings["table_cell_alignment"] = previous_alignment or "right"

    def test_setup_app_menus_exposes_table_cell_alignment_actions(self):
        actions = getattr(self.window, "_table_cell_alignment_actions", {})

        assert set(actions.keys()) == {"left", "center", "right"}
        assert actions["center"].isCheckable() is True

    def test_apply_table_cell_alignment_preference_updates_gui_prefs_without_rerender(
        self, monkeypatch
    ):
        persist_calls = {"count": 0}
        render_calls: list[tuple[int, bool]] = []
        alignment_calls: list[str] = []

        def _fake_persist():
            persist_calls["count"] += 1
            return True

        def _fake_render(page, *, update_details=True):
            render_calls.append((page, update_details))

        def _fake_alignment(_window, alignment_name):
            alignment_calls.append(alignment_name)

        monkeypatch.setattr(self.window, "_persist_gui_preferences", _fake_persist)
        monkeypatch.setattr(self.window, "display_current_page", _fake_render)
        monkeypatch.setattr(
            gui_ssa.ssa_gui_table,
            "apply_table_cell_alignment",
            _fake_alignment,
        )

        ok = self.window._apply_table_cell_alignment_preference("right")

        assert ok is True
        assert (
            gui_ssa.GUI_MAIN_PREFERENCES["gui_settings"]["table_cell_alignment"]
            == "right"
        )
        assert persist_calls["count"] == 1
        assert render_calls == []
        assert alignment_calls == ["right"]
        assert self.window._table_cell_alignment_actions["right"].isChecked() is True
        assert "Direita" in str(self.window.status_label.text() or "")

    def test_apply_table_cell_alignment_preference_rejects_invalid_value(
        self, monkeypatch
    ):
        calls = {"persist": 0, "render": 0}

        monkeypatch.setattr(
            self.window,
            "_persist_gui_preferences",
            lambda: calls.__setitem__("persist", calls["persist"] + 1) or True,
        )
        monkeypatch.setattr(
            self.window,
            "display_current_page",
            lambda *_args, **_kwargs: calls.__setitem__("render", calls["render"] + 1),
        )

        ok = self.window._apply_table_cell_alignment_preference("diagonal")

        assert ok is False
        assert calls["persist"] == 0
        assert calls["render"] == 0
        assert "invalido" in str(self.window.status_label.text() or "").casefold()

    def test_display_current_page_preserves_filter_prefix_with_reserved_space(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window._saved_gui_column_widths["numero_ssa"] = 100
        monkeypatch.setattr(
            self.window, "_get_visual_filter_columns", lambda: {"numero_ssa"}
        )

        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("numero_ssa")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text == "[f] SSA"

    def test_apply_adaptive_header_labels_expands_and_shrinks_with_runtime_width(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window._adaptive_header_label_width_cache = {}
        self.window._adaptive_header_label_signatures = {}

        self.window.visible_columns = ["descricao_ssa"]
        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("descricao_ssa")
        self.window.table_widget.setColumnWidth(header_index, 160)
        ssa_gui_table._apply_adaptive_header_labels(self.window)
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text == "Descricao da SSA"

        self.window.table_widget.setColumnWidth(header_index, 85)
        ssa_gui_table._apply_adaptive_header_labels(self.window)
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text == "Desc. SSA"

    def test_apply_adaptive_header_labels_handles_missing_header_item_and_stale_column(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window.visible_columns = ["descricao_ssa"]
        self.window.display_current_page(1)
        QApplication.processEvents()

        header_index = self.window._current_display_columns.index("descricao_ssa")
        removed_item = self.window.table_widget.takeHorizontalHeaderItem(header_index)
        assert removed_item is not None
        self.window._current_display_columns.append("stale_missing_column")

        ssa_gui_table._apply_adaptive_header_labels(self.window)

        restored_item = self.window.table_widget.horizontalHeaderItem(header_index)
        assert restored_item is not None
        assert str(restored_item.text() or "") == "Descricao da SSA"

    def test_clear_operations_preserve_group_structure(self):
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        self.window._clear_single_column_filter("setor_executor", "IEE3, MEL3, MEL4")
        # Grupo deve ser limpo sem remover as linhas do painel
        assert self.window._active_column_filters.get("setor_executor", None) == ""
        assert self.window._active_column_filters.get("setor_emissor", None) == ""

        # Reaplica valor manual e garante aplicação correta
        self.window._active_column_filters["setor_executor"] = "IEE3"
        self.window._sync_or_group_values("setor_executor", "IEE3")
        self.window._refresh_after_filter_change()
        # O grupo Executor/Emissor e OU: basta uma das colunas conter IEE3.
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2])

        # Limpa todos e garante reset completo
        self.window._clear_all_column_filters()
        assert self.window._active_column_filters
        assert not any(
            str(v).strip() for v in self.window._active_column_filters.values()
        )
        self.window._refresh_after_filter_change()
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])

    def test_details_and_default_display_order_place_emissor_before_executor(self):
        priority = list(gui_ssa.DETAIL_FIELD_PRIORITY)
        assert priority.index("setor_emissor") < priority.index("setor_executor")
        required_columns = list(gui_ssa.REQUIRED_GUI_COLUMNS)
        assert required_columns.index("setor_emissor") < required_columns.index(
            "setor_executor"
        )

    def test_default_display_columns_follow_requested_canonical_order(self):
        expected = [
            "numero_ssa",
            "localizacao_codigo",
            "situacao",
            "setor_emissor",
            "setor_executor",
            "derivada_de",
            "data_cadastro",
            "semana_cadastro",
            "descricao_ssa",
            "solicitante",
            "grau_prioridade_planejamento",
            "semana_programada",
            "total_de_reprogramacoes",
            "execucao_parcial",
            "descricao_execucao",
            "semana_executada",
            "responsavel_execucao",
        ]
        assert list(gui_ssa.GUI_MAIN_PREFERENCES["display_columns"]) == expected
        assert list(gui_ssa.REQUIRED_GUI_COLUMNS) == [
            "numero_ssa",
            "localizacao_codigo",
            "situacao",
            "setor_emissor",
            "setor_executor",
            "derivada_de",
            "data_cadastro",
            "solicitante",
            "grau_prioridade_planejamento",
            "semana_programada",
            "total_de_reprogramacoes",
            "execucao_parcial",
            "descricao_execucao",
            "semana_executada",
            "responsavel_execucao",
        ]

    def test_semana_programada_short_label_is_sem_prog(self):
        assert (
            gui_ssa.GUI_MAIN_PREFERENCES["column_display_names"]["semana_programada"]
            == "Sem. Prog."
        )

    def test_advanced_responsavel_selection_filters_use_full_button_labels(self):
        labels_by_key = {
            key: label for key, label in advanced_ui._ADVANCED_RESPONSAVEL_FIELD_DEFS
        }

        assert labels_by_key["prog"] == "Responsavel Programacao"
        assert labels_by_key["exec_resp"] == "Responsavel Execucao"

    def test_widths_and_short_labels_follow_latest_quick_adjustments(self):
        column_names = gui_ssa.GUI_MAIN_PREFERENCES["column_display_names"]
        column_widths = gui_ssa.GUI_MAIN_PREFERENCES["column_widths"]
        default_widths = DEFAULT_COLUMN_WIDTHS
        if sys.platform == "darwin":
            expected = {
                "grau_prioridade_emissao": 86,
                "grau_prioridade_planejamento": 98,
                "execucao_parcial": 78,
                "total_de_reprogramacoes": 96,
                "semana_executada": 60,
            }
        elif sys.platform == "win32":
            expected = {
                "grau_prioridade_emissao": 86,
                "grau_prioridade_planejamento": 128,
                "execucao_parcial": 78,
                "total_de_reprogramacoes": 96,
                "semana_executada": 92,
            }
        else:
            expected = {
                "grau_prioridade_emissao": 86,
                "grau_prioridade_planejamento": 122,
                "execucao_parcial": 130,
                "total_de_reprogramacoes": 96,
                "semana_executada": 96,
            }

        assert column_names["execucao_parcial"] == "Exec. Parc."
        assert default_widths["data_cadastro"] == 84
        assert (
            default_widths["grau_prioridade_emissao"]
            == expected["grau_prioridade_emissao"]
        )
        assert (
            default_widths["grau_prioridade_planejamento"]
            == expected["grau_prioridade_planejamento"]
        )
        assert default_widths["execucao_parcial"] == expected["execucao_parcial"]
        assert (
            default_widths["total_de_reprogramacoes"]
            == expected["total_de_reprogramacoes"]
        )
        assert default_widths["semana_executada"] == expected["semana_executada"]
        assert default_widths["responsavel_execucao"] == 150
        assert column_widths["data_cadastro"] >= default_widths["data_cadastro"]
        assert (
            column_widths["grau_prioridade_emissao"]
            >= default_widths["grau_prioridade_emissao"]
        )
        assert (
            column_widths["grau_prioridade_planejamento"]
            >= default_widths["grau_prioridade_planejamento"]
        )

    def test_column_filter_default_order_places_emissor_before_executor(self):
        columns = list(self.window._column_filter_default_columns())
        assert columns.index("setor_emissor") < columns.index("setor_executor")

    def test_filters_summary_clear_keeps_column_rows_visible(self, monkeypatch):
        self.window._active_column_filters = {
            "descricao_ssa": "",
            "setor_emissor": "IEE3",
            "setor_executor": "",
            "descricao_execucao": "",
        }
        monkeypatch.setattr(
            self.window,
            "_confirm_filter_summary_item_removal",
            lambda _text: True,
        )

        self.window._remove_filters_summary_actions(
            "Setor Emissor: IEE3",
            [{"kind": "column", "column": "setor_emissor"}],
        )

        assert self.window._active_column_filters.get("setor_emissor", None) == ""
        controls = self._get_column_filter_controls()
        if hasattr(self.window, "_expand_column_alias_for_filter"):
            emissor_label = self.window._expand_column_alias_for_filter("setor_emissor")
        else:
            emissor_label = self.window._resolve_column_display_name("setor_emissor")
        assert emissor_label in controls

    def test_gui_config_exposes_data_arquivo_origem_label_and_width(self):
        assert (
            gui_ssa.GUI_MAIN_PREFERENCES["column_display_names"]["data_arquivo_origem"]
            == "Data do Arquivo de Origem"
        )
        assert (
            gui_ssa.GUI_MAIN_PREFERENCES["column_widths"]["data_arquivo_origem"] >= 188
        )

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

        created_actions: list[_FakeAction] = []

        class _FakeMenu:
            def __init__(self, _parent=None):
                self.actions: list[_FakeAction] = []

            def addAction(self, text: str):
                action = _FakeAction(text)
                self.actions.append(action)
                created_actions.append(action)
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

        from gui.ssa import column_filter_panel

        monkeypatch.setattr(column_filter_panel, "QMenu", _FakeMenu)
        monkeypatch.setattr(
            self.window,
            "_expand_column_alias_for_filter",
            lambda _col: (_ for _ in ()).throw(RuntimeError("alias expansion failed")),
        )
        self.window._active_column_filters = None

        self.window._open_add_column_filter_menu()
        menu_columns = {action.data() for action in created_actions}

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

        created_actions.clear()
        self.window._active_column_filters = {"Data Cadastro": ""}
        self.window._open_add_column_filter_menu()
        menu_columns = {action.data() for action in created_actions}
        assert "Data Cadastro" in menu_columns
        active_action = next(
            action for action in created_actions if action.data() == "Data Cadastro"
        )
        assert active_action.checked is True

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

    def test_on_columns_changed_persists_visible_columns_state(self, monkeypatch):
        calls = {"persist": 0}

        def _fake_persist():
            calls["persist"] += 1

        monkeypatch.setattr(
            self.window, "_persist_visible_columns_order", _fake_persist
        )

        new_columns = [
            col for col in self.window.visible_columns if col != "descricao_ssa"
        ]
        self.window.on_columns_changed(new_columns)

        assert calls["persist"] == 1

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
            assert apply_btn.text() == "↵"
            assert clear_btn.text() == "⌫"
            assert hide_btn.text() == "-"
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

        status = self.window.filtered_status_label.text()
        assert status == "1 de 5 SSAs"

    def test_refresh_after_filter_change_skips_extra_filter_steps_without_active_filters(
        self, monkeypatch
    ):
        advanced_calls = {"count": 0}
        column_calls = {"count": 0}

        def _fail_advanced(df):
            advanced_calls["count"] += 1
            raise AssertionError("advanced filters should be skipped")

        def _fail_column(df):
            column_calls["count"] += 1
            raise AssertionError("column filters should be skipped")

        self.window.df_completo = self.base_df.copy()
        self.window._df_last_search_filtered = self.window.df_completo
        self.window.df_exibido = self.base_df.iloc[0:0].copy()
        self.window.search_input.setText("")
        self.window._advanced_filters = {}
        self.window._advanced_filters_active = False
        self.window._exclude_ste_sca = False
        for key in list(self.window._active_column_filters.keys()):
            self.window._active_column_filters[key] = ""

        monkeypatch.setattr(self.window, "_apply_advanced_filters", _fail_advanced)
        monkeypatch.setattr(self.window, "_apply_column_filters", _fail_column)

        self.window._refresh_after_filter_change()

        assert advanced_calls["count"] == 0
        assert column_calls["count"] == 0
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])

    def test_refresh_after_filter_change_skips_extra_filter_steps_for_simple_search_result(
        self, monkeypatch
    ):
        advanced_calls = {"count": 0}
        column_calls = {"count": 0}
        filtered = self.base_df.iloc[[4, 3, 0]].copy()
        filtered.attrs["ssa_sorted_for_display"] = True

        def _fail_advanced(df):
            advanced_calls["count"] += 1
            raise AssertionError("advanced filters should be skipped")

        def _fail_column(df):
            column_calls["count"] += 1
            raise AssertionError("column filters should be skipped")

        self.window._df_last_search_filtered = filtered
        self.window.df_exibido = self.base_df.iloc[0:0].copy()
        self.window.search_input.setText("MEL3")
        self.window._active_filter_search_display = "MEL3"
        self.window._pending_search_display = ""
        self.window._advanced_filters = {}
        self.window._advanced_filters_active = False
        self.window._exclude_ste_sca = False
        for key in list(self.window._active_column_filters.keys()):
            self.window._active_column_filters[key] = ""

        monkeypatch.setattr(self.window, "_apply_advanced_filters", _fail_advanced)
        monkeypatch.setattr(self.window, "_apply_column_filters", _fail_column)

        self.window._refresh_after_filter_change()

        assert advanced_calls["count"] == 0
        assert column_calls["count"] == 0
        assert self.window.df_exibido is filtered

    def test_refresh_after_filter_change_ignores_stale_search_base_for_pending_text(
        self,
    ):
        stale_filtered = self.base_df[self.base_df["numero_ssa"] == 1].copy()
        self.window._df_last_search_filtered = stale_filtered
        self.window._active_filter_search_display = "Teste A"
        self.window._pending_search_display = ""
        self.window.search_input.setText("Teste B")
        self.window._debounce_timer.stop()
        self.window._active_column_filters = {"situacao": "STE"}

        self.window._refresh_after_filter_change()

        assert self.window.df_exibido["numero_ssa"].tolist() == [2]
        assert self.window._active_filter_search_display == "Teste B"

    def test_set_filtered_count_status_accepts_suffix(self):
        self.window._set_filtered_count_status(filtered_total=2, original_total=5)
        status = self.window.filtered_status_label.text()
        assert status == "2 de 5 SSAs"

    def test_apply_advanced_filters_notice_uses_count_status_helper(self, monkeypatch):
        self.window._pending_search_display = "Busca X"

        def _fake_refresh():
            callback = getattr(self.window, "_adv_notice_callback", None)
            if callable(callback):
                callback("derivada_empty")

        monkeypatch.setattr(self.window, "_refresh_after_filter_change", _fake_refresh)
        self.window._apply_advanced_filters_from_ui(store_only=False)
        status = self.window.filtered_status_label.text()
        assert status == "5 de 5 SSAs"
        assert "Aviso" not in status

    def test_update_filters_summary_styles_active_state(self):
        self.window._active_column_filters = {"setor_executor": "IEE3"}

        self.window._update_filters_summary()

        frame_css = str(self.window.filters_summary_frame.styleSheet() or "")
        label_css = str(self.window.filters_summary_label.styleSheet() or "")
        assert "border:1px solid" in frame_css
        assert "font-weight:700" in label_css
        assert "background:transparent" in label_css

    def test_find_unmapped_alias_columns_reports_only_unmapped(self):
        self.window.internal_to_display["numero_ssa"] = "Numero SSA"
        missing = self.window._find_unmapped_alias_columns(
            ["numero_ssa", "descricao_ssa", "coluna_sem_alias", "#", "coluna_sem_alias"]
        )
        assert missing == ["coluna_sem_alias"]

    def test_general_search_and_or_display(self):
        realistic_df = self._build_realistic_base_df_50()
        assert len(realistic_df) == 50

        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        target_row = realistic_df.iloc[0]
        target_ssa = str(target_row["numero_ssa"])
        target_desc = str(target_row["descricao_ssa"])
        target_solicitante = str(target_row["solicitante"])
        exclude_solicitante = next(
            (
                str(name)
                for name in realistic_df["solicitante"].tolist()
                if str(name) != target_solicitante
            ),
            "SOLICITANTE_NAO_EXISTENTE",
        )

        self.window.search_input.setText(target_ssa)
        self.window.initiate_filtering()
        QApplication.processEvents()

        # Busca geral com termo unico deve localizar exatamente a SSA alvo
        visible_ssa = [str(value) for value in self._extract_visible_ssa()]
        assert Counter(visible_ssa) == Counter([target_ssa])
        assert self.window.df_exibido["descricao_ssa"].tolist() == [target_desc]
        assert self.window.search_input.text() == target_ssa

        # Combinacao com termo negativo deve manter resultado quando exclui solicitante diferente
        self.window.search_input.setText(f"{target_ssa}, !{exclude_solicitante}")
        self.window.initiate_filtering()
        QApplication.processEvents()
        visible_ssa = [str(value) for value in self._extract_visible_ssa()]
        assert Counter(visible_ssa) == Counter([target_ssa])
        assert (
            self.window.search_input.text() == f"{target_ssa}, !{exclude_solicitante}"
        )

    def test_general_search_undo_restores_previous_applied_filter_state(self):
        realistic_df = self._build_realistic_base_df_50()
        self.window._sync_filtering = True
        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        target_ssa = str(realistic_df.iloc[0]["numero_ssa"])
        self.window.search_input.setText(f"={target_ssa}")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert len(self.window.df_exibido) == 1
        assert self.window.search_input.text() == f"={target_ssa}"
        assert self.window.undo_filter_btn.isEnabled() is True

        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert len(self.window.df_exibido) == len(realistic_df)
        assert self.window.undo_filter_btn.isEnabled() is False

    def test_general_search_undo_after_column_filter_restores_applied_state(self):
        realistic_df = self._build_realistic_base_df_50()
        self.window._sync_filtering = True
        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        column_value = str(realistic_df.iloc[0]["setor_executor"])
        filtered_by_column = realistic_df[
            realistic_df["setor_executor"].astype(str) == column_value
        ]
        target_ssa = str(filtered_by_column.iloc[0]["numero_ssa"])

        self.window._active_column_filters["setor_executor"] = column_value
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert len(self.window.df_exibido) == len(filtered_by_column)

        self.window.search_input.setText(f"={target_ssa}")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert len(self.window.df_exibido) == 1

        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert (
            self.window._active_column_filters.get("setor_executor") == column_value
        )
        assert Counter(self.window.df_exibido["numero_ssa"]) == Counter(
            filtered_by_column["numero_ssa"]
        )

    def test_general_search_button_click_filters_real_table_content(self):
        realistic_df = self._build_realistic_base_df_50()
        assert len(realistic_df) == 50

        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        target_row = realistic_df.iloc[0]
        target_ssa = str(target_row["numero_ssa"])
        target_desc = str(target_row["descricao_ssa"])
        target_solicitante = str(target_row["solicitante"])
        exclude_solicitante = next(
            (
                str(name)
                for name in realistic_df["solicitante"].tolist()
                if str(name) != target_solicitante
            ),
            "SOLICITANTE_NAO_EXISTENTE",
        )

        main_ctx = self._panel_context()
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        main_ctx["search_input"].setText(f"{target_ssa}, !{exclude_solicitante}")
        cast(Any, QTest).mouseClick(
            main_ctx["search_button"], Qt.MouseButton.LeftButton
        )
        QApplication.processEvents()

        visible_ssa = [str(value) for value in self._extract_visible_ssa()]
        assert Counter(visible_ssa) == Counter([target_ssa])
        assert self.window.df_exibido["descricao_ssa"].tolist() == [target_desc]
        assert self.window.table_widget.rowCount() == 1

        descricao_idx = self.window._current_display_columns.index("descricao_ssa")
        descricao_item = self.window.table_widget.item(0, descricao_idx)

        assert descricao_item is not None
        assert descricao_item.text() == target_desc

    def test_general_search_zero_results_keeps_empty_display(self):
        realistic_df = self._build_realistic_base_df_50()
        assert len(realistic_df) == 50

        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.search_input.setText("Termo inexistente")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert self.window.df_exibido.empty
        assert self._extract_visible_ssa() == []
        assert "0 de 50 SSAs" in self.window.filtered_status_label.text()
        assert self.window.search_input.text() == "Termo inexistente"

    def test_general_search_ignores_complex_df_attrs_from_ssa_index_cache(self):
        realistic_df = self._build_realistic_base_df_50()
        target_ssa = str(realistic_df.iloc[0]["numero_ssa"])
        realistic_df.attrs["_ssa_series_index"] = {
            str(row["numero_ssa"]): row.copy() for _, row in realistic_df.iterrows()
        }

        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.search_input.setText(target_ssa)
        self.window.initiate_filtering()
        QApplication.processEvents()

        visible_ssa = [str(value) for value in self._extract_visible_ssa()]
        assert Counter(visible_ssa) == Counter([target_ssa])

    def test_general_search_does_not_persist_row_text_cache_on_same_dataframe(self):
        realistic_df = self._build_realistic_base_df_50()
        self.window._sync_filtering = True
        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())

        self.window.search_input.setText("Teste")
        self.window.initiate_filtering()
        QApplication.processEvents()

        self.window.search_input.setText("Exec")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert app_logic.FILTER_SEARCH_CACHE_ATTR not in self.window.df_completo.attrs

    def test_initiate_filtering_refines_previous_search_subset_when_safe(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        previous_subset = app_logic.filter_dataframe(
            self.base_df.copy(),
            ["MEL"],
            search_columns=filter_mixin.build_gui_general_search_columns(self.base_df),
        )
        self.window._df_last_search_filtered = previous_subset
        self.window._active_filter_search_display = "MEL"
        self.window.paginator.set_dataframe(self.base_df.copy())

        captured_sources: list[pd.DataFrame] = []
        original_apply_terms = self.window._apply_general_search_terms

        def _tracked_apply_terms(frame: pd.DataFrame, *args, **kwargs):
            captured_sources.append(frame)
            return original_apply_terms(frame, *args, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_apply_general_search_terms",
            _tracked_apply_terms,
        )

        self.window.search_input.setText("MEL3")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert captured_sources
        assert captured_sources[0] is previous_subset

    def test_initiate_filtering_broadening_search_uses_df_completo(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = app_logic.filter_dataframe(
            self.base_df.copy(),
            ["MEL3"],
            search_columns=filter_mixin.build_gui_general_search_columns(self.base_df),
        )
        self.window._active_filter_search_display = "MEL3"
        self.window.paginator.set_dataframe(self.base_df.copy())

        captured_sources: list[pd.DataFrame] = []
        original_apply_terms = self.window._apply_general_search_terms

        def _tracked_apply_terms(frame: pd.DataFrame, *args, **kwargs):
            captured_sources.append(frame)
            return original_apply_terms(frame, *args, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_apply_general_search_terms",
            _tracked_apply_terms,
        )

        self.window.search_input.setText("MEL")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert captured_sources
        assert captured_sources[0] is self.window.df_completo

    def test_initiate_filtering_refinement_with_advanced_filters_uses_df_completo(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = app_logic.filter_dataframe(
            self.base_df.copy(),
            ["MEL"],
            search_columns=filter_mixin.build_gui_general_search_columns(self.base_df),
        )
        self.window._active_filter_search_display = "MEL"
        self.window._advanced_filters_active = True
        self.window.paginator.set_dataframe(self.base_df.copy())

        captured_sources: list[pd.DataFrame] = []
        original_apply_terms = self.window._apply_general_search_terms

        def _tracked_apply_terms(frame: pd.DataFrame, *args, **kwargs):
            captured_sources.append(frame)
            return original_apply_terms(frame, *args, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_apply_general_search_terms",
            _tracked_apply_terms,
        )

        self.window.search_input.setText("MEL3")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert captured_sources
        assert captured_sources[0] is self.window.df_completo

    def test_initiate_filtering_refinement_with_column_filter_uses_df_completo(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = app_logic.filter_dataframe(
            self.base_df.copy(),
            ["MEL"],
            search_columns=filter_mixin.build_gui_general_search_columns(self.base_df),
        )
        self.window._active_filter_search_display = "MEL"
        self.window._active_column_filters["situacao"] = "APV"
        self.window.paginator.set_dataframe(self.base_df.copy())

        captured_sources: list[pd.DataFrame] = []
        original_apply_terms = self.window._apply_general_search_terms

        def _tracked_apply_terms(frame: pd.DataFrame, *args, **kwargs):
            captured_sources.append(frame)
            return original_apply_terms(frame, *args, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_apply_general_search_terms",
            _tracked_apply_terms,
        )

        self.window.search_input.setText("MEL3")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert captured_sources
        assert captured_sources[0] is self.window.df_completo

    def test_initiate_filtering_refinement_with_excluded_terminal_uses_df_completo(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = app_logic.filter_dataframe(
            self.base_df.copy(),
            ["MEL"],
            search_columns=filter_mixin.build_gui_general_search_columns(self.base_df),
        )
        self.window._active_filter_search_display = "MEL"
        self.window._exclude_ste_sca = True
        self.window.paginator.set_dataframe(self.base_df.copy())

        captured_sources: list[pd.DataFrame] = []
        original_apply_terms = self.window._apply_general_search_terms

        def _tracked_apply_terms(frame: pd.DataFrame, *args, **kwargs):
            captured_sources.append(frame)
            return original_apply_terms(frame, *args, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_apply_general_search_terms",
            _tracked_apply_terms,
        )

        self.window.search_input.setText("MEL3")
        self.window.initiate_filtering()
        QApplication.processEvents()

        assert captured_sources
        assert captured_sources[0] is self.window.df_completo

    def test_filter_dataframe_large_search_does_not_persist_row_text_cache(self):
        heavy_df = self._build_heavy_filters_df(rows=6000)

        filtered = app_logic.filter_dataframe(
            heavy_df,
            ["Descricao 5"],
            search_columns=["descricao_ssa", "setor_executor"],
        )

        assert not filtered.empty
        assert app_logic.FILTER_SEARCH_CACHE_ATTR not in heavy_df.attrs

    def test_filter_dataframe_large_anchored_regex_works_without_cached_base_lower_df(
        self,
    ):
        heavy_df = self._build_heavy_filters_df(rows=6000)

        filtered = app_logic.filter_dataframe(
            heavy_df,
            ["~^descricao 5"],
            search_columns=["descricao_ssa"],
        )

        assert not filtered.empty
        assert app_logic.FILTER_SEARCH_CACHE_ATTR not in heavy_df.attrs

    def test_build_gui_general_search_columns_skips_all_null_columns_from_attrs(self):
        df = self._build_heavy_filters_df(rows=8)
        for column_name in (
            "numero_ssa_relacionada_1",
            "numero_ssa_relacionada_2",
            "numero_ssa_relacionada_3",
            "setor_emissor_relacionado_1",
            "setor_executor_relacionado_1",
            "situacao_relacionada_1",
            "relacao",
        ):
            df[column_name] = pd.NA
        df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "descricao_ssa",
            "setor_executor",
            "setor_emissor",
            "descricao_execucao",
        ]

        columns = filter_mixin.build_gui_general_search_columns(df)

        assert "numero_ssa" in columns
        assert "descricao_ssa" in columns
        assert "numero_ssa_relacionada_1" not in columns
        assert "setor_emissor_relacionado_1" not in columns
        assert "relacao" not in columns

    def test_build_render_marker_sample_ignores_heavy_attrs_payload(self):
        sample_df = pd.DataFrame(
            {
                "numero_ssa": ["202500001", "202500002", "202500003"],
                "situacao": ["APV", "STE", "SES"],
            }
        )
        sample_df.attrs["_ssa_series_index"] = {
            f"ssa_{idx}": {"idx": idx} for idx in range(5000)
        }

        markers = ssa_gui_table._build_render_marker_sample(sample_df)

        assert markers[0][0] == "202500001"
        assert markers[-1][1] == "SES"

    def test_column_widths_stability_during_cycles(self):
        self.window.df_completo = self.base_df.copy()
        self.window.df_exibido = self.base_df.copy()
        self.window._df_last_search_filtered = self.base_df.copy()
        self.window.paginator.set_dataframe(self.base_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        def current_widths():
            return {
                column: self.window.table_widget.columnWidth(index)
                for index, column in enumerate(
                    getattr(self.window, "_current_display_columns", []) or []
                )
            }

        # User/runtime widths must be one source of truth across all reset paths.
        self.window.table_widget.setColumnWidth(1, 240)
        baseline_widths = current_widths()
        self.window._saved_gui_column_widths.update(baseline_widths)
        self.window._gui_column_pixel_widths.update(baseline_widths)

        # Aplica perfil OR, filtros gerais e limpa várias vezes
        self.window._apply_filter_profile("IEE3 + MEL3 + MEL4", refresh=True)
        QApplication.processEvents()
        assert current_widths() == baseline_widths

        self.window.search_input.setText("Teste A, Teste D")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert current_widths() == baseline_widths

        self.window._clear_all_column_filters()
        QApplication.processEvents()
        assert current_widths() == baseline_widths

        self.window.clear_filter()
        QApplication.processEvents()
        assert current_widths() == baseline_widths

        self.window._active_column_filters["descricao_ssa"] = "Teste"
        self.window._safe_store_last_filter_state("width_stability_global_clear")
        self.window._clear_all_filters_global()
        QApplication.processEvents()
        assert current_widths() == baseline_widths

        self.window._active_column_filters["descricao_ssa"] = "Teste"
        self.window._hard_reset_filters_state()
        QApplication.processEvents()
        assert current_widths() == baseline_widths

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
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        tiny_df = self.base_df.iloc[:1].copy()
        self.window.df_completo = tiny_df.copy()
        self.window.df_exibido = tiny_df.copy()
        self.window._df_last_search_filtered = tiny_df.copy()
        self._panel_context()["paginator"].set_dataframe(tiny_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        ctx = self._panel_context()
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
        self._set_filter_panel_tab("main")
        QApplication.processEvents()
        self.window.resize(1520, 980)
        QApplication.processEvents()
        self.window._sync_bottom_panel_heights()
        QApplication.processEvents()

        details_group = None
        filters_panel_group = None
        inner_groups = []
        for ctx in self._iter_panel_contexts():
            for key in (
                "details_group",
                "filters_panel_group",
                "adv_filters_group",
                "col_filters_group",
            ):
                widget = ctx.get(key)
                if widget is None:
                    continue
                if key == "details_group":
                    details_group = widget
                    continue
                if key == "filters_panel_group":
                    filters_panel_group = widget
                    continue
                if widget in inner_groups:
                    continue
                inner_groups.append(widget)

        assert details_group is not None
        assert filters_panel_group is not None
        assert len(inner_groups) >= 2
        splitter = self._panel_context()["main_bottom_splitter"]
        assert isinstance(splitter, QtWidgets.QSplitter)
        assert splitter.orientation() == Qt.Orientation.Vertical
        assert splitter.handleWidth() == 8
        assert "mainTableBottomSplitter" not in str(splitter.styleSheet() or "")
        assert abs(int(details_group.height()) - int(filters_panel_group.height())) <= 4
        assert int(details_group.height()) <= int(splitter.sizes()[1]) + 4
        assert int(filters_panel_group.height()) <= int(splitter.sizes()[1]) + 4
        parent = filters_panel_group.parentWidget()
        if parent is not None and int(parent.height()) > 0:
            parent_delta = int(parent.height()) - int(filters_panel_group.height())
            assert 0 <= parent_delta <= 4

    def test_main_bottom_splitter_persists_user_height(self, monkeypatch):
        self._set_filter_panel_tab("filters")
        self.window.resize(1520, 980)
        QApplication.processEvents()

        ctx = self._panel_context()
        splitter = ctx["main_bottom_splitter"]
        table = ctx["table_widget"]
        details_group = ctx["details_group"]
        filters_panel_group = ctx["filters_panel_group"]
        initial_table_height = int(table.height())

        splitter.setSizes([720, 210])
        QApplication.processEvents()
        self.window._save_main_bottom_splitter_pref()
        self.window._sync_bottom_panel_heights()
        QApplication.processEvents()

        saved_height = gui_ssa.GUI_MAIN_PREFERENCES["gui_settings"][
            "main_bottom_panel_height_px"
        ]
        assert 190 <= int(saved_height) <= 260
        assert int(table.height()) > initial_table_height
        assert abs(int(details_group.height()) - int(filters_panel_group.height())) <= 4

    def test_bottom_panels_splitter_handle_drag_resizes_table_and_panels(self):
        self._set_filter_panel_tab("filters")
        self.window.resize(1210, 920)
        QApplication.processEvents()
        self.window._restore_main_bottom_splitter_sizes()
        self.window._sync_bottom_panel_heights()
        QApplication.processEvents()

        ctx = self._panel_context()
        splitter = ctx["main_bottom_splitter"]
        details_group = ctx["details_group"]
        filters_panel_group = ctx["filters_panel_group"]
        handle = cast(QtWidgets.QWidget, splitter.handle(1))
        start_sizes = list(splitter.sizes())
        start = handle.rect().center()
        end = start + QPoint(0, 120)

        qt_test = cast(Any, QTest)
        qt_test.mousePress(
            handle,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            start,
        )
        qt_test.mouseMove(handle, end, delay=50)
        qt_test.mouseRelease(
            handle,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            end,
            delay=50,
        )
        QApplication.processEvents()

        end_sizes = list(splitter.sizes())
        assert end_sizes[0] > start_sizes[0]
        assert end_sizes[1] < start_sizes[1]
        assert abs(int(details_group.height()) - int(filters_panel_group.height())) <= 4
        assert int(details_group.height()) <= end_sizes[1] + 4
        assert int(filters_panel_group.height()) <= end_sizes[1] + 4

    def test_filter_summary_bar_keeps_geometry_when_switching_filter_tabs(self):
        self.window.resize(1280, 880)
        QApplication.processEvents()

        measurements = []
        for index in (0, 1, 0, 1):
            self._set_filter_panel_tab("filters" if index == 1 else "main")
            QApplication.processEvents()
            ctx = self._panel_context()
            summary = ctx["filters_summary_frame"]
            table = ctx["table_widget"]
            measurements.append(
                (
                    int(summary.height()),
                    int(summary.mapToGlobal(QPoint(0, 0)).y()),
                    int(table.mapToGlobal(QPoint(0, 0)).y()),
                )
            )

        assert {height for height, _summary_y, _table_y in measurements} == {44}
        assert len({table_y for _height, _summary_y, table_y in measurements}) == 1

    def test_filter_summary_active_items_stay_in_horizontal_scroll_area(self):
        self.window.resize(980, 760)
        self.window.search_input.setText("Texto muito longo " * 20)
        self.window._active_column_filters["descricao_ssa"] = "Filtro longo " * 30
        self.window._update_filters_summary()
        QApplication.processEvents()

        scroll = self.window.filters_summary_scroll
        items_widget = self.window.filters_summary_items_widget
        buttons = items_widget.findChildren(QPushButton)

        assert str(self.window.filters_summary_label.text() or "") == ""
        assert self.window.filters_summary_label.isVisible() is False
        assert isinstance(scroll, QtWidgets.QScrollArea)
        assert scroll.isVisible() is True
        assert scroll.height() <= 36
        assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert items_widget.sizeHint().width() > scroll.viewport().width()
        assert scroll.horizontalScrollBar().maximum() > 0
        assert {button.y() for button in buttons} == {0}

    def test_filter_summary_button_pool_discards_hidden_excess_after_spike(self):
        presenter = self.window._get_filter_summary_presenter()
        assert presenter is not None

        def _entries(total: int) -> list[dict[str, Any]]:
            return [
                {
                    "text": f"Filtro {index}",
                    "actions": [{"kind": "search", "value": str(index)}],
                }
                for index in range(total)
            ]

        presenter.update(
            theme_name="dark",
            summary_text="Filtros ativos",
            active_state=True,
            entries=_entries(80),
            on_remove=lambda _text, _actions: None,
        )
        QApplication.processEvents()
        assert len(presenter._button_pool) == 80

        presenter.update(
            theme_name="dark",
            summary_text="Filtros ativos",
            active_state=True,
            entries=_entries(1),
            on_remove=lambda _text, _actions: None,
        )
        QApplication.processEvents()
        assert len(presenter._button_pool) <= SUMMARY_BUTTON_POOL_LIMIT

        presenter.update(
            theme_name="dark",
            summary_text="Filtros ativos",
            active_state=True,
            entries=_entries(2),
            on_remove=lambda _text, _actions: None,
        )
        QApplication.processEvents()
        visible_buttons = [
            button
            for button in presenter._button_pool
            if isinstance(button, QPushButton) and button.isVisible()
        ]
        assert [button.text() for button in visible_buttons[:2]] == [
            "Filtro 0",
            "Filtro 1",
        ]

    def test_filter_summary_button_pool_keeps_exact_limit(self):
        presenter = self.window._get_filter_summary_presenter()
        assert presenter is not None
        buttons = [QPushButton() for _ in range(SUMMARY_BUTTON_POOL_LIMIT)]
        presenter._button_pool = buttons

        presenter._trim_hidden_button_pool(
            layout=self.window.filters_summary_items_layout,
            visible_button_count=0,
        )

        assert presenter._button_pool == buttons

    def test_filter_summary_button_pool_trims_one_above_limit(self):
        presenter = self.window._get_filter_summary_presenter()
        assert presenter is not None

        class _TrackingButton(QPushButton):
            def __init__(self):
                super().__init__()
                self.delete_later_called = False

            def deleteLater(self):
                self.delete_later_called = True
                return super().deleteLater()

        stale_button = _TrackingButton()
        presenter._button_pool = [
            QPushButton() for _ in range(SUMMARY_BUTTON_POOL_LIMIT)
        ] + [stale_button]

        presenter._trim_hidden_button_pool(
            layout=self.window.filters_summary_items_layout,
            visible_button_count=0,
        )

        assert len(presenter._button_pool) == SUMMARY_BUTTON_POOL_LIMIT
        assert stale_button.delete_later_called is True

    def test_filter_summary_button_pool_still_deletes_when_layout_remove_fails(self):
        presenter = self.window._get_filter_summary_presenter()
        assert presenter is not None

        class _FailingLayout:
            def removeWidget(self, _button):
                raise RuntimeError("wrapped C/C++ object has been deleted")

        class _TrackingButton(QPushButton):
            def __init__(self):
                super().__init__()
                self.delete_later_called = False

            def deleteLater(self):
                self.delete_later_called = True
                return super().deleteLater()

        stale_button = _TrackingButton()
        presenter._button_pool = [
            QPushButton() for _ in range(SUMMARY_BUTTON_POOL_LIMIT)
        ] + [stale_button]

        presenter._trim_hidden_button_pool(
            layout=_FailingLayout(),
            visible_button_count=0,
        )

        assert len(presenter._button_pool) == SUMMARY_BUTTON_POOL_LIMIT
        assert stale_button.delete_later_called is True

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
        for ctx in self._iter_panel_contexts():
            button = ctx.get("clear_filter_button")
            assert button is not None
            assert button.text() == "⌫"
            tooltip = str(button.toolTip() or "").casefold()
            assert "apenas a busca" in tooltip
            assert "texto" in tooltip
            assert "selecao" in tooltip

    def test_search_buttons_use_single_live_handlers(self):
        main_ctx = self._panel_context()
        filters_ctx = self._panel_context()
        main_ctx["clear_filter_button"].setEnabled(True)
        filters_ctx["clear_filter_button"].setEnabled(True)
        assert main_ctx["search_button"] is filters_ctx["search_button"]
        assert main_ctx["clear_filter_button"] is filters_ctx["clear_filter_button"]

        self.window.search_input.setText("Teste A")
        cast(Any, QTest).mouseClick(main_ctx["search_button"], Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])

        cast(Any, QTest).mouseClick(
            filters_ctx["clear_filter_button"], Qt.MouseButton.LeftButton
        )
        QApplication.processEvents()
        assert self.window.search_input.text() == ""
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])

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

    def test_clear_all_filters_repaints_table_when_render_signature_is_stale(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        assert getattr(self.window, "_last_table_render_signature", None) is not None

        situacao_col = self.window._current_display_columns.index("situacao")
        descricao_col = self.window._current_display_columns.index("descricao_ssa")
        for row in range(self.window.table_widget.rowCount()):
            for col in (situacao_col, descricao_col):
                item = self.window.table_widget.item(row, col)
                assert item is not None
                item.setText("")

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window.table_widget.updatesEnabled() is True
        assert not any(
            self.window.table_widget.isRowHidden(row)
            for row in range(self.window.table_widget.rowCount())
        )
        assert all(
            self.window.table_widget.columnWidth(col) > 0
            for col in range(self.window.table_widget.columnCount())
        )
        assert self.window.table_widget.item(0, situacao_col).text().strip()
        assert self.window.table_widget.item(0, descricao_col).text().strip()

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
        for ctx in self._iter_panel_contexts():
            ctx["search_input"].setText("")
        self.window._refresh_after_filter_change()
        QApplication.processEvents()
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_filter_button_state_syncs_across_tabs_without_switch(self):
        buttons = []
        for ctx in self._iter_panel_contexts():
            button = ctx.get("clear_filter_button")
            if button is not None:
                buttons.append(button)
        assert len(buttons) == 1
        assert all(button.isEnabled() is False for button in buttons)

        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert all(button.isEnabled() is True for button in buttons)

        self.window.clear_filter()
        QApplication.processEvents()
        assert all(button.isEnabled() is False for button in buttons)

    def test_three_repeated_clear_search_clicks_offer_hard_reset(self):
        main_ctx = self._panel_context()
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
        filters_ctx = self._panel_context()
        self._set_filter_panel_tab("filters")
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
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._advanced_filters = {"setor_executor": ["IEE3"]}
        self.window._advanced_filters_active = True
        self.window._adv_options_dirty = False
        self.window._adv_options_scheduled = True
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.mark_materialized(responsavel_state.all_prefixes)
        assert responsavel_state.status_flags() == (True, False)

        with patch.object(
            self.window, "_refresh_advanced_filter_options", return_value=None
        ) as refresh_mock:
            self.window._clear_advanced_filters()
            QApplication.processEvents()

        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert self.window._adv_options_dirty is False
        assert responsavel_state.built_prefixes == set()
        assert responsavel_state.dirty_prefixes == responsavel_state.all_prefixes
        refresh_mock.assert_called_once()

    def test_undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore(self):
        undo_buttons = []
        for ctx in self._iter_panel_contexts():
            button = ctx.get("undo_filter_btn")
            if button is not None:
                undo_buttons.append(button)
        assert len(undo_buttons) == 1

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

    def test_restore_last_filter_state_recomputes_general_search_without_snapshot_df(
        self, monkeypatch
    ):
        realistic_df = self._build_realistic_base_df_50()
        self.window._sync_filtering = True
        self.window.df_completo = realistic_df.copy()
        self.window.df_exibido = realistic_df.copy()
        self.window._df_last_search_filtered = realistic_df.copy()
        self.window.paginator.set_dataframe(realistic_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.search_input.setText("Exec 1")
        self.window.initiate_filtering()
        QApplication.processEvents()
        filtered_before = self.window.df_exibido.copy()

        self.window._safe_store_last_filter_state("test_column_filter")
        self.window._active_column_filters["setor_executor"] = "SETOR_00"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert self.window._last_filter_state is not None
        assert "df_last_search_filtered" not in self.window._last_filter_state
        summary_updates = []
        original_update_summary = self.window._update_filters_summary

        def _tracked_update_summary():
            summary_updates.append(1)
            return original_update_summary()

        monkeypatch.setattr(
            self.window,
            "_update_filters_summary",
            _tracked_update_summary,
        )

        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window.search_input.text().strip() == "Exec 1"
        assert self.window._active_column_filters["setor_executor"] == ""
        assert Counter(self.window.df_exibido["numero_ssa"]) == Counter(
            filtered_before["numero_ssa"]
        )
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "Busca: 'Exec 1'" in summary_buttons
        assert summary_updates

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
        assert emissor_clear.text() == "⌫"
        assert "limpa o valor" in (emissor_clear.toolTip() or "").casefold()
        assert emissor_hide.text() == "-"
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
        assert first_context.startswith("sha256:")

        self.window._on_exclude_ste_sca_toggled(True)
        second_context = self.window._build_filter_cache_context()
        assert second_context != first_context
        assert second_context.startswith("sha256:")

        self.window._clear_all_filters_global()
        QApplication.processEvents()
        assert self.window._build_filter_cache_context() == ""

    def test_filters_summary_shows_exclude_ste_sca_as_active_restriction(self):
        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()

        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "situacao!=SCA/SES/STE" in summary_buttons

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

    def test_build_column_mask_allows_safe_anchor_regex(self):
        series = pd.Series(["foo start", "prefix foo"], dtype="string")
        mask = self.window._build_column_mask(series, "~^foo")
        assert list(mask) == [True, False]

    def test_build_column_mask_rejects_unapproved_regex_quantifier(self):
        series = pd.Series(["foo123bar", "foo.*bar"], dtype="string")
        mask = self.window._build_column_mask(series, "~foo.*bar")
        assert list(mask) == [False, True]

    def test_activate_column_filter_stores_undo_snapshot(self):
        self.window._last_filter_state = None
        self.window.search_input.setText("Marca")
        QApplication.processEvents()

        self.window._activate_column_filter("coluna_temporaria_teste")
        QApplication.processEvents()

        assert self.window._last_filter_state is not None
        snapshot = self.window._last_filter_state
        assert snapshot.get("search_text", "").strip() == ""
        assert "coluna_temporaria_teste" not in (
            snapshot.get("active_column_filters") or {}
        )
        assert "df_last_search_filtered" not in snapshot

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
        with (
            patch("gui.gui_ssa.QMessageBox.information", return_value=None),
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                side_effect=[("Zeta filtro", True), ("Alfa filtro", True)],
            ),
        ):
            self.window.persistent_filters = []
            self.window.search_input.setText("Zebra filtro")
            self.window.save_current_filter()
            self.window.search_input.setText("Alfa filtro")
            self.window.save_current_filter()

        names = [f["name"] for f in self.window.persistent_filters]
        assert names == sorted(names, key=lambda n: n.casefold())

    def test_persistent_filter_saves_and_restores_all_filter_state(self):
        with (
            patch.object(QMessageBox, "information"),
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Executor MEL4", True),
            ),
        ):
            self.window.search_input.clear()
            self.window._active_column_filters["setor_executor"] = "MEL4"
            self.window._exclude_ste_sca = True
            self.window.save_current_filter()

        assert len(self.window.persistent_filters) == 1
        saved_filter = self.window.persistent_filters[0]
        assert saved_filter["name"] == "Executor MEL4"
        assert saved_filter["terms"] == ""
        assert saved_filter["state"]["active_column_filters"]["setor_executor"] == "MEL4"
        assert saved_filter["state"]["exclude_ste_sca"] is True

        self.window._active_column_filters["setor_executor"] = ""
        self.window._exclude_ste_sca = False
        self.window.apply_persistent_filter(saved_filter)
        QApplication.processEvents()

        assert self.window.search_input.text().strip() == ""
        assert self.window._active_column_filters["setor_executor"] == "MEL4"
        assert self.window._exclude_ste_sca is True

    def test_persistent_filter_save_snapshot_failure_warns_without_saving(self):
        with (
            patch.object(
                self.window,
                "_snapshot_filter_state",
                side_effect=RuntimeError("snapshot failed"),
            ),
            patch.object(QMessageBox, "warning") as warning_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText"
            ) as name_mock,
        ):
            self.window.save_current_filter()

        assert self.window.persistent_filters == []
        assert not os.path.exists(self._saved_filters_path)
        assert name_mock.call_count == 0
        assert warning_mock.call_count == 1
        assert warning_mock.call_args.args[1] == "Erro"
        assert "Nao foi possivel ler o filtro atual" in warning_mock.call_args.args[2]

    def test_persistent_filter_apply_copy_failure_warns_and_preserves_undo(self):
        controller = self.window._get_persistent_filter_ui_controller()
        saved_filter = {
            "name": "Filtro quebrado",
            "terms": "",
            "state": {
                "search_text": "",
                "active_column_filters": {"setor_executor": "MEL4"},
            },
        }
        original_undo = {"search_text": "undo original"}
        self.window._last_filter_state = original_undo

        with (
            patch.object(
                controller,
                "copy_filter_mapping",
                side_effect=RuntimeError("copy failed"),
            ),
            patch.object(QMessageBox, "warning") as warning_mock,
        ):
            self.window.apply_persistent_filter(saved_filter)

        assert self.window._last_filter_state is original_undo
        assert self.window._active_column_filters.get("setor_executor") != "MEL4"
        assert warning_mock.call_count == 1
        assert warning_mock.call_args.args[1] == "Erro"
        assert "Nao foi possivel aplicar o filtro salvo" in warning_mock.call_args.args[2]

    def test_persistent_filter_apply_restore_failure_warns_and_preserves_undo(self):
        saved_filter = {
            "name": "Filtro quebrado",
            "terms": "",
            "state": {
                "search_text": "",
                "active_column_filters": {"setor_executor": "MEL4"},
            },
        }
        original_undo = {"search_text": "undo original"}
        self.window._last_filter_state = original_undo

        with (
            patch.object(
                self.window,
                "_restore_last_filter_state",
                side_effect=RuntimeError("restore failed"),
            ),
            patch.object(QMessageBox, "warning") as warning_mock,
        ):
            self.window.apply_persistent_filter(saved_filter)

        assert self.window._last_filter_state is original_undo
        assert self.window._active_column_filters.get("setor_executor") != "MEL4"
        assert warning_mock.call_count == 1
        assert warning_mock.call_args.args[1] == "Erro"
        assert "Nao foi possivel aplicar o filtro salvo" in warning_mock.call_args.args[2]

    def test_persistent_filter_save_materializes_pending_responsavel_execucao(self):
        df = self.base_df.assign(
            responsavel_execucao=[
                "Resp Exec A",
                "Resp Exec B",
                "Resp Exec C",
                "Resp Exec D",
                "Resp Exec E",
            ]
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()
        self.window._ensure_responsavel_options_materialized(
            target_prefix="adv_responsavel_execucao"
        )
        QApplication.processEvents()

        checks = getattr(self.window, "adv_responsavel_execucao_checks", []) or []
        target_check = next(check for check in checks if check.property("value"))
        target_value = str(target_check.property("value") or "")
        target_check.setChecked(True)
        QApplication.processEvents()

        assert self.window._advanced_filters["responsavel_execucao"] == [target_value]
        assert self.window._advanced_filters_active is True

        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Responsavel execucao", True),
            ),
        ):
            self.window.save_current_filter()

        assert len(self.window.persistent_filters) == 1
        saved_filter = self.window.persistent_filters[0]
        advanced = saved_filter["state"]["advanced_filters"]
        assert advanced["responsavel_execucao"] == [target_value]
        assert saved_filter["state"]["advanced_filters_active"] is True
        assert not any(
            call_args.args[2] == "Este filtro ja esta salvo."
            for call_args in info_mock.call_args_list
        )

    def test_persistent_filter_distinguishes_pending_responsavel_execucao_values(self):
        df = self.base_df.assign(
            responsavel_execucao=[
                "Resp Exec A",
                "Resp Exec B",
                "Resp Exec C",
                "Resp Exec D",
                "Resp Exec E",
            ]
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()
        self.window._ensure_responsavel_options_materialized(
            target_prefix="adv_responsavel_execucao"
        )
        QApplication.processEvents()

        checks = [
            check
            for check in (getattr(self.window, "adv_responsavel_execucao_checks", []) or [])
            if check.property("value")
        ]
        first_check, second_check = checks[:2]
        first_value = str(first_check.property("value") or "")
        second_value = str(second_check.property("value") or "")

        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                side_effect=[("Responsavel A", True), ("Responsavel B", True)],
            ),
        ):
            self.window.search_input.setText("responsavel")
            first_check.setChecked(True)
            QApplication.processEvents()
            self.window.save_current_filter()

            first_check.setChecked(False)
            second_check.setChecked(True)
            QApplication.processEvents()
            self.window.save_current_filter()

        assert len(self.window.persistent_filters) == 2
        saved_values = [
            item["state"]["advanced_filters"]["responsavel_execucao"][0]
            for item in self.window.persistent_filters
        ]
        assert sorted(saved_values) == sorted([first_value, second_value])
        assert not any(
            call_args.args[2] == "Este filtro ja esta salvo."
            for call_args in info_mock.call_args_list
        )

    def test_persistent_filters_reload_from_saved_file(self):
        with (
            patch.object(QMessageBox, "information"),
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Executor salvo", True),
            ),
        ):
            self.window.search_input.clear()
            self.window._active_column_filters["setor_executor"] = "MEL4"
            self.window.save_current_filter()

        assert os.path.exists(self._saved_filters_path)

        self.window.persistent_filters = []
        self.window.load_persistent_filters()

        assert len(self.window.persistent_filters) == 1
        saved = self.window.persistent_filters[0]
        assert saved["name"] == "Executor salvo"
        assert saved["state"]["active_column_filters"]["setor_executor"] == "MEL4"

    def test_persistent_filter_uses_manual_name_and_applies_saved_terms(self):
        with (
            patch.object(QMessageBox, "information"),
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Minha consulta", True),
            ),
        ):
            self.window.search_input.setText("Teste C")
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

        assert len(self.window.persistent_filters) == 1
        saved_filter = self.window.persistent_filters[0]
        assert saved_filter["name"] == "Minha consulta"
        with open(self._saved_filters_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["filters"][0]["name"] == "Minha consulta"

        self.window.update_filter_tags()
        QApplication.processEvents()
        tag_texts = [
            str(button.text() or "")
            for button in self.window.filter_tags_widget.findChildren(QPushButton)
        ]
        assert "Minha consulta" in tag_texts

        self.window.search_input.clear()
        self.window.initiate_filtering()
        self.window.apply_persistent_filter(saved_filter)
        QApplication.processEvents()

        assert self.window.search_input.text() == "Teste C"
        assert self.window.df_exibido["numero_ssa"].tolist() == [3]

    def test_persistent_filter_tags_refresh_theme_colors_after_theme_change(self):
        self.window.persistent_filters = [
            {"name": "!scc", "terms": "!scc", "state": {}},
            {"name": "br...", "terms": "braba", "state": {}},
        ]

        self.window.apply_theme("dracula")
        QApplication.processEvents()
        dark_pairs = self._persistent_filter_tag_button_pairs()
        assert dark_pairs
        dark_style = dark_pairs[0][0].styleSheet()
        dark_remove_style = dark_pairs[0][1].styleSheet()
        dark_roles = get_theme_roles("dracula")
        assert f"color: {dark_roles['input_text']}" in dark_style
        assert f"border: 1px solid {dark_roles['tag_border']}" in dark_style
        assert f"border: 1px solid {dark_roles['tag_border']}" in dark_remove_style

        self.window.apply_theme("paper")
        QApplication.processEvents()
        light_pairs = self._persistent_filter_tag_button_pairs()
        assert light_pairs
        light_style = light_pairs[0][0].styleSheet()
        light_remove_style = light_pairs[0][1].styleSheet()
        light_roles = get_theme_roles("paper")
        assert f"color: {light_roles['input_text']}" in light_style
        assert f"border: 1px solid {light_roles['tag_border']}" in light_style
        assert f"border: 1px solid {light_roles['tag_border']}" in light_remove_style
        assert dark_roles["input_text"] not in light_style
        assert dark_roles["tag_border"] not in light_style

    def test_persistent_filter_save_rejects_duplicate_manual_name(self):
        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                side_effect=[("Minha consulta", True), (" minha consulta ", True)],
            ) as name_mock,
        ):
            self.window.search_input.setText("Teste A")
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

            self.window.search_input.setText("Teste B")
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

        assert name_mock.call_count == 2
        assert len(self.window.persistent_filters) == 1
        assert self.window.persistent_filters[0]["name"] == "Minha consulta"
        assert self.window.persistent_filters[0]["terms"] == "Teste A"
        assert info_mock.call_args_list[-1].args[2] == (
            "Ja existe um filtro salvo com este nome."
        )

    def test_persistent_filter_restores_search_situacao_and_quick_visual_state(self):
        scenario_df = self.base_df.copy()
        scenario_df.loc[4, "situacao"] = "STE"
        scenario_df.loc[4, "localizacao_codigo"] = "G097F001"
        self.window.df_completo = scenario_df.copy()
        self.window.df_exibido = scenario_df.copy()
        self.window._df_last_search_filtered = scenario_df.copy()
        self.window.paginator.set_dataframe(scenario_df.copy())

        with (
            patch.object(QMessageBox, "information"),
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("STE sem G097", True),
            ),
        ):
            self.window.search_input.setText("!G097")
            self.window._active_column_filters["situacao"] = "STE"
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

        saved_filter = self.window.persistent_filters[0]
        assert saved_filter["name"] == "STE sem G097"

        self.window.clear_filter()
        QApplication.processEvents()
        self.window.apply_persistent_filter(saved_filter)
        QApplication.processEvents()

        buttons = getattr(self.window, "quick_situacao_buttons", {})
        assert self.window.search_input.text() == "!G097"
        assert self.window._active_column_filters.get("situacao") == "STE"
        assert buttons["STE"].isChecked() is True
        assert set(self.window.df_exibido["situacao"].astype(str)) == {"STE"}
        assert not self.window.df_exibido["localizacao_codigo"].astype(str).str.contains(
            "G097", case=False
        ).any()

    def test_persistent_filter_save_cancel_does_not_create_filter(self):
        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Filtro ignorado", False),
            ) as name_mock,
        ):
            self.window.search_input.setText("Teste A")
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

        assert name_mock.call_count == 1
        assert info_mock.call_count == 0
        assert self.window.persistent_filters == []
        assert not os.path.exists(self._saved_filters_path)

    def test_persistent_filter_save_empty_name_does_not_create_filter(self):
        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("   ", True),
            ),
        ):
            self.window.search_input.setText("Teste A")
            self.window.initiate_filtering()
            QApplication.processEvents()
            self.window.save_current_filter()

        assert self.window.persistent_filters == []
        assert info_mock.call_args.args[2] == "Informe um nome para salvar o filtro."
        assert not os.path.exists(self._saved_filters_path)

    def test_persistent_filters_reload_legacy_terms_without_state(self):
        payload = {
            "version": 1,
            "filters": [{"name": "Legado", "terms": "Teste C"}],
        }
        with open(self._saved_filters_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

        self.window.persistent_filters = []
        self.window.load_persistent_filters()

        assert self.window.persistent_filters == [
            {"name": "Legado", "terms": "Teste C"}
        ]

    def test_persistent_filter_tags_do_not_expand_search_row_width(self):
        long_name = "Filtro salvo com nome grande para testar largura " * 3
        self.window.persistent_filters = [
            {"name": f"{long_name}{idx}", "terms": f"Teste {idx}"}
            for idx in range(12)
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        assert self.window.filter_tags_widget.maximumWidth() <= 280
        assert self.window.filter_tags_widget.width() <= 280
        for i in range(self.window.filter_tags_layout.count()):
            tag_item = self.window.filter_tags_layout.itemAt(i)
            tag_widget = tag_item.widget() if tag_item else None
            tag_layout = tag_widget.layout() if tag_widget else None
            if tag_layout is None:
                continue
            tag_button_item = tag_layout.itemAt(0)
            tag_button = tag_button_item.widget() if tag_button_item else None
            assert tag_button is not None
            assert tag_button.maximumWidth() <= 180

    def test_persistent_filter_tag_describes_column_state_without_terms(self):
        self.window.persistent_filters = [
            {
                "name": "Filtro coluna",
                "terms": "",
                "state": {
                    "search_text": "",
                    "active_column_filters": {"setor_executor": "MEL4"},
                    "advanced_filters": {},
                    "advanced_filters_active": False,
                },
            }
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        tag_button = self._first_persistent_filter_tag_button()
        assert tag_button is not None
        assert tag_button.text().strip()
        assert "*" in tag_button.text()
        assert "[estado]" not in tag_button.text()
        tooltip = str(tag_button.toolTip() or "")
        assert "Clique para aplicar filtro salvo" in tooltip
        assert "Coluna setor_executor: MEL4" in tooltip

    def test_persistent_filter_tag_describes_advanced_state_without_terms(self):
        self.window.persistent_filters = [
            {
                "name": "Filtro avancado",
                "terms": "",
                "state": {
                    "search_text": "",
                    "active_column_filters": {},
                    "advanced_filters": {
                        "responsavel_execucao": ["Resp Exec A"],
                        "situacao": ["STE"],
                    },
                    "advanced_filters_active": True,
                },
            }
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        tag_button = self._first_persistent_filter_tag_button()
        assert tag_button is not None
        assert "*" in tag_button.text()
        assert "[estado]" not in tag_button.text()
        tooltip = str(tag_button.toolTip() or "")
        assert "Avancado responsavel_execucao: Resp Exec A" in tooltip
        assert "Avancado situacao: STE" in tooltip

    def test_persistent_filter_tag_visuals_stay_compact_with_state_only_filters(self):
        self.window.persistent_filters = [
            {
                "name": f"Filtro combinado {idx}",
                "terms": "",
                "state": {
                    "search_text": "",
                    "active_column_filters": {"setor_executor": f"MEL{idx}"},
                    "advanced_filters": {
                        "responsavel_execucao": [f"Resp Exec {idx}"]
                    },
                    "advanced_filters_active": True,
                },
            }
            for idx in range(1, 5)
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        pairs = self._persistent_filter_tag_button_pairs()
        assert len(pairs) == 4
        for tag_button, remove_button in pairs:
            assert tag_button.objectName() == "persistentFilterTagButton"
            assert remove_button.objectName() == "persistentFilterRemoveButton"
            assert tag_button.objectName() != remove_button.objectName()
            assert tag_button.text().strip()
            assert "*" in tag_button.text()
            assert "[estado]" not in tag_button.text()
            assert remove_button.text() == "X"
            assert remove_button.maximumWidth() <= 20
            tooltip = str(tag_button.toolTip() or "")
            assert "Clique para aplicar filtro salvo" in tooltip
            assert "Coluna setor_executor:" in tooltip
            assert "Avancado responsavel_execucao:" in tooltip

    def test_persistent_filter_tag_uses_fallback_for_invisible_name(self):
        self.window.persistent_filters = [
            {
                "name": "\u200b",
                "terms": "",
                "state": {
                    "search_text": "",
                    "active_column_filters": {"situacao": "STE"},
                    "advanced_filters": {},
                    "advanced_filters_active": False,
                },
            }
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        tag_button = self._first_persistent_filter_tag_button()
        assert tag_button is not None
        assert tag_button.text().startswith("Filtro salvo")
        assert tag_button.text().strip()
        assert "Coluna situacao: STE" in str(tag_button.toolTip() or "")

    def test_legacy_persistent_filter_tag_keeps_terms_description(self):
        self.window.persistent_filters = [
            {"name": "Legado", "terms": "Teste C"}
        ]

        self.window.update_filter_tags()
        QApplication.processEvents()

        tag_button = self._first_persistent_filter_tag_button()
        assert tag_button is not None
        assert tag_button.text() == "Legado"
        tooltip = str(tag_button.toolTip() or "")
        assert "Busca: Teste C" in tooltip
        assert "[estado]" not in tag_button.text()

    def test_persistent_filter_deduplicates_state_with_set_values(self):
        with (
            patch.object(QMessageBox, "information") as info_mock,
            patch(
                "gui.ssa.persistent_filter_ui.QInputDialog.getText",
                return_value=("Executor MEL4", True),
            ) as name_mock,
        ):
            self.window.search_input.clear()
            self.window._active_column_filters["setor_executor"] = "MEL4"
            self.window._hidden_column_filter_lines = {"setor_emissor", "situacao"}
            self.window.save_current_filter()

            self.window._hidden_column_filter_lines = {"situacao", "setor_emissor"}
            self.window.save_current_filter()

        assert len(self.window.persistent_filters) == 1
        assert name_mock.call_count == 1
        assert info_mock.call_args_list[-1].args[2] == "Este filtro ja esta salvo."

    def test_legacy_persistent_filter_applies_terms_not_raw_dict(self):
        legacy_filter = {"name": "Legado", "terms": "Teste C"}

        self.window.apply_persistent_filter(legacy_filter)
        QApplication.processEvents()

        assert self.window.search_input.text() == "Teste C"
        assert "{" not in self.window.search_input.text()

    def test_graphical_remove_active_persistent_filter_can_be_undone(self):
        self.window.search_input.setText("Teste C")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert self.window.df_exibido["numero_ssa"].tolist() == [3]
        assert str(self.window.filters_summary_label.text() or "") == ""
        assert self.window.filters_summary_label.isVisible() is False
        assert "Busca: 'Teste C'" in [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert self.window._get_visual_filter_columns() == set()

        self.window.persistent_filters = [
            {"name": "Filtro Teste C", "terms": "Teste C"}
        ]
        self.window.update_filter_tags()
        QApplication.processEvents()

        remove_button = None
        for i in range(self.window.filter_tags_layout.count()):
            tag_item = self.window.filter_tags_layout.itemAt(i)
            tag_widget = tag_item.widget() if tag_item else None
            tag_layout = tag_widget.layout() if tag_widget else None
            if tag_layout is None:
                continue
            for j in range(tag_layout.count()):
                widget_item = tag_layout.itemAt(j)
                widget = widget_item.widget() if widget_item else None
                if isinstance(widget, QPushButton) and widget.text() == "X":
                    remove_button = widget
                    break
            if remove_button is not None:
                break

        assert remove_button is not None
        cast(Any, QTest).mouseClick(remove_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert self.window.persistent_filters == []
        with open(self._saved_filters_path, encoding="utf-8") as handle:
            assert json.load(handle)["filters"] == []
        assert self.window.search_input.text() == ""
        assert "Nenhum filtro ativo" in str(
            self.window.filters_summary_label.text() or ""
        )
        assert self.window._get_visual_filter_columns() == set()
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == set(
            self.base_df["numero_ssa"].tolist()
        )
        assert self.window._last_filter_state is not None

        cast(Any, QTest).mouseClick(
            self.window.undo_filter_btn,
            Qt.MouseButton.LeftButton,
        )
        QApplication.processEvents()

        assert self.window.search_input.text().strip() == "Teste C"
        assert self.window.df_exibido["numero_ssa"].tolist() == [3]
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "Busca: 'Teste C'" in summary_buttons
        assert self.window._get_visual_filter_columns() == set()

    def test_advanced_filter_checks_survive_tab_switch(self):
        """Rebuild dos menus avançados deve persistir listas *_checks no tab_context."""
        self.window._adv_options_dirty = True
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()
        assert len(getattr(self.window, "adv_executor_checks", []) or []) > 0

        self._set_filter_panel_tab("main")
        QApplication.processEvents()
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        assert len(getattr(self.window, "adv_executor_checks", []) or []) > 0

    def test_refresh_advanced_options_does_not_eager_load_responsavel(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._advanced_filters = {
            "solicitante": ["User1", "User2"],
            "solicitante_exclude_values": ["User5"],
        }
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = None
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.built_prefixes.clear()
        responsavel_state.dirty_prefixes = set(responsavel_state.all_prefixes)

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self.window._refresh_advanced_filter_options()
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert responsavel_state.status_flags() == (False, True)
        button = getattr(self.window, "adv_responsavel_solicitante_button", None)
        if button is None:
            button = getattr(self.window, "_adv_ctx", {}).get(
                "adv_responsavel_solicitante_button"
            )
        assert button is not None
        assert "Incluir: User1, User2" in button.toolTip()
        assert "Diferente: User5" in button.toolTip()

    def test_responsavel_solicitante_alias_materializes_values_in_advanced_panel(self):
        alias_df = self.base_df.drop(columns=["solicitante"]).assign(
            responsavel_solicitante=["Alias1", "Alias2", "Alias3", "Alias4", "Alias5"]
        )
        self.window.df_completo = alias_df.copy()
        self.window.df_exibido = alias_df.copy()
        self.window._df_last_search_filtered = alias_df.copy()
        self.window.paginator.set_dataframe(alias_df.copy())
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        self.window._ensure_responsavel_options_materialized(
            target_prefix="adv_responsavel_solicitante"
        )
        QApplication.processEvents()

        values = [
            str(check.property("value") or "")
            for check in (
                getattr(self.window, "adv_responsavel_solicitante_checks", []) or []
            )
        ]
        assert "Alias1" in values
        assert "Alias5" in values

    def test_sort_responsavel_values_uses_full_dataset_for_area_prefix(self):
        full_df = pd.DataFrame(
            {
                "solicitante": ["Andre", "Andre", "Andre", "Andre"],
                "setor_executor": ["IEE1", "IEE1", "IEE1", "MEL4"],
                "setor_emissor": ["", "", "", ""],
            }
        )
        subset_df = full_df[full_df["setor_executor"] == "MEL4"].copy()

        decorated = self.window._sort_responsavel_values(
            subset_df,
            ["Andre"],
            "solicitante",
            df_source=full_df,
        )

        assert decorated == [("Andre", decorated[0][1])]
        assert "IEE1 - Andre" in decorated[0][1]
        assert "MEL4 - Andre" not in decorated[0][1]

    def test_responsavel_order_uses_sector_priority_before_alpha_name(self):
        decorated = filter_domain_rules.order_responsavel_values(
            ["Zulu", "Andre", "Bruno", "Carla", "Denise", "Edu", "Fabio", "Ana"],
            {
                "Zulu": {"MEL1": 1},
                "Andre": {"IEE1": 1},
                "Bruno": {"IEE3": 1},
                "Carla": {"MEL4": 1},
                "Denise": {"IEE2": 1},
                "Edu": {"IEE4": 1},
                "Fabio": {"MEL2": 1},
                "Ana": {"MEL3": 1},
            },
        )

        assert [label for _, label in decorated] == [
            "IEE3 - Bruno",
            "IEE1 - Andre",
            "IEE2 - Denise",
            "IEE4 - Edu",
            "MEL1 - Zulu",
            "MEL2 - Fabio",
            "MEL3 - Ana",
            "MEL4 - Carla",
        ]

    def test_macro_combo_real_click_opens_popup(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        combo = self.window.adv_macro_combo
        target = combo.lineEdit() or combo

        combo.hidePopup()
        combo.show()
        QApplication.processEvents()
        cast(Any, QTest).mouseClick(target, Qt.MouseButton.LeftButton)

        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not combo.view().isVisible():
            QApplication.processEvents()
            cast(Any, QTest).qWait(10)

        assert combo.view().isVisible()
        combo.hidePopup()

    def test_apply_advanced_filters_preserves_responsavel_when_not_materialized(self):
        self.window._advanced_filters = {
            "solicitante": ["User1"],
            "solicitante_exclude_values": ["User2"],
            "responsavel_programacao": ["ProgA"],
            "responsavel_programacao_exclude_values": ["ProgB"],
            "responsavel_execucao": ["ExecA"],
            "responsavel_execucao_exclude_values": ["ExecB"],
        }
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.built_prefixes.clear()
        responsavel_state.dirty_prefixes = set(responsavel_state.all_prefixes)

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

    @pytest.mark.parametrize(
        ("filter_key", "prefix", "value"),
        [
            ("solicitante", "adv_responsavel_solicitante", "Sol A"),
            (
                "responsavel_programacao",
                "adv_responsavel_programacao",
                "Prog A",
            ),
            ("responsavel_execucao", "adv_responsavel_execucao", "Exec A"),
        ],
    )
    def test_responsavel_multiselect_toggle_applies_filter_immediately(
        self,
        filter_key: str,
        prefix: str,
        value: str,
    ):
        self._load_responsavel_filter_contract_df()

        self._toggle_responsavel_filter_value(prefix=prefix, value=value)

        assert self.window._advanced_filters[filter_key] == [value]
        self._assert_filter_result_contract(
            filter_key=filter_key,
            expected_ssas={202600001, 202600003},
        )
        self._assert_multiselect_button_reflects_value(prefix=prefix, value=value)

    @pytest.mark.parametrize(
        ("filter_key", "prefix", "value", "expected_ssas"),
        [
            (
                "solicitante_exclude_values",
                "adv_responsavel_solicitante",
                "Sol B",
                {202600001, 202600003, 202600004},
            ),
            (
                "responsavel_programacao_exclude_values",
                "adv_responsavel_programacao",
                "Prog B",
                {202600001, 202600003, 202600004},
            ),
            (
                "responsavel_execucao_exclude_values",
                "adv_responsavel_execucao",
                "Exec B",
                {202600001, 202600003, 202600004},
            ),
        ],
    )
    def test_responsavel_multiselect_exclude_toggle_applies_filter_immediately(
        self,
        filter_key: str,
        prefix: str,
        value: str,
        expected_ssas: set[int],
    ):
        self._load_responsavel_filter_contract_df()

        self._toggle_responsavel_filter_value(
            prefix=prefix,
            value=value,
            exclude=True,
        )

        assert self.window._advanced_filters[filter_key] == [value]
        self._assert_filter_result_contract(
            filter_key=filter_key,
            expected_ssas=expected_ssas,
            expected_visual_column=filter_key.replace("_exclude_values", ""),
        )
        self._assert_multiselect_button_reflects_value(
            prefix=prefix,
            value=value,
            exclude=True,
        )

    def test_standard_advanced_status_toggle_still_applies_filter_via_debounce(self):
        self._load_responsavel_filter_contract_df()
        checks = getattr(self.window, "adv_status_checks", []) or []
        target = next(
            check
            for check in checks
            if str(check.property("value") or "") == "APV"
        )

        target.setChecked(True)
        QApplication.processEvents()
        self._wait_until_timer_inactive(self.window._advanced_apply_timer)

        assert self.window._advanced_filters["situacao"] == ["APV"]
        self._assert_filter_result_contract(
            filter_key="situacao",
            expected_ssas={202600001, 202600003},
        )
        self._assert_multiselect_button_reflects_value(
            prefix="adv_status",
            value="APV",
        )

    @pytest.mark.parametrize(
        ("filter_key", "prefix", "value", "expected_ssas", "expected_visual_column"),
        [
            (
                "setor_executor",
                "adv_executor",
                "IEE3",
                {202600001, 202600002},
                "setor_executor",
            ),
            (
                "setor_emissor",
                "adv_emissor",
                "ABC",
                {202600001, 202600003},
                "setor_emissor",
            ),
            ("situacao", "adv_status", "APV", {202600001, 202600003}, "situacao"),
            (
                "prioridade_emissao_values",
                "adv_prioridade_emissao",
                "1",
                {202600001, 202600003},
                "grau_prioridade_emissao",
            ),
            (
                "prioridade_planejamento_values",
                "adv_prioridade_planejamento",
                "2",
                {202600001, 202600002},
                "grau_prioridade_planejamento",
            ),
        ],
    )
    def test_standard_advanced_multiselect_include_toggle_applies_filter(
        self,
        filter_key: str,
        prefix: str,
        value: str,
        expected_ssas: set[int],
        expected_visual_column: str,
    ):
        self._load_responsavel_filter_contract_df()

        self._toggle_advanced_multiselect_value(prefix=prefix, value=value)

        assert self.window._advanced_filters[filter_key] == [value]
        self._assert_filter_result_contract(
            filter_key=filter_key,
            expected_ssas=expected_ssas,
            expected_visual_column=expected_visual_column,
        )
        self._assert_multiselect_button_reflects_value(prefix=prefix, value=value)

    @pytest.mark.parametrize(
        ("filter_key", "prefix", "value", "expected_ssas", "expected_visual_column"),
        [
            (
                "setor_executor_exclude_values",
                "adv_executor",
                "MEL4",
                {202600001, 202600002},
                "setor_executor",
            ),
            (
                "setor_emissor_exclude_values",
                "adv_emissor",
                "XYZ",
                {202600001, 202600003, 202600004},
                "setor_emissor",
            ),
            (
                "situacao_exclude_values",
                "adv_status",
                "SCA",
                {202600001, 202600002, 202600003},
                "situacao",
            ),
            (
                "prioridade_emissao_exclude_values",
                "adv_prioridade_emissao",
                "3",
                {202600001, 202600002, 202600003},
                "grau_prioridade_emissao",
            ),
            (
                "prioridade_planejamento_exclude_values",
                "adv_prioridade_planejamento",
                "1",
                {202600001, 202600002, 202600003},
                "grau_prioridade_planejamento",
            ),
        ],
    )
    def test_standard_advanced_multiselect_exclude_toggle_applies_filter(
        self,
        filter_key: str,
        prefix: str,
        value: str,
        expected_ssas: set[int],
        expected_visual_column: str,
    ):
        self._load_responsavel_filter_contract_df()

        self._toggle_advanced_multiselect_value(
            prefix=prefix,
            value=value,
            exclude=True,
        )

        assert self.window._advanced_filters[filter_key] == [value]
        self._assert_filter_result_contract(
            filter_key=filter_key,
            expected_ssas=expected_ssas,
            expected_visual_column=expected_visual_column,
        )
        self._assert_multiselect_button_reflects_value(
            prefix=prefix,
            value=value,
            exclude=True,
        )

    def test_reprogramacoes_multiselect_toggle_applies_filter(self):
        self._load_responsavel_filter_contract_df()
        if "num_reprogramacoes" not in self.window.visible_columns:
            self.window.visible_columns.append("num_reprogramacoes")

        self._toggle_advanced_multiselect_value(prefix="adv_reprog", value="2")
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window._advanced_filters["num_reprogramacoes_values"] == ["2"]
        assert self.window._advanced_filters["num_reprogramacoes_mode"] == "eq"
        self._assert_filter_result_contract(
            filter_key="num_reprogramacoes_values",
            expected_ssas={202600003, 202600004},
            expected_visual_column="num_reprogramacoes",
        )
        self._assert_multiselect_button_reflects_value(
            prefix="adv_reprog",
            value="2",
        )
        header_index = self.window._current_display_columns.index("num_reprogramacoes")
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text.startswith("[f] ")
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
            if not button.isHidden()
        ]
        assert any("Reprog" in text and "2" in text for text in summary_buttons)

    def test_advanced_filter_visual_map_covers_widget_multiselect_keys(self):
        expected_keys = {"num_reprogramacoes_values"}
        for spec in (
            ADVANCED_STANDARD_MULTISELECT_SPECS
            + ADVANCED_RESPONSAVEL_MULTISELECT_SPECS
        ):
            expected_keys.add(spec.include_key)
            if spec.exclude_key is not None:
                expected_keys.add(spec.exclude_key)
        for spec in ADVANCED_YEAR_MULTISELECT_SPECS:
            expected_keys.add(f"{spec.base_key}_values")
            expected_keys.add(f"{spec.base_key}_exclude_values")

        visual_keys = set(filter_domain_rules.ADVANCED_FILTER_VISUAL_COLUMN_MAP)

        assert expected_keys - visual_keys == set()

    def test_advanced_multiselect_clear_syncs_buttons_status_summary_and_header(self):
        self._load_responsavel_filter_contract_df()
        if "responsavel_execucao" not in self.window.visible_columns:
            self.window.visible_columns.append("responsavel_execucao")
        self._toggle_responsavel_filter_value(
            prefix="adv_responsavel_execucao",
            value="Exec A",
        )
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window._advanced_filters["responsavel_execucao"] == ["Exec A"]
        self._assert_filter_result_contract(
            filter_key="responsavel_execucao",
            expected_ssas={202600001, 202600003},
        )
        self._assert_multiselect_button_reflects_value(
            prefix="adv_responsavel_execucao",
            value="Exec A",
        )
        header_index = self.window._current_display_columns.index(
            "responsavel_execucao"
        )
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert header_text.startswith("[f] ")
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
            if not button.isHidden()
        ]
        assert any("Exec A" in text for text in summary_buttons)

        self.window._clear_advanced_filters()
        QApplication.processEvents()
        self.window.display_current_page(1)
        QApplication.processEvents()

        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert set(self.window.df_exibido["numero_ssa"].astype(int).tolist()) == {
            202600001,
            202600002,
            202600003,
            202600004,
        }
        assert "Selecionar" in str(
            self.window.adv_responsavel_execucao_button.toolTip() or ""
        )
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
            if not button.isHidden()
        ]
        assert not any("Exec A" in text for text in summary_buttons)
        header_text = str(
            self.window.table_widget.horizontalHeaderItem(header_index).text() or ""
        )
        assert not header_text.startswith("[f] ")

    def test_quick_executor_and_advanced_executor_remain_bidirectionally_synced(self):
        self._load_responsavel_filter_contract_df()
        self.window._refresh_quick_setor_executor_options()
        combo = getattr(self.window, "quick_setor_executor_combo", None)
        assert combo is not None
        mel4_idx = combo.findData("MEL4")
        assert mel4_idx >= 0

        combo.setCurrentIndex(mel4_idx)
        QApplication.processEvents()

        assert self.window._active_column_filters.get("setor_executor") == "MEL4"
        assert self.window._advanced_filters.get("setor_executor") == ["MEL4"]
        self._assert_filter_result_contract(
            filter_key="setor_executor",
            expected_ssas={202600003, 202600004},
        )
        self._assert_multiselect_button_reflects_value(
            prefix="adv_executor",
            value="MEL4",
        )

        self._toggle_advanced_multiselect_value(
            prefix="adv_executor",
            value="IEE3",
        )

        assert self.window._advanced_filters.get("setor_executor") == [
            "IEE3",
            "MEL4",
        ]
        assert self.window._active_column_filters.get("setor_executor") == (
            "IEE3, MEL4"
        )
        self._assert_filter_result_contract(
            filter_key="setor_executor",
            expected_ssas={202600001, 202600002, 202600003, 202600004},
        )
        assert str(combo.currentText() or "") == "Todos"

    def test_advanced_exclude_is_menu_only_without_field_checkbox(self):
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        exclude = getattr(self.window, "adv_status_exclude", None)

        assert exclude is None
        status_button = getattr(self.window, "adv_status_button", None)
        assert status_button is not None
        parent = status_button.parentWidget()
        assert isinstance(parent, QGroupBox)
        assert parent.title() == "Situacao"
        assert not [
            child
            for child in parent.findChildren(QCheckBox)
            if str(child.text() or "") == "Diferente"
        ]
        exclude_checks = getattr(self.window, "adv_status_exclude_checks", None)
        assert exclude_checks
        assert any(isinstance(check, QCheckBox) for check in exclude_checks)
        assert getattr(self.window, "adv_year_emissao_exclude", None) is None

    def test_advanced_selection_applies_after_configured_debounce(self):
        self.window._debounce_timer.setInterval(120)
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        status_checks = getattr(self.window, "adv_status_checks", [])
        target_check = next(check for check in status_checks if check.property("value"))
        target_value = str(target_check.property("value") or "")
        target_check.setChecked(True)
        QApplication.processEvents()

        timer = getattr(self.window, "_advanced_apply_timer", None)
        assert timer is not None
        assert timer.interval() == self.window._debounce_timer.interval()
        assert timer.isActive() is True

        self._wait_until_timer_inactive(timer)

        assert self.window._advanced_filters.get("situacao") == [target_value]
        assert self.window._advanced_filters_active is True

    def test_include_only_advanced_menus_do_not_render_exclude_column(self):
        def menu_labels(menu):
            labels = []
            for action in menu.actions():
                widget = action.defaultWidget()
                if widget is None:
                    continue
                labels.extend(label.text() for label in widget.findChildren(QLabel))
            return labels

        advanced_ui._refresh_reprogramacoes_menu(self.window, ["0", "1"], {}, None)
        advanced_ui._refresh_derivadas_menu(self.window, {}, None)

        self.window.adv_reprog_checks[0].setChecked(True)
        self.window.adv_derivada_checks[0].setChecked(True)

        assert "Nao conter" not in menu_labels(self.window.adv_reprog_menu)
        assert "Nao conter" not in menu_labels(self.window.adv_derivada_menu)
        assert "Diferente" not in self.window.adv_reprog_button.toolTip()
        assert "Diferente" not in self.window.adv_derivada_button.toolTip()

    def test_ensure_responsavel_options_materialized_runs_once_when_dirty(self):
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.built_prefixes.clear()
        responsavel_state.dirty_prefixes = set(responsavel_state.all_prefixes)

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self.window._ensure_responsavel_options_materialized()
            self.window._ensure_responsavel_options_materialized()

        assert refresh_mock.call_count == 1
        assert responsavel_state.status_flags() == (True, False)

    def test_responsavel_state_marks_built_prefix_stale_after_sector_change(self):
        responsavel_state = self.window.responsavel_materialization_state
        target_prefix = "adv_responsavel_solicitante"

        responsavel_state.mark_materialized({target_prefix})
        responsavel_state.mark_dirty({target_prefix})

        assert responsavel_state.stale_built_prefixes() == {target_prefix}

    def test_switch_to_filters_tab_does_not_materialize_responsavel_eagerly(self):
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = None
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.built_prefixes.clear()
        responsavel_state.dirty_prefixes = set(responsavel_state.all_prefixes)

        with patch.object(
            self.window,
            "_refresh_responsavel_options",
            wraps=self.window._refresh_responsavel_options,
        ) as refresh_mock:
            self._set_filter_panel_tab("filters")
            QApplication.processEvents()

        assert refresh_mock.call_count == 0
        assert responsavel_state.status_flags() == (False, True)

    def test_switch_to_filters_tab_coalesces_advanced_refresh_triggers(self):
        self.window._adv_options_dirty = True
        self.window._adv_values_cache = None
        self.window._pending_theme_refresh_column_filters = (
            getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        )
        self._panel_context()["_theme_name"] = None
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        with patch.object(
            self.window,
            "_refresh_advanced_filter_options",
            wraps=self.window._refresh_advanced_filter_options,
        ) as refresh_mock:
            self._set_filter_panel_tab("filters")
            deadline = time.time() + 2.0
            while time.time() < deadline and refresh_mock.call_count < 1:
                QApplication.processEvents()
                time.sleep(0.01)

        assert refresh_mock.call_count == 1
        assert self.window._adv_options_dirty is False

    def test_theme_refresh_does_not_schedule_advanced_options_rebuild(self):
        self.window._active_filter_panel_kind = "advanced"
        self.window._adv_options_dirty = False
        self.window._pending_theme_refresh_column_filters = ["pending"]

        with patch.object(
            self.window,
            "_schedule_adv_options_refresh",
            side_effect=AssertionError(
                "troca de tema nao deve reconstruir opcoes avancadas"
            ),
        ):
            self.window.refresh_filter_widgets_after_theme(
                getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
            )

        assert self.window._adv_options_dirty is False
        assert self.window._pending_theme_refresh_column_filters is None

    def test_bind_filters_tab_skips_series_lookup_when_render_key_is_unchanged(self):
        ctx = self._panel_context()
        current_page = max(1, self.window.paginator.current_page)
        ctx["_last_render_key"] = (
            id(self.window.df_exibido),
            current_page,
            tuple(self.window.visible_columns),
        )
        self.window._details_current_ssa = str(
            self.window.df_exibido.iloc[0]["numero_ssa"]
        )

        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=AssertionError(
                "_get_series_for_ssa nao deveria rodar sem rerender"
            ),
        ):
            self._set_filter_panel_tab("filters")
            QApplication.processEvents()

        assert ctx["_last_render_key"] == (
            id(self.window.df_exibido),
            current_page,
            tuple(self.window.visible_columns),
        )

    def test_switch_to_filters_tab_does_not_reapply_same_theme(self):
        with patch.object(
            self.window, "apply_theme", wraps=self.window.apply_theme
        ) as apply_mock:
            self._set_filter_panel_tab("filters")
            QApplication.processEvents()
            # Switch away and back: after the first bind, the same theme should not be re-applied.
            self._set_filter_panel_tab("main")
            QApplication.processEvents()
            self._set_filter_panel_tab("filters")
            QApplication.processEvents()

        assert apply_mock.call_count == 0

    def test_filters_tab_switch_and_responsavel_materialization_smoke_latency(self):
        heavy_df = self._build_heavy_filters_df(rows=1200)
        self.window._active_data_load_request_id = 33
        self.window.on_data_loaded(heavy_df, request_id=33)
        QApplication.processEvents()
        t0 = time.perf_counter()
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        switch_ms = (time.perf_counter() - t0) * 1000.0

        responsavel_state = self.window.responsavel_materialization_state
        assert responsavel_state.status_flags()[0] is False
        assert switch_ms < 3000.0

        target_prefix = "adv_responsavel_solicitante"
        t1 = time.perf_counter()
        self.window._ensure_responsavel_options_materialized(
            target_prefix=target_prefix
        )
        QApplication.processEvents()
        materialize_ms = (time.perf_counter() - t1) * 1000.0

        assert target_prefix in responsavel_state.built_prefixes
        assert responsavel_state.status_flags() == (False, True)
        assert materialize_ms < 5000.0

    def test_theme_cycle_smoke_latency_on_filters_tab(self):
        self._set_filter_panel_tab("filters")
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

    def test_apply_theme_styles_details_text_with_theme_roles_on_light_theme(self):
        self.window.apply_theme("mint-light")
        QApplication.processEvents()

        roles = dict(getattr(self.window, "_current_theme_roles", {}) or {})
        style = str(self.window.details_text.styleSheet() or "")
        document = self.window.details_text.document()

        assert roles["panel_text"] in style
        assert roles["panel_bg"] in style
        assert "padding:2px" in style
        assert document is not None
        assert document.documentMargin() == pytest.approx(2.0)

    def test_apply_theme_refreshes_derivadas_graph_box_colors(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202100046"],
                "descricao_ssa": ["Pai", "Filha"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        self.window.table_widget.selectRow(0)
        self.window.details_tab_bar.setCurrentIndex(1)

        self.window.apply_theme("mint-light")
        QApplication.processEvents()
        light_svg = str(self.window.details_graph_label._graph_svg_markup or "")

        self.window.apply_theme("dracula")
        QApplication.processEvents()
        dark_svg = str(self.window.details_graph_label._graph_svg_markup or "")

        light_fill = str(get_theme_roles("mint-light").get("input_bg") or "")
        dark_fill = str(get_theme_roles("dracula").get("input_bg") or "")
        assert light_fill
        assert dark_fill
        assert light_fill in light_svg
        assert dark_fill in dark_svg
        assert light_svg != dark_svg

    def test_apply_theme_preserves_derivadas_graph_when_selection_refresh_clears(
        self, monkeypatch
    ):
        series = pd.Series(
            {
                "numero_ssa": "202100046",
                "situacao": "APV",
                "derivada_de": "",
                "descricao_ssa": "Pai",
            }
        )
        self.window._details_current_series_for_derivadas = series
        self.window._details_current_derivadas_font_family = "monospace"
        refresh_seen: list[pd.Series | None] = []

        def _clear_transient_selection_state():
            self.window._details_current_series_for_derivadas = None
            self.window._details_current_derivadas_font_family = None
            self.window._pending_details_series = None

        def _capture_refresh(window):
            refresh_seen.append(
                getattr(window, "_details_current_series_for_derivadas", None)
            )

        monkeypatch.setattr(
            self.window,
            "update_details_from_selection",
            _clear_transient_selection_state,
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "refresh_derivadas_views_after_theme",
            _capture_refresh,
        )

        self.window.apply_theme("dracula")

        assert self.window._details_current_series_for_derivadas is series
        assert self.window._details_current_derivadas_font_family == "monospace"
        assert self.window._pending_details_series is series
        assert refresh_seen == [series]

    def test_apply_theme_logs_derivadas_refresh_failure(self, monkeypatch, caplog):
        def _raise_refresh(_window):
            raise RuntimeError("refresh failed")

        monkeypatch.setattr(
            ssa_gui_details,
            "refresh_derivadas_views_after_theme",
            _raise_refresh,
        )

        with caplog.at_level("WARNING"):
            self.window.apply_theme("dracula")

        assert "Failed to refresh derivadas graphs after apply_theme" in caplog.text
        assert "refresh failed" in caplog.text

    def test_apply_theme_styles_advanced_field_boxes_with_theme_roles(self):
        self._set_filter_panel_tab("filters")
        self.window.apply_theme("mint-light")
        QApplication.processEvents()

        roles = dict(getattr(self.window, "_current_theme_roles", {}) or {})
        state = self.window._advanced_filter_panel_state

        for key in ("prog_box", "exec_resp_box", "week_emis_box", "week_exec_box"):
            widget = state.grid_widgets[key]
            style = str(widget.styleSheet() or "")
            assert roles["panel_text"] in style
            assert roles["panel_bg"] in style
            assert roles["panel_border"] in style
            if sys.platform.startswith("win"):
                assert widget.title() == ""
                assert "QLabel#advancedFilterFieldTitleLabel" in style
                title_label = widget.findChild(QLabel, "advancedFilterFieldTitleLabel")
                assert title_label is not None
                assert title_label.text()

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
        main_tab_idx = 0
        current_theme = getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        other_theme = "windows7" if current_theme != "windows7" else "gruvbox"

        for i in range(5):
            self._set_filter_panel_tab("filters")
            QApplication.processEvents()
            if i % 2 == 0:
                self.window.apply_theme(other_theme)
            else:
                self.window.apply_theme(current_theme)
            QApplication.processEvents()
            self._set_filter_panel_tab("main")
            QApplication.processEvents()

        self.window.apply_theme(current_theme)
        QApplication.processEvents()
        assert getattr(self.window, "_current_theme", None) == current_theme
        assert self.window.main_tabs.currentIndex() == main_tab_idx

    def test_theme_switch_reapplies_on_tab_bind_for_inactive_tab(self):
        """Theme updates must re-style both tabs, even when switched after the change."""
        filters_ctx = self._panel_context()
        main_ctx = self._panel_context()

        current_theme = getattr(self.window, "_current_theme", "gruvbox") or "gruvbox"
        other_theme = "windows7" if current_theme != "windows7" else "gruvbox"

        initial_main_css = main_ctx["search_input"].styleSheet() or ""
        initial_main_box_css = main_ctx["quick_search_box"].styleSheet() or ""
        assert initial_main_css
        assert initial_main_box_css
        initial_filters_css = filters_ctx["search_input"].styleSheet() or ""
        initial_filters_box_css = filters_ctx["quick_search_box"].styleSheet() or ""
        assert initial_filters_css == initial_main_css
        assert initial_filters_box_css == initial_main_box_css
        assert "QLineEdit:focus" in initial_main_css
        assert "border:0" in initial_main_css
        assert "border:1px solid" in initial_main_box_css

        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        assert (filters_ctx["search_input"].styleSheet() or "") == initial_main_css
        assert (filters_ctx["quick_search_box"].styleSheet() or "") == initial_main_box_css

        # Apply a different theme while on filters tab, then switch back to main.
        self.window.apply_theme(other_theme)
        QApplication.processEvents()
        updated_filters_css = filters_ctx["search_input"].styleSheet() or ""
        updated_filters_box_css = filters_ctx["quick_search_box"].styleSheet() or ""
        assert updated_filters_css
        assert updated_filters_box_css
        assert updated_filters_css != initial_main_css
        assert updated_filters_box_css != initial_main_box_css
        assert "QLineEdit:focus" in updated_filters_css
        assert "border:0" in updated_filters_css
        assert "border:1px solid" in updated_filters_box_css
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        # Both tab search boxes must be themed together, not only after binding.
        assert getattr(self.window, "_current_theme", None) == other_theme
        assert (main_ctx["search_input"].styleSheet() or "") == updated_filters_css
        assert (main_ctx["quick_search_box"].styleSheet() or "") == updated_filters_box_css

    def test_switch_to_advanced_filter_panel_keeps_pending_search_live(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()
        assert Counter(self._extract_visible_ssa()) == Counter([1])

        # Switching the local filter panel is visual only; the single live search
        # debounce must still complete against the current search text.
        self.window.search_input.setText("Teste A, Teste D")
        self._set_filter_panel_tab("filters")
        cast(Any, QTest).qWait(int(self.window._debounce_timer.interval()) + 80)
        QApplication.processEvents()

        assert getattr(self.window, "_active_filter_panel_kind") == "advanced"
        assert Counter(self._extract_visible_ssa()) == Counter()
        assert self.window.search_input.text().strip() == "Teste A, Teste D"

    def test_general_search_debounce_uses_configured_interval_without_legacy_floor(self):
        expected = gui_ssa.ssa_system_controller.resolve_search_debounce_ms(
            gui_ssa.GUI_MAIN_PREFERENCES.get("gui_settings", {}),
            logger=gui_ssa.logger,
        )

        assert int(self.window._debounce_timer.interval()) == expected
        assert expected < 1400

    def test_clear_filter_on_filters_tab_clears_search_in_all_tabs(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        main_ctx = self._panel_context()
        assert main_ctx["search_input"].text().strip() == "Teste A"
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window.clear_filter()
        QApplication.processEvents()

        for ctx in self._iter_panel_contexts():
            assert ctx["search_input"].text().strip() == ""
        assert self.window.clear_filter_button.isEnabled() is False

    def test_filters_summary_shows_global_filters_on_both_tabs(self):
        self.window.search_input.setText("Teste A")
        self.window.initiate_filtering()
        QApplication.processEvents()

        self.window._active_column_filters["descricao_ssa"] = "Teste"
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        main_summary = str(self.window.filters_summary_label.toolTip() or "")
        main_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "Busca: 'Teste A'" in main_summary
        assert "Desc: Teste" in main_summary
        assert "Busca: 'Teste A'" in main_buttons
        assert "Desc: Teste" in main_buttons
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        filters_summary = str(self.window.filters_summary_label.toolTip() or "")
        filters_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "Busca: 'Teste A'" in filters_summary
        assert "Desc: Teste" in filters_summary
        assert "Busca: 'Teste A'" in filters_buttons
        assert "Desc: Teste" in filters_buttons

    def test_on_filter_finished_uses_pending_search_display_for_status(self):
        self.window._active_filter_request_id = 31
        self.window._active_filter_search_request_id = 31
        self.window._active_filter_search_display = "Teste A"
        self.window.search_input.setText("")
        filtered = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(filtered)
        QApplication.processEvents()

        assert "para 'Teste A'" in self.window.status_label.text()

    def test_on_filter_finished_preserves_manual_details_when_ssa_remains_visible(self):
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(3)
        QApplication.processEvents()

        assert self.window._details_current_ssa == 4

        self.window._active_filter_request_id = 41
        self.window._active_filter_search_request_id = 41
        self.window._active_filter_search_display = "APV/AMP"
        filtered = self.base_df[self.base_df["situacao"].isin(["APV", "AMP"])].copy()

        self.window.on_filter_finished(filtered, request_id=41)
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == [5, 4, 1]
        assert self.window._details_current_ssa == 4
        assert "Teste D" in str(self.window.details_text.toHtml() or "")
        assert self.window.table_widget.selectionModel().selectedRows() == []

    def test_on_filter_finished_updates_details_when_manual_selection_leaves_result(
        self,
    ):
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(3)
        QApplication.processEvents()

        assert self.window._details_current_ssa == 4

        self.window._active_filter_request_id = 42
        self.window._active_filter_search_request_id = 42
        self.window._active_filter_search_display = "Teste A"
        filtered = self.base_df[self.base_df["descricao_ssa"].eq("Teste A")].copy()

        self.window.on_filter_finished(filtered, request_id=42)
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == [1]
        assert self.window._details_current_ssa == 1
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Teste A" in details_html
        assert "Teste D" not in details_html
        assert self.window.table_widget.selectionModel().selectedRows() == []

    def test_on_filter_finished_pending_jump_overrides_previous_manual_selection(
        self, monkeypatch
    ):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])
        target_desc = str(df.iloc[target_pos]["descricao_ssa"])

        self.window.df_completo = df.copy()
        self.window.df_exibido = df.iloc[:50].copy().reset_index(drop=True)
        self.window._df_last_search_filtered = self.window.df_exibido.copy()
        self.window.paginator.page_size = 50
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()

        scheduled = {}

        def fake_single_shot(delay, callback):
            scheduled["delay"] = delay
            scheduled["callback"] = callback

        monkeypatch.setattr(ssa_gui_details.QTimer, "singleShot", fake_single_shot)

        self.window._active_filter_request_id = 55
        self.window._active_filter_search_request_id = 55
        self.window._active_filter_search_display = f"={target_ssa}"
        self.window._pending_jump_to_ssa = {
            "numero_ssa": target_ssa,
            "request_id": 55,
        }

        self.window.on_filter_finished(df.copy(), request_id=55)
        QApplication.processEvents()

        assert getattr(self.window, "_pending_jump_to_ssa", None) is None
        assert str(self.window._details_current_ssa) == target_ssa
        assert target_desc in str(self.window.details_text.toHtml() or "")
        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert scheduled["delay"] == 0

        scheduled["callback"]()
        QApplication.processEvents()

        selected_rows = self.window.table_widget.selectionModel().selectedRows()
        assert len(selected_rows) == 1
        selected_series = self.window._get_series_from_row(selected_rows[0].row())
        assert str(selected_series.get("numero_ssa")) == target_ssa
        assert str(self.window._details_current_ssa) == target_ssa

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
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        captured_widths = []
        with patch.object(
            self.window,
            "_reorganize_advanced_filters_grid",
            side_effect=captured_widths.append,
        ):
            event = QResizeEvent(QSize(1280, 800), QSize(1200, 760))
            self.window.resizeEvent(event)
            debounce_ms = int(
                getattr(self.window._resize_recompute_timer, "interval", lambda: 300)()
            )
            cast(Any, QTest).qWait(debounce_ms + 80)

        assert captured_widths
        assert captured_widths[0] >= 0

    def test_resize_event_coalesces_width_recompute_with_restartable_timer(self):
        self.window._last_window_width = 900
        self.window._data_revision = 17
        self.window.df_exibido = self.base_df.copy()
        self.window.df_para_tabela = self.base_df.copy()
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

    def test_details_html_breaks_data_arquivo_origem_label_in_two_lines(self):
        series = self.base_df.iloc[0].copy()
        series["data_arquivo_origem"] = "2026-03-02"

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=False
        )

        assert "Data do Arquivo<br/>de Origem:" in html

    def test_details_html_groups_origin_metadata_at_end(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["descricao_ssa"] = "Texto principal"
        series["sistema_origem"] = "SAM API"
        series["data_arquivo_origem"] = "2026-03-02 13:45:00"
        series["data_planilha"] = "2026-03-02T13:45:00"
        series["arquivo_origem"] = "sam_api_20260302_134500.xlsx"

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=False
        )

        system_pos = html.index("Sistema de Origem:")
        file_date_pos = html.index("Data do Arquivo<br/>de Origem:")
        sheet_date_pos = html.index("Data da Planilha:")
        sheet_file_pos = html.index("Planilha de Origem:")
        assert system_pos < file_date_pos < sheet_date_pos < sheet_file_pos
        assert html.index("Descricao da SSA:") < system_pos

    def test_details_html_right_aligns_values_and_preserves_full_text(self):
        long_text = (
            "Texto completo da SSA com conteudo suficiente para ocupar a caixa "
            "sem inserir reticencias artificiais ou cortar o valor renderizado."
        )
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["descricao_ssa"] = long_text

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=False
        )

        assert "text-align: right;" in html
        assert long_text in html
        assert "reticencias artificiais..." not in html

    def test_details_text_disables_automatic_link_navigation(self):
        details_text = self.window.details_text
        assert details_text.openExternalLinks() is False
        assert details_text.openLinks() is False

    def test_details_html_renders_related_ssa_links(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["numero_ssa_relacionada_1"] = "202500777"
        series["numero_ssa_relacionada_2"] = "202500888"
        series["situacao_relacionada_1"] = "STE"
        series["situacao_relacionada_2"] = "APG"
        series["relacao"] = "RELACIONADA"

        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=lambda _window, numero: object()
            if str(numero) in {"202500777", "202500888"}
            else None,
        ):
            html = self.window._format_details_html(
                series,
                highlight_search_terms=False,
                linkify=True,
            )

        assert "SSAs relacionadas (2)" in html
        assert 'href="ssa:202500777"' in html
        assert 'href="ssa:202500888"' in html

    def test_details_html_tolerates_pd_na_in_related_relation_fields(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["numero_ssa_relacionada_1"] = "202500777"
        series["numero_ssa_relacionada_2"] = pd.NA
        series["situacao_relacionada_1"] = pd.NA
        series["situacao_relacionada_2"] = pd.NA
        series["relacao"] = pd.NA

        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=lambda _window, numero: object()
            if str(numero) == "202500777"
            else None,
        ):
            html = self.window._format_details_html(
                series,
                highlight_search_terms=False,
                linkify=True,
            )

        assert "SSAs relacionadas (1)" in html
        assert 'href="ssa:202500777"' in html
        assert ssa_gui_details._normalize_ssa_relation_value(pd.NA) == ""

    def test_update_details_from_series_uses_ssa_index_for_related_links(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["numero_ssa_relacionada_1"] = "202500777"
        series["situacao_relacionada_1"] = "STE"
        series["numero_ssa_relacionada_2"] = "202500888"
        series["situacao_relacionada_2"] = "SES"

        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=lambda _window, numero: object()
            if str(numero) in {"202500777", "202500888"}
            else None,
        ):
            ssa_gui_details._update_details_from_series(self.window, series)

        html = self.window.details_text.toHtml()
        assert "copy-ssa:202600023" in html
        assert "202500777" in html
        assert "202500888" in html

    def test_advanced_emissor_include_status_exclude_and_single_undo_contract(self):
        scenario_df = pd.DataFrame(
            {
                "numero_ssa": [
                    "202600001",
                    "202600002",
                    "202600003",
                    "202600004",
                    "202600005",
                    "202600006",
                ],
                "situacao": ["APV", "STE", "STE", "APV", "SCA", "APV"],
                "derivada_de": ["", "", "", "", "", ""],
                "localizacao_codigo": ["LOC1", "LOC2", "LOC3", "LOC4", "LOC5", "LOC6"],
                "descricao_localizacao": ["Desc"] * 6,
                "equipamento": ["EQ"] * 6,
                "semana_cadastro": [202501] * 6,
                "semana_programada": [202503] * 6,
                "data_cadastro": ["2025-01-01"] * 6,
                "descricao_ssa": ["A", "B", "C", "D", "E", "F"],
                "setor_executor": ["MEL4"] * 6,
                "setor_emissor": ["IEE1", "IEE1", "IEE2", "IEE2", "IEE3", "MEL4"],
                "descricao_execucao": ["Exec"] * 6,
                "solicitante": ["User"] * 6,
            }
        )
        self.window.df_completo = scenario_df.copy()
        self.window.df_exibido = scenario_df.copy()
        self.window._df_last_search_filtered = scenario_df.copy()
        self.window.paginator.set_dataframe(scenario_df.copy())
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        def check_values(checks, values):
            expected = set(values)
            found = set()
            for checkbox in checks or []:
                value = str(checkbox.property("value") or "")
                if value in expected:
                    checkbox.setChecked(True)
                    found.add(value)
            assert found == expected

        check_values(getattr(self.window, "adv_emissor_checks", []), ["IEE1", "IEE2"])
        self.window._apply_advanced_filters_from_ui()
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == [
            "202600004",
            "202600003",
            "202600002",
            "202600001",
        ]
        assert self.window._advanced_filters.get("setor_emissor") == ["IEE1", "IEE2"]

        check_values(getattr(self.window, "adv_status_exclude_checks", []), ["STE"])
        self.window._apply_advanced_filters_from_ui()
        QApplication.processEvents()

        assert self.window._advanced_filters.get("situacao_exclude_values") == ["STE"]
        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == [
            "202600004",
            "202600001",
        ]

        self.window._restore_last_filter_state()
        QApplication.processEvents()

        assert self.window._advanced_filters.get("setor_emissor") == ["IEE1", "IEE2"]
        assert not self.window._advanced_filters.get("situacao_exclude_values")
        assert self.window.df_exibido["numero_ssa"].astype(str).tolist() == [
            "202600004",
            "202600003",
            "202600002",
            "202600001",
        ]
        assert self.window.undo_filter_btn.isEnabled() is False

    def test_update_details_from_series_resolves_related_ssas_without_full_index_build(
        self,
    ):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["numero_ssa_relacionada_1"] = "202500777"
        series["situacao_relacionada_1"] = "STE"
        series["numero_ssa_relacionada_2"] = "202500888"
        series["situacao_relacionada_2"] = "SES"
        series_map = series.to_dict()

        self.window.df_exibido = pd.DataFrame([series]).copy()
        self.window.df_completo = pd.DataFrame(
            [
                series_map,
                {**series_map, "numero_ssa": "202500777", "situacao": "STE"},
                {**series_map, "numero_ssa": "202500888", "situacao": "SES"},
            ]
        ).copy()

        with patch(
            "gui.ssa.gui_details._get_df_ssa_series_index",
            side_effect=AssertionError("nao deveria montar indice completo"),
        ), patch(
            "gui.ssa.gui_details._get_window_ssa_series_index",
            side_effect=AssertionError("nao deveria montar indice global"),
        ), patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=AssertionError("nao deveria escanear SSA relacionada"),
        ):
            ssa_gui_details._update_details_from_series(self.window, series)

        html = self.window.details_text.toHtml()
        assert "202500777" in html
        assert "202500888" in html

    def test_details_html_expands_situacao_and_links_numero_ssa_for_copy(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa"] = "202600023"
        series["situacao"] = "APG"

        html = self.window._format_details_html(
            series, highlight_search_terms=False, linkify=True
        )

        assert "APG - Aguardando Programacao" in html
        assert "copy-ssa:202600023" in html

    def test_derivadas_tree_html_includes_status_codes(self, monkeypatch):
        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda *_args, **_kwargs: {
                "target": "202600023",
                "target_status": "APG",
                "parents": ["202516514"],
                "children": [{"ssa": "202600029", "situacao": "SPG"}],
                "descendants": [{"ssa": "202600030", "situacao": "STE"}],
                "ancestors": [
                    {"ssa": "202516514", "situacao": "STE", "min_distance": 1}
                ],
                "direct_children_count": 1,
                "descendants_count": 1,
            },
        )
        html = ssa_gui_details._build_derivadas_tree_html(self.window, "202600023")

        assert "202600023 (APG)" in html
        assert "202516514 (STE)" in html
        assert "202600029 (SPG)" in html

    def test_collect_derivadas_tree_data_child_includes_parent_and_siblings(
        self, monkeypatch
    ):
        family_df = pd.DataFrame(
            {
                "numero_ssa": ["202600100", "202600101", "202600102", "202600103"],
                "derivada_de": ["", "202600100", "202600100", "202600102"],
                "situacao": ["STE", "APG", "SPG", "STE"],
                "descricao_ssa": ["mae", "filha alvo", "irma", "sobrinha"],
            }
        )
        self.window.df_completo = family_df
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        data = ssa_gui_details._collect_derivadas_tree_data(self.window, "202600101")

        assert data["parents"] == ["202600100"]
        assert data["family_roots"] == ["202600100"]
        assert data["render_family"] is True
        assert any(
            row.get("ssa") == "202600101" and row.get("parent") == "202600100"
            for row in data["descendants"]
        )
        assert any(
            row.get("ssa") == "202600102" and row.get("parent") == "202600100"
            for row in data["descendants"]
        )
        assert any(
            row.get("ssa") == "202600103" and row.get("parent") == "202600102"
            for row in data["descendants"]
        )

    def test_collect_derivadas_tree_data_accepts_short_relation_ids(
        self, monkeypatch
    ):
        family_df = pd.DataFrame(
            {
                "numero_ssa": ["100", "101", "102", "103"],
                "derivada_de": ["", "100", "100", "102"],
                "situacao": ["STE", "APG", "SPG", "STE"],
                "descricao_ssa": ["mae", "filha alvo", "irma", "sobrinha"],
            }
        )
        self.window.df_completo = family_df
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        data = ssa_gui_details._collect_derivadas_tree_data(self.window, "101")

        assert data["parents"] == ["100"]
        assert data["family_roots"] == ["100"]
        assert data["render_family"] is True
        assert any(
            row.get("ssa") == "102" and row.get("parent") == "100"
            for row in data["descendants"]
        )

    def test_collect_derivadas_tree_data_rebuilds_family_cache_after_in_place_change(
        self, monkeypatch
    ):
        family_df = pd.DataFrame(
            {
                "numero_ssa": ["202600100", "202600101", "202600102"],
                "derivada_de": ["", "202600100", "202600100"],
                "situacao": ["STE", "APG", "SPG"],
            }
        )
        self.window.df_completo = family_df
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        first = ssa_gui_details._collect_derivadas_tree_data(self.window, "202600101")
        family_df.loc[2, "derivada_de"] = "202600101"
        second = ssa_gui_details._collect_derivadas_tree_data(self.window, "202600101")

        assert any(
            row.get("ssa") == "202600102" and row.get("parent") == "202600100"
            for row in first["descendants"]
        )
        assert any(
            row.get("ssa") == "202600102" and row.get("parent") == "202600101"
            for row in second["descendants"]
        )
        assert not any(
            row.get("ssa") == "202600102" and row.get("parent") == "202600100"
            for row in second["descendants"]
        )

    def test_collect_derivadas_tree_data_rebuilds_large_family_cache_without_token(
        self, monkeypatch
    ):
        rows = [("202600000", ""), ("202600001", "202600000")]
        rows.extend((f"2026{i:05d}", "202600000") for i in range(2, 80))
        family_df = pd.DataFrame(rows, columns=["numero_ssa", "derivada_de"])
        family_df["situacao"] = "APG"
        self.window.df_completo = family_df
        self.window._data_uuid = None
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        first = ssa_gui_details._collect_derivadas_tree_data(self.window, "202600001")
        family_df.loc[7, "derivada_de"] = "202600001"
        second = ssa_gui_details._collect_derivadas_tree_data(self.window, "202600001")
        changed_child = str(family_df.loc[7, "numero_ssa"])

        assert not any(
            row.get("ssa") == changed_child and row.get("parent") == "202600001"
            for row in first["descendants"]
        )
        assert any(
            row.get("ssa") == changed_child and row.get("parent") == "202600001"
            for row in second["descendants"]
        )

    def test_derivadas_family_edges_cache_invalidates_on_revision_change(self):
        family_df = pd.DataFrame(
            {
                "numero_ssa": ["202600100", "202600101", "202600102"],
                "derivada_de": ["", "202600100", "202600100"],
            }
        )
        self.window.df_completo = family_df
        self.window._data_uuid = "stable-token"
        self.window._data_revision = 1

        first_edges = ssa_gui_details._get_cached_derivadas_family_edges(self.window)
        family_df.loc[2, "derivada_de"] = "202600101"
        self.window._data_revision = 2
        second_edges = ssa_gui_details._get_cached_derivadas_family_edges(self.window)

        assert ("202600100", "202600102") in first_edges
        assert ("202600101", "202600102") in second_edges
        assert ("202600100", "202600102") not in second_edges

    def test_derivadas_family_edges_cache_uses_revision_without_uuid(self):
        family_df = pd.DataFrame(
            {
                "numero_ssa": ["202600100", "202600101", "202600102"],
                "derivada_de": ["", "202600100", "202600100"],
            }
        )
        self.window.df_completo = family_df
        self.window._data_uuid = None
        self.window._data_revision = 1

        first_edges = ssa_gui_details._get_cached_derivadas_family_edges(self.window)
        family_df.loc[2, "derivada_de"] = "202600101"
        self.window._data_revision = 2
        second_edges = ssa_gui_details._get_cached_derivadas_family_edges(self.window)

        assert ("202600100", "202600102") in first_edges
        assert ("202600101", "202600102") in second_edges
        assert ("202600100", "202600102") not in second_edges

    def test_derivadas_family_edges_drop_empty_and_duplicate_pairs(self):
        family_df = pd.DataFrame(
            {
                "numero_ssa": [
                    "202600100",
                    "202600101",
                    "202600101",
                    "",
                    "202600102",
                ],
                "derivada_de": [
                    "",
                    "202600100",
                    "202600100",
                    "202600100",
                    "",
                ],
            }
        )
        self.window.df_completo = family_df
        self.window._data_uuid = "stable-token"
        self.window._data_revision = 1

        edges = ssa_gui_details._get_cached_derivadas_family_edges(self.window)

        assert edges == [("202600100", "202600101")]

    def test_details_ssa_index_cache_invalidates_on_revision_change(self):
        details_df = pd.DataFrame(
            {
                "numero_ssa": ["202600101"],
                "situacao": ["APG"],
            }
        )
        self.window._data_uuid = "stable-token"
        self.window._data_revision = 1

        first_index = ssa_gui_details._get_df_ssa_series_index(self.window, details_df)
        details_df.loc[0, "numero_ssa"] = "202600102"
        self.window._data_revision = 2
        second_index = ssa_gui_details._get_df_ssa_series_index(self.window, details_df)

        assert "202600101" in first_index
        assert "202600102" in second_index
        assert "202600101" not in second_index

    def test_gui_smoke_clicks_search_tabs_and_derivadas_filter(self, monkeypatch):
        family_df = pd.DataFrame(
            {
                "numero_ssa": [
                    "202600100",
                    "202600101",
                    "202600102",
                    "202600103",
                ],
                "situacao": ["APG", "SPG", "APG", "STE"],
                "derivada_de": ["", "202600100", "202600100", "202600102"],
                "localizacao_codigo": ["L0", "L1", "L2", "L3"],
                "descricao_localizacao": ["Local"] * 4,
                "equipamento": ["EQ"] * 4,
                "semana_cadastro": [202601] * 4,
                "semana_programada": [202602] * 4,
                "data_cadastro": ["2026-01-01"] * 4,
                "descricao_ssa": ["Mae", "Alvo", "Irma", "Sobrinha"],
                "setor_executor": ["IEE3", "MEL4", "IEE3", "XYZ"],
                "setor_emissor": ["ABC", "IEE3", "MEL4", "MEL4"],
                "descricao_execucao": [
                    "Mae exec",
                    "Alvo exec",
                    "Irma exec",
                    "Sobrinha exec",
                ],
                "solicitante": ["User0", "User1", "User2", "User3"],
            }
        )
        self.window.df_completo = family_df.copy()
        self.window.df_exibido = family_df.copy()
        self.window.df_para_tabela = family_df.copy()
        self.window._df_last_search_filtered = family_df.copy()
        self.window.paginator.set_dataframe(family_df.copy())
        self.window.display_current_page(1)
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)
        QApplication.processEvents()

        main_ctx = self._panel_context()
        self._set_filter_panel_tab("main")
        main_ctx["search_input"].setText("202600101")
        cast(Any, QTest).mouseClick(
            main_ctx["search_button"],
            Qt.MouseButton.LeftButton,
        )
        QApplication.processEvents()

        assert self.window.df_exibido["numero_ssa"].tolist() == ["202600101"]

        assert self.window.main_tabs.count() == 1
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        self.window.df_exibido = family_df.copy()
        self.window._df_last_search_filtered = family_df.copy()
        self.window.paginator.set_dataframe(family_df.copy())
        self.window.display_current_page(1)
        self.window._filter_by_derivadas("202600100")
        QApplication.processEvents()

        assert set(self.window.df_exibido["numero_ssa"].tolist()) == {
            "202600101",
            "202600102",
        }

    def test_gui_smoke_opens_details_dialog_with_parent_sibling_family(
        self, monkeypatch
    ):
        family_df = pd.DataFrame(
            {
                "numero_ssa": [
                    "202600100",
                    "202600101",
                    "202600102",
                    "202600103",
                ],
                "situacao": ["APG", "SPG", "APG", "STE"],
                "derivada_de": ["", "202600100", "202600100", "202600102"],
                "localizacao_codigo": ["L0", "L1", "L2", "L3"],
                "descricao_localizacao": ["Local"] * 4,
                "equipamento": ["EQ"] * 4,
                "semana_cadastro": [202601] * 4,
                "semana_programada": [202602] * 4,
                "data_cadastro": ["2026-01-01"] * 4,
                "descricao_ssa": ["Mae", "Alvo", "Irma", "Sobrinha"],
                "setor_executor": ["IEE3", "MEL4", "IEE3", "XYZ"],
                "setor_emissor": ["ABC", "IEE3", "MEL4", "MEL4"],
                "descricao_execucao": [
                    "Mae exec",
                    "Alvo exec",
                    "Irma exec",
                    "Sobrinha exec",
                ],
                "solicitante": ["User0", "User1", "User2", "User3"],
            }
        )
        self.window.df_completo = family_df.copy()
        self.window.df_exibido = family_df.copy()
        self.window.df_para_tabela = family_df.copy()
        self.window._df_last_search_filtered = family_df.copy()
        self.window.paginator.set_dataframe(family_df.copy())
        self.window.display_current_page(1)
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)
        QApplication.processEvents()

        def _inspect_dialog():
            for widget in QApplication.topLevelWidgets():
                if not isinstance(widget, QtWidgets.QDialog):
                    continue
                if "Detalhes da SSA" not in str(widget.windowTitle()):
                    continue
                browsers = widget.findChildren(QtWidgets.QTextBrowser)
                joined = "\n".join(
                    str(browser.toPlainText() or "")
                    + "\n"
                    + str(browser.toHtml() or "")
                    for browser in browsers
                )
                dialog_result.update(
                    {
                        "found": True,
                        "has_mae": "202600100" in joined,
                        "has_alvo": "202600101" in joined,
                        "has_irma": "202600102" in joined,
                        "has_sobrinha": "202600103" in joined,
                    }
                )
                widget.accept()
                return True
            return False

        dialog_result = {"found": False}
        ssa_gui_details._open_details_dialog_for_ssa(self.window, "202600101")
        deadline = time.monotonic() + 3.0
        while not dialog_result["found"] and time.monotonic() < deadline:
            QApplication.processEvents()
            cast(Any, QTest).qWait(50)
            _inspect_dialog()

        assert dialog_result == {
            "found": True,
            "has_mae": True,
            "has_alvo": True,
            "has_irma": True,
            "has_sobrinha": True,
        }

    def test_derivadas_tree_large_family_uses_limited_payload(self, monkeypatch):
        rows = [("202600000", "", "APG")]
        rows.append(("202699999", "202600000", "SPG"))
        rows.extend((f"2026{i:05d}", "202600000", "APG") for i in range(1, 20000))
        family_df = pd.DataFrame(
            rows,
            columns=["numero_ssa", "derivada_de", "situacao"],
        )
        family_df["descricao_ssa"] = "SSA"
        self.window.df_completo = family_df
        self.window.df_exibido = family_df
        self.window.df_para_tabela = family_df
        self.window._df_last_search_filtered = family_df
        self.window._data_uuid = None
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        tree_data = ssa_gui_details._collect_derivadas_tree_data(
            self.window,
            "202699999",
        )
        ssa_index = ssa_gui_details._get_df_ssa_series_index(
            self.window,
            self.window.df_para_tabela,
        )
        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202699999",
            tree_data_override=tree_data,
            ssa_index=ssa_index,
        )

        assert tree_data["descendants_partial"] is True
        assert len(tree_data["descendants"]) <= ssa_gui_details.DERIVADAS_GRAPH_MAX_DESCENDANTS
        assert any(
            row.get("ssa") == "202699999" and row.get("parent") == "202600000"
            for row in tree_data["descendants"]
        )
        assert "... (+" in html

    def test_collect_derivadas_tree_data_large_family_preserves_target_edge(
        self, monkeypatch
    ):
        rows = [("202600000", ""), ("202699999", "202600000")]
        rows.extend((f"2026{i:05d}", "202600000") for i in range(1, 220))
        family_df = pd.DataFrame(rows, columns=["numero_ssa", "derivada_de"])
        family_df["situacao"] = "APG"
        self.window.df_completo = family_df
        self.window._data_uuid = None
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        data = ssa_gui_details._collect_derivadas_tree_data(self.window, "202699999")

        assert data["descendants_partial"] is True
        assert data["render_family"] is True
        assert any(
            row.get("ssa") == "202699999" and row.get("parent") == "202600000"
            for row in data["descendants"]
        )

    def test_derivadas_tree_html_renders_parent_sibling_family(self):
        data: dict[str, object] = {
            "target": "202600101",
            "parents": ["202600100"],
            "family_roots": ["202600100"],
            "children": [],
            "descendants": [
                {"ssa": "202600101", "parent": "202600100"},
                {"ssa": "202600102", "parent": "202600100"},
                {"ssa": "202600103", "parent": "202600102"},
            ],
            "ancestors": [{"ssa": "202600100", "min_distance": 1}],
            "direct_children_count": 0,
            "descendants_count": 3,
            "render_family": True,
        }

        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202600101",
            tree_data_override=data,
        )

        assert "202600100" in html
        assert "202600101" in html
        assert "202600102" in html
        assert "202600103" in html

    def test_derivadas_tree_html_marks_partial_family(self):
        data: dict[str, object] = {
            "target": "202600101",
            "parents": ["202600100"],
            "family_roots": ["202600100"],
            "children": [],
            "descendants": [
                {"ssa": "202600101", "parent": "202600100"},
            ],
            "ancestors": [{"ssa": "202600100", "min_distance": 1}],
            "direct_children_count": 0,
            "descendants_count": 1,
            "descendants_partial": True,
            "render_family": True,
        }

        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202600101",
            tree_data_override=data,
        )

        assert "... (+1)" in html

    def test_build_derivadas_mermaid_text_generates_edges(self):
        data: dict[str, object] = {
            "target": "202600023",
            "parents": ["202516514"],
            "children": ["202600029", "202600030"],
            "descendants": [
                {"ssa": "202600023", "parent": "202516514"},
                {"ssa": "202600031", "parent": "202600029"},
            ],
        }
        mermaid = ssa_gui_details._build_derivadas_mermaid_text(data)
        assert mermaid.startswith("flowchart LR")
        assert 'N202516514["202516514"] --> N202600023' in mermaid
        assert mermaid.count("N202516514") == 1
        assert 'N202600023 --> N202600029["202600029"]' in mermaid
        assert 'N202600029 --> N202600031["202600031"]' in mermaid

    def test_build_derivadas_mermaid_text_returns_empty_without_target(self):
        assert ssa_gui_details._build_derivadas_mermaid_text({}) == ""

    def test_build_derivadas_mermaid_text_uses_stable_non_numeric_node_id(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_details,
            "_normalize_ssa_relation_value",
            lambda value: str(value or "").strip(),
        )
        mermaid = ssa_gui_details._build_derivadas_mermaid_text(
            {"target": "ALVO", "children": ["FILHA"]}
        )
        target_id = re.search(r'(N_[a-f0-9]+)\["ALVO"\]', mermaid)
        child_id = re.search(r'(N_[a-f0-9]+)\["FILHA"\]', mermaid)

        assert target_id is not None
        assert child_id is not None
        assert target_id.group(1) != child_id.group(1)
        assert f"{target_id.group(1)} --> {child_id.group(1)}" in mermaid

    def test_build_derivadas_mermaid_text_avoids_digit_collision_for_text_ids(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            ssa_gui_details,
            "_normalize_ssa_relation_value",
            lambda value: str(value or "").strip(),
        )
        mermaid = ssa_gui_details._build_derivadas_mermaid_text(
            {"target": "SSA-2025", "children": ["REL-2025"]}
        )
        target_id = re.search(r'(N_[a-f0-9]+)\["SSA-2025"\]', mermaid)
        child_id = re.search(r'(N_[a-f0-9]+)\["REL-2025"\]', mermaid)

        assert target_id is not None
        assert child_id is not None
        assert target_id.group(1) != child_id.group(1)
        assert "N2025" not in mermaid

    def test_build_derivadas_graph_html_generates_svg(self):
        data: dict[str, object] = {
            "target": "202600023",
            "parents": ["202516514"],
            "children": ["202600029", "202600030"],
            "descendants": [{"ssa": "202600031", "parent": "202600029"}],
            "related": [{"ssa": "202500777", "situacao": "STE", "relacao": "REL"}],
            "descendants_count": 3,
        }
        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            data,
            link_color="#4a90e2",
            font_family="monospace",
        )
        assert "<svg" in html
        assert "202600023" in html
        assert "202500777" in html
        assert "stroke-dasharray" in html
        assert "marker-end" in html
        assert "Grafo de derivadas" in html
        assert 'fill="#69b7ff"' not in html
        assert 'data-ssa="202600023"' in html
        assert 'data-ssa="202500777"' in html

    @staticmethod
    def test_graph_navigation_hitboxes_scale_svg_nodes():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" '
            'viewBox="0 0 200 100">'
            '<rect data-ssa="202100186" x="50" y="20" width="80" height="30" />'
            "</svg>"
        )

        hitboxes = ssa_gui_details._graph_navigation_hitboxes_from_svg(
            svg,
            render_width=400,
            render_height=200,
        )

        assert hitboxes == [("202100186", 100.0, 40.0, 260.0, 100.0)]

    @staticmethod
    def test_graph_navigation_hitboxes_ignore_stroke_width_attribute():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="286" height="106" '
            'viewBox="0 0 286 106">'
            '<rect x="8" y="8" width="80" height="30" data-ssa="202100046" '
            'rx="5" ry="5" fill="#000" stroke="#fff" stroke-width="0.8" />'
            "</svg>"
        )

        hitboxes = ssa_gui_details._graph_navigation_hitboxes_from_svg(
            svg,
            render_width=400,
            render_height=148,
        )

        assert hitboxes == [
            (
                "202100046",
                pytest.approx(11.1888111888),
                pytest.approx(11.1698113208),
                pytest.approx(123.0769230769),
                pytest.approx(53.0566037736),
            )
        ]

    def test_derivadas_tree_html_handles_cycle_in_descendants(self):
        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202100135",
            tree_data_override={
                "target": "202100135",
                "parents": [],
                "children": ["202100186"],
                "descendants": [
                    {"ssa": "202100186", "parent": "202100135"},
                    {"ssa": "202100135", "parent": "202100186"},
                ],
                "related": [],
                "descendants_count": 2,
            },
            ssa_index={},
        )

        assert "202100135" in html
        assert "202100186" in html

    def test_derivadas_graph_label_click_opens_details_dialog(self, monkeypatch):
        label = self.window.details_graph_label
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100186", 10.0, 10.0, 90.0, 50.0)])
        opened: list[str] = []
        jump_calls: list[str] = []

        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)
        monkeypatch.setattr(self.window, "_jump_to_ssa", jump_calls.append)

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(20, 20),
        )

        assert opened == ["202100186"]
        assert jump_calls == []

    def test_derivadas_graph_label_shows_clickable_cursor_on_node(self):
        label = self.window.details_graph_label
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100186", 10.0, 10.0, 90.0, 50.0)])
        label.show()
        QApplication.processEvents()

        inside_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(20, 20),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        label.mouseMoveEvent(inside_event)

        assert label.cursor().shape() == Qt.CursorShape.PointingHandCursor

        outside_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(160, 100),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        label.mouseMoveEvent(outside_event)

        assert label.cursor().shape() == Qt.CursorShape.ArrowCursor

    def test_derivadas_graph_label_click_uses_logical_pixmap_size(self, monkeypatch):
        class _FakeSize:
            def width(self):
                return 90.0

            def height(self):
                return 30.0

        class _FakePixmap:
            def isNull(self):
                return False

            def deviceIndependentSize(self):
                return _FakeSize()

            def width(self):
                return 180

            def height(self):
                return 60

        label = self.window.details_graph_label
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100186", 10.0, 10.0, 45.0, 20.0)])
        opened: list[str] = []

        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)
        monkeypatch.setattr(label, "pixmap", lambda: _FakePixmap())

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(78, 60),
        )

        assert opened == ["202100186"]

    def test_derivadas_graph_label_click_uses_centered_display_coordinates(
        self, monkeypatch
    ):
        class _FakeSize:
            def width(self):
                return 90.0

            def height(self):
                return 30.0

        class _FakePixmap:
            def isNull(self):
                return False

            def deviceIndependentSize(self):
                return _FakeSize()

            def width(self):
                return 180

            def height(self):
                return 60

        label = self.window.details_graph_label
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100186", 10.0, 10.0, 45.0, 20.0)])
        opened: list[str] = []

        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)
        monkeypatch.setattr(label, "pixmap", lambda: _FakePixmap())

        offset_x = int((label.width() - 90.0) / 2.0)
        offset_y = int((label.height() - 30.0) / 2.0)

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(offset_x + 27, offset_y + 15),
        )

        assert opened == ["202100186"]

    def test_derivadas_graph_label_click_opens_details_without_table_state_change(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202100046"],
                "descricao_ssa": ["Pai", "Filha"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window.details_tab_bar.setCurrentIndex(1)
        QApplication.processEvents()
        self.window.table_widget.selectRow(0)
        self.window.update_details_from_selection()
        QApplication.processEvents()
        ctx = self._panel_context()
        before_shell_sizes = (
            ctx["details_group"].width(),
            ctx["details_group"].height(),
            ctx["filters_panel_group"].width(),
            ctx["filters_panel_group"].height(),
        )
        before_shell_tops = (
            ctx["details_group"].mapToGlobal(QPoint(0, 0)).y(),
            ctx["filters_panel_group"].mapToGlobal(QPoint(0, 0)).y(),
        )
        before_base_tabs = (
            ctx["details_tab_bar"].mapToGlobal(QPoint(0, 0)).x(),
            ctx["details_tab_bar"].mapToGlobal(QPoint(0, 0)).y(),
            ctx["details_tab_bar"].tabRect(0).getRect(),
            ctx["details_tab_bar"].tabRect(1).getRect(),
        )

        label = self.window.details_graph_label
        pixmap = label.pixmap()
        hitboxes = getattr(label, "_ssa_hitboxes", [])

        assert pixmap is not None
        assert pixmap.isNull() is False
        assert len(hitboxes) >= 2

        child_ssa, left, top, right, bottom = hitboxes[-1]
        logical_size = pixmap.deviceIndependentSize()
        offset_x = int((label.width() - float(logical_size.width())) / 2.0)
        offset_y = int((label.height() - float(logical_size.height())) / 2.0)
        click_x = offset_x + int((left + right) / 2.0)
        click_y = offset_y + int((top + bottom) / 2.0)

        assert child_ssa == "202100154"
        assert self.window.table_widget.currentRow() == 0
        before_search = str(self.window.search_input.text() or "")
        before_filters = dict(self.window._active_column_filters)
        opened: list[str] = []
        jump_calls: list[str] = []
        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)
        monkeypatch.setattr(
            ssa_gui_details,
            "_open_details_dialog_for_ssa",
            lambda _window, numero_ssa, series=None: opened.append(numero_ssa),
        )
        monkeypatch.setattr(self.window, "_jump_to_ssa", jump_calls.append)

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(click_x, click_y),
        )
        QApplication.processEvents()
        after_shell_sizes = (
            ctx["details_group"].width(),
            ctx["details_group"].height(),
            ctx["filters_panel_group"].width(),
            ctx["filters_panel_group"].height(),
        )
        after_shell_tops = (
            ctx["details_group"].mapToGlobal(QPoint(0, 0)).y(),
            ctx["filters_panel_group"].mapToGlobal(QPoint(0, 0)).y(),
        )
        after_base_tabs = (
            ctx["details_tab_bar"].mapToGlobal(QPoint(0, 0)).x(),
            ctx["details_tab_bar"].mapToGlobal(QPoint(0, 0)).y(),
            ctx["details_tab_bar"].tabRect(0).getRect(),
            ctx["details_tab_bar"].tabRect(1).getRect(),
        )

        assert opened == ["202100154"]
        assert jump_calls == []
        assert self.window.table_widget.currentRow() == 0
        assert getattr(self.window, "_details_current_ssa", "") == "202100046"
        assert str(self.window.search_input.text() or "") == before_search
        assert self.window._active_column_filters == before_filters
        assert getattr(self.window, "_pending_jump_to_ssa", None) is None
        assert ctx["details_tab_bar"].count() == 2
        assert ctx["details_stack"].currentIndex() == 1
        live_context_state = getattr(self.window, "_details_context_state", None)
        if isinstance(live_context_state, dict):
            assert str(live_context_state.get("current_ssa") or "") != "202100154"
        assert before_shell_sizes == after_shell_sizes
        assert before_shell_tops == after_shell_tops
        assert before_base_tabs == after_base_tabs
        assert abs(after_shell_tops[0] - after_shell_tops[1]) <= 1

    def test_derivadas_graph_label_refresh_helper_reapplies_hitboxes(self, monkeypatch):
        class _FakeSize:
            def width(self):
                return 180.0

            def height(self):
                return 90.0

        class _FakePixmap:
            def isNull(self):
                return False

            def deviceIndependentSize(self):
                return _FakeSize()

            def width(self):
                return 180

            def height(self):
                return 90

        label = self.window.details_graph_label
        label.resize(260, 170)
        label.set_graph_svg_markup(
            '<svg viewBox="0 0 200 100">'
            '<rect data-ssa="202100186" x="50" y="20" width="80" height="30" />'
            "</svg>"
        )
        monkeypatch.setattr(label, "pixmap", lambda: _FakePixmap())
        refresh_calls: list[str] = []

        def _refresh_hitboxes(widget, svg: str):
            refresh_calls.append(svg)
            ssa_gui_details.reapply_graph_navigation_hitboxes(widget, svg)

        monkeypatch.setattr(
            self.window, "_refresh_derivadas_graph_hitboxes", _refresh_hitboxes
        )
        opened: list[str] = []

        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)

        label._refresh_hitboxes_from_svg()

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(103, 66),
        )

        assert refresh_calls
        assert opened == ["202100186"]

    def test_build_derivadas_graph_html_offsets_text_baseline_for_qt_svg(self):
        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            {"target": "202600023", "children": ["202600024"]},
            link_color="#4a90e2",
            font_family="monospace",
        )

        rect_match = re.search(
            r'<rect[^>]*\by="([^"]+)"[^>]*data-ssa="202600023"[^>]*/>',
            html,
        )
        text_match = re.search(
            r'<text[^>]*\by="([^"]+)"[^>]*>202600023</text>',
            html,
        )
        assert rect_match is not None
        assert text_match is not None
        rect_top = float(rect_match.group(1))
        text_y = float(text_match.group(1))
        assert text_y > (rect_top + 15.0)

    def test_derivadas_graph_label_ignores_right_click(self, monkeypatch):
        label = self.window.details_graph_label
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100186", 10.0, 10.0, 90.0, 50.0)])
        opened: list[str] = []
        jump_calls: list[str] = []

        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)
        monkeypatch.setattr(self.window, "_jump_to_ssa", jump_calls.append)

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.RightButton,
            pos=QPoint(20, 20),
        )

        assert opened == []
        assert jump_calls == []

    def test_details_dialog_graph_label_click_opens_details_dialog(
        self, monkeypatch
    ):
        from gui.ssa.main_window_bottom_section import DerivadasGraphLabel

        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202100046"],
                "descricao_ssa": ["Pai", "Filha"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        shown: list[QDialog] = []

        def record_dialog_show(dialog: QDialog) -> None:
            shown.append(dialog)

        monkeypatch.setattr(
            QtWidgets.QDialog,
            "show",
            record_dialog_show,
            raising=False,
        )

        self.window._open_details_dialog_for_ssa("202100046")
        QApplication.processEvents()

        assert shown
        label = shown[0].findChild(DerivadasGraphLabel)
        assert label is not None
        label.setFixedSize(200, 120)
        label.set_ssa_hitboxes([("202100154", 10.0, 10.0, 90.0, 50.0)])
        opened: list[str] = []
        monkeypatch.setattr(self.window, "_open_details_dialog_for_ssa", opened.append)

        cast(Any, QTest).mouseClick(
            label,
            Qt.MouseButton.LeftButton,
            pos=QPoint(20, 20),
        )

        assert opened == ["202100154"]
        shown[0].close()

    def test_apply_theme_refreshes_open_details_dialog_graph_colors(
        self, monkeypatch
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154"],
                "situacao": ["APV", "STE"],
                "derivada_de": ["", "202100046"],
                "descricao_ssa": ["Pai", "Filha"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        shown: list[QDialog] = []

        def record_dialog_show(dialog: QDialog) -> None:
            shown.append(dialog)

        monkeypatch.setattr(
            QtWidgets.QDialog,
            "show",
            record_dialog_show,
            raising=False,
        )

        self.window.apply_theme("mint-light")
        self.window._open_details_dialog_for_ssa("202100046")
        QApplication.processEvents()

        assert shown
        presenter = getattr(shown[0], "_ssa_details_dialog_presenter", None)
        assert presenter is not None
        light_svg = str(presenter.export_state["svg"] or "")

        self.window.apply_theme("dracula")
        QApplication.processEvents()
        dark_svg = str(presenter.export_state["svg"] or "")

        light_fill = str(get_theme_roles("mint-light").get("input_bg") or "")
        dark_fill = str(get_theme_roles("dracula").get("input_bg") or "")
        assert light_fill
        assert dark_fill
        assert light_fill in light_svg
        assert dark_fill in dark_svg
        assert light_svg != dark_svg
        shown[0].close()

    def test_build_derivadas_graph_html_sanitizes_font_family(self):
        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            {"target": "202600023", "children": ["202600024"]},
            link_color="#4a90e2",
            font_family='bad";onclick="alert(1)',
        )

        assert 'onclick="alert(1)' not in html
        assert "font-family:sans-serif" in html

    def test_build_derivadas_graph_html_preserves_quoted_font_family(self):
        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            {"target": "202600023", "children": ["202600024"]},
            link_color="#4a90e2",
            font_family="Menlo, 'Andale Mono', Consolas",
        )

        assert "font-family:sans-serif" not in html
        assert "Menlo" in html
        assert "Andale Mono" in html
        assert "Consolas" in html

    def test_build_derivadas_graph_html_dashes_relation_type_edges(self):
        data: dict[str, object] = {
            "target": "202600023",
            "parents": [],
            "children": ["202600024"],
            "descendants": [
                {
                    "ssa": "202600024",
                    "parent": "202600023",
                    "relation_type": 2,
                    "relation_raw_label": "Relacionada",
                }
            ],
            "descendants_count": 1,
        }

        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            data,
            link_color="#4a90e2",
            font_family="monospace",
        )

        assert 'data-from="202600023" data-to="202600024"' in html
        assert "stroke-dasharray" in html

    def test_build_derivadas_graph_html_separates_sibling_edge_lanes(self):
        data: dict[str, object] = {
            "target": "202603583",
            "parents": ["202603570"],
            "children": ["202603588"],
            "descendants": [],
            "related": [
                {"ssa": "202500777", "situacao": "APL", "relacao": "REL"},
                {"ssa": "202500888", "situacao": "APL", "relacao": "REL"},
            ],
            "descendants_count": 1,
        }

        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            data,
            link_color="#4a90e2",
            font_family="monospace",
        )

        lane_xs = [
            float(match.group(1))
            for match in re.finditer(
                r'L([0-9]+(?:\.[0-9]+)?),[0-9]+(?:\.[0-9]+)? L\1,[0-9]+(?:\.[0-9]+)?',
                html,
            )
        ]
        right_node_left_edges = []
        for label in ("202603588", "202500777", "202500888"):
            match = re.search(
                rf'<rect x="([0-9]+(?:\.[0-9]+)?)" y="([0-9]+(?:\.[0-9]+)?)" '
                rf'width="100" height="30"[^>]*/><text[^>]*>{label}</text>',
                html,
            )
            assert match is not None
            right_node_left_edges.append(float(match.group(1)))

        assert len(lane_xs) >= 3
        assert len(set(lane_xs)) >= 3
        assert all(x < min(right_node_left_edges) for x in lane_xs[:3])

    def test_build_derivadas_graph_html_renders_parent_sibling_family(self):
        data: dict[str, object] = {
            "target": "202600101",
            "parents": ["202600100"],
            "family_roots": ["202600100"],
            "children": [],
            "descendants": [
                {"ssa": "202600101", "parent": "202600100"},
                {"ssa": "202600102", "parent": "202600100"},
                {"ssa": "202600103", "parent": "202600102"},
            ],
            "ancestors": [{"ssa": "202600100", "min_distance": 1}],
            "descendants_count": 3,
            "render_family": True,
        }

        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            data,
            link_color="#4a90e2",
            font_family="monospace",
        )

        assert "202600100" in html
        assert "202600101" in html
        assert "202600102" in html
        assert "202600103" in html
        assert 'data-from="202600100" data-to="202600101"' in html
        assert 'data-from="202600100" data-to="202600102"' in html
        assert 'data-from="202600102" data-to="202600103"' in html

    def test_build_derivadas_graph_html_marks_partial_family(self):
        data: dict[str, object] = {
            "target": "202600101",
            "parents": ["202600100"],
            "family_roots": ["202600100"],
            "children": [],
            "descendants": [
                {"ssa": "202600101", "parent": "202600100"},
            ],
            "ancestors": [{"ssa": "202600100", "min_distance": 1}],
            "descendants_count": 1,
            "descendants_partial": True,
            "render_family": True,
        }

        html = ssa_gui_details._build_derivadas_graph_html(
            self.window,
            data,
            link_color="#4a90e2",
            font_family="monospace",
        )

        assert "Exibicao parcial de descendentes: +1" in html

    def test_normalize_ssa_series_reuses_unique_normalizations(self, monkeypatch):
        calls = []

        def _fake_norm(_window, value):
            calls.append(value)
            if value is None:
                return ""
            return str(value)

        monkeypatch.setattr(ssa_gui_details, "_normalize_ssa_value", _fake_norm)
        series = pd.Series(["202600023", "202600023", "202600029", None, "202600029"])
        normalized = ssa_gui_details._normalize_ssa_series(self.window, series)
        assert normalized.tolist() == [
            "202600023",
            "202600023",
            "202600029",
            "",
            "202600029",
        ]
        assert len(calls) <= 3

    def test_normalize_ssa_series_fallback_still_normalizes(self, monkeypatch):
        def _raise_factorize(*_args, **_kwargs):
            raise TypeError("unhashable")

        monkeypatch.setattr(ssa_gui_details.pd, "factorize", _raise_factorize)

        series = pd.Series(["202500001.0", None, "nan", "202500002.0"])
        normalized = ssa_gui_details._normalize_ssa_series(self.window, series)

        assert normalized.tolist() == ["202500001", "", "", "202500002"]

    def test_open_details_dialog_builds_dedicated_tree_tab(self, monkeypatch):
        self.window.df_exibido = self.base_df.copy()
        captured = {}

        def _fake_show(dialog):
            captured["tab_count"] = len(dialog.findChildren(QtWidgets.QTabWidget))
            splitters = dialog.findChildren(QtWidgets.QSplitter)
            captured["splitter_sizes"] = [splitter.sizes() for splitter in splitters]
            captured["splitter_handles"] = [
                splitter.handleWidth() for splitter in splitters
            ]
            captured["graph_label_count"] = sum(
                1
                for label in dialog.findChildren(QLabel)
                if label.pixmap() is not None and not label.pixmap().isNull()
            )
            captured["tool_buttons"] = [
                button.text() for button in dialog.findChildren(QtWidgets.QToolButton)
            ]
            captured["browser_texts"] = [
                browser.toPlainText()
                for browser in dialog.findChildren(QtWidgets.QTextBrowser)
            ]
            dialog.close()

        monkeypatch.setattr(QtWidgets.QDialog, "show", _fake_show, raising=False)
        monkeypatch.setattr(
            QtWidgets.QDialog,
            "exec",
            lambda _dialog: (_ for _ in ()).throw(
                AssertionError("details dialog must be non-modal")
            ),
            raising=False,
        )
        self.window._open_details_dialog_for_ssa("1")
        assert captured["tab_count"] == 0
        assert any(
            len(sizes) == 2
            and sizes[1] >= ssa_gui_details.DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT
            for sizes in captured["splitter_sizes"]
        )
        assert any(
            len(sizes) == 2 and sizes[0] > sizes[1]
            for sizes in captured["splitter_sizes"]
        )
        assert all(width == 10 for width in captured["splitter_handles"])
        assert captured["graph_label_count"] >= 1
        assert "Exportar" in captured["tool_buttons"]
        assert any("Derivadas:" in text for text in captured["browser_texts"])
        assert not any(
            "Relacoes de Derivadas" in text for text in captured["browser_texts"]
        )

    def test_open_details_dialog_clamps_to_active_screen(self, monkeypatch):
        self.window.df_exibido = self.base_df.copy()
        captured = {}

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_dialog_screen_geometry",
            lambda _widget: QRect(0, 0, 900, 700),
        )

        def _fake_show(dialog):
            captured["max_size"] = dialog.maximumSize()
            captured["size"] = dialog.size()
            dialog.close()

        monkeypatch.setattr(QtWidgets.QDialog, "show", _fake_show, raising=False)
        self.window._open_details_dialog_for_ssa("1")

        assert captured["max_size"].width() <= 876
        assert captured["max_size"].height() <= 676
        assert captured["size"].width() <= 876
        assert captured["size"].height() <= 676

    def test_open_details_dialog_width_does_not_expand_to_size_hint(
        self, monkeypatch
    ):
        self.window.df_exibido = self.base_df.copy()
        captured = {}

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_dialog_screen_geometry",
            lambda _widget: QRect(0, 0, 1600, 1200),
        )
        monkeypatch.setattr(
            QtWidgets.QDialog,
            "sizeHint",
            lambda _dialog: QSize(1500, 700),
            raising=False,
        )

        def _fake_show(dialog):
            captured["size"] = dialog.size()
            dialog.close()

        monkeypatch.setattr(QtWidgets.QDialog, "show", _fake_show, raising=False)
        self.window._open_details_dialog_for_ssa("1")

        assert captured["size"].width() == ssa_gui_details.DERIVADAS_DIALOG_MIN_WIDTH

    def test_open_details_dialog_is_modeless_and_keeps_multiple_windows(
        self, monkeypatch
    ):
        self.window.df_exibido = self.base_df.copy()
        shown = []

        monkeypatch.setattr(
            QtWidgets.QDialog,
            "exec",
            lambda _dialog: (_ for _ in ()).throw(
                AssertionError("details dialog must not call exec")
            ),
            raising=False,
        )

        def record_dialog_show(dialog: QDialog) -> None:
            shown.append(dialog)

        monkeypatch.setattr(
            QtWidgets.QDialog,
            "show",
            record_dialog_show,
            raising=False,
        )

        self.window._open_details_dialog_for_ssa("1")
        self.window._open_details_dialog_for_ssa("2")

        assert len(shown) == 2
        assert self.window.isEnabled() is True
        assert all(dialog.isModal() is False for dialog in shown)
        assert all(
            dialog.windowModality() == Qt.WindowModality.NonModal for dialog in shown
        )
        assert shown[0] is not shown[1]
        assert getattr(self.window, "_open_details_dialogs", [])[-2:] == shown
        for dialog in shown:
            dialog.close()

    def test_open_details_dialog_uses_main_window_height(self, monkeypatch):
        self.window.df_exibido = self.base_df.copy()
        self.window.resize(1280, 880)
        captured = {}

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_dialog_screen_geometry",
            lambda _widget: QRect(0, 0, 1600, 1200),
        )

        def _fake_show(dialog):
            captured["size"] = dialog.size()
            captured["minimum_size"] = dialog.minimumSize()
            captured["maximum_size"] = dialog.maximumSize()
            splitters = dialog.findChildren(QtWidgets.QSplitter)
            captured["splitter_sizes"] = [splitter.sizes() for splitter in splitters]
            dialog.close()

        monkeypatch.setattr(QtWidgets.QDialog, "show", _fake_show, raising=False)
        self.window._open_details_dialog_for_ssa("1")

        expected_min_height = max(
            int(880 * 0.72), ssa_gui_details.DERIVADAS_DIALOG_MIN_HEIGHT
        )
        assert captured["size"].height() >= expected_min_height
        assert captured["size"].height() <= captured["maximum_size"].height()
        assert (
            captured["minimum_size"].height()
            == ssa_gui_details.DERIVADAS_DIALOG_MIN_HEIGHT
        )
        assert any(
            len(sizes) == 2
            and sizes[1] >= ssa_gui_details.DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT
            for sizes in captured["splitter_sizes"]
        )

    def test_open_details_dialog_avoids_global_ssa_index_build(self, monkeypatch):
        self.window.df_exibido = self.base_df.copy()
        self.window.df_para_tabela = self.base_df.head(1).copy()

        monkeypatch.setattr(
            QtWidgets.QDialog, "show", lambda dialog: dialog.close(), raising=False
        )

        with patch(
            "gui.ssa.gui_details._get_window_ssa_series_index",
            side_effect=AssertionError("nao deveria montar indice global"),
        ):
            self.window._open_details_dialog_for_ssa("1")

    def test_open_details_dialog_reuses_provided_series_on_initial_render(
        self, monkeypatch
    ):
        self.window.df_exibido = self.base_df.copy()
        self.window.df_para_tabela = self.base_df.head(1).copy()
        series = self.window.df_exibido.iloc[0]
        seen = {"first_target_ok": False}

        monkeypatch.setattr(
            QtWidgets.QDialog, "show", lambda dialog: dialog.close(), raising=False
        )

        original_get_series = ssa_gui_details._get_series_for_ssa

        def _guard_get_series(window, numero_ssa):
            if str(numero_ssa) == "1" and not seen["first_target_ok"]:
                raise AssertionError("nao deveria reconsultar a SSA inicial")
            return original_get_series(window, numero_ssa)

        def _guard_format(window, rendered_series, **kwargs):
            seen["first_target_ok"] = rendered_series is series
            return "<html><body>ok</body></html>"

        monkeypatch.setattr(ssa_gui_details, "_format_details_html", _guard_format)
        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda *_args, **_kwargs: {
                "target": "1",
                "parents": [],
                "children": [],
                "descendants": [],
                "ancestors": [],
                "related": [],
                "direct_children_count": 0,
                "descendants_count": 0,
            },
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_build_derivadas_tree_html",
            lambda *_args, **_kwargs: "<html><body>tree</body></html>",
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_build_derivadas_graph_html",
            lambda *_args, **_kwargs: "",
        )
        monkeypatch.setattr(ssa_gui_details, "_get_series_for_ssa", _guard_get_series)

        self.window._open_details_dialog_for_ssa("1", series=series)

        assert seen["first_target_ok"] is True

    def test_build_derivadas_tree_html_links_valid_missing_target(self, monkeypatch):
        monkeypatch.setattr(
            ssa_gui_details,
            "_collect_derivadas_tree_data",
            lambda _window, _numero: {
                "target": "202602147",
                "parents": ["202500777"],
                "children": [],
                "descendants": [],
                "ancestors": [],
                "direct_children_count": 0,
                "descendants_count": 0,
            },
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_series_for_ssa",
            lambda _window, numero: object() if str(numero) == "202602147" else None,
        )

        html = ssa_gui_details._build_derivadas_tree_html(self.window, "202602147")

        assert '<a href="ssa-context:202602147"' in html
        assert "202500777" in html
        assert 'href="ssa-context:202500777"' not in html

    def test_get_related_ssas_for_series_falls_back_when_mapping_is_empty(self):
        series = self.base_df.iloc[0].copy()
        series["numero_ssa_relacionada_1"] = "202500777"
        series["situacao_relacionada_1"] = ""

        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=lambda _window, numero: {"situacao": "STE"}
            if str(numero) == "202500777"
            else None,
        ):
            related = ssa_gui_details._get_related_ssas_for_series(
                self.window,
                series,
                ssa_index={},
            )

        assert related == [
            {
                "ssa": "202500777",
                "situacao": "STE",
                "relacao": "",
                "exists": "1",
            }
        ]

    def test_collect_derivadas_tree_data_uses_direct_parent_fallback_without_db(
        self, monkeypatch
    ):
        base_df = pd.DataFrame(
            [
                {"numero_ssa": "202603570", "situacao": "ADI"},
                {
                    "numero_ssa": "202603583",
                    "situacao": "STE",
                    "derivada_de": "202603570",
                    "numero_ssa_relacionada_1": "202500777",
                    "situacao_relacionada_1": "APL",
                },
                {
                    "numero_ssa": "202603588",
                    "situacao": "APL",
                    "derivada_de": "202603583",
                },
                {"numero_ssa": "202500777", "situacao": "APL"},
            ]
        )
        self.window.df_completo = base_df.copy()
        self.window.df_exibido = base_df.copy()
        monkeypatch.setattr(ssa_gui_details, "_resolve_current_db_path", lambda: None)

        tree_data = ssa_gui_details._collect_derivadas_tree_data(
            self.window, "202603583"
        )

        assert tree_data["parents"] == ["202603570"]
        assert tree_data["children"] == ["202603588"]
        assert tree_data["related"][0]["ssa"] == "202500777"

    def test_format_details_html_links_valid_missing_derived_target(
        self, monkeypatch
    ):
        seen_targets = []
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_derivadas_for_ssa",
            lambda _window, _numero: ["202602147", "202602147", "202500777"],
        )

        def _fake_get_series(_window, numero):
            seen_targets.append(str(numero))
            return object() if str(numero) == "202602147" else None

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_series_for_ssa",
            _fake_get_series,
        )

        series = pd.Series({"numero_ssa": "202600023", "situacao": "APL"})

        html = ssa_gui_details._format_details_html(
            self.window,
            series,
            highlight_search_terms=False,
            linkify=True,
        )

        assert '<a href="ssa:202602147"' in html
        assert '<a href="ssa:202500777"' not in html
        assert "202500777" in html
        assert seen_targets.count("202602147") == 1
        assert seen_targets.count("202500777") == 1

    def test_details_number_double_click_copies_current_ssa(self, monkeypatch):
        self.window._details_current_ssa = "202600023"
        self.window.details_text.setHtml(
            '<a href="copy-ssa:202600023" style="text-decoration:none;">202600023</a>'
        )
        monkeypatch.setattr(
            self.window.details_text,
            "anchorAt",
            lambda _point: "copy-ssa:202600023",
        )

        class _FakeEvent:
            def type(self):
                return QEvent.Type.MouseButtonDblClick

            def position(self):
                class _P:
                    def toPoint(_self):
                        return QPoint(1, 1)

                return _P()

        handled = self.window.eventFilter(
            self.window._details_text_viewport, _FakeEvent()
        )

        clipboard = QApplication.clipboard()
        assert handled is True
        assert clipboard is not None
        assert clipboard.text() == "202600023"

    def test_details_number_single_click_copies_current_ssa(self, monkeypatch):
        self.window._details_current_ssa = "202600023"
        self.window.details_text.setHtml(
            '<a href="copy-ssa:202600023" style="text-decoration:none;">202600023</a>'
        )
        monkeypatch.setattr(
            self.window.details_text,
            "anchorAt",
            lambda _point: "copy-ssa:202600023",
        )

        class _FakeEvent:
            def type(self):
                return QEvent.Type.MouseButtonPress

            def position(self):
                class _P:
                    def toPoint(_self):
                        return QPoint(1, 1)

                return _P()

        handled = self.window.eventFilter(
            self.window._details_text_viewport, _FakeEvent()
        )

        clipboard = QApplication.clipboard()
        assert handled is True
        assert clipboard is not None
        assert clipboard.text() == "202600023"

    def test_details_anchor_click_copies_current_ssa(self):
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        clipboard.setText("")

        self.window._on_details_anchor_clicked(QUrl("copy-ssa:202600023"))

        assert clipboard.text() == "202600023"

    def test_hidden_column_filter_still_applies_when_column_not_visible(self):
        self.window.visible_columns = [
            "numero_ssa",
            "situacao",
            "setor_executor",
        ]
        self.window._active_column_filters = {
            "solicitante": "User3",
        }

        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        assert Counter(self._extract_visible_ssa()) == Counter([3])
        assert "solicitante" not in self.window._current_display_columns

    def test_clicking_hash_column_opens_sam_ssa_url(self, monkeypatch):
        self.window.table_widget.setColumnCount(2)
        self.window._current_display_columns = ["#", "numero_ssa"]
        opened = []

        monkeypatch.setattr(
            self.window,
            "_get_series_from_row",
            lambda _row: pd.Series({"numero_ssa": "202600001"}),
        )
        monkeypatch.setattr(
            self.window,
            "_resolve_header_column_name",
            lambda column: "#" if column == 0 else "numero_ssa",
        )
        monkeypatch.setattr(
            gui_ssa.QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        self.window.on_table_cell_clicked(0, 0)

        assert opened == [
            "https://osprd.itaipu/SAM_SMA/SSAPublicView.aspx?SerialNumber=202600001&language=pt"
        ]

    def test_clicking_reordered_hash_column_opens_sam_ssa_url(self, monkeypatch):
        self.window.table_widget.setColumnCount(3)
        self.window._current_display_columns = ["situacao", "#", "numero_ssa"]
        opened = []

        monkeypatch.setattr(
            self.window,
            "_get_series_from_row",
            lambda _row: pd.Series({"numero_ssa": "202600001"}),
        )
        monkeypatch.setattr(
            self.window,
            "_resolve_header_column_name",
            lambda column: "#" if column == 1 else "situacao",
        )
        monkeypatch.setattr(
            gui_ssa.QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        self.window.on_table_cell_clicked(0, 0)
        self.window.on_table_cell_clicked(0, 1)

        assert opened == [
            "https://osprd.itaipu/SAM_SMA/SSAPublicView.aspx?SerialNumber=202600001&language=pt"
        ]

    def test_double_click_numero_ssa_copies_without_opening_details(self, monkeypatch):
        self.window.display_current_page(1)
        display_columns = list(
            getattr(self.window, "_current_display_columns", []) or []
        )
        assert "numero_ssa" in display_columns
        numero_col = display_columns.index("numero_ssa")
        model_index = self.window.table_widget.model().index(0, numero_col)

        copied = []
        opened = []

        monkeypatch.setattr(
            self.window,
            "_copy_ssa_to_clipboard",
            lambda numero_ssa, **_kwargs: copied.append(str(numero_ssa)) or True,
        )
        monkeypatch.setattr(
            self.window,
            "_open_details_dialog_for_ssa",
            lambda numero_ssa, series=None: opened.append((str(numero_ssa), series)),
        )

        self.window.on_table_double_click(model_index)

        assert copied == ["1"]
        assert opened == []

    def test_clicking_numero_ssa_column_does_not_open_sam(self, monkeypatch):
        self.window.display_current_page(1)
        display_columns = list(
            getattr(self.window, "_current_display_columns", []) or []
        )
        numero_col = display_columns.index("numero_ssa")
        opened = []

        monkeypatch.setattr(
            QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        self.window.on_table_cell_clicked(0, numero_col)

        assert opened == []

    def test_double_click_non_numero_ssa_opens_details_without_copy(self, monkeypatch):
        self.window.display_current_page(1)
        model_index = self.window.table_widget.model().index(0, 0)

        copied = []
        opened = []

        monkeypatch.setattr(
            self.window,
            "_copy_ssa_to_clipboard",
            lambda numero_ssa, **_kwargs: copied.append(str(numero_ssa)) or True,
        )
        monkeypatch.setattr(
            self.window,
            "_open_details_dialog_for_ssa",
            lambda numero_ssa, series=None: opened.append((str(numero_ssa), series)),
        )

        self.window.on_table_double_click(model_index)

        assert copied == []
        assert len(opened) == 1
        assert opened[0][0] == "1"
        assert opened[0][1].equals(self.window.df_exibido.iloc[0])

    def test_clicking_hash_column_with_pd_na_does_not_raise(self, monkeypatch):
        self.window.df_completo = self.window.df_completo.copy()
        self.window.df_exibido = self.window.df_exibido.copy()
        self.window.df_completo.loc[0, "numero_ssa"] = pd.NA
        self.window.df_exibido.loc[0, "numero_ssa"] = pd.NA
        self.window.display_current_page(1)
        opened = []

        monkeypatch.setattr(
            QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        self.window.on_table_cell_clicked(0, 0)
        assert opened == []

    def test_open_sam_home_uses_default_browser(self, monkeypatch):
        opened = []

        monkeypatch.setattr(
            QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        result = self.window._open_sam_home()

        assert result is True
        assert opened == ["https://osprd.itaipu/SAM_SMA/"]

    def test_generate_xls_button_opens_sam_reports_page(self, monkeypatch):
        opened = []

        monkeypatch.setattr(
            QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        result = self.window._open_sam_reports_xls_page()

        assert result is True
        assert opened == [
            "https://apps.itaipu.gov.br/SAM_SMA_Reports/Reports.aspx",
        ]
        assert (
            str(self.window.status_label.text() or "")
            == "Status: Relatorio XLS aberto no navegador."
        )

    def test_load_xls_button_uses_external_import_handler(self, monkeypatch):
        dialog_calls = []

        monkeypatch.setattr(
            gui_ssa.QFileDialog,
            "getOpenFileNames",
            lambda *args, **kwargs: dialog_calls.append((args, kwargs)) or ([], ""),
        )

        self.window.api_button.click()

        assert len(dialog_calls) == 1

    def test_open_url_in_browser_blocks_file_scheme(self, monkeypatch):
        opened: list[str] = []
        self.window.status_label.setText("Status: inicial")

        monkeypatch.setattr(
            gui_ssa.QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        result = self.window._open_url_in_browser(
            "file:///tmp/ssa.html",
            success_status="Status: deveria abrir",
        )

        assert result is False
        assert opened == []
        assert str(self.window.status_label.text() or "") == "Status: inicial"

    def test_open_url_in_browser_blocks_external_host(self, monkeypatch):
        opened: list[str] = []
        self.window.status_label.setText("Status: inicial")

        monkeypatch.setattr(
            gui_ssa.QDesktopServices,
            "openUrl",
            lambda url: opened.append(url.toString()) or True,
        )

        result = self.window._open_url_in_browser(
            "https://example.com/SAM_SMA/",
            success_status="Status: deveria abrir",
        )

        assert result is False
        assert opened == []
        assert str(self.window.status_label.text() or "") == "Status: inicial"

    def test_load_other_database_validates_selected_db_without_blocking_contract(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "other.db"
        db_file.write_text("stub", encoding="utf-8")
        original_db_path = gui_ssa.DB_PATH

        monkeypatch.setattr(
            gui_ssa.QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(db_file), ""),
        )
        monkeypatch.setattr(
            gui_ssa,
            "query_db",
            lambda *_args, **_kwargs: pd.DataFrame({"numero_ssa": ["1"]}),
        )

        try:
            result = self.window.load_other_database()
            assert bool(result["ok"]) is True
            assert gui_ssa.DB_PATH == str(db_file)
            assert "Banco alternativo selecionado" in self.window.status_label.text()
        finally:
            gui_ssa.DB_PATH = original_db_path

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

    def test_details_anchor_ssa_panel_jumps_to_clean_ssa(self):
        with patch("gui.ssa.gui_details._jump_to_ssa") as jump_mock:
            self.window._on_details_anchor_clicked(QUrl("ssa-panel:202500777"))

        jump_mock.assert_called_once()
        assert jump_mock.call_args.args[0] is self.window
        assert jump_mock.call_args.args[1] == "202500777"
        assert jump_mock.call_args.kwargs == {}

    def test_details_anchor_ssa_context_opens_internal_context(self):
        with patch("gui.ssa.gui_details._open_derivadas_context_panel") as open_mock:
            self.window._on_details_anchor_clicked(QUrl("ssa-context:202500777"))

        open_mock.assert_called_once()
        assert open_mock.call_args.args[0] is self.window
        assert open_mock.call_args.args[1] == "202500777"
        assert open_mock.call_args.kwargs == {}

    def test_details_anchor_ssa_updates_details_without_refilter(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500100", "202500101", "202500102"],
                "situacao": ["APV", "STE", "AMP"],
                "derivada_de": ["", "202500100", ""],
                "localizacao_codigo": ["L0", "L1", "L2"],
                "descricao_localizacao": ["DL0", "DL1", "DL2"],
                "equipamento": ["E0", "E1", "E2"],
                "semana_cadastro": [202501] * 3,
                "semana_programada": [202503] * 3,
                "data_cadastro": ["2025-01-01"] * 3,
                "descricao_ssa": ["Origem", "Filha", "Relacionada"],
                "setor_executor": ["IEE3", "MEL4", "XYZ"],
                "setor_emissor": ["ABC", "MEL4", "XYZ"],
                "descricao_execucao": ["Exec O", "Exec A", "Exec R"],
                "solicitante": ["User0", "User1", "User2"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.iloc[:1].copy()
        self.window._df_last_search_filtered = self.window.df_exibido.copy()
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window.search_input.setText("Origem")
        ssa_gui_details._update_details_from_series(self.window, df.iloc[0])

        self.window._on_details_anchor_clicked(QUrl("ssa:202500102"))

        details_html = str(self.window.details_text.toHtml() or "")
        assert self.window.search_input.text() == "Origem"
        assert str(self.window._details_current_ssa) == "202500102"
        assert "Relacionada" in details_html
        assert "Origem" not in details_html

    def test_normalize_ssa_value_handles_decimal_float_artifact(self):
        assert self.window._normalize_ssa_value("121911787.0") == "121911787"
        assert self.window._normalize_ssa_value(121911787.0) == "121911787"
        assert self.window._normalize_ssa_value(1e20) == "100000000000000000000"

    def test_get_derivadas_for_ssa_accepts_excel_decimal_relation_id_artifact(self):
        df = pd.DataFrame(
            {
                "numero_ssa": [
                    "SSA-101",
                    "121911787.0",
                    "102",
                    "2025-12345",
                    "2025-22222",
                ],
                "derivada_de": ["100", "100", "100", "100", "100"],
            }
        )
        self.window.df_completo = df.copy()

        derived = ssa_gui_details._get_derivadas_for_ssa(self.window, "100")

        assert derived == ["121911787", "102", "202512345", "202522222"]

    def test_get_derivadas_for_ssa_uses_cached_family_edges(self, monkeypatch):
        self.window.df_completo = pd.DataFrame(
            {"numero_ssa": ["101", "102"], "derivada_de": ["100", "100"]}
        )
        monkeypatch.setattr(
            ssa_gui_details,
            "_get_cached_derivadas_family_edges",
            lambda _window: [("100", "101"), ("100", "102"), ("100", "101")],
        )

        def _fail_full_column_scan(_series):
            raise AssertionError("nao deve normalizar coluna inteira a cada consulta")

        monkeypatch.setattr(
            ssa_gui_details,
            "_normalize_ssa_relation_series",
            _fail_full_column_scan,
        )

        derived = ssa_gui_details._get_derivadas_for_ssa(self.window, "100")

        assert derived == ["101", "102"]

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

    def test_get_series_for_ssa_falls_back_to_df_completo_without_building_index(self):
        self.window.df_exibido = pd.DataFrame(
            {
                "numero_ssa": ["100"],
                "descricao_ssa": ["A"],
            }
        )
        self.window.df_completo = pd.DataFrame(
            {
                "numero_ssa": ["100", "200", "300"],
                "descricao_ssa": ["A", "B", "C"],
            }
        )

        with patch(
            "gui.ssa.gui_details._get_df_ssa_series_index",
            side_effect=AssertionError("nao deveria montar indice completo"),
        ):
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

    def test_update_details_from_selection_clears_derivadas_when_selection_clears(self):
        self.window.display_current_page(1)
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()
        self.window._details_current_series_for_derivadas = self.base_df.iloc[0]
        self.window.details_tree_text.setHtml("conteudo antigo")
        self.window.details_graph_label.setText("grafo antigo")

        self.window.table_widget.clearSelection()
        self.window.update_details_from_selection()
        QApplication.processEvents()

        assert self.window._details_current_ssa is None
        assert self.window._details_current_series_for_derivadas is None
        assert self.window.details_text.toPlainText().strip() == ""
        assert self.window.details_tree_text.toPlainText().strip() == ""
        assert str(self.window.details_graph_label.text() or "") == ""

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

    def test_jump_to_ssa_cancels_pending_details_clear_for_offpage_target(
        self, monkeypatch
    ):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])
        target_desc = str(df.iloc[target_pos]["descricao_ssa"])
        first_desc = str(df.iloc[0]["descricao_ssa"])

        self.window.df_completo = df.copy()
        self.window.df_exibido = df.iloc[:50].copy().reset_index(drop=True)
        self.window._df_last_search_filtered = self.window.df_exibido.copy()
        self.window.paginator.page_size = 50
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()

        self.window._jump_to_ssa(target_ssa, _allow_refilter=False)

        deadline = time.time() + 0.25
        while time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)

        details_html = str(self.window.details_text.toHtml() or "")
        timer = getattr(self.window, "_details_update_timer", None)
        assert str(getattr(self.window, "_details_current_ssa", "")) == target_ssa
        assert target_desc in details_html
        assert first_desc not in details_html
        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert timer is not None
        assert timer.isActive() is False
        assert getattr(self.window, "_pending_details_series", "sentinel") is None

    def test_jump_to_ssa_shows_fallback_details_when_refilter_stays_offpage(
        self, monkeypatch
    ):
        rows = 220
        df = self._build_heavy_filters_df(rows)
        target_pos = 157
        target_ssa = str(df.iloc[target_pos]["numero_ssa"])
        target_desc = str(df.iloc[target_pos]["descricao_ssa"])
        first_desc = str(df.iloc[0]["descricao_ssa"])

        self.window.df_completo = df.copy()
        self.window.df_exibido = df.iloc[:50].copy().reset_index(drop=True)
        self.window._df_last_search_filtered = self.window.df_exibido.copy()
        self.window.paginator.page_size = 50
        self.window.paginator.set_dataframe(self.window.df_exibido.copy())
        self.window.display_current_page(1)
        self.window.table_widget.selectRow(0)
        QApplication.processEvents()

        def fake_initiate_filtering():
            self.window._active_filter_request_id = None

        monkeypatch.setattr(self.window, "initiate_filtering", fake_initiate_filtering)
        self.window.filter_thread = None

        self.window._jump_to_ssa(target_ssa)

        details_html = str(self.window.details_text.toHtml() or "")
        assert self.window.search_input.text() == f"={target_ssa}"
        assert str(getattr(self.window, "_details_current_ssa", "")) == target_ssa
        assert target_desc in details_html
        assert first_desc not in details_html
        assert self.window.table_widget.selectionModel().selectedRows() == []
        assert getattr(self.window, "_pending_jump_to_ssa", None) is None

    def test_on_filter_error_recovers_pending_jump_with_exact_ssa_fallback(self):
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
        self.window.search_input.setText(f"={target_ssa}")
        self.window._active_filter_request_id = 1
        self.window._pending_jump_to_ssa = {
            "numero_ssa": target_ssa,
            "request_id": 1,
        }

        self.window.on_filter_error("Erro ao filtrar dados: boom", request_id=1)

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
        assert self.window.search_input.text() == f"={target_ssa}"
        assert getattr(self.window, "_pending_jump_to_ssa", None) is None

    def test_filter_by_derivadas_updates_filtered_dataset_and_details(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500100", "202500101", "202500102", "202500200"],
                "situacao": ["APV", "STE", "AMP", "APV"],
                "derivada_de": ["", "202500100", "202500100", ""],
                "localizacao_codigo": ["L0", "L1", "L2", "L3"],
                "descricao_localizacao": ["DL0", "DL1", "DL2", "DL3"],
                "equipamento": ["E0", "E1", "E2", "E3"],
                "semana_cadastro": [202501] * 4,
                "semana_programada": [202503] * 4,
                "data_cadastro": ["2025-01-01"] * 4,
                "descricao_ssa": ["Origem", "Filha A", "Filha B", "Outra"],
                "setor_executor": ["IEE3", "MEL4", "XYZ", "ABC"],
                "setor_emissor": ["ABC", "MEL4", "XYZ", "AAA"],
                "descricao_execucao": ["Exec O", "Exec A", "Exec B", "Exec X"],
                "solicitante": ["User0", "User1", "User2", "User3"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window._filter_by_derivadas("202500100")
        QApplication.processEvents()

        assert self.window._last_derivada_origem == "202500100"
        assert self.window._active_column_filters["derivada_de"] == "202500100"
        assert self.window.df_exibido["numero_ssa"].tolist() == [
            "202500102",
            "202500101",
        ]
        assert str(self.window._details_current_ssa) == "202500102"
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Filha B" in details_html
        assert "Origem" not in details_html

    def test_clear_derivadas_filter_restores_origin_details_via_jump(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500100", "202500101", "202500102", "202500200"],
                "situacao": ["APV", "STE", "AMP", "APV"],
                "derivada_de": ["", "202500100", "202500100", ""],
                "localizacao_codigo": ["L0", "L1", "L2", "L3"],
                "descricao_localizacao": ["DL0", "DL1", "DL2", "DL3"],
                "equipamento": ["E0", "E1", "E2", "E3"],
                "semana_cadastro": [202501] * 4,
                "semana_programada": [202503] * 4,
                "data_cadastro": ["2025-01-01"] * 4,
                "descricao_ssa": ["Origem", "Filha A", "Filha B", "Outra"],
                "setor_executor": ["IEE3", "MEL4", "XYZ", "ABC"],
                "setor_emissor": ["ABC", "MEL4", "XYZ", "AAA"],
                "descricao_execucao": ["Exec O", "Exec A", "Exec B", "Exec X"],
                "solicitante": ["User0", "User1", "User2", "User3"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()
        self.window._filter_by_derivadas("202500100")
        QApplication.processEvents()

        with patch.object(
            ssa_gui_details,
            "_jump_to_ssa",
            wraps=ssa_gui_details._jump_to_ssa,
        ) as jump_to_ssa_mock:
            self.window._clear_derivadas_filter()
            QApplication.processEvents()

        jump_to_ssa_mock.assert_called_once_with(
            self.window, "202500100", _allow_refilter=False
        )
        assert "derivada_de" not in self.window._active_column_filters
        assert self.window._last_derivada_origem is None
        assert str(self.window._details_current_ssa) == "202500100"
        assert self.window.search_input.text() == ""
        details_html = str(self.window.details_text.toHtml() or "")
        assert "Origem" in details_html
        assert "Filha B" not in details_html

    def test_graphical_derivadas_context_filter_can_be_undone(self, monkeypatch):
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

            def addSeparator(self):
                return None

            def exec(self, _global_pos):
                for action in self._actions:
                    if str(getattr(action, "text", "")).startswith(
                        "Mostrar derivadas"
                    ):
                        action.triggered.emit()
                        return action
                return None

        df = pd.DataFrame(
            {
                "numero_ssa": ["202500100", "202500101", "202500102", "202500200"],
                "situacao": ["APV", "STE", "AMP", "APV"],
                "derivada_de": ["", "202500100", "202500100", ""],
                "localizacao_codigo": ["L0", "L1", "L2", "L3"],
                "descricao_localizacao": ["DL0", "DL1", "DL2", "DL3"],
                "equipamento": ["E0", "E1", "E2", "E3"],
                "semana_cadastro": [202501] * 4,
                "semana_programada": [202503] * 4,
                "data_cadastro": ["2025-01-01"] * 4,
                "descricao_ssa": ["Origem", "Filha A", "Filha B", "Outra"],
                "setor_executor": ["IEE3", "MEL4", "XYZ", "ABC"],
                "setor_emissor": ["ABC", "MEL4", "XYZ", "AAA"],
                "descricao_execucao": ["Exec O", "Exec A", "Exec B", "Exec X"],
                "solicitante": ["User0", "User1", "User2", "User3"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)

        item = next(
            self.window.table_widget.item(0, column)
            for column in range(self.window.table_widget.columnCount())
            if self.window.table_widget.item(0, column) is not None
        )
        pos = self.window.table_widget.visualItemRect(item).center()
        cast(Any, QTest).mouseClick(
            self.window.table_widget.viewport(),
            Qt.MouseButton.RightButton,
            pos=pos,
        )
        self.window.show_context_menu(pos)
        QApplication.processEvents()

        assert self.window._active_column_filters["derivada_de"] == "202500100"
        assert self.window._last_filter_state is not None
        assert str(self.window.filters_summary_label.text() or "") == ""
        assert self.window.filters_summary_label.isVisible() is False
        summary_buttons = [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]
        assert "Deriv: 202500100" in summary_buttons
        assert self.window._get_visual_filter_columns() == {"derivada_de"}
        assert self.window.df_exibido["numero_ssa"].tolist() == [
            "202500102",
            "202500101",
        ]

        cast(Any, QTest).mouseClick(
            self.window.undo_filter_btn,
            Qt.MouseButton.LeftButton,
        )
        QApplication.processEvents()

        assert (
            str(self.window._active_column_filters.get("derivada_de", "")).strip()
            == ""
        )
        assert "Nenhum filtro ativo" in str(
            self.window.filters_summary_label.text() or ""
        )
        assert self.window._get_visual_filter_columns() == set()
        assert set(self.window.df_exibido["numero_ssa"].tolist()) == set(
            df["numero_ssa"].tolist()
        )

    def test_table_context_menu_opens_details_for_right_clicked_ssa(self, monkeypatch):
        opened: list[tuple[str, Any]] = []

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

            def addSeparator(self):
                return None

            def exec(self, _global_pos):
                for action in self._actions:
                    if str(getattr(action, "text", "")) == "Abrir detalhes da SSA":
                        action.triggered.emit()
                        return action
                return None

        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)
        monkeypatch.setattr(
            self.window,
            "_open_details_dialog_for_ssa",
            lambda numero_ssa, series=None: opened.append((numero_ssa, series)),
        )

        item = next(
            self.window.table_widget.item(0, column)
            for column in range(self.window.table_widget.columnCount())
            if self.window.table_widget.item(0, column) is not None
        )
        pos = self.window.table_widget.visualItemRect(item).center()

        self.window.show_context_menu(pos)
        QApplication.processEvents()

        assert opened
        assert opened[0][0] == str(self.window.df_exibido.iloc[0]["numero_ssa"])
        assert opened[0][1] is not None

    def test_table_context_menu_ignores_invalid_ssa_for_details_and_derivadas(
        self, monkeypatch
    ):
        action_texts: list[str] = []

        class _FakeSignal:
            def connect(self, _callback):
                return None

        class _FakeAction:
            def __init__(self, text, _parent=None):
                self.text = text
                self.triggered = _FakeSignal()

        class _FakeMenu:
            def __init__(self, _parent=None):
                self._actions = []

            def addAction(self, action):
                self._actions.append(action)
                action_texts.append(str(getattr(action, "text", "")))
                return action

            def addSeparator(self):
                return None

            def exec(self, _global_pos):
                return None

        monkeypatch.setattr(gui_ssa, "QAction", _FakeAction)
        monkeypatch.setattr(gui_ssa, "QMenu", _FakeMenu)
        monkeypatch.setattr(
            self.window,
            "_get_series_from_row",
            lambda _row: pd.Series({"numero_ssa": float("nan"), "derivada_de": None}),
        )

        item = next(
            self.window.table_widget.item(0, column)
            for column in range(self.window.table_widget.columnCount())
            if self.window.table_widget.item(0, column) is not None
        )
        pos = self.window.table_widget.visualItemRect(item).center()

        self.window.show_context_menu(pos)
        QApplication.processEvents()

        assert "Abrir detalhes da SSA" not in action_texts
        assert "Mostrar derivadas" not in action_texts
        assert "Ir para SSA origem" not in action_texts

    def test_header_resize_updates_runtime_column_width_cache(self):
        self.window._current_display_columns = ["#", "descricao_ssa"]
        self.window._saved_gui_column_widths = {}
        self.window._gui_column_pixel_widths = {}

        self.window._on_header_section_resized(1, 100, 222)

        assert self.window._saved_gui_column_widths.get("descricao_ssa") == 222
        assert self.window._gui_column_pixel_widths.get("descricao_ssa") == 222

    def test_header_resize_schedules_adaptive_header_refresh(self, monkeypatch):
        self.window._current_display_columns = ["#", "descricao_ssa"]
        self.window._saved_gui_column_widths = {}
        self.window._gui_column_pixel_widths = {}

        captured = {"called": False}

        def _fake_schedule(window):
            assert window is self.window
            captured["called"] = True

        monkeypatch.setattr(
            ssa_gui_table,
            "_schedule_adaptive_header_label_refresh",
            _fake_schedule,
        )

        self.window._on_header_section_resized(1, 100, 222)

        assert captured["called"] is True

    def test_header_resize_reapplies_adaptive_label_after_debounce(self, monkeypatch):
        monkeypatch.setattr(
            ssa_gui_table,
            "_measure_header_text_px",
            lambda _window, text: len(str(text or "")) * 8,
        )
        self.window._adaptive_header_label_width_cache = {}
        self.window._adaptive_header_label_signatures = {}
        self.window._saved_gui_column_widths["numero_ssa"] = 50
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("numero_ssa")
        self.window.table_widget.setColumnWidth(logical_index, 140)
        self.window._on_header_section_resized(logical_index, 50, 140)
        time.sleep(0.32)
        QApplication.processEvents()

        header_text = str(
            self.window.table_widget.horizontalHeaderItem(logical_index).text() or ""
        )
        assert header_text == "Numero da SSA"

    def test_header_resize_uses_logical_column_snapshot_during_reorder(
        self, monkeypatch
    ):
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window._current_display_columns = ["#", "numero_ssa", "situacao"]
        self.window.table_widget.setColumnCount(len(self.window._current_display_columns))
        logical_index = self.window._current_display_columns.index("numero_ssa")
        self.window._saved_gui_column_widths = {}
        self.window._gui_column_pixel_widths = {}
        monkeypatch.setattr(
            ssa_gui_table,
            "_schedule_adaptive_header_label_refresh",
            lambda _window: None,
        )
        monkeypatch.setattr(
            ssa_gui_table,
            "_schedule_column_width_preferences_persist",
            lambda _window: None,
        )

        self.window._on_header_section_resized(logical_index, 100, 222)

        assert self.window._saved_gui_column_widths.get("numero_ssa") == 222
        assert self.window._gui_column_pixel_widths.get("numero_ssa") == 222
        assert "situacao" not in self.window._saved_gui_column_widths

    def test_header_resize_reload_uses_correct_column_after_persisted_reorder(
        self, monkeypatch
    ):
        persisted_display = ["situacao"] + [
            col for col in self.window.visible_columns if col != "situacao"
        ]
        persisted_hidden = [
            col
            for col in self._gui_main_preferences_snapshot.get("hidden_columns", [])
            if col not in persisted_display
        ]
        gui_ssa.GUI_MAIN_PREFERENCES["display_columns"] = list(persisted_display)
        gui_ssa.GUI_MAIN_PREFERENCES["hidden_columns"] = list(persisted_hidden)

        reloaded_window = SSAMainWindow()
        reloaded_window.show()
        try:
            reloaded_window.display_current_page(1)
            QApplication.processEvents()
            reloaded_window._saved_gui_column_widths = {}
            reloaded_window._gui_column_pixel_widths = {}
            monkeypatch.setattr(
                ssa_gui_table,
                "_schedule_adaptive_header_label_refresh",
                lambda _window: None,
            )
            monkeypatch.setattr(
                ssa_gui_table,
                "_schedule_column_width_preferences_persist",
                lambda _window: None,
            )

            situacao_logical_index = reloaded_window._current_display_columns.index(
                "situacao"
            )
            reloaded_window._on_header_section_resized(situacao_logical_index, 100, 240)

            assert reloaded_window._saved_gui_column_widths.get("situacao") == 240
            assert reloaded_window._gui_column_pixel_widths.get("situacao") == 240
        finally:
            reloaded_window.close()

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
        logical_index = self.window._current_display_columns.index("situacao")
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

    def test_prompt_column_filter_term_returns_none_when_dialog_unavailable(
        self, monkeypatch
    ):
        monkeypatch.setattr(gui_ssa, "QT_AVAILABLE", False)
        assert self.window._prompt_column_filter_term("Situacao", "STE") is None

    def test_prompt_column_filter_term_returns_none_on_dialog_exception(
        self, monkeypatch
    ):
        class _DialogExplode:
            def __init__(self, *_args, **_kwargs):
                raise RuntimeError("dialog crash")

        monkeypatch.setattr(gui_ssa, "QT_AVAILABLE", True)
        monkeypatch.setattr(gui_ssa, "ColumnFilterDialog", _DialogExplode)
        assert self.window._prompt_column_filter_term("Situacao", "STE") is None

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
        logical_index = self.window._current_display_columns.index("numero_ssa")
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
        logical_index = self.window._current_display_columns.index("numero_ssa")
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

    def test_column_filter_dialog_positions_inside_parent_screen(self, monkeypatch):
        parent = QtWidgets.QWidget()
        parent.setGeometry(1180, 120, 420, 280)
        dialog = ColumnFilterDialog("Solicitante", parent=parent)

        class _FakeScreen:
            def availableGeometry(self):
                return QRect(1000, 40, 900, 700)

        monkeypatch.setattr(
            dialog,
            "_target_screen_geometry",
            lambda: _FakeScreen().availableGeometry(),
        )
        captured = {}
        monkeypatch.setattr(
            dialog,
            "move",
            lambda x, y: captured.update({"x": int(x), "y": int(y)}),
        )

        dialog._position_on_parent_screen()

        assert 1000 <= captured["x"] <= 1900
        assert 40 <= captured["y"] <= 740

    def test_column_manager_dialog_survives_list_widget_setup_failure(self, monkeypatch):
        original_set_alternating = QtWidgets.QListWidget.setAlternatingRowColors

        def _explode(_self, _value):
            raise RuntimeError("forced list config failure")

        monkeypatch.setattr(
            QtWidgets.QListWidget, "setAlternatingRowColors", _explode
        )
        dialog = ColumnManagerDialog(
            {"numero_ssa": "Numero SSA"},
            ["numero_ssa"],
            default_columns=["numero_ssa"],
        )

        assert dialog.list_widget.count() == 1

        monkeypatch.setattr(
            QtWidgets.QListWidget,
            "setAlternatingRowColors",
            original_set_alternating,
        )

    def test_multiselect_menu_uses_widget_screen_geometry(self, monkeypatch):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def emit(self):
                for callback in list(self._callbacks):
                    callback()

        class _FakeRect:
            def bottomLeft(self):
                return QPoint(0, 20)

            def topLeft(self):
                return QPoint(0, 0)

            def center(self):
                return QPoint(40, 10)

        class _FakeButton:
            def __init__(self):
                self.clicked = _FakeSignal()

            def rect(self):
                return _FakeRect()

            def mapToGlobal(self, point):
                return QPoint(1770 + point.x(), 730 + point.y())

            def window(self):
                return self

            def windowHandle(self):
                return None

        class _FakeMenu:
            def sizeHint(self):
                return QSize(260, 220)

            def exec(self, pos):
                captured["pos"] = pos

        class _FakeOwner:
            def _run_menu_pre_show_hook(self, _button):
                return None

        captured = {}
        monkeypatch.setattr(advanced_menu, "_is_not_deleted", lambda _widget: True)
        monkeypatch.setattr(
            advanced_menu,
            "_get_widget_screen_geometry",
            lambda _widget: QRect(1000, 40, 900, 700),
        )

        button = _FakeButton()
        menu = _FakeMenu()
        advanced_menu._attach_multiselect_menu(_FakeOwner(), button, menu)
        button.clicked.emit()

        assert captured["pos"].x() >= 1000
        assert captured["pos"].y() >= 40

    def test_multiselect_menu_limits_high_cardinality_items(self):
        button = QPushButton("Selecionar")
        menu = QtWidgets.QMenu()
        values = [f"Resp {idx:04d}" for idx in range(450)]

        checks, exclude_checks = advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            values,
            {"Resp 0449"},
            None,
            True,
            {"Resp 0448"},
            None,
        )

        include_values = [str(check.property("value") or "") for check in checks]
        exclude_values = [str(check.property("value") or "") for check in exclude_checks]
        assert len(checks) == advanced_menu.HIGH_CARDINALITY_MENU_LIMIT
        assert "Resp 0449" in include_values
        assert "Resp 0448" in exclude_values

    def test_multiselect_menu_selection_labels_use_short_copy(self):
        button = QPushButton("Responsavel")
        button.setProperty("filter_name", "Responsavel")
        button.setProperty("multiselect_popup_kind", "long")
        menu = QtWidgets.QMenu()

        advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            ["Resp A"],
            set(),
            None,
            True,
            set(),
            None,
        )

        header_widget = cast(Any, menu.actions()[0]).defaultWidget()
        assert header_widget is not None
        assert not isinstance(header_widget, QScrollArea)
        header_labels = [
            label.text() for label in header_widget.findChildren(QLabel)
        ]
        assert header_labels[:3] == ["Responsavel", "Incluir", "Excluir"]
        header_labels_by_text = {
            str(label.text() or ""): label
            for label in header_widget.findChildren(QLabel)
        }
        include_label = header_labels_by_text["Incluir"]
        exclude_label = header_labels_by_text["Excluir"]
        assert "font-size: 11px" in str(include_label.styleSheet() or "")
        assert "border" not in str(include_label.styleSheet() or "")
        assert "border" not in str(exclude_label.styleSheet() or "")

        scroll_widget = cast(Any, menu.actions()[1]).defaultWidget()
        assert isinstance(scroll_widget, QScrollArea)
        first_widget = scroll_widget.widget()
        assert first_widget is not None
        first_labels = [
            label.text() for label in first_widget.findChildren(QLabel)
        ]
        assert "Responsavel" not in first_labels
        assert "Incluir" not in first_labels[:2]
        assert "Excluir" not in first_labels[:2]

        labels = []
        tooltips = []
        accessible_names = []
        for action in menu.actions():
            widget = cast(Any, action).defaultWidget()
            if widget is None:
                continue
            labels.extend(label.text() for label in widget.findChildren(QLabel))
            for child_button in widget.findChildren(QPushButton):
                tooltips.append(child_button.toolTip())
                accessible_names.append(child_button.accessibleName())

        assert "Incluir" in labels
        assert "Excluir" in labels
        assert "Selecionar tudo" in labels
        assert "Limpar tudo" in labels
        assert "Conter" not in labels
        assert "Nao conter" not in labels
        assert "Selecionar em lote" not in labels
        assert "Limpar selecao em lote" not in labels
        assert "Selecionar tudo para incluir" in tooltips
        assert "Limpar tudo para incluir" in tooltips
        assert "Selecionar tudo para excluir" in accessible_names
        assert "Limpar tudo para excluir" in accessible_names

    def test_multiselect_sector_popup_is_compact_and_header_columns_align(self):
        button = QPushButton("Selecionar")
        button.setProperty("filter_name", "Emissor")
        button.setProperty("multiselect_popup_kind", "sector")
        menu = QtWidgets.QMenu()
        values = ["IEE3", "IEE1", "IEE2", "IEE4", "MEL1", "MEL2", "MEL3", "MEL4"]

        advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            values,
            set(),
            None,
            True,
            set(),
            None,
        )

        assert 220 <= int(menu.minimumWidth()) <= 300
        header_widget = cast(Any, menu.actions()[0]).defaultWidget()
        assert header_widget is not None
        header_layout = header_widget.layout()
        header_labels = {
            str(label.text() or ""): label
            for label in header_widget.findChildren(QLabel)
        }
        assert int(header_labels["Incluir"].minimumWidth()) == int(
            header_layout.columnMinimumWidth(1)
        )
        assert int(header_labels["Excluir"].minimumWidth()) == int(
            header_layout.columnMinimumWidth(2)
        )
        assert "border" not in str(header_labels["Incluir"].styleSheet() or "")
        assert "border" not in str(header_labels["Excluir"].styleSheet() or "")

        scroll_widget = cast(Any, menu.actions()[1]).defaultWidget()
        assert isinstance(scroll_widget, QScrollArea)
        first_widget = scroll_widget.widget()
        assert first_widget is not None
        layout = first_widget.layout()
        assert int(header_layout.columnMinimumWidth(1)) == int(
            layout.columnMinimumWidth(1)
        )
        assert int(header_layout.columnMinimumWidth(2)) == int(
            layout.columnMinimumWidth(2)
        )
        _, _, header_right_margin, _ = header_layout.getContentsMargins()
        _, _, scroll_right_margin, _ = layout.getContentsMargins()
        scrollbar_width = int(scroll_widget.verticalScrollBar().sizeHint().width())
        assert int(header_right_margin) == int(
            scroll_right_margin + scrollbar_width
        )

    def test_multiselect_batch_select_all_syncs_opposite_column_callback(self):
        button = QPushButton("Selecionar")
        button.setProperty("filter_name", "Responsavel Execucao")
        button.setProperty("multiselect_popup_kind", "long")
        menu = QtWidgets.QMenu()
        include_events = []
        exclude_events = []

        checks, exclude_checks = advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            ["Resp A", "Resp B"],
            set(),
            lambda: include_events.append("include"),
            True,
            {"Resp A"},
            lambda: exclude_events.append("exclude"),
        )

        scroll_widget = cast(Any, menu.actions()[1]).defaultWidget()
        content = scroll_widget.widget()
        buttons = {
            str(child.accessibleName() or ""): child
            for child in content.findChildren(QPushButton)
        }

        buttons["Selecionar tudo para incluir"].click()
        assert include_events == ["include"]
        assert exclude_events == ["exclude"]
        assert all(check.isChecked() for check in checks)
        assert all(not check.isChecked() for check in exclude_checks)

        buttons["Selecionar tudo para excluir"].click()
        assert include_events == ["include", "include"]
        assert exclude_events == ["exclude", "exclude"]
        assert all(not check.isChecked() for check in checks)
        assert all(check.isChecked() for check in exclude_checks)

    def test_multiselect_responsavel_popup_caps_width_and_height(self):
        button = QPushButton("Selecionar")
        button.setProperty("filter_name", "Responsavel Execucao")
        button.setProperty("multiselect_popup_kind", "long")
        menu = QtWidgets.QMenu()
        values = [
            f"IEE1 - RESPONSAVEL COM NOME MUITO LONGO PARA TESTE {idx:03d}"
            for idx in range(200)
        ]

        advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            values,
            set(),
            None,
            True,
            set(),
            None,
        )

        assert int(menu.maximumWidth()) <= 390
        scroll_widget = cast(Any, menu.actions()[1]).defaultWidget()
        assert isinstance(scroll_widget, QScrollArea)
        assert int(scroll_widget.maximumHeight()) <= 160
        labels = [
            label
            for label in scroll_widget.widget().findChildren(QLabel)
            if "RESPONSAVEL COM NOME" in str(label.toolTip() or "")
        ]
        assert labels
        assert all(str(label.text() or "") != str(label.toolTip() or "") for label in labels)

    def test_multiselect_derivadas_popup_uses_short_scroll_height(self):
        button = QPushButton("Selecionar")
        button.setProperty("filter_name", "Derivadas")
        button.setProperty("multiselect_popup_kind", "simple")
        menu = QtWidgets.QMenu()

        advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            [
                ("has", "Possui Derivadas"),
                ("all_ste", "Derivadas em STE/SES"),
                ("is", "Sou Derivada"),
            ],
            set(),
            None,
            False,
            None,
            None,
        )

        scroll_widget = cast(Any, menu.actions()[1]).defaultWidget()
        assert isinstance(scroll_widget, QScrollArea)
        assert int(scroll_widget.maximumHeight()) <= 90

    def test_multiselect_menu_reuses_cached_widgets_when_model_is_unchanged(self):
        button = QPushButton("Selecionar")
        menu = QtWidgets.QMenu()
        values = ["Resp A", "Resp B", "Resp C"]

        first_checks, first_exclude_checks = advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            values,
            {"Resp A"},
            None,
            True,
            {"Resp B"},
            None,
        )
        first_action_count = len(menu.actions())
        second_checks, second_exclude_checks = advanced_menu._rebuild_multiselect_menu(
            self.window,
            button,
            menu,
            values,
            {"Resp A"},
            None,
            True,
            {"Resp B"},
            None,
        )

        assert second_checks == first_checks
        assert second_exclude_checks == first_exclude_checks
        assert len(menu.actions()) == first_action_count

    def test_show_all_columns_by_affinity_reorders_same_select_all_set(
        self, monkeypatch
    ):
        source = ["data_programacao", "descricao_execucao", "numero_ssa"]
        captured = {}
        monkeypatch.setattr(
            self.window, "_get_select_all_columns_from_selector", source.copy
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

    def test_header_real_click_sorts_numero_ssa_asc_then_desc(self):
        click_df = self.base_df.copy()
        click_df["numero_ssa"] = [3, 1, 2, 5, 4]
        self.window.df_completo = click_df.copy()
        self.window.df_exibido = click_df.copy()
        self.window._df_last_search_filtered = click_df.copy()
        self.window.paginator.set_dataframe(click_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("numero_ssa")
        header = self.window.table_widget.horizontalHeader()
        click_pos = QPoint(
            header.sectionViewportPosition(logical_index)
            + max(5, header.sectionSize(logical_index) // 2),
            max(5, header.height() // 2),
        )

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            click_pos,
        )
        QApplication.processEvents()
        assert self.window.df_exibido["numero_ssa"].tolist() == [1, 2, 3, 4, 5]

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            click_pos,
        )
        QApplication.processEvents()
        assert self.window.df_exibido["numero_ssa"].tolist() == [5, 4, 3, 2, 1]

    def test_header_real_click_sorts_visual_column_after_reorder(self):
        click_df = self.base_df.copy()
        click_df["numero_ssa"] = [30, 10, 20, 50, 40]
        click_df["situacao"] = ["C", "A", "B", "E", "D"]
        self.window.df_completo = click_df.copy()
        self.window.df_exibido = click_df.copy()
        self.window._df_last_search_filtered = click_df.copy()
        self.window.paginator.set_dataframe(click_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        header = self.window.table_widget.horizontalHeader()
        initial_situacao_index = self.window._current_display_columns.index("situacao")
        header.moveSection(header.visualIndex(initial_situacao_index), 1)
        QApplication.processEvents()

        situacao_index = self.window._current_display_columns.index("situacao")
        click_pos = QPoint(
            header.sectionViewportPosition(situacao_index)
            + max(5, header.sectionSize(situacao_index) // 2),
            max(5, header.height() // 2),
        )

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            click_pos,
        )
        QApplication.processEvents()

        assert self.window.sort_column == "situacao"
        assert self.window.df_exibido["situacao"].tolist() == ["A", "B", "C", "D", "E"]

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            click_pos,
        )
        QApplication.processEvents()

        assert self.window.sort_column == "situacao"
        assert self.window.df_exibido["situacao"].tolist() == ["E", "D", "C", "B", "A"]

    def test_header_real_click_resets_sort_direction_when_switching_columns(self):
        click_df = self.base_df.copy()
        click_df["numero_ssa"] = [5, 1, 4, 2, 3]
        click_df["situacao"] = ["C", "A", "B", "E", "D"]
        self.window.df_completo = click_df.copy()
        self.window.df_exibido = click_df.copy()
        self.window._df_last_search_filtered = click_df.copy()
        self.window.paginator.set_dataframe(click_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        initial_display_columns = list(self.window._current_display_columns)
        header = self.window.table_widget.horizontalHeader()
        numero_index = self.window._current_display_columns.index("numero_ssa")
        situacao_index = self.window._current_display_columns.index("situacao")
        numero_click_pos = QPoint(
            header.sectionViewportPosition(numero_index)
            + max(5, header.sectionSize(numero_index) // 2),
            max(5, header.height() // 2),
        )
        situacao_click_pos = QPoint(
            header.sectionViewportPosition(situacao_index)
            + max(5, header.sectionSize(situacao_index) // 2),
            max(5, header.height() // 2),
        )

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            numero_click_pos,
        )
        QApplication.processEvents()
        assert self.window.sort_column == "numero_ssa"
        assert self.window.sort_ascending is True
        assert self.window.df_exibido["numero_ssa"].tolist() == [1, 2, 3, 4, 5]
        assert header.sortIndicatorSection() == numero_index
        assert header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            numero_click_pos,
        )
        QApplication.processEvents()
        assert self.window.sort_column == "numero_ssa"
        assert self.window.sort_ascending is False
        assert self.window.df_exibido["numero_ssa"].tolist() == [5, 4, 3, 2, 1]
        assert header.sortIndicatorSection() == numero_index
        assert header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder

        cast(Any, QTest).mouseClick(
            header.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            situacao_click_pos,
        )
        QApplication.processEvents()
        assert self.window.sort_column == "situacao"
        assert self.window.sort_ascending is True
        assert self.window.df_exibido["situacao"].tolist() == ["A", "B", "C", "D", "E"]
        assert header.sortIndicatorSection() == situacao_index
        assert header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
        assert list(self.window._current_display_columns) == initial_display_columns

    def test_persisted_reordered_columns_reload_keeps_real_header_sort(self):
        persisted_display = ["situacao"] + [
            col for col in self.window.visible_columns if col != "situacao"
        ]
        persisted_hidden = [
            col
            for col in self._gui_main_preferences_snapshot.get("hidden_columns", [])
            if col not in persisted_display
        ]
        gui_ssa.GUI_MAIN_PREFERENCES["display_columns"] = list(persisted_display)
        gui_ssa.GUI_MAIN_PREFERENCES["hidden_columns"] = list(persisted_hidden)

        reloaded_window = SSAMainWindow()
        reloaded_window.show()
        try:
            click_df = self.base_df.copy()
            click_df["numero_ssa"] = [30000, 10000, 20000, 50000, 40000]
            click_df["situacao"] = ["C", "A", "B", "E", "D"]
            reloaded_window.df_completo = click_df.copy()
            reloaded_window.df_exibido = click_df.copy()
            reloaded_window._df_last_search_filtered = click_df.copy()
            reloaded_window.paginator.set_dataframe(click_df.copy())
            reloaded_window.display_current_page(1)
            QApplication.processEvents()

            assert reloaded_window.visible_columns[:3] == [
                "situacao",
                "numero_ssa",
                "localizacao_codigo",
            ]

            header = reloaded_window.table_widget.horizontalHeader()
            situacao_index = reloaded_window._current_display_columns.index("situacao")
            click_pos = QPoint(
                header.sectionViewportPosition(situacao_index)
                + max(5, header.sectionSize(situacao_index) // 2),
                max(5, header.height() // 2),
            )

            cast(Any, QTest).mouseClick(
                header.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                click_pos,
            )
            QApplication.processEvents()

            assert reloaded_window.sort_column == "situacao"
            assert reloaded_window.df_exibido["situacao"].tolist() == [
                "A",
                "B",
                "C",
                "D",
                "E",
            ]
        finally:
            reloaded_window.close()

    def test_resolve_header_column_name_uses_logical_snapshot_during_reorder(self):
        self.window.display_current_page(1)
        QApplication.processEvents()

        self.window._current_display_columns = ["#", "numero_ssa", "situacao"]
        self.window.table_widget.setColumnCount(len(self.window._current_display_columns))
        logical_index = self.window._current_display_columns.index("numero_ssa")

        resolved = self.window._resolve_header_column_name(logical_index)

        assert resolved == "numero_ssa"

    def test_header_section_moved_updates_runtime_column_snapshot_before_rerender(
        self, monkeypatch
    ):
        self.window._current_display_columns = ["#", "numero_ssa", "situacao"]
        self.window.visible_columns = ["numero_ssa", "situacao"]
        header = self.window.table_widget.horizontalHeader()
        monkeypatch.setattr(header, "visualIndex", lambda idx: 0 if idx == 0 else idx)
        monkeypatch.setattr(self.window, "_capture_current_column_widths", lambda: {})
        monkeypatch.setattr(self.window, "_restore_column_widths", lambda _widths: None)
        monkeypatch.setattr(
            ssa_gui_table,
            "_get_header_visual_column_order",
            lambda _window: ["#", "situacao", "numero_ssa"],
        )

        captured = {}

        def _fake_display_current_page(page_number, *, update_details=True):
            captured["page_number"] = page_number
            captured["snapshot"] = list(self.window._current_display_columns)
            captured["visible_columns"] = list(self.window.visible_columns)

        monkeypatch.setattr(
            self.window, "display_current_page", _fake_display_current_page
        )

        self.window._on_header_section_moved(2, 2, 1)

        assert captured["page_number"] == self.window.paginator.current_page
        assert captured["snapshot"] == ["#", "situacao", "numero_ssa"]
        assert captured["visible_columns"] == ["situacao", "numero_ssa"]

    def test_header_section_moved_keeps_schema_absent_visible_columns(
        self, monkeypatch
    ):
        self.window._current_display_columns = ["#", "numero_ssa", "situacao"]
        self.window.visible_columns = ["numero_ssa", "situacao", "solicitante"]
        header = self.window.table_widget.horizontalHeader()
        monkeypatch.setattr(header, "visualIndex", lambda idx: 0 if idx == 0 else idx)
        monkeypatch.setattr(self.window, "_capture_current_column_widths", lambda: {})
        monkeypatch.setattr(self.window, "_restore_column_widths", lambda _widths: None)
        monkeypatch.setattr(
            ssa_gui_table,
            "_get_header_visual_column_order",
            lambda _window: ["#", "situacao", "numero_ssa"],
        )

        captured = {}

        def _fake_display_current_page(page_number, *, update_details=True):
            captured["page_number"] = page_number
            captured["snapshot"] = list(self.window._current_display_columns)
            captured["visible_columns"] = list(self.window.visible_columns)

        monkeypatch.setattr(
            self.window, "display_current_page", _fake_display_current_page
        )

        self.window._on_header_section_moved(2, 2, 1)

        assert captured["page_number"] == self.window.paginator.current_page
        assert captured["snapshot"] == ["#", "situacao", "numero_ssa"]
        assert captured["visible_columns"] == [
            "situacao",
            "numero_ssa",
            "solicitante",
        ]

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

    def test_best_fit_width_uses_fixed_column_caps(self):
        series = pd.Series(["2027-01-15 07:27:16"] * 50)

        def _measure(value):
            return len(str(value)) * 12

        width = self.window.width_manager.compute_best_fit_width(
            series=series,
            header_text="Data do arquivo de origem",
            col_name="data_arquivo_origem",
            measure_text=_measure,
            baseline_px=None,
            sample_limit=200,
        )
        assert width <= self.window.width_manager.max_pixel_widths[
            "data_arquivo_origem"
        ]

    def test_compute_optimal_widths_keeps_hash_column_minimum_24(self):
        df = pd.DataFrame({"#": [1], "numero_ssa": ["202500001"]})
        widths = self.window.width_manager.compute_optimal_widths(
            df=df,
            available_width=220,
            column_order=["#", "numero_ssa"],
        )
        assert int(widths.get("#", 0)) == 24

    def test_compute_optimal_widths_uses_canonical_defaults_for_fixed_columns(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500001"],
                "situacao": ["APV"],
                "data_cadastro": ["2025-01-01"],
            }
        )
        widths = self.window.width_manager.compute_optimal_widths(
            df=df,
            available_width=600,
            column_order=["numero_ssa", "situacao", "data_cadastro"],
        )
        assert int(widths["numero_ssa"]) == DEFAULT_COLUMN_WIDTHS["numero_ssa"]
        assert int(widths["situacao"]) == DEFAULT_COLUMN_WIDTHS["situacao"]
        assert int(widths["data_cadastro"]) == DEFAULT_COLUMN_WIDTHS["data_cadastro"]

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

    def test_table_render_prefers_saved_gui_width_over_computed_width(
        self, monkeypatch
    ):
        self.window._saved_gui_column_widths["descricao_ssa"] = 222

        def _fake_compute(_df):
            self.window._gui_column_pixel_widths = {"descricao_ssa": 444, "#": 24}

        monkeypatch.setattr(self.window, "_compute_gui_column_widths", _fake_compute)
        self.window._widths_columns_sig = None
        if hasattr(self.window, "_last_viewport_w"):
            delattr(self.window, "_last_viewport_w")

        self.window.display_current_page(1)
        QApplication.processEvents()

        col_idx = self.window._current_display_columns.index("descricao_ssa")
        assert self.window.table_widget.columnWidth(col_idx) == 222

    def test_progress_bar_visibility_does_not_change_window_minimum_width(self):
        before = int(self.window.minimumSizeHint().width())
        self.window.progress_bar.setVisible(True)
        QApplication.processEvents()
        while_busy = int(self.window.minimumSizeHint().width())
        self.window.progress_bar.setVisible(False)
        QApplication.processEvents()
        after = int(self.window.minimumSizeHint().width())

        assert self.window.progress_bar.sizePolicy().retainSizeWhenHidden() is True
        assert self.window.progress_bar.width() == 24
        assert before == while_busy == after

    def test_build_derivadas_tree_html_uses_spaced_header_layout(self):
        with patch(
            "gui.ssa.gui_details._get_series_for_ssa",
            side_effect=lambda _window, numero: object()
            if str(numero) in {"202602147", "202500111"}
            else None,
        ):
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
                html = ssa_gui_details._build_derivadas_tree_html(
                    self.window, "202602147"
                )

        assert "Derivadas:" in html
        assert '<a href="ssa-context:202602147"' in html
        assert "202500111" in html
        assert "num0" not in html
        assert "&gt;" not in html
        assert "dist=" not in html
        assert "&#8942;" in html
        assert "Sem Derivadas" in html

    def test_derivadas_context_back_and_close_use_internal_tabs(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154", "202100155"],
                "situacao": ["APV", "STE", "SCA"],
                "derivada_de": ["", "202100046", "202100154"],
                "descricao_ssa": ["Pai", "Filha", "Neta"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        ssa_gui_details._open_derivadas_context_panel(self.window, "202100154")
        ssa_gui_details._open_derivadas_context_panel(
            self.window,
            "202100155",
            source_ssa="202100154",
        )
        QApplication.processEvents()

        context_state = getattr(self.window, "_details_context_state", None)
        assert isinstance(context_state, dict)
        assert context_state["tab_bar"].count() == 2
        assert str(context_state.get("current_ssa") or "") == "202100155"

        cast(Any, QTest).mouseClick(
            context_state["close_button"],
            Qt.MouseButton.LeftButton,
        )
        QApplication.processEvents()

        assert context_state["tab_bar"].count() == 1
        assert str(context_state.get("current_ssa") or "") == "202100154"

        cast(Any, QTest).mouseClick(
            context_state["back_button"],
            Qt.MouseButton.LeftButton,
        )
        QApplication.processEvents()

        ctx = self._panel_context()
        assert ctx["details_stack"].currentIndex() == 1

    def test_derivadas_context_graph_click_opens_details_without_nested_context(
        self,
    ):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202100046", "202100154", "202100155"],
                "situacao": ["APV", "STE", "SCA"],
                "derivada_de": ["", "202100046", "202100154"],
                "descricao_ssa": ["Pai", "Filha", "Neta"],
            }
        )
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        ssa_gui_details._open_derivadas_context_panel(self.window, "202100154")
        QApplication.processEvents()

        context_state = getattr(self.window, "_details_context_state", None)
        assert isinstance(context_state, dict)
        graph_label = context_state["graph_label"]
        graph_label.setFixedSize(200, 120)
        graph_label.set_ssa_hitboxes([("202100155", 10.0, 10.0, 90.0, 50.0)])

        with (
            patch("gui.ssa.gui_details._open_details_dialog_for_ssa") as details_mock,
            patch.object(
                self.window,
                "_jump_to_ssa",
                wraps=self.window._jump_to_ssa,
            ) as jump_mock,
            patch("gui.ssa.gui_details._open_derivadas_context_panel") as open_mock,
        ):
            cast(Any, QTest).mouseClick(
                graph_label,
                Qt.MouseButton.LeftButton,
                pos=QPoint(20, 20),
            )
            QApplication.processEvents()

        details_mock.assert_called_once_with(self.window, "202100155")
        jump_mock.assert_not_called()
        open_mock.assert_not_called()
        live_context_state = getattr(self.window, "_details_context_state", None)
        assert isinstance(live_context_state, dict)
        assert str(live_context_state.get("current_ssa") or "") == "202100154"

    def test_open_details_dialog_does_not_build_full_ssa_index_before_render(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202218980", "202218786", "202218787"],
                "descricao_ssa": ["Alvo", "Filha A", "Filha B"],
                "derivada_de": ["", "202218980", "202218980"],
                "situacao": ["APV", "STE", "SCA"],
            }
        )
        self.window.df_completo = df
        self.window.df_exibido = df
        self.window.df_para_tabela = df

        with patch(
            "gui.ssa.gui_details._get_df_ssa_series_index",
            side_effect=AssertionError("full index should not be built on open"),
        ), patch("PyQt6.QtWidgets.QDialog.show", lambda dialog: dialog.close()):
            ssa_gui_details._open_details_dialog_for_ssa(
                self.window,
                "202218980",
                series=df.iloc[0],
            )

    def test_derivadas_tree_html_does_not_scan_dataframe_per_node(self, monkeypatch):
        node_ids = ["202206235", *[f"202206{i:03d}" for i in range(100, 180)]]
        self.window.df_completo = pd.DataFrame(
            {
                "numero_ssa": node_ids,
                "situacao": ["APV", *["STE" for _ in node_ids[1:]]],
                "derivada_de": ["", *["202206235" for _ in node_ids[1:]]],
            }
        )
        self.window.df_exibido = self.window.df_completo.iloc[:1].copy()
        tree_data = {
            "target": "202206235",
            "parents": [],
            "children": [{"ssa": node_ids[1], "parent": "202206235"}],
            "descendants": [
                {"ssa": child, "parent": "202206235", "min_distance": 1}
                for child in node_ids[1:]
            ],
            "ancestors": [],
            "family_roots": ["202206235"],
            "target_status": "",
            "direct_children_count": len(node_ids) - 1,
            "descendants_count": len(node_ids) - 1,
            "render_family": True,
        }

        def _fail_per_node_scan(_window, numero_ssa):
            raise AssertionError(f"per-node dataframe scan for {numero_ssa}")

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_series_for_ssa",
            _fail_per_node_scan,
        )

        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202206235",
            tree_data_override=tree_data,
            ssa_index={},
        )

        assert "202206235" in html
        assert "202206100" in html

    def test_derivadas_tree_html_default_path_does_not_build_full_ssa_index(
        self, monkeypatch
    ):
        self.window.df_completo = pd.DataFrame(
            {
                "numero_ssa": ["202218980", "202218786", "202218787"],
                "descricao_ssa": ["Alvo", "Filha A", "Filha B"],
                "derivada_de": ["", "202218980", "202218980"],
                "situacao": ["APV", "STE", "SCA"],
            }
        )
        self.window.df_exibido = self.window.df_completo.iloc[:1].copy()
        tree_data = {
            "target": "202218980",
            "parents": [],
            "children": [
                {"ssa": "202218786", "parent": "202218980", "situacao": "STE"},
                {"ssa": "202218787", "parent": "202218980", "situacao": "SCA"},
            ],
            "descendants": [
                {"ssa": "202218786", "parent": "202218980", "situacao": "STE"},
                {"ssa": "202218787", "parent": "202218980", "situacao": "SCA"},
            ],
            "ancestors": [],
            "family_roots": ["202218980"],
            "target_status": "APV",
            "direct_children_count": 2,
            "descendants_count": 2,
            "render_family": True,
            "related": [],
        }

        monkeypatch.setattr(
            ssa_gui_details,
            "_get_window_ssa_series_index",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("full index should not be built")
            ),
        )

        html = ssa_gui_details._build_derivadas_tree_html(
            self.window,
            "202218980",
            tree_data_override=tree_data,
        )

        assert "202218980" in html
        assert "202218786" in html
        assert "202218787" in html

    def test_exclude_toggle_syncs_checkbox_state_across_tabs(self):
        """Toggle programático deve manter estado interno e checkboxes em sincronia."""
        self.window._on_exclude_ste_sca_toggled(True)
        QApplication.processEvents()
        assert self.window._exclude_ste_sca is True
        for ctx in self._iter_panel_contexts():
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                assert checkbox.isChecked() is True

        self.window._on_exclude_ste_sca_toggled(False)
        QApplication.processEvents()
        assert self.window._exclude_ste_sca is False
        for ctx in self._iter_panel_contexts():
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
        for ctx in self._iter_panel_contexts():
            checkbox = ctx.get("exclude_ste_checkbox")
            if checkbox is not None:
                checkbox.setChecked(True)

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window._exclude_ste_sca is False
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        for ctx in self._iter_panel_contexts():
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

        for ctx in self._iter_panel_contexts():
            assert ctx["search_input"].text().strip() == ""
        assert all(
            not str(v).strip() for v in self.window._active_column_filters.values()
        )
        assert self.window._exclude_ste_sca is False
        assert self.window._advanced_filters == {}
        assert self.window._advanced_filters_active is False
        assert Counter(self._extract_visible_ssa()) == Counter([1, 2, 3, 4, 5])
        assert self.window.clear_filter_button.isEnabled() is False

    def test_clear_all_filters_global_reuses_df_completo_reference(self):
        self.window.search_input.setText("Teste A")
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        self.window._clear_all_filters_global()
        QApplication.processEvents()

        assert self.window.df_exibido is self.window.df_completo

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
        for ctx in self._iter_panel_contexts():
            if not isinstance(ctx, dict):
                continue
            assert ctx["search_input"].text() == ""
            selector = ctx.get("profile_selector")
            if selector is not None:
                assert selector.currentIndex() == 0

    def test_hard_reset_filters_state_reuses_df_completo_reference(self):
        self.window.search_input.setText("Teste A")
        self.window._refresh_after_filter_change()
        QApplication.processEvents()

        self.window._hard_reset_filters_state()
        QApplication.processEvents()

        assert self.window.df_exibido is self.window.df_completo

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

        assert mae_filhas == {"100": ["102"]}
        assert filha_mae == {"102": "100"}

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
        assert "Relacoes de derivadas atualizadas" in self.window.status_label.text()

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
        assert "Relacoes de derivadas atualizadas" in self.window.status_label.text()

    def test_update_derivadas_from_sources_rejects_second_start_before_preparation(
        self, monkeypatch, tmp_path
    ):
        db_file = tmp_path / "ssas.db"
        db_file.write_bytes(b"sqlite-placeholder")

        monkeypatch.setattr(gui_ssa, "DB_PATH", str(db_file))
        self.window._derivadas_sync_running = True
        self.window._derivadas_sync_table_name = "ssa_table"

        def _should_not_prepare():
            raise AssertionError("running guard must happen before job preparation")

        monkeypatch.setattr(
            self.window,
            "_list_special_derivadas_sheets",
            _should_not_prepare,
        )

        result = self.window.update_derivadas_from_sources()

        assert result == {
            "ok": False,
            "reason": "already_running",
            "db_path": str(db_file),
            "table_name": "ssa_table",
        }
        assert "ja em andamento" in self.window.status_label.text()

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
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(1501)
        self.window._reorganize_advanced_filters_grid(1201)
        self.window._reorganize_advanced_filters_grid(800)
        assert self.window._advanced_filter_panel_state.main_grid.count() > 0

    def test_reorganize_advanced_filters_grid_allows_single_column_width(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(90)
        state = self.window._advanced_filter_panel_state
        assert state.layout_mode == "cols_1"

        grid = state.main_grid
        widgets = state.grid_widgets
        exec_resp_item = grid.itemAtPosition(14, 0)
        assert exec_resp_item is not None
        assert exec_resp_item.widget() is widgets["exec_resp_box"]

    def test_advanced_grid_layout_plan_is_calculated_outside_qt_application(self):
        plan = advanced_layout.build_advanced_grid_layout_plan(
            visible_count=14,
            metrics=advanced_layout.AdvancedGridLayoutMetrics(
                effective_width=900,
                cell_min_width=190,
                spacing=6,
                horizontal_padding=12,
                vertical_spacing=4,
                vertical_padding=8,
            ),
            constraints=advanced_layout.AdvancedGridLayoutConstraints(
                min_cols=1,
                max_cols=4,
                preferred_cols=4,
                field_box_min_height=40,
                field_box_max_height=50,
                max_scroll_height=230,
            ),
        )

        assert plan is not None
        assert plan.cols == 4
        assert plan.layout_mode == "cols_4"

    def test_reorganize_advanced_filters_grid_ignores_non_positive_width_and_recomputes(
        self,
    ):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._reorganize_advanced_filters_grid(1501)
        state = self.window._advanced_filter_panel_state
        assert str(state.layout_mode).startswith("cols_")
        previous_mode = state.layout_mode

        self.window._reorganize_advanced_filters_grid(0)
        assert state.layout_mode == previous_mode

        self.window._reorganize_advanced_filters_grid(800)
        assert state.layout_mode in {"cols_2", "cols_3", "cols_4"}

    def test_reorganize_advanced_filters_grid_increases_spacing_and_caps_wide_cells(
        self,
    ):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window.resize(980, 760)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(980)
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        grid = state.main_grid
        narrow_hspace = int(grid.horizontalSpacing())
        narrow_vspace = int(grid.verticalSpacing())
        narrow_emis = state.grid_widgets["emis_box"].geometry()
        narrow_exec = state.grid_widgets["exec_box"].geometry()
        narrow_gap = int(narrow_exec.x() - (narrow_emis.x() + narrow_emis.width()))

        self.window.resize(1680, 900)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(1680)
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        grid = state.main_grid
        wide_hspace = int(grid.horizontalSpacing())
        wide_vspace = int(grid.verticalSpacing())
        wide_emis = state.grid_widgets["emis_box"].geometry()
        wide_exec = state.grid_widgets["exec_box"].geometry()
        wide_gap = int(wide_exec.x() - (wide_emis.x() + wide_emis.width()))

        assert wide_hspace >= narrow_hspace
        assert wide_vspace >= narrow_vspace
        assert wide_hspace >= 12
        assert wide_vspace >= 4
        assert wide_gap >= narrow_gap
        assert int(state.grid_widgets["macro_box"].maximumWidth()) <= 300
        assert "action_box" not in state.grid_widgets

    def test_reorganize_advanced_filters_grid_keeps_wide_layout_text_uncropped(self):
        self._set_filter_panel_tab("filters")
        self.window.resize(1680, 900)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(1680)
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        grid = state.main_grid
        scroll = state.controls_scroll
        viewport_height = scroll.viewport().height()
        adv_group_height = int(self.window.adv_filters_group.height())

        assert int(grid.verticalSpacing()) >= 4
        assert scroll.verticalScrollBar().maximum() == 0
        expected_scroll_min = max(80, adv_group_height - 4)
        expected_scroll_max = adv_group_height
        assert expected_scroll_max >= expected_scroll_min
        assert expected_scroll_min <= scroll.height() <= expected_scroll_max
        assert "action_box" not in state.grid_widgets
        for widget in state.grid_widgets.values():
            if widget is None or not widget.isVisible():
                continue
            assert (
                advanced_layout.LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT
                <= widget.height()
                <= widget.maximumHeight()
            )
            contents_top = int(widget.contentsRect().top())
            min_child_top = contents_top + 2
            contents_bottom = int(widget.contentsRect().bottom()) + 1
            for child in widget.findChildren(
                QtWidgets.QWidget,
                options=Qt.FindChildOption.FindDirectChildrenOnly,
            ):
                if child.isVisible():
                    assert int(child.geometry().y()) >= min_child_top
                    assert int(child.geometry().bottom()) <= contents_bottom
            assert widget.geometry().y() + widget.geometry().height() <= viewport_height - 4
        for key in ("prog_box", "exec_resp_box"):
            widget = state.grid_widgets[key]
            direct_child_heights = [
                int(child.height())
                for child in widget.findChildren(
                    QtWidgets.QWidget,
                    options=Qt.FindChildOption.FindDirectChildrenOnly,
                )
                if child.isVisible()
            ]
            control_height = max(direct_child_heights, default=0)
            assert widget.height() <= advanced_layout.LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT + 8
            assert widget.height() >= int(widget.minimumSizeHint().height())
            assert widget.height() >= control_height + 10
        for control in state.metric_controls:
            if control is not None and control.isVisible():
                assert control.height() >= int(control.fontMetrics().height()) + 4

    def test_advanced_selection_grid_recomputes_from_passed_width_when_growing(self):
        self._set_filter_panel_tab("filters")
        self.window.resize(980, 760)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(760)
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        assert state.grid_cols is not None
        compact_cols = int(state.grid_cols)

        self.window.resize(1680, 900)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(1680)
        QApplication.processEvents()

        assert int(state.last_effective_width) == 1680
        assert int(state.grid_cols) >= compact_cols
        assert int(state.grid_cols) == 4

    def test_advanced_selection_windows_sized_layout_fills_bottom_area(self):
        self._set_filter_panel_tab("filters")
        for width, height in ((1200, 900), (1680, 900)):
            self.window.resize(width, height)
            QApplication.processEvents()
            self.window._restore_main_bottom_splitter_sizes()
            self.window._sync_bottom_panel_heights()
            self.window._reorganize_advanced_filters_grid(
                self.window.adv_filters_group.width()
            )
            QApplication.processEvents()

            ctx = self._panel_context()
            details_group = ctx["details_group"]
            filters_panel_group = ctx["filters_panel_group"]
            parent = filters_panel_group.parentWidget()
            state = self.window._advanced_filter_panel_state
            scroll = state.controls_scroll

            assert abs(int(details_group.height()) - int(filters_panel_group.height())) <= 4
            if parent is not None and int(parent.height()) > 0:
                parent_delta = int(parent.height()) - int(filters_panel_group.height())
                assert 0 <= parent_delta <= 4

            usable_adv_height = max(80, int(self.window.adv_filters_group.height()) - 4)
            assert int(scroll.height()) >= int(usable_adv_height * 0.90)
            assert int(scroll.height()) <= int(self.window.adv_filters_group.height())
            assert scroll.verticalScrollBar().maximum() == 0
            assert scroll.horizontalScrollBar().maximum() == 0
            if sys.platform.startswith("win"):
                assert int(state.grid_cols) <= 3
                assert self.window.adv_macro_combo.objectName() == "advancedMacroCombo"
                macro_line = self.window.adv_macro_combo.lineEdit()
                assert macro_line is not None
                assert macro_line.isReadOnly()
                assert macro_line.alignment() & Qt.AlignmentFlag.AlignCenter
                assert not macro_line.testAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents
                )
                assert macro_line.property("ssa_macro_click_filter") is True
                assert (
                    self.window.adv_macro_combo.cursor().shape()
                    == Qt.CursorShape.PointingHandCursor
                )
                macro_height = int(self.window.adv_macro_combo.height())
                for control in state.metric_controls:
                    if control is self.window.adv_reprog_mode:
                        continue
                    assert int(control.height()) == macro_height
                assert self.window.adv_reprog_mode.objectName() == "advancedReprogModeCombo"
                assert int(self.window.adv_reprog_mode.height()) >= 26
            assert "action_box" not in state.grid_widgets
            for key in ("emis_box", "exec_box", "status_box", "sol_box", "prog_box", "exec_resp_box"):
                widget = state.grid_widgets.get(key)
                assert widget is not None
                assert widget.isVisible()
                if sys.platform.startswith("win"):
                    assert int(widget.height()) >= 43
                assert widget.geometry().y() + widget.geometry().height() <= scroll.viewport().height() - 4
                for child in widget.findChildren(
                    QtWidgets.QWidget,
                    options=Qt.FindChildOption.FindDirectChildrenOnly,
                ):
                    if child.isVisible():
                        assert int(child.geometry().bottom()) <= int(widget.contentsRect().bottom()) + 1

    def test_reorganize_advanced_filters_grid_caps_narrow_width(self):
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window.resize(420, 760)
        QApplication.processEvents()
        self.window._reorganize_advanced_filters_grid(420)
        QApplication.processEvents()

        state = self.window._advanced_filter_panel_state
        grid = state.main_grid

        assert 1 <= state.grid_cols <= 2
        assert int(grid.horizontalSpacing()) == 4
        assert int(grid.verticalSpacing()) == 2
        reprog_button = self.window.adv_reprog_button
        sem_dados_width = reprog_button.fontMetrics().horizontalAdvance("Sem dados")
        assert int(reprog_button.maximumWidth()) >= sem_dados_width + 16
        assert int(state.grid_widgets["macro_box"].maximumWidth()) <= 340
        assert "action_box" not in state.grid_widgets

    def test_reprogramacoes_menu_builds_without_responsavel_materialized(self):
        self.window.df_completo = self.base_df.assign(
            num_reprogramacoes=[0, 1, 2, 2, 3]
        ).copy()
        self.window._adv_values_cache = {}
        self.window.responsavel_materialization_state.built_prefixes.clear()
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
        self._set_filter_panel_tab("filters")
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

    def test_refresh_advanced_filter_options_restores_reprog_and_derivada_summaries(
        self,
    ):
        df = self.base_df.copy()
        df.loc[0, "num_reprogramacoes"] = "2"
        df.loc[1, "num_reprogramacoes"] = "0"
        df.loc[0, "derivada_de"] = "202600001"
        df.loc[1, "derivada_de"] = ""
        self.window.df_completo = df.copy()
        self.window.df_exibido = df.copy()
        self.window._df_last_search_filtered = df.copy()
        self.window.paginator.set_dataframe(df.copy())
        self.window._advanced_filters = {
            "num_reprogramacoes_values": ["2"],
            "derivada_has": True,
        }
        self._set_filter_panel_tab("filters")
        QApplication.processEvents()

        self.window._refresh_advanced_filter_options()
        QApplication.processEvents()

        reprog_button = self.window.adv_reprog_button
        derivada_button = self.window.adv_derivada_button
        assert str(reprog_button.text() or "") != "Selecionar"
        assert "2" in str(reprog_button.toolTip() or "")
        assert str(derivada_button.text() or "") != "Selecionar"
        assert "has" in str(derivada_button.toolTip() or "")

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

    def test_on_header_clicked_sorts_generic_mixed_text_column(self):
        extra_rows = pd.concat([self.base_df.iloc[[0]].copy() for _ in range(3)])
        extra_rows = extra_rows.reset_index(drop=True)
        extra_rows["numero_ssa"] = [6, 7, 8]
        mixed_df = pd.concat(
            [self.base_df.copy(), extra_rows],
            ignore_index=True,
        )
        mixed_df["situacao"] = pd.Series(
            ["B", "#", "10", "2", "@", "A", "", None], dtype="object"
        )
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window._df_last_search_filtered = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("situacao")

        self.window.on_header_clicked(logical_index)
        asc_vals = self.window.df_exibido["situacao"].tolist()
        assert asc_vals[:6] == ["#", "@", "2", "10", "A", "B"]
        assert asc_vals[-2:] == ["", None]

        self.window.on_header_clicked(logical_index)
        desc_vals = self.window.df_exibido["situacao"].tolist()
        assert desc_vals[:6] == ["B", "A", "10", "2", "@", "#"]
        assert desc_vals[-2:] == ["", None]

    def test_on_header_clicked_reuses_generic_mixed_text_sort_cache(self):
        rows = 200
        mixed_df = pd.DataFrame(
            {
                "numero_ssa": list(range(1000, 1000 + rows)),
                "situacao": [
                    ["B", "#", "10", "2", "@", "A", "", None][i % 8]
                    for i in range(rows)
                ],
                "derivada_de": [""] * rows,
                "localizacao_codigo": [f"LOC{i % 20:02d}" for i in range(rows)],
                "descricao_localizacao": ["Desc"] * rows,
                "equipamento": ["EQ"] * rows,
                "semana_cadastro": [202501] * rows,
                "semana_programada": [202503] * rows,
                "data_cadastro": ["2025-01-01"] * rows,
                "descricao_ssa": [f"Descricao {i}" for i in range(rows)],
                "setor_executor": ["MEG2"] * rows,
                "setor_emissor": ["MEG2"] * rows,
                "descricao_execucao": [f"Execucao {i}" for i in range(rows)],
                "solicitante": ["User"] * rows,
            }
        )
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window._df_last_search_filtered = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("situacao")

        with patch.object(
            self.window,
            "_build_mixed_text_sort_keys",
            wraps=self.window._build_mixed_text_sort_keys,
        ) as build_keys:
            self.window.on_header_clicked(logical_index)
            cache_after_first = dict(self.window._mixed_text_sort_cache)
            assert build_keys.call_count == 1
            assert cache_after_first["column_name"] == "situacao"
            assert isinstance(cache_after_first["keys_df"], pd.DataFrame)
            assert cache_after_first["keys_df"].index.equals(
                self.window.df_exibido.index
            )

            self.window.on_header_clicked(logical_index)
            cache_after_second = dict(self.window._mixed_text_sort_cache)
            assert build_keys.call_count == 1
            assert cache_after_second["column_name"] == "situacao"
            assert isinstance(cache_after_second["keys_df"], pd.DataFrame)
            assert cache_after_second["keys_df"].index.equals(
                self.window.df_exibido.index
            )

    def test_on_header_clicked_uses_plain_sort_for_descriptive_text_columns(self):
        mixed_df = pd.DataFrame(
            {
                "numero_ssa": [1001, 1002, 1003, 1004, 1005],
                "situacao": ["APV"] * 5,
                "derivada_de": [""] * 5,
                "localizacao_codigo": ["LOC1"] * 5,
                "descricao_localizacao": ["Desc"] * 5,
                "equipamento": ["EQ"] * 5,
                "semana_cadastro": [202501] * 5,
                "semana_programada": [202503] * 5,
                "data_cadastro": ["2025-01-01"] * 5,
                "descricao_ssa": ["beta", "Alpha", "#tag", "10-item", None],
                "setor_executor": ["MEG2"] * 5,
                "setor_emissor": ["MEG2"] * 5,
                "descricao_execucao": ["Execucao"] * 5,
                "solicitante": ["User"] * 5,
            }
        )
        self.window.df_completo = mixed_df.copy()
        self.window.df_exibido = mixed_df.copy()
        self.window._df_last_search_filtered = mixed_df.copy()
        self.window.paginator.set_dataframe(mixed_df.copy())
        self.window.display_current_page(1)
        QApplication.processEvents()

        logical_index = self.window._current_display_columns.index("descricao_ssa")

        with patch.object(
            self.window,
            "_build_mixed_text_sort_keys",
            wraps=self.window._build_mixed_text_sort_keys,
        ) as build_keys:
            self.window.on_header_clicked(logical_index)

        assert build_keys.called is False
        sorted_values = self.window.df_exibido["descricao_ssa"].tolist()
        assert sorted_values[:4] == ["#tag", "10-item", "Alpha", "beta"]
        assert pd.isna(sorted_values[4])

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

    def test_column_filter_null_and_not_null_tokens_are_inverse(self):
        nullable_df = self.base_df.assign(
            setor_executor=pd.Series([pd.NA, "MEL4", "", "-", "IEE3"], dtype="string"),
        ).copy()

        self.window._active_column_filters = {"setor_executor": "NULL"}
        null_filtered = self.window._apply_column_filters(nullable_df)

        self.window._active_column_filters = {"setor_executor": "!NULL"}
        not_null_filtered = self.window._apply_column_filters(nullable_df)

        assert null_filtered["numero_ssa"].tolist() == [1, 3, 4]
        assert not_null_filtered["numero_ssa"].tolist() == [2, 5]
        assert set(null_filtered["numero_ssa"]).isdisjoint(not_null_filtered["numero_ssa"])
        assert set(null_filtered["numero_ssa"]) | set(not_null_filtered["numero_ssa"]) == set(
            nullable_df["numero_ssa"]
        )

    def test_column_filter_date_display_guard_handles_missing_display_series(
        self, monkeypatch
    ):
        dated_df = self.base_df.assign(
            data_programacao=pd.Series(
                ["01/01/2025", "02/01/2025", "03/01/2025", "04/01/2025", "05/01/2025"],
                dtype="string",
            )
        ).copy()
        self.window._active_column_filters = {"data_programacao": "01/01/2025"}

        monkeypatch.setattr(
            self.window,
            "_get_column_filter_date_display_series",
            lambda *_args, **_kwargs: None,
        )

        filtered = self.window._apply_column_filters(dated_df)

        assert filtered["numero_ssa"].tolist() == [1]

    def test_column_filter_date_display_guard_accepts_iso_date_text(self):
        assert (
            self.window._should_match_date_display_filter(
                "data_cadastro",
                "2026-05-13",
            )
            is True
        )

    def test_column_filter_date_display_exclusion_wins_across_raw_and_display(
        self,
    ):
        dated_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2],
                "data_cadastro": ["2026-05-13", "2026-05-14"],
            }
        )
        self.window._active_column_filters = {
            "data_cadastro": "13/05/2026,!2026-05-13"
        }

        filtered = self.window._apply_column_filters(dated_df)

        assert filtered.empty

    def test_column_filter_date_display_combines_includes_and_excludes_per_token(
        self,
    ):
        dated_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2, 3],
                "data_cadastro": ["2026-05-13", "2026-05-14", "2026-05-15"],
            }
        )
        self.window._active_column_filters = {
            "data_cadastro": "13/05/2026,15/05/2026,!2026-05-15"
        }

        filtered = self.window._apply_column_filters(dated_df)

        assert filtered["numero_ssa"].tolist() == [1]

    def test_column_filter_date_display_exclude_only_keeps_other_dates(self):
        dated_df = pd.DataFrame(
            {
                "numero_ssa": [1, 2, 3],
                "data_cadastro": ["2026-05-13", "2026-05-14", "2026-05-15"],
            }
        )
        self.window._active_column_filters = {"data_cadastro": "!14/05/2026"}

        filtered = self.window._apply_column_filters(dated_df)

        assert filtered["numero_ssa"].tolist() == [1, 3]

    def test_column_filter_date_display_series_reuses_cache_on_same_revision(self):
        dated_df = self.base_df.assign(
            data_programacao=pd.Series(
                [
                    "2025-01-01 08:00:00",
                    "2025-01-02 09:00:00",
                    "2025-01-03 10:00:00",
                    "2025-01-04 11:00:00",
                    "",
                ],
                dtype="string",
            )
        ).copy()
        self.window._data_revision = 71

        first_series = self.window._get_column_filter_date_display_series(
            dated_df, "data_programacao"
        )
        second_series = self.window._get_column_filter_date_display_series(
            dated_df, "data_programacao"
        )

        assert first_series is second_series
        cache_token = self._column_filter_cache_token(dated_df)
        assert getattr(self.window, "_column_filter_date_cache_scope", None) == (
            71,
            cache_token,
        )

    def test_column_filter_date_display_series_invalidates_cache_on_revision_change(
        self,
    ):
        dated_df = self.base_df.assign(
            data_programacao=pd.Series(
                [
                    "2025-01-01 08:00:00",
                    "2025-01-02 09:00:00",
                    "2025-01-03 10:00:00",
                    "2025-01-04 11:00:00",
                    "",
                ],
                dtype="string",
            )
        ).copy()
        self.window._data_revision = 81

        first_series = self.window._get_column_filter_date_display_series(
            dated_df, "data_programacao"
        )
        dated_df.loc[0, "data_programacao"] = "2025-03-05 10:00:00"
        self.window._data_revision = 82
        second_series = self.window._get_column_filter_date_display_series(
            dated_df, "data_programacao"
        )

        assert first_series is not second_series
        assert second_series.iloc[0] == "05/03/2025"
        cache_token = self._column_filter_cache_token(dated_df)
        assert getattr(self.window, "_column_filter_date_cache_scope", None) == (
            82,
            cache_token,
        )

    def test_apply_column_filters_combines_masks_before_slicing_dataframe(
        self, monkeypatch
    ):
        tracked_lengths: list[tuple[str, int, str]] = []
        original_build_column_mask = self.window._build_column_mask

        def _tracked_build_column_mask(
            series: pd.Series,
            raw: str,
            **kwargs,
        ):
            tracked_lengths.append((str(series.name), len(series), str(raw)))
            return original_build_column_mask(series, raw, **kwargs)

        monkeypatch.setattr(
            self.window,
            "_build_column_mask",
            _tracked_build_column_mask,
        )

        self.window._active_column_filters = OrderedDict(
            [
                ("setor_executor", "MEL4"),
                ("descricao_ssa", "Teste C"),
            ]
        )

        filtered = self.window._apply_column_filters(self.base_df.copy())

        assert filtered["numero_ssa"].tolist() == [3]
        executor_calls = [
            length for name, length, raw in tracked_lengths if name == "setor_executor"
        ]
        descricao_calls = [
            length for name, length, raw in tracked_lengths if name == "descricao_ssa"
        ]
        assert executor_calls == [len(self.base_df)]
        assert descricao_calls == [len(self.base_df)]

    def test_apply_column_filters_caches_second_column_from_base_dataframe(self):
        repeated_df = self.base_df.copy()
        self.window._data_revision = 91
        self.window._column_filter_series_cache_revision = None
        self.window._column_filter_series_cache = {}
        self.window._active_column_filters = OrderedDict(
            [
                ("setor_executor", "MEL4"),
                ("descricao_ssa", "Teste C"),
            ]
        )

        filtered = self.window._apply_column_filters(repeated_df)

        assert filtered["numero_ssa"].tolist() == [3]
        cache_token = self._column_filter_cache_token(repeated_df)
        assert set(self.window._column_filter_series_cache) == {
            ((91, cache_token), "setor_executor"),
            ((91, cache_token), "descricao_ssa"),
        }

    def test_apply_column_filters_reuses_normalized_series_on_same_revision(self):
        repeated_df = self.base_df.copy()
        self.window._data_revision = 33
        self.window._column_filter_series_cache_revision = None
        self.window._column_filter_series_cache = {}
        self.window._active_column_filters = {"setor_executor": "MEL4"}

        first_filtered = self.window._apply_column_filters(repeated_df)
        cache_token = self._column_filter_cache_token(repeated_df)
        first_key = ((33, cache_token), "setor_executor")
        first_series = self.window._column_filter_series_cache[first_key]

        second_filtered = self.window._apply_column_filters(repeated_df)
        second_series = self.window._column_filter_series_cache[first_key]

        assert first_filtered["numero_ssa"].tolist() == [3]
        assert second_filtered["numero_ssa"].tolist() == [3]
        assert first_series is second_series

    def test_apply_column_filters_invalidates_normalized_series_cache_on_revision_change(
        self,
    ):
        repeated_df = self.base_df.copy()
        self.window._data_revision = 40
        self.window._column_filter_series_cache_revision = None
        self.window._column_filter_series_cache = {}
        self.window._active_column_filters = {"setor_executor": "MEL4"}

        self.window._apply_column_filters(repeated_df)
        cache_token = self._column_filter_cache_token(repeated_df)
        first_key = ((40, cache_token), "setor_executor")
        first_series = self.window._column_filter_series_cache[first_key]

        self.window._data_revision = 41
        self.window._apply_column_filters(repeated_df)
        second_key = ((41, cache_token), "setor_executor")
        second_series = self.window._column_filter_series_cache[second_key]

        assert first_series is not second_series
        assert self.window._column_filter_series_cache_revision == 41

    def test_apply_column_filters_scopes_normalized_series_cache_by_dataframe_identity(
        self,
    ):
        first_df = self.base_df.copy()
        second_df = self.base_df.copy()
        self.window._data_revision = 52
        self.window._column_filter_series_cache_revision = None
        self.window._column_filter_series_cache = {}
        self.window._active_column_filters = {"setor_executor": "MEL4"}

        self.window._apply_column_filters(first_df)
        self.window._apply_column_filters(second_df)

        first_token = self._column_filter_cache_token(first_df)
        second_token = self._column_filter_cache_token(second_df)
        first_key = ((52, first_token), "setor_executor")
        second_key = ((52, second_token), "setor_executor")

        assert first_key in self.window._column_filter_series_cache
        assert second_key in self.window._column_filter_series_cache
        assert (
            self.window._column_filter_series_cache[first_key]
            is not self.window._column_filter_series_cache[second_key]
        )

    def test_column_filter_cache_keeps_bounded_series_and_masks(self):
        df = pd.DataFrame(
            {
                "c1": ["alfa", "beta"],
                "c2": ["alfa", "beta"],
                "c3": ["alfa", "beta"],
            }
        )
        caches = filter_mixin.ColumnFilterCaches(
            revision=None,
            series={},
            casefold={},
            mask={},
            date_scope=None,
            date_parsed={},
            date={},
            max_entries=2,
        )

        def _build_mask(series, raw, **kwargs):
            return filter_mixin.build_column_mask(
                series,
                raw,
                default_mode="contains",
                **kwargs,
            )

        for column in ("c1", "c2", "c3"):
            filter_mixin.apply_column_filters(
                df,
                {column: "alfa"},
                {},
                revision=1,
                caches=caches,
                build_column_mask=_build_mask,
                date_display_columns=set(),
            )

        assert len(caches.series) <= 2
        assert len(caches.casefold) <= 2
        assert len(caches.mask) <= 2

    def test_filter_alias_map_reuses_module_cache_between_instances(
        self, monkeypatch
    ):
        cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()
        opened_paths: list[str] = []
        real_open = filter_aliases.Path.open

        def _counted_open(path_obj, *args, **kwargs):
            if str(path_obj).endswith("filter_aliases.json"):
                opened_paths.append(str(path_obj))
            return real_open(path_obj, *args, **kwargs)

        class _AliasConsumer(filter_mixin.FilterGUISSAMixin):
            pass

        monkeypatch.setattr(filter_aliases.Path, "open", _counted_open)

        first_map = _AliasConsumer()._get_filter_alias_map()
        second_map = _AliasConsumer()._get_filter_alias_map()

        assert first_map == second_map
        assert len(opened_paths) == 1
        cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()

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
            "source_marker": ("stale-token",),
            "source_len": len(self.window.df_exibido.index),
            "keys_df": stale_keys,
        }

        logical_index = self.window._current_display_columns.index("num_reprogramacoes")
        self.window.on_header_clicked(logical_index)

        cache = self.window._num_reprog_sort_cache
        assert isinstance(cache.get("source_marker"), tuple)
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

    def test_on_filter_finished_uses_filtered_dataframe_result(self):
        self.window._active_filter_request_id = 22
        filtered = self.base_df.iloc[:1].copy()

        self.window.on_filter_finished(filtered, request_id=22)

        pd.testing.assert_frame_equal(
            self.window._df_last_search_filtered.reset_index(drop=True),
            filtered.reset_index(drop=True),
        )

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

    def test_clear_filter_reuses_df_completo_as_search_baseline(self):
        self.window.search_input.setText("Teste A")

        self.window.clear_filter()

        assert self.window._df_last_search_filtered is self.window.df_completo

    def test_clear_filter_skips_full_refresh_for_pending_search_only(self, monkeypatch):
        self.window.search_input.setText("Teste A")
        self.window._pending_search_display = "Teste A"
        self.window._active_filter_search_display = ""

        def fail_refresh():
            raise AssertionError("clear_filter should not refresh unchanged table")

        monkeypatch.setattr(self.window, "_refresh_after_filter_change", fail_refresh)

        self.window.clear_filter()
        QApplication.processEvents()

        assert self.window.search_input.text() == ""
        assert self.window._pending_search_display is None
        assert self.window._df_last_search_filtered is self.window.df_completo
        assert self.window.clear_filter_button.isEnabled() is False

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

    def test_initiate_filtering_sync_single_chunk_uses_filtered_result(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.search_input.setText("Teste A")
        filtered = self.base_df.iloc[:1].copy()

        monkeypatch.setattr(
            filter_mixin,
            "filter_dataframe",
            lambda *args, **kwargs: filtered,
        )

        self.window.initiate_filtering()
        QApplication.processEvents()

        pd.testing.assert_frame_equal(
            self.window._df_last_search_filtered.reset_index(drop=True),
            filtered.reset_index(drop=True),
        )

    def test_initiate_filtering_fallback_uses_filtered_result(
        self, monkeypatch
    ):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste A")
        filtered = self.base_df.iloc[:1].copy()

        monkeypatch.setattr(
            filter_mixin,
            "filter_dataframe",
            lambda *args, **kwargs: filtered,
        )

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", None):
            self.window.initiate_filtering()
            QApplication.processEvents()

        pd.testing.assert_frame_equal(
            self.window._df_last_search_filtered.reset_index(drop=True),
            filtered.reset_index(drop=True),
        )

    def test_initiate_filtering_sync_deduplicates_identical_chunks(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.search_input.setText("Teste A, Teste A")
        filtered = self.base_df.iloc[:1].copy()
        calls = []

        def _fake_filter(*args, **kwargs):
            calls.append(kwargs.get("search_columns"))
            return filtered

        monkeypatch.setattr(filter_mixin, "filter_dataframe", _fake_filter)

        self.window.initiate_filtering()
        QApplication.processEvents()

        assert len(calls) == 1
        pd.testing.assert_frame_equal(
            self.window._df_last_search_filtered.reset_index(drop=True),
            filtered.reset_index(drop=True),
        )

    def test_initiate_filtering_fallback_deduplicates_identical_chunks(
        self, monkeypatch
    ):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste A, Teste A")
        filtered = self.base_df.iloc[:1].copy()
        calls = []

        def _fake_filter(*args, **kwargs):
            calls.append(kwargs.get("search_columns"))
            return filtered

        monkeypatch.setattr(filter_mixin, "filter_dataframe", _fake_filter)

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", None):
            self.window.initiate_filtering()
            QApplication.processEvents()

        assert len(calls) == 1
        pd.testing.assert_frame_equal(
            self.window._df_last_search_filtered.reset_index(drop=True),
            filtered.reset_index(drop=True),
        )

    def test_initiate_filtering_sync_multi_chunk_deduplicates_overlaps_by_index(
        self, monkeypatch
    ):
        self.window._sync_filtering = True
        self.window.search_input.setText("Teste A")

        monkeypatch.setattr(
            self.window,
            "_prepare_search_chunks",
            lambda _text: ["chunk-a", "chunk-b"],
        )

        def _fake_filter(_df, parsed, **_kwargs):
            values = tuple(token.get("value") for token in parsed)
            if set(values) == {"chunk-a", "chunk-b"}:
                return self.base_df.iloc[[0, 1, 2]].copy()
            if values == ("chunk-a",):
                return self.base_df.iloc[[0, 1]].copy()
            return self.base_df.iloc[[1, 2]].copy()

        monkeypatch.setattr(filter_mixin, "filter_dataframe", _fake_filter)

        self.window.initiate_filtering()
        QApplication.processEvents()

        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [3, 2, 1]

    def test_on_filter_finished_defers_general_sort_when_post_filters_are_active(
        self, monkeypatch
    ):
        self.window._active_filter_request_id = 41
        self.window._active_filter_search_request_id = 41
        self.window._active_filter_search_display = "Teste"
        self.window.search_input.setText("Teste")
        self.window._active_column_filters["situacao"] = "APV"
        filtered_search = self.base_df.iloc[[0, 4, 3]].copy()
        sort_calls = {"numero_ssa": 0}
        original_sort_values = pd.DataFrame.sort_values

        def _count_numero_sort(frame, by=None, *args, **kwargs):
            if by == "numero_ssa":
                sort_calls["numero_ssa"] += 1
            return original_sort_values(frame, by=by, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "sort_values", _count_numero_sort)

        self.window.on_filter_finished(filtered_search, request_id=41)
        QApplication.processEvents()

        assert sort_calls["numero_ssa"] == 1
        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [
            1,
            5,
            4,
        ]
        assert self.window.df_exibido["numero_ssa"].tolist() == [5, 1]

    def test_initiate_filtering_fallback_multi_chunk_keeps_equal_rows_distinct(
        self, monkeypatch
    ):
        self.window._sync_filtering = False
        self.window.search_input.setText("Teste A")
        repeated_df = self.base_df.iloc[[0, 0]].copy()
        repeated_df.index = [0, 1]
        self.window.df_completo = repeated_df.copy()
        self.window.df_exibido = repeated_df.copy()
        self.window._df_last_search_filtered = repeated_df.copy()

        monkeypatch.setattr(
            self.window,
            "_prepare_search_chunks",
            lambda _text: ["chunk-a", "chunk-b"],
        )

        def _fake_filter(_df, parsed, **_kwargs):
            values = tuple(token.get("value") for token in parsed)
            if set(values) == {"chunk-a", "chunk-b"}:
                return repeated_df.iloc[[0, 1]].copy()
            if values == ("chunk-a",):
                return repeated_df.iloc[[0]].copy()
            return repeated_df.iloc[[1]].copy()

        monkeypatch.setattr(filter_mixin, "filter_dataframe", _fake_filter)

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", None):
            self.window.initiate_filtering()
            QApplication.processEvents()

        assert self.window._df_last_search_filtered["numero_ssa"].tolist() == [1, 1]

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
        self.window._filter_worker_registry.clear()

        def _connect_side_effect(_signal, _slot, *, label):
            if label == "filter_worker.finished.release":
                return False
            return True

        with patch(
            "gui.mixins.filter_gui_ssa_mixin._connect_filter_signal",
            side_effect=_connect_side_effect,
        ):
            self.window._retain_filter_worker_until_finished(worker)

        assert not self.window._filter_worker_registry.contains(worker)

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
        assert worker.wait_called_ms is None
        assert worker.deleted is True
        assert self.window.filter_thread is None

    def test_filter_worker_cleanup_accepts_already_deleted_qt_worker(self):
        class _DeletedSignal:
            def disconnect(self, _callback=None):
                raise RuntimeError(
                    "wrapped C/C++ object of type FilterWorker has been deleted"
                )

        class _DeletedWorker:
            def __init__(self):
                self.filter_finished = _DeletedSignal()
                self.error_occurred = _DeletedSignal()

        worker = _DeletedWorker()
        self.window._filter_worker_registry.add(worker)

        assert self.window._cleanup_filter_worker(worker) is True
        assert not self.window._filter_worker_registry.contains(worker)

    def test_filter_worker_stop_accepts_already_deleted_qt_worker(self, caplog):
        class _DeletedWorker:
            def cancel(self):
                raise RuntimeError(
                    "wrapped C/C++ object of type FilterWorker has been deleted"
                )

        worker = _DeletedWorker()
        self.window._filter_worker_registry.add(worker)

        with caplog.at_level("WARNING"):
            still_running = self.window._filter_worker_lifecycle()._request_worker_stop(
                worker
            )

        assert still_running is False
        assert not self.window._filter_worker_registry.contains(worker)
        assert "Falha ao solicitar encerramento do worker de filtro" not in caplog.text

    def test_close_event_cancels_filter_worker_when_running_check_fails(self):
        class _BrokenRunningWorker:
            def __init__(self):
                self.quit_called = False
                self.wait_called_ms = None

            def isRunning(self):
                raise RuntimeError("state unavailable")

            def quit(self):
                self.quit_called = True

            def wait(self, ms):
                self.wait_called_ms = ms
                return True

        worker = _BrokenRunningWorker()
        self.window.filter_thread = worker

        with patch.object(
            self.window,
            "_cancel_active_filter_worker",
            side_effect=RuntimeError("cancel unavailable"),
        ) as cancel_mock:
            event = QCloseEvent()
            self.window.closeEvent(event)

        assert event.isAccepted() is True
        cancel_mock.assert_called_once_with("closeEvent")
        assert worker.quit_called is True
        assert worker.wait_called_ms == 3000

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
        self.window._filter_worker_registry.clear()

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _NewWorker):
            self.window.initiate_filtering()

        assert previous_worker.quit_called is True
        assert previous_worker.wait_called_ms is None
        assert self.window._filter_worker_registry.contains(previous_worker)

        previous_worker.finish_now()
        assert previous_worker.deleted is True
        assert not self.window._filter_worker_registry.contains(previous_worker)

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
        assert worker.wait_called_ms is None
        assert worker.deleted is True
        assert self.window.data_loader_thread is None

    def test_close_event_stops_main_and_sector_debounce_timers(self):
        self.window._debounce_timer.start()
        self.window._sector_debounce_timer.start()
        self.window._advanced_apply_timer = QTimer(self.window)
        self.window._advanced_apply_timer.start(200)
        assert self.window._debounce_timer.isActive() is True
        assert self.window._sector_debounce_timer.isActive() is True
        assert self.window._advanced_apply_timer.isActive() is True

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert self.window._debounce_timer.isActive() is False
        assert self.window._sector_debounce_timer.isActive() is False
        assert self.window._advanced_apply_timer.isActive() is False

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

    def test_on_data_loaded_fallback_keeps_df_completo_order_and_sorts_df_exibido(self):
        self.window._active_data_load_request_id = 27
        df = self.base_df.iloc[[0, 1, 2, 3, 4]].copy()
        df.attrs.clear()
        df["numero_ssa"] = [
            "202500004.0",
            "202500005.0",
            "202500003.0",
            "202500001.0",
            "202500002.0",
        ]
        df["situacao"] = ["STE", "APV", "AMP", "STE", "APV"]

        self.window.on_data_loaded(df, request_id=27)

        assert self.window.df_completo["numero_ssa"].tolist() == [
            "202500004",
            "202500005",
            "202500003",
            "202500001",
            "202500002",
        ]
        assert self.window.df_exibido["numero_ssa"].tolist() == [
            "202500005",
            "202500004",
            "202500003",
            "202500002",
            "202500001",
        ]
        assert self.window.df_exibido is not self.window.df_completo

    def test_on_data_loaded_uses_preprocessed_attrs_from_worker(self):
        self.window._active_data_load_request_id = 22
        sorted_df = self.base_df.copy().iloc[::-1].copy()
        sorted_df["numero_ssa"] = [
            "202500005",
            "202500004",
            "202500003",
            "202500002",
            "202500001",
        ]
        sorted_df.attrs["ssa_preprocessed_for_gui"] = True
        sorted_df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "descricao_ssa",
        ]

        self.window.on_data_loaded(sorted_df, request_id=22)

        assert self.window.df_completo.equals(sorted_df)
        assert self.window.df_exibido.iloc[0]["numero_ssa"] == "202500005"
        assert self.window.df_exibido.iloc[-1]["numero_ssa"] == "202500001"
        assert {"numero_ssa", "situacao", "descricao_ssa"}.issubset(
            self.window._non_null_cols_cache
        )

    def test_on_data_loaded_reuses_df_completo_as_search_baseline(self):
        self.window._active_data_load_request_id = 26
        sorted_df = self.base_df.copy().iloc[::-1].copy()
        sorted_df.attrs["ssa_preprocessed_for_gui"] = True
        sorted_df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "descricao_ssa",
        ]

        self.window.on_data_loaded(sorted_df, request_id=26)

        assert self.window._df_last_search_filtered is self.window.df_completo

    def test_on_data_loaded_reapplies_visible_general_search_after_reload(self):
        self.window._active_data_load_request_id = 34
        df = self.base_df.copy()
        df["localizacao_codigo"] = [
            "G097F001",
            "LOC2",
            "LOC3",
            "G097F002",
            "LOC5",
        ]
        df.attrs["ssa_preprocessed_for_gui"] = True
        df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "localizacao_codigo",
        ]
        self.window.search_input.setText("!G097")
        self.window._active_filter_search_display = "!G097"
        self.window._active_filter_search_request_id = 33

        self.window.on_data_loaded(df, request_id=34)

        assert "G097F001" not in self.window.df_exibido["localizacao_codigo"].tolist()
        assert "G097F002" not in self.window.df_exibido["localizacao_codigo"].tolist()
        assert self.window._active_filter_search_display == "!G097"
        assert self.window.search_input.text() == "!G097"

    def test_on_data_loaded_preserves_preprocessed_worker_order_without_filters(self):
        self.window._active_data_load_request_id = 25
        sorted_df = self.base_df.iloc[[1, 4, 2, 0, 3]].copy()
        sorted_df["numero_ssa"] = [
            "202500005",
            "202500003",
            "202500004",
            "202500001",
            "202500002",
        ]
        sorted_df["situacao"] = ["APV", "AMP", "STE", "STE", "APV"]
        sorted_df.attrs["ssa_preprocessed_for_gui"] = True
        sorted_df.attrs["ssa_non_null_cols"] = [
            "numero_ssa",
            "situacao",
            "descricao_ssa",
        ]

        self.window.on_data_loaded(sorted_df, request_id=25)

        assert self.window.df_completo["numero_ssa"].tolist() == [
            "202500005",
            "202500003",
            "202500004",
            "202500001",
            "202500002",
        ]
        assert self.window.df_exibido["numero_ssa"].tolist() == [
            "202500005",
            "202500003",
            "202500004",
            "202500001",
            "202500002",
        ]
        assert self.window.df_exibido is self.window.df_completo

    def test_on_data_loaded_propagates_non_null_attrs_for_fallback_path(self):
        self.window._active_data_load_request_id = 24
        df = self.base_df.copy()
        df["numero_ssa_relacionada_1"] = pd.NA
        df["relacao"] = pd.NA

        self.window.on_data_loaded(df, request_id=24)

        non_null_attr = self.window.df_completo.attrs.get("ssa_non_null_cols")
        assert isinstance(non_null_attr, list)
        assert "numero_ssa" in non_null_attr
        assert "descricao_ssa" in non_null_attr
        assert "numero_ssa_relacionada_1" not in non_null_attr
        assert "relacao" not in non_null_attr

    def test_on_data_loaded_defers_advanced_refresh_until_filters_tab(self):
        self.window._active_data_load_request_id = 23
        self.window._adv_options_dirty = False
        self.window._adv_values_cache = None
        self._set_filter_panel_tab("main")
        QApplication.processEvents()

        with patch.object(
            self.window,
            "_refresh_advanced_filter_options",
            wraps=self.window._refresh_advanced_filter_options,
        ) as refresh_mock:
            self.window.on_data_loaded(self.base_df.copy(), request_id=23)
            QApplication.processEvents()

            assert refresh_mock.call_count == 0
            assert self.window._adv_options_dirty is True

            self._set_filter_panel_tab("filters")
            QApplication.processEvents()

        assert refresh_mock.call_count >= 1
        assert self.window._adv_options_dirty is False

    def test_on_data_loaded_skips_full_refresh_when_no_filters_active(self):
        self.window._active_data_load_request_id = 32
        self.window.search_input.setText("")
        self.window._advanced_filters = {}
        self.window._advanced_filters_active = False
        self.window._exclude_ste_sca = False
        self.window._active_column_filters = OrderedDict()

        with patch.object(
            self.window,
            "_refresh_after_filter_change",
            side_effect=AssertionError("refresh completo nao deveria rodar"),
        ) as refresh_mock:
            self.window.on_data_loaded(self.base_df.copy(), request_id=32)

        assert refresh_mock.call_count == 0
        assert self.window.table_widget.rowCount() == len(self.base_df)
        assert self.window.filtered_status_label.text() == "5 de 5 SSAs"
        assert self.window.clear_filter_button.isEnabled() is False

    def test_on_data_loaded_resets_sort_caches(self):
        self.window._active_data_load_request_id = 31
        df = self.base_df.copy()
        df["num_reprogramacoes"] = [2, "Reprogramacao #1", 0, "", None]
        self.window._num_reprog_sort_cache = {
            "source_marker": ("old-num-token",),
            "source_len": 123,
            "keys_df": pd.DataFrame(
                {
                    "__reprog_is_nan": [False],
                    "__reprog_num": [1],
                    "__reprog_txt": ["stale"],
                }
            ),
        }
        self.window._mixed_text_sort_cache = {
            "column_name": "situacao",
            "source_marker": ("old-mixed-token",),
            "source_len": 123,
            "keys_df": pd.DataFrame(
                {
                    "__mixed_is_empty": [False],
                    "__mixed_bucket_order": [2],
                    "__mixed_symbol_txt": [None],
                    "__mixed_num": [None],
                    "__mixed_alpha_txt": ["apv"],
                    "__mixed_other_txt": [None],
                }
            ),
        }

        self.window.on_data_loaded(df, request_id=31)

        num_cache = self.window._num_reprog_sort_cache
        assert num_cache["source_marker"] is None
        assert num_cache["source_len"] == 0
        assert num_cache["keys_df"] is None
        mixed_cache = self.window._mixed_text_sort_cache
        assert mixed_cache["column_name"] is None
        assert mixed_cache["source_marker"] is None
        assert mixed_cache["source_len"] == 0
        assert mixed_cache["keys_df"] is None

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
        assert stale_worker.wait_called_ms is None
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
        assert worker.wait_called_ms is None
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
        if self.window._filter_worker_registry.contains(worker):
            self.window._filter_worker_registry.remove(worker)
        self.window.filter_thread = worker

        event = QCloseEvent()
        self.window.closeEvent(event)

        assert event.isAccepted() is True
        assert worker.quit_called is True
        assert worker.wait_called_ms is None
        assert self.window._filter_worker_registry.contains(worker)

        worker.finish_now()
        assert worker.deleted is True
        assert not self.window._filter_worker_registry.contains(worker)

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
            assert worker.wait_calls == []
            assert worker.terminate_called is False
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
            assert worker.wait_calls == []
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

    def test_close_event_keeps_rescan_shutdown_nonblocking_after_initial_state_check(
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
        original_running_helper = ssa_gui_workers.is_rescan_worker_running

        def _tracked_running_helper(target, sip_module):
            call_counter["count"] += 1
            return original_running_helper(target, sip_module)

        monkeypatch.setattr(
            ssa_gui_workers, "is_rescan_worker_running", _tracked_running_helper
        )

        try:
            event = QCloseEvent()
            self.window.closeEvent(event)

            assert event.isAccepted() is True
            assert worker.stop_called is True
            assert worker.quit_called is True
            assert call_counter["count"] == 1
            assert worker.wait_calls == []
            assert worker.terminate_called is False
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
        assert worker.wait_called_ms is None
        assert worker.deleted is True
        assert self.window.data_loader_thread is None
        assert self.window.progress_bar.isVisible() is False
        assert self.window.load_button.isEnabled() is True
        assert self.window.search_button.isEnabled() is True

    def test_on_load_finished_replaces_transient_loading_status_with_terminal_text(
        self,
    ):
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
        self.window._active_data_load_request_id = 14
        self.window.df_exibido = self.base_df.copy()
        self.window.status_label.setText("Status: Carregando dados...")

        self.window.on_load_finished(worker=worker, request_id=14)

        assert (
            self.window.status_label.text()
            == "Status: 5 SSAs carregadas. Pronto para filtrar."
        )

    def test_on_filter_finished_skips_width_adjustments_when_table_widget_invalid(
        self, monkeypatch
    ):
        self.window._active_filter_request_id = 77
        self.window._active_filter_search_request_id = 77
        self.window._active_filter_search_display = "Teste"
        monkeypatch.setattr(self.window, "_refresh_after_filter_change", lambda: None)
        monkeypatch.setattr(self.window, "_apply_search_display", lambda: None)
        self.window.table_widget = None
        status_before = self.window.filtered_status_label.text()

        self.window.on_filter_finished(self.base_df.copy(), request_id=77)

        assert self.window.filtered_status_label.text() == status_before

    def test_on_filter_finished_zero_results_separates_count_from_notice(self):
        self.window.search_input.setText("SVP, R001")
        self.window._active_filter_request_id = 88
        self.window._active_filter_search_request_id = 88
        self.window._active_filter_search_display = "SVP, R001"
        self.window._pending_search_display = "SVP, R001"
        self.window.df_exibido = self.base_df.iloc[0:0].copy()
        self.window._df_last_search_filtered = self.base_df.iloc[0:0].copy()
        with patch.object(
            self.window, "_refresh_after_filter_change", lambda **_kwargs: True
        ):
            self.window.on_filter_finished(self.base_df.iloc[0:0].copy(), request_id=88)

        status = str(self.window.filtered_status_label.text() or "")
        assert status == "0 de 5 SSAs"
        assert self.window.status_label.text() == (
            "Status: Busca para 'SVP, R001'. Aviso: nenhum resultado para o filtro atual."
        )

    def test_build_gui_general_search_columns_excludes_dates_but_keeps_weeks(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["202500001"],
                "semana_cadastro": [202501],
                "semana_programada": [202502],
                "grau_prioridade_emissao": [3],
                "coluna_textual_nova": pd.Series(["texto livre"], dtype="string"),
                "data_cadastro": ["2025-01-01"],
                "data_planilha": ["2025-01-02"],
                "sn_instalado": ["ABC123"],
            }
        )

        columns = filter_mixin.build_gui_general_search_columns(df)

        assert "semana_cadastro" in columns
        assert "semana_programada" in columns
        assert "grau_prioridade_emissao" in columns
        assert "coluna_textual_nova" in columns
        assert "data_cadastro" not in columns
        assert "data_planilha" not in columns
        assert "sn_instalado" not in columns

    def test_initiate_filtering_uses_gui_general_search_columns_for_week_and_priority(
        self,
    ):
        filtered_df = pd.DataFrame(
            {
                "numero_ssa": ["202500001", "202500002"],
                "situacao": ["APV", "APV"],
                "derivada_de": ["", ""],
                "localizacao_codigo": ["LOC1", "LOC2"],
                "descricao_localizacao": ["Desc1", "Desc2"],
                "equipamento": ["EQ1", "EQ2"],
                "semana_cadastro": [202501, 202501],
                "semana_programada": [202512, 202510],
                "data_cadastro": ["2025-01-01", "2025-01-02"],
                "descricao_ssa": ["Teste A", "Teste B"],
                "setor_executor": ["IEE3", "OURO"],
                "setor_emissor": ["ABC", "ABC"],
                "descricao_execucao": ["Exec A", "Exec B"],
                "solicitante": ["User1", "User2"],
                "grau_prioridade_emissao": [3, 1],
            }
        )
        self.window.df_completo = filtered_df.copy()
        self.window.df_exibido = filtered_df.copy()
        self.window._df_last_search_filtered = filtered_df.copy()
        self.window.paginator.set_dataframe(filtered_df.copy())

        self.window.search_input.setText("3, 202512")
        self.window.initiate_filtering()

        assert list(self.window.df_exibido["numero_ssa"]) == ["202500001"]

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
        self.window._filter_worker_registry.clear()

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
        assert self.window._filter_worker_registry.contains(previous_filter_worker)

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

    def test_retain_data_loader_worker_fallback_disconnect_attempts_shutdown(self):
        class _FakeSignal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def disconnect(self, _callback=None):
                self._callbacks.clear()

        class _BrokenFinishedSignal:
            def connect(self, _callback):
                raise RuntimeError("signal down")

            def disconnect(self, _callback=None):
                return None

        class _Worker:
            def __init__(self):
                self.data_loaded = _FakeSignal()
                self.error_occurred = _FakeSignal()
                self.finished = _BrokenFinishedSignal()
                self.destroyed = _FakeSignal()
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

        worker = _Worker()

        ssa_gui_workers.retain_data_loader_worker_until_finished(
            self.window,
            worker,
            global_workers=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=gui_ssa.RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=gui_ssa.RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=gui_ssa.sip,
        )

        assert worker.quit_called is True
        assert worker.wait_called_ms == gui_ssa.RETIRED_WORKER_FORCE_WAIT_MS
        assert worker.deleted is True
        assert worker not in getattr(self.window, "_retired_data_loader_workers", [])

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

        self.window._filter_worker_registry.clear()
        self.window._filter_request_seq = 0
        slow_workers = []

        with patch("gui.mixins.filter_gui_ssa_mixin.FilterWorker", _NewFilterWorker):
            for _ in range(10):
                slow = _SlowFilterWorker()
                slow_workers.append(slow)
                self.window.filter_thread = slow
                self.window.initiate_filtering()
                assert self.window._filter_worker_registry.contains(slow)
                slow.finish_now()

        assert self.window._filter_worker_registry.snapshot() == []
        assert self.window._active_filter_request_id == 10
        assert all(worker.quit_called for worker in slow_workers)

    def test_restore_filter_state_syncs_exclude_checkbox_all_tabs(self):
        for ctx in self._iter_panel_contexts():
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
        for ctx in self._iter_panel_contexts():
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
        assert "situacao!=SCA/SES/STE" in [
            str(button.text() or "")
            for button in self.window.filters_summary_items_widget.findChildren(
                QPushButton
            )
        ]

    def test_restore_last_filter_state_preserves_snapshot_when_render_fails(
        self, monkeypatch
    ):
        self.window.search_input.setText("Teste A")
        self.window._safe_store_last_filter_state("test_restore_failure")
        snapshot = self.window._last_filter_state
        assert snapshot is not None

        def fail_render(_restored_search_text):
            raise RuntimeError("forced restore render failure")

        monkeypatch.setattr(self.window, "_render_restored_filter_state", fail_render)

        with pytest.raises(RuntimeError, match="forced restore render failure"):
            self.window._restore_last_filter_state()

        assert self.window._last_filter_state is snapshot
        assert self.window.undo_filter_btn.isEnabled() is True

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

        cancel_mock.assert_called_once_with("clear_filter")

    def test_clear_all_filters_global_cancels_active_filter_worker(self):
        with patch.object(self.window, "_cancel_active_filter_worker") as cancel_mock:
            self.window._clear_all_filters_global()

        cancel_mock.assert_called_once_with("clear_all_filters_global")

    def test_schedule_sector_refresh_stops_pending_timer_when_not_materialized(self):
        responsavel_state = self.window.responsavel_materialization_state
        responsavel_state.built_prefixes.clear()
        responsavel_state.dirty_prefixes.clear()
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

        assert responsavel_state.status_flags()[1] is True
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
            ssa_gui_workers.retain_data_loader_worker_until_finished(
                self.window,
                worker,
                global_workers=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                global_meta=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META,
                max_global_workers=gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                retired_ttl_sec=gui_ssa.RETIRED_WORKER_TTL_SEC,
                retired_force_wait_ms=gui_ssa.RETIRED_WORKER_FORCE_WAIT_MS,
                sip_module=gui_ssa.sip,
            )
            assert worker in self.window._retired_data_loader_workers
            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS

            # Simula finalização silenciosa sem emissao de finished().
            worker._running = False
            ssa_gui_workers.prune_retired_data_loader_workers(
                self.window,
                global_workers=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                global_meta=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META,
                max_global_workers=gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                retired_ttl_sec=gui_ssa.RETIRED_WORKER_TTL_SEC,
                retired_force_wait_ms=gui_ssa.RETIRED_WORKER_FORCE_WAIT_MS,
                sip_module=gui_ssa.sip,
            )

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
            ssa_gui_workers.retain_data_loader_worker_until_finished(
                self.window,
                worker,
                global_workers=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                global_meta=gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META,
                max_global_workers=gui_ssa.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
                retired_ttl_sec=gui_ssa.RETIRED_WORKER_TTL_SEC,
                retired_force_wait_ms=gui_ssa.RETIRED_WORKER_FORCE_WAIT_MS,
                sip_module=gui_ssa.sip,
            )

            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS
            assert worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META
        finally:
            if worker in gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS:
                gui_ssa.GLOBAL_RETIRED_DATA_LOADER_WORKERS.remove(worker)
            gui_ssa.GLOBAL_RETIRED_DATA_LOADER_META.pop(worker, None)
