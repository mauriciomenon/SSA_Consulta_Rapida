"""Runtime table resolution for manual derivadas sync."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def resolve_derivadas_table_name(
    db_path: str,
    candidate_names: Iterable[str],
    fallback_table: str,
) -> str:
    """Return the first existing SSA table compatible with derivadas sync."""
    candidates = _valid_unique_table_names(candidate_names)
    if not candidates:
        return fallback_table
    try:
        compatible = _compatible_derivadas_tables(db_path, candidates)
    except (OSError, sqlite3.Error, ValueError) as exc:
        logger.warning("Falha ao resolver tabela para sync de derivadas: %s", exc)
        return fallback_table
    for name in candidates:
        if name in compatible:
            return name
    return fallback_table


def _valid_unique_table_names(names: Iterable[str]) -> list[str]:
    candidates: list[str] = []
    for name in names:
        if isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            if name not in candidates:
                candidates.append(name)
    return candidates


def _compatible_derivadas_tables(db_path: str, candidates: list[str]) -> set[str]:
    required_cols = {"numero_ssa", "derivada_de"}
    compatible: set[str] = set()
    with sqlite3.connect(db_path) as conn:
        existing = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for name in candidates:
            if name not in existing:
                continue
            columns = {
                str(row[1]).strip()
                for row in conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            }
            if required_cols.issubset(columns):
                compatible.add(name)
    return compatible
