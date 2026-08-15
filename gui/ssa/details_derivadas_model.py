"""Pure model builders for SSA details derivadas views."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import chain
from typing import Any, Callable, Mapping, cast

from gui.ssa.details_relation_rules import is_secondary_relation
from shared.numero_ssa import normalize_relation_id as normalize_numero_ssa_relation


def normalize_relation_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
    normalized = str(normalize_numero_ssa_relation(value) or "").strip()
    if normalized:
        return normalized
    text = str(value).strip()
    lowered = text.casefold()
    if lowered in ("", "nan", "none", "nat", "<na>"):
        return ""
    if text.isdigit():
        return text
    if "." in text:
        whole, fractional = text.split(".", 1)
        if whole.isdigit() and fractional and set(fractional) <= {"0"}:
            return whole
    return ""


def empty_tree_data() -> dict[str, object]:
    return {
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


def normalize_tree_data(
    *,
    target: str,
    snapshot: Mapping[str, object] | None,
    fallback_children: list[object],
    direct_parent: str,
    local_payload: Mapping[str, object] | None,
    related: list[dict[str, str]],
    target_status: str,
) -> dict[str, object]:
    if not target:
        return empty_tree_data()

    state = _tree_state_from_snapshot(snapshot)
    parents = state["parents"]
    children = state["children"]
    descendants = state["descendants"]
    ancestors = state["ancestors"]
    profile = state["profile"]
    family_roots = state["family_roots"]
    family_descendants = state["family_descendants"]
    descendants_partial = state["descendants_partial"]

    if not children:
        children = list(fallback_children)
    else:
        children = _normalize_values(children)
    parents = _normalize_values(parents)
    if not parents and direct_parent:
        parents = [direct_parent]

    descendants = _normalize_descendants(descendants)
    ancestors = _normalize_ancestors(ancestors)
    ancestors.sort(key=_ancestor_sort_key)
    if not family_roots and ancestors:
        family_roots = _family_roots_from_ancestors(ancestors)
    if not family_roots:
        family_roots = list(dict.fromkeys(parents or [target]))

    if not family_descendants and local_payload:
        local_state = _local_family_state(local_payload)
        if local_state["parents"] and not parents:
            parents = local_state["parents"]
        if local_state["children"] and not children:
            children = local_state["children"]
        if local_state["family_roots"] and not family_roots:
            family_roots = local_state["family_roots"]
        family_descendants = local_state["family_descendants"]
        descendants_partial = local_state["descendants_partial"]

    if family_descendants:
        descendants = family_descendants
    family_child_values = {
        normalize_relation_value(raw.get("ssa"))
        for raw in family_descendants
        if isinstance(raw, dict)
    }
    render_family = bool(
        family_descendants
        and family_roots
        and (target in family_roots or target in family_child_values)
    )
    direct_children_count = _int_or_default(profile.get("direct_children_count"), len(children))
    profile_descendants_count = _int_or_default(profile.get("descendants_count"), 0)
    if profile_descendants_count > 0:
        descendants_count = profile_descendants_count
    elif descendants_partial:
        descendants_count = len(descendants) + 1
    else:
        descendants_count = len(descendants) or len(children)

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


@dataclass(frozen=True)
class DerivadasTreeRenderModel:
    target: str
    lineage: list[object]
    descendants_entries: list[object]
    child_map: dict[str, list[object]]
    direct_children: list[object]
    entry_by_ssa: dict[str, object]
    family_roots: list[str]
    render_family: bool
    hidden_descendants: int
    related_entries: list[object]


def build_tree_render_model(data: Mapping[str, object]) -> DerivadasTreeRenderModel | None:
    target = normalize_relation_value(data.get("target", ""))
    if not target:
        return None

    lineage = _lineage_entries(data)
    descendants_entries = _list_entries(data.get("descendants", []))
    child_map = _child_entry_map(descendants_entries)
    direct_children = _list_entries(data.get("children", []))
    entry_by_ssa = _entry_lookup_by_ssa(lineage, descendants_entries, direct_children)

    family_roots = _normalize_values(data.get("family_roots", []))
    render_family = bool(data.get("render_family")) and bool(family_roots)
    hidden_descendants = _hidden_count(
        data.get("descendants_count"),
        len(descendants_entries),
        partial=bool(data.get("descendants_partial")),
    )
    related_entries = _list_entries(data.get("related", []))
    return DerivadasTreeRenderModel(
        target=target,
        lineage=lineage,
        descendants_entries=descendants_entries,
        child_map=child_map,
        direct_children=direct_children,
        entry_by_ssa=entry_by_ssa,
        family_roots=family_roots,
        render_family=render_family,
        hidden_descendants=hidden_descendants,
        related_entries=related_entries,
    )


@dataclass(frozen=True)
class DerivadasGraphModel:
    target: str
    nodes: set[str]
    edges: list[tuple[str, str]]
    dashed_edges: set[tuple[str, str]]
    positions: dict[str, tuple[float, float]]
    svg_width: int
    svg_height: int
    offset_x: float
    offset_y: float
    descendants_count: int
    truncated: int


def build_mermaid_text(
    data: Mapping[str, object],
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> str:
    target = normalizer(data.get("target", ""))
    if not target:
        return ""

    node_ids: dict[str, str] = {}

    def node_id(value: str) -> str:
        cached = node_ids.get(value)
        if cached is not None:
            return cached
        resolved = _node_id(value)
        node_ids[value] = resolved
        return resolved

    lines = ["flowchart LR"]
    lines.append(f'  {node_id(target)}["{_label(target)}"]')
    edge_seen: set[tuple[str, str, bool]] = set()

    for parent in _normalize_values(data.get("parents", []), normalizer=normalizer):
        edge = (parent, target, False)
        if edge in edge_seen:
            continue
        edge_seen.add(edge)
        lines.append(f'  {node_id(parent)}["{_label(parent)}"] --> {node_id(target)}')

    for child in _normalize_values(data.get("children", []), normalizer=normalizer):
        edge = (target, child, False)
        if edge in edge_seen:
            continue
        edge_seen.add(edge)
        lines.append(f'  {node_id(target)} --> {node_id(child)}["{_label(child)}"]')

    for raw in _dict_entries(data.get("descendants", [])):
        ssa = normalizer(raw.get("ssa", ""))
        parent = normalizer(raw.get("parent", ""))
        if not ssa:
            continue
        if parent:
            edge = (parent, ssa, False)
            if edge in edge_seen:
                continue
            edge_seen.add(edge)
            lines.append(f'  {node_id(parent)} --> {node_id(ssa)}["{_label(ssa)}"]')
        else:
            edge = (target, ssa, True)
            if edge in edge_seen:
                continue
            edge_seen.add(edge)
            lines.append(f'  {node_id(target)} -.-> {node_id(ssa)}["{_label(ssa)}"]')

    for raw in _dict_entries(data.get("related", [])):
        related_ssa = normalizer(raw.get("ssa", ""))
        if not related_ssa:
            continue
        edge = (target, related_ssa, True)
        if edge in edge_seen:
            continue
        edge_seen.add(edge)
        lines.append(
            f'  {node_id(target)} -.-> {node_id(related_ssa)}["{_label(related_ssa)}"]'
        )
    return "\n".join(lines)


def build_graph_model(
    data: Mapping[str, object],
    *,
    max_descendants: int,
    node_width: float,
    node_height: float,
    x_gap: float,
    y_gap: float,
    margin: float,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> DerivadasGraphModel | None:
    target = normalizer(data.get("target"))
    if not target:
        return None

    parents = _normalize_values(data.get("parents", []), normalizer=normalizer)
    children = _normalize_values(data.get("children", []), normalizer=normalizer)
    descendants_entries = _list_entries(data.get("descendants", []))
    descendants = _normalize_graph_descendants(
        descendants_entries, max_descendants, normalizer=normalizer
    )
    nodes: set[str] = {target}
    edges: list[tuple[str, str]] = []
    dashed_edges: set[tuple[str, str]] = set()
    edge_seen: set[tuple[str, str]] = set()

    def add_edge(source: str, target_node: str, *, dashed: bool = False) -> None:
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

    for parent in parents:
        add_edge(parent, target)
    for child in children:
        add_edge(target, child)
    for row in descendants:
        descendant = str(row.get("ssa", "") or "")
        parent = str(row.get("parent", "") or "")
        dashed = is_secondary_relation(row)
        if parent:
            add_edge(parent, descendant, dashed=dashed)
        else:
            add_edge(target, descendant, dashed=True)
    for raw in _dict_entries(data.get("related", [])):
        related_ssa = normalizer(raw.get("ssa"))
        if related_ssa:
            add_edge(target, related_ssa, dashed=True)

    ordered_nodes = _ordered_graph_nodes(
        data,
        target=target,
        children=children,
        descendants_entries=cast(list[object], descendants),
        normalizer=normalizer,
    )
    positioned_nodes = {node for node, _depth in ordered_nodes}
    if missing_nodes := nodes - positioned_nodes:
        depth_by_node = dict(ordered_nodes)
        fallback_depth = max(depth_by_node.values(), default=0) + 1
        for missing_node in sorted(missing_nodes):
            missing_depth = fallback_depth
            if missing_node == target:
                parent_depths = [
                    depth_by_node[parent]
                    for parent in parents
                    if parent in depth_by_node
                ]
                if parent_depths:
                    missing_depth = min(parent_depths) + 1
                else:
                    missing_depth = min(fallback_depth, len(parents))
            ordered_nodes.append((missing_node, missing_depth))
            depth_by_node[missing_node] = missing_depth
    positions = {
        node: (margin + depth * x_gap, margin + index * y_gap)
        for index, (node, depth) in enumerate(ordered_nodes)
    }
    if not positions:
        return None

    min_x = min(x - node_width / 2.0 for x, _ in positions.values())
    max_x = max(x + node_width / 2.0 for x, _ in positions.values())
    min_y = min(y - node_height / 2.0 for _, y in positions.values())
    max_y = max(y + node_height / 2.0 for _, y in positions.values())
    offset_x = margin - min_x
    offset_y = margin - min_y
    descendants_count = _int_or_default(data.get("descendants_count"), 0)
    truncated = _hidden_count(
        data.get("descendants_count"),
        len(descendants),
        partial=bool(data.get("descendants_partial")),
    )
    return DerivadasGraphModel(
        target=target,
        nodes=nodes,
        edges=edges,
        dashed_edges=dashed_edges,
        positions=positions,
        svg_width=int(max_x - min_x + margin * 2),
        svg_height=int(max_y - min_y + margin * 2),
        offset_x=offset_x,
        offset_y=offset_y,
        descendants_count=descendants_count,
        truncated=truncated,
    )


def _normalize_values(
    entries: object,
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> list[str]:
    if not isinstance(entries, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in entries:
        value = normalizer(raw)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _tree_state_from_snapshot(
    snapshot: Mapping[str, object] | None,
) -> dict[str, Any]:
    if not snapshot:
        return {
            "parents": [],
            "children": [],
            "descendants": [],
            "ancestors": [],
            "profile": {},
            "family_roots": [],
            "family_descendants": [],
            "descendants_partial": False,
        }
    raw_profile = snapshot.get("hierarchy_profile", {}) or {}
    return {
        "parents": _list_entries(snapshot.get("parents", [])),
        "children": _list_entries(snapshot.get("children", [])),
        "descendants": _list_entries(snapshot.get("descendants", [])),
        "ancestors": _list_entries(snapshot.get("ancestors", [])),
        "profile": raw_profile if isinstance(raw_profile, Mapping) else {},
        "family_roots": _normalize_values(snapshot.get("family_roots", [])),
        "family_descendants": _dict_entries(snapshot.get("family_descendants", [])),
        "descendants_partial": bool(snapshot.get("family_truncated")),
    }


def _local_family_state(payload: Mapping[str, object]) -> dict[str, Any]:
    return {
        "parents": _list_entries(payload.get("parents", [])),
        "children": _list_entries(payload.get("children", [])),
        "family_roots": _normalize_values(payload.get("family_roots", [])),
        "family_descendants": _dict_entries(payload.get("family_descendants", [])),
        "descendants_partial": bool(payload.get("family_truncated")),
    }


def _list_entries(entries: object) -> list[object]:
    return list(cast(list[object], entries)) if isinstance(entries, list) else []


def _dict_entries(entries: object) -> list[dict[str, object]]:
    return [
        cast(dict[str, object], raw)
        for raw in _list_entries(entries)
        if isinstance(raw, dict)
    ]


def _normalize_descendants(entries: list[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child, parent = _normalized_child_parent(raw_map)
        if child:
            normalized.append({**raw_map, "ssa": child, "parent": parent})
    return normalized


def _normalize_ancestors(entries: list[object]) -> list[object]:
    normalized: list[object] = []
    for raw in entries:
        if isinstance(raw, dict):
            raw_map = cast(dict[str, object], raw)
            ancestor_value = normalize_relation_value(raw_map.get("ssa"))
            if ancestor_value:
                normalized.append({**raw_map, "ssa": ancestor_value})
            continue
        ancestor_value = normalize_relation_value(raw)
        if ancestor_value:
            normalized.append(ancestor_value)
    return normalized


def _ancestor_sort_key(entry: object) -> tuple[int, str]:
    if not isinstance(entry, dict):
        return (0, normalize_relation_value(entry))
    raw_map = cast(dict[str, object], entry)
    raw_distance = raw_map.get("min_distance")
    distance = raw_distance if isinstance(raw_distance, int) else 0
    return (-distance, normalize_relation_value(raw_map.get("ssa")))


def _family_roots_from_ancestors(ancestors: list[object]) -> list[str]:
    roots: list[str] = []
    root_distance = None
    for raw in ancestors:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        raw_distance = raw_map.get("min_distance")
        if not isinstance(raw_distance, int):
            continue
        distance = raw_distance
        if root_distance is None:
            root_distance = distance
        if distance == root_distance:
            root_value = normalize_relation_value(raw_map.get("ssa"))
            if root_value and root_value not in roots:
                roots.append(root_value)
    return roots


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped)
        except ValueError:
            return default
    return default


def _hidden_count(total: object, visible_count: int, *, partial: bool = False) -> int:
    hidden = max(0, _int_or_default(total, 0) - visible_count)
    if partial and hidden == 0:
        return 1
    return hidden


def _entry_ssa(
    entry: object,
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> str:
    if isinstance(entry, dict):
        return normalizer(cast(dict[str, object], entry).get("ssa"))
    return normalizer(entry)


def _lineage_entries(data: Mapping[str, object]) -> list[object]:
    ancestors_entries = _list_entries(data.get("ancestors", []))
    if not ancestors_entries:
        ancestors_entries = _list_entries(data.get("parents", []))
    lineage: list[object] = []
    lineage_seen: set[str] = set()
    for raw in ancestors_entries:
        normalized = _entry_ssa(raw)
        if not normalized or normalized in lineage_seen:
            continue
        lineage_seen.add(normalized)
        lineage.append(raw)
    return lineage


def _child_entry_map(
    entries: list[object],
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> dict[str, list[object]]:
    child_map: dict[str, list[object]] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child_value, parent_value = _normalized_child_parent(
            raw_map, normalizer=normalizer
        )
        if not child_value or not parent_value:
            continue
        child_map.setdefault(parent_value, []).append(raw)
    for child_values in child_map.values():
        child_values.sort(
            key=lambda entry: _entry_ssa(entry, normalizer=normalizer) or ""
        )
    return child_map


def _entry_lookup_by_ssa(
    lineage: list[object],
    descendants: list[object],
    direct_children: list[object],
) -> dict[str, object]:
    entry_by_ssa: dict[str, object] = {}
    for raw in chain(lineage, descendants, direct_children):
        normalized = _entry_ssa(raw)
        if normalized and normalized not in entry_by_ssa:
            entry_by_ssa[normalized] = raw
    return entry_by_ssa


def _normalized_child_parent(
    raw_map: Mapping[str, object],
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> tuple[str, str]:
    return normalizer(raw_map.get("ssa")), normalizer(raw_map.get("parent"))


def _node_id(value: str) -> str:
    if value.isdigit():
        return f"N{value}"
    stable_hash = hashlib.md5(
        value.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()[:12]
    return f"N_{stable_hash}"


def _label(value: str) -> str:
    return str(value).replace('"', "'")


def _normalize_graph_descendants(
    entries: list[object],
    max_descendants: int,
    *,
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> list[dict[str, object]]:
    descendants: list[dict[str, object]] = []
    for raw in entries[:max_descendants]:
        if not isinstance(raw, dict):
            continue
        raw_map = cast(dict[str, object], raw)
        child, parent = _normalized_child_parent(raw_map, normalizer=normalizer)
        if not child:
            continue
        row: dict[str, object] = {"ssa": child, "parent": parent}
        if raw_map.get("relation_type") is not None:
            row["relation_type"] = raw_map.get("relation_type")
        if raw_map.get("relation_raw_label"):
            row["relation_raw_label"] = raw_map.get("relation_raw_label")
        descendants.append(row)
    return descendants


def _ordered_graph_nodes(
    data: Mapping[str, object],
    *,
    target: str,
    children: list[str],
    descendants_entries: list[object],
    normalizer: Callable[[object], str] = normalize_relation_value,
) -> list[tuple[str, int]]:
    lineage = [
        node
        for raw in _lineage_entries(data)
        if (node := _entry_ssa(raw, normalizer=normalizer))
    ]
    child_map = {
        parent: [
            child_ssa
            for child in child_entries
            if (child_ssa := _entry_ssa(child, normalizer=normalizer))
        ]
        for parent, child_entries in _child_entry_map(
            descendants_entries, normalizer=normalizer
        ).items()
    }
    reversed_child_map = {
        parent: tuple(reversed(child_values))
        for parent, child_values in child_map.items()
    }

    ordered_nodes: list[tuple[str, int]] = []
    family_roots = _normalize_values(data.get("family_roots", []), normalizer=normalizer)
    render_family = bool(data.get("render_family")) and bool(child_map) and bool(family_roots)
    target_depth = len(lineage)
    seen_nodes: set[str] = set()

    def append_node(node: str, depth: int) -> None:
        if not node or node in seen_nodes:
            return
        seen_nodes.add(node)
        ordered_nodes.append((node, depth))

    if render_family:
        if target not in family_roots and not any(
            target in child_values for child_values in child_map.values()
        ):
            append_node(target, target_depth)
        for root in family_roots:
            stack = [(root, 0)]
            while stack:
                node, depth = stack.pop()
                if not node or node in seen_nodes:
                    continue
                append_node(node, depth)
                for child_ssa in reversed_child_map.get(node, ()):
                    if child_ssa not in seen_nodes:
                        stack.append((child_ssa, depth + 1))
    else:
        for depth, node in enumerate(lineage):
            append_node(node, depth)
        append_node(target, target_depth)

        def append_descendant_nodes(parent_ssa: str, depth: int) -> None:
            stack = [
                (child_ssa, depth)
                for child_ssa in reversed_child_map.get(parent_ssa, ())
            ]
            while stack:
                child_ssa, child_depth = stack.pop()
                if child_ssa in seen_nodes:
                    continue
                append_node(child_ssa, child_depth)
                for nested_child in reversed_child_map.get(child_ssa, ()):
                    if nested_child not in seen_nodes:
                        stack.append((nested_child, child_depth + 1))

        for child_ssa in children:
            if not child_ssa or child_ssa in seen_nodes:
                continue
            append_node(child_ssa, target_depth + 1)
            append_descendant_nodes(child_ssa, target_depth + 2)

    related_entries = data.get("related", [])
    if isinstance(related_entries, list):
        for raw in related_entries:
            if not isinstance(raw, dict):
                continue
            related_ssa = normalizer(cast(dict[str, object], raw).get("ssa"))
            if not related_ssa or related_ssa in seen_nodes:
                continue
            append_node(related_ssa, target_depth + 1)
    return ordered_nodes
