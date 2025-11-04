# gui/tabs/main_tab.py
# Main tab with SSA table and search

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QGroupBox, QTextEdit, QWidget, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.tabs.base_tab import BaseTab


class MainTab(BaseTab):
    """
    Main tab showing SSA table, search bar, and details panel.

    This is a CLEAN implementation without legacy code.
    All search logic goes through helpers only.
    """

    # Signals
    search_requested = pyqtSignal(str)
    ssa_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        """Setup the main tab UI."""
        layout = self.get_layout()

        # Search section
        search_group = self._create_search_section()
        layout.addWidget(search_group)

        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Table section
        table_widget = self._create_table_section()
        splitter.addWidget(table_widget)

        # Details section
        details_widget = self._create_details_section()
        splitter.addWidget(details_widget)

        splitter.setStretchFactor(0, 3)  # Table gets 75%
        splitter.setStretchFactor(1, 1)  # Details gets 25%

        layout.addWidget(splitter)

    def _create_search_section(self):
        """Create search bar section."""
        group = QGroupBox("Pesquisa")
        layout = QHBoxLayout()

        # Search label
        self.search_label = QLabel("Buscar:")
        layout.addWidget(self.search_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite termos separados por virgula")
        self.search_input.returnPressed.connect(self._on_search)
        layout.addWidget(self.search_input)

        # Search button
        self.search_button = QPushButton("Filtrar")
        self.search_button.clicked.connect(self._on_search)
        layout.addWidget(self.search_button)

        # Clear button
        self.clear_button = QPushButton("Limpar")
        self.clear_button.clicked.connect(self._on_clear)
        layout.addWidget(self.clear_button)

        # Help text
        self.help_label = QLabel("Dica: use virgulas para separar termos")
        self.help_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.help_label)

        group.setLayout(layout)
        return group

    def _create_table_section(self):
        """Create table widget."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Table
        self.table_widget = QTableWidget()
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table_widget)

        widget.setLayout(layout)
        return widget

    def _create_details_section(self):
        """Create details panel."""
        group = QGroupBox("Detalhes da SSA")
        layout = QVBoxLayout()

        # Details text
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)

        group.setLayout(layout)
        return group

    def _on_search(self):
        """Handle search button click."""
        text = self.search_input.text().strip()
        print(f"[MainTab] Search requested: '{text}'")
        print(f"[MainTab] Text length: {len(text)}")
        print(f"[MainTab] Text repr: {text!r}")

        # Log each character
        for i, char in enumerate(text):
            print(f"[MainTab] Char {i}: '{char}' (ord={ord(char)})")

        self.search_requested.emit(text)

    def _on_clear(self):
        """Handle clear button click."""
        self.search_input.clear()
        self.search_requested.emit("")

    def _on_row_selected(self):
        """Handle row selection."""
        selected = self.table_widget.selectedItems()
        if selected:
            row = selected[0].row()
            self.ssa_selected.emit(row)

    def set_search_text(self, text: str):
        """Set search input text (called externally)."""
        print(f"[MainTab] set_search_text called: '{text}'")
        print(f"[MainTab] Text repr: {text!r}")
        self.search_input.setText(text)

    def get_search_text(self) -> str:
        """Get current search text."""
        text = self.search_input.text()
        print(f"[MainTab] get_search_text returning: '{text}'")
        return text
