from __future__ import annotations

import itertools
from collections.abc import Mapping

ASCII_ARG_LIMIT = 50
ASCII_ARG_DEPTH_LIMIT = 3


def sanitize_ascii_text(value: object) -> str:
    return str(value).encode("ascii", "ignore").decode("ascii")


def sanitize_ascii_arg(value: object, depth: int = 0) -> object:
    if isinstance(value, str):
        return sanitize_ascii_text(value)
    if isinstance(value, (int, float, bool, type(None))):
        return value
    if depth >= ASCII_ARG_DEPTH_LIMIT:
        return sanitize_ascii_text(value)
    if isinstance(value, Mapping):
        return {
            sanitize_ascii_text(key): sanitize_ascii_arg(item, depth + 1)
            for key, item in itertools.islice(value.items(), ASCII_ARG_LIMIT)
        }
    if isinstance(value, tuple):
        return tuple(
            sanitize_ascii_arg(item, depth + 1)
            for item in itertools.islice(value, ASCII_ARG_LIMIT)
        )
    if isinstance(value, list):
        return [
            sanitize_ascii_arg(item, depth + 1)
            for item in itertools.islice(value, ASCII_ARG_LIMIT)
        ]
    if isinstance(value, set):
        return {
            sanitize_ascii_arg(item, depth + 1)
            for item in itertools.islice(value, ASCII_ARG_LIMIT)
        }
    return sanitize_ascii_text(value)
