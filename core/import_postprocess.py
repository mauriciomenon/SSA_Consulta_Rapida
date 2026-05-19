"""Post-import file movement helpers."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
DESTINATION_SUFFIX_LIMIT = 10000


def build_nonconflicting_destination(
    path: Path,
    *,
    existing_names: Optional[set[str]] = None,
    suffix_index_cache: Optional[dict[tuple[str, str], int]] = None,
) -> Path:
    """Return a non-conflicting destination path by suffixing __N when needed."""
    names = existing_names
    if names is None:
        names = _directory_names(path.parent)
    if path.name not in names:
        return path
    stem, suffix = _split_filename_preserving_suffixes(path)
    cache_key = (stem, suffix)
    if suffix_index_cache is None:
        suffix_index_cache = _build_suffix_index_cache(names)
    start_index = suffix_index_cache.setdefault(cache_key, 1)
    for idx in range(start_index, DESTINATION_SUFFIX_LIMIT):
        candidate = path.with_name(f"{stem}__{idx}{suffix}")
        if candidate.name not in names:
            if suffix_index_cache is not None:
                suffix_index_cache[cache_key] = idx + 1
            return candidate
    raise OSError(f"Nao foi possivel resolver destino unico para '{path}'")


def _build_suffix_index_cache(names: set[str]) -> dict[tuple[str, str], int]:
    cache: dict[tuple[str, str], int] = {}
    for name in names:
        stem, suffix = _split_filename_preserving_suffixes(Path(name))
        base_stem, separator, number_part = stem.rpartition("__")
        if not separator or not number_part.isdigit():
            continue
        cache_key = (base_stem, suffix)
        cache[cache_key] = max(cache.get(cache_key, 1), int(number_part) + 1)
    return cache


def _directory_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {entry.name for entry in os.scandir(path)}


def _split_filename_preserving_suffixes(path: Path) -> tuple[str, str]:
    suffix = "".join(path.suffixes)
    if not suffix:
        return path.name, ""
    stem = path.name[: -len(suffix)]
    if not stem:
        return path.name, ""
    return stem, suffix


def _destination_root(
    docs_root: Path,
    processadas_subdir: str,
    nosurvivor_subdir: str,
    *,
    route_to_nosurvivor: bool,
) -> Path:
    destination_root = (docs_root / processadas_subdir).resolve()
    if route_to_nosurvivor:
        destination_root = (destination_root / nosurvivor_subdir).resolve()
    return destination_root


def move_file_after_import(
    *,
    file_path: str,
    docs_dir: str,
    destination_root: Path,
    existing_destination_names: Optional[set[str]] = None,
    suffix_index_cache: Optional[dict[tuple[str, str], int]] = None,
) -> str:
    """Move processed file to processadas or nosurvivor and return final path."""
    source = Path(file_path).resolve()
    docs_root = Path(docs_dir).resolve()
    if not source.exists():
        logger.warning("Arquivo para pos-processamento nao encontrado: %s", file_path)
        return file_path
    try:
        source.relative_to(docs_root)
    except ValueError:
        logger.warning(
            "Arquivo fora de docs_dir nao sera movido no pos-processamento: %s",
            file_path,
        )
        return file_path

    destination_root = destination_root.resolve()
    if source.is_relative_to(destination_root):
        return str(source)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = build_nonconflicting_destination(
        destination_root / source.name,
        existing_names=existing_destination_names,
        suffix_index_cache=suffix_index_cache,
    )
    if destination == source:
        return str(source)
    try:
        shutil.move(str(source), str(destination))
    except (OSError, RuntimeError, shutil.Error, ValueError) as exc:
        logger.warning(
            "Falha ao mover arquivo pos-importacao '%s' para '%s': %s",
            file_path,
            destination,
            exc,
        )
        return file_path
    try:
        src_rel = source.relative_to(docs_root).as_posix()
    except ValueError:
        src_rel = str(source)
    try:
        dst_rel = destination.relative_to(docs_root).as_posix()
    except ValueError:
        dst_rel = str(destination)
    logger.info(
        "Arquivo pos-importacao movido: %s -> %s",
        src_rel,
        dst_rel,
    )
    if existing_destination_names is not None:
        existing_destination_names.add(destination.name)
    return str(destination.resolve())


def route_and_move_processed_files(
    *,
    successful_files_with_records: List[tuple[str, int]],
    docs_dir: str,
    processadas_subdir: str,
    nosurvivor_subdir: str,
    route_zero_survivor_to_nosurvivor: bool,
) -> Dict[str, str]:
    """Apply post-import moves and return old_path -> final_path mapping."""
    moved_paths: Dict[str, str] = {}
    destination_name_cache: dict[Path, set[str]] = {}
    suffix_index_cache_by_root: dict[Path, dict[tuple[str, str], int]] = {}
    docs_root = Path(docs_dir).resolve()
    for file_path, record_count in successful_files_with_records:
        try:
            normalized_record_count = int(record_count)
        except (TypeError, ValueError):
            logger.warning(
                "Contagem invalida para movimentacao pos-importacao de '%s': %r",
                os.path.basename(file_path),
                record_count,
            )
            normalized_record_count = 0
        route_to_nosurvivor = bool(
            route_zero_survivor_to_nosurvivor
            and normalized_record_count <= 0
        )
        destination_root = _destination_root(
            docs_root,
            processadas_subdir,
            nosurvivor_subdir,
            route_to_nosurvivor=route_to_nosurvivor,
        )
        existing_names = destination_name_cache.get(destination_root)
        if existing_names is None:
            existing_names = _directory_names(destination_root)
            destination_name_cache[destination_root] = existing_names
            suffix_index_cache_by_root[destination_root] = _build_suffix_index_cache(
                existing_names
            )
        suffix_index_cache = suffix_index_cache_by_root[destination_root]
        final_path = move_file_after_import(
            file_path=file_path,
            docs_dir=docs_dir,
            existing_destination_names=existing_names,
            destination_root=destination_root,
            suffix_index_cache=suffix_index_cache,
        )
        moved_paths[file_path] = final_path
        moved_paths[str(Path(file_path).resolve())] = final_path
    return moved_paths
