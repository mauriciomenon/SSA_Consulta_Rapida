"""Helpers to validate SQL identifiers used in dynamic SQL strings.

SQLite does not support parameterization of table or column names.
To avoid SQL injection or malformed queries, validate identifiers explicitly.
"""

from __future__ import annotations

import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_identifier(name: str | bytes | None) -> bool:
    """Return True if name is a safe SQL identifier.

    Accepts only ASCII letters, digits, and underscores, not starting with a digit.
    """
    if not isinstance(name, str):
        return False
    return bool(_IDENTIFIER_RE.fullmatch(name))


def quote_identifier(name: str | bytes | None) -> str:
    """Return a double-quoted SQL identifier after strict validation."""
    if not isinstance(name, str) or not is_valid_identifier(name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return f'"{name}"'
