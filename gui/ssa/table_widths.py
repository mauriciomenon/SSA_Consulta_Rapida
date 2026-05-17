from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import import_module
from typing import Any

import pandas as pd

from gui.gui_config import DEFAULT_COLUMN_WIDTHS, GUI_MAIN_PREFERENCES
from gui.qt_stubs import QTimer
from utils.robust_logging import get_robust_logger

QObject: Any = None
try:
    qt_core = import_module("PyQt6.QtCore")
    QObject = getattr(qt_core, "QObject", None)
except Exception:
    QObject = None

logger = get_robust_logger().get_logger(__name__, "gui")


@dataclass(frozen=True)
class ColumnWidthContext:
    visible_columns: tuple[str, ...]
    width_manager: Any
    widget_width: int
    window_width: int


def fallback_column_width(col_name: str) -> int:
    if col_name in DEFAULT_COLUMN_WIDTHS:
        return int(DEFAULT_COLUMN_WIDTHS[col_name])
    if col_name == "#":
        return 24
    return 120


def resolve_column_width(
    window,
    col_name: str,
    *,
    include_runtime: bool,
    include_preferences: bool,
) -> int:
    px = getattr(window, "_saved_gui_column_widths", {}).get(col_name)
    if px is None and include_runtime:
        px = getattr(window, "_gui_column_pixel_widths", {}).get(col_name)
    if px is None and include_preferences:
        px = GUI_MAIN_PREFERENCES.get("column_widths", {}).get(col_name)
    if px is None:
        px = fallback_column_width(col_name)
    return int(px)


def needs_width_recompute(window, cols_sig, viewport_width):
    need_cols = (not hasattr(window, "_widths_columns_sig")) or (
        window._widths_columns_sig != cols_sig
    )
    need_vw = (not hasattr(window, "_last_viewport_w")) or (
        abs(viewport_width - window._last_viewport_w) > 12
    )
    saved_widths = getattr(window, "_saved_gui_column_widths", {})
    has_persisted_widths_for_all = isinstance(saved_widths, dict) and all(
        (
            isinstance(width_value := saved_widths.get(col_name), (int, float))
            and int(width_value) > 0
        )
        for col_name in cols_sig
    )
    if need_vw and has_persisted_widths_for_all:
        need_vw = False
    return need_cols or need_vw


def compute_widths_for_df(
    df: pd.DataFrame,
    visible_columns,
    width_manager,
    internal_to_display=None,
    saved_widths=None,
    widget_width: int = 0,
    window_width: int = 0,
):
    del internal_to_display, saved_widths
    context = ColumnWidthContext(
        visible_columns=tuple(visible_columns or ()),
        width_manager=width_manager,
        widget_width=int(widget_width),
        window_width=int(window_width),
    )
    return compute_column_widths_from_context(df, context)


def compute_column_widths_from_context(df: pd.DataFrame, context: ColumnWidthContext):
    if not context.visible_columns:
        return None
    if hasattr(df, "columns"):
        existing_visible_cols = [
            col for col in context.visible_columns if col in df.columns
        ]
        if not existing_visible_cols:
            return None
        sampled_df = sample_width_dataframe(df)
        visible_df = sampled_df[existing_visible_cols]
    else:
        existing_visible_cols = list(context.visible_columns)
        visible_df = df
    table_width = context.widget_width
    if table_width < 500:
        table_width = max(
            1000 if sys.platform == "darwin" else 1400,
            context.window_width - 50,
        )
    else:
        table_width = max(1, table_width - 40)
    min_width = 1100 if sys.platform == "darwin" else 1400
    table_width = max(table_width, min_width)
    correct_column_order = ["#"] + existing_visible_cols
    column_widths = context.width_manager.compute_optimal_widths(
        df=visible_df, available_width=table_width, column_order=correct_column_order
    )
    if sys.platform == "darwin":
        desc = column_widths.get("descricao_ssa")
        if desc is not None and desc > 520:
            column_widths["descricao_ssa"] = 520
    return column_widths


def sample_width_dataframe(df: pd.DataFrame, max_rows: int = 1000) -> pd.DataFrame:
    if len(df.index) <= max_rows:
        return df
    head_rows = max_rows // 2
    tail_rows = max_rows - head_rows
    return pd.concat([df.head(head_rows), df.tail(tail_rows)], ignore_index=True)


def compute_gui_column_widths(window, df: pd.DataFrame):
    try:
        visible_columns = getattr(window, "visible_columns", [])
        width_manager = getattr(window, "width_manager", None)
        if width_manager is None:
            logger.debug("WidthManager nao inicializado; pulando calculo de larguras.")
            return

        try:
            widget_width = int(window.table_widget.width())
        except Exception as exc:
            logger.debug(
                "Falha ao ler largura do table_widget em _compute_gui_column_widths: %s",
                exc,
            )
            widget_width = 0
        try:
            window_width = int(window.width())
        except Exception as exc:
            logger.debug(
                "Falha ao ler largura da janela em _compute_gui_column_widths: %s", exc
            )
            window_width = widget_width

        column_widths = compute_widths_for_df(
            df,
            visible_columns,
            width_manager,
            widget_width=widget_width,
            window_width=window_width,
        )
        if not column_widths:
            logger.error("Nenhuma coluna visivel encontrada no DataFrame")
            return
        window._gui_column_pixel_widths = column_widths

    except Exception as exc:
        logger.error("Falha em _compute_gui_column_widths: %s", exc)
        visible_cols = ["#"] + (visible_columns if visible_columns else [])
        window._gui_column_pixel_widths = {
            col: resolve_column_width(
                window,
                col,
                include_runtime=False,
                include_preferences=True,
            )
            for col in visible_cols
        }


def resolve_column_name_for_width_persist(window, logical_index: int) -> str | None:
    resolver = getattr(window, "_resolve_header_column_name", None)
    if callable(resolver):
        col_name = resolver(logical_index)
        if col_name:
            return col_name
    cols = list(getattr(window, "_current_display_columns", []) or [])
    if not cols or logical_index < 0 or logical_index >= len(cols):
        return None
    return cols[logical_index]


def persist_column_width_change(window, col_name: str, new_size: int) -> None:
    min_px = 24 if col_name == "#" else 30
    new_px = max(min_px, min(int(new_size), 1200))
    saved_widths = getattr(window, "_saved_gui_column_widths", None)
    if not isinstance(saved_widths, dict):
        saved_widths = {}
        window._saved_gui_column_widths = saved_widths
    window._saved_gui_column_widths[col_name] = new_px
    if hasattr(window, "_gui_column_pixel_widths"):
        window._gui_column_pixel_widths[col_name] = new_px


def flush_column_width_preferences(window) -> None:
    try:
        saved_widths = getattr(window, "_saved_gui_column_widths", None)
        if not isinstance(saved_widths, dict):
            return
        prefs_widths = GUI_MAIN_PREFERENCES.setdefault("column_widths", {})
        changed = False
        for col_name, width in saved_widths.items():
            if not isinstance(col_name, str) or not col_name:
                continue
            if not isinstance(width, (int, float)):
                logger.debug(
                    "Ignorando largura de coluna invalida: column=%s width=%r",
                    col_name,
                    width,
                )
                continue
            width_px = max(30, min(int(width), 1200))
            if prefs_widths.get(col_name) != width_px:
                prefs_widths[col_name] = width_px
                changed = True
        if changed:
            persist = getattr(window, "_persist_gui_preferences", None)
            if callable(persist):
                persist()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao persistir preferencias de largura de colunas: %s", exc)


def schedule_column_width_preferences_persist(window) -> None:
    try:
        timer = getattr(window, "_column_width_persist_timer", None)
        if timer is None:
            timer = QTimer(_timer_parent(window))
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: flush_column_width_preferences(window))
            setattr(window, "_column_width_persist_timer", timer)
        timer.start(250)
    except Exception as exc:
        logger.debug("Falha ao agendar persistencia de largura de colunas: %s", exc)


def _timer_parent(window):
    return window if QObject is not None and isinstance(window, QObject) else None
