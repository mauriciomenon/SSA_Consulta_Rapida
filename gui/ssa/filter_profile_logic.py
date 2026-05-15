"""Filter profile normalization for the SSA GUI."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import re
from typing import Any

DEFAULT_SIMPLE_PROFILE_COLUMN = "situacao"
INLINE_EXECUTOR_COLUMN = "setor_executor"
INLINE_EMISSOR_COLUMN = "setor_emissor"


@dataclass(frozen=True)
class NormalizedFilterProfile:
    columns: OrderedDict[str, str] = field(default_factory=OrderedDict)
    or_groups: tuple[NormalizedOrGroup, ...] = ()
    profile_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedOrGroup:
    columns: tuple[str, ...]
    values: tuple[str, ...]


def normalize_filter_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for item in value if (text := normalize_filter_text(item))]
    if isinstance(value, str):
        text = normalize_filter_text(value)
        return [text] if text else []
    if value is None:
        return []
    text = normalize_filter_text(value)
    return [text] if text else []


def normalize_filter_text(value: Any) -> str:
    return str(value).strip()


def normalize_filter_display(value: Any) -> str:
    return ", ".join(normalize_filter_values(value))


def normalize_inline_executor_emissor_profile(profile_name: Any) -> NormalizedFilterProfile:
    raw = str(profile_name)
    tokens = [token.strip() for token in re.split(r"[+,]", raw) if token.strip()]
    if not tokens:
        return NormalizedFilterProfile()
    columns = OrderedDict(
        (
            (INLINE_EXECUTOR_COLUMN, ", ".join(tokens)),
            (INLINE_EMISSOR_COLUMN, ", ".join(tokens)),
        )
    )
    return NormalizedFilterProfile(
        columns=columns,
        or_groups=(
            NormalizedOrGroup(
                columns=(INLINE_EXECUTOR_COLUMN, INLINE_EMISSOR_COLUMN),
                values=tuple(tokens),
            ),
        ),
        profile_columns=(INLINE_EXECUTOR_COLUMN, INLINE_EMISSOR_COLUMN),
    )


def normalize_named_filter_profile(profile_def: Any) -> NormalizedFilterProfile:
    if not isinstance(profile_def, dict):
        return _normalize_simple_profile(profile_def)

    all_section = profile_def.get("all") if isinstance(profile_def.get("all"), dict) else None
    any_section = profile_def.get("any") if isinstance(profile_def.get("any"), list) else None
    if all_section or "any" in profile_def:
        return _normalize_sectioned_profile(all_section, any_section)
    return _normalize_flat_profile(profile_def)


def _normalize_simple_profile(profile_def: Any) -> NormalizedFilterProfile:
    columns: OrderedDict[str, str] = OrderedDict()
    profile_columns: dict[str, None] = {}
    values = normalize_filter_values(profile_def)
    if values:
        columns[DEFAULT_SIMPLE_PROFILE_COLUMN] = normalize_filter_display(profile_def)
        _append_unique(profile_columns, DEFAULT_SIMPLE_PROFILE_COLUMN)
    return NormalizedFilterProfile(
        columns=columns,
        or_groups=(),
        profile_columns=tuple(profile_columns),
    )


def _normalize_sectioned_profile(
    all_section: dict | None,
    any_section: list | None,
) -> NormalizedFilterProfile:
    columns: OrderedDict[str, str] = OrderedDict()
    or_groups: list[NormalizedOrGroup] = []
    profile_columns: dict[str, None] = {}
    all_columns: set[str] = set()
    if all_section:
        _add_profile_columns_from_mapping(all_section, columns, profile_columns)
        all_columns.update(str(column_name).strip() for column_name in all_section)

    if any_section:
        _normalize_any_filter_groups(
            any_section,
            columns,
            or_groups,
            profile_columns,
            protected_columns=all_columns,
        )

    return NormalizedFilterProfile(
        columns=columns,
        or_groups=tuple(or_groups),
        profile_columns=tuple(profile_columns),
    )


def _normalize_flat_profile(profile_def: dict) -> NormalizedFilterProfile:
    columns: OrderedDict[str, str] = OrderedDict()
    profile_columns: dict[str, None] = {}
    _add_profile_columns_from_mapping(profile_def, columns, profile_columns)
    return NormalizedFilterProfile(
        columns=columns,
        or_groups=(),
        profile_columns=tuple(profile_columns),
    )


def _normalize_any_filter_groups(
    any_section: list,
    columns: OrderedDict[str, str],
    or_groups: list[NormalizedOrGroup],
    profile_columns: dict[str, None],
    *,
    protected_columns: set[str],
) -> None:
    for group in any_section:
        if not isinstance(group, dict):
            continue
        raw_columns = group.get("columns") if isinstance(group.get("columns"), list) else []
        group_columns = tuple(
            normalized
            for column in raw_columns
            if (normalized := str(column).strip())
            and normalized not in protected_columns
        )
        values = tuple(normalize_filter_values(group.get("values")))
        if not group_columns:
            continue
        display_values = normalize_filter_display(group.get("values"))
        for column_name in group_columns:
            columns[column_name] = display_values
            _append_unique(profile_columns, column_name)
        or_groups.append(NormalizedOrGroup(columns=group_columns, values=values))


def _add_profile_columns_from_mapping(
    source: dict,
    columns: OrderedDict[str, str],
    profile_columns: dict[str, None],
) -> None:
    for column_name, value in source.items():
        normalized_column = normalize_filter_text(column_name)
        if not normalized_column:
            continue
        columns[normalized_column] = normalize_filter_display(value)
        _append_unique(profile_columns, normalized_column)


def _append_unique(values: dict[str, None], value: Any) -> None:
    normalized = normalize_filter_text(value)
    if normalized:
        values.setdefault(normalized, None)
