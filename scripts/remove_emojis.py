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
import shutil
from pathlib import Path

# Unicode ranges commonly used for emojis
EMOJI_RANGES = [
    (0x1F300, 0x1F5FF),  # Misc symbols and pictographs
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F680, 0x1F6FF),  # Transport and map symbols
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
]

EXTS = (".md", ".rst", ".txt")


def contains_emoji(s: str) -> bool:
    for ch in s:
        o = ord(ch)
        for a, b in EMOJI_RANGES:
            if a <= o <= b:
                return True
    return False


def remove_emojis_from_text(s: str) -> str:
    out_chars = []
    for ch in s:
        o = ord(ch)
        drop = False
        for a, b in EMOJI_RANGES:
            if a <= o <= b:
                drop = True
                break
        if not drop:
            out_chars.append(ch)
    return "".join(out_chars)


def scan_files(root: Path):
    files = []
    for path in root.rglob("*"):
        try:
            if not path.exists():
                continue
            if not path.is_file():
                continue
        except OSError:
            # Skip paths we can't stat (symlinks, special files)
            continue

        name = path.name
        if name.startswith("README") or path.suffix.lower() in EXTS:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if contains_emoji(text):
                files.append(path)
    return files


def backup_file(original: Path, backup_root: Path):
    target = backup_root / original.relative_to(Path.cwd())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--apply", action="store_true", help="Actually modify files")
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="List files only",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    os.chdir(root)
    files = scan_files(root)
    if not files:
        print("No files with emojis found.")
        return 0

    print(f"Found {len(files)} files containing emojis:")
    for p in files:
        print(" -", p)

    if args.dry_run and not args.apply:
        print("\nDry-run. No files were modified.")
        return 0

    backup_root = root / ".emoji_backups"
    if args.apply:
        print("\nApplying emoji removal and creating backups in .emoji_backups/")
        for p in files:
            try:
                backup_file(p, backup_root)
                text = p.read_text(encoding="utf-8")
                cleaned = remove_emojis_from_text(text)
                if cleaned != text:
                    p.write_text(cleaned, encoding="utf-8")
                    print("Cleaned:", p)
            except Exception as e:
                print("Failed to process", p, e)
        print("\nDone. Review changes with git diff and commit if OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
