from __future__ import annotations

import argparse
import functools
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable, Mapping

from utils.robust_logging import get_robust_logger


class SourceExposureError(RuntimeError):
    pass


class UnsupportedArtifactError(RuntimeError):
    pass


logger = get_robust_logger().get_logger(__name__, "build")


FORBIDDEN_SUFFIXES = {".py", ".pyc", ".pyo"}
PYC_TAG_RE = re.compile(r"\.cpython-\d+[A-Za-z0-9_]*$")


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_entry(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _repo_python_files_from_git(repo_root: Path) -> set[str]:
    git_path = shutil.which("git")
    if git_path is None:
        raise SourceExposureError("git nao encontrado no PATH")
    try:
        result = subprocess.run(
            [git_path, "ls-files"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            encoding="utf-8",
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise SourceExposureError("git nao encontrado no PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceExposureError("git ls-files excedeu timeout de 120s") from exc
    if result.returncode != 0:
        raise SourceExposureError(
            f"falha ao listar fontes Python rastreados em {repo_root}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    sources = [
        normalized
        for line in result.stdout.splitlines()
        if (normalized := _normalize_entry(line)).lower().endswith(".py")
    ]
    case_map: dict[str, str] = {}
    collisions = []
    for source in sources:
        key = source.lower()
        previous = case_map.setdefault(key, source)
        if previous != source:
            collisions.append(f"{previous} / {source}")
    if collisions:
        sample = ", ".join(sorted(collisions)[:5])
        raise SourceExposureError(
            f"inventario Python tem caminhos ambiguos por caixa: {sample}"
        )
    return set(case_map)


@functools.lru_cache(maxsize=8)
def _tracked_python_sources(repo_root_text: str) -> frozenset[str]:
    repo_root = Path(repo_root_text).resolve()
    sources = _repo_python_files_from_git(repo_root)
    if not sources:
        raise SourceExposureError(f"nenhum arquivo Python rastreado em {repo_root}")
    return frozenset(sources)


def _pyc_source_name(name: str) -> str:
    path = Path(name)
    stem = PYC_TAG_RE.sub("", path.stem)
    source_name = f"{stem}.py"
    if path.parent.name == "__pycache__":
        return (path.parent.parent / source_name).as_posix()
    return path.with_name(source_name).as_posix()


def _artifact_source_name(name: str) -> str | None:
    normalized = _normalize_entry(name).lower()
    path = Path(normalized)
    if path.suffix.lower() not in FORBIDDEN_SUFFIXES:
        return None
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return _pyc_source_name(normalized).lower()
    return normalized


def _source_candidates_from_name(source_name: str) -> set[str]:
    parts = tuple(part for part in source_name.split("/") if part)
    if not parts:
        return set()

    candidates = set()
    for index in range(len(parts)):
        candidates.add("/".join(parts[index:]))
    return candidates


def _has_app_source_context(
    parts: tuple[str, ...],
    index: int,
) -> bool:
    if index == 0:
        return True
    prefix = parts[:index]
    if any(part.startswith("ssa_") for part in prefix):
        return True
    if "_internal" in prefix:
        return prefix.index("_internal") + 1 == index
    return "bundle" in prefix


def _is_forbidden_source_entry(
    name: str,
    tracked_source_parts: Mapping[str, tuple[str, ...]],
) -> bool:
    source_name = _artifact_source_name(name)
    if source_name is None:
        return False
    entry_parts = tuple(part for part in source_name.split("/") if part)
    for candidate in _source_candidates_from_name(source_name):
        candidate_parts = tracked_source_parts.get(candidate)
        if not candidate_parts:
            continue
        for index in range(len(entry_parts) - len(candidate_parts) + 1):
            if entry_parts[index:] == candidate_parts and _has_app_source_context(
                entry_parts,
                index,
            ):
                return True
    return False


def _iter_directory_entries(path: Path) -> Iterable[str]:
    for item in path.rglob("*"):
        if item.is_file():
            yield item.relative_to(path).as_posix()


def _iter_zip_entries(path: Path) -> Iterable[str]:
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if not entry.is_dir():
                yield entry.filename


def _iter_tar_entries(path: Path) -> Iterable[str]:
    with tarfile.open(path) as archive:
        for entry in archive:
            if entry.isfile():
                yield entry.name


def _iter_artifact_entries(path: Path) -> Iterable[str]:
    if path.is_dir():
        yield from _iter_directory_entries(path)
        return
    if path.suffix.lower() == ".zip":
        yield from _iter_zip_entries(path)
        return
    if path.name.endswith((".tar.gz", ".tgz")):
        yield from _iter_tar_entries(path)
        return
    raise UnsupportedArtifactError(f"tipo de artefato sem suporte: {path}")


def validate_source_protection(path: Path, repo_root: Path | None = None) -> None:
    effective_repo_root = (repo_root or _default_repo_root()).resolve()
    tracked_sources = _tracked_python_sources(effective_repo_root.as_posix())
    tracked_source_parts = {
        source: tuple(part for part in source.split("/") if part)
        for source in tracked_sources
    }
    exposed = []
    for entry in _iter_artifact_entries(path):
        if _is_forbidden_source_entry(entry, tracked_source_parts):
            exposed.append(entry)
            if len(exposed) >= 10:
                break
    if exposed:
        sample = ", ".join(sorted(exposed))
        raise SourceExposureError(
            f"artefato expoe fonte/bytecode Python do app: {path}: {sample}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)

    failed = False
    for artifact in args.artifacts:
        try:
            validate_source_protection(artifact, repo_root=args.repo_root)
        except (SourceExposureError, UnsupportedArtifactError) as exc:
            logger.error("Erro: %s", exc)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
