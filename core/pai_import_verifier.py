"""Verification helpers for PAI imports."""

from __future__ import annotations

import logging
from pathlib import Path
from sqlite3 import Error as SQLiteError

from armazenamento import database
from shared.db_names import CANONICAL_SSA_TABLE

logger = logging.getLogger(__name__)


def count_imported_ssa_rows(db_path: Path) -> int | None:
    if not Path(db_path).exists():
        return 0
    try:
        return database.count_table_rows(str(db_path), CANONICAL_SSA_TABLE)
    except (OSError, ValueError, SQLiteError) as exc:
        logger.error("Falha ao verificar linhas importadas PAI: %s", exc)
        return None
