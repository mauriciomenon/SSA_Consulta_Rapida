"""Supported spreadsheet import formats."""

from __future__ import annotations

import os

SUPPORTED_IMPORT_SUFFIXES = (".xlsx",)


def is_supported_import_file(path: str | os.PathLike[str] | None) -> bool:
    if path is None:
        return False
    try:
        path_text = os.fspath(path)
    except TypeError:
        return False
    if not isinstance(path_text, str):
        return False
    return path_text.casefold().endswith(SUPPORTED_IMPORT_SUFFIXES)


def supported_import_suffixes_text() -> str:
    return ", ".join(SUPPORTED_IMPORT_SUFFIXES)
