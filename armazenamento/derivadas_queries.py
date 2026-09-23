"""Read/query API for derivadas matrix, closure and summary tables."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Iterator, cast

from armazenamento.database import get_db_connection
from armazenamento.derivadas_schema import scan_derivadas_read_schema_readiness
from shared.numero_ssa import normalize_relation_id, normalize_strict

ALLOWED_TOP_METRICS = {
    "direct_children": "direct_children_count",
    "descendants": "descendants_count",
    "ancestors": "ancestors_count",
    "levels_below": "levels_below_max",
    "levels_above": "levels_above_max",
}
DERIVADAS_QUERY_BUSY_TIMEOUT_MS = 3000
DERIVADAS_MAX_DISTANCE_LIMIT = 64
DERIVADAS_FAMILY_NODE_LIMIT = 400
logger = logging.getLogger(__name__)


def _normalize_or_none(value: Any) -> str | None:
    return normalize_strict(value)


def _normalize_max_distance(max_distance: int | None) -> int | None:
    if max_distance is None:
        return None
    try:
        parsed = int(max_distance)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_distance must be an integer or None") from exc
    if parsed < 1:
        raise ValueError("max_distance must be >= 1 when provided")
    return min(parsed, DERIVADAS_MAX_DISTANCE_LIMIT)


@contextmanager
def _open_derivadas_connection(
    db_path: str,
) -> Iterator[tuple[sqlite3.Connection | None, bool]]:
    with get_db_connection(db_path) as conn:
        conn.execute(f"PRAGMA busy_timeout = {DERIVADAS_QUERY_BUSY_TIMEOUT_MS}")
        # Guardrail: query helpers are strictly read-only.
        conn.execute("PRAGMA query_only = ON")
        readiness = scan_derivadas_read_schema_readiness(conn)
        schema_ready = bool(readiness.get("is_ready"))
        if not schema_ready:
            yield None, False
            return
        yield conn, True


def get_parents(db_path: str, ssa: Any, *, include_inactive: bool = False) -> list[str]:
    child_ssa = _normalize_or_none(ssa)
    if not child_ssa:
        return []
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        if include_inactive:
            query = "SELECT parent_ssa FROM ssa_derivada_matrix WHERE child_ssa = ? ORDER BY parent_ssa"
            rows = conn.execute(query, (child_ssa,)).fetchall()
        else:
            query = "SELECT parent_ssa FROM ssa_derivada_matrix WHERE child_ssa = ? AND active = 1 ORDER BY parent_ssa"
            rows = conn.execute(query, (child_ssa,)).fetchall()
        return [row[0] for row in rows]


def get_parent(db_path: str, ssa: Any, *, include_inactive: bool = False) -> str | None:
    parents = get_parents(db_path, ssa, include_inactive=include_inactive)
    if len(parents) == 1:
        return parents[0]
    return None


def get_children(
    db_path: str, ssa: Any, *, include_inactive: bool = False
) -> list[str]:
    parent_ssa = _normalize_or_none(ssa)
    if not parent_ssa:
        return []
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        if include_inactive:
            query = "SELECT child_ssa FROM ssa_derivada_matrix WHERE parent_ssa = ? ORDER BY child_ssa"
            rows = conn.execute(query, (parent_ssa,)).fetchall()
        else:
            query = "SELECT child_ssa FROM ssa_derivada_matrix WHERE parent_ssa = ? AND active = 1 ORDER BY child_ssa"
            rows = conn.execute(query, (parent_ssa,)).fetchall()
        return [row[0] for row in rows]


def has_children(db_path: str, ssa: Any, *, include_inactive: bool = False) -> bool:
    return children_count(db_path, ssa, include_inactive=include_inactive) > 0


def children_count(db_path: str, ssa: Any, *, include_inactive: bool = False) -> int:
    parent_ssa = _normalize_or_none(ssa)
    if not parent_ssa:
        return 0
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return 0
        conn = cast(sqlite3.Connection, conn)
        if include_inactive:
            query = "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE parent_ssa = ?"
            value = conn.execute(query, (parent_ssa,)).fetchone()[0]
        else:
            query = "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE parent_ssa = ? AND active = 1"
            value = conn.execute(query, (parent_ssa,)).fetchone()[0]
        return int(value)


def get_ancestors(
    db_path: str, ssa: Any, *, max_distance: int | None = None
) -> list[dict[str, Any]]:
    descendant_ssa = _normalize_or_none(ssa)
    if not descendant_ssa:
        return []
    safe_max_distance = _normalize_max_distance(max_distance)
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        if safe_max_distance is not None:
            rows = conn.execute(
                """
                SELECT ancestor_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE descendant_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, ancestor_ssa
                """,
                (descendant_ssa, safe_max_distance),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT ancestor_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE descendant_ssa = ?
                ORDER BY min_distance, ancestor_ssa
                """,
                (descendant_ssa,),
            ).fetchall()
        return [
            {
                "ssa": row[0],
                "min_distance": int(row[1]),
                "max_distance": int(row[2]),
                "path_count": int(row[3]),
            }
            for row in rows
        ]


def get_descendants(
    db_path: str, ssa: Any, *, max_distance: int | None = None
) -> list[dict[str, Any]]:
    ancestor_ssa = _normalize_or_none(ssa)
    if not ancestor_ssa:
        return []
    safe_max_distance = _normalize_max_distance(max_distance)
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        if safe_max_distance is not None:
            rows = conn.execute(
                """
                SELECT descendant_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE ancestor_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, descendant_ssa
                """,
                (ancestor_ssa, safe_max_distance),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT descendant_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE ancestor_ssa = ?
                ORDER BY min_distance, descendant_ssa
                """,
                (ancestor_ssa,),
            ).fetchall()
        return [
            {
                "ssa": row[0],
                "min_distance": int(row[1]),
                "max_distance": int(row[2]),
                "path_count": int(row[3]),
            }
            for row in rows
        ]


def get_hierarchy_profile(db_path: str, ssa: Any) -> dict[str, Any]:
    target_ssa = _normalize_or_none(ssa)
    if not target_ssa:
        return {}
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return {}
        conn = cast(sqlite3.Connection, conn)
        row = conn.execute(
            """
            SELECT
                ssa,
                direct_parents_count,
                direct_children_count,
                ancestors_count,
                descendants_count,
                level_from_root_min,
                level_from_root_max,
                levels_above_max,
                levels_below_max,
                component_size,
                has_cycle,
                last_sync_at
            FROM ssa_derivada_summary
            WHERE ssa = ?
            """,
            (target_ssa,),
        ).fetchone()
        if row is not None:
            return {
                "ssa": row[0],
                "direct_parents_count": int(row[1]),
                "direct_children_count": int(row[2]),
                "ancestors_count": int(row[3]),
                "descendants_count": int(row[4]),
                "level_from_root_min": row[5],
                "level_from_root_max": row[6],
                "levels_above_max": int(row[7]),
                "levels_below_max": int(row[8]),
                "component_size": int(row[9]),
                "has_cycle": bool(row[10]),
                "last_sync_at": row[11],
            }

        # Fallback when summary table has no row for this SSA.
        direct_parents = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE child_ssa = ? AND active = 1",
            (target_ssa,),
        ).fetchone()[0]
        direct_children = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE parent_ssa = ? AND active = 1",
            (target_ssa,),
        ).fetchone()[0]
        return {
            "ssa": target_ssa,
            "direct_parents_count": int(direct_parents),
            "direct_children_count": int(direct_children),
            "ancestors_count": 0,
            "descendants_count": 0,
            "level_from_root_min": None,
            "level_from_root_max": None,
            "levels_above_max": 0,
            "levels_below_max": 0,
            "component_size": 1,
            "has_cycle": False,
            "last_sync_at": None,
        }


def _load_adjacency(conn: sqlite3.Connection, direction: str) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    if direction == "down":
        rows = conn.execute(
            "SELECT parent_ssa, child_ssa FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchall()
        for parent, child in rows:
            adjacency[parent].append(child)
    elif direction == "up":
        rows = conn.execute(
            "SELECT child_ssa, parent_ssa FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchall()
        for child, parent in rows:
            adjacency[child].append(parent)
    else:
        raise ValueError(f"Invalid direction: {direction}")
    for node in list(adjacency.keys()):
        adjacency[node] = sorted(set(adjacency[node]))
    return adjacency


def _collect_paths(
    adjacency: dict[str, list[str]],
    start_ssa: str,
    *,
    depth: int,
    max_nodes: int,
) -> list[list[str]]:
    if depth < 1:
        return [[start_ssa]]

    try:
        safe_max_nodes = int(max_nodes)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_nodes must be an integer") from exc
    if safe_max_nodes < 1:
        return [[start_ssa]]

    # max_nodes bounds the traversal to avoid path explosion on high-branching graphs.
    # We cap both:
    # - number of traversal states enqueued (controls memory/runtime)
    # - number of paths returned (controls output size)
    max_states = safe_max_nodes
    max_paths = safe_max_nodes
    max_stack = safe_max_nodes

    stack: list[tuple[str, list[str], set[str]]] = [
        (start_ssa, [start_ssa], {start_ssa})
    ]
    paths: list[list[str]] = []
    states_seen = 1
    truncated = False

    while stack and len(paths) < max_paths:
        node, path, seen = stack.pop()
        children = adjacency.get(node, [])
        # Depth is measured in edges; the node path has length edge_depth + 1.
        edge_depth = len(path) - 1
        if not children or edge_depth >= depth:
            paths.append(path)
            continue
        if states_seen >= max_states:
            truncated = True
            paths.append(path)
            continue

        produced_any = False
        for nxt in reversed(children):
            if len(paths) >= max_paths:
                truncated = True
                break
            if nxt in seen:
                paths.append(path + [nxt])
                produced_any = True
                continue
            if states_seen >= max_states:
                truncated = True
                break
            next_path = path + [nxt]
            stack.append((nxt, next_path, seen | {nxt}))
            states_seen += 1
            produced_any = True
            if len(stack) >= max_stack:
                truncated = True
                break

        if not produced_any and len(paths) < max_paths:
            # No expansion possible due to caps; keep a partial path so callers have deterministic output.
            paths.append(path)

    if stack and len(paths) >= max_paths:
        truncated = True
    if truncated:
        logger.warning(
            "Path traversal truncated for %s (depth=%s, max_nodes=%s, states=%s, paths=%s)",
            start_ssa,
            depth,
            safe_max_nodes,
            states_seen,
            len(paths),
        )
    if not paths:
        return [[start_ssa]]
    return paths


def get_paths_down(
    db_path: str,
    ssa: Any,
    *,
    depth: int = 5,
    max_nodes: int = 500,
) -> list[list[str]]:
    root = _normalize_or_none(ssa)
    if not root:
        return []
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        adjacency = _load_adjacency(conn, direction="down")
        return _collect_paths(adjacency, root, depth=depth, max_nodes=max_nodes)


def get_paths_up(
    db_path: str,
    ssa: Any,
    *,
    depth: int = 5,
    max_nodes: int = 500,
) -> list[list[str]]:
    child = _normalize_or_none(ssa)
    if not child:
        return []
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        adjacency = _load_adjacency(conn, direction="up")
        return _collect_paths(adjacency, child, depth=depth, max_nodes=max_nodes)


def build_family_payload_from_edges(
    ssa: Any,
    edges: list[tuple[Any, Any]],
    *,
    max_nodes: int = DERIVADAS_FAMILY_NODE_LIMIT,
    allow_relation_ids: bool = False,
) -> dict[str, Any]:
    normalizer = normalize_relation_id if allow_relation_ids else _normalize_or_none
    target_ssa = normalizer(ssa)
    if not target_ssa:
        return {
            "parents": [],
            "children": [],
            "family_roots": [],
            "family_descendants": [],
            "family_truncated": False,
        }
    safe_max_nodes = max(1, min(int(max_nodes), DERIVADAS_FAMILY_NODE_LIMIT))
    children_by_parent: dict[str, set[str]] = defaultdict(set)
    parents_by_child: dict[str, set[str]] = defaultdict(set)
    for parent_raw, child_raw in edges:
        parent = normalizer(parent_raw)
        child = normalizer(child_raw)
        if not parent or not child or parent == child:
            continue
        children_by_parent[parent].add(child)
        parents_by_child[child].add(parent)

    parents = sorted(parents_by_child.get(target_ssa, set()))
    children = sorted(children_by_parent.get(target_ssa, set()))
    family_roots: list[str] = []
    seen_ancestors: set[str] = set()
    stack = [(parent, 1) for parent in reversed(parents)]
    while stack:
        node, distance = stack.pop()
        if node in seen_ancestors:
            continue
        seen_ancestors.add(node)
        node_parents = sorted(parents_by_child.get(node, set()))
        if not node_parents:
            family_roots.append(node)
            continue
        for parent in reversed(node_parents):
            stack.append((parent, distance + 1))
    if not family_roots:
        family_roots = list(dict.fromkeys(parents or [target_ssa]))

    family_descendants: list[dict[str, Any]] = []
    replace_candidate_indexes: list[int] = []
    seen_edges: set[tuple[str, str]] = set()
    family_truncated = False

    priority_nodes: set[str] = {target_ssa}
    priority_stack = [target_ssa]
    while priority_stack:
        child = priority_stack.pop()
        for parent in sorted(parents_by_child.get(child, set()), reverse=True):
            if parent in priority_nodes:
                continue
            priority_nodes.add(parent)
            priority_stack.append(parent)

    queue = [(root, 0) for root in family_roots]
    queued_nodes = set(family_roots)
    distance_by_node = {root: 0 for root in family_roots}
    queue_index = 0
    while queue_index < len(queue) and len(family_descendants) < safe_max_nodes:
        parent, depth = queue[queue_index]
        queue_index += 1
        ordered_children = sorted(
            children_by_parent.get(parent, set()),
            key=lambda child: (0 if child in priority_nodes else 1, child),
        )
        for child_index, child in enumerate(ordered_children):
            edge = (parent, child)
            if edge in seen_edges:
                continue
            if len(family_descendants) >= safe_max_nodes:
                family_truncated = True
                if child_index < len(ordered_children):
                    break
            seen_edges.add(edge)
            node_distance = distance_by_node.get(child, depth + 1)
            family_descendants.append(
                {"ssa": child, "parent": parent, "min_distance": node_distance}
            )
            if child not in priority_nodes and parent != target_ssa:
                replace_candidate_indexes.append(len(family_descendants) - 1)
            if child not in queued_nodes:
                queued_nodes.add(child)
                distance_by_node[child] = depth + 1
                queue.append((child, depth + 1))
    if queue_index < len(queue):
        family_truncated = True
    for child in sorted(children_by_parent.get(target_ssa, set())):
        edge = (target_ssa, child)
        if edge in seen_edges:
            continue
        target_distance = distance_by_node.get(target_ssa, 0)
        required_row = {
            "ssa": child,
            "parent": target_ssa,
            "min_distance": target_distance + 1,
        }
        if len(family_descendants) < safe_max_nodes:
            family_descendants.append(required_row)
            seen_edges.add(edge)
            family_truncated = True
            continue
        replace_index = None
        while replace_candidate_indexes:
            index = replace_candidate_indexes.pop()
            row = family_descendants[index]
            row_parent = str(row.get("parent", "") or "")
            row_child = str(row.get("ssa", "") or "")
            if row_child in priority_nodes or row_parent == target_ssa:
                continue
            replace_index = index
            break
        if replace_index is None:
            family_truncated = True
            continue
        old_row = family_descendants[replace_index]
        seen_edges.discard(
            (
                str(old_row.get("parent", "") or ""),
                str(old_row.get("ssa", "") or ""),
            )
        )
        family_descendants[replace_index] = required_row
        seen_edges.add(edge)
        family_truncated = True

    return {
        "parents": parents,
        "children": children,
        "family_roots": family_roots,
        "family_descendants": family_descendants,
        "family_truncated": family_truncated,
    }


def _collect_family_subgraph(
    conn: sqlite3.Connection,
    *,
    target_ssa: str,
    parents: list[str],
    ancestor_rows: list[tuple[Any, ...]],
    safe_max_distance: int | None,
    safe_max_nodes: int,
) -> tuple[list[str], list[dict[str, Any]], bool]:
    family_roots: list[str] = []
    if ancestor_rows:
        ancestor_values = sorted({row[0] for row in ancestor_rows})
        ancestor_placeholders = ",".join("?" for _ in ancestor_values)
        ancestor_edge_rows = conn.execute(
            f"""
            SELECT parent_ssa, child_ssa
            FROM ssa_derivada_matrix
            WHERE active = 1
              AND child_ssa IN ({ancestor_placeholders})
            """,  # nosec B608  # skipcq: BAN-B608
            tuple(ancestor_values),
        ).fetchall()
        ancestors_with_parent = {
            child for parent, child in ancestor_edge_rows if parent in ancestor_values
        }
        family_roots = [
            value for value in ancestor_values if value not in ancestors_with_parent
        ]
    if not family_roots:
        family_roots = list(dict.fromkeys(parents or [target_ssa]))

    family_descendants: list[dict[str, Any]] = []
    family_truncated = False

    root_placeholders = ",".join("?" for _ in family_roots)
    family_depth_limit = safe_max_distance or DERIVADAS_MAX_DISTANCE_LIMIT
    family_limit = safe_max_nodes + 1
    family_node_rows = conn.execute(
        f"""
        SELECT descendant_ssa, MIN(min_distance) AS depth
        FROM ssa_derivada_closure
        WHERE ancestor_ssa IN ({root_placeholders})
          AND min_distance <= ?
        GROUP BY descendant_ssa
        ORDER BY depth, descendant_ssa
        LIMIT ?
        """,  # nosec B608  # skipcq: BAN-B608
        (*family_roots, family_depth_limit, family_limit),
    ).fetchall()
    family_truncated = len(family_node_rows) > safe_max_nodes
    distance_by_node = {
        row[0]: int(row[1]) for row in family_node_rows[:safe_max_nodes]
    }
    ancestor_distance_by_node = {row[0]: int(row[1]) for row in ancestor_rows}
    if ancestor_distance_by_node:
        distance_by_node.setdefault(target_ssa, max(ancestor_distance_by_node.values()))
    ordered_ancestors = sorted(
        ancestor_distance_by_node,
        key=lambda node: (-ancestor_distance_by_node[node], node),
    )
    node_candidates = list(
        dict.fromkeys(
            [*parents, target_ssa, *ordered_ancestors, *sorted(distance_by_node)]
        )
    )
    if len(node_candidates) > safe_max_nodes:
        family_truncated = True
    family_nodes = node_candidates[:safe_max_nodes]
    node_placeholders = ",".join("?" for _ in family_nodes)
    edge_rows = conn.execute(
        f"""
        SELECT DISTINCT parent_ssa, child_ssa, relation_type, relation_raw_label
        FROM ssa_derivada_matrix
        WHERE active = 1
          AND parent_ssa IN ({node_placeholders})
          AND child_ssa IN ({node_placeholders})
        ORDER BY parent_ssa, child_ssa
        LIMIT ?
        """,  # nosec B608  # skipcq: BAN-B608
        (*family_nodes, *family_nodes, family_limit),
    ).fetchall()
    family_truncated = family_truncated or len(edge_rows) > safe_max_nodes
    for row in edge_rows[:safe_max_nodes]:
        entry: dict[str, Any] = {
            "ssa": row[1],
            "parent": row[0],
            "min_distance": int(distance_by_node.get(row[1], 1)),
        }
        raw_relation_type = row[2]
        try:
            relation_type = int(raw_relation_type or 0)
        except (TypeError, ValueError):
            logger.warning(
                "relation_type invalido em ssa_derivada_matrix: parent=%s child=%s value=%r",
                row[0],
                row[1],
                raw_relation_type,
            )
            relation_type = 0
        relation_raw_label = row[3]
        if relation_type not in (0, 1):
            entry["relation_type"] = relation_type
        if relation_raw_label:
            entry["relation_raw_label"] = relation_raw_label
        family_descendants.append(entry)
    return family_roots, family_descendants, family_truncated


def get_top_by_metric(
    db_path: str, metric: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    if metric not in ALLOWED_TOP_METRICS:
        raise ValueError(f"Unsupported top metric: {metric}")
    safe_limit = max(1, min(int(limit), 500))
    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return []
        conn = cast(sqlite3.Connection, conn)
        rows = conn.execute(
            """
            SELECT
                ssa,
                CASE ?
                    WHEN 'direct_children' THEN direct_children_count
                    WHEN 'descendants' THEN descendants_count
                    WHEN 'ancestors' THEN ancestors_count
                    WHEN 'levels_below' THEN levels_below_max
                    WHEN 'levels_above' THEN levels_above_max
                END AS metric_value,
                direct_parents_count,
                direct_children_count,
                ancestors_count,
                descendants_count
            FROM ssa_derivada_summary
            ORDER BY metric_value DESC, ssa
            LIMIT ?
            """,
            (metric, safe_limit),
        ).fetchall()
        return [
            {
                "ssa": row[0],
                "metric": int(row[1] or 0),
                "direct_parents_count": int(row[2] or 0),
                "direct_children_count": int(row[3] or 0),
                "ancestors_count": int(row[4] or 0),
                "descendants_count": int(row[5] or 0),
            }
            for row in rows
        ]


def get_ssa_hierarchy_snapshot(
    db_path: str,
    ssa: Any,
    *,
    max_distance: int | None = 5,
    max_nodes: int = DERIVADAS_FAMILY_NODE_LIMIT,
) -> dict[str, Any]:
    """Return GUI-friendly hierarchy payload in a single call.

    This helper keeps reads in one DB connection and returns:
      - direct parent(s) and children
      - hierarchy profile (levels, counts, cycle/component info)
      - ancestors/descendants up to `max_distance` (or full when None)
    """

    target_ssa = _normalize_or_none(ssa)
    if not target_ssa:
        return {
            "ssa": None,
            "parent": None,
            "parents": [],
            "children": [],
            "children_count": 0,
            "has_children": False,
            "is_multiparent": False,
            "hierarchy_profile": {},
            "ancestors": [],
            "descendants": [],
            "family_roots": [],
            "family_descendants": [],
            "family_truncated": False,
        }
    safe_max_distance = _normalize_max_distance(max_distance)
    safe_max_nodes = max(1, min(int(max_nodes), DERIVADAS_FAMILY_NODE_LIMIT))

    with _open_derivadas_connection(db_path) as (conn, schema_ready):
        if not schema_ready:
            return {
                "ssa": target_ssa,
                "parent": None,
                "parents": [],
                "children": [],
                "children_count": 0,
                "has_children": False,
                "is_multiparent": False,
                "hierarchy_profile": {},
                "ancestors": [],
                "descendants": [],
                "family_roots": [],
                "family_descendants": [],
                "family_truncated": False,
            }
        conn = cast(sqlite3.Connection, conn)
        conn.execute("BEGIN")
        parents_rows = conn.execute(
            """
            SELECT parent_ssa
            FROM ssa_derivada_matrix
            WHERE child_ssa = ? AND active = 1
            ORDER BY parent_ssa
            """,
            (target_ssa,),
        ).fetchall()
        parents = [row[0] for row in parents_rows]

        children_rows = conn.execute(
            """
            SELECT child_ssa
            FROM ssa_derivada_matrix
            WHERE parent_ssa = ? AND active = 1
            ORDER BY child_ssa
            """,
            (target_ssa,),
        ).fetchall()
        children = [row[0] for row in children_rows]

        profile_row = conn.execute(
            """
            SELECT
                ssa,
                direct_parents_count,
                direct_children_count,
                ancestors_count,
                descendants_count,
                level_from_root_min,
                level_from_root_max,
                levels_above_max,
                levels_below_max,
                component_size,
                has_cycle,
                last_sync_at
            FROM ssa_derivada_summary
            WHERE ssa = ?
            """,
            (target_ssa,),
        ).fetchone()
        if profile_row is not None:
            hierarchy_profile = {
                "ssa": profile_row[0],
                "direct_parents_count": int(profile_row[1]),
                "direct_children_count": int(profile_row[2]),
                "ancestors_count": int(profile_row[3]),
                "descendants_count": int(profile_row[4]),
                "level_from_root_min": profile_row[5],
                "level_from_root_max": profile_row[6],
                "levels_above_max": int(profile_row[7]),
                "levels_below_max": int(profile_row[8]),
                "component_size": int(profile_row[9]),
                "has_cycle": bool(profile_row[10]),
                "last_sync_at": profile_row[11],
            }
        else:
            hierarchy_profile = {
                "ssa": target_ssa,
                "direct_parents_count": len(parents),
                "direct_children_count": len(children),
                "ancestors_count": 0,
                "descendants_count": 0,
                "level_from_root_min": None,
                "level_from_root_max": None,
                "levels_above_max": 0,
                "levels_below_max": 0,
                "component_size": 1,
                "has_cycle": False,
                "last_sync_at": None,
            }

        if safe_max_distance is not None:
            ancestor_rows = conn.execute(
                """
                SELECT ancestor_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE descendant_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, ancestor_ssa
                """,
                (target_ssa, safe_max_distance),
            ).fetchall()
            descendant_rows = conn.execute(
                """
                SELECT descendant_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE ancestor_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, descendant_ssa
                """,
                (target_ssa, safe_max_distance),
            ).fetchall()
        else:
            ancestor_rows = conn.execute(
                """
                SELECT ancestor_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE descendant_ssa = ?
                ORDER BY min_distance, ancestor_ssa
                """,
                (target_ssa,),
            ).fetchall()
            descendant_rows = conn.execute(
                """
                SELECT descendant_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE ancestor_ssa = ?
                ORDER BY min_distance, descendant_ssa
                """,
                (target_ssa,),
            ).fetchall()

        ancestors = [
            {
                "ssa": row[0],
                "min_distance": int(row[1]),
                "max_distance": int(row[2]),
                "path_count": int(row[3]),
            }
            for row in ancestor_rows
        ]
        descendants = [
            {
                "ssa": row[0],
                "min_distance": int(row[1]),
                "max_distance": int(row[2]),
                "path_count": int(row[3]),
            }
            for row in descendant_rows
        ]

        family_roots, family_descendants, family_truncated = _collect_family_subgraph(
            conn,
            target_ssa=target_ssa,
            parents=parents,
            ancestor_rows=ancestor_rows,
            safe_max_distance=safe_max_distance,
            safe_max_nodes=safe_max_nodes,
        )

        return {
            "ssa": target_ssa,
            "parent": parents[0] if len(parents) == 1 else None,
            "parents": parents,
            "children": children,
            "children_count": len(children),
            "has_children": bool(children),
            "is_multiparent": len(parents) > 1,
            "hierarchy_profile": hierarchy_profile,
            "ancestors": ancestors,
            "descendants": descendants,
            "family_roots": family_roots,
            "family_descendants": family_descendants,
            "family_truncated": family_truncated,
        }
