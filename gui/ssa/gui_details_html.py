# gui/ssa/gui_details_html.py
# Relation: used by gui/ssa/gui_details.py to render the details HTML table.

from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, cast

from gui.helpers.theme_helpers import pick_css_color
from gui.ssa.details_display_config import DetailsDisplayConfig
from shared.ssa_status import format_status_display
from utils.formatting import format_cell
from utils.robust_logging import get_robust_logger
from utils.themes import get_theme_roles

logger = get_robust_logger().get_logger(__name__, "gui")

_CSS_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgba?\([0-9,\s.]+\)|[a-zA-Z][a-zA-Z0-9_-]*)$"
)
_CSS_FONT_RE = re.compile(r"^[\w\s,'\".-]+$")
_ORIGIN_DETAIL_FIELD_FINAL_BLOCK_ORDER = {
    "sistema_origem": 0,
    "data_arquivo_origem": 1,
    "data_planilha": 2,
    "arquivo_origem": 3,
}


@dataclass(frozen=True)
class DetailsHtmlDependencies:
    collect_highlight_terms: Callable[[Any], list[str]]
    get_window_ssa_series_index: Callable[[Any], Mapping[str, Any]]
    get_derivadas_for_ssa: Callable[[Any, Any], list[str]]
    get_related_ssas_for_series: Callable[..., list[dict[str, Any]]]
    hydrate_ssa_index_candidates: Callable[..., None]
    get_series_for_ssa: Callable[[Any, str], Any]
    normalize_ssa_value: Callable[[Any, Any], str]
    highlight_text: Callable[[Any, str, list[str]], str]
    render_ssa_navigation_link: Callable[..., str]


def _resolve_details_font_family(window: Any) -> str:
    try:
        ui_font_family = str(window.font().family() or "").strip()
    except Exception as exc:
        logger.debug("Falha ao ler familia de fonte da UI para detalhes: %s", exc)
        ui_font_family = ""
    return ui_font_family or "sans-serif"


def _safe_css_number(
    value: Any, *, fallback: float, min_value: float = 0.0, max_value: float = 64.0
) -> float:
    safe_fallback = min(max(float(fallback), min_value), max_value)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return safe_fallback
    if not min_value <= numeric <= max_value:
        return safe_fallback
    return numeric


def _safe_css_color(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if text and _CSS_COLOR_RE.fullmatch(text):
        return text
    return fallback


def _safe_font_family(value: Any) -> str:
    text = str(value or "").strip()
    if text and _CSS_FONT_RE.fullmatch(text):
        return text
    return "sans-serif"


def _resolve_details_colors(window: Any) -> tuple[str, str]:
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
    return text_color, link_color


def _field_sort_key(config: DetailsDisplayConfig, item: tuple[Any, Any]) -> tuple[int, Any]:
    col, _ = item
    try:
        return (0, config.field_priority.index(col))
    except ValueError:
        if col in _ORIGIN_DETAIL_FIELD_FINAL_BLOCK_ORDER:
            return (2, _ORIGIN_DETAIL_FIELD_FINAL_BLOCK_ORDER[col])
        return (1, str(col))


def _display_name_html(display_name: str) -> str:
    return html_module.escape(display_name)


def _append_detail_row(
    html_lines: list[str],
    *,
    label: str,
    value_html: str,
    config: DetailsDisplayConfig,
    label_font_size_pt: float,
) -> None:
    safe_padding = _safe_css_number(config.table_padding, fallback=6.0)
    safe_border = _safe_css_color(config.border_color, fallback="#d0d0d0")
    safe_label_font_size = _safe_css_number(label_font_size_pt, fallback=12.0)
    html_lines.append(
        f"<tr>"
        f'<td style="padding: {safe_padding:g}px; '
        f"border-bottom: 1px solid {safe_border}; "
        f'font-weight: bold; font-size: {safe_label_font_size:g}pt; vertical-align: top;">'
        f"{label}:</td>"
        f'<td style="padding: {safe_padding:g}px; '
        f"border-bottom: 1px solid {safe_border}; "
        f"overflow-wrap: anywhere; word-break: break-word; "
        f'white-space: pre-wrap; text-align: right;">'
        f"{value_html}</td>"
        f"</tr>"
    )


def _render_field_value(
    window: Any,
    deps: DetailsHtmlDependencies,
    *,
    col: Any,
    formatted_value: str,
    search_terms: list[str],
    text_color: str,
    highlight_search_terms: bool,
    linkify: bool,
) -> str:
    if col == "situacao":
        formatted_value = format_status_display(formatted_value)
    if col == "numero_ssa" and linkify:
        safe_ssa = deps.normalize_ssa_value(window, formatted_value)
        escaped_value = html_module.escape(formatted_value)
        if safe_ssa:
            return (
                f'<a href="copy-ssa:{safe_ssa}" style="color:{text_color}; '
                f'text-decoration:none;">{escaped_value}</a>'
            )
        return escaped_value
    if highlight_search_terms and search_terms:
        return deps.highlight_text(window, formatted_value, search_terms)
    return html_module.escape(formatted_value)


def _render_derivadas_row(
    window: Any,
    deps: DetailsHtmlDependencies,
    html_lines: list[str],
    *,
    series: Any,
    ssa_index: Mapping[str, Any],
    allow_global_index: bool,
    search_terms: list[str],
    link_color: str,
    highlight_search_terms: bool,
    linkify: bool,
    config: DetailsDisplayConfig,
    label_font_size_pt: float,
) -> None:
    try:
        derived_list = deps.get_derivadas_for_ssa(window, series.get("numero_ssa"))
    except Exception as exc:
        logger.debug("Falha ao coletar lista de derivadas para detalhes HTML: %s", exc)
        derived_list = []
    if not derived_list:
        return

    if linkify:
        items = []
        derived_exists_cache: dict[str, bool] = {}
        if isinstance(ssa_index, dict) and ssa_index:
            deps.hydrate_ssa_index_candidates(
                window, cast(dict[str, Any], ssa_index), derived_list
            )
        for item in derived_list:
            href = deps.normalize_ssa_value(window, item)
            exists = False
            if href:
                cached_exists = derived_exists_cache.get(href)
                if cached_exists is None:
                    resolved_series = ssa_index.get(href)
                    if resolved_series is None and allow_global_index:
                        resolved_series = deps.get_series_for_ssa(window, href)
                    cached_exists = resolved_series is not None
                    derived_exists_cache[href] = cached_exists
                exists = cached_exists
            items.append(
                deps.render_ssa_navigation_link(
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
            derived_text = deps.highlight_text(window, derived_text, search_terms)
        else:
            derived_text = html_module.escape(derived_text)

    _append_detail_row(
        html_lines,
        label=html_module.escape(f"SSAs derivadas ({len(derived_list)})"),
        value_html=derived_text,
        config=config,
        label_font_size_pt=label_font_size_pt,
    )


def _render_related_row(
    window: Any,
    deps: DetailsHtmlDependencies,
    html_lines: list[str],
    *,
    series: Any,
    ssa_index: Mapping[str, Any],
    link_color: str,
    linkify: bool,
    config: DetailsDisplayConfig,
    label_font_size_pt: float,
) -> None:
    related_items = deps.get_related_ssas_for_series(
        window, series, ssa_index=ssa_index
    )
    if not related_items:
        return

    rendered_items = []
    seen_related = set()
    for item in related_items:
        related_ssa = str(item.get("ssa", "") or "").strip()
        if not related_ssa or related_ssa in seen_related:
            continue
        seen_related.add(related_ssa)
        related_exists = bool(item.get("exists", False))
        status_hint = str(item.get("situacao", "") or "").strip().upper()
        rendered_items.append(
            deps.render_ssa_navigation_link(
                related_ssa,
                link_color=link_color,
                panel_mode=False,
                exists=related_exists,
                status_hint=status_hint,
            )
            if linkify
            else html_module.escape(related_ssa)
        )
    if rendered_items:
        _append_detail_row(
            html_lines,
            label=html_module.escape(f"SSAs relacionadas ({len(rendered_items)})"),
            value_html=", ".join(rendered_items),
            config=config,
            label_font_size_pt=label_font_size_pt,
        )


def render_details_html(
    window: Any,
    series: Any,
    *,
    config: DetailsDisplayConfig,
    hidden_fields: set[str],
    deps: DetailsHtmlDependencies,
    highlight_search_terms: bool = False,
    font_size_pt: float | None = None,
    linkify: bool = False,
    label_font_size_pt: float | None = None,
    font_family: str | None = None,
    ssa_index: Mapping[str, Any] | None = None,
) -> str:
    if font_size_pt is None:
        font_size_pt = config.details_dialog_font_size
    if label_font_size_pt is None:
        label_font_size_pt = font_size_pt
    if not font_family:
        font_family = _resolve_details_font_family(window)
    font_family = _safe_font_family(font_family)
    font_size_pt = _safe_css_number(font_size_pt, fallback=12.0)
    text_color, link_color = _resolve_details_colors(window)
    text_color = _safe_css_color(text_color, fallback="#d0d0d0")
    link_color = _safe_css_color(link_color, fallback="#4a90e2")

    search_terms = deps.collect_highlight_terms(window) if highlight_search_terms else []

    html_lines = [
        (
            f'<html><body style="font-family: {font_family}; '
            f'font-size: {font_size_pt}pt; color: {text_color};">'
        ),
        '<table style="width: 100%; border-collapse: collapse; table-layout: fixed;">',
        '<colgroup><col style="width: 18%;"/><col style="width: 82%;"/></colgroup>',
    ]

    sorted_items = sorted(series.items(), key=lambda item: _field_sort_key(config, item))
    for col, value in sorted_items:
        if col in hidden_fields or str(col).startswith("_"):
            continue
        formatted_value = format_cell(value, col)
        if not formatted_value:
            continue
        display_name = config.display_overrides.get(
            col, window.internal_to_display.get(col, col)
        )
        label_html = config.label_line_breaks.get(
            str(col), _display_name_html(display_name)
        )
        formatted_value = _render_field_value(
            window,
            deps,
            col=col,
            formatted_value=formatted_value,
            search_terms=search_terms,
            text_color=text_color,
            highlight_search_terms=highlight_search_terms,
            linkify=linkify,
        )
        _append_detail_row(
            html_lines,
            label=label_html,
            value_html=formatted_value,
            config=config,
            label_font_size_pt=label_font_size_pt,
        )

    allow_global_index = ssa_index is None
    if allow_global_index:
        ssa_index = deps.get_window_ssa_series_index(window)
    if ssa_index is None:
        ssa_index = {}

    _render_derivadas_row(
        window,
        deps,
        html_lines,
        series=series,
        ssa_index=ssa_index,
        allow_global_index=allow_global_index,
        search_terms=search_terms,
        link_color=link_color,
        highlight_search_terms=highlight_search_terms,
        linkify=linkify,
        config=config,
        label_font_size_pt=label_font_size_pt,
    )
    _render_related_row(
        window,
        deps,
        html_lines,
        series=series,
        ssa_index=ssa_index,
        link_color=link_color,
        linkify=linkify,
        config=config,
        label_font_size_pt=label_font_size_pt,
    )

    html_lines.append("</table></body></html>")
    return "\n".join(html_lines)
