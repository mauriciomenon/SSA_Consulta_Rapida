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
import hashlib
import json
import logging
import os
import sqlite3
import unicodedata
from collections import defaultdict, deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from armazenamento.database import get_db_connection
from armazenamento.derivadas_schema import (
    ensure_derivadas_schema_on_connection,
    scan_derivadas_read_schema_readiness,
)
from armazenamento.identifier_utils import is_valid_identifier
from shared.numero_ssa import normalize_strict
from utils.path_safety import ensure_path_is_allowed

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
DERIVADAS_BUSY_TIMEOUT_MS = 5000
SHEET_PARENT_ALIASES: tuple[str, ...] = (
    "parent",
    "ssa_mae",
    "ssa_pai",
    "numero_ssa_mae",
    "numero_mae",
)
SHEET_CHILD_ALIASES: tuple[str, ...] = (
    "child",
    "ssa_filha",
    "ssa_derivada",
    "numero_ssa_filha",
    "numero_filha",
    "numero_ssa",
)
SHEET_LABEL_ALIASES: tuple[str, ...] = (
    "relacao",
    "tipo_relacao",
    "relation",
    "label",
    "descricao_relacao",
    "relation_raw_label",
)
SPECIAL_SHEET_HEADER_ROW_INDEX = 1


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


def _parse_utc_str(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _graph_fingerprint(edges: list[tuple[str, str, int]]) -> str:
    digest = hashlib.sha256()
    for parent, child, source_flags in sorted(edges):
        digest.update(parent.encode("utf-8"))
        digest.update(b"->")
        digest.update(child.encode("utf-8"))
        digest.update(b":")
        digest.update(str(int(source_flags)).encode("ascii"))
        digest.update(b";")
    return digest.hexdigest()


def _resolve_sync_actor(actor: str | None) -> str:
    """Resolve an audit-friendly actor label for sync runs."""

    if actor is not None:
        return str(actor).strip()[:128]
    for env_var in ("SSA_DERIVADAS_ACTOR", "SSA_SYNC_ACTOR", "USER", "USERNAME"):
        value = os.environ.get(env_var)
        if value and value.strip():
            return value.strip()[:128]
    return ""


def _normalize_ssa(value: Any) -> str | None:
    return normalize_strict(value)


def _configure_derivadas_connection(conn: sqlite3.Connection) -> None:
    """Apply low-cost connection guards for derivadas operations."""

    conn.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        f"PRAGMA busy_timeout = {DERIVADAS_BUSY_TIMEOUT_MS}"
    )


@contextmanager
def _open_derivadas_read_connection(db_path: str):
    safe_db_path = str(
        ensure_path_is_allowed(
            db_path,
            purpose="derivadas read database",
            expect_directory=False,
        )
    )
    with get_db_connection(safe_db_path) as conn:
        _configure_derivadas_connection(conn)
        # Guardrail: scan/stats helpers must remain read-only.
        conn.execute("PRAGMA query_only = ON")
        yield conn


def _begin_derivadas_write_transaction(conn: sqlite3.Connection) -> None:
    """Acquire a write lock early to avoid lock escalation mid-sync."""

    if conn.in_transaction:
        return
    conn.execute("BEGIN IMMEDIATE")


def _is_sqlite_locked_error(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.Error):
        return False
    message = str(exc).casefold()
    return "database is locked" in message or "database schema is locked" in message


def _safe_sync_run_error_message(exc: BaseException) -> str:
    """Return a safe, non-sensitive error string for persistence.

    Full exception details are logged via logger.exception, but should not be
    stored in the DB because they may contain paths or other sensitive data.
    """

    kind = exc.__class__.__name__
    locked = _is_sqlite_locked_error(exc)
    digest = hashlib.sha256(f"{kind}:{exc}".encode("utf-8", "replace")).hexdigest()[:16]
    payload: dict[str, Any] = {"error": "sync_failed", "kind": kind, "digest": digest}
    if locked:
        payload["locked"] = True
    return json.dumps(payload, ensure_ascii=True)


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


def _normalize_sheet_file_path(value: Any) -> str:
    normalized = str(value).strip()
    if not normalized:
        return ""
    return os.path.abspath(os.path.expanduser(normalized))


def _sheet_stats_has_parse_evidence(stats: dict[str, Any] | None) -> bool:
    current = stats or {}
    accepted_edges = int(current.get("accepted_edges", 0) or 0)
    special_layout_detected = int(current.get("special_layout_detected", 0) or 0)
    informational_rows = int(current.get("informational_rows_skipped", 0) or 0)
    return accepted_edges > 0 or special_layout_detected > 0 or informational_rows > 0


def _build_sheet_evidence_summary(
    sheet_file_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    files_total = len(sheet_file_reports)
    files_with_evidence = 0
    files_without_evidence: list[str] = []
    for entry in sheet_file_reports:
        current_file = str(entry.get("sheet_file") or "").strip()
        has_evidence = bool(entry.get("has_parse_evidence"))
        if has_evidence:
            files_with_evidence += 1
            continue
        files_without_evidence.append(current_file)
    return {
        "files_total": files_total,
        "files_with_evidence": files_with_evidence,
        "files_without_evidence": files_without_evidence,
        "is_complete": files_total == files_with_evidence,
    }


def collect_db_edges(
    conn: sqlite3.Connection, table_name: str = "ssa_table"
) -> dict[str, Any]:
    """Collect normalized parent->child edges from `numero_ssa -> derivada_de`."""

    safe_table = _validate_table_name(table_name)
    query = (
        "SELECT numero_ssa, derivada_de "
        f'FROM "{safe_table}" '  # nosec B608  # skipcq: BAN-B608
        "WHERE derivada_de IS NOT NULL"
    )

    rows = conn.execute(
        query
    ).fetchall()  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query

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

    multiparent = {
        child: sorted(parents)
        for child, parents in child_to_parents.items()
        if len(parents) > 1
    }
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


def _load_sheet_dataframe(
    sheet_file: str, sheet_name: str | None = None
) -> list[pd.DataFrame]:
    if not isinstance(sheet_file, str) or not sheet_file.strip():
        raise ValueError("sheet_file must be a non-empty path string")
    if not os.path.exists(sheet_file):
        raise FileNotFoundError(f"Sheet source file not found: {sheet_file}")
    if not os.path.isfile(sheet_file):
        raise ValueError(f"sheet_file must be a file path: {sheet_file}")

    ext = os.path.splitext(sheet_file)[1].lower()
    if ext in {".csv", ".txt"}:
        return [pd.read_csv(sheet_file)]
    if ext == ".tsv":
        return [pd.read_csv(sheet_file, sep="\t")]
    if ext in {".xlsx", ".xlsm", ".xls"}:
        return _load_excel_frames(sheet_file, sheet_name=sheet_name)
    raise ValueError(f"Unsupported sheet format for derivadas sync: {sheet_file}")


def _load_excel_frames(
    sheet_file: str,
    *,
    sheet_name: str | None = None,
    header: int | None = 0,
) -> list[pd.DataFrame]:
    from utils.robust_importer import import_excel_robust

    try:
        frames: list[pd.DataFrame] = []
        parse_errors: list[tuple[str, Exception]] = []
        with pd.ExcelFile(sheet_file) as workbook:
            target_sheets = [sheet_name] if sheet_name else list(workbook.sheet_names)
            for target_sheet in target_sheets:
                try:
                    frame, _stats = import_excel_robust(
                        workbook,
                        sheet_name=target_sheet,
                        header=header,
                        raw_mode=True,
                        raise_on_error=True,
                    )
                    frames.append(frame)
                except Exception as exc:
                    logger.warning(
                        "Failed to parse sheet '%s' from '%s': %s",
                        target_sheet,
                        sheet_file,
                        exc,
                    )
                    parse_errors.append((target_sheet, exc))

        if frames:
            return frames
        if parse_errors:
            raise parse_errors[0][1]
        return []
    except Exception as exc:
        raise ValueError(
            f"Failed to parse sheet source file '{sheet_file}': {exc}"
        ) from exc


def _normalize_sheet_column_name(value: Any) -> str:
    text = str(value).strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text if ch.isalnum())


def _resolve_sheet_column_name(
    columns: list[str],
    requested: str | None,
    *,
    aliases: tuple[str, ...],
) -> str | None:
    if requested is None:
        return None
    if requested in columns:
        return requested

    normalized_map: dict[str, str] = {}
    for column in columns:
        key = _normalize_sheet_column_name(column)
        if key and key not in normalized_map:
            normalized_map[key] = column

    requested_norm = _normalize_sheet_column_name(requested)
    if requested_norm in normalized_map:
        return normalized_map[requested_norm]

    for alias in aliases:
        alias_norm = _normalize_sheet_column_name(alias)
        if alias_norm in normalized_map:
            return normalized_map[alias_norm]
    return None


def _resolve_sheet_columns(
    frame: pd.DataFrame,
    *,
    parent_col: str,
    child_col: str,
    label_col: str | None,
) -> tuple[str | None, str | None, str | None]:
    columns = [str(col) for col in frame.columns]
    resolved_parent = _resolve_sheet_column_name(
        columns, parent_col, aliases=SHEET_PARENT_ALIASES
    )
    resolved_child = _resolve_sheet_column_name(
        columns, child_col, aliases=SHEET_CHILD_ALIASES
    )
    resolved_label = _resolve_sheet_column_name(
        columns, label_col, aliases=SHEET_LABEL_ALIASES
    )
    return resolved_parent, resolved_child, resolved_label


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
        "missing_label_column_rows": 0,
        "resolved_parent_alias_rows": 0,
        "resolved_child_alias_rows": 0,
        "resolved_label_alias_rows": 0,
    }

    for frame in frames:
        if frame is None or frame.empty:
            continue

        resolved_parent_col, resolved_child_col, resolved_label_col = (
            _resolve_sheet_columns(
                frame,
                parent_col=parent_col,
                child_col=child_col,
                label_col=label_col,
            )
        )
        if not resolved_parent_col or not resolved_child_col:
            stats["missing_columns"] += int(len(frame))
            continue
        if resolved_parent_col != parent_col:
            stats["resolved_parent_alias_rows"] += int(len(frame))
        if resolved_child_col != child_col:
            stats["resolved_child_alias_rows"] += int(len(frame))
        if label_col:
            if resolved_label_col and resolved_label_col != label_col:
                stats["resolved_label_alias_rows"] += int(len(frame))
            if not resolved_label_col:
                stats["missing_label_column_rows"] += int(len(frame))

        stats["input_rows"] += int(len(frame))
        for _, row in frame.iterrows():
            parent_norm = _normalize_ssa(row.get(resolved_parent_col))
            child_norm = _normalize_ssa(row.get(resolved_child_col))
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
            relation_label = (
                _clean_relation_label(row.get(resolved_label_col))
                if resolved_label_col
                else None
            )
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
    if not edges and int(stats.get("missing_columns", 0)) > 0:
        fallback = _collect_special_visual_sheet_edges(
            sheet_file=sheet_file, sheet_name=sheet_name
        )
        fallback_stats = fallback.get("stats") or {}
        if int(fallback_stats.get("special_layout_detected", 0)) > 0:
            return fallback
    multiparent = {
        child: sorted(parents)
        for child, parents in child_to_parents.items()
        if len(parents) > 1
    }
    stats["multiparent_in_source"] = len(multiparent)
    return {"edges": edges, "stats": stats, "multiparent_detail": multiparent}


def _collect_special_visual_sheet_edges(
    sheet_file: str,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Fallback parser for "SSAs Derivadas e Relacionadas" visual matrix layout."""

    ext = os.path.splitext(sheet_file)[1].lower()
    if ext not in {".xlsx", ".xlsm", ".xls"}:
        return {
            "edges": [],
            "stats": {"accepted_edges": 0, "special_layout_detected": 0},
            "multiparent_detail": {},
        }

    raw_frames = _load_excel_frames(sheet_file, sheet_name=sheet_name, header=None)

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
        "informational_rows_skipped": 0,
        "missing_columns": 0,
        "missing_label_column_rows": 0,
        "resolved_parent_alias_rows": 0,
        "resolved_child_alias_rows": 0,
        "resolved_label_alias_rows": 0,
        "special_layout_detected": 0,
    }

    for frame in raw_frames:
        if frame is None or frame.empty:
            continue
        if frame.shape[0] <= SPECIAL_SHEET_HEADER_ROW_INDEX:
            continue
        header_row = frame.iloc[SPECIAL_SHEET_HEADER_ROW_INDEX]
        normalized_headers = [
            _normalize_sheet_column_name(header_row.iloc[index])
            for index in range(frame.shape[1])
        ]
        column_groups: list[tuple[int, int, int]] = []
        relation_indexes = [
            index for index, header in enumerate(normalized_headers) if header == "relacao"
        ]
        for relation_index in relation_indexes:
            child_index = next(
                (
                    index
                    for index in range(relation_index - 1, -1, -1)
                    if normalized_headers[index] == "numerodassa"
                ),
                None,
            )
            parent_index = next(
                (
                    index
                    for index in range(relation_index + 1, frame.shape[1])
                    if normalized_headers[index] == "numerodassa"
                ),
                None,
            )
            if child_index is None or parent_index is None:
                stats["missing_columns"] += 1
                continue
            column_groups.append((child_index, relation_index, parent_index))

        if not column_groups:
            continue

        stats["special_layout_detected"] += 1
        data_rows = frame.iloc[SPECIAL_SHEET_HEADER_ROW_INDEX + 1 :]
        stats["input_rows"] += int(len(data_rows))

        for _, row in data_rows.iterrows():
            for child_col, relation_col, parent_col in column_groups:
                child_raw = row.iloc[child_col]
                relation_raw = row.iloc[relation_col]
                parent_raw = row.iloc[parent_col]

                child_norm = _normalize_ssa(child_raw)
                parent_norm = _normalize_ssa(parent_raw)
                relation_norm = _clean_relation_label(relation_raw)
                # Visual sheets include many context/info rows with no edge payload.
                # Do not classify those as invalid parent/child to keep signal useful.
                if not parent_norm and not child_norm and relation_norm is None:
                    stats["informational_rows_skipped"] += 1
                    continue
                # Root/context rows often carry only child SSA with empty relation/parent.
                # Treat these as informational instead of invalid parent.
                if not parent_norm and relation_norm is None:
                    stats["informational_rows_skipped"] += 1
                    continue
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
                edges.append(
                    SourceEdge(
                        parent_ssa=parent_norm,
                        child_ssa=child_norm,
                        source_name=SOURCE_SHEET_DERIVADAS,
                        source_flag=SOURCE_FLAG_SHEET,
                        relation_type=RELATION_TYPE_SHEET,
                        relation_raw_label=relation_norm,
                    )
                )

    stats["accepted_edges"] = len(edges)
    multiparent = {
        child: sorted(parents)
        for child, parents in child_to_parents.items()
        if len(parents) > 1
    }
    stats["multiparent_in_source"] = len(multiparent)
    return {"edges": edges, "stats": stats, "multiparent_detail": multiparent}


def _merge_edges(source_edges: list[SourceEdge]) -> list[MatrixEdge]:
    merged: dict[tuple[str, str], MatrixEdge] = {}
    best_priority_by_pair: dict[tuple[str, str], int] = {}

    for edge in source_edges:
        key = (edge.parent_ssa, edge.child_ssa)
        prev = merged.get(key)
        source_priority = SOURCE_PRIORITY.get(edge.source_name, 0)
        if prev is None:
            merged[key] = MatrixEdge(
                parent_ssa=edge.parent_ssa,
                child_ssa=edge.child_ssa,
                source_flags=edge.source_flag,
                relation_type=edge.relation_type,
                relation_raw_label=edge.relation_raw_label,
            )
            best_priority_by_pair[key] = source_priority
            continue

        keep_label = prev.relation_raw_label
        keep_type = prev.relation_type

        if source_priority >= best_priority_by_pair.get(key, -1):
            best_priority_by_pair[key] = source_priority
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

    return list(merged.values())


def _build_child_parent_map(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    child_parents: dict[str, set[str]] = defaultdict(set)
    for parent, child in edges:
        child_parents[child].add(parent)
    return child_parents


def _cycle_nodes_scc(edges: list[tuple[str, str]]) -> set[str]:
    """Return nodes that participate in at least one directed cycle.

    Uses an iterative Kosaraju SCC pass to avoid recursion depth issues.
    """

    adjacency: dict[str, set[str]] = defaultdict(set)
    reverse_adjacency: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()

    for parent, child in edges:
        adjacency[parent].add(child)
        reverse_adjacency[child].add(parent)
        nodes.add(parent)
        nodes.add(child)

    visited: set[str] = set()
    order: list[str] = []
    for node in sorted(nodes):
        if node in visited:
            continue
        visited.add(node)
        stack: list[tuple[str, Iterator[str]]] = [
            (node, iter(adjacency.get(node, ())))
        ]  # (node, iterator)
        while stack:
            current, it = stack[-1]
            try:
                nxt = next(it)
            except StopIteration:
                stack.pop()
                order.append(current)
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            stack.append((nxt, iter(adjacency.get(nxt, ()))))

    cycles: set[str] = set()
    visited.clear()
    for node in reversed(order):
        if node in visited:
            continue
        component: list[str] = []
        queue = [node]
        visited.add(node)
        while queue:
            current = queue.pop()
            component.append(current)
            for prev in reverse_adjacency.get(current, ()):
                if prev in visited:
                    continue
                visited.add(prev)
                queue.append(prev)
        if len(component) > 1:
            cycles.update(component)

    return cycles


def _build_closure_rows(
    edges: list[tuple[str, str]], depth_cap: int = 32
) -> tuple[list[tuple[str, str, int, int, int]], set[str]]:
    adjacency: dict[str, tuple[str, ...]] = defaultdict(tuple)
    children_map: dict[str, list[str]] = defaultdict(list)
    for parent, child in edges:
        children_map[parent].append(child)
    adjacency = {
        parent: tuple(sorted(set(children), key=lambda value: value.casefold()))
        for parent, children in children_map.items()
    }

    cycle_nodes = _cycle_nodes_scc(edges)
    metrics: dict[tuple[str, str], list[int]] = {}

    # Avoid enumerating all simple paths (can explode in DAGs with merges). We compute:
    # - min_distance: shortest path length (BFS)
    # - max_distance: longest discovered depth within depth_cap
    # - path_count: number of distinct shortest paths (saturated to cap)
    path_count_cap = 1_000_000

    for ancestor in adjacency.keys():
        dist: dict[str, int] = {ancestor: 0}
        max_dist: dict[str, int] = {ancestor: 0}
        count: dict[str, int] = {ancestor: 1}
        queue = deque((ancestor,))
        while queue:
            node = queue.popleft()
            depth = dist[node]
            if depth >= depth_cap:
                continue
            for child in adjacency.get(node, ()):
                next_depth = depth + 1
                prev_depth = dist.get(child)
                if prev_depth is None:
                    dist[child] = next_depth
                    count[child] = count.get(node, 1)
                    queue.append(child)
                    continue
                if next_depth == prev_depth:
                    updated = count.get(child, 1) + count.get(node, 1)
                    count[child] = (
                        updated if updated < path_count_cap else path_count_cap
                    )

        max_queue = deque((ancestor,))
        while max_queue:
            node = max_queue.popleft()
            depth = max_dist[node]
            if depth >= depth_cap:
                continue
            for child in adjacency.get(node, ()):
                next_depth = depth + 1
                previous_max = max_dist.get(child)
                if previous_max is None or next_depth > previous_max:
                    max_dist[child] = next_depth
                    max_queue.append(child)

        for descendant, min_distance in dist.items():
            if descendant == ancestor:
                continue
            key = (ancestor, descendant)
            shortest_paths = count.get(descendant, 1)
            metrics[key] = [
                min_distance,
                max_dist.get(descendant, min_distance),
                shortest_paths,
            ]

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
        descendants_count = len(
            {descendant for descendant, _min_d, _max_d in descendants}
        )

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
        levels_below_max = max(
            (max_d for _desc, _min_d, max_d in descendants), default=0
        )
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
    rows = conn.execute(
        f'SELECT numero_ssa FROM "{safe_table}" WHERE numero_ssa IS NOT NULL'  # nosec B608  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
    ).fetchall()
    out: set[str] = set()
    for row in rows:
        normalized = _normalize_ssa(row[0])
        if normalized:
            out.add(normalized)
    return out


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    safe_table = _validate_table_name(table_name)
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (safe_table,),
    ).fetchone()
    return row is not None


def _analyze_reconciliation(
    all_ssa: set[str],
    matrix_edges: list[MatrixEdge],
    source_edges: list[SourceEdge],
) -> dict[str, Any]:
    pair_edges = [(edge.parent_ssa, edge.child_ssa) for edge in matrix_edges]

    child_parents = _build_child_parent_map(pair_edges)
    multiparent_children = {
        child: sorted(parents)
        for child, parents in child_parents.items()
        if len(parents) > 1
    }

    orphan_parents = sorted(
        {parent for parent, _child in pair_edges if parent not in all_ssa}
    )
    orphan_children = sorted(
        {child for _parent, child in pair_edges if child not in all_ssa}
    )

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

    cycle_nodes = _cycle_nodes_scc(pair_edges)
    return {
        "multiparent_children_count": len(multiparent_children),
        "multiparent_children_sample": dict(list(multiparent_children.items())[:20]),
        "orphan_parents_count": len(orphan_parents),
        "orphan_parents_sample": orphan_parents[:20],
        "orphan_children_count": len(orphan_children),
        "orphan_children_sample": orphan_children[:20],
        "db_vs_sheet_conflict_count": len(db_vs_sheet_conflicts),
        "db_vs_sheet_conflict_sample": dict(list(db_vs_sheet_conflicts.items())[:20]),
        "source_distribution": dict(
            sorted(source_distribution.items(), key=lambda item: int(item[0]))
        ),
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
    for (
        parent_ssa,
        child_ssa,
        source_name,
        source_flag,
        relation_type,
        relation_raw_label,
    ) in rows:
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
        for row in conn.execute(
            "SELECT parent_ssa, child_ssa FROM ssa_derivada_matrix"
        ).fetchall()
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


def _replace_closure(
    conn: sqlite3.Connection,
    closure_rows: list[tuple[str, str, int, int, int]],
    timestamp: str,
) -> None:
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
        [
            (ancestor, descendant, min_d, max_d, path_count, timestamp)
            for ancestor, descendant, min_d, max_d, path_count in closure_rows
        ],
    )


def _replace_summary(
    conn: sqlite3.Connection, summary_rows: list[tuple[Any, ...]]
) -> None:
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
    actor: str,
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
            actor,
            managed_sources,
            started_at,
            status,
            db_edges,
            sheet_edges,
            merged_edges
        ) VALUES (?, ?, ?, ?, 'running', ?, ?, ?)
        """,
        (
            mode,
            actor,
            ",".join(managed_sources),
            started_at,
            db_edges,
            sheet_edges,
            merged_edges,
        ),
    )
    run_id = row.lastrowid
    if run_id is None:
        raise RuntimeError("Failed to persist sync run metadata: missing lastrowid")
    return int(run_id)


def _finish_sync_run(
    conn: sqlite3.Connection,
    sync_run_id: int,
    finished_at: str,
    reconciliation: dict[str, Any],
    active_edges: int,
    status: str = "ok",
    graph_fingerprint: str | None = None,
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
            graph_fingerprint = ?,
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
            graph_fingerprint,
            message,
            sync_run_id,
        ),
    )


def _scan_materialization_integrity(conn: sqlite3.Connection) -> dict[str, Any]:
    """Validate materialized derivadas tables inside current transaction.

    The scan also returns the active matrix rows so the caller can reuse them
    for fingerprinting without issuing a second identical query.
    """

    matrix_rows = conn.execute(
        """
        SELECT parent_ssa, child_ssa, source_flags
        FROM ssa_derivada_matrix
        WHERE active = 1
        """
    ).fetchall()
    source_rows = conn.execute(
        """
        SELECT parent_ssa, child_ssa, source_flag
        FROM ssa_derivada_source
        WHERE is_active = 1
        """
    ).fetchall()

    matrix_pairs: dict[tuple[str, str], int] = {
        (row[0], row[1]): int(row[2]) for row in matrix_rows
    }
    source_flags_by_pair: dict[tuple[str, str], int] = defaultdict(int)
    for parent, child, source_flag in source_rows:
        source_flags_by_pair[(parent, child)] |= int(source_flag or 0)

    missing_source_pairs = sorted(
        [pair for pair in matrix_pairs if pair not in source_flags_by_pair]
    )
    source_without_matrix_pairs = sorted(
        [pair for pair in source_flags_by_pair if pair not in matrix_pairs]
    )
    flag_mismatch_pairs = sorted(
        [
            pair
            for pair in matrix_pairs
            if pair in source_flags_by_pair
            and matrix_pairs[pair] != source_flags_by_pair[pair]
        ]
    )
    invalid_matrix_pairs = sorted(
        [
            pair
            for pair in matrix_pairs
            if pair[0] == pair[1]
            or not _normalize_ssa(pair[0])
            or not _normalize_ssa(pair[1])
        ]
    )

    closure_self = int(
        conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_closure WHERE ancestor_ssa = descendant_ssa"
        ).fetchone()[0]
    )

    nodes_in_matrix: set[str] = set()
    for parent, child, _flags in matrix_rows:
        nodes_in_matrix.add(parent)
        nodes_in_matrix.add(child)
    summary_nodes = {
        row[0]
        for row in conn.execute("SELECT ssa FROM ssa_derivada_summary").fetchall()
    }
    summary_missing_nodes = sorted(nodes_in_matrix - summary_nodes)
    summary_extra_nodes = sorted(summary_nodes - nodes_in_matrix)

    issue_counts = {
        "missing_source_pairs": len(missing_source_pairs),
        "source_without_matrix_pairs": len(source_without_matrix_pairs),
        "flag_mismatch_pairs": len(flag_mismatch_pairs),
        "invalid_matrix_pairs": len(invalid_matrix_pairs),
        "closure_self_rows": closure_self,
        "summary_missing_nodes": len(summary_missing_nodes),
        "summary_extra_nodes": len(summary_extra_nodes),
    }
    is_consistent = all(count == 0 for count in issue_counts.values())

    return {
        "is_consistent": is_consistent,
        "issue_counts": issue_counts,
        "matrix_active_edges": len(matrix_rows),
        "matrix_rows": matrix_rows,
        "source_active_edges": len(source_rows),
        "summary_nodes": len(summary_nodes),
        "samples": {
            "missing_source_pairs": [
                f"{parent}->{child}" for parent, child in missing_source_pairs[:20]
            ],
            "source_without_matrix_pairs": [
                f"{parent}->{child}"
                for parent, child in source_without_matrix_pairs[:20]
            ],
            "flag_mismatch_pairs": [
                f"{parent}->{child}" for parent, child in flag_mismatch_pairs[:20]
            ],
            "invalid_matrix_pairs": [
                f"{parent}->{child}" for parent, child in invalid_matrix_pairs[:20]
            ],
            "summary_missing_nodes": summary_missing_nodes[:20],
            "summary_extra_nodes": summary_extra_nodes[:20],
        },
    }


def sync_derivadas(
    db_path: str,
    table_name: str = "ssa_table",
    *,
    sheet_file: str | None = None,
    sheet_files: list[str] | None = None,
    sheet_parent_col: str = "parent_ssa",
    sheet_child_col: str = "child_ssa",
    sheet_label_col: str | None = "relation_label",
    sheet_name: str | None = None,
    include_db_source: bool = True,
    full_rebuild: bool = False,
    verify_only: bool = False,
    actor: str | None = None,
) -> dict[str, Any]:
    """Run a full derivadas sync/validation cycle."""

    normalized_sheet_files: list[str] = []
    seen_sheet_files: set[str] = set()
    for candidate in [sheet_file] if sheet_file else []:
        normalized = _normalize_sheet_file_path(candidate)
        if normalized and normalized not in seen_sheet_files:
            normalized_sheet_files.append(normalized)
            seen_sheet_files.add(normalized)
    for candidate in sheet_files or []:
        normalized = _normalize_sheet_file_path(candidate)
        if normalized and normalized not in seen_sheet_files:
            normalized_sheet_files.append(normalized)
            seen_sheet_files.add(normalized)

    if not include_db_source and not normalized_sheet_files:
        raise ValueError(
            "sync_derivadas requires at least one source: include_db_source=True or sheet_file provided"
        )

    mode = "full_rebuild" if full_rebuild else "sync"
    timestamp = _now_utc_str()
    sync_actor = _resolve_sync_actor(actor)
    safe_db_path = str(
        ensure_path_is_allowed(
            db_path,
            purpose="sync derivadas database",
            expect_directory=False,
        )
    )

    with get_db_connection(safe_db_path) as conn:
        _configure_derivadas_connection(conn)
        db_source_table_exists = _table_exists(conn, table_name=table_name)

        source_edges: list[SourceEdge] = []
        db_stats: dict[str, Any] = {"accepted_edges": 0}
        sheet_stats: dict[str, Any] = {"accepted_edges": 0}
        db_multiparent: dict[str, Any] = {}
        sheet_multiparent: dict[str, Any] = {}
        sheet_file_reports: list[dict[str, Any]] = []

        if include_db_source and db_source_table_exists:
            db_result = collect_db_edges(conn, table_name=table_name)
            source_edges.extend(db_result["edges"])
            db_stats = db_result["stats"]
            db_multiparent = db_result["multiparent_detail"]

        if normalized_sheet_files:
            merged_sheet_stats: dict[str, Any] = {}
            merged_sheet_multiparent: dict[str, set[str]] = defaultdict(set)
            for current_sheet_file in normalized_sheet_files:
                sheet_result = collect_sheet_edges(
                    sheet_file=current_sheet_file,
                    parent_col=sheet_parent_col,
                    child_col=sheet_child_col,
                    label_col=sheet_label_col,
                    sheet_name=sheet_name,
                )
                source_edges.extend(sheet_result["edges"])
                current_stats = dict(sheet_result.get("stats") or {})
                for key, value in current_stats.items():
                    if isinstance(value, int):
                        merged_sheet_stats[key] = (
                            int(merged_sheet_stats.get(key, 0)) + value
                        )
                    else:
                        merged_sheet_stats[key] = value
                sheet_file_reports.append(
                    {
                        "sheet_file": current_sheet_file,
                        "stats": current_stats,
                        "has_parse_evidence": _sheet_stats_has_parse_evidence(
                            current_stats
                        ),
                    }
                )
                current_multiparent = sheet_result.get("multiparent_detail") or {}
                for child_ssa, parents in current_multiparent.items():
                    if isinstance(parents, list):
                        merged_sheet_multiparent[str(child_ssa)].update(
                            str(parent) for parent in parents
                        )
            sheet_stats = (
                merged_sheet_stats if merged_sheet_stats else {"accepted_edges": 0}
            )
            sheet_stats["files_count"] = len(normalized_sheet_files)
            sheet_multiparent = {
                child_ssa: sorted(parents)
                for child_ssa, parents in merged_sheet_multiparent.items()
            }

        merged_edges = _merge_edges(source_edges)

        if db_source_table_exists:
            all_ssa = _fetch_all_ssa(conn, table_name=table_name)
        else:
            all_ssa = set()
        reconciliation_pre = _analyze_reconciliation(
            all_ssa, merged_edges, source_edges
        )
        managed_source_names: set[str] = set()
        if include_db_source:
            managed_source_names.add(SOURCE_DB_FIELD)
        if normalized_sheet_files:
            managed_source_names.add(SOURCE_SHEET_DERIVADAS)
        managed_source_names.update(edge.source_name for edge in source_edges)
        managed_sources = sorted(managed_source_names)

        report: dict[str, Any] = {
            "mode": mode,
            "verify_only": bool(verify_only),
            "actor": sync_actor,
            "managed_sources": managed_sources,
            "db_stats": db_stats,
            "sheet_stats": sheet_stats,
            "sheet_files": list(normalized_sheet_files),
            "sheet_file_reports": sheet_file_reports,
            "sheet_evidence": _build_sheet_evidence_summary(sheet_file_reports),
            "merge_stats": {
                "source_edges": len(source_edges),
                "merged_edges": len(merged_edges),
            },
            "reconciliation": reconciliation_pre,
            "source_multiparent": {
                SOURCE_DB_FIELD: {
                    "count": len(db_multiparent),
                    "sample": dict(list(db_multiparent.items())[:20]),
                },
                SOURCE_SHEET_DERIVADAS: {
                    "count": len(sheet_multiparent),
                    "sample": dict(list(sheet_multiparent.items())[:20]),
                },
            },
            "timestamp": timestamp,
        }

        if verify_only:
            return report

        ensure_derivadas_schema_on_connection(conn)
        if conn.in_transaction:
            conn.commit()

        started_at = timestamp
        _begin_derivadas_write_transaction(conn)
        run_id = _start_sync_run(
            conn,
            mode=mode,
            actor=sync_actor,
            managed_sources=managed_sources,
            started_at=started_at,
            db_edges=int(db_stats.get("accepted_edges", 0)),
            sheet_edges=int(sheet_stats.get("accepted_edges", 0)),
            merged_edges=len(merged_edges),
        )
        conn.commit()

        try:
            _begin_derivadas_write_transaction(conn)
            _upsert_source_rows(
                conn, source_edges, managed_sources=managed_sources, timestamp=timestamp
            )

            matrix_edges = _matrix_from_active_sources(conn)
            _upsert_matrix_rows(
                conn,
                matrix_edges=matrix_edges,
                timestamp=timestamp,
                full_rebuild=full_rebuild,
            )

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
            edge_pairs = [
                (edge.parent_ssa, edge.child_ssa) for edge in active_matrix_edges
            ]
            edge_fingerprint = _graph_fingerprint(
                [
                    (edge.parent_ssa, edge.child_ssa, edge.source_flags)
                    for edge in active_matrix_edges
                ]
            )

            closure_rows, cycle_nodes = _build_closure_rows(edge_pairs)
            _replace_closure(conn, closure_rows=closure_rows, timestamp=timestamp)

            summary_rows = _build_summary_rows(
                edges=edge_pairs,
                closure_rows=closure_rows,
                cycle_nodes=cycle_nodes,
                timestamp=timestamp,
            )
            _replace_summary(conn, summary_rows=summary_rows)
            integrity_scan = _scan_materialization_integrity(conn)
            if not bool(integrity_scan.get("is_consistent")):
                issue_counts = integrity_scan.get("issue_counts", {})
                logger.error("Derivadas sync integrity check failed: %s", issue_counts)
                raise RuntimeError("Derivadas sync integrity check failed")

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
                graph_fingerprint=edge_fingerprint,
                message=json.dumps(
                    {"graph_fingerprint": edge_fingerprint}, ensure_ascii=False
                ),
            )
            conn.commit()

            report.update(
                {
                    "sync_run_id": run_id,
                    "active_edges": len(active_matrix_edges),
                    "closure_rows": len(closure_rows),
                    "summary_rows": len(summary_rows),
                    "reconciliation": reconciliation_post,
                    "graph_fingerprint": edge_fingerprint,
                    "finished_at": finished_at,
                    "integrity_check": integrity_scan,
                }
            )
            return report
        except Exception as exc:
            logger.exception("Derivadas sync failed: %s", exc)
            finished_at = _now_utc_str()
            if conn.in_transaction:
                conn.rollback()
            try:
                _begin_derivadas_write_transaction(conn)
                _finish_sync_run(
                    conn,
                    sync_run_id=run_id,
                    finished_at=finished_at,
                    reconciliation=reconciliation_pre,
                    active_edges=0,
                    status="error",
                    message=_safe_sync_run_error_message(exc),
                )
                conn.commit()
            except sqlite3.Error as sync_run_error:
                logger.error(
                    "Unable to persist failed sync_run metadata (run_id=%s): %s",
                    run_id,
                    sync_run_error,
                )
                conn.rollback()
            raise


def get_sync_stats(db_path: str) -> dict[str, Any]:
    """Return compact stats for matrix, closure, summary and latest sync run."""

    with _open_derivadas_read_connection(db_path) as conn:
        schema_readiness = scan_derivadas_read_schema_readiness(conn)
        if not schema_readiness["is_ready"]:
            return {
                "schema_ready": False,
                "schema_readiness": schema_readiness,
                "matrix_total": 0,
                "matrix_active": 0,
                "closure_total": 0,
                "summary_total": 0,
                "latest_sync": None,
            }

        matrix_active = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix WHERE active = 1"
        ).fetchone()[0]
        matrix_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_matrix"
        ).fetchone()[0]
        closure_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_closure"
        ).fetchone()[0]
        summary_total = conn.execute(
            "SELECT COUNT(*) FROM ssa_derivada_summary"
        ).fetchone()[0]
        sync_run_cols = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(ssa_derivada_sync_run)"
            ).fetchall()
        }
        has_actor = "actor" in sync_run_cols
        if has_actor:
            latest_sql = """
                SELECT
                    sync_run_id,
                    mode,
                    actor,
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
                    cycle_node_count,
                    graph_fingerprint
                FROM ssa_derivada_sync_run
                ORDER BY sync_run_id DESC
                LIMIT 1
            """
        else:
            latest_sql = """
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
                    cycle_node_count,
                    graph_fingerprint
                FROM ssa_derivada_sync_run
                ORDER BY sync_run_id DESC
                LIMIT 1
            """
        latest = conn.execute(latest_sql).fetchone()

        latest_row = (
            {
                "sync_run_id": latest[0],
                "mode": latest[1],
                "actor": latest[2] if has_actor else None,
                "managed_sources": latest[3] if has_actor else latest[2],
                "started_at": latest[4] if has_actor else latest[3],
                "finished_at": latest[5] if has_actor else latest[4],
                "status": latest[6] if has_actor else latest[5],
                "db_edges": latest[7] if has_actor else latest[6],
                "sheet_edges": latest[8] if has_actor else latest[7],
                "merged_edges": latest[9] if has_actor else latest[8],
                "active_edges": latest[10] if has_actor else latest[9],
                "conflict_count": latest[11] if has_actor else latest[10],
                "multiparent_count": latest[12] if has_actor else latest[11],
                "orphan_parent_count": latest[13] if has_actor else latest[12],
                "orphan_child_count": latest[14] if has_actor else latest[13],
                "cycle_node_count": latest[15] if has_actor else latest[14],
                "graph_fingerprint": latest[16] if has_actor else latest[15],
            }
            if latest
            else None
        )

        return {
            "schema_ready": True,
            "matrix_total": int(matrix_total),
            "matrix_active": int(matrix_active),
            "closure_total": int(closure_total),
            "summary_total": int(summary_total),
            "latest_sync": latest_row,
        }


def scan_derivadas_consistency(db_path: str) -> dict[str, Any]:
    """Independent low-cost consistency scan for derivadas materialization.

    This scan does not read source spreadsheets and does not modify data.
    """

    with _open_derivadas_read_connection(db_path) as conn:
        schema_readiness = scan_derivadas_read_schema_readiness(conn)
        if not schema_readiness["is_ready"]:
            return {
                "schema_ready": False,
                "is_consistent": False,
                "issue_counts": {
                    "schema_not_ready": 1,
                    "missing_source_pairs": 0,
                    "source_without_matrix_pairs": 0,
                    "flag_mismatch_pairs": 0,
                    "invalid_matrix_pairs": 0,
                    "closure_self_rows": 0,
                    "summary_missing_nodes": 0,
                    "summary_extra_nodes": 0,
                    "fingerprint_mismatch": 0,
                },
                "schema_readiness": schema_readiness,
                "matrix_active_edges": 0,
                "source_active_edges": 0,
                "summary_nodes": 0,
                "graph_fingerprint": None,
                "latest_sync": None,
                "samples": {
                    "missing_source_pairs": [],
                    "source_without_matrix_pairs": [],
                    "flag_mismatch_pairs": [],
                    "invalid_matrix_pairs": [],
                    "summary_missing_nodes": [],
                    "summary_extra_nodes": [],
                    "fingerprint": {"current": None, "latest_sync": None},
                },
            }

        integrity_scan = _scan_materialization_integrity(conn)
        matrix_rows = integrity_scan.get("matrix_rows", [])
        issue_counts = dict(integrity_scan["issue_counts"])

        latest = conn.execute(
            """
            SELECT sync_run_id, finished_at, status, message, graph_fingerprint
            FROM ssa_derivada_sync_run
            ORDER BY sync_run_id DESC
            LIMIT 1
            """
        ).fetchone()

        edge_fingerprint = _graph_fingerprint(
            [(row[0], row[1], int(row[2])) for row in matrix_rows]
        )
        latest_fingerprint: str | None = None
        if latest:
            latest_fingerprint = latest[4]
            if not latest_fingerprint and latest[3]:
                try:
                    payload = json.loads(latest[3])
                except (TypeError, ValueError) as exc:
                    logger.warning(
                        "Payload de sync_run sem JSON valido para graph_fingerprint: %s",
                        exc,
                    )
                    payload = {}
                latest_fingerprint = payload.get("graph_fingerprint")
        fingerprint_mismatch = (
            int(bool(latest_fingerprint and latest_fingerprint != edge_fingerprint))
            if latest
            else 0
        )

        issue_counts["fingerprint_mismatch"] = fingerprint_mismatch
        is_consistent = all(count == 0 for count in issue_counts.values())

        return {
            "schema_ready": True,
            "is_consistent": is_consistent,
            "issue_counts": issue_counts,
            "matrix_active_edges": int(integrity_scan["matrix_active_edges"]),
            "source_active_edges": int(integrity_scan["source_active_edges"]),
            "summary_nodes": int(integrity_scan["summary_nodes"]),
            "graph_fingerprint": edge_fingerprint,
            "latest_sync": (
                {
                    "sync_run_id": int(latest[0]),
                    "finished_at": latest[1],
                    "status": latest[2],
                    "message": latest[3],
                    "graph_fingerprint": latest_fingerprint,
                }
                if latest
                else None
            ),
            "samples": dict(
                integrity_scan["samples"],
                fingerprint={
                    "current": edge_fingerprint,
                    "latest_sync": latest_fingerprint,
                },
            ),
        }


def self_heal_derivadas(
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
    force: bool = False,
    actor: str | None = None,
) -> dict[str, Any]:
    """Attempt self-healing by running sync only when scan indicates issues."""

    before = scan_derivadas_consistency(db_path)
    if before["is_consistent"] and not force:
        return {"healed": False, "reason": "already_consistent", "before": before}

    sync_report = sync_derivadas(
        db_path=db_path,
        table_name=table_name,
        sheet_file=sheet_file,
        sheet_parent_col=sheet_parent_col,
        sheet_child_col=sheet_child_col,
        sheet_label_col=sheet_label_col,
        sheet_name=sheet_name,
        include_db_source=include_db_source,
        full_rebuild=full_rebuild,
        verify_only=False,
        actor=actor,
    )
    after = scan_derivadas_consistency(db_path)
    return {
        "healed": True,
        "before": before,
        "sync": sync_report,
        "after": after,
    }


def run_derivadas_maintenance(
    db_path: str,
    table_name: str = "ssa_table",
    *,
    min_interval_seconds: int = 3600,
    auto_heal: bool = True,
    full_rebuild: bool = False,
    actor: str | None = None,
) -> dict[str, Any]:
    """Background-friendly maintenance trigger with interval guard."""

    try:
        with _open_derivadas_read_connection(db_path) as conn:
            schema_readiness = scan_derivadas_read_schema_readiness(conn)
            latest = (
                conn.execute(
                    """
                    SELECT finished_at
                    FROM ssa_derivada_sync_run
                    WHERE status = 'ok'
                    ORDER BY sync_run_id DESC
                    LIMIT 1
                    """
                ).fetchone()
                if schema_readiness["is_ready"]
                else None
            )
    except sqlite3.OperationalError as exc:
        if _is_sqlite_locked_error(exc):
            return {
                "ran": False,
                "reason": "database_locked",
                "phase": "read_latest_sync",
                "error": str(exc),
            }
        raise

    now = datetime.now(timezone.utc)
    last_finished = _parse_utc_str(latest[0] if latest else None)
    if last_finished is not None:
        delta = now - last_finished
        if delta < timedelta(seconds=max(0, int(min_interval_seconds))):
            return {
                "ran": False,
                "reason": "interval_guard",
                "next_in_seconds": int(
                    max(0, int(min_interval_seconds) - delta.total_seconds())
                ),
            }

    try:
        scan_report = scan_derivadas_consistency(db_path)
    except sqlite3.OperationalError as exc:
        if _is_sqlite_locked_error(exc):
            return {
                "ran": False,
                "reason": "database_locked",
                "phase": "scan",
                "error": str(exc),
            }
        raise
    if not scan_report.get("schema_ready", True):
        return {
            "ran": True,
            "scan_only": True,
            "is_consistent": False,
            "reason": "schema_not_ready",
            "scan": scan_report,
        }

    if scan_report["is_consistent"]:
        return {
            "ran": True,
            "scan_only": True,
            "is_consistent": True,
            "scan": scan_report,
        }

    if not auto_heal:
        return {
            "ran": True,
            "scan_only": True,
            "is_consistent": False,
            "scan": scan_report,
        }

    try:
        heal_report = self_heal_derivadas(
            db_path=db_path,
            table_name=table_name,
            full_rebuild=full_rebuild,
            actor=actor or "maintenance",
        )
    except sqlite3.OperationalError as exc:
        if _is_sqlite_locked_error(exc):
            return {
                "ran": False,
                "reason": "database_locked",
                "phase": "self_heal",
                "error": str(exc),
            }
        raise
    return {
        "ran": True,
        "scan_only": False,
        "is_consistent": bool(heal_report.get("after", {}).get("is_consistent")),
        "heal": heal_report,
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
        "multiparent_children_count": reconciliation.get(
            "multiparent_children_count", 0
        ),
        "orphan_parents_count": reconciliation.get("orphan_parents_count", 0),
        "orphan_children_count": reconciliation.get("orphan_children_count", 0),
        "db_vs_sheet_conflict_count": reconciliation.get(
            "db_vs_sheet_conflict_count", 0
        ),
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
