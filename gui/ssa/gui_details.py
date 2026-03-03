# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import os
import re

import pandas as pd

from gui.helpers.formatting_helpers import highlight_text
from gui.helpers.theme_helpers import pick_css_color
from utils.themes import get_theme_roles
from utils.formatting import format_cell
from utils.robust_logging import get_robust_logger

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
DERIVADAS_DIALOG_RATIO_LEFT = 20
DERIVADAS_DIALOG_RATIO_RIGHT = 80
DERIVADAS_DIALOG_MIN_HEIGHT = 650
DERIVADAS_DIALOG_DETAILS_FONT_PT = 12.0
DERIVADAS_DIALOG_TREE_FONT_PT = 12.0
DERIVADAS_DIALOG_LABEL_FONT_PT = 11.0
SSA_NORM_CACHE_MAX_ENTRIES = 64


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


def _format_details_html(
    window,
    series,
    highlight_search_terms=False,
    font_size_pt=None,
    linkify=False,
    label_font_size_pt=None,
    font_family=None,
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
        display_name = DETAIL_DISPLAY_OVERRIDES.get(col, window.internal_to_display.get(col, col))
        if highlight_search_terms and search_terms:
            formatted_value = _highlight_text(window, formatted_value, search_terms)
        else:
            formatted_value = html_module.escape(formatted_value)
        display_name_html = html_module.escape(display_name)
        if display_name == "Grau de Prioridade (Emissao)":
            display_name_html = "Grau de Prioridade<br/>(Emissao)"

        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">"
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
                    f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
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
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">"
            f"{html_module.escape(label)}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{derived_text}</td>"
            f"</tr>"
        )

    derivadas_rel = _get_derivadas_relations_info(window, series.get("numero_ssa"))
    if derivadas_rel.get("has_data"):
        parent_list = derivadas_rel.get("parents", [])
        children_list = derivadas_rel.get("children", [])
        descendants_count = int(derivadas_rel.get("descendants_count", 0))

        def _ssa_display(value):
            normalized = _normalize_ssa_value(window, value)
            if normalized:
                return normalized
            return str(value).strip()

        html_lines.append(
            f"<tr>"
            f'<td colspan="2" style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt;\">Relacoes de Derivadas</td>"
            f"</tr>"
        )

        mae_direta_text = "-"
        if parent_list:
            if linkify:
                first_parent = html_module.escape(_ssa_display(parent_list[0]))
                href_parent = _normalize_ssa_value(window, parent_list[0])
                mae_direta_text = (
                    f'<a href="ssa-details:{href_parent}" style="color:{link_color}; '
                    f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
                    f"{first_parent}</a>"
                )
            else:
                mae_direta_text = html_module.escape(_ssa_display(parent_list[0]))
            if len(parent_list) > 1:
                mae_direta_text = f"{mae_direta_text} (+{len(parent_list) - 1})"
        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">Mae direta:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{mae_direta_text}</td>"
            f"</tr>"
        )

        top_children = children_list[:DERIVADAS_DETAILS_TOP_N]
        if top_children:
            if linkify:
                child_items = []
                for child in top_children:
                    href_child = _normalize_ssa_value(window, child)
                    display_child = html_module.escape(_ssa_display(child))
                    child_items.append(
                        f'<a href="ssa:{href_child}" style="color:{link_color}; '
                        f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
                        f"{display_child}</a>"
                    )
                filhas_text = ", ".join(child_items)
            else:
                filhas_text = ", ".join(html_module.escape(_ssa_display(child)) for child in top_children)
            if len(children_list) > DERIVADAS_DETAILS_TOP_N:
                filhas_text = f"{filhas_text} ... (+{len(children_list) - DERIVADAS_DETAILS_TOP_N})"
        else:
            filhas_text = "-"
        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">"
            f"Filhas diretas ({len(children_list)}):</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{filhas_text}</td>"
            f"</tr>"
        )

        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">"
            f"Descendentes ({descendants_count}):</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{descendants_count}</td>"
            f"</tr>"
        )

        if linkify:
            open_tree_text = (
                f'<a href="derivadas:tree" style="color:{link_color}; '
                f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
                "Abrir arvore completa</a>"
            )
        else:
            open_tree_text = "Abrir arvore completa"
        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; font-size: {label_font_size_pt}pt; width: 30%; vertical-align: top;\">Acoes:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{open_tree_text}</td>"
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
    except Exception:
        pass
    text = str(raw).strip()
    if not text:
        return ""
    # Preserve integer value when represented as decimal string.
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    lowered = text.casefold()
    if lowered in ("nan", "none", "nat", "<na>"):
        return ""
    try:
        digits = re.sub(r"\D", "", text)
    except Exception:
        digits = ""
    if digits:
        return digits
    return lowered


def _normalize_ssa_series(window, series: pd.Series) -> pd.Series:
    """Normaliza valores de SSA em modo vetorizado (mais rapido que apply)."""
    try:
        s = series.astype(str).str.strip()
        # Normalize decimal integer strings to plain digits (e.g. 121911787.0).
        s = s.str.replace(r"^(\d+)\.0+$", r"\1", regex=True)
        lowered = s.str.casefold()
        empty_mask = s.isna() | s.eq("") | lowered.isin(("nan", "none", "nat", "<na>"))
        digits = s.str.replace(r"\D+", "", regex=True)
        out = digits.where(digits.ne(""), lowered)
        return out.where(~empty_mask, "")
    except Exception as exc:
        logger.debug("Falha ao normalizar SSA series; fallback apply: %s", exc)
        try:
            return series.map(lambda value: _normalize_ssa_value(window, value))
        except Exception:
            return pd.Series([""] * len(series), index=getattr(series, "index", None))


def _get_cached_normalized_series(window, df, column_name: str) -> pd.Series:
    if df is None or column_name not in getattr(df, "columns", []):
        return pd.Series(dtype="object")
    cache = getattr(window, "_ssa_norm_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        window._ssa_norm_cache = cache
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


def update_details_from_selection(window):
    """Atualiza o painel de detalhes com base na linha selecionada."""
    if window.table_widget.rowCount() == 0:
        window._details_current_ssa = None
        window.details_text.clear()
        return
    selected_rows = window.table_widget.selectionModel().selectedRows()
    if not selected_rows:
        window._details_current_ssa = None
        window.details_text.clear()
        return
    row = selected_rows[0].row()
    series = window._get_series_from_row(row)
    if series is None:
        window._details_current_ssa = None
        window.details_text.clear()
        return
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
        return
    except Exception as exc:
        logger.debug("Falha ao renderizar detalhes em HTML; aplicando fallback texto: %s", exc)

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
        display_name = DETAIL_DISPLAY_OVERRIDES.get(col, window.internal_to_display.get(col, col))
        lines.append(f"{display_name}: {formatted_value}")
    details_str = "\n".join(lines)
    try:
        window.details_text.setPlainText(details_str)
    except Exception as exc:
        logger.debug("Falha ao renderizar detalhes em texto simples: %s", exc)


def _get_derivadas_for_ssa(window, numero_ssa):
    if window.df_completo is None or window.df_completo.empty:
        return []
    if "derivada_de" not in window.df_completo.columns or "numero_ssa" not in window.df_completo.columns:
        return []
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return []
    try:
        series_norm = _get_cached_normalized_series(window, window.df_completo, "derivada_de")
        mask = series_norm.eq(num_norm)
        derived_raw = window.df_completo.loc[mask, "numero_ssa"].tolist()
        derived = []
        for value in derived_raw:
            formatted = format_cell(value, "numero_ssa")
            if formatted:
                derived.append(formatted)
        return derived
    except Exception as exc:
        logger.debug("Falha ao coletar derivadas para SSA %s: %s", numero_ssa, exc)
        return []


def _jump_to_ssa(window, numero_ssa):
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return
    try:
        def _find_position(df):
            if df is None or df.empty or "numero_ssa" not in df.columns:
                return None
            df_reset_local = df.reset_index(drop=True)
            # Avoid caching for this temporary reset_index DataFrame.
            series_norm_local = _normalize_ssa_series(window, df_reset_local["numero_ssa"])
            mask_local = series_norm_local.eq(num_norm)
            if not mask_local.any():
                return None
            return int(mask_local[mask_local].index[0])

        pos = _find_position(window.df_exibido)
        if pos is None:
            window.search_input.setText(f"={num_norm}")
            window.initiate_filtering()
            pos = _find_position(window.df_exibido)
            if pos is None:
                return
        page_size = int(getattr(window.paginator, "page_size", 50))
        if page_size <= 0:
            logger.warning("Page size invalido ao saltar para SSA %s: %s", num_norm, page_size)
            return
        page = int(pos // page_size + 1)
        try:
            window.paginator.current_page = page
        except Exception as exc:
            logger.debug("Falha ao atualizar pagina atual no salto para SSA %s: %s", num_norm, exc)
        window.display_current_page(page)
        row_in_page = int(pos % page_size)
        try:
            window.table_widget.selectRow(row_in_page)
        except Exception as exc:
            logger.debug("Falha ao selecionar linha %s no salto para SSA %s: %s", row_in_page, num_norm, exc)
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
    num_norm = _normalize_ssa_value(window, numero_ssa)
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
            logger.debug("Falha ao ler relacoes de derivadas no DB para %s: %s", num_norm, exc)

    if not children:
        children = _get_derivadas_for_ssa(window, num_norm)
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
    target = _normalize_ssa_value(window, numero_ssa)
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
            logger.debug("Falha ao coletar arvore de derivadas no DB para %s: %s", target, exc)

    if not children:
        children = _get_derivadas_for_ssa(window, target)
    direct_children_count = int(profile.get("direct_children_count") or len(children))
    descendants_count = int(profile.get("descendants_count") or len(descendants) or len(children))
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
):
    if not link_color:
        roles = get_theme_roles(getattr(window, "_current_theme", "dark"))
        link_color = roles.get("accent") or roles.get("panel_text") or roles.get("label_color")
    data = _collect_derivadas_tree_data(window, numero_ssa)
    target = data.get("target", "")
    if not target:
        return ""

    def _ssa_link(value):
        safe = _normalize_ssa_value(window, value)
        if not safe:
            return html_module.escape(str(value))
        return (
            f'<a href="ssa-panel:{safe}" style="color:{link_color}; '
            f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
            f"{html_module.escape(str(safe))}</a>"
        )

    lines = []
    if tree_font_pt is None:
        tree_font_pt = DERIVADAS_DIALOG_TREE_FONT_PT
    if not font_family:
        font_family = MONO_FONT_FAMILY
    lines.append(
        f'<div style="font-family:{font_family}; font-size:{tree_font_pt:.2f}pt; line-height:1.45;">'
    )
    lines.append("<b>Lista de derivadas:</b><br/><br/>")
    lines.append(f"<b>{_ssa_link(target)}</b><br/><br/>")
    parents = data.get("parents", [])
    lines.append("<b>SSA originaria</b><br/>")
    if parents:
        for parent in parents:
            lines.append(f"&nbsp;&nbsp;{_ssa_link(parent)}<br/>")
    else:
        lines.append("&nbsp;&nbsp;nenhuma<br/>")
    lines.append("<br/>")

    children = data.get("children", [])
    lines.append(f"<b>SSAs derivadas diretas ({int(data.get('direct_children_count', 0))})</b><br/>")
    if children:
        for child in children:
            lines.append(f"&nbsp;&nbsp;{_ssa_link(child)}<br/>")
    else:
        lines.append("&nbsp;&nbsp;nenhuma<br/>")
    lines.append("<br/>")

    descendants = data.get("descendants", [])
    desc_count = int(data.get("descendants_count", 0))
    lines.append(f"<b>SSAs derivadas de derivadas ({desc_count})</b><br/>")
    if descendants:
        for item in descendants[:50]:
            ssa = str(item.get("ssa", "")).strip()
            if ssa:
                lines.append(f"&nbsp;&nbsp;{_ssa_link(ssa)}<br/>")
        extra = len(descendants) - min(len(descendants), 50)
        if extra > 0:
            lines.append(f"&nbsp;&nbsp;... (+{extra})<br/>")
    else:
        lines.append("&nbsp;&nbsp;nenhuma<br/>")

    ancestors = data.get("ancestors", [])
    if ancestors:
        lines.append("<br/>")
        lines.append(f"<b>Ancestrais ({len(ancestors)})</b><br/>")
        for item in ancestors[:50]:
            ssa = str(item.get("ssa", "")).strip()
            dist = item.get("min_distance")
            if ssa:
                lines.append(f"&nbsp;&nbsp;- {_ssa_link(ssa)} (dist={dist})<br/>")

    lines.append("</div>")
    return "".join(lines)


def _open_details_dialog_for_ssa(window, numero_ssa):
    target = _normalize_ssa_value(window, numero_ssa)
    if not target:
        return
    series = _get_series_for_ssa(window, target)
    if series is None:
        return

    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QSplitter
        from PyQt6.QtGui import QPalette
    except Exception:
        return

    dialog = QDialog(window)
    dialog.setWindowTitle(f"Detalhes da SSA #{target}")
    dialog.setMinimumWidth(700)
    dialog.setMinimumHeight(DERIVADAS_DIALOG_MIN_HEIGHT)

    root_layout = QVBoxLayout(dialog)
    content_splitter = QSplitter(Qt.Orientation.Horizontal)
    content_splitter.setChildrenCollapsible(False)

    tree_browser = QTextBrowser()
    tree_browser.setReadOnly(True)
    tree_browser.setOpenLinks(False)
    tree_browser.setOpenExternalLinks(False)
    tree_browser.setMinimumWidth(90)

    details_browser = QTextBrowser()
    details_browser.setReadOnly(True)
    details_browser.setOpenLinks(False)
    details_browser.setOpenExternalLinks(False)
    details_browser.setMinimumWidth(360)

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
        logger.debug("Falha ao obter fonte base da UI para dialogo de detalhes: %s", exc)

    def _render_target(ssa_target):
        normalized = _normalize_ssa_value(window, ssa_target)
        if not normalized:
            return False
        series_target = _get_series_for_ssa(window, normalized)
        if series_target is None:
            return False
        current_target["ssa"] = normalized
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
        )
        if tree_html:
            tree_browser.setHtml(tree_html)
        else:
            tree_browser.setPlainText("Arvore de derivadas indisponivel para esta SSA.")
        return True

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

    tree_browser.anchorClicked.connect(_handle_dialog_anchor)
    details_browser.anchorClicked.connect(_handle_dialog_anchor)
    if not _render_target(target):
        return

    # Keep a stable 20/80 split: derivadas panel (left) / SSA details (right).
    content_splitter.addWidget(tree_browser)
    content_splitter.addWidget(details_browser)
    content_splitter.setStretchFactor(0, DERIVADAS_DIALOG_RATIO_LEFT)
    content_splitter.setStretchFactor(1, DERIVADAS_DIALOG_RATIO_RIGHT)
    total_ratio = DERIVADAS_DIALOG_RATIO_LEFT + DERIVADAS_DIALOG_RATIO_RIGHT
    left_width = max(90, int(dialog.minimumWidth() * DERIVADAS_DIALOG_RATIO_LEFT / total_ratio))
    right_width = max(360, int(dialog.minimumWidth() * DERIVADAS_DIALOG_RATIO_RIGHT / total_ratio))
    content_splitter.setSizes([left_width, right_width])
    root_layout.addWidget(content_splitter)

    close_button = QPushButton("Fechar")
    close_button.clicked.connect(dialog.accept)
    root_layout.addWidget(close_button)
    dialog.exec()


def _filter_by_derivadas(window, numero_ssa):
    num_norm = _normalize_ssa_value(window, numero_ssa)
    if not num_norm:
        return
    window._last_derivada_origem = num_norm
    window._active_column_filters["derivada_de"] = num_norm
    try:
        window._build_column_filters_panel()
    except Exception as exc:
        logger.warning("Falha ao reconstruir painel de filtros ao filtrar por derivadas: %s", exc)
    window._refresh_after_filter_change()


def _clear_derivadas_filter(window):
    if "derivada_de" in window._active_column_filters:
        window._active_column_filters.pop("derivada_de", None)
    try:
        window._build_column_filters_panel()
    except Exception as exc:
        logger.warning("Falha ao reconstruir painel de filtros ao limpar filtro de derivadas: %s", exc)
    window._refresh_after_filter_change()
    if window._last_derivada_origem:
        _jump_to_ssa(window, window._last_derivada_origem)
        window._last_derivada_origem = None
