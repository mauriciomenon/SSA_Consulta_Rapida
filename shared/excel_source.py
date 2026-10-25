"""Limites e abertura validada de planilhas Excel (BL-44).

Usado pela extracao (extracao/extractor.py) e pelo armazenamento (armazenamento/derivadas_sync.py):
armazenamento nao importa extracao, e shared/ nao importa camadas do app. Movido literalmente de
extracao/extractor.py: limite por arquivo, por lote e descompactado (zip bomb).
"""

import os
from contextlib import contextmanager
from typing import BinaryIO, Generator, Iterable
from zipfile import BadZipFile, ZipFile

MAX_XLSX_FILE_BYTES = 128 * 1024 * 1024
MAX_IMPORT_BATCH_FILES = 64
MAX_IMPORT_BATCH_BYTES = 1024 * 1024 * 1024
MAX_XLSX_EXPANDED_BYTES = 1024 * 1024 * 1024
_ZIP_BASED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm"})


class ExtractionError(Exception):
    """Erro durante a extração de dados de um arquivo."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def validate_excel_import_limits(
    file_paths: Iterable[str | os.PathLike[str] | BinaryIO],
    *,
    inspect_archives: bool = True,
    ignore_unavailable: bool = False,
    enforce_batch_file_limit: bool = True,
    reject_invalid_archives: bool = True,
) -> int:
    """Validate file, batch, and declared expanded XLSX sizes."""
    sources = tuple(file_paths)
    if enforce_batch_file_limit and len(sources) > MAX_IMPORT_BATCH_FILES:
        raise ExtractionError(
            f"Lote de importacao excede o limite de {MAX_IMPORT_BATCH_FILES} arquivos "
            f"(recebido: {len(sources)}).",
            error_code="BATCH_FILE_LIMIT_EXCEEDED",
        )

    total_batch_bytes = 0
    for source in sources:
        owns_stream = isinstance(source, (str, os.PathLike))
        file_path = (
            os.fspath(source)
            if owns_stream
            else str(getattr(source, "name", "<stream>"))
        )
        base_name = os.path.basename(file_path) or file_path
        try:
            stream = open(file_path, "rb") if owns_stream else source
        except OSError as exc:
            if ignore_unavailable:
                continue
            raise ExtractionError(
                f"Nao foi possivel abrir '{base_name}' para validacao: {exc}",
                error_code="FILE_SIZE_CHECK_FAILED",
            ) from exc

        original_position: int | None = None
        try:
            original_position = stream.tell()
            try:
                file_size = os.fstat(stream.fileno()).st_size
            except (AttributeError, OSError):
                try:
                    stream.seek(0, os.SEEK_END)
                    file_size = stream.tell()
                except (AttributeError, OSError) as exc:
                    if ignore_unavailable:
                        continue
                    raise ExtractionError(
                        f"Nao foi possivel verificar o tamanho de '{base_name}': {exc}",
                        error_code="FILE_SIZE_CHECK_FAILED",
                    ) from exc

            if file_size > MAX_XLSX_FILE_BYTES:
                raise ExtractionError(
                    f"Arquivo '{base_name}' excede o limite de "
                    f"{MAX_XLSX_FILE_BYTES // (1024 * 1024)} MiB "
                    f"(tamanho: {file_size // (1024 * 1024)} MiB).",
                    error_code="FILE_TOO_LARGE",
                )

            total_batch_bytes += file_size
            if total_batch_bytes > MAX_IMPORT_BATCH_BYTES:
                raise ExtractionError(
                    "Lote de importacao excede o limite de "
                    f"{MAX_IMPORT_BATCH_BYTES // (1024 * 1024 * 1024)} GiB "
                    f"(total: {total_batch_bytes // (1024 * 1024 * 1024)} GiB).",
                    error_code="BATCH_SIZE_LIMIT_EXCEEDED",
                )

            suffix = os.path.splitext(file_path)[1].casefold()
            if inspect_archives and suffix in _ZIP_BASED_EXCEL_SUFFIXES:
                try:
                    stream.seek(0)
                    expanded_bytes = 0
                    with ZipFile(stream) as archive:
                        for member in archive.infolist():
                            expanded_bytes += member.file_size
                            if expanded_bytes > MAX_XLSX_EXPANDED_BYTES:
                                raise ExtractionError(
                                    f"Arquivo '{base_name}' excede o limite descompactado de "
                                    f"{MAX_XLSX_EXPANDED_BYTES // (1024 * 1024 * 1024)} GiB.",
                                    error_code="XLSX_EXPANDED_TOO_LARGE",
                                )
                except ExtractionError:
                    raise
                except (BadZipFile, OSError) as exc:
                    if reject_invalid_archives:
                        raise ExtractionError(
                            f"Arquivo '{base_name}' nao e um XLSX valido: {exc}",
                            error_code="INVALID_XLSX_ARCHIVE",
                        ) from exc
        finally:
            if owns_stream:
                stream.close()
            elif original_position is not None:
                # Sem posicao original (tell falhou), o erro de tell propaga intacto.
                stream.seek(original_position)

    return total_batch_bytes


@contextmanager
def open_validated_excel_source(
    file_path: str | os.PathLike[str],
) -> Generator[BinaryIO]:
    """Open, validate, and yield the same stream consumed by the parser."""
    try:
        with open(file_path, "rb") as source_stream:
            validate_excel_import_limits((source_stream,))
            yield source_stream
    except ExtractionError:
        raise
    except OSError as exc:
        base_name = os.path.basename(os.fspath(file_path)) or os.fspath(file_path)
        raise ExtractionError(
            f"Nao foi possivel abrir '{base_name}' para leitura: {exc}",
            error_code="FILE_SIZE_CHECK_FAILED",
        ) from exc
