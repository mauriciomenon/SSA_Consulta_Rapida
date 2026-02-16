# gui/ssa/gui_details.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles details panel formatting, highlight, and derivadas navigation.
# Relation: uses gui/helpers/formatting_helpers.highlight_text and utils.formatting.format_cell.

from __future__ import annotations

import html as html_module
import logging
import re

import pandas as pd

from gui.helpers.formatting_helpers import highlight_text
from utils.formatting import format_cell

logger = logging.getLogger(__name__)

DETAILS_DIALOG_FONT_SIZE = 10
DETAILS_DIALOG_TABLE_PADDING = 8
DETAILS_DIALOG_BORDER_COLOR = "#ccc"
DETAIL_FIELD_PRIORITY = []
DETAIL_DISPLAY_OVERRIDES = {}
HIGHLIGHT_BACKGROUND_COLOR = "yellow"
HIGHLIGHT_FONT_WEIGHT = "bold"
MONO_FONT_FAMILY = "monospace"


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
    if details_dialog_border_color:
        DETAILS_DIALOG_BORDER_COLOR = details_dialog_border_color
    if detail_field_priority is not None:
        DETAIL_FIELD_PRIORITY = list(detail_field_priority)
    if detail_display_overrides is not None:
        DETAIL_DISPLAY_OVERRIDES = dict(detail_display_overrides)
    if highlight_background_color:
        HIGHLIGHT_BACKGROUND_COLOR = highlight_background_color
    if highlight_font_weight:
        HIGHLIGHT_FONT_WEIGHT = highlight_font_weight
    if mono_font_family:
        MONO_FONT_FAMILY = mono_font_family


def _normalize_highlight_term(self, term):
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


def _get_current_search_terms(self):
    """Retorna lista de termos de busca atuais."""
    search_text = self.search_input.text().strip()
    if not search_text:
        return []
    terms = [term.strip() for term in search_text.split(",") if term.strip()]
    clean_terms = []
    for term in terms:
        normalized = _normalize_highlight_term(self, term)
        if normalized:
            clean_terms.append(normalized)
    return clean_terms


def _collect_highlight_terms(self):
    """Combina termos da busca geral e filtros de coluna para realce."""
    aggregated = []
    seen = set()
    for term in _get_current_search_terms(self):
        if term and term not in seen:
            aggregated.append(term)
            seen.add(term)
    for raw in getattr(self, "_active_column_filters", {}).values():
        if not raw:
            continue
        normalized_raw = str(raw).replace(";", ",")
        tokens = [tok.strip() for tok in normalized_raw.split(",") if tok.strip()]
        for tok in tokens:
            normalized = _normalize_highlight_term(self, tok)
            if normalized and normalized not in seen:
                aggregated.append(normalized)
                seen.add(normalized)
    return aggregated


def _highlight_text(self, text, terms):
    """Delegate to helper function."""
    bg = getattr(self, "_highlight_bg_color", HIGHLIGHT_BACKGROUND_COLOR)
    fg = getattr(self, "_highlight_text_color", None)
    weight = getattr(self, "_highlight_font_weight", HIGHLIGHT_FONT_WEIGHT)
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


def _format_details_html(self, series, highlight_search_terms=False, font_size_pt=None, linkify=False):
    """Formata dados da SSA como HTML com highlight opcional."""
    HIDDEN_DETAIL_FIELDS = {"id", "derivada_de"}

    if font_size_pt is None:
        font_size_pt = DETAILS_DIALOG_FONT_SIZE

    search_terms = _collect_highlight_terms(self) if highlight_search_terms else []

    try:
        from PyQt6.QtGui import QPalette as _QPal

        text_color = self.palette().color(_QPal.ColorRole.WindowText).name()
        link_color = self.palette().color(_QPal.ColorRole.Highlight).name()
    except Exception:
        text_color = "#000000"
        link_color = text_color

    html_lines = [
        (
            f'<html><body style="font-family: {MONO_FONT_FAMILY}; '
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
        display_name = DETAIL_DISPLAY_OVERRIDES.get(col, self.internal_to_display.get(col, col))
        if highlight_search_terms and search_terms:
            formatted_value = _highlight_text(self, formatted_value, search_terms)
        else:
            formatted_value = html_module.escape(formatted_value)

        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; width: 30%; vertical-align: top;\">"
            f"{html_module.escape(display_name)}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{formatted_value}</td>"
            f"</tr>"
        )

    try:
        derived_list = _get_derivadas_for_ssa(self, series.get("numero_ssa"))
    except Exception:
        derived_list = []
    if derived_list:
        if linkify:
            items = []
            for item in derived_list:
                href = _normalize_ssa_value(self, item)
                display = html_module.escape(item)
                items.append(
                    f'<a href="ssa://{href}" style="color:{link_color}; '
                    f"text-decoration:none; border-bottom: 1px solid {link_color};\">"
                    f"{display}</a>"
                )
            derived_text = ", ".join(items)
        else:
            derived_text = ", ".join(derived_list)
            if highlight_search_terms and search_terms:
                derived_text = _highlight_text(self, derived_text, search_terms)
            else:
                derived_text = html_module.escape(derived_text)
        label = f"SSAs derivadas ({len(derived_list)})"
        html_lines.append(
            f"<tr>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; '
            f"font-weight: bold; width: 30%; vertical-align: top;\">"
            f"{html_module.escape(label)}:</td>"
            f'<td style="padding: {DETAILS_DIALOG_TABLE_PADDING}px; '
            f'border-bottom: 1px solid {DETAILS_DIALOG_BORDER_COLOR}; width: 70%;">'
            f"{derived_text}</td>"
            f"</tr>"
        )

    html_lines.append("</table></body></html>")
    return "\n".join(html_lines)


def _normalize_ssa_value(self, value):
    try:
        raw = value or ""
    except Exception:
        raw = ""
    text = str(raw).strip()
    if not text:
        return ""
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


def _normalize_ssa_series(self, series: pd.Series) -> pd.Series:
    """Normaliza valores de SSA em modo vetorizado (mais rapido que apply)."""
    try:
        s = series.astype(str).str.strip()
        lowered = s.str.casefold()
        empty_mask = s.eq("") | lowered.isin(("nan", "none", "nat", "<na>"))
        digits = s.str.replace(r"\D+", "", regex=True)
        out = digits.where(digits.ne(""), lowered)
        return out.where(~empty_mask, "")
    except Exception as exc:
        logger.debug("Falha ao normalizar SSA series; fallback apply: %s", exc)
        try:
            return series.apply(lambda value: _normalize_ssa_value(self, value))
        except Exception:
            return pd.Series([""] * len(series), index=getattr(series, "index", None))


def update_details_from_selection(self):
    """Atualiza o painel de detalhes com base na linha selecionada."""
    if self.table_widget.rowCount() == 0:
        self.details_text.clear()
        return
    selected_rows = self.table_widget.selectionModel().selectedRows()
    if not selected_rows:
        self.details_text.clear()
        return
    row = selected_rows[0].row()
    series = self._get_series_from_row(row)
    if series is None:
        self.details_text.clear()
        return

    try:
        font_size_pt = None
        if hasattr(self, "details_group"):
            try:
                base_font = self.details_group.font()
                size = base_font.pointSizeF()
                if size <= 0:
                    size = float(base_font.pointSize())
                if size > 0:
                    font_size_pt = max(size - 1.0, 8.0)
            except Exception:
                font_size_pt = None
        html_content = _format_details_html(
            self,
            series,
            highlight_search_terms=True,
            font_size_pt=font_size_pt,
            linkify=True,
        )
        self.details_text.setHtml(html_content)
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
        if col in {"id", "derivada_de"} or str(col).startswith("_"):
            continue
        formatted_value = format_cell(value, col)
        if not formatted_value:
            continue
        display_name = DETAIL_DISPLAY_OVERRIDES.get(col, self.internal_to_display.get(col, col))
        lines.append(f"{display_name}: {formatted_value}")
    details_str = "\n".join(lines)
    try:
        self.details_text.setPlainText(details_str)
    except Exception as exc:
        logger.debug("Falha ao renderizar detalhes em texto simples: %s", exc)


def _get_derivadas_for_ssa(self, numero_ssa):
    if self.df_completo is None or self.df_completo.empty:
        return []
    if "derivada_de" not in self.df_completo.columns or "numero_ssa" not in self.df_completo.columns:
        return []
    num_norm = _normalize_ssa_value(self, numero_ssa)
    if not num_norm:
        return []
    try:
        series_norm = _normalize_ssa_series(self, self.df_completo["derivada_de"])
        mask = series_norm.eq(num_norm)
        derived_raw = self.df_completo.loc[mask, "numero_ssa"].tolist()
        derived = []
        for value in derived_raw:
            formatted = format_cell(value, "numero_ssa")
            if formatted:
                derived.append(formatted)
        return derived
    except Exception as exc:
        logger.debug("Falha ao coletar derivadas para SSA %s: %s", numero_ssa, exc)
        return []


def _jump_to_ssa(self, numero_ssa):
    num_norm = _normalize_ssa_value(self, numero_ssa)
    if not num_norm:
        return
    try:
        df_reset = self.df_exibido.reset_index(drop=True)
        if "numero_ssa" not in df_reset.columns:
            return
        series_norm = _normalize_ssa_series(self, df_reset["numero_ssa"])
        mask = series_norm.eq(num_norm)
        if not mask.any():
            self.search_input.setText(f"={num_norm}")
            self.initiate_filtering()
            return
        pos = int(mask[mask].index[0])
        page_size = int(getattr(self.paginator, "page_size", 50))
        page = int(pos // page_size + 1)
        try:
            self.paginator.current_page = page
        except Exception as exc:
            logger.debug("Falha ao atualizar pagina atual no salto para SSA %s: %s", num_norm, exc)
        self.display_current_page(page)
        row_in_page = int(pos % page_size)
        try:
            self.table_widget.selectRow(row_in_page)
        except Exception as exc:
            logger.debug("Falha ao selecionar linha %s no salto para SSA %s: %s", row_in_page, num_norm, exc)
    except Exception as exc:
        logger.debug("Falha ao navegar para SSA %s: %s", numero_ssa, exc)


def _on_details_anchor_clicked(self, url):
    try:
        href = url.toString()
    except Exception:
        return
    if not href:
        return
    if href.startswith("ssa://"):
        target = href[len("ssa://") :]
    elif href.startswith("ssa:"):
        target = href[len("ssa:") :]
    else:
        return
    target = target.strip().lstrip("/")
    if target:
        _jump_to_ssa(self, target)


def _filter_by_derivadas(self, numero_ssa):
    num_norm = _normalize_ssa_value(self, numero_ssa)
    if not num_norm:
        return
    self._last_derivada_origem = num_norm
    self._active_column_filters["derivada_de"] = num_norm
    try:
        self._build_column_filters_panel()
    except Exception as exc:
        logger.warning("Falha ao reconstruir painel de filtros ao filtrar por derivadas: %s", exc)
    self._refresh_after_filter_change()


def _clear_derivadas_filter(self):
    if "derivada_de" in self._active_column_filters:
        self._active_column_filters.pop("derivada_de", None)
    try:
        self._build_column_filters_panel()
    except Exception as exc:
        logger.warning("Falha ao reconstruir painel de filtros ao limpar filtro de derivadas: %s", exc)
    self._refresh_after_filter_change()
    if self._last_derivada_origem:
        _jump_to_ssa(self, self._last_derivada_origem)
        self._last_derivada_origem = None
