# gui_ssa.py 20250725 173000 (PoC - GUI PyQt6 para SSA_Consulta_Rapida)
"""
Prova de Conceito Refinada de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Refinamentos em relação à PoC básica:
1. Seleção de colunas com base em display_mappings.json e prioridade.
2. Paginação simples para lidar com grandes conjuntos de dados.
3. Uso de nomes de exibição para colunas.
4. Feedback mais detalhado ao usuário.
5. Estrutura mais preparada para expansão (ordenação, exportação).

Para executar: python gui_ssa.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""

import sys
import os
import pandas as pd
import json
import subprocess
try:
    from utils.version import get_app_version
except Exception:
    def get_app_version():
        return "3.0.7+"

# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importações dos managers unificados
from gui.simple_width_manager import SimpleWidthManager, SimpleCacheManager
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS

# --- Função para Carregar Configurações da GUI Principal ---
def load_gui_main_preferences():
    """Carrega configurações específicas da GUI Principal do arquivo JSON"""
    config_path = os.path.join(project_root, 'config', 'gui_main_preferences.json')
    
    # Configurações padrão caso o arquivo não exista
    default_config = {
        "display_columns": [
            "numero_ssa", "setor_executor", "situacao", "descricao_ssa",
            "data_cadastro", "semana_cadastro", "localizacao_codigo", "grau_prioridade_emissao"
        ],
        "hidden_columns": ["descricao_localizacao", "equipamento", "servico_origem"],
        "column_display_names": {
            "numero_ssa": "Número SSA", "setor_executor": "Exec.",
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
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Valida estrutura mínima
                if isinstance(loaded_config, dict) and 'display_columns' in loaded_config:
                    return loaded_config
                else:
                    print(f"Configuração inválida em {config_path}, usando padrões.")
                    return default_config
        else:
            print(f"Arquivo de configuração não encontrado em {config_path}, usando padrões.")
            return default_config
    except Exception as e:
        print(f"Erro ao carregar configurações da GUI Principal: {e}, usando padrões.")
        return default_config

# Carrega as configurações globalmente
GUI_MAIN_PREFERENCES = load_gui_main_preferences()

from utils.formatting import format_dataframe_for_display

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms
from armazenamento.database import query_db

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
        QMenu, QGroupBox, QTextEdit, QTextBrowser, QFileDialog, QScrollArea, QDialog, QDialogButtonBox,
        QSpacerItem, QSizePolicy
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QItemSelectionModel, QTimer, QEvent
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QApplication
except Exception:
    QT_AVAILABLE = False
    # Stubs mínimos para permitir import em ambiente CI sem libs gráficas
    class _Sig:
        def emit(self, *a, **k):
            pass
        def connect(self, *a, **k):
            pass
    def pyqtSignal(*a, **k):
        return _Sig()
    class QWidget: pass
    class QMainWindow: pass
    class QApplication:
        def __init__(self, *a, **k): pass
        def exec(self): return 0
    class QVBoxLayout: 
        def __init__(self, *a, **k): pass
    class QHBoxLayout(QVBoxLayout): pass
    class QGridLayout(QVBoxLayout): pass
    class QLabel: 
        def __init__(self, *a, **k): pass
    class QPushButton(LABEL:=object):
        def __init__(self, *a, **k): pass
        def clicked(self): return _Sig()
    class QLineEdit: 
        def __init__(self, *a, **k): pass
        def text(self): return ""
    class QTableWidget: pass
    class QTableWidgetItem: 
        def __init__(self, *a, **k): pass
    class QHeaderView: Stretch = 1
    class QMessageBox: pass
    class QProgressBar: pass
    class QComboBox:
        def __init__(self): self._items=[]
        def addItems(self, items): self._items.extend(items)
        def addWidget(self, *a, **k): pass
        def setMinimumWidth(self, *a, **k): pass
    class QSpinBox: pass
    class QAbstractItemView: NoEditTriggers=0
    class QMenu: pass
    class QGroupBox: pass
    class QTextEdit: pass
    class QFileDialog: pass
    class QAction: pass
    class QItemSelectionModel: Select=0
    class QTimer: pass
    class QThread:
        def __init__(self, *a, **k): pass
        def start(self): pass
        def run(self): pass
    class Qt: AlignLeft=0

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssas'
CONFIG_DIR = os.path.join(project_root, 'config')
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'display_mappings.json')

# --- Funções Auxiliares ---

def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibição independente do CLI."""
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
            if df is not None and not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")

class FilterWorker(QThread):
    """Thread para filtrar dados."""
    filter_finished = pyqtSignal(pd.DataFrame) # Emite o DataFrame filtrado
    error_occurred = pyqtSignal(str)

    def __init__(self, df_completo, search_terms, default_mode: str = 'contains'):
        super().__init__()
        self.df_completo = df_completo
        self.search_terms = search_terms
        self.default_mode = default_mode

    def run(self):
        try:
            if self.search_terms:
                parsed = parse_search_terms(self.search_terms, default_mode=self.default_mode)
                df_filtrado = filter_dataframe(self.df_completo, parsed)
            else:
                df_filtrado = self.df_completo.copy()
            self.filter_finished.emit(df_filtrado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao filtrar dados: {e}")

# --- Componentes da GUI ---

class ColumnSelector(QWidget):
    """Widget para selecionar colunas a serem exibidas."""
    columns_changed = pyqtSignal(list) # Emite a lista de colunas selecionadas

    def __init__(self, display_map, initial_columns):
        super().__init__()
        self.display_map = display_map
        self.internal_to_display = {k: v for k, v in display_map.items()}
        self.display_to_internal = {v: k for k, v in display_map.items()}
        
        # Colunas iniciais (internas)
        self.selected_internal_columns = initial_columns
        
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Layout horizontal compacto para adicionar colunas
        add_column_layout = QHBoxLayout()
        
        # ComboBox para adicionar colunas
        add_column_layout.addWidget(QLabel("Adicionar Coluna:"))
        self.add_column_combo = QComboBox()
        self.add_column_combo.setMinimumWidth(150)
        # Preenche com todas as colunas possíveis (baseadas no display_map)
        all_display_names = sorted(self.display_to_internal.keys())
        self.add_column_combo.addItems(all_display_names)
        add_column_layout.addWidget(self.add_column_combo)
        
        add_button = QPushButton("Adicionar")
        add_button.setMaximumWidth(80)
        add_button.clicked.connect(self.add_column)
        add_column_layout.addWidget(add_button)

        # Espaçador para empurrar o status das colunas para a direita
        add_column_layout.addStretch()

        # Status de colunas atual (opcional, comentado por agora)
        # self.selected_columns_label = QLabel("Colunas Atuais: " + ", ".join([self.internal_to_display.get(c, c) for c in self.selected_internal_columns]))
        # self.selected_columns_label.setMaximumWidth(300)
        # add_column_layout.addWidget(self.selected_columns_label)
        
        layout.addLayout(add_column_layout)

    def add_column(self):
        display_name = self.add_column_combo.currentText()
        internal_name = self.display_to_internal.get(display_name)
        if internal_name and internal_name not in self.selected_internal_columns:
            self.selected_internal_columns.append(internal_name)
            self.columns_changed.emit(self.selected_internal_columns)

    def get_selected_columns(self):
        return self.selected_internal_columns


class DataPaginator(QWidget):
    """Widget para paginação de dados."""
    page_changed = pyqtSignal(int) # Emite o número da nova página (1-based)

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

        self.prev_button = QPushButton("Página Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)

        self.page_info_label = QLabel("Página 1 de 1")

        self.next_button = QPushButton("Próxima Página")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)

        # Controle de tamanho da página
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Linhas por Página:"))
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
        if self.df is not None and not self.df.empty:
            self.total_pages = (len(self.df) + self.page_size - 1) // self.page_size
        else:
            self.total_pages = 1
            self.current_page = 1
        # Pode ser chamado antes do init_ui terminar em alguns cenários; proteja acesso
        if hasattr(self, 'page_info_label') and self.page_info_label is not None:
            self.page_info_label.setText(f"Página {self.current_page} de {self.total_pages}")

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
        # Reset para a página 1 ao mudar o tamanho
        self.current_page = 1
        self.update_pagination_info()
        self.update_buttons()
        # Notifica que a página 1 (com novo tamanho) deve ser carregada
        self.page_changed.emit(self.current_page)

    def get_current_slice(self):
        """Retorna o slice do DataFrame para a página atual."""
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.df.iloc[start_idx:end_idx]


# --- Diálogo de Ajuda (GUI PoC revisado) ---
class FilterHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda – Filtros (CLI/GUI)")
        self.setModal(True)
        self.resize(560, 480)
        layout = QVBoxLayout()
        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        app_version = get_app_version() if callable(get_app_version) else "3.0.7+"
        help_text.setHtml(
            """
            <h3>Como usar os filtros</h3>
            <h4>Separação de termos</h4>
            <ul>
              <li><b>Vírgula (,)</b> ou <b>espaço</b> separam múltiplos termos</li>
            </ul>
            <h4>Modos por termo</h4>
            <ul>
              <li><b>contém</b> (padrão): <code>foo</code></li>
              <li><b>começa com</b>: <code>^foo</code></li>
              <li><b>termina com</b>: <code>foo$</code></li>
              <li><b>igual</b>: <code>=foo</code></li>
              <li><b>regex</b>: <code>~foo.*bar</code></li>
              <li><b>negativo</b>: prefixe <code>!</code> (ex.: <code>!^adm</code>, <code>!$2025</code>)</li>
              <li><b>vazios/nulos</b>: <code>=NULL</code> ou <code>NULL</code> (equivale a campo vazio, nulo ou <code>-</code>)</li>
            </ul>
            <h4>Exemplos</h4>
            <ul>
              <li><code>mel3</code> – procura por MEL3</li>
              <li><code>pendente, programar</code> – termos combinados</li>
              <li><code>executada, !mel4</code> – exclui MEL4</li>
              <li><code>g076, amp</code> – combina setores</li>
              <li><code>=NULL</code> – somente campos vazios/nulos</li>
            </ul>
            <h4>Filtro por coluna</h4>
            <p>Abra o menu com <b>clique direito</b> no título da coluna. O painel à direita mostra os filtros por coluna com botões <b>Aplicar</b> e <b>Limpar</b>. Regras idênticas às do filtro geral.</p>
            <h4>Dicas</h4>
            <ul>
              <li>Não diferencia maiúsculas/minúsculas</li>
              <li>Termos parciais funcionam (ex.: <code>exec</code> encontra <i>executada</i>)</li>
              <li>Deixe vazio para ver todas as SSAs</li>
            </ul>
            <hr/>
            <p style='font-size:12px;'>
              <b>Projeto:</b> SSA_Consulta_Rapida • <b>Versão:</b> %s<br/>
              <b>Autor:</b> Mauricio Menon • <b>Repositório:</b> 
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
    Janela principal da aplicacao GUI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Rápida de SSAs - GUI Principal")
        self.setGeometry(100, 100, 1200, 800)

        self.df_completo = pd.DataFrame()
        self.df_exibido = pd.DataFrame()  # DataFrame filtrado
        self.df_para_tabela = pd.DataFrame()  # DataFrame paginado para exibição

        # Carrega mapeamentos de exibição das preferências da GUI principal
        self.display_map = GUI_MAIN_PREFERENCES.get("display_mappings", load_display_mappings())
        self.internal_to_display = {k: v for k, v in self.display_map.items()}

        # Colunas padrão para exibição (das configurações JSON)
        self.default_columns = GUI_MAIN_PREFERENCES.get("display_columns", [
            'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
            'data_cadastro', 'semana_cadastro'
        ])
        
        # Garante que colunas padrão existam no mapeamento
        self.visible_columns = [col for col in self.default_columns if col in self.internal_to_display or col == '#']

        # Configurações de GUI (independentes do CLI)
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        self._restored_page_size = gui_settings.get("page_size", 50)
        
        # Inicializa managers unificados (substitui código frankenstein)
        self.width_manager = SimpleWidthManager()
        self.cache_manager = SimpleCacheManager()

        # Estado de ordenação e filtros por coluna
        self.sort_column = None
        self.sort_ascending = True
        self._active_column_filters = {}
        self._df_last_search_filtered = pd.DataFrame()
        
        # Larguras salvas por coluna (das configurações JSON) - mantido para compatibilidade
        self._saved_gui_column_widths = GUI_MAIN_PREFERENCES.get("column_widths", {}).copy()

        # Debounce de filtro (da configuração JSON)
        debounce_delay = gui_settings.get("debounce_delay", 250)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_delay)
        self._debounce_timer.timeout.connect(self.initiate_filtering)

        # Filtros persistentes
        self.persistent_filters = []

        self.init_ui()

        # Carrega filtros após a GUI estar configurada
        self.load_persistent_filters()
        # Pré-habilitar entradas vazias para Situação e Executor no painel
        for key in ("situacao", "setor_executor"):
            if key in self.internal_to_display and key not in self._active_column_filters:
                self._active_column_filters[key] = ""
        # Atualiza painel com filtros pré-exibidos
        try:
            self._build_column_filters_panel()
        except Exception:
            pass

        # Auto-carregar dados na abertura (assíncrono via worker)
        # Auto-load sempre habilitado (robusto e responsivo)
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
        # Semana Atual (YYYYWW) ao lado de 'Abrir Pasta' (informativo, não clicável)
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
        self.week_label.setToolTip("Semana ISO atual (não clicável)")
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

        # Botão de Ajuda (como na PoC)
        help_button = QPushButton("Ajuda")
        help_button.setToolTip("Ajuda sobre filtros e uso da interface")
        help_button.clicked.connect(self.show_filter_help)
        toolbar_layout.addWidget(help_button)

        main_layout.addLayout(toolbar_layout)

        # Margem superior da faixa de pesquisa (simétrica com base)
        main_layout.addSpacing(6)

        # --- Barra de Pesquisa e Filtros (grupos esquerda/direita) ---
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)

        left = QHBoxLayout(); left.setContentsMargins(0, 0, 0, 0)
        self.search_label = QLabel("Pesquisar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Termos por vírgula. Modos: foo, ^pre, suf$, =exato, ~regex, !neg")
        self.search_input.setToolTip(
            "Modos por termo: \n"
            "- contém (padrão): foo\n- começa com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex: ~foo.*bar\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
        )
        self.search_input.setMinimumWidth(260)
        self.search_input.setMaximumWidth(600)
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

        right = QHBoxLayout(); right.setContentsMargins(0, 0, 0, 0)
        self.column_selector = ColumnSelector(self.display_map, self.visible_columns)
        self.column_selector.columns_changed.connect(self.on_columns_changed)
        right.addWidget(self.column_selector)

        search_row.addLayout(left)
        # Espaçador expansível garante que o grupo da direita encoste no limite direito
        search_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        search_row.addLayout(right)
        main_layout.addLayout(search_row)

        # Ajuda compacta do filtro global (linha curta abaixo da pesquisa)
        help_line = QHBoxLayout()
        help_line.setContentsMargins(0, 0, 0, 0)
        self.search_help = QLabel("Termos: ^pre, suf$, =exato, ~regex, !neg — múltiplos por vírgula")
        self.search_help.setWordWrap(True)
        self.search_help.setStyleSheet("font-size: 10px; color: palette(mid);")
        self.search_help.setMaximumWidth(680)
        self.search_help.setMaximumHeight(18)
        help_line.addWidget(self.search_help)
        help_line.addStretch()
        main_layout.addLayout(help_line)
        # Espaço para destacar a faixa de pesquisa (simétrico com o topo)
        main_layout.addSpacing(6)

        # --- Paginador e Filtros Persistentes ---
        pagination_filters_layout = QHBoxLayout()
        
        # Paginador
        self.paginator = DataPaginator(self.df_para_tabela)
        self.paginator.page_changed.connect(self.display_current_page)
        pagination_filters_layout.addWidget(self.paginator)
        
        # Espaçamento entre paginador e filtros
        pagination_filters_layout.addSpacing(20)
        
        # Área de filtros persistentes
        self.persistent_filters_layout = QHBoxLayout()
        self.persistent_filters_layout.setContentsMargins(0, 0, 0, 0)
        
        save_filter_button = QPushButton("Salvar Filtro")
        save_filter_button.setMaximumWidth(100)
        save_filter_button.setToolTip("Salvar filtro atual como persistente")
        save_filter_button.clicked.connect(self.save_current_filter)
        self.persistent_filters_layout.addWidget(save_filter_button)
        
        # Container para tags de filtros
        self.filter_tags_widget = QWidget()
        self.filter_tags_layout = QHBoxLayout(self.filter_tags_widget)
        self.filter_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_tags_layout.setSpacing(5)
        self.persistent_filters_layout.addWidget(self.filter_tags_widget)
        
        pagination_filters_layout.addLayout(self.persistent_filters_layout)
        pagination_filters_layout.addStretch()
        
        main_layout.addLayout(pagination_filters_layout)
        
        # Restaura page size se configurado
        if isinstance(self._restored_page_size, int) and 10 <= self._restored_page_size <= 500:
            self.paginator.page_size_spinbox.setValue(self._restored_page_size)
        # Persiste alterações do page size
        self.paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)

        # --- Tabela de Dados ---
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Começa como Interativo; após preencher a página, aplicamos larguras fixas para estabilidade
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_widget.verticalHeader().setVisible(False)
        
        # CORREÇÃO v3.0.5: Performance otimizada - removido word wrap global e resize automático
        # Word wrap causa lentidão extrema em grandes datasets
        # self.table_widget.setWordWrap(True)  # ← REMOVIDO - causava travamentos
        
        # Altura fixa otimizada ao invés de resize automático
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_widget.verticalHeader().setDefaultSectionSize(24)  # Altura fixa otimizada

        # Conecta clique duplo para mostrar detalhes (placeholder)
        self.table_widget.doubleClicked.connect(self.on_table_double_click)
        # Atualiza painel de detalhes quando a seleção muda
        self.table_widget.itemSelectionChanged.connect(self.update_details_from_selection)
        # Salva largura quando usuário redimensionar uma coluna
        self.table_widget.horizontalHeader().sectionResized.connect(self._on_header_section_resized)
        
        # Ordenação por clique no cabeçalho + menu de filtro por coluna
        try:
            header = self.table_widget.horizontalHeader()
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(True)
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

        # --- Painel de Detalhes + Painel de Filtros por Coluna (com rodapé fixo) ---
        bottom_layout = QHBoxLayout()

        # Detalhes (maior)
        self.details_group = QGroupBox("Detalhes da SSA Selecionada")
        details_layout = QVBoxLayout(self.details_group)
        self.details_text = QTextEdit(); self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        bottom_layout.addWidget(self.details_group, 5)

        # Filtros por Coluna com lista rolável + rodapé fixo
        self.col_filters_group = QGroupBox("Filtros por Coluna")
        col_filters_outer = QVBoxLayout(self.col_filters_group)
        from PyQt6.QtWidgets import QScrollArea
        self.col_filters_scroll = QScrollArea(); self.col_filters_scroll.setWidgetResizable(True)
        self.col_filters_container = QWidget()
        self.col_filters_list_layout = QVBoxLayout(self.col_filters_container)
        self.col_filters_scroll.setWidget(self.col_filters_container)
        col_filters_outer.addWidget(self.col_filters_scroll, 1)
        # Rodapé fixo
        footer = QHBoxLayout(); footer.addStretch()
        self.clear_all_btn = QPushButton("Limpar todos filtros de colunas")
        self.clear_all_btn.setMaximumWidth(260)
        self.clear_all_btn.clicked.connect(self._clear_all_column_filters)
        footer.addWidget(self.clear_all_btn); footer.addStretch()
        col_filters_outer.addLayout(footer)

        self._build_column_filters_panel()
        bottom_layout.addWidget(self.col_filters_group, 4)

        # Respiro antes do bloco inferior
        main_layout.addSpacing(12)
        main_layout.addLayout(bottom_layout)

        # --- Conecta Workers ---
        self.data_loader_thread = None
        self.filter_thread = None

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        # Chamar start() novamente reinicia o QTimer automaticamente
        self._debounce_timer.start()

    # --- Slots e Handlers ---

    def load_data(self):
        if not os.path.exists(DB_PATH):
            QMessageBox.warning(self, "Erro", f"Banco de dados '{DB_PATH}' não encontrado. Execute o programa principal primeiro.")
            return

        self.status_label.setText("Status: Carregando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        self.data_loader_thread = DataLoaderWorker(DB_PATH, TABLE_NAME)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_load_error)
        self.data_loader_thread.finished.connect(self.on_load_finished)
        self.data_loader_thread.start()

    def on_data_loaded(self, df: pd.DataFrame):
        self.df_completo = df.copy()
        # Inicialmente, exibimos todos os dados
        base = df.copy()
        # Ordenação padrão: não-STE primeiro; depois número SSA desc
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
        # Atualiza o paginador com o DataFrame completo
        self.paginator.set_dataframe(self.df_exibido)
        # Exibe a primeira página
        self.display_current_page(1)
        self.status_label.setText(f"Status: {len(self.df_completo)} SSAs carregadas. Pronto para filtrar.")
        self.clear_filter_button.setEnabled(True)

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
        self.data_loader_thread = None

    def initiate_filtering(self):
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        search_text = self.search_input.text().strip()
        search_terms = []
        if search_text:
            search_terms = [term.strip() for term in search_text.split(',') if term.strip()]

        self.status_label.setText("Status: Filtrando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Descobre default_mode nas configurações JSON (OTIMIZAÇÃO: usando cache)
        if not hasattr(self, '_cached_default_mode'):
            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode
        
        # Inicia a thread de filtragem
        self.filter_thread = FilterWorker(self.df_completo, search_terms, default_mode=default_mode)
        self.filter_thread.filter_finished.connect(self.on_filter_finished)
        self.filter_thread.error_occurred.connect(self.on_filter_error)
        self.filter_thread.finished.connect(self.on_filter_finished_cleanup)
        self.filter_thread.start()

    def on_filter_finished(self, df_filtrado: pd.DataFrame):
        # Atualiza baseline do resultado da busca global
        self._df_last_search_filtered = df_filtrado.copy()
        # Aplica filtros por coluna, se houver
        df_final = self._df_last_search_filtered
        if self._active_column_filters:
            try:
                for c, term in list(self._active_column_filters.items()):
                    if c in df_final.columns and term:
                        df_final = df_final[df_final[c].astype(str).str.contains(str(term), case=False, na=False)]
            except Exception:
                pass
        self.df_exibido = df_final
        # Atualiza o paginador com o DataFrame filtrado
        self.paginator.set_dataframe(self.df_exibido)
        # OTIMIZAÇÃO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        # Exibe a primeira página dos resultados filtrados (larguras serão calculadas lá)
        self.display_current_page(1)
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas.")

    def on_filter_error(self, error_msg: str):
        QMessageBox.critical(self, "Erro de Filtro", error_msg)
        self.status_label.setText("Status: Erro ao aplicar filtro.")

    def on_filter_finished_cleanup(self):
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.filter_thread = None

    def clear_filter(self):
        """Limpa o filtro e mostra todos os dados."""
        self.search_input.clear()
        self._active_column_filters.clear()
        self.df_exibido = self.df_completo.copy()
        self._df_last_search_filtered = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        self.status_label.setText(f"Status: Filtro limpo. {len(self.df_exibido)} SSAs exibidas.")
        self._build_column_filters_panel()

    # --- Ordenação por clique no cabeçalho ---
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
            # Ignora a coluna de índice
            if col_name == '#':
                return

            # Alterna direção ao clicar na mesma coluna
            if getattr(self, 'sort_column', None) == col_name:
                self.sort_ascending = not getattr(self, 'sort_ascending', True)
            else:
                self.sort_column = col_name
                self.sort_ascending = True

            # Ordena resultado filtrado atual e reinicia paginação
            try:
                self.df_exibido = self.df_exibido.sort_values(
                    by=self.sort_column,
                    ascending=self.sort_ascending,
                    na_position='last'
                )
            except Exception:
                pass

            self.paginator.set_dataframe(self.df_exibido)
            self.display_current_page(1)

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

            def _recompute_and_refresh():
                base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
                df = self._apply_column_filters(base)
                self.df_exibido = df
                self.paginator.set_dataframe(self.df_exibido)
                self.display_current_page(1)
                self._build_column_filters_panel()

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
                    self._active_column_filters[col_name] = str(term)
                    _recompute_and_refresh()

            def _clear():
                if col_name in self._active_column_filters:
                    del self._active_column_filters[col_name]
                    _recompute_and_refresh()

            def _clear_all():
                if self._active_column_filters:
                    self._active_column_filters.clear()
                    _recompute_and_refresh()

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
                # Qt6: MouseButtonPress com botão direito
                if et == QEvent.Type.MouseButtonPress:
                    btn = getattr(event, 'button', lambda: None)()
                    if btn == Qt.MouseButton.RightButton:
                        # Compatível com position() (Qt6) e pos()
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

    # --- Helpers: painel e aplicação dos filtros por coluna ---
    def _build_column_filters_panel(self):
        # Escolhe layout de lista (compatível com versões antigas e novas)
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

        if not self._active_column_filters:
            lbl = QLabel("Nenhum filtro por coluna aplicado.")
            lbl.setWordWrap(True)
            target_layout.addWidget(lbl)
            target_layout.addStretch()
            return

        for col, term in self._active_column_filters.items():
            row = QHBoxLayout()
            name_lbl = QLabel(self.internal_to_display.get(col, col))
            name_lbl.setMinimumWidth(140)
            term_box = QLineEdit(str(term))
            term_box.setPlaceholderText("Termos: ^pre, suf$, =exato, ~regex, !neg")
            # Botão Aplicar atualiza o filtro com o texto da caixa
            apply_btn = QPushButton("Aplicar")
            def _mk_apply(c=col, tb=term_box):
                def _inner():
                    self._active_column_filters[c] = tb.text().strip()
                    base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
                    self.df_exibido = self._apply_column_filters(base)
                    self.paginator.set_dataframe(self.df_exibido)
                    self.display_current_page(1)
                return _inner
            apply_btn.clicked.connect(_mk_apply())
            # Botão Limpar remove o filtro da coluna
            clear_btn = QPushButton("Limpar")
            def _mk_clear(c=col):
                return lambda: self._clear_single_column_filter(c)
            clear_btn.clicked.connect(_mk_clear())
            row.addWidget(name_lbl)
            row.addWidget(term_box, 1)
            row.addWidget(apply_btn)
            row.addWidget(clear_btn)
            row_w = QWidget()
            row_w.setLayout(row)
            target_layout.addWidget(row_w)

        # Botão limpar todos
        # Rodapé centralizado (se não houver barra fixa)
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

    def _clear_single_column_filter(self, col_name: str):
        if col_name in self._active_column_filters:
            del self._active_column_filters[col_name]
            base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
            self.df_exibido = self._apply_column_filters(base)
            self.paginator.set_dataframe(self.df_exibido)
            self.display_current_page(1)
            self._build_column_filters_panel()

    def _clear_all_column_filters(self):
        if self._active_column_filters:
            self._active_column_filters.clear()
            base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
            self.df_exibido = base.copy()
            self.paginator.set_dataframe(self.df_exibido)
            self.display_current_page(1)
            self._build_column_filters_panel()

    def show_filter_help(self):
        try:
            dlg = FilterHelpDialog(self)
            dlg.exec()
        except Exception:
            # Em ambientes sem GUI completa, ignore
            pass

    def _apply_column_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todos os filtros por coluna com as mesmas regras de busca (prefixo ^, sufixo $, =exato, ~regex, !neg)."""
        if df is None or df.empty or not self._active_column_filters:
            return df
        out = df
        for col, raw in self._active_column_filters.items():
            if col not in out.columns or not str(raw).strip():
                continue
            mask = self._build_column_mask(out[col].astype(str), str(raw).strip())
            out = out[mask]
        return out

    def _build_column_mask(self, series: pd.Series, raw: str) -> pd.Series:
        # Divide por vírgulas ou espaços
        tokens = [t.strip() for t in raw.replace('\n',' ').split(',')]
        tokens = [t for tok in tokens for t in tok.split() if t]
        if not tokens:
            return pd.Series([True]*len(series), index=series.index)

        # Determina modo padrão a partir das preferências
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
            # Regex explícito
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

        # OR entre inclusões; exclusões (com !) removem
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

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleção de colunas muda."""
        self.visible_columns = new_columns
        # Reexibe a página atual com as novas colunas
        self.display_current_page(self.paginator.current_page)
        # Nota: Persistência de preferências removida para isolamento do CLI
        # As configurações ficam no arquivo gui_main_preferences.json

    def display_current_page(self, page_number):
        """Exibe a página especificada do DataFrame filtrado."""
        # Obtem o slice de dados para a página atual do paginator
        self.df_para_tabela = self.paginator.get_current_slice()

        if self.df_para_tabela.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        # Seleciona apenas as colunas visíveis
        cols_to_show = [col for col in self.visible_columns if col in self.df_para_tabela.columns]
        if not cols_to_show:
            # Se nenhuma coluna selecionada for valida, mostra as padroes
            cols_to_show = [col for col in self.default_columns if col in self.df_para_tabela.columns]
            if not cols_to_show:
                # Ultimo recurso: mostra todas
                cols_to_show = self.df_para_tabela.columns.tolist()

        # Mantém a ordem EXATA definida em gui_main_preferences.json
        # Sem reordenação para garantir correspondência com as larguras calculadas

        display_df = self.df_para_tabela[cols_to_show].copy()
        # Mantém colunas atuais para mapear índice->nome ao salvar larguras
        self._current_display_columns = ['#'] + list(display_df.columns)

        # Adiciona a coluna de índice '#'
        if '#' not in display_df.columns:
            display_df.insert(
                0,
                '#',
                range(
                    (self.paginator.current_page - 1) * self.paginator.page_size + 1,
                    (self.paginator.current_page - 1) * self.paginator.page_size + 1 + len(display_df)
                ),
            )

        # Aplica formatação compartilhada para exibição (datas, numeros, SSA, nulls)
        # OTIMIZAÇÃO: Cache formatação para evitar reformatar dados inalterados
        display_df_hash = hash(str(display_df.shape) + str(list(display_df.columns)) + str(display_df.iloc[0].values.tobytes() if len(display_df) > 0 else ''))
        
        # Usa CacheManager unificado para cache de DataFrame formatado
        cached_formatted = self.cache_manager.get_cached_formatted_df(display_df_hash)
        if cached_formatted is None:
            try:
                formatted_df = format_dataframe_for_display(display_df)
                self.cache_manager.cache_formatted_df(display_df_hash, formatted_df)
                display_df = formatted_df
            except Exception:
                # falha de formatação não deve quebrar a GUI; segue sem formatar
                pass
        else:
            # Usa versão formatada do cache
            display_df = cached_formatted

    # Configura a tabela
        self.table_widget.setRowCount(len(display_df))
        self.table_widget.setColumnCount(len(display_df.columns))

        # Define cabeçalhos de exibição com indicador de filtro [f] por coluna
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

        columns_list = list(display_df.columns)
        for row_idx in range(len(display_df)):
            row_data = display_df.iloc[row_idx]
            for col_idx, col_name in enumerate(columns_list):
                value = row_data.iloc[col_idx]
                item_text = "" if pd.isna(value) else str(value)

                # CORREÇÃO v3.0.5: Não truncar colunas de descrição e solicitante - deixar word wrap funcionar
                if col_name not in ['descricao_ssa', 'descricao_execucao', 'solicitante']:
                    # Trunca apenas colunas que não são de descrição
                    max_chars = self._calculate_max_chars_for_column(col_name, col_idx)
                    if len(item_text) > max_chars:
                        item_text = item_text[:max_chars-3] + "..."

                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                # Armazena o índice da linha original nos dados filtrados para referência
                if col_name == '#':
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        row_idx + (self.paginator.current_page - 1) * self.paginator.page_size,
                    )
                self.table_widget.setItem(row_idx, col_idx, item)

        # Sempre recalcula larguras best-fit para otimizar espaço
        # OTIMIZAÇÃO: Só recalcula se necessário (novo dataset ou resize)
        current_df_hash = hash(str(display_df.shape) + str(list(display_df.columns)))
        if not hasattr(self, '_widths_computed_for_df_hash') or self._widths_computed_for_df_hash != current_df_hash:
            self._compute_gui_column_widths(display_df)
            self._widths_computed_for_df_hash = current_df_hash
            
        # Configura header como Interactive para permitir larguras customizadas
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
        for i, col_name in enumerate(display_df.columns):
            # Usa a coluna diretamente do DataFrame (que já inclui '#')
            col_key = col_name
                
            px = getattr(self, '_gui_column_pixel_widths', {}).get(col_key)
            
            # Se não há largura calculada, usa configuração salva manualmente pelo usuário
            if px is None:
                px = self._saved_gui_column_widths.get(col_key)
            
            # Fallbacks apenas se nenhuma das anteriores estiver disponível
            if px is None:
                if col_key == '#':
                    px = 30
                elif col_key == 'numero_ssa':
                    px = 93  # 11 chars * 7 + 16
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
                    px = 280  # Menor que descrição_ssa
                else:
                    px = 80  # Fallback geral
            
            # Aplica limites de segurança apenas
            px = max(30, min(int(px), 1000))  # Permite larguras maiores para descriptions
            
            # print(f"DEBUG: Aplicando largura {px}px para coluna '{col_key}' (índice {i})")
            self.table_widget.setColumnWidth(i, px)
            
        # CORREÇÃO: Desabilitado temporariamente para evitar conflitos com best-fit
        # QTimer.singleShot(100, self._force_column_widths)

        # Seleciona a primeira linha (se houver) e atualiza detalhes
        if self.table_widget.rowCount() > 0:
            self.table_widget.selectRow(0)
        self.update_details_from_selection()

    def _force_column_widths(self):
        """Força reaplicação das larguras das colunas para garantir que sejam respeitadas."""
        if not hasattr(self, 'visible_columns') or not self.visible_columns:
            return
            
        for i, col_name in enumerate(['#'] + self.visible_columns):
            # Busca largura salva das configurações
            px = self._saved_gui_column_widths.get(col_name)
            if px is not None:
                current_width = self.table_widget.columnWidth(i)
                if current_width != px:
                    self.table_widget.setColumnWidth(i, int(px))

    def _compute_gui_column_widths(self, df: pd.DataFrame):
        """
        Calcula larguras de colunas usando o WidthManager unificado.
        Substitui 150+ linhas de código frankenstein por uma chamada limpa.
        """
        try:
            # Garante que visible_columns esteja definido
            if not hasattr(self, 'visible_columns') or not self.visible_columns:
                return
            
            # CORREÇÃO CRÍTICA: Filtra visible_columns para incluir apenas colunas que EXISTEM no DataFrame
            if hasattr(df, 'columns'):
                existing_visible_cols = [col for col in self.visible_columns if col in df.columns]
                if not existing_visible_cols:
                    print("ERRO: Nenhuma coluna visível encontrada no DataFrame")
                    return
                
                # IMPORTANTE: Mantém a ordem exata de self.visible_columns
                visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
            else:
                visible_df = df
            
            # Obtém largura da tabela
            widget_width = self.table_widget.width()
            viewport_width = self.table_widget.viewport().width()
            
            if widget_width < 500:  # Tabela ainda não inicializada
                table_width = max(1400, self.width() - 50)
            else:
                table_width = widget_width - 40  # Margem para scrollbars
            
            # Garante largura mínima para funcionamento adequado
            table_width = max(table_width, 1400)
            
            # Usa o WidthManager para calcular larguras otimizadas  
            # IMPORTANTE: Força ordem correta das colunas (adiciona '#' no início)
            correct_column_order = ['#'] + existing_visible_cols
            column_widths = self.width_manager.compute_optimal_widths(
                df=visible_df,
                available_width=table_width,
                display_mappings=self.internal_to_display,
                saved_widths=self._saved_gui_column_widths,
                column_order=correct_column_order
            )
            
            # Mantém compatibilidade com código existente
            self._gui_column_pixel_widths = column_widths
            
        except Exception as e:
            print(f"ERRO em _compute_gui_column_widths: {e}")
            # Fallback para larguras mínimas das colunas visíveis apenas
            visible_cols = ['#'] + (self.visible_columns if hasattr(self, 'visible_columns') else [])
            self._gui_column_pixel_widths = {col: 100 for col in visible_cols}

    def _calculate_max_chars_for_column(self, col_name: str, col_idx: int) -> int:
        """Calcula o número máximo de caracteres baseado na largura da coluna."""
        try:
            # Usa largura calculada pelo WidthManager ou largura atual da coluna
            width_px = getattr(self, '_gui_column_pixel_widths', {}).get(col_name)
            if width_px is None:
                width_px = self.table_widget.columnWidth(col_idx)
            
            # Converte pixels em caracteres (aproximadamente 7px por caractere)
            max_chars = max(15, int((width_px - 10) / 6.5))  # Melhores proporções
            
            # Limites específicos por tipo de coluna
            if col_name in ['descricao_ssa', 'descricao_execucao']:
                # Descrições podem usar toda largura disponível
                max_chars = max(50, max_chars)  # Mínimo mais alto para descrições
            elif col_name in ['numero_ssa', 'localizacao_codigo']:
                # Campos curtos não precisam de muito espaço
                max_chars = min(max_chars, 25)
            elif col_name == 'solicitante':
                # Solicitante deve caber pelo menos "MAURICIO MENON"
                max_chars = max(15, max_chars)  # Garante pelo menos 15 caracteres
            else:
                # Campos gerais - mais generoso
                max_chars = min(max_chars, 80)  # Limite mais alto
                
            return max_chars
        except:
            # Fallback mais generoso
            return 80

    def _on_header_section_resized(self, logical_index: int, old_size: int, new_size: int):
        """Salva a largura ajustada pelo usuário na configuração persistente."""
        try:
            cols = getattr(self, '_current_display_columns', None)
            if not cols or logical_index < 0 or logical_index >= len(cols):
                return
            col_name = cols[logical_index]
            # Persist only reasonable sizes
            new_px = max(30, min(int(new_size), 1200))
            # Atualiza cache local - TEMPORARIAMENTE DESABILITADO para usar larguras fixas
            # self._saved_gui_column_widths[col_name] = new_px
            # Nota: Persistência removida para isolamento do CLI
            # As larguras ficam configuradas no arquivo gui_main_preferences.json
        except Exception:
            # Evita quebrar a GUI por falhas de IO
            pass

    def on_table_double_click(self, index):
        """Placeholder para ação de clique duplo (ex: mostrar detalhes)."""
        row = index.row()
        # O item da coluna '#' contém o índice da linha original
        index_item = self.table_widget.item(row, 0)  # Assume '#' é a primeira coluna
        if index_item:
            original_index = index_item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None and 0 <= original_index < len(self.df_exibido):
                # Aqui você chamaria uma função para mostrar detalhes
                # Ex: show_details_window(self.df_exibido.iloc[original_index])
                QMessageBox.information(
                    self,
                    "Detalhes",
                    f"Detalhes para SSA na linha {original_index + 1} (página {self.paginator.current_page})\n"
                    f"Dados: {self.df_exibido.iloc[original_index].to_dict()}",
                )
            else:
                QMessageBox.information(self, "Info", "Não foi possível encontrar os dados detalhados para esta linha.")

    def _save_page_size_pref(self, new_size: int):
        """Persiste o tamanho da página no settings."""
        # Nota: Persistência removida para isolamento do CLI
        # O tamanho da página fica configurado no arquivo gui_main_preferences.json
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

        # Usa dados originais (não formatados) para detalhes
        series = self.df_exibido.iloc[int(original_index)]
        # Constrói um texto amigável com nomes de exibição
        lines = []
        for col, value in series.items():
            display_name = self.internal_to_display.get(col, col)
            # Mostra numero_ssa "natural" (int se possível)
            if col == 'numero_ssa':
                try:
                    if pd.notna(value):
                        value = int(value)
                except Exception:
                    pass
            text = "" if pd.isna(value) else str(value)
            lines.append(f"{display_name}: {text}")
        details_str = "\n".join(lines)
        self.details_text.setPlainText(details_str)

    def show_context_menu(self, position):
        """Mostra menu de contexto na tabela."""
        if self.table_widget.itemAt(position):
            menu = QMenu(self)
            
            # Ações para células
            copy_cell_action = QAction("Copiar Valor da Célula", self)
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
                if column > 0:  # Não permitir remover a coluna de índice
                    column_name = self.table_widget.horizontalHeaderItem(column).text()
                    
                    remove_column_action = QAction(f"Remover Coluna '{column_name}'", self)
                    remove_column_action.triggered.connect(lambda: self.remove_column_by_index(column))
                    menu.addAction(remove_column_action)
                    
                    auto_fit_action = QAction(f"Ajustar Largura '{column_name}'", self)
                    auto_fit_action.triggered.connect(lambda: self.auto_fit_column(column))
                    menu.addAction(auto_fit_action)
            
            menu.exec(self.table_widget.mapToGlobal(position))

    def copy_cell_value(self):
        """Copia o valor da célula selecionada."""
        current_item = self.table_widget.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(current_item.text())

    def copy_row_data(self):
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
        """Remove uma coluna específica baseada no índice."""
        if column_index > 0 and column_index < len(self.visible_columns):  # Protege coluna de índice
            internal_column = self.visible_columns[column_index - 1]  # -1 porque há coluna '#'
            if internal_column in self.visible_columns:
                self.visible_columns.remove(internal_column)
                self.on_columns_changed(self.visible_columns)

    def auto_fit_column(self, column_index):
        """Ajusta automaticamente a largura da coluna baseada no conteúdo."""
        self.table_widget.resizeColumnToContents(column_index)
        # Salva a nova largura
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        if header_item and column_index > 0:  # Não salvar largura da coluna de índice
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
                # Executa de forma assíncrona
                result = subprocess.run([
                    sys.executable, main_py_path
                ], capture_output=True, text=True, cwd=project_root)
                
                if result.returncode == 0:
                    self.status_label.setText("Status: Reescaneamento concluído. Clique em 'Carregar Dados' para atualizar.")
                    QMessageBox.information(self, "Sucesso", "Reescaneamento concluído com sucesso!")
                else:
                    self.status_label.setText("Status: Erro no reescaneamento.")
                    QMessageBox.warning(self, "Erro", f"Erro no reescaneamento:\n{result.stderr}")
            else:
                QMessageBox.warning(self, "Erro", f"Arquivo main.py não encontrado em {main_py_path}")
                
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
            QMessageBox.warning(self, "Erro", f"Pasta não encontrada: {docs_path}")

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
                # Testa se o arquivo é um banco válido
                test_df = query_db(db_file, TABLE_NAME)
                if test_df is not None and not test_df.empty:
                    # Atualiza o caminho do banco
                    global DB_PATH
                    DB_PATH = db_file
                    self.status_label.setText(f"Status: Banco alternativo selecionado: {os.path.basename(db_file)}")
                    QMessageBox.information(self, "Sucesso", f"Banco de dados selecionado: {os.path.basename(db_file)}\n\nClique em 'Carregar Dados' para carregar os dados.")
                else:
                    QMessageBox.warning(self, "Erro", "O arquivo selecionado não contém dados válidos na tabela 'ssas'.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir o banco de dados: {e}")
        elif db_file:  # Arquivo selecionado mas não existe
            QMessageBox.warning(self, "Erro", "Arquivo selecionado não existe.")

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
        
        # Cria um nome baseado no filtro (limitado para exibição)
        filter_name = current_text[:20] + "..." if len(current_text) > 20 else current_text
        
        # Verifica se já existe
        for f in self.persistent_filters:
            if f["terms"] == current_text:
                QMessageBox.information(self, "Aviso", "Este filtro já está salvo.")
                return
        
        # Adiciona novo filtro
        new_filter = {"name": filter_name, "terms": current_text}
        self.persistent_filters.append(new_filter)
        self.update_filter_tags()
        
        QMessageBox.information(self, "Sucesso", f"Filtro '{filter_name}' salvo com sucesso!")

    def update_filter_tags(self):
        """Atualiza as tags visuais dos filtros persistentes."""
        # Remove tags existentes
        for i in reversed(range(self.filter_tags_layout.count())):
            child = self.filter_tags_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()
        
        # Estilo adaptativo claro/escuro
        pal = self.palette()
        base = pal.window().color()
        is_dark = base.value() < 128
        fg = pal.windowText().color().name()
        border = '#6b6b6b' if is_dark else '#909090'
        bg_normal = 'transparent'
        bg_hover = '#2a2a2a' if is_dark else '#f0f7ff'
        bg_pressed = '#3a3a3a' if is_dark else '#d9ecff'

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
        for filter_data in self.persistent_filters:
            tag_button = QPushButton(filter_data["name"])
            tag_button.setMaximumHeight(25)
            tag_button.setStyleSheet(tag_css)
            tag_button.setToolTip(f"Clique para aplicar: {filter_data['terms']}")
            tag_button.clicked.connect(lambda checked, terms=filter_data["terms"]: self.apply_persistent_filter(terms))
            
            # Botão X para remover
            remove_button = QPushButton("×")
            remove_button.setMaximumSize(20, 20)
            remove_button.setStyleSheet(tag_css)
            remove_button.setToolTip("Remover filtro")
            remove_button.clicked.connect(lambda checked, filter_data=filter_data: self.remove_persistent_filter(filter_data))
            
            # Layout horizontal para tag + botão remover
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
        """Reotimiza larguras das colunas quando a janela é redimensionada."""
        super().resizeEvent(event)
        
        # Só recalcula se há dados carregados e uma mudança significativa na largura
        if (hasattr(self, 'df_exibido') and not self.df_exibido.empty and 
            hasattr(self, '_last_window_width')):
            width_change = abs(event.size().width() - self._last_window_width)
            if width_change > 50:  # Só recalcula se mudança for > 50px
                # Delay para evitar recálculos excessivos durante resize
                QTimer.singleShot(300, self._recompute_column_widths_on_resize)
        
        # Salva largura atual
        self._last_window_width = event.size().width()

    def _recompute_column_widths_on_resize(self):
        """Recalcula e aplica larguras das colunas após resize da janela."""
        try:
            # Verifica se widgets estão em estado válido
            if (not hasattr(self, 'df_para_tabela') or self.df_para_tabela.empty or
                not self.table_widget or not self.table_widget.isVisible()):
                return
                
            # Recalcula larguras com nova dimensão da janela usando WidthManager
            self._compute_gui_column_widths(self.df_para_tabela)
            # Aplica as novas larguras
            self._apply_computed_widths_only()
        except Exception as e:
            print(f"AVISO: Erro durante recálculo de larguras no resize: {e}")

    def _apply_computed_widths_only(self):
        """Aplica apenas as larguras calculadas pelo WidthManager (ignora configurações salvas)."""
        try:
            if (not hasattr(self, 'df_para_tabela') or self.df_para_tabela.empty or
                not hasattr(self, '_gui_column_pixel_widths') or 
                not self.table_widget or not self.table_widget.isVisible()):
                return
            
            # CORREÇÃO CRÍTICA: Usar _current_display_columns que contém apenas as colunas visíveis filtradas
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
                        if current_width != px:  # Só aplica se diferente
                            self.table_widget.setColumnWidth(col_index, px)
                    
        except Exception as e:
            print(f"AVISO: Erro durante aplicação de larguras: {e}")

    def closeEvent(self, event):
        """
        Método chamado quando a janela é fechada.
        Garante cleanup adequado dos QThreads para evitar o erro:
        'QThread: Destroyed while thread is still running'
        """
        # Aguarda finalização do data loader thread se estiver rodando
        if hasattr(self, 'data_loader_thread') and self.data_loader_thread and self.data_loader_thread.isRunning():
            self.data_loader_thread.quit()
            self.data_loader_thread.wait(3000)  # Aguarda até 3 segundos
            
        # Aguarda finalização do filter thread se estiver rodando  
        if hasattr(self, 'filter_thread') and self.filter_thread and self.filter_thread.isRunning():
            self.filter_thread.quit()
            self.filter_thread.wait(3000)  # Aguarda até 3 segundos
            
        # Aceita o evento de fechamento
        event.accept()

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
