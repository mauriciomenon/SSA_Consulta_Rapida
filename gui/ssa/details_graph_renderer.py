"""SVG/HTML renderer for SSA derivadas graph."""

from __future__ import annotations

import html as html_module
import re
from typing import Mapping

from gui.helpers.theme_helpers import pick_css_color
from gui.ssa import details_derivadas_model
from gui.ssa.details_dialog_constants import (
    DERIVADAS_GRAPH_MARGIN,
    DERIVADAS_GRAPH_MAX_DESCENDANTS,
    DERIVADAS_GRAPH_NODE_HEIGHT,
    DERIVADAS_GRAPH_NODE_WIDTH,
    DERIVADAS_GRAPH_X_GAP,
    DERIVADAS_GRAPH_Y_GAP,
)
from utils.themes import get_theme_roles

_CSS_FONT_FAMILY_RE = re.compile(r"^[\w\s,.-]+$")


def build_derivadas_graph_html(
    *,
    current_theme: str,
    data: Mapping[str, object],
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
    )
    if graph_model is None:
        return ""

    safe_font_family = _safe_font_family(font_family)
    node_w = DERIVADAS_GRAPH_NODE_WIDTH
    node_h = DERIVADAS_GRAPH_NODE_HEIGHT
    theme_roles = get_theme_roles(current_theme)
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
    node_target_text = _contrast_text_color(node_target_fill, fallback=text_color)
    node_stroke = pick_css_color(
        link_color,
        theme_roles.get("border"),
        fallback="#4a90e2",
    )

    svg_lines = _build_svg_lines(
        graph_model=graph_model,
        node_w=node_w,
        node_h=node_h,
        node_fill=node_fill,
        node_target_fill=node_target_fill,
        node_target_text=node_target_text,
        node_stroke=node_stroke,
        text_color=text_color,
        font_family=safe_font_family,
    )
    summary = _graph_summary(graph_model)
    return (
        "<html><body style="
        f'"font-family:{html_module.escape(safe_font_family)}; margin:6px;">'
        "<div style='margin-bottom:6px; font-weight:600;'>Grafo de derivadas</div>"
        f"{''.join(svg_lines)}"
        f"<div style='margin-top:8px; opacity:0.85;'>{html_module.escape(summary)}</div>"
        "</body></html>"
    )


def _build_svg_lines(
    *,
    graph_model: details_derivadas_model.DerivadasGraphModel,
    node_w: int,
    node_h: int,
    node_fill: str,
    node_target_fill: str,
    node_target_text: str,
    node_stroke: str,
    text_color: str,
    font_family: str,
) -> list[str]:
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{graph_model.svg_width}" '
        f'height="{graph_model.svg_height}" viewBox="0 0 {graph_model.svg_width} {graph_model.svg_height}">',
        "<defs>",
        '<marker id="arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="1.7" orient="auto">',
        f'<polygon points="0 0, 4 1.7, 0 3.4" fill="{node_stroke}" />',
        "</marker>",
        "</defs>",
    ]
    svg_lines.extend(
        _edge_lines(
            graph_model=graph_model,
            node_w=node_w,
            node_stroke=node_stroke,
        )
    )
    svg_lines.extend(
        _node_lines(
            graph_model=graph_model,
            node_w=node_w,
            node_h=node_h,
            node_fill=node_fill,
            node_target_fill=node_target_fill,
            node_target_text=node_target_text,
            node_stroke=node_stroke,
            text_color=text_color,
            font_family=font_family,
        )
    )
    svg_lines.append("</svg>")
    return svg_lines


def _edge_lines(
    *,
    graph_model: details_derivadas_model.DerivadasGraphModel,
    node_w: int,
    node_stroke: str,
) -> list[str]:
    lane_counters: dict[tuple[str, int], int] = {}
    lines: list[str] = []
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
        mid_x = _compute_lane_x(lane_counters, source, x1, x2)
        dash_attr = (
            ' stroke-dasharray="7 6"'
            if (source, target_node) in graph_model.dashed_edges
            else ""
        )
        safe_source = html_module.escape(source, quote=True)
        safe_target_node = html_module.escape(target_node, quote=True)
        lines.append(
            f'<path data-from="{safe_source}" data-to="{safe_target_node}" '
            f'd="M{x1:.1f},{y1:.1f} L{mid_x:.1f},{y1:.1f} '
            f'L{mid_x:.1f},{y2:.1f} L{x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{node_stroke}" stroke-width="0.9" '
            f'marker-end="url(#arrow)"{dash_attr} />'
        )
    return lines


def _node_lines(
    *,
    graph_model: details_derivadas_model.DerivadasGraphModel,
    node_w: int,
    node_h: int,
    node_fill: str,
    node_target_fill: str,
    node_target_text: str,
    node_stroke: str,
    text_color: str,
    font_family: str,
) -> list[str]:
    lines: list[str] = []
    for node, (x, y) in graph_model.positions.items():
        x0 = x - node_w / 2.0 + graph_model.offset_x
        y0 = y - node_h / 2.0 + graph_model.offset_y
        fill = node_target_fill if node == graph_model.target else node_fill
        node_text_color = node_target_text if node == graph_model.target else text_color
        safe_node = html_module.escape(node)
        lines.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{node_w}" height="{node_h}" '
            f'rx="5" ry="5" fill="{fill}" stroke="{node_stroke}" stroke-width="0.8" />'
        )
        lines.append(
            f'<text x="{(x0 + node_w / 2.0):.1f}" y="{(y0 + node_h / 2.0):.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="{html_module.escape(font_family)}" font-size="{_node_font_size(node, node_w, node_h):.1f}" fill="{node_text_color}">{safe_node}</text>'
        )
    return lines


def _safe_font_family(value: str) -> str:
    text = str(value or "").strip()
    if text and _CSS_FONT_FAMILY_RE.fullmatch(text):
        return text
    return "sans-serif"


def _contrast_text_color(fill_color: str, *, fallback: str) -> str:
    text = str(fill_color or "").strip()
    if not text.startswith("#") or len(text) not in (4, 7):
        return fallback
    if len(text) == 4:
        text = "#" + "".join(ch * 2 for ch in text[1:])
    try:
        red = int(text[1:3], 16)
        green = int(text[3:5], 16)
        blue = int(text[5:7], 16)
    except ValueError:
        return fallback
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return "#101820" if luminance >= 0.48 else "#f5f7fb"


def _compute_lane_x(
    lane_counters: dict[tuple[str, int], int],
    source: str,
    x1: float,
    x2: float,
) -> float:
    direction = 1 if x2 >= x1 else -1
    lane_key = (source, direction)
    lane_index = lane_counters.get(lane_key, 0)
    lane_counters[lane_key] = lane_index + 1
    span = x2 - x1 if direction > 0 else x1 - x2
    if span <= 0:
        return x1
    min_offset = min(2.0, span / 2.0)
    max_offset = max(min_offset, span - min_offset)
    lane_delta = min(max(min_offset, float(lane_index + 1) * 3.0), max_offset)
    final_mid_x = x1 + (direction * lane_delta)
    return final_mid_x


def _node_font_size(value: str, node_w: int, node_h: int) -> float:
    usable_w = max(18.0, float(node_w) - 18.0)
    text_len = max(1, len(str(value or "")))
    by_width = usable_w / (text_len * 0.56)
    by_height = max(10.0, float(node_h) * 0.56)
    return max(11.0, min(by_width, by_height, 15.5))


def _graph_summary(
    graph_model: details_derivadas_model.DerivadasGraphModel,
) -> str:
    summary = (
        f"Total de nos: {len(graph_model.nodes)} | Total de relacoes: {len(graph_model.edges)} | "
        f"Descendentes: {graph_model.descendants_count}"
    )
    if graph_model.truncated > 0:
        return f"{summary} | Exibicao parcial de descendentes: +{graph_model.truncated}"
    return summary
