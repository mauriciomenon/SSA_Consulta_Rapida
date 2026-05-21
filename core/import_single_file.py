"""Single-file Excel import implementation."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from utils.file_metadata import best_datetime_for_file

from core.import_errors import DatabaseError, ExtractionError, ImporterError

logger = logging.getLogger(__name__)

SOURCE_METADATA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("arquivo_origem", "TEXT"),
    ("data_arquivo_origem", "TEXT"),
    ("data_planilha", "TEXT"),
)


@dataclass(frozen=True, slots=True)
class ImportSingleFileServices:
    extract_data_from_excel: Callable[..., Any]
    extractor_error_type: type[Exception]
    validate_dataframe_before_insert: Callable[[Any, str], Dict[str, Any]]
    ensure_column_exists: Callable[[str, str, str, str], Any]
    insert_dataframe_with_smart_upsert: Callable[[Any, str, str], bool]


def ensure_source_metadata_columns(
    db_path: str,
    table_name: str,
    ensure_column_exists: Callable[[str, str, str, str], Any],
) -> None:
    for column_name, column_type in SOURCE_METADATA_COLUMNS:
        ensure_column_exists(db_path, table_name, column_name, column_type)


def _log_validation_violations(
    file_path: str,
    violations: list[dict[str, Any]],
) -> None:
    validation_rule_labels = {
        "duplicate_numero_ssa_exact": "Duplicidade exata no export",
        "duplicate_numero_ssa_conflict": "Duplicidade conflitante no export",
    }
    for violation in violations:
        rule = str(violation.get("rule") or "")
        count = violation.get("count")
        severity = violation.get("severity", "warning")
        sample = violation.get("sample_ssa") or []
        sample_txt = f" (ex.: {', '.join(sample)})" if sample else ""
        rule_txt = str(rule or "regra_desconhecida").replace("_", " ")
        default_prefix = (
            "Erro de validacao"
            if severity == "error"
            else "Aviso de validacao"
        )
        rule_label = validation_rule_labels.get(
            rule,
            f"{default_prefix} [{rule_txt}]",
        )
        message = f"{rule_label} atingiu {count} linha(s){sample_txt}"
        if severity == "error":
            logger.error(
                "Validacao - %s: %s", os.path.basename(file_path), message
            )
        else:
            logger.warning(
                "Validacao - %s: %s", os.path.basename(file_path), message
            )


def _drop_required_invalid_rows(
    df: Any,
    file_path: str,
    invalid_by_column: dict[str, Any],
) -> tuple[Any, int]:
    critical_columns = {"numero_ssa", "data_cadastro"}
    rows_to_drop: set[int] = set()
    for column, indices in invalid_by_column.items():
        if column in critical_columns:
            rows_to_drop.update(indices)

    if not rows_to_drop:
        return df, 0

    drop_indices = list(rows_to_drop)
    sample_indices = drop_indices[:5]
    if "numero_ssa" in df.columns:
        sample_ssas = df.loc[sample_indices, "numero_ssa"].astype(str).tolist()
    else:
        sample_ssas = [str(idx) for idx in sample_indices]
    logger.error(
        "Removendo %s linha(s) com dados obrigatorios ausentes em '%s' (amostra: %s)",
        len(rows_to_drop),
        os.path.basename(file_path),
        ", ".join(sample_ssas),
    )
    return df.drop(index=drop_indices), len(rows_to_drop)


def _add_source_metadata_columns(df: Any, file_path: str) -> Any:
    basename = os.path.basename(file_path)
    if "arquivo_origem" not in df.columns:
        df["arquivo_origem"] = basename
    else:
        df["arquivo_origem"] = df["arquivo_origem"].fillna(basename)
    needs_file_dt_text = "data_arquivo_origem" not in df.columns or bool(
        df["data_arquivo_origem"].isna().any()
    )
    needs_file_dt_iso = "data_planilha" not in df.columns or bool(
        df["data_planilha"].isna().any()
    )
    best_file_dt = (
        best_datetime_for_file(file_path)
        if needs_file_dt_text or needs_file_dt_iso
        else None
    )
    file_dt_text = (
        best_file_dt.strftime("%Y-%m-%d %H:%M:%S")
        if best_file_dt is not None
        else None
    )
    file_dt_iso = (
        best_file_dt.isoformat(timespec="seconds")
        if best_file_dt is not None
        else None
    )
    if "data_arquivo_origem" not in df.columns:
        df["data_arquivo_origem"] = file_dt_text
    else:
        df["data_arquivo_origem"] = df["data_arquivo_origem"].fillna(file_dt_text)
    if "data_planilha" not in df.columns:
        df["data_planilha"] = file_dt_iso
    else:
        df["data_planilha"] = df["data_planilha"].fillna(file_dt_iso)
    return df


def import_single_file(
    file_path: str,
    db_path: str,
    table_name: str,
    should_cancel: Optional[Callable[[], bool]] = None,
    _metrics_out: Optional[Dict[str, Any]] = None,
    *,
    services: ImportSingleFileServices,
    metadata_columns_ready: bool = False,
) -> tuple[bool, int]:
    """
    Importa um unico arquivo Excel para o banco de dados.

    Args:
        file_path (str): Caminho completo para o arquivo Excel.
        db_path (str): Caminho para o banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.
        should_cancel (Optional[Callable[[], bool]]): Callback consultivo para cancelar a operacao.

    Returns:
        tuple[bool, int]: (sucesso, numero_de_registros_processados)

    Raises:
        ExtractionError: Se houver falha na extracao.
        DatabaseError: Se houver falha na insercao no DB.
    """
    logger.info("Iniciando importacao de '%s'...", file_path)
    metrics: Dict[str, Any] = {"file": os.path.basename(file_path)}
    try:
        if not os.path.isfile(file_path):
            raise ExtractionError(
                f"Arquivo de importacao nao encontrado: {file_path}",
                error_code="MISSING_FILE",
            )
        extraction_started = time.perf_counter()
        df = services.extract_data_from_excel(file_path, should_cancel=should_cancel)
        extraction_duration = time.perf_counter() - extraction_started
        if df is None:
            raise ExtractionError(f"Extractor retornou None para '{file_path}'")
        invalid_row_summary_raw = df.attrs.get("invalid_row_summary")
        invalid_row_summary = (
            dict(invalid_row_summary_raw)
            if isinstance(invalid_row_summary_raw, dict)
            else {}
        )
        row_count_before_invalid_filter_raw = df.attrs.get(
            "row_count_before_invalid_filter"
        )
        row_count_before_invalid_filter = (
            int(row_count_before_invalid_filter_raw)
            if isinstance(row_count_before_invalid_filter_raw, int)
            else int(len(df))
        )
        metrics["durations"] = {"extraction_seconds": round(extraction_duration, 3)}
        metrics["counts"] = {
            "rows_extracted": int(len(df)),
            "rows_before_invalid_filter": row_count_before_invalid_filter,
            "rows_removed_invalid_identity": int(
                invalid_row_summary.get("total_removed", 0)
            ),
            "rows_ready_for_insert": 0,
            "rows_inserted": 0,
        }
        metrics["invalid_identity"] = invalid_row_summary
        metrics["invalid_identity_tracked"] = bool(invalid_row_summary)
        if should_cancel and should_cancel():
            raise ExtractionError(
                "operation cancelled", error_code="OPERATION_CANCELLED"
            )
        if not df.empty:
            if should_cancel and should_cancel():
                raise ExtractionError(
                    "operation cancelled", error_code="OPERATION_CANCELLED"
                )
            # NOVA: Validar dados antes da insercao
            logger.info("Validando dados extraidos de '%s'...", file_path)
            validation_started = time.perf_counter()
            validation_report = services.validate_dataframe_before_insert(
                df, table_name
            )

            _log_validation_violations(
                file_path,
                list(validation_report.get("violations", [])),
            )

            invalid_by_column = validation_report.get("invalid_by_column", {})
            df, dropped_required_rows = _drop_required_invalid_rows(
                df, file_path, invalid_by_column
            )
            metrics["durations"]["validation_seconds"] = round(
                time.perf_counter() - validation_started, 3
            )
            metrics["counts"]["rows_ready_for_insert"] = int(len(df))
            metrics["counts"]["rows_removed_required_validation"] = int(
                dropped_required_rows
            )

            if df.empty:
                logger.error(
                    "Nenhuma linha valida restou apos validacao de '%s'; nada sera inserido.",
                    os.path.basename(file_path),
                )
                return False, 0

            critical_missing_rules = {
                "missing_column_numero_ssa",
                "missing_column_data_cadastro",
            }
            has_critical_missing_columns = any(
                violation.get("rule") in critical_missing_rules
                and violation.get("severity") == "error"
                for violation in validation_report.get("violations", [])
            )

            # Se ha problemas criticos, pode escolher entre falhar ou continuar
            if not validation_report.get("is_valid", False):
                critical_issues = list(validation_report.get("issues", []))
                critical_summary = "; ".join(
                    str(issue) for issue in critical_issues[:5]
                )
                logger.error(
                    "Validacao critica em '%s': %s",
                    os.path.basename(file_path),
                    critical_summary or "sem detalhe",
                )
                if has_critical_missing_columns:
                    raise ExtractionError(
                        critical_summary
                        or "Colunas obrigatorias ausentes no DataFrame",
                        error_code="MISSING_REQUIRED_COLUMNS",
                    )
                logger.warning(
                    "Validacao critica em '%s': seguindo com insercao por politica atual.",
                    os.path.basename(file_path),
                )
            else:
                logger.info(
                    "Validacao concluida para '%s': %s linhas prontas para insercao",
                    os.path.basename(file_path),
                    len(df),
                )

            # Garante coluna de rastreio de origem no banco
            if not metadata_columns_ready:
                ensure_source_metadata_columns(
                    db_path, table_name, services.ensure_column_exists
                )
            df = _add_source_metadata_columns(df, file_path)

            # Conta registros antes de inserir
            record_count = len(df)
            insertion_started = time.perf_counter()

            # CORRECAO CRITICA: Usar smart_upsert para evitar duplicatas
            if should_cancel and should_cancel():
                raise ExtractionError(
                    "operation cancelled", error_code="OPERATION_CANCELLED"
                )
            success = services.insert_dataframe_with_smart_upsert(
                df, db_path, table_name
            )
            metrics["durations"]["insert_seconds"] = round(
                time.perf_counter() - insertion_started, 3
            )
            metrics["counts"]["rows_inserted"] = int(record_count if success else 0)
            if success:
                counts = metrics.get("counts", {})
                logger.info(
                    "Resumo do arquivo '%s': extracao=%ss, validacao=%ss, insercao=%ss, linhas=%s, invalidos_sem_identidade=%s, prontas=%s",
                    os.path.basename(file_path),
                    metrics["durations"].get("extraction_seconds", 0),
                    metrics["durations"].get("validation_seconds", 0),
                    metrics["durations"].get("insert_seconds", 0),
                    counts.get("rows_extracted", 0),
                    counts.get("rows_removed_invalid_identity", 0),
                    counts.get("rows_ready_for_insert", 0),
                )
                logger.info(
                    "Importacao finalizada para '%s': inseridas=%s, removidas_validacao=%s, invalidos_sem_identidade=%s",
                    os.path.basename(file_path),
                    counts.get("rows_inserted", 0),
                    counts.get("rows_removed_required_validation", 0),
                    counts.get("rows_removed_invalid_identity", 0),
                )
                return True, record_count
            else:
                logger.error(
                    "Falha ao inserir dados validados de '%s' no banco de dados.",
                    os.path.basename(file_path),
                )
                raise DatabaseError(f"Erro ao inserir dados do arquivo {file_path}")
        else:
            logger.warning(
                "Arquivo '%s' sem linhas validas apos extracao; importacao ignorada.",
                os.path.basename(file_path),
            )
            return True, 0  # Nao e um erro critico, apenas nao ha dados
    except services.extractor_error_type as e:
        # Normalize extractor error type into core.app_logic.ExtractionError
        message = str(e).strip() or "Erro de extracao sem detalhe"
        raise ExtractionError(
            message,
            error_code=getattr(e, "error_code", None),
        ) from e
    except ExtractionError:
        raise
    except DatabaseError:
        raise
    except ImporterError:
        raise
    except (RuntimeError, TypeError, ValueError) as e:
        error_type = type(e).__name__
        logger.exception(
            "Erro inesperado (%s) ao importar '%s': %s",
            error_type,
            file_path,
            e,
        )
        raise ExtractionError(f"{error_type} ao importar {file_path}: {e}") from e
    finally:
        if _metrics_out is not None:
            _metrics_out.update(metrics)
