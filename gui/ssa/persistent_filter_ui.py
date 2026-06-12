"""Persistent filter UI controller."""

from __future__ import annotations

import unicodedata
from typing import Any, Callable, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
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
        apply_advanced = getattr(self.window, "_apply_advanced_filters_from_ui", None)
        if callable(apply_advanced):
            try:
                apply_advanced(store_only=True)
            except Exception as exc:
                logger.warning(
                    "Falha ao sincronizar filtros avancados antes de salvar filtro: %s",
                    exc,
                )
        try:
            current_state = self.window._snapshot_filter_state()
        except Exception as exc:
            logger.warning("Falha ao capturar filtro atual para salvar: %s", exc)
            QMessageBox.warning(
                qt_parent(self.window),
                "Erro",
                "Nao foi possivel ler o filtro atual para salvar.",
            )
            return
        current_text = str(current_state.get("search_text", "") or "").strip()
        if not self._has_filter_state(current_state, current_text):
            QMessageBox.information(
                qt_parent(self.window),
                "Aviso",
                "Aplique algum filtro antes de salvar.",
            )
            return

        current_state_key = persistent_filter_state_key(current_state)
        index = self.index()
        if current_state_key in index.state_keys or (
            not current_state_key and current_text in index.legacy_terms
        ):
            QMessageBox.information(
                qt_parent(self.window), "Aviso", "Este filtro ja esta salvo."
            )
            return

        suggested_name = build_persistent_filter_name(
            current_state,
            existing_count=len(self.window.persistent_filters),
        )
        raw_filter_name, accepted = QInputDialog.getText(
            qt_parent(self.window),
            "Salvar filtro",
            "Nome do filtro:",
            text=suggested_name,
        )
        if not accepted:
            return
        filter_name = self._fit_filter_name_to_search_width(
            str(raw_filter_name or "").strip()
        )
        if not filter_name:
            QMessageBox.information(
                qt_parent(self.window),
                "Aviso",
                "Informe um nome para salvar o filtro.",
            )
            return
        if self._filter_name_exists(filter_name):
            QMessageBox.information(
                qt_parent(self.window),
                "Aviso",
                "Ja existe um filtro salvo com este nome.",
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
#        QMessageBox.information(
#            qt_parent(self.window),
#            "Sucesso",
#            f"Filtro '{filter_name}' salvo com sucesso!",
#        )

    def update_tags(self) -> None:
        self._clear_tag_layout()
        tag_css = self._tag_css()
        apply_filter = self.window.apply_persistent_filter
        remove_filter = self.window.remove_persistent_filter
        sorted_filters = sort_persistent_filters(self.window.persistent_filters)
        filter_count = len(sorted_filters)
        for filter_data in sorted_filters:
            self.window.filter_tags_layout.addWidget(
                self._build_filter_tag_widget(
                    filter_data,
                    tag_css,
                    filter_count=filter_count,
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
        roles = dict(getattr(self.window, "_current_theme_roles", {}) or {})
        if not roles:
            roles = get_theme_roles(getattr(self.window, "_current_theme", "dark"))
        palette_text = self.window.palette().windowText().color().name()
        fg = (
            roles.get("input_text")
            or roles.get("panel_text")
            or roles.get("summary_text_color")
            or palette_text
        )
        border = roles.get("tag_border") or roles.get("input_border") or palette_text
        bg_normal = roles.get("tag_normal_bg") or roles.get("input_bg") or "transparent"
        bg_hover = roles.get("tag_hover") or bg_normal
        bg_pressed = roles.get("tag_pressed") or bg_hover
        return f"""
            QPushButton#persistentFilterTagButton {{
                color: {fg};
                background-color: {bg_normal};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 1px 4px;
                min-width: 24px;
                font-size: 10px;
            }}
            QPushButton#persistentFilterRemoveButton {{
                color: {fg};
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 3px;
                padding: 0px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton#persistentFilterTagButton:hover,
            QPushButton#persistentFilterRemoveButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton#persistentFilterTagButton:pressed,
            QPushButton#persistentFilterRemoveButton:pressed {{
                background-color: {bg_pressed};
            }}
        """

    def _build_filter_tag_widget(
        self,
        filter_data: dict[str, Any],
        tag_css: str,
        *,
        filter_count: int,
        apply_filter: Callable[[Any], None],
        remove_filter: Callable[[Any], None],
    ):
        tag_button_width = self._filter_tag_button_width(filter_count)
        display_name = self._filter_tag_display_name(filter_data, tag_button_width)
        tag_button = QPushButton(display_name)
        tag_button.setObjectName("persistentFilterTagButton")
        tag_button.setMaximumHeight(25)
        tag_button.setMaximumWidth(tag_button_width)
        tag_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        tag_button.setStyleSheet(tag_css)
        tag_button.setToolTip(self._filter_tag_tooltip(filter_data, display_name))
        tag_button.clicked.connect(
            lambda _checked, filter_data=filter_data: apply_filter(filter_data)
        )

        remove_button = QPushButton("X")
        remove_button.setObjectName("persistentFilterRemoveButton")
        remove_button.setFixedSize(18, 20)
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

    def _filter_tag_button_width(self, filter_count: int) -> int:
        try:
            total_width = int(
                self.window.filter_tags_widget.width()
                or self.window.filter_tags_widget.maximumWidth()
                or 280
            )
            tag_count = max(1, filter_count)
            outer_spacing = max(0, tag_count - 1) * 5
            inner_spacing = tag_count * 2
            remove_width = tag_count * 18
            available = total_width - outer_spacing - inner_spacing - remove_width
            return max(36, min(180, available // tag_count))
        except Exception as exc:
            logger.debug(
                "Falha ao calcular largura de tag de filtro persistente: %s", exc
            )
            return 72

    def _filter_tag_display_name(
        self, filter_data: dict[str, Any], tag_button_width: int
    ) -> str:
        name = str(filter_data.get("name") or "").strip()
        if not self._has_visible_text(name):
            name = "Filtro salvo"
        if self._filter_uses_state_without_terms(filter_data):
            suffix = " *"
            suffix_width = self.window.filter_tags_widget.fontMetrics().horizontalAdvance(
                suffix
            )
            return f"{self._fit_filter_name_to_tag_width(name, tag_button_width - suffix_width)}{suffix}"
        return self._fit_filter_name_to_tag_width(name, tag_button_width)

    def _fit_filter_name_to_tag_width(self, filter_name: str, width_px: int) -> str:
        try:
            metrics = self.window.filter_tags_widget.fontMetrics()
            available = max(24, width_px - 8)
            if metrics.horizontalAdvance(filter_name) <= available:
                return filter_name
            return metrics.elidedText(
                filter_name, Qt.TextElideMode.ElideRight, available
            )
        except Exception as exc:
            logger.debug(
                "Falha ao truncar nome da tag de filtro persistente: %s", exc
            )
            return filter_name

    @staticmethod
    def _has_visible_text(text: str) -> bool:
        return any(
            not char.isspace() and unicodedata.category(char) != "Cf"
            for char in text
        )

    def _filter_name_exists(self, filter_name: str) -> bool:
        normalized_name = filter_name.strip().casefold()
        if not normalized_name:
            return False
        return any(
            str(filter_data.get("name") or "").strip().casefold() == normalized_name
            for filter_data in getattr(self.window, "persistent_filters", []) or []
            if isinstance(filter_data, dict)
        )

    @staticmethod
    def _filter_uses_state_without_terms(filter_data: dict[str, Any]) -> bool:
        terms = str(filter_data.get("terms") or "").strip()
        return bool(isinstance(filter_data.get("state"), dict) and not terms)

    def _filter_tag_tooltip(
        self, filter_data: dict[str, Any], display_name: str
    ) -> str:
        lines = ["Clique para aplicar filtro salvo", f"Nome: {display_name}"]
        lines.extend(self._filter_tag_summary_lines(filter_data))
        if len(lines) == 2:
            lines.append("Sem descricao detalhada")
        return "\n".join(lines)

    def _filter_tag_summary_lines(self, filter_data: dict[str, Any]) -> list[str]:
        state = filter_data.get("state")
        state_dict = state if isinstance(state, dict) else {}
        search_text = str(
            filter_data.get("terms") or state_dict.get("search_text") or ""
        ).strip()
        lines = [f"Busca: {search_text}"] if search_text else []
        lines.extend(self._column_filter_summary_lines(state_dict))
        lines.extend(self._advanced_filter_summary_lines(state_dict))
        profile_name = str(state_dict.get("current_filter_profile") or "").strip()
        if profile_name:
            lines.append(f"Perfil: {profile_name}")
        return lines

    @staticmethod
    def _column_filter_summary_lines(state: dict[str, Any]) -> list[str]:
        columns = state.get("active_column_filters")
        if not isinstance(columns, dict):
            return []
        return [
            f"Coluna {key}: {value_text}"
            for key, value in columns.items()
            if (value_text := str(value or "").strip())
        ][:4]

    @staticmethod
    def _advanced_filter_summary_lines(state: dict[str, Any]) -> list[str]:
        advanced = state.get("advanced_filters")
        if not isinstance(advanced, dict):
            return []
        lines: list[str] = []
        for key, value in advanced.items():
            values = value if isinstance(value, (list, tuple, set)) else [value]
            value_text = ", ".join(
                str(item).strip() for item in values if str(item).strip()
            )
            if value_text:
                lines.append(f"Avancado {key}: {value_text}")
            if len(lines) >= 4:
                break
        return lines

    def _apply_state_filter(self, filter_data: dict[str, Any]) -> None:
        try:
            undo_state_before_apply = self.window._snapshot_filter_state()
        except Exception as exc:
            logger.warning(
                "Falha ao salvar estado antes de aplicar filtro persistente: %s",
                exc,
            )
            undo_state_before_apply = None
        try:
            restored_state = self.copy_filter_mapping(filter_data["state"])
            self.window._restore_last_filter_state(
                restored_state,
                consume_undo=False,
            )
        except Exception as exc:
            logger.warning("Falha ao aplicar filtro persistente salvo: %s", exc)
            QMessageBox.warning(
                qt_parent(self.window),
                "Erro",
                "Nao foi possivel aplicar o filtro salvo.",
            )
            return
        refresh_quick_situacao = getattr(
            self.window, "_refresh_quick_situacao_buttons", None
        )
        if callable(refresh_quick_situacao):
            refresh_quick_situacao()
        # The GUI filter undo contract is a single snapshot, not a stack.
        self.window._last_filter_state = undo_state_before_apply
        self.window._update_undo_button_state()
