"""Presenter for the active filters summary bar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QSizePolicy

from gui.ssa.filter_summary_entries import SummaryAction, SummaryEntry, shorten_summary_label
from gui.ssa.filter_summary_style import build_summary_button_stylesheet
from utils.themes import get_theme_roles


@dataclass(frozen=True)
class _SummaryTheme:
    accent: str
    border: str
    text_color: str
    background: str
    font_size: int

    @property
    def style_signature(self) -> tuple[str, str, str, str, int]:
        return self.border, self.accent, self.background, self.text_color, self.font_size


@dataclass(frozen=True)
class FilterSummaryWidgets:
    frame: Any
    label: Any
    items_widget: Any
    items_layout: Any
    scroll: Any


class FilterSummaryPresenter:
    def __init__(self, widgets: FilterSummaryWidgets, logger: Any) -> None:
        self._widgets = widgets
        self._logger = logger
        self._button_pool: list[QPushButton] = []
        self._button_width_cache: dict[tuple, int] = {}
        self._stylesheet_cache: dict[tuple[str, str, str, str, int], str] = {}
        self._on_remove: Callable[[str, list[SummaryAction]], None] | None = None

    def update(
        self,
        *,
        theme_name: str,
        summary_text: str,
        active_state: bool,
        entries: list[SummaryEntry],
        on_remove: Callable[[str, list[SummaryAction]], None],
    ) -> None:
        self._on_remove = on_remove
        self._apply_visual_state(
            theme_name=theme_name,
            summary_text=summary_text,
            active_state=active_state,
        )
        self._rebuild_buttons(entries, theme_name=theme_name)

    def clear_buttons(self) -> None:
        layout = self._widgets.items_layout
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._button_pool = []
        self._button_width_cache.clear()

    def _apply_visual_state(
        self, *, theme_name: str, summary_text: str, active_state: bool
    ) -> None:
        roles = get_theme_roles(theme_name)
        summary_color = (
            roles.get("summary_text_color")
            or roles.get("panel_text")
            or roles.get("label_color")
            or "palette(windowText)"
        )
        summary_bg = self._apply_frame_style(active_state=active_state, roles=roles)
        self._apply_label_style(
            summary_text=summary_text,
            active_state=active_state,
            summary_color=summary_color,
        )
        self._apply_scroll_style(active_state=active_state, summary_bg=summary_bg)

    def _apply_frame_style(self, *, active_state: bool, roles: dict[str, str]) -> str:
        summary_bg = roles.get("summary_frame_bg") or roles.get("panel_bg") or "transparent"
        frame = self._widgets.frame
        if frame is not None:
            active_border = (
                roles.get("accent")
                or roles.get("input_border_focus")
                or roles.get("panel_text")
                or "palette(highlight)"
            )
            idle_border = (
                roles.get("input_border") or roles.get("panel_border") or "palette(mid)"
            )
            frame_border = active_border if active_state else idle_border
            frame.setStyleSheet(
                "QFrame#filtersSummaryFrame {"
                f"background:{summary_bg};"
                f"border:1px solid {frame_border};"
                "border-radius:4px;"
                "}"
            )
        return summary_bg

    def _apply_label_style(
        self, *, summary_text: str, active_state: bool, summary_color: str
    ) -> None:
        label = self._widgets.label
        if label is None:
            return
        label.setText("" if active_state else "Nenhum filtro ativo")
        label.setToolTip(summary_text if active_state else "")
        try:
            label.setVisible(not active_state)
        except Exception as exc:
            self._logger.debug(
                "Falha ao atualizar visibilidade do texto de filtros ativos: %s",
                exc,
            )
        label.setStyleSheet(
            f"color:{summary_color};"
            "background:transparent;"
            "padding:0 2px;"
            + ("font-weight:700;" if active_state else "font-weight:400;")
        )

    def _apply_scroll_style(self, *, active_state: bool, summary_bg: str) -> None:
        scroll = self._widgets.scroll
        if scroll is None:
            return
        try:
            scroll.setVisible(active_state)
            scroll.setStyleSheet(
                "QScrollArea {"
                "border:0;"
                f"background:{summary_bg};"
                "}"
                "QScrollArea > QWidget > QWidget {"
                f"background:{summary_bg};"
                "}"
            )
            viewport = scroll.viewport()
            if viewport is not None:
                viewport.setAutoFillBackground(False)
        except Exception as exc:
            self._logger.debug(
                "Falha ao atualizar visibilidade do scroll de filtros ativos: %s",
                exc,
            )

    def _rebuild_buttons(
        self,
        entries: list[SummaryEntry],
        *,
        theme_name: str,
    ) -> None:
        layout = self._widgets.items_layout
        container = self._widgets.items_widget
        if layout is None or container is None:
            return
        if len(self._button_width_cache) > 256:
            self._button_width_cache.clear()
        if len(self._stylesheet_cache) > 32:
            self._stylesheet_cache.clear()
        compact = len(entries) >= 3 or sum(
            len(str(entry.get("text") or "")) for entry in entries
        ) > 60
        theme = self._resolve_button_theme(theme_name, compact=compact)
        self._configure_button_container(container)
        content_width = 0
        spacing = self._layout_spacing(layout)
        visible_button_count = 0
        for index, entry in enumerate(entries):
            button_width = self._sync_entry_button(
                index,
                entry,
                pool=self._button_pool,
                container=container,
                layout=layout,
                style_signature=theme.style_signature,
                stylesheet_cache=self._stylesheet_cache,
                width_cache=self._button_width_cache,
            )
            if button_width <= 0:
                continue
            visible_button_count += 1
            content_width += button_width + spacing
        self._hide_extra_buttons(self._button_pool[visible_button_count:])
        self._sync_container_size(
            container=container,
            layout=layout,
            visible_button_count=visible_button_count,
            content_width=content_width,
        )

    def _resolve_button_theme(self, theme_name: str, *, compact: bool = False) -> _SummaryTheme:
        roles = get_theme_roles(theme_name)
        accent = roles.get("accent") or roles.get("input_border_focus") or "#4a90e2"
        return _SummaryTheme(
            accent=accent,
            border=roles.get("input_border") or roles.get("panel_border") or accent,
            text_color=roles.get("panel_text") or roles.get("label_color") or "inherit",
            background=roles.get("input_bg") or "transparent",
            font_size=11 if compact else 12,
        )

    def _configure_button_container(self, container: Any) -> None:
        try:
            container.setFixedHeight(22)
            container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        except Exception as exc:
            self._logger.debug(
                "Falha ao configurar tamanho do container de filtros ativos: %s", exc
            )

    def _layout_spacing(self, layout: Any) -> int:
        try:
            return int(layout.spacing() or 0)
        except Exception as exc:
            self._logger.debug("Falha ao obter espacamento dos filtros ativos: %s", exc)
            return 0

    def _sync_entry_button(
        self,
        index: int,
        entry: SummaryEntry,
        *,
        pool: list[Any],
        container: Any,
        layout: Any,
        style_signature: tuple[str, str, str, str, int],
        stylesheet_cache: dict,
        width_cache: dict,
    ) -> int:
        text = str(entry.get("text") or "").strip()
        raw_actions = entry.get("actions")
        if not text or not isinstance(raw_actions, list) or not raw_actions:
            return 0
        actions: list[SummaryAction] = [
            cast(SummaryAction, dict(action))
            for action in raw_actions
            if isinstance(action, dict)
        ]
        if not actions:
            return 0
        display_text = shorten_summary_label(text)
        if index < len(pool) and isinstance(pool[index], QPushButton):
            button = pool[index]
        else:
            button = QPushButton(container)
            button.clicked.connect(
                lambda _checked=False, current=button: self._on_button_clicked(current)
            )
            pool.append(button)
            layout.addWidget(button, 0)
        button.setText(display_text)
        button.setToolTip(f"Clique para remover este filtro: {text}")
        button.setProperty("filter_summary_text", text)
        button.setProperty("filter_summary_actions", actions)
        self._apply_button_style(
            button,
            text=text,
            style_signature=style_signature,
            stylesheet_cache=stylesheet_cache,
        )
        width_key = (display_text, style_signature)
        return self._measure_button_width(button, width_key=width_key, width_cache=width_cache)

    def _apply_button_style(
        self,
        button: QPushButton,
        *,
        text: str,
        style_signature: tuple[str, str, str, str, int],
        stylesheet_cache: dict,
    ) -> None:
        border, accent, background, text_color, font_size = style_signature
        try:
            button.setVisible(True)
            button.setFixedHeight(22)
            button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            if button.property("filter_summary_style") != style_signature:
                stylesheet = stylesheet_cache.get(style_signature)
                if not isinstance(stylesheet, str):
                    stylesheet = build_summary_button_stylesheet(
                        border=border,
                        accent=accent,
                        background=background,
                        text_color=text_color,
                        font_size=font_size,
                    )
                    stylesheet_cache[style_signature] = stylesheet
                button.setStyleSheet(stylesheet)
                button.setProperty("filter_summary_style", style_signature)
        except Exception as exc:
            self._logger.debug(
                "Falha ao aplicar estilo em botao do resumo de filtros '%s': %s",
                text,
                exc,
            )

    def _measure_button_width(
        self, button: QPushButton, *, width_key: tuple, width_cache: dict
    ) -> int:
        try:
            button_width = width_cache.get(width_key)
            if not isinstance(button_width, int):
                button_width = int(button.sizeHint().width())
                width_cache[width_key] = button_width
            return button_width
        except Exception as exc:
            self._logger.debug(
                "Falha ao medir largura do botao de filtro ativo: %s", exc
            )
            return 0

    def _hide_extra_buttons(self, buttons: list[Any]) -> None:
        for button in buttons:
            try:
                if isinstance(button, QPushButton):
                    button.setVisible(False)
                    button.setProperty("filter_summary_text", "")
                    button.setProperty("filter_summary_actions", [])
            except TypeError:
                self._logger.debug(
                    "Botao excedente de filtro ativo ja estava sem handler de clique."
                )
            except RuntimeError as exc:
                self._logger.debug(
                    "Falha ao ocultar botao excedente do resumo de filtros: %s", exc
                )

    def _sync_container_size(
        self,
        *,
        container: Any,
        layout: Any,
        visible_button_count: int,
        content_width: int,
    ) -> None:
        try:
            layout.activate()
            scroll = self._widgets.scroll
            viewport_width = 0
            if scroll is not None and scroll.viewport() is not None:
                viewport_width = int(scroll.viewport().width() or 0)
                try:
                    scroll_policy = Qt.ScrollBarPolicy
                    policy = (
                        scroll_policy.ScrollBarAsNeeded
                        if visible_button_count > 0 and content_width > viewport_width
                        else scroll_policy.ScrollBarAlwaysOff
                    )
                    scroll.setHorizontalScrollBarPolicy(policy)
                except Exception as exc:
                    self._logger.debug(
                        "Falha ao ajustar politica do scroll de filtros ativos: %s", exc
                    )
            container.setFixedSize(max(1, content_width, viewport_width), 22)
        except Exception as exc:
            self._logger.debug("Falha ao ajustar largura dos filtros ativos: %s", exc)
        try:
            container.setVisible(visible_button_count > 0)
        except Exception as exc:
            self._logger.debug(
                "Falha ao atualizar visibilidade do container de resumo de filtros: %s",
                exc,
            )

    def _on_button_clicked(
        self,
        button: QPushButton,
    ) -> None:
        item_text = str(button.property("filter_summary_text") or "")
        raw_actions = button.property("filter_summary_actions")
        actions = raw_actions if isinstance(raw_actions, list) else []
        if self._on_remove is not None:
            self._on_remove(item_text, actions)
