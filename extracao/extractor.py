# extracao/extractor.py 20250725 101500 (v6.4 - Melhorias de Tipo, Sanitizacao, Logging)
"""
Módulo responsável pela extração e normalização inicial de dados de arquivos Excel.

Lê arquivos .xlsx, identifica cabeçalhos, normaliza nomes de colunas usando
`config/column_mappings.json` e converte tipos de dados fundamentais.
"""

import logging
import os
import re
from contextlib import contextmanager
from typing import Any, BinaryIO, Callable, Dict, Iterable, Iterator, Optional
from zipfile import BadZipFile, ZipFile

import pandas as pd

from shared.column_mappings import load_column_mappings_integrity
from shared.date_utils import parse_datetime_series_mixed
from shared.import_contract import MANDATORY_SCHEMA_COLUMNS
from utils.file_metadata import best_datetime_for_file
from utils.robust_importer import import_excel_robust

logger = logging.getLogger(__name__)
TEMPO_EXCEDIDO_RE = re.compile(r"(\d+)\s*(mi|mo|m|d|h)(?=\s|$|\d)", re.IGNORECASE)

MAX_XLSX_FILE_BYTES = 128 * 1024 * 1024
MAX_IMPORT_BATCH_FILES = 64
MAX_IMPORT_BATCH_BYTES = 1024 * 1024 * 1024
MAX_XLSX_EXPANDED_BYTES = 1024 * 1024 * 1024
_ZIP_BASED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm"})
_SOURCE_SHEET_COLUMN = "__ssa_source_sheet"
_SOURCE_ROW_COLUMN = "__ssa_source_row"
_HIERARCHICAL_MARKER_COLUMNS = (
    "numero_desvios",
    "num_reprogramacoes",
    "parciais",
)
_HIERARCHICAL_SEQUENCE_RE = re.compile(
    r"^(?P<stem>.+?\S)\s+#\s*(?P<order>[1-9]\d*)\s*$"
)


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
            else:
                stream.seek(original_position)

    return total_batch_bytes


@contextmanager
def open_validated_excel_source(
    file_path: str | os.PathLike[str],
) -> Iterator[BinaryIO]:
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


def _load_column_mappings() -> dict:
    """
    Carrega o mapeamento de nomes de colunas a partir do arquivo JSON.

    Returns:
        dict: Um dicionário {alias: nome_canonico}.
              Retorna um dicionário vazio se o arquivo não for encontrado.
    """
    try:
        mappings = load_column_mappings_integrity()
        inverted_map = {
            alias: canonical
            for canonical, aliases in mappings.items()
            for alias in aliases
        }
        logger.debug(
            f"Mapeamento de colunas carregado com {len(inverted_map)} entradas (via integridade)."
        )
        return inverted_map
    except Exception as e:
        logger.error(f"Falha ao carregar mapeamentos de coluna com integridade: {e}")
        return {}


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure column names are unique while keeping semantic aliases when possible."""

    if df.empty:
        return df

    counts: dict[str, int] = {}
    used: set[str] = set()
    resolved: list[str] = []

    # Canonical resolution map - subsequent duplicates get deterministic names.
    duplicate_resolution: dict[str, list[str]] = {
        "desde": ["desde", "desde_1", "desde_2"],
        "ate": ["ate", "ate_1", "ate_2"],
        "sn": ["sn_retirado", "sn_instalado", "sn_extra"],
        "numero_ssa": [
            "numero_ssa",
            "numero_ssa_relacionada_1",
            "numero_ssa_relacionada_2",
            "numero_ssa_relacionada_3",
        ],
        "setor_emissor": [
            "setor_emissor",
            "setor_emissor_relacionado_1",
            "setor_emissor_relacionado_2",
        ],
        "setor_executor": [
            "setor_executor",
            "setor_executor_relacionado_1",
            "setor_executor_relacionado_2",
        ],
        "situacao": ["situacao", "situacao_relacionada_1", "situacao_relacionada_2"],
    }

    for original_name in df.columns:
        base_name = str(original_name)
        count = counts.get(base_name, 0)
        normalized = base_name.lower()
        options = duplicate_resolution.get(normalized)
        if options and count < len(options):
            candidate = options[count]
        elif count == 0:
            candidate = base_name
        else:
            candidate = f"{base_name}_{count}"
        # Guarantee uniqueness even after resolution.
        while candidate in used:
            count += 1
            counts[base_name] = count
            options = duplicate_resolution.get(normalized)
            if options and count < len(options):
                candidate = options[count]
            else:
                candidate = f"{base_name}_{count}"
        counts[base_name] = count + 1
        used.add(candidate)
        resolved.append(candidate)

    df = df.copy()
    df.columns = resolved
    return df


def _normalize_tempo_excedido_value(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    matches = TEMPO_EXCEDIDO_RE.findall(text)
    if not matches:
        return text
    units = {"months": 0, "days": 0, "hours": 0, "minutes": 0}
    for number, unit in matches:
        try:
            qty = int(number)
        except ValueError:
            return text
        if unit == "mi":
            units["minutes"] += qty
        elif unit == "m":
            units["minutes"] += qty
        elif unit == "mo":
            units["months"] += qty
        elif unit == "d":
            units["days"] += qty
        elif unit == "h":
            units["hours"] += qty
    parts = ["P"]
    if units["months"]:
        parts.append(f"{units['months']}M")
    if units["days"]:
        parts.append(f"{units['days']}D")
    time_parts: list[str] = []
    if units["hours"]:
        time_parts.append(f"{units['hours']}H")
    if units["minutes"]:
        time_parts.append(f"{units['minutes']}M")
    if time_parts:
        parts.append("T" + "".join(time_parts))
    normalized = "".join(parts)
    return normalized if normalized != "P" else text


def _record_debug_phase_columns(
    debug_phases: Optional[dict[str, list[str]]],
    phase_name: str,
    columns: Any,
    *,
    context_name: str | None = None,
) -> None:
    if debug_phases is None:
        return
    serialized = [str(column) for column in list(columns)]
    if phase_name not in debug_phases:
        debug_phases[phase_name] = serialized
    if context_name:
        debug_phases[f"{context_name}:{phase_name}"] = serialized


def _summarize_invalid_identity_rows(
    frame: pd.DataFrame,
    invalid_mask: pd.Series,
) -> dict[str, Any]:
    invalid_rows = frame.loc[invalid_mask].copy()
    if invalid_rows.empty:
        return {
            "total_removed": 0,
            "empty_removed": 0,
            "payload_removed": 0,
            "payload_columns_sample": [],
        }

    payload_columns = [
        col
        for col in invalid_rows.columns
        if col not in {"numero_ssa", "descricao_ssa"}
    ]
    if payload_columns:
        payload_frame = invalid_rows[payload_columns].copy()
        for col in payload_columns:
            if pd.api.types.is_object_dtype(
                payload_frame[col]
            ) or pd.api.types.is_string_dtype(payload_frame[col]):
                stripped = payload_frame[col].astype("string").str.strip()
                payload_frame[col] = payload_frame[col].mask(stripped.eq(""), pd.NA)
        payload_presence = payload_frame.notna().any(axis=1)
    else:
        payload_presence = pd.Series(False, index=invalid_rows.index, dtype=bool)

    payload_removed = int(payload_presence.sum())
    empty_removed = int((~payload_presence).sum())
    payload_columns_sample = [
        str(col) for col in payload_columns if payload_frame[col].notna().any()
    ][:8]
    return {
        "total_removed": int(len(invalid_rows)),
        "empty_removed": empty_removed,
        "payload_removed": payload_removed,
        "payload_columns_sample": payload_columns_sample,
    }


def _capture_hierarchical_records(
    frame: pd.DataFrame,
    *,
    source_path: str,
) -> tuple[list[dict[str, Any]], set[Any], dict[str, int]]:
    """Capture report events without flattening them into the one-row SSA table."""
    required = {
        "numero_ssa",
        "descricao_ssa",
        _SOURCE_SHEET_COLUMN,
        _SOURCE_ROW_COLUMN,
    }
    if not required.issubset(frame.columns):
        return [], set(), {}

    source_datetime = best_datetime_for_file(source_path)
    arquivo_origem = os.path.basename(source_path) or source_path
    data_planilha = (
        source_datetime.isoformat(timespec="seconds")
        if source_datetime is not None
        else None
    )
    data_arquivo_origem = (
        source_datetime.strftime("%Y-%m-%d %H:%M:%S")
        if source_datetime is not None
        else None
    )

    def _present(series: pd.Series) -> pd.Series:
        text = series.astype("string").str.strip()
        return (
            series.notna()
            & text.ne("")
            & ~text.str.casefold().isin({"<na>", "none", "nan", "null"})
        )

    numero_present = _present(frame["numero_ssa"])
    descricao_present = _present(frame["descricao_ssa"])
    sheet_values = frame[_SOURCE_SHEET_COLUMN]
    parent_boundary = numero_present | descricao_present
    group_number = parent_boundary.groupby(sheet_values, sort=False).cumsum()
    parent_raw = (
        frame["numero_ssa"]
        .where(numero_present)
        .groupby([sheet_values, group_number], sort=False)
        .ffill()
    )
    parent_ssa = (
        pd.to_numeric(parent_raw, errors="coerce").astype("Int64").astype("string")
    )

    records: list[dict[str, Any]] = []
    captured_indices: set[Any] = set()
    captured_by_type: dict[str, int] = {}
    internal_columns = {_SOURCE_SHEET_COLUMN, _SOURCE_ROW_COLUMN}
    identity_columns = {"numero_ssa", "descricao_ssa"}
    identity_blank = ~numero_present & ~descricao_present
    linked_identity_blank = identity_blank & parent_ssa.notna()
    groupers = [sheet_values, group_number]

    marker_masks: dict[Any, pd.Series] = {}
    for marker_column in _HIERARCHICAL_MARKER_COLUMNS:
        if marker_column not in frame.columns:
            continue
        marker_text = frame[marker_column].astype("string").str.strip()
        canonical_marker_present = _present(frame[marker_column])
        textual_marker = marker_text.str.contains(r"[^\W\d_]", regex=True, na=False)
        canonical_sequence = marker_text.str.extract(_HIERARCHICAL_SEQUENCE_RE)
        canonical_order = pd.to_numeric(canonical_sequence["order"], errors="coerce")
        first_parent = (
            canonical_order.eq(1)
            & numero_present
            & parent_ssa.notna()
        )
        textual_parent = (
            canonical_marker_present
            & textual_marker
            & numero_present
            & parent_ssa.notna()
        )
        textual_child = canonical_marker_present & textual_marker & linked_identity_blank
        qualified_group = first_parent.groupby(groupers, sort=False).transform("any") | (
            textual_parent.groupby(groupers, sort=False).transform("any")
            & textual_child.groupby(groupers, sort=False).transform("any")
        )
        marker_masks[marker_column] = canonical_marker_present & qualified_group

    known_children = pd.Series(False, index=frame.index, dtype=bool)
    for marker_present in marker_masks.values():
        known_children |= marker_present & linked_identity_blank
    remaining_linked = linked_identity_blank & ~known_children
    if remaining_linked.any():
        excluded_columns = internal_columns | identity_columns | set(
            _HIERARCHICAL_MARKER_COLUMNS
        )
        structural_group_owner: dict[tuple[Any, Any], Any] = {}
        for marker_column in frame.columns:
            if marker_column in excluded_columns:
                continue
            marker_values = frame[marker_column]
            if not (
                pd.api.types.is_object_dtype(marker_values)
                or pd.api.types.is_string_dtype(marker_values)
            ):
                continue
            child_text = (
                marker_values.loc[remaining_linked].astype("string").str.strip()
            )
            if child_text.empty or not child_text.str.contains("#", regex=False).any():
                continue
            child_sequence = child_text.str.extract(_HIERARCHICAL_SEQUENCE_RE)
            child_order = pd.to_numeric(child_sequence["order"], errors="coerce")
            if not child_order.eq(2).any():
                continue

            marker_text = frame[marker_column].astype("string").str.strip()
            marker_sequence = marker_text.str.extract(_HIERARCHICAL_SEQUENCE_RE)
            marker_order = pd.to_numeric(marker_sequence["order"], errors="coerce")
            sequence_table = pd.DataFrame(
                {
                    "sheet": sheet_values,
                    "group": group_number,
                    "stem": marker_sequence["stem"].astype("string").str.casefold(),
                    "order": marker_order,
                },
                index=frame.index,
            )
            parent_keys = set(
                sequence_table.loc[
                    numero_present & parent_ssa.notna() & marker_order.eq(1),
                    ["sheet", "group", "stem"],
                ].itertuples(index=False, name=None)
            )
            child_keys = set(
                sequence_table.loc[
                    remaining_linked & marker_order.eq(2),
                    ["sheet", "group", "stem"],
                ].itertuples(index=False, name=None)
            )
            qualified_keys = parent_keys & child_keys
            if not qualified_keys:
                continue
            qualified_stems: dict[tuple[Any, Any], set[str]] = {}
            for sheet, group, stem in qualified_keys:
                qualified_stems.setdefault((sheet, group), set()).add(str(stem))
            for group_key in qualified_stems:
                previous_column = structural_group_owner.get(group_key)
                if previous_column is not None and previous_column != marker_column:
                    raise ExtractionError(
                        "Ambiguous hierarchical marker columns "
                        f"{previous_column!r} and {marker_column!r} in "
                        f"sheet {group_key[0]!r}",
                        error_code="AMBIGUOUS_HIERARCHICAL_MARKERS",
                    )
                structural_group_owner[group_key] = marker_column
            marker_casefolded = marker_text.str.casefold()
            numbered_rows: list[bool] = []
            ambiguous_tail = False
            for sheet, group, label, stem, order in zip(
                sheet_values,
                group_number,
                marker_casefolded,
                marker_sequence["stem"].astype("string").str.casefold(),
                marker_order,
                strict=True,
            ):
                group_stems = qualified_stems.get((sheet, group), ())
                related = isinstance(label, str) and any(
                    label == group_stem or label.startswith(f"{group_stem} ")
                    for group_stem in group_stems
                )
                numbered = bool(pd.notna(order)) and (
                    sheet,
                    group,
                    str(stem),
                ) in qualified_keys
                numbered_rows.append(numbered)
                ambiguous_tail |= related and not numbered
            if ambiguous_tail:
                raise ExtractionError(
                    f"Ambiguous unnumbered hierarchical tail in {marker_column!r}",
                    error_code="AMBIGUOUS_HIERARCHICAL_TAIL",
                )
            marker_masks[marker_column] = _present(frame[marker_column]) & pd.Series(
                numbered_rows,
                index=frame.index,
                dtype=bool,
            )

    for marker_column, marker_present in marker_masks.items():
        linked_children = marker_present & linked_identity_blank
        event_rows = marker_present & (
            (numero_present & parent_ssa.notna()) | linked_children
        )
        if not event_rows.any():
            continue

        captured_indices.update(frame.index[linked_children].tolist())
        record_type = str(marker_column).strip()
        has_linked_children = bool(linked_children.any())
        event_columns = [marker_column]
        if has_linked_children:
            captured_by_type[record_type] = int(linked_children.sum())
            event_columns = [
                column
                for column in frame.columns
                if column not in internal_columns | identity_columns
                and _present(frame.loc[linked_children, column]).any()
            ]
        event_order = (
            frame.loc[event_rows]
            .groupby(
                [sheet_values.loc[event_rows], group_number.loc[event_rows]],
                sort=False,
            )
            .cumcount()
            + 1
        )

        event_index = frame.index[event_rows]
        for start in range(0, len(event_index), 1000):
            chunk_index = event_index[start : start + 1000]
            payload_frame = frame.loc[chunk_index, event_columns].copy()
            for column in event_columns:
                if pd.api.types.is_object_dtype(
                    payload_frame[column]
                ) or pd.api.types.is_string_dtype(payload_frame[column]):
                    text = payload_frame[column].astype("string").str.strip()
                    payload_frame[column] = text.mask(
                        text.str.casefold().isin({"", "<na>", "none", "nan", "null"}),
                        pd.NA,
                    )
            payload_rows = payload_frame.to_json(
                orient="records",
                lines=True,
                date_format="iso",
                force_ascii=True,
            ).splitlines()
            metadata_rows = zip(
                parent_ssa.loc[chunk_index].tolist(),
                frame.loc[chunk_index, marker_column].tolist(),
                frame.loc[chunk_index, _SOURCE_SHEET_COLUMN].tolist(),
                frame.loc[chunk_index, _SOURCE_ROW_COLUMN].tolist(),
                event_order.loc[chunk_index].tolist(),
                payload_rows,
                strict=True,
            )
            for (
                numero_ssa,
                label,
                source_sheet,
                source_row,
                order,
                payload_json,
            ) in metadata_rows:
                records.append(
                    {
                        "numero_ssa": str(numero_ssa),
                        "record_type": record_type,
                        "record_order": int(order),
                        "record_label": str(label).strip(),
                        "payload_json": payload_json,
                        "arquivo_origem": arquivo_origem,
                        "data_planilha": data_planilha,
                        "data_arquivo_origem": data_arquivo_origem,
                        "source_sheet": str(source_sheet),
                        "source_row": int(source_row),
                    }
                )

    return records, captured_indices, captured_by_type


def _normalize_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas-chave para tipos de dados padronizados.

    Args:
        df (pd.DataFrame): O DataFrame bruto após combinar planilhas.

    Returns:
        pd.DataFrame: O DataFrame com tipos de dados normalizados.
    """
    logger.debug("Iniciando normalização de tipos de dados...")
    df_normalized = df.copy()  # Trabalha em uma cópia

    # --- Conversao de numero_ssa para Int64 nullable ---
    if "numero_ssa" in df_normalized.columns:
        logger.debug("Convertendo 'numero_ssa' para Int64...")
        df_normalized["numero_ssa"] = pd.to_numeric(
            df_normalized["numero_ssa"], errors="coerce"
        ).astype("Int64")

    # --- Conversao de data_cadastro para datetime ---
    if "data_cadastro" in df_normalized.columns:
        logger.debug("Convertendo 'data_cadastro' para datetime...")
        df_normalized["data_cadastro"] = parse_datetime_series_mixed(
            df_normalized["data_cadastro"]
        )
        missing_mask = df_normalized["data_cadastro"].isna()
        if missing_mask.any():
            logger.debug(
                "Detectados %s registros sem 'data_cadastro' apos conversao inicial; aplicando fallbacks.",
                int(missing_mask.sum()),
            )
            fallback_candidates = [
                "desde",
                "desde_1",
                "data_inicio_programada",
                "data_programacao",
            ]
            for col in fallback_candidates:
                if col not in df_normalized.columns:
                    continue
                candidate_series = parse_datetime_series_mixed(df_normalized[col])
                fill_mask = missing_mask & candidate_series.notna()
                if fill_mask.any():
                    df_normalized.loc[fill_mask, "data_cadastro"] = (
                        candidate_series.loc[fill_mask]
                    )
                    missing_mask = df_normalized["data_cadastro"].isna()
                    logger.debug(
                        "Preenchidos %s registros de 'data_cadastro' usando coluna '%s'. Restantes sem 'data_cadastro': %s",
                        int(fill_mask.sum()),
                        col,
                        int(missing_mask.sum()),
                    )
                    if not missing_mask.any():
                        break
            if missing_mask.any():
                logger.debug(
                    "Ainda restam %s registros sem 'data_cadastro' apos fallbacks.",
                    int(missing_mask.sum()),
                )

    # --- Conversao de colunas de semana para Int64 nullable ---
    semana_columns = [col for col in df_normalized.columns if "semana" in col.lower()]
    for col in semana_columns:
        logger.debug(f"Convertendo coluna de semana '{col}' para Int64...")
        df_normalized[col] = pd.to_numeric(df_normalized[col], errors="coerce").astype(
            "Int64"
        )

    # --- Conversao de outras colunas numericas conhecidas ---
    numeric_columns = [
        "total_de_reprogramacoes",
    ]
    for col in numeric_columns:
        if col in df_normalized.columns:
            logger.debug(f"Convertendo '{col}' para Int64...")
            df_normalized[col] = pd.to_numeric(
                df_normalized[col], errors="coerce"
            ).astype("Int64")

    # Keep canonical numeric semantics for reprogramacoes:
    # - num_reprogramacoes accepts numeric values
    # - total_de_reprogramacoes backfills num_reprogramacoes when available
    if "num_reprogramacoes" in df_normalized.columns:
        logger.debug("Convertendo 'num_reprogramacoes' para Int64...")
        num_series = pd.to_numeric(df_normalized["num_reprogramacoes"], errors="coerce")
        if "total_de_reprogramacoes" in df_normalized.columns:
            backfill_mask = (
                num_series.isna() & df_normalized["total_de_reprogramacoes"].notna()
            )
            if backfill_mask.any():
                logger.debug(
                    "Backfill de 'num_reprogramacoes' com 'total_de_reprogramacoes' em %s linhas.",
                    int(backfill_mask.sum()),
                )
                num_series.loc[backfill_mask] = df_normalized.loc[
                    backfill_mask, "total_de_reprogramacoes"
                ]
        df_normalized["num_reprogramacoes"] = num_series.astype("Int64")

    logger.debug("Normalização de tipos concluída.")
    return df_normalized


def extract_data_from_excel(
    file_path: str,
    *,
    should_cancel: Optional[Callable[[], bool]] = None,
    _debug_phases: Optional[dict[str, list[str]]] = None,
) -> pd.DataFrame:
    """
    Extrai dados de um único arquivo Excel (.xlsx).

    Args:
        file_path (str): Caminho completo para o arquivo Excel.
        should_cancel (Optional[Callable[[], bool]]): Callback consultivo para
            interromper a extracao quando retornar True.

    Returns:
        pd.DataFrame: Um DataFrame com os dados extraídos e normalizados.
            Pode ser vazio quando o arquivo tem cabecalho sem linhas de dados.
    """
    logger.info(f"Iniciando extração de dados de '{file_path}'...")
    base_name = os.path.basename(file_path) if file_path else "arquivo"
    saw_header = False
    try:

        def _check_cancel() -> None:
            if should_cancel is not None and should_cancel():
                raise ExtractionError(
                    "operation cancelled",
                    error_code="OPERATION_CANCELLED",
                )

        _check_cancel()
        all_sheets_data = []
        column_mappings = _load_column_mappings()
        normalized_column_mappings = {
            str(key).strip(): value for key, value in column_mappings.items()
        }
        with (
            open_validated_excel_source(file_path) as source_stream,
            pd.ExcelFile(source_stream, engine="openpyxl") as xl_file,
        ):
            for sheet_name in xl_file.sheet_names:
                _check_cancel()
                logger.debug(f"Processando planilha '{sheet_name}'...")
                # Le a planilha inteira
                parsed_sheet = xl_file.parse(sheet_name, header=None)
                if not isinstance(parsed_sheet, pd.DataFrame):
                    raise ExtractionError(
                        f"Unexpected parse output type for sheet '{sheet_name}': {type(parsed_sheet).__name__}"
                    )
                sheet_df = parsed_sheet
                if sheet_df.empty or sheet_df.shape[1] == 0:
                    logger.debug("Planilha '%s' vazia; ignorando.", sheet_name)
                    continue

                # Encontra a linha do cabecalho (primeira celula nao vazia na coluna 0)
                _check_cancel()
                first_column = sheet_df.iloc[:, 0]
                header_candidates = first_column[
                    first_column.notna()
                    & first_column.astype("string").str.strip().ne("")
                ].index
                header_row_idx = (
                    int(header_candidates[0]) if len(header_candidates) else None
                )

                if header_row_idx is not None:
                    saw_header = True
                    # Define os cabecalhos
                    sheet_df.columns = sheet_df.iloc[header_row_idx]
                    _record_debug_phase_columns(
                        _debug_phases,
                        "header_raw",
                        sheet_df.columns,
                        context_name=sheet_name,
                    )
                    # Remove linhas anteriores ao cabecalho e o proprio cabecalho
                    sheet_df = sheet_df.drop(sheet_df.index[: header_row_idx + 1])
                    # Reseta o indice
                    sheet_df = sheet_df.reset_index(drop=True)

                    # Remove colunas completamente vazias, mas preserva aliases
                    # das colunas obrigatorias ate a normalizacao canonica.
                    columns_to_keep: list[int] = []
                    for col_idx, col_name in enumerate(sheet_df.columns):
                        column_data = sheet_df.iloc[:, col_idx]
                        if not column_data.isna().all():
                            columns_to_keep.append(col_idx)
                            continue
                        if isinstance(col_name, pd.Series):
                            non_null_labels = col_name.dropna()
                            if non_null_labels.empty:
                                continue
                            col_name = non_null_labels.iloc[0]
                        if pd.isna(col_name):
                            continue
                        normalized_col_name = str(col_name).strip()
                        canonical_name = normalized_column_mappings.get(
                            normalized_col_name,
                            column_mappings.get(col_name, normalized_col_name),
                        )
                        if canonical_name in MANDATORY_SCHEMA_COLUMNS:
                            columns_to_keep.append(col_idx)
                    if len(columns_to_keep) != len(sheet_df.columns):
                        sheet_df = sheet_df.iloc[:, columns_to_keep]
                    _record_debug_phase_columns(
                        _debug_phases,
                        "after_empty_column_prune",
                        sheet_df.columns,
                        context_name=sheet_name,
                    )

                    if not sheet_df.empty:
                        reserved_names = {_SOURCE_SHEET_COLUMN, _SOURCE_ROW_COLUMN}
                        reserved_columns = {
                            str(column)
                            for column in sheet_df.columns
                            if str(column) in reserved_names
                        }
                        if reserved_columns:
                            raise ExtractionError(
                                "Reserved internal columns found in source: "
                                f"{sorted(reserved_columns)}",
                                error_code="RESERVED_COLUMN_COLLISION",
                            )
                        sheet_df[_SOURCE_SHEET_COLUMN] = str(sheet_name)
                        sheet_df[_SOURCE_ROW_COLUMN] = (
                            sheet_df.index + header_row_idx + 2
                        )
                        all_sheets_data.append(sheet_df)
                    else:
                        logger.debug(
                            f"Planilha '{sheet_name}' está vazia após processamento."
                        )
                else:
                    logger.warning(
                        "Planilha '%s' em '%s' nao possui cabecalho identificavel.",
                        sheet_name,
                        file_path,
                    )

        if not all_sheets_data:
            if saw_header:
                logger.info(
                    "Arquivo '%s' sem linhas de dados apos cabecalho; retornando vazio.",
                    file_path,
                )
                return pd.DataFrame()
            raise ExtractionError(f"No header found in any sheet for file: {base_name}")

        # Combina dados de todas as planilhas
        combined_df = pd.concat(all_sheets_data, ignore_index=True, sort=False)

        # Remove linhas completamente vazias
        initial_len = len(combined_df)
        empty_row_mask = (
            combined_df.drop(
                columns=[_SOURCE_SHEET_COLUMN, _SOURCE_ROW_COLUMN], errors="ignore"
            )
            .isna()
            .all(axis=1)
        )
        combined_df = combined_df.loc[~empty_row_mask].copy()
        final_len = len(combined_df)
        early_empty_removed = initial_len - final_len
        if initial_len != final_len:
            logger.debug(
                f"Removidas {initial_len - final_len} linhas completamente vazias."
            )

        if combined_df.empty:
            logger.warning(
                "Nenhum dado valido encontrado em '%s' apos combinacao; retornando vazio.",
                file_path,
            )
            return pd.DataFrame()

        source_sheet = combined_df.pop(_SOURCE_SHEET_COLUMN)
        source_row = combined_df.pop(_SOURCE_ROW_COLUMN)

        if not column_mappings:
            logger.warning(
                "Mapeamento de colunas vazio; mantendo nomes originais para '%s'.",
                file_path,
            )

        # Normaliza os nomes das colunas.
        if column_mappings:
            rename_columns = {
                col: normalized_column_mappings.get(
                    str(col).strip(),
                    column_mappings.get(col, str(col).strip()),
                )
                for col in combined_df.columns
            }
            combined_df.rename(columns=rename_columns, inplace=True)
        _record_debug_phase_columns(
            _debug_phases,
            "after_rename",
            combined_df.columns,
        )

        def _is_unnamed_header_value(header_value: Any) -> bool:
            if isinstance(header_value, str):
                normalized_header = header_value.strip().lower()
                return normalized_header in {"", "nan"} or normalized_header.startswith(
                    "unnamed:"
                )
            return bool(pd.isna(header_value))

        if "anomalia" in combined_df.columns and not {
            "total_tempo_tpe_executada",
            "total_tempo_tex_executada",
            "total_tempo_tpo_executada",
        }.intersection(set(combined_df.columns)):
            anomaly_idx = list(combined_df.columns).index("anomalia")
            trailing_positions = list(range(anomaly_idx + 1, len(combined_df.columns)))
            trailing_unnamed_positions = [
                pos
                for pos in trailing_positions
                if _is_unnamed_header_value(combined_df.columns[pos])
            ]
            if trailing_unnamed_positions == trailing_positions:
                if len(trailing_unnamed_positions) == 3:
                    renamed_columns = list(combined_df.columns)
                    renamed_columns[trailing_unnamed_positions[0]] = (
                        "total_tempo_tpe_executada"
                    )
                    renamed_columns[trailing_unnamed_positions[1]] = (
                        "total_tempo_tex_executada"
                    )
                    renamed_columns[trailing_unnamed_positions[2]] = (
                        "total_tempo_tpo_executada"
                    )
                    combined_df.columns = renamed_columns
                    logger.info(
                        "Arquivo '%s' possui 3 colunas finais sem header apos 'anomalia'; remapeadas para totais TPE/TEX/TPO executada.",
                        file_path,
                    )
                elif (
                    len(trailing_unnamed_positions) == 1
                    and "total_tempo_tex_executada" not in combined_df.columns
                ):
                    tex_pos = trailing_unnamed_positions[0]
                    tex_series = combined_df.iloc[:, tex_pos]
                    tex_non_null = tex_series.dropna()
                    numeric_tex = pd.to_numeric(tex_non_null, errors="coerce")
                    if not tex_non_null.empty and numeric_tex.notna().all():
                        renamed_columns = list(combined_df.columns)
                        renamed_columns[tex_pos] = "total_tempo_tex_executada"
                        combined_df.columns = renamed_columns
                        logger.info(
                            "Arquivo '%s' possui 1 coluna final sem header apos 'anomalia'; remapeada para total_tempo_tex_executada.",
                            file_path,
                        )

        trailing_unnamed_positions: list[int] = []
        for pos in range(len(combined_df.columns) - 1, -1, -1):
            if _is_unnamed_header_value(combined_df.columns[pos]):
                trailing_unnamed_positions.append(pos)
                continue
            break
        trailing_unnamed_positions.reverse()
        if (
            len(trailing_unnamed_positions) == 1
            and "total_tempo_tex_executada" not in combined_df.columns
            and {
                "execucao_parcial",
                "responsavel_execucao",
                "descricao_execucao",
                "prazo_limite",
            }.issubset(set(combined_df.columns))
        ):
            tex_pos = trailing_unnamed_positions[0]
            previous_named = combined_df.columns[tex_pos - 1] if tex_pos > 0 else None
            tex_series = combined_df.iloc[:, tex_pos]
            tex_non_null = tex_series.dropna()
            numeric_tex = pd.to_numeric(tex_non_null, errors="coerce")
            if (
                previous_named in {"anomalia", "prazo_limite"}
                and not tex_non_null.empty
                and numeric_tex.notna().all()
            ):
                renamed_columns = list(combined_df.columns)
                renamed_columns[tex_pos] = "total_tempo_tex_executada"
                combined_df.columns = renamed_columns
                logger.info(
                    "Arquivo '%s' possui 1 coluna trailing sem header no bloco de execucao; remapeada para total_tempo_tex_executada.",
                    file_path,
                )

        _record_debug_phase_columns(
            _debug_phases,
            "after_structural_repair",
            combined_df.columns,
        )

        # Resolve duplicadas apos a normalizacao contextual.
        combined_df = _deduplicate_columns(combined_df)
        _record_debug_phase_columns(
            _debug_phases,
            "after_deduplicate",
            combined_df.columns,
        )

        combined_df[_SOURCE_SHEET_COLUMN] = source_sheet.reindex(combined_df.index)
        combined_df[_SOURCE_ROW_COLUMN] = source_row.reindex(combined_df.index)

        missing_required = MANDATORY_SCHEMA_COLUMNS.difference(set(combined_df.columns))
        if missing_required:
            missing_required_sorted = sorted(missing_required)
            available_columns = sorted(str(col) for col in combined_df.columns)
            debug_phase_names = (
                sorted(_debug_phases.keys()) if isinstance(_debug_phases, dict) else []
            )
            raise ExtractionError(
                "Missing required columns after normalization: "
                f"{missing_required_sorted}; "
                f"available_columns={available_columns[:40]}; "
                f"debug_phases={debug_phase_names}",
                error_code="MISSING_REQUIRED_COLUMNS",
            )

        event_records, captured_indices, captured_by_type = (
            _capture_hierarchical_records(combined_df, source_path=file_path)
        )
        combined_df.drop(
            columns=[_SOURCE_SHEET_COLUMN, _SOURCE_ROW_COLUMN],
            inplace=True,
        )

        if "prazo_limite" in combined_df.columns:
            status_col = "status_execucao_prazo"
            status_map = {
                "fora de prazo": "Fora de Prazo",
                "dentro do prazo": "Dentro do Prazo",
                "não aplica": "Não Se Aplica",
                "nao aplica": "Não Se Aplica",
            }
            prazo_series = combined_df["prazo_limite"].astype(str).str.strip()
            status_series = pd.Series(pd.NA, index=combined_df.index, dtype="object")
            status_mask = prazo_series.str.lower().isin(status_map.keys())
            if status_mask.any():
                combined_df.loc[status_mask, "prazo_limite"] = pd.NA
                status_series.loc[status_mask] = (
                    prazo_series.loc[status_mask].str.lower().map(status_map)
                )
            combined_df[status_col] = status_series

        if "tempo_excedido" in combined_df.columns:
            combined_df["tempo_excedido"] = combined_df["tempo_excedido"].apply(
                _normalize_tempo_excedido_value
            )

        logger.debug(f"Colunas renomeadas. Novas colunas: {list(combined_df.columns)}")

        # Normaliza os tipos de dados
        _check_cancel()
        combined_df = _normalize_datatypes(combined_df)

        # --- Sanitizacao Basica de Strings ---
        logger.debug("Iniciando strip/null-mask de strings...")
        for col in combined_df.columns:
            _check_cancel()
            # Verifica se a coluna é de tipo 'object' (pandas usa para strings e mixed types)
            if pd.api.types.is_object_dtype(combined_df[col]):
                cleaned = combined_df[col].astype("string").str.strip()
                null_like = cleaned.isna() | cleaned.isin(
                    ["", "nan", "None", "NaN", "<NA>"]
                )
                combined_df[col] = cleaned.mask(null_like, pd.NA)

                # Mantem o conteudo original no DB tanto quanto possivel;
                # sanitizacao agressiva continua sendo responsabilidade de exibicao.

        # --- VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS ---
        logger.debug("Validando campos obrigatórios...")

        # Filtrar registros com campos essenciais vazios
        before_validation = len(combined_df)

        # Remover registros completamente inválidos (sem SSA e sem descrição)
        numero_series = (
            combined_df["numero_ssa"]
            if "numero_ssa" in combined_df.columns
            else pd.Series(
                [pd.NA] * len(combined_df), index=combined_df.index, dtype="object"
            )
        )
        descricao_series = (
            combined_df["descricao_ssa"]
            if "descricao_ssa" in combined_df.columns
            else pd.Series(
                [pd.NA] * len(combined_df), index=combined_df.index, dtype="object"
            )
        )
        valid_mask = (numero_series.notna() & (numero_series != "")) | (
            descricao_series.notna() & (descricao_series != "")
        )

        captured_mask = pd.Series(
            combined_df.index.isin(captured_indices),
            index=combined_df.index,
            dtype=bool,
        )
        invalid_summary = _summarize_invalid_identity_rows(
            combined_df, ~valid_mask & ~captured_mask
        )
        invalid_summary["hierarchical_rows_captured"] = len(captured_indices)
        invalid_summary["hierarchical_records_captured"] = len(event_records)
        invalid_summary["hierarchical_rows_by_type"] = captured_by_type
        if early_empty_removed > 0:
            invalid_summary["empty_removed"] += early_empty_removed
            invalid_summary["total_removed"] += early_empty_removed
            invalid_summary["empty_removed_pre_identity_filter"] = early_empty_removed
        combined_df = combined_df[valid_mask].copy().reset_index(drop=True)
        combined_df.attrs["invalid_row_summary"] = invalid_summary
        combined_df.attrs["ssa_event_records"] = event_records
        combined_df.attrs["row_count_before_invalid_filter"] = (
            before_validation + early_empty_removed
        )

        if event_records:
            logger.info(
                "Extracao - %s: capturados %s registros hierarquicos (%s continuacoes)",
                base_name,
                len(event_records),
                len(captured_indices),
            )

        if invalid_summary.get("total_removed", 0) > 0:
            invalid_count = int(invalid_summary.get("total_removed", 0))
            payload_cols = invalid_summary.get("payload_columns_sample") or []
            payload_txt = (
                f" (colunas: {', '.join(payload_cols)})" if payload_cols else ""
            )
            logger.warning(
                "Extracao - %s: removidos %s registros invalidos sem identidade: %s vazios, %s com payload%s",
                base_name,
                invalid_count,
                invalid_summary.get("empty_removed", 0),
                invalid_summary.get("payload_removed", 0),
                payload_txt,
            )

        # Validar campos críticos e avisar sobre problemas
        if "numero_ssa" in combined_df.columns:
            empty_ssa = combined_df["numero_ssa"].isna() | (
                combined_df["numero_ssa"] == ""
            )
            if empty_ssa.sum() > 0:
                logger.warning(
                    "Extracao - %s: %s registros sem numero de SSA (mantidos por descricao valida)",
                    base_name,
                    int(empty_ssa.sum()),
                )

        if "semana_cadastro" in combined_df.columns:
            empty_week = (
                combined_df["semana_cadastro"].isna()
                | (combined_df["semana_cadastro"] == "")
                | (combined_df["semana_cadastro"] == "-")
            )
            if empty_week.sum() > 0:
                logger.warning(
                    "Extracao - %s: %s registros sem semana de cadastro",
                    base_name,
                    int(empty_week.sum()),
                )

        logger.info(
            "Extracao concluida para '%s': %s linhas validas, %s invalidos sem identidade",
            base_name,
            len(combined_df),
            int(invalid_summary.get("total_removed", 0)),
        )
        return combined_df

    except ExtractionError:
        raise
    except FileNotFoundError as e:
        logger.error("Arquivo '%s' nao encontrado.", file_path)
        raise ExtractionError(f"File not found: {base_name}") from e
    except pd.errors.ParserError as e:
        logger.error(
            "Erro ao ler '%s': problema ao analisar arquivo Excel: %s",
            file_path,
            e,
        )
        raise ExtractionError(f"Parser error reading Excel file: {base_name}") from e
    except Exception as e:
        logger.error(
            "Erro inesperado ao processar '%s': %s", file_path, e, exc_info=True
        )
        raise ExtractionError(
            f"Unexpected error processing Excel file: {base_name}"
        ) from e


def read_report(file_path: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Le um relatorio Excel e retorna um DataFrame normalizado e metadados simples.

    A leitura usa `import_excel_robust` como caminho unico de ingestao.

    Args:
        file_path: Caminho do arquivo .xlsx a ser lido.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: DataFrame resultante
        (vazio em caso de erro) e metadados com source_path e stats_dict.
    """
    if not os.path.exists(file_path):
        metadata: Dict[str, Any] = {
            "source_path": file_path,
            "stats_dict": {
                "status": "error",
                "error": f"File not found: {os.path.basename(file_path)}",
            },
        }
        logger.warning(
            "Falha em read_report para '%s': arquivo nao encontrado", file_path
        )
        return pd.DataFrame(), metadata

    try:
        df, stats_dict = import_excel_robust(file_path)
    except Exception as exc:
        logger.error(
            "Falha em read_report para '%s': %s", file_path, exc, exc_info=True
        )
        metadata = {
            "source_path": file_path,
            "stats_dict": {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            },
        }
        return pd.DataFrame(), metadata

    metadata = {
        "source_path": file_path,
        "stats_dict": stats_dict,
    }
    return df, metadata
