from __future__ import annotations

from typing import Any


def fake_database_analyzer_type(
    *,
    structure: dict[str, Any],
    sanity: dict[str, Any],
):
    class FakeDatabaseAnalyzer:
        def __init__(self, db_path):
            self.db_path = db_path

        def analyze_table_structure(self):
            return structure

        def perform_sanity_check(self):
            return sanity

    return FakeDatabaseAnalyzer
