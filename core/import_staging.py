from __future__ import annotations

import os
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
MAX_STAGING_RESERVATION_ATTEMPTS = 20


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
    docs_dir: str | os.PathLike[str] | None = None,
    source_files: Sequence[str | os.PathLike[str]],
    progress_offset: int = 0,
    progress_total: int | None = None,
    should_cancel: CancelCallback | None = None,
    output_callback: LineCallback | None = None,
    error_callback: LineCallback | None = None,
) -> tuple[list[str], dict[str, int]]:
    project_root_path = Path(project_root).resolve()
    docs_candidate = Path(docs_dir).expanduser() if docs_dir else project_root_path / "docs_entrada"
    docs_path = ensure_path_is_allowed(
        docs_candidate,
        purpose="explicit_import_docs_dir",
        base=project_root_path if docs_dir is None else None,
        must_exist=False,
        expect_directory=True,
    )
    docs_path.mkdir(parents=True, exist_ok=True)

    from extracao.extractor import ExtractionError, validate_excel_import_limits

    try:
        validate_excel_import_limits(
            source_files,
            inspect_archives=False,
            ignore_unavailable=True,
        )
    except ExtractionError as exc:
        raise ValueError(str(exc)) from exc

    reserved_paths = {
        os.path.abspath(str(path)) for path in docs_path.iterdir() if path.is_file()
    }
    summary = empty_external_staging_summary()
    staged_files: list[str] = []
    copied_staged_files: list[str] = []
    total_sources = len(source_files)
    normalized_progress_offset = max(int(progress_offset), 0)
    normalized_progress_total = max(
        int(progress_total or total_sources), total_sources
    )
    explicit_allowed_files = _normalize_explicit_allowed_files(source_files)

    for index, raw_source in enumerate(tuple(source_files), start=1):
        if callable(should_cancel) and should_cancel():
            break
        source = str(raw_source or "").strip()
        if not source:
            summary["skipped"] += 1
            continue
        _emit_stage_prepare(
            output_callback,
            source=source,
            index=normalized_progress_offset + index,
            total=normalized_progress_total,
        )
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
        except OSError as exc:
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
                should_cancel=should_cancel,
                error_callback=error_callback,
            )
            if cancelled:
                break
            if staged_file:
                try:
                    validate_excel_import_limits(
                        (staged_file,),
                        reject_invalid_archives=False,
                    )
                except ExtractionError as exc:
                    if was_copied:
                        _remove_destination(
                            Path(staged_file),
                            error_callback=error_callback,
                            context="apos rejeicao por limite",
                            ignore_missing=True,
                        )
                    raise ValueError(str(exc)) from exc
                staged_files.append(staged_file)
                if was_copied:
                    copied_staged_files.append(staged_file)
                    summary["copied"] += 1
                else:
                    summary["already_staged"] += 1
        except OSError as exc:
            summary["failed"] += 1
            _emit_stage_error(
                error_callback,
                f"Falha ao copiar arquivo externo '{validated_source}': {exc}",
            )

    try:
        validate_excel_import_limits(staged_files, inspect_archives=False)
    except ExtractionError as exc:
        for copied_file in copied_staged_files:
            _remove_destination(
                Path(copied_file),
                error_callback=error_callback,
                context="apos rejeicao do lote",
                ignore_missing=True,
            )
        raise ValueError(str(exc)) from exc

    summary["staged"] = len(staged_files)
    _emit_stage_summary(output_callback, summary)
    return staged_files, summary


def _stage_validated_external_source(
    *,
    validated_source: str,
    docs_path: Path,
    reserved_paths: set[str],
    should_cancel: CancelCallback | None,
    error_callback: LineCallback | None,
) -> tuple[str | None, bool, bool]:
    base_destination = docs_path / os.path.basename(validated_source)
    base_destination_abs = os.path.abspath(str(base_destination))
    source_abs = os.path.abspath(validated_source)
    if source_abs == base_destination_abs:
        reserved_paths.add(base_destination_abs)
        return base_destination_abs, False, False

    for _attempt in range(MAX_STAGING_RESERVATION_ATTEMPTS):
        destination = _reserve_staging_destination(
            base_destination=base_destination,
            reserved_paths=reserved_paths,
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
        except OSError:
            if destination_created:
                _remove_destination(
                    destination,
                    error_callback=error_callback,
                    context="parcial",
                    ignore_missing=True,
                )
            reserved_paths.discard(destination_abs)
            raise
    raise FileExistsError(
        "Destino de staging ocupado apos "
        f"{MAX_STAGING_RESERVATION_ATTEMPTS} tentativas: {base_destination}"
    )


def _reserve_staging_destination(
    *,
    base_destination: Path,
    reserved_paths: set[str],
) -> Path:
    destination = reserve_unique_path(
        base_destination,
        reserved_paths=reserved_paths,
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
        if not ignore_missing:
            _emit_stage_error(
                error_callback,
                f"Arquivo staged {context} nao encontrado para remocao: '{destination}'",
            )
        return
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
            f"falhas={summary['failed']}, "
            f"ja_no_destino={summary['already_staged']}, "
            f"staged={summary['staged']}"
        )
