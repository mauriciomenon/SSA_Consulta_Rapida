#!/usr/bin/env python3
"""CLI utilitario para sincronizacao e consulta de derivadas."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any

# Resolve imports when executed as `python scripts/derivadas_cli.py`.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from armazenamento.derivadas_queries import ALLOWED_TOP_METRICS  # noqa: E402
from armazenamento.derivadas_queries import (
    get_ancestors,
    get_children,
    get_descendants,
    get_hierarchy_profile,
    get_parent,
    get_parents,
    get_paths_down,
    get_paths_up,
    get_ssa_hierarchy_snapshot,
    get_top_by_metric,
)
from armazenamento.derivadas_schema import scan_derivadas_schema_readiness_from_path  # noqa: E402
from armazenamento.derivadas_sync import get_sync_stats  # noqa: E402
from armazenamento.derivadas_sync import (
    run_derivadas_maintenance,
    scan_derivadas_consistency,
    self_heal_derivadas,
    sync_derivadas,
)


def _as_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _print_list(title: str, values: list[str]) -> None:
    print(title)
    if not values:
        print("  (none)")
        return
    for value in values:
        print(f"  - {value}")


def _list_special_sheet_files(docs_dir: str) -> list[str]:
    if not isinstance(docs_dir, str) or not docs_dir.strip():
        raise ValueError("special docs dir must be a non-empty path")
    normalized = os.path.abspath(os.path.expanduser(docs_dir.strip()))
    if not os.path.isdir(normalized):
        raise ValueError(f"special docs dir not found: {normalized}")
    files: list[str] = []
    for base_name in os.listdir(normalized):
        lowered = str(base_name).strip().casefold()
        if lowered.startswith("ssas derivadas e relacionadas") and lowered.endswith(
            ".xlsx"
        ):
            files.append(os.path.join(normalized, base_name))
    return sorted(files, key=lambda path: os.path.basename(path).casefold())


def _handle_sync(args: argparse.Namespace) -> dict[str, Any]:
    sheet_files: list[str] = []
    if args.sheet_files_glob:
        sheet_files = sorted(glob.glob(args.sheet_files_glob))
    if args.special_docs_dir:
        sheet_files.extend(_list_special_sheet_files(args.special_docs_dir))
    report = sync_derivadas(
        db_path=args.db,
        table_name=args.table_name,
        sheet_file=args.sheet_file,
        sheet_files=sheet_files or None,
        sheet_parent_col=args.sheet_parent_col,
        sheet_child_col=args.sheet_child_col,
        sheet_label_col=args.sheet_label_col,
        sheet_name=args.sheet_name,
        include_db_source=not args.no_db_source,
        full_rebuild=args.full_rebuild,
        verify_only=args.verify_only,
        actor=args.actor,
    )
    if args.require_consistency and not args.verify_only:
        scan = scan_derivadas_consistency(db_path=args.db)
        report["consistency_scan"] = scan
        if not bool(scan.get("schema_ready")) or not bool(scan.get("is_consistent")):
            issue_counts = scan.get("issue_counts") or {}
            raise RuntimeError(
                f"Derivadas consistency check failed: {json.dumps(issue_counts, ensure_ascii=True)}"
            )
    return report


def _handle_stats(args: argparse.Namespace) -> dict[str, Any]:
    return get_sync_stats(db_path=args.db)


def _handle_scan(args: argparse.Namespace) -> dict[str, Any]:
    return scan_derivadas_consistency(db_path=args.db)


def _handle_schema_scan(args: argparse.Namespace) -> dict[str, Any]:
    return scan_derivadas_schema_readiness_from_path(db_path=args.db)


def _handle_heal(args: argparse.Namespace) -> dict[str, Any]:
    return self_heal_derivadas(
        db_path=args.db,
        table_name=args.table_name,
        sheet_file=args.sheet_file,
        sheet_parent_col=args.sheet_parent_col,
        sheet_child_col=args.sheet_child_col,
        sheet_label_col=args.sheet_label_col,
        sheet_name=args.sheet_name,
        include_db_source=not args.no_db_source,
        full_rebuild=args.full_rebuild,
        force=args.force,
        actor=args.actor,
    )


def _handle_maintenance(args: argparse.Namespace) -> dict[str, Any]:
    return run_derivadas_maintenance(
        db_path=args.db,
        table_name=args.table_name,
        min_interval_seconds=args.min_interval_seconds,
        auto_heal=not args.no_auto_heal,
        full_rebuild=args.full_rebuild,
        actor=args.actor,
    )


def _handle_info(args: argparse.Namespace) -> dict[str, Any]:
    profile = get_hierarchy_profile(args.db, args.ssa)
    if not args.with_lineage:
        return profile
    return {
        "profile": profile,
        "ancestors": get_ancestors(args.db, args.ssa, max_distance=args.depth),
        "descendants": get_descendants(args.db, args.ssa, max_distance=args.depth),
    }


def _handle_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    return get_ssa_hierarchy_snapshot(args.db, args.ssa, max_distance=args.depth)


def _handle_parents(args: argparse.Namespace) -> dict[str, Any]:
    parents = get_parents(args.db, args.ssa)
    return {
        "ssa": args.ssa,
        "parent": get_parent(args.db, args.ssa),
        "parents": parents,
        "count": len(parents),
    }


def _handle_children(args: argparse.Namespace) -> dict[str, Any]:
    children = get_children(args.db, args.ssa)
    return {
        "ssa": args.ssa,
        "children": children,
        "count": len(children),
    }


def _handle_lineage(args: argparse.Namespace) -> dict[str, Any]:
    data: dict[str, Any] = {"ssa": args.ssa, "direction": args.direction}
    if args.direction in {"up", "both"}:
        data["up_paths"] = get_paths_up(
            args.db, args.ssa, depth=args.depth, max_nodes=args.max_nodes
        )
    if args.direction in {"down", "both"}:
        data["down_paths"] = get_paths_down(
            args.db, args.ssa, depth=args.depth, max_nodes=args.max_nodes
        )
    return data


def _handle_top(args: argparse.Namespace) -> dict[str, Any]:
    rows = get_top_by_metric(args.db, args.metric, limit=args.limit)
    return {"metric": args.metric, "limit": args.limit, "rows": rows}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Derivadas database helper CLI")
    parser.add_argument("--db", default="data/ssas.db", help="SQLite database path")
    parser.add_argument("--table-name", default="ssa_table", help="Base SSA table name")
    parser.add_argument(
        "--actor", default=None, help="Optional actor label for audit trail"
    )
    parser.add_argument(
        "--output", choices=("text", "json"), default="text", help="Output format"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="Synchronize derivadas tables")
    sync_parser.add_argument("--sheet-file", help="Optional sheet/csv source path")
    sync_parser.add_argument(
        "--sheet-files-glob",
        help="Optional glob pattern to pass multiple sheet files to derivadas sync",
    )
    sync_parser.add_argument(
        "--special-docs-dir",
        help="Optional docs dir to auto-discover SSAs Derivadas e Relacionadas_*.xlsx files",
    )
    sync_parser.add_argument("--sheet-name", help="Optional sheet name when using xlsx")
    sync_parser.add_argument(
        "--sheet-parent-col", default="parent_ssa", help="Sheet parent column"
    )
    sync_parser.add_argument(
        "--sheet-child-col", default="child_ssa", help="Sheet child column"
    )
    sync_parser.add_argument(
        "--sheet-label-col",
        default="relation_label",
        help="Sheet relation label column",
    )
    sync_parser.add_argument(
        "--full-rebuild", action="store_true", help="Hard cleanup stale matrix rows"
    )
    sync_parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only validate and report without writing",
    )
    sync_parser.add_argument(
        "--require-consistency",
        action="store_true",
        help="Fail sync command when post-sync consistency scan is not clean",
    )
    sync_parser.add_argument(
        "--no-db-source", action="store_true", help="Ignore DB derivada_de source"
    )
    sync_parser.set_defaults(func=_handle_sync)

    stats_parser = sub.add_parser(
        "stats", help="Show derivadas sync/materialization stats"
    )
    stats_parser.set_defaults(func=_handle_stats)

    scan_parser = sub.add_parser("scan", help="Run independent consistency scan")
    scan_parser.set_defaults(func=_handle_scan)

    schema_scan_parser = sub.add_parser(
        "schema-scan", help="Run schema readiness scan without migration"
    )
    schema_scan_parser.set_defaults(func=_handle_schema_scan)

    heal_parser = sub.add_parser("heal", help="Run self-heal based on consistency scan")
    heal_parser.add_argument("--sheet-file", help="Optional sheet/csv source path")
    heal_parser.add_argument("--sheet-name", help="Optional sheet name when using xlsx")
    heal_parser.add_argument(
        "--sheet-parent-col", default="parent_ssa", help="Sheet parent column"
    )
    heal_parser.add_argument(
        "--sheet-child-col", default="child_ssa", help="Sheet child column"
    )
    heal_parser.add_argument(
        "--sheet-label-col",
        default="relation_label",
        help="Sheet relation label column",
    )
    heal_parser.add_argument(
        "--full-rebuild", action="store_true", help="Hard cleanup stale matrix rows"
    )
    heal_parser.add_argument(
        "--no-db-source", action="store_true", help="Ignore DB derivada_de source"
    )
    heal_parser.add_argument(
        "--force",
        action="store_true",
        help="Force healing even when scan is consistent",
    )
    heal_parser.set_defaults(func=_handle_heal)

    maintenance_parser = sub.add_parser(
        "maintenance",
        help="Run interval-guarded low-cost maintenance (scan + optional heal)",
    )
    maintenance_parser.add_argument(
        "--min-interval-seconds",
        type=int,
        default=14400,
        help="Minimum wait between maintenance runs in seconds (default: 14400)",
    )
    maintenance_parser.add_argument(
        "--no-auto-heal",
        action="store_true",
        help="Disable automatic healing actions during maintenance",
    )
    maintenance_parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Force a full rebuild instead of incremental maintenance",
    )
    maintenance_parser.set_defaults(func=_handle_maintenance)

    info_parser = sub.add_parser("info", help="Show hierarchy profile for one SSA")
    info_parser.add_argument("ssa", help="SSA number")
    info_parser.add_argument(
        "--with-lineage", action="store_true", help="Include ancestor/descendant rows"
    )
    info_parser.add_argument(
        "--depth", type=int, default=5, help="Depth cap for lineage retrieval"
    )
    info_parser.set_defaults(func=_handle_info)

    snapshot_parser = sub.add_parser(
        "snapshot", help="Single-call hierarchy payload for one SSA"
    )
    snapshot_parser.add_argument("ssa", help="SSA number")
    snapshot_parser.add_argument(
        "--depth", type=int, default=5, help="Max ancestor/descendant distance"
    )
    snapshot_parser.set_defaults(func=_handle_snapshot)

    parents_parser = sub.add_parser("parents", help="List direct parents")
    parents_parser.add_argument("ssa", help="SSA number")
    parents_parser.set_defaults(func=_handle_parents)

    children_parser = sub.add_parser("children", help="List direct children")
    children_parser.add_argument("ssa", help="SSA number")
    children_parser.set_defaults(func=_handle_children)

    lineage_parser = sub.add_parser("lineage", help="List path lineage up/down")
    lineage_parser.add_argument("ssa", help="SSA number")
    lineage_parser.add_argument(
        "--direction", choices=("up", "down", "both"), default="both"
    )
    lineage_parser.add_argument("--depth", type=int, default=5, help="Path depth cap")
    lineage_parser.add_argument(
        "--max-nodes", type=int, default=500, help="Traversal cap"
    )
    lineage_parser.set_defaults(func=_handle_lineage)

    top_parser = sub.add_parser("top", help="Top SSAs by hierarchy metric")
    top_parser.add_argument(
        "--metric", choices=tuple(ALLOWED_TOP_METRICS.keys()), default="direct_children"
    )
    top_parser.add_argument("--limit", type=int, default=20)
    top_parser.set_defaults(func=_handle_top)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    if args.output == "json":
        _as_json(result)
        return 0

    # Text output (human readable shortcuts; JSON remains available via --output json)
    if args.command == "parents":
        _print_list("Parents:", result["parents"])
        print(f"Count: {result['count']}")
        if result.get("parent"):
            print(f"Single parent: {result['parent']}")
        return 0
    if args.command == "children":
        _print_list("Children:", result["children"])
        print(f"Count: {result['count']}")
        return 0
    if args.command == "top":
        print(f"Top metric: {result['metric']} (limit={result['limit']})")
        for row in result["rows"]:
            print(
                f"{row['ssa']}  metric={row['metric']}  "
                f"children={row['direct_children_count']}  descendants={row['descendants_count']}"
            )
        return 0

    # Remaining commands print compact JSON to keep output deterministic in text mode.
    _as_json(result)
    return 0


def _main_entrypoint() -> int:
    try:
        return main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main_entrypoint())
