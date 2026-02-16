# gui/widgets/rescan_progress_dialog.py
# Progress dialog for database rescanning

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QProgressBar, QLabel
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class RescanProgressDialog(QDialog):
    """
    Dialog showing real-time progress of database rescan.

    Features:
    - Real-time output from main.py
    - Progress bar
    - Separate display for errors
    - Cancel button
    """

    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reescaneamento em Andamento")
        self.setModal(True)
        self.resize(800, 600)
        self._cancel_requested = False
        self._finished = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Iniciando reescaneamento...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Output section
        output_label = QLabel("Saida do Processo:")
        output_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.output_text)

        # Error section
        error_label = QLabel("Erros e Avisos:")
        error_label.setStyleSheet("font-weight: bold; color: red;")
        layout.addWidget(error_label)

        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setFont(QFont("Courier New", 9))
        self.error_text.setMaximumHeight(150)
        layout.addWidget(self.error_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()

        self.close_button = QPushButton("Fechar")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def append_output(self, line: str):
        """Append line to output display."""
        # When the dialog is cancelled and closed, the worker may still emit a few
        # lines while stopping. Avoid spending UI time updating a hidden dialog.
        if self._cancel_requested and not self.isVisible():
            return
        self.output_text.append(line)
        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_error(self, line: str):
        """Append line to error display."""
        if self._cancel_requested and not self.isVisible():
            return
        self.error_text.append(line)
        # Auto-scroll to bottom
        scrollbar = self.error_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, percentage: int, message: str):
        """Update progress bar and status."""
        if self._cancel_requested and not self.isVisible():
            return
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def set_finished(self, success: bool, message: str = ""):
        """Mark process as finished."""
        self._finished = True
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)

        if success:
            self.status_label.setText("Reescaneamento concluido com sucesso!")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: green;")
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(f"Reescaneamento falhou: {message}")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: red;")
            if message:
                self.append_error(f"\nERRO FINAL: {message}")

    def reject(self) -> None:
        """Request cancel and close the dialog while running.

        The rescan can take time to stop. Keeping the dialog open and modal can
        trap the user and make "exit/close" feel broken. Here we request cancel
        once and allow the dialog to close immediately.
        """
        if self._finished:
            super().reject()
            return
        if not self._cancel_requested:
            self._cancel_requested = True
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelamento solicitado. Aguarde...")
            self.cancel_requested.emit()
        # Mantem dialogo aberto enquanto o worker finaliza, evitando fechar cedo.
