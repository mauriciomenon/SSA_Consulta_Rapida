"""Post-import file movement helpers."""

from __future__ import annotations

import errno
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
    existing_names: set[str],
    suffix_index_cache: dict[tuple[str, str], int],
) -> Path:
    """Return a non-conflicting destination path by suffixing __N when needed."""
    if path.name not in existing_names:
        return path
    stem, suffix = _split_filename_preserving_suffixes(path)
    cache_key = (stem, suffix)
    start_index = suffix_index_cache.setdefault(cache_key, 1)
    for idx in range(start_index, DESTINATION_SUFFIX_LIMIT):
        candidate = path.with_name(f"{stem}__{idx}{suffix}")
        if candidate.name not in existing_names:
            suffix_index_cache[cache_key] = idx + 1
            return candidate
    raise OSError(f"Nao foi possivel resolver destino unico para '{path}'")


def _build_suffix_index_cache(names: set[str]) -> dict[tuple[str, str], int]:
    used_indexes: dict[tuple[str, str], set[int]] = {}
    for name in names:
        stem, suffix = _split_filename_preserving_suffixes(Path(name))
        base_stem, separator, number_part = stem.rpartition("__")
        if not separator or not number_part.isdigit():
            continue
        cache_key = (base_stem, suffix)
        used_indexes.setdefault(cache_key, set()).add(int(number_part))
    return {
        cache_key: _first_available_suffix_index(indexes)
        for cache_key, indexes in used_indexes.items()
    }


def _first_available_suffix_index(indexes: set[int]) -> int:
    for idx in range(1, DESTINATION_SUFFIX_LIMIT):
        if idx not in indexes:
            return idx
    raise OSError("Limite de sufixos de destino esgotado")


def _directory_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {entry.name for entry in os.scandir(path)}


def _split_filename_preserving_suffixes(path: Path) -> tuple[str, str]:
    if path.name.startswith(".") and path.name.count(".") == 1:
        return path.name, ""
    suffix = "".join(path.suffixes)
    if not suffix:
        return path.name, ""
    stem = path.name[: -len(suffix)]
    if not stem:
        single_suffix = path.suffix
        if single_suffix and path.name != single_suffix:
            return path.name[: -len(single_suffix)], single_suffix
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
    destination_root.relative_to(docs_root)
    return destination_root


def move_file_after_import(
    *,
    file_path: str,
    docs_dir: str,
    destination_root: Path,
    existing_destination_names: Optional[set[str]] = None,
    suffix_index_cache: Optional[dict[tuple[str, str], int]] = None,
) -> str | None:
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
    try:
        destination_root.relative_to(docs_root)
    except ValueError:
        logger.warning(
            "Destino de pos-processamento fora de docs_dir sera ignorado: %s",
            destination_root,
        )
        return file_path
    if source.is_relative_to(destination_root):
        return file_path
    destination_root.mkdir(parents=True, exist_ok=True)
    if existing_destination_names is None:
        existing_destination_names = _directory_names(destination_root)
    if suffix_index_cache is None:
        suffix_index_cache = _build_suffix_index_cache(existing_destination_names)
    try:
        destination = _move_to_available_destination(
            source,
            destination_root,
            existing_destination_names,
            suffix_index_cache,
        )
    except (OSError, RuntimeError, shutil.Error, ValueError) as exc:
        logger.warning(
            "Falha ao mover arquivo pos-importacao '%s' para '%s': %s",
            file_path,
            destination_root,
            exc,
        )
        return None
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


def _move_to_available_destination(
    source: Path,
    destination_root: Path,
    existing_names: set[str],
    suffix_index_cache: dict[tuple[str, str], int],
) -> Path:
    attempted_names: set[str] = set()
    for _attempt in range(DESTINATION_SUFFIX_LIMIT):
        destination = build_nonconflicting_destination(
            destination_root / source.name,
            existing_names=existing_names,
            suffix_index_cache=suffix_index_cache,
        )
        if destination == source:
            return source
        if destination.name in attempted_names:
            raise OSError(f"Destino repetido durante retry: {destination}")
        attempted_names.add(destination.name)
        try:
            _move_without_overwrite(source, destination)
            return destination
        except FileExistsError:
            existing_names.add(destination.name)
            _advance_suffix_cache_after_conflict(
                source.name,
                destination.name,
                suffix_index_cache,
            )
    raise OSError(f"Nao foi possivel reservar destino unico para '{source}'")


def _advance_suffix_cache_after_conflict(
    source_name: str,
    failed_name: str,
    suffix_index_cache: dict[tuple[str, str], int],
) -> None:
    stem, suffix = _split_filename_preserving_suffixes(Path(source_name))
    cache_key = (stem, suffix)
    failed_stem, failed_suffix = _split_filename_preserving_suffixes(Path(failed_name))
    failed_base, separator, number_part = failed_stem.rpartition("__")
    next_index = 1
    if (
        separator
        and failed_base == stem
        and failed_suffix == suffix
        and number_part.isdigit()
    ):
        next_index = int(number_part) + 1
    suffix_index_cache[cache_key] = max(
        suffix_index_cache.get(cache_key, 1),
        next_index,
    )


def _move_without_overwrite(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
        source.unlink()
        return
    except FileExistsError:
        raise
    except OSError as exc:
        if exc.errno not in {
            errno.EXDEV,
            errno.EPERM,
            errno.EACCES,
            errno.ENOTSUP,
            getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        }:
            raise
        destination_fd = None
        destination_created = False
        try:
            source_mode = source.stat().st_mode & 0o777
            destination_fd = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                source_mode,
            )
            destination_created = True
            try:
                destination_stream = os.fdopen(destination_fd, "wb")
            except Exception:
                os.close(destination_fd)
                destination_fd = None
                raise
            with destination_stream as reserved:
                destination_fd = None
                with source.open("rb") as src:
                    shutil.copyfileobj(src, reserved)
                reserved.flush()
                try:
                    os.fsync(reserved.fileno())
                except OSError as fsync_exc:
                    logger.debug(
                        "fsync failed for postprocess destination '%s': %s",
                        destination,
                        fsync_exc,
                    )
            shutil.copystat(source, destination, follow_symlinks=True)
            source.unlink()
            return
        except Exception:
            if destination_fd is not None:
                os.close(destination_fd)
            if destination_created:
                destination.unlink(missing_ok=True)
            raise


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
        try:
            destination_root = _destination_root(
                docs_root,
                processadas_subdir,
                nosurvivor_subdir,
                route_to_nosurvivor=route_to_nosurvivor,
            )
        except ValueError:
            logger.warning(
                "Destino de pos-processamento fora de docs_dir sera ignorado: %s",
                processadas_subdir,
            )
            moved_paths[file_path] = file_path
            moved_paths[str(Path(file_path).resolve())] = file_path
            continue
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
        if final_path is None:
            continue
        moved_paths[file_path] = final_path
        moved_paths[str(Path(file_path).resolve())] = final_path
    return moved_paths
