"""
Helpers to keep user-provided paths inside an allowlist.

The goal is to stop Streamlit/CLI inputs from reaching arbitrary locations
outside the project or temp roots. Extra bases can be added via the
SSA_EXTRA_ALLOWED_PATHS env var (os.pathsep-separated).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable, List

# Base directory for relative paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PathSafetyError(ValueError):
    """Raised when a path is not allowed for security reasons."""


def _unique(paths: Iterable[Path]) -> List[Path]:
    seen: list[Path] = []
    for p in paths:
        try:
            resolved = p.resolve()
        except Exception:
            resolved = p
        if resolved not in seen:
            seen.append(resolved)
    return seen


def _load_allowed_roots() -> List[Path]:
    roots = [
        PROJECT_ROOT,
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "docs_entrada",
        Path(tempfile.gettempdir()),
    ]
    extra_env = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    for raw in extra_env.split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw).expanduser())
    return _unique(roots)


ALLOWED_ROOTS: List[Path] = _load_allowed_roots()


def _is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def ensure_path_is_allowed(
    raw_path: str | os.PathLike,
    *,
    purpose: str = "path",
    base: Path | None = None,
    must_exist: bool = False,
    expect_directory: bool | None = None,
) -> Path:
    """
    Normalize a user-provided path and ensure it stays inside allowed roots.

    Args:
        raw_path: The input path (string or Path-like).
        purpose: Short label for error messages.
        base: Optional base for resolving relative paths (defaults to CWD).
        must_exist: If True, raises when the path is missing.
        expect_directory: When True, rejects files; when False, rejects dirs.
    """
    if raw_path is None:
        raise PathSafetyError(f"{purpose}: caminho vazio nao permitido")

    candidate = Path(raw_path).expanduser()
    if base and not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed = ALLOWED_ROOTS
    if not any(_is_within(candidate, root) for root in allowed):
        allowed_list = ", ".join(str(r) for r in allowed)
        raise PathSafetyError(
            f"{purpose}: '{candidate}' fora das bases permitidas ({allowed_list}). "
            "Use SSA_EXTRA_ALLOWED_PATHS para liberar diretorios adicionais."
        )

    if must_exist and not candidate.exists():
        raise PathSafetyError(f"{purpose}: '{candidate}' nao existe.")

    if expect_directory is True and candidate.exists() and not candidate.is_dir():
        raise PathSafetyError(f"{purpose}: '{candidate}' precisa ser um diretorio.")
    if expect_directory is False and candidate.exists() and candidate.is_dir():
        raise PathSafetyError(f"{purpose}: '{candidate}' deve ser um arquivo, nao um diretorio.")

    return candidate
