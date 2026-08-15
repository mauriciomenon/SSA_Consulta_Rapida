"""Display naming rules for saved GUI filters."""

from __future__ import annotations

from typing import Any


def build_persistent_filter_name(
    state: dict[str, Any],
    *,
    existing_count: int,
) -> str:
    search_text = str(state.get("search_text", "") or "").strip()
    if search_text:
        return search_text
    profile_name = str(state.get("current_filter_profile") or "").strip()
    if profile_name:
        return profile_name
    return f"Filtro combinado {existing_count + 1}"
