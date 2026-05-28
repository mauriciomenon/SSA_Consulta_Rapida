# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import math
import os
import re
from typing import Any, Mapping, cast

import pandas as pd

from core.dataframe_fingerprint import build_dataframe_filter_hash
from gui.helpers.formatting_helpers import highlight_text
from gui.helpers.theme_helpers import pick_css_color
from gui.qt_stubs import QTimer
from gui.ssa import details_data_provider
from gui.ssa import details_derivadas_model
from gui.ssa import details_graph_renderer
from gui.ssa.details_display_config import DetailsDisplayConfig
from gui.ssa.details_dialog_constants import (
    DERIVADAS_DIALOG_BOTTOM_TARGET_MIN_HEIGHT,
    DERIVADAS_DIALOG_DETAILS_FONT_PT,
    DERIVADAS_DIALOG_LABEL_FONT_PT,
    DERIVADAS_DIALOG_MIN_HEIGHT,
    DERIVADAS_DIALOG_MIN_WIDTH,
    DERIVADAS_DIALOG_TREE_FONT_PT,
    DERIVADAS_GRAPH_MAX_DESCENDANTS,
    HIDDEN_DETAIL_FIELDS,
    SSA_NORM_CACHE_MAX_ENTRIES,
)
from gui.ssa.details_dialog_presenter import (
    DetailsDialogCallbacks,
    DetailsDialogPresenter,
)
from gui.ssa.details_graph_export import load_svg_render_dependencies
from gui.ssa.details_graph_export import render_graph_svg_pixmap
from gui.ssa.details_normalization import (
    is_missing_scalar as _is_missing_scalar,
    normalize_ssa_relation_series as _normalize_ssa_relation_series,
    normalize_ssa_relation_value as _normalize_ssa_relation_value,
)
from gui.ssa.details_series_index import DetailsSeriesIndex
from gui.ssa.gui_details_html import DetailsHtmlDependencies, render_details_html
from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from shared.ssa_status import format_status_display, get_status_code
from utils.formatting import format_cell
from utils.robust_logging import get_robust_logger
from utils.themes import get_theme_roles

logger = get_robust_logger().get_logger(__name__, "gui")


DETAILS_CONFIG = DetailsDisplayConfig()

_SVG_VIEWBOX_RE = re.compile(
    r'<svg[^>]*\bviewBox="0\s+0\s+([0-9.]+)\s+([0-9.]+)"',
    re.IGNORECASE,
)
_SVG_NODE_RECT_RE = re.compile(
    r'<rect(?=[^>]*\bdata-ssa="([^"]+)")(?=[^>]*(?<![-\w])x="([0-9.]+)")'
    r'(?=[^>]*(?<![-\w])y="([0-9.]+)")'
    r'(?=[^>]*(?<![-\w])width="([0-9.]+)")'
    r'(?=[^>]*(?<![-\w])height="([0-9.]+)")[^>]*>',
    re.IGNORECASE,
)


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
    normalized = _normalize_ssa_value(None, numero_ssa)
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
    normalized = _normalize_ssa_value(None, numero_ssa)
    if not normalized:
        return html_module.escape(str(numero_ssa or ""))
    label = normalized
    status_code = str(status_hint or "").strip().upper()
    if status_code:
        label = f"{normalized} ({status_code})"
    escaped_label = html_module.escape(label)
    href = _build_ssa_href(normalized, panel_mode=panel_mode)
    if not href or not exists:
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
    deps = DetailsHtmlDependencies(
        collect_highlight_terms=_collect_highlight_terms,
        get_window_ssa_series_index=_get_window_ssa_series_index,
        get_derivadas_for_ssa=_get_derivadas_for_ssa,
        get_related_ssas_for_series=_get_related_ssas_for_series,
        hydrate_ssa_index_candidates=_hydrate_ssa_index_candidates,
        get_series_for_ssa=_get_series_for_ssa,
        normalize_ssa_value=_normalize_ssa_value,
        highlight_text=_highlight_text,
        render_ssa_navigation_link=_render_ssa_navigation_link,
    )
    return render_details_html(
        window,
        series,
        config=DETAILS_CONFIG,
        hidden_fields=HIDDEN_DETAIL_FIELDS,
        deps=deps,
        highlight_search_terms=highlight_search_terms,
        font_size_pt=font_size_pt,
        linkify=linkify,
        label_font_size_pt=label_font_size_pt,
        font_family=font_family,
        ssa_index=ssa_index,
    )


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
        resolved = pd.Series("", index=series_obj.index, dtype="object")
        valid_codes = codes >= 0
        if bool(valid_codes.any()):
            resolved.iloc[valid_codes] = pd.array(
                normalized_uniques,
                dtype="object",
            ).take(codes[valid_codes])
        return resolved
    except Exception as exc:
        logger.debug("Falha ao normalizar SSA series; fallback apply: %s", exc)
        return series.map(lambda value: _normalize_ssa_value(window, value)).astype("object")


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
    data_revision = getattr(window, "_data_revision", None)
    frame_token = _get_details_frame_fingerprint(window, df)
    key = (
        frame_token,
        str(column_name),
        len(df),
        data_revision,
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


def _get_cached_relation_series(window, df, column_name: str) -> pd.Series:
    if df is None or column_name not in getattr(df, "columns", []):
        return pd.Series(dtype="object")
    data_uuid = getattr(window, "_data_uuid", None)
    if data_uuid is None:
        return _normalize_ssa_relation_series(df[column_name])
    cache_owner = getattr(window, "cache_manager", None)
    cache_get = getattr(cache_owner, "get_cached_value", None)
    cache_put = getattr(cache_owner, "cache_value", None)
    if not callable(cache_get) or not callable(cache_put):
        return _normalize_ssa_relation_series(df[column_name])
    data_revision = getattr(window, "_data_revision", None)
    frame_token = _get_details_frame_fingerprint(window, df)
    key = (
        frame_token,
        str(column_name),
        len(df),
        data_revision,
        data_uuid,
    )
    cached = cache_get("ssa_relation_norm", key)
    if isinstance(cached, pd.Series) and len(cached) == len(df):
        return cached
    normalized = _normalize_ssa_relation_series(df[column_name])
    cache_put(
        "ssa_relation_norm",
        key,
        normalized,
        max_entries=SSA_NORM_CACHE_MAX_ENTRIES,
    )
    return normalized


def _get_df_ssa_series_index(window, df) -> Mapping[str, pd.Series]:
    if df is None or df.empty or "numero_ssa" not in getattr(df, "columns", []):
        return {}
    data_uuid = getattr(window, "_data_uuid", None)
    cache_enabled = data_uuid is not None
    cache_owner = getattr(window, "cache_manager", None)
    cache_get = getattr(cache_owner, "get_cached_value", None)
    cache_put = getattr(cache_owner, "cache_value", None)
    has_cache_manager = callable(cache_get) and callable(cache_put)
    cache_key = None
    cached = None
    if cache_enabled and has_cache_manager:
        cache_key = (
            _get_details_frame_fingerprint(window, df),
            len(df),
            getattr(window, "_data_revision", None),
            data_uuid,
        )
        cached = cast(Any, cache_get)("details_df_ssa_index", cache_key)
    if isinstance(cached, Mapping) and cached:
        return cached

    lookup: Mapping[str, pd.Series] = {}
    normalized_series = _get_cached_normalized_series(window, df, "numero_ssa")
    try:
        normalized_text_series = normalized_series.fillna("")
        first_value_mask = normalized_text_series.ne("") & ~normalized_text_series.duplicated()
        first_positions = first_value_mask.to_numpy().nonzero()[0]
        first_values = normalized_text_series.iloc[first_positions]
        if first_values.empty:
            return lookup
        row_positions = {
            str(normalized): int(position)
            for normalized, position in zip(
                first_values.to_list(), first_positions, strict=True
            )
        }
        lookup = DetailsSeriesIndex(df, row_positions)
    except Exception as exc:
        logger.debug("Falha ao montar indice SSA por DataFrame: %s", exc)
        return {}
    if cache_enabled and has_cache_manager and cache_key is not None:
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


def _normalize_ssa_candidate_keys(window, candidates) -> set[str]:
    return {
        normalized
        for normalized in (
            _normalize_ssa_value(window, candidate) for candidate in candidates
        )
        if normalized
    }


def _seed_resolved_ssa_candidates(
    existing: Mapping[str, pd.Series] | None,
    remaining: set[str],
) -> dict[str, pd.Series]:
    if not existing:
        return {}
    resolved = {
        key: value
        for key, value in existing.items()
        if key in remaining and value is not None
    }
    remaining.difference_update(resolved.keys())
    return resolved


def _hydrate_resolved_ssa_candidates_from_df(
    window,
    df,
    remaining: set[str],
    resolved: dict[str, pd.Series],
) -> None:
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
    matched_positions = matches.to_numpy().nonzero()[0]
    for matched_position in matched_positions:
        normalized_value = normalized_series.iloc[int(matched_position)]
        key = str(normalized_value or "").strip()
        if not key or key in resolved:
            continue
        matched = df.iloc[int(matched_position)]
        resolved[key] = matched
    remaining.difference_update(resolved.keys())


def _resolve_ssa_series_candidates(
    window,
    candidates,
    *,
    existing: Mapping[str, pd.Series] | None = None,
) -> dict[str, pd.Series]:
    remaining = _normalize_ssa_candidate_keys(window, candidates)
    resolved = _seed_resolved_ssa_candidates(existing, remaining)
    if not remaining:
        return resolved
    _hydrate_resolved_ssa_candidates_from_df(
        window,
        getattr(window, "df_exibido", None),
        remaining,
        resolved,
    )
    _hydrate_resolved_ssa_candidates_from_df(
        window,
        getattr(window, "df_completo", None),
        remaining,
        resolved,
    )
    return resolved


def _get_details_frame_fingerprint(window, df) -> str:
    data_uuid = getattr(window, "_data_uuid", None)
    data_revision = getattr(window, "_data_revision", None)
    if data_uuid is None or data_revision is None:
        return build_dataframe_filter_hash(df)
    token = (
        id(df),
        data_uuid,
        data_revision,
        tuple(getattr(df, "shape", (0, 0))),
        tuple(str(column) for column in getattr(df, "columns", [])),
    )
    cache = getattr(window, "_details_frame_fingerprint_cache", None)
    if not isinstance(cache, dict):
        cache = {}
    cached_value = cache.get(token)
    if isinstance(cached_value, str) and cached_value:
        return cached_value
    fingerprint = repr(token)
    if len(cache) >= SSA_NORM_CACHE_MAX_ENTRIES:
        cache.pop(next(iter(cache)))
    cache[token] = fingerprint
    setattr(window, "_details_frame_fingerprint_cache", cache)
    return fingerprint


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
        _schedule_details_update(window, None)
        return
    selected_rows = window.table_widget.selectionModel().selectedRows()
    if not selected_rows:
        _schedule_details_update(window, None)
        return
    row = selected_rows[0].row()
    series = window._get_series_from_row(row)
    render_signature = _get_details_render_signature(window, series)
    current_signature = window.details_text.property("details_render_signature")
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
    if series is None:
        try:
            window.details_text.setProperty("details_render_signature", None)
        except Exception as exc:
            logger.debug("Falha ao limpar assinatura pendente de detalhes: %s", exc)
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


def _clear_main_details_state(window) -> None:
    setattr(window, "_details_current_ssa", None)
    window.details_text.setProperty("details_render_signature", None)
    window.details_text.clear()
    setattr(window, "_details_current_series_for_derivadas", None)
    _clear_main_details_derivadas_panel(window)


def _resolve_details_render_fonts(window) -> tuple[float | None, str | None]:
    font_size_pt = None
    font_family = None
    if not hasattr(window, "details_group"):
        return font_size_pt, font_family
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
        return None, None
    return font_size_pt, font_family


def _get_cached_details_ssa_index(window) -> Mapping[str, pd.Series]:
    details_ssa_index: Mapping[str, pd.Series] = {}
    current_sources = (
        getattr(window, "df_exibido", None),
        getattr(window, "df_completo", None),
    )
    cached_sources = getattr(window, "_details_ssa_index_sources", None)
    cached_lookup = getattr(window, "_details_ssa_series_index", None)
    if (
        isinstance(cached_sources, tuple)
        and len(cached_sources) == 4
        and cached_sources[0] is current_sources[0]
        and cached_sources[1] is current_sources[1]
        and cached_sources[2] == getattr(window, "_data_revision", None)
        and cached_sources[3] == getattr(window, "_data_uuid", None)
        and isinstance(cached_lookup, dict)
    ):
        details_ssa_index = cached_lookup
    return details_ssa_index


def _render_main_details_html(window, series, render_signature) -> bool:
    font_size_pt, font_family = _resolve_details_render_fonts(window)
    html_content = _format_details_html(
        window,
        series,
        highlight_search_terms=True,
        font_size_pt=font_size_pt,
        linkify=True,
        font_family=font_family,
        ssa_index=_get_cached_details_ssa_index(window),
    )
    window.details_text.setHtml(html_content)
    window.details_text.setProperty("details_render_signature", render_signature)
    setattr(window, "_details_current_series_for_derivadas", series)
    setattr(window, "_details_current_derivadas_font_family", font_family)
    _sync_main_details_derivadas_panel(window)
    return True


def _build_plaintext_details(window, series) -> str:
    def field_sort_key(item):
        col, _ = item
        try:
            return (0, DETAILS_CONFIG.field_priority.index(col))
        except ValueError:
            return (1, col)

    lines = []
    for col, value in sorted(series.items(), key=field_sort_key):
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
    return "\n".join(lines)


def _render_main_details_plaintext(window, series, render_signature) -> None:
    window.details_text.setPlainText(_build_plaintext_details(window, series))
    window.details_text.setProperty("details_render_signature", render_signature)
    setattr(window, "_details_current_series_for_derivadas", series)
    setattr(window, "_details_current_derivadas_font_family", None)
    _sync_main_details_derivadas_panel(window)


def _update_details_from_series(window, series):
    """Atualiza o painel de detalhes a partir de uma serie ja resolvida."""
    if series is None:
        _clear_main_details_state(window)
        return
    render_signature = _get_details_render_signature(window, series)
    try:
        setattr(window, "_details_current_ssa", series.get("numero_ssa"))
    except Exception:
        setattr(window, "_details_current_ssa", None)

    try:
        _render_main_details_html(window, series, render_signature)
        return
    except Exception as exc:
        logger.debug(
            "Falha ao renderizar detalhes em HTML; aplicando fallback texto: %s", exc
        )

    try:
        _render_main_details_plaintext(window, series, render_signature)
    except Exception as exc:
        logger.debug("Falha ao renderizar detalhes em texto simples: %s", exc)


def _clear_main_details_derivadas_panel(window) -> None:
    for attr in ("details_tree_text", "details_graph_label", "details_graph_text"):
        widget = getattr(window, attr, None)
        if widget is None:
            continue
        try:
            _set_graph_navigation_hitboxes(widget, [])
            clear_svg_markup = getattr(widget, "clear_graph_svg_markup", None)
            if callable(clear_svg_markup):
                clear_svg_markup()
            widget.clear()
            if attr in ("details_graph_label", "details_graph_text"):
                widget.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao limpar %s: %s", attr, exc)


def _sync_main_details_derivadas_panel(window) -> None:
    stack = getattr(window, "details_stack", None)
    try:
        active_derivadas = stack is not None and int(stack.currentIndex()) == 1
    except Exception as exc:
        logger.debug("Falha ao ler aba ativa de detalhes: %s", exc)
        active_derivadas = False
    if active_derivadas:
        refresh_main_details_derivadas_panel(window)
        return
    _clear_main_details_derivadas_panel(window)


def _clear_graph_browser_markup(graph_browser: Any) -> None:
    _set_graph_navigation_hitboxes(graph_browser, [])
    clear_svg_markup = getattr(graph_browser, "clear_graph_svg_markup", None)
    if callable(clear_svg_markup):
        clear_svg_markup()


def _set_graph_browser_message(
    tree_browser: Any,
    graph_browser: Any,
    message: str,
    *,
    tree_visible: bool,
    use_html: bool = False,
) -> None:
    tree_browser.setVisible(tree_visible)
    _clear_graph_browser_markup(graph_browser)
    if hasattr(graph_browser, "setPixmap"):
        graph_browser.clear()
    if use_html and hasattr(graph_browser, "setHtml"):
        graph_browser.setHtml(message)
    else:
        graph_browser.setText(message)
    graph_browser.setVisible(True)


def _resolve_derivadas_panel_payload(
    window, series, font_family: str | None
) -> tuple[Any, Any, str, Mapping[str, object], str, str]:
    tree_browser = getattr(window, "details_tree_text", None)
    graph_label = getattr(window, "details_graph_label", None)
    graph_browser = graph_label or getattr(window, "details_graph_text", None)
    if tree_browser is None or graph_browser is None:
        raise ValueError("details panel widgets unavailable")
    numero_ssa = series.get("numero_ssa")
    normalized = _normalize_ssa_relation_value(numero_ssa)
    if not normalized:
        raise ValueError("invalid numero_ssa for derivadas panel")
    roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
    link_color = str(
        roles.get("accent") or roles.get("panel_text") or roles.get("label_color")
    )
    safe_font_family = font_family or DETAILS_CONFIG.mono_font_family
    tree_data = _collect_derivadas_tree_data(window, normalized)
    return tree_browser, graph_browser, normalized, tree_data, link_color, safe_font_family


def _render_derivadas_graph_svg_or_fallback(
    window,
    tree_browser: Any,
    graph_browser: Any,
    tree_data: Mapping[str, object],
    *,
    link_color: str,
    font_family: str,
) -> None:
    graph_html = _build_derivadas_graph_html(
        window,
        tree_data,
        link_color=link_color,
        font_family=font_family,
    )
    graph_svg = _extract_inline_svg_markup(graph_html)
    svg_deps = load_svg_render_dependencies()
    if graph_svg and svg_deps is not None:
        graph_panel = graph_browser.parentWidget() or graph_browser
        if not render_graph_svg_pixmap(
            graph_svg=graph_svg,
            graph_label=graph_browser,
            graph_panel=graph_panel,
            dependencies=svg_deps,
        ):
            _set_graph_browser_message(
                tree_browser,
                graph_browser,
                "Grafo de derivadas indisponivel.",
                tree_visible=True,
            )
            return
        tree_browser.setVisible(False)
        graph_browser.setVisible(True)
        set_svg_markup = getattr(graph_browser, "set_graph_svg_markup", None)
        if callable(set_svg_markup):
            set_svg_markup(graph_svg)
        _apply_graph_navigation_hitboxes(graph_browser, graph_svg)
        return
    if hasattr(graph_browser, "setHtml"):
        _set_graph_browser_message(
            tree_browser,
            graph_browser,
            graph_html or "Grafo de derivadas indisponivel.",
            tree_visible=True,
            use_html=True,
        )
        return
    _set_graph_browser_message(
        tree_browser,
        graph_browser,
        "Grafo de derivadas indisponivel.",
        tree_visible=True,
    )


def _update_main_details_derivadas_panel(window, series, *, font_family: str | None) -> None:
    try:
        (
            tree_browser,
            graph_browser,
            normalized,
            tree_data,
            link_color,
            safe_font_family,
        ) = _resolve_derivadas_panel_payload(window, series, font_family)
    except Exception as exc:
        logger.debug("Falha ao resolver painel principal de derivadas: %s", exc)
        _clear_main_details_derivadas_panel(window)
        return
    try:
        if not _has_derivadas_graph_relations(tree_data):
            _set_graph_browser_message(
                tree_browser,
                graph_browser,
                "Sem SSAs Derivadas.",
                tree_visible=False,
            )
            return
        tree_html = _build_derivadas_tree_html(
            window,
            normalized,
            link_color=link_color,
            font_family=safe_font_family,
            tree_data_override=tree_data,
            ssa_index={},
        )
        tree_browser.setHtml(tree_html or "Sem derivadas para exibir.")
        _render_derivadas_graph_svg_or_fallback(
            window,
            tree_browser,
            graph_browser,
            tree_data,
            link_color=link_color,
            font_family=safe_font_family,
        )
    except Exception as exc:
        logger.debug("Falha ao atualizar painel principal de derivadas: %s", exc)
        _clear_main_details_derivadas_panel(window)


def _has_derivadas_graph_relations(tree_data: Mapping[str, object]) -> bool:
    for key in ("parents", "children", "descendants", "ancestors", "related"):
        value = tree_data.get(key)
        if value:
            return True
    return False


def _set_graph_navigation_hitboxes(
    graph_widget: Any,
    hitboxes: list[tuple[str, float, float, float, float]],
) -> None:
    setter = getattr(graph_widget, "set_ssa_hitboxes", None)
    if callable(setter):
        setter(hitboxes)


def _apply_graph_navigation_hitboxes(graph_widget: Any, graph_svg: str) -> None:
    render_width = int(graph_widget.width())
    render_height = int(graph_widget.height())
    pixmap_getter = getattr(graph_widget, "pixmap", None)
    pixmap = pixmap_getter() if callable(pixmap_getter) else None
    if pixmap is not None:
        size_getter = getattr(pixmap, "deviceIndependentSize", None)
        logical_size = size_getter() if callable(size_getter) else None
        logical_width_getter = getattr(logical_size, "width", None)
        logical_height_getter = getattr(logical_size, "height", None)
        if callable(logical_width_getter) and callable(logical_height_getter):
            render_width = int(logical_width_getter())
            render_height = int(logical_height_getter())
        else:
            width_getter = getattr(pixmap, "width", None)
            height_getter = getattr(pixmap, "height", None)
            if callable(width_getter) and callable(height_getter):
                render_width = int(width_getter())
                render_height = int(height_getter())
    hitboxes = _graph_navigation_hitboxes_from_svg(
        graph_svg,
        render_width=float(max(1, render_width)),
        render_height=float(max(1, render_height)),
    )
    _set_graph_navigation_hitboxes(graph_widget, hitboxes)


def reapply_graph_navigation_hitboxes(graph_widget: Any, graph_svg: str) -> None:
    _apply_graph_navigation_hitboxes(graph_widget, graph_svg)


def _graph_navigation_hitboxes_from_svg(
    graph_svg: str,
    *,
    render_width: float,
    render_height: float,
) -> list[tuple[str, float, float, float, float]]:
    if not graph_svg:
        return []
    viewbox_match = _SVG_VIEWBOX_RE.search(graph_svg)
    if viewbox_match is None:
        return []
    try:
        svg_width = float(viewbox_match.group(1))
        svg_height = float(viewbox_match.group(2))
    except ValueError:
        return []
    if svg_width <= 0.0 or svg_height <= 0.0:
        return []
    scale_x = render_width / svg_width
    scale_y = render_height / svg_height
    hitboxes: list[tuple[str, float, float, float, float]] = []
    for match in _SVG_NODE_RECT_RE.finditer(graph_svg):
        try:
            ssa = html_module.unescape(match.group(1)).strip()
            left = float(match.group(2)) * scale_x
            top = float(match.group(3)) * scale_y
            width = float(match.group(4)) * scale_x
            height = float(match.group(5)) * scale_y
        except ValueError:
            continue
        if not ssa or width <= 0.0 or height <= 0.0:
            continue
        hitboxes.append((ssa, left, top, left + width, top + height))
    return hitboxes


def refresh_main_details_derivadas_panel(window) -> None:
    series = getattr(window, "_details_current_series_for_derivadas", None)
    if series is None:
        _clear_main_details_derivadas_panel(window)
        return
    _update_main_details_derivadas_panel(
        window,
        series,
        font_family=getattr(window, "_details_current_derivadas_font_family", None),
    )


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


def _find_series_position_by_ssa(window, df, target: str, *, use_index_lookup: bool = True):
    if df is None or df.empty or "numero_ssa" not in df.columns:
        return None, None
    try:
        if use_index_lookup:
            ssa_index = _get_df_ssa_series_index(window, df)
            if isinstance(ssa_index, DetailsSeriesIndex):
                position = ssa_index.get_position(target)
                if position is None:
                    return None, None
                matched = ssa_index.get(target)
                return int(position), matched
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


def _show_jump_fallback_details(window, num_norm: str, fallback_series: pd.Series) -> None:
    try:
        table_widget = getattr(window, "table_widget", None)
        if (
            table_widget is not None
            and hasattr(table_widget, "clearSelection")
            and hasattr(table_widget, "selectionModel")
        ):
            selection_model = table_widget.selectionModel()
            if selection_model is not None and selection_model.hasSelection():
                table_widget.clearSelection()
    except Exception as exc:
        logger.debug(
            "Falha ao limpar selecao no salto para SSA %s fora da pagina: %s",
            num_norm,
            exc,
        )
    try:
        details_timer = getattr(window, "_details_update_timer", None)
        if details_timer is not None and hasattr(details_timer, "stop"):
            details_timer.stop()
        setattr(window, "_pending_details_series", None)
    except Exception as exc:
        logger.debug(
            "Falha ao cancelar atualizacao pendente no salto para SSA %s: %s",
            num_norm,
            exc,
        )
    _update_details_from_series(window, fallback_series)


def _display_jump_target_page(
    window,
    paginator,
    pos: int,
    matched_series: pd.Series | None,
    num_norm: str,
) -> None:
    page_size = int(getattr(paginator, "page_size", 50))
    if page_size <= 0:
        logger.warning(
            "Page size invalido ao saltar para SSA %s: %s", num_norm, page_size
        )
        return
    page = int(pos // page_size + 1)
    try:
        paginator.current_page = page
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar pagina atual no salto para SSA %s: %s",
            num_norm,
            exc,
        )
    window.display_current_page(page, update_details=False)
    row_in_page = int(pos % page_size)
    _update_details_from_series(window, matched_series)

    def _select_target_row_later() -> None:
        try:
            if int(getattr(paginator, "current_page", 1)) != page:
                logger.debug(
                    "Selecao adiada ignorada para SSA %s: pagina atual mudou",
                    num_norm,
                )
                return
            table_widget = getattr(window, "table_widget", None)
            if table_widget is None:
                return
            if row_in_page < 0 or row_in_page >= table_widget.rowCount():
                return
            table_widget.selectRow(row_in_page)
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


def _jump_to_ssa(window, numero_ssa, *, _allow_refilter=True):
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return
    try:
        pos = None
        pos, matched_series = _find_series_position_by_ssa(
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
            pos, matched_series = _find_series_position_by_ssa(
                window, getattr(window, "df_exibido", None), num_norm
            )
        if pos is None:
            fallback_series = _get_series_for_ssa(window, num_norm)
            if fallback_series is None:
                return
            _show_jump_fallback_details(window, num_norm, fallback_series)
            return
        paginator = getattr(window, "paginator", None)
        if paginator is None:
            _update_details_from_series(window, matched_series)
            return
        _display_jump_target_page(window, paginator, pos, matched_series, num_norm)
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
        window, getattr(window, "df_completo", None), target, use_index_lookup=False
    )
    return match


def _extract_prefixed_anchor_target(href: str, prefix: str) -> str:
    return href[len(prefix) :].strip().lstrip("/")


def _resolve_details_anchor_action(href: str) -> tuple[str, str | None, bool]:
    if href.startswith("copy-ssa:"):
        return ("copy", _extract_prefixed_anchor_target(href, "copy-ssa:"), True)
    if href.startswith("derivadas:tree") or href.startswith("derivadas://tree"):
        return ("derivadas-tree", None, True)
    for prefix in ("ssa-details:", "ssa_details://"):
        if href.startswith(prefix):
            return ("details-dialog", _extract_prefixed_anchor_target(href, prefix), True)
    for prefix, allow_refilter in (
        ("ssa-panel:", True),
        ("ssa:", False),
        ("ssa://", False),
    ):
        if href.startswith(prefix):
            return (
                "jump",
                _extract_prefixed_anchor_target(href, prefix),
                allow_refilter,
            )
    return ("", None, False)


def _on_details_anchor_clicked(window, url):
    try:
        href = url.toString()
    except Exception:
        return
    if not href:
        return
    action, target, allow_refilter = _resolve_details_anchor_action(href)
    if action == "copy":
        if target:
            window._copy_ssa_to_clipboard(target)
        return
    if action == "derivadas-tree":
        _show_derivadas_tree_for_ssa(window, getattr(window, "_details_current_ssa", None))
        return
    if action == "details-dialog":
        if target:
            _open_details_dialog_for_ssa(window, target)
        return
    if action == "jump" and target:
        if allow_refilter:
            _jump_to_ssa(window, target)
        else:
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
        cache_enabled = data_uuid is not None or data_revision is not None
        row_count = len(source_df)
        cache_key = (
            _get_details_frame_fingerprint(window, source_df),
            row_count,
            data_revision,
            data_uuid,
        )
        cached_edges = (
            cast(Any, cache_get)("details_derivadas_family_edges", cache_key)
            if cache_enabled and has_cache_manager
            else None
        )
        if isinstance(cached_edges, list):
            return cast(list[tuple[str, str]], cached_edges)

        number_series = _get_cached_normalized_series(window, source_df, "numero_ssa")
        parent_series = _get_cached_relation_series(window, source_df, "derivada_de")
        valid_mask = parent_series.ne("") & number_series.ne("")
        if bool(valid_mask.any()):
            valid_pairs = zip(
                parent_series.loc[valid_mask].to_numpy(copy=False),
                number_series.loc[valid_mask].to_numpy(copy=False),
                strict=True,
            )
            edges = cast(
                list[tuple[str, str]],
                list(dict.fromkeys(valid_pairs)),
            )
        else:
            edges = []
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
        source_df = getattr(window, "df_completo", None)
        cache_owner = getattr(window, "cache_manager", None)
        cache_get = getattr(cache_owner, "get_cached_value", None)
        cache_put = getattr(cache_owner, "cache_value", None)
        has_cache_manager = callable(cache_get) and callable(cache_put)
        data_revision = getattr(window, "_data_revision", None)
        data_uuid = getattr(window, "_data_uuid", None)
        row_count = len(source_df) if isinstance(source_df, pd.DataFrame) else 0
        frame_token = (
            _get_details_frame_fingerprint(window, source_df)
            if isinstance(source_df, pd.DataFrame)
            else None
        )
        cache_key = (frame_token, row_count, data_revision, data_uuid)
        if data_uuid is not None and has_cache_manager:
            cached_map = cast(Any, cache_get)(
                "details_derivadas_children_by_parent", cache_key
            )
            if isinstance(cached_map, dict):
                return cast(dict[str, list[str]], cached_map)

        edges = _get_cached_derivadas_family_edges(window)
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
        if data_uuid is not None and has_cache_manager:
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
    shape = tuple(getattr(df, "shape", (0, 0)))
    if data_uuid is not None:
        if revision is not None:
            return ("revision", revision, shape)
        return ("uuid", data_uuid, shape, _get_details_frame_fingerprint(window, df))
    return ("uncached", id(df), shape, object())


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

    local_payload = None
    local_edges = _get_cached_derivadas_family_edges(window)
    if local_edges:
        local_payload = details_data_provider.build_local_family_payload(
            target,
            local_edges,
            max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
        )
    local_has_relation_data = bool(
        local_payload
        and (
            local_payload.get("parents")
            or local_payload.get("children")
            or local_payload.get("family_roots")
            or local_payload.get("family_descendants")
        )
    )
    snapshot = None
    snapshot_has_relation_data = False
    if not local_has_relation_data:
        snapshot = details_data_provider.load_derivadas_snapshot(
            db_path,
            target,
            max_nodes=DERIVADAS_GRAPH_MAX_DESCENDANTS,
        )
        snapshot_has_relation_data = bool(
            snapshot
            and (
                snapshot.get("parents")
                or snapshot.get("children")
                or snapshot.get("ancestors")
                or snapshot.get("descendants")
                or snapshot.get("family_roots")
                or snapshot.get("family_descendants")
            )
        )
    series_target = _get_series_for_ssa(window, target)
    related = _get_related_ssas_for_series(window, series_target)
    try:
        target_status = get_status_code(series_target.get("situacao"))
    except Exception as exc:
        logger.debug("Falha ao obter situacao alvo da arvore %s: %s", target, exc)
        target_status = ""
    tree_data = details_derivadas_model.normalize_tree_data(
        target=target,
        snapshot=snapshot,
        fallback_children=(
            []
            if snapshot_has_relation_data or local_has_relation_data
            else _get_derivadas_for_ssa(window, target)
        ),
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
    if isinstance(ssa_index, dict):
        cast(dict[str, pd.Series], ssa_index).update(resolved_candidates)
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
    if ssa_index is None:
        ssa_index = {}
    target_status = str(data.get("target_status", "") or "").strip().upper()
    status_by_ssa, existing_tree_ssas = _build_derivadas_link_state(
        window, data, target, ssa_index=ssa_index
    )

    def _ssa_link(value, *, status_hint: str | None = None):
        safe = _normalize_ssa_relation_value(value) or _normalize_ssa_value(
            window, value
        )
        if not safe:
            return html_module.escape(str(value))
        lookup_key = _normalize_ssa_value(window, value) or safe
        resolved_series = ssa_index.get(lookup_key)
        if resolved_series is None and lookup_key != safe:
            resolved_series = ssa_index.get(safe)
        if (
            resolved_series is None
            and allow_global_index
            and len(ssa_index) <= DERIVADAS_GRAPH_MAX_DESCENDANTS
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

    def _entry_ssa_value(entry) -> str:
        if isinstance(entry, dict):
            return _normalize_ssa_relation_value(entry.get("ssa"))
        return _normalize_ssa_relation_value(entry)

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
                child_value = _entry_ssa_value(raw_child)
                if child_value and child_value not in seen_family_nodes:
                    stack.append((child_value, depth + 1))
    else:
        for raw in tree_model.lineage:
            rendered = _render_entry(raw)
            if rendered:
                _append_line(lines, 0, rendered)
        _append_line(lines, len(tree_model.lineage), _ssa_link(target), current=True)
        if tree_model.direct_children:
            seen_descendants: set[str] = {target}
            seen_descendants.update(
                value
                for value in (
                    _entry_ssa_value(raw_lineage) for raw_lineage in tree_model.lineage
                )
                if value
            )
            for raw in tree_model.direct_children:
                rendered = _render_entry(raw)
                child_value = _entry_ssa_value(raw)
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
                    descendant_value = _entry_ssa_value(raw_descendant)
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
                        child_value = _entry_ssa_value(raw_child)
                        if child_value and child_value not in seen_descendants:
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
    return details_graph_renderer.build_derivadas_graph_html(
        current_theme=str(getattr(window, "_current_theme", "dark") or "dark"),
        data=data,
        link_color=link_color,
        font_family=font_family,
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


def _resolve_details_dialog_target(window, numero_ssa, series=None):
    target = _normalize_ssa_value(window, numero_ssa)
    if not target:
        return None
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
        return None
    return target, series


def _resolve_details_dialog_style(window, palette_cls):
    try:
        link_color = window.palette().color(palette_cls.ColorRole.Highlight).name()
    except Exception:
        roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
        link_color = pick_css_color(
            roles.get("accent"),
            roles.get("panel_text"),
            roles.get("label_color"),
            fallback="#4a90e2",
        )

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
    return (
        link_color,
        dialog_font_pt,
        dialog_label_font_pt,
        dialog_tree_font_pt,
        dialog_font_family,
    )


def _build_details_dialog_callbacks(window) -> DetailsDialogCallbacks:
    return DetailsDialogCallbacks(
        apply_geometry=_apply_details_dialog_geometry,
        build_graph_html=_build_derivadas_graph_html,
        build_mermaid_text=_build_derivadas_mermaid_text,
        build_tree_html=_build_derivadas_tree_html,
        collect_tree_data=_collect_derivadas_tree_data,
        copy_ssa_to_clipboard=window._copy_ssa_to_clipboard,
        extract_svg_markup=_extract_inline_svg_markup,
        format_details_html=_format_details_html,
        get_series_for_ssa=_get_series_for_ssa,
        logger=logger,
        normalize_ssa_value=_normalize_ssa_value,
        resolve_style=_resolve_details_dialog_style,
    )


def _open_details_dialog_for_ssa(window, numero_ssa, series=None):
    resolved_target = _resolve_details_dialog_target(window, numero_ssa, series)
    if resolved_target is None:
        return
    target, series = resolved_target
    DetailsDialogPresenter(
        window=window,
        target=target,
        series=series,
        callbacks=_build_details_dialog_callbacks(window),
    ).open()


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
