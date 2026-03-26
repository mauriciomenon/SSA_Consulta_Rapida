"""Utility script to remove trailing whitespace, convert tabs to 4 spaces, and collapse whitespace-only lines.

Usage (from project root):
    python scripts/clean_whitespace.py

It will modify *.py files except within virtual environments or build artefacts.
"""

from __future__ import annotations

from pathlib import Path

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "build",
    "dist",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
}

PYTHON_EXT = ".py"


def clean_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    changed = []
    modified = False
    for line in original.splitlines():
        # Replace tabs with 4 spaces
        line = line.replace("\t", "    ")
        # Strip trailing whitespace
        stripped = line.rstrip()
        if stripped != line:
            modified = True
            line = stripped
        # Normalize whitespace-only lines to empty
        if line.strip() == "" and line != "":
            modified = True
            line = ""
        changed.append(line)
    new_content = "\n".join(changed) + "\n"
    if new_content != original:
        path.write_text(new_content, encoding="utf-8")
        modified = True
    return modified


def iter_python_files(base: Path):
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix != PYTHON_EXT:
            continue
        if any(seg in EXCLUDE_DIRS for seg in p.parts):
            continue
        yield p


def main() -> None:
    base = Path(".")
    total = 0
    modified = 0
    for file_path in iter_python_files(base):
        total += 1
        if clean_file(file_path):
            modified += 1
    print(f"Whitespace cleanup complete: {modified}/{total} python files modified.")


if __name__ == "__main__":  # pragma: no cover
    main()
