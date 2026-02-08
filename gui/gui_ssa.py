# flake8: noqa
# gui_ssa.py (GUI PyQt6 para SSA_Consulta_Rapida)
# Last modified: 2025-10-30T16:05:00 (completed search simplification: removed ALL v/OU/OR/AND processing)
"""
Prova de Conceito Refinada de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Refinamentos em relação à PoC básica:
1. Seleção de colunas com base em display_mappings.json e prioridade.
2. Paginacao simples para lidar with grandes conjuntos de dados.
3. Uso de nomes de exibição para colunas.
4. Feedback mais detalhado ao usuário.
5. Estrutura mais preparada para expansão (ordenação, exportação).

Para executar: python gui_ssa.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""
# flake8: noqa

import sys
import os
import pandas as pd
import json
import subprocess
import re
import logging
import copy
from collections import OrderedDict
from time import perf_counter


try:
    from utils.version import get_app_version
except ImportError:
    def get_app_version():
        return "3.11+"

# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importações dos managers unificados
from gui.simple_width_manager import SimpleWidthManager, SimpleCacheManager  # noqa: E402
from utils.themes import get_palette, get_theme_roles, normalize_theme  # noqa: E402
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS  # noqa: E402
from gui.gui_config import (  # noqa: E402
    GUI_MAIN_PREFERENCES,
    REQUIRED_DISPLAY_COLUMNS,
    load_gui_main_preferences,  # noqa: F401 - re-export for compatibility
)

# Inicializar logging robusto
try:
    from utils.robust_logging import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.debug("Sistema de logging robusto inicializado na GUI", extra={'component': 'gui'})
except Exception as e:
    # Fallback para logging padrão
    logger = logging.getLogger(__name__)
    logger.error(f"Falha ao inicializar logging robusto: {e}")
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

from utils.formatting import format_dataframe_for_display, format_cell  # noqa: E402

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms  # noqa: E402
import hashlib
from armazenamento.database import query_db  # noqa: E402

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6 import sip
    from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
    QMenu, QGroupBox, QTextEdit, QTextBrowser, QFileDialog, QDialog, QDialogButtonBox,
        QSpacerItem, QSizePolicy, QFrame, QListWidget, QListWidgetItem, QCheckBox, QTabWidget,
        QScrollArea, QToolButton, QWidgetAction
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QPoint
    from PyQt6.QtGui import QAction, QFont

    # Import workers, cache, widgets, and helpers from separate modules
    from gui.workers import DataLoaderWorker, FilterWorker  # noqa: E402
    from gui.cache import FilterCache  # noqa: E402
    from gui.widgets import ColumnManagerDialog, ColumnSelector, DataPaginator, FilterHelpDialog  # noqa: E402
    from gui.helpers import (  # noqa: E402
        build_global_widget_qss, build_central_widget_qss, build_group_box_qss, build_line_edit_qss,
        normalize_chunk_for_parse, format_search_display, highlight_text
    )
    # Import mixins for code organization
    from gui.mixins import FilterGUISSAMixin  # noqa: E402
except ImportError as exc:
    QT_AVAILABLE = False
    sip = None
    logger.warning("PyQt6 import failed, using headless stub mode: %s", exc)
    # Stubs mánimos para permitir import em ambiente CI sem libs grãficas
    class _Sig:
        def emit(self, *a, **k):
            pass
        def connect(self, *a, **k):
            pass
    def pyqtSignal(*a, **k):
        return _Sig()
    class QWidget:
        def findChildren(self, *a, **k):
            return []

    class QMainWindow:
        pass

    class QAction:
        def __init__(self, *a, **k):
            pass

    class QFont:
        def __init__(self, *a, **k):
            self._point_size = 10.0

        def setPointSizeF(self, size):
            self._point_size = size

        def pointSizeF(self):
            return self._point_size

        def setWeight(self, *a, **k):
            pass

        def setBold(self, *a, **k):
            pass
    class QPoint:
        def __init__(self, x=0, y=0):
            self._x = x
            self._y = y
        def x(self):
            return self._x
        def y(self):
            return self._y
        def setY(self, y):
            self._y = y
    class QApplication:
        def __init__(self, *a, **k): pass
        def exec(self): return 0
    class QVBoxLayout:
        def __init__(self, *a, **k):
            pass

    class QHBoxLayout(QVBoxLayout):
        pass

    class QGridLayout(QVBoxLayout):
        pass
    class QTabWidget:
        def __init__(self, *a, **k):
            self.currentChanged = _Sig()
        def addTab(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass
    class QLabel:
        def __init__(self, *a, **k):
            pass
    class QPushButton:
        def __init__(self, *a, **k):
            pass
        def clicked(self):
            return _Sig()
    class QLineEdit:
        def __init__(self, *a, **k):
            self._text = ""
            self.returnPressed = _Sig()
            self.textChanged = _Sig()
        def text(self):
            return self._text
        def setText(self, value):
            self._text = "" if value is None else str(value)
        def clear(self):
            self._text = ""
        def setPlaceholderText(self, *a, **k):
            pass
        def setToolTip(self, *a, **k):
            pass
        def setMinimumWidth(self, *a, **k):
            pass
        def setMaximumWidth(self, *a, **k):
            pass
        def setMinimumHeight(self, *a, **k):
            pass
        def setSizePolicy(self, *a, **k):
            pass
        def blockSignals(self, *a, **k):
            pass
        def hasFocus(self):
            return False
        def setEnabled(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass
    class QTableWidget:
        pass

    class QTableWidgetItem:
        def __init__(self, *a, **k):
            pass

    class QHeaderView:
        Stretch = 1
    class QMessageBox:
        pass

    class QProgressBar:
        pass
    class QComboBox:
        class SizeAdjustPolicy:
            AdjustToContents = 0

        def __init__(self):
            self._items = []
            self._data = []
            self._current_index = 0
            self.currentIndexChanged = _Sig()

        def addItems(self, items):
            for item in items:
                self.addItem(item)

        def addItem(self, item, userData=None):
            self._items.append(item)
            self._data.append(userData)

        def addWidget(self, *a, **k):
            pass

        def setMinimumWidth(self, *a, **k):
            pass

        def setSizeAdjustPolicy(self, *a, **k):
            pass

        def setMaximumWidth(self, *a, **k):
            pass

        def currentIndex(self):
            return self._current_index

        def setCurrentIndex(self, *a, **k):
            try:
                self._current_index = int(a[0])
            except Exception:
                self._current_index = 0

        def currentData(self):
            return self.itemData(self._current_index)

        def clear(self):
            self._items = []
            self._data = []
            self._current_index = 0

        def blockSignals(self, *a, **k):
            pass

        def itemData(self, index):
            try:
                return self._data[index]
            except Exception:
                return None

        def findData(self, data):
            try:
                return self._data.index(data)
            except ValueError:
                return -1
    class QSpinBox:
        pass

    class QAbstractItemView:
        NoEditTriggers = 0

    class QMenu:
        def __init__(self, *a, **k):
            self._actions = []
        def addAction(self, action):
            self._actions.append(action)
            return action
        def addSeparator(self):
            return None
        def clear(self):
            self._actions = []
        def exec(self, *a, **k):
            pass
        def setPalette(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass
        def setAttribute(self, *a, **k):
            pass
        def setMaximumHeight(self, *a, **k):
            pass

    class QWidgetAction:
        def __init__(self, *a, **k):
            self._widget = None
        def setDefaultWidget(self, widget):
            self._widget = widget

    class QToolButton:
        class ToolButtonPopupMode:
            InstantPopup = 0
        def __init__(self, *a, **k):
            self._menu = None
            self._text = ""
        def setText(self, text):
            self._text = text
        def text(self):
            return self._text
        def setMenu(self, menu):
            self._menu = menu
        def setPopupMode(self, *a, **k):
            pass
        def showMenu(self):
            pass
        def setToolTip(self, *a, **k):
            pass
        def setMinimumWidth(self, *a, **k):
            pass
        def setSizePolicy(self, *a, **k):
            pass
        def setEnabled(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass

    class QGroupBox:
        def setVisible(self, *a, **k):
            pass
        def setEnabled(self, *a, **k):
            pass

    class QTextEdit:
        def __init__(self, *a, **k):
            pass
        def setReadOnly(self, *a, **k):
            pass
        def setFrameShape(self, *a, **k):
            pass
        def viewport(self):
            class _Viewport:
                def setAutoFillBackground(self, *a, **k):
                    pass
            return _Viewport()
        def clear(self):
            pass
        def setHtml(self, *a, **k):
            pass
        def setPlainText(self, *a, **k):
            pass
        def setFont(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass

    class QTextBrowser(QTextEdit):
        def setOpenExternalLinks(self, *a, **k):
            pass

    class QScrollArea:
        def __init__(self, *a, **k):
            pass
        def setWidgetResizable(self, *a, **k):
            pass
        def setWidget(self, *a, **k):
            pass

    class QFileDialog:
        pass

    class QAction:
        pass

    class QDialog:
        class DialogCode:
            Accepted = 1
            Rejected = 0

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def accept(self):
            return self.DialogCode.Accepted

        def reject(self):
            return self.DialogCode.Rejected

    class QListWidget:
        def __init__(self, *a, **k):
            self._items = []

        def setAlternatingRowColors(self, *a, **k):
            pass

        def setSelectionMode(self, *a, **k):
            pass

        def setDragDropMode(self, *a, **k):
            pass

        def setDefaultDropAction(self, *a, **k):
            pass

        def clear(self):
            self._items.clear()

        def addItem(self, item):
            self._items.append(item)

        def count(self):
            return len(self._items)

        def item(self, index):
            try:
                return self._items[index]
            except Exception:
                return None

    class QListWidgetItem:
        def __init__(self, text=""):
            self._text = text
            self._data = {}
            self._flags = 0
            self._check = 0
            self._hidden = False

        def flags(self):
            return self._flags

        def setFlags(self, flags):
            self._flags = flags

        def setData(self, role, value):
            self._data[role] = value

        def data(self, role):
            return self._data.get(role)

        def setCheckState(self, state):
            self._check = state

        def checkState(self):
            return self._check

        def text(self):
            return self._text

        def setHidden(self, hidden):
            self._hidden = hidden

    class QDialogButtonBox:
        class StandardButton:
            Ok = 0
            Cancel = 1

        def __init__(self, *a, **k):
            self.accepted = _Sig()
            self.rejected = _Sig()

    class QCheckBox:
        def __init__(self, *a, **k):
            self._checked = False
            self._text = a[0] if a else ""
            self.toggled = _Sig()

        def isChecked(self):
            return self._checked

        def setChecked(self, val):
            self._checked = bool(val)

        def setToolTip(self, *a, **k):
            pass

        def text(self):
            return self._text
        def setEnabled(self, *a, **k):
            pass

    class QItemSelectionModel:
        Select = 0

    class QTimer:
        pass
    class QThread:
        def __init__(self, *a, **k): pass
        def start(self): pass
        def run(self): pass
    class Qt:
        AlignLeft = 0

    # Stub for FilterGUISSAMixin in headless mode
    class FilterGUISSAMixin:
        """Stub mixin for headless testing."""
        pass


def _is_widget_valid(widget) -> bool:
    """Return True when a Qt widget reference still points to a live object."""
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except Exception:
        return False

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')

# Constantes de UI
DETAILS_DIALOG_FONT_SIZE = 10  # pt
DETAILS_DIALOG_TABLE_PADDING = 8  # px
DETAILS_DIALOG_BORDER_COLOR = '#ccc'
DETAILS_DIALOG_MIN_WIDTH = 700  # px
DETAILS_DIALOG_MIN_HEIGHT = 500  # px
HIGHLIGHT_BACKGROUND_COLOR = 'yellow'
HIGHLIGHT_FONT_WEIGHT = 'bold'

DIVISAO_SETORES = {
    "SMME": ["MEL1", "MEL2", "MEL3", "MEL4"],
    "SMIN": ["IEE1", "IEE2", "IEE3", "IEE4"],
    "SMIL": ["ILA1", "ILA2", "ILA3", "ILA4"],
    "SMMG": ["MEG1", "MEG2", "MEG3", "MEG4"],
}
SECTOR_TO_DIV = {sec: div for div, secs in DIVISAO_SETORES.items() for sec in secs}

# Prioridade de campos para ordenacao em detalhes
DETAIL_FIELD_PRIORITY = [
    'numero_ssa',
    'situacao',
    'descricao_ssa',
    'descricao_servico',
    'setor_executor',
    'setor_emissor',
    'data_cadastro',
    'prazo_limite',
]

DETAIL_DISPLAY_OVERRIDES = {
    'situacao': 'Situacao',
    'semana_cadastro': 'Semana de Cadastro',
    'data_cadastro': 'Data de Cadastro',
    'loc': 'Localizacao',
    'descricao_ssa': 'Descricao da SSA',
    'setor_executor': 'Setor Executor',
    'setor_emissor': 'Setor Emissor',
    'responsavel_emissor': 'Responsavel Emissor',
    'solicitante': 'Solicitante',
    'servico_origem': 'Servico de Origem',
    'grau_prioridade_emissao': 'Grau de Prioridade (Emissao)',
    'grau_prioridade_planejamento': 'Grau de Prioridade (Planejamento)',
    'execucao_simples': 'Execucao Simples',
    'responsavel_programacao': 'Responsavel pela Programacao',
    'responsavel_execucao': 'Responsavel pela Execucao',
    'num_reprogramacoes': 'Reprogramacoes',
    'semana_programada': 'Semana Programada',
    'semana_executada': 'Semana Executada',
    'prazo_limite': 'Prazo Limite',
    'tempo_disponivel': 'Tempo Disponivel',
    'data_limite': 'Data Limite',
    'tempo_excedido': 'Tempo Excedido',
    'total_tempo_tex_executada': 'Tempo Total (TEX)',
    'total_tempo_tpe_executada': 'Tempo Total (TPE)',
    'total_tempo_tpo_executada': 'Tempo Total (TPO)',
    'numero_ssa': 'Numero da SSA',
    'descricao_execucao': 'Descricao da Execucao',
    'status_execucao_prazo': 'Situacao do Prazo',
    'execucao_parcial': 'Execucao Parcial',
}

TABLE_NAME = 'ssas'

# --- Funções Auxiliares ---

def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibiçção independente do CLI."""
    # Defensive merge keeps legacy aliases and stable labels even on partial JSON configs.
    merged_mappings = dict(DEFAULT_DISPLAY_MAPPINGS)
    merged_mappings.update(GUI_MAIN_PREFERENCES.get("column_display_names", {}))
    merged_mappings.update(GUI_MAIN_PREFERENCES.get("display_mappings", {}))
    return merged_mappings

# --- Worker Threads ---

# --- Componentes da GUI ---

# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow, FilterGUISSAMixin):
    """
    Janela principal da aplicação GUI.

    Inherits from FilterGUISSAMixin for filter-related methods.
    """
    TAB_WIDGET_ATTRS = (
        "search_label",
        "search_input",
        "search_button",
        "clear_filter_button",
        "column_selector",
        "search_help",
        "paginator",
        "profile_selector",
        "persistent_filters_layout",
        "filter_tags_widget",
        "filter_tags_layout",
        "exclude_ste_checkbox",
        "col_filter_indicator",
        "filters_summary_frame",
        "filters_summary_label",
        "clear_all_filters_btn",
        "export_list_btn",
        "undo_filter_btn",
        "table_widget",
        "details_group",
        "details_text",
        "col_filters_group",
        "col_filters_hint",
        "col_filters_scroll",
        "col_filters_container",
        "col_filters_list_layout",
        "add_column_filter_btn",
        "clear_all_btn",
        "adv_filters_group",
        "adv_executor_button",
        "adv_executor_menu",
        "adv_executor_checks",
        "adv_executor_exclude",
        "adv_emissor_button",
        "adv_emissor_menu",
        "adv_emissor_checks",
        "adv_emissor_exclude",
        "adv_divisao_button",
        "adv_divisao_menu",
        "adv_divisao_checks",
        "adv_divisao_exclude",
        "adv_status_button",
        "adv_status_menu",
        "adv_status_checks",
        "adv_status_exclude",
        "adv_year_emissao_button",
        "adv_year_emissao_menu",
        "adv_year_emissao_checks",
        "adv_year_execucao_button",
        "adv_year_execucao_menu",
        "adv_year_execucao_checks",
        "adv_week_emissao_start",
        "adv_week_emissao_end",
        "adv_week_emissao_exclude",
        "adv_week_execucao_start",
        "adv_week_execucao_end",
        "adv_week_execucao_exclude",
        "adv_prioridade_emissao_button",
        "adv_prioridade_emissao_menu",
        "adv_prioridade_emissao_checks",
        "adv_prioridade_planejamento_button",
        "adv_prioridade_planejamento_menu",
        "adv_prioridade_planejamento_checks",
        "adv_derivada_has",
        "adv_derivada_all_ste",
        "adv_derivada_is",
        "adv_derivadas_especificas_button",
        "adv_macro_combo",
        "adv_responsavel_solicitante_button",
        "adv_responsavel_solicitante_menu",
        "adv_responsavel_solicitante_checks",
        "adv_responsavel_solicitante_exclude",
        "adv_responsavel_solicitante_box",
        "adv_responsavel_programacao_button",
        "adv_responsavel_programacao_menu",
        "adv_responsavel_programacao_checks",
        "adv_responsavel_programacao_exclude",
        "adv_responsavel_programacao_box",
        "adv_responsavel_execucao_button",
        "adv_responsavel_execucao_menu",
        "adv_responsavel_execucao_checks",
        "adv_responsavel_execucao_exclude",
        "adv_responsavel_execucao_box",
        "adv_responsavel_emissor_button",
        "adv_responsavel_emissor_menu",
        "adv_responsavel_emissor_checks",
        "adv_responsavel_emissor_exclude",
        "adv_responsavel_emissor_box",
        "adv_save_defaults_btn",
    )
    def _get_theme_catalog(self):
        light_themes = [
            ("Classico", 'classico'),
            ("Mint Light", 'mint-light'),
            ("Paper", 'paper'),
            ("Solarized Light", 'solarized-light'),
            ("Windows 7", 'windows7'),
        ]
        dark_themes = [
            ("Catppuccin (Mocha)", 'catppuccin'),
            ("Dark", 'dark'),
            ("Dracula", 'dracula'),
            ("Grayscale", 'grayscale'),
            ("Gruvbox", 'gruvbox'),
            ("Nord", 'nord'),
            ("Solarized Dark", 'solarized-dark'),
            ("Tokyo Night", 'tokyo-night'),
        ]
        return light_themes, dark_themes

    def _get_theme_keys(self):
        light_themes, dark_themes = self._get_theme_catalog()
        return {key for _, key in light_themes + dark_themes}

    def _persist_gui_preferences(self):
        try:
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Falha ao persistir preferencias GUI: %s", e)

    def _resolve_startup_theme(self):
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        theme_default = gui_settings.get("theme_default")
        last_theme = gui_settings.get("theme")
        theme_keys = self._get_theme_keys()
        for candidate in (theme_default, last_theme, "gruvbox"):
            if isinstance(candidate, str) and candidate.strip():
                normalized = normalize_theme(candidate)
                if normalized in theme_keys:
                    return normalized
        return "gruvbox"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Rapida de SSAs")
        self.setGeometry(100, 100, 1200, 800)
        # Icone da janela (prioriza .ico no Windows)
        try:
            from PyQt6.QtGui import QIcon
            ico_path = os.path.join(project_root, 'resources', 'app_icon.ico')
            if os.path.exists(ico_path):
                self.setWindowIcon(QIcon(ico_path))
            else:
                svg_path = os.path.join(project_root, 'resources', 'app_icon.svg')
                if os.path.exists(svg_path):
                    self.setWindowIcon(QIcon(svg_path))
        except Exception:
            pass

        self.df_completo = pd.DataFrame()
        self.df_exibido = pd.DataFrame()  # DataFrame filtrado
        self.df_para_tabela = pd.DataFrame()  # DataFrame paginado para exibiçção

        try:
            base_font = QFont(self.font())
            if base_font.pointSizeF() <= 0:
                base_font.setPointSizeF(11.0)
            self._info_font = base_font
        except Exception:
            self._info_font = None

        # Carrega mapeamentos de exibicao das preferencias da GUI principal
        self.display_map = GUI_MAIN_PREFERENCES.get("display_mappings", load_display_mappings())
        self.internal_to_display = {k: v for k, v in self.display_map.items()}

        # Colunas padrção para exibiçção (das configurações JSON)
        self.default_columns = GUI_MAIN_PREFERENCES.get(
            "display_columns", list(REQUIRED_DISPLAY_COLUMNS)
        )
        for required_col in REQUIRED_DISPLAY_COLUMNS:
            if required_col not in self.default_columns:
                self.default_columns.append(required_col)

        # Garante que colunas padrção existam no mapeamento
        self.visible_columns = [col for col in self.default_columns if col in self.internal_to_display or col == '#']

        # Perfis de filtro por setor (precarregados)
        self.filter_profiles = GUI_MAIN_PREFERENCES.get("filter_profiles", {})
        self.default_filter_profile = GUI_MAIN_PREFERENCES.get("default_filter_profile")
        self.current_filter_profile = None
        self._profile_base_filters = {}
        self._profile_lock = False
        self._profile_columns = self._collect_profile_columns(self.filter_profiles)
        for extra_col in ("descricao_ssa",):
            if extra_col not in self._profile_columns:
                self._profile_columns.append(extra_col)
        self._column_or_groups = []
        self._column_to_or_group = {}
        self._exclude_ste_sca = False
        self._pending_search_display = ''

        # Configurações de GUI (independentes do CLI)
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        self._restored_page_size = gui_settings.get("page_size", 50)

        # Inicializa managers unificados (substitui codigo frankenstein)
        self.width_manager = SimpleWidthManager()
        self.cache_manager = SimpleCacheManager()

        # Estado de ordenaçção e filtros por coluna
        self.sort_column = None
        self.sort_ascending = True
        self._active_column_filters = OrderedDict()
        self._column_filter_inputs = {}
        self._column_filter_labels = {}
        self._pending_filter_focus = None
        self._current_theme = None
        self._highlight_bg_color = HIGHLIGHT_BACKGROUND_COLOR
        self._highlight_text_color = None
        self._highlight_font_weight = HIGHLIGHT_FONT_WEIGHT
        self._df_last_search_filtered = pd.DataFrame()
        adv_default = gui_settings.get("advanced_filters_default")
        self._advanced_filters = dict(adv_default) if isinstance(adv_default, dict) else {}
        self._advanced_filters_active = False
        self._adv_options_dirty = True
        self._last_derivada_origem = None
        self._adv_sector_syncing = False

        # Timer de debounce para otimização de filtros de setor (evita rebuilds excessivos)
        self._sector_debounce_timer = None
        self._sector_debounce_delay = 300  # ms

        self._initialize_profile_filter_placeholders()

        # Larguras salvas por coluna (das configurações JSON) - mantido para compatibilidade
        self._saved_gui_column_widths = GUI_MAIN_PREFERENCES.get("column_widths", {}).copy()

        # Debounce de filtro (da configuraçção JSON)
        debounce_delay = gui_settings.get("debounce_delay", 250)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_delay)
        self._debounce_timer.timeout.connect(self.initiate_filtering)

        # Filtros persistentes
        self.persistent_filters = []

        self.init_ui()

        # Carrega filtros apos a GUI estar configurada
        self.load_persistent_filters()
        # Aplica o tema preferido antes do auto-load
        preferred_theme = self._resolve_startup_theme()
        self.apply_theme(preferred_theme)
        try:
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = preferred_theme
            self._persist_gui_preferences()
        except Exception:
            pass
        # Aplica perfil inicial de filtros por setor
        self._apply_initial_filter_profile()

        # Auto-carregar dados na abertura (assáncrono, mantêm a janela responsiva)
        QTimer.singleShot(150, self.load_data)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)


        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()

        # Botões principais de dados
        self.load_button = QPushButton("Carregar Dados")
        self.load_button.setToolTip("Carregar dados do banco de dados existente")
        self.load_button.clicked.connect(self.load_data)
        toolbar_layout.addWidget(self.load_button)

        self.load_other_db_button = QPushButton("Carregar Outro DB")
        self.load_other_db_button.setToolTip("Selecionar e carregar outro arquivo de banco de dados")
        self.load_other_db_button.clicked.connect(self.load_other_database)
        toolbar_layout.addWidget(self.load_other_db_button)

        # Botões de ações
        self.rescan_button = QPushButton("Reescanear")
        self.rescan_button.setToolTip("Reprocessar arquivos Excel da pasta docs_entrada")
        self.rescan_button.clicked.connect(self.rescan_data)
        toolbar_layout.addWidget(self.rescan_button)

        self.explorer_button = QPushButton("Abrir Pasta")
        self.explorer_button.setToolTip("Abrir pasta docs_entrada no Windows Explorer")
        self.explorer_button.clicked.connect(self.open_docs_folder)
        toolbar_layout.addWidget(self.explorer_button)
        # Semana Atual (YYYYWW) ao lado de 'Abrir Pasta' (informativo, nção clicãvel)
        try:
            from datetime import date
            y, w, _ = date.today().isocalendar()
            week_str = f"{y}{w:02d}"
        except Exception:
            week_str = "-"
        self.week_label = QLabel(f"Semana Atual: {week_str}")
        # Destaque visual em caixa
        self._week_label_style = (
            "font-weight:600; border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        self.week_label.setStyleSheet(self._week_label_style)
        self.week_label.setToolTip("Semana ISO atual (nção clicãvel)")
        toolbar_layout.addSpacing(6)
        toolbar_layout.addWidget(self.week_label)

        # Espaçamento antes do status
        toolbar_layout.addStretch()

        # Status em caixa e progresso
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")
        self.status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)

        # Botção de Ajuda (como na PoC)
        help_button = QPushButton("Ajuda")
        help_button.setToolTip("Ajuda sobre filtros e uso da interface")
        help_button.clicked.connect(self.show_filter_help)
        toolbar_layout.addWidget(help_button)

        # Botção de Tema (Claro/Escuro/Gruvbox)
        theme_button = QPushButton("Tema")
        theme_button.setToolTip("Alterar tema (Claro/Escuro/Gruvbox)")
        theme_button.clicked.connect(self.toggle_theme_menu)
        toolbar_layout.addWidget(theme_button)

        main_layout.addLayout(toolbar_layout)
        self.main_tabs = QTabWidget()
        tab_main = QWidget()
        ctx_main = self._build_tab_content(tab_main, "main")
        self.main_tabs.addTab(tab_main, "SSAs")
        tab_filters = QWidget()
        ctx_filters = self._build_tab_content(tab_filters, "filters")
        self.main_tabs.addTab(tab_filters, "Filtros")
        self._tab_contexts = [ctx_main, ctx_filters]
        main_layout.addWidget(self.main_tabs)
        self.main_tabs.currentChanged.connect(self._on_tab_changed)
        self._bind_tab_context(ctx_main)

        # --- Conecta Workers / Flags ---
        # Threads iniciadas sob demanda
        self.data_loader_thread = None
        self.filter_thread = None
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in ("1", "true", "yes", "on")
        # Em ambiente de testes (pytest), force modo síncrono para previsibilidade
        if not self._sync_filtering and os.environ.get("PYTEST_CURRENT_TEST"):
            self._sync_filtering = True

        # Configura cache size da configuração
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        cache_size = gui_settings.get("filter_cache_size", 50)
        FilterWorker._cache = FilterCache(max_size=cache_size)

    def _build_tab_content(self, page: QWidget, tab_kind: str = "main") -> dict:
        tab_layout = QVBoxLayout(page)
        ctx = {}

        # Top spacing for search row
        tab_layout.addSpacing(6)

        # Search row
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        search_label = QLabel("Pesquisa Geral:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("Separe por virgulas (condicao E: todos os termos obrigatorios); ! exclui")
        search_input.setToolTip(
            "Condicao E: Todos os termos separados por virgula devem estar presentes.\n\n"
            "Modos por termo: \n"
            "- contem (padrao): foo\n- comeca com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex: ~foo.*bar\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
        )
        search_input.setMinimumWidth(425)
        search_input.setMaximumWidth(950)
        try:
            search_input.setMinimumHeight(26)
        except Exception:
            pass
        search_input.returnPressed.connect(self.initiate_filtering)
        search_input.textChanged.connect(self._on_search_text_changed)
        search_button = QPushButton("Aplicar")
        search_button.clicked.connect(self.initiate_filtering)
        clear_filter_button = QPushButton("Limpar Filtro")
        clear_filter_button.clicked.connect(self.clear_filter)
        clear_filter_button.setEnabled(False)
        left.addWidget(search_label)
        left.addWidget(search_input)
        left.addWidget(search_button)
        left.addWidget(clear_filter_button)

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        column_selector = ColumnSelector(
            self.display_map,
            self.visible_columns,
            default_columns=self.default_columns,
            available_columns=list(self.display_map.keys()),
            info_font=self._info_font,
        )
        column_selector.columns_changed.connect(self.on_columns_changed)
        right.addWidget(column_selector)

        search_row.addLayout(left)
        search_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        search_row.addLayout(right)
        tab_layout.addLayout(search_row)

        search_help = QLabel(
            "Separe por virgulas (logica E: todos os termos obrigatorios). Use ! para excluir. A busca vale para qualquer coluna."
        )
        search_help.setWordWrap(False)
        try:
            search_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        search_help.setStyleSheet("color: palette(mid); margin:0; padding:0;")
        try:
            search_help.setVisible(False)
        except Exception:
            pass
        tab_layout.addSpacing(4)

        # Pagination and persistent filters
        pagination_filters_layout = QHBoxLayout()
        pagination_filters_layout.setContentsMargins(0, 0, 0, 0)

        paginator = DataPaginator(self.df_para_tabela)
        paginator.page_changed.connect(self.display_current_page)
        pagination_filters_layout.addWidget(paginator)

        profile_layout = QHBoxLayout()
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(4)
        profile_label = QLabel("Perfil de filtro:")
        profile_selector = QComboBox()
        try:
            profile_selector.setMinimumWidth(150)
            profile_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        except Exception:
            pass
        profile_selector.addItem("Personalizado", None)
        for profile_name in self.filter_profiles.keys():
            profile_selector.addItem(profile_name, profile_name)
        profile_selector.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(profile_selector)
        pagination_filters_layout.addSpacing(12)
        pagination_filters_layout.addLayout(profile_layout)

        pagination_filters_layout.addSpacing(12)

        persistent_filters_layout = QHBoxLayout()
        persistent_filters_layout.setContentsMargins(0, 0, 0, 0)

        save_filter_button = QPushButton("Salvar Filtro")
        save_filter_button.setMaximumWidth(100)
        save_filter_button.setToolTip("Salvar filtro atual como persistente")
        save_filter_button.clicked.connect(self.save_current_filter)
        persistent_filters_layout.addWidget(save_filter_button)

        exclude_ste_checkbox = QCheckBox("Nao esta em STE/SCA")
        exclude_ste_checkbox.setToolTip("Oculta SSAs com situacao STE ou SCA")
        try:
            exclude_ste_checkbox.setChecked(False)
        except Exception:
            pass
        try:
            exclude_ste_checkbox.setVisible(False)
        except Exception:
            pass
        try:
            exclude_ste_checkbox.toggled.connect(self._on_exclude_ste_sca_toggled)
        except Exception:
            pass
        persistent_filters_layout.addWidget(exclude_ste_checkbox)

        filter_tags_widget = QWidget()
        filter_tags_layout = QHBoxLayout(filter_tags_widget)
        filter_tags_layout.setContentsMargins(0, 0, 0, 0)
        filter_tags_layout.setSpacing(5)
        persistent_filters_layout.addWidget(filter_tags_widget)

        pagination_filters_layout.addLayout(persistent_filters_layout)
        pagination_filters_layout.addStretch()

        col_filter_indicator = QLabel("")
        try:
            if self._info_font is not None:
                col_filter_indicator.setFont(QFont(self._info_font))
        except Exception:
            pass
        col_filter_indicator.setToolTip(
            "Filtros por coluna acumulam com a Pesquisa Geral (logica E entre filtros). "
            "Dentro de cada filtro, use virgulas para alternativas (logica OU). Consulte a ajuda para outros atalhos."
        )
        try:
            col_filter_indicator.setVisible(False)
        except Exception:
            pass

        tab_layout.addLayout(pagination_filters_layout)

        filters_summary_frame = None
        filters_summary_label = None
        clear_all_filters_btn = None
        export_list_btn = None
        undo_filter_btn = None
        try:
            filters_summary_frame = QFrame()
            filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
            summary_layout = QHBoxLayout(filters_summary_frame)
            summary_layout.setContentsMargins(6, 4, 6, 4)
            summary_layout.setSpacing(8)
            filters_summary_label = QLabel("Nenhum filtro ativo")
            if self._info_font is not None:
                try:
                    filters_summary_label.setFont(QFont(self._info_font))
                except Exception:
                    pass
            clear_all_filters_btn = QPushButton("Limpar todos os filtros")
            clear_all_filters_btn.setMaximumWidth(200)
            clear_all_filters_btn.clicked.connect(self._clear_all_filters_global)
            try:
                clear_all_filters_btn.setStyleSheet(self._week_label_style)
            except Exception:
                pass
            export_list_btn = QPushButton("Exportar lista")
            export_list_btn.setMaximumWidth(160)
            export_list_btn.setToolTip("Exportar lista atual para arquivo txt")
            export_list_btn.clicked.connect(self._export_current_list_txt)
            try:
                export_list_btn.setStyleSheet(self._week_label_style)
            except Exception:
                pass
            undo_filter_btn = QPushButton("Undo")
            undo_filter_btn.setMaximumWidth(160)
            undo_filter_btn.setToolTip("Desfaz o ultimo filtro aplicado")
            undo_filter_btn.clicked.connect(self._restore_last_filter_state)
            try:
                undo_filter_btn.setStyleSheet(self._week_label_style)
            except Exception:
                pass
            summary_layout.addWidget(clear_all_filters_btn, 0)
            summary_layout.addWidget(export_list_btn, 0)
            summary_layout.addWidget(undo_filter_btn, 0)
            summary_layout.addWidget(filters_summary_label, 1)
            tab_layout.addWidget(filters_summary_frame)
            filters_summary_frame.setVisible(True)
            try:
                self._update_undo_button_state()
            except Exception:
                pass
        except Exception:
            pass

        if isinstance(self._restored_page_size, int) and 10 <= self._restored_page_size <= 500:
            try:
                paginator.page_size_spinbox.setValue(self._restored_page_size)
            except Exception:
                pass
        try:
            paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)
        except Exception:
            pass

        # Table
        table_widget = QTableWidget()
        table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table_widget.verticalHeader().setVisible(False)
        table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table_widget.verticalHeader().setDefaultSectionSize(24)

        table_widget.doubleClicked.connect(self.on_table_double_click)
        table_widget.itemSelectionChanged.connect(self.update_details_from_selection)
        table_widget.horizontalHeader().sectionResized.connect(self._on_header_section_resized)

        try:
            header = table_widget.horizontalHeader()
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(True)
            try:
                header.setMinimumSectionSize(80)
                header.setDefaultSectionSize(100)
            except Exception:
                pass
            try:
                f = header.font()
                f.setBold(False)
                header.setFont(f)
                header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
            except Exception:
                pass
            header.sectionClicked.connect(self.on_header_clicked)
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(self.show_header_context_menu)
            header.installEventFilter(self)
        except Exception:
            pass

        table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_widget.customContextMenuRequested.connect(self.show_context_menu)

        tab_layout.addWidget(table_widget)

        # Details + column filters
        bottom_layout = QHBoxLayout()
        details_group = QGroupBox("Detalhes da SSA Selecionada")
        details_layout = QVBoxLayout(details_group)
        details_layout.setContentsMargins(2, 2, 2, 2)
        details_layout.setSpacing(2)
        details_text = QTextBrowser()
        try:
            details_text.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass
        try:
            details_text.viewport().setAutoFillBackground(False)
        except Exception:
            pass
        details_text.setReadOnly(True)
        try:
            details_text.setOpenExternalLinks(False)
            details_text.anchorClicked.connect(self._on_details_anchor_clicked)
        except Exception:
            pass
        details_layout.addWidget(details_text)
        bottom_layout.addWidget(details_group, 2)

        col_filters_group = QGroupBox("Filtros por Coluna")
        col_filters_outer = QVBoxLayout(col_filters_group)
        col_filters_hint = QLabel("Use virgulas para alternativas (logica OU dentro da coluna). Entre colunas mantemos logica E.")
        try:
            col_filters_hint.setStyleSheet("color: palette(windowText); font-size: 11px;")
        except Exception:
            pass
        col_filters_outer.addWidget(col_filters_hint)
        col_filters_scroll = QScrollArea()
        col_filters_scroll.setWidgetResizable(True)
        col_filters_container = QWidget()
        col_filters_list_layout = QVBoxLayout(col_filters_container)
        col_filters_scroll.setWidget(col_filters_container)
        col_filters_outer.addWidget(col_filters_scroll, 1)
        footer = QHBoxLayout()
        footer.addStretch()
        add_column_filter_btn = QPushButton("Adicionar filtro de coluna")
        add_column_filter_btn.setMaximumWidth(260)
        add_column_filter_btn.setToolTip("Selecionar coluna visivel para ativar filtro dedicado")
        add_column_filter_btn.clicked.connect(self._open_add_column_filter_menu)
        footer.addWidget(add_column_filter_btn)
        footer.addSpacing(8)
        clear_all_btn = QPushButton("Limpar todos filtros de colunas")
        clear_all_btn.setMaximumWidth(260)
        clear_all_btn.clicked.connect(self._clear_all_column_filters)
        footer.addWidget(clear_all_btn)
        footer.addStretch()
        col_filters_outer.addLayout(footer)

        right_col_widget = QWidget()
        right_col = QVBoxLayout(right_col_widget)
        right_col.setContentsMargins(0, 0, 0, 0)
        if tab_kind == "filters":
            adv_group, adv_ctx = self._build_advanced_filters_panel()
            right_col.addWidget(adv_group, 1)
            col_filters_group.setVisible(False)
            right_col.addWidget(col_filters_group)
            # APENAS na aba Filtros: Detalhes max 40% (2) vs Filtros 60% (3)
            bottom_layout.addWidget(right_col_widget, 3)
        else:
            right_col.addWidget(col_filters_group)
            # CORRECAO 2026-01-08: Aba SSAs com proporcao 50/50 (igual stretch)
            # Detalhes ja tem stretch=2, filtros coluna tambem com stretch=2
            bottom_layout.addWidget(right_col_widget, 2)

        tab_layout.addSpacing(12)
        tab_layout.addLayout(bottom_layout)

        ctx.update(
            {
                "search_label": search_label,
                "search_input": search_input,
                "search_button": search_button,
                "clear_filter_button": clear_filter_button,
                "column_selector": column_selector,
                "search_help": search_help,
                "paginator": paginator,
                "profile_selector": profile_selector,
                "persistent_filters_layout": persistent_filters_layout,
                "filter_tags_widget": filter_tags_widget,
                "filter_tags_layout": filter_tags_layout,
                "exclude_ste_checkbox": exclude_ste_checkbox,
                "col_filter_indicator": col_filter_indicator,
                "filters_summary_frame": filters_summary_frame,
                "filters_summary_label": filters_summary_label,
                "clear_all_filters_btn": clear_all_filters_btn,
                "export_list_btn": export_list_btn,
                "undo_filter_btn": undo_filter_btn,
                "table_widget": table_widget,
                "details_group": details_group,
                "details_text": details_text,
                "col_filters_group": col_filters_group,
                "col_filters_hint": col_filters_hint,
                "col_filters_scroll": col_filters_scroll,
                "col_filters_container": col_filters_container,
                "col_filters_list_layout": col_filters_list_layout,
                "add_column_filter_btn": add_column_filter_btn,
                "clear_all_btn": clear_all_btn,
                "tab_kind": tab_kind,
            }
        )
        if tab_kind == "filters":
            self._adv_ctx = adv_ctx
            ctx.update(adv_ctx)
        return ctx

    def _bind_tab_context(self, ctx: dict) -> None:
        self._current_tab_kind = ctx.get("tab_kind")
        for name in self.TAB_WIDGET_ATTRS:
            if name in ctx:
                setattr(self, name, ctx[name])
        try:
            active_text = self.search_input.text().strip()
            self.clear_filter_button.setEnabled(bool(active_text))
        except Exception:
            pass
        try:
            if ctx.get("tab_kind") == "filters":
                self.search_input.blockSignals(True)
                self.search_input.clear()
                self.clear_filter_button.setEnabled(False)
        except Exception:
            pass
        finally:
            try:
                if ctx.get("tab_kind") == "filters":
                    self.search_input.blockSignals(False)
            except Exception:
                pass

        tab_kind = ctx.get("tab_kind")
        try:
            if tab_kind == "filters" and hasattr(self, "adv_filters_group") and self.adv_filters_group is not None:
                if getattr(self, "_adv_options_dirty", False) or not getattr(self, "_adv_values_cache", None):
                    try:
                        self._refresh_advanced_filter_options()
                        self._adv_options_dirty = False
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            if hasattr(self, "exclude_ste_checkbox") and not self.exclude_ste_checkbox.isVisible():
                self._exclude_ste_sca = False
        except Exception:
            pass

        try:
            if self.current_filter_profile:
                idx = self.profile_selector.findData(self.current_filter_profile)
            else:
                idx = 0
            if idx >= 0:
                self.profile_selector.blockSignals(True)
                self.profile_selector.setCurrentIndex(idx)
        except Exception:
            pass
        finally:
            try:
                self.profile_selector.blockSignals(False)
            except Exception:
                pass

        try:
            self.column_selector.set_selected_columns(self.visible_columns)
        except Exception:
            pass

        try:
            df_id = id(self.df_exibido)
            if ctx.get("_paginator_df_id") != df_id:
                self.paginator.set_dataframe(self.df_exibido)
                ctx["_paginator_df_id"] = df_id
        except Exception:
            pass
        try:
            if tab_kind != "filters":
                self._build_column_filters_panel()
        except Exception:
            pass
        try:
            if tab_kind != "filters":
                self._update_col_filter_indicator()
        except Exception:
            pass
        try:
            self._update_filters_summary()
        except Exception:
            pass
        try:
            self._update_undo_button_state()
        except Exception:
            pass
        try:
            if tab_kind != "filters":
                self.update_filter_tags()
        except Exception:
            pass
        try:
            current_theme = getattr(self, "_current_theme", None)
            if current_theme and ctx.get("_theme_name") != current_theme:
                self.apply_theme(current_theme)
                ctx["_theme_name"] = current_theme
        except Exception:
            pass
        try:
            current_page = max(1, getattr(self.paginator, "current_page", 1))
            render_key = (id(self.df_exibido), current_page, tuple(self.visible_columns))
            if ctx.get("_last_render_key") != render_key:
                ctx["_last_render_key"] = render_key
                self.display_current_page(current_page)
        except Exception:
            pass

    def _sync_checks_to_tab_context(self):
        """Mantem o contexto da aba Filtros com as listas de checkboxes reconstruidas."""
        try:
            if not hasattr(self, "_tab_contexts"):
                return
            filters_ctx = None
            for ctx in self._tab_contexts:
                if ctx.get("tab_kind") == "filters":
                    filters_ctx = ctx
                    break
            if filters_ctx is None:
                return

            synced = 0
            for attr, value in vars(self).items():
                if not attr.startswith("adv_") or not attr.endswith("_checks"):
                    continue
                if value is None:
                    continue
                filters_ctx[attr] = value
                synced += 1
            logger.debug("_sync_checks_to_tab_context: %s atributos sincronizados", synced)
        except Exception as e:
            logger.error("Erro em _sync_checks_to_tab_context: %s", e)

    def _schedule_adv_options_refresh(self):
        if getattr(self, "_adv_options_scheduled", False):
            return
        self._adv_options_scheduled = True
        try:
            QTimer.singleShot(0, self._run_adv_options_refresh)
        except Exception:
            self._adv_options_scheduled = False
            try:
                self._run_adv_options_refresh()
            except Exception:
                pass

    def _run_adv_options_refresh(self):
        self._adv_options_scheduled = False
        if getattr(self, "_current_tab_kind", None) != "filters":
            return
        if not getattr(self, "_adv_options_dirty", False):
            return
        try:
            self._refresh_advanced_filter_options()
            self._adv_options_dirty = False
        except Exception:
            pass

    def _on_tab_changed(self, index: int) -> None:
        if not hasattr(self, "_tab_contexts"):
            return
        if index < 0 or index >= len(self._tab_contexts):
            return
        ctx = self._tab_contexts[index]
        self._bind_tab_context(ctx)

    def _make_multiselect_box(self, title: str, placeholder: str = "Selecionar", with_exclude: bool = True):
        box = QGroupBox(title)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        button = QToolButton()
        button.setText(placeholder)
        try:
            button.setMaximumWidth(100)
        except Exception:
            pass
        try:
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        menu = QMenu(button)
        try:
            menu.setMaximumHeight(360)
        except Exception:
            pass
        self._attach_multiselect_menu(button, menu)
        button.setToolTip(placeholder)
        try:
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        except Exception:
            pass
        exclude = None
        if with_exclude:
            exclude = QCheckBox("Diferente")
            try:
                exclude.setVisible(False)
            except Exception:
                pass
        layout.addWidget(button, 1)
        return box, button, menu, exclude

    def _attach_multiselect_menu(self, button, menu):
        if button is None or menu is None:
            return
        def _show_menu():
            try:
                rect = button.rect()
                pos = button.mapToGlobal(rect.bottomLeft())
                try:
                    menu_size = menu.sizeHint()
                    screen = QApplication.primaryScreen().geometry()
                    if menu_size and screen and pos.y() + menu_size.height() > screen.bottom():
                        pos = button.mapToGlobal(rect.topLeft())
                        pos.setY(pos.y() - menu_size.height())
                except Exception:
                    pass
                menu.exec(pos)
                return
            except Exception:
                pass
        try:
            button.clicked.connect(_show_menu)
        except Exception:
            pass

    def _update_multiselect_button(self, button, checks, placeholder: str = "Selecionar", exclude_checks=None):
        if button is None:
            return
        selected = []
        for cb in checks or []:
            try:
                if not _is_widget_valid(cb):
                    continue
                if cb.isChecked():
                    value = self._checkbox_value(cb)
                    if value:
                        selected.append(value)
            except Exception:
                pass
        excluded = []
        for cb in exclude_checks or []:
            try:
                if not _is_widget_valid(cb):
                    continue
                if cb.isChecked():
                    value = self._checkbox_value(cb)
                    if value:
                        excluded.append(value)
            except Exception:
                pass
        total = len(checks or [])
        if total == 0:
            text = "Sem dados"
        elif not selected and not excluded:
            text = placeholder
        elif len(selected) == total and not excluded:
            text = "Todos"
        elif selected and excluded:
            text = f"{len(selected)} inc, {len(excluded)} dif"
        elif selected:
            text = f"{len(selected)} incluir"
        elif excluded:
            text = f"{len(excluded)} diferente"
        else:
            text = f"{len(selected)} selecionados"
        try:
            button.setText(text)
            # Esmaecimento visual para botoes sem dados
            if total == 0:
                button.setEnabled(False)
                button.setStyleSheet("color: #888; background-color: #f0f0f0;")
            else:
                button.setEnabled(True)
                button.setStyleSheet("")  # Remove estilo customizado
            if selected or excluded:
                button.setToolTip(
                    "Incluir: " + ", ".join(selected) + ("\nDiferente: " + ", ".join(excluded) if excluded else "")
                )
            else:
                button.setToolTip(placeholder if total > 0 else "Nenhum dado disponivel")
        except Exception:
            pass

    def _rebuild_multiselect_menu(
        self,
        button,
        menu,
        values,
        selected_set,
        on_toggle=None,
        on_apply=None,
        exclude_selected_set=None,
        on_exclude_toggle=None,
    ):
        try:
            menu.clear()
        except Exception:
            pass
        selected_norm = {str(v).casefold() for v in (selected_set or [])}
        exclude_norm = {str(v).casefold() for v in (exclude_selected_set or [])}
        checks = []
        exclude_checks = []

        # Obter nome do filtro do titulo do GroupBox pai (subindo na hierarquia)
        filter_name = ""
        try:
            parent = button.parent()
            while parent is not None:
                if isinstance(parent, QGroupBox):
                    candidate = parent.title()
                    # Ignorar titulos genericos como "Valores"
                    if candidate and candidate not in ("Valores", ""):
                        filter_name = candidate
                        break
                parent = parent.parent()
        except Exception:
            pass

        try:
            try:
                max_label_len = max((len(str(v)) for v in values), default=4)
            except Exception:
                max_label_len = 4
            computed = max_label_len * 8 + 70
            min_width = max(int(getattr(button, "width", lambda: 0)() or 0), min(360, max(160, computed)))
            menu.setMinimumWidth(min_width)
        except Exception:
            pass

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(6, 4, 14, 4)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        try:
            grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        except Exception:
            pass
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        row_idx = 0

        # Header com nome do filtro (sempre) e colunas == / != (so quando tem exclude)
        if filter_name:
            label_filter = QLabel(filter_name)
            try:
                label_filter.setStyleSheet("font-weight: bold; font-size: 11px;")
            except Exception:
                pass
            grid.addWidget(label_filter, row_idx, 0)

            if exclude_selected_set is not None:
                label_inc = QLabel("==")
                label_exc = QLabel("!=")
                try:
                    # == com destaque (borda), != sem destaque (invertido conforme solicitado)
                    label_inc.setStyleSheet("font-size: 10px; color: #888; border: 1px solid #aaa; border-radius: 2px; padding: 1px 3px;")
                    label_exc.setStyleSheet("font-size: 10px; color: #555;")
                    label_inc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                    label_exc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                except Exception:
                    pass
                grid.addWidget(label_inc, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
                grid.addWidget(label_exc, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
            row_idx += 1

            # Separador entre header e conteudo
            header_sep = QFrame()
            header_sep.setFrameShape(QFrame.Shape.HLine)
            header_sep.setFrameShadow(QFrame.Shadow.Sunken)
            col_span = 3 if exclude_selected_set is not None else 1
            grid.addWidget(header_sep, row_idx, 0, 1, col_span)
            row_idx += 1

        # Estilo para checkboxes com indicacao visual clara quando marcados
        # CORRECAO 2026-01-08: Adicionado estilo :checked para feedback visual
        cb_style_include = """
            QCheckBox::indicator {
                background-color: #f0f0f0;
                border: 1px solid #888;
                border-radius: 2px;
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:checked {
                background-color: #4a90d9;
                border: 1px solid #2a70b9;
                image: none;
            }
        """
        cb_style_exclude = """
            QCheckBox::indicator {
                background-color: #f5f5f5;
                border: 1px solid #bbb;
                border-radius: 2px;
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:checked {
                background-color: #d94a4a;
                border: 1px solid #b92a2a;
                image: none;
            }
        """

        for val in values:
            label_text = str(val[1]) if isinstance(val, (list, tuple)) and len(val) > 1 else str(val)
            cb_value = val[0] if isinstance(val, (list, tuple)) and len(val) > 0 else val
            # Ignorar valores vazios ou apenas espacos
            if not label_text or not label_text.strip():
                continue
            label = QLabel(label_text)
            try:
                label.setStyleSheet("font-size: 11px;")
            except Exception:
                pass
            include_cb = QCheckBox()
            exclude_cb = QCheckBox() if exclude_selected_set is not None else None
            try:
                include_cb.setProperty("value", str(cb_value))
                include_cb.setStyleSheet(cb_style_include)
            except Exception:
                pass
            if exclude_cb is not None:
                try:
                    exclude_cb.setProperty("value", str(cb_value))
                    exclude_cb.setStyleSheet(cb_style_exclude)
                except Exception:
                    pass
            try:
                include_cb.setChecked(str(cb_value).casefold() in selected_norm)
            except Exception:
                pass
            if exclude_cb is not None:
                try:
                    exclude_cb.setChecked(str(cb_value).casefold() in exclude_norm)
                except Exception:
                    pass
            grid.addWidget(label, row_idx, 0)
            grid.addWidget(include_cb, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
            if exclude_cb is not None:
                grid.addWidget(exclude_cb, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
            row_idx += 1
            checks.append(include_cb)
            if exclude_cb is not None:
                exclude_checks.append(exclude_cb)
            if exclude_cb is not None:
                def _toggle_include(checked, other=exclude_cb):
                    if checked and _is_widget_valid(other) and other.isChecked():
                        other.setChecked(False)
                def _toggle_exclude(checked, other=include_cb):
                    if checked and _is_widget_valid(other) and other.isChecked():
                        other.setChecked(False)
                try:
                    include_cb.toggled.connect(_toggle_include)
                    exclude_cb.toggled.connect(_toggle_exclude)
                except Exception:
                    pass
            if on_toggle is not None:
                try:
                    include_cb.toggled.connect(on_toggle)
                except Exception:
                    pass
            if exclude_cb is not None and on_exclude_toggle is not None:
                try:
                    exclude_cb.toggled.connect(on_exclude_toggle)
                except Exception:
                    pass

        # Separador antes de Selecionar/Desmarcar
        if exclude_selected_set is not None:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            grid.addWidget(separator, row_idx, 0, 1, 3)
            row_idx += 1

            # Selecionar/Desmarcar ao fim da lista
            select_all_include = QCheckBox()
            deselect_all_include = QCheckBox()
            select_all_exclude = QCheckBox()
            deselect_all_exclude = QCheckBox()

            for cb in [select_all_include, deselect_all_include]:
                cb.setStyleSheet(cb_style_include)
            for cb in [select_all_exclude, deselect_all_exclude]:
                cb.setStyleSheet(cb_style_exclude)

            label_select = QLabel("Selecionar tudo")
            label_deselect = QLabel("Desmarcar tudo")
            try:
                label_select.setStyleSheet("font-size: 11px;")
                label_deselect.setStyleSheet("font-size: 11px;")
            except Exception:
                pass

            grid.addWidget(label_select, row_idx, 0)
            grid.addWidget(select_all_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
            grid.addWidget(select_all_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
            row_idx += 1

            grid.addWidget(label_deselect, row_idx, 0)
            grid.addWidget(deselect_all_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
            grid.addWidget(deselect_all_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
            row_idx += 1

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
        except Exception:
            pass
        try:
            from PyQt6.QtGui import QPalette as _QPal
            pal = (button or scroll).palette()
            border = pal.color(_QPal.ColorRole.Mid).name()
            bg = pal.color(_QPal.ColorRole.Base).name()
            container.setStyleSheet(f"QWidget {{ background: {bg}; }} QLabel {{ font-size: 11px; }}")
            scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {border}; }}")
        except Exception:
            pass
        try:
            scroll.setFixedHeight(320)
        except Exception:
            pass
        scroll_act = QWidgetAction(menu)
        scroll_act.setDefaultWidget(scroll)
        try:
            menu.addAction(scroll_act)
        except Exception:
            pass

        # Conectar funcionalidade de Selecionar/Desmarcar Tudo com blockSignals
        # CORRECAO 2026-01-08: Reset do checkbox apos acao para feedback visual correto
        if exclude_selected_set is not None:
            def _select_all_include():
                for cb in checks:
                    cb.blockSignals(True)
                    cb.setChecked(True)
                    cb.blockSignals(False)
                # Reset checkbox de acao apos executar
                select_all_include.blockSignals(True)
                select_all_include.setChecked(False)
                select_all_include.blockSignals(False)
                if on_toggle:
                    on_toggle()

            def _deselect_all_include():
                for cb in checks:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
                # Reset checkbox de acao apos executar
                deselect_all_include.blockSignals(True)
                deselect_all_include.setChecked(False)
                deselect_all_include.blockSignals(False)
                if on_toggle:
                    on_toggle()

            def _select_all_exclude():
                for cb in exclude_checks:
                    cb.blockSignals(True)
                    cb.setChecked(True)
                    cb.blockSignals(False)
                # Reset checkbox de acao apos executar
                select_all_exclude.blockSignals(True)
                select_all_exclude.setChecked(False)
                select_all_exclude.blockSignals(False)
                if on_exclude_toggle:
                    on_exclude_toggle()

            def _deselect_all_exclude():
                for cb in exclude_checks:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
                # Reset checkbox de acao apos executar
                deselect_all_exclude.blockSignals(True)
                deselect_all_exclude.setChecked(False)
                deselect_all_exclude.blockSignals(False)
                if on_exclude_toggle:
                    on_exclude_toggle()

            try:
                select_all_include.toggled.connect(lambda checked: _select_all_include() if checked else None)
                deselect_all_include.toggled.connect(lambda checked: _deselect_all_include() if checked else None)
                select_all_exclude.toggled.connect(lambda checked: _select_all_exclude() if checked else None)
                deselect_all_exclude.toggled.connect(lambda checked: _deselect_all_exclude() if checked else None)
            except Exception:
                pass

        # Botoes OK e Cancelar - OK sempre a direita
        # OTIMIZACAO 2026-01-08: OK apenas fecha o menu, NAO aplica filtro
        # A aplicacao fica para o botao "Aplicar" geral (evita recalculagens por toggle)
        if on_apply is not None:
            cancel_btn = QPushButton("Cancelar")
            cancel_btn.setFixedWidth(70)
            cancel_btn.setToolTip("Fechar sem aplicar")
            ok_btn = QPushButton("OK")
            ok_btn.setFixedWidth(70)
            ok_btn.setToolTip("Confirmar selecao (use botao Aplicar para filtrar)")
            try:
                cancel_btn.clicked.connect(menu.close)
            except Exception:
                pass
            try:
                ok_btn.clicked.connect(menu.close)
                # REMOVIDO: ok_btn.clicked.connect(on_apply)
                # Agora o filtro so e aplicado pelo botao "Aplicar" geral
            except Exception:
                pass
            ok_row = QWidget()
            ok_layout = QHBoxLayout(ok_row)
            ok_layout.setContentsMargins(6, 4, 6, 6)
            ok_layout.addStretch()
            ok_layout.addWidget(cancel_btn)
            ok_layout.addSpacing(8)
            ok_layout.addWidget(ok_btn)
            ok_act = QWidgetAction(menu)
            ok_act.setDefaultWidget(ok_row)
            try:
                menu.addAction(ok_act)
            except Exception:
                pass
        self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)
        if exclude_selected_set is not None:
            return checks, exclude_checks
        return checks, []

    def _checkbox_value(self, checkbox) -> str:
        try:
            text = checkbox.text()
            if text:
                return text
        except Exception:
            pass
        try:
            value = checkbox.property("value")
            if value is not None:
                return str(value)
        except Exception:
            pass
        return ""

    def _sync_multiselect_checks(self, button, checks, selected, exclude_checks=None, exclude_selected=None):
        selected_set = {str(v).casefold() for v in (selected or [])}
        for cb in checks or []:
            try:
                cb.setChecked(self._checkbox_value(cb).casefold() in selected_set)
            except Exception:
                pass
        exclude_set = {str(v).casefold() for v in (exclude_selected or [])}
        for cb in exclude_checks or []:
            try:
                cb.setChecked(self._checkbox_value(cb).casefold() in exclude_set)
            except Exception:
                pass
        self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)

    def _build_advanced_filters_panel(self):
        group = QGroupBox("Filtros Avancados")
        outer = QVBoxLayout(group)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(2)

        # Container para grid (preparado para scroll futuro)
        grid_container = QWidget()
        grid_container_layout = QVBoxLayout(grid_container)
        grid_container_layout.setContentsMargins(0, 0, 0, 0)
        grid_container_layout.setSpacing(0)

        emis_box, emis_button, emis_menu, emis_exclude = self._make_multiselect_box("Emissor")
        exec_box, exec_button, exec_menu, exec_exclude = self._make_multiselect_box("Executor")
        div_box, div_button, div_menu, div_exclude = self._make_multiselect_box("Divisao")
        status_box, status_button, status_menu, status_exclude = self._make_multiselect_box("Situacao")
        year_emissao_box, year_emissao_button, year_emissao_menu, _ = self._make_multiselect_box("Ano Emissao", with_exclude=False)
        year_execucao_box, year_execucao_button, year_execucao_menu, _ = self._make_multiselect_box("Ano Execucao", with_exclude=False)

        reprog_box = QGroupBox("Reprogramacoes")
        reprog_layout = QHBoxLayout(reprog_box)
        reprog_layout.setContentsMargins(2, 1, 2, 1)
        reprog_layout.setSpacing(2)
        reprog_mode = QComboBox()
        reprog_mode.addItem("= Igual", "eq")
        reprog_mode.addItem("<= Menor", "lte")
        reprog_mode.addItem(">= Maior", "gte")
        try:
            reprog_mode.setFixedWidth(80)
        except Exception:
            pass
        reprog_layout.addWidget(reprog_mode)
        reprog_menu_box, reprog_button, reprog_menu, _ = self._make_multiselect_box("Valores", with_exclude=False)
        try:
            reprog_button.setFixedWidth(80)
        except Exception:
            pass
        reprog_layout.addWidget(reprog_button, 1)
        self.adv_reprog_mode = reprog_mode
        self.adv_reprog_button = reprog_button
        self.adv_reprog_menu = reprog_menu
        self.adv_reprog_checks = []

        prio_emis_box, prio_emis_button, prio_emis_menu, _ = self._make_multiselect_box("Prio. Emissao")
        prio_plan_box, prio_plan_button, prio_plan_menu, _ = self._make_multiselect_box("Prio. Planejamento")

        deriv_box = QGroupBox("Derivadas")
        deriv_layout = QHBoxLayout(deriv_box)
        deriv_layout.setContentsMargins(2, 1, 2, 1)
        deriv_layout.setSpacing(2)
        deriv_has = QCheckBox("Tem")
        deriv_all_ste = QCheckBox("STE")
        deriv_is = QCheckBox("Sou Derivada")
        derivadas_select_btn = QPushButton("Especificas...")
        try:
            derivadas_select_btn.setMaximumWidth(100)
            derivadas_select_btn.setEnabled(False)  # Habilitado quando existir derivadas
        except Exception:
            pass
        derivadas_select_btn.setToolTip("Ver arvore de derivadas (habilitado quando existirem derivadas na lista)")
        try:
            derivadas_select_btn.clicked.connect(self._show_derivadas_popup)
        except Exception:
            pass
        try:
            deriv_has.toggled.connect(lambda checked: self._on_derivada_has_toggled(checked))
            deriv_all_ste.toggled.connect(lambda checked: self._on_derivada_all_ste_toggled(checked))
        except Exception:
            pass
        deriv_layout.addWidget(deriv_has)
        deriv_layout.addWidget(deriv_all_ste)
        deriv_layout.addWidget(deriv_is)
        deriv_layout.addWidget(derivadas_select_btn)
        deriv_layout.addStretch()

        week_emis_box = QGroupBox("Emissao (AnoSemana)")
        week_emis_layout = QHBoxLayout(week_emis_box)
        week_emis_layout.setContentsMargins(2, 1, 2, 1)
        week_emis_layout.setSpacing(2)
        week_emissao_start = QLineEdit()
        week_emissao_start.setPlaceholderText("Ini")
        try:
            week_emissao_start.setMaxLength(6)
            week_emissao_start.setFixedWidth(60)
        except Exception:
            pass
        week_emissao_end = QLineEdit()
        week_emissao_end.setPlaceholderText("Fim")
        try:
            week_emissao_end.setMaxLength(6)
            week_emissao_end.setFixedWidth(60)
        except Exception:
            pass
        week_emissao_exclude = None
        week_emis_layout.addWidget(week_emissao_start)
        week_emis_layout.addWidget(week_emissao_end)

        week_exec_box = QGroupBox("Execucao (AnoSemana)")
        week_exec_layout = QHBoxLayout(week_exec_box)
        week_exec_layout.setContentsMargins(2, 1, 2, 1)
        week_exec_layout.setSpacing(2)
        week_exec_start = QLineEdit()
        week_exec_start.setPlaceholderText("Ini")
        try:
            week_exec_start.setMaxLength(6)
            week_exec_start.setFixedWidth(60)
        except Exception:
            pass
        week_exec_end = QLineEdit()
        week_exec_end.setPlaceholderText("Fim")
        try:
            week_exec_end.setMaxLength(6)
            week_exec_end.setFixedWidth(60)
        except Exception:
            pass
        week_exec_exclude = None
        week_exec_layout.addWidget(week_exec_start)
        week_exec_layout.addWidget(week_exec_end)

        macro_box = QGroupBox("Macro")
        macro_layout = QHBoxLayout(macro_box)
        macro_layout.setContentsMargins(2, 1, 2, 1)
        macro_combo = QComboBox()
        try:
            macro_combo.setMinimumWidth(100)
        except Exception:
            pass
        macro_combo.addItem("Nenhum", None)
        macro_combo.addItem("Baixar", "ssas_para_baixar")
        macro_combo.currentIndexChanged.connect(self._on_macro_filter_changed)
        macro_layout.addWidget(macro_combo)

        sol_box, sol_button, sol_menu, sol_exclude = self._make_multiselect_box("Solicitante")
        prog_box, prog_button, prog_menu, prog_exclude = self._make_multiselect_box("Resp Prog")
        exec_resp_box, exec_resp_button, exec_resp_menu, exec_resp_exclude = self._make_multiselect_box("Resp Exec")
        emis_resp_box, emis_resp_button, emis_resp_menu, emis_resp_exclude = self._make_multiselect_box("Resp Emis")

        main_grid = QGridLayout()
        main_grid.setContentsMargins(0, 0, 0, 0)
        main_grid.setHorizontalSpacing(4)
        main_grid.setVerticalSpacing(8)  # Espacamento entre linhas para conforto visual
        main_grid.addWidget(emis_box, 0, 0)
        main_grid.addWidget(exec_box, 0, 1)
        main_grid.addWidget(div_box, 0, 2)
        main_grid.addWidget(status_box, 0, 3)
        main_grid.addWidget(year_emissao_box, 0, 4)
        main_grid.addWidget(year_execucao_box, 0, 5)
        main_grid.addWidget(reprog_box, 1, 0)
        main_grid.addWidget(prio_emis_box, 1, 1)
        main_grid.addWidget(prio_plan_box, 1, 2)
        main_grid.addWidget(deriv_box, 1, 3, 1, 2)
        main_grid.addWidget(macro_box, 1, 5)
        main_grid.addWidget(week_emis_box, 2, 0)
        main_grid.addWidget(week_exec_box, 2, 1)
        main_grid.addWidget(sol_box, 2, 2)
        main_grid.addWidget(prog_box, 2, 3)
        main_grid.addWidget(exec_resp_box, 2, 4)
        main_grid.addWidget(emis_resp_box, 2, 5)
        for col in range(6):
            main_grid.setColumnStretch(col, 1)

        # Adiciona grid ao container
        grid_container_layout.addLayout(main_grid)
        outer.addWidget(grid_container, 1)

        # Armazena referencia ao grid para reorganizacao responsiva
        self._adv_filters_main_grid = main_grid
        self._adv_filters_grid_widgets = {
            "emis_box": emis_box, "exec_box": exec_box, "div_box": div_box,
            "status_box": status_box, "year_emissao_box": year_emissao_box,
            "year_execucao_box": year_execucao_box, "reprog_box": reprog_box,
            "prio_emis_box": prio_emis_box, "prio_plan_box": prio_plan_box,
            "deriv_box": deriv_box, "macro_box": macro_box,
            "week_emis_box": week_emis_box, "week_exec_box": week_exec_box,
            "sol_box": sol_box, "prog_box": prog_box,
            "exec_resp_box": exec_resp_box, "emis_resp_box": emis_resp_box
        }

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 2, 0, 0)
        buttons_row.addStretch()
        apply_btn = QPushButton("Aplicar")
        clear_btn = QPushButton("Limpar")
        save_defaults_btn = QPushButton("Salvar padrao")
        apply_btn.clicked.connect(self._apply_advanced_filters_from_ui)
        clear_btn.clicked.connect(self._clear_advanced_filters)
        save_defaults_btn.clicked.connect(self._save_advanced_filters_default)
        buttons_row.addWidget(apply_btn)
        buttons_row.addSpacing(4)
        buttons_row.addWidget(clear_btn)
        buttons_row.addSpacing(4)
        buttons_row.addWidget(save_defaults_btn)
        buttons_row.addStretch()

        outer.addLayout(buttons_row)

        ctx = {
            "adv_filters_group": group,
            "adv_executor_button": exec_button,
            "adv_executor_menu": exec_menu,
            "adv_executor_checks": [],
            "adv_executor_exclude": exec_exclude,
            "adv_emissor_button": emis_button,
            "adv_emissor_menu": emis_menu,
            "adv_emissor_checks": [],
            "adv_emissor_exclude": emis_exclude,
            "adv_divisao_button": div_button,
            "adv_divisao_menu": div_menu,
            "adv_divisao_checks": [],
            "adv_divisao_exclude": div_exclude,
            "adv_status_button": status_button,
            "adv_status_menu": status_menu,
            "adv_status_checks": [],
            "adv_status_exclude": status_exclude,
            "adv_year_emissao_button": year_emissao_button,
            "adv_year_emissao_menu": year_emissao_menu,
            "adv_year_emissao_checks": [],
            "adv_year_execucao_button": year_execucao_button,
            "adv_year_execucao_menu": year_execucao_menu,
            "adv_year_execucao_checks": [],
            "adv_reprog_box": reprog_box,
            "adv_reprog_mode": reprog_mode,
            "adv_reprog_button": reprog_button,
            "adv_reprog_menu": reprog_menu,
            "adv_reprog_checks": [],
            "adv_week_emissao_start": week_emissao_start,
            "adv_week_emissao_end": week_emissao_end,
            "adv_week_emissao_exclude": week_emissao_exclude,
            "adv_week_execucao_start": week_exec_start,
            "adv_week_execucao_end": week_exec_end,
            "adv_week_execucao_exclude": week_exec_exclude,
            "adv_prioridade_emissao_button": prio_emis_button,
            "adv_prioridade_emissao_menu": prio_emis_menu,
            "adv_prioridade_emissao_checks": [],
            "adv_prioridade_planejamento_button": prio_plan_button,
            "adv_prioridade_planejamento_menu": prio_plan_menu,
            "adv_prioridade_planejamento_checks": [],
            "adv_derivada_has": deriv_has,
            "adv_derivada_all_ste": deriv_all_ste,
            "adv_derivada_is": deriv_is,
            "adv_derivadas_especificas_button": derivadas_select_btn,
            "adv_responsavel_solicitante_button": sol_button,
            "adv_responsavel_solicitante_menu": sol_menu,
            "adv_responsavel_solicitante_checks": [],
            "adv_responsavel_solicitante_exclude": sol_exclude,
            "adv_responsavel_solicitante_box": sol_box,
            "adv_responsavel_programacao_button": prog_button,
            "adv_responsavel_programacao_menu": prog_menu,
            "adv_responsavel_programacao_checks": [],
            "adv_responsavel_programacao_exclude": prog_exclude,
            "adv_responsavel_programacao_box": prog_box,
            "adv_responsavel_execucao_button": exec_resp_button,
            "adv_responsavel_execucao_menu": exec_resp_menu,
            "adv_responsavel_execucao_checks": [],
            "adv_responsavel_execucao_exclude": exec_resp_exclude,
            "adv_responsavel_execucao_box": exec_resp_box,
            "adv_responsavel_emissor_button": emis_resp_button,
            "adv_responsavel_emissor_menu": emis_resp_menu,
            "adv_responsavel_emissor_checks": [],
            "adv_responsavel_emissor_exclude": emis_resp_exclude,
            "adv_responsavel_emissor_box": emis_resp_box,
            "adv_macro_combo": macro_combo,
            "adv_save_defaults_btn": save_defaults_btn,
        }
        return group, ctx

    def _on_derivada_has_toggled(self, checked: bool):
        """Quando 'Tem' é desmarcado, 'STE' também deve ser desmarcado."""
        if not checked:
            try:
                if hasattr(self, "adv_derivada_all_ste") and self.adv_derivada_all_ste.isChecked():
                    self.adv_derivada_all_ste.setChecked(False)
            except Exception:
                pass

    def _on_derivada_all_ste_toggled(self, checked: bool):
        if not checked:
            return
        try:
            if hasattr(self, "adv_derivada_has"):
                self.adv_derivada_has.setChecked(True)
        except Exception:
            pass

    def _show_derivadas_popup(self):
        """Mostra popup com arvore de derivadas em texto plano."""
        try:
            df = self._df_last_search_filtered if hasattr(self, "_df_last_search_filtered") else None
            if df is None or df.empty:
                return

            # Buscar coluna de derivada_de
            derivada_col = None
            numero_col = None
            for col in df.columns:
                col_lower = col.lower()
                if "derivada" in col_lower:
                    derivada_col = col
                elif "numero" in col_lower and "ssa" in col_lower:
                    numero_col = col

            if derivada_col is None or numero_col is None:
                return

            mae_filhas, filha_mae = self._build_derivadas_tree(df, numero_col, derivada_col)

            if not mae_filhas and not filha_mae:
                return

            # Construir texto
            lines = []

            # Derivadas (maes com suas filhas)
            if mae_filhas:
                lines.append("Derivadas")
                for mae in sorted(mae_filhas.keys()):
                    filhas = mae_filhas[mae]
                    # Verificar se alguma filha tambem e mae
                    filhas_str_parts = []
                    for f in sorted(filhas):
                        if f in mae_filhas:
                            # Filha tambem e mae, incluir netas entre parenteses
                            netas = mae_filhas[f]
                            filhas_str_parts.append(f"{f}({','.join(sorted(netas))})")
                        else:
                            filhas_str_parts.append(f)
                    lines.append(f"{mae} -> {', '.join(filhas_str_parts)}")

            lines.append("")

            # SSA de origem (filhas com suas maes)
            if filha_mae:
                lines.append("SSA de origem")
                for filha in sorted(filha_mae.keys()):
                    mae = filha_mae[filha]
                    lines.append(f"{filha} -> {mae}")

            text = "\n".join(lines)

            # Criar dialogo com texto copiavel e pesquisavel
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
            dialog = QDialog(self)
            dialog.setWindowTitle("Arvore de Derivadas")
            dialog.setMinimumSize(500, 400)
            layout = QVBoxLayout(dialog)

            text_edit = QTextEdit()
            text_edit.setPlainText(text)
            text_edit.setReadOnly(True)
            try:
                text_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
            except Exception:
                pass
            layout.addWidget(text_edit)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dialog.close)
            layout.addWidget(buttons)

            dialog.exec()
        except Exception as e:
            logger.warning("Erro ao mostrar popup de derivadas: %s", e)

    def _build_derivadas_tree(self, df: pd.DataFrame, numero_col: str, derivada_col: str):
        """Constroi arvore de derivadas com normalizacao robusta de SSA."""
        mae_filhas: dict[str, list[str]] = {}
        filha_mae: dict[str, str] = {}
        if df is None or df.empty:
            return mae_filhas, filha_mae
        if numero_col not in df.columns or derivada_col not in df.columns:
            return mae_filhas, filha_mae

        try:
            df_work = df[[numero_col, derivada_col]].copy()
        except Exception:
            return mae_filhas, filha_mae

        for _, row in df_work.iterrows():
            numero = self._normalize_ssa_value(row.get(numero_col))
            derivada_de = self._normalize_ssa_value(row.get(derivada_col))
            if not numero or not derivada_de:
                continue
            filha_mae[numero] = derivada_de
            mae_filhas.setdefault(derivada_de, set()).add(numero)

        for mae, filhas in list(mae_filhas.items()):
            mae_filhas[mae] = sorted(filhas, key=lambda value: str(value).casefold())

        return mae_filhas, filha_mae

    def _update_derivadas_button_state(self):
        """Habilita/desabilita botao Especificas baseado em existencia de derivadas."""
        try:
            btn = getattr(self, "adv_derivadas_especificas_button", None)
            if btn is None:
                btn = getattr(self, "_adv_ctx", {}).get("adv_derivadas_especificas_button")
            if btn is None:
                return

            df = self._df_last_search_filtered if hasattr(self, "_df_last_search_filtered") else None
            if df is None or df.empty:
                btn.setEnabled(False)
                return

            # Verificar se existe coluna derivada_de com valores
            derivada_col = None
            for col in df.columns:
                if "derivada" in col.lower():
                    derivada_col = col
                    break

            if derivada_col is None:
                btn.setEnabled(False)
                return

            # Verificar se ha valores normalizados validos (ignora '', None, NaN)
            normalized = df[derivada_col].apply(self._normalize_ssa_value)
            has_derivadas = normalized.ne("").any()
            btn.setEnabled(bool(has_derivadas))
        except Exception:
            pass

    def _save_advanced_filters_default(self):
        self._apply_advanced_filters_from_ui(store_only=True)
        try:
            gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
            gui_settings["advanced_filters_default"] = copy.deepcopy(self._advanced_filters or {})
            self._persist_gui_preferences()
        except Exception as e:
            logger.warning("Falha ao salvar filtros avancados default: %s", e)

    def _on_macro_filter_changed(self):
        try:
            choice = self.adv_macro_combo.currentData()
        except Exception:
            choice = None
        if choice == "ssas_para_baixar":
            try:
                if hasattr(self, "adv_derivada_has"):
                    self.adv_derivada_has.setChecked(True)
                if hasattr(self, "adv_derivada_all_ste"):
                    self.adv_derivada_all_ste.setChecked(True)
            except Exception:
                pass
            try:
                self._sync_multiselect_checks(
                    getattr(self, "adv_status_button", None),
                    getattr(self, "adv_status_checks", None),
                    [],
                    getattr(self, "adv_status_exclude_checks", None),
                    ["STE", "SCA"],
                )
            except Exception:
                pass
            try:
                if hasattr(self, "adv_executor_button"):
                    self.adv_executor_button.showMenu()
            except Exception:
                pass
        self._apply_advanced_filters_from_ui()

    def _reorganize_advanced_filters_grid(self, width: int):
        """Reorganiza grid de filtros avancados baseado na largura disponivel."""
        if not hasattr(self, "_adv_filters_main_grid") or not hasattr(self, "_adv_filters_grid_widgets"):
            return

        grid = self._adv_filters_main_grid
        w = self._adv_filters_grid_widgets

        # Remove todos os widgets do grid
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Define layout baseado na largura
        # Largura > 1400px: Grid 6x3 (layout original denso)
        if width > 1400:
            grid.addWidget(w["emis_box"], 0, 0)
            grid.addWidget(w["exec_box"], 0, 1)
            grid.addWidget(w["div_box"], 0, 2)
            grid.addWidget(w["status_box"], 0, 3)
            grid.addWidget(w["year_emissao_box"], 0, 4)
            grid.addWidget(w["year_execucao_box"], 0, 5)
            grid.addWidget(w["reprog_box"], 1, 0)
            grid.addWidget(w["prio_emis_box"], 1, 1)
            grid.addWidget(w["prio_plan_box"], 1, 2)
            grid.addWidget(w["deriv_box"], 1, 3, 1, 2)
            grid.addWidget(w["macro_box"], 1, 5)
            grid.addWidget(w["week_emis_box"], 2, 0)
            grid.addWidget(w["week_exec_box"], 2, 1)
            grid.addWidget(w["sol_box"], 2, 2)
            grid.addWidget(w["prog_box"], 2, 3)
            grid.addWidget(w["exec_resp_box"], 2, 4)
            grid.addWidget(w["emis_resp_box"], 2, 5)
            for col in range(6):
                grid.setColumnStretch(col, 1)

        # Largura 900-1400px: Grid 3x6 (meio termo)
        elif width > 900:
            grid.addWidget(w["emis_box"], 0, 0)
            grid.addWidget(w["exec_box"], 0, 1)
            grid.addWidget(w["div_box"], 0, 2)
            grid.addWidget(w["status_box"], 1, 0)
            grid.addWidget(w["year_emissao_box"], 1, 1)
            grid.addWidget(w["year_execucao_box"], 1, 2)
            grid.addWidget(w["reprog_box"], 2, 0)
            grid.addWidget(w["prio_emis_box"], 2, 1)
            grid.addWidget(w["prio_plan_box"], 2, 2)
            grid.addWidget(w["deriv_box"], 3, 0, 1, 2)
            grid.addWidget(w["macro_box"], 3, 2)
            grid.addWidget(w["week_emis_box"], 4, 0)
            grid.addWidget(w["week_exec_box"], 4, 1)
            grid.addWidget(w["sol_box"], 4, 2)
            grid.addWidget(w["prog_box"], 5, 0)
            grid.addWidget(w["exec_resp_box"], 5, 1)
            grid.addWidget(w["emis_resp_box"], 5, 2)
            for col in range(3):
                grid.setColumnStretch(col, 1)

        # Largura < 900px: Grid 2x9 (mais vertical)
        else:
            grid.addWidget(w["emis_box"], 0, 0)
            grid.addWidget(w["exec_box"], 0, 1)
            grid.addWidget(w["div_box"], 1, 0)
            grid.addWidget(w["status_box"], 1, 1)
            grid.addWidget(w["year_emissao_box"], 2, 0)
            grid.addWidget(w["year_execucao_box"], 2, 1)
            grid.addWidget(w["reprog_box"], 3, 0)
            grid.addWidget(w["prio_emis_box"], 3, 1)
            grid.addWidget(w["prio_plan_box"], 4, 0)
            grid.addWidget(w["deriv_box"], 4, 1, 1, 1)
            grid.addWidget(w["macro_box"], 5, 0)
            grid.addWidget(w["week_emis_box"], 5, 1)
            grid.addWidget(w["week_exec_box"], 6, 0)
            grid.addWidget(w["sol_box"], 6, 1)
            grid.addWidget(w["prog_box"], 7, 0)
            grid.addWidget(w["exec_resp_box"], 7, 1)
            grid.addWidget(w["emis_resp_box"], 8, 0, 1, 2)
            for col in range(2):
                grid.setColumnStretch(col, 1)

    def _on_adv_sector_selection_changed(self, *_):
        if getattr(self, "_adv_sector_syncing", False):
            return
        try:
            self._apply_divisao_to_setor_checks()
        except Exception:
            pass
        try:
            self._update_multiselect_button(
                self.adv_executor_button,
                self.adv_executor_checks,
                exclude_checks=getattr(self, "adv_executor_exclude_checks", None),
            )
        except Exception:
            pass
        try:
            self._update_multiselect_button(
                self.adv_emissor_button,
                self.adv_emissor_checks,
                exclude_checks=getattr(self, "adv_emissor_exclude_checks", None),
            )
        except Exception:
            pass
        try:
            self._update_multiselect_button(
                self.adv_divisao_button,
                self.adv_divisao_checks,
                exclude_checks=getattr(self, "adv_divisao_exclude_checks", None),
            )
        except Exception:
            pass
        try:
            self._refresh_responsavel_options()
        except Exception:
            pass

    def _on_adv_sector_exclude_changed(self, *_):
        """Atualiza filtros de exclusão de setor com debouncing."""
        try:
            self._update_multiselect_button(
                self.adv_executor_button,
                self.adv_executor_checks,
                exclude_checks=getattr(self, "adv_executor_exclude_checks", None),
            )
        except Exception:
            pass
        try:
            self._update_multiselect_button(
                self.adv_emissor_button,
                self.adv_emissor_checks,
                exclude_checks=getattr(self, "adv_emissor_exclude_checks", None),
            )
        except Exception:
            pass
        try:
            self._update_multiselect_button(
                self.adv_divisao_button,
                self.adv_divisao_checks,
                exclude_checks=getattr(self, "adv_divisao_exclude_checks", None),
            )
        except Exception:
            pass

        # Debounce: cancela timer anterior e agenda novo refresh
        if self._sector_debounce_timer is not None:
            try:
                self._sector_debounce_timer.stop()
            except Exception:
                pass

        try:
            from PyQt6.QtCore import QTimer
            self._sector_debounce_timer = QTimer()
            self._sector_debounce_timer.setSingleShot(True)
            self._sector_debounce_timer.timeout.connect(self._refresh_responsavel_options)
            self._sector_debounce_timer.start(self._sector_debounce_delay)
        except Exception:
            # Fallback sem debounce se timer falhar
            try:
                self._refresh_responsavel_options()
            except Exception:
                pass

    def _collect_divisao_setores(self, divisao_values):
        setores = set()
        for div in divisao_values or []:
            try:
                setores.update(DIVISAO_SETORES.get(str(div), []))
            except Exception:
                pass
        return setores

    def _sector_sort_key(self, sector: str):
        div = SECTOR_TO_DIV.get(sector, "")
        # Ordem: SMIN primeiro (0), SMME segundo (1), outras divisoes alfabeticamente (2+)
        if div == "SMIN":
            div_rank = 0
        elif div == "SMME":
            div_rank = 1
        elif div:
            div_rank = 2
        else:
            div_rank = 3
        return (div_rank, div.casefold(), sector.casefold())

    def _sort_sectors(self, values):
        return sorted(values, key=self._sector_sort_key)

    def _sort_responsavel_values(self, df_subset, values, resp_col: str):
        if not values:
            return []
        sector_cols = [c for c in ["setor_executor", "setor_emissor"] if c in df_subset.columns]
        sector_counts = {}
        for col in sector_cols:
            try:
                pairs = df_subset[[col, resp_col]].dropna()
            except Exception:
                continue
            for sec, person in pairs.itertuples(index=False):
                sec_str = str(sec).strip()
                person_str = str(person).strip()
                if not person_str:
                    continue
                sector_counts.setdefault(person_str, {})
                sector_counts[person_str][sec_str] = sector_counts[person_str].get(sec_str, 0) + 1

        def _best_sector(person):
            counts = sector_counts.get(person, {})
            if not counts:
                return ""
            return max(counts.items(), key=lambda t: (t[1], -len(t[0]), t[0].casefold()))[0]

        def _key(person):
            sec = _best_sector(person)
            div = SECTOR_TO_DIV.get(sec, "")
            div_rank = 0 if div == "SMIN" else 1 if div else 2
            return (div_rank, div.casefold(), sec.casefold(), person.casefold())

        ordered = sorted(values, key=_key)
        decorated = []
        for person in ordered:
            sec = _best_sector(person)
            div = SECTOR_TO_DIV.get(sec, "")
            prefix = ""
            if div and sec:
                prefix = f"{div} / {sec} - "
            elif sec:
                prefix = f"{sec} - "
            display = f"{prefix}{person}"
            decorated.append((person, display))
        return decorated

    def _apply_divisao_to_setor_checks(self):
        """Aplica selecao de divisao aos checkboxes de setor.
        
        CORRECAO 2026-01-08: Adicionado blockSignals() para evitar loop infinito
        de signals que causava travamento da interface.
        """
        selected_div = self._get_checked_values(getattr(self, "adv_divisao_checks", None))
        setores = self._collect_divisao_setores(selected_div)
        if not setores:
            return
        setores_norm = {str(s).casefold() for s in setores}
        self._adv_sector_syncing = True
        try:
            for cb in getattr(self, "adv_executor_checks", None) or []:
                try:
                    if not _is_widget_valid(cb):
                        continue
                    if cb.text().casefold() in setores_norm:
                        cb.blockSignals(True)
                        cb.setChecked(True)
                        cb.blockSignals(False)
                except Exception:
                    pass
            for cb in getattr(self, "adv_emissor_checks", None) or []:
                try:
                    if not _is_widget_valid(cb):
                        continue
                    if cb.text().casefold() in setores_norm:
                        cb.blockSignals(True)
                        cb.setChecked(True)
                        cb.blockSignals(False)
                except Exception:
                    pass
        finally:
            self._adv_sector_syncing = False

    def _refresh_responsavel_options(self):
        if self.df_completo is None or self.df_completo.empty:
            return
        exec_values = self._get_checked_values(getattr(self, "adv_executor_checks", None))
        emis_values = self._get_checked_values(getattr(self, "adv_emissor_checks", None))
        div_values = self._get_checked_values(getattr(self, "adv_divisao_checks", None))
        exec_excluded = self._get_checked_values(getattr(self, "adv_executor_exclude_checks", None))
        emis_excluded = self._get_checked_values(getattr(self, "adv_emissor_exclude_checks", None))
        div_excluded = self._get_checked_values(getattr(self, "adv_divisao_exclude_checks", None))
        has_sector = bool(exec_values or emis_values or div_values or exec_excluded or emis_excluded or div_excluded)
        apply_cb = lambda: self._apply_advanced_filters_from_ui()

        def _set_enabled(widget, enabled):
            if widget is None:
                return
            try:
                widget.setEnabled(bool(enabled))
            except Exception:
                pass

        def _set_visible(widget, visible):
            if widget is None:
                return
            try:
                widget.setVisible(bool(visible))
            except Exception:
                pass

        df = self.df_completo
        exec_col = "setor_executor"
        emis_col = "setor_emissor"
        selected_exec = set(exec_values)
        selected_emis = set(emis_values)
        selected_div = set(div_values)
        selected_exec_excluded = set(exec_excluded)
        selected_emis_excluded = set(emis_excluded)
        selected_div_excluded = set(div_excluded)
        div_setores = self._collect_divisao_setores(selected_div)
        div_setores_excluded = self._collect_divisao_setores(selected_div_excluded)
        filters = self._advanced_filters or {}

        def _apply_sector_subset(frame):
            subset = frame
            if exec_col in subset.columns:
                allowed = set(selected_exec) | set(div_setores)
                excluded = set(selected_exec_excluded) | set(div_setores_excluded)
                if allowed:
                    subset = subset[subset[exec_col].astype(str).isin(allowed)]
                if excluded:
                    subset = subset[~subset[exec_col].astype(str).isin(excluded)]
            if emis_col in subset.columns and selected_emis:
                subset = subset[subset[emis_col].astype(str).isin(selected_emis)]
            if emis_col in subset.columns and selected_emis_excluded:
                subset = subset[~subset[emis_col].astype(str).isin(selected_emis_excluded)]
            return subset

        if has_sector:
            df = _apply_sector_subset(df)

        def _unique_sorted(col):
            try:
                vals = df[col].dropna().astype(str).str.strip()
                vals = vals[vals != ""]
                vals = [v for v in set(vals) if v]
                return sorted(vals, key=lambda v: v.casefold())
            except Exception:
                return []

        resp_cols = [
            ("solicitante", "adv_responsavel_solicitante"),
            ("responsavel_programacao", "adv_responsavel_programacao"),
            ("responsavel_execucao", "adv_responsavel_execucao"),
            ("responsavel_emissor", "adv_responsavel_emissor"),
        ]
        for col, prefix in resp_cols:
            box = getattr(self, f"{prefix}_box", None)
            button = getattr(self, f"{prefix}_button", None)
            menu = getattr(self, f"{prefix}_menu", None)
            checks_attr = f"{prefix}_checks"
            exclude_checks_attr = f"{prefix}_exclude_checks"
            exclude = getattr(self, f"{prefix}_exclude", None)
            col_exists = col in self.df_completo.columns
            _set_visible(box, col_exists)
            if not col_exists:
                _set_enabled(button, False)
                _set_enabled(exclude, False)
                setattr(self, checks_attr, [])
                setattr(self, exclude_checks_attr, [])
                continue
            values = _unique_sorted(col)
            try:
                values = self._sort_responsavel_values(df, values, col)
            except Exception:
                pass
            _set_enabled(button, True)
            _set_enabled(exclude, True)
            selected = set((self._advanced_filters or {}).get(col) or [])
            excluded = set((self._advanced_filters or {}).get(f"{col}_exclude_values") or [])
            include_checks, exclude_checks = self._rebuild_multiselect_menu(
                button,
                menu,
                values,
                selected,
                lambda *_: self._update_multiselect_button(
                    button,
                    getattr(self, checks_attr, []),
                    exclude_checks=getattr(self, exclude_checks_attr, None),
                ),
                apply_cb,
                excluded,
                lambda *_: self._update_multiselect_button(
                    button,
                    getattr(self, checks_attr, []),
                    exclude_checks=getattr(self, exclude_checks_attr, None),
                ),
            )
            setattr(self, checks_attr, include_checks)
            setattr(self, exclude_checks_attr, exclude_checks)

        # Reprogramacoes (código duplicado removido)
        reprog_values = getattr(self, "_adv_values_cache", {}).get("reprog_vals", [])
        try:
            include_checks, _ = self._rebuild_multiselect_menu(
                getattr(self, "adv_reprog_button", None),
                getattr(self, "adv_reprog_menu", None),
                reprog_values,
                set((self._advanced_filters or {}).get("num_reprogramacoes_values") or []),
                lambda *_: self._update_multiselect_button(
                    getattr(self, "adv_reprog_button", None),
                    getattr(self, "adv_reprog_checks", None),
                ),
                lambda *_: self._apply_advanced_filters_from_ui(),
                None,
                None,
            )
            self.adv_reprog_checks = include_checks
            try:
                mode = (self._advanced_filters or {}).get("num_reprogramacoes_mode")
                if mode is not None and getattr(self, "adv_reprog_mode", None):
                    idx = getattr(self, "adv_reprog_mode").findData(mode)
                    if idx >= 0:
                        getattr(self, "adv_reprog_mode").setCurrentIndex(idx)
            except Exception:
                pass
        except Exception:
            self.adv_reprog_checks = []

        # SSAs Derivadas Específicas (novo filtro granular)
        adv_cache = getattr(self, "_adv_values_cache", {}) or {}
        derivadas_numbers = adv_cache.get("derivadas_vals", [])
        if not derivadas_numbers:
            # Extrai numeros unicos de SSAs derivadas se nao estiver em cache
            try:
                if "derivada_de" in df.columns:
                    derivadas_series = df["derivada_de"].apply(self._normalize_ssa_value)
                    derivadas_numbers = sorted(
                        {v for v in derivadas_series.unique() if v and str(v).strip()},
                        key=lambda x: str(x).casefold()
                    )
                    adv_cache["derivadas_vals"] = derivadas_numbers
                    self._adv_values_cache = adv_cache
            except Exception:
                pass

    def _clear_advanced_filters(self):
        try:
            self._store_last_filter_state()
        except Exception:
            pass
        self._advanced_filters = {}
        self._advanced_filters_active = False
        try:
            self._sync_advanced_filter_ui()
        except Exception:
            pass
        try:
            self._refresh_after_filter_change()
        except Exception:
            pass

    def _has_active_advanced_filters(self, data: dict) -> bool:
        if not isinstance(data, dict) or not data:
            return False
        list_keys = (
            "setor_executor",
            "setor_emissor",
            "divisao",
            "situacao",
            "solicitante",
            "responsavel_programacao",
            "responsavel_execucao",
            "responsavel_emissor",
        )
        for key in list_keys:
            if data.get(key):
                return True
        exclude_list_keys = (
            "setor_executor_exclude_values",
            "setor_emissor_exclude_values",
            "divisao_exclude_values",
            "situacao_exclude_values",
            "solicitante_exclude_values",
            "responsavel_programacao_exclude_values",
            "responsavel_execucao_exclude_values",
            "responsavel_emissor_exclude_values",
            "prioridade_emissao_exclude_values",
            "prioridade_planejamento_exclude_values",
        )
        for key in exclude_list_keys:
            if data.get(key):
                return True
        if data.get("ano_emissao") or data.get("ano_execucao"):
            return True
        if data.get("ano_emissao_values") or data.get("ano_execucao_values"):
            return True
        if data.get("ano_emissao_exclude_values") or data.get("ano_execucao_exclude_values"):
            return True
        if data.get("prioridade_emissao_values") or data.get("prioridade_planejamento_values"):
            return True
        if data.get("semana_emissao_inicio") is not None or data.get("semana_emissao_fim") is not None:
            return True
        if data.get("semana_execucao_inicio") is not None or data.get("semana_execucao_fim") is not None:
            return True
        if data.get("derivada_has") or data.get("derivada_all_ste") or data.get("derivada_is"):
            return True
        if data.get("macro_filter"):
            return True
        return False

    def _apply_advanced_filters_from_ui(self, store_only: bool = False):
        if not store_only:
            try:
                self._store_last_filter_state()
            except Exception:
                pass
        data = {}
        try:
            data["setor_executor"] = self._get_checked_values(getattr(self, "adv_executor_checks", None))
        except Exception:
            data["setor_executor"] = []
        try:
            data["setor_executor_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_executor_exclude_checks", None)
            )
        except Exception:
            data["setor_executor_exclude_values"] = []
        try:
            data["setor_emissor"] = self._get_checked_values(getattr(self, "adv_emissor_checks", None))
        except Exception:
            data["setor_emissor"] = []
        try:
            data["setor_emissor_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_emissor_exclude_checks", None)
            )
        except Exception:
            data["setor_emissor_exclude_values"] = []
        try:
            data["divisao"] = self._get_checked_values(getattr(self, "adv_divisao_checks", None))
        except Exception:
            data["divisao"] = []
        try:
            data["divisao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_divisao_exclude_checks", None)
            )
        except Exception:
            data["divisao_exclude_values"] = []
        try:
            data["situacao"] = self._get_checked_values(getattr(self, "adv_status_checks", None))
        except Exception:
            data["situacao"] = []
        try:
            data["situacao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_status_exclude_checks", None)
            )
        except Exception:
            data["situacao_exclude_values"] = []
        try:
            data["ano_emissao_values"] = self._get_checked_values(
                getattr(self, "adv_year_emissao_checks", None)
            )
        except Exception:
            data["ano_emissao_values"] = []
        try:
            data["ano_emissao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_year_emissao_exclude_checks", None)
            )
        except Exception:
            data["ano_emissao_exclude_values"] = []
        try:
            data["ano_execucao_values"] = self._get_checked_values(
                getattr(self, "adv_year_execucao_checks", None)
            )
        except Exception:
            data["ano_execucao_values"] = []
        try:
            data["ano_execucao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_year_execucao_exclude_checks", None)
            )
        except Exception:
            data["ano_execucao_exclude_values"] = []
        try:
            data["semana_emissao_inicio"] = self._parse_week(self.adv_week_emissao_start.text())
            data["semana_emissao_fim"] = self._parse_week(self.adv_week_emissao_end.text())
        except Exception:
            data["semana_emissao_inicio"] = None
            data["semana_emissao_fim"] = None
        try:
            data["semana_execucao_inicio"] = self._parse_week(self.adv_week_execucao_start.text())
            data["semana_execucao_fim"] = self._parse_week(self.adv_week_execucao_end.text())
        except Exception:
            data["semana_execucao_inicio"] = None
            data["semana_execucao_fim"] = None
        data["semana_emissao_exclude"] = False
        data["semana_execucao_exclude"] = False
        try:
            data["derivada_has"] = bool(getattr(self, "adv_derivada_has", None).isChecked())
        except Exception:
            data["derivada_has"] = False
        try:
            data["derivada_all_ste"] = bool(getattr(self, "adv_derivada_all_ste", None).isChecked())
        except Exception:
            data["derivada_all_ste"] = False
        if data.get("derivada_all_ste"):
            data["derivada_has"] = True
        try:
            data["derivada_is"] = bool(getattr(self, "adv_derivada_is", None).isChecked())
        except Exception:
            data["derivada_is"] = False
        # derivadas_especificas_values removido - botao Especificas agora e apenas visualizacao
        try:
            data["solicitante"] = self._get_checked_values(getattr(self, "adv_responsavel_solicitante_checks", None))
        except Exception:
            data["solicitante"] = []
        try:
            data["solicitante_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_responsavel_solicitante_exclude_checks", None)
            )
        except Exception:
            data["solicitante_exclude_values"] = []
        try:
            data["responsavel_programacao"] = self._get_checked_values(
                getattr(self, "adv_responsavel_programacao_checks", None)
            )
        except Exception:
            data["responsavel_programacao"] = []
        try:
            data["responsavel_programacao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_responsavel_programacao_exclude_checks", None)
            )
        except Exception:
            data["responsavel_programacao_exclude_values"] = []
        try:
            data["responsavel_execucao"] = self._get_checked_values(
                getattr(self, "adv_responsavel_execucao_checks", None)
            )
        except Exception:
            data["responsavel_execucao"] = []
        try:
            data["responsavel_execucao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_responsavel_execucao_exclude_checks", None)
            )
        except Exception:
            data["responsavel_execucao_exclude_values"] = []
        try:
            data["responsavel_emissor"] = self._get_checked_values(
                getattr(self, "adv_responsavel_emissor_checks", None)
            )
        except Exception:
            data["responsavel_emissor"] = []
        try:
            data["responsavel_emissor_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_responsavel_emissor_exclude_checks", None)
            )
        except Exception:
            data["responsavel_emissor_exclude_values"] = []
        try:
            data["num_reprogramacoes_values"] = self._get_checked_values(getattr(self, "adv_reprog_checks", None))
        except Exception:
            data["num_reprogramacoes_values"] = []
        try:
            mode_idx = getattr(self, "adv_reprog_mode", None).currentIndex()
            data["num_reprogramacoes_mode"] = getattr(self, "adv_reprog_mode", None).itemData(mode_idx)
        except Exception:
            data["num_reprogramacoes_mode"] = None
        try:
            data["prioridade_emissao_values"] = self._get_checked_values(
                getattr(self, "adv_prioridade_emissao_checks", None)
            )
        except Exception:
            data["prioridade_emissao_values"] = []
        try:
            data["prioridade_emissao_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_prioridade_emissao_exclude_checks", None)
            )
        except Exception:
            data["prioridade_emissao_exclude_values"] = []
        try:
            data["prioridade_planejamento_values"] = self._get_checked_values(
                getattr(self, "adv_prioridade_planejamento_checks", None)
            )
        except Exception:
            data["prioridade_planejamento_values"] = []
        try:
            data["prioridade_planejamento_exclude_values"] = self._get_checked_values(
                getattr(self, "adv_prioridade_planejamento_exclude_checks", None)
            )
        except Exception:
            data["prioridade_planejamento_exclude_values"] = []
        try:
            data["macro_filter"] = self.adv_macro_combo.currentData()
        except Exception:
            data["macro_filter"] = None

        self._advanced_filters = data
        if store_only:
            return
        self._advanced_filters_active = self._has_active_advanced_filters(data)
        try:
            self._refresh_after_filter_change()
        except Exception:
            pass

    def _parse_week(self, raw: str):
        s = str(raw or "").strip()
        if not s:
            return None
        if not s.isdigit():
            return None
        if len(s) != 6:
            return None
        return int(s)

    def _get_checked_values(self, source):
        values = []
        if source is None:
            return values
        if isinstance(source, list):
            for child in source:
                try:
                    if not _is_widget_valid(child):
                        continue
                    if child.isChecked():
                        value = self._checkbox_value(child)
                        if value:
                            values.append(value)
                except Exception:
                    pass
            return values
        if hasattr(source, "findChildren"):
            try:
                children = source.findChildren(QCheckBox)
            except Exception:
                children = []
            for child in children:
                try:
                    if not _is_widget_valid(child):
                        continue
                    if child.isChecked():
                        value = self._checkbox_value(child)
                        if value:
                            values.append(value)
                except Exception:
                    pass
        return values

    def _sync_advanced_filter_ui(self):
        data = self._advanced_filters or {}
        self._sync_multiselect_checks(
            getattr(self, "adv_executor_button", None),
            getattr(self, "adv_executor_checks", None),
            data.get("setor_executor"),
            getattr(self, "adv_executor_exclude_checks", None),
            data.get("setor_executor_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_emissor_button", None),
            getattr(self, "adv_emissor_checks", None),
            data.get("setor_emissor"),
            getattr(self, "adv_emissor_exclude_checks", None),
            data.get("setor_emissor_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_divisao_button", None),
            getattr(self, "adv_divisao_checks", None),
            data.get("divisao"),
            getattr(self, "adv_divisao_exclude_checks", None),
            data.get("divisao_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_status_button", None),
            getattr(self, "adv_status_checks", None),
            data.get("situacao"),
            getattr(self, "adv_status_exclude_checks", None),
            data.get("situacao_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_responsavel_solicitante_button", None),
            getattr(self, "adv_responsavel_solicitante_checks", None),
            data.get("solicitante"),
            getattr(self, "adv_responsavel_solicitante_exclude_checks", None),
            data.get("solicitante_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_responsavel_programacao_button", None),
            getattr(self, "adv_responsavel_programacao_checks", None),
            data.get("responsavel_programacao"),
            getattr(self, "adv_responsavel_programacao_exclude_checks", None),
            data.get("responsavel_programacao_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_responsavel_execucao_button", None),
            getattr(self, "adv_responsavel_execucao_checks", None),
            data.get("responsavel_execucao"),
            getattr(self, "adv_responsavel_execucao_exclude_checks", None),
            data.get("responsavel_execucao_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_responsavel_emissor_button", None),
            getattr(self, "adv_responsavel_emissor_checks", None),
            data.get("responsavel_emissor"),
            getattr(self, "adv_responsavel_emissor_exclude_checks", None),
            data.get("responsavel_emissor_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_prioridade_emissao_button", None),
            getattr(self, "adv_prioridade_emissao_checks", None),
            data.get("prioridade_emissao_values"),
            getattr(self, "adv_prioridade_emissao_exclude_checks", None),
            data.get("prioridade_emissao_exclude_values"),
        )
        self._sync_multiselect_checks(
            getattr(self, "adv_prioridade_planejamento_button", None),
            getattr(self, "adv_prioridade_planejamento_checks", None),
            data.get("prioridade_planejamento_values"),
            getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
            data.get("prioridade_planejamento_exclude_values"),
        )
        try:
            emissao_values = data.get("ano_emissao_values")
            emissao_exclude = data.get("ano_emissao_exclude_values")
            if emissao_values is None and data.get("ano_emissao") is not None:
                emissao_values = [data.get("ano_emissao")]
            if emissao_exclude is None and data.get("ano_emissao_exclude") and data.get("ano_emissao") is not None:
                emissao_exclude = [data.get("ano_emissao")]
            self._sync_multiselect_checks(
                getattr(self, "adv_year_emissao_button", None),
                getattr(self, "adv_year_emissao_checks", None),
                emissao_values,
                getattr(self, "adv_year_emissao_exclude_checks", None),
                emissao_exclude,
            )
        except Exception:
            pass
        try:
            execucao_values = data.get("ano_execucao_values")
            execucao_exclude = data.get("ano_execucao_exclude_values")
            if execucao_values is None and data.get("ano_execucao") is not None:
                execucao_values = [data.get("ano_execucao")]
            if execucao_exclude is None and data.get("ano_execucao_exclude") and data.get("ano_execucao") is not None:
                execucao_exclude = [data.get("ano_execucao")]
            self._sync_multiselect_checks(
                getattr(self, "adv_year_execucao_button", None),
                getattr(self, "adv_year_execucao_checks", None),
                execucao_values,
                getattr(self, "adv_year_execucao_exclude_checks", None),
                execucao_exclude,
            )
        except Exception:
            pass
        try:
            self.adv_week_emissao_start.setText("" if data.get("semana_emissao_inicio") is None else str(data.get("semana_emissao_inicio")))
            self.adv_week_emissao_end.setText("" if data.get("semana_emissao_fim") is None else str(data.get("semana_emissao_fim")))
            self.adv_week_execucao_start.setText("" if data.get("semana_execucao_inicio") is None else str(data.get("semana_execucao_inicio")))
            self.adv_week_execucao_end.setText("" if data.get("semana_execucao_fim") is None else str(data.get("semana_execucao_fim")))
        except Exception:
            pass
        try:
            if hasattr(self, "adv_derivada_has"):
                if data.get("derivada_all_ste"):
                    self.adv_derivada_has.setChecked(True)
                else:
                    self.adv_derivada_has.setChecked(bool(data.get("derivada_has")))
            if hasattr(self, "adv_derivada_all_ste"):
                self.adv_derivada_all_ste.setChecked(bool(data.get("derivada_all_ste")))
            if hasattr(self, "adv_derivada_is"):
                self.adv_derivada_is.setChecked(bool(data.get("derivada_is")))
        except Exception:
            pass
        try:
            if hasattr(self, "adv_macro_combo"):
                self.adv_macro_combo.blockSignals(True)
                idx = self.adv_macro_combo.findData(data.get("macro_filter"))
                self.adv_macro_combo.setCurrentIndex(max(0, idx))
        except Exception:
            pass
        finally:
            try:
                if hasattr(self, "adv_macro_combo"):
                    self.adv_macro_combo.blockSignals(False)
            except Exception:
                pass
        try:
            self._apply_divisao_to_setor_checks()
        except Exception:
            pass

    def _refresh_advanced_filter_options(self):
        """Atualiza opcoes de filtros avancados com cache granular otimizado."""
        if self.df_completo is None or self.df_completo.empty:
            logger.debug("_refresh_advanced_filter_options: df_completo vazio ou None")
            return
        start = perf_counter()
        df = self.df_completo
        logger.debug(f"_refresh_advanced_filter_options: iniciando com {len(df)} registros")
        filters = self._advanced_filters or {}
        apply_cb = lambda: self._apply_advanced_filters_from_ui()

        # Cache granular: permite invalidacao parcial por tipo de filtro
        cache = getattr(self, "_adv_values_cache", None)
        df_key = (
            len(df),
            tuple(df.columns),
            getattr(self, "_data_load_token", None),
        )

        # Verifica se pode reutilizar cache completo
        if cache and cache.get("df_key") == df_key and not getattr(self, "_adv_options_dirty", False):
            self._adv_options_scheduled = False
            return

        df_id = id(df)

        # Inicializa cache granular se necessário
        if not isinstance(cache, dict) or cache.get("df_id") != df_id:
            cache = {"df_id": df_id, "df_key": df_key}
            self._adv_values_cache = cache

        def _unique_sorted(col):
            try:
                vals = df[col].dropna().astype(str).str.strip()
                vals = vals[vals != ""]
                return sorted(set(vals), key=lambda v: v.casefold())
            except Exception:
                return []

        def _sort_sector_values(values):
            try:
                return self._sort_sectors(set(values))
            except Exception:
                return sorted(set(values), key=lambda v: str(v).casefold())

        def _div_key(val):
            text = str(val).upper()
            # Ordem: SMIN primeiro (0), SMME segundo (1), outras alfabetico (2)
            if text == "SMIN":
                return (0, text)
            elif text == "SMME":
                return (1, text)
            return (2, text)

        # Popula cache se necessário (bloco único consolidado) - CORRIGIDO: removida duplicação
        if cache.get("exec_vals") is None:
            cache["exec_vals"] = (
                _sort_sector_values(_unique_sorted("setor_executor")) if "setor_executor" in df.columns else []
            )
            cache["emis_vals"] = (
                _sort_sector_values(_unique_sorted("setor_emissor")) if "setor_emissor" in df.columns else []
            )
            cache["status_vals"] = _unique_sorted("situacao") if "situacao" in df.columns else []
            cache["divisao_vals"] = sorted(DIVISAO_SETORES.keys(), key=_div_key)

            def _collect_years_from_dates(series):
                """Extrai anos de datas usando operações vetorizadas (otimizado)."""
                try:
                    # Vetorizado: converte diretamente para datetime sem apply()
                    ts = pd.to_datetime(series, errors="coerce")
                    # Extrai anos e remove NaT
                    years = ts.dt.year.dropna().astype(int).unique()
                    return sorted(years, reverse=True)
                except Exception:
                    return []

            def _collect_years_from_weeks(series):
                """Extrai anos de semanas (formato YYYYWW) vetorizado."""
                try:
                    nums = pd.to_numeric(series, errors="coerce").dropna().astype(int)
                    # Vetorizado: unique() em vez de tolist() + set() + sorted()
                    years = (nums // 100).unique()
                    return sorted(years, reverse=True)
                except Exception:
                    return []

            emissao_years = []
            if "data_cadastro" in df.columns:
                emissao_years = _collect_years_from_dates(df["data_cadastro"])
            elif "semana_cadastro" in df.columns:
                emissao_years = _collect_years_from_weeks(df["semana_cadastro"])

            execucao_years = []
            if "semana_executada" in df.columns:
                execucao_years = _collect_years_from_weeks(df["semana_executada"])

            cache["emissao_years"] = emissao_years
            cache["execucao_years"] = execucao_years
            cache["prio_emissao_vals"] = (
                _unique_sorted("grau_prioridade_emissao") if "grau_prioridade_emissao" in df.columns else []
            )
            cache["prio_planejamento_vals"] = (
                _unique_sorted("grau_prioridade_planejamento") if "grau_prioridade_planejamento" in df.columns else []
            )
            if "num_reprogramacoes" in df.columns:
                try:
                    # Vetorizado: dropna() já remove NaN, sem necessidade de lambda
                    reprog_series = pd.to_numeric(df["num_reprogramacoes"], errors="coerce").dropna()
                    # unique() evita tolist() + set() + sorted()
                    reprog_vals = reprog_series.astype(int).unique()
                    cache["reprog_vals"] = sorted(reprog_vals, reverse=True)
                except Exception:
                    cache["reprog_vals"] = []
            else:
                cache["reprog_vals"] = []
            self._adv_values_cache = cache
            logger.debug(f"_refresh_advanced_filter_options: cache populado - exec={len(cache.get('exec_vals', []))}, emis={len(cache.get('emis_vals', []))}, status={len(cache.get('status_vals', []))}")

        exec_vals = cache.get("exec_vals", [])
        emis_vals = cache.get("emis_vals", [])
        status_vals = cache.get("status_vals", [])
        divisao_vals = cache.get("divisao_vals", [])
        emissao_years = cache.get("emissao_years", [])
        execucao_years = cache.get("execucao_years", [])
        prio_emissao_vals = cache.get("prio_emissao_vals", [])
        prio_planejamento_vals = cache.get("prio_planejamento_vals", [])

        if hasattr(self, "adv_executor_menu"):
            exec_include, exec_exclude = self._rebuild_multiselect_menu(
                self.adv_executor_button,
                self.adv_executor_menu,
                exec_vals,
                set(filters.get("setor_executor") or []),
                self._on_adv_sector_selection_changed,
                apply_cb,
                set(filters.get("setor_executor_exclude_values") or []),
                self._on_adv_sector_exclude_changed,
            )
            self.adv_executor_checks = exec_include
            self.adv_executor_exclude_checks = exec_exclude
        if hasattr(self, "adv_emissor_menu"):
            emis_include, emis_exclude = self._rebuild_multiselect_menu(
                self.adv_emissor_button,
                self.adv_emissor_menu,
                emis_vals,
                set(filters.get("setor_emissor") or []),
                self._on_adv_sector_selection_changed,
                apply_cb,
                set(filters.get("setor_emissor_exclude_values") or []),
                self._on_adv_sector_exclude_changed,
            )
            self.adv_emissor_checks = emis_include
            self.adv_emissor_exclude_checks = emis_exclude
        if hasattr(self, "adv_divisao_menu"):
            div_include, div_exclude = self._rebuild_multiselect_menu(
                self.adv_divisao_button,
                self.adv_divisao_menu,
                divisao_vals,
                set(filters.get("divisao") or []),
                self._on_adv_sector_selection_changed,
                apply_cb,
                set(filters.get("divisao_exclude_values") or []),
                self._on_adv_sector_exclude_changed,
            )
            self.adv_divisao_checks = div_include
            self.adv_divisao_exclude_checks = div_exclude
        if hasattr(self, "adv_status_menu"):
            status_include, status_exclude = self._rebuild_multiselect_menu(
                self.adv_status_button,
                self.adv_status_menu,
                status_vals,
                set(filters.get("situacao") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_status_button,
                    getattr(self, "adv_status_checks", None),
                    exclude_checks=getattr(self, "adv_status_exclude_checks", None),
                ),
                apply_cb,
                set(filters.get("situacao_exclude_values") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_status_button,
                    getattr(self, "adv_status_checks", None),
                    exclude_checks=getattr(self, "adv_status_exclude_checks", None),
                ),
            )
            self.adv_status_checks = status_include
            self.adv_status_exclude_checks = status_exclude

        if hasattr(self, "adv_year_emissao_menu"):
            inc_vals = filters.get("ano_emissao_values")
            exc_vals = filters.get("ano_emissao_exclude_values")
            if inc_vals is None and filters.get("ano_emissao") is not None:
                inc_vals = [filters.get("ano_emissao")]
            if exc_vals is None and filters.get("ano_emissao_exclude") and filters.get("ano_emissao") is not None:
                exc_vals = [filters.get("ano_emissao")]
            # Filtra valores vazios/nulos
            year_values = [str(y) for y in emissao_years if y and str(y).strip()]
            inc_set = {str(v) for v in (inc_vals or [])}
            exc_set = {str(v) for v in (exc_vals or [])}
            year_include, year_exclude = self._rebuild_multiselect_menu(
                self.adv_year_emissao_button,
                self.adv_year_emissao_menu,
                year_values,
                inc_set,
                lambda *_: self._update_multiselect_button(
                    self.adv_year_emissao_button,
                    getattr(self, "adv_year_emissao_checks", None),
                    exclude_checks=getattr(self, "adv_year_emissao_exclude_checks", None),
                ),
                apply_cb,
                exc_set,
                lambda *_: self._update_multiselect_button(
                    self.adv_year_emissao_button,
                    getattr(self, "adv_year_emissao_checks", None),
                    exclude_checks=getattr(self, "adv_year_emissao_exclude_checks", None),
                ),
            )
            self.adv_year_emissao_checks = year_include
            self.adv_year_emissao_exclude_checks = year_exclude
        if hasattr(self, "adv_year_execucao_menu"):
            inc_vals = filters.get("ano_execucao_values")
            exc_vals = filters.get("ano_execucao_exclude_values")
            if inc_vals is None and filters.get("ano_execucao") is not None:
                inc_vals = [filters.get("ano_execucao")]
            if exc_vals is None and filters.get("ano_execucao_exclude") and filters.get("ano_execucao") is not None:
                exc_vals = [filters.get("ano_execucao")]
            # Filtra valores vazios/nulos
            year_values = [str(y) for y in execucao_years if y and str(y).strip()]
            inc_set = {str(v) for v in (inc_vals or [])}
            exc_set = {str(v) for v in (exc_vals or [])}
            year_include, year_exclude = self._rebuild_multiselect_menu(
                self.adv_year_execucao_button,
                self.adv_year_execucao_menu,
                year_values,
                inc_set,
                lambda *_: self._update_multiselect_button(
                    self.adv_year_execucao_button,
                    getattr(self, "adv_year_execucao_checks", None),
                    exclude_checks=getattr(self, "adv_year_execucao_exclude_checks", None),
                ),
                apply_cb,
                exc_set,
                lambda *_: self._update_multiselect_button(
                    self.adv_year_execucao_button,
                    getattr(self, "adv_year_execucao_checks", None),
                    exclude_checks=getattr(self, "adv_year_execucao_exclude_checks", None),
                ),
            )
            self.adv_year_execucao_checks = year_include
            self.adv_year_execucao_exclude_checks = year_exclude

        if hasattr(self, "adv_prioridade_emissao_menu"):
            prio_include, prio_exclude = self._rebuild_multiselect_menu(
                self.adv_prioridade_emissao_button,
                self.adv_prioridade_emissao_menu,
                prio_emissao_vals,
                set(filters.get("prioridade_emissao_values") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_prioridade_emissao_button,
                    getattr(self, "adv_prioridade_emissao_checks", None),
                    exclude_checks=getattr(self, "adv_prioridade_emissao_exclude_checks", None),
                ),
                apply_cb,
                set(filters.get("prioridade_emissao_exclude_values") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_prioridade_emissao_button,
                    getattr(self, "adv_prioridade_emissao_checks", None),
                    exclude_checks=getattr(self, "adv_prioridade_emissao_exclude_checks", None),
                ),
            )
            self.adv_prioridade_emissao_checks = prio_include
            self.adv_prioridade_emissao_exclude_checks = prio_exclude
        if hasattr(self, "adv_prioridade_planejamento_menu"):
            prio_include, prio_exclude = self._rebuild_multiselect_menu(
                self.adv_prioridade_planejamento_button,
                self.adv_prioridade_planejamento_menu,
                prio_planejamento_vals,
                set(filters.get("prioridade_planejamento_values") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_prioridade_planejamento_button,
                    getattr(self, "adv_prioridade_planejamento_checks", None),
                    exclude_checks=getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
                ),
                apply_cb,
                set(filters.get("prioridade_planejamento_exclude_values") or []),
                lambda *_: self._update_multiselect_button(
                    self.adv_prioridade_planejamento_button,
                    getattr(self, "adv_prioridade_planejamento_checks", None),
                    exclude_checks=getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
                ),
            )
            self.adv_prioridade_planejamento_checks = prio_include
            self.adv_prioridade_planejamento_exclude_checks = prio_exclude

        self._refresh_responsavel_options()
        self._sync_checks_to_tab_context()
        self._sync_advanced_filter_ui()
        try:
            elapsed_ms = (perf_counter() - start) * 1000.0
            logger.debug("Advanced filter options refresh: %.1fms", elapsed_ms)
        except Exception:
            pass

    def _apply_advanced_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        filters = self._advanced_filters or {}
        if not filters:
            return df
        if not getattr(self, "_advanced_filters_active", False):
            return df
        mask = pd.Series(True, index=df.index)

        def _apply_in(col, values, exclude_values=None):
            nonlocal mask
            if col not in df.columns:
                return
            try:
                series = df[col].astype(str)
                series_norm = series.str.casefold()
                if values:
                    values_norm = {str(v).casefold() for v in values}
                    mask &= series_norm.isin(values_norm)
                if exclude_values:
                    exclude_norm = {str(v).casefold() for v in exclude_values}
                    mask &= ~series_norm.isin(exclude_norm)
            except Exception:
                pass

        exec_values = filters.get("setor_executor") or []
        emis_values = filters.get("setor_emissor") or []
        div_values = filters.get("divisao") or []
        exec_excluded = filters.get("setor_executor_exclude_values") or []
        emis_excluded = filters.get("setor_emissor_exclude_values") or []
        div_excluded = filters.get("divisao_exclude_values") or []

        if "setor_executor" in df.columns:
            allowed = set(exec_values) | self._collect_divisao_setores(div_values)
            excluded = set(exec_excluded) | self._collect_divisao_setores(div_excluded)
            try:
                series = df["setor_executor"].astype(str)
                series_norm = series.str.casefold()
                allowed_norm = {str(v).casefold() for v in allowed}
                excluded_norm = {str(v).casefold() for v in excluded}
                if allowed_norm:
                    mask &= series_norm.isin(allowed_norm)
                if excluded_norm:
                    mask &= ~series_norm.isin(excluded_norm)
            except Exception:
                pass

        _apply_in("setor_emissor", emis_values, emis_excluded)

        situacao_vals = filters.get("situacao") or []
        situacao_excluded = filters.get("situacao_exclude_values") or []
        _apply_in("situacao", situacao_vals, situacao_excluded)

        _apply_in(
            "solicitante",
            filters.get("solicitante") or [],
            filters.get("solicitante_exclude_values") or [],
        )
        _apply_in(
            "responsavel_programacao",
            filters.get("responsavel_programacao") or [],
            filters.get("responsavel_programacao_exclude_values") or [],
        )
        _apply_in(
            "responsavel_execucao",
            filters.get("responsavel_execucao") or [],
            filters.get("responsavel_execucao_exclude_values") or [],
        )
        _apply_in(
            "responsavel_emissor",
            filters.get("responsavel_emissor") or [],
            filters.get("responsavel_emissor_exclude_values") or [],
        )
        _apply_in(
            "grau_prioridade_emissao",
            filters.get("prioridade_emissao_values") or [],
            filters.get("prioridade_emissao_exclude_values") or [],
        )
        _apply_in(
            "grau_prioridade_planejamento",
            filters.get("prioridade_planejamento_values") or [],
            filters.get("prioridade_planejamento_exclude_values") or [],
        )
        try:
            reprog_vals = filters.get("num_reprogramacoes_values") or []
            mode = filters.get("num_reprogramacoes_mode")
            if reprog_vals and mode and "num_reprogramacoes" in df.columns:
                series = pd.to_numeric(df["num_reprogramacoes"], errors="coerce").dropna()
                vals = [int(v) for v in reprog_vals if pd.notna(v)]
                if mode == "eq":
                    mask &= series.isin(vals)
                elif mode == "lte":
                    threshold = max(vals)
                    mask &= series <= threshold
                elif mode == "gte":
                    threshold = min(vals)
                    mask &= series >= threshold
        except Exception:
            pass

        def _to_int_set(values):
            result = set()
            for raw in values or []:
                text = str(raw).strip()
                if text.isdigit():
                    result.add(int(text))
            return result

        emissao_inc = _to_int_set(filters.get("ano_emissao_values") or [])
        emissao_exc = _to_int_set(filters.get("ano_emissao_exclude_values") or [])
        if not emissao_inc and filters.get("ano_emissao") is not None:
            emissao_inc = _to_int_set([filters.get("ano_emissao")])
        if not emissao_exc and filters.get("ano_emissao_exclude") and filters.get("ano_emissao") is not None:
            emissao_exc = _to_int_set([filters.get("ano_emissao")])

        if emissao_inc or emissao_exc:
            if "data_cadastro" in df.columns:
                try:
                    from shared.date_utils import parse_any_date
                    parsed = df["data_cadastro"].apply(parse_any_date)
                    ts = pd.to_datetime(parsed, errors="coerce", format="%Y-%m-%d %H:%M:%S")
                    years = ts.dt.year
                    if emissao_inc:
                        mask &= years.isin(emissao_inc)
                    if emissao_exc:
                        mask &= ~years.isin(emissao_exc)
                except Exception:
                    pass
            elif "semana_cadastro" in df.columns:
                try:
                    nums = pd.to_numeric(df["semana_cadastro"], errors="coerce").astype("Int64")
                    years = (nums // 100).astype("Int64")
                    if emissao_inc:
                        mask &= years.isin(emissao_inc)
                    if emissao_exc:
                        mask &= ~years.isin(emissao_exc)
                except Exception:
                    pass

        execucao_inc = _to_int_set(filters.get("ano_execucao_values") or [])
        execucao_exc = _to_int_set(filters.get("ano_execucao_exclude_values") or [])
        if not execucao_inc and filters.get("ano_execucao") is not None:
            execucao_inc = _to_int_set([filters.get("ano_execucao")])
        if not execucao_exc and filters.get("ano_execucao_exclude") and filters.get("ano_execucao") is not None:
            execucao_exc = _to_int_set([filters.get("ano_execucao")])

        if "semana_executada" in df.columns and (execucao_inc or execucao_exc):
            try:
                nums = pd.to_numeric(df["semana_executada"], errors="coerce").astype("Int64")
                years = (nums // 100).astype("Int64")
                if execucao_inc:
                    mask &= years.isin(execucao_inc)
                if execucao_exc:
                    mask &= ~years.isin(execucao_exc)
            except Exception:
                pass

        def _apply_week_range(col, start_key, end_key, exclude_key):
            nonlocal mask
            if col not in df.columns:
                return
            start = filters.get(start_key)
            end = filters.get(end_key)
            if start is None and end is None:
                return
            try:
                nums = pd.to_numeric(df[col], errors="coerce")
                range_mask = pd.Series(True, index=df.index)
                if start is not None:
                    range_mask &= nums.ge(int(start))
                if end is not None:
                    range_mask &= nums.le(int(end))
                if filters.get(exclude_key):
                    mask &= ~range_mask
                else:
                    mask &= range_mask
            except Exception:
                pass

        _apply_week_range("semana_cadastro", "semana_emissao_inicio", "semana_emissao_fim", "semana_emissao_exclude")
        _apply_week_range("semana_executada", "semana_execucao_inicio", "semana_execucao_fim", "semana_execucao_exclude")

        derivada_has = bool(filters.get("derivada_has"))
        derivada_all_ste = bool(filters.get("derivada_all_ste"))
        derivada_is = bool(filters.get("derivada_is"))

        if "derivada_de" in df.columns:
            series_derivada = df["derivada_de"].apply(self._normalize_ssa_value)
            has_derivada = series_derivada.ne("")
            if derivada_is:
                mask &= has_derivada

            if (derivada_has or derivada_all_ste) and "numero_ssa" in df.columns:
                try:
                    origins = set(series_derivada[has_derivada].unique())
                except Exception:
                    origins = set()
                if derivada_all_ste and "situacao" in df.columns:
                    try:
                        derived = df[has_derivada].copy()
                        derived["_derivada_norm"] = series_derivada[has_derivada].values
                        grouped = derived.groupby("_derivada_norm")["situacao"].apply(
                            lambda s: s.astype(str).str.upper().eq("STE").all()
                        )
                        origins = set(grouped[grouped].index.astype(str).tolist())
                    except Exception:
                        origins = set()
                if origins:
                    try:
                        origin_norm = {str(o) for o in origins if str(o).strip()}
                        numero_norm = df["numero_ssa"].apply(self._normalize_ssa_value)
                        mask &= numero_norm.isin(origin_norm)
                    except Exception:
                        pass
                else:
                    mask &= False

        if mask.all():
            return df
        return df[mask]

    def load_data(self):
        if not os.path.exists(DB_PATH):
            QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' nao encontrado. Execute o programa principal primeiro.")
            return

        self.status_label.setText("Status: Carregando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        self.data_loader_thread = DataLoaderWorker(DB_PATH, TABLE_NAME)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_load_error)
        self.data_loader_thread.finished.connect(self.on_load_finished)
        try:
            self.data_loader_thread.finished.connect(self.data_loader_thread.deleteLater)
        except Exception:
            pass
        self.data_loader_thread.start()

    def on_data_loaded(self, df: pd.DataFrame):
        self.df_completo = df.copy()
        self._adv_options_dirty = True
        self._adv_values_cache = None
        # Inicialmente, exibimos todos os dados
        base = df.copy()
        # Ordenacao padrao: nao-STE primeiro; depois numero SSA desc
        try:
            if 'situacao' in base.columns:
                is_ste = base['situacao'].astype(str).str.upper().eq('STE')
            else:
                is_ste = pd.Series([False]*len(base), index=base.index)
            if 'numero_ssa' in base.columns:
                ssa_str = base['numero_ssa'].astype(str).str.replace(r'\D', '', regex=True)
                ssa_int = ssa_str.apply(lambda s: int(s) if s.isdigit() else -1)
            else:
                ssa_int = pd.Series([-1]*len(base), index=base.index)
            base = base.assign(__is_ste=is_ste, __ssa=ssa_int).sort_values(
                by=['__is_ste','__ssa'], ascending=[True, False], na_position='last'
            ).drop(columns=['__is_ste','__ssa'])
        except Exception as e:
            logger.warning("Falha na ordenacao inicial dos dados: %s", e)
        self.df_exibido = base
        self._df_last_search_filtered = df.copy()
        self._widths_computed_for_df_hash = None
        self.clear_filter_button.setEnabled(True)
        self._refresh_after_filter_change()
        try:
            self._refresh_advanced_filter_options()
        except Exception as e:
            logger.warning("Falha ao atualizar opcoes de filtros avancados: %s", e)
        try:
            self._update_derivadas_button_state()
        except Exception:
            pass
        profile_hint = f" (perfil: {self.current_filter_profile})" if self.current_filter_profile else ""
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs carregadas{profile_hint}. Pronto para filtrar.")

    def on_load_error(self, error_msg: str):
        QMessageBox.critical(self, "Erro de Carregamento", error_msg)
        self.status_label.setText("Status: Erro ao carregar dados.")
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_load_finished(self):
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        # Finalização segura do loader
        try:
            worker = getattr(self, 'data_loader_thread', None)
            if worker is not None:
                try:
                    if hasattr(worker, 'isRunning') and worker.isRunning():
                        worker.quit()
                        worker.wait(1500)
                except Exception:
                    pass
                try:
                    worker.deleteLater()
                except Exception:
                    pass
        finally:
            self.data_loader_thread = None

    def on_header_clicked(self, logical_index: int):
        try:
            if logical_index < 0 or self.table_widget.columnCount() == 0:
                return
            # Usa o mapa de colunas exibidas atualmente, que inclui '#'
            if not hasattr(self, '_current_display_columns'):
                return
            if logical_index >= len(self._current_display_columns):
                return
            col_name = self._current_display_columns[logical_index]
            # Ignora a coluna de ándice
            if col_name == '#':
                return

            # Alterna direçção ao clicar na mesma coluna
            if getattr(self, 'sort_column', None) == col_name:
                self.sort_ascending = not getattr(self, 'sort_ascending', True)
            else:
                self.sort_column = col_name
                self.sort_ascending = True

            # Ordena resultado filtrado atual e reinicia paginaçção
            try:
                self.df_exibido = self.df_exibido.sort_values(
                    by=self.sort_column,
                    ascending=self.sort_ascending,
                    na_position='last'
                )
            except Exception:
                pass

            self.paginator.set_dataframe(self.df_exibido)
            (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()

            # Indicador visual na UI
            try:
                header = self.table_widget.horizontalHeader()
                order = Qt.SortOrder.AscendingOrder if self.sort_ascending else Qt.SortOrder.DescendingOrder
                header.setSortIndicatorShown(True)
                header.setSortIndicator(logical_index, order)
            except Exception:
                pass
        except Exception:
            pass

    # --- Filtro por coluna via clique direito no cabeçalho ---
    def show_header_context_menu(self, pos):
        try:
            header = self.table_widget.horizontalHeader()
            logical_index = header.logicalIndexAt(pos)
            if logical_index < 0 or self.table_widget.columnCount() == 0:
                return
            if not hasattr(self, '_current_display_columns'):
                return
            if logical_index >= len(self._current_display_columns):
                return
            col_name = self._current_display_columns[logical_index]
            if col_name == '#':
                return

            menu = QMenu(self)
            full_name = DEFAULT_DISPLAY_MAPPINGS.get(col_name, self.internal_to_display.get(col_name, col_name))
            apply_action = QAction(f"Filtrar '{full_name}'...", self)
            clear_action = QAction("Limpar filtro desta coluna", self)
            clear_all_action = QAction("Limpar todos filtros de colunas", self)

            def _apply():
                term = None
                try:
                    from PyQt6.QtWidgets import QInputDialog
                except Exception:
                    QInputDialog = None
                if QInputDialog:
                    ok = False
                    term, ok = QInputDialog.getText(self, "Filtro por coluna", f"Termo para '{full_name}':")
                    if not ok:
                        term = None
                else:
                    term = self.search_input.text().strip()
                if term is not None:
                    self._active_column_filters[col_name] = str(term).strip()
                    self._mark_profile_as_custom()
                    self._build_column_filters_panel()
                    self._refresh_after_filter_change()

            def _clear():
                self._clear_single_column_filter(col_name)

            def _clear_all():
                self._clear_all_column_filters()

            apply_action.triggered.connect(_apply)
            clear_action.triggered.connect(_clear)
            clear_all_action.triggered.connect(_clear_all)

            menu.addAction(apply_action)
            if col_name in self._active_column_filters:
                menu.addAction(clear_action)
            if self._active_column_filters:
                menu.addAction(clear_all_action)
            menu.exec(header.mapToGlobal(pos))
        except Exception:
            pass

    # Garante menu de contexto no cabeçalho em qualquer tema/estilo
    def resizeEvent(self, event):
        """Detecta mudancas de tamanho da janela para adaptar layout."""
        try:
            super().resizeEvent(event)
        except Exception:
            pass

        # Reorganiza grid de filtros avancados se estiver na aba Filtros
        try:
            if getattr(self, "_current_tab_kind", None) == "filters":
                if hasattr(self, "adv_filters_group") and self.adv_filters_group:
                    width = self.adv_filters_group.width()
                    self._reorganize_advanced_filters_grid(width)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            header = self.table_widget.horizontalHeader()
            if obj is header:
                et = event.type()
                if et == QEvent.Type.ContextMenu:
                    self.show_header_context_menu(event.pos())
                    return True
                # Qt6: MouseButtonPress com botção direito
                if et == QEvent.Type.MouseButtonPress:
                    btn = getattr(event, 'button', lambda: None)()
                    if btn == Qt.MouseButton.RightButton:
                        # Compatável com position() (Qt6) e pos()
                        pos = getattr(event, 'position', None)
                        if callable(pos):
                            p = pos().toPoint()
                        else:
                            p = event.pos()
                        self.show_header_context_menu(p)
                        return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    # --- Helpers: painel e aplicaçção dos filtros por coluna ---
    def toggle_theme_menu(self):
        from PyQt6.QtWidgets import QMenu, QWidgetAction, QCheckBox
        from functools import partial
        menu = QMenu(self)
        # Em alguns estilos (Windows), QMenu ignora QPalette; aplique paleta/QSS com cores hex calculadas
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt as _Qt
            from PyQt6.QtGui import QPalette as _QPal
            app = QApplication.instance()
            pal = app.palette() if app is not None else self.palette()
            if app is not None:
                menu.setPalette(pal)
            try:
                menu.setAttribute(_Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            win = pal.color(_QPal.ColorRole.Window).name()
            wtxt = pal.color(_QPal.ColorRole.WindowText).name()
            mid = pal.color(_QPal.ColorRole.Mid).name()
            hi = pal.color(_QPal.ColorRole.Highlight).name()
            hitxt = pal.color(_QPal.ColorRole.HighlightedText).name()
            menu.setStyleSheet(
                f"QMenu {{ background-color: {win}; color: {wtxt}; border:1px solid {mid}; }}"
                f"QMenu::item:selected {{ background-color: {hi}; color: {hitxt}; }}"
                f"QMenu::separator {{ height:1px; background: {mid}; margin:4px 8px; }}"
            )
        except Exception:
            pass
        light_themes, dark_themes = self._get_theme_catalog()
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        theme_default = gui_settings.get("theme_default")
        current_theme = normalize_theme(getattr(self, "_current_theme", "") or theme_default or "gruvbox")
        roles = get_theme_roles(current_theme)
        try:
            from PyQt6.QtGui import QPalette as _QPal
            pal = menu.palette()
            wtxt = pal.color(_QPal.ColorRole.WindowText).name()
            win = pal.color(_QPal.ColorRole.Window).name()
        except Exception:
            wtxt = "#ffffff"
            win = "#000000"
        support_color = roles.get("support_text_color") or roles.get("label_color") or wtxt
        if support_color.lower() == win.lower():
            support_color = wtxt

        try:
            check_action = QWidgetAction(menu)
            check_widget = QCheckBox("Usar tema atual como padrao")
            check_widget.setChecked(normalize_theme(theme_default or "") == current_theme)
            try:
                check_widget.setStyleSheet(f"color: {wtxt}; padding: 4px 10px;")
            except Exception:
                pass
            def _toggle_default(checked):
                gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
                if checked:
                    active_theme = normalize_theme(getattr(self, "_current_theme", "") or "gruvbox")
                    gui_settings["theme_default"] = active_theme
                else:
                    gui_settings.pop("theme_default", None)
                self._persist_gui_preferences()
            check_widget.toggled.connect(_toggle_default)
            check_action.setDefaultWidget(check_widget)
            menu.addAction(check_action)
        except Exception:
            default_action = menu.addAction("Usar tema atual como padrao")
            if default_action is not None:
                try:
                    default_action.setCheckable(True)
                    default_action.setChecked(normalize_theme(theme_default or "") == current_theme)
                    def _toggle_default_action(checked):
                        gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
                        if checked:
                            active_theme = normalize_theme(getattr(self, "_current_theme", "") or "gruvbox")
                            gui_settings["theme_default"] = active_theme
                        else:
                            gui_settings.pop("theme_default", None)
                        self._persist_gui_preferences()
                    default_action.triggered.connect(_toggle_default_action)
                except Exception:
                    pass
        menu.addSeparator()

        def _add_label(text: str):
            try:
                from PyQt6.QtWidgets import QWidgetAction
                label = QLabel(text)
                try:
                    label_color = support_color
                    label.setStyleSheet(
                        f"color: {label_color}; font-weight: 600; padding: 4px 10px;"
                    )
                except Exception:
                    pass
                action = QWidgetAction(menu)
                action.setDefaultWidget(label)
                menu.addAction(action)
            except Exception:
                act = menu.addAction(text)
                if act is not None:
                    try:
                        act.setEnabled(False)
                    except Exception:
                        pass

        def _add_group(items):
            for label, key in items:
                act = menu.addAction(label)
                if act is not None:
                    trigger = getattr(act, "triggered", None)
                    if trigger is not None:
                        try:
                            trigger.connect(partial(self.apply_theme, key))
                        except Exception:
                            pass

        _add_label("Light")
        _add_group(sorted(light_themes, key=lambda item: item[0].lower()))
        menu.addSeparator()
        _add_label("Dark")
        _add_group(sorted(dark_themes, key=lambda item: item[0].lower()))

        try:
            labels = [name for name, _ in light_themes + dark_themes]
            fm = menu.fontMetrics()
            widest = max(fm.horizontalAdvance(lbl) for lbl in labels)
            menu.setMinimumWidth(widest + 48)
        except Exception:
            pass
        btn = self.sender()
        try:
            if btn is not None:
                menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        except Exception:
            pass

    def apply_theme(self, name: str):
        """
        Apply theme to the entire application and all widgets.

        This method is organized into clear sections for easy maintenance.
        See temp/THEME_ROLES_MAPPING.md for mapping of theme roles to widgets.

        Args:
            name: Theme name (will be normalized: 'dark', 'grayscale', 'gruvbox', etc.)
        """
        # ============================================================
        # SECTION 1: Theme Setup and Palette Loading
        # ============================================================
        # Normalize theme name and load QPalette from utils.themes
        normalized = normalize_theme(name)
        try:
            from PyQt6.QtWidgets import QApplication, QStyleFactory
            app = QApplication.instance()
            pal = get_palette(normalized)
            # Em Windows, alguns estilos ignoram QPalette em QMenu/ToolTip.
            # Para consistencia, force "Fusion" em todos os temas.
            try:
                if app is not None:
                    styles = QStyleFactory.keys()
                    if styles and 'Fusion' in styles:
                        app.setStyle('Fusion')
            except Exception:
                pass
            # Aplica paleta no aplicativo inteiro para garantir consistência
            if app is not None:
                app.setPalette(pal)
                # Injeta QSS com cores hex da paleta para Menu/Tooltip/ListViews (evita branco com letras claras)
                try:
                    app.setStyleSheet("")
                    block = build_global_widget_qss(pal)
                    app.setStyleSheet(block)
                except Exception:
                    pass
            # Garante também na janela atual
            self.setPalette(pal)
        except Exception:  # noqa: BLE001
            pal = get_palette(normalized)
            self.setPalette(pal)

            # ============================================================
            # SECTION 2: Application-Wide Widget Settings
            # ============================================================
            # Set central widget background and table header styling
            # Ensure central widget background matches the palette to avoid white boxes
            try:
                central = self.centralWidget()
                if central is not None:
                    try:
                        central.setStyleSheet("")
                    except Exception:
                        pass
                    existing = central.styleSheet() or ""
                    start = existing.find("/* SSA_MAIN_BG_START */")
                    if start != -1:
                        end = existing.find("/* SSA_MAIN_BG_END */", start)
                        if end != -1:
                            end += len("/* SSA_MAIN_BG_END */")
                            existing = (existing[:start] + existing[end:]).rstrip()
                        else:
                            existing = existing[:start].rstrip()
                    normalized_name = normalize_theme(normalized)
                    if normalized_name in {'grayscale', 'gruvbox', 'dark', 'dracula', 'solarized-dark', 'tokyo-night', 'catppuccin', 'nord'}:
                        bg = pal.window().color().name()
                        block = build_central_widget_qss(bg)
                        new_css = existing
                        if new_css:
                            if not new_css.endswith("\n"):
                                new_css += "\n"
                            new_css += block
                        else:
                            new_css = block
                        central.setStyleSheet(new_css)
                    else:
                        central.setStyleSheet(existing)
            except Exception:
                pass
            try:
                if hasattr(self, "main_tabs") and self.main_tabs is not None:
                    tab_bg = pal.color(_QPal.ColorRole.Window).name()
                    tab_text = pal.color(_QPal.ColorRole.WindowText).name()
                    tab_mid = pal.color(_QPal.ColorRole.Mid).name()
                    accent = roles.get('accent', tab_text)
                    support_color = roles.get('support_text_color', tab_text)
                    tab_css = (
                        "QTabWidget::pane {"
                        f" border:1px solid {tab_mid};"
                        f" background:{tab_bg};"
                        " margin:0; padding:0;"
                        " }"
                        "QTabBar::tab {"
                        f" color:{support_color}; background:{tab_bg};"
                        " padding:4px 10px; font-weight:500; border:1px solid transparent;"
                        " }"
                        "QTabBar::tab:selected {"
                        f" color:{tab_text}; font-weight:600; background:{tab_bg};"
                        f" border:1px solid {accent}; border-bottom:2px solid {accent};"
                        " margin-bottom:-1px; margin-top:1px;"
                        " }"
                        "QTabBar::tab:!selected {"
                        f" color:{support_color};"
                        " }"
                    )
                    self.main_tabs.setStyleSheet(tab_css)
            except Exception:
                pass
        try:
            header = self.table_widget.horizontalHeader()
            header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
        except Exception:
            pass

        # ============================================================
        # SECTION 3: Extract Theme Color Roles
        # ============================================================
        # Load all color roles from theme for widget styling
        # These variables are used in subsequent sections
        self._current_theme = normalized
        try:
            light_themes = {'windows7', 'classico', 'solarized-light', 'mint-light', 'paper'}
            selector = getattr(self, 'column_selector', None)
            pal_active = self.palette()
            from PyQt6.QtGui import QPalette as _QPal
            roles = get_theme_roles(normalized)
            txt = pal_active.color(_QPal.ColorRole.WindowText).name()
            base = pal_active.color(_QPal.ColorRole.Base).name()
            mid = pal_active.color(_QPal.ColorRole.Mid).name()
            high = pal_active.color(_QPal.ColorRole.Highlight).name()
            label_color = roles.get('label_color', txt)
            support_color = roles.get('support_text_color', label_color)
            indicator_color = roles.get('indicator_text_color', support_color)
            summary_color = roles.get('summary_text_color', label_color)
            summary_bg = roles.get('summary_frame_bg', roles.get('panel_bg', base))
            summary_border = roles.get('summary_frame_border', roles.get('panel_border', mid))
            accent = roles.get('accent', high)
            accent_soft = roles.get('accent_soft', support_color)
            input_bg = roles.get('input_bg', base)
            input_text = roles.get('input_text', txt)
            input_border = roles.get('input_border', mid)
            input_focus = roles.get('input_border_focus', accent)
            input_placeholder = roles.get('input_placeholder', support_color)
            panel_bg = roles.get('panel_bg', pal_active.color(_QPal.ColorRole.Window).name())
            panel_text = roles.get('panel_text', txt)
            panel_border = roles.get('panel_border', input_border)
            try:
                highlight_fg = pal_active.color(_QPal.ColorRole.HighlightedText).name()
            except Exception:
                highlight_fg = None
            self._highlight_bg_color = high or HIGHLIGHT_BACKGROUND_COLOR
            self._highlight_text_color = highlight_fg or None
            self._highlight_font_weight = HIGHLIGHT_FONT_WEIGHT

            # ============================================================
            # SECTION 4: Search Bar Components
            # ============================================================
            # Style the search label and search input field
            if hasattr(self, 'search_label'):
                self.search_label.setStyleSheet(f"color: {label_color}; font-weight: 600;")

            if hasattr(self, 'search_input') and self.search_input is not None:
                self.search_input.setStyleSheet(
                    build_line_edit_qss(input_text, input_bg, input_border, input_focus, input_placeholder)
                )

            tool_btn_css = (
                "QToolButton {"
                f" color: {input_text}; background: {input_bg}; border:1px solid {input_border};"
                " border-radius:4px; padding:2px 6px; }"
                "QToolButton:pressed {"
                f" background: {accent_soft}; }}"
            )
            adv_buttons = [
                "adv_executor_button",
                "adv_emissor_button",
                "adv_divisao_button",
                "adv_status_button",
                "adv_year_emissao_button",
                "adv_year_execucao_button",
                "adv_prioridade_emissao_button",
                "adv_prioridade_planejamento_button",
                "adv_responsavel_solicitante_button",
                "adv_responsavel_programacao_button",
                "adv_responsavel_execucao_button",
                "adv_responsavel_emissor_button",
            ]
            for name in adv_buttons:
                btn = getattr(self, name, None)
                if btn is not None:
                    try:
                        btn.setStyleSheet(tool_btn_css)
                    except Exception:
                        pass
            adv_line_edits = [
                "adv_week_emissao_start",
                "adv_week_emissao_end",
                "adv_week_execucao_start",
                "adv_week_execucao_end",
            ]
            for name in adv_line_edits:
                widget = getattr(self, name, None)
                if widget is not None:
                    try:
                        widget.setStyleSheet(
                            build_line_edit_qss(input_text, input_bg, input_border, input_focus, input_placeholder)
                        )
                    except Exception:
                        pass

            # ============================================================
            # SECTION 5: Details Panel
            # ============================================================
            # Style the SSA details text widget and its group box
            if hasattr(self, 'details_text'):
                if hasattr(self, 'details_group'):
                    try:
                        base_font = self.details_group.font()
                        small_font = QFont(base_font)
                        size = small_font.pointSizeF()
                        if size <= 0:
                            size = float(small_font.pointSize())
                        if size > 0:
                            small_font.setPointSizeF(max(size - 1.5, 1.0))
                        self.details_text.setFont(small_font)
                    except Exception:
                        pass
                if normalized in light_themes:
                    self.details_text.setStyleSheet('')
                else:
                    self.details_text.setStyleSheet(
                        "QTextEdit {"
                        f" color: {panel_text}; background: {panel_bg}; border: none; padding:4px;"
                        " }"
                    )

            group_css = build_group_box_qss(panel_text, panel_border, panel_bg)

            if hasattr(self, 'details_group'):
                if normalized in light_themes:
                    self.details_group.setStyleSheet('')
                else:
                    self.details_group.setStyleSheet(group_css)

            # ============================================================
            # SECTION 6: Column Filters Panel
            # ============================================================
            # Style the column filters group box
            if hasattr(self, 'col_filters_group'):
                if normalized in light_themes:
                    self.col_filters_group.setStyleSheet('')
                else:
                    self.col_filters_group.setStyleSheet(group_css)
            if hasattr(self, 'adv_filters_group'):
                if normalized in light_themes:
                    self.adv_filters_group.setStyleSheet('')
                else:
                    self.adv_filters_group.setStyleSheet(group_css)

            # ============================================================
            # SECTION 7: Status and Week Labels
            # ============================================================
            # Style the week indicator and status bar label
            highlight_style = (
                f"font-weight:600; color:{accent}; background:{panel_bg}; "
                f"border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
            )
            self._week_label_style = highlight_style
            if hasattr(self, 'week_label'):
                self.week_label.setStyleSheet(highlight_style)

            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(
                    f"color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
                )

            # ============================================================
            # SECTION 8: Support Text and Indicators
            # ============================================================
            # Style help text and filter indicator labels
            if hasattr(self, 'search_help'):
                css = f"font-size:10px; color:{support_color}; margin:0; padding:0;"
                if hasattr(self, 'status_label'):
                    try:
                        self.search_help.setFont(self.status_label.font())
                    except Exception:
                        pass
                self.search_help.setStyleSheet(css)

            if hasattr(self, 'col_filter_indicator'):
                self.col_filter_indicator.setStyleSheet(f"color:{indicator_color};")

            # ============================================================
            # SECTION 9: Filters Summary
            # ============================================================
            # Style the summary label and frame showing active filters
            if hasattr(self, 'filters_summary_label'):
                self.filters_summary_label.setStyleSheet(f"color:{summary_color};")

            if hasattr(self, 'filters_summary_frame'):
                self.filters_summary_frame.setStyleSheet(
                    "QFrame {"
                    f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px; padding:4px;"
                    " }"
                )
            if hasattr(self, 'clear_all_filters_btn'):
                self.clear_all_filters_btn.setStyleSheet(highlight_style)
            if hasattr(self, 'export_list_btn'):
                self.export_list_btn.setStyleSheet(highlight_style)
            if hasattr(self, 'undo_filter_btn'):
                self.undo_filter_btn.setStyleSheet(highlight_style)
            if hasattr(self, 'clear_all_btn'):
                self.clear_all_btn.setStyleSheet(highlight_style)

            # ============================================================
            # SECTION 10: Column Selector and Hints
            # ============================================================
            # Style the column selector widget and filter hints
            if selector is not None and hasattr(selector, 'summary_label'):
                selector.summary_label.setStyleSheet(f"color:{indicator_color};")

            if hasattr(self, 'col_filters_hint'):
                self.col_filters_hint.setStyleSheet(f"color:{support_color}; font-size: 11px;")
        except Exception:
            pass

        # ============================================================
        # SECTION 11: Dynamic Column Filter Widgets
        # ============================================================
        # Refresh all dynamically created column filter input widgets
        self._refresh_column_filter_widgets()

        # ============================================================
        # SECTION 12: Persistence and Platform Adjustments
        # ============================================================
        # Save theme preference and apply macOS-specific contrast fixes
        try:
            # Persistencia simples do tema sem normalizacao adicional
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = normalized
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._apply_macos_contrast(normalized)
        try:
            self.update_details_from_selection()
        except Exception:
            pass

    def _apply_macos_contrast(self, theme_name: str):
        if sys.platform != 'darwin':
            return
        normalized = normalize_theme(theme_name)
        roles = get_theme_roles(normalized)
        text_color = roles.get('panel_text')
        bg_color = roles.get('panel_bg')
        border_color = roles.get('panel_border')
        label_color = roles.get('label_color')
        block = (
            "/* SSA_MAC_QSS_START */\n"
            "QLineEdit, QTextEdit, QTextBrowser {"
            f" color:{text_color}; background-color:{bg_color}; border:1px solid {border_color}; }}\n"
            "QGroupBox, QLabel {"
            f" color:{label_color}; }}\n"
            "/* SSA_MAC_QSS_END */"
        )
        try:
            central = self.centralWidget()
            if central is not None:
                existing = central.styleSheet() or ""
                start = existing.find("/* SSA_MAC_QSS_START */")
                end = existing.find("/* SSA_MAC_QSS_END */", start)
                if start != -1 and end != -1 and end > start:
                    end += len("/* SSA_MAC_QSS_END */")
                    existing = existing[:start] + existing[end:]
                new_qss = (existing + ("\n" if existing and not existing.endswith("\n") else "") + block).strip()
                central.setStyleSheet(new_qss)
        except Exception:
            pass

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleçção de colunas muda."""
        self.visible_columns = new_columns
        if hasattr(self, 'column_selector') and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(new_columns)
            except Exception:
                pass
        # Reexibe a pãgina atual com as novas colunas
        self.display_current_page(self.paginator.current_page)
        # Nota: Persistencia de preferencias removida para isolamento do CLI
        # As configurações ficam no arquivo gui_main_preferences.json

    def display_current_page(self, page_number):
        """Exibe a pãgina especificada do DataFrame filtrado."""
        # Obtem o slice de dados para a pãgina atual do paginator
        self.df_para_tabela = self.paginator.get_current_slice()

        # Congela redimensionamento automático durante a reconstrução da tabela
        try:
            header = self.table_widget.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        except Exception:
            header = None

        if self.df_para_tabela.empty:
            # Mesmo sem linhas, mantenha as colunas visíveis e larguras aplicadas
            self.table_widget.setRowCount(0)
            # Determina colunas válidas a partir de df_exibido (mesmo vazio, mantém schema)
            valid_cols = []
            try:
                base_cols = list(getattr(self, 'df_exibido', pd.DataFrame()).columns)
                if base_cols:
                    valid_cols = [c for c in self.visible_columns if c in base_cols]
            except Exception:
                valid_cols = list(self.visible_columns)

            if not valid_cols:
                valid_cols = [c for c in self.default_columns if c in base_cols] if base_cols else list(self.visible_columns)

            # Atualiza colunas atuais (inclui '#') e aplica cabeçalhos
            self._current_display_columns = ['#'] + list(valid_cols)
            self.table_widget.setColumnCount(len(self._current_display_columns))
            headers = []
            for col in self._current_display_columns:
                base = '#' if col == '#' else self.internal_to_display.get(col, col)
                term = self._active_column_filters.get(col)
                has_filter = bool(term) and str(term).strip() != '' and col != '#'
                headers.append(f"[f] {base}" if has_filter else base)
            try:
                self.table_widget.setHorizontalHeaderLabels(headers)
            except Exception:
                pass

            # Aplica larguras salvas ou fallbacks seguros
            for i, col_name in enumerate(self._current_display_columns):
                px = self._saved_gui_column_widths.get(col_name)
                if px is None:
                    if col_name == '#':
                        px = 30
                    elif col_name == 'numero_ssa':
                        px = 110
                    elif col_name == 'localizacao_codigo':
                        px = 86
                    elif col_name == 'situacao':
                        px = 51
                    elif col_name == 'descricao_ssa':
                        px = 296
                    elif col_name == 'data_cadastro':
                        px = 100
                    elif col_name == 'setor_emissor':
                        px = 58
                    elif col_name == 'derivada_de':
                        px = 93
                    elif col_name == 'semana_programada':
                        px = 72
                    elif col_name == 'descricao_execucao':
                        px = 280
                    else:
                        px = 80
                try:
                    self.table_widget.setColumnWidth(i, max(30, int(px)))
                except Exception:
                    pass

            # Garantia extra para a primeira coluna de dados
            try:
                if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                    self.table_widget.setColumnWidth(1, 80)
            except Exception:
                pass

            # Restaura modo interativo com limites mínimos após aplicar larguras
            try:
                if header is not None:
                    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                    header.setMinimumSectionSize(80)
                    header.setDefaultSectionSize(100)
            except Exception:
                pass
            return

        # Seleciona apenas as colunas visáveis
        cols_to_show = [col for col in self.visible_columns if col in self.df_para_tabela.columns]
        if not cols_to_show:
            # Se nenhuma coluna selecionada for valida, mostra as padroes
            cols_to_show = [col for col in self.default_columns if col in self.df_para_tabela.columns]
            if not cols_to_show:
                # Ultimo recurso: mostra todas
                cols_to_show = self.df_para_tabela.columns.tolist()

        # Mantêm a ordem EXATA definida em gui_main_preferences.json
        # Sem reordenacao para garantir correspondencia com as larguras calculadas

        display_df = self.df_para_tabela[cols_to_show].copy()
        # Mantêm colunas atuais para mapear ándice->nome ao salvar larguras
        self._current_display_columns = ['#'] + list(display_df.columns)

        # Adiciona a coluna de ándice '#'
        if '#' not in display_df.columns:
            display_df.insert(
                0,
                '#',
                range(
                    (self.paginator.current_page - 1) * self.paginator.page_size + 1,
                    (self.paginator.current_page - 1) * self.paginator.page_size + 1 + len(display_df)
                ),
            )

        # Single display-formatting entrypoint for GUI table rendering.
        # Keep format_dataframe_for_display here to avoid scattered per-cell rules.
        # OTIMIZACAO: Cache formatacao para evitar reformatar dados inalterados
        display_df_hash = hash(str(display_df.shape) + str(list(display_df.columns)) + str(display_df.iloc[0].values.tobytes() if len(display_df) > 0 else ''))

        # Usa CacheManager unificado para cache de DataFrame formatado
        cached_formatted = self.cache_manager.get_cached_formatted_df(display_df_hash)
        if cached_formatted is None:
            try:
                formatted_df = format_dataframe_for_display(display_df)
                self.cache_manager.cache_formatted_df(display_df_hash, formatted_df)
                display_df = formatted_df
            except Exception:
                # falha de formataçção nção deve quebrar a GUI; segue sem formatar
                pass
        else:
            # Usa versção formatada do cache
            display_df = cached_formatted

    # Configura a tabela
        self.table_widget.setRowCount(len(display_df))
        self.table_widget.setColumnCount(len(display_df.columns))

        # Define cabeçalhos de exibiçção com indicador de filtro [f] por coluna
        display_headers = []
        for col in display_df.columns:
            base = '#' if col == '#' else self.internal_to_display.get(col, col)
            term = self._active_column_filters.get(col)
            has_filter = bool(term) and str(term).strip() != ''
            if has_filter and col != '#':
                base = f"[f] {base}"
            display_headers.append(base)
        self.table_widget.setHorizontalHeaderLabels(display_headers)

        # Preenche os dados usando batch operations para melhor performance
        columns_list = list(display_df.columns)
        for row_idx in range(len(display_df)):
            row_data = display_df.iloc[row_idx]
            for col_idx, col_name in enumerate(columns_list):
                value = row_data.iloc[col_idx]
                item_text = "" if pd.isna(value) else str(value)

                # CORRECAO v3.0.5: Nao truncar colunas de descricao e solicitante - deixar word wrap funcionar
                if col_name not in ['descricao_ssa', 'descricao_execucao', 'solicitante']:
                    # Trunca apenas colunas que nção sção de descriçção
                    max_chars = self._calculate_max_chars_for_column(col_name, col_idx)
                    if len(item_text) > max_chars:
                        item_text = item_text[:max_chars-3] + "..."

                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                # Armazena o indice da linha original nos dados filtrados para referencia
                if col_name == '#':
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        row_idx + (self.paginator.current_page - 1) * self.paginator.page_size,
                    )
                self.table_widget.setItem(row_idx, col_idx, item)

        # Recalcula larguras APENAS quando o conjunto/ordem de colunas muda
        # ou quando a largura util do viewport mudar significativamente
        cols_sig = tuple(display_df.columns)
        try:
            vw = self.table_widget.viewport().width()
        except Exception:
            vw = -1
        need_cols = (not hasattr(self, '_widths_columns_sig')) or (self._widths_columns_sig != cols_sig)
        need_vw = (not hasattr(self, '_last_viewport_w')) or (abs(vw - self._last_viewport_w) > 12)
        if need_cols or need_vw:
            self._compute_gui_column_widths(display_df)
            self._widths_columns_sig = cols_sig
            self._last_viewport_w = vw

        # Continuamos com header congelado (Fixed) até aplicar larguras calculadas
        header = self.table_widget.horizontalHeader()

        for i, col_name in enumerate(display_df.columns):
            # Usa a coluna diretamente do DataFrame (que jã inclui '#')
            col_key = col_name

            px = getattr(self, '_gui_column_pixel_widths', {}).get(col_key)

            # Se nção hã largura calculada, usa configuraçção salva manualmente pelo usuãrio
            if px is None:
                px = self._saved_gui_column_widths.get(col_key)

            # Fallbacks apenas se nenhuma das anteriores estiver disponável
            if px is None:
                if col_key == '#':
                    px = 30
                elif col_key == 'numero_ssa':
                    px = 110  # leve aumento para leitura do n┬║ SSA
                elif col_key == 'localizacao_codigo':
                    px = 86  # 10 chars * 7 + 16
                elif col_key == 'situacao':
                    px = 51  # 5 chars * 7 + 16
                elif col_key == 'descricao_ssa':
                    px = 296  # 40 chars * 7 + 16
                elif col_key == 'data_cadastro':
                    px = 100  # 12 chars * 7 + 16
                elif col_key == 'setor_emissor':
                    px = 58  # 6 chars * 7 + 16
                elif col_key == 'derivada_de':
                    px = 93  # 11 chars * 7 + 16
                elif col_key == 'semana_programada':
                    px = 72  # 8 chars * 7 + 16
                elif col_key == 'descricao_execucao':
                    px = 280  # Menor que descriçção_ssa
                else:
                    px = 80  # Fallback geral

            # Aplica limites de segurança apenas
            px = max(30, min(int(px), 1000))  # Permite larguras maiores para descriptions

            self.table_widget.setColumnWidth(i, px)

        # Reforça larguras após preencher dados para evitar zeragem em ambientes headless/CI
        try:
            self._force_column_widths()
        except Exception:
            pass

        # Garantia final: se alguma coluna ainda ficou com largura 0, aplica fallback seguro
        try:
            self._ensure_nonzero_column_widths()
        except Exception:
            pass

        # Após aplicar larguras, restaura modo interativo com limites mínimos
        try:
            if header is not None:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                header.setMinimumSectionSize(80)
                header.setDefaultSectionSize(100)
        except Exception:
            pass

        # Seleciona a primeira linha (se houver) e atualiza detalhes
        if self.table_widget.rowCount() > 0:
            self.table_widget.selectRow(0)
        self.update_details_from_selection()

        # Reaplica garantia de larguras não zeradas após eventos de layout pendentes
        try:
            QTimer.singleShot(0, self._ensure_nonzero_column_widths)
        except Exception:
            pass

    # --- Wrappers de compatibilidade com testes antigos (PoC) ---
    def display_data(self, df):  # usado em testes legados
        try:
            if df is None or getattr(df, 'empty', True):
                return
            self.df_completo = df.copy()
            self.df_exibido = df.copy()
            self.paginator.set_dataframe(self.df_exibido)
            self.display_current_page(getattr(self.paginator, 'current_page', 1))
        except Exception:
            pass

    def _force_column_widths(self):
        """Força reaplicaçção das larguras das colunas para garantir que sejam respeitadas."""
        if not hasattr(self, 'visible_columns') or not self.visible_columns:
            return

        for i, col_name in enumerate(['#'] + self.visible_columns):
            # Busca largura salva das configurações
            px = self._saved_gui_column_widths.get(col_name)
            if px is not None:
                current_width = self.table_widget.columnWidth(i)
                if current_width != px:
                    self.table_widget.setColumnWidth(i, int(px))

    def _ensure_nonzero_column_widths(self):
        """Garante que nenhuma coluna permaneça com largura 0.
        Estratégia simples por índice: se alguma coluna estiver com 0px, define 80px.
        """
        try:
            col_count = self.table_widget.columnCount()
            if col_count <= 0:
                return
            for i in range(col_count):
                if self.table_widget.columnWidth(i) == 0:
                    # Primeiro tenta dimensionar pelo conteúdo
                    try:
                        self.table_widget.resizeColumnToContents(i)
                    except Exception:
                        pass
                    if self.table_widget.columnWidth(i) == 0:
                        self.table_widget.setColumnWidth(i, 80)
        except Exception:
            pass

    def _set_safe_width_for_col_index(self, idx: int, px: int = 80):
        """Define uma largura segura para um índice de coluna, se possível."""
        try:
            if idx < 0:
                return
            if self.table_widget.columnCount() <= idx:
                return
            if self.table_widget.columnWidth(idx) == 0:
                self.table_widget.setColumnWidth(idx, max(30, int(px)))
        except Exception:
            pass

    def _compute_gui_column_widths(self, df: pd.DataFrame):
        """
        Calcula larguras de colunas usando o WidthManager unificado.
        Substitui 150+ linhas de codigo frankenstein por uma chamada limpa.
        """
        try:
            # Garante que visible_columns esteja definido
            if not hasattr(self, 'visible_columns') or not self.visible_columns:
                return

            # CORRECAO CRITICA: Filtra visible_columns para incluir apenas colunas que EXISTEM no DataFrame
            if hasattr(df, 'columns'):
                existing_visible_cols = [col for col in self.visible_columns if col in df.columns]
                if not existing_visible_cols:
                    print("ERRO: Nenhuma coluna visível encontrada no DataFrame")
                    return

                # IMPORTANTE: Mantêm a ordem exata de self.visible_columns
                visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
            else:
                visible_df = df

            # Obtêm largura da tabela
            widget_width = self.table_widget.width()

            if widget_width < 500:  # Tabela ainda nção inicializada
                table_width = max(1000 if sys.platform == 'darwin' else 1400, self.width() - 50)
            else:
                table_width = widget_width - 40  # Margem para scrollbars

            min_width = 1100 if sys.platform == 'darwin' else 1400
            table_width = max(table_width, min_width)

            # Usa o WidthManager para calcular larguras otimizadas
            # IMPORTANTE: Força ordem correta das colunas (adiciona '#' no inácio)
            correct_column_order = ['#'] + existing_visible_cols
            column_widths = self.width_manager.compute_optimal_widths(
                df=visible_df,
                available_width=table_width,
                display_mappings=self.internal_to_display,
                saved_widths=self._saved_gui_column_widths,
                column_order=correct_column_order
            )

            if sys.platform == "darwin":
                column_widths = {
                    key: (value + 2 if key != '#' else value)
                    for key, value in column_widths.items()
                }

            # Mantem compatibilidade com codigo existente
            self._gui_column_pixel_widths = column_widths

        except Exception as e:
            print(f"ERRO em _compute_gui_column_widths: {e}")
            # Fallback para larguras mánimas das colunas visáveis apenas
            visible_cols = ['#'] + (self.visible_columns if hasattr(self, 'visible_columns') else [])
            self._gui_column_pixel_widths = {col: 100 for col in visible_cols}

    def _calculate_max_chars_for_column(self, col_name: str, col_idx: int) -> int:
        """Calcula o numero maximo de caracteres baseado na largura da coluna."""
        try:
            # Usa largura calculada pelo WidthManager ou largura atual da coluna
            width_px = getattr(self, '_gui_column_pixel_widths', {}).get(col_name)
            if width_px is None:
                width_px = self.table_widget.columnWidth(col_idx)

            # Converte pixels em caracteres (aproximadamente 7px por caractere)
            max_chars = max(15, int((width_px - 10) / 6.5))  # Melhores proporções

            # Limites especáficos por tipo de coluna
            if col_name in ['descricao_ssa', 'descricao_execucao']:
                # Descrições podem usar toda largura disponável
                max_chars = max(50, max_chars)  # Mánimo mais alto para descrições
            elif col_name in ['numero_ssa', 'localizacao_codigo']:
                # Campos curtos nção precisam de muito espaço
                max_chars = min(max_chars, 25)
            elif col_name == 'solicitante':
                # Solicitante deve caber pelo menos "MAURICIO MENON"
                max_chars = max(15, max_chars)  # Garante pelo menos 15 caracteres
            else:
                # Campos gerais - mais generoso
                max_chars = min(max_chars, 80)  # Limite mais alto

            return max_chars
        except Exception:  # noqa: BLE001
            # Fallback mais generoso
            return 80

    def _on_header_section_resized(self, logical_index: int, old_size: int, new_size: int):
        """Salva a largura ajustada pelo usuãrio na configuraçção persistente."""
        try:
            cols = getattr(self, '_current_display_columns', None)
            if not cols or logical_index < 0 or logical_index >= len(cols):
                return
            col_name = cols[logical_index]
            new_px = max(30, min(int(new_size), 1200))
            if col_name:
                self._saved_gui_column_widths[col_name] = new_px
                if hasattr(self, '_gui_column_pixel_widths'):
                    self._gui_column_pixel_widths[col_name] = new_px
        except Exception:  # noqa: BLE001
            # Evita quebrar a GUI por falhas de IO
            pass

    def _normalize_highlight_term(self, term):
        """Remove modos e negacoes para uso no highlight."""
        if term is None:
            return ""
        cleaned = str(term).strip()
        if not cleaned:
            return ""
        if cleaned.startswith('!') or cleaned.startswith('-'):
            cleaned = cleaned[1:]
        if cleaned.startswith('~') or cleaned.startswith('=') or cleaned.startswith('^'):
            cleaned = cleaned[1:]
        if cleaned.endswith('$'):
            cleaned = cleaned[:-1]
        return cleaned.strip()

    def _get_current_search_terms(self):
        """Retorna lista de termos de busca atuais."""
        search_text = self.search_input.text().strip()
        if not search_text:
            return []
        # Split por virgulas
        terms = [term.strip() for term in search_text.split(',') if term.strip()]
        clean_terms = []
        for term in terms:
            normalized = self._normalize_highlight_term(term)
            if normalized:
                clean_terms.append(normalized)
        return clean_terms

    def _collect_highlight_terms(self):
        """Combina termos da busca geral e filtros de coluna para realce."""
        aggregated = []
        seen = set()
        for term in self._get_current_search_terms():
            if term and term not in seen:
                aggregated.append(term)
                seen.add(term)
        for raw in getattr(self, '_active_column_filters', {}).values():
            if not raw:
                continue
            normalized_raw = str(raw).replace(';', ',')
            tokens = [tok.strip() for tok in normalized_raw.split(',') if tok.strip()]
            for tok in tokens:
                normalized = self._normalize_highlight_term(tok)
                if normalized and normalized not in seen:
                    aggregated.append(normalized)
                    seen.add(normalized)
        return aggregated

    def _highlight_text(self, text, terms):
        """Delegate to helper function."""
        bg = getattr(self, '_highlight_bg_color', HIGHLIGHT_BACKGROUND_COLOR)
        fg = getattr(self, '_highlight_text_color', None)
        weight = getattr(self, '_highlight_font_weight', HIGHLIGHT_FONT_WEIGHT)
        return highlight_text(text, terms, bg, weight, fg)

    def _format_details_html(self, series, highlight_search_terms=False, font_size_pt=None, linkify=False):
        """Formata dados da SSA como HTML com highlight opcional."""
        # Single display-formatting entrypoint for details panel; keep format_cell here.
        # HTML is required here to keep search hit highlighting in the details panel.
        import html as html_module
        HIDDEN_DETAIL_FIELDS = {"id", "derivada_de"}

        if font_size_pt is None:
            font_size_pt = DETAILS_DIALOG_FONT_SIZE

        # Obtem termos de busca se necessario
        search_terms = (
            self._collect_highlight_terms() if highlight_search_terms else []
        )

        try:
            from PyQt6.QtGui import QPalette as _QPal
            text_color = self.palette().color(_QPal.ColorRole.WindowText).name()
            link_color = self.palette().color(_QPal.ColorRole.Highlight).name()
        except Exception:
            text_color = "#000000"
            link_color = text_color

        html_lines = [f'<html><body style="font-family: monospace; font-size: {font_size_pt}pt; color: {text_color};">']
        html_lines.append('<table style="width: 100%; border-collapse: collapse;">')

        # Ordenar campos: prioridade primeiro, depois alfabetico
        def field_sort_key(item):
            col, _ = item
            try:
                return (0, DETAIL_FIELD_PRIORITY.index(col))
            except ValueError:
                return (1, col)

        sorted_items = sorted(series.items(), key=field_sort_key)

        for col, value in sorted_items:
            if col in HIDDEN_DETAIL_FIELDS or str(col).startswith("_"):
                continue
            # Formata valor
            formatted_value = format_cell(value, col)

            # Pula campos vazios
            if not formatted_value:
                continue

            # Nome de exibicao
            display_name = DETAIL_DISPLAY_OVERRIDES.get(col, self.internal_to_display.get(col, col))

            # Aplica highlight se necessario
            if highlight_search_terms and search_terms:
                formatted_value = self._highlight_text(formatted_value, search_terms)
            else:
                formatted_value = html_module.escape(formatted_value)

            # Adiciona linha
            html_lines.append(
                f'<tr>'
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; font-weight: bold; width: 30%; vertical-align: top;">{html_module.escape(display_name)}:</td>'
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">{formatted_value}</td>'
                f'</tr>'
            )

        try:
            derived_list = self._get_derivadas_for_ssa(series.get("numero_ssa"))
        except Exception:
            derived_list = []
        if derived_list:
            if linkify:
                items = []
                for item in derived_list:
                    href = self._normalize_ssa_value(item)
                    display = html_module.escape(item)
                    items.append(
                        f'<a href="ssa://{href}" style="color:{link_color}; text-decoration:none; border-bottom: 1px solid {link_color};">'
                        f'{display}</a>'
                    )
                derived_text = ", ".join(items)
            else:
                derived_text = ", ".join(derived_list)
                if highlight_search_terms and search_terms:
                    derived_text = self._highlight_text(derived_text, search_terms)
                else:
                    derived_text = html_module.escape(derived_text)
            label = f"SSAs derivadas ({len(derived_list)})"
            html_lines.append(
                f'<tr>'
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; font-weight: bold; width: 30%; vertical-align: top;">{html_module.escape(label)}:</td>'
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">{derived_text}</td>'
                f'</tr>'
            )

        html_lines.append('</table></body></html>')
        return '\n'.join(html_lines)

    def on_table_double_click(self, index):
        """Mostra janela de detalhes formatada ao duplo clique."""
        row = index.row()
        index_item = self.table_widget.item(row, 0)
        if not index_item:
            return
        original_index = index_item.data(Qt.ItemDataRole.UserRole)
        if original_index is None or not (0 <= original_index < len(self.df_exibido)):
            QMessageBox.information(self, "Info", "Nao foi possivel encontrar os dados detalhados para esta linha.")
            return

        # Obtem dados da SSA
        series = self.df_exibido.iloc[int(original_index)]

        # Cria janela de dialogo
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalhes da SSA #{series.get('numero_ssa', 'N/A')}")
        dialog.setMinimumWidth(DETAILS_DIALOG_MIN_WIDTH)
        dialog.setMinimumHeight(DETAILS_DIALOG_MIN_HEIGHT)

        layout = QVBoxLayout(dialog)

        # Texto formatado com HTML
        # CORRECAO 2026-01-08: linkify=True e conectar anchorClicked para navegacao funcionar
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(False)
        text_browser.anchorClicked.connect(self._on_details_anchor_clicked)

        # Formata conteudo com links clicaveis
        html_content = self._format_details_html(series, highlight_search_terms=True, linkify=True)
        text_browser.setHtml(html_content)

        layout.addWidget(text_browser)

        # Botao fechar
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def _save_page_size_pref(self, new_size: int):
        """Persiste o tamanho da pãgina no settings."""
        # Nota: Persistencia removida para isolamento do CLI
        # O tamanho da pãgina fica configurado no arquivo gui_main_preferences.json
        pass

    def _get_series_from_row(self, row: int):
        try:
            index_item = self.table_widget.item(row, 0)
        except Exception:
            return None
        if not index_item:
            return None
        try:
            original_index = index_item.data(Qt.ItemDataRole.UserRole)
        except Exception:
            original_index = None
        if original_index is None or not (0 <= original_index < len(self.df_exibido)):
            return None
        try:
            return self.df_exibido.iloc[int(original_index)]
        except Exception:
            return None

    def _normalize_ssa_value(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        lowered = text.casefold()
        if lowered in ("nan", "none", "nat"):
            return ""
        try:
            digits = re.sub(r"\D", "", text)
        except Exception:
            digits = ""
        if digits:
            return digits
        return lowered

    def update_details_from_selection(self):
        """Atualiza o painel de detalhes com base na linha selecionada."""
        if self.table_widget.rowCount() == 0:
            self.details_text.clear()
            return
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            self.details_text.clear()
            return
        row = selected_rows[0].row()
        series = self._get_series_from_row(row)
        if series is None:
            self.details_text.clear()
            return

        try:
            font_size_pt = None
            if hasattr(self, 'details_group'):
                try:
                    base_font = self.details_group.font()
                    size = base_font.pointSizeF()
                    if size <= 0:
                        size = float(base_font.pointSize())
                    if size > 0:
                        # HTML content sets its own font-size; adjust here to keep details smaller.
                        font_size_pt = max(size - 1.0, 8.0)
                except Exception:
                    font_size_pt = None
            html_content = self._format_details_html(
                series,
                highlight_search_terms=True,
                font_size_pt=font_size_pt,
                linkify=True,
            )
            self.details_text.setHtml(html_content)
            return
        except Exception:
            pass

        # Fallback para texto simples se HTML nao estiver disponivel
        def field_sort_key(item):
            col, _ = item
            try:
                return (0, DETAIL_FIELD_PRIORITY.index(col))
            except ValueError:
                return (1, col)

        sorted_items = sorted(series.items(), key=field_sort_key)
        lines = []
        for col, value in sorted_items:
            if col in {"id", "derivada_de"} or str(col).startswith("_"):
                continue
            formatted_value = format_cell(value, col)
            if not formatted_value:
                continue
            display_name = DETAIL_DISPLAY_OVERRIDES.get(col, self.internal_to_display.get(col, col))
            lines.append(f"{display_name}: {formatted_value}")
        details_str = "\n".join(lines)
        try:
            self.details_text.setPlainText(details_str)
        except Exception:
            pass

    def _get_derivadas_for_ssa(self, numero_ssa):
        if self.df_completo is None or self.df_completo.empty:
            return []
        if "derivada_de" not in self.df_completo.columns or "numero_ssa" not in self.df_completo.columns:
            return []
        num_norm = self._normalize_ssa_value(numero_ssa)
        if not num_norm:
            return []
        try:
            series_norm = self.df_completo["derivada_de"].apply(self._normalize_ssa_value)
            mask = series_norm.eq(num_norm)
            derived_raw = self.df_completo.loc[mask, "numero_ssa"].tolist()
            derived = []
            for value in derived_raw:
                formatted = format_cell(value, "numero_ssa")
                if formatted:
                    derived.append(formatted)
            return derived
        except Exception:
            return []

    def _jump_to_ssa(self, numero_ssa):
        num_norm = self._normalize_ssa_value(numero_ssa)
        if not num_norm:
            return
        try:
            df_reset = self.df_exibido.reset_index(drop=True)
            if "numero_ssa" not in df_reset.columns:
                return
            series_norm = df_reset["numero_ssa"].apply(self._normalize_ssa_value)
            mask = series_norm.eq(num_norm)
            if not mask.any():
                self.search_input.setText(f"={num_norm}")
                self.initiate_filtering()
                return
            pos = int(mask[mask].index[0])
            page_size = int(getattr(self.paginator, "page_size", 50))
            page = int(pos // page_size + 1)
            try:
                self.paginator.current_page = page
            except Exception:
                pass
            self.display_current_page(page)
            row_in_page = int(pos % page_size)
            try:
                self.table_widget.selectRow(row_in_page)
            except Exception:
                pass
        except Exception:
            pass

    def _on_details_anchor_clicked(self, url):
        try:
            href = url.toString()
        except Exception:
            return
        if not href:
            return
        if href.startswith("ssa://"):
            target = href[len("ssa://"):]
        elif href.startswith("ssa:"):
            target = href[len("ssa:"):]
        else:
            return
        target = target.strip().lstrip("/")
        if target:
            self._jump_to_ssa(target)

    def _filter_by_derivadas(self, numero_ssa):
        num_norm = self._normalize_ssa_value(numero_ssa)
        if not num_norm:
            return
        self._last_derivada_origem = num_norm
        self._active_column_filters["derivada_de"] = num_norm
        try:
            self._build_column_filters_panel()
        except Exception:
            pass
        self._refresh_after_filter_change()

    def _clear_derivadas_filter(self):
        if "derivada_de" in self._active_column_filters:
            self._active_column_filters.pop("derivada_de", None)
        try:
            self._build_column_filters_panel()
        except Exception:
            pass
        self._refresh_after_filter_change()
        if self._last_derivada_origem:
            self._jump_to_ssa(self._last_derivada_origem)
            self._last_derivada_origem = None

    def show_context_menu(self, position):
        """Mostra menu de contexto na tabela."""
        if self.table_widget.itemAt(position):
            menu = QMenu(self)

            # Acoes para celulas
            copy_cell_action = QAction("Copiar Valor da Celula", self)
            copy_cell_action.triggered.connect(self.copy_cell_value)
            menu.addAction(copy_cell_action)

            copy_row_action = QAction("Copiar Linha Completa", self)
            copy_row_action.triggered.connect(self.copy_row_data)
            menu.addAction(copy_row_action)

            export_action = QAction("Exportar lista (txt)", self)
            export_action.triggered.connect(self._export_current_list_txt)
            menu.addAction(export_action)

            menu.addSeparator()

            current_item = self.table_widget.itemAt(position)
            row_series = None
            if current_item:
                try:
                    row_series = self._get_series_from_row(current_item.row())
                except Exception:
                    row_series = None

            if row_series is not None:
                numero_ssa = str(row_series.get("numero_ssa", "")).strip()
                derivada_de = str(row_series.get("derivada_de", "")).strip()
                derived_list = self._get_derivadas_for_ssa(numero_ssa) if numero_ssa else []
                if derivada_de:
                    origem_action = QAction("Ir para SSA origem", self)
                    origem_action.triggered.connect(lambda: self._jump_to_ssa(derivada_de))
                    menu.addAction(origem_action)
                if derived_list:
                    label = f"Mostrar derivadas ({len(derived_list)})"
                    derivadas_action = QAction(label, self)
                    derivadas_action.triggered.connect(lambda: self._filter_by_derivadas(numero_ssa))
                    menu.addAction(derivadas_action)
                if self._last_derivada_origem:
                    voltar_action = QAction("Voltar SSA origem", self)
                    voltar_action.triggered.connect(self._clear_derivadas_filter)
                    menu.addAction(voltar_action)
                menu.addSeparator()

            # Acoes para colunas
            if current_item:
                column = current_item.column()
                if column > 0:  # Nção permitir remover a coluna de ándice
                    column_name = self.table_widget.horizontalHeaderItem(column).text()

                    remove_column_action = QAction(f"Remover Coluna '{column_name}'", self)
                    remove_column_action.triggered.connect(lambda: self.remove_column_by_index(column))
                    menu.addAction(remove_column_action)

                    auto_fit_action = QAction(f"Ajustar Largura '{column_name}'", self)
                    auto_fit_action.triggered.connect(lambda: self.auto_fit_column(column))
                    menu.addAction(auto_fit_action)

            menu.exec(self.table_widget.mapToGlobal(position))

    def copy_cell_value(self, *_):  # QAction triggered pode enviar 'checked'
        """Copia o valor da celula selecionada."""
        current_item = self.table_widget.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(current_item.text())

    def copy_row_data(self, *_):  # aceita args opcionais de QAction
        """Copia todos os dados da linha selecionada."""
        current_row = self.table_widget.currentRow()
        if current_row >= 0:
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(current_row, col)
                row_data.append(item.text() if item else "")

            clipboard = QApplication.clipboard()
            clipboard.setText("\t".join(row_data))

    def _export_current_list_txt(self):
        if self.df_exibido is None or self.df_exibido.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado para exportar.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Exportar lista", "", "Text Files (*.txt)")
        except Exception:
            path = ""
        if not path:
            return
        cols = [col for col in self.visible_columns if col in self.df_exibido.columns]
        if not cols:
            cols = list(self.df_exibido.columns)
        export_df = self.df_exibido[cols].copy()
        try:
            export_df = format_dataframe_for_display(export_df)
        except Exception as e:
            logger.warning("Falha ao formatar dataframe para exportacao: %s", e)
        try:
            export_df.to_csv(path, sep="\t", index=False)
        except Exception as e:
            logger.error("Falha ao exportar lista para arquivo: %s", e)
            QMessageBox.information(self, "Aviso", "Falha ao exportar a lista.")

    def remove_column_by_index(self, column_index):
        """Remove uma coluna especáfica baseada no ándice."""
        if column_index > 0 and column_index < len(self.visible_columns):  # Protege coluna de ándice
            internal_column = self.visible_columns[column_index - 1]  # -1 porque hã coluna '#'
            if internal_column in self.visible_columns:
                self.visible_columns.remove(internal_column)
                self.on_columns_changed(self.visible_columns)

    def auto_fit_column(self, column_index):
        """Ajusta automaticamente a largura da coluna baseada no conteudo."""
        self.table_widget.resizeColumnToContents(column_index)
        # Salva a nova largura
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        if header_item and column_index > 0:  # Nção salvar largura da coluna de ándice
            internal_column = self.visible_columns[column_index - 1] if column_index <= len(self.visible_columns) else None
            if internal_column:
                new_width = self.table_widget.columnWidth(column_index)
                self._save_column_width(internal_column, new_width)

    def rescan_data(self):
        """Reprocessa os arquivos Excel com feedback visual em tempo real."""
        from gui.workers import RescanWorker
        from gui.widgets import RescanProgressDialog

        # Check if main.py exists
        main_py_path = os.path.join(project_root, 'main.py')
        if not os.path.exists(main_py_path):
            QMessageBox.warning(self, "Erro", f"Arquivo main.py nao encontrado em {main_py_path}")
            return

        # Create progress dialog
        progress_dialog = RescanProgressDialog(self)

        # Create and configure worker
        worker = RescanWorker(main_py_path, project_root)

        # Connect signals
        worker.output_line.connect(progress_dialog.append_output)
        worker.error_line.connect(progress_dialog.append_error)
        worker.progress.connect(progress_dialog.update_progress)

        def on_success():
            progress_dialog.set_finished(True)
            self.status_label.setText("Status: Reescaneamento concluido. Clique em 'Carregar Dados' para atualizar.")

        def on_error(error_msg):
            progress_dialog.set_finished(False, error_msg)
            self.status_label.setText("Status: Erro no reescaneamento.")

        worker.finished_success.connect(on_success)
        worker.finished_error.connect(on_error)

        # Handle dialog rejection (cancel button)
        def on_dialog_rejected():
            if worker.isRunning():
                worker.stop()
                worker.wait(2000)  # Wait up to 2 seconds
                if worker.isRunning():
                    worker.terminate()

        progress_dialog.rejected.connect(on_dialog_rejected)

        # Start worker and show dialog
        worker.start()
        progress_dialog.exec()

        # Cleanup
        if worker.isRunning():
            worker.wait()

    def open_docs_folder(self):
        """Abre a pasta docs_entrada no Windows Explorer."""
        docs_path = os.path.join(project_root, 'docs_entrada')

        if os.path.exists(docs_path):
            try:
                # Abre no Windows Explorer
                subprocess.run(['explorer', docs_path], check=True)
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao abrir pasta: {e}")
        else:
            QMessageBox.warning(self, "Erro", f"Pasta nao encontrada: {docs_path}")

    def load_other_database(self):
        """Permite selecionar e carregar outro arquivo de banco de dados."""
        file_dialog = QFileDialog()
        db_file, _ = file_dialog.getOpenFileName(
            self,
            "Selecionar Banco de Dados",
            os.path.join(project_root, 'data'),
            "Arquivos de Banco (*.db *.sqlite);;Todos os Arquivos (*)"
        )

        if db_file and os.path.exists(db_file):
            try:
                # Testa se o arquivo eh um banco valido
                test_df = query_db(db_file, TABLE_NAME)
                if test_df is not None and not test_df.empty:
                    # Atualiza o caminho do banco
                    global DB_PATH
                    DB_PATH = db_file
                    self.status_label.setText(f"Status: Banco alternativo selecionado: {os.path.basename(db_file)}")
                    QMessageBox.information(self, "Sucesso", f"Banco de dados selecionado: {os.path.basename(db_file)}\n\nClique em 'Carregar Dados' para carregar os dados.")
                else:
                    QMessageBox.warning(self, "Erro", "O arquivo selecionado nao contem dados validos na tabela 'ssas'.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir o banco de dados: {e}")
        elif db_file:  # Arquivo selecionado mas nao existe
            QMessageBox.warning(self, "Erro", "Arquivo selecionado nao existe.")

    def remove_persistent_filter(self, filter_data):
        """Remove um filtro persistente e atualiza imediatamente."""
        if filter_data in self.persistent_filters:
            self.persistent_filters.remove(filter_data)
            self.update_filter_tags()
            # Atualiza imediatamente se o filtro removido estava ativo
            current_search = self.search_input.text().strip()
            if current_search == filter_data["terms"]:
                self.search_input.clear()
                self.initiate_filtering()

    def resizeEvent(self, event):
        """Reotimiza larguras das colunas quando a janela eh redimensionada."""
        super().resizeEvent(event)

        # So recalcula se ha dados carregados e uma mudanca significativa na largura
        if (hasattr(self, 'df_exibido') and not self.df_exibido.empty and
            hasattr(self, '_last_window_width')):
            width_change = abs(event.size().width() - self._last_window_width)
            if width_change > 12:  # So recalcula se mudanca for > 12px
                # Delay para evitar recãlculos excessivos durante resize
                QTimer.singleShot(300, self._recompute_column_widths_on_resize)

        # Salva largura atual
        self._last_window_width = event.size().width()

    def _recompute_column_widths_on_resize(self):
        """Recalcula e aplica larguras das colunas apos resize da janela."""
        try:
            # Verifica se widgets estção em estado vãlido
            if (not hasattr(self, 'df_para_tabela') or self.df_para_tabela.empty or
                not self.table_widget or not self.table_widget.isVisible()):
                return

            # Recalcula larguras com nova dimensção da janela usando WidthManager
            self._compute_gui_column_widths(self.df_para_tabela)
            # Aplica as novas larguras
            self._apply_computed_widths_only()
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.exception("Column width recompute failed during resize")

    def _apply_computed_widths_only(self):
        """Aplica apenas as larguras calculadas pelo WidthManager (ignora configurações salvas)."""
        try:
            if (not hasattr(self, 'df_para_tabela') or self.df_para_tabela.empty or
                not hasattr(self, '_gui_column_pixel_widths') or
                not self.table_widget or not self.table_widget.isVisible()):
                return

            # CORRECAO CRITICA: Usar _current_display_columns que contem apenas as colunas visiveis filtradas
            # Em vez de ['#'] + todas as colunas do df_para_tabela
            if not hasattr(self, '_current_display_columns') or not self._current_display_columns:
                return

            table_columns = self._current_display_columns

            # Aplicar larguras para todas as colunas definidas
            for col_name, px in self._gui_column_pixel_widths.items():
                if col_name in table_columns and px and px > 0:
                    col_index = table_columns.index(col_name)
                    if col_index < self.table_widget.columnCount():
                        current_width = self.table_widget.columnWidth(col_index)
                        if current_width != px:  # So aplica se diferente
                            self.table_widget.setColumnWidth(col_index, px)

        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.exception("Column width apply failed during resize handling")

    def closeEvent(self, event):
        """
        Metodo chamado quando a janela eh fechada.
        Garante cleanup adequado dos QThreads para evitar o erro:
        'QThread: Destroyed while thread is still running'
        """
        # Aguarda finalizacao do data loader thread se estiver rodando
        if hasattr(self, 'data_loader_thread') and self.data_loader_thread and self.data_loader_thread.isRunning():
            self.data_loader_thread.quit()
            self.data_loader_thread.wait(3000)  # Aguarda ate 3 segundos

        # Aguarda finalizacao do filter thread se estiver rodando
        if hasattr(self, 'filter_thread') and self.filter_thread and self.filter_thread.isRunning():
            # Desconecta sinais para evitar callbacks tardios durante teardown
            try:
                self.filter_thread.finished.disconnect(self.on_filter_finished_cleanup)
            except (TypeError, RuntimeError, AttributeError) as exc:
                logger.debug("Signal disconnect skipped during close cleanup: %s", exc)
            try:
                self.filter_thread.filter_finished.disconnect(self.on_filter_finished)
            except (TypeError, RuntimeError, AttributeError) as exc:
                logger.debug("Signal disconnect skipped during close cleanup: %s", exc)
            try:
                self.filter_thread.error_occurred.disconnect(self.on_filter_error)
            except (TypeError, RuntimeError, AttributeError) as exc:
                logger.debug("Signal disconnect skipped during close cleanup: %s", exc)
            self.filter_thread.quit()
            self.filter_thread.wait(3000)  # Aguarda ate 3 segundos

        # Aceita o evento de fechamento
        event.accept()

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
