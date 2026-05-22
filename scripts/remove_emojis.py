"""Remove emojis from text files in the repository.

Usage:
    python scripts/remove_emojis.py --dry-run
    python scripts/remove_emojis.py --apply

This script will by default scan files with extensions: .md, .rst, .txt and files named README*.
It writes backups to .emoji_backups/<relative_path>.bak before modifying.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Unicode ranges commonly used for emojis
EMOJI_RANGES = [
    (0x231A, 0x231B),  # Watch/hourglass
    (0x2328, 0x2328),  # Keyboard
    (0x23CF, 0x23FA),  # Media controls and time symbols
    (0x2600, 0x26FF),  # Misc symbol emoji forms
    (0x2705, 0x2705),  # White heavy check mark
    (0x2708, 0x270D),  # Travel and writing emoji forms
    (0x2728, 0x2728),  # Sparkles
    (0x274C, 0x274E),  # Cross mark emoji forms
    (0x2753, 0x2757),  # Question/exclamation emoji forms
    (0x2795, 0x2797),  # Plus/minus/divide emoji forms
    (0x27A1, 0x27BF),  # Arrow and loop emoji forms
    (0x2934, 0x2935),  # Arrow emoji forms
    (0x2B05, 0x2B55),  # Arrow/shape emoji forms
    (0x3030, 0x303D),  # Wavy dash and part alternation mark
    (0x3297, 0x3299),  # Enclosed ideograph emoji forms
    (0x1F300, 0x1F5FF),  # Misc symbols and pictographs
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F680, 0x1F6FF),  # Transport and map symbols
    (0x1F700, 0x1F77F),  # Alchemical symbols
    (0x1F780, 0x1F7FF),  # Geometric shapes extended
    (0x1F800, 0x1F8FF),  # Supplemental arrows
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    (0x1FA70, 0x1FAFF),  # Symbols and pictographs extended-A
]
EMOJI_PATTERN = re.compile(
    "[" + "".join(f"{chr(start)}-{chr(end)}" for start, end in EMOJI_RANGES) + "]"
)

EXTS = (".md", ".rst", ".txt")
SKIP_DIRS = {
    ".emoji_backups",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


def contains_emoji(s: str) -> bool:
    return EMOJI_PATTERN.search(s) is not None


def remove_emojis_from_text(s: str) -> str:
    return EMOJI_PATTERN.sub("", s)


def iter_text_files(root: Path):
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        current_path = Path(current_root)
        for filename in filenames:
            path = current_path / filename
            if not (filename.startswith("README") or path.suffix.lower() in EXTS):
                continue
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def backup_file(original: Path, backup_root: Path, root: Path):
    target = backup_root / original.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = target.with_name(f"{target.name}.{stamp}")
        if target.exists():
            target = target.with_name(f"{target.name}.{uuid.uuid4().hex}")
    shutil.copy2(original, target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Actually modify files")
    mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="List files containing emojis",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    os.chdir(root)
    if args.dry_run or not args.apply:
        found_count = 0
        print("Files containing emojis:")
        for p in iter_text_files(root):
            try:
                with p.open("r", encoding="utf-8") as handle:
                    while chunk := handle.read(65536):
                        if contains_emoji(chunk):
                            found_count += 1
                            print(" -", p)
                            break
            except (OSError, UnicodeDecodeError) as exc:
                print(f"Skipping unreadable text file {p}: {exc}", file=sys.stderr)
        if not found_count:
            print("No files with emojis found.")
            return 0
        print(f"\nFound {found_count} files containing emojis.")
        print("\nDry-run. No files were modified.")
        return 0

    backup_root = root / ".emoji_backups"
    print("\nApplying emoji removal and creating backups in .emoji_backups/")
    cleaned_count = 0
    for p in iter_text_files(root):
        changed = False
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=p.parent,
                prefix=f".{p.name}.",
                suffix=".emoji-tmp",
                delete=False,
            ) as target:
                temp_path = Path(target.name)
                with p.open("r", encoding="utf-8") as source:
                    for line in source:
                        cleaned, replacements = EMOJI_PATTERN.subn("", line)
                        changed = changed or replacements > 0
                        target.write(cleaned)
            if changed:
                backup_file(p, backup_root, root)
                temp_path.replace(p)
                cleaned_count += 1
                print("Cleaned:", p)
            else:
                temp_path.unlink(missing_ok=True)
        except (OSError, UnicodeDecodeError) as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            print("Failed to process", p, exc, file=sys.stderr)
    if not cleaned_count:
        print("No files with emojis found.")
        return 0
    print("\nDone. Review changes with git diff and commit if OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
