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
from collections import OrderedDict


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

# --- Função para Carregar Configurações da GUI Principal ---
def load_gui_main_preferences():
    """Carrega configuracoes especificas da GUI Principal do arquivo JSON."""
    config_path = os.path.join(project_root, 'config', 'gui_main_preferences.json')

    default_config = {
        "display_columns": [
            "numero_ssa", "setor_executor", "situacao", "descricao_ssa",
            "data_cadastro", "semana_cadastro", "localizacao_codigo", "grau_prioridade_emissao"
        ],
        "hidden_columns": ["descricao_localizacao", "equipamento", "servico_origem"],
        "column_display_names": {
            "numero_ssa": "Numero SSA", "setor_executor": "Exec.",
            "situacao": "Sit.", "descricao_ssa": "Desc.",
            "data_cadastro": "Data Cad.", "semana_cadastro": "Sem.Cad.",
            "localizacao_codigo": "Loc.", "grau_prioridade_emissao": "Prio.Emis."
        },
        "column_widths": {
            "#": 50, "numero_ssa": 120, "setor_executor": 150, "situacao": 120,
            "descricao_ssa": 300, "data_cadastro": 110, "semana_cadastro": 100
        },
        "gui_settings": {
            "page_size": 50, "auto_load": False, "debounce_delay": 250,
            "default_filter_mode": "contains", "show_progress_bar": True
        },
        "version": "1.0.0"
    }

    if not os.path.exists(config_path):
        logger.warning("Gui main preferences not found at %s, using defaults.", config_path)
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as handle:
            loaded_config = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("Unable to parse gui main preferences at %s: %s", config_path, exc)
        return default_config
    except OSError as exc:
        logger.error("Unable to read gui main preferences at %s: %s", config_path, exc)
        return default_config

    if not isinstance(loaded_config, dict) or 'display_columns' not in loaded_config:
        logger.warning("Invalid gui main preferences structure at %s, using defaults.", config_path)
        return default_config

    return loaded_config
# Carrega as configurações globalmente
GUI_MAIN_PREFERENCES = load_gui_main_preferences()

from utils.formatting import format_dataframe_for_display, format_cell  # noqa: E402

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms  # noqa: E402
import hashlib
from armazenamento.database import query_db  # noqa: E402

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
    QMenu, QGroupBox, QTextEdit, QTextBrowser, QFileDialog, QDialog, QDialogButtonBox,
        QSpacerItem, QSizePolicy, QFrame, QListWidget, QListWidgetItem, QCheckBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
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
        pass

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
            pass
        def text(self):
            return ""
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
            return 0

        def setCurrentIndex(self, *a, **k):
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
        pass

    class QGroupBox:
        pass

    class QTextEdit:
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
            self.toggled = _Sig()

        def isChecked(self):
            return self._checked

        def setChecked(self, val):
            self._checked = bool(val)

        def setToolTip(self, *a, **k):
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
    'descricao_ssa': 'Descricao da SSA',
    'setor_executor': 'Setor Executor',
    'setor_emissor': 'Setor Emissor',
    'solicitante': 'Solicitante',
    'servico_origem': 'Servico de Origem',
    'grau_prioridade_emissao': 'Grau de Prioridade (Emissao)',
    'grau_prioridade_planejamento': 'Grau de Prioridade (Planejamento)',
    'execucao_simples': 'Execucao Simples',
    'responsavel_programacao': 'Responsavel pela Programacao',
    'responsavel_execucao': 'Responsavel pela Execucao',
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
CONFIG_DIR = os.path.join(project_root, 'config')
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'display_mappings.json')

# --- Funções Auxiliares ---

def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibiçção independente do CLI."""
    # Usa configurações da GUI Main em vez de display_mappings.json
    return GUI_MAIN_PREFERENCES.get("column_display_names", {})

# --- Worker Threads ---

# --- Componentes da GUI ---

# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow, FilterGUISSAMixin):
    """
    Janela principal da aplicação GUI.

    Inherits from FilterGUISSAMixin for filter-related methods.
    """
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
        self.default_columns = GUI_MAIN_PREFERENCES.get("display_columns", [
            'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
            'data_cadastro', 'semana_cadastro'
        ])

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
        # Aplica o tema preferido (padrao: claro) antes do auto-load
        preferred_theme = gui_settings.get("theme", "light")
        self.apply_theme(preferred_theme)
        try:
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = preferred_theme
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
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
        self.week_label.setStyleSheet(
            "font-weight:600; border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
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

        # Margem superior da faixa de pesquisa (simetrica com base)
        main_layout.addSpacing(6)

        # --- Barra de Pesquisa e Filtros (grupos esquerda/direita) ---
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        self.search_label = QLabel("Pesquisa Geral:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Separe por virgulas (condicao E: todos os termos obrigatorios); ! exclui")
        self.search_input.setToolTip(
            "Condicao E: Todos os termos separados por virgula devem estar presentes.\n\n"
            "Modos por termo: \n"
            "- contem (padrao): foo\n- comeca com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex: ~foo.*bar\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
        )
        self.search_input.setMinimumWidth(425)  # +~25% para mais conforto
        self.search_input.setMaximumWidth(950)
        try:
            self.search_input.setMinimumHeight(26)
        except Exception:
            pass
        self.search_input.returnPressed.connect(self.initiate_filtering)
        self.search_button = QPushButton("Aplicar")
        self.search_button.clicked.connect(self.initiate_filtering)
        self.clear_filter_button = QPushButton("Limpar Filtro")
        self.clear_filter_button.clicked.connect(self.clear_filter)
        self.clear_filter_button.setEnabled(False)
        left.addWidget(self.search_label)
        left.addWidget(self.search_input)
        left.addWidget(self.search_button)
        left.addWidget(self.clear_filter_button)

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        self.column_selector = ColumnSelector(
            self.display_map,
            self.visible_columns,
            default_columns=self.default_columns,
            available_columns=list(self.display_map.keys()),
            info_font=self._info_font,
        )
        self.column_selector.columns_changed.connect(self.on_columns_changed)
        right.addWidget(self.column_selector)

        search_row.addLayout(left)
        # Espaçador expansável garante que o grupo da direita encoste no limite direito
        search_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        search_row.addLayout(right)
        main_layout.addLayout(search_row)

        # Ajuda compacta do filtro global (linha curta abaixo da pesquisa)
        help_line = QHBoxLayout()
        help_line.setContentsMargins(0, 0, 0, 0)
        # Texto direto e visivel; etiqueta se expande ate o fim da linha
        self.search_help = QLabel(
            "Separe por virgulas (logica E: todos os termos obrigatorios). Use ! para excluir. A busca vale para qualquer coluna."
        )
        self.search_help.setWordWrap(False)
        try:
            self.search_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        self.search_help.setStyleSheet("color: palette(mid); margin:0; padding:0;")
        help_line.addWidget(self.search_help)
        main_layout.addLayout(help_line)
        # Espaco para destacar a faixa de pesquisa (simetrico com o topo)
        main_layout.addSpacing(6)

        # --- Paginador e Filtros Persistentes ---
        pagination_filters_layout = QHBoxLayout()
        pagination_filters_layout.setContentsMargins(0, 0, 0, 0)

        # Paginador
        self.paginator = DataPaginator(self.df_para_tabela)
        self.paginator.page_changed.connect(self.display_current_page)
        pagination_filters_layout.addWidget(self.paginator)

        # Perfil de filtro por setor
        profile_layout = QHBoxLayout()
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(4)
        profile_label = QLabel("Perfil de filtro:")
        self.profile_selector = QComboBox()
        try:
            self.profile_selector.setMinimumWidth(150)
            self.profile_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        except Exception:
            pass
        self.profile_selector.addItem("Personalizado", None)
        for profile_name in self.filter_profiles.keys():
            self.profile_selector.addItem(profile_name, profile_name)
        self.profile_selector.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(self.profile_selector)
        pagination_filters_layout.addSpacing(12)
        pagination_filters_layout.addLayout(profile_layout)

        # Espaçamento entre paginador e filtros
        pagination_filters_layout.addSpacing(12)

        # Area de filtros persistentes
        self.persistent_filters_layout = QHBoxLayout()
        self.persistent_filters_layout.setContentsMargins(0, 0, 0, 0)

        save_filter_button = QPushButton("Salvar Filtro")
        save_filter_button.setMaximumWidth(100)
        save_filter_button.setToolTip("Salvar filtro atual como persistente")
        save_filter_button.clicked.connect(self.save_current_filter)
        self.persistent_filters_layout.addWidget(save_filter_button)

        self.exclude_ste_checkbox = QCheckBox("Nao esta em STE/SCA")
        self.exclude_ste_checkbox.setToolTip("Oculta SSAs com situacao STE ou SCA")
        try:
            self.exclude_ste_checkbox.setChecked(False)
        except Exception:
            pass
        try:
            self.exclude_ste_checkbox.toggled.connect(self._on_exclude_ste_sca_toggled)
        except Exception:
            pass
        self.persistent_filters_layout.addWidget(self.exclude_ste_checkbox)

        # Container para tags de filtros
        self.filter_tags_widget = QWidget()
        self.filter_tags_layout = QHBoxLayout(self.filter_tags_widget)
        self.filter_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_tags_layout.setSpacing(5)
        self.persistent_filters_layout.addWidget(self.filter_tags_widget)

        pagination_filters_layout.addLayout(self.persistent_filters_layout)
        pagination_filters_layout.addStretch()
        # Indicador de filtros por coluna (ao lado de "Salvar Filtro")
        self.col_filter_indicator = QLabel("Filtros por coluna: Não ativo")
        try:
            if self._info_font is not None:
                self.col_filter_indicator.setFont(QFont(self._info_font))
        except Exception:
            pass
        self.col_filter_indicator.setToolTip(
            "Filtros por coluna acumulam com a Pesquisa Geral (logica E entre filtros). "
            "Dentro de cada filtro, use virgulas para alternativas (logica OU). Consulte a ajuda para outros atalhos."
        )
        pagination_filters_layout.addWidget(self.col_filter_indicator)

        main_layout.addLayout(pagination_filters_layout)

        # Linha de resumo de filtros aplicados (Geral + Colunas)
        try:
            self.filters_summary_frame = QFrame()
            self.filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
            summary_layout = QHBoxLayout(self.filters_summary_frame)
            summary_layout.setContentsMargins(6,4,6,4)
            summary_layout.setSpacing(8)
            self.filters_summary_label = QLabel("Nenhum filtro ativo")
            if self._info_font is not None:
                try:
                    self.filters_summary_label.setFont(QFont(self._info_font))
                except Exception:
                    pass
            self.clear_all_filters_btn = QPushButton("Limpar todos os filtros")
            self.clear_all_filters_btn.setMaximumWidth(200)
            self.clear_all_filters_btn.clicked.connect(self._clear_all_filters_global)
            summary_layout.addWidget(self.filters_summary_label, 1)
            summary_layout.addWidget(self.clear_all_filters_btn, 0)
            main_layout.addWidget(self.filters_summary_frame)
            # Sempre visível; o texto é atualizado conforme filtros
            self.filters_summary_frame.setVisible(True)
        except Exception:
            pass

        # Restaura page size se configurado
        if isinstance(self._restored_page_size, int) and 10 <= self._restored_page_size <= 500:
            self.paginator.page_size_spinbox.setValue(self._restored_page_size)
        # Persiste alterações do page size
        self.paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)

        # --- Tabela de Dados ---
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Começa como Interativo; apos preencher a pagina, aplicamos larguras fixas para estabilidade
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(False)

        # CORRECAO v3.0.5: Performance otimizada - removido word wrap global e resize automatico
        # Word wrap causa lentidção extrema em grandes datasets
        # self.table_widget.setWordWrap(True)  # ÔåÉ REMOVIDO - causava travamentos

        # Altura fixa otimizada ao inves de resize automatico
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_widget.verticalHeader().setDefaultSectionSize(24)  # Altura fixa otimizada

        # Conecta clique duplo para mostrar detalhes (placeholder)
        self.table_widget.doubleClicked.connect(self.on_table_double_click)
        # Atualiza painel de detalhes quando a seleçção muda
        self.table_widget.itemSelectionChanged.connect(self.update_details_from_selection)
        # Salva largura quando usuãrio redimensionar uma coluna
        self.table_widget.horizontalHeader().sectionResized.connect(self._on_header_section_resized)

        # Ordenaçção por clique no cabeçalho + menu de filtro por coluna
        try:
            header = self.table_widget.horizontalHeader()
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(True)
            # Evita colunas com largura zero em cenários headless/CI
            try:
                header.setMinimumSectionSize(80)
                header.setDefaultSectionSize(100)
            except Exception:
                pass
            # Fonte do cabeçalho nunca em negrito (evita ocupar mais espaço)
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
            # Filtro de eventos garante menu mesmo em temas/estilos que suprimem o sinal
            header.installEventFilter(self)
        except Exception:
            pass

        # Habilita menu de contexto
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        main_layout.addWidget(self.table_widget)

        # --- Painel de Detalhes + Painel de Filtros por Coluna (com rodape fixo) ---
        bottom_layout = QHBoxLayout()

        # Detalhes (maior)
        self.details_group = QGroupBox("Detalhes da SSA Selecionada")
        details_layout = QVBoxLayout(self.details_group)
        details_layout.setContentsMargins(2, 2, 2, 2)  # Reduzido de 5 para 2
        details_layout.setSpacing(2)  # Reduzido de 3 para 2
        self.details_text = QTextEdit()
        try:
            self.details_text.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass
        try:
            self.details_text.viewport().setAutoFillBackground(False)
        except Exception:
            pass
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        bottom_layout.addWidget(self.details_group, 5)
        

        # Filtros por Coluna com lista rolavel + rodape fixo
        self.col_filters_group = QGroupBox("Filtros por Coluna")
        col_filters_outer = QVBoxLayout(self.col_filters_group)
        from PyQt6.QtWidgets import QScrollArea
        self.col_filters_hint = QLabel("Use virgulas para alternativas (logica OU dentro da coluna). Entre colunas mantemos logica E.")
        try:
            self.col_filters_hint.setStyleSheet("color: palette(windowText); font-size: 11px;")
        except Exception:
            pass
        col_filters_outer.addWidget(self.col_filters_hint)
        self.col_filters_scroll = QScrollArea()
        self.col_filters_scroll.setWidgetResizable(True)
        self.col_filters_container = QWidget()
        self.col_filters_list_layout = QVBoxLayout(self.col_filters_container)
        self.col_filters_scroll.setWidget(self.col_filters_container)
        col_filters_outer.addWidget(self.col_filters_scroll, 1)
        # Rodape fixo
        footer = QHBoxLayout()
        footer.addStretch()
        self.add_column_filter_btn = QPushButton("Adicionar filtro de coluna")
        self.add_column_filter_btn.setMaximumWidth(260)
        self.add_column_filter_btn.setToolTip("Selecionar coluna visivel para ativar filtro dedicado")
        self.add_column_filter_btn.clicked.connect(self._open_add_column_filter_menu)
        footer.addWidget(self.add_column_filter_btn)
        footer.addSpacing(8)
        self.clear_all_btn = QPushButton("Limpar todos filtros de colunas")
        self.clear_all_btn.setMaximumWidth(260)
        self.clear_all_btn.clicked.connect(self._clear_all_column_filters)
        footer.addWidget(self.clear_all_btn)
        footer.addStretch()
        col_filters_outer.addLayout(footer)

        # Constrói painel inicial de filtros por coluna
        try:
            self._build_column_filters_panel()
        except Exception:
            pass

        # Coluna da direita: apenas grupo de filtros por coluna (resumo duplicado removido)
        right_col_widget = QWidget()
        right_col = QVBoxLayout(right_col_widget)
        right_col.setContentsMargins(0,0,0,0)
        right_col.addWidget(self.col_filters_group)
        bottom_layout.addWidget(right_col_widget, 5)

        # Respiro antes do bloco inferior
        main_layout.addSpacing(12)
        main_layout.addLayout(bottom_layout)

        # --- Conecta Workers / Flags ---
        # Threads iniciadas sob demanda
        self.data_loader_thread = None
        self.filter_thread = None
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in ("1", "true", "yes", "on")
        # Em ambiente de testes (pytest), force modo síncrono para previsibilidade
        if not self._sync_filtering and os.environ.get("PYTEST_CURRENT_TEST"):
            self._sync_filtering = True
        
        # Conecta debounce automático ao digitar
        self.search_input.textChanged.connect(self._on_search_text_changed)
        
        # Configura cache size da configuração
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        cache_size = gui_settings.get("filter_cache_size", 50)
        FilterWorker._cache = FilterCache(max_size=cache_size)

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
        except Exception:
            pass
        self.df_exibido = base
        self._df_last_search_filtered = df.copy()
        self._widths_computed_for_df_hash = None
        self.clear_filter_button.setEnabled(True)
        self._refresh_after_filter_change()
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
        from PyQt6.QtWidgets import QMenu
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
        light_themes = [
            ("Claro", 'claro'),
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

        def _add_label(text: str):
            try:
                from PyQt6.QtWidgets import QWidgetAction
                label = QLabel(text)
                try:
                    from PyQt6.QtGui import QPalette as _QPal
                    pal = menu.palette()
                    label_color = pal.color(_QPal.ColorRole.Mid).name()
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
            light_themes = {'windows7', 'claro', 'solarized-light', 'mint-light', 'paper'}
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

            # ============================================================
            # SECTION 5: Details Panel
            # ============================================================
            # Style the SSA details text widget and its group box
            if hasattr(self, 'details_text'):
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

            # ============================================================
            # SECTION 7: Status and Week Labels
            # ============================================================
            # Style the week indicator and status bar label
            if hasattr(self, 'week_label'):
                if normalized in light_themes:
                    self.week_label.setStyleSheet('')
                else:
                    self.week_label.setStyleSheet(
                        f"font-weight:600; color:{accent}; background:{panel_bg}; border:1px solid {panel_border}; border-radius:4px; padding:2px 6px;"
                    )

            if hasattr(self, 'status_label'):
                if normalized in light_themes:
                    self.status_label.setStyleSheet('')
                else:
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

        # Aplica formataçção compartilhada para exibiçção (datas, numeros, SSA, nulls)
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

    def _format_details_html(self, series, highlight_search_terms=False):
        """Formata dados da SSA como HTML com highlight opcional."""
        import html as html_module

        # Obtem termos de busca se necessario
        search_terms = (
            self._collect_highlight_terms() if highlight_search_terms else []
        )

        try:
            from PyQt6.QtGui import QPalette as _QPal
            text_color = self.palette().color(_QPal.ColorRole.WindowText).name()
        except Exception:
            text_color = "#000000"

        html_lines = [f'<html><body style="font-family: monospace; font-size: {DETAILS_DIALOG_FONT_SIZE}pt; color: {text_color};">']
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
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(False)

        # Formata conteudo
        html_content = self._format_details_html(series, highlight_search_terms=True)
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
        index_item = self.table_widget.item(row, 0)
        if not index_item:
            self.details_text.clear()
            return
        original_index = index_item.data(Qt.ItemDataRole.UserRole)
        if original_index is None or not (0 <= original_index < len(self.df_exibido)):
            self.details_text.clear()
            return

        # Usa dados originais (nao formatados) para detalhes
        series = self.df_exibido.iloc[int(original_index)]

        try:
            html_content = self._format_details_html(series, highlight_search_terms=True)
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

            menu.addSeparator()

            # Ações para colunas
            current_item = self.table_widget.itemAt(position)
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

