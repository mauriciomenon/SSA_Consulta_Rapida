"""Supported spreadsheet import formats."""

from __future__ import annotations


SUPPORTED_IMPORT_SUFFIXES = (".xlsx",)


def supported_import_suffixes_text() -> str:
    return ", ".join(SUPPORTED_IMPORT_SUFFIXES)
