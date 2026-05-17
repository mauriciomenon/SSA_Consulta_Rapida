"""Resize handling for the SSA main window."""

from __future__ import annotations

from typing import Any, Protocol

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")
RESIZE_WIDTH_SAMPLE_ROWS = 100


class ResizeWindowProtocol(Protocol):
    _active_filter_panel_kind: str | None
    _data_revision: int
    _gui_column_pixel_widths: dict[str, int]
    _current_display_columns: list[str]
    _last_resize_width_key: tuple[int, int, int, int, int] | None
    _last_window_width: int
    _resize_controller: "MainWindowResizeController"
    _resize_recompute_timer: Any
    _resize_timer_cls: Any
    adv_filters_group: Any
    df_para_tabela: Any
    table_widget: Any

    def width(self) -> int: ...
    def isVisible(self) -> bool: ...
    def _reorganize_advanced_filters_grid(self, width: int) -> None: ...
    def _sync_bottom_panel_heights(self) -> None: ...
    def _compute_gui_column_widths(self, width_df: Any) -> None: ...
    def _recompute_column_widths_on_resize(
        self, expected_revision: int | None = None
    ) -> None: ...

_sip: Any | None
try:
    from PyQt6 import sip as _qt_sip

    _sip = _qt_sip
except Exception:  # pragma: no cover - import depends on Qt availability.
    _sip = None


def _is_widget_valid(widget: Any) -> bool:
    if widget is None:
        return False
    if _sip is not None:
        try:
            if _sip.isdeleted(widget):
                return False
        except Exception as exc:
            logger.debug("Falha ao validar widget Qt durante resize: %s", exc)
            return False
    return True


class MainWindowResizeController:
    """Owns resize debounce state for SSAMainWindow."""

    def __init__(self, window: ResizeWindowProtocol, qtimer_cls: Any):
        self.window = window
        self.qtimer_cls = qtimer_cls
        self.pending_revision: int | None = None
        self.pending_adv_filters_width: int | None = None
        self.pending_sync_bottom = False
        self.last_window_width = int(window.width()) if hasattr(window, "width") else 0
        window._last_window_width = self.last_window_width
        self.timer = qtimer_cls(window)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timeout)

    def handle_resize_event(self, event: Any) -> None:
        self._sync_legacy_width_alias()
        self.pending_adv_filters_width = self._pending_advanced_layout_width()
        self.pending_sync_bottom = True

        if not self._should_recompute_column_widths():
            self.schedule(expected_revision=None)
            self._store_last_window_width(event.size().width())
            return

        expected_revision = int(getattr(self.window, "_data_revision", 0) or 0)
        self.schedule(expected_revision=expected_revision)
        self._store_last_window_width(event.size().width())

    def _sync_legacy_width_alias(self) -> None:
        legacy_width = getattr(self.window, "_last_window_width", None)
        if legacy_width is None:
            return
        try:
            self.last_window_width = int(legacy_width)
        except (TypeError, ValueError):
            logger.debug("Largura legada invalida durante resize: %r", legacy_width)

    def _store_last_window_width(self, width: int) -> None:
        self.last_window_width = int(width)
        self.window._last_window_width = self.last_window_width

    def _pending_advanced_layout_width(self) -> int | None:
        try:
            if getattr(self.window, "_active_filter_panel_kind", None) != "advanced":
                return None
            adv_group = getattr(self.window, "adv_filters_group", None)
            if not adv_group:
                return None
            return int(adv_group.width())
        except Exception as exc:
            logger.debug(
                "Falha ao capturar largura dos filtros durante resize: %s", exc
            )
            return None

    def _should_recompute_column_widths(self) -> bool:
        if not hasattr(self.window, "df_para_tabela"):
            return False
        return not self.window.df_para_tabela.empty

    def schedule(self, expected_revision: int | None) -> None:
        try:
            if expected_revision is not None:
                self.pending_revision = int(expected_revision)
            if self.timer is not None:
                self.timer.setInterval(300)
                self.timer.start()
                return
            self.qtimer_cls.singleShot(300, self.on_timeout)
        except Exception as exc:
            logger.debug("Falha ao agendar recompute de resize: %s", exc)

    def on_timeout(self) -> None:
        expected_revision = self.pending_revision
        self.pending_revision = None
        self.apply_pending_layout()
        if expected_revision is not None:
            self.window._recompute_column_widths_on_resize(
                expected_revision=expected_revision
            )

    def apply_pending_layout(self) -> None:
        adv_filters_width = self.pending_adv_filters_width
        self.pending_adv_filters_width = None
        sync_bottom = self.pending_sync_bottom
        self.pending_sync_bottom = False

        if adv_filters_width is not None:
            try:
                self.window._reorganize_advanced_filters_grid(int(adv_filters_width))
            except Exception as exc:
                logger.debug(
                    "Falha ao reorganizar grid de filtros durante resize: %s", exc
                )
        if sync_bottom:
            try:
                self.window._sync_bottom_panel_heights()
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar altura dos paineis inferiores durante resize: %s",
                    exc,
                )

    def recompute_column_widths(self, expected_revision: int | None = None) -> None:
        try:
            table_widget = self._visible_table_widget()
            if table_widget is None:
                return
            if not self._revision_matches(expected_revision):
                return

            width_key = self._current_width_key()
            if getattr(self.window, "_last_resize_width_key", None) == width_key:
                return

            self.window._compute_gui_column_widths(self._sample_width_dataframe())
            self.apply_computed_widths_only()
            self.window._last_resize_width_key = width_key
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.exception("Column width recompute failed during resize")

    def _visible_table_widget(self) -> Any | None:
        if hasattr(self.window, "isVisible") and not self.window.isVisible():
            return None
        table_widget = getattr(self.window, "table_widget", None)
        if not _is_widget_valid(table_widget):
            return None
        if (
            table_widget is None
            or not hasattr(self.window, "df_para_tabela")
            or self.window.df_para_tabela.empty
            or not table_widget.isVisible()
        ):
            return None
        return table_widget

    def _revision_matches(self, expected_revision: int | None) -> bool:
        if expected_revision is None:
            return True
        current_revision = int(getattr(self.window, "_data_revision", 0) or 0)
        return current_revision == int(expected_revision)

    def _current_width_key(self) -> tuple[int, int, int, int, int]:
        return (
            id(self.window.df_para_tabela),
            len(self.window.df_para_tabela.index),
            len(self.window.df_para_tabela.columns),
            int(getattr(self.window, "_data_revision", 0) or 0),
            int(self.last_window_width),
        )

    def _sample_width_dataframe(self) -> Any:
        width_df = self.window.df_para_tabela
        if len(width_df.index) > RESIZE_WIDTH_SAMPLE_ROWS:
            return width_df.head(RESIZE_WIDTH_SAMPLE_ROWS)
        return width_df

    def apply_computed_widths_only(self) -> None:
        try:
            if (
                not hasattr(self.window, "df_para_tabela")
                or self.window.df_para_tabela.empty
                or not hasattr(self.window, "_gui_column_pixel_widths")
                or not self.window.table_widget
                or not self.window.table_widget.isVisible()
            ):
                return

            table_columns = getattr(self.window, "_current_display_columns", None)
            if not table_columns:
                return

            table_widget = self.window.table_widget
            widths = self.window._gui_column_pixel_widths
            table_column_index = {name: idx for idx, name in enumerate(table_columns)}
            table_widget.setUpdatesEnabled(False)
            try:
                for col_name, px in widths.items():
                    col_index = table_column_index.get(col_name)
                    if col_index is None or not px or px <= 0:
                        continue
                    if col_index < table_widget.columnCount():
                        current_width = table_widget.columnWidth(col_index)
                        if current_width != px:
                            table_widget.setColumnWidth(col_index, px)
            finally:
                table_widget.setUpdatesEnabled(True)

        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.exception("Column width apply failed during resize handling")


def initialize_resize_controller(
    window: ResizeWindowProtocol, qtimer_cls: Any
) -> MainWindowResizeController:
    controller = MainWindowResizeController(window, qtimer_cls)
    window._resize_controller = controller
    window._resize_recompute_timer = controller.timer
    return controller


def _controller(window: ResizeWindowProtocol) -> MainWindowResizeController | None:
    controller = getattr(window, "_resize_controller", None)
    if controller is None:
        qtimer_cls = getattr(window, "_resize_timer_cls", None)
        if qtimer_cls is None:
            try:
                from PyQt6.QtCore import QTimer as qtimer_cls
            except Exception as exc:
                logger.debug("QTimer indisponivel para resize controller: %s", exc)
                return None

        controller = initialize_resize_controller(window, qtimer_cls)
    return controller


def handle_resize_event(window: ResizeWindowProtocol, event: Any) -> None:
    controller = _controller(window)
    if controller is not None:
        controller.handle_resize_event(event)


def recompute_column_widths_on_resize(
    window: ResizeWindowProtocol, expected_revision: int | None = None
) -> None:
    controller = _controller(window)
    if controller is not None:
        controller.recompute_column_widths(expected_revision=expected_revision)


def schedule_resize_recompute(
    window: ResizeWindowProtocol, expected_revision: int | None
) -> None:
    controller = _controller(window)
    if controller is not None:
        controller.schedule(expected_revision=expected_revision)


def on_resize_recompute_timeout(window: ResizeWindowProtocol) -> None:
    controller = _controller(window)
    if controller is not None:
        controller.on_timeout()


def apply_computed_widths_only(window: ResizeWindowProtocol) -> None:
    controller = _controller(window)
    if controller is not None:
        controller.apply_computed_widths_only()
