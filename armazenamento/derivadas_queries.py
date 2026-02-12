"""Read/query API for derivadas matrix, closure and summary tables."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from typing import Any

from armazenamento.database import get_db_connection
from armazenamento.derivadas_schema import ensure_derivadas_schema_for_read
from shared.numero_ssa import normalize_strict

ALLOWED_TOP_METRICS = {
    "direct_children": "direct_children_count",
    "descendants": "descendants_count",
    "ancestors": "ancestors_count",
    "levels_below": "levels_below_max",
    "levels_above": "levels_above_max",
}
DERIVADAS_QUERY_BUSY_TIMEOUT_MS = 3000


def _normalize_or_none(value: Any) -> str | None:
    return normalize_strict(value)


@contextmanager
def _open_derivadas_connection(db_path: str):
    with get_db_connection(db_path) as conn:
        conn.execute(f"PRAGMA busy_timeout = {DERIVADAS_QUERY_BUSY_TIMEOUT_MS}")
        ensure_derivadas_schema_for_read(conn)
        yield conn


def get_parents(db_path: str, ssa: Any, *, include_inactive: bool = False) -> list[str]:
    child_ssa = _normalize_or_none(ssa)
    if not child_ssa:
        return []
    with _open_derivadas_connection(db_path) as conn:
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


def get_children(db_path: str, ssa: Any, *, include_inactive: bool = False) -> list[str]:
    parent_ssa = _normalize_or_none(ssa)
    if not parent_ssa:
        return []
    with _open_derivadas_connection(db_path) as conn:
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
    with _open_derivadas_connection(db_path) as conn:
        if include_inactive:
            query = "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE parent_ssa = ?"
            value = conn.execute(query, (parent_ssa,)).fetchone()[0]
        else:
            query = "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE parent_ssa = ? AND active = 1"
            value = conn.execute(query, (parent_ssa,)).fetchone()[0]
        return int(value)


def get_ancestors(db_path: str, ssa: Any, *, max_distance: int | None = None) -> list[dict[str, Any]]:
    descendant_ssa = _normalize_or_none(ssa)
    if not descendant_ssa:
        return []
    with _open_derivadas_connection(db_path) as conn:
        if max_distance is not None:
            rows = conn.execute(
                """
                SELECT ancestor_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE descendant_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, ancestor_ssa
                """,
                (descendant_ssa, max_distance),
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


def get_descendants(db_path: str, ssa: Any, *, max_distance: int | None = None) -> list[dict[str, Any]]:
    ancestor_ssa = _normalize_or_none(ssa)
    if not ancestor_ssa:
        return []
    with _open_derivadas_connection(db_path) as conn:
        if max_distance is not None:
            rows = conn.execute(
                """
                SELECT descendant_ssa, min_distance, max_distance, path_count
                FROM ssa_derivada_closure
                WHERE ancestor_ssa = ? AND min_distance <= ?
                ORDER BY min_distance, descendant_ssa
                """,
                (ancestor_ssa, max_distance),
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
    with _open_derivadas_connection(db_path) as conn:
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

    stack: list[tuple[str, list[str], set[str]]] = [(start_ssa, [start_ssa], {start_ssa})]
    paths: list[list[str]] = []
    visited_steps = 0

    while stack:
        node, path, seen = stack.pop()
        if visited_steps >= max_nodes:
            break
        visited_steps += 1
        children = adjacency.get(node, [])
        if not children or len(path) > depth:
            paths.append(path)
            continue
        for nxt in reversed(children):
            if nxt in seen:
                paths.append(path + [nxt])
                continue
            next_path = path + [nxt]
            if len(next_path) > depth + 1:
                paths.append(next_path)
                continue
            stack.append((nxt, next_path, seen | {nxt}))

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
    with _open_derivadas_connection(db_path) as conn:
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
    with _open_derivadas_connection(db_path) as conn:
        adjacency = _load_adjacency(conn, direction="up")
        return _collect_paths(adjacency, child, depth=depth, max_nodes=max_nodes)


def get_top_by_metric(db_path: str, metric: str, *, limit: int = 20) -> list[dict[str, Any]]:
    metric_col = ALLOWED_TOP_METRICS.get(metric)
    if not metric_col:
        raise ValueError(f"Unsupported top metric: {metric}")
    safe_limit = max(1, min(int(limit), 500))
    with _open_derivadas_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT ssa, {metric_col}, direct_parents_count, direct_children_count, ancestors_count, descendants_count
            FROM ssa_derivada_summary
            ORDER BY {metric_col} DESC, ssa
            LIMIT ?
            """,
            (safe_limit,),
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
