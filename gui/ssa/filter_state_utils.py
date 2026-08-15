"""Small value helpers for filter state snapshots."""

from __future__ import annotations

from typing import Any


def copy_filter_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: copy_filter_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [copy_filter_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(copy_filter_value(item) for item in value)
    if isinstance(value, set):
        return {copy_filter_value(item) for item in value}
    return value


def copy_filter_mapping(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    return {key: copy_filter_value(item) for key, item in value.items()}


def freeze_filter_state_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(
            (str(key), freeze_filter_state_value(item))
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_filter_state_value(item) for item in value)
    if isinstance(value, set):
        return tuple(
            sorted((freeze_filter_state_value(item) for item in value), key=repr)
        )
    try:
        hash(value)
    except TypeError:
        return str(value)
    return value
