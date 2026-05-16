# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import math
import os
from typing import Any, Mapping, cast

import pandas as pd

from gui.helpers.formatting_helpers import highlight_text
from gui.helpers.theme_helpers import pick_css_color
from gui.qt_stubs import QTimer
from gui.ssa import details_data_provider
from gui.ssa import details_derivadas_model
from gui.ssa.details_display_config import DetailsDisplayConfig
from gui.ssa.details_graph_export import (
    DetailsGraphExportController,
    load_svg_render_dependencies,
    render_graph_svg_pixmap,
)
from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from shared.ssa_status import format_status_display, get_status_code
from utils.formatting import format_cell
from utils.robust_logging import get_robust_logger
from utils.themes import get_theme_roles

logger = get_robust_logger().get_logger(__name__, "gui")


DETAILS_CONFIG = DetailsDisplayConfig()
HIDDEN_DETAIL_FIELDS = {"id", "derivada_de"}
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
    DETAILS_CONFIG.update(
        details_dialog_font_size=details_dialog_font_size,
        details_dialog_table_padding=details_dialog_table_padding,
        details_dialog_border_color=details_dialog_border_color,
        detail_field_priority=detail_field_priority,
        detail_display_overrides=detail_display_overrides,
        highlight_background_color=highlight_background_color,
        highlight_font_weight=highlight_font_weight,
        mono_font_family=mono_font_family,
    )


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
    bg = getattr(window, "_highlight_bg_color", DETAILS_CONFIG.highlight_background_color)
    fg = getattr(window, "_highlight_text_color", DETAILS_CONFIG.highlight_text_color)
    weight = getattr(window, "_highlight_font_weight", DETAILS_CONFIG.highlight_font_weight)
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
        font_size_pt = DETAILS_CONFIG.details_dialog_font_size
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
            return (0, DETAILS_CONFIG.field_priority.index(col))
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
        display_name = DETAILS_CONFIG.display_overrides.get(
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
            f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
            f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
            f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
            f"{display_name_html}:</td>"
            f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
            f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
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
            if isinstance(ssa_index, dict):
                _hydrate_ssa_index_candidates(
                    window,
                    cast(dict[str, pd.Series], ssa_index),
                    derived_list,
                )
            for item in derived_list:
                href = _normalize_ssa_value(window, item)
                exists = False
                if href:
                    cached_exists = derived_exists_cache.get(href)
                    if cached_exists is None:
                        resolved_series = ssa_index.get(href)
                        if resolved_series is None and allow_global_index:
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
            f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
            f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
            f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
            f"{html_module.escape(label)}:</td>"
            f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
            f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
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
            related_exists = bool(item.get("exists", False))
            rendered_items.append(
                _render_ssa_navigation_link(
                    related_ssa,
                    link_color=link_color,
                    panel_mode=False,
                    exists=related_exists,
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
                f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
                f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
                f'font-weight: bold; font-size: {label_font_size_pt}pt; vertical-align: top;">'
                f"{html_module.escape(label)}:</td>"
                f'<td style="padding: {DETAILS_CONFIG.table_padding}px; '
                f"border-bottom: 1px solid {DETAILS_CONFIG.border_color}; "
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
            if pd.isna(raw) or not math.isfinite(raw):
                return ""
            if raw.is_integer():
                raw = f"{raw:.0f}"
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
    if text.casefold() in ("nan", "none", "nat", "<na>"):
        return ""
    if text.isdigit():
        # Compat branch: GUI tests and local temporary IDs can still be short numeric.
        return text
    if text and all(ch.isdigit() or ch in ".- " for ch in text):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return digits
    return ""


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
        return pd.Series([""] * len(series), index=series.index, dtype="object")


def _normalize_ssa_relation_value(value) -> str:
    if _is_missing_scalar(value):
        return ""
    return details_derivadas_model.normalize_relation_value(value)


def _is_missing_scalar(value) -> bool:
    if value is None:
        return True
    try:
        if not pd.api.types.is_scalar(value):
            return False
        return bool(pd.isna(value))
    except Exception as exc:
        logger.debug("Falha ao avaliar valor escalar ausente: %s", exc)
        return False


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
        valid_series = normalized_series.astype("string").fillna("").str.strip()
        valid_series = valid_series[valid_series.ne("")]
        unique_series = valid_series[~valid_series.duplicated()]
        if unique_series.empty:
            return lookup
        first_rows = df.loc[unique_series.index]
        if isinstance(first_rows, pd.Series):
            first_rows = first_rows.to_frame().T
        for normalized, (_, matched) in zip(unique_series.to_list(), first_rows.iterrows()):
            normalized_text = str(normalized or "").strip()
            if not normalized_text:
                continue
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


def _hydrate_ssa_index_candidates(
    window,
    ssa_index: dict[str, pd.Series],
    candidates: list[str],
) -> None:
    resolved = _resolve_ssa_series_candidates(window, candidates, existing=ssa_index)
    ssa_index.update(resolved)


def _resolve_ssa_series_candidates(
    window,
    candidates,
    *,
    existing: Mapping[str, pd.Series] | None = None,
) -> dict[str, pd.Series]:
    resolved: dict[str, pd.Series] = {}
    remaining = {
        normalized
        for normalized in (
            _normalize_ssa_relation_value(candidate) for candidate in candidates
        )
        if normalized
    }
    if existing:
        resolved.update(
            {
                key: value
                for key, value in existing.items()
                if key in remaining and value is not None
            }
        )
        remaining.difference_update(resolved.keys())
    if not remaining:
        return resolved

    def hydrate_from_df(df) -> None:
        nonlocal remaining
        if (
            not remaining
            or df is None
            or df.empty
            or "numero_ssa" not in getattr(df, "columns", [])
        ):
            return
        normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
        if normalized_series.empty:
            return
        matches = normalized_series.isin(remaining)
        if not bool(matches.any()):
            return
        matched_normalized = normalized_series[matches]
        matched_rows = df.loc[matched_normalized.index]
        if isinstance(matched_rows, pd.Series):
            matched_rows = matched_rows.to_frame().T
        for normalized_value, (_, matched) in zip(
            matched_normalized.to_list(), matched_rows.iterrows()
        ):
            key = str(normalized_value or "").strip()
            if not key or key in resolved:
                continue
            resolved[key] = matched
        remaining.difference_update(resolved.keys())

    hydrate_from_df(getattr(window, "df_exibido", None))
    hydrate_from_df(getattr(window, "df_completo", None))
    return resolved


def _get_details_db_signature():
    db_path = _resolve_current_db_path()
    return details_data_provider.get_db_mtime(db_path)


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
    _schedule_details_update(window, series)


def _schedule_details_update(window, series) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        _update_details_from_series(window, series)
        return
    timer = getattr(window, "_details_update_timer", None)
    if timer is None:
        timer = QTimer(window)
        timer.setSingleShot(True)
        timer.setInterval(80)
        window._details_update_timer = timer

        def _flush_pending_details_update() -> None:
            pending_series = getattr(window, "_pending_details_series", None)
            window._pending_details_series = None
            _update_details_from_series(window, pending_series)

        timer.timeout.connect(_flush_pending_details_update)
    window._pending_details_series = series
    timer.start()


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
            return (0, DETAILS_CONFIG.field_priority.index(col))
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
        display_name = DETAILS_CONFIG.display_overrides.get(
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
        return _get_cached_derivadas_children_by_parent(window).get(num_norm, [])
    except Exception as exc:
        logger.debug("Falha ao coletar derivadas para SSA %s: %s", numero_ssa, exc)
        return []


def _get_related_ssas_for_series(
    window, series, *, ssa_index: Mapping[str, pd.Series] | None = None
) -> list[dict[str, str]]:
    if series is None:
        return []
    relation_value = series.get("relacao", "")
    relation_label = (
        "" if _is_missing_scalar(relation_value) else str(relation_value).strip()
    )
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
            if not _is_missing_scalar(status_value):
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


def _find_series_position_by_ssa(window, df, target: str):
    if df is None or df.empty or "numero_ssa" not in df.columns:
        return None, None
    try:
        normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
        if normalized_series.empty:
            return None, None
        matches = normalized_series.eq(target)
        if not bool(matches.any()):
            return None, None
        positions = matches.to_numpy().nonzero()[0]
        if len(positions) == 0:
            return None, None
        position = int(positions[0])
        matched = df.iloc[position]
        if isinstance(matched, pd.DataFrame):
            matched = matched.iloc[0]
        return position, matched
    except Exception as exc:
        logger.debug("Falha ao localizar SSA %s em dataframe: %s", target, exc)
        return None, None


def _jump_to_ssa(window, numero_ssa, *, _allow_refilter=True):
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return
    try:
        pos = None
        pos, _matched_series = _find_series_position_by_ssa(
            window, getattr(window, "df_exibido", None), num_norm
        )
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
            pos, _matched_series = _find_series_position_by_ssa(
                window, getattr(window, "df_exibido", None), num_norm
            )
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

    _position, match = _find_series_position_by_ssa(
        window, getattr(window, "df_exibido", None), target
    )
    if match is not None:
        return match
    _position, match = _find_series_position_by_ssa(
        window, getattr(window, "df_completo", None), target
    )
    return match


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
    return details_data_provider.resolve_current_db_path()


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
        ordered_pairs = pair_df[["parent", "child"]]
        for row in ordered_pairs.itertuples(index=False):
            parent_text = str(row.parent).strip()
            child_text = str(row.child).strip()
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


def _get_cached_derivadas_children_by_parent(window) -> dict[str, list[str]]:
    try:
        edges = _get_cached_derivadas_family_edges(window)
        cache_owner = getattr(window, "cache_manager", None)
        cache_get = getattr(cache_owner, "get_cached_value", None)
        cache_put = getattr(cache_owner, "cache_value", None)
        has_cache_manager = callable(cache_get) and callable(cache_put)
        cache_key = (id(edges), len(edges))
        if has_cache_manager:
            cached_map = cast(Any, cache_get)(
                "details_derivadas_children_by_parent", cache_key
            )
            if isinstance(cached_map, dict):
                return cast(dict[str, list[str]], cached_map)

        children_by_parent: dict[str, list[str]] = {}
        seen_by_parent: dict[str, set[str]] = {}
        for parent_value, child_value in edges:
            if not parent_value or not child_value:
                continue
            seen = seen_by_parent.setdefault(parent_value, set())
            if child_value in seen:
                continue
            seen.add(child_value)
            children_by_parent.setdefault(parent_value, []).append(child_value)
        if has_cache_manager:
            cast(Any, cache_put)(
                "details_derivadas_children_by_parent",
                cache_key,
                children_by_parent,
                max_entries=SSA_NORM_CACHE_MAX_ENTRIES,
            )
        return children_by_parent
    except Exception as exc:
        logger.debug("Falha ao montar mapa local de derivadas por pai: %s", exc)
        return {}


def _derivadas_frame_cache_token(window) -> object:
    df = getattr(window, "df_completo", None)
    if df is None or getattr(df, "empty", True):
        return ("empty", 0)
    data_uuid = getattr(window, "_data_uuid", None)
    revision = getattr(window, "_data_revision", None)
    if data_uuid is not None and revision is not None:
        return ("revision", revision, tuple(getattr(df, "shape", (0, 0))))
    columns = [
        column
        for column in ("numero_ssa", "derivada_de", "situacao")
        if column in getattr(df, "columns", [])
    ]
    if columns:
        try:
            relation_hash = int(
                pd.util.hash_pandas_object(
                    df.loc[:, columns].astype("string").fillna(""),
                    index=False,
                ).sum()
            )
            return ("content", tuple(getattr(df, "shape", (0, 0))), relation_hash)
        except Exception as exc:
            logger.debug("Falha ao calcular assinatura local de derivadas: %s", exc)
    return ("identity", id(df), tuple(getattr(df, "shape", (0, 0))))


def _collect_derivadas_tree_data(window, numero_ssa):
    target = _normalize_ssa_relation_value(numero_ssa)
    if not target:
        return details_derivadas_model.empty_tree_data()

    db_path = _resolve_current_db_path()
    db_mtime = details_data_provider.get_db_mtime(db_path)
    data_uuid = getattr(window, "_data_uuid", None)
    cache_owner = getattr(window, "cache_manager", None)
    cache_get = getattr(cache_owner, "get_cached_value", None)
    cache_put = getattr(cache_owner, "cache_value", None)
    data_token = data_uuid if data_uuid is not None else _derivadas_frame_cache_token(window)
    cache_key = (db_path, db_mtime, data_token, target)
    if callable(cache_get):
        cached = cast(Any, cache_get)("details_derivadas_tree_data", cache_key)
        if isinstance(cached, dict):
            return cached

    snapshot = details_data_provider.load_derivadas_snapshot(
        db_path,
        target,
        max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
    )
    series_target = _get_series_for_ssa(window, target)
    local_payload = None
    if not snapshot or not snapshot.get("family_descendants"):
        local_edges = _get_cached_derivadas_family_edges(window)
        local_payload = details_data_provider.build_local_family_payload(
            target,
            local_edges,
            max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
        )
    related = _get_related_ssas_for_series(window, series_target)
    try:
        target_status = get_status_code(series_target.get("situacao"))
    except Exception as exc:
        logger.debug("Falha ao obter situacao alvo da arvore %s: %s", target, exc)
        target_status = ""
    tree_data = details_derivadas_model.normalize_tree_data(
        target=target,
        snapshot=snapshot,
        fallback_children=_get_derivadas_for_ssa(window, target),
        direct_parent=_get_direct_parent_for_series(series_target),
        local_payload=local_payload,
        related=related,
        target_status=target_status,
    )
    if callable(cache_put):
        cast(Any, cache_put)("details_derivadas_tree_data", cache_key, tree_data)
    return tree_data


def _build_derivadas_link_state(
    window,
    data: Mapping[str, object],
    target: str,
    *,
    ssa_index: Mapping[str, pd.Series] | None = None,
):
    target_status = str(data.get("target_status", "") or "").strip().upper()
    candidate_ssas: set[str] = {target}
    existing_tree_ssas: set[str] = set()
    status_by_ssa: dict[str, str] = {}
    if target_status:
        status_by_ssa[target] = target_status

    def remember_candidate(raw) -> None:
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
                remember_candidate(raw_candidate)

    resolved_candidates = _resolve_ssa_series_candidates(
        window, candidate_ssas, existing=ssa_index
    )
    for candidate, resolved_series in resolved_candidates.items():
        existing_tree_ssas.add(candidate)
        if candidate in status_by_ssa:
            continue
        try:
            status_code = get_status_code(resolved_series.get("situacao"))
        except Exception as exc:
            logger.debug(
                "Falha ao obter situacao da SSA %s pelo indice de detalhes: %s",
                candidate,
                exc,
            )
            status_code = ""
        if status_code:
            status_by_ssa[candidate] = status_code
    return status_by_ssa, existing_tree_ssas


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
    status_by_ssa, existing_tree_ssas = _build_derivadas_link_state(
        window, data, target, ssa_index=ssa_index
    )

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
        font_family = DETAILS_CONFIG.mono_font_family

    tree_model = details_derivadas_model.build_tree_render_model(data)
    if tree_model is None:
        return ""

    lines.append(
        f'<div style="font-family:{font_family}; font-size:{tree_font_pt:.2f}pt; line-height:1.85;">'
    )
    lines.append("<b>Derivadas:</b><br/>")

    if tree_model.render_family:
        seen_family_nodes: set[str] = set()
        stack = [(root, 0) for root in reversed(tree_model.family_roots)]
        while stack:
            raw_node, depth = stack.pop()
            safe_node = _normalize_ssa_relation_value(raw_node)
            if not safe_node or safe_node in seen_family_nodes:
                continue
            seen_family_nodes.add(safe_node)
            rendered = _render_entry(tree_model.entry_by_ssa.get(safe_node, safe_node))
            if rendered:
                _append_line(lines, depth, rendered, current=safe_node == target)
            for raw_child in reversed(tree_model.child_map.get(safe_node, [])):
                child_value = _normalize_ssa_relation_value(
                    cast(dict[str, object], raw_child).get("ssa")
                    if isinstance(raw_child, dict)
                    else raw_child
                )
                if child_value and child_value not in seen_family_nodes:
                    stack.append((child_value, depth + 1))
    else:
        for raw in tree_model.lineage:
            rendered = _render_entry(raw)
            if rendered:
                _append_line(lines, 0, rendered)
        _append_line(lines, len(tree_model.lineage), _ssa_link(target), current=True)
        if tree_model.direct_children:
            seen_descendants: set[str] = set()
            for raw in tree_model.direct_children:
                rendered = _render_entry(raw)
                child_value = _normalize_ssa_relation_value(
                    cast(dict[str, object], raw).get("ssa")
                    if isinstance(raw, dict)
                    else raw
                )
                if not rendered or not child_value or child_value in seen_descendants:
                    continue
                seen_descendants.add(child_value)
                _append_line(lines, len(tree_model.lineage) + 1, rendered)
                stack = [
                    (raw_child, len(tree_model.lineage) + 2)
                    for raw_child in reversed(tree_model.child_map.get(child_value, []))
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
                        or descendant_value in seen_descendants
                        or not rendered_descendant
                    ):
                        continue
                    seen_descendants.add(descendant_value)
                    _append_line(lines, depth, rendered_descendant)
                    for raw_child in reversed(tree_model.child_map.get(descendant_value, [])):
                        stack.append((raw_child, depth + 1))
        else:
            _append_line(
                lines,
                len(tree_model.lineage) + 1,
                '<span style="opacity:0.82;">Sem Derivadas</span>',
            )

    if tree_model.hidden_descendants > 0:
        lines.append(
            f"{'&nbsp;' * ((len(tree_model.lineage) + 1) * 4)}... (+{tree_model.hidden_descendants})<br/>"
        )
    if tree_model.related_entries:
        lines.append("<br/><b>Relacionadas:</b><br/>")
        for raw in tree_model.related_entries:
            rendered = _render_entry(raw)
            if rendered:
                _append_line(lines, 1, rendered)

    lines.append("</div>")
    return "".join(lines)


def _build_derivadas_mermaid_text(data: Mapping[str, object]) -> str:
    return details_derivadas_model.build_mermaid_text(
        data,
        normalizer=_normalize_ssa_relation_value,
    )


def _build_derivadas_graph_html(
    window,
    data: Mapping[str, object],
    *,
    link_color: str,
    font_family: str,
) -> str:
    graph_model = details_derivadas_model.build_graph_model(
        data,
        max_descendants=DERIVADAS_GRAPH_MAX_DESCENDANTS,
        node_width=DERIVADAS_GRAPH_NODE_WIDTH,
        node_height=DERIVADAS_GRAPH_NODE_HEIGHT,
        x_gap=DERIVADAS_GRAPH_X_GAP,
        y_gap=DERIVADAS_GRAPH_Y_GAP,
        margin=DERIVADAS_GRAPH_MARGIN,
        normalizer=_normalize_ssa_relation_value,
    )
    if graph_model is None:
        return ""
    node_w = DERIVADAS_GRAPH_NODE_WIDTH
    node_h = DERIVADAS_GRAPH_NODE_HEIGHT
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
        text_len = max(1, len(str(value or "")))
        by_width = usable_w / (text_len * 0.56)
        by_height = max(10.0, float(node_h) * 0.56)
        return max(11.0, min(by_width, by_height, 15.5))

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{graph_model.svg_width}" '
        f'height="{graph_model.svg_height}" viewBox="0 0 {graph_model.svg_width} {graph_model.svg_height}">',
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
        if span <= 0:
            return x1
        min_offset = min(2.0, span / 2.0)
        max_offset = max(min_offset, span - min_offset)
        lane_offset = min(max(min_offset, float(lane_index + 1) * 3.0), max_offset)
        return x1 + (direction * lane_offset)

    for source, target_node in graph_model.edges:
        source_pos = graph_model.positions.get(source)
        target_pos = graph_model.positions.get(target_node)
        if source_pos is None or target_pos is None:
            continue
        sx, sy = source_pos
        tx, ty = target_pos
        x1 = sx + node_w / 2.0 + graph_model.offset_x
        x2 = tx - node_w / 2.0 + graph_model.offset_x
        y1 = sy + graph_model.offset_y
        y2 = ty + graph_model.offset_y
        mid_x = _compute_lane_x(source, x1, x2)
        dash_attr = (
            ' stroke-dasharray="7 6"'
            if (source, target_node) in graph_model.dashed_edges
            else ""
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

    for node, (x, y) in graph_model.positions.items():
        x0 = x - node_w / 2.0 + graph_model.offset_x
        y0 = y - node_h / 2.0 + graph_model.offset_y
        fill = node_target_fill if node == graph_model.target else node_fill
        safe_node = html_module.escape(node)
        svg_lines.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{node_w}" height="{node_h}" '
            f'rx="5" ry="5" fill="{fill}" stroke="{node_stroke}" stroke-width="0.8" />'
        )
        svg_lines.append(
            f'<text x="{(x0 + node_w / 2.0):.1f}" y="{(y0 + node_h / 2.0 + 5):.1f}" text-anchor="middle" '
            f'font-family="{html_module.escape(font_family)}" font-size="{_node_font_size(node):.1f}" fill="{text_color}">{safe_node}</text>'
        )
    svg_lines.append("</svg>")

    summary = (
        f"Nos: {len(graph_model.nodes)} | Relacoes: {len(graph_model.edges)} | "
        f"Descendentes: {graph_model.descendants_count}"
    )
    if graph_model.truncated > 0:
        summary = (
            f"{summary} | Exibicao parcial de descendentes: +{graph_model.truncated}"
        )
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


def _apply_details_dialog_geometry(window, dialog, details_tab_splitter) -> None:
    screen_geometry = _get_dialog_screen_geometry(window)
    if screen_geometry is None:
        return
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
    target_width = min(max(current_size.width(), DERIVADAS_DIALOG_MIN_WIDTH), safe_width)
    target_height = desired_height
    if target_width != current_size.width() or target_height != current_size.height():
        dialog.resize(target_width, target_height)
    bottom_height = min(
        max(
            DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT,
            int(target_height * 0.26),
        ),
        max(0, target_height - 240),
    )
    details_tab_splitter.setSizes([max(0, target_height - bottom_height), bottom_height])


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
        from PyQt6.QtCore import Qt
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
    svg_render_deps = load_svg_render_dependencies()
    if svg_render_deps is None:
        logger.debug("QSvgRenderer unavailable for derivadas graph rendering")

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
    if svg_render_deps is not None:
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
        tree_graph_browser,
        0,
        0,
        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
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
    dialog_font_family = DETAILS_CONFIG.mono_font_family
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
        if tree_graph_label is None or svg_render_deps is None:
            return False
        return render_graph_svg_pixmap(
            graph_svg=graph_svg,
            graph_label=tree_graph_label,
            graph_panel=tree_graph_panel,
            dependencies=svg_render_deps,
        )

    def _render_target(ssa_target, resolved_series=None):
        export_state["svg"] = ""
        export_state["mermaid"] = ""
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
            if not graph_svg or not _render_graph_pixmap(graph_svg):
                tree_graph_label.setText("Grafo de derivadas indisponivel.")
                if svg_render_deps is not None:
                    tree_graph_label.setPixmap(svg_render_deps.pixmap_cls())
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

    export_controller = DetailsGraphExportController(
        dialog=dialog,
        graph_widget=tree_graph_browser,
        export_state=export_state,
        file_dialog_cls=QFileDialog,
        message_box_cls=QMessageBox,
        menu_cls=QMenu,
        logger=logger,
    )

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
        lambda pos: export_controller.show_menu(tree_graph_browser.mapToGlobal(pos))
    )
    export_button.clicked.connect(
        lambda: export_controller.show_menu(
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
    _apply_details_dialog_geometry(window, dialog, details_tab_splitter)
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
