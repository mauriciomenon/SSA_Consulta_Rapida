from __future__ import annotations

import argparse
import functools
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

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
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SourceExposureError(
            f"falha ao listar fontes Python rastreados em {repo_root}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return {_normalize_entry(line) for line in result.stdout.splitlines() if line}


@functools.lru_cache(maxsize=8)
def _tracked_python_sources(repo_root_text: str) -> frozenset[str]:
    repo_root = Path(repo_root_text)
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


def _source_candidates(name: str) -> set[str]:
    normalized = _normalize_entry(name)
    path = Path(normalized)
    if path.suffix.lower() not in FORBIDDEN_SUFFIXES:
        return set()

    parts = tuple(part for part in normalized.split("/") if part)
    if not parts:
        return set()

    candidates = set()
    candidate_parts = parts
    if path.suffix.lower() in {".pyc", ".pyo"}:
        candidate_parts = tuple(part for part in _pyc_source_name(normalized).split("/") if part)
    for index in range(len(candidate_parts)):
        candidates.add("/".join(candidate_parts[index:]))
    return candidates


def _is_forbidden_source_entry(name: str, tracked_sources: frozenset[str]) -> bool:
    return bool(_source_candidates(name) & tracked_sources)


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
    tracked_sources = _tracked_python_sources(str(effective_repo_root))
    exposed = []
    for entry in _iter_artifact_entries(path):
        if _is_forbidden_source_entry(entry, tracked_sources):
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

    try:
        for artifact in args.artifacts:
            validate_source_protection(artifact, repo_root=args.repo_root)
    except (SourceExposureError, UnsupportedArtifactError) as exc:
        logger.error("Erro: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
