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

import copy
import json
import logging
import ntpath
import os
import posixpath
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
from collections import OrderedDict
from datetime import datetime
from time import perf_counter
from typing import Any, cast

import pandas as pd

try:
    from utils.version import get_app_version
except ImportError:

    def get_app_version(project_root: str | None = None) -> str:
        _ = project_root
        return "3.11+"


# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
runtime_root_override = os.environ.get("SSA_RUNTIME_ROOT")
code_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if runtime_root_override:
    project_root = os.path.abspath(runtime_root_override)
else:
    project_root = code_root
if code_root not in sys.path:
    sys.path.insert(0, code_root)

from core.config_manager import COLUMN_AFFINITY_SCORES  # noqa: E402
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS, atomic_write_json_file
from gui.gui_config import COMPATIBILITY_NULL_UI_COLUMNS  # noqa: E402
from gui.gui_config import DEFAULT_GUI_SETTINGS  # noqa: E402
from gui.gui_config import get_gui_main_preferences_path  # noqa: E402
from gui.gui_config import load_gui_main_preferences  # noqa: F401 - re-export for compatibility
from gui.gui_config import GUI_MAIN_PREFERENCES, REQUIRED_DISPLAY_COLUMNS

# Importações dos managers unificados
from gui.simple_width_manager import SimpleCacheManager  # noqa: E402
from gui.simple_width_manager import SimpleWidthManager
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from gui.ssa import gui_filters_advanced as ssa_gui_filters  # noqa: E402
from gui.ssa import gui_table as ssa_gui_table  # noqa: E402
from gui.ssa import gui_theme as ssa_gui_theme  # noqa: E402
from gui.ssa import gui_workers as ssa_gui_workers  # noqa: E402
from shared.db_names import ALL_SSA_TABLE_NAMES  # noqa: E402
from shared.db_names import CANONICAL_SSA_TABLE
from utils.themes import get_theme_roles, normalize_theme  # noqa: E402

# Inicializar logging robusto
try:
    from utils.robust_logging import setup_logging

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.debug(
        "Sistema de logging robusto inicializado na GUI", extra={"component": "gui"}
    )
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

_COLUMN_FILTER_DIALOG_MIN_WIDTH = 420
_COLUMN_FILTER_DIALOG_HINT = "Aceita termo, !termo para exclusao"
_TABLE_CELL_ALIGNMENT_LABELS = {
    "left": "Esquerda",
    "center": "Centro",
    "right": "Direita",
}
_DEFAULT_TABLE_CELL_ALIGNMENT = str(DEFAULT_GUI_SETTINGS["table_cell_alignment"])
SAM_HOME_URL = "https://osprd.itaipu/SAM_SMA/"
SAM_SSA_PUBLIC_VIEW_URL = (
    "https://osprd.itaipu/SAM_SMA/SSAPublicView.aspx"
    "?SerialNumber={numero_ssa}&language=pt"
)

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

import hashlib

from armazenamento.database import query_db  # noqa: E402
from armazenamento.derivadas_sync import (  # noqa: E402
    scan_derivadas_consistency,
    sync_derivadas,
)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms  # noqa: E402
from utils.formatting import format_cell  # noqa: E402
from utils.formatting import format_dataframe_for_display

# (mantido acima)


# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6 import sip
    from PyQt6.QtCore import (
        PYQT_VERSION_STR,
        QT_VERSION_STR,
        QEvent,
        QPoint,
        QSignalBlocker,
        Qt,
        QThread,
        QTimer,
        QUrl,
        pyqtSignal,
    )
    from PyQt6.QtGui import QAction, QDesktopServices, QFont
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpacerItem,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextBrowser,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
        QWidgetAction,
    )

    from gui.cache import FilterCache  # noqa: E402
    from gui.helpers import format_search_display  # noqa: E402
    from gui.helpers import highlight_text, normalize_chunk_for_parse

    # Import mixins for code organization
    from gui.mixins import FilterGUISSAMixin  # noqa: E402
    from gui.mixins import TabContextGUISSAMixin
    from gui.widgets import ColumnSelector  # noqa: E402
    from gui.widgets import (
        ColumnFilterDialog,
        ColumnManagerDialog,
        DataPaginator,
        FilterHelpDialog,
    )

    # Import workers, cache, widgets, and helpers from separate modules
    from gui.workers import DataLoaderWorker, FilterWorker  # noqa: E402
except ImportError as exc:
    QT_AVAILABLE = False
    sip = cast(Any, None)
    PYQT_VERSION_STR = "indisponivel"
    QT_VERSION_STR = "indisponivel"
    logger.warning("PyQt6 import failed, using headless stub mode: %s", exc)
    DataLoaderWorker = cast(Any, None)
    FilterWorker = cast(Any, None)
    ColumnFilterDialog = cast(Any, None)
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
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return 0

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
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def run(self):
            pass

    class QSignalBlocker:
        def __init__(self, *_args, **_kwargs):
            pass

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
DB_PATH = os.environ.get("SSA_DB_PATH") or os.path.join(project_root, "data", "ssas.db")
TSM_DEBUG_ENABLED = str(os.environ.get("SSA_TSM_DEBUG", "")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Constantes de UI
DETAILS_DIALOG_FONT_SIZE = 10  # pt
DETAILS_DIALOG_TABLE_PADDING = 8  # px
DETAILS_DIALOG_BORDER_COLOR = "#ccc"
DETAILS_DIALOG_MIN_WIDTH = 700  # px
DETAILS_DIALOG_MIN_HEIGHT = 500  # px
HIGHLIGHT_BACKGROUND_COLOR = "yellow"
HIGHLIGHT_FONT_WEIGHT = "bold"

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

_TSM_DEBUG_EVENT_NAMES = {
    QEvent.Type.FocusIn: "focus_in",
    QEvent.Type.FocusOut: "focus_out",
    QEvent.Type.InputMethod: "input_method",
    QEvent.Type.InputMethodQuery: "input_method_query",
    QEvent.Type.Show: "show",
    QEvent.Type.Hide: "hide",
}

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
    "numero_ssa",
    "situacao",
    "descricao_ssa",
    "localizacao_codigo",
    "descricao_servico",
    "setor_emissor",
    "setor_executor",
    "data_cadastro",
    "prazo_limite",
]

DETAIL_DISPLAY_OVERRIDES = {
    "situacao": "Situacao",
    "semana_cadastro": "Semana de Cadastro",
    "data_cadastro": "Data de Cadastro",
    "localizacao_codigo": "Localizacao",
    "loc": "Localizacao",
    "descricao_ssa": "Descricao da SSA",
    "setor_executor": "Setor Executor",
    "setor_emissor": "Setor Emissor",
    "responsavel_emissor": "Responsavel Emissor",
    "solicitante": "Solicitante",
    "servico_origem": "Servico de Origem",
    "grau_prioridade_emissao": "Grau de Prioridade (Emissao)",
    "grau_prioridade_planejamento": "Grau de Prioridade (Planejamento)",
    "execucao_simples": "Execucao Simples",
    "responsavel_programacao": "Responsavel pela Programacao",
    "responsavel_execucao": "Responsavel pela Execucao",
    "num_reprogramacoes": "Reprogramacoes",
    "semana_programada": "Semana Programada",
    "semana_executada": "Semana Executada",
    "prazo_limite": "Prazo Limite",
    "tempo_disponivel": "Tempo Disponivel",
    "data_limite": "Data Limite",
    "tempo_excedido": "Tempo Excedido",
    "total_tempo_tex_executada": "Tempo Total (TEX)",
    "total_tempo_tpe_executada": "Tempo Total (TPE)",
    "total_tempo_tpo_executada": "Tempo Total (TPO)",
    "numero_ssa": "Numero da SSA",
    "descricao_execucao": "Descricao da Execucao",
    "status_execucao_prazo": "Situacao do Prazo",
    "execucao_parcial": "Execucao Parcial",
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


def resolve_app_version_text() -> str:
    """Resolve versao da aplicacao para exibicao em UI."""
    try:
        app_version = str(get_app_version()).strip()
    except Exception as exc:
        logger.debug("Falha ao resolver versao da aplicacao: %s", exc)
        app_version = ""
    if not app_version:
        return "0.0.0"
    return app_version


def resolve_uv_version_text() -> str:
    """Resolve versao do uv para exibicao em UI."""
    uv_exe = shutil.which("uv")
    if not uv_exe:
        return "indisponivel"
    try:
        result = subprocess.run(
            [uv_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        output = str(result.stdout or result.stderr).strip()
        if output:
            return output
    except Exception as exc:
        logger.debug("Falha ao resolver versao do uv: %s", exc)
    return "indisponivel"


def _iter_build_info_candidates():
    seen = set()
    raw_candidates = []
    bundled_root = os.environ.get("SSA_BUNDLED_ROOT", "")
    if bundled_root:
        raw_candidates.append(os.path.join(bundled_root, "config", "build_info.json"))
        raw_candidates.append(
            os.path.join(bundled_root, "_internal", "config", "build_info.json")
        )
    config_dir = os.environ.get("SSA_CONFIG_DIR", "")
    if config_dir:
        raw_candidates.append(os.path.join(config_dir, "build_info.json"))
    raw_candidates.append(os.path.join(project_root, "config", "build_info.json"))
    for raw_path in raw_candidates:
        path = os.path.abspath(raw_path)
        if path in seen:
            continue
        seen.add(path)
        yield path


def _load_embedded_build_info() -> dict[str, Any]:
    for path in _iter_build_info_candidates():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return cast(dict[str, Any], payload)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Falha ao ler build_info %s: %s", path, exc)
    return {}


def _iter_installation_guide_candidates():
    seen = set()
    guide_rel_path = os.path.join("docs", "GUIA_MIGRACAO_NOVA_INSTALACAO.md")
    raw_candidates = [os.path.join(project_root, guide_rel_path)]
    bundled_root = os.environ.get("SSA_BUNDLED_ROOT", "")
    if bundled_root:
        raw_candidates.append(os.path.join(bundled_root, guide_rel_path))
        raw_candidates.append(
            os.path.join(bundled_root, "_internal", guide_rel_path)
        )
    for raw_path in raw_candidates:
        path = os.path.abspath(raw_path)
        if path in seen:
            continue
        seen.add(path)
        yield path


def resolve_git_commit_hash_text() -> str:
    """Resolve hash curto do commit atual para exibicao em UI."""
    git_exe = shutil.which("git")
    if not git_exe:
        return "indisponivel"
    try:
        result = subprocess.run(
            [git_exe, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            cwd=project_root,
        )
        output = str(result.stdout or "").strip()
        if output:
            return output
    except Exception as exc:
        logger.debug("Falha ao resolver hash de commit: %s", exc)
    return "indisponivel"


def build_about_message(app_version: str) -> str:
    """Monta texto do dialogo Sobre."""
    python_version = str(sys.version.split()[0]) if sys.version else "indisponivel"
    pandas_version = str(getattr(pd, "__version__", "indisponivel"))
    pyqt_version = str(PYQT_VERSION_STR or "indisponivel")
    qt_version = str(QT_VERSION_STR or "indisponivel")
    build_info = _load_embedded_build_info()
    uv_version = resolve_uv_version_text()
    if uv_version == "indisponivel":
        uv_version = str(build_info.get("uv_version") or uv_version)
    commit_hash = resolve_git_commit_hash_text()
    if commit_hash == "indisponivel":
        commit_hash = str(
            build_info.get("git_commit_short")
            or build_info.get("git_commit")
            or commit_hash
        )
    lines = [
        "Consulta Rapida de SSAs",
        f"Versao app: {app_version}",
        "",
        f"Python: {python_version}",
        f"uv: {uv_version}",
        f"PyQt6: {pyqt_version}",
        f"Qt: {qt_version}",
        f"pandas: {pandas_version}",
        f"Commit: {commit_hash}",
    ]
    build_datetime = str(build_info.get("build_datetime") or "").strip()
    if build_datetime:
        lines.append(f"Build: {build_datetime}")
    c_compiler_version = str(build_info.get("c_compiler_version") or "").strip()
    if c_compiler_version:
        lines.append(f"C/C++: {c_compiler_version}")
    rustc_version = str(build_info.get("rustc_version") or "").strip()
    if rustc_version:
        lines.append(f"Rust: {rustc_version}")
    return "\n".join(lines)


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

    def _set_widget_min_height_safe(
        self, widget: QWidget, height: int, label: str
    ) -> None:
        try:
            widget.setMinimumHeight(height)
        except Exception as exc:
            logger.debug("Falha ao aplicar altura minima em %s: %s", label, exc)

    def _set_widget_fixed_height_safe(
        self, widget: QWidget, height: int, label: str
    ) -> None:
        try:
            widget.setMinimumHeight(height)
            widget.setMaximumHeight(height)
        except Exception as exc:
            logger.debug("Falha ao aplicar altura fixa em %s: %s", label, exc)

    def _persist_gui_preferences(self):
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
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

    def _log_tsm_debug(self, event_name: str, *, widget_role: str, obj) -> None:
        if not TSM_DEBUG_ENABLED:
            return
        try:
            tab_index = (
                int(self.main_tabs.currentIndex())
                if hasattr(self, "main_tabs") and self.main_tabs is not None
                else -1
            )
        except Exception:
            tab_index = -1
        try:
            object_name = str(getattr(obj, "objectName", lambda: "")() or "")
        except Exception:
            object_name = ""
        logger.warning(
            "[TSM_DEBUG] event=%s role=%s class=%s object_name=%s tab=%s",
            event_name,
            widget_role,
            type(obj).__name__,
            object_name,
            tab_index,
        )

    def _register_tsm_debug_widget(self, widget, role: str) -> None:
        if not TSM_DEBUG_ENABLED or widget is None:
            return
        try:
            probes = getattr(self, "_tsm_debug_widget_roles", None)
            if not isinstance(probes, dict):
                probes = {}
                self._tsm_debug_widget_roles = probes
            probes[id(widget)] = str(role)
            widget.installEventFilter(self)
        except Exception as exc:
            logger.debug("Falha ao registrar widget para TSM debug (%s): %s", role, exc)

    def _setup_tsm_debug_probes(self) -> None:
        if not TSM_DEBUG_ENABLED:
            return
        try:
            self._register_tsm_debug_widget(getattr(self, "main_tabs", None), "tabs")
            contexts = list(getattr(self, "_tab_contexts", []) or [])
            for idx, ctx in enumerate(contexts):
                if not isinstance(ctx, dict):
                    continue
                prefix = f"tab{idx}"
                for key in (
                    "search_input",
                    "quick_setor_executor_combo",
                    "adv_week_emissao_start",
                    "adv_week_execucao_start",
                ):
                    self._register_tsm_debug_widget(ctx.get(key), f"{prefix}.{key}")
        except Exception as exc:
            logger.debug("Falha ao instalar probes de TSM debug: %s", exc)

    def _apply_table_cell_alignment_preference(self, alignment_name: str):
        normalized = str(alignment_name or "").strip().lower()
        if normalized not in _TABLE_CELL_ALIGNMENT_LABELS:
            logger.warning(
                "Valor invalido para table_cell_alignment via menu: %r",
                alignment_name,
            )
            self.status_label.setText("Status: Alinhamento de celulas invalido.")
            return False

        gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        gui_settings["table_cell_alignment"] = normalized
        current_details_ssa = getattr(self, "_details_current_ssa", None)
        current_details_series = None
        if current_details_ssa:
            try:
                current_details_series = ssa_gui_details._get_series_for_ssa(
                    self, current_details_ssa
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao resolver detalhes atuais antes de reaplicar alinhamento da tabela: %s",
                    exc,
                )

        for key, action in getattr(self, "_table_cell_alignment_actions", {}).items():
            try:
                action.setChecked(key == normalized)
            except Exception as exc:
                logger.debug("Falha ao atualizar check do alinhamento %s: %s", key, exc)

        persisted = self._persist_gui_preferences()
        self.display_current_page(self.paginator.current_page, update_details=False)
        if current_details_series is not None:
            try:
                ssa_gui_details._update_details_from_series(
                    self, current_details_series
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao restaurar detalhes atuais apos mudar alinhamento da tabela: %s",
                    exc,
                )

        if persisted:
            self.status_label.setText(
                f"Status: Alinhamento das celulas definido para {_TABLE_CELL_ALIGNMENT_LABELS[normalized]}."
            )
        else:
            self.status_label.setText(
                "Status: Alinhamento aplicado, mas falhou a persistencia das preferencias."
            )
        return persisted

    def show_about_dialog(self):
        QMessageBox.information(self, "Sobre", build_about_message(self._app_version))

    def __init__(self):
        super().__init__()
        try:
            # Evita acumulo de janelas/widgets fechados (impacta performance ao reaplicar tema global).
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        except Exception as exc:
            logger.debug("Failed to set WA_DeleteOnClose on main window: %s", exc)
        self._app_version = resolve_app_version_text()
        self.setWindowTitle(f"Consulta Rapida de SSAs v{self._app_version}")
        self.setGeometry(100, 100, 1200, 800)
        self._last_window_width = self.width()
        # Icone da janela (prioriza .ico no Windows)
        try:
            from PyQt6.QtGui import QIcon

            if sys.platform == "darwin":
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.icns"),
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                ]
            elif sys.platform.startswith("win"):
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                    os.path.join(project_root, "resources", "app_icon.icns"),
                ]
            else:
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.icns"),
                ]
            for icon_path in icon_candidates:
                if not os.path.exists(icon_path):
                    continue
                app_icon = QIcon(icon_path)
                if app_icon.isNull():
                    continue
                self.setWindowIcon(app_icon)
                app_instance_getter = getattr(QApplication, "instance", None)
                app_instance = (
                    app_instance_getter() if callable(app_instance_getter) else None
                )
                if app_instance is not None and hasattr(app_instance, "setWindowIcon"):
                    app_instance.setWindowIcon(app_icon)
                if hasattr(QApplication, "setWindowIcon"):
                    QApplication.setWindowIcon(app_icon)
                break
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
        self.visible_columns = [
            col
            for col in self.default_columns
            if col in self.internal_to_display or col == "#"
        ]

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
        self._pending_search_display = ""

        # Configurações de GUI (independentes do CLI)
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        self._restored_page_size = gui_settings.get("page_size", 50)
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
        self._advanced_filters = (
            dict(adv_default) if isinstance(adv_default, dict) else {}
        )
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
        self._saved_gui_column_widths = GUI_MAIN_PREFERENCES.get(
            "column_widths", {}
        ).copy()

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
            GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})["theme"] = (
                preferred_theme
            )
            self._persist_gui_preferences()
        except Exception as exc:
            logger.debug("Failed to persist preferred startup theme: %s", exc)
        # Aplica perfil inicial de filtros por setor
        self._apply_initial_filter_profile()

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
        self.open_sam_button = QPushButton("Abrir SAM")
        self.open_sam_button.setToolTip("Abrir pagina principal do SAM no navegador")
        self.open_sam_button.clicked.connect(self._open_sam_home)
        toolbar_layout.addWidget(cast(Any, self.open_sam_button))

        self.load_button = QPushButton("Carregar Dados")
        self.load_button.setToolTip("Carregar dados do banco de dados existente")
        self.load_button.clicked.connect(self.load_data)
        toolbar_layout.addWidget(cast(Any, self.load_button))

        # Botões de ações
        self.rescan_button = QPushButton("Reescanear")
        self.rescan_button.setToolTip(
            "Reprocessar arquivos Excel da pasta docs_entrada"
        )
        self.rescan_button.clicked.connect(self.rescan_data)
        toolbar_layout.addWidget(cast(Any, self.rescan_button))

        self.update_derivadas_button = QPushButton("Atualizar Derivadas", self)
        self.update_derivadas_button.setToolTip(
            "Atualizar tabelas de derivadas (fase DB e fase planilhas especiais)"
        )
        self.update_derivadas_button.clicked.connect(self.update_derivadas_from_sources)
        # Botao removido da barra superior por UX; funcionalidade permanece no menu Database.
        self.update_derivadas_button.setVisible(False)
        # Semana Atual (YYYYWW) como indicador informativo na barra superior
        try:
            from datetime import date

            y, w, _ = date.today().isocalendar()
            week_str = f"{y}{w:02d}"
        except Exception:
            week_str = "-"
        self.week_label = QLabel(f"Semana Atual: {week_str}")
        # Destaque visual em caixa
        self._week_label_style = "font-weight:600; border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        self.week_label.setStyleSheet(self._week_label_style)
        self.week_label.setToolTip("Semana ISO atual")
        toolbar_layout.addSpacing(6)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(cast(Any, self.week_label))
        toolbar_layout.addStretch()

        self.filtered_status_label = QLabel("Status: 0 de 0 SSAs")
        self.filtered_status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        self.filtered_status_label.setMinimumWidth(170)
        self.filtered_status_label.setMaximumWidth(240)
        self.filtered_status_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        toolbar_layout.addWidget(cast(Any, self.filtered_status_label))

        # Status em caixa e progresso
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")
        self.status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        # Keep toolbar geometry stable even when status text gets longer.
        self.status_label.setMinimumWidth(280)
        self.status_label.setMaximumWidth(520)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
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
        try:
            tab_bar = self.main_tabs.tabBar()
            if tab_bar is not None:
                tab_bar.setVisible(False)
                tab_bar.setMaximumHeight(0)
        except Exception as exc:
            logger.debug("Falha ao ocultar barra nativa de abas: %s", exc)
        self._tab_contexts = [ctx_main, ctx_filters]
        self._sync_inline_tab_selector_state(0)
        main_layout.addWidget(cast(Any, self.main_tabs))
        self.main_tabs.currentChanged.connect(self._on_tab_changed)
        self._bind_tab_context(ctx_main)
        self._setup_tsm_debug_probes()
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug(
                "Falha ao agendar sincronizacao inicial de altura dos paineis inferiores: %s",
                exc,
            )

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
        self._num_reprog_sort_cache = {
            "source_id": None,
            "source_len": 0,
            "keys_df": None,
        }
        self._pending_resize_recompute_revision = None
        self._resize_recompute_timer = QTimer(self)
        self._resize_recompute_timer.setSingleShot(True)
        self._resize_recompute_timer.timeout.connect(self._on_resize_recompute_timeout)
        self._filter_request_seq = 0
        self._active_filter_request_id = 0
        self._active_filter_search_request_id = None
        self._active_filter_search_display = ""
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        # Em ambiente de testes (pytest), force modo síncrono para previsibilidade
        if not self._sync_filtering and os.environ.get("PYTEST_CURRENT_TEST"):
            self._sync_filtering = True

        # Configura cache size da configuração
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        cache_size = gui_settings.get("filter_cache_size", 50)
        if FilterWorker is not None and FilterCache is not None:
            FilterWorker._cache = FilterCache(max_size=cache_size)
        else:
            logger.warning(
                "FilterWorker/FilterCache indisponivel; cache de filtro nao inicializado"
            )

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
        search_input = QLineEdit()
        search_input.setPlaceholderText("Termos separados por virgula; ! exclui termo")
        search_input.setToolTip(
            "Todos os termos digitados devem ser satisfeitos na mesma linha.\n\n"
            "A busca pesquisa nas colunas relevantes da GUI; datas puras ficam nos filtros especificos.\n\n"
            "Modos por termo: \n"
            "- contem (padrao): foo\n- comeca com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex: ~foo.*bar\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
        )
        search_input.setMinimumWidth(425)
        search_input.setMaximumWidth(950)
        self._set_widget_min_height_safe(search_input, 26, "campo de pesquisa")
        search_input.returnPressed.connect(
            lambda tab=tab_kind: self._on_general_search_apply_clicked(tab)
        )
        search_input.textChanged.connect(self._on_search_text_changed)
        search_button = QPushButton("Aplicar")
        self._set_widget_fixed_height_safe(
            search_button, 26, "botao Aplicar da pesquisa geral"
        )
        try:
            search_button.setStyleSheet(self._week_label_style)
            search_button.setMaximumWidth(110)
        except Exception as exc:
            logger.debug("Falha ao aplicar estilo no botao Aplicar da pesquisa: %s", exc)
        search_button.clicked.connect(
            lambda _checked=False, tab=tab_kind: self._on_general_search_apply_clicked(
                tab
            )
        )
        clear_filter_button = QPushButton("Limpar Busca")
        self._set_widget_fixed_height_safe(
            clear_filter_button, 26, "botao Limpar Busca"
        )
        try:
            clear_filter_button.setStyleSheet(self._week_label_style)
            clear_filter_button.setMaximumWidth(130)
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar estilo no botao Limpar Busca da pesquisa: %s", exc
            )
        clear_filter_button.clicked.connect(
            lambda _checked=False, tab=tab_kind: self._on_general_search_clear_clicked(
                tab
            )
        )
        clear_filter_button.setToolTip(
            "Limpa apenas a busca e cancela a busca em andamento. "
            "Filtros de coluna e avancados continuam ativos."
        )
        clear_filter_button.setEnabled(False)
        save_filter_button = QPushButton("Salvar Filtros")
        self._set_widget_fixed_height_safe(
            save_filter_button, 26, "botao Salvar Filtros"
        )
        save_filter_button.setMaximumWidth(170)
        save_filter_button.setToolTip(
            "Salva o estado atual: busca, filtros de coluna, filtros avancados e perfil."
        )
        try:
            save_filter_button.setStyleSheet(self._week_label_style)
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar estilo no botao Salvar Filtros: %s", exc
            )
        save_filter_button.clicked.connect(self.save_current_filter)

        filter_tags_widget = QWidget()
        self._set_widget_fixed_height_safe(
            filter_tags_widget, 26, "area de filtros salvos"
        )
        filter_tags_widget.setMaximumWidth(280)
        filter_tags_widget.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        filter_tags_layout = QHBoxLayout(cast(Any, filter_tags_widget))
        filter_tags_layout.setContentsMargins(0, 0, 0, 0)
        filter_tags_layout.setSpacing(5)

        left.addWidget(cast(Any, clear_filter_button))
        left.addWidget(cast(Any, search_button))
        left.addWidget(cast(Any, search_input))
        left.addSpacing(8)
        left.addWidget(cast(Any, filter_tags_widget))
        column_selector = ColumnSelector(
            self.display_map,
            self.visible_columns,
            default_columns=self.default_columns,
            available_columns=self._get_canonical_available_columns(),
            info_font=self._info_font,
        )
        column_selector.columns_changed.connect(self.on_columns_changed)

        quick_setor_executor_label = QLabel("Setor Executor:")
        quick_setor_executor_combo = QComboBox()
        quick_setor_executor_combo.setToolTip(
            "Filtro rapido de Setor Executor (aplica junto com os demais filtros)."
        )
        try:
            quick_setor_executor_combo.setMinimumWidth(138)
            quick_setor_executor_combo.setMaximumWidth(188)
            quick_setor_executor_combo.setMinimumContentsLength(9)
            quick_setor_executor_combo.setMaxVisibleItems(14)
            control_height = 26
            self._set_widget_fixed_height_safe(
                quick_setor_executor_combo,
                control_height,
                "combo rapido de setor executor",
            )
            adjust_policy = getattr(
                QComboBox.SizeAdjustPolicy,
                "AdjustToMinimumContentsLengthWithIcon",
                None,
            )
            if adjust_policy is None:
                adjust_policy = getattr(
                    QComboBox.SizeAdjustPolicy, "AdjustToContents", None
                )
            if adjust_policy is not None:
                quick_setor_executor_combo.setSizeAdjustPolicy(cast(Any, adjust_policy))
            quick_setor_executor_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
            combo_view = quick_setor_executor_combo.view()
            if combo_view is not None:
                scroll_bar_policy = getattr(
                    getattr(Qt, "ScrollBarPolicy", None), "ScrollBarAsNeeded", None
                )
                if scroll_bar_policy is not None:
                    combo_view.setVerticalScrollBarPolicy(cast(Any, scroll_bar_policy))
        except Exception as exc:
            logger.debug("Falha ao configurar combo rapido de setor executor: %s", exc)
        self._populate_quick_setor_executor_combo(
            quick_setor_executor_combo,
            selected_value=str(
                OrderedDict(self._active_column_filters or {}).get("setor_executor", "")
            ).strip(),
        )
        quick_setor_executor_combo.currentIndexChanged.connect(
            lambda _idx,
            combo=quick_setor_executor_combo: self._on_quick_setor_executor_changed(
                combo
            )
        )

        search_row.addLayout(cast(Any, left))
        search_row.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        tab_layout.addLayout(cast(Any, search_row))

        search_help = QLabel(
            "Use termos positivos e ! para excluir. A busca vale para qualquer coluna."
        )
        search_help.setWordWrap(False)
        try:
            search_help.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
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
        pagination_filters_layout.addSpacing(8)
        pagination_filters_layout.addWidget(cast(Any, column_selector))

        profile_selector = None
        pagination_filters_layout.addSpacing(12)

        persistent_filters_layout = QHBoxLayout()
        persistent_filters_layout.setContentsMargins(0, 0, 0, 0)

        exclude_ste_checkbox = QCheckBox("Nao esta em SCA/SES/STE")
        exclude_ste_checkbox.setToolTip("Oculta SSAs com situacao SCA, SES ou STE")
        try:
            exclude_ste_checkbox.setChecked(False)
        except Exception as exc:
            logger.debug(
                "Falha ao inicializar estado do checkbox excluir STE/SCA: %s", exc
            )
        try:
            exclude_ste_checkbox.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar checkbox excluir STE/SCA na aba: %s", exc)
        try:
            exclude_ste_checkbox.toggled.connect(self._on_exclude_ste_sca_toggled)
        except Exception as exc:
            logger.warning(
                "Falha ao conectar toggle do checkbox excluir STE/SCA: %s", exc
            )
        persistent_filters_layout.addWidget(cast(Any, exclude_ste_checkbox))

        pagination_filters_layout.addLayout(cast(Any, persistent_filters_layout))
        pagination_filters_layout.addStretch()
        pagination_filters_layout.addWidget(cast(Any, quick_setor_executor_label))
        pagination_filters_layout.addSpacing(8)
        pagination_filters_layout.addWidget(cast(Any, quick_setor_executor_combo))

        col_filter_indicator = QLabel("")
        try:
            if self._info_font is not None:
                col_filter_indicator.setFont(cast(Any, QFont(self._info_font)))
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar fonte no indicador de filtro por coluna: %s", exc
            )
        col_filter_indicator.setToolTip(
            "Filtros por coluna acumulam com a busca (logica E entre filtros). "
            "Dentro da mesma coluna, virgulas representam alternativas implicitas. Consulte a ajuda para outros atalhos."
        )
        try:
            col_filter_indicator.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar indicador de filtro por coluna: %s", exc)

        tab_layout.addLayout(cast(Any, pagination_filters_layout))

        filters_summary_frame = None
        filters_summary_label = None
        filters_summary_items_widget = None
        filters_summary_items_layout = None
        clear_all_filters_btn = None
        export_list_btn = None
        undo_filter_btn = None
        try:
            filters_summary_frame = QFrame()
            filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
            self._set_widget_fixed_height_safe(
                filters_summary_frame, 44, "barra de filtros ativos"
            )
            summary_layout = QHBoxLayout(cast(Any, filters_summary_frame))
            summary_layout.setContentsMargins(6, 4, 6, 4)
            summary_layout.setSpacing(8)
            try:
                align_top = cast(Any, Qt).AlignmentFlag.AlignTop
                cast(Any, summary_layout).setAlignment(align_top)
            except Exception as exc:
                logger.debug("Falha ao alinhar resumo de filtros no topo: %s", exc)
                align_top = None
            filters_summary_label = QLabel("Nenhum filtro ativo")
            if self._info_font is not None:
                try:
                    filters_summary_label.setFont(cast(Any, QFont(self._info_font)))
                except Exception as exc:
                    logger.debug("Falha ao aplicar fonte no resumo de filtros: %s", exc)
            filters_summary_items_widget = QWidget()
            filters_summary_items_layout = QHBoxLayout(
                cast(Any, filters_summary_items_widget)
            )
            filters_summary_items_layout.setContentsMargins(0, 0, 0, 0)
            filters_summary_items_layout.setSpacing(6)
            clear_all_filters_btn = QPushButton("Limpar todos os filtros")
            clear_all_filters_btn.setMaximumWidth(200)
            clear_all_filters_btn.clicked.connect(self._on_clear_all_filters_clicked)
            try:
                clear_all_filters_btn.setStyleSheet(self._week_label_style)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estilo no botao limpar todos os filtros: %s", exc
                )
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
                logger.debug(
                    "Falha ao aplicar estilo no botao undo de filtros: %s", exc
                )
            summary_text_layout = QVBoxLayout()
            summary_text_layout.setContentsMargins(0, 0, 0, 0)
            summary_text_layout.setSpacing(4)
            summary_text_layout.addWidget(cast(Any, filters_summary_label), 0)
            summary_text_layout.addWidget(cast(Any, filters_summary_items_widget), 0)
            if align_top is None:
                summary_layout.addWidget(cast(Any, clear_all_filters_btn), 0)
                summary_layout.addWidget(cast(Any, save_filter_button), 0)
                summary_layout.addWidget(cast(Any, export_list_btn), 0)
                summary_layout.addWidget(cast(Any, undo_filter_btn), 0)
            else:
                summary_layout.addWidget(cast(Any, clear_all_filters_btn), 0, align_top)
                summary_layout.addWidget(cast(Any, save_filter_button), 0, align_top)
                summary_layout.addWidget(cast(Any, export_list_btn), 0, align_top)
                summary_layout.addWidget(cast(Any, undo_filter_btn), 0, align_top)
            summary_layout.addLayout(cast(Any, summary_text_layout), 1)
            tab_layout.addWidget(cast(Any, filters_summary_frame))
            filters_summary_frame.setVisible(True)
            try:
                self._update_undo_button_state()
            except Exception as exc:
                logger.debug("Falha ao atualizar estado inicial do botao undo: %s", exc)
        except Exception as exc:
            logger.warning(
                "Falha ao construir painel de resumo de filtros da aba: %s", exc
            )

        if (
            isinstance(self._restored_page_size, int)
            and 10 <= self._restored_page_size <= 500
        ):
            try:
                paginator.page_size_spinbox.setValue(self._restored_page_size)
            except Exception as exc:
                logger.debug("Falha ao restaurar page size na paginacao: %s", exc)
        try:
            paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)
        except Exception as exc:
            logger.warning(
                "Falha ao conectar persistencia de page size na paginacao: %s", exc
            )

        # Table
        table_widget = QTableWidget()
        table_widget.setEditTriggers(cast(Any, QTableWidget.EditTrigger.NoEditTriggers))
        table_widget.setSelectionBehavior(
            cast(Any, QAbstractItemView.SelectionBehavior.SelectRows)
        )
        self._set_widget_min_height_safe(table_widget, 220, "tabela principal")
        header = table_widget.horizontalHeader()
        vertical_header = table_widget.verticalHeader()
        if header is not None and vertical_header is not None:
            header.setSectionResizeMode(cast(Any, QHeaderView.ResizeMode.Interactive))
            vertical_header.setVisible(False)
            vertical_header.setSectionResizeMode(
                cast(Any, QHeaderView.ResizeMode.Fixed)
            )
            vertical_header.setDefaultSectionSize(24)
            header.sectionResized.connect(self._on_header_section_resized)
        else:
            logger.warning(
                "Header da tabela indisponivel; configuracao avancada de colunas ignorada."
            )

        table_widget.doubleClicked.connect(self.on_table_double_click)
        table_widget.cellClicked.connect(self.on_table_cell_clicked)
        table_widget.itemSelectionChanged.connect(self.update_details_from_selection)

        try:
            if header is not None:
                header.setSectionsClickable(True)
                header.setSortIndicatorShown(True)
                try:
                    header.setSectionsMovable(True)
                except Exception as exc:
                    logger.debug(
                        "Falha ao habilitar drag and drop no header da tabela: %s", exc
                    )
                try:
                    header.setFirstSectionMovable(False)
                except Exception as exc:
                    logger.debug(
                        "Falha ao fixar primeira secao do header da tabela: %s", exc
                    )
                try:
                    header.setMinimumSectionSize(26)
                    header.setDefaultSectionSize(92)
                except Exception as exc:
                    logger.debug(
                        "Falha ao configurar tamanho minimo/default do header da tabela: %s",
                        exc,
                    )
                try:
                    f = header.font()
                    f.setBold(False)
                    header.setFont(f)
                    header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar estilo/fonte no header da tabela: %s", exc
                    )
                header.sectionClicked.connect(self.on_header_clicked)
                header.sectionMoved.connect(self._on_header_section_moved)
                header.setContextMenuPolicy(
                    cast(Any, Qt.ContextMenuPolicy.CustomContextMenu)
                )
                header.customContextMenuRequested.connect(self.show_header_context_menu)
                header.installEventFilter(self)
        except Exception as exc:
            logger.warning(
                "Falha ao configurar comportamento do header da tabela: %s", exc
            )

        table_widget.setContextMenuPolicy(
            cast(Any, Qt.ContextMenuPolicy.CustomContextMenu)
        )
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
                details_viewport.installEventFilter(self)
                self._details_text_viewport = details_viewport
        except Exception as exc:
            logger.debug(
                "Falha ao configurar preenchimento do viewport de detalhes: %s", exc
            )
        details_text.setReadOnly(True)
        try:
            details_text.setOpenLinks(False)
            details_text.setOpenExternalLinks(False)
            details_text.anchorClicked.connect(self._on_details_anchor_clicked)
        except Exception as exc:
            logger.debug("Falha ao configurar links no painel de detalhes: %s", exc)
        details_layout.addWidget(cast(Any, details_text))
        bottom_layout.addWidget(cast(Any, details_group), 2)

        col_filters_group = QGroupBox("")
        col_filters_outer = QVBoxLayout(cast(Any, col_filters_group))
        col_filters_outer.setContentsMargins(1, 1, 1, 1)
        col_filters_outer.setSpacing(1)
        tab_selector_ssas_btn = QPushButton("Por coluna")
        tab_selector_filters_btn = QPushButton("Avancados")
        inline_tab_style = (
            "QPushButton {"
            "font-weight:600; border:1px solid palette(mid); border-radius:4px;"
            "padding:1px 8px; background: transparent;"
            "}"
            "QPushButton:checked {"
            "background: palette(highlight); color: palette(highlighted-text);"
            "}"
        )
        for button, target_index, tooltip in (
            (tab_selector_ssas_btn, 0, "Mostrar aba por coluna"),
            (tab_selector_filters_btn, 1, "Mostrar aba de filtros avancados"),
        ):
            try:
                button.setCheckable(True)
                button.setMaximumWidth(78)
                self._set_widget_fixed_height_safe(
                    button, 22, f"seletor compacto de aba {target_index}"
                )
                button.setToolTip(tooltip)
                button.setStyleSheet(inline_tab_style)
                if hasattr(button, "setFlat"):
                    button.setFlat(True)
            except Exception as exc:
                logger.debug(
                    "Falha ao configurar seletor compacto de aba %s: %s",
                    target_index,
                    exc,
                )
            button.clicked.connect(
                lambda _checked=False, index=target_index: self.main_tabs.setCurrentIndex(
                    index
                )
            )

        def _build_inline_filter_tabs_header() -> QWidget:
            inline_tabs_widget = QWidget()
            self._set_widget_fixed_height_safe(
                inline_tabs_widget, 26, "cabecalho compacto de abas de filtros"
            )
            inline_tabs_layout = QHBoxLayout(cast(Any, inline_tabs_widget))
            inline_tabs_layout.setContentsMargins(0, 0, 0, 0)
            inline_tabs_layout.setSpacing(6)
            inline_title_label = QLabel(
                "Filtros Avancados" if tab_kind == "filters" else "Filtros por Coluna"
            )
            try:
                inline_title_label.setStyleSheet(
                    "font-weight:600; color: palette(windowText);"
                )
            except Exception as exc:
                logger.debug("Falha ao aplicar estilo no titulo inline de filtros: %s", exc)
            inline_tabs_layout.addWidget(cast(Any, inline_title_label), 0)
            inline_tabs_layout.addSpacing(8)
            inline_tabs_layout.addWidget(cast(Any, tab_selector_ssas_btn), 0)
            inline_tabs_layout.addWidget(cast(Any, tab_selector_filters_btn), 0)
            inline_tabs_layout.addStretch(1)
            return inline_tabs_widget
        inline_tabs_widget = _build_inline_filter_tabs_header()
        col_filters_outer.addWidget(cast(Any, inline_tabs_widget), 0)
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
        add_column_filter_btn.setToolTip(
            "Selecionar qualquer coluna para ativar filtro dedicado"
        )
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
            try:
                adv_group.setTitle("")
                adv_layout = adv_group.layout()
                if adv_layout is not None:
                    inline_tabs_widget = _build_inline_filter_tabs_header()
                    adv_layout.insertWidget(0, cast(Any, inline_tabs_widget), 0)
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar titulo de grupo de filtros avancados: %s",
                    exc,
                )
            right_col.addWidget(cast(Any, adv_group), 1)
            col_filters_group.setVisible(False)
            right_col.addWidget(cast(Any, col_filters_group))
            # APENAS na aba Filtros: Detalhes max 40% (2) vs Filtros 60% (3)
            bottom_layout.addWidget(cast(Any, right_col_widget), 3)
        else:
            right_col.addWidget(cast(Any, col_filters_group), 1)
            # Aba SSAs: manter Detalhes em 40% (2) e painel da direita em 60% (3).
            bottom_layout.addWidget(cast(Any, right_col_widget), 3)

        tab_layout.addSpacing(4)
        tab_layout.addLayout(cast(Any, bottom_layout), 4)

        ctx.update(
            {
                "search_input": search_input,
                "search_button": search_button,
                "clear_filter_button": clear_filter_button,
                "save_filter_button": save_filter_button,
                "column_selector": column_selector,
                "quick_setor_executor_label": quick_setor_executor_label,
                "quick_setor_executor_combo": quick_setor_executor_combo,
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
                "filters_summary_items_widget": filters_summary_items_widget,
                "filters_summary_items_layout": filters_summary_items_layout,
                "clear_all_filters_btn": clear_all_filters_btn,
                "export_list_btn": export_list_btn,
                "undo_filter_btn": undo_filter_btn,
                "table_widget": table_widget,
                "details_group": details_group,
                "details_text": details_text,
                "col_filters_group": col_filters_group,
                "col_filters_scroll": col_filters_scroll,
                "col_filters_container": col_filters_container,
                "col_filters_list_layout": col_filters_list_layout,
                "tab_kind": tab_kind,
                "inline_tabs_widget": inline_tabs_widget,
                "tab_selector_ssas_btn": tab_selector_ssas_btn,
                "tab_selector_filters_btn": tab_selector_filters_btn,
                "add_column_filter_btn": add_column_filter_btn,
                "clear_all_btn": clear_all_btn,
            }
        )
        if tab_kind == "filters":
            self._adv_ctx = adv_ctx
            ctx.update(adv_ctx)
        return ctx

    def _get_canonical_available_columns(self) -> list[str]:
        """Retorna colunas elegiveis para seletores de UI (sem legados invalidos)."""
        legacy_invalid_columns = {
            "Numero da SSA",
            "Número da SSA",
            "No SSA",
            "Data Cadastro",
        }
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
                allowed_columns = {
                    token.strip() for token in allowed_raw.split(",") if token.strip()
                }
        except Exception as exc:
            logger.debug(
                "Falha ao ler whitelist de colunas via SSA_ALLOWED_COLUMNS: %s", exc
            )
            allowed_columns = None

        non_null_cols = None
        try:
            cached_cols = getattr(self, "_non_null_cols_cache", None)
            if isinstance(cached_cols, set) and cached_cols:
                non_null_cols = set(cached_cols)
        except Exception as exc:
            logger.debug(
                "Falha ao ler cache de colunas nao nulas para menu canonico: %s", exc
            )
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
                logger.warning(
                    "Falha no fallback de refresh de filtros avancados: %s",
                    fallback_exc,
                )

    def _run_adv_options_refresh(self):
        self._adv_options_scheduled = False
        if getattr(self, "_current_tab_kind", None) != "filters":
            return
        if not getattr(self, "_adv_options_dirty", False):
            return
        try:
            self._refresh_advanced_filter_options()
            self._sync_advanced_executor_ui_from_active_filter()
            self._adv_options_dirty = False
        except Exception as exc:
            logger.warning("Falha ao executar refresh de filtros avancados: %s", exc)

    def _sync_inline_tab_selector_state(self, active_index: int) -> None:
        contexts = list(getattr(self, "_tab_contexts", []) or [])
        for ctx in contexts:
            if not isinstance(ctx, dict):
                continue
            for button_index, key in (
                (0, "tab_selector_ssas_btn"),
                (1, "tab_selector_filters_btn"),
            ):
                button = ctx.get(key)
                if button is None:
                    continue
                signals_blocked = False
                try:
                    button.blockSignals(True)
                    signals_blocked = True
                    button.setChecked(button_index == active_index)
                except Exception as exc:
                    logger.debug(
                        "Falha ao sincronizar seletor visual de aba %s: %s",
                        button_index,
                        exc,
                    )
                finally:
                    if signals_blocked:
                        try:
                            button.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais do seletor visual de aba: %s",
                                exc,
                            )

    def _on_tab_changed(self, index: int) -> None:
        if not hasattr(self, "_tab_contexts"):
            return
        if index < 0 or index >= len(self._tab_contexts):
            return
        ctx = self._tab_contexts[index]
        if TSM_DEBUG_ENABLED:
            logger.warning(
                "[TSM_DEBUG] tab_changed index=%s kind=%s",
                index,
                str(ctx.get("tab_kind") or ""),
            )
        self._sync_inline_tab_selector_state(index)
        self._bind_tab_context(ctx)
        try:
            self._refresh_quick_setor_executor_options()
            self._sync_quick_setor_executor_combo_from_filters()
            self._sync_advanced_executor_ui_from_active_filter()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido de setor executor na troca de aba: %s",
                exc,
            )
        if ctx.get("tab_kind") == "filters":
            try:
                ssa_gui_theme.reapply_current_theme_widget_styles(
                    self,
                    highlight_defaults=(
                        HIGHLIGHT_BACKGROUND_COLOR,
                        HIGHLIGHT_FONT_WEIGHT,
                    ),
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao reaplicar estilos do tema na aba de filtros: %s", exc
                )
            pending_theme = getattr(self, "_pending_theme_refresh_column_filters", None)
            if pending_theme:
                try:
                    self._adv_options_dirty = True
                    if hasattr(self, "_schedule_adv_options_refresh"):
                        self._schedule_adv_options_refresh()
                    elif hasattr(self, "_refresh_advanced_filter_options"):
                        self._refresh_advanced_filter_options()
                except Exception as exc:
                    logger.debug(
                        "Falha ao atualizar filtros avancados pendentes na troca de aba: %s",
                        exc,
                    )
                finally:
                    self._pending_theme_refresh_column_filters = None
            try:
                if bool(getattr(self, "_adv_options_dirty", False)):
                    self._schedule_adv_options_refresh()
            except Exception as exc:
                logger.debug(
                    "Falha ao agendar refresh de filtros avancados na troca de aba: %s",
                    exc,
                )
            try:
                self._reorganize_advanced_filters_grid(
                    getattr(self, "adv_filters_group").width()
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao reorganizar filtros avancados apos troca de aba: %s", exc
                )
            try:
                QTimer.singleShot(
                    0,
                    lambda: self._reorganize_advanced_filters_grid(
                        getattr(self, "adv_filters_group").width()
                    ),
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao agendar reorganizacao deferida apos troca de aba: %s", exc
                )
        try:
            self._queue_bottom_panel_height_sync()
        except Exception as exc:
            logger.debug(
                "Falha ao enfileirar sincronizacao de altura apos troca de aba: %s", exc
            )

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
        base_height = int(window_height * 0.26)
        font_adjust = max(0, base_font_pt - 10) * 8
        target = base_height + font_adjust
        return max(200, min(280, target))

    def _queue_bottom_panel_height_sync(self) -> None:
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug(
                "Falha ao enfileirar sincronizacao de altura dos paineis inferiores: %s",
                exc,
            )
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
            self._set_widget_fixed_height_safe(
                widget, target, f"painel inferior {type(widget).__name__}"
            )
        try:
            current_kind = getattr(self, "_current_tab_kind", None)
            if (
                current_kind == "filters"
                and hasattr(self, "adv_filters_group")
                and self.adv_filters_group is not None
            ):
                self._reorganize_advanced_filters_grid(self.adv_filters_group.width())
        except Exception as exc:
            logger.debug(
                "Falha ao reorganizar painel avancado apos sync de altura: %s", exc
            )

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

    def _ensure_responsavel_options_materialized(
        self, target_prefix: str | None = None, force: bool = False
    ):
        return ssa_gui_filters._ensure_responsavel_options_materialized(
            self, target_prefix, force
        )

    def _sync_responsavel_button_summaries(self, only_prefixes=None):
        return ssa_gui_filters._sync_responsavel_button_summaries(self, only_prefixes)

    def _attach_multiselect_menu(self, button, menu):
        return ssa_gui_filters._attach_multiselect_menu(self, button, menu)

    def _update_multiselect_button(
        self, button, checks, placeholder: str = "Selecionar", exclude_checks=None
    ):
        return ssa_gui_filters._update_multiselect_button(
            self, button, checks, placeholder, exclude_checks
        )

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

    def _sync_multiselect_checks(
        self, button, checks, selected, exclude_checks=None, exclude_selected=None
    ):
        return ssa_gui_filters._sync_multiselect_checks(
            self, button, checks, selected, exclude_checks, exclude_selected
        )

    def _build_advanced_filters_panel(self):
        return ssa_gui_filters._build_advanced_filters_panel(self)

    def _on_derivada_has_toggled(self, checked: bool):
        return ssa_gui_filters._on_derivada_has_toggled(self, checked)

    def _on_derivada_all_ste_toggled(self, checked: bool):
        _ = checked
        return None

    def _show_derivadas_popup(self):
        return ssa_gui_filters._show_derivadas_popup(self)

    def _build_derivadas_tree(
        self, df: pd.DataFrame, numero_col: str, derivada_col: str
    ):
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

    def _sort_responsavel_values(
        self, df_subset, values, resp_col: str, df_source=None
    ):
        return ssa_gui_filters._sort_responsavel_values(
            self, df_subset, values, resp_col, df_source=df_source
        )

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
        from gui.ssa import (
            gui_filters_advanced_ui as ssa_gui_filters_ui,
        )  # local fallback during split

        fallback_handler = getattr(
            ssa_gui_filters_ui, "_has_active_advanced_filters", None
        )
        if callable(fallback_handler):
            return fallback_handler(self, data)
        logger.warning(
            "Advanced filters activity handler is unavailable; assuming inactive filters."
        )
        return False

    def _apply_advanced_filters_from_ui(self, store_only: bool = False):
        return ssa_gui_filters._apply_advanced_filters_from_ui(self, store_only)

    def _parse_week(self, raw: str):
        return ssa_gui_filters._parse_week(self, raw)

    def _get_checked_values(self, source):
        return ssa_gui_filters._get_checked_values(self, source)

    def _sync_advanced_filter_ui(self):
        return ssa_gui_filters._sync_advanced_filter_ui(self)

    def _refresh_sector_menus(
        self, exec_vals, emis_vals, status_vals, filters, apply_cb
    ):
        return ssa_gui_filters._refresh_sector_menus(
            self, exec_vals, emis_vals, status_vals, filters, apply_cb
        )

    def _refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb):
        return ssa_gui_filters._refresh_year_menus(
            self, emissao_years, execucao_years, filters, apply_cb
        )

    def _refresh_priority_menus(
        self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
    ):
        return ssa_gui_filters._refresh_priority_menus(
            self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
        )

    def _refresh_reprogramacoes_menu(self, reprog_vals, filters, apply_cb):
        return ssa_gui_filters._refresh_reprogramacoes_menu(
            self, reprog_vals, filters, apply_cb
        )

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
            self._sync_advanced_executor_ui_from_active_filter()
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar combo rapido de setor executor apos carga: %s", exc
            )

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
        source_df = self.df_exibido
        if source_df is None or source_df.empty:
            return source_df
        if "num_reprogramacoes" not in source_df.columns:
            return source_df

        sort_keys = self._get_num_reprogramacoes_sort_keys()
        sort_direction = bool(ascending)
        ordered_index = sort_keys.sort_values(
            by=["__reprog_is_nan", "__reprog_num", "__reprog_txt"],
            ascending=[True, sort_direction, sort_direction],
            na_position="last",
            kind="mergesort",
        ).index
        sorted_keys = sort_keys.loc[ordered_index]
        self._last_num_reprog_sorted_keys = sorted_keys
        return source_df.loc[ordered_index]

    def _build_num_reprogramacoes_sort_keys(
        self, source_df: pd.DataFrame
    ) -> pd.DataFrame:
        raw_series = source_df["num_reprogramacoes"]
        raw_text = raw_series.astype("string").fillna("")
        numeric = pd.to_numeric(raw_series, errors="coerce").astype("Float64")
        missing_numeric_mask = numeric.isna()
        if bool(missing_numeric_mask.any()):
            extracted_source = raw_text[missing_numeric_mask]
            extracted = extracted_source.str.extract(r"(-?\d+)")[0]
            extracted_numeric = pd.to_numeric(extracted, errors="coerce").astype(
                "Float64"
            )
            numeric = numeric.copy()
            numeric.loc[missing_numeric_mask] = extracted_numeric
        return pd.DataFrame(
            {
                "__reprog_is_nan": numeric.isna(),
                "__reprog_num": numeric,
                "__reprog_txt": raw_text.str.casefold(),
            },
            index=source_df.index,
        )

    def _should_use_mixed_text_sort(self, column_name: str) -> bool:
        source_df = self.df_exibido
        if not isinstance(source_df, pd.DataFrame):
            return False
        if column_name not in source_df.columns:
            return False
        series = source_df[column_name]
        dtype = getattr(series, "dtype", None)
        return bool(
            pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)
        )

    def _build_mixed_text_sort_keys(
        self, source_series: pd.Series, ascending: bool
    ) -> pd.DataFrame:
        raw_text = source_series.astype("string").fillna("").str.strip()
        empty_mask = source_series.isna() | raw_text.eq("")
        normalized_numeric_text = raw_text.str.replace(",", ".", regex=False)
        is_numeric = normalized_numeric_text.str.fullmatch(
            r"[+-]?\d+(?:\.\d+)?"
        ).fillna(False)
        numeric_values = pd.to_numeric(
            normalized_numeric_text.where(is_numeric), errors="coerce"
        ).astype("Float64")

        first_char = raw_text.str.slice(0, 1)
        starts_alpha = first_char.str.isalpha().fillna(False)
        starts_alnum = first_char.str.isalnum().fillna(False)
        alpha_mask = (~empty_mask) & (~is_numeric) & starts_alpha
        symbol_mask = (~empty_mask) & (~is_numeric) & (~starts_alpha) & (~starts_alnum)
        other_text_mask = (~empty_mask) & (~is_numeric) & (~alpha_mask) & (~symbol_mask)

        symbol_rank = 0 if ascending else 3
        numeric_rank = 1 if ascending else 2
        alpha_rank = 2 if ascending else 1
        other_rank = 3 if ascending else 0
        bucket_order = pd.Series(other_rank, index=raw_text.index, dtype="Int64")
        bucket_order.loc[symbol_mask] = symbol_rank
        bucket_order.loc[is_numeric] = numeric_rank
        bucket_order.loc[alpha_mask] = alpha_rank
        bucket_order.loc[empty_mask] = 9

        normalized_text = raw_text.str.casefold()
        return pd.DataFrame(
            {
                "__mixed_is_empty": empty_mask,
                "__mixed_bucket_order": bucket_order,
                "__mixed_symbol_txt": normalized_text.where(symbol_mask),
                "__mixed_num": numeric_values,
                "__mixed_alpha_txt": normalized_text.where(alpha_mask),
                "__mixed_other_txt": normalized_text.where(other_text_mask),
            },
            index=source_series.index,
        )

    def _sort_mixed_text_column_robust(
        self, column_name: str, ascending: bool
    ) -> pd.DataFrame:
        source_df = self.df_exibido
        if source_df is None or source_df.empty:
            return source_df
        if column_name not in source_df.columns:
            return source_df

        sort_keys = self._build_mixed_text_sort_keys(
            source_df[column_name], ascending=ascending
        )
        sort_direction = bool(ascending)
        ordered_index = sort_keys.sort_values(
            by=[
                "__mixed_is_empty",
                "__mixed_bucket_order",
                "__mixed_symbol_txt",
                "__mixed_num",
                "__mixed_alpha_txt",
                "__mixed_other_txt",
            ],
            ascending=[
                True,
                True,
                sort_direction,
                sort_direction,
                sort_direction,
                sort_direction,
            ],
            na_position="last",
            kind="mergesort",
        ).index
        return source_df.loc[ordered_index]

    def _get_num_reprogramacoes_sort_keys(self) -> pd.DataFrame:
        source_df = self.df_exibido
        if not isinstance(source_df, pd.DataFrame):
            return pd.DataFrame(
                {
                    "__reprog_is_nan": pd.Series(dtype="bool"),
                    "__reprog_num": pd.Series(dtype="float64"),
                    "__reprog_txt": pd.Series(dtype="string"),
                }
            )
        if "num_reprogramacoes" not in source_df.columns:
            return pd.DataFrame(index=source_df.index)

        source_id = id(source_df)
        source_len = len(source_df.index)
        cache = getattr(self, "_num_reprog_sort_cache", None)
        keys_df = cache.get("keys_df") if isinstance(cache, dict) else None
        cache_source_len = (
            cache.get("source_len", -1) if isinstance(cache, dict) else -1
        )
        try:
            cache_source_len_int = int(cache_source_len)
        except (TypeError, ValueError):
            cache_source_len_int = -1
        cache_is_valid = (
            isinstance(cache, dict)
            and cache.get("source_id") == source_id
            and cache_source_len_int == source_len
            and isinstance(keys_df, pd.DataFrame)
            and keys_df.index.equals(source_df.index)
        )
        if not cache_is_valid:
            keys_df = self._build_num_reprogramacoes_sort_keys(source_df)
            self._num_reprog_sort_cache = {
                "source_id": source_id,
                "source_len": source_len,
                "keys_df": keys_df,
            }
        if not isinstance(keys_df, pd.DataFrame):
            keys_df = self._build_num_reprogramacoes_sort_keys(source_df)
        if not keys_df.index.equals(source_df.index):
            keys_df = self._build_num_reprogramacoes_sort_keys(source_df)
            self._num_reprog_sort_cache = {
                "source_id": source_id,
                "source_len": source_len,
                "keys_df": keys_df,
            }
        return keys_df

    def _reset_num_reprogramacoes_sort_cache(self) -> None:
        self._num_reprog_sort_cache = {
            "source_id": None,
            "source_len": 0,
            "keys_df": None,
        }

    def _prime_num_reprogramacoes_sort_cache(self) -> None:
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

    def _resolve_header_column_name(self, logical_index: int) -> str | None:
        if logical_index < 0 or self.table_widget.columnCount() == 0:
            return None
        current_columns = list(getattr(self, "_current_display_columns", []) or [])
        if not current_columns or logical_index >= len(current_columns):
            return None

        header = self.table_widget.horizontalHeader()
        if header is not None:
            try:
                visual_index = int(header.visualIndex(logical_index))
            except Exception as exc:
                logger.debug(
                    "Falha ao consultar visualIndex para logical_index=%s: %s",
                    logical_index,
                    exc,
                )
                visual_index = logical_index

            try:
                visual_order = ssa_gui_table._get_header_visual_column_order(self)
            except Exception as exc:
                logger.debug("Falha ao resolver ordem visual atual do header: %s", exc)
                visual_order = current_columns

            if 0 <= visual_index < len(visual_order):
                resolved = str(visual_order[visual_index] or "").strip()
                if resolved and resolved != "#":
                    return resolved

        resolved = str(current_columns[logical_index] or "").strip()
        if not resolved or resolved == "#":
            return None
        return resolved

    def on_header_clicked(self, logical_index: int):
        try:
            col_name = self._resolve_header_column_name(logical_index)
            if not col_name:
                return
            preserved_widths = self._capture_current_column_widths()
            self._skip_width_recompute_once = True

            # Alterna direçção ao clicar na mesma coluna
            if getattr(self, "sort_column", None) == col_name:
                self.sort_ascending = not getattr(self, "sort_ascending", True)
            else:
                self.sort_column = col_name
                self.sort_ascending = True

            # Ordena resultado filtrado atual e reinicia paginaçção
            try:
                if self.sort_column == "num_reprogramacoes":
                    self.df_exibido = self._sort_num_reprogramacoes_robust(
                        self.sort_ascending
                    )
                    sorted_keys = getattr(self, "_last_num_reprog_sorted_keys", None)
                    if isinstance(
                        sorted_keys, pd.DataFrame
                    ) and sorted_keys.index.equals(self.df_exibido.index):
                        self._num_reprog_sort_cache = {
                            "source_id": id(self.df_exibido),
                            "source_len": len(self.df_exibido.index),
                            "keys_df": sorted_keys,
                        }
                    else:
                        self._prime_num_reprogramacoes_sort_cache()
                    self._last_num_reprog_sorted_keys = None
                else:
                    if self._should_use_mixed_text_sort(self.sort_column):
                        self.df_exibido = self._sort_mixed_text_column_robust(
                            self.sort_column, self.sort_ascending
                        )
                    else:
                        self.df_exibido = self.df_exibido.sort_values(
                            by=self.sort_column,
                            ascending=self.sort_ascending,
                            na_position="last",
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
            current_page = max(
                1,
                min(
                    getattr(self.paginator, "current_page", 1),
                    getattr(self.paginator, "total_pages", 1),
                ),
            )
            self.display_current_page(current_page, update_details=False)
            self._restore_column_widths(preserved_widths)

            # Indicador visual na UI
            try:
                header = self.table_widget.horizontalHeader()
                order = (
                    Qt.SortOrder.AscendingOrder
                    if self.sort_ascending
                    else Qt.SortOrder.DescendingOrder
                )
                header.setSortIndicatorShown(True)
                header.setSortIndicator(logical_index, order)
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar indicador visual de ordenacao: %s", exc
                )
        except Exception as exc:
            logger.exception("Erro ao processar clique no cabecalho da tabela: %s", exc)

    # --- Filtro por coluna via clique direito no cabeçalho ---
    def _prompt_column_filter_term(self, full_name: str, initial_value: str = ""):
        if not QT_AVAILABLE or ColumnFilterDialog is None:
            return None
        try:
            if TSM_DEBUG_ENABLED:
                logger.warning(
                    "[TSM_DEBUG] open_column_filter_dialog column=%s has_initial=%s",
                    full_name,
                    bool(str(initial_value or "").strip()),
                )
            dialog = ColumnFilterDialog(
                full_name,
                str(initial_value or ""),
                hint_text=_COLUMN_FILTER_DIALOG_HINT,
                min_width=_COLUMN_FILTER_DIALOG_MIN_WIDTH,
                parent=self,
            )
            try:
                dialog._position_on_parent_screen()
            except Exception as exc:
                logger.debug(
                    "Falha ao posicionar dialogo de filtro por coluna na tela ativa: %s",
                    exc,
                )
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            if not accepted:
                return None
            return dialog.get_value()
        except Exception as exc:
            logger.debug("Falha ao abrir dialogo de filtro por coluna: %s", exc)
            return None

    def show_header_context_menu(self, pos):
        try:
            header = self.table_widget.horizontalHeader()
            logical_index = header.logicalIndexAt(pos)
            col_name = self._resolve_header_column_name(logical_index)
            if not col_name:
                return

            menu = QMenu(self)
            full_name = self._expand_column_alias_for_filter(col_name)
            apply_action = QAction(f"Filtrar '{full_name}'...", self)
            clear_action = QAction("Limpar filtro desta coluna", self)
            clear_all_action = QAction("Limpar todos filtros de colunas", self)
            best_fit_visible_action = QAction("Best fit colunas visiveis", self)
            show_all_affinity_action = QAction("Exibir todas colunas (afinidade)", self)

            def _apply():
                term = self._prompt_column_filter_term(
                    full_name,
                    str(self._active_column_filters.get(col_name, "")).strip(),
                )
                if term is not None:
                    normalized_term = str(term).strip()
                    if (
                        str(self._active_column_filters.get(col_name, "")).strip()
                        != normalized_term
                    ):
                        self._safe_store_last_filter_state(
                            "header_context_apply_column_filter"
                        )
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
            show_all_affinity_action.triggered.connect(
                self._show_all_columns_by_affinity
            )

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
            if TSM_DEBUG_ENABLED:
                probes = getattr(self, "_tsm_debug_widget_roles", None)
                if isinstance(probes, dict):
                    role = probes.get(id(obj))
                    event_name = _TSM_DEBUG_EVENT_NAMES.get(event.type())
                    if role and event_name:
                        self._log_tsm_debug(event_name, widget_role=role, obj=obj)
            header = self.table_widget.horizontalHeader()
            if obj is header:
                et = event.type()
                if et == QEvent.Type.ContextMenu:
                    self.show_header_context_menu(event.pos())
                    return True
                # Qt6: MouseButtonPress com botção direito
                if et == QEvent.Type.MouseButtonPress:
                    btn = getattr(event, "button", lambda: None)()
                    if btn == Qt.MouseButton.RightButton:
                        # Compatável com position() (Qt6) e pos()
                        pos = getattr(event, "position", None)
                        if callable(pos):
                            p = pos().toPoint()
                        else:
                            p = event.pos()
                        self.show_header_context_menu(p)
                        return True
            details_viewport = getattr(self, "_details_text_viewport", None)
            if obj is details_viewport and event.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonDblClick,
            ):
                pos = getattr(event, "position", None)
                if callable(pos):
                    point = pos().toPoint()
                else:
                    point = event.pos()
                details_text = getattr(self, "details_text", None)
                anchor = ""
                if details_text is not None:
                    try:
                        anchor = str(details_text.anchorAt(point) or "")
                    except Exception:
                        anchor = ""
                if anchor.startswith("copy-ssa:"):
                    target = anchor[len("copy-ssa:") :].strip().lstrip("/")
                    if target:
                        self._copy_ssa_to_clipboard(target)
                        return True
        except Exception as exc:
            logger.debug("Falha no eventFilter do header da tabela: %s", exc)
        return super().eventFilter(obj, event)

    # --- Helpers: painel e aplicaçção dos filtros por coluna ---
    def toggle_theme_menu(self):
        if TSM_DEBUG_ENABLED:
            logger.warning("[TSM_DEBUG] open_theme_dialog")
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
        self.visible_columns = list(new_columns)
        if hasattr(self, "column_selector") and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(self.visible_columns)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar colunas selecionadas no selector: %s", exc
                )
        # Reexibe a pãgina atual com as novas colunas
        self.display_current_page(self.paginator.current_page, update_details=False)
        try:
            self._persist_visible_columns_order()
        except Exception as exc:
            logger.debug(
                "Falha ao persistir estado de colunas visiveis apos alteracao: %s", exc
            )

    def _persist_visible_columns_order(self) -> None:
        ordered_visible_columns = []
        seen_visible = set()
        for column_name in list(self.visible_columns):
            if not isinstance(column_name, str):
                continue
            cleaned = column_name.strip()
            if not cleaned or cleaned == "#" or cleaned in seen_visible:
                continue
            seen_visible.add(cleaned)
            ordered_visible_columns.append(cleaned)

        available_columns = []
        selector = getattr(self, "column_selector", None)
        if selector is not None:
            available_columns.extend(getattr(selector, "available_columns", []) or [])
        available_columns.extend(getattr(self, "default_columns", []) or [])
        available_columns.extend(GUI_MAIN_PREFERENCES.get("display_columns", []) or [])
        available_columns.extend(GUI_MAIN_PREFERENCES.get("hidden_columns", []) or [])
        display_map = getattr(self, "display_map", None)
        if isinstance(display_map, dict):
            available_columns.extend(display_map.keys())

        known_columns = []
        seen_known = set()
        for column_name in available_columns:
            if not isinstance(column_name, str):
                continue
            cleaned = column_name.strip()
            if not cleaned or cleaned == "#" or cleaned in seen_known:
                continue
            seen_known.add(cleaned)
            known_columns.append(cleaned)

        hidden_columns = [
            column_name
            for column_name in known_columns
            if column_name not in seen_visible
        ]

        current_display = GUI_MAIN_PREFERENCES.setdefault("display_columns", [])
        current_hidden = GUI_MAIN_PREFERENCES.setdefault("hidden_columns", [])
        if (
            current_display == ordered_visible_columns
            and current_hidden == hidden_columns
        ):
            return
        GUI_MAIN_PREFERENCES["display_columns"] = list(ordered_visible_columns)
        GUI_MAIN_PREFERENCES["hidden_columns"] = list(hidden_columns)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        snapshot = copy.deepcopy(GUI_MAIN_PREFERENCES)
        snapshot["display_columns"] = list(ordered_visible_columns)
        snapshot["hidden_columns"] = list(hidden_columns)
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
                snapshot,
                indent=2,
                ensure_ascii=False,
            )
        except Exception as exc:
            logger.warning(
                "Falha ao persistir nova ordem de colunas apos drag no header: %s", exc
            )

    def _on_header_section_moved(
        self,
        logical_index: int,
        old_visual_index: int,
        new_visual_index: int,
    ) -> None:
        _ = old_visual_index
        _ = new_visual_index
        if bool(getattr(self, "_header_order_sync_suspended", False)):
            return
        header = self.table_widget.horizontalHeader()
        if header is None:
            return
        current_columns = list(getattr(self, "_current_display_columns", []) or [])
        if (
            not current_columns
            or logical_index < 0
            or logical_index >= len(current_columns)
        ):
            return
        if current_columns[0] == "#" and header.visualIndex(0) != 0:
            self._skip_width_recompute_once = True
            self.display_current_page(self.paginator.current_page, update_details=False)
            return
        ordered_columns = ssa_gui_table._get_header_visual_column_order(self)
        if not ordered_columns:
            return
        ordered_visible_columns = [col for col in ordered_columns if col != "#"]
        if not ordered_visible_columns:
            return
        current_visible_columns = list(getattr(self, "visible_columns", []) or [])
        missing_visible_columns = [
            column_name
            for column_name in current_visible_columns
            if column_name not in ordered_visible_columns
        ]
        merged_visible_columns = ordered_visible_columns + missing_visible_columns
        if (
            not merged_visible_columns
            or merged_visible_columns == current_visible_columns
        ):
            return
        preserved_widths = self._capture_current_column_widths()
        self._current_display_columns = list(ordered_columns)
        self.visible_columns = merged_visible_columns
        if hasattr(self, "column_selector") and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(self.visible_columns)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar selector apos reorder de colunas: %s", exc
                )
        try:
            self._persist_visible_columns_order()
        except Exception as exc:
            logger.debug("Falha ao persistir nova ordem de colunas apos drag: %s", exc)
        self._skip_width_recompute_once = True
        self.display_current_page(self.paginator.current_page, update_details=False)
        self._restore_column_widths(preserved_widths)

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

    def _populate_quick_setor_executor_combo(
        self, combo, selected_value: str = ""
    ) -> None:
        if combo is None:
            return
        options = self._collect_setor_executor_values_for_combo()
        selected = str(selected_value or "").strip()
        self._quick_setor_executor_syncing = True
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Todos", "")
            for value in options:
                combo.addItem(value, value)
            idx = combo.findData(selected)
            if idx < 0:
                idx = 0
            combo.setCurrentIndex(idx)
            self._update_quick_setor_executor_combo_display(combo)
        except Exception as exc:
            logger.debug("Falha ao popular combo rapido de setor executor: %s", exc)
        finally:
            try:
                combo.blockSignals(False)
            except Exception as exc:
                logger.debug(
                    "Falha ao reativar sinais do combo rapido de setor executor: %s",
                    exc,
                )
            self._quick_setor_executor_syncing = False

    def _update_quick_setor_executor_combo_display(self, combo) -> None:
        if combo is None:
            return
        value = ""
        try:
            value = str(combo.currentData() or "").strip()
        except Exception as exc:
            logger.debug(
                "Falha ao ler valor atual do combo rapido de setor executor: %s", exc
            )
        display_text = value if value else "Todos"
        try:
            line_edit = combo.lineEdit()
            if line_edit is not None:
                line_edit.setText(display_text)
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar texto exibido do combo rapido de setor executor: %s",
                exc,
            )

    @staticmethod
    def _split_filter_csv_values(raw_value: str) -> list[str]:
        values = []
        seen = set()
        for part in str(raw_value or "").split(","):
            item = str(part or "").strip()
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(item)
        return values

    @staticmethod
    def _normalize_filter_sequence_values(raw_values) -> list[str]:
        values = []
        seen = set()
        for raw in raw_values or []:
            item = str(raw or "").strip()
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(item)
        return values

    def _sync_advanced_executor_filter_from_active_filters(
        self, *, clear_exclude: bool = False
    ) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_raw = str(active_filters.get("setor_executor", "") or "").strip()
        selected_values = self._split_filter_csv_values(selected_raw)
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        if selected_values:
            advanced_filters["setor_executor"] = selected_values
            if clear_exclude:
                advanced_filters["setor_executor_exclude_values"] = []
        else:
            advanced_filters.pop("setor_executor", None)
            if clear_exclude and not advanced_filters.get(
                "setor_executor_exclude_values"
            ):
                advanced_filters.pop("setor_executor_exclude_values", None)
        self._advanced_filters = advanced_filters
        self._advanced_filters_active = self._has_active_advanced_filters(
            advanced_filters
        )
        self._adv_options_dirty = True
        self._mark_responsavel_dirty()

    def _sync_active_executor_filter_from_advanced_filters(
        self, *, clear_when_missing: bool = False
    ) -> None:
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        selected_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        if selected_values:
            active_filters["setor_executor"] = ", ".join(selected_values)
        elif clear_when_missing:
            active_filters.pop("setor_executor", None)
        self._active_column_filters = active_filters

    def _sync_advanced_executor_ui_from_active_filter(self) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        selected_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        exclude_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor_exclude_values")
        )
        if not selected_values and not exclude_values:
            selected_raw = str(active_filters.get("setor_executor", "") or "").strip()
            selected_values = self._split_filter_csv_values(selected_raw)
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            if ctx.get("tab_kind") != "filters":
                continue
            button = ctx.get("adv_executor_button")
            checks = ctx.get("adv_executor_checks")
            exclude_checks = ctx.get("adv_executor_exclude_checks")
            if button is None:
                continue
            if checks:
                self._sync_multiselect_checks(
                    button,
                    checks,
                    selected_values,
                    exclude_checks,
                    exclude_values,
                )
            else:
                if selected_values and exclude_values:
                    button.setText(
                        f"Incluir: {', '.join(selected_values)} | Diferente: {', '.join(exclude_values)}"
                    )
                elif selected_values:
                    button.setText(f"Incluir: {', '.join(selected_values)}")
                elif exclude_values:
                    button.setText(f"Diferente: {', '.join(exclude_values)}")
                else:
                    button.setText("Selecionar")

    def _sync_quick_setor_executor_combo_from_filters(self) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_value = str(active_filters.get("setor_executor", "") or "").strip()
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        advanced_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        advanced_excludes = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor_exclude_values")
        )
        if not selected_value and len(advanced_values) == 1 and not advanced_excludes:
            selected_value = advanced_values[0]
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
            try:
                has_existing_options = combo.count() > 0
            except Exception:
                has_existing_options = False
            if has_existing_options:
                try:
                    idx = combo.findData(selected_value)
                except Exception:
                    idx = -1
                if idx >= 0:
                    self._quick_setor_executor_syncing = True
                    try:
                        combo.blockSignals(True)
                        combo.setCurrentIndex(idx)
                        self._update_quick_setor_executor_combo_display(combo)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao sincronizar selecao do combo rapido de setor executor: %s",
                            exc,
                        )
                    finally:
                        try:
                            combo.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais na sincronizacao do combo rapido de setor executor: %s",
                                exc,
                            )
                        self._quick_setor_executor_syncing = False
                    continue
            self._populate_quick_setor_executor_combo(
                combo, selected_value=selected_value
            )

    def _refresh_quick_setor_executor_options(self) -> None:
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_value = str(active_filters.get("setor_executor", "") or "").strip()
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        advanced_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        advanced_excludes = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor_exclude_values")
        )
        if not selected_value and len(advanced_values) == 1 and not advanced_excludes:
            selected_value = advanced_values[0]
        if "," in selected_value:
            selected_value = ""
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            combo = ctx.get("quick_setor_executor_combo")
            if combo is None:
                continue
            self._populate_quick_setor_executor_combo(
                combo, selected_value=selected_value
            )

    def _on_quick_setor_executor_changed(self, combo) -> None:
        if bool(getattr(self, "_quick_setor_executor_syncing", False)):
            return
        selected = ""
        try:
            selected = str(combo.currentData() or "").strip()
        except Exception as exc:
            logger.debug(
                "Falha ao ler valor do combo rapido de setor executor: %s", exc
            )
        self._safe_store_last_filter_state("quick_setor_executor_changed")
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        if selected:
            active_filters["setor_executor"] = selected
        else:
            active_filters.pop("setor_executor", None)
        self._update_quick_setor_executor_combo_display(combo)
        self._active_column_filters = active_filters
        self._sync_advanced_executor_filter_from_active_filters(
            clear_exclude=bool(selected)
        )
        self._sync_advanced_filter_ui()
        if hasattr(self, "_schedule_sector_options_refresh"):
            self._schedule_sector_options_refresh()
        self._mark_profile_as_custom()
        self._build_column_filters_panel()
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
            available = list(
                dict.fromkeys(
                    available + [col for col in canonical if col not in available]
                )
            )
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
        if width_manager is None or not hasattr(
            width_manager, "capture_current_column_widths"
        ):
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

    def display_current_page(self, page_number, *, update_details=True):
        return ssa_gui_table.display_current_page(
            self, page_number, update_details=update_details
        )

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

    def _on_header_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ):
        return ssa_gui_table._on_header_section_resized(
            self, logical_index, old_size, new_size
        )

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

    @staticmethod
    def _build_sam_ssa_url(numero_ssa: str) -> str:
        return SAM_SSA_PUBLIC_VIEW_URL.format(numero_ssa=str(numero_ssa).strip())

    def _open_url_in_browser(self, url: str, *, success_status: str) -> bool:
        safe_url = str(url or "").strip()
        if not safe_url:
            return False
        try:
            ok = bool(QDesktopServices.openUrl(QUrl(safe_url)))
        except Exception as exc:
            logger.warning("Falha ao abrir URL externa %s: %s", safe_url, exc)
            ok = False
        if ok and hasattr(self, "status_label"):
            self.status_label.setText(success_status)
        return ok

    def _open_sam_home(self):
        opened = self._open_url_in_browser(
            SAM_HOME_URL,
            success_status="Status: SAM aberto no navegador.",
        )
        if not opened and not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(self, "Erro", "Falha ao abrir o SAM no navegador.")
        return opened

    def _open_sam_ssa(self, numero_ssa: str):
        safe_numero = self._normalize_ssa_value(numero_ssa)
        if not safe_numero:
            return False
        opened = self._open_url_in_browser(
            self._build_sam_ssa_url(safe_numero),
            success_status=f"Status: SSA {safe_numero} aberta no SAM.",
        )
        if not opened and not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(
                self,
                "Erro",
                f"Falha ao abrir a SSA {safe_numero} no navegador.",
            )
        return opened

    def _copy_ssa_to_clipboard(
        self, numero_ssa: str, *, status_text: str = "Status: Numero da SSA copiado."
    ) -> bool:
        safe_numero = self._normalize_ssa_value(numero_ssa)
        if not safe_numero:
            return False
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(safe_numero)
        if hasattr(self, "status_label"):
            self.status_label.setText(status_text)
        return True

    def on_table_cell_clicked(self, row: int, column: int):
        if column != 0:
            return
        series = self._get_series_from_row(row)
        if series is None:
            return
        numero_ssa = series.get("numero_ssa")
        self._open_sam_ssa(numero_ssa)

    def on_table_double_click(self, index):
        """Mostra janela de detalhes formatada ao duplo clique."""
        clicked_column_name = ""
        try:
            clicked_column = int(index.column())
        except Exception:
            clicked_column = -1
        try:
            display_columns = getattr(self, "_current_display_columns", None)
            if isinstance(display_columns, list) and 0 <= clicked_column < len(
                display_columns
            ):
                clicked_column_name = str(display_columns[clicked_column] or "")
        except Exception:
            clicked_column_name = ""

        row = index.row()
        index_item = self.table_widget.item(row, 0)
        if not index_item:
            return
        original_index = index_item.data(Qt.ItemDataRole.UserRole)
        if original_index is None or not (0 <= original_index < len(self.df_exibido)):
            QMessageBox.information(
                self,
                "Info",
                "Nao foi possivel encontrar os dados detalhados para esta linha.",
            )
            return

        series = self.df_exibido.iloc[int(original_index)]
        numero_ssa = series.get("numero_ssa")
        if clicked_column_name == "numero_ssa":
            self._copy_ssa_to_clipboard(numero_ssa)
            return
        self._open_details_dialog_for_ssa(numero_ssa, series=series)

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

    def _jump_to_ssa(self, numero_ssa, **kwargs):
        return ssa_gui_details._jump_to_ssa(self, numero_ssa, **kwargs)

    def _on_details_anchor_clicked(self, url):
        return ssa_gui_details._on_details_anchor_clicked(self, url)

    def _open_details_dialog_for_ssa(self, numero_ssa, series=None):
        return ssa_gui_details._open_details_dialog_for_ssa(
            self, numero_ssa, series=series
        )

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
                derived_list = (
                    self._get_derivadas_for_ssa(numero_ssa) if numero_ssa else []
                )
                if derivada_de:
                    origem_action = QAction("Ir para SSA origem", self)
                    origem_action.triggered.connect(
                        lambda: self._jump_to_ssa(derivada_de)
                    )
                    cast(Any, menu).addAction(origem_action)
                if derived_list:
                    label = f"Mostrar derivadas ({len(derived_list)})"
                    derivadas_action = QAction(label, self)
                    derivadas_action.triggered.connect(
                        lambda: self._filter_by_derivadas(numero_ssa)
                    )
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

                    remove_column_action = QAction(
                        f"Remover Coluna '{column_name}'", self
                    )
                    remove_column_action.triggered.connect(
                        lambda: self.remove_column_by_index(column)
                    )
                    cast(Any, menu).addAction(remove_column_action)

                    auto_fit_action = QAction(f"Ajustar Largura '{column_name}'", self)
                    auto_fit_action.triggered.connect(
                        lambda: self.auto_fit_column(column)
                    )
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
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar lista", "", "Text Files (*.txt)"
            )
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
        """Remove uma coluna especifica baseada no indice da tabela."""
        if column_index <= 0:
            return
        internal_index = column_index - 1  # Coluna 0 da tabela e '#'
        if internal_index < 0 or internal_index >= len(self.visible_columns):
            return
        internal_column = self.visible_columns[internal_index]
        if internal_column in self.visible_columns:
            self.visible_columns.remove(internal_column)
            self.on_columns_changed(self.visible_columns)

    def _compute_best_fit_width_for_column(
        self, column_index: int, sample_limit: int = 2000
    ) -> int | None:
        if column_index < 0 or column_index >= self.table_widget.columnCount():
            return None
        cols = getattr(self, "_current_display_columns", None)
        if not cols or column_index >= len(cols):
            return None
        col_name = cols[column_index]
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        header_text = (
            str(header_item.text()) if header_item is not None else str(col_name)
        )
        width_manager = getattr(self, "width_manager", None)
        font_metrics = self.table_widget.fontMetrics()
        series = None
        if (
            self.df_exibido is not None
            and not self.df_exibido.empty
            and col_name in self.df_exibido.columns
        ):
            series = self.df_exibido[col_name]
        if width_manager is not None and hasattr(
            width_manager, "compute_best_fit_width"
        ):
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
        arquivo_menu.addAction(load_action)

        rescan_diff_action = QAction("Atualizar Dados", self)
        rescan_diff_action.triggered.connect(self.rescan_diff_data)
        arquivo_menu.addAction(rescan_diff_action)

        export_action = QAction("Exportar lista", self)
        export_action.triggered.connect(self._export_current_list_txt)
        arquivo_menu.addAction(export_action)

        close_action = QAction("Sair", self)
        close_action.triggered.connect(self.close)
        arquivo_menu.addAction(close_action)

        import_action = QAction("Importar XLS/XLSX externo", self)
        import_action.triggered.connect(self.import_external_excel_files)
        importacao_menu.addAction(import_action)

        rescan_diff_action = QAction("Atualizar Dados", self)
        rescan_diff_action.triggered.connect(self.rescan_diff_data)
        importacao_menu.addAction(rescan_diff_action)

        rescan_full_action = QAction("Reescaneamento Completo", self)
        rescan_full_action.triggered.connect(self.rescan_full_data)
        importacao_menu.addAction(rescan_full_action)

        open_docs_action = QAction("Abrir Pasta de Arquivos", self)
        set_status_tip = getattr(open_docs_action, "setStatusTip", None)
        if callable(set_status_tip):
            set_status_tip(
                f"Pasta atual de entrada: {os.path.join(project_root, 'docs_entrada')}"
            )
        open_docs_action.triggered.connect(self.open_docs_folder)
        importacao_menu.addAction(open_docs_action)

        open_processadas_action = QAction("Abrir Pasta Arquivos Processados", self)
        open_processadas_action.triggered.connect(self.open_processadas_folder)
        importacao_menu.addAction(open_processadas_action)

        open_nosurvivor_action = QAction("Abrir Pasta Arquivos Redundantes", self)
        open_nosurvivor_action.triggered.connect(self.open_nosurvivor_folder)
        importacao_menu.addAction(open_nosurvivor_action)

        consolidate_action = QAction("Consolidar arquivos de entrada", self)
        consolidate_action.triggered.connect(self.consolidate_input_files)
        importacao_menu.addAction(consolidate_action)

        rescan_prompt_action = QAction("Reescanear", self)
        rescan_prompt_action.triggered.connect(self.rescan_data)
        db_menu.addAction(rescan_prompt_action)

        derivadas_action = QAction("Atualizar derivadas", self)
        derivadas_action.triggered.connect(self.update_derivadas_from_sources)
        db_menu.addAction(derivadas_action)

        load_other_db_action = QAction("Carregar outro DB", self)
        load_other_db_action.triggered.connect(self.load_other_database)
        db_menu.addAction(load_other_db_action)

        vacuum_analyze_action = QAction("Compactar DB", self)
        vacuum_analyze_action.triggered.connect(self.run_vacuum_analyze)
        db_menu.addAction(vacuum_analyze_action)

        open_settings_action = QAction("Abrir arquivo de opcoes", self)
        open_settings_action.triggered.connect(self.open_settings_file_with_backup)
        opcoes_menu.addAction(open_settings_action)

        reset_settings_action = QAction("Restaurar opcoes padrao", self)
        reset_settings_action.triggered.connect(self.reset_settings_to_defaults)
        opcoes_menu.addAction(reset_settings_action)

        hard_reset_filters_action = QAction("Limpar Filtros", self)
        hard_reset_filters_action.triggered.connect(self._hard_reset_filters_state)
        opcoes_menu.addAction(hard_reset_filters_action)

        alignment_menu = opcoes_menu.addMenu("Alinhamento da tabela")
        current_alignment = str(
            GUI_MAIN_PREFERENCES.get("gui_settings", {})
            .get(
                "table_cell_alignment",
                _DEFAULT_TABLE_CELL_ALIGNMENT,
            )
            .strip()
            .lower()
        )
        self._table_cell_alignment_actions = {}
        for alignment_name, label in _TABLE_CELL_ALIGNMENT_LABELS.items():
            alignment_action = QAction(label, self)
            cast(Any, alignment_action).setCheckable(True)
            cast(Any, alignment_action).setChecked(alignment_name == current_alignment)
            cast(Any, alignment_action).triggered.connect(
                lambda _checked=False,
                name=alignment_name: self._apply_table_cell_alignment_preference(name)
            )
            alignment_menu.addAction(alignment_action)
            self._table_cell_alignment_actions[alignment_name] = alignment_action

        theme_action = QAction("Selecionar Tema", self)
        theme_action.triggered.connect(self.toggle_theme_menu)
        opcoes_menu.addAction(theme_action)

        install_action = QAction("Instalacao", self)
        install_action.triggered.connect(self.open_installation_guide)
        ajuda_menu.addAction(install_action)

        help_action = QAction("Ajuda", self)
        help_action.triggered.connect(self.show_filter_help)
        ajuda_menu.addAction(help_action)

        about_handler = getattr(self, "show_about_dialog", None)
        if callable(about_handler):
            about_action = QAction("Sobre", self)
            about_action.triggered.connect(about_handler)
            ajuda_menu.addAction(about_action)

    def import_external_excel_files(self):
        """Enfileira importacao externa; o staging roda em background."""
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos Excel para importar",
            os.path.expanduser("~"),
            "Arquivos Excel (*.xlsx *.xls);;Todos os Arquivos (*)",
        )

        if not selected_files:
            return {
                "selected": 0,
                "copied": 0,
                "skipped": 0,
                "failed": 0,
                "unsupported": 0,
                "staged": 0,
                "result_scope": "queue",
                "db_updated": False,
                "db_update_requested": False,
                "queued": False,
            }

        selected_count = len(selected_files)
        copied = 0
        skipped = 0
        failed = 0
        unsupported = 0
        queued = False
        safe_selected_files: list[str] = []
        for raw_source in selected_files:
            source = str(raw_source or "").strip()
            if not source:
                skipped += 1
                continue
            try:
                validated_source = SSAMainWindow._validate_local_open_target(
                    source,
                    must_exist=True,
                    expect_dir=False,
                )
            except Exception as exc:
                logger.warning(
                    "Importacao externa rejeitou caminho invalido '%s': %s",
                    source,
                    exc,
                )
                failed += 1
                continue
            if not validated_source.casefold().endswith((".xlsx", ".xls")):
                logger.info(
                    "Importacao externa ignorou arquivo nao suportado pelo pipeline: %s",
                    validated_source,
                )
                unsupported += 1
                continue
            safe_selected_files.append(validated_source)
        try:
            from gui.widgets import RescanProgressDialog
            from gui.workers import RescanWorker

            if safe_selected_files:
                ssa_gui_workers.rescan_data(
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
                    rescan_mode="explicit",
                    source_files=tuple(safe_selected_files),
                    db_path=DB_PATH,
                    operation_label="Importacao externa",
                    reload_on_success=True,
                    operation_kind="import",
                )
                queued = True
        except Exception as exc:
            logger.warning("Falha ao iniciar importacao externa: %s", exc)
            failed += len(safe_selected_files)

        if hasattr(self, "status_label") and not queued:
            summary = (
                f"Status: Importacao externa preparada - selecionados={selected_count}, "
                f"falhas={failed}, "
                f"enfileirada=nao."
            )
            self.status_label.setText(summary)

        return {
            "selected": selected_count,
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "unsupported": unsupported,
            "staged": len(safe_selected_files) if queued else 0,
            "result_scope": "queue",
            "db_updated": False,
            "db_update_requested": queued,
            "queued": queued,
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
        if os.path.basename(normalized).startswith("-"):
            raise ValueError(
                "Caminho inicia com '-' e pode ser interpretado como opcao de comando."
            )
        if must_exist and not os.path.exists(normalized):
            raise FileNotFoundError(f"Caminho nao encontrado: {normalized}")
        if (
            expect_dir is True
            and os.path.exists(normalized)
            and not os.path.isdir(normalized)
        ):
            raise ValueError(f"Era esperado diretorio: {normalized}")
        if (
            expect_dir is False
            and os.path.exists(normalized)
            and os.path.isdir(normalized)
        ):
            raise ValueError(f"Era esperado arquivo: {normalized}")
        return normalized

    @staticmethod
    def _resolve_platform_open_command() -> str:
        preferred_paths: list[str] = []
        path_module = os.path
        if sys.platform.startswith("win"):
            windir = os.environ.get("WINDIR", r"C:\Windows")
            preferred_paths.append(os.path.join(windir, "explorer.exe"))
            cmd = "explorer"
            path_module = ntpath
        elif sys.platform == "darwin":
            preferred_paths.append("/usr/bin/open")
            cmd = "open"
            path_module = posixpath
        else:
            preferred_paths.extend(("/usr/bin/xdg-open", "/bin/xdg-open"))
            cmd = "xdg-open"
            path_module = posixpath
        for preferred in preferred_paths:
            preferred_abs = path_module.abspath(preferred)
            if path_module.isabs(preferred_abs) and os.path.isfile(preferred_abs):
                return preferred_abs
        resolved = shutil.which(cmd)
        if not resolved:
            raise RuntimeError(f"Comando indisponivel para abrir recurso: {cmd}")
        resolved_abs = path_module.abspath(resolved)
        if not path_module.isabs(resolved_abs):
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
            return {
                "opened": False,
                "backup_created": False,
                "settings_path": settings_path,
            }

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
            return {
                "opened": False,
                "backup_created": True,
                "settings_path": settings_path,
            }

        opened = False
        try:
            if QT_AVAILABLE:
                opened = bool(
                    QDesktopServices.openUrl(QUrl.fromLocalFile(safe_settings_path))
                )
            if not opened:
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen([resolved, safe_settings_path], shell=False)
                opened = True
        except Exception as exc:
            logger.warning("Falha ao abrir settings para edicao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao abrir opcoes: {exc}")
            return {
                "opened": False,
                "backup_created": True,
                "settings_path": settings_path,
            }

        if hasattr(self, "status_label"):
            self.status_label.setText(
                "Status: Opcoes abertas no editor externo (arquivo principal)."
            )
        return {
            "opened": opened,
            "backup_created": True,
            "settings_path": safe_settings_path,
        }

    def reset_settings_to_defaults(self):
        """Restaura settings.json para os valores padrao com backup previo."""
        settings_path = self._resolve_settings_file_path()
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        try:
            from core import config_manager

            resolver = getattr(config_manager, "_resolve_config_path", None)
            if callable(resolver):
                default_settings_path = str(
                    resolver(config_manager.DEFAULT_SETTINGS_FILE)
                )
            else:
                default_settings_path = os.path.join(
                    project_root, "config", "default_settings.json"
                )
            if not os.path.exists(default_settings_path):
                config_manager.ensure_default_settings(fail_fast=False)
            with open(default_settings_path, "r", encoding="utf-8") as handle:
                default_settings = json.load(handle)
        except Exception as exc:
            logger.warning("Falha ao carregar defaults de opcoes: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self, "Erro", f"Falha ao carregar opcoes padrao: {exc}"
                )
            return {"ok": False, "reason": "load_default_failed"}

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Confirmar restauracao",
                (f"Restaurar opcoes padrao agora? Isso sobrescreve {settings_path}."),
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
                QMessageBox.warning(
                    self, "Erro", f"Falha ao criar backup de opcoes: {exc}"
                )
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

    def consolidate_input_files(self):
        """Enfileira consolidacao de docs_entrada para processadas em background."""
        queued = False
        failed = 0
        try:
            from gui.widgets import RescanProgressDialog
            from gui.workers import RescanWorker

            ssa_gui_workers.rescan_data(
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
                operation_label="Consolidacao de arquivos",
                reload_on_success=False,
                operation_kind="consolidate",
            )
            queued = True
        except Exception as exc:
            logger.warning("Falha ao iniciar consolidacao de arquivos: %s", exc)
            failed = 1

        if hasattr(self, "status_label") and not queued:
            self.status_label.setText(
                "Status: Falha ao enfileirar consolidacao de arquivos."
            )
        return {
            "moved": 0,
            "nosurvivor": 0,
            "pending": 0,
            "failed": failed,
            "queued": queued,
            "result_scope": "queue",
        }

    def rescan_data(self):
        """Reprocessa os arquivos Excel com feedback visual em tempo real."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

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
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def rescan_diff_data(self):
        """Reprocessa somente arquivos alterados por hash (modo diff)."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

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
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def rescan_full_data(self):
        """Reprocessa tudo recriando DB candidato (modo full)."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

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
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def open_docs_folder(self):
        """Abre a pasta docs_entrada no explorador de arquivos (nao bloqueante)."""
        docs_path = os.path.join(project_root, "docs_entrada")
        if hasattr(self, "status_label"):
            self.status_label.setText(f"Status: Pasta de entrada: {docs_path}")
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
        doc_candidates = list(_iter_installation_guide_candidates())
        doc_path = next((path for path in doc_candidates if os.path.exists(path)), "")
        if not os.path.exists(doc_path):
            missing_reference = (
                doc_candidates[0]
                if doc_candidates
                else os.path.abspath(
                    os.path.join(
                        project_root, "docs", "GUIA_MIGRACAO_NOVA_INSTALACAO.md"
                    )
                )
            )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Guia de instalacao nao encontrado: {missing_reference}",
                )
            return {"opened": False, "reason": "missing_file"}
        try:
            safe_doc_path = SSAMainWindow._validate_local_open_target(
                doc_path,
                must_exist=True,
                expect_dir=False,
            )
            opened = False
            if QT_AVAILABLE:
                safe_doc_url = QUrl.fromLocalFile(safe_doc_path)
                opened = bool(QDesktopServices.openUrl(safe_doc_url))
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
                QMessageBox.warning(
                    self, "Erro", f"Falha ao abrir guia de instalacao: {exc}"
                )
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
            self.status_label.setText(
                "Status: Compactando DB e atualizando estatisticas..."
            )

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
                self.status_label.setText(
                    "Status: DB compactado e estatisticas atualizadas."
                )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(
                    self, "Sucesso", "Compactacao e atualizacao do DB concluidas."
                )
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
            logger.warning(
                "Caminho de pasta invalido para abertura (%s): %s", folder_label, exc
            )
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
            logger.warning(
                "Caminho de pasta invalido apos validacao (%s): %s", folder_label, exc
            )
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
                QMessageBox.warning(
                    self, "Erro", f"Erro ao abrir pasta: {fallback_exc}"
                )

    def _list_special_derivadas_sheets(self) -> list[str]:
        docs_path = os.path.join(project_root, "docs_entrada")
        if not os.path.isdir(docs_path):
            return []
        files: list[str] = []
        for base_name in os.listdir(docs_path):
            lowered = str(base_name).strip().casefold()
            if lowered.startswith("ssas derivadas e relacionadas") and lowered.endswith(
                ".xlsx"
            ):
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
                        for row in conn.execute(
                            f'PRAGMA table_info("{name}")'
                        ).fetchall()
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
        db_path = DB_PATH
        if not db_path or not os.path.exists(db_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            QMessageBox.warning(self, "Erro", f"Banco nao encontrado: {db_path}")
            return

        special_files = self._list_special_derivadas_sheets()
        table_name = self._resolve_derivadas_table_name(db_path)
        previous_status = (
            self.status_label.text() if hasattr(self, "status_label") else ""
        )
        previous_progress_visible = (
            bool(self.progress_bar.isVisible())
            if hasattr(self, "progress_bar")
            else False
        )
        previous_progress_range = (
            (self.progress_bar.minimum(), self.progress_bar.maximum())
            if hasattr(self, "progress_bar")
            else (0, 0)
        )
        previous_progress_value = (
            int(self.progress_bar.value()) if hasattr(self, "progress_bar") else 0
        )
        previous_ui_state = {
            "status": previous_status,
            "progress_visible": previous_progress_visible,
            "progress_range": previous_progress_range,
            "progress_value": previous_progress_value,
        }

        if bool(getattr(self, "_derivadas_sync_running", False)):
            if hasattr(self, "status_label"):
                self.status_label.setText(
                    "Status: Atualizacao de derivadas ja em andamento."
                )
            return {
                "ok": False,
                "reason": "already_running",
                "db_path": db_path,
                "table_name": table_name,
            }

        self._start_derivadas_sync_ui_state(
            previous_ui_state, "Status: Atualizando derivadas via DB..."
        )

        if os.environ.get("PYTEST_CURRENT_TEST"):
            result = SSAMainWindow._execute_derivadas_sync_job(
                db_path=db_path,
                table_name=table_name,
                special_files=special_files,
            )
            return SSAMainWindow._finalize_derivadas_sync_result(
                self, result, previous_ui_state=previous_ui_state
            )

        self._derivadas_sync_running = True
        self._derivadas_sync_thread = None
        self._derivadas_sync_pending_result = None
        self._derivadas_sync_phase_status = "Status: Atualizando derivadas via DB..."
        self._derivadas_sync_ui_state = previous_ui_state

        def _window_alive() -> bool:
            if self is None:
                return False
            if not hasattr(self, "metaObject"):
                return True
            if sip is None:
                return True
            try:
                return not sip.isdeleted(self)
            except Exception:
                return False

        def _set_phase_status(text: str) -> None:
            self._derivadas_sync_phase_status = str(text or "")

        def _work() -> None:
            try:
                result = SSAMainWindow._execute_derivadas_sync_job(
                    db_path=db_path,
                    table_name=table_name,
                    special_files=special_files,
                    status_callback=_set_phase_status,
                )
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            self._derivadas_sync_pending_result = result

        def _poll_delivery() -> None:
            if not _window_alive():
                self._derivadas_sync_pending_result = None
                self._derivadas_sync_thread = None
                self._derivadas_sync_running = False
                return
            phase_status = str(getattr(self, "_derivadas_sync_phase_status", "") or "")
            if phase_status and hasattr(self, "status_label"):
                self.status_label.setText(phase_status)
            pending = getattr(self, "_derivadas_sync_pending_result", None)
            if pending is None:
                if bool(getattr(self, "_derivadas_sync_running", False)):
                    QTimer.singleShot(100, _poll_delivery)
                return
            self._derivadas_sync_pending_result = None
            SSAMainWindow._finalize_derivadas_sync_result(self, pending)

        worker = threading.Thread(target=_work, daemon=True)
        self._derivadas_sync_thread = worker
        worker.start()
        QTimer.singleShot(100, _poll_delivery)
        return {
            "ok": True,
            "started": True,
            "db_path": db_path,
            "table_name": table_name,
        }

    def _start_derivadas_sync_ui_state(
        self, previous_ui_state: dict[str, Any], initial_status: str
    ) -> None:
        try:
            self.update_derivadas_button.setEnabled(False)
            if hasattr(self, "progress_bar"):
                if bool(previous_ui_state.get("progress_visible")):
                    self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
            if hasattr(self, "status_label"):
                self.status_label.setText(initial_status)
        except Exception as exc:
            logger.warning(
                "Falha ao preparar estado visual antes do sync manual de derivadas: %s",
                exc,
            )

    @staticmethod
    def _execute_derivadas_sync_job(
        *,
        db_path: str,
        table_name: str,
        special_files: list[str],
        status_callback=None,
    ) -> dict[str, Any]:
        def _set_status(text: str) -> None:
            if callable(status_callback):
                status_callback(text)

        def _has_sheet_parse_evidence(entry: dict[str, Any]) -> bool:
            if not isinstance(entry, dict):
                return False
            raw_stats = entry.get("stats")
            stats = raw_stats if isinstance(raw_stats, dict) else {}
            has_flag = bool(entry.get("has_parse_evidence"))
            accepted = int(stats.get("accepted_edges", 0) or 0)
            special_layout = int(stats.get("special_layout_detected", 0) or 0)
            informational = int(stats.get("informational_rows_skipped", 0) or 0)
            return has_flag or accepted > 0 or special_layout > 0 or informational > 0

        try:
            _set_status("Status: Atualizando derivadas via DB...")
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
                _set_status(
                    "Status: Atualizando derivadas via planilhas especiais "
                    f"({len(special_files)})..."
                )
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
                    if current_entry is None or not _has_sheet_parse_evidence(
                        current_entry
                    ):
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
            if not bool(consistency.get("schema_ready")) or not bool(
                consistency.get("is_consistent")
            ):
                issue_counts = consistency.get("issue_counts") or {}
                raise RuntimeError(
                    "Derivadas inconsistente apos sync manual: "
                    f"{json.dumps(issue_counts, ensure_ascii=True)}"
                )
            return {
                "ok": True,
                "db_edges": db_edges,
                "sheet_edges": sheet_edges,
                "merged_edges": merged_edges,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _finalize_derivadas_sync_result(
        self,
        result: dict[str, Any],
        *,
        previous_ui_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        previous = (
            previous_ui_state or getattr(self, "_derivadas_sync_ui_state", {}) or {}
        )
        self._derivadas_sync_running = False
        self._derivadas_sync_thread = None
        self._derivadas_sync_pending_result = None
        self._derivadas_sync_phase_status = ""

        try:
            self.update_derivadas_button.setEnabled(True)
            if hasattr(self, "progress_bar"):
                self.progress_bar.setVisible(bool(previous.get("progress_visible")))
                progress_range = previous.get("progress_range") or (0, 0)
                self.progress_bar.setRange(progress_range[0], progress_range[1])
                self.progress_bar.setValue(int(previous.get("progress_value", 0) or 0))
        except Exception as exc:
            logger.warning(
                "Falha ao restaurar estado visual do sync manual de derivadas: %s",
                exc,
            )

        if bool(result.get("ok")):
            merged_edges = int(result.get("merged_edges", 0) or 0)
            db_edges = int(result.get("db_edges", 0) or 0)
            sheet_edges = int(result.get("sheet_edges", 0) or 0)
            if hasattr(self, "status_label"):
                self.status_label.setText(
                    "Status: Derivadas atualizadas (merged="
                    f"{merged_edges}, db={db_edges}, sheet={sheet_edges})."
                )
            try:
                self._update_derivadas_button_state()
            except Exception as exc:
                logger.warning(
                    "Falha ao atualizar estado do botao de derivadas apos sync manual: %s",
                    exc,
                )
            return result

        error = str(result.get("error") or "Erro desconhecido")
        logger.error("Falha ao atualizar derivadas manualmente: %s", error)
        if hasattr(self, "status_label"):
            self.status_label.setText("Status: Falha ao atualizar derivadas.")
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.critical(self, "Erro", f"Falha ao atualizar derivadas: {error}")
        return result

    @staticmethod
    def _validate_database_candidate(db_file: str) -> dict[str, Any]:
        try:
            test_df = query_db(db_file, TABLE_NAME)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "db_file": db_file}
        has_rows = bool(test_df is not None and not test_df.empty)
        return {"ok": has_rows, "db_file": db_file}

    def _finalize_database_candidate_validation(
        self, result: dict[str, Any]
    ) -> dict[str, Any]:
        self._other_db_validation_running = False
        self._other_db_validation_thread = None
        self._other_db_validation_pending_result = None

        db_file = str(result.get("db_file") or "").strip()
        if bool(result.get("ok")) and db_file:
            global DB_PATH
            DB_PATH = db_file
            self.status_label.setText(
                f"Status: Banco alternativo selecionado: {os.path.basename(db_file)}"
            )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(
                    self,
                    "Sucesso",
                    (
                        f"Banco de dados selecionado: {os.path.basename(db_file)}\n\n"
                        "Clique em 'Carregar Dados' para carregar os dados."
                    ),
                )
            return result

        error = str(result.get("error") or "").strip()
        if error:
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.critical(
                    self, "Erro", f"Erro ao abrir o banco de dados: {error}"
                )
            self.status_label.setText("Status: Falha ao validar banco alternativo.")
            return result

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(
                self,
                "Erro",
                "O arquivo selecionado nao contem dados validos na tabela principal de SSAs.",
            )
        self.status_label.setText("Status: Banco alternativo invalido.")
        return {"ok": False, "db_file": db_file}

    def load_other_database(self):
        """Permite selecionar e carregar outro arquivo de banco de dados."""
        file_dialog = QFileDialog()
        db_file, _ = file_dialog.getOpenFileName(
            self,
            "Selecionar Banco de Dados",
            os.path.join(project_root, "data"),
            "Arquivos de Banco (*.db *.sqlite);;Todos os Arquivos (*)",
        )

        if db_file and os.path.exists(db_file):
            if bool(getattr(self, "_other_db_validation_running", False)):
                self.status_label.setText(
                    "Status: Validacao de banco alternativo ja em andamento."
                )
                return {"ok": False, "reason": "already_running", "db_file": db_file}
            self.status_label.setText("Status: Validando banco alternativo...")
            if os.environ.get("PYTEST_CURRENT_TEST"):
                result = SSAMainWindow._validate_database_candidate(db_file)
                return self._finalize_database_candidate_validation(result)

            self._other_db_validation_running = True
            self._other_db_validation_thread = None
            self._other_db_validation_pending_result = None

            def _window_alive() -> bool:
                if self is None:
                    return False
                if not hasattr(self, "metaObject"):
                    return True
                if sip is None:
                    return True
                try:
                    return not sip.isdeleted(self)
                except Exception:
                    return False

            def _work() -> None:
                self._other_db_validation_pending_result = (
                    SSAMainWindow._validate_database_candidate(db_file)
                )

            def _poll_delivery() -> None:
                if not _window_alive():
                    self._other_db_validation_pending_result = None
                    self._other_db_validation_thread = None
                    self._other_db_validation_running = False
                    return
                pending = getattr(self, "_other_db_validation_pending_result", None)
                if pending is None:
                    if bool(getattr(self, "_other_db_validation_running", False)):
                        QTimer.singleShot(100, _poll_delivery)
                    return
                self._other_db_validation_pending_result = None
                SSAMainWindow._finalize_database_candidate_validation(self, pending)

            worker = threading.Thread(target=_work, daemon=True)
            self._other_db_validation_thread = worker
            worker.start()
            QTimer.singleShot(100, _poll_delivery)
            return {"ok": True, "started": True, "db_file": db_file}
        elif db_file:  # Arquivo selecionado mas nao existe
            QMessageBox.warning(self, "Erro", "Arquivo selecionado nao existe.")

    def remove_persistent_filter(self, filter_data):
        """Remove um filtro persistente e atualiza imediatamente."""
        if filter_data in self.persistent_filters:
            current_search = self.search_input.text().strip()
            removed_active_filter = current_search == filter_data["terms"]
            previous_filter_state = None
            if removed_active_filter:
                try:
                    self._safe_store_last_filter_state("remove_persistent_filter")
                    previous_filter_state = copy.deepcopy(
                        getattr(self, "_last_filter_state", None)
                    )
                except Exception as exc:
                    logger.warning(
                        "Falha ao salvar estado antes de remover filtro persistente: %s",
                        exc,
                    )
            self.persistent_filters.remove(filter_data)
            try:
                self._save_persistent_filters_file()
            except Exception as exc:
                logger.warning("Falha ao persistir remocao de filtro salvo: %s", exc)
            self.update_filter_tags()
            # Atualiza imediatamente se o filtro removido estava ativo
            if removed_active_filter:
                self.search_input.clear()
                self.initiate_filtering()
                if previous_filter_state:
                    self._last_filter_state = previous_filter_state
                    try:
                        self._update_undo_button_state()
                    except Exception as exc:
                        logger.debug(
                            "Falha ao atualizar botao undo apos remover filtro persistente: %s",
                            exc,
                        )

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
            logger.debug(
                "Falha ao sincronizar altura dos paineis inferiores durante resize: %s",
                exc,
            )

        # So recalcula se ha dados carregados e uma mudanca significativa na largura
        if (
            hasattr(self, "df_exibido")
            and not self.df_exibido.empty
            and hasattr(self, "_last_window_width")
        ):
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
                or not hasattr(self, "df_para_tabela")
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
            if (
                hasattr(self, "_resize_recompute_timer")
                and self._resize_recompute_timer is not None
            ):
                self._resize_recompute_timer.start(300)
            else:
                QTimer.singleShot(
                    300,
                    lambda rev=int(
                        expected_revision
                    ): self._recompute_column_widths_on_resize(expected_revision=rev),
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
            if (
                not hasattr(self, "df_para_tabela")
                or self.df_para_tabela.empty
                or not hasattr(self, "_gui_column_pixel_widths")
                or not self.table_widget
                or not self.table_widget.isVisible()
            ):
                return

            # CORRECAO CRITICA: Usar _current_display_columns que contem apenas as colunas visiveis filtradas
            # Em vez de ['#'] + todas as colunas do df_para_tabela
            if (
                not hasattr(self, "_current_display_columns")
                or not self._current_display_columns
            ):
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
                logger.debug(
                    "Falha no cleanup do data loader durante closeEvent: %s", exc
                )
            finally:
                if getattr(self, "data_loader_thread", None) is data_worker:
                    self.data_loader_thread = None

        # Aguarda finalizacao do filter thread se estiver rodando
        worker = getattr(self, "filter_thread", None)
        if worker and hasattr(worker, "isRunning") and worker.isRunning():
            try:
                # Usa cleanup centralizado (desconecta todos os callbacks, inclusive lambdas)
                self._cancel_active_filter_worker("closeEvent", wait_ms=3000)
            except Exception as exc:
                logger.debug("Filter cleanup fallback in closeEvent: %s", exc)
                try:
                    worker.quit()
                    worker.wait(3000)  # Aguarda ate 3 segundos
                except Exception as fallback_exc:
                    logger.debug(
                        "Falha no fallback de encerramento do filter worker: %s",
                        fallback_exc,
                    )

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
                    if (
                        len(GLOBAL_RETIRED_RESCAN_WORKERS)
                        <= MAX_GLOBAL_RETIRED_RESCAN_WORKERS
                    ):
                        return
                    overflow = (
                        len(GLOBAL_RETIRED_RESCAN_WORKERS)
                        - MAX_GLOBAL_RETIRED_RESCAN_WORKERS
                    )
                    dropped_workers = GLOBAL_RETIRED_RESCAN_WORKERS[:overflow]
                    GLOBAL_RETIRED_RESCAN_WORKERS[:] = GLOBAL_RETIRED_RESCAN_WORKERS[
                        overflow:
                    ]
                    for dropped_worker in dropped_workers:
                        GLOBAL_RETIRED_RESCAN_META.pop(dropped_worker, None)

                try:
                    if not ssa_gui_workers.is_data_loader_worker_alive(
                        target_worker, sip
                    ):
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
                        logger.debug(
                            "Falha ao podar rescan workers apos retencao global: %s",
                            exc,
                        )
                    logger.debug(
                        "RescanWorker retido globalmente durante closeEvent (%s).",
                        reason,
                    )
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
                        logger.debug(
                            "Falha ao solicitar stop do RescanWorker no closeEvent: %s",
                            exc,
                        )
                    try:
                        if hasattr(rescan_worker, "quit"):
                            rescan_worker.quit()
                    except Exception as exc:
                        logger.debug(
                            "Falha ao solicitar quit do RescanWorker no closeEvent: %s",
                            exc,
                        )
                    try:
                        rescan_worker.wait(1500)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao aguardar RescanWorker no closeEvent: %s", exc
                        )
                    try:
                        if self._is_rescan_worker_running(rescan_worker):
                            try:
                                if hasattr(rescan_worker, "terminate"):
                                    rescan_worker.terminate()
                                    rescan_worker.wait(1500)
                            except Exception as exc:
                                logger.debug(
                                    "Falha no fallback terminate do RescanWorker no closeEvent: %s",
                                    exc,
                                )
                        if self._is_rescan_worker_running(rescan_worker):
                            retained_globally = _retain_rescan_worker_global(
                                rescan_worker,
                                reason="still-running-after-shutdown",
                            )
                    except Exception as exc:
                        logger.debug(
                            "Falha ao checar/reter RescanWorker no closeEvent: %s", exc
                        )
            except Exception as exc:
                logger.debug(
                    "Falha ao encerrar RescanWorker durante closeEvent: %s", exc
                )
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
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
