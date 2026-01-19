"""
Gerenciador de sub-abas de detalhes de SSAs.
Widget dedicado para visualizacao de multiplas SSAs com navegacao estilo Notepad++.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.helpers.formatting_helpers import normalize_ssa_value


class DetailsTabWidget(QWidget):
    """Widget para gerenciar sub-abas de detalhes de SSAs."""

    # Sinal emitido quando uma SSA e aberta
    ssa_opened = pyqtSignal(str)

    def __init__(self, parent=None, data_provider=None, html_formatter=None):
        super().__init__(parent)
        self.parent_window = (
            parent  # Mantido para compatibilidade, mas nao deve ser usado para logica
        )
        self.data_provider = data_provider  # Callable[[str], pd.Series | None]
        self.html_formatter = html_formatter  # Callable[[pd.Series], str]
        self.tabs = []  # Lista de dicts: {'numero_ssa': str, 'widget': QWidget, 'button': QPushButton, 'series': pd.Series}
        self.current_index = -1
        self.max_tabs = 10
        self._init_ui()

    def _init_ui(self):
        """Inicializa a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Campo de entrada para numero SSA
        input_row = QHBoxLayout()
        input_label = QLabel("Numero SSA:")
        input_label.setFixedWidth(100)

        self.ssa_input = QLineEdit()
        self.ssa_input.setPlaceholderText("Digite o numero da SSA e pressione Enter...")
        self.ssa_input.returnPressed.connect(self._on_input_enter)

        input_row.addWidget(input_label)
        input_row.addWidget(self.ssa_input)
        layout.addLayout(input_row)

        # Barra de sub-abas com navegacao
        self.tab_bar = QWidget()
        self.tab_bar_layout = QHBoxLayout(self.tab_bar)
        self.tab_bar_layout.setContentsMargins(0, 4, 0, 4)
        self.tab_bar_layout.setSpacing(4)

        # Seta para navegar a esquerda
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.setToolTip("SSA anterior")
        self.prev_btn.clicked.connect(lambda: self.navigate(-1))
        self.tab_bar_layout.addWidget(self.prev_btn)

        # Container de abas (scroll horizontal futuro)
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setSpacing(2)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.addStretch(1)  # Empurra abas para a esquerda
        self.tab_bar_layout.addWidget(self.tabs_container, 1)

        # Seta para navegar a direita
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedWidth(30)
        self.next_btn.setToolTip("Proxima SSA")
        self.next_btn.clicked.connect(lambda: self.navigate(1))
        self.tab_bar_layout.addWidget(self.next_btn)

        layout.addWidget(self.tab_bar)

        # Area de conteudo empilhada
        self.content_stack = QStackedWidget()

        # Widget placeholder quando nenhuma aba esta aberta
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_label = QLabel(
            "Nenhuma SSA aberta.\nDigite um numero SSA acima para visualizar detalhes."
        )
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: gray; font-size: 14pt;")
        placeholder_layout.addWidget(placeholder_label)

        self.content_stack.addWidget(placeholder)
        self.content_stack.setCurrentIndex(0)

        layout.addWidget(self.content_stack, 1)

        self._update_nav_buttons()
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilos CSS aos componentes."""
        # Estilo para input de SSA
        self.ssa_input.setStyleSheet(
            """
            QLineEdit {
                padding: 6px;
                border: 1px solid palette(mid);
                border-radius: 3px;
                background: palette(base);
            }
            QLineEdit:focus {
                border: 1px solid palette(highlight);
            }
        """
        )

        # Estilo para botoes de navegacao
        nav_button_style = """
            QPushButton {
                background: palette(button);
                border: 1px solid palette(mid);
                border-radius: 3px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: palette(light);
            }
            QPushButton:pressed {
                background: palette(dark);
            }
            QPushButton:disabled {
                color: palette(mid);
            }
        """
        self.prev_btn.setStyleSheet(nav_button_style)
        self.next_btn.setStyleSheet(nav_button_style)

        # Estilo para barra de abas
        self.tab_bar.setStyleSheet(
            """
            QWidget {
                background: palette(window);
                border-bottom: 1px solid palette(mid);
            }
        """
        )

    def open_ssa(self, numero_ssa: str) -> bool:
        """
        Abre uma SSA em nova sub-aba ou foca aba existente.

        Args:
            numero_ssa: Numero da SSA a abrir

        Returns:
            bool: True se a SSA foi aberta com sucesso, False caso contrario
        """
        if not numero_ssa or not numero_ssa.strip():
            return False

        # Normaliza numero usando helper
        try:
            num_norm = normalize_ssa_value(numero_ssa)
        except Exception:
            num_norm = numero_ssa.strip()

        # Verifica se SSA ja esta aberta
        for i, tab in enumerate(self.tabs):
            if tab["numero_ssa"] == num_norm:
                self.current_index = i
                # +1 porque index 0 e o placeholder
                self.content_stack.setCurrentIndex(i + 1)
                self._update_tab_highlights()
                self._update_nav_buttons()
                return True

        # Busca dados da SSA no DataFrame
        series = self._get_ssa_series(num_norm)
        if series is None:
            QMessageBox.warning(
                self,
                "SSA nao encontrada",
                f"A SSA '{numero_ssa}' nao foi encontrada no banco de dados.",
            )
            return False

        # Cria widget de conteudo
        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.anchorClicked.connect(self._on_link_clicked)

        # Renderiza HTML usando formatador injetado
        try:
            if self.html_formatter:
                html = self.html_formatter(series)
            else:
                html = f"<pre>Dados: {series.to_string()}</pre>"
            content.setHtml(html)
        except Exception as e:
            content.setPlainText(f"Erro ao renderizar detalhes: {e}")

        # Cria widget de aba (botao + close button)
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(4, 2, 4, 2)
        tab_layout.setSpacing(4)

        # Botao principal da aba (clicavel)
        tab_btn = QPushButton(num_norm)
        tab_btn.setCheckable(True)
        tab_btn.setFlat(True)
        tab_btn.setMinimumWidth(120)
        tab_btn.setToolTip(f"SSA {num_norm}\nClique para focar")
        # Usa propriedade para identificar a aba, evitando problemas com indices capturados em lambda
        tab_btn.setProperty("ssa_number", num_norm)
        tab_btn.clicked.connect(
            lambda checked, n=num_norm: self._on_tab_clicked_by_ssa(n)
        )
        tab_btn.setStyleSheet(
            """
            QPushButton {
                background: palette(button);
                border: 1px solid palette(mid);
                border-top-left-radius: 4px;
                border-top-right-radius: 0px;
                border-bottom: none;
                padding: 6px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background: palette(light);
            }
            QPushButton:checked {
                background: palette(base);
                border-bottom: 2px solid palette(highlight);
                font-weight: bold;
            }
        """
        )
        tab_layout.addWidget(tab_btn)

        # Botao de fechar (x)
        close_btn = QToolButton()
        close_btn.setText("x")
        close_btn.setFixedSize(18, 18)
        close_btn.setToolTip("Fechar aba")
        close_btn.setProperty("ssa_number", num_norm)
        close_btn.clicked.connect(lambda checked, n=num_norm: self.close_tab_by_ssa(n))
        close_btn.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                border: none;
                border-top-right-radius: 4px;
                color: palette(mid);
                font-weight: bold;
            }
            QToolButton:hover {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
        """
        )
        tab_layout.addWidget(close_btn)

        # Adiciona aba a lista
        self.tabs.append(
            {
                "numero_ssa": num_norm,
                "widget": content,
                "tab_widget": tab_widget,
                "button": tab_btn,
                "close_button": close_btn,
                "series": series,
            }
        )

        # Remove stretch temporariamente, adiciona widget, re-adiciona stretch
        # Verifica se existe item antes de remover para evitar crash
        if self.tabs_layout.count() > 0:
            last_item = self.tabs_layout.itemAt(self.tabs_layout.count() - 1)
            # Remove apenas se for um spacer item (stretch)
            if last_item.spacerItem():
                self.tabs_layout.removeItem(last_item)

        self.tabs_layout.addWidget(tab_widget)
        self.tabs_layout.addStretch(1)

        # Adiciona widget ao stack (index = len(tabs) porque 0 e placeholder)
        self.content_stack.addWidget(content)

        # Foca nova aba
        self.current_index = len(self.tabs) - 1
        self.content_stack.setCurrentIndex(self.current_index + 1)
        self._update_tab_highlights()
        self._update_nav_buttons()

        # Emite sinal
        self.ssa_opened.emit(num_norm)

        # Aplica limite de abas
        if len(self.tabs) > self.max_tabs:
            self.close_tab(0)  # Fecha a mais antiga

        return True

    def close_tab(self, index: int):
        """
        Fecha uma sub-aba pelo indice.

        Args:
            index: Indice da aba a fechar (0-based)
        """
        if not (0 <= index < len(self.tabs)):
            return

        tab = self.tabs.pop(index)

        # Remove widget da aba
        self.tabs_layout.removeWidget(tab["tab_widget"])
        tab["tab_widget"].deleteLater()

        # Remove widget do stack (index + 1 porque 0 e placeholder)
        self.content_stack.removeWidget(tab["widget"])
        tab["widget"].deleteLater()

        # Ajusta indice atual
        if self.current_index >= len(self.tabs):
            self.current_index = max(-1, len(self.tabs) - 1)

        # Atualiza visualizacao
        if self.current_index >= 0:
            self.content_stack.setCurrentIndex(self.current_index + 1)
        else:
            self.content_stack.setCurrentIndex(0)  # Mostra placeholder

        self._update_tab_highlights()
        self._update_nav_buttons()

    def navigate(self, direction: int):
        """
        Navega entre abas.

        Args:
            direction: -1 para anterior, +1 para proxima
        """
        if not self.tabs:
            return

        new_idx = self.current_index + direction
        if 0 <= new_idx < len(self.tabs):
            self.current_index = new_idx
            self.content_stack.setCurrentIndex(new_idx + 1)
            self._update_tab_highlights()
            self._update_nav_buttons()

    def _on_tab_clicked(self, index: int):
        """Handler para clique em botao de aba."""
        # Verifica se clique foi na parte do 'x' (fechar)
        # Por simplicidade, sempre foca a aba. Para fechar, usuario pode usar close button separado
        if 0 <= index < len(self.tabs):
            self.current_index = index
            self.content_stack.setCurrentIndex(index + 1)
            self._update_tab_highlights()
            self._update_nav_buttons()

    def _on_tab_clicked_by_ssa(self, ssa_number: str):
        """Handler para clique em aba usando numero da SSA (mais seguro que indice)."""
        for i, tab in enumerate(self.tabs):
            if tab["numero_ssa"] == ssa_number:
                self._on_tab_clicked(i)
                break

    def close_tab_by_ssa(self, ssa_number: str):
        """Fecha aba usando numero da SSA (mais seguro que indice)."""
        for i, tab in enumerate(self.tabs):
            if tab["numero_ssa"] == ssa_number:
                self.close_tab(i)
                break

    def _on_input_enter(self):
        """Handler para Enter pressionado no campo de input."""
        numero = self.ssa_input.text().strip()
        if numero:
            # UIREFACTOR 2026-01-08: So limpa campo se SSA foi encontrada
            # Permite usuario corrigir numero se errou
            if self.open_ssa(numero):
                self.ssa_input.clear()

    def _on_link_clicked(self, url):
        """
        Handler para links clicados no conteudo HTML.

        Args:
            url: QUrl do link clicado
        """
        href = url.toString()
        if href.startswith("ssa://"):
            # Extrai numero SSA do link
            target = href[6:].strip().lstrip("/")
            if target:
                self.open_ssa(target)
        # Links externos sao ignorados (openExternalLinks=False)

    def _get_ssa_series(self, numero_ssa: str):
        """
                Busca dados de uma SSA no DataFrame principal.
        usando o provedor de dados.

                Args:
                    numero_ssa: Numero normalizado da SSA

                Returns:
                    pandas.Series com dados da SSA ou None se nao encontrada
        """
        if self.data_provider:
            try:
                return self.data_provider(numero_ssa)
            except Exception:
                pass
        return None

    def _update_tab_highlights(self):
        """Atualiza estilo visual das abas (highlight da aba atual)."""
        for i, tab in enumerate(self.tabs):
            tab["button"].setChecked(i == self.current_index)

    def _update_nav_buttons(self):
        """Atualiza estado habilitado/desabilitado dos botoes de navegacao."""
        has_tabs = len(self.tabs) > 0
        self.prev_btn.setEnabled(has_tabs and self.current_index > 0)
        self.next_btn.setEnabled(has_tabs and self.current_index < len(self.tabs) - 1)
        self.tab_bar.setVisible(has_tabs)  # Esconde barra se nao ha abas

    def close_all_tabs(self):
        """Fecha todas as sub-abas abertas."""
        while self.tabs:
            self.close_tab(0)

    def get_open_ssa_numbers(self):
        """
        Retorna lista de numeros SSA atualmente abertos.

        Returns:
            List[str]: Numeros SSA abertos
        """
        return [tab["numero_ssa"] for tab in self.tabs]
