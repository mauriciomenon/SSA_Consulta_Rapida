# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import hashlib
import os
from typing import Any, Mapping, cast

import pandas as pd

from gui.helpers.formatting_helpers import highlight_text
from gui.helpers.theme_helpers import pick_css_color
from gui.qt_stubs import QTimer
from shared.numero_ssa import normalize_relation_id as normalize_numero_ssa_relation
from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from shared.ssa_status import format_status_display, get_status_code
from utils.formatting import format_cell
from utils.robust_logging import get_robust_logger
from utils.themes import get_theme_roles

logger = get_robust_logger().get_logger(__name__, "gui")

DETAILS_DIALOG_FONT_SIZE = 10
DETAILS_DIALOG_TABLE_PADDING = 8
DETAILS_DIALOG_BORDER_COLOR = "#ccc"
DETAIL_FIELD_PRIORITY = []
DETAIL_DISPLAY_OVERRIDES = {}
HIGHLIGHT_BACKGROUND_COLOR = "yellow"
HIGHLIGHT_FONT_WEIGHT = "bold"
MONO_FONT_FAMILY = "monospace"
HIDDEN_DETAIL_FIELDS = {"id", "derivada_de"}
DERIVADAS_DETAILS_TOP_N = 5
DERIVADAS_DIALOG_RATIO_LEFT = 24
DERIVADAS_DIALOG_RATIO_RIGHT = 76
DERIVADAS_DIALOG_MIN_HEIGHT = 640
DERIVADAS_DIALOG_DETAILS_FONT_PT = 12.0
DERIVADAS_DIALOG_TREE_FONT_PT = 12.0
DERIVADAS_DIALOG_LABEL_FONT_PT = 11.0
SSA_NORM_CACHE_MAX_ENTRIES = 64
DERIVADAS_DIALOG_MIN_WIDTH = 960
DERIVADAS_DIALOG_TREE_MIN_WIDTH = 180
DERIVADAS_DIALOG_DETAILS_MIN_WIDTH = 520
DERIVADAS_GRAPH_NODE_WIDTH = 100
DERIVADAS_GRAPH_NODE_HEIGHT = 30
DERIVADAS_GRAPH_X_GAP = 170
DERIVADAS_GRAPH_Y_GAP = 60
DERIVADAS_GRAPH_MARGIN = 8
DERIVADAS_GRAPH_MAX_DESCENDANTS = 120
DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT = 120
DERIVADAS_SPLITTER_HANDLE_WIDTH = 10
DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT = 180


def _init_readonly_text_browser(
    browser, *, min_width: int | None = None, min_height: int | None = None
):
    browser.setReadOnly(True)
    browser.setOpenLinks(False)
    browser.setOpenExternalLinks(False)
    if min_width is not None:
        browser.setMinimumWidth(min_width)
    if min_height is not None:
        browser.setMinimumHeight(min_height)
    return browser


def configure_details_constants(
    details_dialog_font_size,
    details_dialog_table_padding,
    details_dialog_border_color,
    detail_field_priority,
    detail_display_overrides,
    highlight_background_color,
    highlight_font_weight,
    mono_font_family,
) -> None:
    global DETAILS_DIALOG_FONT_SIZE
    global DETAILS_DIALOG_TABLE_PADDING
    global DETAILS_DIALOG_BORDER_COLOR
    global DETAIL_FIELD_PRIORITY
    global DETAIL_DISPLAY_OVERRIDES
    global HIGHLIGHT_BACKGROUND_COLOR
    global HIGHLIGHT_FONT_WEIGHT
    global MONO_FONT_FAMILY

    if details_dialog_font_size is not None:
        DETAILS_DIALOG_FONT_SIZE = details_dialog_font_size
    if details_dialog_table_padding is not None:
        DETAILS_DIALOG_TABLE_PADDING = details_dialog_table_padding
    if details_dialog_border_color is not None:
        DETAILS_DIALOG_BORDER_COLOR = details_dialog_border_color
    if detail_field_priority is not None:
        DETAIL_FIELD_PRIORITY = list(detail_field_priority)
    if detail_display_overrides is not None:
        DETAIL_DISPLAY_OVERRIDES = dict(detail_display_overrides)
    if highlight_background_color is not None:
        HIGHLIGHT_BACKGROUND_COLOR = highlight_background_color
    if highlight_font_weight is not None:
        HIGHLIGHT_FONT_WEIGHT = highlight_font_weight
    if mono_font_family is not None:
        MONO_FONT_FAMILY = mono_font_family


def _normalize_highlight_term(window, term):
    """Remove modos e negacoes para uso no highlight."""
    if term is None:
        return ""
    cleaned = str(term).strip()
    if not cleaned:
        return ""
    if cleaned.startswith("!") or cleaned.startswith("-"):
        cleaned = cleaned[1:]
    if cleaned.startswith("~") or cleaned.startswith("=") or cleaned.startswith("^"):
        cleaned = cleaned[1:]
    if cleaned.endswith("$"):
        cleaned = cleaned[:-1]
    return cleaned.strip()


def _get_current_search_terms(window):
    """Retorna lista de termos de busca atuais."""
    search_text = window.search_input.text().strip()
    if not search_text:
        return []
    terms = [term.strip() for term in search_text.split(",") if term.strip()]
    clean_terms = []
    for term in terms:
        normalized = _normalize_highlight_term(window, term)
        if normalized:
            clean_terms.append(normalized)
    return clean_terms


def _collect_highlight_terms(window):
    """Combina termos da busca geral e filtros de coluna para realce."""
    aggregated = []
    seen = set()
    for term in _get_current_search_terms(window):
        if term and term not in seen:
            aggregated.append(term)
            seen.add(term)
    for raw in getattr(window, "_active_column_filters", {}).values():
        if not raw:
            continue
        normalized_raw = str(raw).replace(";", ",")
        tokens = [tok.strip() for tok in normalized_raw.split(",") if tok.strip()]
        for tok in tokens:
            normalized = _normalize_highlight_term(window, tok)
            if normalized and normalized not in seen:
                aggregated.append(normalized)
                seen.add(normalized)
    return aggregated


def _highlight_text(window, text, terms):
    """Delegate to helper function."""
    bg = getattr(window, "_highlight_bg_color", HIGHLIGHT_BACKGROUND_COLOR)
    fg = getattr(window, "_highlight_text_color", None)
    weight = getattr(window, "_highlight_font_weight", HIGHLIGHT_FONT_WEIGHT)
    try:
        return highlight_text(
            text,
            terms,
            bg_color=bg,
            font_weight=weight,
            text_color=fg,
        )
    except TypeError:
        # Compat with legacy helper signatures (without text_color).
        try:
            return highlight_text(text, terms, bg, weight)
        except TypeError:
            return highlight_text(text, terms)


def _get_situacao_for_ssa(window, numero_ssa) -> str:
    try:
        series = _get_series_for_ssa(window, numero_ssa)
    except Exception as exc:
        logger.debug("Falha ao resolver situacao para SSA %s: %s", numero_ssa, exc)
        return ""
    if series is None:
        return ""
    try:
        value = series.get("situacao")
    except Exception as exc:
        logger.debug(
            "Falha ao obter campo situacao para SSA %s: %s", numero_ssa, exc
        )
        value = ""
    return get_status_code(value)


def _build_ssa_href(numero_ssa: str, *, panel_mode: bool) -> str:
    normalized = _normalize_ssa_relation_value(numero_ssa)
    if not normalized:
        return ""
    return f"ssa-panel:{normalized}" if panel_mode else f"ssa:{normalized}"


def _render_ssa_navigation_link(
    numero_ssa: str,
    *,
    link_color: str,
    panel_mode: bool,
    exists: bool,
    status_hint: str = "",
) -> str:
    normalized = _normalize_ssa_relation_value(numero_ssa)
    if not normalized:
        return html_module.escape(str(numero_ssa or ""))
    label = normalized
    status_code = str(status_hint or "").strip().upper()
    if status_code:
        label = f"{normalized} ({status_code})"
    escaped_label = html_module.escape(label)
    href = _build_ssa_href(normalized, panel_mode=panel_mode)
    if not exists or not href:
        return escaped_label
    return (
        f'<a href="{href}" style="color:{link_color}; '
        f'text-decoration:none; border-bottom: 1px solid {link_color};">'
        f"{escaped_label}</a>"
    )


def _format_details_html(
    window,
    series,
    highlight_search_terms=False,
    font_size_pt=None,
    linkify=False,
    label_font_size_pt=None,
    font_family=None,
    ssa_index: Mapping[str, pd.Series] | None = None,
):
    """Formata dados da SSA como HTML com highlight opcional."""
    if font_size_pt is None:
        font_size_pt = DETAILS_DIALOG_FONT_SIZE
    if label_font_size_pt is None:
        label_font_size_pt = font_size_pt
    if not font_family:
        try:
            ui_font_family = str(window.font().family() or "").strip()
        except Exception as exc:
            logger.debug("Falha ao ler familia de fonte da UI para detalhes: %s", exc)
            ui_font_family = ""
        font_family = ui_font_family or "sans-serif"

    search_terms = _collect_highlight_terms(window) if highlight_search_terms else []

    theme_roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
    try:
        from PyQt6.QtGui import QPalette as _QPal

        text_color = pick_css_color(
            window.palette().color(_QPal.ColorRole.WindowText).name(),
            theme_roles.get("panel_text"),
            theme_roles.get("label_color"),
            fallback="#d0d0d0",
        )
        link_color = pick_css_color(
            window.palette().color(_QPal.ColorRole.Highlight).name(),
            theme_roles.get("accent"),
            text_color,
            fallback="#4a90e2",
        )
    except Exception as exc:
        logger.debug("Falha ao resolver cores de tema para detalhes HTML: %s", exc)
        text_color = pick_css_color(
            theme_roles.get("panel_text"),
            theme_roles.get("label_color"),
            fallback="#d0d0d0",
        )
        link_color = pick_css_color(
            theme_roles.get("accent"),
            text_color,
            fallback="#4a90e2",
        )

    html_lines = [
        (
            f'<html><body style="font-family: {font_family}; '
            f'font-size: {font_size_pt}pt; color: {text_color};">'
        )
    ]
    html_lines.append(
        '<table style="width: 100%; border-collapse: collapse; table-layout: fixed;">'
    )
    html_lines.append(
        '<colgroup><col style="width: 18%;"/><col style="width: 82%;"/></colgroup>'
    )

    def field_sort_key(item):
        col, _ = item
        try:
            return (0, DETAIL_FIELD_PRIORITY.index(col))
        except ValueError:
            return (1, col)

    sorted_items = sorted(series.items(), key=field_sort_key)

    for col, value in sorted_items:
        if col in HIDDEN_DETAIL_FIELDS or str(col).startswith("_"):
            continue
        formatted_value = format_cell(value, col)
        if not formatted_value:
            continue
        if col == "situacao":
            formatted_value = format_status_display(formatted_value)
        display_name = DETAIL_DISPLAY_OVERRIDES.get(
            col, window.internal_to_display.get(col, col)
        )
        if col == "numero_ssa" and linkify:
            safe_ssa = _normalize_ssa_value(window, formatted_value)
            escaped_value = html_module.escape(formatted_value)
            if safe_ssa:
                formatted_value = (
                    f'<a href="copy-ssa:{safe_ssa}" style="color:{text_color}; '
                    f'text-decoration:none;">{escaped_value}</a>'
                )
            else:
                formatted_value = escaped_value
        elif highlight_search_terms and search_terms:
            formatted_value = _highlight_text(window, formatted_value, search_terms)
        else:
            formatted_value = html_module.escape(formatted_value)
        display_name_html = html_module.escape(display_name)
        if display_name == "Grau de Prioridade (Emissao)":
            display_name_html = "Grau de Prioridade<br/>(Emissao)"
        elif display_name == "Data do Arquivo de Origem":
            display_name_html = "Data do Arquivo<br/>de Origem"

        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
            f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
            f"{display_name_html}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
            f'overflow-wrap: anywhere; word-break: break-word;">'
            f"{formatted_value}</td>"
            f"</tr>"
        )

    allow_global_index = ssa_index is None
    if allow_global_index:
        ssa_index = _get_window_ssa_series_index(window)
    if ssa_index is None:
        ssa_index = {}

    try:
        derived_list = _get_derivadas_for_ssa(window, series.get("numero_ssa"))
    except Exception as exc:
        logger.debug(
            "Falha ao coletar lista de derivadas para detalhes HTML: %s", exc
        )
        derived_list = []
    if derived_list:
        if linkify:
            items = []
            derived_exists_cache: dict[str, bool] = {}
            for item in derived_list:
                href = _normalize_ssa_value(window, item)
                exists = False
                if href:
                    cached_exists = derived_exists_cache.get(href)
                    if cached_exists is None:
                        resolved_series = ssa_index.get(href)
                        if resolved_series is None:
                            resolved_series = _get_series_for_ssa(window, href)
                        cached_exists = resolved_series is not None
                        derived_exists_cache[href] = cached_exists
                    exists = cached_exists
                items.append(
                    _render_ssa_navigation_link(
                        href or item,
                        link_color=link_color,
                        panel_mode=False,
                        exists=exists,
                    )
                )
            derived_text = ", ".join(items)
        else:
            derived_text = ", ".join(derived_list)
            if highlight_search_terms and search_terms:
                derived_text = _highlight_text(window, derived_text, search_terms)
            else:
                derived_text = html_module.escape(derived_text)
        label = f"SSAs derivadas ({len(derived_list)})"
        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
            f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
            f"{html_module.escape(label)}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
            f'overflow-wrap: anywhere; word-break: break-word;">'
            f"{derived_text}</td>"
            f"</tr>"
        )

    related_items = _get_related_ssas_for_series(window, series, ssa_index=ssa_index)
    if related_items:
        rendered_items = []
        seen_related = set()
        for item in related_items:
            related_ssa = str(item.get("ssa", "") or "").strip()
            if not related_ssa or related_ssa in seen_related:
                continue
            seen_related.add(related_ssa)
            rendered_items.append(
                _render_ssa_navigation_link(
                    related_ssa,
                    link_color=link_color,
                    panel_mode=False,
                    exists=bool(item.get("exists", False)) if linkify else False,
                    status_hint="",
                )
                if linkify
                else html_module.escape(related_ssa)
            )
        if rendered_items:
            label = f"SSAs relacionadas ({len(rendered_items)})"
            related_text = ", ".join(rendered_items)
            html_lines.append(
                f"<tr>"
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
                f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
                f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
                f"{html_module.escape(label)}:</td>"
                f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
                f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
                f'overflow-wrap: anywhere; word-break: break-word;">'
                f"{related_text}</td>"
                f"</tr>"
            )

    html_lines.append("</table></body></html>")
    return "\n".join(html_lines)


def _normalize_ssa_value(window, value):
    raw = value
    if raw is None:
        return ""
    # Handle float artifacts from DataFrame/object conversion (e.g. 121911787.0).
    try:
        if isinstance(raw, float):
            if pd.isna(raw):
                return ""
            if raw.is_integer():
                raw = int(raw)
    except Exception as exc:
        logger.debug("Falha ao normalizar artefato float de SSA %r: %s", value, exc)
    text = str(raw).strip()
    if not text:
        return ""
    strict_value = normalize_numero_ssa_strict(text)
    if strict_value:
        return strict_value
    if text.count(".") == 1:
        whole, fractional = text.split(".", 1)
        if whole.isdigit() and fractional and set(fractional) <= {"0"}:
            text = whole
    lowered = text.casefold()
    if lowered in ("nan", "none", "nat", "<na>"):
        return ""
    if text.isdigit():
        # Compat branch: GUI tests and local temporary IDs can still be short numeric.
        return text
    if text and all(ch.isdigit() or ch in ".- " for ch in text):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return digits
    return lowered


def _normalize_ssa_series(window, series: pd.Series) -> pd.Series:
    """Normaliza SSA em serie com cache por valor unico."""
    try:
        series_obj = series.astype("object")
        codes, uniques = pd.factorize(series_obj, sort=False)
        normalized_uniques = [_normalize_ssa_value(window, value) for value in uniques]
        resolved = [""] * len(series_obj)
        for index, code in enumerate(codes):
            if code >= 0:
                resolved[index] = normalized_uniques[code]
        return pd.Series(resolved, index=series_obj.index, dtype="object")
    except Exception as exc:
        logger.debug("Falha ao normalizar SSA series; fallback apply: %s", exc)
        try:
            return series.map(lambda value: _normalize_ssa_value(window, value))
        except Exception as fallback_exc:
            logger.debug("Falha no fallback de normalizacao SSA series: %s", fallback_exc)
            return pd.Series([""] * len(series), index=getattr(series, "index", None))


def _normalize_ssa_relation_value(value) -> str:
    normalized = str(normalize_numero_ssa_relation(value) or "").strip()
    if normalized:
        return normalized
    text = str(value or "").strip()
    if text.isdigit():
        return text
    if "." not in text:
        return ""
    whole, fractional = text.split(".", 1)
    if whole.isdigit() and fractional and set(fractional) <= {"0"}:
        return whole
    return ""


def _normalize_ssa_relation_series(series: pd.Series) -> pd.Series:
    try:
        series_obj = series.astype("object")
        codes, uniques = pd.factorize(series_obj, sort=False)
        normalized_uniques = [_normalize_ssa_relation_value(value) for value in uniques]
        resolved = [""] * len(series_obj)
        for index, code in enumerate(codes):
            if code >= 0:
                resolved[index] = normalized_uniques[code]
        return pd.Series(resolved, index=series_obj.index, dtype="object")
    except Exception:
        return series.map(_normalize_ssa_relation_value)


def _get_cached_normalized_series(window, df, column_name: str) -> pd.Series:
    if df is None or column_name not in getattr(df, "columns", []):
        return pd.Series(dtype="object")
    data_uuid = getattr(window, "_data_uuid", None)
    if data_uuid is None:
        return _normalize_ssa_series(window, df[column_name])
    cache_owner = getattr(window, "cache_manager", None)
    cache_get = getattr(cache_owner, "get_cached_value", None)
    cache_put = getattr(cache_owner, "cache_value", None)
    if not callable(cache_get) or not callable(cache_put):
        return _normalize_ssa_series(window, df[column_name])
    key = (
        id(df),
        str(column_name),
        len(df),
        getattr(window, "_data_revision", None),
        data_uuid,
    )
    cached = cache_get("ssa_norm", key)
    if isinstance(cached, pd.Series) and len(cached) == len(df):
        return cached
    normalized = _normalize_ssa_series(window, df[column_name])
    cache_put(
        "ssa_norm",
        key,
        normalized,
        max_entries=SSA_NORM_CACHE_MAX_ENTRIES,
    )
    return normalized


def _get_df_ssa_series_index(window, df) -> dict[str, pd.Series]:
    if df is None or df.empty or "numero_ssa" not in getattr(df, "columns", []):
        return {}
    data_uuid = getattr(window, "_data_uuid", None)
    cache_enabled = data_uuid is not None
    cache_owner = getattr(window, "cache_manager", None)
    cache_get = getattr(cache_owner, "get_cached_value", None)
    cache_put = getattr(cache_owner, "cache_value", None)
    has_cache_manager = callable(cache_get) and callable(cache_put)
    cache_key = (
        id(df),
        len(df),
        getattr(window, "_data_revision", None),
        data_uuid,
    )
    cached = (
        cast(Any, cache_get)("details_df_ssa_index", cache_key)
        if cache_enabled and has_cache_manager
        else None
    )
    if isinstance(cached, dict) and cached:
        return cached

    lookup: dict[str, pd.Series] = {}
    normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
    try:
        for idx_label, normalized in zip(df.index, normalized_series.tolist()):
            normalized_text = str(normalized or "").strip()
            if not normalized_text or normalized_text in lookup:
                continue
            matched = df.loc[idx_label]
            if isinstance(matched, pd.DataFrame):
                matched = matched.iloc[0]
            lookup[normalized_text] = matched
    except Exception as exc:
        logger.debug("Falha ao montar indice SSA por DataFrame: %s", exc)
        return {}
    if cache_enabled and has_cache_manager:
        cast(Any, cache_put)(
            "details_df_ssa_index",
            cache_key,
            lookup,
            max_entries=8,
        )
    return lookup


def _get_window_ssa_series_index(window) -> dict[str, pd.Series]:
    current_sources = (
        getattr(window, "df_exibido", None),
        getattr(window, "df_completo", None),
    )
    data_uuid = getattr(window, "_data_uuid", None)
    data_revision = getattr(window, "_data_revision", None)
    if data_uuid is None:
        cached_sources = None
    else:
        cached_sources = getattr(window, "_details_ssa_index_sources", None)
    cached_lookup = getattr(window, "_details_ssa_series_index", None)
    if (
        isinstance(cached_sources, tuple)
        and len(cached_sources) == 4
        and cached_sources[0] is current_sources[0]
        and cached_sources[1] is current_sources[1]
        and cached_sources[2] == data_revision
        and cached_sources[3] == data_uuid
        and isinstance(cached_lookup, dict)
    ):
        return cached_lookup

    merged: dict[str, pd.Series] = {}
    for df in current_sources:
        for numero_ssa, series in _get_df_ssa_series_index(window, df).items():
            if numero_ssa not in merged:
                merged[numero_ssa] = series
    if data_uuid is not None:
        window._details_ssa_index_sources = (
            current_sources[0],
            current_sources[1],
            data_revision,
            data_uuid,
        )
        window._details_ssa_series_index = merged
    return merged


def _get_details_db_signature():
    db_path = _resolve_current_db_path()
    if not db_path:
        return None
    try:
        return os.path.getmtime(db_path)
    except Exception as exc:
        logger.debug("Falha ao ler mtime do banco de detalhes %s: %s", db_path, exc)
        return None


def _get_details_render_signature(window, series):
    if series is None:
        return None
    try:
        selected_ssa = series.get("numero_ssa")
    except Exception as exc:
        logger.debug("Falha ao ler numero_ssa da serie para assinatura: %s", exc)
        selected_ssa = None
    try:
        search_terms = tuple(_collect_highlight_terms(window))
    except Exception as exc:
        logger.debug("Falha ao coletar termos para assinatura de detalhes: %s", exc)
        search_terms = ()
    try:
        series_signature = tuple(
            (str(column), "" if pd.isna(value) else str(value))
            for column, value in series.items()
        )
    except Exception as exc:
        logger.debug("Falha ao montar assinatura estruturada de detalhes: %s", exc)
        try:
            series_signature = str(series)
        except Exception as fallback_exc:
            logger.debug(
                "Falha no fallback textual da assinatura de detalhes: %s",
                fallback_exc,
            )
            series_signature = ""
    return (selected_ssa, search_terms, _get_details_db_signature(), series_signature)


def update_details_from_selection(window):
    """Atualiza o painel de detalhes com base na linha selecionada."""
    if window.table_widget.rowCount() == 0:
        window._details_current_ssa = None
        window.details_text.setProperty("details_render_signature", None)
        window.details_text.clear()
        return
    selected_rows = window.table_widget.selectionModel().selectedRows()
    if not selected_rows:
        window._details_current_ssa = None
        window.details_text.setProperty("details_render_signature", None)
        window.details_text.clear()
        return
    row = selected_rows[0].row()
    series = window._get_series_from_row(row)
    selected_ssa = None
    try:
        selected_ssa = series.get("numero_ssa")
    except Exception as exc:
        logger.debug("Falha ao ler numero_ssa da linha selecionada: %s", exc)
        selected_ssa = None
    render_signature = _get_details_render_signature(window, series)
    current_signature = window.details_text.property("details_render_signature")
    skip_ssa = window.table_widget.property("details_skip_selection_once_for_ssa")
    if skip_ssa is not None:
        window.table_widget.setProperty("details_skip_selection_once_for_ssa", None)
    if selected_ssa is not None and selected_ssa == skip_ssa:
        try:
            if (
                not window.details_text.document().isEmpty()
                and render_signature == current_signature
            ):
                return
        except Exception:
            if (
                window.details_text.toPlainText().strip()
                and render_signature == current_signature
            ):
                return
    try:
        if (
            not window.details_text.document().isEmpty()
            and render_signature == current_signature
        ):
            return
    except Exception:
        if (
            window.details_text.toPlainText().strip()
            and render_signature == current_signature
        ):
            return
    _update_details_from_series(window, series)


def _update_details_from_series(window, series):
    """Atualiza o painel de detalhes a partir de uma serie ja resolvida."""
    if series is None:
        window._details_current_ssa = None
        window.details_text.setProperty("details_render_signature", None)
        window.details_text.clear()
        return
    render_signature = _get_details_render_signature(window, series)
    try:
        window._details_current_ssa = series.get("numero_ssa")
    except Exception:
        window._details_current_ssa = None

    try:
        font_size_pt = None
        font_family = None
        if hasattr(window, "details_group"):
            try:
                base_font = window.details_group.font()
                size = base_font.pointSizeF()
                if size <= 0:
                    size = float(base_font.pointSize())
                if size > 0:
                    font_size_pt = max(size - 1.0, 8.0)
                family = str(base_font.family() or "").strip()
                if family:
                    font_family = family
            except Exception:
                font_size_pt = None
                font_family = None
        html_content = _format_details_html(
            window,
            series,
            highlight_search_terms=True,
            font_size_pt=font_size_pt,
            linkify=True,
            font_family=font_family,
            # Evita construir o indice SSA global no primeiro paint do painel.
            # Para o painel lateral, os poucos lookups adicionais sao mais baratos
            # que materializar o indice completo no startup.
            ssa_index={},
        )
        window.details_text.setHtml(html_content)
        window.details_text.setProperty("details_render_signature", render_signature)
        return
    except Exception as exc:
        logger.debug(
            "Falha ao renderizar detalhes em HTML; aplicando fallback texto: %s", exc
        )

    def field_sort_key(item):
        col, _ = item
        try:
            return (0, DETAIL_FIELD_PRIORITY.index(col))
        except ValueError:
            return (1, col)

    sorted_items = sorted(series.items(), key=field_sort_key)
    lines = []
    for col, value in sorted_items:
        if col in HIDDEN_DETAIL_FIELDS or str(col).startswith("_"):
            continue
        formatted_value = format_cell(value, col)
        if not formatted_value:
            continue
        if col == "situacao":
            formatted_value = format_status_display(formatted_value)
        display_name = DETAIL_DISPLAY_OVERRIDES.get(
            col, window.internal_to_display.get(col, col)
        )
        lines.append(f"{display_name}: {formatted_value}")
    details_str = "\n".join(lines)
    try:
        window.details_text.setPlainText(details_str)
        window.details_text.setProperty("details_render_signature", render_signature)
    except Exception as exc:
        logger.debug("Falha ao renderizar detalhes em texto simples: %s", exc)


def _get_derivadas_for_ssa(window, numero_ssa):
    if window.df_completo is None or window.df_completo.empty:
        return []
    if (
        "derivada_de" not in window.df_completo.columns
        or "numero_ssa" not in window.df_completo.columns
    ):
        return []
    num_norm = _normalize_ssa_relation_value(numero_ssa)
    if not num_norm:
        return []
    try:
        derived = []
        seen = set()
        for parent_value, child_value in _get_cached_derivadas_family_edges(window):
            if parent_value != num_norm or not child_value or child_value in seen:
                continue
            seen.add(child_value)
            derived.append(child_value)
        return derived
    except Exception as exc:
        logger.debug("Falha ao coletar derivadas para SSA %s: %s", numero_ssa, exc)
        return []


def _get_related_ssas_for_series(
    window, series, *, ssa_index: Mapping[str, pd.Series] | None = None
) -> list[dict[str, str]]:
    if series is None:
        return []
    relation_value = series.get("relacao", "")
    relation_label = "" if pd.isna(relation_value) else str(relation_value).strip()
    related_specs = (
        ("numero_ssa_relacionada_1", "situacao_relacionada_1"),
        ("numero_ssa_relacionada_2", "situacao_relacionada_2"),
        ("numero_ssa_relacionada_3", None),
    )
    related_items: list[dict[str, str]] = []
    seen: set[str] = set()
    for numero_col, situacao_col in related_specs:
        normalized = _normalize_ssa_relation_value(series.get(numero_col, ""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        status_hint = ""
        if situacao_col:
            status_value = series.get(situacao_col, "")
            if not pd.isna(status_value):
                status_hint = str(status_value).strip().upper()
        resolved_series = None
        if isinstance(ssa_index, Mapping):
            resolved_series = ssa_index.get(normalized)
        if resolved_series is None:
            resolved_series = _get_series_for_ssa(window, normalized)
        if not status_hint and resolved_series is not None:
            try:
                status_hint = get_status_code(resolved_series.get("situacao"))
            except Exception as exc:
                logger.debug(
                    "Falha ao obter situacao da SSA relacionada %s: %s",
                    normalized,
                    exc,
                )
        related_items.append(
            {
                "ssa": normalized,
                "situacao": status_hint,
                "relacao": relation_label,
                "exists": "1" if resolved_series is not None else "",
            }
        )
    return related_items


def _get_direct_parent_for_series(series: pd.Series | None) -> str:
    if series is None:
        return ""
    return _normalize_ssa_relation_value(series.get("derivada_de"))


def _jump_to_ssa(window, numero_ssa, *, _allow_refilter=True):
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return
    try:
        pos = None
        if (
            window.df_exibido is not None
            and not window.df_exibido.empty
            and "numero_ssa" in window.df_exibido.columns
        ):
            series_norm = _get_cached_normalized_series(
                window, window.df_exibido, "numero_ssa"
            )
            mask = series_norm.eq(num_norm)
            if mask.any():
                positions = mask.to_numpy().nonzero()[0]
                if len(positions) > 0:
                    pos = int(positions[0])
        if pos is None and _allow_refilter:
            window.search_input.setText(f"={num_norm}")
            window.initiate_filtering()
            request_id = getattr(window, "_active_filter_request_id", None)
            filter_thread = getattr(window, "filter_thread", None)
            is_async_inflight = False
            try:
                is_async_inflight = bool(
                    filter_thread is not None
                    and hasattr(filter_thread, "isRunning")
                    and filter_thread.isRunning()
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao verificar worker pendente no salto para SSA %s: %s",
                    num_norm,
                    exc,
                )
                is_async_inflight = False
            if is_async_inflight and request_id is not None:
                window._pending_jump_to_ssa = {
                    "numero_ssa": num_norm,
                    "request_id": request_id,
                }
                return
            if (
                window.df_exibido is not None
                and not window.df_exibido.empty
                and "numero_ssa" in window.df_exibido.columns
            ):
                series_norm = _get_cached_normalized_series(
                    window, window.df_exibido, "numero_ssa"
                )
                mask = series_norm.eq(num_norm)
                if mask.any():
                    positions = mask.to_numpy().nonzero()[0]
                    if len(positions) > 0:
                        pos = int(positions[0])
        if pos is None and not _allow_refilter:
            _update_details_from_series(window, _get_series_for_ssa(window, num_norm))
            return
        if pos is None:
            return
        page_size = int(getattr(window.paginator, "page_size", 50))
        if page_size <= 0:
            logger.warning(
                "Page size invalido ao saltar para SSA %s: %s", num_norm, page_size
            )
            return
        page = int(pos // page_size + 1)
        try:
            window.paginator.current_page = page
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar pagina atual no salto para SSA %s: %s",
                num_norm,
                exc,
            )
        window.display_current_page(page, update_details=False)
        row_in_page = int(pos % page_size)
        target_series = None
        try:
            target_series = window.df_exibido.iloc[int(pos)]
        except Exception as exc:
            logger.debug(
                "Falha ao resolver serie alvo no salto para SSA %s: %s", num_norm, exc
            )
        _update_details_from_series(window, target_series)
        window.table_widget.setProperty(
            "details_skip_selection_once_for_ssa",
            getattr(window, "_details_current_ssa", None),
        )

        def _select_target_row_later():
            try:
                if int(getattr(window.paginator, "current_page", 1)) != page:
                    return
                if row_in_page < 0 or row_in_page >= window.table_widget.rowCount():
                    return
                window.table_widget.selectRow(row_in_page)
            except Exception as exc:
                logger.debug(
                    "Falha ao selecionar linha %s no salto para SSA %s: %s",
                    row_in_page,
                    num_norm,
                    exc,
                )

        try:
            QTimer.singleShot(0, _select_target_row_later)
        except Exception as exc:
            logger.debug(
                "Falha ao agendar selecao da linha %s no salto para SSA %s: %s",
                row_in_page,
                num_norm,
                exc,
            )
            _select_target_row_later()
    except Exception as exc:
        logger.debug("Falha ao navegar para SSA %s: %s", numero_ssa, exc)


def _get_series_for_ssa(window, numero_ssa):
    target = _normalize_ssa_value(window, numero_ssa)
    if not target:
        return None

    def _find_in_df(df):
        if df is None or df.empty or "numero_ssa" not in df.columns:
            return None
        try:
            normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
            if normalized_series.empty:
                return None
            matches = normalized_series.eq(target)
            if not bool(matches.any()):
                return None
            positions = matches.to_numpy().nonzero()[0]
            if len(positions) == 0:
                return None
            matched = df.iloc[int(positions[0])]
            if isinstance(matched, pd.DataFrame):
                matched = matched.iloc[0]
            return matched
        except Exception as exc:
            logger.debug("Falha ao localizar SSA %s em dataframe: %s", target, exc)
            return None

    match = _find_in_df(getattr(window, "df_exibido", None))
    if match is not None:
        return match
    return _find_in_df(getattr(window, "df_completo", None))


def _on_details_anchor_clicked(window, url):
    try:
        href = url.toString()
    except Exception:
        return
    if not href:
        return
    if href.startswith("copy-ssa:"):
        target = href[len("copy-ssa:") :].strip().lstrip("/")
        if target:
            window._copy_ssa_to_clipboard(target)
        return
    if href.startswith("derivadas:tree") or href.startswith("derivadas://tree"):
        current_ssa = getattr(window, "_details_current_ssa", None)
        _show_derivadas_tree_for_ssa(window, current_ssa)
        return
    if href.startswith("ssa-details:"):
        target = href[len("ssa-details:") :].strip().lstrip("/")
        if target:
            _open_details_dialog_for_ssa(window, target)
        return
    if href.startswith("ssa_details://"):
        target = href[len("ssa_details://") :].strip().lstrip("/")
        if target:
            _open_details_dialog_for_ssa(window, target)
        return
    if href.startswith("ssa:"):
        target = href[len("ssa:") :]
    elif href.startswith("ssa://"):
        target = href[len("ssa://") :]
    else:
        return
    target = target.strip().lstrip("/")
    if target:
        _jump_to_ssa(window, target, _allow_refilter=False)


def _resolve_current_db_path():
    try:
        from gui import gui_ssa as gui_ssa_module
    except Exception:
        return None
    db_path = getattr(gui_ssa_module, "DB_PATH", None)
    if isinstance(db_path, str) and db_path.strip():
        return db_path
    return None


def _get_derivadas_relations_info(window, numero_ssa):
    empty = {"has_data": False, "parents": [], "children": [], "descendants_count": 0}
    num_norm = _normalize_ssa_relation_value(numero_ssa)
    if not num_norm:
        return empty

    parents = []
    children = []
    descendants_count = 0

    db_path = _resolve_current_db_path()
    if db_path and os.path.exists(db_path):
        try:
            from armazenamento import derivadas_queries

            parents = derivadas_queries.get_parents(db_path, num_norm)
            children = derivadas_queries.get_children(db_path, num_norm)
            profile = derivadas_queries.get_hierarchy_profile(db_path, num_norm) or {}
            descendants_count = int(profile.get("descendants_count") or 0)
        except Exception as exc:
            logger.debug(
                "Falha ao ler relacoes de derivadas no DB para %s: %s", num_norm, exc
            )

    if not children:
        children = _get_derivadas_for_ssa(window, num_norm)
    else:
        children = [
            value
            for value in (_normalize_ssa_relation_value(raw) for raw in children)
            if value
        ]
    parents = [
        value
        for value in (_normalize_ssa_relation_value(raw) for raw in parents)
        if value
    ]
    if not parents:
        direct_parent = _get_direct_parent_for_series(_get_series_for_ssa(window, num_norm))
        if direct_parent:
            parents = [direct_parent]
    if descendants_count <= 0:
        descendants_count = len(children)

    has_data = bool(parents or children or descendants_count > 0)
    return {
        "has_data": has_data,
        "parents": parents,
        "children": children,
        "descendants_count": descendants_count,
    }


def _show_derivadas_tree_for_ssa(window, numero_ssa):
    _open_details_dialog_for_ssa(window, numero_ssa)


def _get_cached_derivadas_family_edges(window) -> list[tuple[str, str]]:
    source_df = getattr(window, "df_completo", None)
    if (
        not isinstance(source_df, pd.DataFrame)
        or source_df.empty
        or "numero_ssa" not in source_df.columns
        or "derivada_de" not in source_df.columns
    ):
        return []
    try:
        cache_owner = getattr(window, "cache_manager", None)
        cache_get = getattr(cache_owner, "get_cached_value", None)
        cache_put = getattr(cache_owner, "cache_value", None)
        has_cache_manager = callable(cache_get) and callable(cache_put)
        data_revision = getattr(window, "_data_revision", None)
        data_uuid = getattr(window, "_data_uuid", None)
        cache_enabled = data_uuid is not None
        row_count = len(source_df)
        cache_key = (id(source_df), row_count, data_revision, data_uuid)
        cached_edges = (
            cast(Any, cache_get)("details_derivadas_family_edges", cache_key)
            if cache_enabled and has_cache_manager
            else None
        )
        if isinstance(cached_edges, list):
            return cast(list[tuple[str, str]], cached_edges)

        edges: list[tuple[str, str]] = []
        seen_edges: set[tuple[str, str]] = set()
        number_series = _normalize_ssa_relation_series(source_df["numero_ssa"])
        parent_series = _normalize_ssa_relation_series(source_df["derivada_de"])
        pair_df = pd.DataFrame({"child": number_series, "parent": parent_series})
        pair_df = pair_df.dropna()
        pair_df = pair_df[
            pair_df["child"].astype(str).str.strip().ne("")
            & pair_df["parent"].astype(str).str.strip().ne("")
        ]
        for parent_value, child_value in pair_df[["parent", "child"]].itertuples(
            index=False, name=None
        ):
            parent_text = str(parent_value).strip()
            child_text = str(child_value).strip()
            if not parent_text or not child_text:
                continue
            edge = (parent_text, child_text)
            if edge not in seen_edges:
                seen_edges.add(edge)
                edges.append(edge)
        if cache_enabled and has_cache_manager:
            cast(Any, cache_put)(
                "details_derivadas_family_edges",
                cache_key,
                edges,
                max_entries=SSA_NORM_CACHE_MAX_ENTRIES,
            )
        return edges
    except Exception as exc:
        logger.debug("Falha ao montar cache local de familia de derivadas: %s", exc)
        return []


def _collect_derivadas_tree_data(window, numero_ssa):
    target = _normalize_ssa_relation_value(numero_ssa)
    empty = {
        "target": "",
        "parents": [],
        "children": [],
        "descendants": [],
        "ancestors": [],
        "family_roots": [],
        "target_status": "",
        "descendants_partial": False,
        "related": [],
        "direct_children_count": 0,
        "descendants_count": 0,
    }
    if not target:
        return empty

    parents = []
    children = []
    descendants = []
    ancestors = []
    profile = {}
    family_roots: list[str] = []
    family_descendants: list[dict[str, object]] = []
    descendants_partial = False

    db_path = _resolve_current_db_path()
    if db_path and os.path.exists(db_path):
        try:
            from armazenamento import derivadas_queries

            snapshot = derivadas_queries.get_ssa_hierarchy_snapshot(
                db_path,
                target,
                max_distance=None,
                max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
            )
            parents = list(snapshot.get("parents", []) or [])
            children = list(snapshot.get("children", []) or [])
            descendants = list(snapshot.get("descendants", []) or [])
            ancestors = list(snapshot.get("ancestors", []) or [])
            profile = cast(dict[str, object], snapshot.get("hierarchy_profile", {}) or {})
            family_roots = [
                value
                for value in (
                    _normalize_ssa_relation_value(raw)
                    for raw in cast(list[object], snapshot.get("family_roots", []) or [])
                )
                if value
            ]
            family_descendants = [
                cast(dict[str, object], raw)
                for raw in cast(
                    list[object], snapshot.get("family_descendants", []) or []
                )
                if isinstance(raw, dict)
            ]
            descendants_partial = bool(snapshot.get("family_truncated"))
        except Exception as exc:
            logger.debug(
                "Falha ao coletar arvore de derivadas no DB para %s: %s", target, exc
            )

    if not children:
        children = _get_derivadas_for_ssa(window, target)
    else:
        children = [
            value
            for value in (_normalize_ssa_relation_value(raw) for raw in children)
            if value
        ]
    parents = [
        value
        for value in (_normalize_ssa_relation_value(raw) for raw in parents)
        if value
    ]
    series_target = _get_series_for_ssa(window, target)
    if not parents:
        direct_parent = _get_direct_parent_for_series(series_target)
        if direct_parent:
            parents = [direct_parent]
    normalized_descendants = []
    for raw in descendants:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child = _normalize_ssa_relation_value(raw_map.get("ssa"))
        parent = _normalize_ssa_relation_value(raw_map.get("parent"))
        if not child:
            continue
        normalized_descendants.append(
            {
                **raw_map,
                "ssa": child,
                "parent": parent,
            }
        )
    descendants = normalized_descendants
    normalized_ancestors = []
    for raw in ancestors:
        if isinstance(raw, dict):
            raw_map = cast(dict[str, object], raw)
            ancestor_value = _normalize_ssa_relation_value(raw_map.get("ssa"))
            if not ancestor_value:
                continue
            normalized_ancestors.append({**raw_map, "ssa": ancestor_value})
            continue
        ancestor_value = _normalize_ssa_relation_value(raw)
        if ancestor_value:
            normalized_ancestors.append(ancestor_value)
    ancestors = normalized_ancestors
    def _ancestor_sort_key(entry):
        if not isinstance(entry, dict):
            return (0, _normalize_ssa_relation_value(entry))
        raw_map = cast(dict[str, object], entry)
        try:
            raw_distance = raw_map.get("min_distance")
            distance = raw_distance if isinstance(raw_distance, int) else 0
        except (TypeError, ValueError):
            distance = 0
        return (-distance, _normalize_ssa_relation_value(raw_map.get("ssa")))

    ancestors.sort(key=_ancestor_sort_key)
    if not family_roots and ancestors:
        root_distance = None
        for raw in ancestors:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            try:
                raw_distance = raw_map.get("min_distance")
                distance = raw_distance if isinstance(raw_distance, int) else 0
            except (TypeError, ValueError):
                distance = 0
            if root_distance is None:
                root_distance = distance
            if distance == root_distance:
                root_value = _normalize_ssa_relation_value(raw_map.get("ssa"))
                if root_value and root_value not in family_roots:
                    family_roots.append(root_value)
    if not family_roots:
        family_roots = list(dict.fromkeys(parents or [target]))

    if not family_descendants:
        try:
            from armazenamento.derivadas_queries import build_family_payload_from_edges

            local_edges = _get_cached_derivadas_family_edges(window)
            local_payload = build_family_payload_from_edges(
                target,
                local_edges,
                max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
                allow_relation_ids=normalize_numero_ssa_strict(target) is None,
            )
            if not parents:
                parents = list(local_payload.get("parents", []) or [])
            if not children:
                children = list(local_payload.get("children", []) or [])
            family_roots = [
                value
                for value in (
                    _normalize_ssa_relation_value(raw)
                    for raw in cast(
                        list[object], local_payload.get("family_roots", []) or []
                    )
                )
                if value
            ] or family_roots
            family_descendants = [
                cast(dict[str, object], raw)
                for raw in cast(
                    list[object],
                    local_payload.get("family_descendants", []) or [],
                )
                if isinstance(raw, dict)
            ]
            descendants_partial = bool(local_payload.get("family_truncated"))
        except Exception as exc:
            logger.debug(
                "Falha ao montar payload local de familia de derivadas para %s: %s",
                target,
                exc,
            )
    if family_descendants:
        descendants = family_descendants
    family_child_values = {
        _normalize_ssa_relation_value(raw.get("ssa"))
        for raw in family_descendants
        if isinstance(raw, dict)
    }
    render_family = bool(
        family_descendants
        and family_roots
        and (target in family_roots or target in family_child_values)
    )
    raw_direct_children_count = profile.get("direct_children_count")
    direct_children_count = (
        raw_direct_children_count
        if isinstance(raw_direct_children_count, int)
        else len(children)
    )
    raw_profile_descendants_count = profile.get("descendants_count")
    profile_descendants_count = (
        raw_profile_descendants_count
        if isinstance(raw_profile_descendants_count, int)
        else 0
    )
    if profile_descendants_count > 0:
        descendants_count = profile_descendants_count
    elif descendants_partial:
        descendants_count = len(descendants) + 1
    else:
        descendants_count = len(descendants) or len(children)
    related = _get_related_ssas_for_series(window, series_target)
    try:
        target_status = get_status_code(series_target.get("situacao"))
    except Exception as exc:
        logger.debug("Falha ao obter situacao alvo da arvore %s: %s", target, exc)
        target_status = ""
    return {
        "target": target,
        "parents": parents,
        "children": children,
        "descendants": descendants,
        "ancestors": ancestors,
        "family_roots": family_roots,
        "target_status": target_status,
        "descendants_partial": descendants_partial,
        "render_family": render_family,
        "related": related,
        "direct_children_count": direct_children_count,
        "descendants_count": descendants_count,
    }


def _build_derivadas_tree_html(
    window,
    numero_ssa,
    link_color=None,
    tree_font_pt=None,
    font_family=None,
    tree_data_override=None,
    ssa_index: Mapping[str, pd.Series] | None = None,
):
    if not link_color:
        roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
        link_color = (
            roles.get("accent") or roles.get("panel_text") or roles.get("label_color")
        )
    safe_link_color = str(link_color or "")
    data = (
        tree_data_override
        if isinstance(tree_data_override, dict)
        else _collect_derivadas_tree_data(window, numero_ssa)
    )
    target = _normalize_ssa_relation_value(data.get("target", ""))
    if not target:
        return ""

    allow_global_index = ssa_index is None
    if allow_global_index:
        ssa_index = _get_window_ssa_series_index(window)
    if ssa_index is None:
        ssa_index = {}
    target_status = str(data.get("target_status", "") or "").strip().upper()
    fallback_ssa_index: dict[str, pd.Series] | None = None
    candidate_ssas: set[str] = {target}
    existing_tree_ssas: set[str] = set()
    status_by_ssa: dict[str, str] = {}
    if target_status:
        status_by_ssa[target] = target_status

    def _remember_tree_candidate(raw) -> None:
        if isinstance(raw, dict):
            raw_map = cast(dict[str, object], raw)
            ssa = _normalize_ssa_relation_value(raw_map.get("ssa"))
            parent = _normalize_ssa_relation_value(raw_map.get("parent"))
            if parent:
                candidate_ssas.add(parent)
            status_hint = str(raw_map.get("situacao", "") or "").strip().upper()
        else:
            ssa = _normalize_ssa_relation_value(raw)
            status_hint = ""
        if not ssa:
            return
        candidate_ssas.add(ssa)
        if status_hint and ssa not in status_by_ssa:
            status_by_ssa[ssa] = status_hint

    for candidate_key in (
        "parents",
        "children",
        "descendants",
        "ancestors",
        "family_roots",
        "related",
    ):
        raw_candidates = data.get(candidate_key, [])
        if isinstance(raw_candidates, list):
            for raw_candidate in raw_candidates:
                _remember_tree_candidate(raw_candidate)

    def _hydrate_tree_candidates_from_df(df) -> None:
        remaining = candidate_ssas - existing_tree_ssas
        if (
            not remaining
            or df is None
            or df.empty
            or "numero_ssa" not in getattr(df, "columns", [])
        ):
            return
        try:
            normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
            if normalized_series.empty:
                return
            matches = normalized_series.isin(remaining)
            if not bool(matches.any()):
                return
            for idx_label, normalized in normalized_series[matches].items():
                normalized_text = str(normalized or "").strip()
                if not normalized_text:
                    continue
                existing_tree_ssas.add(normalized_text)
                if normalized_text in status_by_ssa or "situacao" not in df.columns:
                    continue
                matched = df.loc[idx_label]
                if isinstance(matched, pd.DataFrame):
                    matched = matched.iloc[0]
                try:
                    status_code = get_status_code(matched.get("situacao"))
                except Exception as exc:
                    logger.debug(
                        "Falha ao obter situacao da SSA %s no mapa local da arvore: %s",
                        normalized_text,
                        exc,
                    )
                    status_code = ""
                if status_code:
                    status_by_ssa[normalized_text] = status_code
                if len(existing_tree_ssas) >= len(candidate_ssas):
                    return
        except Exception as exc:
            logger.debug("Falha ao hidratar candidatos da arvore de derivadas: %s", exc)

    _hydrate_tree_candidates_from_df(getattr(window, "df_exibido", None))
    _hydrate_tree_candidates_from_df(getattr(window, "df_completo", None))

    def _ssa_link(value, *, status_hint: str | None = None):
        nonlocal fallback_ssa_index
        safe = _normalize_ssa_relation_value(value)
        if not safe:
            return html_module.escape(str(value))
        resolved_series = ssa_index.get(safe)
        if resolved_series is None and allow_global_index and fallback_ssa_index is None:
            fallback_ssa_index = _get_window_ssa_series_index(window)
        if resolved_series is None and fallback_ssa_index:
            resolved_series = fallback_ssa_index.get(safe)
        if (
            resolved_series is None
            and allow_global_index
            and (not fallback_ssa_index or len(fallback_ssa_index) <= DERIVADAS_GRAPH_MAX_DESCENDANTS)
        ):
            resolved_series = _get_series_for_ssa(window, safe)
        status_code = str(status_hint or "").strip().upper()
        if not status_code and safe == target:
            status_code = target_status
        if not status_code:
            status_code = status_by_ssa.get(safe, "")
        if not status_code and resolved_series is not None:
            try:
                status_code = get_status_code(resolved_series.get("situacao"))
            except Exception as exc:
                logger.debug("Falha ao obter situacao da SSA %s na arvore: %s", safe, exc)
        return _render_ssa_navigation_link(
            safe,
            link_color=safe_link_color,
            panel_mode=True,
            exists=resolved_series is not None or safe in existing_tree_ssas,
            status_hint=status_code,
        )

    def _render_entry(entry):
        if isinstance(entry, dict):
            ssa = str(entry.get("ssa", "")).strip()
            if not ssa:
                return ""
            status_hint = str(entry.get("situacao", "")).strip().upper()
            return _ssa_link(ssa, status_hint=status_hint)
        return _ssa_link(entry)

    def _append_line(lines, depth: int, rendered: str, *, current: bool = False):
        guide = ""
        for _ in range(depth):
            guide += (
                '<span style="display:inline-block; width:18px; '
                'text-align:center; opacity:0.55;">&#8942;</span>'
            )
        content = f"{guide}<span>{rendered}</span>"
        if current:
            content = (
                f'<span style="font-weight:700; color:{html_module.escape(safe_link_color)};">'
                f"{content}"
                "</span>"
            )
        lines.append(
            f'<div style="margin:0 0 6px 0; white-space:nowrap;">{content}</div>'
        )

    lines = []
    if tree_font_pt is None:
        tree_font_pt = DERIVADAS_DIALOG_TREE_FONT_PT
    if not font_family:
        font_family = MONO_FONT_FAMILY

    raw_ancestors_entries = data.get("ancestors", [])
    ancestors_entries = (
        list(cast(list[object], raw_ancestors_entries))
        if isinstance(raw_ancestors_entries, list)
        else []
    )
    if not ancestors_entries:
        raw_parent_entries = data.get("parents", [])
        ancestors_entries = (
            list(cast(list[object], raw_parent_entries))
            if isinstance(raw_parent_entries, list)
            else []
        )
    lineage: list[object] = []
    lineage_seen: set[str] = set()
    for raw in ancestors_entries:
        rendered = _render_entry(raw)
        normalized = _normalize_ssa_relation_value(
            cast(dict[str, object], raw).get("ssa") if isinstance(raw, dict) else raw
        )
        if not rendered or not normalized or normalized in lineage_seen:
            continue
        lineage_seen.add(normalized)
        lineage.append(raw)

    raw_descendants_entries = data.get("descendants", [])
    descendants_entries = (
        list(cast(list[object], raw_descendants_entries))
        if isinstance(raw_descendants_entries, list)
        else []
    )
    child_map: dict[str, list[object]] = {}
    descendants_entries_list = (
        list(cast(list[object], descendants_entries))
        if isinstance(descendants_entries, list)
        else []
    )
    for raw in descendants_entries_list:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child_value = _normalize_ssa_relation_value(raw_map.get("ssa"))
        parent_value = _normalize_ssa_relation_value(raw_map.get("parent"))
        if not child_value or not parent_value:
            continue
        child_map.setdefault(parent_value, []).append(raw)
    for child_values in child_map.values():
        child_values.sort(
            key=lambda entry: _normalize_ssa_relation_value(
                cast(dict[str, object], entry).get("ssa")
            )
            or ""
        )

    direct_children = list(data.get("children", []) or [])
    entry_by_ssa: dict[str, object] = {}
    for raw in [*lineage, *descendants_entries_list, *direct_children]:
        normalized = _normalize_ssa_relation_value(
            cast(dict[str, object], raw).get("ssa") if isinstance(raw, dict) else raw
        )
        if normalized and normalized not in entry_by_ssa:
            entry_by_ssa[normalized] = raw

    lines.append(
        f'<div style="font-family:{font_family}; font-size:{tree_font_pt:.2f}pt; line-height:1.85;">'
    )
    lines.append("<b>Derivadas:</b><br/>")
    raw_family_roots = data.get("family_roots", [])
    family_roots = (
        [
            value
            for value in (
                _normalize_ssa_relation_value(raw)
                for raw in cast(list[object], raw_family_roots)
            )
            if value
        ]
        if isinstance(raw_family_roots, list)
        else []
    )
    render_family = bool(data.get("render_family")) and bool(child_map) and bool(family_roots)

    if render_family:
        seen_family_nodes: set[str] = set()
        stack = [(root, 0) for root in reversed(family_roots)]
        while stack:
            raw_node, depth = stack.pop()
            safe_node = _normalize_ssa_relation_value(raw_node)
            if not safe_node or safe_node in seen_family_nodes:
                continue
            seen_family_nodes.add(safe_node)
            rendered = _render_entry(entry_by_ssa.get(safe_node, safe_node))
            if rendered:
                _append_line(lines, depth, rendered, current=safe_node == target)
            for raw_child in reversed(child_map.get(safe_node, [])):
                child_value = _normalize_ssa_relation_value(
                    cast(dict[str, object], raw_child).get("ssa")
                )
                if child_value and child_value not in seen_family_nodes:
                    stack.append((child_value, depth + 1))
    else:
        for raw in lineage:
            rendered = _render_entry(raw)
            if rendered:
                _append_line(lines, 0, rendered)
        _append_line(lines, len(lineage), _ssa_link(target), current=True)
        if direct_children:
            for raw in direct_children:
                rendered = _render_entry(raw)
                child_value = _normalize_ssa_relation_value(
                    raw.get("ssa") if isinstance(raw, dict) else raw
                )
                if not rendered or not child_value:
                    continue
                _append_line(lines, len(lineage) + 1, rendered)
                seen_child_descendants = {child_value}
                stack = [
                    (raw_child, len(lineage) + 2)
                    for raw_child in reversed(child_map.get(child_value, []))
                ]
                while stack:
                    raw_descendant, depth = stack.pop()
                    if not isinstance(raw_descendant, dict):
                        continue
                    raw_descendant_map = cast(dict[str, object], raw_descendant)
                    descendant_value = _normalize_ssa_relation_value(
                        raw_descendant_map.get("ssa")
                    )
                    rendered_descendant = _render_entry(raw_descendant)
                    if (
                        not descendant_value
                        or descendant_value in seen_child_descendants
                        or not rendered_descendant
                    ):
                        continue
                    seen_child_descendants.add(descendant_value)
                    _append_line(lines, depth, rendered_descendant)
                    for raw_child in reversed(child_map.get(descendant_value, [])):
                        stack.append((raw_child, depth + 1))
        else:
            _append_line(
                lines,
                len(lineage) + 1,
                '<span style="opacity:0.82;">Sem Derivadas</span>',
            )

    descendants_count = int(data.get("descendants_count", 0) or 0)
    hidden_descendants = max(0, descendants_count - len(descendants_entries))
    if bool(data.get("descendants_partial")) and hidden_descendants == 0:
        hidden_descendants = 1
    if hidden_descendants > 0:
        lines.append(
            f"{'&nbsp;' * ((len(lineage) + 1) * 4)}... (+{hidden_descendants})<br/>"
        )
    related_entries = data.get("related", [])
    if isinstance(related_entries, list) and related_entries:
        lines.append("<br/><b>Relacionadas:</b><br/>")
        for raw in related_entries:
            rendered = _render_entry(raw)
            if rendered:
                _append_line(lines, 1, rendered)

    lines.append("</div>")
    return "".join(lines)


def _build_derivadas_mermaid_text(data: Mapping[str, object]) -> str:
    target = _normalize_ssa_relation_value(data.get("target", ""))
    if not target:
        return ""

    def _node_id(value: str) -> str:
        if value.isdigit():
            return f"N{value}"
        stable_hash = hashlib.md5(
            value.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:12]
        return f"N_{stable_hash}"

    def _label(value: str) -> str:
        clean = str(value).replace('"', "'")
        return clean

    lines = ["flowchart LR"]
    lines.append(f'  {_node_id(target)}["{_label(target)}"]')
    edge_seen: set[tuple[str, str, bool]] = set()

    parents = data.get("parents", [])
    if isinstance(parents, list):
        for raw in parents:
            parent = _normalize_ssa_relation_value(raw)
            if not parent:
                continue
            edge = (parent, target, False)
            if edge in edge_seen:
                continue
            edge_seen.add(edge)
            lines.append(
                f'  {_node_id(parent)}["{_label(parent)}"] --> {_node_id(target)}'
            )

    children = data.get("children", [])
    if isinstance(children, list):
        for raw in children:
            child = _normalize_ssa_relation_value(raw)
            if not child:
                continue
            edge = (target, child, False)
            if edge in edge_seen:
                continue
            edge_seen.add(edge)
            lines.append(
                f'  {_node_id(target)} --> {_node_id(child)}["{_label(child)}"]'
            )

    descendants = data.get("descendants", [])
    if isinstance(descendants, list):
        for raw in descendants:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            ssa = _normalize_ssa_relation_value(raw_map.get("ssa", ""))
            parent = _normalize_ssa_relation_value(raw_map.get("parent", ""))
            if not ssa:
                continue
            if parent:
                edge = (parent, ssa, False)
                if edge in edge_seen:
                    continue
                edge_seen.add(edge)
                lines.append(
                    f'  {_node_id(parent)} --> {_node_id(ssa)}["{_label(ssa)}"]'
                )
            else:
                edge = (target, ssa, True)
                if edge in edge_seen:
                    continue
                edge_seen.add(edge)
                lines.append(
                    f'  {_node_id(target)} -.-> {_node_id(ssa)}["{_label(ssa)}"]'
                )
    related = data.get("related", [])
    if isinstance(related, list):
        for raw in related:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            related_ssa = _normalize_ssa_relation_value(raw_map.get("ssa", ""))
            if not related_ssa:
                continue
            edge = (target, related_ssa, True)
            if edge in edge_seen:
                continue
            edge_seen.add(edge)
            lines.append(
                f'  {_node_id(target)} -.-> {_node_id(related_ssa)}["{_label(related_ssa)}"]'
            )
    return "\n".join(lines)


def _build_derivadas_graph_html(
    window,
    data: Mapping[str, object],
    *,
    link_color: str,
    font_family: str,
) -> str:
    target = _normalize_ssa_relation_value(data.get("target"))
    if not target:
        return ""

    def _normalize_list(entries) -> list[str]:
        if not isinstance(entries, list):
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in entries:
            value = _normalize_ssa_relation_value(raw)
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    parents = _normalize_list(data.get("parents", []))
    children = _normalize_list(data.get("children", []))
    descendants_entries = data.get("descendants", [])
    descendants: list[dict[str, object]] = []
    if isinstance(descendants_entries, list):
        for raw in descendants_entries[:DERIVADAS_GRAPH_MAX_DESCENDANTS]:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            child = _normalize_ssa_relation_value(raw_map.get("ssa"))
            parent = _normalize_ssa_relation_value(raw_map.get("parent"))
            if not child:
                continue
            row: dict[str, object] = {"ssa": child, "parent": parent}
            if raw_map.get("relation_type") is not None:
                row["relation_type"] = raw_map.get("relation_type")
            if raw_map.get("relation_raw_label"):
                row["relation_raw_label"] = raw_map.get("relation_raw_label")
            descendants.append(row)

    nodes: set[str] = {target}
    edges: list[tuple[str, str]] = []
    dashed_edges: set[tuple[str, str]] = set()
    edge_seen: set[tuple[str, str]] = set()

    def _add_edge(source: str, target_node: str, *, dashed: bool = False) -> None:
        if not source or not target_node:
            return
        edge = (source, target_node)
        if edge in edge_seen:
            if dashed:
                dashed_edges.add(edge)
            return
        edge_seen.add(edge)
        edges.append(edge)
        nodes.add(source)
        nodes.add(target_node)
        if dashed:
            dashed_edges.add(edge)

    def _is_related_edge(row: Mapping[str, object]) -> bool:
        raw_label = str(row.get("relation_raw_label") or row.get("relacao") or "")
        label = raw_label.strip().casefold()
        if "derivad" in label:
            return False
        if label:
            return True
        raw_type = row.get("relation_type")
        if raw_type is None:
            return False
        try:
            return int(cast(Any, raw_type)) not in (0, 1)
        except (TypeError, ValueError):
            return False

    for parent in parents:
        _add_edge(parent, target)
    for child in children:
        _add_edge(target, child)
    for row in descendants:
        descendant = str(row.get("ssa", "") or "")
        parent = str(row.get("parent", "") or "")
        dashed = _is_related_edge(row)
        if parent:
            _add_edge(parent, descendant, dashed=dashed)
        else:
            _add_edge(target, descendant, dashed=True)
    related_entries = data.get("related", [])
    if isinstance(related_entries, list):
        for raw in related_entries:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            related_ssa = _normalize_ssa_relation_value(raw_map.get("ssa"))
            if related_ssa:
                _add_edge(target, related_ssa, dashed=True)

    positions: dict[str, tuple[float, float]] = {}
    node_w = DERIVADAS_GRAPH_NODE_WIDTH
    node_h = DERIVADAS_GRAPH_NODE_HEIGHT
    x_gap = DERIVADAS_GRAPH_X_GAP
    y_gap = DERIVADAS_GRAPH_Y_GAP
    margin = DERIVADAS_GRAPH_MARGIN
    raw_ancestors_entries = data.get("ancestors", [])
    ancestors_entries = (
        list(cast(list[object], raw_ancestors_entries))
        if isinstance(raw_ancestors_entries, list)
        else []
    )
    if not ancestors_entries:
        raw_parent_entries = data.get("parents", [])
        ancestors_entries = (
            list(cast(list[object], raw_parent_entries))
            if isinstance(raw_parent_entries, list)
            else []
        )
    lineage: list[str] = []
    lineage_seen: set[str] = set()
    for raw in ancestors_entries:
        normalized = _normalize_ssa_relation_value(
            cast(dict[str, object], raw).get("ssa") if isinstance(raw, dict) else raw
        )
        if not normalized or normalized in lineage_seen:
            continue
        lineage_seen.add(normalized)
        lineage.append(normalized)

    child_map: dict[str, list[str]] = {}
    descendants_entries_list = (
        list(cast(list[object], descendants_entries))
        if isinstance(descendants_entries, list)
        else []
    )
    for raw in descendants_entries_list:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child_value = _normalize_ssa_relation_value(raw_map.get("ssa"))
        parent_value = _normalize_ssa_relation_value(raw_map.get("parent"))
        if not child_value or not parent_value:
            continue
        child_map.setdefault(parent_value, []).append(child_value)
    for child_values in child_map.values():
        child_values.sort()

    ordered_nodes: list[tuple[str, int]] = []
    raw_family_roots = data.get("family_roots", [])
    family_roots = (
        [
            value
            for value in (
                _normalize_ssa_relation_value(raw)
                for raw in cast(list[object], raw_family_roots)
            )
            if value
        ]
        if isinstance(raw_family_roots, list)
        else []
    )
    render_family = bool(data.get("render_family")) and bool(child_map) and bool(family_roots)
    target_depth = len(lineage)

    def _append_family_graph_node(node: str, depth: int, seen: set[str]) -> None:
        if not node or node in seen:
            return
        seen.add(node)
        ordered_nodes.append((node, depth))
        for child_ssa in child_map.get(node, []):
            _append_family_graph_node(child_ssa, depth + 1, seen)

    if render_family:
        seen_family_nodes: set[str] = set()
        for root in family_roots:
            _append_family_graph_node(root, 0, seen_family_nodes)
        for node, depth in ordered_nodes:
            if node == target:
                target_depth = depth
                break
    else:
        for depth, node in enumerate(lineage):
            ordered_nodes.append((node, depth))
        target_depth = len(lineage)
        ordered_nodes.append((target, target_depth))

        seen_children: set[str] = set()

        def _append_descendant_nodes(parent_ssa: str, depth: int) -> None:
            for child_ssa in child_map.get(parent_ssa, []):
                if child_ssa in seen_children:
                    continue
                seen_children.add(child_ssa)
                ordered_nodes.append((child_ssa, depth))
                _append_descendant_nodes(child_ssa, depth + 1)

        for raw in children:
            child_ssa = _normalize_ssa_relation_value(
                raw.get("ssa") if isinstance(raw, dict) else raw
            )
            if not child_ssa or child_ssa in seen_children:
                continue
            seen_children.add(child_ssa)
            ordered_nodes.append((child_ssa, target_depth + 1))
            _append_descendant_nodes(child_ssa, target_depth + 2)

    if isinstance(related_entries, list):
        related_seen: set[str] = set()
        for raw in related_entries:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            related_ssa = _normalize_ssa_relation_value(raw_map.get("ssa"))
            if not related_ssa or related_ssa in related_seen:
                continue
            related_seen.add(related_ssa)
            ordered_nodes.append((related_ssa, target_depth + 1))

    for index, (node, depth) in enumerate(ordered_nodes):
        x = margin + depth * x_gap
        y = margin + index * y_gap
        positions[node] = (x, y)

    if not positions:
        return ""

    min_x = min(x - node_w / 2.0 for x, _ in positions.values())
    max_x = max(x + node_w / 2.0 for x, _ in positions.values())
    min_y = min(y - node_h / 2.0 for _, y in positions.values())
    max_y = max(y + node_h / 2.0 for _, y in positions.values())

    offset_x = margin - min_x
    offset_y = margin - min_y
    svg_width = int(max_x - min_x + margin * 2)
    svg_height = int(max_y - min_y + margin * 2)

    theme_roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
    text_color = pick_css_color(
        theme_roles.get("panel_text"),
        theme_roles.get("label_color"),
        fallback="#d0d0d0",
    )
    node_fill = pick_css_color(
        theme_roles.get("input_bg"),
        theme_roles.get("panel_bg"),
        fallback="#1f1f1f",
    )
    node_target_fill = "#69b7ff"
    node_stroke = pick_css_color(
        link_color,
        theme_roles.get("border"),
        fallback="#4a90e2",
    )

    def _node_font_size(value: str) -> float:
        usable_w = max(18.0, float(node_w) - 18.0)
        by_width = usable_w / max(1.0, len(value) * 0.56)
        by_height = max(10.0, float(node_h) * 0.56)
        return max(11.0, min(by_width, by_height, 15.5))

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" '
        f'height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        "<defs>",
        '<marker id="arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="1.7" orient="auto">',
        f'<polygon points="0 0, 4 1.7, 0 3.4" fill="{node_stroke}" />',
        "</marker>",
        "</defs>",
    ]

    lane_counters: dict[tuple[str, int], int] = {}

    def _compute_lane_x(source: str, x1: float, x2: float) -> float:
        direction = 1 if x2 >= x1 else -1
        lane_key = (source, direction)
        lane_index = lane_counters.get(lane_key, 0)
        lane_counters[lane_key] = lane_index + 1
        span = x2 - x1 if direction > 0 else x1 - x2
        max_offset = max(2.0, span - 2.0)
        lane_offset = min(max(2.0, float(lane_index + 1) * 3.0), max_offset)
        return x1 + lane_offset if direction > 0 else x1 - lane_offset

    for source, target_node in edges:
        source_pos = positions.get(source)
        target_pos = positions.get(target_node)
        if source_pos is None or target_pos is None:
            continue
        sx, sy = source_pos
        tx, ty = target_pos
        x1 = sx + node_w / 2.0 + offset_x
        x2 = tx - node_w / 2.0 + offset_x
        y1 = sy + offset_y
        y2 = ty + offset_y
        mid_x = _compute_lane_x(source, x1, x2)
        dash_attr = (
            ' stroke-dasharray="7 6"' if (source, target_node) in dashed_edges else ""
        )
        safe_source = html_module.escape(source, quote=True)
        safe_target_node = html_module.escape(target_node, quote=True)
        svg_lines.append(
            f'<path data-from="{safe_source}" data-to="{safe_target_node}" '
            f'd="M{x1:.1f},{y1:.1f} L{mid_x:.1f},{y1:.1f} '
            f'L{mid_x:.1f},{y2:.1f} L{x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{node_stroke}" stroke-width="0.9" '
            f'marker-end="url(#arrow)"{dash_attr} />'
        )

    for node, (x, y) in positions.items():
        x0 = x - node_w / 2.0 + offset_x
        y0 = y - node_h / 2.0 + offset_y
        fill = node_target_fill if node == target else node_fill
        safe_node = html_module.escape(node)
        svg_lines.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{node_w}" height="{node_h}" '
            f'rx="5" ry="5" fill="{fill}" stroke="{node_stroke}" stroke-width="0.8" />'
        )
        svg_lines.append(
            f'<text x="{(x + offset_x):.1f}" y="{(y + offset_y + 5):.1f}" text-anchor="middle" '
            f'font-family="{html_module.escape(font_family)}" font-size="{_node_font_size(node):.1f}" fill="{text_color}">{safe_node}</text>'
        )
    svg_lines.append("</svg>")

    raw_descendants_count = data.get("descendants_count", 0)
    if isinstance(raw_descendants_count, bool):
        descendants_count = int(raw_descendants_count)
    elif isinstance(raw_descendants_count, int):
        descendants_count = raw_descendants_count
    elif isinstance(raw_descendants_count, float):
        descendants_count = int(raw_descendants_count)
    elif isinstance(raw_descendants_count, str):
        try:
            descendants_count = int(raw_descendants_count.strip() or "0")
        except Exception:
            descendants_count = 0
    else:
        descendants_count = 0
    truncated = 0
    if isinstance(descendants_entries, list):
        truncated = max(0, descendants_count - len(descendants))
    if bool(data.get("descendants_partial")) and truncated == 0:
        truncated = 1
    summary = f"Nos: {len(nodes)} | Relacoes: {len(edges)} | Descendentes: {descendants_count}"
    if truncated > 0:
        summary = f"{summary} | Exibicao parcial de descendentes: +{truncated}"
    return (
        "<html><body style="
        f'"font-family:{html_module.escape(font_family)}; margin:6px;">'
        "<div style='margin-bottom:6px; font-weight:600;'>Grafo de derivadas</div>"
        f"{''.join(svg_lines)}"
        f"<div style='margin-top:8px; opacity:0.85;'>{html_module.escape(summary)}</div>"
        "</body></html>"
    )


def _extract_inline_svg_markup(graph_html: str) -> str:
    if not graph_html:
        return ""
    start = graph_html.find("<svg")
    end = graph_html.rfind("</svg>")
    if start < 0 or end < 0 or end < start:
        return ""
    return graph_html[start : end + len("</svg>")]


def _get_dialog_screen_geometry(widget):
    window_handle = widget.windowHandle()
    if window_handle is not None:
        screen = window_handle.screen()
        if screen is not None:
            return screen.availableGeometry()

    from PyQt6.QtWidgets import QApplication

    center = widget.frameGeometry().center()
    screen = QApplication.screenAt(center)
    if screen is not None:
        return screen.availableGeometry()

    screen = widget.screen()
    if screen is not None:
        return screen.availableGeometry()

    screen = QApplication.primaryScreen()
    if screen is not None:
        return screen.availableGeometry()
    return None


def _open_details_dialog_for_ssa(window, numero_ssa, series=None):
    target = _normalize_ssa_value(window, numero_ssa)
    if not target:
        return
    if series is not None:
        try:
            series_target = (
                _normalize_ssa_value(window, series.get("numero_ssa")) == target
            )
        except Exception:
            series_target = False
        if not series_target:
            series = None
    if series is None:
        series = _get_series_for_ssa(window, target)
    if series is None:
        return

    try:
        from PyQt6.QtCore import QByteArray, Qt
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import (
            QDialog,
            QFileDialog,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QMenu,
            QMessageBox,
            QPushButton,
            QSplitter,
            QTextBrowser,
            QToolButton,
            QVBoxLayout,
            QWidget,
        )
    except Exception:
        return
    qsvg_renderer_cls: type[object] | None
    try:
        from PyQt6.QtGui import QPainter, QPixmap
        from PyQt6.QtSvg import QSvgRenderer as _QSvgRenderer

        qsvg_renderer_cls = _QSvgRenderer
    except Exception as exc:
        qsvg_renderer_cls = None
        logger.debug("QSvgRenderer unavailable for derivadas graph rendering: %s", exc)

    dialog = QDialog(window)
    dialog.setWindowTitle(f"Detalhes da SSA #{target}")
    dialog.setMinimumWidth(DERIVADAS_DIALOG_MIN_WIDTH)
    dialog.setMinimumHeight(DERIVADAS_DIALOG_MIN_HEIGHT)

    root_layout = QVBoxLayout(dialog)
    details_tab_splitter = QSplitter(Qt.Orientation.Vertical)
    details_tab_splitter.setChildrenCollapsible(False)
    details_tab_splitter.setHandleWidth(DERIVADAS_SPLITTER_HANDLE_WIDTH)
    details_derivadas_splitter = QSplitter(Qt.Orientation.Horizontal)
    details_derivadas_splitter.setChildrenCollapsible(False)
    details_derivadas_splitter.setHandleWidth(DERIVADAS_SPLITTER_HANDLE_WIDTH)
    details_browser = _init_readonly_text_browser(
        QTextBrowser(), min_width=DERIVADAS_DIALOG_DETAILS_MIN_WIDTH
    )
    tree_tab_browser = _init_readonly_text_browser(
        QTextBrowser(),
        min_width=DERIVADAS_DIALOG_TREE_MIN_WIDTH,
        min_height=DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT,
    )
    tree_graph_label = None
    tree_graph_text_browser = None
    if qsvg_renderer_cls is not None:
        tree_graph_label = QLabel(dialog)
        tree_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tree_graph_label.setStyleSheet("border:none; background:transparent;")
        tree_graph_label.setMinimumHeight(DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT)
        tree_graph_browser = tree_graph_label
    else:
        tree_graph_text_browser = _init_readonly_text_browser(
            QTextBrowser(), min_height=DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT
        )
        tree_graph_browser = tree_graph_text_browser
    tree_graph_panel = QWidget(dialog)
    tree_graph_panel_layout = QGridLayout(tree_graph_panel)
    tree_graph_panel_layout.setContentsMargins(0, 0, 0, 0)
    tree_graph_panel_layout.setSpacing(0)
    tree_graph_panel_layout.addWidget(
        tree_graph_browser, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter
    )
    export_button = QToolButton(tree_graph_panel)
    export_button.setText("Exportar")
    export_button.setAutoRaise(True)
    export_button.setToolTip("Exportar grafo em PNG, SVG ou Mermaid")
    tree_graph_panel_layout.addWidget(
        export_button,
        0,
        0,
        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    )
    try:
        link_color = window.palette().color(QPalette.ColorRole.Highlight).name()
    except Exception:
        roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
        link_color = pick_css_color(
            roles.get("accent"),
            roles.get("panel_text"),
            roles.get("label_color"),
            fallback="#4a90e2",
        )

    current_target = {"ssa": target}
    export_state = {"svg": "", "mermaid": "", "target": target}
    dialog_font_pt = DERIVADAS_DIALOG_DETAILS_FONT_PT
    dialog_label_font_pt = DERIVADAS_DIALOG_LABEL_FONT_PT
    dialog_tree_font_pt = DERIVADAS_DIALOG_TREE_FONT_PT
    dialog_font_family = MONO_FONT_FAMILY
    try:
        base_font = window.font()
        size = base_font.pointSizeF()
        if size <= 0:
            size = float(base_font.pointSize())
        if size > 0:
            dialog_font_pt = size
            dialog_label_font_pt = size
            dialog_tree_font_pt = size
        family = str(base_font.family() or "").strip()
        if family:
            dialog_font_family = family
    except Exception as exc:
        logger.debug(
            "Falha ao obter fonte base da UI para dialogo de detalhes: %s", exc
        )

    def _render_graph_pixmap(graph_svg: str) -> bool:
        if tree_graph_label is None or qsvg_renderer_cls is None or not graph_svg:
            return False
        renderer = qsvg_renderer_cls(QByteArray(graph_svg.encode("utf-8")))
        default_size = renderer.defaultSize()
        natural_w = max(1, int(default_size.width()))
        natural_h = max(1, int(default_size.height()))
        available_w = max(120, tree_graph_panel.width() - 24)
        available_h = max(120, tree_graph_panel.height() - 24)
        scale = min(1.0, available_w / natural_w, available_h / natural_h)
        render_w = max(1, int(natural_w * scale))
        render_h = max(1, int(natural_h * scale))
        pixmap = QPixmap(render_w, render_h)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        tree_graph_label.setPixmap(pixmap)
        tree_graph_label.setFixedSize(pixmap.size())
        tree_graph_label.setToolTip("")
        return True

    def _render_target(ssa_target, resolved_series=None):
        normalized = _normalize_ssa_value(window, ssa_target)
        if not normalized:
            return False
        if resolved_series is not None:
            try:
                matches_target = (
                    _normalize_ssa_value(window, resolved_series.get("numero_ssa"))
                    == normalized
                )
            except Exception:
                matches_target = False
            if not matches_target:
                resolved_series = None
        series_target = resolved_series
        if series_target is None:
            series_target = _get_series_for_ssa(window, normalized)
        if series_target is None:
            return False
        ssa_index: dict[str, pd.Series] = {}
        current_target["ssa"] = normalized
        export_state["target"] = normalized
        tree_data = _collect_derivadas_tree_data(window, normalized)
        html_details = _format_details_html(
            window,
            series_target,
            highlight_search_terms=True,
            font_size_pt=dialog_font_pt,
            linkify=True,
            label_font_size_pt=dialog_label_font_pt,
            font_family=dialog_font_family,
            ssa_index=ssa_index,
        )
        details_browser.setHtml(html_details)
        tree_html = _build_derivadas_tree_html(
            window,
            normalized,
            link_color=link_color,
            tree_font_pt=dialog_tree_font_pt,
            font_family=dialog_font_family,
            tree_data_override=tree_data,
            ssa_index=ssa_index,
        )
        mermaid_text = _build_derivadas_mermaid_text(tree_data)
        graph_html = _build_derivadas_graph_html(
            window,
            tree_data,
            link_color=link_color,
            font_family=dialog_font_family,
        )
        graph_svg = _extract_inline_svg_markup(graph_html)
        export_state["svg"] = graph_svg
        export_state["mermaid"] = mermaid_text
        if tree_graph_label is not None:
            if graph_svg and _render_graph_pixmap(graph_svg):
                pass
            else:
                tree_graph_label.setText("Grafo de derivadas indisponivel.")
                tree_graph_label.setPixmap(QPixmap())
                tree_graph_label.setToolTip("Grafo de derivadas indisponivel.")
        elif graph_html and tree_graph_text_browser is not None:
            tree_graph_text_browser.setHtml(graph_html)
        else:
            if tree_graph_text_browser is None:
                logger.warning(
                    "Widget de grafo de derivadas ausente para %s", normalized
                )
                return False
            tree_graph_text_browser.setPlainText("Grafo de derivadas indisponivel.")
        if tree_html:
            tree_tab_browser.setHtml(tree_html)
        else:
            tree_tab_browser.setPlainText("Arvore de derivadas indisponivel.")
        return True

    def _export_target_basename() -> str:
        safe_target = str(export_state["target"]).strip() or "desconhecida"
        return f"derivadas_{safe_target}"

    def _export_graph_png() -> None:
        default_name = f"{_export_target_basename()}.png"
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Exportar grafo em PNG",
            default_name,
            "PNG (*.png)",
        )
        if not path:
            return
        pixmap = tree_graph_browser.grab()
        if pixmap.isNull():
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Grafo indisponivel para exportacao em PNG.",
            )
            return
        if not pixmap.save(path, "PNG"):
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Falha ao salvar o arquivo PNG.",
            )

    def _export_graph_svg() -> None:
        graph_svg = str(export_state["svg"] or "")
        if not graph_svg:
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Grafo indisponivel para exportacao em SVG.",
            )
            return
        default_name = f"{_export_target_basename()}.svg"
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Exportar grafo em SVG",
            default_name,
            "SVG (*.svg)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(graph_svg)
        except OSError as exc:
            logger.warning("Falha ao exportar grafo SVG: %s", exc)
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Falha ao salvar o arquivo SVG.",
            )

    def _export_graph_mermaid() -> None:
        mermaid_text = str(export_state["mermaid"] or "")
        if not mermaid_text:
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Mermaid indisponivel para exportacao.",
            )
            return
        default_name = f"{_export_target_basename()}.mmd"
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Exportar Mermaid",
            default_name,
            "Mermaid (*.mmd);;Texto (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(mermaid_text)
        except OSError as exc:
            logger.warning("Falha ao exportar Mermaid: %s", exc)
            QMessageBox.warning(
                dialog,
                "Exportacao",
                "Falha ao salvar o arquivo Mermaid.",
            )

    def _show_graph_export_menu(global_pos) -> None:
        menu = QMenu(dialog)
        menu.addAction("Exportar PNG", _export_graph_png)
        menu.addAction("Exportar SVG", _export_graph_svg)
        menu.addAction("Exportar Mermaid", _export_graph_mermaid)
        menu.exec(global_pos)

    def _refresh_graph_after_resize() -> None:
        graph_svg = str(export_state["svg"] or "")
        if graph_svg:
            _render_graph_pixmap(graph_svg)

    def _handle_dialog_anchor(url):
        try:
            href = url.toString()
        except Exception:
            return
        if not href:
            return
        if href.startswith("ssa-panel:"):
            target_href = href[len("ssa-panel:") :].strip().lstrip("/")
            _render_target(target_href)
            return
        if href.startswith("copy-ssa:"):
            target_href = href[len("copy-ssa:") :].strip().lstrip("/")
            if target_href:
                window._copy_ssa_to_clipboard(target_href)
            return
        if href.startswith("ssa-details:"):
            target_href = href[len("ssa-details:") :].strip().lstrip("/")
            _render_target(target_href)
            return
        if href.startswith("ssa_details://"):
            target_href = href[len("ssa_details://") :].strip().lstrip("/")
            _render_target(target_href)
            return
        if href.startswith("ssa:"):
            target_href = href[len("ssa:") :].strip().lstrip("/")
            _render_target(target_href)
            return
        if href.startswith("derivadas:tree") or href.startswith("derivadas://tree"):
            _render_target(current_target["ssa"])

    details_browser.anchorClicked.connect(_handle_dialog_anchor)
    tree_tab_browser.anchorClicked.connect(_handle_dialog_anchor)
    if tree_graph_text_browser is not None:
        tree_graph_text_browser.anchorClicked.connect(_handle_dialog_anchor)
    tree_graph_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    tree_graph_browser.customContextMenuRequested.connect(
        lambda pos: _show_graph_export_menu(tree_graph_browser.mapToGlobal(pos))
    )
    export_button.clicked.connect(
        lambda: _show_graph_export_menu(
            export_button.mapToGlobal(export_button.rect().bottomRight())
        )
    )
    if not _render_target(target, resolved_series=series):
        return

    details_tab_splitter.addWidget(details_browser)
    details_derivadas_splitter.addWidget(tree_tab_browser)
    details_derivadas_splitter.addWidget(tree_graph_panel)
    details_derivadas_splitter.setStretchFactor(0, DERIVADAS_DIALOG_RATIO_LEFT)
    details_derivadas_splitter.setStretchFactor(1, DERIVADAS_DIALOG_RATIO_RIGHT)
    details_derivadas_splitter.setSizes(
        [DERIVADAS_DIALOG_RATIO_LEFT * 10, DERIVADAS_DIALOG_RATIO_RIGHT * 10]
    )
    details_tab_splitter.addWidget(details_derivadas_splitter)
    details_tab_splitter.setStretchFactor(0, 1)
    details_tab_splitter.setStretchFactor(1, 1)
    details_tab_splitter.setSizes([470, DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT])

    root_layout.addWidget(details_tab_splitter)

    close_button = QPushButton("Fechar")
    close_button.setMinimumWidth(180)
    close_button.setMaximumWidth(240)
    close_button.clicked.connect(dialog.accept)
    close_row = QHBoxLayout()
    close_row.addStretch(1)
    close_row.addWidget(close_button)
    close_row.addStretch(1)
    root_layout.addLayout(close_row)
    screen_geometry = _get_dialog_screen_geometry(window)
    if screen_geometry is not None:
        safe_width = max(640, screen_geometry.width() - 24)
        safe_height = max(480, screen_geometry.height() - 24)
        window_height = 0
        try:
            window_height = int(window.height())
        except Exception as exc:
            logger.debug("Falha ao ler altura da janela principal: %s", exc)
        desired_height = safe_height
        if window_height > 0:
            desired_height = min(
                max(int(window_height * 0.72), DERIVADAS_DIALOG_MIN_HEIGHT),
                safe_height,
            )
        dialog.setMinimumSize(
            min(DERIVADAS_DIALOG_MIN_WIDTH, safe_width),
            min(DERIVADAS_DIALOG_MIN_HEIGHT, safe_height),
        )
        dialog.setMaximumSize(safe_width, safe_height)
        current_size = dialog.sizeHint()
        target_width = min(
            max(current_size.width(), DERIVADAS_DIALOG_MIN_WIDTH), safe_width
        )
        target_height = desired_height
        if (
            target_width != current_size.width()
            or target_height != current_size.height()
        ):
            dialog.resize(target_width, target_height)
        bottom_height = min(
            max(
                DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT,
                int(target_height * 0.26),
            ),
            max(0, target_height - 240),
        )
        details_tab_splitter.setSizes(
            [max(0, target_height - bottom_height), bottom_height]
        )
    if tree_graph_label is not None:
        QTimer.singleShot(0, _refresh_graph_after_resize)
    dialog.exec()


def _store_window_filter_state(window, reason: str) -> None:
    try:
        store_state = getattr(window, "_safe_store_last_filter_state", None)
        if callable(store_state):
            store_state(reason)
        else:
            window._store_last_filter_state()
    except Exception as exc:
        logger.warning("Falha ao salvar estado de filtros (%s): %s", reason, exc)


def _filter_by_derivadas(window, numero_ssa):
    num_norm = _normalize_ssa_relation_value(numero_ssa)
    if not num_norm:
        return
    current_value = str(
        getattr(window, "_active_column_filters", {}).get("derivada_de", "") or ""
    ).strip()
    if current_value != num_norm:
        _store_window_filter_state(window, "filter_by_derivadas")
    window._last_derivada_origem = _normalize_ssa_value(window, num_norm) or num_norm
    window._active_column_filters["derivada_de"] = num_norm
    try:
        window._build_column_filters_panel()
    except Exception as exc:
        logger.warning(
            "Falha ao reconstruir painel de filtros ao filtrar por derivadas: %s", exc
        )
    window._refresh_after_filter_change()


def _clear_derivadas_filter(window):
    if "derivada_de" in window._active_column_filters:
        _store_window_filter_state(window, "clear_derivadas_filter")
        window._active_column_filters.pop("derivada_de", None)
    try:
        window._build_column_filters_panel()
    except Exception as exc:
        logger.warning(
            "Falha ao reconstruir painel de filtros ao limpar filtro de derivadas: %s",
            exc,
        )
    window._refresh_after_filter_change()
    if window._last_derivada_origem:
        _jump_to_ssa(window, window._last_derivada_origem, _allow_refilter=False)
        window._last_derivada_origem = None
