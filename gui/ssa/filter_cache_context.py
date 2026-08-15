"""Cache context helpers for SSA filter workers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class FilterCacheParts:
    columns: tuple[tuple[str, str], ...]
    advanced_payload: str
    advanced_filters_active: bool
    exclude_terminal_statuses: bool

    def fingerprint(self) -> tuple:
        return (
            self.columns,
            self.advanced_filters_active,
            self.advanced_payload,
            self.exclude_terminal_statuses,
        )


def build_filter_cache_fingerprint(
    column_filters: dict | None,
    advanced_filters: dict | None,
    *,
    advanced_filters_active: bool,
    exclude_terminal_statuses: bool,
) -> tuple:
    """Build a lightweight fingerprint to decide whether the digest is stale."""
    parts = build_filter_cache_parts(
        column_filters,
        advanced_filters,
        advanced_filters_active=advanced_filters_active,
        exclude_terminal_statuses=exclude_terminal_statuses,
    )
    return parts.fingerprint()


def build_filter_cache_snapshot(
    column_filters: dict | None,
    advanced_filters: dict | None,
    *,
    advanced_filters_active: bool,
    exclude_terminal_statuses: bool,
) -> tuple[tuple, str]:
    parts = build_filter_cache_parts(
        column_filters,
        advanced_filters,
        advanced_filters_active=advanced_filters_active,
        exclude_terminal_statuses=exclude_terminal_statuses,
    )
    return parts.fingerprint(), build_filter_cache_context_from_parts(parts)


def build_filter_cache_context(
    column_filters: dict | None,
    advanced_filters: dict | None,
    *,
    advanced_filters_active: bool,
    exclude_terminal_statuses: bool,
) -> str:
    """Build a deterministic cache context for the effective filter state."""
    parts = build_filter_cache_parts(
        column_filters,
        advanced_filters,
        advanced_filters_active=advanced_filters_active,
        exclude_terminal_statuses=exclude_terminal_statuses,
    )
    return build_filter_cache_context_from_parts(parts)


def build_filter_cache_context_from_parts(parts: FilterCacheParts) -> str:
    digest = hashlib.sha256()
    has_context = False

    for column_name, normalized_value in parts.columns:
        if normalized_value == "":
            continue
        has_context = True
        digest.update(b"column\x00")
        digest.update(column_name.encode("utf-8", "surrogatepass"))
        digest.update(b"\x00")
        digest.update(normalized_value.encode("utf-8", "surrogatepass"))

    if parts.advanced_payload:
        has_context = True
        digest.update(b"advanced_active\x001")
        digest.update(b"advanced_payload\x00")
        digest.update(parts.advanced_payload.encode("utf-8"))

    if parts.exclude_terminal_statuses:
        has_context = True
        digest.update(b"exclude_terminal_statuses\x001")

    if not has_context:
        return ""
    return f"sha256:{digest.hexdigest()}"


def build_filter_cache_parts(
    column_filters: dict | None,
    advanced_filters: dict | None,
    *,
    advanced_filters_active: bool,
    exclude_terminal_statuses: bool,
) -> FilterCacheParts:
    safe_column_filters = column_filters if isinstance(column_filters, dict) else {}
    safe_advanced_filters = advanced_filters if isinstance(advanced_filters, dict) else {}
    normalized_columns = tuple(
        sorted(
            (str(column), str(value).strip())
            for column, value in safe_column_filters.items()
        )
    )
    advanced_payload = (
        _stable_advanced_payload(safe_advanced_filters)
        if advanced_filters_active and safe_advanced_filters
        else ""
    )
    return FilterCacheParts(
        columns=normalized_columns,
        advanced_payload=advanced_payload,
        advanced_filters_active=bool(advanced_filters_active),
        exclude_terminal_statuses=bool(exclude_terminal_statuses),
    )


def _stable_advanced_payload(value: dict) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=lambda value: f"<non-json:{type(value).__name__}:{id(value)}>",
        )
    except (TypeError, ValueError):
        return "<invalid-json>"
