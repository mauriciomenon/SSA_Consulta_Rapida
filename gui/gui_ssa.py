# gui_ssa.py (GUI PyQt6 para SSA_Consulta_Rapida)
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

import sys
import os
import pandas as pd
import json
import subprocess
try:
    from utils.version import get_app_version
except Exception:
    def get_app_version():
        return "3.10+"

# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importações dos managers unificados
from gui.simple_width_manager import SimpleWidthManager, SimpleCacheManager  # noqa: E402
from utils.themes import get_palette  # noqa: E402
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS  # noqa: E402

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

from utils.formatting import format_dataframe_for_display  # noqa: E402

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms  # noqa: E402
from armazenamento.database import query_db  # noqa: E402

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
    QMenu, QGroupBox, QTextEdit, QTextBrowser, QFileDialog, QDialog, QDialogButtonBox,
        QSpacerItem, QSizePolicy, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
    from PyQt6.QtGui import QAction
except Exception:
    QT_AVAILABLE = False
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
        def __init__(self): self._items=[]
        def addItems(self, items): self._items.extend(items)
        def addWidget(self, *a, **k): pass
        def setMinimumWidth(self, *a, **k): pass
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
        # Preenche com todas as colunas possáveis (baseadas no display_map)
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
              <li><b>Virgula (,)</b> ou <b>espaco</b> separam multiplos termos</li>
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

        # Configurações de GUI (independentes do CLI)
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        self._restored_page_size = gui_settings.get("page_size", 50)

        # Inicializa managers unificados (substitui codigo frankenstein)
        self.width_manager = SimpleWidthManager()
        self.cache_manager = SimpleCacheManager()

        # Estado de ordenaçção e filtros por coluna
        self.sort_column = None
        self.sort_ascending = True
        self._active_column_filters = {}
        self._df_last_search_filtered = pd.DataFrame()

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
        # Pre-aplica tema (padrao: gruvbox) antes do auto-load
        # Abrir sempre com tema Gruvbox, independente do salvo
        self.apply_theme('gruvbox')
        try:
            # Persiste preferencia padrao em gruvbox, sem impedir troca manual depois
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = 'gruvbox'
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        # Pre-habilitar entradas vazias para Situacao, Executor e Descricao da SSA no painel
        for key in ("situacao", "setor_executor", "descricao_ssa"):
            if key in self.internal_to_display and key not in self._active_column_filters:
                self._active_column_filters[key] = ""
        # Atualiza painel com filtros pre-exibidos
        try:
            self._build_column_filters_panel()
        except Exception:
            pass

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
        self.search_input.setPlaceholderText("Separe por vírgulas; ! exclui; busca em todas as colunas")
        self.search_input.setToolTip(
            "Modos por termo: \n"
            "- contêm (padrção): foo\n- começa com: ^foo\n- termina com: foo$\n- igual: =foo\n- regex: ~foo.*bar\n- negativos: prefixe ! (ex.: !^adm, !$2025)"
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
        self.column_selector = ColumnSelector(self.display_map, self.visible_columns)
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
            "Separe por várgulas. Use ! para excluir. A busca vale para qualquer coluna."
        )
        self.search_help.setWordWrap(False)
        try:
            self.search_help.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        self.search_help.setStyleSheet("font-size: 10px; color: palette(mid); margin:0; padding:0;")
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

        # Espaçamento entre paginador e filtros
        pagination_filters_layout.addSpacing(20)

        # Area de filtros persistentes
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
        # Indicador de filtros por coluna (ao lado de "Salvar Filtro")
        self.col_filter_indicator = QLabel("Filtros por coluna: Nao ativo")
        self.col_filter_indicator.setStyleSheet("font-size: 11px; color: palette(mid);")
        pagination_filters_layout.addWidget(self.col_filter_indicator)

        main_layout.addLayout(pagination_filters_layout)

        # Linha de resumo de filtros aplicados (Geral + Colunas)
        try:
            self.filters_summary_frame = QFrame()
            self.filters_summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
            self.filters_summary_frame.setStyleSheet("QFrame{ border:1px solid palette(mid); padding:4px; }")
            summary_layout = QHBoxLayout(self.filters_summary_frame)
            summary_layout.setContentsMargins(6,4,6,4)
            summary_layout.setSpacing(8)
            self.filters_summary_label = QLabel("Nenhum filtro ativo")
            self.filters_summary_label.setStyleSheet("")
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
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        bottom_layout.addWidget(self.details_group, 5)

        # Filtros por Coluna com lista rolavel + rodape fixo
        self.col_filters_group = QGroupBox("Filtros por Coluna")
        col_filters_outer = QVBoxLayout(self.col_filters_group)
        from PyQt6.QtWidgets import QScrollArea
        self.col_filters_scroll = QScrollArea()
        self.col_filters_scroll.setWidgetResizable(True)
        self.col_filters_container = QWidget()
        self.col_filters_list_layout = QVBoxLayout(self.col_filters_container)
        self.col_filters_scroll.setWidget(self.col_filters_container)
        col_filters_outer.addWidget(self.col_filters_scroll, 1)
        # Rodape fixo
        footer = QHBoxLayout()
        footer.addStretch()
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
        bottom_layout.addWidget(right_col_widget, 4)

        # Respiro antes do bloco inferior
        main_layout.addSpacing(12)
        main_layout.addLayout(bottom_layout)

        # --- Conecta Workers / Flags ---
        # Threads iniciadas sob demanda
        self.data_loader_thread = None
        self.filter_thread = None
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in ("1", "true", "yes", "on")

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        # Chamar start() novamente reinicia o QTimer automaticamente
        self._debounce_timer.start()

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
        # Atualiza o paginador com o DataFrame completo
        self.paginator.set_dataframe(self.df_exibido)
        # Exibe a primeira pagina
        (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
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

        # Descobre default_mode nas configuracoes JSON (OTIMIZACAO: usando cache)
        if not hasattr(self, '_cached_default_mode'):
            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode

        # Modo síncrono (sem QThread) opcional para testes
        if getattr(self, '_sync_filtering', False):
            try:
                if search_terms:
                    parsed = parse_search_terms(search_terms, default_mode=default_mode)
                    df_filtrado = filter_dataframe(self.df_completo, parsed)
                else:
                    df_filtrado = self.df_completo.copy()
                self.on_filter_finished(df_filtrado)
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(f"Erro ao filtrar dados: {e}")
            finally:
                self.on_filter_finished_cleanup()
            return

        # Inicia a thread de filtragem (modo padrão assíncrono)
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
        # OTIMIZACAO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        # Exibe a primeira pagina dos resultados filtrados (larguras serao calculadas la)
        (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs encontradas.")
        # Atualizar resumo de filtros
        try:
            self._update_filters_summary()
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
            if hasattr(self, "progress_bar") and self.progress_bar:  # type: ignore[attr-defined]
                try:
                    self.progress_bar.setVisible(False)
                except Exception:
                    pass
            for btn_attr in ("load_button", "search_button"):
                btn = getattr(self, btn_attr, None)
                if btn is not None:
                    try:
                        btn.setEnabled(True)
                    except Exception:
                        pass
            # Garantir limpeza segura da referência ao worker
            worker = getattr(self, "filter_thread", None)
            if worker is not None:
                try:
                    # Se ainda ativo, não forçar join aqui (evita travas em GUI), apenas limpar referência depois
                    if not worker.isFinished():  # type: ignore[attr-defined]
                        pass
                except Exception:
                    pass
            self.filter_thread = None
        except Exception:
            # Nunca propagar exceção daqui; log mínimo opcional futuro
            self.filter_thread = None

    def clear_filter(self):
        """Limpa o filtro e mostra todos os dados."""
        self.search_input.clear()
        self._active_column_filters.clear()
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

            def _recompute_and_refresh():
                base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
                df = self._apply_column_filters(base)
                self.df_exibido = df
                self.paginator.set_dataframe(self.df_exibido)
                (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
                self._build_column_filters_panel()
                self._update_col_filter_indicator()

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

        if not self._active_column_filters:
            lbl = QLabel("Nenhum filtro por coluna aplicado.")
            lbl.setWordWrap(True)
            target_layout.addWidget(lbl)
            target_layout.addStretch()
            self._update_col_filter_indicator()
            return

        for col, term in self._active_column_filters.items():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            full_name = DEFAULT_DISPLAY_MAPPINGS.get(col, self.internal_to_display.get(col, col))
            name_lbl = QLabel(full_name)
            name_lbl.setMinimumWidth(100)
            try:
                name_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            term_box = QLineEdit(str(term))
            term_box.setPlaceholderText("Separe por várgulas. Modos: foo, ^pre, suf$, =exato, ~regex, !neg")
            # Reduzido para garantir visibilidade dos botões em telas estreitas
            term_box.setMinimumWidth(220)
            term_box.setStyleSheet("font-size: 11px;")
            try:
                term_box.setMinimumHeight(26)
            except Exception:
                pass
            try:
                term_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            # Enter aplica o filtro desta coluna
            try:
                term_box.returnPressed.connect(lambda c=col, tb=term_box: _mk_apply(c, tb)())
            except Exception:
                pass
            # Botção Aplicar atualiza o filtro com o texto da caixa
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
                    self._active_column_filters[c] = tb.text().strip()
                    base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
                    self.df_exibido = self._apply_column_filters(base)
                    self.paginator.set_dataframe(self.df_exibido)
                    try:
                        current = max(1, min(self.paginator.current_page, self.paginator.total_pages))
                        self.display_current_page(current)
                    except Exception:
                        (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
                    self._update_col_filter_indicator()
                    try:
                        self._update_filters_summary()
                    except Exception:
                        pass
                return _inner
            apply_btn.clicked.connect(_mk_apply())
            # Botção Limpar remove o filtro da coluna
            clear_btn = QPushButton("Limpar")
            try:
                clear_btn.setMinimumHeight(26)
            except Exception:
                pass
            try:
                clear_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                clear_btn.setFixedWidth(68)
            except Exception:
                pass
            def _mk_clear(c=col):
                return lambda: self._clear_single_column_filter(c, term_box.text().strip())
            clear_btn.clicked.connect(_mk_clear())
            row.addWidget(name_lbl)
            row.addWidget(term_box, 1)
            row.addWidget(apply_btn)
            row.addWidget(clear_btn)
            row_w = QWidget()
            row_w.setLayout(row)
            target_layout.addWidget(row_w)

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

    def _clear_single_column_filter(self, col_name: str, current_text: str = None):
        if col_name in self._active_column_filters:
            # Se já está vazio e o campo também está vazio, não faz nada
            try:
                if str(self._active_column_filters.get(col_name, '')).strip() == '' and (current_text is None or str(current_text).strip() == ''):
                    return
            except Exception:
                pass
            # Para filtros padrão, manter a entrada vazia; demais, remover
            default_keep = {"situacao", "setor_executor", "descricao_ssa"}
            if col_name in default_keep:
                self._active_column_filters[col_name] = ""
            else:
                del self._active_column_filters[col_name]
            base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
            self.df_exibido = self._apply_column_filters(base)
            self.paginator.set_dataframe(self.df_exibido)
            (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
            self._build_column_filters_panel()
            self._update_col_filter_indicator()

    def _clear_all_column_filters(self):
        if self._active_column_filters:
            # Preserva entradas padrão (Situacao, Executor, Descricao da SSA) como vazias
            self._active_column_filters.clear()
            for k in ("situacao", "setor_executor", "descricao_ssa"):
                self._active_column_filters[k] = ""
            base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
            self.df_exibido = base.copy()
            self.paginator.set_dataframe(self.df_exibido)
            (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
            self._build_column_filters_panel()
            self._update_col_filter_indicator()
            # Atualizar resumo de filtros
            try:
                self._update_filters_summary()
            except Exception:
                pass

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

        # Filtros de coluna
        if hasattr(self, '_active_column_filters') and self._active_column_filters:
            for col_name, filter_value in self._active_column_filters.items():
                if filter_value and filter_value.strip():
                    # Traduz nome da coluna para exibicao
                    display_name = col_name.replace('_', ' ').title()
                    if col_name == 'situacao':
                        display_name = 'Situacao'
                    elif col_name == 'setor_executor':
                        display_name = 'Executor'
                    elif col_name == 'descricao_ssa':
                        display_name = 'Descricao da SSA'
                    active_filters.append(f"{display_name}: '{filter_value.strip()}'")

        # Monta texto do resumo
        if active_filters:
            summary_text = f"Filtros ativos: {' | '.join(active_filters)}"
        else:
            summary_text = "Nenhum filtro ativo"

        # Atualiza label de resumo principal
        if hasattr(self, 'filters_summary_label'):
            self.filters_summary_label.setText(summary_text)

    def toggle_theme_menu(self):
        from PyQt6.QtWidgets import QMenu
        from functools import partial
        menu = QMenu(self)
        for label, key in (("Claro", 'light'), ("Escuro", 'dark'), ("Gruvbox", 'gruvbox')):
            act = menu.addAction(label)
            if act is not None:  # defesa para analise estatica
                try:
                    act.triggered.connect(partial(self.apply_theme, key))  # type: ignore[attr-defined]
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
        try:
            from PyQt6.QtWidgets import QApplication
            if (name or '').lower() == 'light':
                # Usa a paleta padrão sem depender de QStyleFactory
                app = QApplication.instance()
                if app is not None and hasattr(app, 'style'):
                    style_obj = app.style()
                    try:
                        pal = style_obj.standardPalette()  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001
                        pal = get_palette('light')
                else:
                    pal = get_palette('light')
                self.setPalette(pal)
            else:
                pal = get_palette(name)
                self.setPalette(pal)
        except Exception:  # noqa: BLE001
            pal = get_palette(name)
            self.setPalette(pal)
        try:
            header = self.table_widget.horizontalHeader()
            header.setStyleSheet("QHeaderView::section{font-weight: normal;}")
        except Exception:
            pass
        # Ajustes de contraste por tema para rotulos informativos
        try:
            theme = (name or '').lower()
            if theme == 'light':
                # Usar aparencia padrao do sistema/Fusion; sem CSS pesado
                if hasattr(self, 'week_label'):
                    self.week_label.setStyleSheet("")
                if hasattr(self, 'status_label'):
                    self.status_label.setStyleSheet("")
                if hasattr(self, 'search_help'):
                    self.search_help.setStyleSheet("")
            else:
                # Temas escuros (inclui Gruvbox) com contraste garantido
                if hasattr(self, 'week_label'):
                    self.week_label.setStyleSheet(
                        "font-weight:600; color:#ddd; background:#2a2a2a; border:1px solid #555; border-radius:4px; padding:2px 6px;"
                    )
                if hasattr(self, 'status_label'):
                    self.status_label.setStyleSheet(
                        "color:#ddd; background:#2a2a2a; border:1px solid #555; border-radius:4px; padding:2px 6px;"
                    )
                if hasattr(self, 'search_help'):
                    self.search_help.setStyleSheet("font-size:10px; color:#b8b8b8; margin:0; padding:0;")
        except Exception:
            pass
        # Persistencia
        try:
            # Persistencia simples do tema sem normalizacao adicional
            GUI_MAIN_PREFERENCES.setdefault('gui_settings', {})['theme'] = (name or '').lower()
            with open(os.path.join(project_root, 'config', 'gui_main_preferences.json'), 'w', encoding='utf-8') as f:
                json.dump(GUI_MAIN_PREFERENCES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _update_col_filter_indicator(self):
        # Ativo quando existe ao menos um termo não vazio em filtros por coluna
        active = any((str(v).strip() != "") for _, v in (self._active_column_filters or {}).items())
        txt = "Filtros por coluna: Ativo" if active else "Filtros por coluna: Nao ativo"
        if hasattr(self, 'col_filter_indicator'):
            self.col_filter_indicator.setText(txt)

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
        # Divide por várgulas ou espaços
        tokens = [t.strip() for t in raw.replace('\n',' ').split(',')]
        tokens = [t for tok in tokens for t in tok.split() if t]
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
        """Chamado quando a seleçção de colunas muda."""
        self.visible_columns = new_columns
        # Reexibe a pãgina atual com as novas colunas
        self.display_current_page(self.paginator.current_page)
        # Nota: Persistencia de preferencias removida para isolamento do CLI
        # As configurações ficam no arquivo gui_main_preferences.json

    def display_current_page(self, page_number):
        """Exibe a pãgina especificada do DataFrame filtrado."""
        # Obtem o slice de dados para a pãgina atual do paginator
        self.df_para_tabela = self.paginator.get_current_slice()

        if self.df_para_tabela.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
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

        # Configura header como Interactive para permitir larguras customizadas
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

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

            # print(f"DEBUG: Aplicando largura {px}px para coluna '{col_key}' (índice {i})")
            self.table_widget.setColumnWidth(i, px)

        # CORRECAO: Desabilitado temporariamente para evitar conflitos com best-fit
        # QTimer.singleShot(100, self._force_column_widths)

        # Seleciona a primeira linha (se houver) e atualiza detalhes
        if self.table_widget.rowCount() > 0:
            self.table_widget.selectRow(0)
        self.update_details_from_selection()

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
                table_width = max(1400, self.width() - 50)
            else:
                table_width = widget_width - 40  # Margem para scrollbars

            # Garante largura mánima para funcionamento adequado
            table_width = max(table_width, 1400)

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
            # Persist only reasonable sizes (desabilitado - placeholder para evitar lint de variavel nao usada)
            _ = cols[logical_index]
            _ = max(30, min(int(new_size), 1200))
            # Atualiza cache local - TEMPORARIAMENTE DESABILITADO para usar larguras fixas
            # self._saved_gui_column_widths[col_name] = new_px
            # Nota: Persistencia removida para isolamento do CLI
            # As larguras ficam configuradas no arquivo gui_main_preferences.json
        except Exception:  # noqa: BLE001
            # Evita quebrar a GUI por falhas de IO
            pass

    def on_table_double_click(self, index):
        """Placeholder para açção de clique duplo (ex: mostrar detalhes)."""
        row = index.row()
        # O item da coluna '#' contêm o ándice da linha original
        index_item = self.table_widget.item(row, 0)  # Assume '#' eh a primeira coluna
        if index_item:
            original_index = index_item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None and 0 <= original_index < len(self.df_exibido):
                # Aqui voce chamaria uma funcao para mostrar detalhes
                # Ex: show_details_window(self.df_exibido.iloc[original_index])
                QMessageBox.information(
                    self,
                    "Detalhes",
                    f"Detalhes para SSA na linha {original_index + 1} (pãgina {self.paginator.current_page})\n"
                    f"Dados: {self.df_exibido.iloc[original_index].to_dict()}",
                )
            else:
                QMessageBox.information(self, "Info", "Nção foi possável encontrar os dados detalhados para esta linha.")

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

        # Usa dados originais (nção formatados) para detalhes
        series = self.df_exibido.iloc[int(original_index)]
        # Constroi um texto amigavel com nomes de exibicao
        lines = []
        for col, value in series.items():
            display_name = self.internal_to_display.get(col, col)
            # Mostra numero_ssa "natural" (int se possável)
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
        except Exception as e:
            print(f"AVISO: Erro durante recãlculo de larguras no resize: {e}")

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

        except Exception as e:
            print(f"AVISO: Erro durante aplicaçção de larguras: {e}")

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
            except Exception:
                pass
            try:
                self.filter_thread.filter_finished.disconnect(self.on_filter_finished)
            except Exception:
                pass
            try:
                self.filter_thread.error_occurred.disconnect(self.on_filter_error)
            except Exception:
                pass
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





