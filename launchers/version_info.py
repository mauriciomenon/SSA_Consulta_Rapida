"""Shared helpers to resolve repository version info for launcher scripts."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_VERSION_JSON = REPO_ROOT / "config" / "version.json"
_VERSION_FALLBACK = REPO_ROOT / "VERSION"


def _extract_version_from_long(value: str) -> str:
    """Attempt to extract a semantic version from a descriptive string."""
    tokens = value.replace('-', ' ').split()
    for token in tokens:
        cleaned = token.lstrip('vV')
        if cleaned and all(part.isdigit() for part in cleaned.split('.')):
            return cleaned
    return value


@lru_cache(maxsize=1)
def get_current_version(default: str = "0.0.0") -> str:
    """Return the application version string from config/version.json or VERSION."""
    try:
        if _VERSION_JSON.exists():
            data = json.loads(_VERSION_JSON.read_text(encoding="utf-8"))
            candidate = data.get("version_short") or data.get("version")
            if not candidate:
                version_long = data.get("version_long")
                if isinstance(version_long, str):
                    candidate = _extract_version_from_long(version_long)
            if candidate:
                return str(candidate)
    except Exception:
        pass

    try:
        if _VERSION_FALLBACK.exists():
            value = _VERSION_FALLBACK.read_text(encoding="utf-8").strip()
            if value:
                return value
    except Exception:
        pass

    return default
