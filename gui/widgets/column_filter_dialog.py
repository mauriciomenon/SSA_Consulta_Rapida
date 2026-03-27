# Dialog for entering a single column filter term.

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class ColumnFilterDialog(QDialog):
    """Dialogo pequeno para filtro por coluna."""

    def __init__(
        self,
        column_name: str,
        initial_value: str = "",
        *,
        hint_text: str = "",
        min_width: int = 420,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Filtro por coluna")
        self.setMinimumWidth(max(320, int(min_width)))
        self._input = QLineEdit()
        self._build_ui(column_name, initial_value, hint_text)

    def _build_ui(self, column_name: str, initial_value: str, hint_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(f"Termo para '{column_name}'")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if str(hint_text or "").strip():
            hint_label = QLabel(str(hint_text))
            hint_font = hint_label.font()
            try:
                point_size = hint_font.pointSize()
                if point_size > 0:
                    hint_font.setPointSize(max(8, point_size - 1))
                hint_label.setFont(hint_font)
            except Exception:
                pass
            hint_label.setWordWrap(True)
            layout.addWidget(hint_label)

        self._input.setText(str(initial_value or ""))
        self._input.selectAll()
        layout.addWidget(self._input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._input.setFocus()

    def get_value(self) -> str:
        return self._input.text()
