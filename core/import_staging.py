from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Iterable, Sequence

from core.import_formats import SUPPORTED_IMPORT_SUFFIXES
from core.import_formats import supported_import_suffixes_text
from utils.file_copy import copy_source_without_execute_bit
from utils.path_safety import ensure_path_is_allowed, reserve_unique_path

CancelCallback = Callable[[], bool]
LineCallback = Callable[[str], None]
EXTERNAL_STAGING_SUMMARY_KEYS = (
    "copied",
    "skipped",
    "failed",
    "unsupported",
    "staged",
    "already_staged",
)


def empty_external_staging_summary() -> dict[str, int]:
    return dict.fromkeys(EXTERNAL_STAGING_SUMMARY_KEYS, 0)


def _normalize_explicit_allowed_files(
    extra_allowed_files: Iterable[str | os.PathLike[str]] | None,
) -> set[Path]:
    if not extra_allowed_files:
        return set()
    allowed_files: set[Path] = set()
    for raw in extra_allowed_files:
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        resolved = candidate.resolve(strict=False)
        allowed_files.add(resolved)
    return allowed_files


def validate_external_source_path(
    raw_source: str | os.PathLike[str],
    *,
    extra_allowed_files: Iterable[str | os.PathLike[str]] | None = None,
    normalized_allowed_files: set[Path] | None = None,
) -> str:
    source = str(raw_source or "").strip()
    if not source:
        raise ValueError("Caminho vazio para staging externo.")
    if any(ch in source for ch in ("\x00", "\n", "\r")):
        raise ValueError("Caminho externo contem caracteres invalidos.")
    normalized = os.path.abspath(os.path.normpath(source))
    if os.path.basename(normalized).startswith("-"):
        raise ValueError("Caminho externo inicia com '-' e nao e permitido.")
    source_path = Path(normalized)
    try:
        safe_source_path = ensure_path_is_allowed(
            source_path,
            purpose="external_import_file",
            must_exist=True,
            expect_directory=False,
        )
    except ValueError as exc:
        if not source_path.exists():
            raise FileNotFoundError(f"Arquivo inexistente: {normalized}") from exc
        if not source_path.is_file():
            raise
        explicit_allowed_files = (
            normalized_allowed_files
            if normalized_allowed_files is not None
            else _normalize_explicit_allowed_files(extra_allowed_files)
        )
        resolved_source = source_path.resolve(strict=False)
        if resolved_source not in explicit_allowed_files:
            raise
        safe_source_path = resolved_source
    source_path = safe_source_path
    if source_path.suffix.casefold() not in SUPPORTED_IMPORT_SUFFIXES:
        raise ValueError(
            "Arquivo nao suportado para staging "
            f"({supported_import_suffixes_text()}): {source_path.name}"
        )
    return str(source_path)


def stage_external_import_files(
    *,
    project_root: str | os.PathLike[str],
    source_files: Sequence[str | os.PathLike[str]],
    should_cancel: CancelCallback | None = None,
    output_callback: LineCallback | None = None,
    error_callback: LineCallback | None = None,
) -> tuple[list[str], dict[str, int]]:
    project_root_path = Path(project_root).resolve()
    docs_path = ensure_path_is_allowed(
        project_root_path / "docs_entrada",
        purpose="explicit_import_docs_dir",
        base=project_root_path,
        must_exist=False,
        expect_directory=True,
    )
    docs_path.mkdir(parents=True, exist_ok=True)

    reserved_paths = {
        os.path.abspath(str(path)) for path in docs_path.iterdir() if path.is_file()
    }
    next_suffix_by_base: dict[str, int] = {}
    summary = empty_external_staging_summary()
    staged_files: list[str] = []
    total_sources = len(source_files)
    explicit_allowed_files = _normalize_explicit_allowed_files(source_files)

    for index, raw_source in enumerate(tuple(source_files), start=1):
        if callable(should_cancel) and should_cancel():
            break
        source = str(raw_source or "").strip()
        if not source:
            summary["skipped"] += 1
            continue
        _emit_stage_prepare(output_callback, source=source, index=index, total=total_sources)
        try:
            validated_source = validate_external_source_path(
                source,
                normalized_allowed_files=explicit_allowed_files,
            )
        except FileNotFoundError:
            summary["failed"] += 1
            _emit_stage_error(error_callback, f"Arquivo inexistente: {source}")
            continue
        except ValueError as exc:
            summary["unsupported"] += 1
            _emit_stage_ignored(output_callback, str(exc))
            continue
        except (OSError, shutil.Error) as exc:
            summary["failed"] += 1
            _emit_stage_error(
                error_callback,
                f"Falha ao validar arquivo externo '{source}': {exc}",
            )
            continue

        try:
            staged_file, was_copied, cancelled = _stage_validated_external_source(
                validated_source=validated_source,
                docs_path=docs_path,
                reserved_paths=reserved_paths,
                next_suffix_by_base=next_suffix_by_base,
                should_cancel=should_cancel,
                error_callback=error_callback,
            )
            if cancelled:
                break
            if staged_file:
                staged_files.append(staged_file)
                if was_copied:
                    summary["copied"] += 1
                else:
                    summary["already_staged"] += 1
        except (OSError, shutil.Error) as exc:
            summary["failed"] += 1
            _emit_stage_error(
                error_callback,
                f"Falha ao copiar arquivo externo '{validated_source}': {exc}",
            )

    summary["staged"] = len(staged_files)
    _emit_stage_summary(output_callback, summary)
    return staged_files, summary


def _stage_validated_external_source(
    *,
    validated_source: str,
    docs_path: Path,
    reserved_paths: set[str],
    next_suffix_by_base: dict[str, int],
    should_cancel: CancelCallback | None,
    error_callback: LineCallback | None,
) -> tuple[str | None, bool, bool]:
    base_destination = docs_path / os.path.basename(validated_source)
    base_destination_abs = os.path.abspath(str(base_destination))
    source_abs = os.path.abspath(validated_source)
    if source_abs == base_destination_abs:
        reserved_paths.add(base_destination_abs)
        return base_destination_abs, False, False

    for _attempt in range(3):
        destination = _reserve_staging_destination(
            base_destination=base_destination,
            base_destination_abs=base_destination_abs,
            reserved_paths=reserved_paths,
            next_suffix_by_base=next_suffix_by_base,
        )
        destination_abs = os.path.abspath(destination)
        if callable(should_cancel) and should_cancel():
            reserved_paths.discard(destination_abs)
            return None, False, True

        destination_created = False
        try:
            copy_source_without_execute_bit(validated_source, destination)
            destination_created = True
            if callable(should_cancel) and should_cancel():
                _remove_destination(
                    destination,
                    error_callback=error_callback,
                    context="apos cancelamento",
                    ignore_missing=False,
                )
                reserved_paths.discard(destination_abs)
                return None, False, True
            return str(destination), True, False
        except FileExistsError:
            reserved_paths.discard(destination_abs)
            continue
        except (OSError, shutil.Error):
            if destination_created:
                _remove_destination(
                    destination,
                    error_callback=error_callback,
                    context="parcial",
                    ignore_missing=True,
                )
            reserved_paths.discard(destination_abs)
            raise
    raise FileExistsError(f"Destino de staging ocupado repetidamente: {base_destination}")


def _reserve_staging_destination(
    *,
    base_destination: Path,
    base_destination_abs: str,
    reserved_paths: set[str],
    next_suffix_by_base: dict[str, int],
) -> Path:
    destination = reserve_unique_path(
        base_destination,
        reserved_paths=reserved_paths,
        starting_index=next_suffix_by_base.get(base_destination_abs, 1),
    )
    destination_name = Path(destination).stem
    prefix = f"{base_destination.stem}__"
    if destination_name.startswith(prefix):
        raw_index = destination_name[len(prefix) :]
        if raw_index.isdigit():
            next_suffix_by_base[base_destination_abs] = max(
                next_suffix_by_base.get(base_destination_abs, 1),
                int(raw_index) + 1,
            )
    return Path(destination)


def _remove_destination(
    destination: Path,
    *,
    error_callback: LineCallback | None,
    context: str,
    ignore_missing: bool,
) -> None:
    try:
        os.remove(destination)
    except FileNotFoundError:
        if ignore_missing:
            return
        raise
    except OSError as exc:
        _emit_stage_error(
            error_callback,
            f"Falha ao remover arquivo staged {context} '{destination}': {exc}",
        )


def _emit_stage_prepare(
    output_callback: LineCallback | None,
    *,
    source: str,
    index: int,
    total: int,
) -> None:
    if callable(output_callback):
        output_callback(
            f"[STAGE {index}/{total}] Preparando: {os.path.basename(source) or source}"
        )


def _emit_stage_ignored(
    output_callback: LineCallback | None,
    message: str,
) -> None:
    if callable(output_callback):
        output_callback(f"[IGNORADO] {message}")


def _emit_stage_error(
    error_callback: LineCallback | None,
    message: str,
) -> None:
    if callable(error_callback):
        error_callback(f"[ERRO] {message}")


def _emit_stage_summary(
    output_callback: LineCallback | None,
    summary: dict[str, int],
) -> None:
    if callable(output_callback):
        output_callback(
            "Staging concluido: "
            f"copiados={summary['copied']}, skipped={summary['skipped']}, "
            f"nao_suportados={summary['unsupported']}, "
            f"falhas={summary['failed']}, staged={summary['staged']}"
        )
