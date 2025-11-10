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
