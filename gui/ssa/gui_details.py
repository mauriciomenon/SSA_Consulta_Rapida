# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import os
from typing import Mapping, cast

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
DERIVADAS_DIALOG_RATIO_LEFT = 18
DERIVADAS_DIALOG_RATIO_RIGHT = 82
DERIVADAS_DIALOG_MIN_HEIGHT = 730
DERIVADAS_DIALOG_DETAILS_FONT_PT = 12.0
DERIVADAS_DIALOG_TREE_FONT_PT = 12.0
DERIVADAS_DIALOG_LABEL_FONT_PT = 11.0
SSA_NORM_CACHE_MAX_ENTRIES = 64
DERIVADAS_DIALOG_MIN_WIDTH = 960
DERIVADAS_DIALOG_TREE_MIN_WIDTH = 180
DERIVADAS_DIALOG_DETAILS_MIN_WIDTH = 520
DERIVADAS_GRAPH_NODE_WIDTH = 100
DERIVADAS_GRAPH_NODE_HEIGHT = 30
DERIVADAS_GRAPH_X_GAP = 110
DERIVADAS_GRAPH_Y_GAP = 60
DERIVADAS_GRAPH_MARGIN = 8
DERIVADAS_GRAPH_MAX_DESCENDANTS = 120
DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT = 120
DERIVADAS_SPLITTER_HANDLE_WIDTH = 10


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
    except Exception:
        value = ""
    return get_status_code(value)


def _format_details_html(
    window,
    series,
    highlight_search_terms=False,
    font_size_pt=None,
    linkify=False,
    label_font_size_pt=None,
    font_family=None,
    derivadas_rel_override=None,
):
    """Formata dados da SSA como HTML com highlight opcional."""
    if font_size_pt is None:
        font_size_pt = DETAILS_DIALOG_FONT_SIZE
    if label_font_size_pt is None:
        label_font_size_pt = font_size_pt
    if not font_family:
        font_family = MONO_FONT_FAMILY

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
    except Exception:
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
    html_lines.append('<table style="width: 100%; border-collapse: collapse;">')

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

        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f"border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; "
            f'font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;">'
            f"{display_name_html}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{formatted_value}</td>"
            f"</tr>"
        )

    try:
        derived_list = _get_derivadas_for_ssa(window, series.get("numero_ssa"))
    except Exception:
        derived_list = []
    if derived_list:
        if linkify:
            items = []
            for item in derived_list:
                href = _normalize_ssa_value(window, item)
                display = html_module.escape(item)
                items.append(
                    f'<a href="ssa:{href}" style="color:{link_color}; '
                    f'text-decoration:none; border-bottom: 1px solid {link_color};">'
                    f"{display}</a>"
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
            f'font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;">'
            f"{html_module.escape(label)}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{derived_text}</td>"
            f"</tr>"
        )

    html_lines.append("</table></body></html>")
    return "\n".join(html_lines)


def _normalize_ssa_value(window, value):
    try:
        raw = value
    except Exception:
        raw = ""
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
        except Exception:
            return pd.Series([""] * len(series), index=getattr(series, "index", None))


def _normalize_ssa_relation_value(value) -> str:
    return str(normalize_numero_ssa_relation(value) or "").strip()


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
    cache_owner = getattr(window, "cache_manager", None)
    if cache_owner is None:
        cache_owner = window
    cache = getattr(cache_owner, "_ssa_norm_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(cache_owner, "_ssa_norm_cache", cache)
    key = (id(df), str(column_name))
    cached = cache.get(key)
    if isinstance(cached, pd.Series) and len(cached) == len(df):
        return cached
    normalized = _normalize_ssa_series(window, df[column_name])
    if len(cache) >= SSA_NORM_CACHE_MAX_ENTRIES:
        overflow = len(cache) - SSA_NORM_CACHE_MAX_ENTRIES + 1
        for stale_key in list(cache.keys())[:overflow]:
            cache.pop(stale_key, None)
    cache[key] = normalized
    return normalized


def _get_details_db_signature():
    db_path = _resolve_current_db_path()
    if not db_path:
        return None
    try:
        return os.path.getmtime(db_path)
    except Exception:
        return None


def _get_details_render_signature(window, series):
    if series is None:
        return None
    try:
        selected_ssa = series.get("numero_ssa")
    except Exception:
        selected_ssa = None
    try:
        search_terms = tuple(_collect_highlight_terms(window))
    except Exception:
        search_terms = ()
    try:
        series_signature = tuple(
            (str(column), "" if pd.isna(value) else str(value))
            for column, value in series.items()
        )
    except Exception:
        try:
            series_signature = str(series)
        except Exception:
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
    except Exception:
        selected_ssa = None
    render_signature = _get_details_render_signature(window, series)
    current_signature = window.details_text.property("details_render_signature")
    skip_ssa = window.table_widget.property("details_skip_selection_once_for_ssa")
    if skip_ssa is not None and selected_ssa != skip_ssa:
        window.table_widget.setProperty("details_skip_selection_once_for_ssa", None)
    if selected_ssa is not None and selected_ssa == skip_ssa:
        window.table_widget.setProperty("details_skip_selection_once_for_ssa", None)
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
        if hasattr(window, "details_group"):
            try:
                base_font = window.details_group.font()
                size = base_font.pointSizeF()
                if size <= 0:
                    size = float(base_font.pointSize())
                if size > 0:
                    font_size_pt = max(size - 1.0, 8.0)
            except Exception:
                font_size_pt = None
        html_content = _format_details_html(
            window,
            series,
            highlight_search_terms=True,
            font_size_pt=font_size_pt,
            linkify=True,
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
        series_norm = _normalize_ssa_relation_series(window.df_completo["derivada_de"])
        mask = series_norm.eq(num_norm)
        derived_series = _normalize_ssa_relation_series(
            window.df_completo.loc[mask, "numero_ssa"]
        )
        derived = []
        seen = set()
        for value in derived_series.tolist():
            formatted = str(value or "").strip()
            if formatted and formatted not in seen:
                seen.add(formatted)
                derived.append(formatted)
        return derived
    except Exception as exc:
        logger.debug("Falha ao coletar derivadas para SSA %s: %s", numero_ssa, exc)
        return []


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
            series_norm = _get_cached_normalized_series(window, df, "numero_ssa")
            mask = series_norm.eq(target)
            if not mask.any():
                return None
            idx_label = mask[mask].index[0]
            matched = df.loc[idx_label]
            if isinstance(matched, pd.DataFrame):
                return matched.iloc[0]
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
        _jump_to_ssa(window, target)


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


def _collect_derivadas_tree_data(window, numero_ssa):
    target = _normalize_ssa_relation_value(numero_ssa)
    empty = {
        "target": "",
        "parents": [],
        "children": [],
        "descendants": [],
        "ancestors": [],
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

    db_path = _resolve_current_db_path()
    if db_path and os.path.exists(db_path):
        try:
            from armazenamento import derivadas_queries

            parents = derivadas_queries.get_parents(db_path, target)
            children = derivadas_queries.get_children(db_path, target)
            descendants = derivadas_queries.get_descendants(db_path, target)
            ancestors = derivadas_queries.get_ancestors(db_path, target)
            profile = derivadas_queries.get_hierarchy_profile(db_path, target) or {}
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
    direct_children_count = int(profile.get("direct_children_count") or len(children))
    descendants_count = int(
        profile.get("descendants_count") or len(descendants) or len(children)
    )
    return {
        "target": target,
        "parents": parents,
        "children": children,
        "descendants": descendants,
        "ancestors": ancestors,
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

    def _ssa_link(value, *, status_hint: str | None = None):
        safe = _normalize_ssa_relation_value(value)
        if not safe:
            return html_module.escape(str(value))
        status_code = (
            str(status_hint or _get_situacao_for_ssa(window, safe)).strip().upper()
        )
        label = safe if not status_code else f"{safe} ({status_code})"
        return (
            f'<a href="ssa-panel:{safe}" style="color:{link_color}; '
            f'text-decoration:none; border-bottom: 1px solid {link_color};">'
            f"{html_module.escape(label)}</a>"
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

    def _append_descendants(lines, parent_ssa: str, depth: int) -> None:
        for raw in child_map.get(parent_ssa, []):
            raw_map = cast(dict[str, object], raw)
            child_value = _normalize_ssa_relation_value(raw_map.get("ssa"))
            rendered = _render_entry(raw)
            if not child_value or not rendered:
                continue
            _append_line(lines, depth, rendered)
            _append_descendants(lines, child_value, depth + 1)

    lines.append(
        f'<div style="font-family:{font_family}; font-size:{tree_font_pt:.2f}pt; line-height:1.85;">'
    )
    lines.append("<b>Derivadas:</b><br/><br/>")
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
            _append_descendants(lines, child_value, len(lineage) + 2)
    else:
        _append_line(
            lines,
            len(lineage) + 1,
            '<span style="opacity:0.82;">Sem Derivadas</span>',
        )

    descendants_count = int(data.get("descendants_count", 0) or 0)
    direct_children_count = int(data.get("direct_children_count", 0) or 0)
    hidden_descendants = max(
        0, descendants_count - direct_children_count - len(descendants_entries)
    )
    if hidden_descendants > 0:
        lines.append(
            f"{'&nbsp;' * ((len(lineage) + 1) * 4)}... (+{hidden_descendants})<br/>"
        )

    lines.append("</div>")
    return "".join(lines)


def _build_derivadas_mermaid_text(data: Mapping[str, object]) -> str:
    target = _normalize_ssa_relation_value(data.get("target", ""))
    if not target:
        return ""

    def _node_id(value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        return f"N{digits}" if digits else f"N_{abs(hash(value))}"

    def _label(value: str) -> str:
        clean = str(value).replace('"', "'")
        return clean

    lines = ["flowchart TD"]
    lines.append(f'  {_node_id(target)}["{_label(target)}"]')

    parents = data.get("parents", [])
    if isinstance(parents, list):
        for raw in parents:
            parent = _normalize_ssa_relation_value(raw)
            if not parent:
                continue
            lines.append(
                f'  {_node_id(parent)}["{_label(parent)}"] --> {_node_id(target)}'
            )

    children = data.get("children", [])
    if isinstance(children, list):
        for raw in children:
            child = _normalize_ssa_relation_value(raw)
            if not child:
                continue
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
                lines.append(
                    f'  {_node_id(parent)} --> {_node_id(ssa)}["{_label(ssa)}"]'
                )
            else:
                lines.append(
                    f'  {_node_id(target)} -.-> {_node_id(ssa)}["{_label(ssa)}"]'
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
    descendants: list[dict[str, str]] = []
    if isinstance(descendants_entries, list):
        for raw in descendants_entries[:DERIVADAS_GRAPH_MAX_DESCENDANTS]:
            if not isinstance(raw, dict):
                continue
            raw_map = cast(dict[str, object], raw)
            child = _normalize_ssa_relation_value(raw_map.get("ssa"))
            parent = _normalize_ssa_relation_value(raw_map.get("parent"))
            if not child:
                continue
            descendants.append({"ssa": child, "parent": parent})

    nodes: set[str] = {target}
    edges: list[tuple[str, str]] = []
    dashed_edges: set[tuple[str, str]] = set()
    edge_seen: set[tuple[str, str]] = set()

    def _add_edge(source: str, target_node: str, *, dashed: bool = False) -> None:
        if not source or not target_node:
            return
        edge = (source, target_node)
        if edge in edge_seen:
            return
        edge_seen.add(edge)
        edges.append(edge)
        nodes.add(source)
        nodes.add(target_node)
        if dashed:
            dashed_edges.add(edge)

    for parent in parents:
        _add_edge(parent, target)
    for child in children:
        _add_edge(target, child)
    for row in descendants:
        descendant = row.get("ssa", "")
        parent = row.get("parent", "")
        if parent:
            _add_edge(parent, descendant)
        else:
            _add_edge(target, descendant, dashed=True)

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
    for depth, node in enumerate(lineage):
        ordered_nodes.append((node, depth))
    current_depth = len(lineage)
    ordered_nodes.append((target, current_depth))

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
        ordered_nodes.append((child_ssa, current_depth + 1))
        _append_descendant_nodes(child_ssa, current_depth + 2)

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
        mid_x = x1 + max(12.0, (x2 - x1) / 2.0)
        dash_attr = (
            ' stroke-dasharray="7 6"' if (source, target_node) in dashed_edges else ""
        )
        svg_lines.append(
            f'<path d="M{x1:.1f},{y1:.1f} L{mid_x:.1f},{y1:.1f} '
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
        truncated = max(0, len(descendants_entries) - len(descendants))
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


def _open_details_dialog_for_ssa(window, numero_ssa):
    target = _normalize_ssa_value(window, numero_ssa)
    if not target:
        return
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
        QTextBrowser(), min_height=DERIVADAS_DIALOG_GRAPH_PANEL_MIN_HEIGHT
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

    def _render_target(ssa_target):
        normalized = _normalize_ssa_value(window, ssa_target)
        if not normalized:
            return False
        series_target = _get_series_for_ssa(window, normalized)
        if series_target is None:
            return False
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
        )
        details_browser.setHtml(html_details)
        tree_html = _build_derivadas_tree_html(
            window,
            normalized,
            link_color=link_color,
            tree_font_pt=dialog_tree_font_pt,
            font_family=dialog_font_family,
            tree_data_override=tree_data,
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
            assert tree_graph_text_browser is not None
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
    if not _render_target(target):
        return

    details_tab_splitter.addWidget(details_browser)
    details_derivadas_splitter.addWidget(tree_tab_browser)
    details_derivadas_splitter.addWidget(tree_graph_panel)
    details_derivadas_splitter.setStretchFactor(0, 1)
    details_derivadas_splitter.setStretchFactor(1, 1)
    details_derivadas_splitter.setSizes([430, 560])
    details_tab_splitter.addWidget(details_derivadas_splitter)
    details_tab_splitter.setStretchFactor(0, 1)
    details_tab_splitter.setStretchFactor(1, 0)
    details_tab_splitter.setSizes([560, 170])

    root_layout.addWidget(details_tab_splitter)

    close_button = QPushButton("Fechar")
    close_button.clicked.connect(dialog.accept)
    root_layout.addWidget(close_button)
    screen_geometry = _get_dialog_screen_geometry(window)
    if screen_geometry is not None:
        safe_width = max(640, screen_geometry.width() - 24)
        safe_height = max(480, screen_geometry.height() - 24)
        dialog.setMinimumSize(
            min(DERIVADAS_DIALOG_MIN_WIDTH, safe_width),
            min(DERIVADAS_DIALOG_MIN_HEIGHT, safe_height),
        )
        dialog.setMaximumSize(safe_width, safe_height)
        dialog.adjustSize()
        current_size = dialog.size()
        target_width = min(current_size.width(), safe_width)
        target_height = min(current_size.height(), safe_height)
        if (
            target_width != current_size.width()
            or target_height != current_size.height()
        ):
            dialog.resize(target_width, target_height)
    if tree_graph_label is not None:
        QTimer.singleShot(0, _refresh_graph_after_resize)
    dialog.exec()


def _filter_by_derivadas(window, numero_ssa):
    num_norm = _normalize_ssa_relation_value(numero_ssa)
    if not num_norm:
        return
    window._last_derivada_origem = num_norm
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
        _jump_to_ssa(window, window._last_derivada_origem)
        window._last_derivada_origem = None
