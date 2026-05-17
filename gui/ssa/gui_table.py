# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles table rendering, pagination, and column width logic.
# Relation: does not modify filter state.

from __future__ import annotations

import sys
from contextlib import contextmanager
from importlib import import_module
from typing import Any

import pandas as pd

from gui.gui_config import (
    COLUMN_HEADER_LABEL_VARIANTS,
    DEFAULT_COLUMN_DISPLAY_NAMES,
    DEFAULT_COLUMN_WIDTHS,
    DEFAULT_GUI_SETTINGS,
    GUI_MAIN_PREFERENCES,
)
from gui.qt_stubs import QHeaderView, Qt, QTableWidgetItem, QTimer
from gui.ssa import gui_details as ssa_gui_details
from utils.formatting import (
    format_dataframe_for_table_display as format_dataframe_for_display,
)
from utils.robust_logging import get_robust_logger

QBrush: Any = None
QColor: Any = None
QObject: Any = None
try:
    qt_gui = import_module("PyQt6.QtGui")
    QBrush = getattr(qt_gui, "QBrush", None)
    QColor = getattr(qt_gui, "QColor", None)
except Exception:
    QBrush = None
    QColor = None
try:
    qt_core = import_module("PyQt6.QtCore")
    QObject = getattr(qt_core, "QObject", None)
except Exception:
    QObject = None

logger = get_robust_logger().get_logger(__name__, "gui")

_FILTER_HEADER_PREFIX = "[f] "
_HEADER_SIDE_PADDING_TEXT = "  "
_ADAPTIVE_HEADER_REFRESH_DELAY_MS = 150
_DEFAULT_TABLE_CELL_ALIGNMENT = str(DEFAULT_GUI_SETTINGS["table_cell_alignment"])
_TABLE_CELL_HORIZONTAL_ALIGNMENT_MAP = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
}
_HASH_LINK_TOOLTIP = "Abrir SSA no SAM"
if QBrush is not None and QColor is not None:
    try:
        _HASH_LINK_FOREGROUND = QBrush(QColor("#4a90e2"))
    except Exception:
        _HASH_LINK_FOREGROUND = None
else:
    _HASH_LINK_FOREGROUND = None


def _set_current_display_columns(window, columns: list[str]) -> None:
    window._current_display_columns = list(columns)


def _current_display_columns(window) -> list[str]:
    return list(getattr(window, "_current_display_columns", []) or [])


def _get_visual_filter_columns(window, *, context: str) -> set[str]:
    visual_filter_columns: set[str] = set()
    get_visual_filter_columns = getattr(window, "_get_visual_filter_columns", None)
    if not callable(get_visual_filter_columns):
        return visual_filter_columns
    try:
        visual_filter_columns = set(get_visual_filter_columns())
    except Exception as exc:
        logger.debug(
            "Falha ao coletar colunas visuais filtradas em %s: %s",
            context,
            exc,
        )
    return visual_filter_columns


def _build_display_headers(
    window, columns: list[str], visual_filter_columns: set[str]
) -> list[str]:
    headers: list[str] = []
    for col in columns:
        base = "#" if col == "#" else window.internal_to_display.get(col, col)
        has_filter = col != "#" and col in visual_filter_columns
        headers.append(f"{_FILTER_HEADER_PREFIX}{base}" if has_filter else base)
    return headers


def _measure_header_text_px(window, text: str) -> int:
    """Return measured width in px; fallback is a rough px estimate."""
    header = None
    try:
        header = window.table_widget.horizontalHeader()
    except Exception as exc:
        logger.debug("Falha ao obter header para medir texto: %s", exc)
    if header is not None and hasattr(header, "fontMetrics"):
        try:
            font_metrics = header.fontMetrics()
            if font_metrics is not None and hasattr(font_metrics, "horizontalAdvance"):
                return max(0, int(font_metrics.horizontalAdvance(text)))
        except Exception as exc:
            logger.debug("Falha ao medir texto do header com fontMetrics: %s", exc)
    return max(0, len(text)) * 8


def _select_adaptive_header_label(
    window,
    column_name: str,
    available_px: int,
    has_filter: bool,
    *,
    prefix_px: int | None = None,
    padding_px: int | None = None,
    label_width_cache: dict[str, int] | None = None,
) -> str:
    """Return the best header label variant, keeping the shortest canonical fallback."""
    if column_name == "#":
        return "#"

    base_label = str(window.internal_to_display.get(column_name, column_name))
    default_label = DEFAULT_COLUMN_DISPLAY_NAMES.get(column_name)
    if default_label is not None and base_label != default_label:
        return base_label

    variants = COLUMN_HEADER_LABEL_VARIANTS.get(column_name, {})
    short_label = str(variants.get("short", base_label))
    medium_label = str(variants.get("medium", short_label))
    long_label = str(variants.get("long", medium_label))

    if label_width_cache is None:
        label_width_cache = {}
    effective_prefix_px = prefix_px if has_filter and prefix_px is not None else 0
    if has_filter and prefix_px is None:
        effective_prefix_px = _measure_header_text_px(window, _FILTER_HEADER_PREFIX)
    effective_padding_px = (
        padding_px
        if padding_px is not None
        else _measure_header_text_px(window, _HEADER_SIDE_PADDING_TEXT)
    )
    usable_px = max(0, int(available_px) - effective_prefix_px - effective_padding_px)

    for label in (long_label, medium_label, short_label):
        if label not in label_width_cache:
            label_width_cache[label] = _measure_header_text_px(window, label)
        if label_width_cache[label] <= usable_px:
            return label
    # Keep the shortest approved label instead of inventing a runtime ellipsis.
    return short_label


def _apply_adaptive_header_labels(window) -> None:
    columns = _current_display_columns(window)
    if not columns:
        return

    try:
        header = window.table_widget.horizontalHeader()
    except Exception as exc:
        logger.debug(
            "Falha ao obter header para recalcular labels adaptativos: %s", exc
        )
        return
    if header is None:
        return

    label_width_cache = _adaptive_header_label_width_cache(window, header)
    visual_filter_columns = _get_visual_filter_columns(
        window, context="labels adaptativos"
    )
    previous_signatures = _adaptive_header_label_signatures(window)
    next_signatures = {}
    prefix_px = label_width_cache[_FILTER_HEADER_PREFIX]
    padding_px = label_width_cache[_HEADER_SIDE_PADDING_TEXT]
    table = getattr(window, "table_widget", None)
    try:
        column_count = int(table.columnCount()) if table is not None else 0
    except Exception as exc:
        logger.debug("Falha ao consultar quantidade de colunas da tabela: %s", exc)
        column_count = 0

    for logical_index, column_name in enumerate(columns):
        if logical_index >= column_count:
            logger.debug(
                "Pulando label adaptativo fora do range da tabela: index=%s column=%s count=%s",
                logical_index,
                column_name,
                column_count,
            )
            continue
        try:
            available_px = int(window.table_widget.columnWidth(logical_index))
            has_filter = column_name != "#" and column_name in visual_filter_columns
            runtime_label = (
                "#"
                if column_name == "#"
                else str(window.internal_to_display.get(column_name, column_name))
            )
            signature = (available_px, has_filter, runtime_label)
            next_signatures[column_name] = signature
            header_item = window.table_widget.horizontalHeaderItem(logical_index)
            if previous_signatures.get(column_name) == signature and header_item is not None:
                continue
            base_label = _select_adaptive_header_label(
                window,
                column_name,
                available_px,
                has_filter,
                prefix_px=prefix_px,
                padding_px=padding_px,
                label_width_cache=label_width_cache,
            )
            final_label = (
                f"{_FILTER_HEADER_PREFIX}{base_label}" if has_filter else base_label
            )
            if header_item is None:
                header_item = QTableWidgetItem(final_label)
                try:
                    header_item.setToolTip(runtime_label)
                except Exception as exc:
                    logger.debug(
                        "Falha ao aplicar tooltip no header criado para %s: %s",
                        column_name,
                        exc,
                    )
                window.table_widget.setHorizontalHeaderItem(logical_index, header_item)
            if str(header_item.text() or "") != final_label:
                header_item.setText(final_label)
        except Exception as exc:
            logger.debug(
                "Falha ao reaplicar label adaptativo da coluna %s (%s): %s",
                logical_index,
                column_name,
                exc,
            )
    window._adaptive_header_label_width_cache = label_width_cache
    window._adaptive_header_label_signatures = next_signatures


def _header_font_signature(header):
    if not hasattr(header, "font"):
        return None
    try:
        font = header.font()
        return (
            str(font.family()),
            int(font.pointSizeF() * 100),
            int(font.weight()),
            bool(font.italic()),
        )
    except Exception as exc:
        logger.debug("Falha ao ler assinatura da fonte do header: %s", exc)
        return None


def _adaptive_header_label_width_cache(window, header) -> dict[str, int]:
    font_signature = _header_font_signature(header)
    measure_signature = (font_signature, id(_measure_header_text_px))
    if (
        getattr(window, "_adaptive_header_label_width_cache_signature", None)
        != measure_signature
    ):
        window._adaptive_header_label_width_cache = {}
        window._adaptive_header_label_width_cache_signature = measure_signature
        window._adaptive_header_label_width_cache_font = font_signature

    label_width_cache = getattr(window, "_adaptive_header_label_width_cache", {})
    if not isinstance(label_width_cache, dict):
        label_width_cache = {}
    if _FILTER_HEADER_PREFIX not in label_width_cache:
        label_width_cache[_FILTER_HEADER_PREFIX] = _measure_header_text_px(
            window, _FILTER_HEADER_PREFIX
        )
    if _HEADER_SIDE_PADDING_TEXT not in label_width_cache:
        label_width_cache[_HEADER_SIDE_PADDING_TEXT] = _measure_header_text_px(
            window, _HEADER_SIDE_PADDING_TEXT
        )
    return label_width_cache


def _adaptive_header_label_signatures(window) -> dict:
    previous_signatures = getattr(window, "_adaptive_header_label_signatures", {})
    if isinstance(previous_signatures, dict):
        return previous_signatures
    return {}


def _schedule_adaptive_header_label_refresh(window) -> None:
    """Debounce leve para evitar oscilacao visual durante drag do header."""
    timer = getattr(window, "_adaptive_header_label_timer", None)
    try:
        if timer is None:
            timer = QTimer(_timer_parent(window))
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: _apply_adaptive_header_labels(window))
            window._adaptive_header_label_timer = timer
        timer.start(_ADAPTIVE_HEADER_REFRESH_DELAY_MS)
    except Exception as exc:
        logger.debug("Falha ao agendar refresh de labels adaptativos: %s", exc)


def _timer_parent(window):
    if QObject is not None and isinstance(window, QObject):
        return window
    return None


def _get_header_visual_column_order(window) -> list[str]:
    header = window.table_widget.horizontalHeader()
    columns = _current_display_columns(window)
    if header is None or not columns:
        return columns
    ordered_pairs: list[tuple[int, str]] = []
    for logical_index, column_name in enumerate(columns):
        try:
            visual_index = int(header.visualIndex(logical_index))
        except Exception as exc:
            logger.debug(
                "Falha ao consultar visualIndex da coluna %s (%s): %s",
                logical_index,
                column_name,
                exc,
            )
            visual_index = logical_index
        ordered_pairs.append((visual_index, column_name))
    ordered_pairs.sort(key=lambda item: item[0])
    return [column_name for _, column_name in ordered_pairs]


def _fallback_column_width(col_name: str) -> int:
    if col_name in DEFAULT_COLUMN_WIDTHS:
        return int(DEFAULT_COLUMN_WIDTHS[col_name])
    if col_name == "#":
        return 24
    return 120


def _build_render_marker_sample(
    display_df: pd.DataFrame,
) -> tuple[tuple[str, ...], ...]:
    if display_df.empty:
        return tuple()

    try:
        marker_columns = list(display_df.columns)
        if len(display_df) <= 100:
            row_indexes = list(range(len(display_df)))
        else:
            row_indexes = sorted({0, len(display_df) // 2, len(display_df) - 1})
        marker_df = display_df.iloc[row_indexes][marker_columns].fillna("")
        return tuple(
            tuple(str(value) for value in row_values)
            for row_values in marker_df.itertuples(index=False, name=None)
        )
    except Exception as exc:
        logger.debug(
            "Falha ao construir amostra de marcadores da renderizacao: %s", exc
        )
        return tuple()


def _build_page_render_signature(
    window,
    display_df: pd.DataFrame,
    display_headers: list[str],
    *,
    marker_sample: tuple[tuple[str, ...], ...] | None = None,
) -> tuple:
    try:
        viewport_width = int(window.table_widget.viewport().width())
    except Exception:
        viewport_width = -1

    if marker_sample is None:
        marker_sample = _build_render_marker_sample(display_df)

    return (
        getattr(window, "_data_uuid", None),
        int(getattr(window, "_data_revision", 0) or 0),
        int(getattr(window.paginator, "current_page", 1)),
        int(getattr(window.paginator, "page_size", 0)),
        viewport_width,
        tuple(display_df.columns),
        tuple(display_headers),
        int(len(display_df)),
        marker_sample,
    )


@contextmanager
def _freeze_table_batch_state(window, header):
    updates_enabled = None
    sorting_enabled = None
    table_signals_were_blocked = None
    header_updates_enabled = None
    header_signals_were_blocked = None

    if hasattr(window.table_widget, "updatesEnabled"):
        try:
            updates_enabled = bool(window.table_widget.updatesEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar updatesEnabled da tabela: %s", exc)
    if hasattr(window.table_widget, "isSortingEnabled"):
        try:
            sorting_enabled = bool(window.table_widget.isSortingEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar sorting da tabela: %s", exc)
    if hasattr(window.table_widget, "signalsBlocked"):
        try:
            table_signals_were_blocked = bool(window.table_widget.signalsBlocked())
        except Exception as exc:
            logger.debug("Falha ao consultar estado de sinais da tabela: %s", exc)
    if header is not None and hasattr(header, "updatesEnabled"):
        try:
            header_updates_enabled = bool(header.updatesEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar updatesEnabled do header: %s", exc)
    if header is not None and hasattr(header, "signalsBlocked"):
        try:
            header_signals_were_blocked = bool(header.signalsBlocked())
        except Exception as exc:
            logger.debug("Falha ao consultar estado de sinais do header: %s", exc)

    try:
        if hasattr(window.table_widget, "setUpdatesEnabled"):
            window.table_widget.setUpdatesEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar updates da tabela: %s", exc)
    try:
        if sorting_enabled and hasattr(window.table_widget, "setSortingEnabled"):
            window.table_widget.setSortingEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar sorting da tabela: %s", exc)
    try:
        if table_signals_were_blocked is not None:
            window.table_widget.blockSignals(True)
    except Exception as exc:
        logger.debug("Falha ao bloquear sinais da tabela: %s", exc)
    try:
        if header is not None and hasattr(header, "setUpdatesEnabled"):
            header.setUpdatesEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar updates do header: %s", exc)
    try:
        if header is not None and header_signals_were_blocked is not None:
            header.blockSignals(True)
    except Exception as exc:
        logger.debug("Falha ao bloquear sinais do header: %s", exc)

    try:
        yield
    finally:
        try:
            if updates_enabled is not None and hasattr(
                window.table_widget, "setUpdatesEnabled"
            ):
                window.table_widget.setUpdatesEnabled(updates_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar updatesEnabled da tabela: %s", exc)
        try:
            if sorting_enabled is not None and hasattr(
                window.table_widget, "setSortingEnabled"
            ):
                window.table_widget.setSortingEnabled(sorting_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar sorting da tabela: %s", exc)
        try:
            if table_signals_were_blocked is not None:
                window.table_widget.blockSignals(table_signals_were_blocked)
        except Exception as exc:
            logger.debug("Falha ao restaurar sinais da tabela: %s", exc)
        try:
            if (
                header is not None
                and header_updates_enabled is not None
                and hasattr(header, "setUpdatesEnabled")
            ):
                header.setUpdatesEnabled(header_updates_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar updatesEnabled do header: %s", exc)
        try:
            if header is not None and header_signals_were_blocked is not None:
                header.blockSignals(header_signals_were_blocked)
        except Exception as exc:
            logger.debug("Falha ao restaurar sinais do header: %s", exc)


def _refresh_initial_details(window, *, update_details):
    if not update_details:
        return
    first_row_series = (
        window._get_series_from_row(0) if window.table_widget.rowCount() > 0 else None
    )
    try:
        next_signature = ssa_gui_details._get_details_render_signature(
            window, first_row_series
        )
        current_signature = window.details_text.property("details_render_signature")
        if (
            first_row_series is not None
            and current_signature == next_signature
            and not window.details_text.document().isEmpty()
        ):
            return
    except Exception as exc:
        logger.debug(
            "Falha ao comparar assinatura inicial de detalhes durante render: %s", exc
        )
    ssa_gui_details._update_details_from_series(window, first_row_series)


def _resolve_visible_columns_for_page(window):
    visible_selection = list(getattr(window, "visible_columns", []) or [])
    cols_to_show = [
        col for col in visible_selection if col in window.df_para_tabela.columns
    ]
    if cols_to_show:
        return cols_to_show

    default_cols = [
        col for col in window.default_columns if col in window.df_para_tabela.columns
    ]
    if default_cols:
        return default_cols
    return window.df_para_tabela.columns.tolist()


def _build_display_dataframe_for_page(window, cols_to_show):
    display_df = window.df_para_tabela[cols_to_show].copy()
    raw_marker_sample = _build_render_marker_sample(display_df)
    _set_current_display_columns(window, ["#"] + list(display_df.columns))

    if "#" not in display_df.columns:
        display_df.insert(
            0,
            "#",
            range(
                (window.paginator.current_page - 1) * window.paginator.page_size + 1,
                (window.paginator.current_page - 1) * window.paginator.page_size
                + 1
                + len(display_df),
            ),
        )
    return display_df, raw_marker_sample


def _format_display_dataframe_for_table(window, display_df, raw_marker_sample):
    display_df_hash = None
    try:
        data_uuid = getattr(window, "_data_uuid", None)
        data_revision = int(getattr(window, "_data_revision", 0) or 0)
        if data_uuid is not None:
            page = int(window.paginator.current_page)
            page_size = int(window.paginator.page_size)
            width_signature = ()
            try:
                width_manager = getattr(window, "width_manager", None)
                min_char_sizes = getattr(width_manager, "min_char_sizes", None)
                if isinstance(min_char_sizes, dict):
                    width_signature = tuple(
                        (col, min_char_sizes.get(col, "__default__"))
                        for col in display_df.columns
                    )
            except Exception as exc:
                logger.debug(
                    "Falha ao compor assinatura de largura para chave de cache: %s", exc
                )
            display_df_hash = (
                data_uuid,
                data_revision,
                page,
                page_size,
                len(display_df),
                tuple(display_df.columns),
                raw_marker_sample,
                width_signature,
            )
    except Exception as exc:
        logger.debug("Falha ao gerar chave de cache do DataFrame de exibicao: %s", exc)

    cached_formatted = None
    if display_df_hash is not None:
        cached_formatted = window.cache_manager.get_cached_formatted_df(display_df_hash)
    if cached_formatted is not None:
        return cached_formatted

    try:
        formatted_df = format_dataframe_for_display(display_df)
        if display_df_hash is not None:
            window.cache_manager.cache_formatted_df(display_df_hash, formatted_df)
        return formatted_df
    except Exception as exc:
        logger.debug("Falha ao formatar DataFrame para exibicao na tabela: %s", exc)
        return display_df


def _resolve_table_cell_alignment(alignment_name):
    table_cell_alignment_name = str(alignment_name or "").strip().lower()
    horizontal_alignment = _TABLE_CELL_HORIZONTAL_ALIGNMENT_MAP.get(
        table_cell_alignment_name,
        _TABLE_CELL_HORIZONTAL_ALIGNMENT_MAP[_DEFAULT_TABLE_CELL_ALIGNMENT],
    )
    return Qt.AlignmentFlag.AlignVCenter | horizontal_alignment


def _table_cell_alignment_from_preferences():
    gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
    return _resolve_table_cell_alignment(
        gui_settings.get("table_cell_alignment", _DEFAULT_TABLE_CELL_ALIGNMENT)
    )


def _set_hash_column_item_metadata(window, item, row_idx):
    item.setData(
        Qt.ItemDataRole.UserRole,
        row_idx + (window.paginator.current_page - 1) * window.paginator.page_size,
    )
    try:
        font = item.font()
        font.setUnderline(True)
        item.setFont(font)
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo de link na coluna #: %s", exc)
    try:
        if _HASH_LINK_FOREGROUND is not None:
            item.setForeground(_HASH_LINK_FOREGROUND)
    except Exception as exc:
        logger.debug("Falha ao aplicar cor de link na coluna #: %s", exc)
    try:
        if hasattr(item, "setToolTip"):
            item.setToolTip(_HASH_LINK_TOOLTIP)
    except Exception as exc:
        logger.debug("Falha ao aplicar tooltip na coluna #: %s", exc)


def _populate_table_items(window, display_df, table_cell_alignment):
    columns_list = list(display_df.columns)
    cell_render_failures = 0
    for row_idx, row_values in enumerate(display_df.itertuples(index=False, name=None)):
        for col_idx, (col_name, value) in enumerate(
            zip(columns_list, row_values, strict=False)
        ):
            try:
                item_text = str(value)
                item = window.table_widget.item(row_idx, col_idx)
                if item is None:
                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(table_cell_alignment)
                    window.table_widget.setItem(row_idx, col_idx, item)
                elif str(item.text() or "") != item_text:
                    item.setText(item_text)
                    item.setTextAlignment(table_cell_alignment)
                if col_name == "#":
                    _set_hash_column_item_metadata(window, item, row_idx)
            except Exception as exc:
                cell_render_failures += 1
                logger.debug(
                    "Falha ao renderizar celula da tabela (row=%s col=%s key=%s): %s",
                    row_idx,
                    col_idx,
                    col_name,
                    exc,
                )
                try:
                    window.table_widget.setItem(
                        row_idx, col_idx, QTableWidgetItem("")
                    )
                except Exception as fallback_exc:
                    logger.debug(
                        "Falha ao aplicar fallback vazio na celula (row=%s col=%s): %s",
                        row_idx,
                        col_idx,
                        fallback_exc,
                    )
    if cell_render_failures:
        logger.warning(
            "Renderizacao da tabela concluiu com %s falhas de celula.",
            cell_render_failures,
        )


def _resolve_empty_table_columns(window):
    base_frame = getattr(window, "df_exibido", pd.DataFrame())
    base_columns = getattr(base_frame, "columns", [])
    base_cols = list(base_columns)
    visible_columns = list(getattr(window, "visible_columns", []) or [])
    default_columns = list(getattr(window, "default_columns", []) or [])

    valid_cols = [column for column in visible_columns if column in base_cols]
    if valid_cols:
        return valid_cols
    if base_cols:
        return [column for column in default_columns if column in base_cols]
    return visible_columns


def _render_empty_page_table(window, header, *, update_details):
    try:
        if hasattr(window.table_widget, "clearSelection"):
            window.table_widget.clearSelection()
    except Exception as exc:
        logger.debug("Falha ao limpar selecao em tabela vazia: %s", exc)
    window.table_widget.setRowCount(0)

    valid_cols = _resolve_empty_table_columns(window)
    current_columns = ["#"] + list(valid_cols)
    _set_current_display_columns(window, current_columns)
    window.table_widget.setColumnCount(len(current_columns))
    visual_filter_columns = _get_visual_filter_columns(window, context="tabela vazia")
    headers = _build_display_headers(window, current_columns, visual_filter_columns)
    try:
        window.table_widget.setHorizontalHeaderLabels(headers)
    except Exception as exc:
        logger.debug("Falha ao aplicar cabecalhos da tabela vazia: %s", exc)

    for column_index, col_name in enumerate(current_columns):
        px = window._saved_gui_column_widths.get(col_name)
        if px is None:
            px = _fallback_column_width(col_name)
        try:
            window.table_widget.setColumnWidth(column_index, max(30, int(px)))
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar largura da coluna %s em tabela vazia: %s",
                col_name,
                exc,
            )

    try:
        if (
            window.table_widget.columnCount() > 1
            and window.table_widget.columnWidth(1) == 0
        ):
            window.table_widget.setColumnWidth(1, 80)
    except Exception as exc:
        logger.debug(
            "Falha ao reforcar largura da primeira coluna de dados em tabela vazia: %s",
            exc,
        )

    _restore_interactive_header_mode(header)
    _apply_adaptive_header_labels(window)
    if update_details:
        ssa_gui_details._update_details_from_series(window, None)


def _needs_width_recompute(window, cols_sig, viewport_width):
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


def _apply_rendered_table_widths(window, display_df):
    cols_sig = tuple(display_df.columns)
    try:
        viewport_width = window.table_widget.viewport().width()
    except Exception:
        viewport_width = -1
    skip_width_recompute = bool(getattr(window, "_skip_width_recompute_once", False))
    if skip_width_recompute:
        window._skip_width_recompute_once = False
    if not skip_width_recompute and _needs_width_recompute(
        window, cols_sig, viewport_width
    ):
        window._compute_gui_column_widths(display_df)
        window._widths_columns_sig = cols_sig
        window._last_viewport_w = viewport_width

    for column_index, col_name in enumerate(display_df.columns):
        px = window._saved_gui_column_widths.get(col_name)
        if px is None:
            px = getattr(window, "_gui_column_pixel_widths", {}).get(col_name)
        if px is None:
            px = GUI_MAIN_PREFERENCES.get("column_widths", {}).get(col_name)
        if px is None:
            px = _fallback_column_width(col_name)

        max_px = 1000
        width_manager = getattr(window, "width_manager", None)
        max_map = getattr(width_manager, "max_pixel_widths", None)
        if isinstance(max_map, dict):
            try:
                max_px = int(max_map.get(col_name, max_px))
            except Exception:
                max_px = 1000
        min_px = 24 if str(col_name) == "#" else 30
        window.table_widget.setColumnWidth(
            column_index, max(min_px, min(int(px), max_px))
        )


def _sync_pagination_state(window, page_number):
    try:
        requested_page = int(page_number)
    except Exception:
        requested_page = int(getattr(window.paginator, "current_page", 1))
    if requested_page < 1:
        requested_page = 1
    try:
        window.paginator.current_page = requested_page
        window.paginator.update_pagination_info()
        window.paginator.update_buttons()
    except Exception as exc:
        logger.debug("Falha ao sincronizar pagina atual do paginator: %s", exc)


def _load_current_page_slice(window):
    window.df_para_tabela = window.paginator.get_current_slice()
    try:
        if hasattr(window, "_ensure_data_revision"):
            window._ensure_data_revision()
    except Exception as exc:
        logger.debug(
            "Falha ao validar revisao de dados antes de renderizar pagina: %s", exc
        )


def _freeze_table_header_resize(window):
    try:
        header = window.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        return header
    except Exception as exc:
        logger.debug("Falha ao congelar modo de resize do header: %s", exc)
        return None


def _build_page_display_payload(window):
    cols_to_show = _resolve_visible_columns_for_page(window)
    display_df, raw_marker_sample = _build_display_dataframe_for_page(
        window, cols_to_show
    )
    display_df = _format_display_dataframe_for_table(
        window, display_df, raw_marker_sample
    )
    visual_filter_columns = _get_visual_filter_columns(
        window, context="pagina renderizada"
    )
    display_headers = _build_display_headers(
        window, list(display_df.columns), visual_filter_columns
    )
    return display_df, display_headers, raw_marker_sample


def _render_signature_and_reuse(window, display_df, display_headers, raw_marker_sample):
    render_signature = _build_page_render_signature(
        window,
        display_df,
        display_headers,
        marker_sample=raw_marker_sample,
    )
    previous_signature = getattr(window, "_last_table_render_signature", None)
    reuse_render = (
        previous_signature == render_signature
        and window.table_widget.rowCount() == len(display_df)
        and window.table_widget.columnCount() == len(display_df.columns)
    )
    return render_signature, reuse_render


def _rebuild_table_widget(window, header, display_df, display_headers):
    with _freeze_table_batch_state(window, header):
        try:
            if hasattr(window.table_widget, "clearSelection"):
                window.table_widget.clearSelection()
        except Exception as exc:
            logger.debug(
                "Falha ao limpar selecao antes de reconstruir a tabela: %s", exc
            )
        window.table_widget.setRowCount(len(display_df))
        window.table_widget.setColumnCount(len(display_df.columns))
        window.table_widget.setHorizontalHeaderLabels(display_headers)
        _populate_table_items(
            window, display_df, _table_cell_alignment_from_preferences()
        )


def _restore_interactive_header_mode(header):
    try:
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setMinimumSectionSize(26)
            header.setDefaultSectionSize(92)
    except Exception as exc:
        logger.debug("Falha ao restaurar configuracao interativa do header: %s", exc)


def _synchronize_header_visual_order(window, header):
    try:
        if header is None:
            return
        desired_visual_order = _current_display_columns(window)
        current_visual_order = _get_header_visual_column_order(window)
        if desired_visual_order and current_visual_order != desired_visual_order:
            logical_index_by_column = {
                column_name: logical_index
                for logical_index, column_name in enumerate(desired_visual_order)
            }
            window._header_order_sync_suspended = True
            try:
                for desired_visual_index, _column_name in enumerate(
                    desired_visual_order
                ):
                    logical_index = logical_index_by_column[_column_name]
                    current_visual_index = int(header.visualIndex(logical_index))
                    if current_visual_index != desired_visual_index:
                        header.moveSection(current_visual_index, desired_visual_index)
            finally:
                window._header_order_sync_suspended = False
        final_visual_order = _get_header_visual_column_order(window)
        if desired_visual_order and final_visual_order != desired_visual_order:
            logger.warning(
                "Header visual order remained out of sync after render sync: desired=%s actual=%s",
                desired_visual_order,
                final_visual_order,
            )
    except Exception as exc:
        logger.debug(
            "Falha ao sincronizar ordem visual do header com colunas exibidas: %s", exc
        )


def _finalize_page_render(window, display_df, render_signature, *, update_details):
    header = window.table_widget.horizontalHeader()
    _synchronize_header_visual_order(window, header)
    _apply_rendered_table_widths(window, display_df)

    try:
        window._force_column_widths()
    except Exception as exc:
        logger.debug("Falha ao reforcar larguras salvas da tabela: %s", exc)

    try:
        window._ensure_nonzero_column_widths()
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)

    _restore_interactive_header_mode(header)
    _synchronize_header_visual_order(window, header)
    _apply_adaptive_header_labels(window)
    _refresh_initial_details(window, update_details=update_details)
    window._last_table_render_signature = render_signature

    try:
        QTimer.singleShot(0, window._ensure_nonzero_column_widths)
    except Exception as exc:
        logger.debug("Falha ao agendar reforco de largura de colunas: %s", exc)


def display_current_page(window, page_number, *, update_details=True):
    """Exibe a pagina especificada do DataFrame filtrado."""
    _sync_pagination_state(window, page_number)
    _load_current_page_slice(window)
    header = _freeze_table_header_resize(window)

    if window.df_para_tabela.empty:
        _render_empty_page_table(window, header, update_details=update_details)
        return

    display_df, display_headers, raw_marker_sample = _build_page_display_payload(window)
    render_signature, reuse_render = _render_signature_and_reuse(
        window, display_df, display_headers, raw_marker_sample
    )

    if not reuse_render:
        _rebuild_table_widget(window, header, display_df, display_headers)

    _finalize_page_render(
        window, display_df, render_signature, update_details=update_details
    )


# --- Wrappers de compatibilidade com testes antigos (PoC) ---
def display_data(window, df):  # usado em testes legados
    try:
        if df is None or getattr(df, "empty", True):
            return
        window.df_completo = df.copy()
        window.df_exibido = df.copy()
        window.paginator.set_dataframe(window.df_exibido)
        window.display_current_page(getattr(window.paginator, "current_page", 1))
    except Exception as exc:
        logger.warning(
            "Falha ao exibir DataFrame via display_data de compatibilidade: %s", exc
        )


def _force_column_widths(window):
    """Forca reaplicacao das larguras das colunas para garantir que sejam respeitadas."""
    if not hasattr(window, "visible_columns") or not window.visible_columns:
        return

    for i, col_name in enumerate(["#"] + window.visible_columns):
        # Busca largura salva das configuracoes
        px = window._saved_gui_column_widths.get(col_name)
        if px is not None:
            current_width = window.table_widget.columnWidth(i)
            if current_width != px:
                window.table_widget.setColumnWidth(i, int(px))


def _ensure_nonzero_column_widths(window):
    """Garante que nenhuma coluna permanece com largura 0.
    Estrategia simples por indice: se alguma coluna estiver com 0px, define 80px.
    """
    try:
        col_count = window.table_widget.columnCount()
        if col_count <= 0:
            return
        for i in range(col_count):
            if window.table_widget.columnWidth(i) == 0:
                # Primeiro tenta dimensionar pelo conteudo
                try:
                    window.table_widget.resizeColumnToContents(i)
                except Exception as exc:
                    logger.debug(
                        "Falha ao redimensionar coluna %s por conteudo: %s", i, exc
                    )
                if window.table_widget.columnWidth(i) == 0:
                    window.table_widget.setColumnWidth(i, 80)
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)


def _set_safe_width_for_col_index(window, idx: int, px: int = 80):
    """Define uma largura segura para um indice de coluna, se possivel."""
    try:
        if idx < 0:
            return
        if window.table_widget.columnCount() <= idx:
            return
        if window.table_widget.columnWidth(idx) == 0:
            window.table_widget.setColumnWidth(idx, max(30, int(px)))
    except Exception as exc:
        logger.debug("Falha ao aplicar largura segura para coluna %s: %s", idx, exc)


def _compute_widths_for_df(
    df: pd.DataFrame,
    visible_columns,
    width_manager,
    internal_to_display,
    saved_widths,
    widget_width: int,
    window_width: int,
):
    if not visible_columns:
        return None
    if hasattr(df, "columns"):
        existing_visible_cols = [col for col in visible_columns if col in df.columns]
        if not existing_visible_cols:
            return None
        visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
        visible_df = _sample_width_dataframe(visible_df)
    else:
        existing_visible_cols = list(visible_columns)
        visible_df = df
    table_width = widget_width
    if table_width < 500:
        table_width = max(1000 if sys.platform == "darwin" else 1400, window_width - 50)
    else:
        table_width = max(1, table_width - 40)
    min_width = 1100 if sys.platform == "darwin" else 1400
    table_width = max(table_width, min_width)
    correct_column_order = ["#"] + existing_visible_cols
    column_widths = width_manager.compute_optimal_widths(
        df=visible_df, available_width=table_width, column_order=correct_column_order
    )
    if sys.platform == "darwin":
        column_widths = {
            key: (value + 2 if key != "#" else value)
            for key, value in column_widths.items()
        }
    return column_widths


def _sample_width_dataframe(df: pd.DataFrame, max_rows: int = 1000) -> pd.DataFrame:
    if len(df.index) <= max_rows:
        return df
    head_rows = max_rows // 2
    tail_rows = max_rows - head_rows
    return pd.concat([df.head(head_rows), df.tail(tail_rows)])


def _compute_gui_column_widths(window, df: pd.DataFrame):
    """
    Calcula larguras de colunas usando o WidthManager unificado.
    Substitui 150+ linhas de codigo frankenstein por uma chamada limpa.
    """
    try:
        visible_columns = getattr(window, "visible_columns", None)
        if isinstance(visible_columns, (list, tuple)):
            visible_columns = list(visible_columns)
        else:
            visible_columns = []
        if not visible_columns:
            return
        width_manager = getattr(window, "width_manager", None)
        if width_manager is None:
            logger.debug("WidthManager nao inicializado; pulando calculo de larguras.")
            return

        internal_to_display = getattr(window, "internal_to_display", {})
        saved_widths = getattr(window, "_saved_gui_column_widths", {})
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

        column_widths = _compute_widths_for_df(
            df,
            visible_columns,
            width_manager,
            internal_to_display,
            saved_widths,
            widget_width,
            window_width,
        )
        if not column_widths:
            logger.error("Nenhuma coluna visivel encontrada no DataFrame")
            return
        window._gui_column_pixel_widths = column_widths

    except Exception as exc:
        logger.error("Falha em _compute_gui_column_widths: %s", exc)
        # Fallback para larguras minimas das colunas visiveis apenas
        visible_cols = ["#"] + (visible_columns if visible_columns else [])
        window._gui_column_pixel_widths = {col: 100 for col in visible_cols}


def _on_header_section_resized(
    window, logical_index: int, old_size: int, new_size: int
):
    """Salva a largura ajustada pelo usuario na configuracao persistente."""
    try:
        col_name = None
        resolver = getattr(window, "_resolve_header_column_name", None)
        if callable(resolver):
            col_name = resolver(logical_index)
        if not col_name:
            cols = getattr(window, "_current_display_columns", None)
            if not cols or logical_index < 0 or logical_index >= len(cols):
                return
            col_name = cols[logical_index]
        new_px = max(30, min(int(new_size), 1200))
        if col_name:
            window._saved_gui_column_widths[col_name] = new_px
            if hasattr(window, "_gui_column_pixel_widths"):
                window._gui_column_pixel_widths[col_name] = new_px
            _schedule_adaptive_header_label_refresh(window)
            _schedule_column_width_preferences_persist(window)
    except Exception as exc:  # noqa: BLE001
        # Evita quebrar a GUI por falhas de IO, mas preserva evidencia no log.
        logger.debug("Falha ao persistir largura de coluna redimensionada: %s", exc)


def _flush_column_width_preferences(window) -> None:
    """Persiste larguras salvas em cache local para preferencias da GUI."""
    try:
        saved_widths = getattr(window, "_saved_gui_column_widths", None)
        if not isinstance(saved_widths, dict):
            return
        from gui.gui_config import GUI_MAIN_PREFERENCES

        prefs_widths = GUI_MAIN_PREFERENCES.setdefault("column_widths", {})
        changed = False
        for col_name, width in saved_widths.items():
            if not isinstance(col_name, str) or not col_name:
                continue
            try:
                width_px = max(30, min(int(width), 1200))
            except (TypeError, ValueError):
                continue
            if prefs_widths.get(col_name) != width_px:
                prefs_widths[col_name] = width_px
                changed = True
        if changed and hasattr(window, "_persist_gui_preferences"):
            window._persist_gui_preferences()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao atualizar preferencias de largura de coluna: %s", exc)


def _schedule_column_width_preferences_persist(window) -> None:
    """Debounce de persistencia de largura para evitar IO excessivo em drag de header."""
    timer = getattr(window, "_column_width_persist_timer", None)
    try:
        if timer is None:
            timer = QTimer(_timer_parent(window))
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: _flush_column_width_preferences(window))
            setattr(window, "_column_width_persist_timer", timer)
        timer.start(250)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao agendar persistencia de largura de coluna: %s", exc)


def apply_table_cell_alignment(window, alignment_name: str) -> None:
    table_cell_alignment = _resolve_table_cell_alignment(alignment_name)
    table = getattr(window, "table_widget", None)
    if table is None:
        return
    try:
        row_count = int(table.rowCount())
        column_count = int(table.columnCount())
    except Exception as exc:
        logger.debug("Falha ao consultar tamanho da tabela para alinhamento: %s", exc)
        return
    for row_index in range(row_count):
        for column_index in range(column_count):
            item = table.item(row_index, column_index)
            if item is not None:
                item.setTextAlignment(table_cell_alignment)
