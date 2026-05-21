"""Database operations used by GUI controllers."""

from __future__ import annotations

from typing import Any, Callable


def execute_vacuum_analyze(
    db_path: str, vacuum_analyze_database_fn: Callable[[str], dict[str, Any]]
) -> dict[str, Any]:
    return vacuum_analyze_database_fn(db_path)


def validate_database_candidate(
    db_file: str,
    *,
    table_name: str,
    query_db_fn: Callable[..., Any],
) -> dict[str, Any]:
    try:
        test_df = query_db_fn(db_file, table_name, raise_on_error=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "db_file": db_file}
    has_rows = bool(test_df is not None and not test_df.empty)
    return {"ok": has_rows, "db_file": db_file}
