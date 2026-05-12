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
    tokens = value.replace("-", " ").split()
    for token in tokens:
        cleaned = token.lstrip("vV")
        if cleaned and all(part.isdigit() for part in cleaned.split(".")):
            return cleaned
    return value


def _version_candidate(data: dict[str, object]) -> str:
    candidate = data.get("version_short") or data.get("version")
    if not candidate:
        version_long = data.get("version_long")
        if isinstance(version_long, str):
            candidate = _extract_version_from_long(version_long)
    return str(candidate or "").strip()


@lru_cache(maxsize=1)
def get_current_version(default: str | None = None) -> str:
    """Return the application version string from config/version.json or VERSION."""
    json_error: RuntimeError | None = None
    if _VERSION_JSON.exists():
        try:
            payload = json.loads(_VERSION_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            json_error = RuntimeError(
                f"Arquivo de versao invalido: {_VERSION_JSON}: {exc}"
            )
            payload = None
        except OSError as exc:
            raise RuntimeError(f"Falha ao ler arquivo de versao: {_VERSION_JSON}: {exc}") from exc
        if json_error is None:
            if not isinstance(payload, dict):
                json_error = RuntimeError(f"Arquivo de versao invalido: {_VERSION_JSON}")
            else:
                candidate = _version_candidate(payload)
                if candidate:
                    return candidate
                json_error = RuntimeError(
                    "Chave de versao ausente em "
                    f"{_VERSION_JSON}; esperado version_short, version ou version_long"
                )

    if _VERSION_FALLBACK.exists():
        try:
            value = _VERSION_FALLBACK.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Falha ao ler arquivo de versao: {_VERSION_FALLBACK}: {exc}") from exc
        if value:
            return value
        raise RuntimeError(f"Arquivo de versao vazio: {_VERSION_FALLBACK}")

    if default is not None:
        return default
    if json_error is not None:
        raise json_error
    raise RuntimeError(f"Arquivo de versao ausente: {_VERSION_JSON}")
