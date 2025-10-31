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

from utils.formatting import format_dataframe_for_display  # noqa: E402

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

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
DETAIL_DISPLAY_OVERRIDES = {
    'situacao': 'Situação',
    'semana_cadastro': 'Semana de Cadastro',
    'data_cadastro': 'Data de Cadastro',
    'descricao_ssa': 'Descrição da SSA',
    'setor_executor': 'Setor Executor',
    'setor_emissor': 'Setor Emissor',
    'solicitante': 'Solicitante',
    'servico_origem': 'Serviço de Origem',
    'grau_prioridade_emissao': 'Grau de Prioridade (Emissão)',
    'grau_prioridade_planejamento': 'Grau de Prioridade (Planejamento)',
    'execucao_simples': 'Execução Simples',
    'responsavel_programacao': 'Responsável pela Programação',
    'responsavel_execucao': 'Responsável pela Execução',
    'semana_programada': 'Semana Programada',
    'prazo_limite': 'Prazo Limite',
    'tempo_disponivel': 'Tempo Disponível',
    'data_limite': 'Data Limite',
    'tempo_excedido': 'Tempo Excedido',
    'numero_ssa': 'Número da SSA',
    'descricao_execucao': 'Descrição da Execução',
    'status_execucao_prazo': 'Situação do Prazo',
    'execucao_parcial': 'Execução Parcial',
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

class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco."""
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_path, table_name):
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name

    def run(self):
        try:
            # Query customizada que mapeia os nomes corretos das colunas
            query = '''
            SELECT
                numero_ssa,
                situacao,
                derivada_de,
                localizacao_codigo,
                descricao_localizacao,
                equipamento,
                semana_cadastro,
                data_cadastro,
                descricao_ssa,
                setor_emissor,
                setor_executor,
                solicitante,
                servico_origem,
                grau_prioridade_emissao,
                grau_prioridade_planejamento,
                execucao_simples,
                responsavel_programacao,
                semana_programada,
                responsavel_execucao,
                descricao_execucao,
                id,
                sistema_origem,
                prazo_limite,
                tempo_disponivel,
                data_limite,
                tempo_excedido,
                desde,
                tempo_total,
                desde_1,
                total_tempo_tpe_planejado,
                total_tempo_tex_planejado,
                total_tempo_tpo_planejado,
                total_horas_programadas,
                execucao_parcial,
                anomalia,
                semana_executada,
                num_reprogramacoes
            FROM ssa_table
            '''

            df = query_db(self.db_path, '', query)
            if not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")

class FilterCache:
    """Cache inteligente LRU para resultados de filtros da GUI."""
    
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._cache = OrderedDict()  # LRU cache
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def _generate_key(self, df_hash: str, search_chunks: list, default_mode: str) -> str:
        """Gera chave única para cache baseada nos parâmetros de filtro."""
        # Converte search_chunks em string determinística
        chunks_str = str(sorted([str(sorted(chunk)) if isinstance(chunk, list) else str(chunk) for chunk in search_chunks]))
        
        # Cria hash combinado
        combined = f"{df_hash}|{chunks_str}|{default_mode}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def get(self, df_hash: str, search_chunks: list, default_mode: str) -> pd.DataFrame:
        """Recupera resultado do cache se disponível."""
        key = self._generate_key(df_hash, search_chunks, default_mode)
        
        if key in self._cache:
            # Move para o final (marca como recentemente usado)
            result = self._cache.pop(key)
            self._cache[key] = result
            self._stats['hits'] += 1
            logger.debug(f"Cache hit for filter key: {key[:8]}...")
            return result.copy()  # Retorna cópia para evitar modificações
        
        self._stats['misses'] += 1
        logger.debug(f"Cache miss for filter key: {key[:8]}...")
        return None
    
    def put(self, df_hash: str, search_chunks: list, default_mode: str, result: pd.DataFrame):
        """Armazena resultado no cache."""
        key = self._generate_key(df_hash, search_chunks, default_mode)
        
        # Remove entrada existente se houver
        if key in self._cache:
            del self._cache[key]
        
        # Adiciona nova entrada
        self._cache[key] = result.copy()
        
        # Implementa política LRU
        while len(self._cache) > self.max_size:
            # Remove item mais antigo (primeiro na OrderedDict)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats['evictions'] += 1
        
        logger.debug(f"Cache put for filter key: {key[:8]}... (size: {len(self._cache)})")
    
    def clear(self):
        """Limpa todo o cache."""
        self._cache.clear()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        logger.debug("Filter cache cleared")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'evictions': self._stats['evictions'],
            'hit_rate': hit_rate
        }


class FilterWorker(QThread):
    """Thread para filtrar dados com cache inteligente."""
    filter_finished = pyqtSignal(pd.DataFrame) # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)
    
    # Cache de classe compartilhado entre instâncias
    _cache = FilterCache(max_size=50)

    def __init__(self, df_completo, search_chunks, default_mode: str = 'contains'):
        super().__init__()
        self.df_completo = df_completo
        self.search_chunks = search_chunks or []
        self.default_mode = default_mode
        
        # Gera hash do DataFrame para cache
        self.df_hash = hashlib.md5(str(df_completo.shape).encode()).hexdigest()[:16]

    def run(self):
        try:
            # Verifica cache primeiro
            cached_result = self._cache.get(self.df_hash, self.search_chunks, self.default_mode)
            if cached_result is not None:
                self.filter_finished.emit(cached_result)
                return
            
            # Cache miss - executa filtro
            if self.search_chunks:
                frames = []
                for terms in self.search_chunks:
                    if terms:
                        parsed = parse_search_terms(terms, default_mode=self.default_mode)
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    else:
                        frames.append(self.df_completo.copy())
                if frames:
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True)
                else:
                    df_filtrado = self.df_completo.copy()
            else:
                df_filtrado = self.df_completo.copy()
            
            # Armazena no cache
            self._cache.put(self.df_hash, self.search_chunks, self.default_mode, df_filtrado)
            
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")

# --- Componentes da GUI ---

class ColumnManagerDialog(QDialog):
    """Diálogo para marcar e reordenar colunas visíveis."""

    def __init__(self, display_map, selected_columns, default_columns=None, available_columns=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar colunas visíveis")
        self.resize(420, 500)
        self.display_map = display_map or {}
        self.default_columns = list(default_columns or [])
        all_from_map = list(self.display_map.keys())
        self.available_columns = list(available_columns or []) or all_from_map
        if not self.available_columns:
            self.available_columns = list(selected_columns)
        self.available_columns = list(dict.fromkeys(self.available_columns + [c for c in all_from_map if c not in self.available_columns]))
        self._build_ui(selected_columns)

    def _build_ui(self, selected_columns):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel("Marque as colunas que deseja ver. Arraste as linhas marcadas para reordenar.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrar por nome da coluna")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        try:
            self.list_widget.setAlternatingRowColors(True)
            self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        except Exception:
            pass
        layout.addWidget(self.list_widget, 1)

        self._populate_list(selected_columns)

        tools_row = QHBoxLayout()
        self.restore_btn = QPushButton("Restaurar padrão")
        self.restore_btn.clicked.connect(self.restore_defaults)
        tools_row.addWidget(self.restore_btn)

        self.select_all_btn = QPushButton("Selecionar tudo")
        self.select_all_btn.clicked.connect(self.select_all)
        tools_row.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Limpar seleção")
        self.clear_all_btn.clicked.connect(self.clear_all)
        tools_row.addStretch()
        tools_row.addWidget(self.clear_all_btn)
        layout.addLayout(tools_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _ordered_columns(self, selected_columns):
        selection = [c for c in selected_columns if c in self.available_columns]
        if not selection and self.default_columns:
            selection = [c for c in self.default_columns if c in self.available_columns]
        remaining = [c for c in self.available_columns if c not in selection]
        return selection + remaining

    def _populate_list(self, selected_columns):
        self.list_widget.clear()
        for col in self._ordered_columns(selected_columns):
            display_name = self.display_map.get(col, col)
            item = QListWidgetItem(display_name)
            try:
                flags = item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsSelectable
                item.setFlags(flags)
            except Exception:
                pass
            item.setData(Qt.ItemDataRole.UserRole, col)
            if selected_columns:
                state = Qt.CheckState.Checked if col in selected_columns else Qt.CheckState.Unchecked
            else:
                state = Qt.CheckState.Checked if col in self.default_columns else Qt.CheckState.Unchecked
            item.setCheckState(state)
            self.list_widget.addItem(item)

    def _apply_filter(self, text):
        text = (text or '').strip().casefold()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            display = item.text().casefold()
            internal = str(item.data(Qt.ItemDataRole.UserRole) or '').casefold()
            visible = not text or text in display or text in internal
            try:
                item.setHidden(not visible)
            except Exception:
                pass

    def restore_defaults(self):
        self._populate_list(self.default_columns)

    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def clear_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def get_selected_columns(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                col = item.data(Qt.ItemDataRole.UserRole)
                if col and col not in selected:
                    selected.append(col)
        return selected


class ColumnSelector(QWidget):
    """Widget compacto que abre o gerenciador de colunas."""
    columns_changed = pyqtSignal(list)

    def __init__(
        self,
        display_map,
        initial_columns,
        default_columns=None,
        available_columns=None,
        info_font=None,
    ):
        super().__init__()
        self.display_map = display_map or {}
        self.default_columns = list(default_columns or initial_columns)
        self.selected_internal_columns = list(initial_columns)
        self.available_columns = list(available_columns or self.display_map.keys())
        for col in self.selected_internal_columns:
            if col not in self.available_columns:
                self.available_columns.append(col)
        self._info_font = info_font
        self.init_ui()
        if self._info_font is not None:
            self.set_summary_font(self._info_font)
        self._update_summary()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.manage_button = QPushButton("Colunas visíveis...")
        self.manage_button.setToolTip("Configurar colunas rápidas (marcar, ordenar e restaurar padrão)")
        self.manage_button.clicked.connect(self.open_dialog)
        layout.addWidget(self.manage_button)

        self.summary_label = QLabel()
        try:
            self.summary_label.setStyleSheet("color: palette(windowText);")
        except Exception:
            pass
        layout.addWidget(self.summary_label)
        layout.addStretch()

    def open_dialog(self):
        dialog = ColumnManagerDialog(
            self.display_map,
            self.selected_internal_columns,
            default_columns=self.default_columns,
            available_columns=self.available_columns,
            parent=self
        )
        try:
            result = dialog.exec()
        except Exception:
            result = dialog.accept() or QDialog.DialogCode.Accepted
        if result == QDialog.DialogCode.Accepted:
            new_columns = dialog.get_selected_columns()
            if not new_columns:
                new_columns = list(self.default_columns)
            self.selected_internal_columns = new_columns
            for col in self.selected_internal_columns:
                if col not in self.available_columns:
                    self.available_columns.append(col)
            self._update_summary()
            self.columns_changed.emit(self.selected_internal_columns)

    def _update_summary(self):
        translated = [self.display_map.get(col, col) for col in self.selected_internal_columns]
        if not translated:
            text = "Nenhuma coluna selecionada"
            tooltip = text
        else:
            text = f"{len(translated)} colunas ativas"
            tooltip = ", ".join(translated)
        self.summary_label.setText(text)
        self.summary_label.setToolTip(tooltip)

    def get_selected_columns(self):
        return self.selected_internal_columns

    def set_selected_columns(self, columns):
        self.selected_internal_columns = list(columns)
        for col in self.selected_internal_columns:
            if col not in self.available_columns:
                self.available_columns.append(col)
        self._update_summary()

    def set_summary_font(self, font):
        """Aplica fonte compartilhada para o resumo (harmoniza com outros indicadores)."""
        if font is None:
            return
        try:
            self.summary_label.setFont(QFont(font))
        except Exception:
            try:
                self.summary_label.setFont(font)
            except Exception:
                pass


class DataPaginator(QWidget):
    """Widget para paginacao de dados."""
    page_changed = pyqtSignal(int) # Emite o numero da nova pagina (1-based)

    def __init__(self, df, page_size=50):
        super().__init__()
        self.df = df
        self.page_size = page_size
        self.current_page = 1
        self.total_pages = 1
        self.init_ui()
        self.update_pagination_info()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.prev_button = QPushButton("Pagina Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)

        self.page_info_label = QLabel("Pagina 1 de 1")

        self.next_button = QPushButton("Proxima Pagina")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)

        # Controle de tamanho da pagina
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Linhas por Pagina:"))
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setRange(10, 500)
        self.page_size_spinbox.setSingleStep(10)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.valueChanged.connect(self.change_page_size)
        page_size_layout.addWidget(self.page_size_spinbox)

        layout.addWidget(self.prev_button)
        layout.addWidget(self.page_info_label)
        layout.addWidget(self.next_button)
        layout.addStretch()
        layout.addLayout(page_size_layout)

    def set_dataframe(self, df):
        self.df = df
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()

    def update_pagination_info(self):
        # Calcula total de paginas com guard rails (df pode estar vazio ou ainda nao definido)
        if getattr(self, 'df', None) is not None and not self.df.empty:
            self.total_pages = (len(self.df) + self.page_size - 1) // self.page_size
        else:
            self.total_pages = 1
            self.current_page = 1
        # Pode ser chamado antes do init_ui terminar em alguns cenarios; proteja acesso
        if hasattr(self, 'page_info_label'):
            self.page_info_label.setText(f"Pagina {self.current_page} de {self.total_pages}")

    def update_buttons(self):
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_pagination_info()
            self.update_buttons()
            self.page_changed.emit(self.current_page)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pagination_info()
            self.update_buttons()
            self.page_changed.emit(self.current_page)

    def change_page_size(self, new_size):
        self.page_size = new_size
        # Reset para a pagina 1 ao mudar o tamanho
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()
        # Notifica que a pagina 1 (com novo tamanho) deve ser carregada
        self.page_changed.emit(self.current_page)

    def get_current_slice(self):
        """Retorna o slice do DataFrame para a pagina atual."""
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.df.iloc[start_idx:end_idx]


# --- Diãlogo de Ajuda (GUI PoC revisado) ---
class FilterHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - Filtros (CLI/GUI)")
        self.setModal(True)
        self.resize(560, 480)
        layout = QVBoxLayout()
        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        app_version = get_app_version() if callable(get_app_version) else "3.0.7+"
        help_text.setHtml(
            """
            <h3>Como usar os filtros</h3>
            <h4>Separacao de termos</h4>
            <ul>
              <li><b>Pesquisa Geral</b>: virgulas separam termos (logica E - TODOS os termos obrigatorios)</li>
              <li><b>Filtros de Coluna</b>: virgulas separam alternativas (logica OU - qualquer termo serve)</li>
            </ul>
            <h4>Modos por termo</h4>
            <ul>
              <li><b>contem</b> (padrao): <code>foo</code></li>
              <li><b>comeca com</b>: <code>^foo</code></li>
              <li><b>termina com</b>: <code>foo$</code></li>
              <li><b>igual</b>: <code>=foo</code></li>
              <li><b>regex</b>: <code>~foo.*bar</code></li>
              <li><b>negativo</b>: prefixe <code>!</code> (ex.: <code>!^adm</code>, <code>!$2025</code>)</li>
              <li><b>vazios/nulos</b>: <code>=NULL</code> ou <code>NULL</code> (equivale a campo vazio, nulo ou <code>-</code>)</li>
            </ul>
            <h4>Exemplos</h4>
            <ul>
              <li><code>mel3</code> — procura por MEL3</li>
              <li><code>pendente, programar</code> — termos combinados</li>
              <li><code>executada, !mel4</code> — exclui MEL4</li>
              <li><code>g076, amp</code> — combina setores</li>
              <li><code>=NULL</code> — somente campos vazios/nulos</li>
            </ul>
            <h4>Filtro por coluna</h4>
            <p>Abra o menu com <b>clique direito</b> no titulo da coluna. O painel a direita mostra os filtros por coluna com botoes <b>Aplicar</b> e <b>Limpar</b>. Regras identicas as do filtro geral.</p>
            <h4>Dicas</h4>
            <ul>
              <li>Nao diferencia maiusculas/minusculas</li>
              <li>Termos parciais funcionam (ex.: <code>exec</code> encontra <i>executada</i>)</li>
              <li>Deixe vazio para ver todas as SSAs</li>
            </ul>
            <hr/>
            <p style='font-size:12px;'>
              <b>Projeto:</b> SSA_Consulta_Rapida • <b>Versao:</b> %s<br/>
              <b>Autor:</b> Mauricio Menon • <b>Repositorio:</b>
              <a href='https://github.com/mauriciomenon/SSA_Consulta_Rapida'>github.com/mauriciomenon/SSA_Consulta_Rapida</a>
            </p>
            """
            % app_version
        )
        layout.addWidget(help_text)
        okb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        okb.accepted.connect(self.accept)
        layout.addWidget(okb)
        self.setLayout(layout)

# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow):
    """
    Janela principal da aplicação GUI.
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

        self.exclude_ste_checkbox = QCheckBox("Não está em STE/SCA")
        self.exclude_ste_checkbox.setToolTip("Oculta SSAs com situação STE ou SCA")
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

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        # Chamar start() novamente reinicia o QTimer automaticamente
        self._debounce_timer.start()
    
    def clear_filter_cache(self):
        """Limpa o cache de filtros."""
        FilterWorker._cache.clear()
        logger.info("Cache de filtros limpo")
    
    def get_filter_cache_stats(self) -> dict:
        """Retorna estatísticas do cache de filtros."""
        return FilterWorker._cache.get_stats()

    # --- Slots e Handlers ---

    def load_data(self):
        if not os.path.exists(DB_PATH):
            QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' nção encontrado. Execute o programa principal primeiro.")
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

    def initiate_filtering(self):
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        search_text = self.search_input.text().strip()
        raw_chunks = self._split_search_expression(search_text) if search_text else []
        chunk_terms_lists = [self._normalize_chunk_for_parse(chunk) for chunk in raw_chunks] if raw_chunks else ([] if not search_text else [self._normalize_chunk_for_parse(search_text)])
        # remove empty chunk lists
        chunk_terms_lists = [terms for terms in chunk_terms_lists if terms]

        if hasattr(self, 'clear_filter_button'):
            has_terms = bool(chunk_terms_lists or search_text or any(str(v).strip() for v in self._active_column_filters.values()))
            self.clear_filter_button.setEnabled(has_terms)

        if chunk_terms_lists:
            display_text = self._format_search_display(chunk_terms_lists)
        else:
            display_text = search_text if search_text else ''
        self._pending_search_display = display_text

        self.status_label.setText("Status: Filtrando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Descobre default_mode nas configuracoes JSON (OTIMIZACAO: usando cache)
        if not hasattr(self, '_cached_default_mode'):
            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode

        # Modo síncrono (sem QThread) opcional para testes
        if getattr(self, '_sync_filtering', False):
            try:
                if chunk_terms_lists:
                    frames = []
                    for terms in chunk_terms_lists:
                        parsed = parse_search_terms(terms, default_mode=default_mode)
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True) if frames else self.df_completo.copy()
                else:
                    df_filtrado = self.df_completo.copy()
                self.on_filter_finished(df_filtrado)
                # Em modo síncrono, garanta larguras válidas imediatamente após aplicar o filtro
                try:
                    self._ensure_nonzero_column_widths()
                except Exception:
                    pass
                try:
                    if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                        self.table_widget.setColumnWidth(1, 80)
                except Exception:
                    pass
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(f"Erro ao filtrar dados: {e}")
            finally:
                self.on_filter_finished_cleanup()
            return

        # Inicia a thread de filtragem (modo padrão assíncrono)
        self.filter_thread = FilterWorker(self.df_completo, chunk_terms_lists, default_mode=default_mode)
        self.filter_thread.filter_finished.connect(self.on_filter_finished)
        self.filter_thread.error_occurred.connect(self.on_filter_error)
        self.filter_thread.finished.connect(self.on_filter_finished_cleanup)
        # Garante destruição segura do objeto thread após terminar
        try:
            self.filter_thread.finished.connect(self.filter_thread.deleteLater)
        except Exception:
            pass
        self.filter_thread.start()

    def on_filter_finished(self, df_filtrado: pd.DataFrame):
        # Atualiza baseline do resultado da busca global
        self._df_last_search_filtered = df_filtrado.copy()
        # OTIMIZACAO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        self._refresh_after_filter_change()
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas.")
        if hasattr(self, 'clear_filter_button'):
            self.clear_filter_button.setEnabled(True)
        self._apply_search_display()
        # Reforça reaplicação de larguras após busca para evitar colunas zeradas em headless/CI
        try:
            self._ensure_nonzero_column_widths()
        except Exception:
            pass
        # Recalcula e aplica larguras com base no slice atual exibido para garantir consistência imediata
        try:
            if hasattr(self, 'df_para_tabela') and not self.df_para_tabela.empty:
                self._compute_gui_column_widths(self.df_para_tabela)
                self._apply_computed_widths_only()
        except Exception:
            pass
        # Garantia específica: coluna 1 (primeira após '#') nunca deve ficar com largura 0
        try:
            if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                self.table_widget.setColumnWidth(1, 80)
        except Exception:
            pass
        # Agenda um ajuste seguro pós-loop de eventos
        try:
            QTimer.singleShot(0, lambda: self._set_safe_width_for_col_index(1, 80))
        except Exception:
            pass

    def on_filter_error(self, error_msg: str):
        QMessageBox.critical(self, "Erro de Filtro", error_msg)
        self.status_label.setText("Status: Erro ao aplicar filtro.")

    def on_filter_finished_cleanup(self):
        """Limpa estado pós-thread de filtragem com checagens defensivas.

        Em execuções headless/CI alguns widgets podem já ter sido destruídos
        (ex.: fechamento da janela durante teardown de teste), o que pode causar
        abort em chamadas Qt nativas. Garantimos que os atributos existem e que
        o thread já não está em execução antes de manipular.
        """
        # Debug trace para investigação de estabilidade em testes headless
        try:
            progress_bar = getattr(self, "progress_bar", None)
            if progress_bar is not None:
                try:
                    progress_bar.setVisible(False)
                except Exception:
                    pass
            for btn_attr in ("load_button", "search_button"):
                btn = getattr(self, btn_attr, None)
                if btn is not None:
                    try:
                        btn.setEnabled(True)
                    except Exception:
                        pass
            # Garantir finalização adequada do worker de filtro
            worker = getattr(self, "filter_thread", None)
            if worker is not None:
                try:
                    # Desconectar sinais para evitar callbacks tardios
                    try:
                        worker.filter_finished.disconnect(self.on_filter_finished)
                    except Exception:
                        pass
                    try:
                        worker.error_occurred.disconnect(self.on_filter_error)
                    except Exception:
                        pass
                    try:
                        worker.finished.disconnect(self.on_filter_finished_cleanup)
                    except Exception:
                        pass
                    # Solicita término e aguarda brevemente
                    try:
                        if hasattr(worker, 'isRunning') and worker.isRunning():
                            worker.quit()
                            worker.wait(1500)
                    except Exception:
                        pass
                    # Deleta o objeto de forma segura
                    try:
                        worker.deleteLater()
                    except Exception:
                        pass
                finally:
                    self.filter_thread = None
        except Exception:
            # Nunca propagar exceção daqui; log mínimo opcional futuro
            self.filter_thread = None

    def clear_filter(self):
        """Limpa o filtro e mostra todos os dados."""
        try:
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.setText('')
        finally:
            self.search_input.blockSignals(False)
        self._pending_search_display = None
        # self._active_column_filters.clear()  # Comentado para não limpar filtros por coluna
        # Limpa o cache de filtros ao limpar filtros
        self.clear_filter_cache()
        self.df_exibido = self.df_completo.copy()
        self._df_last_search_filtered = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
        self.status_label.setText(f"Status: Filtro limpo. {len(self.df_exibido)} SSAs exibidas.")
        self._build_column_filters_panel()
        # Atualizar resumo de filtros
        try:
            self._update_filters_summary()
        except Exception:
            pass

    # --- Ordenaçção por clique no cabeçalho ---
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
    def _open_add_column_filter_menu(self):
        """Exibe menu com colunas visiveis para ativar filtros dedicados."""
        try:
            from PyQt6.QtWidgets import QMenu
        except Exception:
            return
        if not hasattr(self, '_current_display_columns') or not self._current_display_columns:
            return
        menu = QMenu(self)
        columns = []
        for col in self._current_display_columns:
            if col == '#':
                continue
            display = DEFAULT_DISPLAY_MAPPINGS.get(col, self.internal_to_display.get(col, col))
            action = menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(col in self._active_column_filters)
            action.setData(col)
            columns.append(action)
        if not columns:
            menu.deleteLater()
            return
        chosen = menu.exec(self.add_column_filter_btn.mapToGlobal(self.add_column_filter_btn.rect().bottomLeft()))
        if chosen is None:
            return
        col_name = chosen.data()
        if not col_name:
            return
        if col_name in self._active_column_filters:
            self._deactivate_column_filter(col_name)
        else:
            self._activate_column_filter(col_name)

    def _activate_column_filter(self, col_name: str):
        """Garante entrada para a coluna solicitada e prepara foco na interface."""
        if not col_name:
            return
        if col_name not in self._active_column_filters:
            self._active_column_filters[col_name] = ""
            try:
                self._mark_profile_as_custom()
            except Exception:
                pass
        self._pending_filter_focus = col_name
        self._build_column_filters_panel()


    def _deactivate_column_filter(self, col_name: str):
        """Remove coluna do conjunto de filtros ativos e atualiza a interface."""
        if not col_name:
            return
        removed = False
        if col_name in self._column_to_or_group:
            group = self._column_to_or_group.get(col_name)
            if group:
                for member in group.get('columns', []):
                    if member in self._active_column_filters:
                        self._active_column_filters.pop(member, None)
                        removed = True
                group['values'] = []
        elif col_name in self._active_column_filters:
            self._active_column_filters.pop(col_name, None)
            removed = True
        if not removed:
            return
        try:
            self._mark_profile_as_custom()
        except Exception:
            pass
        self._pending_filter_focus = None
        self._build_column_filters_panel()
        self._refresh_after_filter_change()

    def _build_column_filters_panel(self):
        # Escolhe layout de lista (compatável com versões antigas e novas)
        target_layout = None
        if hasattr(self, 'col_filters_list_layout'):
            target_layout = self.col_filters_list_layout
        elif hasattr(self, 'col_filters_layout'):
            target_layout = self.col_filters_layout
        else:
            return

        # Limpa layout
        while target_layout.count():
            item = target_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._column_filter_inputs = {}
        self._column_filter_labels = {}
        # Controle de linhas ocultas (somente exibição)
        if not hasattr(self, '_hidden_column_filter_lines'):
            self._hidden_column_filter_lines = set()

        if not self._active_column_filters:
            lbl = QLabel("Nenhum filtro por coluna aplicado.")
            lbl.setWordWrap(True)
            target_layout.addWidget(lbl)
            target_layout.addStretch()
            self._column_filter_inputs = {}
            self._column_filter_labels = {}
            self._pending_filter_focus = None
            self._update_col_filter_indicator()
            return


        for col, term in self._active_column_filters.items():
            # Pula linhas ocultas (removidas da exibição)
            if hasattr(self, '_hidden_column_filter_lines') and col in self._hidden_column_filter_lines:
                continue
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            full_name = DEFAULT_DISPLAY_MAPPINGS.get(col, self.internal_to_display.get(col, col))
            name_lbl = QLabel(full_name)
            self._column_filter_labels[col] = name_lbl
            name_lbl.setMinimumWidth(100)
            try:
                name_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            # Exibe 'OU' no campo (apenas visual). Internamente continuamos usando vírgulas.
            try:
                display_text = self._format_column_filter_display_value(str(term), column=col)
            except Exception:
                display_text = str(term)
            term_box = QLineEdit(display_text)
            self._column_filter_inputs[col] = term_box
            # Placeholder sem conectivos OU/AND — OR agora é dedicado
            term_box.setPlaceholderText("Separe termos por vírgulas. Modos: foo, ^pre, suf$, =exato, ~regex, !neg")
            # Reduzido para garantir visibilidade dos botões em telas estreitas
            term_box.setMinimumWidth(220)
            try:
                term_box.setMinimumHeight(26)
            except Exception:
                pass
            try:
                term_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            self._apply_filter_widget_theme(name_lbl, term_box)
            # Enter aplica o filtro desta coluna
            try:
                term_box.returnPressed.connect(lambda c=col, tb=term_box: _mk_apply(c, tb)())
            except Exception:
                pass
            # Botao Aplicar atualiza o filtro com o texto da caixa
            apply_btn = QPushButton("Aplicar")
            try:
                apply_btn.setMinimumHeight(26)
            except Exception:
                pass
            try:
                apply_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                apply_btn.setFixedWidth(72)
            except Exception:
                pass
            def _mk_apply(c=col, tb=term_box):
                def _inner():
                    # Simplified: use text directly (comma-separated terms = OR logic)
                    new_text = str(tb.text()).strip()
                    self._active_column_filters[c] = new_text
                    self._sync_or_group_values(c, new_text)
                    self._mark_profile_as_custom()
                    self._build_column_filters_panel()
                    self._refresh_after_filter_change()
                return _inner
            apply_btn.clicked.connect(_mk_apply())
            # Botão para remover a linha da exibição (não altera o valor do filtro)
            clear_btn = QPushButton("Remover")  # Corrigido capitalização
            try:
                clear_btn.setMinimumHeight(26)
            except Exception:
                pass
            try:
                clear_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                clear_btn.setFixedWidth(72)  # Padronizado com o botão Aplicar
            except Exception:
                pass
            
            def _mk_remove_line(c=col):
                def _inner():
                    try:
                        self._hidden_column_filter_lines.add(c)
                    except Exception:
                        self._hidden_column_filter_lines = {c}
                    # Não altera self._active_column_filters[c]
                    self._build_column_filters_panel()
                    # Não refiltra; apenas exibição
                return _inner
            try:
                clear_btn.clicked.connect(_mk_remove_line())
            except Exception:
                pass
            # Oculta o botão para colunas fixas que não devem ser removidas da exibição
            try:
                fixed_cols = {"descricao_ssa", "setor_executor", "situacao", "localizacao_codigo", "descricao_localizacao"}
                if col in fixed_cols:
                    clear_btn.setVisible(False)
            except Exception:
                pass
            row.addWidget(name_lbl)
            row.addWidget(term_box, 1)
            row.addWidget(apply_btn)
            row.addWidget(clear_btn)
            # Layout order: label, input, Aplicar, Remover (OU button removed - only commas needed)
            row_w = QWidget()
            row_w.setLayout(row)
            target_layout.addWidget(row_w)

        self._update_col_filter_indicator()
        focus_col = self._pending_filter_focus
        if focus_col and focus_col in self._column_filter_inputs:
            try:
                widget = self._column_filter_inputs[focus_col]
                widget.setFocus()
                widget.selectAll()
            except Exception:
                pass
        self._pending_filter_focus = None
        self._refresh_column_filter_widgets()
        # Botção limpar todos
        # Rodape centralizado (se nao houver barra fixa)
        if not hasattr(self, 'clear_all_btn'):
            clear_all = QPushButton("Limpar todos filtros de colunas")
            clear_all.setMaximumWidth(260)
            clear_all.clicked.connect(self._clear_all_column_filters)
            footer = QHBoxLayout()
            footer.addStretch()
            footer.addWidget(clear_all)
            footer.addStretch()
            row_w = QWidget()
            row_w.setLayout(footer)
            target_layout.addWidget(row_w)
        target_layout.addStretch()


    def _apply_filter_widget_theme(self, label_widget=None, input_widget=None):
        theme = getattr(self, '_current_theme', '') or 'dark'
        roles = get_theme_roles(theme)
        label_color = roles.get('support_text_color') or roles.get('label_color')
        if label_widget is not None:
            label_widget.setStyleSheet(f'color:{label_color};')
        if input_widget is not None:
            input_text = roles.get('input_text')
            input_bg = roles.get('input_bg')
            input_border = roles.get('input_border')
            input_focus = roles.get('input_border_focus') or roles.get('accent')
            input_placeholder = roles.get('input_placeholder')
            style = (
                f"QLineEdit {{ font-size:11px; color:{input_text}; background:{input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px; }}\n"
                f"QLineEdit::placeholder {{ color:{input_placeholder}; }}\n"
                f"QLineEdit:focus {{ border:1px solid {input_focus}; }}\n"
            )
            input_widget.setStyleSheet(style)

    def _refresh_column_filter_widgets(self):
        labels = getattr(self, '_column_filter_labels', {}) or {}
        inputs = getattr(self, '_column_filter_inputs', {}) or {}
        for col, label in labels.items():
            self._apply_filter_widget_theme(label, inputs.get(col))
    def _clear_single_column_filter(self, col_name: str, current_text: str = None):
        if col_name in self._active_column_filters:
            # Se já está vazio e o campo também está vazio, não faz nada
            try:
                if str(self._active_column_filters.get(col_name, '')).strip() == '' and (current_text is None or str(current_text).strip() == ''):
                    return
            except Exception:
                pass
            if col_name in self._column_to_or_group:
                self._sync_or_group_values(col_name, "")
            elif col_name in self._active_column_filters:
                self._active_column_filters[col_name] = ""
            self._mark_profile_as_custom()
            self._build_column_filters_panel()
            self._refresh_after_filter_change()

    def _clear_all_column_filters(self):
        if self._active_column_filters:
            for group in getattr(self, '_column_or_groups', []):
                group['values'] = []
                for col in group.get('columns', []):
                    self._active_column_filters[col] = ""
            for col in list(self._active_column_filters.keys()):
                if col not in self._column_to_or_group:
                    self._active_column_filters[col] = ""
            # Restaura linhas ocultas apenas na exibição
            try:
                self._hidden_column_filter_lines.clear()
            except Exception:
                self._hidden_column_filter_lines = set()
            # Limpa também o texto dedicado de OR (somente exibição)
            self._dedicated_or_text = ''
            self._mark_profile_as_custom()
            self._build_column_filters_panel()
            self._refresh_after_filter_change()

    def _on_exclude_ste_sca_toggled(self, checked: bool):
        self._exclude_ste_sca = bool(checked)
        self._mark_profile_as_custom()
        self._refresh_after_filter_change()

    def _clear_all_filters_global(self):
        """Limpa todos os filtros: busca geral + filtros de coluna"""
        # Limpar filtro de busca geral
        self.search_input.clear()
        self._df_last_search_filtered = pd.DataFrame()

        # Limpar todos os filtros de coluna
        if self._active_column_filters:
            self._active_column_filters.clear()
            for k in ("situacao", "setor_executor", "descricao_ssa"):
                self._active_column_filters[k] = ""

        # Resetar para dataset completo
        self.df_exibido = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        # Restaura linhas ocultas e limpa Filtro OU dedicado (exibição)
        try:
            self._hidden_column_filter_lines.clear()
        except Exception:
            self._hidden_column_filter_lines = set()
        self._dedicated_or_text = ''
        self._build_column_filters_panel()
        self._update_col_filter_indicator()

        # Atualizar interface
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs carregadas. Pronto para filtrar.")
        if hasattr(self, 'clear_filter_button'):
            self.clear_filter_button.setEnabled(False)

        # Atualizar resumo de filtros
        self._update_filters_summary()

    def _update_filters_summary(self):
        """Atualiza o resumo de filtros ativos na interface"""
        # Coleta filtros ativos
        active_filters = []

        # Filtro de busca geral
        if hasattr(self, 'search_input') and self.search_input.text().strip():
            active_filters.append(f"Busca: '{self.search_input.text().strip()}'")

        def _display_name(col: str) -> str:
            if col == 'setor_executor':
                return 'Executor'
            if col == 'setor_emissor':
                return 'Emissor'
            if col == 'descricao_ssa':
                return 'Descricao da SSA'
            if col == 'situacao':
                return 'Situacao'
            return self.internal_to_display.get(col, col.replace('_', ' ').title())

        # Filtro OU dedicado (exibição)
        or_text = str(getattr(self, '_dedicated_or_text', '') or '').strip()
        if or_text:
            active_filters.append(f"Filtro OU: {self._format_column_filter_display_value(or_text)}")

        # Filtros de coluna (exibição)
        if hasattr(self, '_active_column_filters') and self._active_column_filters:
            processed_groups = set()
            for group in getattr(self, '_column_or_groups', []):
                if not group.get('values'):
                    continue
                gid = id(group)
                processed_groups.add(gid)
                columns = group.get('columns', [])
                if set(columns) == {'setor_executor', 'setor_emissor'}:
                    label = 'Executor ou Emissor (OU)'
                else:
                    label = f"{' ou '.join(_display_name(c) for c in columns)} (OU)"
                values_txt = self._format_column_filter_display_value(', '.join(group.get('values', [])))
                if values_txt:
                    active_filters.append(f"{label}: {values_txt}")

            for col_name, filter_value in self._active_column_filters.items():
                if col_name in self._column_to_or_group:
                    continue
                normalized_value = self._format_column_filter_display_value(str(filter_value), column=col_name)
                if not normalized_value:
                    continue
                active_filters.append(f"{_display_name(col_name)}: {normalized_value}")

        if getattr(self, '_exclude_ste_sca', False):
            active_filters.append("situacao≠{STE,SCA}")

        # Monta texto do resumo
        if active_filters:
            summary_text = "Filtros ativos: " + "; ".join(active_filters)
        else:
            summary_text = "Nenhum filtro ativo"

        # Atualiza label de resumo principal
        if hasattr(self, 'filters_summary_label'):
            self.filters_summary_label.setText(summary_text)

    def _format_column_filter_display_value(self, raw: str, *, column: str | None = None) -> str:
        """Normaliza um valor de filtro de coluna para exibicao consistente.

        SIMPLIFIED: No logical operators - just comma-separated terms.
        - Splits by commas only
        - Removes extra spaces
        - Maintains markers (^, $, =, ~, !) in tokens
        - Applies optional column aliases for display
        - Returns comma-separated terms (OR logic implicit)
        """
        if not raw:
            return ""
        try:
            text = str(raw).strip()
            # Remove extra spaces
            import re as _re
            text = _re.sub(r'\s+', ' ', text).strip()
            # Split by commas only
            tokens = [t.strip() for t in text.split(',') if t.strip()]
            # Apply optional display aliases per column
            if tokens:
                alias_map = self._get_filter_alias_map()
                mapped: list[str] = []
                col_map = None
                if column and isinstance(alias_map, dict):
                    col_map = alias_map.get(column) or alias_map.get(column.lower())
                global_map = alias_map.get('_global') if isinstance(alias_map, dict) else None
                for tok in tokens:
                    key = tok.casefold()
                    new_tok = None
                    if isinstance(col_map, dict):
                        new_tok = col_map.get(key) or col_map.get(tok)
                    if new_tok is None and isinstance(global_map, dict):
                        new_tok = global_map.get(key) or global_map.get(tok)
                    mapped.append(new_tok if isinstance(new_tok, str) and new_tok.strip() else tok)
                tokens = mapped
            # Display as comma-separated (OR logic)
            return ', '.join(tokens)
        except Exception:
            # Fallback: display raw, trimmed
            return str(raw).strip()

    def _get_filter_alias_map(self) -> dict:
        """Carrega mapeamento opcional de aliases para exibição de filtros de coluna.
        Estrutura esperada (config/filter_aliases.json):
        {
          "_global": { "ste": "STE" },
          "setor_executor": { "svp": "S/P" }
        }
        Chaves de lookup aceitam minúsculas (casefold). Retorna {} se ausente/erro.
        """
        if hasattr(self, '_filter_alias_map') and isinstance(self._filter_alias_map, dict):
            return self._filter_alias_map
        try:
            cfg_path = os.path.join(project_root, 'config', 'filter_aliases.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Normaliza apenas para dict
                if isinstance(data, dict):
                    self._filter_alias_map = data
                    return self._filter_alias_map
        except Exception:
            pass
        self._filter_alias_map = {}
        return self._filter_alias_map

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
        theme_options = [
            ("Escala de cinza", 'grayscale'),
            ("Escuro", 'dark'),
            ("Gruvbox", 'gruvbox'),
            ("One Dark Pro", 'one-dark'),
            ("Dracula", 'dracula'),
            ("Solarized Dark", 'solarized-dark'),
            ("Solarized Light", 'solarized-light'),
            ("Tokyo Night", 'tokyo-night'),
            ("Catppuccin (Mocha)", 'catppuccin'),
            ("Windows 7", 'windows7'),
            ("KDE", 'kde'),
            ("GNOME", 'gnome'),
        ]
        for label, key in theme_options:
            act = menu.addAction(label)
            if act is not None:  # defesa para analise estatica
                trigger = getattr(act, "triggered", None)
                if trigger is not None:
                    try:
                        trigger.connect(partial(self.apply_theme, key))
                    except Exception:
                        pass
        btn = self.sender()
        try:
            if btn is not None:
                menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        except Exception:
            pass

    def apply_theme(self, name: str):
        # get_palette ja importado no topo; fallback silencioso se falhar
        normalized = normalize_theme(name)
        try:
            from PyQt6.QtWidgets import QApplication, QStyleFactory
            app = QApplication.instance()
            if normalized == 'grayscale':
                # Usa a paleta padrão sem depender de QStyleFactory
                if app is not None and hasattr(app, 'style'):
                    style_obj = app.style()
                    palette_factory = getattr(style_obj, 'standardPalette', None)
                    try:
                        pal = palette_factory() if callable(palette_factory) else get_palette(normalized)
                    except Exception:  # noqa: BLE001
                        pal = get_palette(normalized)
                else:
                    pal = get_palette(normalized)
            else:
                pal = get_palette(normalized)
            # Em Windows, alguns estilos ignoram QPalette em QMenu/ToolTip.
            # Ao usar temas personalizados (não-sistema), force "Fusion" para melhor consistência.
            try:
                if app is not None:
                    if normalized not in {'grayscale', 'windows7', 'gnome'}:
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
                    from PyQt6.QtGui import QPalette as _QPal
                    win = pal.color(_QPal.ColorRole.Window).name()
                    wtxt = pal.color(_QPal.ColorRole.WindowText).name()
                    base = pal.color(_QPal.ColorRole.Base).name()
                    text = pal.color(_QPal.ColorRole.Text).name()
                    mid = pal.color(_QPal.ColorRole.Mid).name()
                    hi = pal.color(_QPal.ColorRole.Highlight).name()
                    hitxt = pal.color(_QPal.ColorRole.HighlightedText).name()
                    ttbase = pal.color(_QPal.ColorRole.ToolTipBase).name()
                    tttext = pal.color(_QPal.ColorRole.ToolTipText).name()
                    block = (
                        "/* SSA_THEME_QSS_START */\n"
                        f"QMenu {{ background-color: {win}; color: {wtxt}; border:1px solid {mid}; }}\n"
                        f"QMenu::separator {{ height:1px; background: {mid}; margin:4px 8px; }}\n"
                        f"QMenu::item:selected {{ background-color: {hi}; color: {hitxt}; }}\n"
                        f"QToolTip {{ background-color: {ttbase}; color: {tttext}; border:1px solid {mid}; }}\n"
                        f"QComboBox QAbstractItemView {{ background-color: {base}; color: {text}; selection-background-color: {hi}; selection-color: {hitxt}; }}\n"
                        "/* SSA_THEME_QSS_END */"
                    )
                    existing_qss = app.styleSheet() or ""
                    start = existing_qss.find("/* SSA_THEME_QSS_START */")
                    end = existing_qss.find("/* SSA_THEME_QSS_END */")
                    if start != -1 and end != -1 and end > start:
                        end += len("/* SSA_THEME_QSS_END */")
                        new_qss = existing_qss[:start] + block + existing_qss[end:]
                    else:
                        new_qss = existing_qss + ("\n" if existing_qss else "") + block
                    app.setStyleSheet(new_qss)
                except Exception:
                    pass
            # Garante também na janela atual
            self.setPalette(pal)
        except Exception:  # noqa: BLE001
            pal = get_palette(normalized)
            self.setPalette(pal)
        # Ensure central widget background matches the palette to avoid white boxes
        try:
            central = self.centralWidget()
            if central is not None:
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
                if normalized_name in {'gruvbox', 'dark', 'kde', 'one-dark', 'dracula', 'solarized-dark', 'tokyo-night', 'catppuccin'}:
                    bg = pal.window().color().name()
                    block = (
                        "/* SSA_MAIN_BG_START */\n"
                        f"QWidget {{ background-color: {bg}; }}\n"
                        "/* SSA_MAIN_BG_END */"
                    )
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
        # Ajustes de contraste por tema para rotulos informativos
        self._current_theme = normalized
        try:
            light_themes = {'grayscale', 'windows7', 'gnome', 'solarized-light'}
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

            if hasattr(self, 'search_label'):
                self.search_label.setStyleSheet(f"color: {label_color}; font-weight: 600;")

            if hasattr(self, 'search_input') and self.search_input is not None:
                self.search_input.setStyleSheet(
                    "QLineEdit {"
                    f" color: {input_text}; background: {input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px;"
                    " }"
                    "QLineEdit::placeholder {"
                    f" color: {input_placeholder};"
                    " }"
                    "QLineEdit:focus {"
                    f" border:2px solid {input_focus};"
                    " }"
                )

            if hasattr(self, 'details_text'):
                if normalized in light_themes:
                    self.details_text.setStyleSheet('')
                else:
                    self.details_text.setStyleSheet(
                        "QTextEdit {"
                        f" color: {panel_text}; background: {panel_bg}; border: none; padding:4px;"
                        " }"
                    )

            group_css = (
                "QGroupBox {"
                f" color: {panel_text}; border:1px solid {panel_border}; border-radius:4px; margin-top: 6px;"
                " }"
                "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding:0 3px; }"
            )

            if hasattr(self, 'details_group'):
                if normalized in light_themes:
                    self.details_group.setStyleSheet('')
                else:
                    self.details_group.setStyleSheet(group_css)

            if hasattr(self, 'col_filters_group'):
                if normalized in light_themes:
                    self.col_filters_group.setStyleSheet('')
                else:
                    self.col_filters_group.setStyleSheet(group_css)

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

            if hasattr(self, 'filters_summary_label'):
                self.filters_summary_label.setStyleSheet(f"color:{summary_color};")

            if hasattr(self, 'filters_summary_frame'):
                self.filters_summary_frame.setStyleSheet(
                    "QFrame {"
                    f" background:{summary_bg}; border:1px solid {summary_border}; border-radius:4px; padding:4px;"
                    " }"
                )

            if selector is not None and hasattr(selector, 'summary_label'):
                selector.summary_label.setStyleSheet(f"color:{indicator_color};")

            if hasattr(self, 'col_filters_hint'):
                self.col_filters_hint.setStyleSheet(f"color:{support_color}; font-size: 11px;")
        except Exception:
            pass
        self._refresh_column_filter_widgets()
        # Persistencia
        try:
            # Persistencia simples do tema sem normalizacao adicional
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = normalized
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._apply_macos_contrast(normalized)

    def _update_col_filter_indicator(self):
        # Ativo quando existe ao menos um termo não vazio em filtros por coluna
        active = any((str(v).strip() != "") for _, v in (self._active_column_filters or {}).items())
        txt = "Filtros por coluna: Ativo" if active else "Filtros por coluna: Não ativo"
        if hasattr(self, 'col_filter_indicator'):
            self.col_filter_indicator.setText(txt)

    def show_filter_help(self):
        try:
            dlg = FilterHelpDialog(self)
            dlg.exec()
        except Exception:
            # Em ambientes sem GUI completa, ignore
            pass

    def _collect_profile_columns(self, profiles: dict) -> list:
        cols = []
        for profile_data in profiles.values():
            if isinstance(profile_data, dict):
                all_section = profile_data.get('all') if isinstance(profile_data.get('all'), dict) else None
                if all_section:
                    for col_name in all_section.keys():
                        if col_name not in cols:
                            cols.append(col_name)
                any_section = profile_data.get('any') if isinstance(profile_data.get('any'), list) else None
                if any_section:
                    for group in any_section:
                        columns = group.get('columns') if isinstance(group, dict) else None
                        if isinstance(columns, list):
                            for col_name in columns:
                                if col_name not in cols:
                                    cols.append(col_name)
                # Suporte legado: simples dict coluna->valor
                if not (all_section or any_section):
                    for col_name in profile_data.keys():
                        if col_name not in cols:
                            cols.append(col_name)
            elif isinstance(profile_data, list):
                for col_name in profile_data:
                    if isinstance(col_name, str) and col_name not in cols:
                        cols.append(col_name)
        return cols

    def _initialize_profile_filter_placeholders(self):
        """Garante que colunas monitoradas tenham entradas nas estruturas de filtro."""
        if not isinstance(self._active_column_filters, OrderedDict):
            self._active_column_filters = OrderedDict(self._active_column_filters or {})
        for col in self._profile_columns:
            if col not in self._active_column_filters:
                self._active_column_filters[col] = ""
        # Garante linhas iniciais úteis mesmo sem perfil aplicado
        for default_col in ("setor_executor", "setor_emissor", "descricao_ssa"):
            if default_col not in self._active_column_filters:
                self._active_column_filters[default_col] = ""

    def _reset_or_groups(self):
        self._column_or_groups = []
        self._column_to_or_group = {}

    def _register_or_group(self, columns: list, values: list):
        normalized_columns = [c for c in (columns or []) if isinstance(c, str) and c]
        normalized_values = [str(v).strip() for v in (values or []) if str(v).strip()]
        if not normalized_columns:
            return None
        group = {
            'columns': normalized_columns,
            'values': normalized_values,
        }
        self._column_or_groups.append(group)
        for col in normalized_columns:
            self._column_to_or_group[col] = group
        return group

    def _sync_or_group_values(self, column: str, text: str):
        """Syncs filter values across columns in same OR group.

        SIMPLIFIED: No logical operators - just comma-separated terms.
        """
        group = self._column_to_or_group.get(column)
        if not group:
            return
        normalized = str(text or '').strip()
        # Remove extra spaces, semicolons
        normalized = normalized.replace(';', ',')
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        # Split by commas only
        tokens = [token.strip() for token in normalized.split(',') if token.strip()]
        group['values'] = tokens
        # Store internally as comma-separated list (OR logic)
        common_text = ', '.join(tokens)
        for col in group['columns']:
            self._active_column_filters[col] = common_text

    def _apply_column_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todos os filtros por coluna com as mesmas regras de busca (prefixo ^, sufixo $, =exato, ~regex, !neg)."""
        if df is None or df.empty or not self._active_column_filters:
            return df
        working_df = df
        mask = pd.Series(True, index=working_df.index)
        for col, raw in self._active_column_filters.items():
            if col not in working_df.columns:
                continue
            raw_str = str(raw).strip()
            if not raw_str:
                continue
            col_series = working_df[col].astype(str)
            mask &= self._build_column_mask(col_series, raw_str)

        if mask.all():
            return working_df
        return working_df[mask]

    def _refresh_after_filter_change(self):
        """Reaplica filtros de coluna, atualiza tabela e indicadores."""
        base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
        filtered = self._apply_column_filters(base)
        if getattr(self, '_exclude_ste_sca', False) and not filtered.empty and 'situacao' in filtered.columns:
            try:
                mask = ~filtered['situacao'].astype(str).str.upper().isin({'STE', 'SCA'})
                filtered = filtered[mask]
            except Exception:
                pass
        self.df_exibido = filtered
        self.paginator.set_dataframe(self.df_exibido)
        try:
            current = max(1, min(self.paginator.current_page, self.paginator.total_pages))
            self.display_current_page(current)
        except Exception:
            (lambda cp=max(1, min(getattr(self.paginator, 'current_page', 1), getattr(self.paginator, 'total_pages', 1))): self.display_current_page(cp))()
        self._update_col_filter_indicator()
        try:
            self._update_filters_summary()
        except Exception:
            pass

    def _apply_search_display(self):
        display_text = getattr(self, '_pending_search_display', None)
        if display_text is None:
            return
        try:
            self.search_input.blockSignals(True)
            if display_text:
                self.search_input.setText(display_text)
            else:
                self.search_input.clear()
        finally:
            self.search_input.blockSignals(False)
        self._pending_search_display = None

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

    def _mark_profile_as_custom(self):
        """Marca o perfil atual como personalizado quando filtros divergem."""
        if getattr(self, '_profile_lock', False):
            return
        base = self._profile_base_filters or {}
        base_columns = {k: str(v).strip() for k, v in (base.get('columns') or {}).items()}
        base_groups = base.get('or_groups') or []
        base_exclude = bool(base.get('exclude_ste_sca', False))

        if self.current_filter_profile and self.current_filter_profile in self.filter_profiles:
            mismatch = False
            # Verifica colunas mapeadas
            current_columns = {}
            referenced_columns = set(base_columns.keys()) | set(self._active_column_filters.keys())
            for col in referenced_columns:
                if col in self._column_to_or_group:
                    group = self._column_to_or_group.get(col)
                    current_columns[col] = ', '.join(group.get('values', [])) if group else ''
                else:
                    current_columns[col] = str(self._active_column_filters.get(col, '')).strip()

            for col, expected in base_columns.items():
                if current_columns.get(col, '').strip() != expected:
                    mismatch = True
                    break

            if not mismatch:
                # Valores adicionais além do perfil base
                for col, current in current_columns.items():
                    if col not in base_columns and current.strip():
                        mismatch = True
                        break

            if not mismatch:
                # Compara grupos OR
                def _group_repr(group):
                    cols = tuple(group.get('columns', ()))
                    vals = tuple(group.get('values', ()))
                    return (cols, vals)

                current_groups = sorted(_group_repr(g) for g in getattr(self, '_column_or_groups', []))
                expected_groups = sorted(_group_repr({'columns': g.get('columns', ()), 'values': g.get('values', ())}) for g in base_groups)
                if current_groups != expected_groups:
                    mismatch = True

            if not mismatch and base_exclude != bool(self._exclude_ste_sca):
                mismatch = True

            if not mismatch:
                return
        self.current_filter_profile = None
        self._profile_base_filters = {}
        selector = getattr(self, 'profile_selector', None)
        if selector is not None:
            idx = selector.findData(None)
            if idx >= 0 and selector.currentIndex() != idx:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False

    def _apply_filter_profile(self, profile_name, update_selector=True, refresh=True):
        """Aplica filtros pré-configurados de setor."""
        if not profile_name or profile_name not in self.filter_profiles:
            # Fallback ad-hoc: permite strings como "IEE3 + MEL3 + MEL4" para grupo Executor/Emissor
            try:
                import re as _re
                raw = str(profile_name)
                tokens = [_t.strip() for _t in _re.split(r"[+,]", raw) if _t and _t.strip()]
                if tokens:
                    self._reset_or_groups()
                    self._register_or_group(['setor_executor', 'setor_emissor'], tokens)
                    # Garante colunas monitoradas
                    for _col in ('setor_executor', 'setor_emissor'):
                        if _col not in self._profile_columns:
                            self._profile_columns.append(_col)
                    # Define filtros subjacentes separados por vírgulas (lógica)
                    new_filters = OrderedDict(self._active_column_filters or {})
                    for _col in ('setor_executor', 'setor_emissor'):
                        new_filters[_col] = ', '.join(tokens)
                    self._active_column_filters = new_filters
                    # Base do perfil para marcação de personalizado
                    self._profile_base_filters = {
                        'columns': {c: new_filters.get(c, '') for c in ('setor_executor', 'setor_emissor')},
                        'or_groups': [{'columns': ('setor_executor', 'setor_emissor'), 'values': tuple(tokens)}],
                        'exclude_ste_sca': bool(self._exclude_ste_sca),
                    }
                    self._build_column_filters_panel()
                    if refresh:
                        self._refresh_after_filter_change()
                return
            except Exception:
                return
        profile_def = self.filter_profiles.get(profile_name) or {}
        def normalize_values(value) -> list:
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            if isinstance(value, str):
                return [value.strip()] if value.strip() else []
            if value is None:
                return []
            text = str(value).strip()
            return [text] if text else []

        normalized_columns = OrderedDict()
        normalized_groups = []
        self._reset_or_groups()

        if isinstance(profile_def, dict):
            all_section = profile_def.get('all') if isinstance(profile_def.get('all'), dict) else None
            if all_section:
                for col, value in all_section.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = ', '.join(values_list) if values_list else ''
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
            any_section = profile_def.get('any') if isinstance(profile_def.get('any'), list) else None
            if any_section:
                for group in any_section:
                    if not isinstance(group, dict):
                        continue
                    columns = group.get('columns') if isinstance(group.get('columns'), list) else None
                    values_list = normalize_values(group.get('values'))
                    registered = self._register_or_group(columns, values_list)
                    if registered:
                        display_values = ', '.join(registered['values'])
                        for col in registered['columns']:
                            normalized_columns[col] = display_values
                        for col in registered['columns']:
                            if col not in self._profile_columns:
                                self._profile_columns.append(col)
                        normalized_groups.append({
                            'columns': tuple(registered['columns']),
                            'values': tuple(registered['values'])
                        })
            if not all_section and 'any' not in profile_def:
                for col, value in profile_def.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = ', '.join(values_list) if values_list else ''
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
        else:
            values_list = normalize_values(profile_def)
            if values_list:
                normalized_columns['situacao'] = ', '.join(values_list)
                if 'situacao' not in self._profile_columns:
                    self._profile_columns.append('situacao')

        self._profile_lock = True
        try:
            self.current_filter_profile = profile_name
            new_filters = OrderedDict()
            for col in self._profile_columns:
                new_filters[col] = ""
            for col, text in normalized_columns.items():
                if col not in new_filters:
                    new_filters[col] = text
                else:
                    new_filters[col] = text
            for group in self._column_or_groups:
                group_text = ', '.join(group.get('values', []))
                for col in group.get('columns', []):
                    if col not in new_filters:
                        new_filters[col] = group_text
                    else:
                        new_filters[col] = group_text
            self._active_column_filters = new_filters
            # Garante consistência das strings dos grupos OR (subjacente em vírgulas)
            for group in self._column_or_groups:
                display_group = ', '.join(group.get('values', []))
                for col in group.get('columns', []):
                    self._active_column_filters[col] = display_group
            self._profile_base_filters = {
                'columns': {col: new_filters.get(col, '').strip() for col in new_filters},
                'or_groups': normalized_groups,
                'exclude_ste_sca': bool(self._exclude_ste_sca)
            }
            if update_selector and getattr(self, 'profile_selector', None) is not None:
                idx = self.profile_selector.findData(profile_name)
                if idx >= 0 and self.profile_selector.currentIndex() != idx:
                    self.profile_selector.setCurrentIndex(idx)
        finally:
            self._profile_lock = False
        self._build_column_filters_panel()
        if refresh:
            self._refresh_after_filter_change()

    def _apply_initial_filter_profile(self):
        """Seleciona e aplica o perfil inicial definido em configuração."""
        selector = getattr(self, 'profile_selector', None)
        if selector is None:
            return
        initial_profile = self.default_filter_profile if self.default_filter_profile in self.filter_profiles else None
        if not initial_profile and self.filter_profiles:
            initial_profile = next(iter(self.filter_profiles.keys()))
        if initial_profile:
            self._apply_filter_profile(initial_profile, update_selector=True, refresh=False)
        else:
            idx = selector.findData(None)
            if idx >= 0:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False
        self._build_column_filters_panel()
        self._refresh_after_filter_change()

    def on_profile_changed(self, index):
        """Callback ao trocar o perfil de filtros por setor."""
        if getattr(self, '_profile_lock', False):
            return
        selector = getattr(self, 'profile_selector', None)
        if selector is None:
            return
        profile_name = selector.itemData(index)
        if profile_name:
            self._apply_filter_profile(profile_name, update_selector=False)
        else:
            self.current_filter_profile = None
            self._profile_base_filters = {}

    def _build_column_mask(self, series: pd.Series, raw: str) -> pd.Series:
        # Divide SOMENTE por vírgulas; não há conectivos especiais aqui.
        normalized = str(raw)
        tokens = [t.strip() for t in normalized.split(',') if t.strip()]
        if not tokens:
            return pd.Series([True]*len(series), index=series.index)

        # Determina modo padrao a partir das preferencias
        if not hasattr(self, '_cached_default_mode'):
            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode

        def match_token(s: pd.Series, token: str) -> pd.Series:
            neg = token.startswith('!')
            t = token[1:] if neg else token
            # VAZIOS/NULL: aceita NULL ou =NULL (case-insensitive)
            if t.upper() in ('NULL', '=NULL'):
                # Considera nulos, strings vazias e '-'
                res = s.isna() | (s.str.strip().eq('', na=False)) | (s == '-')
                return ~res if neg else res
            # Regex explácito
            if t.startswith('~') and len(t) > 1:
                try:
                    import re
                    pat = re.compile(t[1:], re.IGNORECASE)
                    res = s.str.contains(pat, na=False)
                except Exception:
                    res = s.str.contains(t[1:], case=False, na=False)
            elif t.startswith('='):
                res = s.str.casefold().eq(t[1:].casefold())
            elif t.startswith('^'):
                res = s.str.casefold().str.startswith(t[1:].casefold())
            elif t.endswith('$'):
                res = s.str.casefold().str.endswith(t[:-1].casefold())
            else:
                if default_mode == 'prefix':
                    res = s.str.casefold().str.startswith(t.casefold())
                elif default_mode == 'suffix':
                    res = s.str.casefold().str.endswith(t.casefold())
                elif default_mode == 'exact':
                    res = s.str.casefold().eq(t.casefold())
                elif default_mode == 'regex':
                    try:
                        import re
                        pat = re.compile(t, re.IGNORECASE)
                        res = s.str.contains(pat, na=False)
                    except Exception:
                        res = s.str.contains(t, case=False, na=False)
                else:  # contains
                    res = s.str.contains(t, case=False, na=False)
            return ~res if neg else res

    # OR entre inclusões no MESMO CAMPO; exclusões (com !) removem
        includes = [tok for tok in tokens if not tok.startswith('!')]
        excludes = [tok for tok in tokens if tok.startswith('!')]

        if includes:
            m = match_token(series, includes[0])
            for tok in includes[1:]:
                m = m | match_token(series, tok)
        else:
            m = pd.Series([True]*len(series), index=series.index)
        for tok in excludes:
            m = m & match_token(series, tok)
        return m

    # --- Helpers: Busca Geral com suporte a OR/AND amigável ---

    def _split_search_expression(self, text: str) -> list[str]:
        # Simplified: General search uses ONLY AND logic (commas separate terms)
        # No OR/OU splitting - returns single chunk containing all terms
        if not text:
            return []
        # Return text as single chunk - will be split by commas in _normalize_chunk_for_parse
        return [text.strip()] if text.strip() else []

    def _normalize_chunk_for_parse(self, chunk: str) -> list[str]:
        # Simplified: Split ONLY by commas (no AND/E/OR/OU keywords)
        # User enters terms separated by commas - all terms are required (AND logic)
        if not chunk:
            return []
        cleaned = str(chunk).strip()
        # Replace em-dash and en-dash with regular dash for consistency
        cleaned = cleaned.replace('–', '-').replace('—', '-')
        # Split by commas only
        tokens = [term.strip() for term in cleaned.split(',') if term.strip()]
        return tokens

    def _format_search_display(self, chunks: list[list[str]]) -> str:
        """Formats search terms for display in search input.

        SIMPLIFIED: Always single chunk (no OU splitting), comma-separated terms.
        All terms are required (AND logic).
        """
        if not chunks:
            return ""
        # Since _split_search_expression now always returns single chunk,
        # we always have chunks[0] with comma-separated terms
        if chunks and chunks[0]:
            return ', '.join(chunks[0])
        return ""

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

    def filter_data(self):  # chama o fluxo novo de filtragem
        try:
            self.initiate_filtering()
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

    def _format_value_for_display(self, value, col=None):
        """Formata valor removendo NaN/None/nan e aplicando formatacao especifica."""
        # Remove valores nulos
        if pd.isna(value) or value is None:
            return ""

        # Converte para string
        text = str(value)

        # Remove variacoes de nan/none
        if text.lower() in ('nan', 'none', 'nat', '<na>'):
            return ""

        # Formatacao especifica por coluna
        if col == 'numero_ssa':
            try:
                return str(int(float(text)))
            except (ValueError, TypeError):
                return text

        return text.strip()

    def _get_current_search_terms(self):
        """Retorna lista de termos de busca atuais."""
        search_text = self.search_input.text().strip()
        if not search_text:
            return []
        # Split por virgulas
        terms = [term.strip() for term in search_text.split(',') if term.strip()]
        # Remove prefixos de modo (^, $, =, ~, !)
        clean_terms = []
        for term in terms:
            # Remove negativos
            if term.startswith('!') or term.startswith('-'):
                term = term[1:]
            # Remove modos
            if term.startswith('~'):
                term = term[1:]
            elif term.startswith('='):
                term = term[1:]
            elif term.startswith('^'):
                term = term[1:]
            elif term.endswith('$'):
                term = term[:-1]
            if term:
                clean_terms.append(term)
        return clean_terms

    def _highlight_text(self, text, terms):
        """Aplica highlight HTML nos termos encontrados no texto."""
        if not text or not terms:
            return text

        # Escapar HTML
        import html
        text_escaped = html.escape(str(text))

        # Aplicar highlight para cada termo
        for term in terms:
            if not term:
                continue
            # Case-insensitive search
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text_escaped = pattern.sub(
                lambda m: f'<span style="background-color: yellow; font-weight: bold;">{m.group()}</span>',
                text_escaped
            )

        return text_escaped

    def _format_details_html(self, series, highlight_search_terms=False):
        """Formata dados da SSA como HTML com highlight opcional."""
        import html as html_module

        # Obtem termos de busca se necessario
        search_terms = self._get_current_search_terms() if highlight_search_terms else []

        html_lines = ['<html><body style="font-family: monospace; font-size: 12pt;">']
        html_lines.append('<table style="width: 100%; border-collapse: collapse;">')

        for col, value in series.items():
            # Formata valor
            formatted_value = self._format_value_for_display(value, col)

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
                f'<td style="padding: 8px; border-bottom: 1px solid #ccc; font-weight: bold; width: 30%; vertical-align: top;">{html_module.escape(display_name)}:</td>'
                f'<td style="padding: 8px; border-bottom: 1px solid #ccc; width: 70%;">{formatted_value}</td>'
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
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)

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

        # Constroi texto formatado sem NaN/None
        lines = []
        for col, value in series.items():
            # Formata valor
            formatted_value = self._format_value_for_display(value, col)

            # Pula campos vazios
            if not formatted_value:
                continue

            # Nome de exibicao
            display_name = DETAIL_DISPLAY_OVERRIDES.get(col, self.internal_to_display.get(col, col))

            lines.append(f"{display_name}: {formatted_value}")

        details_str = "\n".join(lines)
        self.details_text.setPlainText(details_str)

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
        """Reprocessa os arquivos Excel executando o processo principal."""
        self.status_label.setText("Status: Reescaneando dados...")
        self.progress_bar.setVisible(True)
        self.rescan_button.setEnabled(False)

        try:
            # Executa o main.py para reprocessar dados
            main_py_path = os.path.join(project_root, 'main.py')
            if os.path.exists(main_py_path):
                # Executa de forma assáncrona
                result = subprocess.run([
                    sys.executable, main_py_path
                ], capture_output=True, text=True, cwd=project_root)

                if result.returncode == 0:
                    self.status_label.setText("Status: Reescaneamento concluádo. Clique em 'Carregar Dados' para atualizar.")
                    QMessageBox.information(self, "Sucesso", "Reescaneamento concluádo com sucesso!")
                else:
                    self.status_label.setText("Status: Erro no reescaneamento.")
                    QMessageBox.warning(self, "Erro", f"Erro no reescaneamento:\n{result.stderr}")
            else:
                QMessageBox.warning(self, "Erro", f"Arquivo main.py nção encontrado em {main_py_path}")

        except Exception as e:
            self.status_label.setText("Status: Erro no reescaneamento.")
            QMessageBox.critical(self, "Erro", f"Erro ao executar reescaneamento: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.rescan_button.setEnabled(True)

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
            QMessageBox.warning(self, "Erro", f"Pasta nção encontrada: {docs_path}")

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
                    QMessageBox.warning(self, "Erro", "O arquivo selecionado nção contêm dados vãlidos na tabela 'ssas'.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir o banco de dados: {e}")
        elif db_file:  # Arquivo selecionado mas nção existe
            QMessageBox.warning(self, "Erro", "Arquivo selecionado nção existe.")

    def load_persistent_filters(self):
        """Carrega filtros persistentes salvos (inicia vazio)."""
        self.persistent_filters = []
        self.update_filter_tags()

    def save_current_filter(self):
        """Salva o filtro atual como persistente."""
        current_text = self.search_input.text().strip()
        if not current_text:
            QMessageBox.information(self, "Aviso", "Digite um filtro na caixa de pesquisa antes de salvar.")
            return

        # Cria um nome baseado no filtro (limitado para exibiçção)
        filter_name = current_text[:20] + "..." if len(current_text) > 20 else current_text

        # Verifica se jã existe
        for f in self.persistent_filters:
            if f["terms"] == current_text:
                QMessageBox.information(self, "Aviso", "Este filtro jã estã salvo.")
                return

        # Adiciona novo filtro
        new_filter = {"name": filter_name, "terms": current_text}
        self.persistent_filters.append(new_filter)
        self.persistent_filters.sort(key=lambda f: f["name"].casefold())
        self.update_filter_tags()

        QMessageBox.information(self, "Sucesso", f"Filtro '{filter_name}' salvo com sucesso!")

    def update_filter_tags(self):
        """Atualiza as tags visuais dos filtros persistentes."""
        # Remove tags existentes
        for i in reversed(range(self.filter_tags_layout.count())):
            child = self.filter_tags_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

        roles = get_theme_roles(getattr(self, '_current_theme', 'dark'))
        fg = roles.get('summary_text_color', self.palette().windowText().color().name())
        border = roles.get('tag_border')
        bg_normal = roles.get('tag_normal_bg')
        bg_hover = roles.get('tag_hover')
        bg_pressed = roles.get('tag_pressed')

        tag_css = f"""
            QPushButton {{
                color: {fg};
                background-color: {bg_normal};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {bg_pressed};
            }}
        """

        # Adiciona novas tags
        for filter_data in sorted(self.persistent_filters, key=lambda f: f["name"].casefold()):
            tag_button = QPushButton(filter_data["name"])
            tag_button.setMaximumHeight(25)
            tag_button.setStyleSheet(tag_css)
            tag_button.setToolTip(f"Clique para aplicar: {filter_data['terms']}")
            tag_button.clicked.connect(lambda checked, terms=filter_data["terms"]: self.apply_persistent_filter(terms))

            # Botção X para remover
            remove_button = QPushButton("X")
            remove_button.setMaximumSize(20, 20)
            remove_button.setStyleSheet(tag_css)
            remove_button.setToolTip("Remover filtro")
            remove_button.clicked.connect(lambda checked, filter_data=filter_data: self.remove_persistent_filter(filter_data))

            # Layout horizontal para tag + botção remover
            tag_layout = QHBoxLayout()
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setSpacing(2)
            tag_layout.addWidget(tag_button)
            tag_layout.addWidget(remove_button)

            tag_widget = QWidget()
            tag_widget.setLayout(tag_layout)
            self.filter_tags_layout.addWidget(tag_widget)

    def apply_persistent_filter(self, terms):
        """Aplica um filtro persistente."""
        self.search_input.setText(terms)
        self.initiate_filtering()

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

