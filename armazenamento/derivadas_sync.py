"""Derivadas synchronization and validation pipeline.

Scope:
  - collect edges from DB field `derivada_de`
  - collect edges from optional spreadsheet
  - merge deterministic sources into matrix/source tables
  - materialize closure and summary tables
  - expose reconciliation metrics for validation workflows
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd  # type: ignore[import-not-found]

from armazenamento.database import get_db_connection
from armazenamento.derivadas_schema import ensure_derivadas_schema_on_connection
from armazenamento.identifier_utils import is_valid_identifier
from shared.numero_ssa import normalize_strict

logger = logging.getLogger(__name__)

SOURCE_DB_FIELD = "db_field"
SOURCE_SHEET_DERIVADAS = "sheet_derivadas"

SOURCE_FLAG_DB = 1
SOURCE_FLAG_SHEET = 2

SOURCE_FLAG_MAP: dict[str, int] = {
    SOURCE_DB_FIELD: SOURCE_FLAG_DB,
    SOURCE_SHEET_DERIVADAS: SOURCE_FLAG_SHEET,
}

SOURCE_PRIORITY: dict[str, int] = {
    SOURCE_DB_FIELD: 10,
    SOURCE_SHEET_DERIVADAS: 20,
}

RELATION_TYPE_UNKNOWN = 0
RELATION_TYPE_DB_DERIVADA_DE = 1
RELATION_TYPE_SHEET = 2


@dataclass(frozen=True, slots=True)
class SourceEdge:
    parent_ssa: str
    child_ssa: str
    source_name: str
    source_flag: int
    relation_type: int
    relation_raw_label: str | None


@dataclass(frozen=True, slots=True)
class MatrixEdge:
    parent_ssa: str
    child_ssa: str
    source_flags: int
    relation_type: int
    relation_raw_label: str | None


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _normalize_ssa(value: Any) -> str | None:
    return normalize_strict(value)


def _clean_relation_label(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.casefold()
    if lowered in {"nan", "none", "<na>", "null"}:
        return None
    return text


def _validate_table_name(table_name: str) -> str:
    if not is_valid_identifier(table_name):
        raise ValueError(f"Invalid table name: {table_name!r}")
    return table_name


def collect_db_edges(conn: sqlite3.Connection, table_name: str = "ssa_table") -> dict[str, Any]:
    """Collect normalized parent->child edges from `numero_ssa -> derivada_de`."""

    safe_table = _validate_table_name(table_name)
    query = f"""
        SELECT numero_ssa, derivada_de
        FROM "{safe_table}"
        WHERE derivada_de IS NOT NULL
    """

    rows = conn.execute(query).fetchall()

    seen_pairs: set[tuple[str, str]] = set()
    child_to_parents: dict[str, set[str]] = defaultdict(set)
    edges: list[SourceEdge] = []

    invalid_parent = 0
    invalid_child = 0
    self_loop = 0
    duplicated = 0

    for row in rows:
        child_norm = _normalize_ssa(row[0])
        parent_norm = _normalize_ssa(row[1])
        if not child_norm:
            invalid_child += 1
            continue
        if not parent_norm:
            invalid_parent += 1
            continue
        if child_norm == parent_norm:
            self_loop += 1
            continue
        key = (parent_norm, child_norm)
        if key in seen_pairs:
            duplicated += 1
            continue
        seen_pairs.add(key)
        child_to_parents[child_norm].add(parent_norm)
        edges.append(
            SourceEdge(
                parent_ssa=parent_norm,
                child_ssa=child_norm,
                source_name=SOURCE_DB_FIELD,
                source_flag=SOURCE_FLAG_DB,
                relation_type=RELATION_TYPE_DB_DERIVADA_DE,
                relation_raw_label=None,
            )
        )

    multiparent = {child: sorted(parents) for child, parents in child_to_parents.items() if len(parents) > 1}
    return {
        "edges": edges,
        "stats": {
            "input_rows": len(rows),
            "accepted_edges": len(edges),
            "invalid_parent": invalid_parent,
            "invalid_child": invalid_child,
            "self_loop": self_loop,
            "duplicated": duplicated,
            "multiparent_in_source": len(multiparent),
        },
        "multiparent_detail": multiparent,
    }


def _load_sheet_dataframe(sheet_file: str, sheet_name: str | None = None) -> list[pd.DataFrame]:
    ext = os.path.splitext(sheet_file)[1].lower()
    if ext in {".csv", ".txt"}:
        return [pd.read_csv(sheet_file)]
    if ext == ".tsv":
        return [pd.read_csv(sheet_file, sep="\t")]
    if ext in {".xlsx", ".xlsm", ".xls"}:
        if sheet_name:
            return [pd.read_excel(sheet_file, sheet_name=sheet_name)]
        loaded = pd.read_excel(sheet_file, sheet_name=None)
        return list(loaded.values()) if isinstance(loaded, dict) else [loaded]
    raise ValueError(f"Unsupported sheet format for derivadas sync: {sheet_file}")


def collect_sheet_edges(
    sheet_file: str,
    parent_col: str = "parent_ssa",
    child_col: str = "child_ssa",
    label_col: str | None = "relation_label",
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Collect normalized parent->child edges from external spreadsheet/csv."""

    frames = _load_sheet_dataframe(sheet_file, sheet_name=sheet_name)

    edges: list[SourceEdge] = []
    seen_pairs: set[tuple[str, str]] = set()
    child_to_parents: dict[str, set[str]] = defaultdict(set)
    stats = {
        "input_rows": 0,
        "accepted_edges": 0,
        "invalid_parent": 0,
        "invalid_child": 0,
        "self_loop": 0,
        "duplicated": 0,
        "missing_columns": 0,
    }

    for frame in frames:
        if frame is None or frame.empty:
            continue
        if parent_col not in frame.columns or child_col not in frame.columns:
            stats["missing_columns"] += int(len(frame))
            continue

        stats["input_rows"] += int(len(frame))
        for _, row in frame.iterrows():
            parent_norm = _normalize_ssa(row.get(parent_col))
            child_norm = _normalize_ssa(row.get(child_col))
            if not parent_norm:
                stats["invalid_parent"] += 1
                continue
            if not child_norm:
                stats["invalid_child"] += 1
                continue
            if parent_norm == child_norm:
                stats["self_loop"] += 1
                continue
            key = (parent_norm, child_norm)
            if key in seen_pairs:
                stats["duplicated"] += 1
                continue
            seen_pairs.add(key)
            child_to_parents[child_norm].add(parent_norm)
            relation_label = _clean_relation_label(row.get(label_col)) if label_col else None
            edges.append(
                SourceEdge(
                    parent_ssa=parent_norm,
                    child_ssa=child_norm,
                    source_name=SOURCE_SHEET_DERIVADAS,
                    source_flag=SOURCE_FLAG_SHEET,
                    relation_type=RELATION_TYPE_SHEET,
                    relation_raw_label=relation_label,
                )
            )

    stats["accepted_edges"] = len(edges)
    multiparent = {child: sorted(parents) for child, parents in child_to_parents.items() if len(parents) > 1}
    stats["multiparent_in_source"] = len(multiparent)
    return {"edges": edges, "stats": stats, "multiparent_detail": multiparent}


def _merge_edges(source_edges: list[SourceEdge]) -> dict[str, Any]:
    merged: dict[tuple[str, str], MatrixEdge] = {}
    source_by_edge: dict[tuple[str, str], list[SourceEdge]] = defaultdict(list)

    for edge in source_edges:
        key = (edge.parent_ssa, edge.child_ssa)
        source_by_edge[key].append(edge)
        prev = merged.get(key)
        if prev is None:
            merged[key] = MatrixEdge(
                parent_ssa=edge.parent_ssa,
                child_ssa=edge.child_ssa,
                source_flags=edge.source_flag,
                relation_type=edge.relation_type,
                relation_raw_label=edge.relation_raw_label,
            )
            continue

        prev_priority = max(SOURCE_PRIORITY.get(se.source_name, 0) for se in source_by_edge[key][:-1]) if source_by_edge[key][:-1] else 0
        new_priority = SOURCE_PRIORITY.get(edge.source_name, 0)
        keep_label = prev.relation_raw_label
        keep_type = prev.relation_type

        if new_priority >= prev_priority:
            if edge.relation_raw_label:
                keep_label = edge.relation_raw_label
            if edge.relation_type:
                keep_type = edge.relation_type

        merged[key] = MatrixEdge(
            parent_ssa=edge.parent_ssa,
            child_ssa=edge.child_ssa,
            source_flags=(prev.source_flags | edge.source_flag),
            relation_type=keep_type,
            relation_raw_label=keep_label,
        )

    return {
        "edges": list(merged.values()),
        "source_by_edge": source_by_edge,
    }


def _build_child_parent_map(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    child_parents: dict[str, set[str]] = defaultdict(set)
    for parent, child in edges:
        child_parents[child].add(parent)
    return child_parents


def _kahn_cycle_nodes(edges: list[tuple[str, str]]) -> set[str]:
    children_by_parent: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()
    for parent, child in edges:
        if child not in children_by_parent[parent]:
            children_by_parent[parent].add(child)
            indegree[child] += 1
        nodes.add(parent)
        nodes.add(child)
        indegree.setdefault(parent, indegree.get(parent, 0))

    queue = deque(node for node in nodes if indegree.get(node, 0) == 0)
    processed = 0
    while queue:
        node = queue.popleft()
        processed += 1
        for child in children_by_parent.get(node, ()):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if processed == len(nodes):
        return set()
    return {node for node in nodes if indegree.get(node, 0) > 0}


def _build_closure_rows(edges: list[tuple[str, str]], depth_cap: int = 32) -> tuple[list[tuple[str, str, int, int, int]], set[str]]:
    adjacency: dict[str, tuple[str, ...]] = defaultdict(tuple)
    children_map: dict[str, list[str]] = defaultdict(list)
    for parent, child in edges:
        children_map[parent].append(child)
    adjacency = {parent: tuple(sorted(set(children), key=lambda value: value.casefold())) for parent, children in children_map.items()}

    cycle_nodes = _kahn_cycle_nodes(edges)
    metrics: dict[tuple[str, str], list[int]] = {}

    for ancestor in adjacency.keys():
        stack: list[tuple[str, int, frozenset[str]]] = [(ancestor, 0, frozenset((ancestor,)))]
        while stack:
            node, depth, visited = stack.pop()
            if depth >= depth_cap:
                continue
            for child in adjacency.get(node, ()):
                if child in visited:
                    cycle_nodes.add(child)
                    cycle_nodes.add(node)
                    continue
                next_depth = depth + 1
                key = (ancestor, child)
                if key not in metrics:
                    metrics[key] = [next_depth, next_depth, 1]
                else:
                    current = metrics[key]
                    if next_depth < current[0]:
                        current[0] = next_depth
                    if next_depth > current[1]:
                        current[1] = next_depth
                    current[2] += 1
                stack.append((child, next_depth, visited.union((child,))))

    closure_rows = [
        (ancestor, descendant, values[0], values[1], values[2])
        for (ancestor, descendant), values in sorted(metrics.items())
    ]
    return closure_rows, cycle_nodes


def _component_sizes(edges: list[tuple[str, str]]) -> dict[str, int]:
    graph: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for parent, child in edges:
        graph[parent].add(child)
        graph[child].add(parent)
        nodes.add(parent)
        nodes.add(child)
    component_size: dict[str, int] = {}
    seen: set[str] = set()
    for node in nodes:
        if node in seen:
            continue
        queue = deque((node,))
        cluster: list[str] = []
        seen.add(node)
        while queue:
            current = queue.popleft()
            cluster.append(current)
            for neigh in graph.get(current, ()):
                if neigh in seen:
                    continue
                seen.add(neigh)
                queue.append(neigh)
        size = len(cluster)
        for item in cluster:
            component_size[item] = size
    return component_size


def _build_summary_rows(
    edges: list[tuple[str, str]],
    closure_rows: list[tuple[str, str, int, int, int]],
    cycle_nodes: set[str],
    timestamp: str,
) -> list[tuple[Any, ...]]:
    children_by_parent: dict[str, set[str]] = defaultdict(set)
    parents_by_child: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for parent, child in edges:
        children_by_parent[parent].add(child)
        parents_by_child[child].add(parent)
        nodes.add(parent)
        nodes.add(child)

    descendants_info: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    ancestors_info: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for ancestor, descendant, min_distance, max_distance, _path_count in closure_rows:
        descendants_info[ancestor].append((descendant, min_distance, max_distance))
        ancestors_info[descendant].append((ancestor, min_distance, max_distance))
        nodes.add(ancestor)
        nodes.add(descendant)

    component_sizes = _component_sizes(edges)
    roots = {node for node in nodes if len(parents_by_child.get(node, set())) == 0}

    rows: list[tuple[Any, ...]] = []
    for node in sorted(nodes):
        direct_parents = len(parents_by_child.get(node, set()))
        direct_children = len(children_by_parent.get(node, set()))
        ancestors = ancestors_info.get(node, [])
        descendants = descendants_info.get(node, [])
        ancestors_count = len({ancestor for ancestor, _min_d, _max_d in ancestors})
        descendants_count = len({descendant for descendant, _min_d, _max_d in descendants})

        level_candidates_min: list[int] = []
        level_candidates_max: list[int] = []
        if node in roots:
            level_candidates_min.append(0)
            level_candidates_max.append(0)
        for ancestor, min_d, max_d in ancestors:
            if ancestor in roots:
                level_candidates_min.append(min_d)
                level_candidates_max.append(max_d)
        level_min = min(level_candidates_min) if level_candidates_min else None
        level_max = max(level_candidates_max) if level_candidates_max else None

        levels_above_max = level_max if level_max is not None else 0
        levels_below_max = max((max_d for _desc, _min_d, max_d in descendants), default=0)
        has_cycle = 1 if node in cycle_nodes else 0
        component_size = component_sizes.get(node, 1)

        rows.append(
            (
                node,
                direct_parents,
                direct_children,
                ancestors_count,
                descendants_count,
                level_min,
                level_max,
                levels_above_max,
                levels_below_max,
                component_size,
                has_cycle,
                timestamp,
            )
        )
    return rows


def _fetch_all_ssa(conn: sqlite3.Connection, table_name: str) -> set[str]:
    safe_table = _validate_table_name(table_name)
    rows = conn.execute(f'SELECT numero_ssa FROM "{safe_table}" WHERE numero_ssa IS NOT NULL').fetchall()
    out: set[str] = set()
    for row in rows:
        normalized = _normalize_ssa(row[0])
        if normalized:
            out.add(normalized)
    return out


def _analyze_reconciliation(
    all_ssa: set[str],
    matrix_edges: list[MatrixEdge],
    source_edges: list[SourceEdge],
) -> dict[str, Any]:
    pair_edges = [(edge.parent_ssa, edge.child_ssa) for edge in matrix_edges]

    child_parents = _build_child_parent_map(pair_edges)
    multiparent_children = {child: sorted(parents) for child, parents in child_parents.items() if len(parents) > 1}

    orphan_parents = sorted({parent for parent, _child in pair_edges if parent not in all_ssa})
    orphan_children = sorted({child for _parent, child in pair_edges if child not in all_ssa})

    db_parents: dict[str, set[str]] = defaultdict(set)
    sheet_parents: dict[str, set[str]] = defaultdict(set)
    for edge in source_edges:
        if edge.source_name == SOURCE_DB_FIELD:
            db_parents[edge.child_ssa].add(edge.parent_ssa)
        elif edge.source_name == SOURCE_SHEET_DERIVADAS:
            sheet_parents[edge.child_ssa].add(edge.parent_ssa)

    db_vs_sheet_conflicts: dict[str, dict[str, list[str]]] = {}
    for child in sorted(set(db_parents).intersection(sheet_parents)):
        db_set = db_parents[child]
        sheet_set = sheet_parents[child]
        if db_set == sheet_set:
            continue
        db_vs_sheet_conflicts[child] = {
            "db_parents": sorted(db_set),
            "sheet_parents": sorted(sheet_set),
        }

    source_distribution: dict[str, int] = defaultdict(int)
    for edge in matrix_edges:
        source_distribution[str(edge.source_flags)] += 1

    cycle_nodes = _kahn_cycle_nodes(pair_edges)
    return {
        "multiparent_children_count": len(multiparent_children),
        "multiparent_children_sample": dict(list(multiparent_children.items())[:20]),
        "orphan_parents_count": len(orphan_parents),
        "orphan_parents_sample": orphan_parents[:20],
        "orphan_children_count": len(orphan_children),
        "orphan_children_sample": orphan_children[:20],
        "db_vs_sheet_conflict_count": len(db_vs_sheet_conflicts),
        "db_vs_sheet_conflict_sample": dict(list(db_vs_sheet_conflicts.items())[:20]),
        "source_distribution": dict(sorted(source_distribution.items(), key=lambda item: int(item[0]))),
        "cycle_node_count": len(cycle_nodes),
        "cycle_node_sample": sorted(cycle_nodes)[:20],
    }


def _upsert_source_rows(
    conn: sqlite3.Connection,
    edges: list[SourceEdge],
    managed_sources: list[str],
    timestamp: str,
) -> None:
    # deactivate active rows for managed sources before reactivating observed edges
    for source_name in managed_sources:
        conn.execute(
            """
            UPDATE ssa_derivada_source
            SET is_active = 0, last_sync_at = ?
            WHERE source_name = ? AND is_active = 1
            """,
            (timestamp, source_name),
        )

    upsert_sql = """
        INSERT INTO ssa_derivada_source (
            parent_ssa,
            child_ssa,
            source_name,
            source_flag,
            relation_type,
            relation_raw_label,
            is_active,
            first_seen_at,
            last_seen_at,
            last_sync_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        ON CONFLICT(parent_ssa, child_ssa, source_name) DO UPDATE SET
            source_flag = excluded.source_flag,
            relation_type = excluded.relation_type,
            relation_raw_label = CASE
                WHEN excluded.relation_raw_label IS NOT NULL AND trim(excluded.relation_raw_label) <> ''
                    THEN excluded.relation_raw_label
                ELSE ssa_derivada_source.relation_raw_label
            END,
            is_active = 1,
            last_seen_at = excluded.last_seen_at,
            last_sync_at = excluded.last_sync_at
    """
    conn.executemany(
        upsert_sql,
        [
            (
                edge.parent_ssa,
                edge.child_ssa,
                edge.source_name,
                edge.source_flag,
                edge.relation_type,
                edge.relation_raw_label,
                timestamp,
                timestamp,
                timestamp,
            )
            for edge in edges
        ],
    )


def _matrix_from_active_sources(conn: sqlite3.Connection) -> list[MatrixEdge]:
    rows = conn.execute(
        """
        SELECT
            parent_ssa,
            child_ssa,
            source_name,
            source_flag,
            relation_type,
            relation_raw_label
        FROM ssa_derivada_source
        WHERE is_active = 1
        """
    ).fetchall()

    grouped: dict[tuple[str, str], list[SourceEdge]] = defaultdict(list)
    for parent_ssa, child_ssa, source_name, source_flag, relation_type, relation_raw_label in rows:
        grouped[(parent_ssa, child_ssa)].append(
            SourceEdge(
                parent_ssa=parent_ssa,
                child_ssa=child_ssa,
                source_name=source_name,
                source_flag=int(source_flag),
                relation_type=int(relation_type),
                relation_raw_label=relation_raw_label,
            )
        )

    matrix_edges: list[MatrixEdge] = []
    for key, source_edges in sorted(grouped.items()):
        source_flags = 0
        best_priority = -1
        relation_type = RELATION_TYPE_UNKNOWN
        relation_raw_label: str | None = None
        for edge in source_edges:
            source_flags |= edge.source_flag
            priority = SOURCE_PRIORITY.get(edge.source_name, 0)
            if priority >= best_priority:
                best_priority = priority
                if edge.relation_type:
                    relation_type = edge.relation_type
                if edge.relation_raw_label:
                    relation_raw_label = edge.relation_raw_label
        matrix_edges.append(
            MatrixEdge(
                parent_ssa=key[0],
                child_ssa=key[1],
                source_flags=source_flags,
                relation_type=relation_type,
                relation_raw_label=relation_raw_label,
            )
        )
    return matrix_edges


def _upsert_matrix_rows(
    conn: sqlite3.Connection,
    matrix_edges: list[MatrixEdge],
    timestamp: str,
    full_rebuild: bool,
) -> None:
    upsert_sql = """
        INSERT INTO ssa_derivada_matrix (
            parent_ssa,
            child_ssa,
            source_flags,
            relation_type,
            relation_raw_label,
            active,
            first_seen_at,
            last_seen_at,
            last_sync_at
        )
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        ON CONFLICT(parent_ssa, child_ssa) DO UPDATE SET
            source_flags = excluded.source_flags,
            relation_type = excluded.relation_type,
            relation_raw_label = CASE
                WHEN excluded.relation_raw_label IS NOT NULL AND trim(excluded.relation_raw_label) <> ''
                    THEN excluded.relation_raw_label
                ELSE ssa_derivada_matrix.relation_raw_label
            END,
            active = 1,
            last_seen_at = excluded.last_seen_at,
            last_sync_at = excluded.last_sync_at
    """
    conn.executemany(
        upsert_sql,
        [
            (
                edge.parent_ssa,
                edge.child_ssa,
                edge.source_flags,
                edge.relation_type,
                edge.relation_raw_label,
                timestamp,
                timestamp,
                timestamp,
            )
            for edge in matrix_edges
        ],
    )

    existing_pairs = {
        (row[0], row[1])
        for row in conn.execute("SELECT parent_ssa, child_ssa FROM ssa_derivada_matrix").fetchall()
    }
    active_pairs = {(edge.parent_ssa, edge.child_ssa) for edge in matrix_edges}
    stale_pairs = existing_pairs - active_pairs
    if stale_pairs:
        if full_rebuild:
            conn.executemany(
                "DELETE FROM ssa_derivada_matrix WHERE parent_ssa = ? AND child_ssa = ?",
                list(stale_pairs),
            )
        else:
            conn.executemany(
                """
                UPDATE ssa_derivada_matrix
                SET active = 0, source_flags = 0, last_sync_at = ?
                WHERE parent_ssa = ? AND child_ssa = ?
                """,
                [(timestamp, parent, child) for parent, child in stale_pairs],
            )


def _replace_closure(conn: sqlite3.Connection, closure_rows: list[tuple[str, str, int, int, int]], timestamp: str) -> None:
    conn.execute("DELETE FROM ssa_derivada_closure")
    if not closure_rows:
        return
    conn.executemany(
        """
        INSERT INTO ssa_derivada_closure (
            ancestor_ssa,
            descendant_ssa,
            min_distance,
            max_distance,
            path_count,
            last_sync_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(ancestor, descendant, min_d, max_d, path_count, timestamp) for ancestor, descendant, min_d, max_d, path_count in closure_rows],
    )


def _replace_summary(conn: sqlite3.Connection, summary_rows: list[tuple[Any, ...]]) -> None:
    conn.execute("DELETE FROM ssa_derivada_summary")
    if not summary_rows:
        return
    conn.executemany(
        """
        INSERT INTO ssa_derivada_summary (
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        summary_rows,
    )


def _start_sync_run(
    conn: sqlite3.Connection,
    mode: str,
    managed_sources: list[str],
    started_at: str,
    db_edges: int,
    sheet_edges: int,
    merged_edges: int,
) -> int:
    row = conn.execute(
        """
        INSERT INTO ssa_derivada_sync_run (
            mode,
            managed_sources,
            started_at,
            status,
            db_edges,
            sheet_edges,
            merged_edges
        ) VALUES (?, ?, ?, 'running', ?, ?, ?)
        """,
        (mode, ",".join(managed_sources), started_at, db_edges, sheet_edges, merged_edges),
    )
    return int(row.lastrowid)


def _finish_sync_run(
    conn: sqlite3.Connection,
    sync_run_id: int,
    finished_at: str,
    reconciliation: dict[str, Any],
    active_edges: int,
    status: str = "ok",
    message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE ssa_derivada_sync_run
        SET
            finished_at = ?,
            status = ?,
            active_edges = ?,
            conflict_count = ?,
            multiparent_count = ?,
            orphan_parent_count = ?,
            orphan_child_count = ?,
            cycle_node_count = ?,
            message = ?
        WHERE sync_run_id = ?
        """,
        (
            finished_at,
            status,
            int(active_edges),
            int(reconciliation.get("db_vs_sheet_conflict_count", 0)),
            int(reconciliation.get("multiparent_children_count", 0)),
            int(reconciliation.get("orphan_parents_count", 0)),
            int(reconciliation.get("orphan_children_count", 0)),
            int(reconciliation.get("cycle_node_count", 0)),
            message,
            sync_run_id,
        ),
    )


def sync_derivadas(
    db_path: str,
    table_name: str = "ssa_table",
    *,
    sheet_file: str | None = None,
    sheet_parent_col: str = "parent_ssa",
    sheet_child_col: str = "child_ssa",
    sheet_label_col: str | None = "relation_label",
    sheet_name: str | None = None,
    include_db_source: bool = True,
    full_rebuild: bool = False,
    verify_only: bool = False,
) -> dict[str, Any]:
    """Run a full derivadas sync/validation cycle."""

    mode = "full_rebuild" if full_rebuild else "sync"
    timestamp = _now_utc_str()

    with get_db_connection(db_path) as conn:
        ensure_derivadas_schema_on_connection(conn)

        source_edges: list[SourceEdge] = []
        db_stats: dict[str, Any] = {"accepted_edges": 0}
        sheet_stats: dict[str, Any] = {"accepted_edges": 0}
        db_multiparent: dict[str, Any] = {}
        sheet_multiparent: dict[str, Any] = {}

        if include_db_source:
            db_result = collect_db_edges(conn, table_name=table_name)
            source_edges.extend(db_result["edges"])
            db_stats = db_result["stats"]
            db_multiparent = db_result["multiparent_detail"]

        if sheet_file:
            sheet_result = collect_sheet_edges(
                sheet_file=sheet_file,
                parent_col=sheet_parent_col,
                child_col=sheet_child_col,
                label_col=sheet_label_col,
                sheet_name=sheet_name,
            )
            source_edges.extend(sheet_result["edges"])
            sheet_stats = sheet_result["stats"]
            sheet_multiparent = sheet_result["multiparent_detail"]

        merge_result = _merge_edges(source_edges)
        merged_edges: list[MatrixEdge] = merge_result["edges"]

        all_ssa = _fetch_all_ssa(conn, table_name=table_name)
        reconciliation_pre = _analyze_reconciliation(all_ssa, merged_edges, source_edges)
        managed_sources = sorted({edge.source_name for edge in source_edges})

        report: dict[str, Any] = {
            "mode": mode,
            "verify_only": bool(verify_only),
            "managed_sources": managed_sources,
            "db_stats": db_stats,
            "sheet_stats": sheet_stats,
            "merge_stats": {
                "source_edges": len(source_edges),
                "merged_edges": len(merged_edges),
            },
            "reconciliation": reconciliation_pre,
            "source_multiparent": {
                SOURCE_DB_FIELD: {"count": len(db_multiparent), "sample": dict(list(db_multiparent.items())[:20])},
                SOURCE_SHEET_DERIVADAS: {"count": len(sheet_multiparent), "sample": dict(list(sheet_multiparent.items())[:20])},
            },
            "timestamp": timestamp,
        }

        if verify_only:
            return report

        started_at = timestamp
        run_id = _start_sync_run(
            conn,
            mode=mode,
            managed_sources=managed_sources,
            started_at=started_at,
            db_edges=int(db_stats.get("accepted_edges", 0)),
            sheet_edges=int(sheet_stats.get("accepted_edges", 0)),
            merged_edges=len(merged_edges),
        )

        try:
            _upsert_source_rows(conn, source_edges, managed_sources=managed_sources, timestamp=timestamp)

            matrix_edges = _matrix_from_active_sources(conn)
            _upsert_matrix_rows(conn, matrix_edges=matrix_edges, timestamp=timestamp, full_rebuild=full_rebuild)

            active_rows = conn.execute(
                """
                SELECT parent_ssa, child_ssa, source_flags, relation_type, relation_raw_label
                FROM ssa_derivada_matrix
                WHERE active = 1
                """
            ).fetchall()
            active_matrix_edges = [
                MatrixEdge(
                    parent_ssa=row[0],
                    child_ssa=row[1],
                    source_flags=int(row[2]),
                    relation_type=int(row[3]),
                    relation_raw_label=row[4],
                )
                for row in active_rows
            ]
            edge_pairs = [(edge.parent_ssa, edge.child_ssa) for edge in active_matrix_edges]

            closure_rows, cycle_nodes = _build_closure_rows(edge_pairs)
            _replace_closure(conn, closure_rows=closure_rows, timestamp=timestamp)

            summary_rows = _build_summary_rows(
                edges=edge_pairs,
                closure_rows=closure_rows,
                cycle_nodes=cycle_nodes,
                timestamp=timestamp,
            )
            _replace_summary(conn, summary_rows=summary_rows)

            reconciliation_post = _analyze_reconciliation(
                all_ssa=all_ssa,
                matrix_edges=active_matrix_edges,
                source_edges=source_edges,
            )

            finished_at = _now_utc_str()
            _finish_sync_run(
                conn,
                sync_run_id=run_id,
                finished_at=finished_at,
                reconciliation=reconciliation_post,
                active_edges=len(active_matrix_edges),
                status="ok",
                message=None,
            )
            conn.commit()

            report.update(
                {
                    "sync_run_id": run_id,
                    "active_edges": len(active_matrix_edges),
                    "closure_rows": len(closure_rows),
                    "summary_rows": len(summary_rows),
                    "reconciliation": reconciliation_post,
                    "finished_at": finished_at,
                }
            )
            return report
        except Exception as exc:
            logger.exception("Derivadas sync failed: %s", exc)
            finished_at = _now_utc_str()
            try:
                _finish_sync_run(
                    conn,
                    sync_run_id=run_id,
                    finished_at=finished_at,
                    reconciliation=reconciliation_pre,
                    active_edges=0,
                    status="error",
                    message=str(exc),
                )
                conn.commit()
            except Exception:
                conn.rollback()
            raise


def get_sync_stats(db_path: str) -> dict[str, Any]:
    """Return compact stats for matrix, closure, summary and latest sync run."""

    with get_db_connection(db_path) as conn:
        ensure_derivadas_schema_on_connection(conn)
        matrix_active = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1").fetchone()[0]
        matrix_total = conn.execute("SELECT COUNT(*) FROM ssa_derivada_matrix").fetchone()[0]
        closure_total = conn.execute("SELECT COUNT(*) FROM ssa_derivada_closure").fetchone()[0]
        summary_total = conn.execute("SELECT COUNT(*) FROM ssa_derivada_summary").fetchone()[0]
        latest = conn.execute(
            """
            SELECT
                sync_run_id,
                mode,
                managed_sources,
                started_at,
                finished_at,
                status,
                db_edges,
                sheet_edges,
                merged_edges,
                active_edges,
                conflict_count,
                multiparent_count,
                orphan_parent_count,
                orphan_child_count,
                cycle_node_count
            FROM ssa_derivada_sync_run
            ORDER BY sync_run_id DESC
            LIMIT 1
            """
        ).fetchone()

        latest_row = (
            {
                "sync_run_id": latest[0],
                "mode": latest[1],
                "managed_sources": latest[2],
                "started_at": latest[3],
                "finished_at": latest[4],
                "status": latest[5],
                "db_edges": latest[6],
                "sheet_edges": latest[7],
                "merged_edges": latest[8],
                "active_edges": latest[9],
                "conflict_count": latest[10],
                "multiparent_count": latest[11],
                "orphan_parent_count": latest[12],
                "orphan_child_count": latest[13],
                "cycle_node_count": latest[14],
            }
            if latest
            else None
        )

        return {
            "matrix_total": int(matrix_total),
            "matrix_active": int(matrix_active),
            "closure_total": int(closure_total),
            "summary_total": int(summary_total),
            "latest_sync": latest_row,
        }


def export_reconciliation_csv(report: dict[str, Any], output_file: str) -> None:
    """Export a lightweight reconciliation report (single-row csv)."""

    reconciliation = dict(report.get("reconciliation") or {})
    row = {
        "timestamp": report.get("timestamp"),
        "mode": report.get("mode"),
        "verify_only": report.get("verify_only"),
        "source_edges": (report.get("merge_stats") or {}).get("source_edges", 0),
        "merged_edges": (report.get("merge_stats") or {}).get("merged_edges", 0),
        "multiparent_children_count": reconciliation.get("multiparent_children_count", 0),
        "orphan_parents_count": reconciliation.get("orphan_parents_count", 0),
        "orphan_children_count": reconciliation.get("orphan_children_count", 0),
        "db_vs_sheet_conflict_count": reconciliation.get("db_vs_sheet_conflict_count", 0),
        "cycle_node_count": reconciliation.get("cycle_node_count", 0),
    }
    fieldnames = list(row.keys())
    with open(output_file, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def export_report_json(report: dict[str, Any], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
