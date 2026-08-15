"""Domain rules for SSA detail relationships."""

from __future__ import annotations

from typing import Any, Mapping, cast


def is_secondary_relation(row: Mapping[str, object]) -> bool:
    raw_label = str(row.get("relation_raw_label") or row.get("relacao") or "")
    label = raw_label.strip().casefold()
    if "derivad" in label:
        return False
    if label:
        return True
    raw_type = row.get("relation_type")
    if raw_type is None:
        return False
    try:
        return int(cast(Any, raw_type)) not in (0, 1)
    except (TypeError, ValueError):
        return False
