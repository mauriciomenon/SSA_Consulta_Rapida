"""Persistent filter UI controller."""

from __future__ import annotations

from typing import Any, Callable, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from gui.ssa.filter_saved_names import build_persistent_filter_name
from gui.ssa.persistent_filters import (
    PersistentFilterStore,
    get_gui_saved_filters_path,
    persistent_filter_state_key,
    sort_persistent_filters,
)
from utils.robust_logging import get_robust_logger
from utils.themes import get_theme_roles

logger = get_robust_logger().get_logger(__name__, "gui")


def qt_parent(obj: Any) -> QWidget | None:
    return cast(QWidget | None, obj)


class PersistentFilterUiController:
    def __init__(
        self,
        window,
        *,
        copy_filter_mapping: Callable[[Any], dict],
        saved_filters_path_factory: Callable[[], str] = get_gui_saved_filters_path,
    ) -> None:
        self.window = window
        self.copy_filter_mapping = copy_filter_mapping
        self.store = PersistentFilterStore(saved_filters_path_factory())

    def load(self) -> None:
        self.window.persistent_filters = self.store.load()
        self.update_tags()

    def save_file(self) -> bool:
        return self.store.save(getattr(self.window, "persistent_filters", []) or [])

    def invalidate_index(self) -> None:
        self.store.invalidate_index()

    def index(self):
        return self.store.index_for(getattr(self.window, "persistent_filters", []) or [])

    def save_current(self) -> None:
        current_state = self.window._snapshot_filter_state()
        current_text = str(current_state.get("search_text", "") or "").strip()
        if not self._has_filter_state(current_state, current_text):
            QMessageBox.information(
                qt_parent(self.window),
                "Aviso",
                "Aplique algum filtro antes de salvar.",
            )
            return

        filter_name = self._fit_filter_name_to_search_width(
            build_persistent_filter_name(
                current_state,
                existing_count=len(self.window.persistent_filters),
            )
        )
        current_state_key = persistent_filter_state_key(current_state)
        index = self.index()
        if current_state_key in index.state_keys or (
            not current_state_key and current_text in index.legacy_terms
        ):
            QMessageBox.information(
                qt_parent(self.window), "Aviso", "Este filtro ja esta salvo."
            )
            return

        new_filter = {
            "name": filter_name,
            "terms": current_text,
            "state": self.copy_filter_mapping(current_state),
        }
        updated_filters, saved = self.store.add_filter(
            self.window.persistent_filters,
            new_filter,
        )
        if not saved:
            QMessageBox.warning(
                qt_parent(self.window),
                "Erro",
                "Nao foi possivel salvar o filtro persistente.",
            )
            return
        self.window.persistent_filters = updated_filters
        self.update_tags()
        QMessageBox.information(
            qt_parent(self.window),
            "Sucesso",
            f"Filtro '{filter_name}' salvo com sucesso!",
        )

    def update_tags(self) -> None:
        self._clear_tag_layout()
        tag_css = self._tag_css()
        apply_filter = self.window.apply_persistent_filter
        remove_filter = self.window.remove_persistent_filter
        for filter_data in sort_persistent_filters(self.window.persistent_filters):
            self.window.filter_tags_layout.addWidget(
                self._build_filter_tag_widget(
                    filter_data,
                    tag_css,
                    apply_filter=apply_filter,
                    remove_filter=remove_filter,
                )
            )

    def apply(self, filter_data) -> None:
        if isinstance(filter_data, dict) and isinstance(filter_data.get("state"), dict):
            self._apply_state_filter(filter_data)
            return
        terms = (
            str(filter_data.get("terms", "") or "")
            if isinstance(filter_data, dict)
            else str(filter_data or "")
        )
        self.window.search_input.setText(terms)
        self.window.initiate_filtering()

    @staticmethod
    def _has_filter_state(current_state: dict[str, Any], current_text: str) -> bool:
        active_columns = current_state.get("active_column_filters") or {}
        active_column_values = [
            str(value).strip()
            for value in active_columns.values()
            if str(value).strip()
        ]
        return bool(
            current_text
            or active_column_values
            or current_state.get("column_or_groups")
            or current_state.get("exclude_ste_sca")
            or current_state.get("advanced_filters_active")
            or current_state.get("current_filter_profile")
        )

    def _fit_filter_name_to_search_width(self, filter_name: str) -> str:
        try:
            metrics = self.window.search_input.fontMetrics()
            width_px = int(
                self.window.search_input.width()
                or self.window.search_input.minimumWidth()
                or 320
            )
            available = max(64, width_px - 40)
            if metrics.horizontalAdvance(filter_name) <= available:
                return filter_name
            return metrics.elidedText(
                filter_name, Qt.TextElideMode.ElideRight, available
            )
        except Exception as exc:
            logger.debug(
                "Falha ao truncar nome de filtro persistente por largura: %s", exc
            )
            return filter_name

    def _clear_tag_layout(self) -> None:
        for i in reversed(range(self.window.filter_tags_layout.count())):
            child = self.window.filter_tags_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

    def _tag_css(self) -> str:
        roles = get_theme_roles(getattr(self.window, "_current_theme", "dark"))
        fg = roles.get(
            "summary_text_color", self.window.palette().windowText().color().name()
        )
        border = roles.get("tag_border")
        bg_normal = roles.get("tag_normal_bg")
        bg_hover = roles.get("tag_hover")
        bg_pressed = roles.get("tag_pressed")
        return f"""
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

    def _build_filter_tag_widget(
        self,
        filter_data: dict[str, Any],
        tag_css: str,
        *,
        apply_filter: Callable[[Any], None],
        remove_filter: Callable[[Any], None],
    ):
        tag_button = QPushButton(filter_data["name"])
        tag_button.setMaximumHeight(25)
        tag_button.setMaximumWidth(180)
        tag_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        tag_button.setStyleSheet(tag_css)
        tag_button.setToolTip(f"Clique para aplicar: {filter_data['terms']}")
        tag_button.clicked.connect(
            lambda _checked, filter_data=filter_data: apply_filter(filter_data)
        )

        remove_button = QPushButton("X")
        remove_button.setMaximumSize(20, 20)
        remove_button.setStyleSheet(tag_css)
        remove_button.setToolTip("Remover filtro")
        remove_button.clicked.connect(
            lambda _checked, filter_data=filter_data: remove_filter(filter_data)
        )

        tag_layout = QHBoxLayout()
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(2)
        tag_layout.addWidget(tag_button)
        tag_layout.addWidget(remove_button)

        tag_widget = QWidget()
        tag_widget.setLayout(tag_layout)
        tag_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        return tag_widget

    def _apply_state_filter(self, filter_data: dict[str, Any]) -> None:
        try:
            undo_state_before_apply = self.window._snapshot_filter_state()
        except Exception as exc:
            logger.warning(
                "Falha ao salvar estado antes de aplicar filtro persistente: %s",
                exc,
            )
            undo_state_before_apply = None
        self.window._restore_last_filter_state(
            self.copy_filter_mapping(filter_data["state"]),
            consume_undo=False,
        )
        # The GUI filter undo contract is a single snapshot, not a stack.
        self.window._last_filter_state = undo_state_before_apply
        self.window._update_undo_button_state()
