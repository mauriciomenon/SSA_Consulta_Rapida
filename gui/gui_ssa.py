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

# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.formatting import format_dataframe_for_display

# (mantido acima)

# --- Importações do Projeto ---
from core.app_logic import filter_dataframe, parse_search_terms
from armazenamento.database import query_db
from core.config_manager import (
    load_settings,
    save_settings,
    load_display_mappings_integrity,  # Para carregar display_mappings
)

# --- Importações do PyQt6 ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QComboBox, QSpinBox, QAbstractItemView,
    QMenu, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QItemSelectionModel, QTimer
from PyQt6.QtGui import QAction

# --- Constantes ---
DB_PATH = os.path.join(project_root, 'data', 'ssas.db')
TABLE_NAME = 'ssas'
CONFIG_DIR = os.path.join(project_root, 'config')
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'display_mappings.json')

# --- Funções Auxiliares ---

def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibição com verificação de integridade."""
    return load_display_mappings_integrity()

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
            df = query_db(self.db_path, self.table_name)
            if df is not None:
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Grupo para seleção
        group_box = QGroupBox("Colunas Visíveis")
        group_layout = QVBoxLayout(group_box)
        
        # ComboBox para adicionar colunas
        self.add_column_combo = QComboBox()
        # Preenche com todas as colunas possíveis (baseadas no display_map)
        all_display_names = sorted(self.display_to_internal.keys())
        self.add_column_combo.addItems(all_display_names)
        
        add_button = QPushButton("Adicionar Coluna")
        add_button.clicked.connect(self.add_column)

        # Lista de colunas selecionadas (usando um ComboBox por simplicidade)
        # Uma implementação mais completa usaria uma QListWidget
        self.selected_columns_label = QLabel("Colunas Atuais: " + ", ".join([self.internal_to_display.get(c, c) for c in self.selected_internal_columns]))
        
        remove_button = QPushButton("Remover Última Coluna")
        remove_button.clicked.connect(self.remove_column)

        group_layout.addWidget(QLabel("Adicionar Coluna:"))
        group_layout.addWidget(self.add_column_combo)
        group_layout.addWidget(add_button)
        group_layout.addWidget(self.selected_columns_label)
        group_layout.addWidget(remove_button)
        
        layout.addWidget(group_box)

    def add_column(self):
        display_name = self.add_column_combo.currentText()
        internal_name = self.display_to_internal.get(display_name)
        if internal_name and internal_name not in self.selected_internal_columns:
            self.selected_internal_columns.append(internal_name)
            self.update_label()
            self.columns_changed.emit(self.selected_internal_columns)

    def remove_column(self):
        if self.selected_internal_columns:
            self.selected_internal_columns.pop()
            self.update_label()
            self.columns_changed.emit(self.selected_internal_columns)

    def update_label(self):
        display_names = [self.internal_to_display.get(c, c) for c in self.selected_internal_columns]
        self.selected_columns_label.setText("Colunas Atuais: " + ", ".join(display_names))

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


# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow):
    """
    Janela principal da aplicacao GUI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consulta Rápida de SSAs - GUI (PoC)")
        self.setGeometry(100, 100, 1200, 800)

        self.df_completo = pd.DataFrame()
        self.df_exibido = pd.DataFrame()  # DataFrame filtrado
        self.df_para_tabela = pd.DataFrame()  # DataFrame paginado para exibição

        # Carrega mapeamentos de exibição
        self.display_map = load_display_mappings()
        self.internal_to_display = {k: v for k, v in self.display_map.items()}

        # Colunas padrão para exibição (prioritárias)
        self.default_columns = [
            'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
            'data_cadastro', 'semana_cadastro'
        ]
        # Garante que colunas padrão existam no mapeamento
        self.visible_columns = [col for col in self.default_columns if col in self.internal_to_display or col == '#']

        # Preferências do usuário (persistência GUI)
        try:
            settings = load_settings()
        except Exception:
            settings = {}
        display_settings = (settings.get('display_settings') or {})
        # Restaura colunas visíveis se existir em settings
        gui_visible = display_settings.get('gui_visible_columns')
        if isinstance(gui_visible, list) and gui_visible:
            # Filtra apenas colunas válidas
            self.visible_columns = [c for c in gui_visible if c in self.internal_to_display or c == '#']
            if not self.visible_columns:
                self.visible_columns = [col for col in self.default_columns if col in self.internal_to_display or col == '#']
        # Página: restaura page_size se disponível
        self._restored_page_size = display_settings.get('gui_page_size')
        # Larguras salvas por coluna (internas)
        self._saved_gui_column_widths = {}
        self._gui_column_pixel_widths = {}  # Inicializa o atributo que estava faltando
        gw = display_settings.get('gui_column_widths')
        if isinstance(gw, dict):
            for k, v in gw.items():
                try:
                    self._saved_gui_column_widths[k] = int(v)
                except Exception:
                    continue

        # Debounce de filtro (250ms)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(250)
        self._debounce_timer.timeout.connect(self.initiate_filtering)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()

        self.load_button = QPushButton("1. Carregar Dados")
        self.load_button.clicked.connect(self.load_data)

        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)
        toolbar_layout.addStretch()

        main_layout.addLayout(toolbar_layout)

        # --- Barra de Pesquisa e Filtros ---
        search_layout = QHBoxLayout()
        self.search_label = QLabel("2. Pesquisar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Termos por vírgula. Modos: foo, ^pre, suf$, =exato, ~regex, !neg")
        self.search_input.setToolTip(
            "Modos por termo: \n"
            "- contém (padrão): foo\n"
            "- começa com: ^foo\n"
            "- termina com: foo$\n"
            "- igual: =foo\n"
            "- regex: ~foo.*bar\n"
            "- negativos: prefixe ! (ex.: !^adm, !$2025)"
        )
        self.search_input.returnPressed.connect(self.initiate_filtering)
        # Aplica debounce ao digitar
        self.search_input.textChanged.connect(self._on_search_text_changed)

        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.initiate_filtering)

        self.clear_filter_button = QPushButton("Limpar Filtro")
        self.clear_filter_button.clicked.connect(self.clear_filter)
        self.clear_filter_button.setEnabled(False)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_filter_button)
        main_layout.addLayout(search_layout)

        # --- Seletor de Colunas ---
        self.column_selector = ColumnSelector(self.display_map, self.visible_columns)
        self.column_selector.columns_changed.connect(self.on_columns_changed)
        main_layout.addWidget(self.column_selector)

        # --- Paginador ---
        self.paginator = DataPaginator(self.df_para_tabela)
        self.paginator.page_changed.connect(self.display_current_page)
        main_layout.addWidget(self.paginator)
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

        # Conecta clique duplo para mostrar detalhes (placeholder)
        self.table_widget.doubleClicked.connect(self.on_table_double_click)
        # Atualiza painel de detalhes quando a seleção muda
        self.table_widget.itemSelectionChanged.connect(self.update_details_from_selection)
        # Salva largura quando usuário redimensionar uma coluna
        self.table_widget.horizontalHeader().sectionResized.connect(self._on_header_section_resized)

        main_layout.addWidget(self.table_widget)

        # --- Painel de Detalhes ---
        self.details_group = QGroupBox("Detalhes da SSA Selecionada")
        details_layout = QVBoxLayout(self.details_group)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        main_layout.addWidget(self.details_group)

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
        self.df_exibido = df.copy()
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

        # Descobre default_mode nas configurações
        try:
            settings = load_settings()
            default_mode = (settings.get('user_preferences') or {}).get('filter_mode_default', 'contains')
        except Exception:
            default_mode = 'contains'
        # Inicia a thread de filtragem
        self.filter_thread = FilterWorker(self.df_completo, search_terms, default_mode=default_mode)
        self.filter_thread.filter_finished.connect(self.on_filter_finished)
        self.filter_thread.error_occurred.connect(self.on_filter_error)
        self.filter_thread.finished.connect(self.on_filter_finished_cleanup)
        self.filter_thread.start()

    def on_filter_finished(self, df_filtrado: pd.DataFrame):
        self.df_exibido = df_filtrado
        # Atualiza o paginador com o DataFrame filtrado
        self.paginator.set_dataframe(self.df_exibido)
        # Pré-calcula larguras estáveis para todas as colunas exibíveis com base no conjunto filtrado
        self._compute_gui_column_widths(self.df_exibido)
        # Exibe a primeira página dos resultados filtrados
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
        self.df_exibido = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        self.status_label.setText(f"Status: Filtro limpo. {len(self.df_exibido)} SSAs exibidas.")

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleção de colunas muda."""
        self.visible_columns = new_columns
        # Reexibe a página atual com as novas colunas
        self.display_current_page(self.paginator.current_page)
        # Persiste preferências
        try:
            settings = load_settings()
        except Exception:
            settings = {}
        display_settings = (settings.get('display_settings') or {})
        display_settings['gui_visible_columns'] = list(self.visible_columns)
        settings['display_settings'] = display_settings
        try:
            save_settings(settings)
        except Exception:
            pass

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

        # Pina ordem essencial: '#' depois numero_ssa, loc, executor, situacao, descricao_ssa
        def _pin(cols):
            pinned = ['numero_ssa', 'localizacao_codigo', 'setor_executor', 'situacao', 'descricao_ssa']
            fixed = [c for c in pinned if c in cols]
            tail = [c for c in cols if c not in fixed]
            return fixed + tail
        cols_to_show = _pin(cols_to_show)

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
        try:
            display_df = format_dataframe_for_display(display_df)
        except Exception:
            # falha de formatação não deve quebrar a GUI; segue sem formatar
            pass

    # Configura a tabela
        self.table_widget.setRowCount(len(display_df))
        self.table_widget.setColumnCount(len(display_df.columns))

        # Define cabeçalhos de exibição
        display_headers = []
        for col in display_df.columns:
            if col == '#':
                display_headers.append('#')
            else:
                display_headers.append(self.internal_to_display.get(col, col))
        self.table_widget.setHorizontalHeaderLabels(display_headers)

        # Preenche os dados
        for row_idx in range(len(display_df)):
            for col_idx, col_name in enumerate(display_df.columns):
                value = display_df.iloc[row_idx, col_idx]
                item_text = "" if pd.isna(value) else str(value)

                # Trunca texto muito longo para a tabela
                if len(item_text) > 50:
                    item_text = item_text[:47] + "..."

                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                # Armazena o índice da linha original nos dados filtrados para referência
                if col_name == '#':
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        row_idx + (self.paginator.current_page - 1) * self.paginator.page_size,
                    )
                self.table_widget.setItem(row_idx, col_idx, item)

        # Aplica larguras estáveis por coluna (em pixels) com modo Fixed para estabilidade entre páginas
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for i, col_name in enumerate(['#'] + list(display_df.columns)):
            # Busca largura salva (prioritária), senão a computada
            px = self._saved_gui_column_widths.get(col_name)
            if px is None:
                px = self._gui_column_pixel_widths.get(col_name)
            # Fallbacks razoáveis: '#' pequeno, numeros médios, descrição maior
            if px is None:
                if col_name == '#':
                    px = 40
                elif col_name == 'numero_ssa':
                    px = 80
                elif col_name in ('descricao_ssa', 'descricao_execucao'):
                    px = 360
                else:
                    px = 100
            # Limites
            px = max(40, min(int(px), 600))
            self.table_widget.setColumnWidth(i, px)

        # Seleciona a primeira linha (se houver) e atualiza detalhes
        if self.table_widget.rowCount() > 0:
            self.table_widget.selectRow(0)
        self.update_details_from_selection()

    def _compute_gui_column_widths(self, df: pd.DataFrame):
        """Calcula larguras em pixels baseadas no conteúdo filtrado para estabilidade entre páginas."""
        self._gui_column_pixel_widths = {}
        if df is None or df.empty:
            return
        # Mapeia colunas internas -> nomes de exibição
        disp_map = {c: self.internal_to_display.get(c, c) for c in df.columns}
        # Estima com base no comprimento 95º percentil e cabeçalho
        # Usa fator ~7 px por caractere como heurística (fonte monoespaçada aproximada)
        for col in df.columns:
            header = disp_map[col]
            try:
                series = df[col].dropna().astype(str)
            except Exception:
                series = pd.Series(dtype=str)
            if not series.empty:
                p95 = int(series.str.len().quantile(0.95, interpolation='lower'))
            else:
                p95 = 0
            target_chars = max(len(header), p95, 3)
            # Tweaks específicos
            if col == 'numero_ssa':
                target_chars = max(target_chars, 9)
            if col in ('descricao_ssa', 'descricao_execucao'):
                target_chars = max(target_chars, 40)
            # Converte caracteres em pixels (aprox. 7 px por char) + margem
            px = target_chars * 7 + 16
            self._gui_column_pixel_widths[col] = px
        # Inclui '#' default
        self._gui_column_pixel_widths['#'] = max(40, self._saved_gui_column_widths.get('#', 40))

    def _on_header_section_resized(self, logical_index: int, old_size: int, new_size: int):
        """Salva a largura ajustada pelo usuário na configuração persistente."""
        try:
            cols = getattr(self, '_current_display_columns', None)
            if not cols or logical_index < 0 or logical_index >= len(cols):
                return
            col_name = cols[logical_index]
            # Persist only reasonable sizes
            new_px = max(30, min(int(new_size), 1200))
            # Atualiza cache local
            self._saved_gui_column_widths[col_name] = new_px
            # Salva em settings
            try:
                settings = load_settings()
            except Exception:
                settings = {}
            ds = (settings.get('display_settings') or {})
            col_widths = (ds.get('gui_column_widths') or {})
            col_widths[col_name] = new_px
            ds['gui_column_widths'] = col_widths
            settings['display_settings'] = ds
            save_settings(settings)
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
        try:
            settings = load_settings()
        except Exception:
            settings = {}
        display_settings = (settings.get('display_settings') or {})
        display_settings['gui_page_size'] = int(new_size)
        settings['display_settings'] = display_settings
        try:
            save_settings(settings)
        except Exception:
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

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
