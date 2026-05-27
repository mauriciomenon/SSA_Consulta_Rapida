# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles table rendering, pagination, and column width logic.
# Relation: does not modify filter state.

from __future__ import annotations

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
from gui.ssa import table_widths
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
_ADAPTIVE_HEADER_REFRESH_DELAY_MS = 250
_DEFAULT_TABLE_CELL_ALIGNMENT = str(DEFAULT_GUI_SETTINGS["table_cell_alignment"])
_TABLE_CELL_HORIZONTAL_ALIGNMENT_MAP = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
}
_LEFT_ANCHORED_TEXT_COLUMNS = frozenset(
    {
        "descricao_ssa",
        "descricao_execucao",
        "descricao_localizacao",
        "solicitante",
        "responsavel_execucao",
        "arquivo_origem",
    }
)
_HASH_LINK_TOOLTIP = "Abrir SSA no SAM"
_HASH_LINK_STYLE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
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
    """Return the best fitting approved header label variant."""
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
    final_label_cache = getattr(window, "_adaptive_header_final_label_cache", {})
    if not isinstance(final_label_cache, dict):
        final_label_cache = {}
    visual_filter_columns = _get_visual_filter_columns(
        window, context="labels adaptativos"
    )
    previous_signatures = _adaptive_header_label_signatures(window)
    next_signatures = {}
    prefix_px = int(label_width_cache.get(_FILTER_HEADER_PREFIX, 0) or 0)
    padding_px = int(label_width_cache.get(_HEADER_SIDE_PADDING_TEXT, 0) or 0)
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
            if bool(window.table_widget.isColumnHidden(logical_index)):
                continue
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
            cache_key = (
                column_name,
                available_px,
                has_filter,
                runtime_label,
                prefix_px,
                padding_px,
            )
            final_label = final_label_cache.get(cache_key)
            if not isinstance(final_label, str):
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
                final_label_cache[cache_key] = final_label
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
    window._adaptive_header_final_label_cache = final_label_cache
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
        window._adaptive_header_final_label_cache = {}
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


def _current_pagination_values(window, fallback_page_size: int = 1) -> tuple[int, int]:
    paginator = getattr(window, "paginator", None)
    try:
        current_page = int(getattr(paginator, "current_page", 1) or 1)
    except Exception:
        current_page = 1
    try:
        page_size = int(getattr(paginator, "page_size", fallback_page_size) or 1)
    except Exception:
        page_size = fallback_page_size
    return max(1, current_page), max(1, page_size)


def _build_display_dataframe_for_page(window, cols_to_show):
    display_df = window.df_para_tabela[cols_to_show].copy()
    raw_marker_sample = _build_render_marker_sample(display_df)
    _set_current_display_columns(window, ["#"] + list(display_df.columns))
    current_page, page_size = _current_pagination_values(
        window, fallback_page_size=max(1, len(display_df))
    )

    if "#" not in display_df.columns:
        display_df.insert(
            0,
            "#",
            range(
                (current_page - 1) * page_size + 1,
                (current_page - 1) * page_size + 1 + len(display_df),
            ),
        )
    return display_df, raw_marker_sample


def _format_display_dataframe_for_table(window, display_df, raw_marker_sample):
    display_df_hash = None
    try:
        data_uuid = getattr(window, "_data_uuid", None)
        data_revision = int(getattr(window, "_data_revision", 0) or 0)
        if data_uuid is not None:
            page, page_size = _current_pagination_values(
                window, fallback_page_size=max(1, len(display_df))
            )
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


def _table_cell_alignment_for_column(col_name: str, default_alignment):
    if str(col_name or "").strip() in _LEFT_ANCHORED_TEXT_COLUMNS:
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    return default_alignment


def _set_hash_column_item_metadata(window, item, row_idx):
    current_page, page_size = _current_pagination_values(window)
    item.setData(
        Qt.ItemDataRole.UserRole,
        row_idx + (current_page - 1) * page_size,
    )
    item.setData(_HASH_LINK_STYLE_ROLE, True)
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
    previous_hash_positions = getattr(window, "_hash_link_item_positions", set())
    if not isinstance(previous_hash_positions, set):
        previous_hash_positions = set()
    current_hash_positions: set[tuple[int, int]] = set()
    for row_idx, row_values in enumerate(display_df.itertuples(index=False, name=None)):
        for col_idx, (col_name, value) in enumerate(zip(columns_list, row_values)):
            try:
                item_text = str(value)
                effective_alignment = _table_cell_alignment_for_column(
                    str(col_name or ""),
                    table_cell_alignment,
                )
                item = window.table_widget.item(row_idx, col_idx)
                if item is None:
                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(effective_alignment)
                    window.table_widget.setItem(row_idx, col_idx, item)
                else:
                    if str(item.text() or "") != item_text:
                        item.setText(item_text)
                    if item.textAlignment() != effective_alignment:
                        item.setTextAlignment(effective_alignment)
                if col_name == "#":
                    _set_hash_column_item_metadata(window, item, row_idx)
                    current_hash_positions.add((row_idx, col_idx))
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
    stale_hash_positions = previous_hash_positions - current_hash_positions
    for row_idx, col_idx in stale_hash_positions:
        try:
            item = window.table_widget.item(row_idx, col_idx)
            if item is None or item.data(_HASH_LINK_STYLE_ROLE) is not True:
                continue
            font = item.font()
            font.setUnderline(False)
            item.setFont(font)
            if QBrush is not None:
                item.setForeground(QBrush())
            if hasattr(item, "setToolTip"):
                item.setToolTip("")
            item.setData(_HASH_LINK_STYLE_ROLE, None)
        except Exception as exc:
            logger.debug(
                "Falha ao resetar estilo de link reaproveitado na celula %s,%s: %s",
                row_idx,
                col_idx,
                exc,
            )
    window._hash_link_item_positions = current_hash_positions


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
        px = table_widths.resolve_column_width(
            window,
            col_name,
            include_runtime=False,
            include_preferences=False,
        )
        try:
            min_px = 24 if str(col_name) == "#" else 30
            window.table_widget.setColumnWidth(column_index, max(min_px, int(px)))
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


def _resolved_user_column_widths(window, width_manager) -> dict:
    if width_manager is None:
        return {}
    saved_widths = getattr(window, "_saved_gui_column_widths", {})
    if not isinstance(saved_widths, dict):
        return {}
    user_widths = {}
    for col_name, width in saved_widths.items():
        try:
            width_px = int(width)
        except (TypeError, ValueError):
            continue
        default_px = DEFAULT_COLUMN_WIDTHS.get(str(col_name))
        if default_px is None or int(default_px) != width_px:
            user_widths[str(col_name)] = width_px
    return user_widths


def _target_table_column_width(
    width_manager, col_name: str, desired_px: int, min_px: int, user_widths: dict
) -> int:
    if width_manager is None:
        return max(int(min_px), int(desired_px))
    return int(width_manager.clamp_pixel_width(col_name, desired_px, min_px, user_widths))


def _minimum_table_column_width(col_name: str, header_min_px: int) -> int:
    return max(24 if str(col_name) == "#" else 30, int(header_min_px))


def _apply_rendered_table_widths(window, display_df):
    cols_sig = tuple(display_df.columns)
    try:
        if int(window.table_widget.columnCount()) != len(cols_sig):
            logger.warning(
                "Tabela com contagem de colunas inconsistente; larguras ignoradas: "
                "table=%s display=%s",
                window.table_widget.columnCount(),
                len(cols_sig),
            )
            return
    except Exception as exc:
        logger.debug("Falha ao validar contagem de colunas da tabela: %s", exc)
        return
    try:
        viewport_width = window.table_widget.viewport().width()
    except Exception:
        viewport_width = -1
    skip_width_recompute = bool(getattr(window, "_skip_width_recompute_once", False))
    if skip_width_recompute:
        window._skip_width_recompute_once = False
    if not skip_width_recompute and table_widths.needs_width_recompute(
        window, cols_sig, viewport_width
    ):
        window._compute_gui_column_widths(display_df)
        window._widths_columns_sig = cols_sig
        window._last_viewport_w = viewport_width

    try:
        header_min_px = int(window.table_widget.horizontalHeader().minimumSectionSize())
    except Exception:
        header_min_px = 0
    width_manager = getattr(window, "width_manager", None)
    user_widths = _resolved_user_column_widths(window, width_manager)
    for column_index, col_name in enumerate(display_df.columns):
        px = table_widths.resolve_column_width(
            window,
            col_name,
            include_runtime=True,
            include_preferences=True,
        )

        min_px = _minimum_table_column_width(col_name, header_min_px)
        window.table_widget.setColumnWidth(
            column_index,
            _target_table_column_width(width_manager, col_name, int(px), min_px, user_widths),
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
        table_cell_alignment = _table_cell_alignment_from_preferences()
        _populate_table_items(window, display_df, table_cell_alignment)
        window._last_table_cell_alignment = table_cell_alignment


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


def _can_skip_reused_render_finalize(window, display_df) -> bool:
    """Return True when a reused page render does not need width/header work."""
    expected_alignment = _table_cell_alignment_from_preferences()
    if getattr(window, "_last_table_cell_alignment", None) != expected_alignment:
        return False
    if bool(getattr(window, "_skip_width_recompute_once", False)):
        return False
    cols_sig = tuple(display_df.columns)
    try:
        if int(window.table_widget.columnCount()) != len(cols_sig):
            return False
    except Exception as exc:
        logger.debug("Falha ao validar contagem de colunas reutilizadas: %s", exc)
        return False
    try:
        viewport_width = window.table_widget.viewport().width()
    except Exception:
        viewport_width = -1
    try:
        if table_widths.needs_width_recompute(window, cols_sig, viewport_width):
            return False
    except Exception as exc:
        logger.debug(
            "Falha ao avaliar reaproveitamento de render da tabela: %s", exc
        )
        return False
    try:
        header_min_px = int(window.table_widget.horizontalHeader().minimumSectionSize())
    except Exception:
        header_min_px = 0
    width_manager = getattr(window, "width_manager", None)
    user_widths = _resolved_user_column_widths(window, width_manager)
    for column_index, col_name in enumerate(display_df.columns):
        try:
            desired_px = table_widths.resolve_column_width(
                window,
                col_name,
                include_runtime=True,
                include_preferences=True,
            )
            min_px = _minimum_table_column_width(col_name, header_min_px)
            target_px = _target_table_column_width(
                width_manager, col_name, int(desired_px), min_px, user_widths
            )
            if int(window.table_widget.columnWidth(column_index)) != target_px:
                return False
        except Exception as exc:
            logger.debug(
                "Falha ao comparar largura reutilizada da coluna %s: %s",
                col_name,
                exc,
            )
            return False
    return True


def _finalize_page_render(
    window, display_df, render_signature, *, update_details, reuse_render=False
):
    if reuse_render and _can_skip_reused_render_finalize(window, display_df):
        try:
            window._ensure_nonzero_column_widths()
        except Exception as exc:
            logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)
        _apply_adaptive_header_labels(window)
        _refresh_initial_details(window, update_details=update_details)
        window._last_table_render_signature = render_signature
        return

    header = window.table_widget.horizontalHeader()
    _apply_rendered_table_widths(window, display_df)

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
        QTimer.singleShot(0, lambda: window._ensure_nonzero_column_widths())
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
        window,
        display_df,
        render_signature,
        update_details=update_details,
        reuse_render=reuse_render,
    )


# --- Wrappers de compatibilidade com testes antigos (PoC) ---
def display_data(window, df):  # usado em testes legados
    try:
        if df is None or getattr(df, "empty", True):
            return
        window.df_completo = df.copy()
        window.df_exibido = df.copy()
        window.paginator.set_dataframe(window.df_exibido)
        display_current_page(window, getattr(window.paginator, "current_page", 1))
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
    internal_to_display=None,
    saved_widths=None,
    widget_width: int = 0,
    window_width: int = 0,
):
    return table_widths.compute_widths_for_df(
        df,
        visible_columns,
        width_manager,
        internal_to_display,
        saved_widths,
        widget_width=widget_width,
        window_width=window_width,
    )


def _compute_column_widths_from_context(df: pd.DataFrame, context):
    return table_widths.compute_column_widths_from_context(df, context)


def _sample_width_dataframe(df: pd.DataFrame, max_rows: int = 1000) -> pd.DataFrame:
    return table_widths.sample_width_dataframe(df, max_rows=max_rows)


def _compute_gui_column_widths(window, df: pd.DataFrame):
    return table_widths.compute_gui_column_widths(window, df)


def _on_header_section_resized(
    window, logical_index: int, old_size: int, new_size: int
):
    """Salva a largura ajustada pelo usuario na configuracao persistente."""
    del old_size
    try:
        col_name = table_widths.resolve_column_name_for_width_persist(
            window, logical_index
        )
        if not col_name:
            return
        table_widths.persist_column_width_change(window, col_name, new_size)
        _schedule_adaptive_header_label_refresh(window)
        _schedule_column_width_preferences_persist(window)
    except Exception as exc:  # noqa: BLE001
        # Evita quebrar a GUI por falhas de IO, mas preserva evidencia no log.
        logger.debug("Falha ao persistir largura de coluna redimensionada: %s", exc)


def _resolve_column_name_for_width_persist(window, logical_index: int) -> str | None:
    return table_widths.resolve_column_name_for_width_persist(window, logical_index)


def _persist_column_width_change(window, col_name: str, new_size: int) -> None:
    table_widths.persist_column_width_change(window, col_name, new_size)
    _schedule_adaptive_header_label_refresh(window)
    _schedule_column_width_preferences_persist(window)


def _flush_column_width_preferences(window) -> None:
    return table_widths.flush_column_width_preferences(window)


def _schedule_column_width_preferences_persist(window) -> None:
    return table_widths.schedule_column_width_preferences_persist(window)


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
    was_updates_enabled = bool(table.updatesEnabled())
    table.setUpdatesEnabled(False)
    try:
        current_columns = _current_display_columns(window)
        for row_index in range(row_count):
            for column_index in range(column_count):
                item = table.item(row_index, column_index)
                if item is None:
                    continue
                col_name = (
                    str(current_columns[column_index] or "")
                    if 0 <= column_index < len(current_columns)
                    else ""
                )
                effective_alignment = _table_cell_alignment_for_column(
                    col_name,
                    table_cell_alignment,
                )
                if item.textAlignment() != effective_alignment:
                    item.setTextAlignment(effective_alignment)
        window._last_table_cell_alignment = table_cell_alignment
    finally:
        table.setUpdatesEnabled(was_updates_enabled)
