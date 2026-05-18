"""Domain helpers for interactive configuration updates."""

from __future__ import annotations

from typing import Any

from core.regex_safety import is_safe_regex_pattern

ALLOWED_FILTER_MODES = ("contains", "prefix", "suffix", "exact", "regex")
CLEAR_DEFAULT_FILTERS_INPUT = "[]"


def normalize_filter_mode(value: str) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in ALLOWED_FILTER_MODES:
        return normalized
    return None


def unsafe_default_filters(filters: list[str], *, default_mode: str) -> list[str]:
    return [
        term
        for term in filters
        if not is_default_filter_allowed_by_regex_policy(term, default_mode=default_mode)
    ]


def is_default_filter_allowed_by_regex_policy(
    term: str, *, default_mode: str
) -> bool:
    """Validate regex policy for terms forced by '~' or by global regex mode."""
    is_regex_term, candidate = split_default_filter_markers(str(term or "").strip())
    if not candidate:
        return True
    if is_regex_term:
        return is_safe_regex_pattern(candidate, reject_quantifiers=True)
    if default_mode == "regex":
        return is_safe_regex_pattern(candidate, reject_quantifiers=True)
    return True


def split_default_filter_markers(term: str) -> tuple[bool, str]:
    candidate = str(term or "").strip()
    if candidate and candidate[0] in {"!", "-"}:
        candidate = candidate[1:].strip()
    if candidate.startswith("~"):
        return True, candidate[1:].strip()
    return False, candidate


def strip_negative_marker(term: str) -> str:
    if term and term[0] in {"!", "-"}:
        return term[1:].strip()
    return term


def resolve_filter_mode_change(raw_filter_mode: str) -> dict[str, Any]:
    requested_mode = str(raw_filter_mode or "").strip().lower()
    changed_filter_mode = False
    invalid_filter_mode = False
    new_filter_mode: str | None = None
    if requested_mode:
        new_filter_mode = normalize_filter_mode(requested_mode)
        changed_filter_mode = new_filter_mode is not None
        invalid_filter_mode = new_filter_mode is None
    return {
        "changed_filter_mode": changed_filter_mode,
        "invalid_filter_mode": invalid_filter_mode,
        "new_filter_mode": new_filter_mode,
    }


def resolve_default_filters_change(
    raw_default_filters: str | None, *, effective_filter_mode: str
) -> dict[str, Any]:
    changed_default_filters = False
    new_default_filters: list[str] | None = None
    unsafe_filters: list[str] = []

    if raw_default_filters is None:
        return {
            "changed_default_filters": changed_default_filters,
            "new_default_filters": new_default_filters,
            "unsafe_filters": unsafe_filters,
        }

    raw_filters = str(raw_default_filters).strip()
    changed_default_filters = True
    if raw_filters == CLEAR_DEFAULT_FILTERS_INPUT:
        new_default_filters = []
    else:
        new_default_filters = [
            item.strip() for item in raw_filters.split(",") if item.strip()
        ]
    unsafe_filters = unsafe_default_filters(
        new_default_filters,
        default_mode=str(effective_filter_mode),
    )
    if unsafe_filters:
        changed_default_filters = False
        new_default_filters = None

    return {
        "changed_default_filters": changed_default_filters,
        "new_default_filters": new_default_filters,
        "unsafe_filters": unsafe_filters,
    }


def resolve_config_command_changes(
    *,
    current_filter_mode: str,
    raw_filter_mode: str,
    raw_default_filters: str | None,
) -> dict[str, Any]:
    mode_change = resolve_filter_mode_change(raw_filter_mode)
    effective_filter_mode = (
        mode_change["new_filter_mode"]
        if mode_change["changed_filter_mode"] and mode_change["new_filter_mode"]
        else current_filter_mode
    )
    filters_change = resolve_default_filters_change(
        raw_default_filters,
        effective_filter_mode=str(effective_filter_mode),
    )
    return {**mode_change, **filters_change}


def apply_settings_updates(
    settings: dict[str, Any],
    *,
    filter_mode: str | None = None,
    default_filters: list[str] | None = None,
) -> dict[str, Any]:
    updated = dict(settings)
    if filter_mode is not None:
        updated["user_preferences"] = {
            **dict(settings.get("user_preferences") or {}),
            "filter_mode_default": filter_mode,
        }
    if default_filters is not None:
        updated["default_filters"] = list(default_filters)
    return updated
