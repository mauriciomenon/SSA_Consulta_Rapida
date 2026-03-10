# flake8: noqa
# gui_ssa.py (GUI PyQt6 para SSA_Consulta_Rapida)
# Last modified: 2025-10-30T16:05:00 (search simplification with explicit semantics in general/column filter tooltips)
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
import shutil
import re
import logging
import copy
import sqlite3
import threading
from datetime import datetime
from collections import OrderedDict
from time import perf_counter
from typing import Any, cast


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
from gui.ssa import gui_theme as ssa_gui_theme  # noqa: E402
from gui.ssa import gui_workers as ssa_gui_workers  # noqa: E402
from gui.ssa import gui_filters_advanced as ssa_gui_filters  # noqa: E402
from gui.ssa import gui_table as ssa_gui_table  # noqa: E402
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from utils.themes import get_theme_roles, normalize_theme  # noqa: E402
from core.config_manager import (  # noqa: E402
    DEFAULT_DISPLAY_MAPPINGS,
    COLUMN_AFFINITY_SCORES,
    atomic_write_json_file,
)
from shared.db_names import ALL_SSA_TABLE_NAMES, CANONICAL_SSA_TABLE  # noqa: E402
from gui.gui_config import (  # noqa: E402
    GUI_MAIN_PREFERENCES,
    REQUIRED_DISPLAY_COLUMNS,
    COMPATIBILITY_NULL_UI_COLUMNS,
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

# Retencao global defensiva para workers de carga que sobrevivem ao ciclo da janela.
GLOBAL_RETIRED_DATA_LOADER_WORKERS = []
MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS = 64
GLOBAL_RETIRED_DATA_LOADER_META = {}

# Retencao global defensiva para workers de reescaneamento (importacao) que podem
# continuar por alguns instantes apos o fechamento do dialogo modal.
GLOBAL_RETIRED_RESCAN_WORKERS = []
MAX_GLOBAL_RETIRED_RESCAN_WORKERS = 8
GLOBAL_RETIRED_RESCAN_META = {}

RETIRED_WORKER_TTL_SEC = 300.0
RETIRED_WORKER_FORCE_WAIT_MS = 500
logger.addHandler(logging.NullHandler())

EXCLUDED_CANONICAL_UI_COLUMNS = {
    "id",
    "desde",
    "desde_1",
    "desde_2",
    "ate",
    "ate_1",
    "ate_2",
    "tempo_excedido",
    "tempo_total",
    "tempo_disponivel",
    "total_tempo_tpe_planejado",
    "total_tempo_tex_planejado",
    "total_tempo_tpo_planejado",
    "total_tempo_tpe_executada",
    "total_tempo_tex_executada",
    "total_tempo_tpo_executada",
    "total_horas_programadas",
    "prazo_limite",
    "data_limite",
    "status_execucao_prazo",
    "sistema_origem",
    "registros_espera",
    "num_reprobaciones",
    "situacao_espera",
    "numero_desvios",
    "justificativa",
    "parciais",
    "situacao_da_parcial",
    "atividade_especial",
    "equipamento_retirado",
    "sn_retirado",
    "destino",
    "equipamento_instalado",
    "sn_instalado",
    "sn_extra",
    "origem",
    "desativacao_da_localizacao",
    "instalacao_estimada",
    "executado",
    "concluido",
    "situacao_de_desvio",
    "relacao",
}

from utils.formatting import format_dataframe_for_display, format_cell  # noqa: E402

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms  # noqa: E402
import hashlib
from armazenamento.database import query_db  # noqa: E402
from armazenamento.derivadas_sync import scan_derivadas_consistency, sync_derivadas  # noqa: E402

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
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QPoint, QSignalBlocker, QUrl
    from PyQt6.QtGui import QAction, QFont, QDesktopServices

    # Import workers, cache, widgets, and helpers from separate modules
    from gui.workers import DataLoaderWorker, FilterWorker  # noqa: E402
    from gui.cache import FilterCache  # noqa: E402
    from gui.widgets import ColumnManagerDialog, ColumnSelector, DataPaginator, FilterHelpDialog  # noqa: E402
    from gui.helpers import (  # noqa: E402
        normalize_chunk_for_parse, format_search_display, highlight_text
    )
    # Import mixins for code organization
    from gui.mixins import FilterGUISSAMixin, TabContextGUISSAMixin  # noqa: E402
except ImportError as exc:
    QT_AVAILABLE = False
    sip = cast(Any, None)
    logger.warning("PyQt6 import failed, using headless stub mode: %s", exc)
    DataLoaderWorker = cast(Any, None)
    FilterWorker = cast(Any, None)
    FilterCache = cast(Any, None)
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
        def __getattr__(self, _name):
            def _noop(*_args, **_kwargs):
                return None
            return _noop

    class QMainWindow(QWidget):
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
        @staticmethod
        def processEvents(*a, **k):
            return None
        @staticmethod
        def clipboard():
            class _Clipboard:
                def setText(self, *a, **k):
                    pass
            return _Clipboard()

    class QVBoxLayout:
        def __init__(self, *a, **k):
            pass
        def addWidget(self, *a, **k):
            pass
        def addLayout(self, *a, **k):
            pass
        def addStretch(self, *a, **k):
            pass
        def addSpacing(self, *a, **k):
            pass
        def setSpacing(self, *a, **k):
            pass
        def setContentsMargins(self, *a, **k):
            pass

    class QHBoxLayout(QVBoxLayout):
        def addItem(self, *a, **k):
            pass

    class QGridLayout(QVBoxLayout):
        pass
    class QTabWidget(QWidget):
        def __init__(self, *a, **k):
            self.currentChanged = _Sig()
        def addTab(self, *a, **k):
            pass
        def setStyleSheet(self, *a, **k):
            pass
    class QLabel(QWidget):
        def __init__(self, *a, **k):
            pass
    class QPushButton(QWidget):
        def __init__(self, *a, **k):
            self.clicked = _Sig()
            self.toggled = _Sig()
            self._text = a[0] if a else ""
            self._checkable = False
            self._checked = False
        def setToolTip(self, *a, **k):
            pass
        def setEnabled(self, *a, **k):
            pass
        def setText(self, text):
            self._text = text
        def text(self):
            return self._text
        def setCheckable(self, enabled):
            self._checkable = bool(enabled)
        def setChecked(self, val):
            self._checked = bool(val)
        def isChecked(self):
            return self._checked
        def setStyleSheet(self, *a, **k):
            pass
        def setMaximumWidth(self, *a, **k):
            pass
    class QLineEdit(QWidget):
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
    class QTableWidget(QWidget):
        class EditTrigger:
            NoEditTriggers = 0

    class QTableWidgetItem:
        def __init__(self, *a, **k):
            pass

    class QHeaderView(QWidget):
        Stretch = 1
        class ResizeMode:
            Stretch = 1
            Interactive = 2
            Fixed = 3
    class QMessageBox:
        @staticmethod
        def information(*a, **k):
            return 0
        @staticmethod
        def warning(*a, **k):
            return 0
        @staticmethod
        def critical(*a, **k):
            return 0

    class QProgressBar(QWidget):
        pass
    class QComboBox(QWidget):
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
    class QSpinBox(QWidget):
        pass

    class QAbstractItemView:
        NoEditTriggers = 0
        class SelectionBehavior:
            SelectRows = 0

    class QMenu(QWidget):
        def __init__(self, *a, **k):
            self._actions = []
        def addAction(self, *args, **kwargs):
            if args and isinstance(args[0], QAction):
                action = args[0]
            else:
                label = str(args[0]) if args else ""
                action = QAction(label)
                callback = args[1] if len(args) > 1 else None
                if callable(callback):
                    action.triggered.connect(callback)
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

    class QToolButton(QWidget):
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

    class QGroupBox(QWidget):
        def __init__(self, *a, **k):
            pass
        def setVisible(self, *a, **k):
            pass
        def setEnabled(self, *a, **k):
            pass

    class QTextEdit(QWidget):
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
        def setOpenLinks(self, *a, **k):
            pass
        def setOpenExternalLinks(self, *a, **k):
            pass

    class QScrollArea(QWidget):
        def __init__(self, *a, **k):
            pass
        def setWidgetResizable(self, *a, **k):
            pass
        def setWidget(self, *a, **k):
            pass

    class QFileDialog:
        @staticmethod
        def getSaveFileName(*a, **k):
            return ("", "")
        @staticmethod
        def getOpenFileName(*a, **k):
            return ("", "")
        @staticmethod
        def getOpenFileNames(*a, **k):
            return ([], "")

    class QAction:
        def __init__(self, *a, **k):
            self.triggered = _Sig()

    class QDialog(QWidget):
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

    class QListWidget(QWidget):
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

    class QCheckBox(QWidget):
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
        def __init__(self, *a, **k):
            self.timeout = _Sig()
        def setSingleShot(self, *a, **k):
            pass
        def setInterval(self, *a, **k):
            pass
        @staticmethod
        def singleShot(*a, **k):
            pass
    class QThread:
        def __init__(self, *a, **k): pass
        def start(self): pass
        def run(self): pass
    class QSignalBlocker:
        def __init__(self, *_args, **_kwargs): pass
    class Qt:
        AlignLeft = 0
        class SortOrder:
            AscendingOrder = 0
            DescendingOrder = 1
        class ContextMenuPolicy:
            CustomContextMenu = 0
        class MouseButton:
            RightButton = 2
        class ItemDataRole:
            UserRole = 32
        class WidgetAttribute:
            WA_DeleteOnClose = 0

    # Stub for FilterGUISSAMixin in headless mode
    class FilterGUISSAMixin:
        """Stub mixin for headless testing."""
        pass

    class TabContextGUISSAMixin:
        """Stub mixin for headless testing."""
        pass

    # Type-checking bridge: fallback stubs are runtime-safe but too strict for static unions.
    QWidget = cast(Any, QWidget)
    QApplication = cast(Any, QApplication)
    QMainWindow = cast(Any, QMainWindow)
    QVBoxLayout = cast(Any, QVBoxLayout)
    QHBoxLayout = cast(Any, QHBoxLayout)
    QGridLayout = cast(Any, QGridLayout)
    QLabel = cast(Any, QLabel)
    QPushButton = cast(Any, QPushButton)
    QLineEdit = cast(Any, QLineEdit)
    QTableWidget = cast(Any, QTableWidget)
    QProgressBar = cast(Any, QProgressBar)
    QTabWidget = cast(Any, QTabWidget)
    QMessageBox = cast(Any, QMessageBox)
    QFileDialog = cast(Any, QFileDialog)
    QMenu = cast(Any, QMenu)
    QAction = cast(Any, QAction)
    QTimer = cast(Any, QTimer)
    Qt = cast(Any, Qt)
    FilterGUISSAMixin = cast(Any, FilterGUISSAMixin)
    TabContextGUISSAMixin = cast(Any, TabContextGUISSAMixin)

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

# Prefer explicit monospace families across Windows/macOS/Linux to avoid Qt
# trying (and failing) to resolve a generic "Monospace" alias.
MONO_FONT_FAMILY = (
    # macOS first
    "Menlo, Monaco, 'Andale Mono', "
    # Windows 11 common monospace families
    "Consolas, 'Cascadia Mono', 'Cascadia Code', 'Segoe UI Mono', 'Lucida Console', "
    # Debian / Linux common monospace families
    "'DejaVu Sans Mono', 'Liberation Mono', 'Noto Sans Mono', 'Ubuntu Mono', "
    "'Droid Sans Mono', 'FreeMono', 'Nimbus Mono L', 'Courier 10 Pitch', "
    # Popular developer fonts (often installed)
    "'Fira Code', 'Fira Mono', 'JetBrains Mono', 'Roboto Mono', "
    "Inconsolata, Hack, 'Source Code Pro', "
    # Last-resort fallbacks
    "'Courier New', Courier"
)

DIVISAO_SETORES = {
    "SMME": ["MEL1", "MEL2", "MEL3", "MEL4"],
    "SMIN": ["IEE1", "IEE2", "IEE3", "IEE4"],
    "SMIL": ["ILA1", "ILA2", "ILA3", "ILA4"],
    "SMMG": ["MEG1", "MEG2", "MEG3", "MEG4"],
}
SECTOR_TO_DIV = {sec: div for div, secs in DIVISAO_SETORES.items() for sec in secs}
try:
    ssa_gui_filters.configure_adv_filters_constants(
        DIVISAO_SETORES,
        SECTOR_TO_DIV,
        MONO_FONT_FAMILY,
    )
except Exception as exc:
    logger.debug("Falha ao configurar constantes de filtros avancados: %s", exc)

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

try:
    ssa_gui_details.configure_details_constants(
        details_dialog_font_size=DETAILS_DIALOG_FONT_SIZE,
        details_dialog_table_padding=DETAILS_DIALOG_TABLE_PADDING,
        details_dialog_border_color=DETAILS_DIALOG_BORDER_COLOR,
        detail_field_priority=DETAIL_FIELD_PRIORITY,
        detail_display_overrides=DETAIL_DISPLAY_OVERRIDES,
        highlight_background_color=HIGHLIGHT_BACKGROUND_COLOR,
        highlight_font_weight=HIGHLIGHT_FONT_WEIGHT,
        mono_font_family=MONO_FONT_FAMILY,
    )
except Exception as exc:
    logger.debug("Falha ao configurar constantes de detalhes: %s", exc)

TABLE_NAME = CANONICAL_SSA_TABLE
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
class SSAMainWindow(QMainWindow, FilterGUISSAMixin, TabContextGUISSAMixin):
    """
    Janela principal da aplicação GUI.

    Inherits from FilterGUISSAMixin for filter-related methods.
    """
    def _get_theme_catalog(self):
        return ssa_gui_theme.get_theme_catalog()

    def _get_theme_keys(self):
        return ssa_gui_theme.get_theme_keys()

    def _persist_gui_preferences(self):
        try:
            atomic_write_json_file(
                os.path.join(project_root, "config", "gui_main_preferences.json"),
                GUI_MAIN_PREFERENCES,
                indent=2,
                ensure_ascii=False,
            )
            return True
        except Exception as exc:
            logger.warning("Falha ao persistir preferencias GUI: %s", exc)
            return False

    def _resolve_startup_theme(self):
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        return ssa_gui_theme.resolve_startup_theme(gui_settings)

    def __init__(self):
        super().__init__()
        try:
            # Evita acumulo de janelas/widgets fechados (impacta performance ao reaplicar tema global).
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        except Exception as exc:
            logger.debug("Failed to set WA_DeleteOnClose on main window: %s", exc)
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
        except Exception as exc:
            logger.debug("Failed to load window icon resources: %s", exc)

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

        # Carrega mapeamentos de exibicao com merge defensivo para evitar labels tecnicos.
        # Fonte canonica: defaults + column_display_names + display_mappings.
        self.display_map = load_display_mappings()
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
        self._persist_quick_filter_config = bool(
            gui_settings.get("persist_quick_filter_config", False)
        )
        self._quick_setor_executor_saved = str(
            gui_settings.get("quick_setor_executor", "") or ""
        ).strip()
        self._quick_setor_executor_syncing = False

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
        self._adv_cache_token = -1
        self._last_derivada_origem = None
        self._adv_sector_syncing = False
        self._adv_sector_handler_running = False
        self._responsavel_options_dirty = True
        self._responsavel_filters_materialized = False
        self._responsavel_all_prefixes = (
            "adv_responsavel_solicitante",
            "adv_responsavel_programacao",
            "adv_responsavel_execucao",
        )
        self._responsavel_materialized_prefixes = set()
        self._responsavel_dirty_prefixes = set(self._responsavel_all_prefixes)
        self._menu_pre_show_hooks = {}

        # Timer de debounce para otimização de filtros de setor (evita rebuilds excessivos)
        self._sector_debounce_delay = 300  # ms
        self._sector_debounce_timer = QTimer(self)
        self._sector_debounce_timer.setSingleShot(True)
        self._sector_debounce_timer.setInterval(self._sector_debounce_delay)
        self._sector_debounce_timer.timeout.connect(self._on_sector_debounce_timeout)

        self._initialize_profile_filter_placeholders()

        # Larguras salvas por coluna (das configurações JSON) - mantido para compatibilidade
        self._saved_gui_column_widths = GUI_MAIN_PREFERENCES.get("column_widths", {}).copy()

        # Debounce de filtro (da configuracao JSON).
        # Mantemos um piso para incentivar uso do botao "Aplicar" sem remover debounce.
        debounce_delay = gui_settings.get("debounce_delay", 250)
        try:
            debounce_delay = int(debounce_delay)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Valor invalido para debounce_delay nas preferencias (%s); usando fallback 250 ms.",
                exc,
            )
            debounce_delay = 250
        minimum_search_debounce_ms = 1400  # ms
        if debounce_delay < minimum_search_debounce_ms:
            debounce_delay = minimum_search_debounce_ms
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
        except Exception as exc:
            logger.debug("Failed to persist preferred startup theme: %s", exc)
        # Aplica perfil inicial de filtros por setor
        self._apply_initial_filter_profile()
        self._apply_initial_quick_setor_executor_filter()

        # Auto-carregar dados na abertura (assáncrono, mantêm a janela responsiva)
        QTimer.singleShot(150, self.load_data)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(cast(Any, central_widget))
        self._setup_app_menus()


        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()

        # Botões principais de dados
        self.load_button = QPushButton("Carregar Dados")
        self.load_button.setToolTip("Carregar dados do banco de dados existente")
        self.load_button.clicked.connect(self.load_data)
        toolbar_layout.addWidget(cast(Any, self.load_button))

        # Botões de ações
        self.rescan_button = QPushButton("Reescanear")
        self.rescan_button.setToolTip("Reprocessar arquivos Excel da pasta docs_entrada")
        self.rescan_button.clicked.connect(self.rescan_data)
        toolbar_layout.addWidget(cast(Any, self.rescan_button))

        self.update_derivadas_button = QPushButton("Atualizar Derivadas")
        self.update_derivadas_button.setToolTip(
            "Atualizar tabelas de derivadas (fase DB e fase planilhas especiais)"
        )
        self.update_derivadas_button.clicked.connect(self.update_derivadas_from_sources)
        toolbar_layout.addWidget(cast(Any, self.update_derivadas_button))
        # Semana Atual (YYYYWW) como indicador informativo na barra superior
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
        self.week_label.setToolTip("Semana ISO atual")
        toolbar_layout.addSpacing(6)
        toolbar_layout.addWidget(cast(Any, self.week_label))

        # Espaçamento antes do status
        toolbar_layout.addStretch()

        # Status em caixa e progresso
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")
        self.status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        # Keep toolbar geometry stable even when status text gets longer.
        self.status_label.setMinimumWidth(520)
        self.status_label.setMaximumWidth(520)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        toolbar_layout.addWidget(cast(Any, self.status_label))
        toolbar_layout.addWidget(cast(Any, self.progress_bar))

        # Botao de Tema no lado direito
        theme_button = QPushButton("Tema")
        theme_button.setToolTip("Selecionar tema em caixa de dialogo")
        theme_button.clicked.connect(self.toggle_theme_menu)
        toolbar_layout.addWidget(cast(Any, theme_button))

        main_layout.addLayout(cast(Any, toolbar_layout))
        self.main_tabs = QTabWidget()
        tab_main = QWidget()
        ctx_main = self._build_tab_content(tab_main, "main")
        self.main_tabs.addTab(cast(Any, tab_main), "SSAs")
        tab_filters = QWidget()
        ctx_filters = self._build_tab_content(tab_filters, "filters")
        self.main_tabs.addTab(cast(Any, tab_filters), "Filtros")
        self._tab_contexts = [ctx_main, ctx_filters]
        main_layout.addWidget(cast(Any, self.main_tabs))
        self.main_tabs.currentChanged.connect(self._on_tab_changed)
        self._bind_tab_context(ctx_main)
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug("Falha ao agendar sincronizacao inicial de altura dos paineis inferiores: %s", exc)

        # --- Conecta Workers / Flags ---
        # Threads iniciadas sob demanda
        self.data_loader_thread = None
        self._retired_data_loader_workers = []
        self.filter_thread = None
        self._retired_filter_workers = []
        self._data_load_request_seq = 0
        self._active_data_load_request_id = 0
        self._data_revision = 0
        self._data_revision_request_id = None
        self._data_uuid = None
        self._num_reprog_sort_cache = {"source_id": None, "source_len": 0, "keys_df": None}
        self._pending_resize_recompute_revision = None
        self._resize_recompute_timer = QTimer(self)
        self._resize_recompute_timer.setSingleShot(True)
        self._resize_recompute_timer.timeout.connect(self._on_resize_recompute_timeout)
        self._filter_request_seq = 0
        self._active_filter_request_id = 0
        self._active_filter_search_request_id = None
        self._active_filter_search_display = ""
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in ("1", "true", "yes", "on")
        # Em ambiente de testes (pytest), force modo síncrono para previsibilidade
        if not self._sync_filtering and os.environ.get("PYTEST_CURRENT_TEST"):
            self._sync_filtering = True

        # Configura cache size da configuração
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        cache_size = gui_settings.get("filter_cache_size", 50)
        if FilterWorker is not None and FilterCache is not None:
            FilterWorker._cache = FilterCache(max_size=cache_size)
        else:
            logger.warning("FilterWorker/FilterCache indisponivel; cache de filtro nao inicializado")

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
        except Exception as exc:
            logger.debug("Falha ao aplicar altura minima no campo de pesquisa: %s", exc)
        search_input.returnPressed.connect(
            lambda tab=tab_kind: self._on_general_search_apply_clicked(tab)
        )
        search_input.textChanged.connect(self._on_search_text_changed)
        search_button = QPushButton("Aplicar")
        search_button.clicked.connect(
            lambda _checked=False, tab=tab_kind: self._on_general_search_apply_clicked(tab)
        )
        clear_filter_button = QPushButton("Limpar Busca")
        clear_filter_button.clicked.connect(
            lambda _checked=False, tab=tab_kind: self._on_general_search_clear_clicked(tab)
        )
        clear_filter_button.setToolTip(
            "Limpa apenas a busca geral. Filtros de coluna e avancados continuam ativos."
        )
        clear_filter_button.setEnabled(False)
        left.addWidget(cast(Any, search_label))
        left.addWidget(cast(Any, search_input))
        left.addWidget(cast(Any, search_button))
        left.addWidget(cast(Any, clear_filter_button))

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        column_selector = ColumnSelector(
            self.display_map,
            self.visible_columns,
            default_columns=self.default_columns,
            available_columns=self._get_canonical_available_columns(),
            info_font=self._info_font,
        )
        column_selector.columns_changed.connect(self.on_columns_changed)
        right.addWidget(cast(Any, column_selector))
        right.addSpacing(8)

        quick_setor_executor_combo = QComboBox()
        quick_setor_executor_combo.setToolTip(
            "Filtro rapido de Setor Executor (aplica junto com os demais filtros)."
        )
        try:
            quick_setor_executor_combo.setMinimumWidth(210)
            quick_setor_executor_combo.setSizeAdjustPolicy(
                cast(Any, QComboBox.SizeAdjustPolicy.AdjustToContents)
            )
        except Exception as exc:
            logger.debug("Falha ao configurar combo rapido de setor executor: %s", exc)
        self._populate_quick_setor_executor_combo(
            quick_setor_executor_combo,
            selected_value=str(
                OrderedDict(self._active_column_filters or {}).get(
                    "setor_executor", ""
                )
                or self._quick_setor_executor_saved
            ).strip(),
        )
        quick_setor_executor_combo.currentIndexChanged.connect(
            lambda _idx, combo=quick_setor_executor_combo: self._on_quick_setor_executor_changed(combo)
        )
        right.addWidget(cast(Any, quick_setor_executor_combo))

        search_row.addLayout(cast(Any, left))
        search_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        search_row.addLayout(cast(Any, right))
        tab_layout.addLayout(cast(Any, search_row))

        search_help = QLabel(
            "Separe por virgulas (logica E: todos os termos obrigatorios). Use ! para excluir. A busca vale para qualquer coluna."
        )
        search_help.setWordWrap(False)
        try:
            search_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception as exc:
            logger.debug("Falha ao aplicar size policy na ajuda de pesquisa: %s", exc)
        search_help.setStyleSheet("color: palette(mid); margin:0; padding:0;")
        try:
            search_help.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar texto de ajuda da pesquisa: %s", exc)
        tab_layout.addSpacing(4)

        # Pagination and persistent filters
        pagination_filters_layout = QHBoxLayout()
        pagination_filters_layout.setContentsMargins(0, 0, 0, 0)

        paginator = DataPaginator(self.df_para_tabela)
        paginator.page_changed.connect(self.display_current_page)
        pagination_filters_layout.addWidget(paginator)

        profile_selector = None
        pagination_filters_layout.addSpacing(12)

        persistent_filters_layout = QHBoxLayout()
        persistent_filters_layout.setContentsMargins(0, 0, 0, 0)

        persist_filter_config_checkbox = QCheckBox("Configuracao persistente")
        persist_filter_config_checkbox.setToolTip(
            "Quando ativo, salva automaticamente o filtro rapido de setor e colunas visiveis."
        )
        try:
            persist_filter_config_checkbox.setChecked(bool(self._persist_quick_filter_config))
        except Exception as exc:
            logger.debug("Falha ao restaurar estado do checkbox de persistencia: %s", exc)
        persist_filter_config_checkbox.toggled.connect(self._on_persist_quick_filter_config_toggled)
        persistent_filters_layout.addWidget(cast(Any, persist_filter_config_checkbox))
        persistent_filters_layout.addSpacing(8)

        save_filter_button = QPushButton("Salvar Filtro")
        save_filter_button.setMaximumWidth(100)
        save_filter_button.setToolTip("Salvar filtro atual como persistente")
        save_filter_button.clicked.connect(self.save_current_filter)
        persistent_filters_layout.addWidget(cast(Any, save_filter_button))

        exclude_ste_checkbox = QCheckBox("Nao esta em STE/SCA")
        exclude_ste_checkbox.setToolTip("Oculta SSAs com situacao STE ou SCA")
        try:
            exclude_ste_checkbox.setChecked(False)
        except Exception as exc:
            logger.debug("Falha ao inicializar estado do checkbox excluir STE/SCA: %s", exc)
        try:
            exclude_ste_checkbox.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar checkbox excluir STE/SCA na aba: %s", exc)
        try:
            exclude_ste_checkbox.toggled.connect(self._on_exclude_ste_sca_toggled)
        except Exception as exc:
            logger.warning("Falha ao conectar toggle do checkbox excluir STE/SCA: %s", exc)
        persistent_filters_layout.addWidget(cast(Any, exclude_ste_checkbox))

        filter_tags_widget = QWidget()
        filter_tags_layout = QHBoxLayout(cast(Any, filter_tags_widget))
        filter_tags_layout.setContentsMargins(0, 0, 0, 0)
        filter_tags_layout.setSpacing(5)
        persistent_filters_layout.addWidget(cast(Any, filter_tags_widget))

        pagination_filters_layout.addLayout(cast(Any, persistent_filters_layout))
        pagination_filters_layout.addStretch()

        col_filter_indicator = QLabel("")
        try:
            if self._info_font is not None:
                col_filter_indicator.setFont(cast(Any, QFont(self._info_font)))
        except Exception as exc:
            logger.debug("Falha ao aplicar fonte no indicador de filtro por coluna: %s", exc)
        col_filter_indicator.setToolTip(
            "Filtros por coluna acumulam com a Pesquisa Geral (logica E entre filtros). "
            "Dentro de cada filtro, use virgulas para alternativas (logica OU). Consulte a ajuda para outros atalhos."
        )
        try:
            col_filter_indicator.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar indicador de filtro por coluna: %s", exc)

        tab_layout.addLayout(cast(Any, pagination_filters_layout))

        filters_summary_frame = None
        filters_summary_label = None
        clear_all_filters_btn = None
        export_list_btn = None
        undo_filter_btn = None
        try:
            filters_summary_frame = QFrame()
            filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
            summary_layout = QHBoxLayout(cast(Any, filters_summary_frame))
            summary_layout.setContentsMargins(6, 4, 6, 4)
            summary_layout.setSpacing(8)
            filters_summary_label = QLabel("Nenhum filtro ativo")
            if self._info_font is not None:
                try:
                    filters_summary_label.setFont(cast(Any, QFont(self._info_font)))
                except Exception as exc:
                    logger.debug("Falha ao aplicar fonte no resumo de filtros: %s", exc)
            clear_all_filters_btn = QPushButton("Limpar todos os filtros")
            clear_all_filters_btn.setMaximumWidth(200)
            clear_all_filters_btn.clicked.connect(self._clear_all_filters_global)
            try:
                clear_all_filters_btn.setStyleSheet(self._week_label_style)
            except Exception as exc:
                logger.debug("Falha ao aplicar estilo no botao limpar todos os filtros: %s", exc)
            export_list_btn = QPushButton("Exportar lista")
            export_list_btn.setMaximumWidth(160)
            export_list_btn.setToolTip("Exportar lista atual para arquivo txt")
            export_list_btn.clicked.connect(self._export_current_list_txt)
            try:
                export_list_btn.setStyleSheet(self._week_label_style)
            except Exception as exc:
                logger.debug("Falha ao aplicar estilo no botao exportar lista: %s", exc)
            undo_filter_btn = QPushButton("Undo")
            undo_filter_btn.setMaximumWidth(160)
            undo_filter_btn.setToolTip("Desfaz o ultimo filtro aplicado")
            undo_filter_btn.clicked.connect(self._restore_last_filter_state)
            try:
                undo_filter_btn.setStyleSheet(self._week_label_style)
            except Exception as exc:
                logger.debug("Falha ao aplicar estilo no botao undo de filtros: %s", exc)
            summary_layout.addWidget(cast(Any, clear_all_filters_btn), 0)
            summary_layout.addWidget(cast(Any, export_list_btn), 0)
            summary_layout.addWidget(cast(Any, undo_filter_btn), 0)
            summary_layout.addWidget(cast(Any, filters_summary_label), 1)
            tab_layout.addWidget(cast(Any, filters_summary_frame))
            filters_summary_frame.setVisible(True)
            try:
                self._update_undo_button_state()
            except Exception as exc:
                logger.debug("Falha ao atualizar estado inicial do botao undo: %s", exc)
        except Exception as exc:
            logger.warning("Falha ao construir painel de resumo de filtros da aba: %s", exc)

        if isinstance(self._restored_page_size, int) and 10 <= self._restored_page_size <= 500:
            try:
                paginator.page_size_spinbox.setValue(self._restored_page_size)
            except Exception as exc:
                logger.debug("Falha ao restaurar page size na paginacao: %s", exc)
        try:
            paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)
        except Exception as exc:
            logger.warning("Falha ao conectar persistencia de page size na paginacao: %s", exc)

        # Table
        table_widget = QTableWidget()
        table_widget.setEditTriggers(cast(Any, QTableWidget.EditTrigger.NoEditTriggers))
        table_widget.setSelectionBehavior(cast(Any, QAbstractItemView.SelectionBehavior.SelectRows))
        try:
            table_widget.setMinimumHeight(220)
        except Exception as exc:
            logger.debug("Falha ao aplicar altura minima na tabela principal: %s", exc)
        header = table_widget.horizontalHeader()
        vertical_header = table_widget.verticalHeader()
        if header is not None and vertical_header is not None:
            header.setSectionResizeMode(cast(Any, QHeaderView.ResizeMode.Interactive))
            vertical_header.setVisible(False)
            vertical_header.setSectionResizeMode(cast(Any, QHeaderView.ResizeMode.Fixed))
            vertical_header.setDefaultSectionSize(24)
            header.sectionResized.connect(self._on_header_section_resized)
        else:
            logger.warning("Header da tabela indisponivel; configuracao avancada de colunas ignorada.")

        table_widget.doubleClicked.connect(self.on_table_double_click)
        table_widget.itemSelectionChanged.connect(self.update_details_from_selection)

        try:
            if header is not None:
                header.setSectionsClickable(True)
                header.setSortIndicatorShown(True)
                try:
                    header.setMinimumSectionSize(26)
                    header.setDefaultSectionSize(92)
                except Exception as exc:
                    logger.debug("Falha ao configurar tamanho minimo/default do header da tabela: %s", exc)
                try:
                    f = header.font()
                    f.setBold(False)
                    header.setFont(f)
                    header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
                except Exception as exc:
                    logger.debug("Falha ao aplicar estilo/fonte no header da tabela: %s", exc)
                header.sectionClicked.connect(self.on_header_clicked)
                header.setContextMenuPolicy(cast(Any, Qt.ContextMenuPolicy.CustomContextMenu))
                header.customContextMenuRequested.connect(self.show_header_context_menu)
                header.installEventFilter(self)
        except Exception as exc:
            logger.warning("Falha ao configurar comportamento do header da tabela: %s", exc)

        table_widget.setContextMenuPolicy(cast(Any, Qt.ContextMenuPolicy.CustomContextMenu))
        table_widget.customContextMenuRequested.connect(self.show_context_menu)

        tab_layout.addWidget(cast(Any, table_widget), 6)

        # Details + column filters
        bottom_layout = QHBoxLayout()
        details_group = QGroupBox("Detalhes da SSA Selecionada")
        details_layout = QVBoxLayout(cast(Any, details_group))
        details_layout.setContentsMargins(2, 2, 2, 2)
        details_layout.setSpacing(2)
        details_text = QTextBrowser()
        try:
            details_text.setFrameShape(QFrame.Shape.NoFrame)
        except Exception as exc:
            logger.debug("Falha ao remover frame do painel de detalhes: %s", exc)
        try:
            details_viewport = details_text.viewport()
            if details_viewport is not None:
                details_viewport.setAutoFillBackground(False)
        except Exception as exc:
            logger.debug("Falha ao configurar preenchimento do viewport de detalhes: %s", exc)
        details_text.setReadOnly(True)
        try:
            details_text.setOpenLinks(False)
            details_text.setOpenExternalLinks(False)
            details_text.anchorClicked.connect(self._on_details_anchor_clicked)
        except Exception as exc:
            logger.debug("Falha ao configurar links no painel de detalhes: %s", exc)
        details_layout.addWidget(cast(Any, details_text))
        bottom_layout.addWidget(cast(Any, details_group), 2)

        col_filters_group = QGroupBox("Filtros por Coluna")
        col_filters_outer = QVBoxLayout(cast(Any, col_filters_group))
        col_filters_hint = QLabel("Use virgulas para alternativas (logica OU dentro da coluna). Entre colunas mantemos logica E.")
        try:
            col_filters_hint.setStyleSheet("color: palette(windowText); font-size: 11px;")
        except Exception as exc:
            logger.debug("Falha ao aplicar estilo da dica de filtros por coluna: %s", exc)
        col_filters_outer.addWidget(cast(Any, col_filters_hint))
        col_filters_scroll = QScrollArea()
        col_filters_scroll.setWidgetResizable(True)
        col_filters_container = QWidget()
        col_filters_list_layout = QVBoxLayout(cast(Any, col_filters_container))
        col_filters_scroll.setWidget(cast(Any, col_filters_container))
        col_filters_outer.addWidget(cast(Any, col_filters_scroll), 1)
        footer = QHBoxLayout()
        footer.addStretch()
        add_column_filter_btn = QPushButton("Adicionar filtro de coluna")
        add_column_filter_btn.setMaximumWidth(260)
        add_column_filter_btn.setToolTip("Selecionar qualquer coluna para ativar filtro dedicado")
        add_column_filter_btn.clicked.connect(self._open_add_column_filter_menu)
        footer.addWidget(cast(Any, add_column_filter_btn))
        footer.addSpacing(8)
        clear_all_btn = QPushButton("Limpar todos filtros de colunas")
        clear_all_btn.setMaximumWidth(260)
        clear_all_btn.clicked.connect(self._clear_all_column_filters)
        footer.addWidget(cast(Any, clear_all_btn))
        footer.addStretch()
        col_filters_outer.addLayout(cast(Any, footer))

        right_col_widget = QWidget()
        right_col = QVBoxLayout(cast(Any, right_col_widget))
        right_col.setContentsMargins(0, 0, 0, 0)
        if tab_kind == "filters":
            adv_group, adv_ctx = self._build_advanced_filters_panel()
            right_col.addWidget(cast(Any, adv_group), 1)
            col_filters_group.setVisible(False)
            right_col.addWidget(cast(Any, col_filters_group))
            # APENAS na aba Filtros: Detalhes max 40% (2) vs Filtros 60% (3)
            bottom_layout.addWidget(cast(Any, right_col_widget), 3)
        else:
            right_col.addWidget(cast(Any, col_filters_group))
            # Aba SSAs: manter Detalhes em 40% (2) e painel da direita em 60% (3).
            bottom_layout.addWidget(cast(Any, right_col_widget), 3)

        tab_layout.addSpacing(12)
        tab_layout.addLayout(cast(Any, bottom_layout), 4)

        ctx.update(
            {
                "search_label": search_label,
                "search_input": search_input,
                "search_button": search_button,
                "clear_filter_button": clear_filter_button,
                "column_selector": column_selector,
                "quick_setor_executor_combo": quick_setor_executor_combo,
                "search_help": search_help,
                "paginator": paginator,
                "profile_selector": profile_selector,
                "persistent_filters_layout": persistent_filters_layout,
                "persist_filter_config_checkbox": persist_filter_config_checkbox,
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

    def _get_canonical_available_columns(self) -> list[str]:
        """Retorna colunas elegiveis para seletores de UI (sem legados invalidos)."""
        legacy_invalid_columns = {"Numero da SSA", "Número da SSA", "No SSA", "Data Cadastro"}
        candidates = []
        seen_candidates = set()
        always_allow = set()
        mapped_columns = set()

        def _append_candidate(value, *, allow: bool = False):
            if not isinstance(value, str):
                return
            col_name = value.strip()
            if not col_name or col_name == "#":
                return
            if col_name in seen_candidates:
                if allow:
                    always_allow.add(col_name)
                return
            seen_candidates.add(col_name)
            candidates.append(col_name)
            if allow:
                always_allow.add(col_name)

        def _collect_mapped_keys(mapping_obj):
            if not isinstance(mapping_obj, dict):
                return
            for key in mapping_obj.keys():
                if not isinstance(key, str):
                    continue
                key_name = key.strip()
                if key_name:
                    mapped_columns.add(key_name)

        for attr_name in (
            "visible_columns",
            "default_columns",
            "_profile_columns",
            "_current_display_columns",
        ):
            values = getattr(self, attr_name, None)
            if isinstance(values, (list, tuple)):
                for value in values:
                    _append_candidate(value, allow=True)

        active_filters = getattr(self, "_active_column_filters", None)
        if isinstance(active_filters, dict):
            for key in active_filters.keys():
                _append_candidate(key, allow=True)
        active_widgets = getattr(self, "_column_filter_widgets", None)
        if isinstance(active_widgets, dict):
            for key in active_widgets.keys():
                _append_candidate(key, allow=True)

        _collect_mapped_keys(DEFAULT_DISPLAY_MAPPINGS)
        _collect_mapped_keys(getattr(self, "internal_to_display", None))
        _collect_mapped_keys(getattr(self, "display_map", None))

        allowed_columns = None
        try:
            allowed_raw = str(os.environ.get("SSA_ALLOWED_COLUMNS", "") or "").strip()
            if allowed_raw:
                allowed_columns = {token.strip() for token in allowed_raw.split(",") if token.strip()}
        except Exception as exc:
            logger.debug("Falha ao ler whitelist de colunas via SSA_ALLOWED_COLUMNS: %s", exc)
            allowed_columns = None

        non_null_cols = None
        try:
            cached_cols = getattr(self, "_non_null_cols_cache", None)
            if isinstance(cached_cols, set) and cached_cols:
                non_null_cols = set(cached_cols)
        except Exception as exc:
            logger.debug("Falha ao ler cache de colunas nao nulas para menu canonico: %s", exc)
            non_null_cols = None

        # Evita scan direto em DataFrame aqui para nao disputar estado com workers.
        # A fonte oficial para "nao nulas" neste ponto e o cache ja calculado no fluxo de carga.

        for col_name in mapped_columns:
            _append_candidate(col_name, allow=(col_name in always_allow))
        if isinstance(non_null_cols, set) and non_null_cols:
            for col_name in non_null_cols:
                _append_candidate(col_name, allow=(col_name in always_allow))
        for col_name in always_allow:
            _append_candidate(col_name, allow=True)

        result = []
        seen = set()

        def _is_canonical_column(col_name: str) -> bool:
            if not col_name or col_name == "#":
                return False
            if col_name in COMPATIBILITY_NULL_UI_COLUMNS:
                return False
            if col_name in legacy_invalid_columns:
                return False
            if col_name in EXCLUDED_CANONICAL_UI_COLUMNS:
                return False
            if "_relacionada_" in col_name or "_relacionado_" in col_name:
                return False
            if not re.fullmatch(r"[a-z][a-z0-9_]*", col_name):
                return False
            if isinstance(allowed_columns, set) and col_name not in allowed_columns:
                return False
            return True

        for col in candidates:
            if not isinstance(col, str):
                continue
            col_name = col.strip()
            if col_name in seen:
                continue
            if not _is_canonical_column(col_name):
                continue
            seen.add(col_name)
            result.append(col_name)
        return result

    def _schedule_adv_options_refresh(self):
        if getattr(self, "_adv_options_scheduled", False):
            return
        self._adv_options_scheduled = True
        try:
            QTimer.singleShot(0, self._run_adv_options_refresh)
        except Exception as exc:
            logger.warning("Falha ao agendar refresh de filtros avancados: %s", exc)
            self._adv_options_scheduled = False
            try:
                self._run_adv_options_refresh()
            except Exception as fallback_exc:
                logger.warning("Falha no fallback de refresh de filtros avancados: %s", fallback_exc)

    def _run_adv_options_refresh(self):
        self._adv_options_scheduled = False
        if getattr(self, "_current_tab_kind", None) != "filters":
            return
        if not getattr(self, "_adv_options_dirty", False):
            return
        try:
            self._refresh_advanced_filter_options()
            self._adv_options_dirty = False
        except Exception as exc:
            logger.warning("Falha ao executar refresh de filtros avancados: %s", exc)

    def _on_tab_changed(self, index: int) -> None:
        if not hasattr(self, "_tab_contexts"):
            return
        if index < 0 or index >= len(self._tab_contexts):
            return
        ctx = self._tab_contexts[index]
        self._bind_tab_context(ctx)
        try:
            self._refresh_quick_setor_executor_options()
            self._sync_quick_setor_executor_combo_from_filters()
        except Exception as exc:
            logger.debug("Falha ao sincronizar combo rapido de setor executor na troca de aba: %s", exc)
        if ctx.get("tab_kind") == "filters":
            try:
                ssa_gui_theme.reapply_current_theme_widget_styles(
                    self,
                    highlight_defaults=(HIGHLIGHT_BACKGROUND_COLOR, HIGHLIGHT_FONT_WEIGHT),
                )
            except Exception as exc:
                logger.debug("Falha ao reaplicar estilos do tema na aba de filtros: %s", exc)
            pending_theme = getattr(self, "_pending_theme_refresh_column_filters", None)
            if pending_theme:
                try:
                    if hasattr(self, "_refresh_advanced_filter_options"):
                        self._refresh_advanced_filter_options()
                except Exception as exc:
                    logger.debug("Falha ao atualizar filtros avancados pendentes na troca de aba: %s", exc)
                finally:
                    self._pending_theme_refresh_column_filters = None
            try:
                self._reorganize_advanced_filters_grid(getattr(self, "adv_filters_group").width())
            except Exception as exc:
                logger.debug("Falha ao reorganizar filtros avancados apos troca de aba: %s", exc)
            try:
                QTimer.singleShot(
                    0,
                    lambda: self._reorganize_advanced_filters_grid(getattr(self, "adv_filters_group").width()),
                )
            except Exception as exc:
                logger.debug("Falha ao agendar reorganizacao deferida apos troca de aba: %s", exc)
        try:
            self._queue_bottom_panel_height_sync()
        except Exception as exc:
            logger.debug("Falha ao enfileirar sincronizacao de altura apos troca de aba: %s", exc)

    def _compute_bottom_panel_target_height(self) -> int:
        try:
            window_height = int(self.height())
        except Exception:
            window_height = 900
        if window_height <= 0:
            window_height = 900
        try:
            base_font_pt = int(self.font().pointSize())
        except Exception:
            base_font_pt = 10
        if base_font_pt <= 0:
            base_font_pt = 10
        base_height = int(window_height * 0.28)
        font_adjust = max(0, base_font_pt - 10) * 8
        target = base_height + font_adjust
        return max(180, min(360, target))

    def _queue_bottom_panel_height_sync(self) -> None:
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug("Falha ao enfileirar sincronizacao de altura dos paineis inferiores: %s", exc)
            self._sync_bottom_panel_heights()

    def _sync_bottom_panel_heights(self) -> None:
        if not hasattr(self, "_tab_contexts"):
            return
        target = self._compute_bottom_panel_target_height()
        seen = set()
        groups = []
        for ctx in self._tab_contexts:
            if not isinstance(ctx, dict):
                continue
            for key in ("details_group", "col_filters_group", "adv_filters_group"):
                widget = ctx.get(key)
                if widget is None:
                    continue
                wid = id(widget)
                if wid in seen:
                    continue
                seen.add(wid)
                groups.append(widget)
        for widget in groups:
            try:
                widget.setMinimumHeight(target)
                widget.setMaximumHeight(target)
            except Exception as exc:
                logger.debug("Falha ao sincronizar altura do painel inferior %s: %s", widget, exc)
        try:
            current_kind = getattr(self, "_current_tab_kind", None)
            if current_kind == "filters" and hasattr(self, "adv_filters_group") and self.adv_filters_group is not None:
                self._reorganize_advanced_filters_grid(self.adv_filters_group.width())
        except Exception as exc:
            logger.debug("Falha ao reorganizar painel avancado apos sync de altura: %s", exc)

    def _make_multiselect_box(
        self,
        title: str,
        placeholder: str = "Selecionar",
        with_exclude: bool = True,
        layout_baseline=None,
    ):
        return ssa_gui_filters._make_multiselect_box(
            self,
            title,
            placeholder,
            with_exclude,
            layout_baseline=layout_baseline,
        )

    def _set_menu_pre_show_hook(self, button, callback):
        return ssa_gui_filters._set_menu_pre_show_hook(self, button, callback)

    def _run_menu_pre_show_hook(self, button):
        return ssa_gui_filters._run_menu_pre_show_hook(self, button)

    def _set_checkbox_checked_quietly(self, checkbox, checked: bool):
        return ssa_gui_filters._set_checkbox_checked_quietly(self, checkbox, checked)

    def _sync_responsavel_flags(self):
        return ssa_gui_filters._sync_responsavel_flags(self)

    def _mark_responsavel_dirty(self, prefixes=None):
        return ssa_gui_filters._mark_responsavel_dirty(self, prefixes)

    def _on_sector_debounce_timeout(self):
        return ssa_gui_filters._on_sector_debounce_timeout(self)

    def _ensure_responsavel_options_materialized(self, target_prefix: str | None = None, force: bool = False):
        return ssa_gui_filters._ensure_responsavel_options_materialized(self, target_prefix, force)

    def _sync_responsavel_button_summaries(self, only_prefixes=None):
        return ssa_gui_filters._sync_responsavel_button_summaries(self, only_prefixes)

    def _attach_multiselect_menu(self, button, menu):
        return ssa_gui_filters._attach_multiselect_menu(self, button, menu)

    def _update_multiselect_button(self, button, checks, placeholder: str = "Selecionar", exclude_checks=None):
        return ssa_gui_filters._update_multiselect_button(self, button, checks, placeholder, exclude_checks)

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
        return ssa_gui_filters._rebuild_multiselect_menu(
            self,
            button,
            menu,
            values,
            selected_set,
            on_toggle,
            on_apply,
            exclude_selected_set,
            on_exclude_toggle,
        )

    def _checkbox_value(self, checkbox):
        return ssa_gui_filters._checkbox_value(self, checkbox)

    def _sync_multiselect_checks(self, button, checks, selected, exclude_checks=None, exclude_selected=None):
        return ssa_gui_filters._sync_multiselect_checks(self, button, checks, selected, exclude_checks, exclude_selected)

    def _build_advanced_filters_panel(self):
        return ssa_gui_filters._build_advanced_filters_panel(self)

    def _on_derivada_has_toggled(self, checked: bool):
        return ssa_gui_filters._on_derivada_has_toggled(self, checked)

    def _on_derivada_all_ste_toggled(self, checked: bool):
        _ = checked
        return None

    def _show_derivadas_popup(self):
        return ssa_gui_filters._show_derivadas_popup(self)

    def _build_derivadas_tree(self, df: pd.DataFrame, numero_col: str, derivada_col: str):
        cache_token = ssa_gui_filters._cache_token(
            getattr(self, "_data_load_request_seq", None),
            getattr(self, "_active_data_load_request_id", None),
            (id(df), df.shape, getattr(self, "_data_uuid", None)),
        )
        return ssa_gui_filters._build_derivadas_tree(
            self,
            df,
            numero_col,
            derivada_col,
            cache_token=cache_token,
            normalize_ssa_series=self._normalize_ssa_series,
        )

    def _update_derivadas_button_state(self):
        return ssa_gui_filters._update_derivadas_button_state(self)

    def _save_advanced_filters_default(self):
        return ssa_gui_filters._save_advanced_filters_default(self)

    def _on_macro_filter_changed(self):
        return ssa_gui_filters._on_macro_filter_changed(self)

    def _reorganize_advanced_filters_grid(self, width: int):
        return ssa_gui_filters._reorganize_advanced_filters_grid(self, width)

    def _on_adv_sector_selection_changed(self, *_):
        return ssa_gui_filters._on_adv_sector_selection_changed(self, *_)

    def _on_adv_sector_exclude_changed(self, *_):
        return ssa_gui_filters._on_adv_sector_exclude_changed(self, *_)

    def _schedule_sector_options_refresh(self):
        return ssa_gui_filters._schedule_sector_options_refresh(self)

    def _collect_divisao_setores(self, divisao_values):
        return ssa_gui_filters._collect_divisao_setores(self, divisao_values)

    def _sector_sort_key(self, sector: str):
        return ssa_gui_filters._sector_sort_key(self, sector)

    def _sort_sectors(self, values):
        return ssa_gui_filters._sort_sectors(self, values)

    def _sort_responsavel_values(self, df_subset, values, resp_col: str):
        return ssa_gui_filters._sort_responsavel_values(self, df_subset, values, resp_col)

    def _apply_divisao_to_setor_checks(self):
        return ssa_gui_filters._apply_divisao_to_setor_checks(self)

    def _refresh_responsavel_options(self, target_prefixes=None):
        return ssa_gui_filters._refresh_responsavel_options(self, target_prefixes)

    def _clear_advanced_filters(self):
        return ssa_gui_filters._clear_advanced_filters(self)

    def _has_active_advanced_filters(self, data: dict):
        handler = getattr(ssa_gui_filters, "_has_active_advanced_filters", None)
        if callable(handler):
            return handler(self, data)
        from gui.ssa import gui_filters_advanced_ui as ssa_gui_filters_ui  # local fallback during split

        fallback_handler = getattr(ssa_gui_filters_ui, "_has_active_advanced_filters", None)
        if callable(fallback_handler):
            return fallback_handler(self, data)
        logger.warning("Advanced filters activity handler is unavailable; assuming inactive filters.")
        return False

    def _apply_advanced_filters_from_ui(self, store_only: bool = False):
        return ssa_gui_filters._apply_advanced_filters_from_ui(self, store_only)

    def _parse_week(self, raw: str):
        return ssa_gui_filters._parse_week(self, raw)

    def _get_checked_values(self, source):
        return ssa_gui_filters._get_checked_values(self, source)

    def _sync_advanced_filter_ui(self):
        return ssa_gui_filters._sync_advanced_filter_ui(self)

    def _refresh_sector_menus(self, exec_vals, emis_vals, status_vals, filters, apply_cb):
        return ssa_gui_filters._refresh_sector_menus(
            self, exec_vals, emis_vals, status_vals, filters, apply_cb
        )

    def _refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb):
        return ssa_gui_filters._refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb)

    def _refresh_priority_menus(self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb):
        return ssa_gui_filters._refresh_priority_menus(
            self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
        )

    def _refresh_reprogramacoes_menu(self, reprog_vals, filters, apply_cb):
        return ssa_gui_filters._refresh_reprogramacoes_menu(self, reprog_vals, filters, apply_cb)

    def _refresh_advanced_filter_options(self):
        return ssa_gui_filters._refresh_advanced_filter_options(self)

    def _apply_advanced_filters(self, df: pd.DataFrame):
        cache_token = ssa_gui_filters._cache_token(
            getattr(self, "_data_load_request_seq", None),
            getattr(self, "_active_data_load_request_id", None),
            (id(df), df.shape, getattr(self, "_data_uuid", None)),
        )
        notice_callback = getattr(self, "_adv_notice_callback", None)
        return ssa_gui_filters._apply_advanced_filters(
            self,
            df,
            cache_token=cache_token,
            normalize_ssa_series=self._normalize_ssa_series,
            notice_callback=notice_callback,
        )

    def _retain_data_loader_worker_until_finished(self, worker) -> None:
        ssa_gui_workers.retain_data_loader_worker_until_finished(
            self,
            worker,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def _is_data_loader_worker_alive(self, worker) -> bool:
        return ssa_gui_workers.is_data_loader_worker_alive(worker, sip_module=sip)

    def _is_data_loader_worker_running(self, worker) -> bool:
        return ssa_gui_workers.is_data_loader_worker_running(worker, sip_module=sip)

    def _prune_retired_data_loader_workers(self) -> None:
        ssa_gui_workers.prune_retired_data_loader_workers(
            self,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def _is_rescan_worker_running(self, worker) -> bool:
        return ssa_gui_workers.is_rescan_worker_running(worker, sip_module=sip)

    def _prune_retired_rescan_workers(self) -> None:
        ssa_gui_workers.prune_retired_rescan_workers(
            self,
            global_workers=GLOBAL_RETIRED_RESCAN_WORKERS,
            global_meta=GLOBAL_RETIRED_RESCAN_META,
            max_global_workers=MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def _cleanup_data_loader_worker(self, worker, wait_ms: int = 1500) -> bool:
        return ssa_gui_workers.cleanup_data_loader_worker(
            self,
            worker,
            wait_ms=wait_ms,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def load_data(self):
        ssa_gui_workers.load_data(
            self,
            db_path=DB_PATH,
            table_name=TABLE_NAME,
            data_loader_cls=DataLoaderWorker,
            qmessagebox=QMessageBox,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def on_data_loaded(self, df: pd.DataFrame, request_id: int | None = None):
        ssa_gui_workers.on_data_loaded(self, df, request_id=request_id)
        try:
            self._refresh_quick_setor_executor_options()
            self._sync_quick_setor_executor_combo_from_filters()
        except Exception as exc:
            logger.debug("Falha ao atualizar combo rapido de setor executor apos carga: %s", exc)

    def on_load_error(self, error_msg: str, request_id: int | None = None):
        ssa_gui_workers.on_load_error(
            self,
            error_msg,
            request_id=request_id,
            db_path=DB_PATH,
            qmessagebox=QMessageBox,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def on_load_finished(self, worker=None, request_id: int | None = None):
        ssa_gui_workers.on_load_finished(
            self,
            worker=worker,
            request_id=request_id,
            global_workers=GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            global_meta=GLOBAL_RETIRED_DATA_LOADER_META,
            max_global_workers=MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
        )

    def _sort_num_reprogramacoes_robust(self, ascending: bool) -> pd.DataFrame:
        """Sort num_reprogramacoes with mixed legacy values without TypeError."""
        if self.df_exibido is None or self.df_exibido.empty:
            return self.df_exibido
        if "num_reprogramacoes" not in self.df_exibido.columns:
            return self.df_exibido

        sort_keys = self._get_num_reprogramacoes_sort_keys()
        ordered_index = sort_keys.sort_values(
            by=["__reprog_is_nan", "__reprog_num", "__reprog_txt"],
            ascending=[True, bool(ascending), True],
            na_position="last",
            kind="mergesort",
        ).index
        return self.df_exibido.loc[ordered_index]

    def _build_num_reprogramacoes_sort_keys(self, source_df: pd.DataFrame) -> pd.DataFrame:
        raw_series = source_df["num_reprogramacoes"]
        numeric = pd.to_numeric(raw_series, errors="coerce")
        missing_numeric_mask = numeric.isna()
        if bool(missing_numeric_mask.any()):
            extracted_source = raw_series[missing_numeric_mask].astype(str)
            extracted = extracted_source.str.extract(r"(-?\d+)")[0]
            extracted_numeric = pd.to_numeric(extracted, errors="coerce")
            numeric = numeric.copy()
            numeric.loc[missing_numeric_mask] = extracted_numeric
        return pd.DataFrame(
            {
                "__reprog_is_nan": numeric.isna(),
                "__reprog_num": numeric,
                "__reprog_txt": raw_series.astype(str).str.casefold(),
            },
            index=source_df.index,
        )

    def _get_num_reprogramacoes_sort_keys(self) -> pd.DataFrame:
        source_df = self.df_exibido
        last_search_df = getattr(self, "_df_last_search_filtered", None)
        if isinstance(last_search_df, pd.DataFrame) and "num_reprogramacoes" in last_search_df.columns:
            source_df = last_search_df

        source_id = id(source_df)
        source_len = len(source_df.index)
        cache = getattr(self, "_num_reprog_sort_cache", None)
        keys_df = cache.get("keys_df") if isinstance(cache, dict) else None
        cache_is_valid = (
            isinstance(cache, dict)
            and cache.get("source_id") == source_id
            and int(cache.get("source_len", -1)) == source_len
            and isinstance(keys_df, pd.DataFrame)
        )
        if not cache_is_valid:
            keys_df = self._build_num_reprogramacoes_sort_keys(source_df)
            self._num_reprog_sort_cache = {
                "source_id": source_id,
                "source_len": source_len,
                "keys_df": keys_df,
            }
        if not isinstance(keys_df, pd.DataFrame):
            keys_df = self._build_num_reprogramacoes_sort_keys(self.df_exibido)
        sort_keys = keys_df.reindex(self.df_exibido.index)
        if bool(sort_keys["__reprog_txt"].isna().any()):
            # Fallback defensivo: indices divergiram; usa dataframe atual.
            sort_keys = self._build_num_reprogramacoes_sort_keys(self.df_exibido)
        return sort_keys

    def _reset_num_reprogramacoes_sort_cache(self) -> None:
        self._num_reprog_sort_cache = {"source_id": None, "source_len": 0, "keys_df": None}

    def _prime_num_reprogramacoes_sort_cache(self) -> None:
        source_df = getattr(self, "_df_last_search_filtered", None)
        if not isinstance(source_df, pd.DataFrame):
            source_df = self.df_exibido
        if not isinstance(source_df, pd.DataFrame):
            self._reset_num_reprogramacoes_sort_cache()
            return
        if source_df.empty or "num_reprogramacoes" not in source_df.columns:
            self._reset_num_reprogramacoes_sort_cache()
            return
        keys_df = self._build_num_reprogramacoes_sort_keys(source_df)
        self._num_reprog_sort_cache = {
            "source_id": id(source_df),
            "source_len": len(source_df.index),
            "keys_df": keys_df,
        }

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
            preserved_widths = self._capture_current_column_widths()
            self._skip_width_recompute_once = True

            # Alterna direçção ao clicar na mesma coluna
            if getattr(self, 'sort_column', None) == col_name:
                self.sort_ascending = not getattr(self, 'sort_ascending', True)
            else:
                self.sort_column = col_name
                self.sort_ascending = True

            # Ordena resultado filtrado atual e reinicia paginaçção
            try:
                if self.sort_column == "num_reprogramacoes":
                    self.df_exibido = self._sort_num_reprogramacoes_robust(self.sort_ascending)
                else:
                    self.df_exibido = self.df_exibido.sort_values(
                        by=self.sort_column,
                        ascending=self.sort_ascending,
                        na_position='last'
                    )
                self._bump_data_revision("sort_column")
            except Exception as exc:
                logger.warning(
                    "Falha ao ordenar coluna '%s' (ascending=%s): %s",
                    self.sort_column,
                    self.sort_ascending,
                    exc,
                )

            self.paginator.set_dataframe(self.df_exibido)
            (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
            self._restore_column_widths(preserved_widths)

            # Indicador visual na UI
            try:
                header = self.table_widget.horizontalHeader()
                order = Qt.SortOrder.AscendingOrder if self.sort_ascending else Qt.SortOrder.DescendingOrder
                header.setSortIndicatorShown(True)
                header.setSortIndicator(logical_index, order)
            except Exception as exc:
                logger.debug("Falha ao atualizar indicador visual de ordenacao: %s", exc)
        except Exception as exc:
            logger.exception("Erro ao processar clique no cabecalho da tabela: %s", exc)

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
            full_name = self._resolve_column_display_name(col_name)
            apply_action = QAction(f"Filtrar '{full_name}'...", self)
            clear_action = QAction("Limpar filtro desta coluna", self)
            clear_all_action = QAction("Limpar todos filtros de colunas", self)
            best_fit_visible_action = QAction("Best fit colunas visiveis", self)
            show_all_affinity_action = QAction("Exibir todas colunas (afinidade)", self)

            def _apply():
                term = None
                input_dialog_cls = cast(Any, None)
                if QT_AVAILABLE:
                    try:
                        from PyQt6.QtWidgets import QInputDialog

                        input_dialog_cls = QInputDialog
                    except Exception as exc:
                        logger.debug("Falha ao importar QInputDialog no filtro por coluna: %s", exc)
                if input_dialog_cls is not None:
                    ok = False
                    term, ok = input_dialog_cls.getText(self, "Filtro por coluna", f"Termo para '{full_name}':")
                    if not ok:
                        term = None
                else:
                    term = self.search_input.text().strip()
                if term is not None:
                    normalized_term = str(term).strip()
                    if str(self._active_column_filters.get(col_name, "")).strip() != normalized_term:
                        self._safe_store_last_filter_state("header_context_apply_column_filter")
                    self._active_column_filters[col_name] = normalized_term
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
            best_fit_visible_action.triggered.connect(self.best_fit_visible_columns)
            show_all_affinity_action.triggered.connect(self._show_all_columns_by_affinity)

            cast(Any, menu).addAction(apply_action)
            if col_name in self._active_column_filters:
                cast(Any, menu).addAction(clear_action)
            if self._active_column_filters:
                cast(Any, menu).addAction(clear_all_action)
            cast(Any, menu).addAction(best_fit_visible_action)
            cast(Any, menu).addAction(show_all_affinity_action)
            menu.exec(header.mapToGlobal(pos))
        except Exception as exc:
            logger.debug("Falha ao abrir menu de contexto do header da tabela: %s", exc)

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
        except Exception as exc:
            logger.debug("Falha no eventFilter do header da tabela: %s", exc)
        return super().eventFilter(obj, event)

    # --- Helpers: painel e aplicaçção dos filtros por coluna ---
    def toggle_theme_menu(self):
        return ssa_gui_theme.toggle_theme_menu(
            self,
            gui_prefs=GUI_MAIN_PREFERENCES,
            project_root=project_root,
        )

    def apply_theme(self, name: str):
        ssa_gui_theme.apply_theme(
            self,
            name,
            gui_prefs=GUI_MAIN_PREFERENCES,
            project_root=project_root,
            highlight_defaults=(HIGHLIGHT_BACKGROUND_COLOR, HIGHLIGHT_FONT_WEIGHT),
        )

    def _apply_macos_contrast(self, theme_name: str):
        ssa_gui_theme.apply_macos_contrast(self, theme_name)

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleçção de colunas muda."""
        self.visible_columns = new_columns
        if hasattr(self, 'column_selector') and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(new_columns)
            except Exception as exc:
                logger.debug("Falha ao sincronizar colunas selecionadas no selector: %s", exc)
        if bool(getattr(self, "_persist_quick_filter_config", False)):
            try:
                GUI_MAIN_PREFERENCES["display_columns"] = list(new_columns)
                self._persist_quick_filter_config_state()
            except Exception as exc:
                logger.warning("Falha ao persistir colunas visiveis com persistencia ativa: %s", exc)
        # Reexibe a pãgina atual com as novas colunas
        self.display_current_page(self.paginator.current_page)
        # Nota: Persistencia de preferencias removida para isolamento do CLI
        # As configurações ficam no arquivo gui_main_preferences.json

    @staticmethod
    def _order_setor_executor_values(values: list[str]) -> list[str]:
        priority = ["IEE1", "IEE2", "IEE3", "IEE4", "MEL1", "MEL2", "MEL3", "MEL4"]
        normalized = []
        seen = set()
        for raw in values or []:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        upper_map = {item.upper(): item for item in normalized}
        ordered = []
        used_upper = set()
        for item in priority:
            if item in upper_map:
                ordered.append(item)
                used_upper.add(item)
        remaining = []
        for item in normalized:
            upper_item = item.upper()
            if upper_item in used_upper:
                continue
            remaining.append(item)
        remaining = sorted(remaining, key=lambda x: x.casefold())
        return ordered + remaining

    def _collect_setor_executor_values_for_combo(self) -> list[str]:
        base_df = getattr(self, "df_completo", None)
        if not isinstance(base_df, pd.DataFrame) or base_df.empty:
            base_df = getattr(self, "df_exibido", None)
        if not isinstance(base_df, pd.DataFrame) or base_df.empty:
            return []
        if "setor_executor" not in base_df.columns:
            return []
        raw_values = []
        for value in base_df["setor_executor"].dropna().astype(str):
            cleaned = str(value or "").strip()
            if cleaned:
                raw_values.append(cleaned)
        return self._order_setor_executor_values(raw_values)

    def _populate_quick_setor_executor_combo(self, combo, selected_value: str = "") -> None:
        if combo is None:
            return
        options = self._collect_setor_executor_values_for_combo()
        selected = str(selected_value or "").strip()
        self._quick_setor_executor_syncing = True
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Setor Executor: Todos", "")
            for value in options:
                combo.addItem(value, value)
            idx = combo.findData(selected)
            if idx < 0:
                idx = 0
            combo.setCurrentIndex(idx)
        except Exception as exc:
            logger.debug("Falha ao popular combo rapido de setor executor: %s", exc)
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass
            self._quick_setor_executor_syncing = False

    def _sync_quick_setor_executor_combo_from_filters(self) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_value = str(active_filters.get("setor_executor", "") or "").strip()
        if "," in selected_value:
            selected_value = ""
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            combo = ctx.get("quick_setor_executor_combo")
            if combo is None:
                continue
            self._populate_quick_setor_executor_combo(combo, selected_value=selected_value)

    def _refresh_quick_setor_executor_options(self) -> None:
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_value = str(active_filters.get("setor_executor", "") or "").strip()
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            combo = ctx.get("quick_setor_executor_combo")
            if combo is None:
                continue
            self._populate_quick_setor_executor_combo(combo, selected_value=selected_value)

    def _persist_quick_filter_config_state(self) -> None:
        try:
            gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
            gui_settings["persist_quick_filter_config"] = bool(self._persist_quick_filter_config)
            if self._persist_quick_filter_config and self._quick_setor_executor_saved:
                gui_settings["quick_setor_executor"] = str(self._quick_setor_executor_saved).strip()
            else:
                gui_settings.pop("quick_setor_executor", None)
            self._persist_gui_preferences()
        except Exception as exc:
            logger.warning("Falha ao persistir estado do filtro rapido de setor executor: %s", exc)

    def _on_persist_quick_filter_config_toggled(self, checked: bool) -> None:
        self._persist_quick_filter_config = bool(checked)
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        current_setor = str(active_filters.get("setor_executor", "") or "").strip()
        self._quick_setor_executor_saved = current_setor if self._persist_quick_filter_config else ""
        tab_contexts = getattr(self, "_tab_contexts", None)
        if isinstance(tab_contexts, list):
            for ctx in tab_contexts:
                if not isinstance(ctx, dict):
                    continue
                checkbox = ctx.get("persist_filter_config_checkbox")
                if checkbox is None:
                    continue
                try:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(self._persist_quick_filter_config)
                except Exception as exc:
                    logger.debug("Falha ao sincronizar checkbox de persistencia entre abas: %s", exc)
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception:
                        pass
        self._persist_quick_filter_config_state()

    def _on_quick_setor_executor_changed(self, combo) -> None:
        if bool(getattr(self, "_quick_setor_executor_syncing", False)):
            return
        selected = ""
        try:
            selected = str(combo.currentData() or "").strip()
        except Exception as exc:
            logger.debug("Falha ao ler valor do combo rapido de setor executor: %s", exc)
        self._safe_store_last_filter_state("quick_setor_executor_changed")
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        if selected:
            active_filters["setor_executor"] = selected
        else:
            active_filters.pop("setor_executor", None)
        self._active_column_filters = active_filters
        self._mark_profile_as_custom()
        self._refresh_after_filter_change()
        self._quick_setor_executor_saved = selected if self._persist_quick_filter_config else ""
        if self._persist_quick_filter_config:
            self._persist_quick_filter_config_state()

    def _apply_initial_quick_setor_executor_filter(self) -> None:
        if not bool(getattr(self, "_persist_quick_filter_config", False)):
            return
        selected = str(getattr(self, "_quick_setor_executor_saved", "") or "").strip()
        if not selected:
            return
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        active_filters["setor_executor"] = selected
        self._active_column_filters = active_filters
        self._refresh_after_filter_change()

    def _get_select_all_columns_from_selector(self) -> list[str]:
        selector = getattr(self, "column_selector", None)
        available = []
        selected = []
        default_columns = list(getattr(self, "default_columns", []) or [])
        if selector is not None:
            available = list(getattr(selector, "available_columns", []) or [])
            selected = list(getattr(selector, "selected_internal_columns", []) or [])
        canonical = list(self._get_canonical_available_columns() or [])
        if not available:
            available = canonical
        else:
            available = list(dict.fromkeys(available + [col for col in canonical if col not in available]))
        selection = [col for col in selected if col in available]
        if not selection:
            selection = [col for col in default_columns if col in available]
        remaining = [col for col in available if col not in selection]
        return selection + remaining

    def _sort_columns_by_affinity_desc(self, columns: list[str]) -> list[str]:
        if not columns:
            return []
        base_index = {col: idx for idx, col in enumerate(columns)}
        return sorted(
            list(dict.fromkeys(columns)),
            key=lambda col: (
                -int(COLUMN_AFFINITY_SCORES.get(col, 0)),
                int(base_index.get(col, 10000)),
            ),
        )

    def _show_all_columns_by_affinity(self) -> None:
        select_all_columns = self._get_select_all_columns_from_selector()
        if not select_all_columns:
            return
        ordered_columns = self._sort_columns_by_affinity_desc(select_all_columns)
        self.on_columns_changed(ordered_columns)

    def _capture_current_column_widths(self) -> dict[str, int]:
        width_manager = getattr(self, "width_manager", None)
        if width_manager is None or not hasattr(width_manager, "capture_current_column_widths"):
            return {}
        return width_manager.capture_current_column_widths(
            self.table_widget,
            getattr(self, "_current_display_columns", []),
        )

    def _restore_column_widths(self, widths: dict[str, int]) -> None:
        if not isinstance(widths, dict) or not widths:
            return
        width_manager = getattr(self, "width_manager", None)
        if width_manager is None or not hasattr(width_manager, "restore_column_widths"):
            return
        gui_widths = getattr(self, "_gui_column_pixel_widths", None)
        if not isinstance(gui_widths, dict):
            gui_widths = {}
            self._gui_column_pixel_widths = gui_widths
        width_manager.restore_column_widths(
            self.table_widget,
            getattr(self, "_current_display_columns", []),
            widths,
            saved_widths=getattr(self, "_saved_gui_column_widths", {}),
            gui_widths=gui_widths,
        )

    def display_current_page(self, page_number):
        return ssa_gui_table.display_current_page(self, page_number)

    def display_data(self, df):
        return ssa_gui_table.display_data(self, df)

    def _force_column_widths(self):
        return ssa_gui_table._force_column_widths(self)

    def _ensure_nonzero_column_widths(self):
        return ssa_gui_table._ensure_nonzero_column_widths(self)

    def _set_safe_width_for_col_index(self, idx: int, px: int = 80):
        return ssa_gui_table._set_safe_width_for_col_index(self, idx, px)

    def _compute_gui_column_widths(self, df: pd.DataFrame):
        return ssa_gui_table._compute_gui_column_widths(self, df)

    def _on_header_section_resized(self, logical_index: int, old_size: int, new_size: int):
        return ssa_gui_table._on_header_section_resized(self, logical_index, old_size, new_size)

    def _normalize_highlight_term(self, term):
        return ssa_gui_details._normalize_highlight_term(self, term)

    def _get_current_search_terms(self):
        return ssa_gui_details._get_current_search_terms(self)

    def _collect_highlight_terms(self):
        return ssa_gui_details._collect_highlight_terms(self)

    def _highlight_text(self, text, terms):
        return ssa_gui_details._highlight_text(self, text, terms)

    def _format_details_html(
        self,
        series,
        highlight_search_terms=False,
        font_size_pt=None,
        linkify=False,
        label_font_size_pt=None,
    ):
        return ssa_gui_details._format_details_html(
            self,
            series,
            highlight_search_terms=highlight_search_terms,
            font_size_pt=font_size_pt,
            linkify=linkify,
            label_font_size_pt=label_font_size_pt,
        )

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

        series = self.df_exibido.iloc[int(original_index)]
        numero_ssa = series.get("numero_ssa")
        self._open_details_dialog_for_ssa(numero_ssa)

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
        return ssa_gui_details._normalize_ssa_value(self, value)

    def _normalize_ssa_series(self, series: pd.Series) -> pd.Series:
        return ssa_gui_details._normalize_ssa_series(self, series)

    def update_details_from_selection(self):
        return ssa_gui_details.update_details_from_selection(self)

    def _get_derivadas_for_ssa(self, numero_ssa):
        return ssa_gui_details._get_derivadas_for_ssa(self, numero_ssa)

    def _jump_to_ssa(self, numero_ssa):
        return ssa_gui_details._jump_to_ssa(self, numero_ssa)

    def _on_details_anchor_clicked(self, url):
        return ssa_gui_details._on_details_anchor_clicked(self, url)

    def _open_details_dialog_for_ssa(self, numero_ssa):
        return ssa_gui_details._open_details_dialog_for_ssa(self, numero_ssa)

    def _filter_by_derivadas(self, numero_ssa):
        return ssa_gui_details._filter_by_derivadas(self, numero_ssa)

    def _clear_derivadas_filter(self):
        return ssa_gui_details._clear_derivadas_filter(self)

    def show_context_menu(self, position):
        """Mostra menu de contexto na tabela."""
        if self.table_widget.itemAt(position):
            menu = QMenu(self)

            # Acoes para celulas
            copy_cell_action = QAction("Copiar Valor da Celula", self)
            copy_cell_action.triggered.connect(self.copy_cell_value)
            cast(Any, menu).addAction(copy_cell_action)

            copy_row_action = QAction("Copiar Linha Completa", self)
            copy_row_action.triggered.connect(self.copy_row_data)
            cast(Any, menu).addAction(copy_row_action)

            export_action = QAction("Exportar lista (txt)", self)
            export_action.triggered.connect(self._export_current_list_txt)
            cast(Any, menu).addAction(export_action)

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
                    cast(Any, menu).addAction(origem_action)
                if derived_list:
                    label = f"Mostrar derivadas ({len(derived_list)})"
                    derivadas_action = QAction(label, self)
                    derivadas_action.triggered.connect(lambda: self._filter_by_derivadas(numero_ssa))
                    cast(Any, menu).addAction(derivadas_action)
                if self._last_derivada_origem:
                    voltar_action = QAction("Voltar SSA origem", self)
                    voltar_action.triggered.connect(self._clear_derivadas_filter)
                    cast(Any, menu).addAction(voltar_action)
                menu.addSeparator()

            # Acoes para colunas
            if current_item:
                column = current_item.column()
                if column > 0:  # Nção permitir remover a coluna de ándice
                    column_name = self.table_widget.horizontalHeaderItem(column).text()

                    remove_column_action = QAction(f"Remover Coluna '{column_name}'", self)
                    remove_column_action.triggered.connect(lambda: self.remove_column_by_index(column))
                    cast(Any, menu).addAction(remove_column_action)

                    auto_fit_action = QAction(f"Ajustar Largura '{column_name}'", self)
                    auto_fit_action.triggered.connect(lambda: self.auto_fit_column(column))
                    cast(Any, menu).addAction(auto_fit_action)

            menu.exec(self.table_widget.mapToGlobal(position))

    def copy_cell_value(self, *_):  # QAction triggered pode enviar 'checked'
        """Copia o valor da celula selecionada."""
        current_item = self.table_widget.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
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
            if clipboard is not None:
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

    def _compute_best_fit_width_for_column(self, column_index: int, sample_limit: int = 2000) -> int | None:
        if column_index < 0 or column_index >= self.table_widget.columnCount():
            return None
        cols = getattr(self, "_current_display_columns", None)
        if not cols or column_index >= len(cols):
            return None
        col_name = cols[column_index]
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        header_text = str(header_item.text()) if header_item is not None else str(col_name)
        width_manager = getattr(self, "width_manager", None)
        font_metrics = self.table_widget.fontMetrics()
        series = None
        if self.df_exibido is not None and not self.df_exibido.empty and col_name in self.df_exibido.columns:
            series = self.df_exibido[col_name]
        if width_manager is not None and hasattr(width_manager, "compute_best_fit_width"):
            return int(
                width_manager.compute_best_fit_width(
                    series=series,
                    header_text=header_text,
                    col_name=col_name,
                    measure_text=font_metrics.horizontalAdvance,
                    sample_limit=int(sample_limit),
                )
            )
        header_px = int(font_metrics.horizontalAdvance(str(header_text))) + 28
        if col_name == "#":
            return max(26, min(int(header_px), 90))
        return max(40, min(int(header_px), 420))

    def _best_fit_column_width(self, column_index: int) -> bool:
        width = self._compute_best_fit_width_for_column(column_index)
        if width is None:
            return False
        old_width = self.table_widget.columnWidth(column_index)
        self.table_widget.setColumnWidth(column_index, int(width))
        self._on_header_section_resized(column_index, old_width, int(width))
        return True

    def best_fit_visible_columns(self):
        col_count = self.table_widget.columnCount()
        if col_count <= 0:
            return
        for column_index in range(col_count):
            if column_index == 0:
                continue
            self._best_fit_column_width(column_index)

    def auto_fit_column(self, column_index):
        """Ajusta automaticamente a largura da coluna baseada no conteudo."""
        if self._best_fit_column_width(column_index):
            return
        old_width = self.table_widget.columnWidth(column_index)
        self.table_widget.resizeColumnToContents(column_index)
        new_width = self.table_widget.columnWidth(column_index)
        self._on_header_section_resized(column_index, old_width, new_width)

    def _setup_app_menus(self) -> None:
        menu_bar_getter = getattr(self, "menuBar", None)
        if not callable(menu_bar_getter):
            return
        menu_bar = menu_bar_getter()
        if menu_bar is None or not hasattr(menu_bar, "addMenu"):
            return

        arquivo_menu = menu_bar.addMenu("Arquivo")
        importacao_menu = menu_bar.addMenu("Importacao")
        db_menu = menu_bar.addMenu("Database")
        opcoes_menu = menu_bar.addMenu("Opcoes")
        ajuda_menu = menu_bar.addMenu("Ajuda")

        load_action = QAction("Recarregar Dados", self)
        load_action.triggered.connect(self.load_data)
        cast(Any, arquivo_menu).addAction(load_action)

        rescan_diff_action = QAction("Atualizar Dados", self)
        rescan_diff_action.triggered.connect(self.rescan_diff_data)
        cast(Any, arquivo_menu).addAction(rescan_diff_action)

        export_action = QAction("Exportar lista", self)
        export_action.triggered.connect(self._export_current_list_txt)
        cast(Any, arquivo_menu).addAction(export_action)

        close_action = QAction("Sair", self)
        close_action.triggered.connect(self.close)
        cast(Any, arquivo_menu).addAction(close_action)

        import_action = QAction("Importar XLS/XLSX externo", self)
        import_action.triggered.connect(self.import_external_excel_files)
        cast(Any, importacao_menu).addAction(import_action)

        rescan_diff_action = QAction("Atualizar Dados", self)
        rescan_diff_action.triggered.connect(self.rescan_diff_data)
        cast(Any, importacao_menu).addAction(rescan_diff_action)

        rescan_full_action = QAction("Reescaneamento Completo", self)
        rescan_full_action.triggered.connect(self.rescan_full_data)
        cast(Any, importacao_menu).addAction(rescan_full_action)

        open_docs_action = QAction("Abrir Pasta de Arquivos", self)
        open_docs_action.triggered.connect(self.open_docs_folder)
        cast(Any, importacao_menu).addAction(open_docs_action)

        open_processadas_action = QAction("Abrir Pasta Arquivos Processados", self)
        open_processadas_action.triggered.connect(self.open_processadas_folder)
        cast(Any, importacao_menu).addAction(open_processadas_action)

        open_nosurvivor_action = QAction("Abrir Pasta Arquivos Redundantes", self)
        open_nosurvivor_action.triggered.connect(self.open_nosurvivor_folder)
        cast(Any, importacao_menu).addAction(open_nosurvivor_action)

        consolidate_action = QAction("Consolidar arquivos de entrada", self)
        consolidate_action.triggered.connect(self.consolidate_input_files)
        cast(Any, importacao_menu).addAction(consolidate_action)

        rescan_prompt_action = QAction("Reescanear", self)
        rescan_prompt_action.triggered.connect(self.rescan_data)
        cast(Any, db_menu).addAction(rescan_prompt_action)

        derivadas_action = QAction("Atualizar derivadas", self)
        derivadas_action.triggered.connect(self.update_derivadas_from_sources)
        cast(Any, db_menu).addAction(derivadas_action)

        load_other_db_action = QAction("Carregar outro DB", self)
        load_other_db_action.triggered.connect(self.load_other_database)
        cast(Any, db_menu).addAction(load_other_db_action)

        vacuum_analyze_action = QAction("Compactar DB", self)
        vacuum_analyze_action.triggered.connect(self.run_vacuum_analyze)
        cast(Any, db_menu).addAction(vacuum_analyze_action)

        open_settings_action = QAction("Abrir arquivo de opcoes", self)
        open_settings_action.triggered.connect(self.open_settings_file_with_backup)
        cast(Any, opcoes_menu).addAction(open_settings_action)

        reset_settings_action = QAction("Restaurar opcoes padrao", self)
        reset_settings_action.triggered.connect(self.reset_settings_to_defaults)
        cast(Any, opcoes_menu).addAction(reset_settings_action)

        theme_action = QAction("Selecionar Tema", self)
        theme_action.triggered.connect(self.toggle_theme_menu)
        cast(Any, opcoes_menu).addAction(theme_action)

        install_action = QAction("Instalacao", self)
        install_action.triggered.connect(self.open_installation_guide)
        cast(Any, ajuda_menu).addAction(install_action)

        help_action = QAction("Ajuda", self)
        help_action.triggered.connect(self.show_filter_help)
        cast(Any, ajuda_menu).addAction(help_action)

    def import_external_excel_files(self):
        """Importa arquivos XLS/XLSX externos para docs_entrada com copia segura."""
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos Excel para importar",
            os.path.expanduser("~"),
            "Arquivos Excel (*.xlsx);;Todos os Arquivos (*)",
        )

        if not selected_files:
            return {"copied": 0, "skipped": 0, "failed": 0, "unsupported": 0}

        docs_path = os.path.join(project_root, "docs_entrada")
        os.makedirs(docs_path, exist_ok=True)

        copied = 0
        skipped = 0
        failed = 0
        unsupported = 0

        for source_path in selected_files:
            source = str(source_path or "").strip()
            if not source:
                skipped += 1
                continue
            if not os.path.isfile(source):
                failed += 1
                continue

            base_name = os.path.basename(source)
            lowered_name = base_name.casefold()
            if not lowered_name.endswith(".xlsx"):
                unsupported += 1
                logger.info(
                    "Importacao externa ignorou arquivo nao suportado pelo pipeline: %s",
                    source,
                )
                continue
            base_destination = os.path.join(docs_path, base_name)

            source_abs = os.path.abspath(source)
            destination_abs = os.path.abspath(base_destination)
            if source_abs == destination_abs:
                skipped += 1
                continue

            build_unique_destination = getattr(self, "_build_unique_destination_path", None)
            if callable(build_unique_destination):
                destination = build_unique_destination(base_destination)
            else:
                destination = SSAMainWindow._build_unique_destination_path.__get__(
                    self,
                    SSAMainWindow,
                )(base_destination)

            try:
                shutil.copy2(source, destination)
                copied += 1
            except Exception as exc:
                logger.warning("Falha ao copiar arquivo externo '%s': %s", source, exc)
                failed += 1

        summary = (
            f"Status: Importacao externa concluida - copiados={copied}, "
            f"ignorados={skipped}, nao_suportados={unsupported}, falhas={failed}."
        )
        if hasattr(self, "status_label"):
            self.status_label.setText(summary)

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(
                self,
                "Importacao externa",
                (
                    "Importacao concluida.\n\n"
                    f"Copiados: {copied}\n"
                    f"Ignorados: {skipped}\n"
                    f"Nao suportados: {unsupported}\n"
                    f"Falhas: {failed}\n\n"
                    f"Destino: {docs_path}"
                ),
            )

        return {
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "unsupported": unsupported,
        }

    def _resolve_settings_file_path(self) -> str:
        try:
            from core import config_manager

            resolver = getattr(config_manager, "_resolve_config_path", None)
            if callable(resolver):
                return str(resolver(config_manager.USER_SETTINGS_FILE))
        except Exception as exc:
            logger.debug("Falha ao resolver settings path via config_manager: %s", exc)
        return os.path.join(project_root, "config", "settings.json")

    def _build_unique_destination_path(self, destination_path: str) -> str:
        if not os.path.exists(destination_path):
            return destination_path
        base, ext = os.path.splitext(destination_path)
        idx = 1
        max_attempts = 10000
        while idx <= max_attempts:
            candidate = f"{base}__{idx}{ext}"
            if not os.path.exists(candidate):
                return candidate
            idx += 1
        raise RuntimeError(
            f"Nao foi possivel gerar nome unico apos {max_attempts} tentativas: {destination_path}"
        )

    @staticmethod
    def _validate_local_open_target(
        target_path: str,
        *,
        must_exist: bool,
        expect_dir: bool | None,
    ) -> str:
        raw = str(target_path or "")
        if not raw.strip():
            raise ValueError("Caminho vazio para abertura.")
        if any(ch in raw for ch in ("\x00", "\n", "\r")):
            raise ValueError("Caminho contem caracteres invalidos.")
        raw_parts = [part for part in raw.replace("\\", "/").split("/") if part]
        if ".." in raw_parts:
            raise ValueError("Caminho com parent traversal nao permitido.")
        normalized = os.path.abspath(os.path.normpath(raw))
        if must_exist and not os.path.exists(normalized):
            raise FileNotFoundError(f"Caminho nao encontrado: {normalized}")
        if expect_dir is True and os.path.exists(normalized) and not os.path.isdir(normalized):
            raise ValueError(f"Era esperado diretorio: {normalized}")
        if expect_dir is False and os.path.exists(normalized) and os.path.isdir(normalized):
            raise ValueError(f"Era esperado arquivo: {normalized}")
        return normalized

    @staticmethod
    def _resolve_platform_open_command() -> str:
        if sys.platform.startswith("win"):
            cmd = "explorer"
        elif sys.platform == "darwin":
            cmd = "open"
        else:
            cmd = "xdg-open"
        resolved = shutil.which(cmd)
        if not resolved:
            raise RuntimeError(f"Comando indisponivel para abrir recurso: {cmd}")
        resolved_abs = os.path.abspath(resolved)
        if not os.path.isabs(resolved_abs):
            raise RuntimeError(f"Comando de abertura invalido: {resolved}")
        return resolved_abs

    def open_settings_file_with_backup(self):
        """Abre settings.json para edicao apos criar backup failsafe com timestamp."""
        settings_path = os.path.abspath(self._resolve_settings_file_path())
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        try:
            if not os.path.exists(settings_path):
                from core.config_manager import load_settings, save_settings

                save_settings(load_settings())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = f"{settings_path}.bak_{timestamp}"
            shutil.copy2(settings_path, backup_path)
        except Exception as exc:
            logger.warning("Falha ao preparar backup de settings: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Falha ao preparar backup de opcoes: {exc}",
                )
            return {"opened": False, "backup_created": False, "settings_path": settings_path}

        try:
            safe_settings_path = SSAMainWindow._validate_local_open_target(
                settings_path,
                must_exist=True,
                expect_dir=False,
            )
        except Exception as exc:
            logger.warning("Caminho de settings invalido para abertura: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Caminho de opcoes invalido: {exc}")
            return {"opened": False, "backup_created": True, "settings_path": settings_path}

        opened = False
        try:
            if QT_AVAILABLE:
                opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(safe_settings_path)))
            if not opened:
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen([resolved, safe_settings_path], shell=False)
                opened = True
        except Exception as exc:
            logger.warning("Falha ao abrir settings para edicao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao abrir opcoes: {exc}")
            return {"opened": False, "backup_created": True, "settings_path": settings_path}

        if hasattr(self, "status_label"):
            self.status_label.setText(
                "Status: Opcoes abertas no editor externo (arquivo principal)."
            )
        return {"opened": opened, "backup_created": True, "settings_path": safe_settings_path}

    def reset_settings_to_defaults(self):
        """Restaura settings.json para os valores padrao com backup previo."""
        settings_path = self._resolve_settings_file_path()
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        try:
            from core import config_manager

            resolver = getattr(config_manager, "_resolve_config_path", None)
            if callable(resolver):
                default_settings_path = str(resolver(config_manager.DEFAULT_SETTINGS_FILE))
            else:
                default_settings_path = os.path.join(project_root, "config", "default_settings.json")
            if not os.path.exists(default_settings_path):
                config_manager.ensure_default_settings(fail_fast=False)
            with open(default_settings_path, "r", encoding="utf-8") as handle:
                default_settings = json.load(handle)
        except Exception as exc:
            logger.warning("Falha ao carregar defaults de opcoes: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao carregar opcoes padrao: {exc}")
            return {"ok": False, "reason": "load_default_failed"}

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Confirmar restauracao",
                "Restaurar opcoes padrao agora? Isso sobrescreve settings.json.",
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.No,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return {"ok": False, "cancelled": True}

        backup_created = False
        backup_path = ""
        try:
            if os.path.exists(settings_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = f"{settings_path}.bak_{timestamp}"
                shutil.copy2(settings_path, backup_path)
                backup_created = True
        except Exception as exc:
            logger.warning("Falha ao criar backup antes do reset de opcoes: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao criar backup de opcoes: {exc}")
            return {"ok": False, "reason": "backup_failed"}

        try:
            from core.config_manager import save_settings

            save_settings(default_settings)
        except Exception as exc:
            logger.warning("Falha ao restaurar opcoes padrao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao restaurar opcoes: {exc}")
            return {"ok": False, "reason": "save_failed"}

        if hasattr(self, "status_label"):
            self.status_label.setText("Status: Opcoes padrao restauradas com sucesso.")
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(self, "Sucesso", "Opcoes padrao restauradas.")
        return {
            "ok": True,
            "settings_path": settings_path,
            "backup_created": backup_created,
            "backup_path": backup_path,
        }

    def _resolve_latest_project_import_report(self, docs_path: str) -> dict[str, Any] | None:
        logs_dir = os.path.join(project_root, "logs")
        if not os.path.isdir(logs_dir):
            return None
        report_paths = sorted(
            (
                os.path.join(logs_dir, name)
                for name in os.listdir(logs_dir)
                if name.startswith("import_run_") and name.endswith(".json")
            ),
            key=os.path.getmtime,
            reverse=True,
        )
        docs_abs = os.path.abspath(docs_path)
        for report_path in report_paths:
            try:
                with open(report_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except Exception:
                continue
            payload_docs = str((payload.get("paths") or {}).get("docs_dir") or "")
            if os.path.abspath(payload_docs) != docs_abs:
                continue
            file_reports = payload.get("file_reports") or []
            if isinstance(file_reports, list) and file_reports:
                payload["_report_path"] = report_path
                return payload
        return None

    def consolidate_input_files(self):
        """Consolida arquivos de docs_entrada para processadas usando o ultimo report."""
        docs_path = os.path.join(project_root, "docs_entrada")
        if not os.path.isdir(docs_path):
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Pasta nao encontrada: {docs_path}")
            return {"moved": 0, "nosurvivor": 0, "pending": 0, "failed": 0}

        report = self._resolve_latest_project_import_report(docs_path)
        if report is None:
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(
                    self,
                    "Consolidacao",
                    "Nenhum import_run com file_reports para docs_entrada foi encontrado.",
                )
            return {"moved": 0, "nosurvivor": 0, "pending": 0, "failed": 0}

        processadas_dir = os.path.join(docs_path, "processadas")
        nosurvivor_dir = os.path.join(processadas_dir, "nosurvivor")
        os.makedirs(processadas_dir, exist_ok=True)
        os.makedirs(nosurvivor_dir, exist_ok=True)

        file_rows: dict[str, dict[str, int | str]] = {}
        mutation_fields = (
            "rows_inserted",
            "rows_updated",
            "rows_changed",
            "rows_ready_for_insert",
        )
        for entry in report.get("file_reports", []):
            if not isinstance(entry, dict):
                continue
            file_name = str(entry.get("file") or "").strip()
            if not file_name:
                continue
            status = str(entry.get("status") or "").strip().casefold()
            counts = entry.get("counts") or {}
            rows_inserted = int((counts.get("rows_inserted", 0) or 0))
            rows_updated = int((counts.get("rows_updated", 0) or 0))
            rows_changed = int((counts.get("rows_changed", 0) or 0))
            rows_ready_for_insert = int(
                counts.get("rows_ready_for_insert", rows_inserted) or 0
            )
            file_rows[file_name] = {
                "status": status,
                "rows_inserted": rows_inserted,
                "rows_updated": rows_updated,
                "rows_changed": rows_changed,
                "rows_ready_for_insert": rows_ready_for_insert,
            }

        moved = 0
        moved_nosurvivor = 0
        pending = 0
        failed = 0
        for base_name in os.listdir(docs_path):
            source_path = os.path.join(docs_path, base_name)
            if not os.path.isfile(source_path):
                continue
            lowered = base_name.casefold()
            if not (lowered.endswith(".xlsx") or lowered.endswith(".xls")):
                continue
            if base_name not in file_rows:
                pending += 1
                continue

            file_meta = file_rows.get(base_name, {})
            status = str(file_meta.get("status") or "").casefold()
            has_mutation = any(
                int(file_meta.get(name, 0) or 0) > 0 for name in mutation_fields
            )
            is_success_status = status in {"", "success", "no_rows"}
            is_zero_survivor = is_success_status and not has_mutation
            target_dir = processadas_dir
            if not is_success_status:
                pending += 1
                continue
            if is_zero_survivor:
                target_dir = nosurvivor_dir
            destination = self._build_unique_destination_path(
                os.path.join(target_dir, base_name)
            )
            try:
                shutil.move(source_path, destination)
                moved += 1
                if target_dir == nosurvivor_dir:
                    moved_nosurvivor += 1
            except Exception as exc:
                logger.warning(
                    "Falha ao mover arquivo na consolidacao '%s': %s",
                    source_path,
                    exc,
                )
                failed += 1

        summary = (
            f"Status: Consolidacao concluida - movidos={moved}, "
            f"nosurvivor={moved_nosurvivor}, pendentes={pending}, falhas={failed}."
        )
        if hasattr(self, "status_label"):
            self.status_label.setText(summary)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(
                self,
                "Consolidacao de arquivos",
                (
                    "Consolidacao concluida.\n\n"
                    f"Movidos: {moved}\n"
                    f"Para nosurvivor: {moved_nosurvivor}\n"
                    f"Pendentes sem evidencia no ultimo report: {pending}\n"
                    f"Falhas: {failed}\n\n"
                    f"Report usado: {report.get('_report_path', 'n/a')}"
                ),
            )
        return {
            "moved": moved,
            "nosurvivor": moved_nosurvivor,
            "pending": pending,
            "failed": failed,
            "report_path": str(report.get("_report_path", "")),
        }

    def rescan_data(self):
        """Reprocessa os arquivos Excel com feedback visual em tempo real."""
        from gui.workers import RescanWorker
        from gui.widgets import RescanProgressDialog

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            global_workers=GLOBAL_RETIRED_RESCAN_WORKERS,
            global_meta=GLOBAL_RETIRED_RESCAN_META,
            max_global_workers=MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
            rescan_mode="prompt",
        )

    def rescan_diff_data(self):
        """Reprocessa somente arquivos alterados por hash (modo diff)."""
        from gui.workers import RescanWorker
        from gui.widgets import RescanProgressDialog

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            global_workers=GLOBAL_RETIRED_RESCAN_WORKERS,
            global_meta=GLOBAL_RETIRED_RESCAN_META,
            max_global_workers=MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
            rescan_mode="diff",
        )

    def rescan_full_data(self):
        """Reprocessa tudo recriando DB candidato (modo full)."""
        from gui.workers import RescanWorker
        from gui.widgets import RescanProgressDialog

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            global_workers=GLOBAL_RETIRED_RESCAN_WORKERS,
            global_meta=GLOBAL_RETIRED_RESCAN_META,
            max_global_workers=MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
            retired_ttl_sec=RETIRED_WORKER_TTL_SEC,
            retired_force_wait_ms=RETIRED_WORKER_FORCE_WAIT_MS,
            sip_module=sip,
            rescan_mode="full",
        )

    def open_docs_folder(self):
        """Abre a pasta docs_entrada no explorador de arquivos (nao bloqueante)."""
        docs_path = os.path.join(project_root, "docs_entrada")
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=docs_path,
            folder_label="pasta de entrada",
        )

    def open_processadas_folder(self):
        """Abre docs_entrada/processadas no explorador de arquivos."""
        folder_path = os.path.join(project_root, "docs_entrada", "processadas")
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=folder_path,
            folder_label="pasta processadas",
        )

    def open_nosurvivor_folder(self):
        """Abre docs_entrada/processadas/nosurvivor no explorador de arquivos."""
        folder_path = os.path.join(
            project_root,
            "docs_entrada",
            "processadas",
            "nosurvivor",
        )
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=folder_path,
            folder_label="pasta sem sobreviventes",
        )

    def open_installation_guide(self):
        """Abre o guia de instalacao no editor/sistema padrao."""
        doc_path = os.path.abspath(
            os.path.join(project_root, "docs", "GUIA_MIGRACAO_NOVA_INSTALACAO.md")
        )
        if not os.path.exists(doc_path):
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Guia de instalacao nao encontrado: {doc_path}")
            return {"opened": False, "reason": "missing_file"}
        try:
            safe_doc_path = SSAMainWindow._validate_local_open_target(
                doc_path,
                must_exist=True,
                expect_dir=False,
            )
            opened = False
            if QT_AVAILABLE:
                opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(safe_doc_path)))
            if not opened:
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen([resolved, safe_doc_path], shell=False)
                opened = True
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Guia de instalacao aberto.")
            return {"opened": opened, "path": safe_doc_path}
        except Exception as exc:
            logger.warning("Falha ao abrir guia de instalacao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao abrir guia de instalacao: {exc}")
            return {"opened": False, "reason": "open_failed", "error": str(exc)}

    def run_vacuum_analyze(self):
        """Executa VACUUM/ANALYZE manualmente no banco principal."""
        db_path = DB_PATH
        if not db_path or not os.path.exists(db_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return {"ok": False, "reason": "missing_db"}
            QMessageBox.warning(self, "Erro", f"Banco nao encontrado: {db_path}")
            return {"ok": False, "reason": "missing_db"}

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Confirmar",
                "Compactar DB e atualizar estatisticas agora?",
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.No,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return {"ok": False, "cancelled": True}

        if bool(getattr(self, "_vacuum_analyze_running", False)):
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Compactacao do DB ja em andamento.")
            return {"ok": False, "reason": "already_running", "db_path": db_path}

        if hasattr(self, "status_label"):
            self.status_label.setText("Status: Compactando DB e atualizando estatisticas...")

        if os.environ.get("PYTEST_CURRENT_TEST"):
            result = SSAMainWindow._execute_vacuum_analyze(db_path)
            return SSAMainWindow._finalize_vacuum_analyze_result(self, result)

        self._vacuum_analyze_running = True
        self._vacuum_analyze_pending_result = None

        def _window_alive() -> bool:
            if self is None:
                return False
            # Test stubs and lightweight stand-ins are not Qt widgets.
            if not hasattr(self, "metaObject"):
                return True
            if sip is None:
                return True
            try:
                return not sip.isdeleted(self)
            except Exception:
                return False

        def _work() -> None:
            try:
                result = SSAMainWindow._execute_vacuum_analyze(db_path)
            except Exception as exc:
                result = {"ok": False, "error": str(exc), "db_path": db_path}
            self._vacuum_analyze_pending_result = result

        def _poll_delivery() -> None:
            if not _window_alive():
                self._vacuum_analyze_pending_result = None
                self._vacuum_analyze_running = False
                self._vacuum_analyze_thread = None
                return
            pending = getattr(self, "_vacuum_analyze_pending_result", None)
            if pending is None:
                if bool(getattr(self, "_vacuum_analyze_running", False)):
                    QTimer.singleShot(100, _poll_delivery)
                return
            self._vacuum_analyze_pending_result = None
            SSAMainWindow._finalize_vacuum_analyze_result(self, pending)

        worker = threading.Thread(target=_work, daemon=True)
        self._vacuum_analyze_thread = worker
        worker.start()
        QTimer.singleShot(100, _poll_delivery)
        return {"ok": True, "started": True, "db_path": db_path}

    @staticmethod
    def _execute_vacuum_analyze(db_path: str) -> dict[str, Any]:
        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            return {"ok": True, "db_path": db_path}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _finalize_vacuum_analyze_result(self, result: dict[str, Any]) -> dict[str, Any]:
        self._vacuum_analyze_running = False
        self._vacuum_analyze_thread = None

        if bool(result.get("ok")):
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: DB compactado e estatisticas atualizadas.")
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(self, "Sucesso", "Compactacao e atualizacao do DB concluidas.")
            return result

        error = str(result.get("error") or "Erro desconhecido")
        logger.error("Falha ao compactar DB e atualizar estatisticas: %s", error)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(self, "Erro", f"Falha na compactacao do DB: {error}")
        return {"ok": False, "error": error, "db_path": result.get("db_path")}

    def _open_folder_non_blocking(self, folder_path: str, folder_label: str) -> None:
        try:
            folder_path = SSAMainWindow._validate_local_open_target(
                folder_path,
                must_exist=False,
                expect_dir=True,
            )
        except Exception as exc:
            logger.warning("Caminho de pasta invalido para abertura (%s): %s", folder_label, exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Caminho de pasta invalido: {exc}")
            return
        if not os.path.exists(folder_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Pasta nao encontrada",
                (
                    f"A pasta '{folder_label}' nao existe.\n\n"
                    "Deseja criar agora?\n"
                    f"{folder_path}"
                ),
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.Yes,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as create_exc:
                logger.warning("Falha ao criar pasta %s: %s", folder_path, create_exc)
                qmessagebox.warning(self, "Erro", f"Falha ao criar pasta: {create_exc}")
                return

        try:
            safe_folder_path = SSAMainWindow._validate_local_open_target(
                folder_path,
                must_exist=True,
                expect_dir=True,
            )
        except Exception as exc:
            logger.warning("Caminho de pasta invalido apos validacao (%s): %s", folder_label, exc)
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            QMessageBox.warning(self, "Erro", f"Caminho de pasta invalido: {exc}")
            return

        try:
            # Prefer Qt abstraction to avoid blocking UI and keep cross-platform behavior.
            if QT_AVAILABLE:
                url = QUrl.fromLocalFile(safe_folder_path)
                ok = QDesktopServices.openUrl(url)
                if ok:
                    return
                raise RuntimeError("QDesktopServices.openUrl returned False")
            raise RuntimeError("Qt not available to open folders")
        except Exception as open_exc:
            logger.warning("Falha ao abrir pasta %s via Qt: %s", folder_label, open_exc)
            try:
                # Best-effort fallback, non-blocking.
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen([resolved, safe_folder_path], shell=False)
                return
            except Exception as fallback_exc:
                logger.warning("Fallback para abrir pasta falhou: %s", fallback_exc)
                if os.environ.get("PYTEST_CURRENT_TEST"):
                    return
                QMessageBox.warning(self, "Erro", f"Erro ao abrir pasta: {fallback_exc}")

    def _list_special_derivadas_sheets(self) -> list[str]:
        docs_path = os.path.join(project_root, "docs_entrada")
        if not os.path.isdir(docs_path):
            return []
        files: list[str] = []
        for base_name in os.listdir(docs_path):
            lowered = str(base_name).strip().casefold()
            if lowered.startswith("ssas derivadas e relacionadas") and lowered.endswith(".xlsx"):
                files.append(os.path.join(docs_path, base_name))
        return sorted(files, key=lambda path: os.path.basename(path).casefold())

    def _resolve_derivadas_table_name(self, db_path: str) -> str:
        candidates: list[str] = []
        for name in (TABLE_NAME, *ALL_SSA_TABLE_NAMES):
            if isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                if name not in candidates:
                    candidates.append(name)
        if not candidates:
            return CANONICAL_SSA_TABLE
        try:
            with sqlite3.connect(db_path) as conn:
                existing = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                required_cols = {"numero_ssa", "derivada_de"}
                compatible: set[str] = set()
                for name in candidates:
                    if name not in existing:
                        continue
                    cols = {
                        str(row[1]).strip()
                        for row in conn.execute(f'PRAGMA table_info("{name}")').fetchall()
                    }
                    if required_cols.issubset(cols):
                        compatible.add(name)
            for name in candidates:
                if name in compatible:
                    return name
        except Exception as exc:
            logger.warning("Falha ao resolver tabela para sync de derivadas: %s", exc)
        return CANONICAL_SSA_TABLE

    def update_derivadas_from_sources(self):
        def _has_sheet_parse_evidence(entry: dict) -> bool:
            if not isinstance(entry, dict):
                return False
            raw_stats = entry.get("stats")
            stats = raw_stats if isinstance(raw_stats, dict) else {}
            has_flag = bool(entry.get("has_parse_evidence"))
            accepted = int(stats.get("accepted_edges", 0) or 0)
            special_layout = int(stats.get("special_layout_detected", 0) or 0)
            informational = int(stats.get("informational_rows_skipped", 0) or 0)
            return has_flag or accepted > 0 or special_layout > 0 or informational > 0

        db_path = DB_PATH
        if not db_path or not os.path.exists(db_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            QMessageBox.warning(self, "Erro", f"Banco nao encontrado: {db_path}")
            return

        special_files = self._list_special_derivadas_sheets()
        table_name = self._resolve_derivadas_table_name(db_path)
        previous_status = self.status_label.text() if hasattr(self, "status_label") else ""
        previous_progress_visible = bool(self.progress_bar.isVisible()) if hasattr(self, "progress_bar") else False
        previous_progress_range = (
            (self.progress_bar.minimum(), self.progress_bar.maximum())
            if hasattr(self, "progress_bar")
            else (0, 0)
        )
        previous_progress_value = int(self.progress_bar.value()) if hasattr(self, "progress_bar") else 0

        try:
            self.update_derivadas_button.setEnabled(False)
            if hasattr(self, "progress_bar"):
                # Do not force visibility here; showing/hiding this widget changes
                # toolbar geometry and causes perceived layout shifts in filters tab.
                if previous_progress_visible:
                    self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Atualizando derivadas via DB...")
            if QT_AVAILABLE:
                QApplication.processEvents()

            db_report = sync_derivadas(
                db_path=db_path,
                table_name=table_name,
                include_db_source=True,
                verify_only=False,
                actor="gui-derivadas-db-phase",
            )

            final_report = db_report
            db_stats = db_report.get("db_stats") or {}
            db_edges = int(db_stats.get("accepted_edges", 0) or 0)
            if special_files:
                if hasattr(self, "status_label"):
                    self.status_label.setText(
                        f"Status: Atualizando derivadas via planilhas especiais ({len(special_files)})..."
                    )
                if QT_AVAILABLE:
                    QApplication.processEvents()
                final_report = sync_derivadas(
                    db_path=db_path,
                    table_name=table_name,
                    include_db_source=False,
                    sheet_files=special_files,
                    verify_only=False,
                    actor="gui-derivadas-sheet-phase",
                )
                reported_files = {
                    os.path.abspath(str(path))
                    for path in (final_report.get("sheet_files") or [])
                }
                expected_files = {os.path.abspath(path) for path in special_files}
                if reported_files != expected_files:
                    raise RuntimeError(
                        "Sync de planilhas especiais sem cobertura completa de arquivos "
                        f"(esperado={len(expected_files)}, recebido={len(reported_files)})."
                    )
                sheet_file_reports = final_report.get("sheet_file_reports") or []
                reports_by_file = {}
                for entry in sheet_file_reports:
                    if not isinstance(entry, dict):
                        continue
                    current_file = str(entry.get("sheet_file") or "").strip()
                    if not current_file:
                        continue
                    reports_by_file[os.path.abspath(current_file)] = entry
                files_without_evidence = []
                for current_file in sorted(expected_files):
                    current_entry = reports_by_file.get(current_file)
                    if current_entry is None or not _has_sheet_parse_evidence(current_entry):
                        files_without_evidence.append(os.path.basename(current_file))
                if files_without_evidence:
                    raise RuntimeError(
                        "Planilhas especiais sem evidencia individual: "
                        + ", ".join(files_without_evidence)
                    )

            merge_stats = final_report.get("merge_stats") or {}
            sheet_stats = final_report.get("sheet_stats") or {}
            merged_edges = int(merge_stats.get("merged_edges", 0) or 0)
            sheet_edges = int(sheet_stats.get("accepted_edges", 0) or 0)
            consistency = scan_derivadas_consistency(db_path=db_path)
            if not bool(consistency.get("schema_ready")) or not bool(consistency.get("is_consistent")):
                issue_counts = consistency.get("issue_counts") or {}
                raise RuntimeError(
                    "Derivadas inconsistente apos sync manual: "
                    f"{json.dumps(issue_counts, ensure_ascii=True)}"
                )
            if hasattr(self, "status_label"):
                self.status_label.setText(
                    "Status: Derivadas atualizadas (merged="
                    f"{merged_edges}, db={db_edges}, sheet={sheet_edges})."
                )
            try:
                self._update_derivadas_button_state()
            except Exception as exc:
                logger.warning("Falha ao atualizar estado do botao de derivadas apos sync manual: %s", exc)
        except Exception as exc:
            logger.exception("Falha ao atualizar derivadas manualmente: %s", exc)
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Falha ao atualizar derivadas.")
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            QMessageBox.critical(self, "Erro", f"Falha ao atualizar derivadas: {exc}")
        finally:
            self.update_derivadas_button.setEnabled(True)
            if hasattr(self, "progress_bar"):
                self.progress_bar.setVisible(previous_progress_visible)
                self.progress_bar.setRange(previous_progress_range[0], previous_progress_range[1])
                self.progress_bar.setValue(previous_progress_value)
            if hasattr(self, "status_label"):
                current_status = self.status_label.text()
                keep_status = current_status.startswith("Status: Derivadas atualizadas") or current_status.startswith(
                    "Status: Falha ao atualizar derivadas"
                )
                if not keep_status:
                    self.status_label.setText(previous_status)

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
                    QMessageBox.warning(self, "Erro", "O arquivo selecionado nao contem dados validos na tabela principal de SSAs.")
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

        # Mantem grid da aba Filtros responsivo durante resize.
        try:
            if getattr(self, "_current_tab_kind", None) == "filters":
                if hasattr(self, "adv_filters_group") and self.adv_filters_group:
                    width = self.adv_filters_group.width()
                    self._reorganize_advanced_filters_grid(width)
        except Exception as exc:
            logger.debug("Falha ao reorganizar grid de filtros durante resize: %s", exc)
        try:
            self._sync_bottom_panel_heights()
        except Exception as exc:
            logger.debug("Falha ao sincronizar altura dos paineis inferiores durante resize: %s", exc)

        # So recalcula se ha dados carregados e uma mudanca significativa na largura
        if (hasattr(self, 'df_exibido') and not self.df_exibido.empty and
            hasattr(self, '_last_window_width')):
            width_change = abs(event.size().width() - self._last_window_width)
            if width_change > 12:  # So recalcula se mudanca for > 12px
                expected_revision = int(getattr(self, "_data_revision", 0) or 0)
                self._schedule_resize_recompute(expected_revision=expected_revision)

        # Salva largura atual
        self._last_window_width = event.size().width()

    def _recompute_column_widths_on_resize(self, expected_revision=None):
        """Recalcula e aplica larguras das colunas apos resize da janela."""
        try:
            if hasattr(self, "isVisible") and not self.isVisible():
                return
            table_widget = getattr(self, "table_widget", None)
            if not _is_widget_valid(table_widget):
                return
            if expected_revision is not None:
                current_revision = int(getattr(self, "_data_revision", 0) or 0)
                if current_revision != int(expected_revision):
                    return
            # Verifica se widgets estção em estado vãlido
            if (
                table_widget is None
                or not hasattr(self, 'df_para_tabela')
                or self.df_para_tabela.empty
                or not table_widget.isVisible()
            ):
                return

            width_key = (
                id(self.df_para_tabela),
                len(self.df_para_tabela.index),
                len(self.df_para_tabela.columns),
                int(getattr(self, "_data_revision", 0) or 0),
                int(getattr(self, "_last_window_width", 0) or 0),
            )
            if getattr(self, "_last_resize_width_key", None) == width_key:
                return

            # Recalcula larguras com nova dimensção da janela usando WidthManager.
            # Em datasets grandes usa amostragem para reduzir custo no thread de UI.
            width_df = self.df_para_tabela
            if len(width_df.index) > 2000:
                width_df = width_df.head(2000)
            self._compute_gui_column_widths(width_df)
            # Aplica as novas larguras
            self._apply_computed_widths_only()
            self._last_resize_width_key = width_key
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.exception("Column width recompute failed during resize")

    def _schedule_resize_recompute(self, expected_revision: int) -> None:
        try:
            self._pending_resize_recompute_revision = int(expected_revision)
            if hasattr(self, "_resize_recompute_timer") and self._resize_recompute_timer is not None:
                self._resize_recompute_timer.start(300)
            else:
                QTimer.singleShot(
                    300,
                    lambda rev=int(expected_revision): self._recompute_column_widths_on_resize(expected_revision=rev),
                )
        except Exception as exc:
            logger.debug("Falha ao agendar recompute de resize: %s", exc)

    def _on_resize_recompute_timeout(self) -> None:
        expected_revision = getattr(self, "_pending_resize_recompute_revision", None)
        self._pending_resize_recompute_revision = None
        self._recompute_column_widths_on_resize(expected_revision=expected_revision)

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
        data_worker = getattr(self, "data_loader_thread", None)
        if data_worker is not None:
            try:
                self._cleanup_data_loader_worker(data_worker, wait_ms=3000)
            except Exception as exc:
                logger.debug("Falha no cleanup do data loader durante closeEvent: %s", exc)
            finally:
                if getattr(self, "data_loader_thread", None) is data_worker:
                    self.data_loader_thread = None

        # Aguarda finalizacao do filter thread se estiver rodando
        worker = getattr(self, 'filter_thread', None)
        if worker and hasattr(worker, 'isRunning') and worker.isRunning():
            try:
                # Usa cleanup centralizado (desconecta todos os callbacks, inclusive lambdas)
                self._cancel_active_filter_worker("closeEvent", wait_ms=3000)
            except Exception as exc:
                logger.debug("Filter cleanup fallback in closeEvent: %s", exc)
                try:
                    worker.quit()
                    worker.wait(3000)  # Aguarda ate 3 segundos
                except Exception as fallback_exc:
                    logger.debug("Falha no fallback de encerramento do filter worker: %s", fallback_exc)

        try:
            self._prune_retired_data_loader_workers()
        except Exception as exc:
            logger.debug("Falha ao podar workers aposentados no closeEvent: %s", exc)

        # Best-effort: parar reescaneamento/importacao em andamento ao encerrar a janela.
        rescan_worker = getattr(self, "_active_rescan_worker", None)
        if rescan_worker is not None:
            retained_globally = False

            def _retain_rescan_worker_global(target_worker, *, reason: str) -> bool:
                workers_lock = getattr(ssa_gui_workers, "_GLOBAL_WORKERS_LOCK", None)
                timestamp = perf_counter()

                def _enforce_rescan_cap() -> None:
                    if len(GLOBAL_RETIRED_RESCAN_WORKERS) <= MAX_GLOBAL_RETIRED_RESCAN_WORKERS:
                        return
                    overflow = len(GLOBAL_RETIRED_RESCAN_WORKERS) - MAX_GLOBAL_RETIRED_RESCAN_WORKERS
                    dropped_workers = GLOBAL_RETIRED_RESCAN_WORKERS[:overflow]
                    GLOBAL_RETIRED_RESCAN_WORKERS[:] = GLOBAL_RETIRED_RESCAN_WORKERS[overflow:]
                    for dropped_worker in dropped_workers:
                        GLOBAL_RETIRED_RESCAN_META.pop(dropped_worker, None)

                try:
                    if not ssa_gui_workers.is_data_loader_worker_alive(target_worker, sip):
                        logger.debug(
                            "RescanWorker invalido no closeEvent (%s); retencao global ignorada.",
                            reason,
                        )
                        return False
                    if workers_lock is None:
                        if target_worker not in GLOBAL_RETIRED_RESCAN_WORKERS:
                            GLOBAL_RETIRED_RESCAN_WORKERS.append(target_worker)
                        GLOBAL_RETIRED_RESCAN_META[target_worker] = timestamp
                        _enforce_rescan_cap()
                    else:
                        with workers_lock:
                            if target_worker not in GLOBAL_RETIRED_RESCAN_WORKERS:
                                GLOBAL_RETIRED_RESCAN_WORKERS.append(target_worker)
                            GLOBAL_RETIRED_RESCAN_META[target_worker] = timestamp
                            _enforce_rescan_cap()
                    try:
                        self._prune_retired_rescan_workers()
                    except Exception as exc:
                        logger.debug("Falha ao podar rescan workers apos retencao global: %s", exc)
                    logger.debug("RescanWorker retido globalmente durante closeEvent (%s).", reason)
                    return True
                except Exception as exc:
                    logger.debug(
                        "Falha ao reter RescanWorker globalmente no closeEvent (%s): %s",
                        reason,
                        exc,
                    )
                    return False

            retained_globally = _retain_rescan_worker_global(
                rescan_worker,
                reason="pre-shutdown-transfer",
            )

            try:
                try:
                    running_now = self._is_rescan_worker_running(rescan_worker)
                except Exception as exc:
                    running_now = True
                    logger.debug(
                        "Falha ao consultar estado inicial do RescanWorker no closeEvent (%s). Assumindo ativo para shutdown defensivo.",
                        exc,
                    )
                if running_now or retained_globally:
                    try:
                        if hasattr(rescan_worker, "stop"):
                            rescan_worker.stop()
                    except Exception as exc:
                        logger.debug("Falha ao solicitar stop do RescanWorker no closeEvent: %s", exc)
                    try:
                        if hasattr(rescan_worker, "quit"):
                            rescan_worker.quit()
                    except Exception as exc:
                        logger.debug("Falha ao solicitar quit do RescanWorker no closeEvent: %s", exc)
                    try:
                        rescan_worker.wait(1500)
                    except Exception as exc:
                        logger.debug("Falha ao aguardar RescanWorker no closeEvent: %s", exc)
                    try:
                        if self._is_rescan_worker_running(rescan_worker):
                            try:
                                if hasattr(rescan_worker, "terminate"):
                                    rescan_worker.terminate()
                                    rescan_worker.wait(1500)
                            except Exception as exc:
                                logger.debug("Falha no fallback terminate do RescanWorker no closeEvent: %s", exc)
                        if self._is_rescan_worker_running(rescan_worker):
                            retained_globally = _retain_rescan_worker_global(
                                rescan_worker,
                                reason="still-running-after-shutdown",
                            )
                    except Exception as exc:
                        logger.debug("Falha ao checar/reter RescanWorker no closeEvent: %s", exc)
            except Exception as exc:
                logger.debug("Falha ao encerrar RescanWorker durante closeEvent: %s", exc)
            finally:
                if not retained_globally:
                    _retain_rescan_worker_global(
                        rescan_worker,
                        reason="fallback-finally",
                    )
                try:
                    self._active_rescan_worker = None
                except Exception:
                    self._active_rescan_worker = None

        # Aceita o evento de fechamento
        event.accept()

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
