import os
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Target directories and file extensions considered safe to normalize.
TARGET_DIRS = {
    "docs",
    "launchers",
    "LocalTemp",
    "resources",
    "reports",
    "scripts",
    "scripts_manutencao",
    "dev_env",
    "interface",
}

TARGET_EXTS = {
    ".md",
    ".txt",
    ".json",
    ".ini",
    ".toml",
    ".yml",
    ".yaml",
    ".sql",
}

# Exclusions to avoid breaking runtime code or data unintentionally.
EXCLUDE_DIRS = {".git", "__pycache__", "data", ".venv", "venv", ".idea", ".vscode"}


def strip_diacritics(text: str) -> str:
    """Remove diacritics (accents, cedillas) but keep base characters and other symbols."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def should_process(path: Path) -> bool:
    if path.suffix.lower() in TARGET_EXTS:
        # Only process files under selected directories or at repo root
        try:
            rel = path.relative_to(ROOT)
        except Exception:
            return False
        parts = rel.parts
        if len(parts) == 1:
            return True  # root files like README.md
        if parts[0] in TARGET_DIRS and parts[0] not in EXCLUDE_DIRS:
            return True
    return False


def iter_candidate_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            path = Path(dirpath) / fname
            if should_process(path):
                yield path


def main() -> int:
    changed = 0
    scanned = 0
    for path in iter_candidate_files(ROOT):
        scanned += 1
        try:
            original = path.read_text(encoding="utf-8")
        except Exception:
            continue  # skip binary or unreadable
        transformed = strip_diacritics(original)
        if transformed != original:
            path.write_text(transformed, encoding="utf-8", newline="\n")
            changed += 1
            print(f"normalized: {path.relative_to(ROOT)}")
    print(f"Done. Scanned={scanned} changed={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
