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
    seen_keys: set[Path] = set()
    for p in paths:
        try:
            resolved = p.resolve()
        except Exception:
            resolved = p
        if resolved not in seen_keys:
            seen.append(resolved)
            seen_keys.add(resolved)
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
_ALLOWED_ROOTS_ENV_VALUE = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")


def refresh_allowed_roots() -> List[Path]:
    global ALLOWED_ROOTS, _ALLOWED_ROOTS_ENV_VALUE
    ALLOWED_ROOTS = _load_allowed_roots()
    _ALLOWED_ROOTS_ENV_VALUE = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    return list(ALLOWED_ROOTS)


def get_allowed_roots() -> List[Path]:
    current_env_value = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    if current_env_value != _ALLOWED_ROOTS_ENV_VALUE:
        return refresh_allowed_roots()
    return list(ALLOWED_ROOTS)


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
    extra_allowed_roots: Iterable[str | os.PathLike] | None = None,
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

    raw_path_value = os.fspath(raw_path)
    if isinstance(raw_path_value, bytes):
        try:
            raw_path_value = os.fsdecode(raw_path_value)
        except Exception as exc:
            raise PathSafetyError(f"{purpose}: caminho com encoding invalido") from exc

    if isinstance(raw_path_value, str) and not raw_path_value.strip():
        raise PathSafetyError(f"{purpose}: caminho vazio nao permitido")

    candidate = Path(raw_path_value).expanduser()
    if base and not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed = get_allowed_roots()
    if extra_allowed_roots:
        allowed = _unique(
            [
                *allowed,
                *[Path(os.fspath(path)).expanduser() for path in extra_allowed_roots],
            ]
        )
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
        raise PathSafetyError(
            f"{purpose}: '{candidate}' deve ser um arquivo, nao um diretorio."
        )

    return candidate


def reserve_unique_path(
    destination_path: str | os.PathLike[str],
    *,
    reserved_paths: set[str] | None = None,
    touch: bool = False,
    starting_index: int = 1,
    max_attempts: int = 10000,
) -> str:
    if reserved_paths is None and not touch:
        raise ValueError("reserve_unique_path requires reserved_paths or touch=True")

    destination = str(destination_path)
    base, ext = os.path.splitext(destination)
    attempt_limit = max(int(max_attempts), 1)

    normalized_destination = os.path.abspath(destination)
    if reserved_paths is not None:
        if normalized_destination not in reserved_paths and not os.path.exists(
            destination
        ):
            reserved_paths.add(normalized_destination)
            return destination
    elif touch:
        try:
            Path(destination).touch(exist_ok=False)
        except FileExistsError:
            pass
        else:
            return destination

    idx = max(int(starting_index), 1)
    attempts = 0
    while attempts < attempt_limit:
        candidate = f"{base}__{idx}{ext}"
        normalized_candidate = os.path.abspath(candidate)
        if reserved_paths is not None:
            if normalized_candidate not in reserved_paths and not os.path.exists(
                candidate
            ):
                reserved_paths.add(normalized_candidate)
                return candidate
        elif touch:
            try:
                Path(candidate).touch(exist_ok=False)
            except FileExistsError:
                idx += 1
                attempts += 1
                continue
            return candidate
        idx += 1
        attempts += 1

    raise RuntimeError(
        "Nao foi possivel gerar nome unico apos "
        f"{attempt_limit} tentativas: {destination}. "
        "Limpe duplicatas no destino ou escolha outro nome."
    )
