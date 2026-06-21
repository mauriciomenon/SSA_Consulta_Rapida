"""Details dialog presentation for SSA details and derivadas graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import pandas as pd

from gui.qt_stubs import QTimer
from gui.ssa.details_dialog_navigation import resolve_details_anchor
from gui.ssa.details_dialog_view import (
    assemble_details_dialog_layout,
    build_details_dialog_widgets,
)
from gui.ssa.details_graph_export import (
    DetailsGraphExportController,
    load_svg_render_dependencies,
    render_graph_svg_pixmap,
)


@dataclass(frozen=True)
class DetailsDialogCallbacks:
    apply_geometry: Callable[[Any, Any, Any], None]
    build_graph_html: Callable[..., str]
    build_mermaid_text: Callable[[Mapping[str, object]], str]
    build_tree_html: Callable[..., str]
    collect_tree_data: Callable[[Any, str], dict[str, object]]
    copy_ssa_to_clipboard: Callable[[str], None]
    extract_svg_markup: Callable[[str], str]
    format_details_html: Callable[..., str]
    get_series_for_ssa: Callable[[Any, str], pd.Series | None]
    logger: Any
    normalize_ssa_value: Callable[[Any, Any], str]
    resolve_style: Callable[[Any, Any], tuple[str, float, float, float, str]]


@dataclass(frozen=True)
class DetailsDialogRenderPayload:
    details_html: str
    graph_html: str
    graph_svg: str
    mermaid_text: str
    tree_html: str


class DetailsDialogPresenter:
    def __init__(
        self,
        *,
        window: Any,
        target: str,
        series: pd.Series,
        callbacks: DetailsDialogCallbacks,
    ) -> None:
        self.window = window
        self.target = target
        self.series = series
        self.callbacks = callbacks
        self.current_target = {"ssa": target}
        self.export_state: dict[str, object] = {
            "svg": "",
            "mermaid": "",
            "target": target,
        }
        self._style: tuple[str, float, float, float, str] | None = None
        self._svg_render_deps = None
        self._render_cache: dict[str, DetailsDialogRenderPayload] = {}
        self._last_graph_render_key: tuple[str, int, int] | None = None
        self._widgets: Any | None = None

    def open(self) -> None:
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPalette
            from PyQt6.QtWidgets import (
                QFileDialog,
                QMenu,
                QMessageBox,
            )
        except Exception:
            return

        self._svg_render_deps = load_svg_render_dependencies()
        if self._svg_render_deps is None:
            self.callbacks.logger.debug(
                "QSvgRenderer unavailable for derivadas graph rendering"
            )
        widgets = build_details_dialog_widgets(
            self.window, self.target, svg_render_deps=self._svg_render_deps
        )
        self._widgets = widgets
        setattr(widgets.dialog, "_ssa_details_dialog_presenter", self)
        self._style = self.callbacks.resolve_style(self.window, QPalette)
        export_controller = DetailsGraphExportController(
            dialog=widgets.dialog,
            graph_widget=widgets.tree_graph_browser,
            export_state=self.export_state,
            file_dialog_cls=QFileDialog,
            message_box_cls=QMessageBox,
            menu_cls=QMenu,
            logger=self.callbacks.logger,
        )
        self._connect_actions(
            widgets=widgets,
            export_controller=export_controller,
            qt_cls=Qt,
        )
        if not self._render_target(
            widgets=widgets,
            style=self._style,
            svg_render_deps=self._svg_render_deps,
            ssa_target=self.target,
            resolved_series=self.series,
        ):
            return

        assemble_details_dialog_layout(widgets, qt_cls=Qt)
        self.callbacks.apply_geometry(
            self.window, widgets.dialog, widgets.details_splitter
        )
        if widgets.tree_graph_label is not None:
            QTimer.singleShot(
                0,
                lambda: self._refresh_graph_after_resize(
                    widgets, self._svg_render_deps
                ),
            )
        self._show_dialog(widgets.dialog)

    def _connect_actions(self, *, widgets, export_controller, qt_cls) -> None:
        widgets.details_browser.anchorClicked.connect(
            lambda url: self._handle_anchor(widgets, url)
        )
        widgets.tree_browser.anchorClicked.connect(
            lambda url: self._handle_anchor(widgets, url)
        )
        if widgets.tree_graph_text_browser is not None:
            widgets.tree_graph_text_browser.anchorClicked.connect(
                lambda url: self._handle_anchor(widgets, url)
            )
        widgets.tree_graph_browser.setContextMenuPolicy(
            qt_cls.ContextMenuPolicy.CustomContextMenu
        )
        widgets.tree_graph_browser.customContextMenuRequested.connect(
            lambda pos: export_controller.show_menu(
                widgets.tree_graph_browser.mapToGlobal(pos)
            )
        )
        widgets.export_button.clicked.connect(
            lambda: export_controller.show_menu(
                widgets.export_button.mapToGlobal(
                    widgets.export_button.rect().bottomRight()
                )
            )
        )
        widgets.close_button.clicked.connect(widgets.dialog.accept)

    def _render_target(
        self,
        *,
        widgets,
        style,
        svg_render_deps,
        ssa_target,
        resolved_series=None,
    ) -> bool:
        if style is None:
            style = self.callbacks.resolve_style(self.window, self._palette_cls())
        link_color, font_pt, label_font_pt, tree_font_pt, font_family = style
        self.export_state["svg"] = ""
        self.export_state["mermaid"] = ""
        normalized = self.callbacks.normalize_ssa_value(self.window, ssa_target)
        if not normalized:
            return False
        series_target = self._resolve_series(normalized, resolved_series)
        if series_target is None:
            return False
        self.current_target["ssa"] = normalized
        self.export_state["target"] = normalized
        payload = self._get_render_payload(
            normalized=normalized,
            series_target=series_target,
            link_color=link_color,
            font_pt=font_pt,
            label_font_pt=label_font_pt,
            tree_font_pt=tree_font_pt,
            font_family=font_family,
        )
        widgets.details_browser.setHtml(payload.details_html)
        self._render_tree_html(widgets, payload.tree_html)
        self._render_graph(widgets, payload, svg_render_deps)
        return True

    def _get_render_payload(
        self,
        *,
        normalized: str,
        series_target: pd.Series,
        link_color: str,
        font_pt: float,
        label_font_pt: float,
        tree_font_pt: float,
        font_family: str,
    ) -> DetailsDialogRenderPayload:
        cached = self._render_cache.get(normalized)
        if cached is not None:
            return cached
        ssa_index: dict[str, pd.Series] = {}
        tree_data = self.callbacks.collect_tree_data(self.window, normalized)
        details_html = self.callbacks.format_details_html(
            self.window,
            series_target,
            highlight_search_terms=True,
            font_size_pt=font_pt,
            linkify=True,
            label_font_size_pt=label_font_pt,
            font_family=font_family,
            ssa_index=ssa_index,
        )
        tree_html = self.callbacks.build_tree_html(
            self.window,
            normalized,
            link_color=link_color,
            tree_font_pt=tree_font_pt,
            font_family=font_family,
            tree_data_override=tree_data,
            ssa_index=ssa_index,
        )
        mermaid_text = self.callbacks.build_mermaid_text(tree_data)
        graph_html = self.callbacks.build_graph_html(
            self.window,
            tree_data,
            link_color=link_color,
            font_family=font_family,
        )
        payload = DetailsDialogRenderPayload(
            details_html=details_html,
            graph_html=graph_html,
            graph_svg=self.callbacks.extract_svg_markup(graph_html),
            mermaid_text=mermaid_text,
            tree_html=tree_html,
        )
        self._render_cache[normalized] = payload
        return payload

    def _resolve_series(self, normalized: str, resolved_series):
        if resolved_series is not None:
            try:
                matches_target = (
                    self.callbacks.normalize_ssa_value(
                        self.window, resolved_series.get("numero_ssa")
                    )
                    == normalized
                )
            except (AttributeError, KeyError, TypeError):
                matches_target = False
            if not matches_target:
                resolved_series = None
        if resolved_series is None:
            resolved_series = self.callbacks.get_series_for_ssa(self.window, normalized)
        return resolved_series

    def _render_tree_html(
        self,
        widgets,
        tree_html: str,
    ) -> None:
        if tree_html:
            widgets.tree_browser.setHtml(tree_html)
        else:
            widgets.tree_browser.setPlainText("Arvore de derivadas indisponivel.")

    def _render_graph(
        self,
        widgets,
        payload: DetailsDialogRenderPayload,
        svg_render_deps,
    ) -> None:
        self.export_state["svg"] = payload.graph_svg
        self.export_state["mermaid"] = payload.mermaid_text
        if widgets.tree_graph_label is not None:
            if not payload.graph_svg or not self._render_graph_pixmap(
                widgets, svg_render_deps
            ):
                self._last_graph_render_key = None
                widgets.tree_graph_label.setText("Grafo de derivadas indisponivel.")
                if svg_render_deps is not None:
                    widgets.tree_graph_label.setPixmap(svg_render_deps.pixmap_cls())
                widgets.tree_graph_label.setToolTip("Grafo de derivadas indisponivel.")
        elif payload.graph_html and widgets.tree_graph_text_browser is not None:
            widgets.tree_graph_text_browser.setHtml(payload.graph_html)
        elif widgets.tree_graph_text_browser is not None:
            widgets.tree_graph_text_browser.setPlainText(
                "Grafo de derivadas indisponivel."
            )
        else:
            self.callbacks.logger.warning("Widget de grafo de derivadas ausente")

    def _render_graph_pixmap(self, widgets, svg_render_deps) -> bool:
        graph_svg = str(self.export_state["svg"] or "")
        if not graph_svg or widgets.tree_graph_label is None or svg_render_deps is None:
            return False
        key = (
            graph_svg,
            int(widgets.tree_graph_panel.width()),
            int(widgets.tree_graph_panel.height()),
        )
        if key == self._last_graph_render_key:
            pixmap = widgets.tree_graph_label.pixmap()
            if pixmap is not None and not pixmap.isNull():
                return True
        rendered = render_graph_svg_pixmap(
            graph_svg=graph_svg,
            graph_label=widgets.tree_graph_label,
            graph_panel=widgets.tree_graph_panel,
            dependencies=svg_render_deps,
            resize_label=False,
        )
        if rendered:
            self._last_graph_render_key = key
            set_svg_markup = getattr(widgets.tree_graph_label, "set_graph_svg_markup", None)
            if callable(set_svg_markup):
                set_svg_markup(graph_svg)
            refresh_hitboxes = getattr(widgets.tree_graph_label, "_refresh_hitboxes_from_svg", None)
            if callable(refresh_hitboxes):
                refresh_hitboxes()
        else:
            self._last_graph_render_key = None
            clear_svg_markup = getattr(
                widgets.tree_graph_label, "clear_graph_svg_markup", None
            )
            if callable(clear_svg_markup):
                clear_svg_markup()
            set_hitboxes = getattr(widgets.tree_graph_label, "set_ssa_hitboxes", None)
            if callable(set_hitboxes):
                set_hitboxes([])
            widgets.tree_graph_label.clear()
        return rendered

    def _refresh_graph_after_resize(self, widgets, svg_render_deps) -> None:
        if self.export_state["svg"]:
            self._render_graph_pixmap(widgets, svg_render_deps)

    def refresh_after_theme(self) -> None:
        if self._widgets is None:
            return
        self._style = self.callbacks.resolve_style(self.window, self._palette_cls())
        self._render_cache.clear()
        self._last_graph_render_key = None
        self._render_target(
            widgets=self._widgets,
            style=self._style,
            svg_render_deps=self._svg_render_deps,
            ssa_target=self.current_target["ssa"],
        )

    def _show_dialog(self, dialog) -> None:
        qt_cls = self._qt_cls()
        dialog.setModal(False)
        dialog.setWindowModality(qt_cls.WindowModality.NonModal)
        dialog.setAttribute(qt_cls.WidgetAttribute.WA_DeleteOnClose, True)
        open_dialogs = getattr(self.window, "_open_details_dialogs", None)
        if not isinstance(open_dialogs, list):
            open_dialogs = []
            setattr(self.window, "_open_details_dialogs", open_dialogs)
        open_dialogs.append(dialog)
        dialog.destroyed.connect(lambda _obj=None: self._forget_dialog(dialog))
        dialog.show()

    def _forget_dialog(self, dialog) -> None:
        open_dialogs = getattr(self.window, "_open_details_dialogs", None)
        if isinstance(open_dialogs, list):
            try:
                open_dialogs.remove(dialog)
            except ValueError:
                self.callbacks.logger.debug("Details dialog was already forgotten")
        try:
            if getattr(dialog, "_ssa_details_dialog_presenter", None) is self:
                delattr(dialog, "_ssa_details_dialog_presenter")
        except (AttributeError, RuntimeError):
            self.callbacks.logger.debug("Details dialog back-reference was unavailable")
        try:
            widgets_dialog = getattr(self._widgets, "dialog", None)
        except RuntimeError:
            widgets_dialog = dialog
        if widgets_dialog is dialog:
            self._widgets = None
            self._last_graph_render_key = None
            self._render_cache.clear()

    def _handle_anchor(self, widgets, url) -> None:
        try:
            href = url.toString()
        except Exception:
            return
        if not href:
            return
        action, target_href = resolve_details_anchor(href)
        if action == "copy":
            if target_href:
                self.callbacks.copy_ssa_to_clipboard(target_href)
            return
        if action == "ssa" and target_href:
            if target_href == self.current_target["ssa"]:
                return
            target_series = self.callbacks.get_series_for_ssa(self.window, target_href)
            self._render_target(
                widgets=widgets,
                style=self._style or self.callbacks.resolve_style(
                    self.window, self._palette_cls()
                ),
                svg_render_deps=self._svg_render_deps,
                ssa_target=target_href,
                resolved_series=target_series,
            )
            return
        if action == "root":
            if self.current_target["ssa"] == self.target:
                return
            self._render_target(
                widgets=widgets,
                style=self._style or self.callbacks.resolve_style(
                    self.window, self._palette_cls()
                ),
                svg_render_deps=self._svg_render_deps,
                ssa_target=self.target,
                resolved_series=self.series,
            )

    @staticmethod
    def _palette_cls():
        from PyQt6.QtGui import QPalette

        return QPalette

    @staticmethod
    def _qt_cls():
        from PyQt6.QtCore import Qt

        return Qt
