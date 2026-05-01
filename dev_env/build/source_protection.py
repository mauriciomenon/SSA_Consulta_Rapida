from __future__ import annotations

import argparse
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


APP_CODE_DIRS = {
    "armazenamento",
    "config",
    "core",
    "exportacao",
    "extracao",
    "gui",
    "interface",
    "launchers",
    "shared",
    "utils",
}
APP_CODE_FILES = {"main.py"}
FORBIDDEN_SUFFIXES = {".py", ".pyc", ".pyo"}
APP_ROOT_MARKERS = {"_internal", "bundle", "runtime", "cli", "gui"}
THIRD_PARTY_MARKERS = {
    "PyQt6",
    "_distutils_hack",
    "dateutil",
    "et_xmlfile",
    "numpy",
    "openpyxl",
    "packaging",
    "pandas",
    "pip",
    "pkg_resources",
    "pytz",
    "setuptools",
    "site-packages",
    "six.py",
    "tabulate",
    "tzdata",
    "wheel",
}


def _normalize_entry(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_forbidden_source_entry(name: str) -> bool:
    normalized = _normalize_entry(name)
    path = Path(normalized)
    if path.suffix.lower() not in FORBIDDEN_SUFFIXES:
        return False

    parts = tuple(part for part in normalized.split("/") if part)
    if not parts:
        return False
    if any(part in THIRD_PARTY_MARKERS for part in parts[:-1]) or parts[-1] in THIRD_PARTY_MARKERS:
        return False
    if "_internal" in parts:
        internal_index = parts.index("_internal")
        if internal_index + 1 < len(parts) and parts[internal_index + 1] in APP_CODE_DIRS:
            return True
        return False
    if parts[-1] in APP_CODE_FILES:
        return True
    for index, part in enumerate(parts[:-1]):
        if part not in APP_CODE_DIRS:
            continue
        if index == 0:
            return True
        parent = parts[index - 1]
        if parent in APP_ROOT_MARKERS or parent.startswith("SSA_"):
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


def validate_source_protection(path: Path) -> None:
    exposed = []
    for entry in _iter_artifact_entries(path):
        if _is_forbidden_source_entry(entry):
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
    args = parser.parse_args(argv)

    try:
        for artifact in args.artifacts:
            validate_source_protection(artifact)
    except (SourceExposureError, UnsupportedArtifactError) as exc:
        logger.error("Erro: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
