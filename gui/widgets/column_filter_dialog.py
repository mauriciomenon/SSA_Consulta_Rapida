# Dialog for entering a single column filter term.

import logging

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


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

    def _target_screen_geometry(self):
        parent_widget = self.parentWidget()
        candidate_widgets = []
        if parent_widget is not None:
            candidate_widgets.append(parent_widget)
            try:
                parent_window = parent_widget.window()
            except (AttributeError, RuntimeError, TypeError) as exc:
                logger.debug("Falha ao obter janela pai do dialogo de filtro: %s", exc)
                parent_window = None
            if parent_window is not None and parent_window is not parent_widget:
                candidate_widgets.append(parent_window)
        for widget in candidate_widgets:
            try:
                window_handle = widget.windowHandle()
                if window_handle is not None:
                    screen = window_handle.screen()
                    if screen is not None:
                        return screen.availableGeometry()
            except (AttributeError, RuntimeError, TypeError) as exc:
                logger.debug("Falha ao obter screen via windowHandle no filtro: %s", exc)
            try:
                screen = QApplication.screenAt(widget.frameGeometry().center())
                if screen is not None:
                    return screen.availableGeometry()
            except (AttributeError, RuntimeError, TypeError) as exc:
                logger.debug("Falha ao obter screen via screenAt no filtro: %s", exc)
        try:
            screen = self.screen()
            if screen is not None:
                return screen.availableGeometry()
        except (AttributeError, RuntimeError, TypeError) as exc:
            logger.debug("Falha ao obter screen atual do filtro: %s", exc)
        try:
            screen = QApplication.primaryScreen()
            if screen is not None:
                return screen.availableGeometry()
        except (AttributeError, RuntimeError, TypeError) as exc:
            logger.debug("Falha ao obter screen primario do filtro: %s", exc)
        return None

    def _position_on_parent_screen(self) -> None:
        screen_geometry = self._target_screen_geometry()
        if screen_geometry is None:
            return
        try:
            self.adjustSize()
        except (AttributeError, RuntimeError, TypeError) as exc:
            logger.debug("Falha ao ajustar tamanho do dialogo de filtro: %s", exc)
        try:
            dialog_geometry = self.frameGeometry()
        except (AttributeError, RuntimeError, TypeError) as exc:
            logger.debug("Falha ao obter geometria do dialogo de filtro: %s", exc)
            return
        target_x = screen_geometry.left() + max(
            0, (screen_geometry.width() - dialog_geometry.width()) // 2
        )
        target_y = screen_geometry.top() + max(
            0, (screen_geometry.height() - dialog_geometry.height()) // 2
        )
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            try:
                parent_center = parent_widget.frameGeometry().center()
                target_x = parent_center.x() - (dialog_geometry.width() // 2)
                target_y = parent_center.y() - (dialog_geometry.height() // 2)
            except (AttributeError, RuntimeError, TypeError) as exc:
                logger.debug("Falha ao centralizar filtro relativo ao pai: %s", exc)
        max_x = screen_geometry.right() - dialog_geometry.width() + 1
        max_y = screen_geometry.bottom() - dialog_geometry.height() + 1
        target_x = max(screen_geometry.left(), min(target_x, max_x))
        target_y = max(screen_geometry.top(), min(target_y, max_y))
        self.move(target_x, target_y)

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
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logger.debug("Falha ao ajustar fonte de hint do filtro: %s", exc)
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
