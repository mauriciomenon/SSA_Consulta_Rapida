"""Supported spreadsheet import formats."""

from __future__ import annotations

SUPPORTED_IMPORT_SUFFIXES = (".xlsx",)


def is_supported_import_file(path: object) -> bool:
    return str(path or "").casefold().endswith(SUPPORTED_IMPORT_SUFFIXES)


def supported_import_suffixes_text() -> str:
    return ", ".join(SUPPORTED_IMPORT_SUFFIXES)
