import sqlite3
from pathlib import Path
from typing import Union

import pandas as pd

from armazenamento.database_integrity import (
    repair_database_if_needed as _core_repair_database_if_needed,
)
from utils.robust_logging import get_robust_logger

TABLE_NAME = "ssa_table"
CORE_METRIC_FIELDS = (
    "numero_ssa",
    "situacao",
    "descricao_ssa",
    "localizacao_codigo",
    "setor_executor",
    "semana_cadastro",
)
REQUIRED_EMPTY_RECORD_FIELDS = (
    "numero_ssa",
    "situacao",
    "descricao_ssa",
)
logger = get_robust_logger().get_logger(__name__, "maintenance")

_CORE_METRICS_QUERY_TEMPLATE = """
    SELECT
        COUNT(*) AS total_records,
        __METRIC_SELECTS__,
        SUM(
            CASE
                WHEN (__CORE_EMPTY_RECORD_CLAUSE__)
                THEN 1 ELSE 0
            END
        ) AS empty_records
    FROM __TABLE_NAME__
"""

_DUPLICATES_QUERY_TEMPLATE = """
    WITH dupes AS (
        SELECT numero_ssa, COUNT(*) AS count
        FROM __TABLE_NAME__
        WHERE NOT (__NUMERO_SSA_INVALID_CLAUSE__)
        GROUP BY numero_ssa
        HAVING COUNT(*) > 1
    )
    SELECT
        numero_ssa,
        count,
        SUM(count - 1) OVER () AS total_duplicated
    FROM dupes
    ORDER BY count DESC
    LIMIT 10
"""

_IMPORT_DATES_QUERY_TEMPLATE = """
    SELECT DATE(data_importacao) as date, COUNT(*) as count
    FROM __TABLE_NAME__
    WHERE data_importacao IS NOT NULL
    GROUP BY DATE(data_importacao)
    ORDER BY date DESC
    LIMIT 5
"""


def _get_project_root() -> Path:
    """Resolve a raiz do projeto para scripts executados fora do cwd do repo."""
    return Path(__file__).resolve().parent.parent


def _get_runtime_root() -> Path:
    cwd_root = Path.cwd()
    if (cwd_root / "data" / "ssas.db").exists():
        return cwd_root
    return _get_project_root()


def _get_db_path() -> Path:
    return _get_runtime_root() / "data" / "ssas.db"


def _get_schema_path() -> Path:
    runtime_schema = _get_runtime_root() / "config" / "schema_unified.sql"
    if runtime_schema.exists():
        return runtime_schema
    return _get_project_root() / "config" / "schema_unified.sql"


def _build_empty_metric_select(field_name: str) -> str:
    return ("SUM(CASE WHEN {invalid_clause} THEN 1 ELSE 0 END) AS {field}").format(
        field=field_name, invalid_clause=_build_invalid_value_clause(field_name)
    )


def _build_invalid_value_clause(field_name: str) -> str:
    return f"{field_name} IS NULL OR {field_name} = '' OR {field_name} = '-'"


def _build_query(template: str) -> str:
    return template.replace("__TABLE_NAME__", TABLE_NAME)


_CORE_METRICS_QUERY = _build_query(
    _CORE_METRICS_QUERY_TEMPLATE.replace(
        "__METRIC_SELECTS__",
        ",\n        ".join(
            _build_empty_metric_select(field) for field in CORE_METRIC_FIELDS
        ),
    ).replace(
        "__CORE_EMPTY_RECORD_CLAUSE__",
        " AND ".join(
            f"({_build_invalid_value_clause(field)})"
            for field in REQUIRED_EMPTY_RECORD_FIELDS
        ),
    ),
)

_DUPLICATES_QUERY = _build_query(
    _DUPLICATES_QUERY_TEMPLATE.replace(
        "__NUMERO_SSA_INVALID_CLAUSE__",
        _build_invalid_value_clause("numero_ssa"),
    )
)

_IMPORT_DATES_QUERY = _build_query(_IMPORT_DATES_QUERY_TEMPLATE)


def _coerce_count(value: Union[int, float, str, None]) -> int:
    if value is None:
        return 0
    if isinstance(value, float) and pd.isna(value):
        return 0
    return int(value)


def _query_core_metrics(conn: sqlite3.Connection) -> tuple[int, dict[str, int], int]:
    result_df = pd.read_sql_query(_CORE_METRICS_QUERY, conn)
    if result_df.empty:
        return 0, {field: 0 for field in CORE_METRIC_FIELDS}, 0

    row = result_df.iloc[0]
    total_records = _coerce_count(row["total_records"])
    empty_counts = {field: _coerce_count(row[field]) for field in CORE_METRIC_FIELDS}
    empty_records = _coerce_count(row["empty_records"])
    return total_records, empty_counts, empty_records


def _query_duplicates(conn: sqlite3.Connection) -> tuple[pd.DataFrame, int]:
    duplicates = pd.read_sql_query(_DUPLICATES_QUERY, conn)
    total_duplicated = (
        int(duplicates.iloc[0]["total_duplicated"]) if len(duplicates) > 0 else 0
    )
    return duplicates, total_duplicated


def _log_duplicates(duplicates: pd.DataFrame, total_duplicated: int) -> None:
    if len(duplicates) > 0:
        logger.warning("ERR DUPLICATAS ENCONTRADAS:")
        logger.warning("   Top 10 numeros de SSA mais duplicados:")
        for _, row in duplicates.iterrows():
            logger.warning("     SSA %s: %s copias", row["numero_ssa"], row["count"])
        logger.warning(
            "   Total de registros duplicados para remocao: %s", f"{total_duplicated:,}"
        )
        return
    logger.info("OK Nenhuma duplicata encontrada por numero_ssa")


def _table_has_column(conn: sqlite3.Connection, column_name: str) -> bool:
    table_info = pd.read_sql_query(f"PRAGMA table_info({TABLE_NAME})", conn)
    return column_name in set(table_info["name"].tolist())


def _query_import_dates(conn: sqlite3.Connection) -> pd.DataFrame:
    if not _table_has_column(conn, "data_importacao"):
        return pd.DataFrame(columns=["date", "count"])
    return pd.read_sql_query(
        _IMPORT_DATES_QUERY,
        conn,
    )


def _log_import_dates(import_dates: pd.DataFrame) -> None:
    if len(import_dates) <= 0:
        return
    logger.info("INFO IMPORTACOES RECENTES:")
    for _, row in import_dates.iterrows():
        logger.info("   %s: %s registros", row["date"], f"{row['count']:,}")


def _log_recommendations(has_duplicates: bool, total_duplicated: int) -> None:
    logger.info("FIX RECOMENDACOES:")
    if has_duplicates:
        logger.info("   1. Remover %s registros duplicados", f"{total_duplicated:,}")
    logger.info("   2. Implementar verificacao de duplicatas antes da insercao")
    logger.info("   3. Validar campos obrigatorios na importacao")
    logger.info("   4. Adicionar indices unicos para prevenir duplicatas futuras")


def verify_database_integrity():
    """Analisa a integridade do banco e identifica problemas."""

    conn = sqlite3.connect(_get_db_path())

    logger.info("INFO ANALISE DE INTEGRIDADE DO BANCO DE DADOS")
    logger.info("=" * 60)

    total_records, empty_counts, empty_records = _query_core_metrics(conn)
    logger.info("INFO Total de registros: %s", f"{total_records:,}")

    duplicates, total_duplicated = _query_duplicates(conn)
    _log_duplicates(duplicates, total_duplicated)

    # 3. Verificar campos vazios críticos
    logger.info("INFO VERIFICACAO DE CAMPOS OBRIGATORIOS:")
    any_empty_fields = False
    for field, empty_count in empty_counts.items():
        if empty_count > 0:
            any_empty_fields = True
            percentage = (empty_count / total_records * 100) if total_records else 0.0
            logger.warning(
                "   ERR %s: %s vazios (%.1f%%)", field, f"{empty_count:,}", percentage
            )
        else:
            logger.info("   OK %s: Todos preenchidos", field)

    if empty_records > 0:
        logger.warning(
            "ERR REGISTROS VAZIOS: %s registros sem dados essenciais",
            f"{empty_records:,}",
        )

    import_dates = pd.DataFrame(columns=["date", "count"])
    try:
        import_dates = _query_import_dates(conn)
        _log_import_dates(import_dates)
    except Exception as exc:
        logger.debug("DEBUG Detalhe da consulta data_importacao: %s", exc)
        logger.warning("WARN Falha ao consultar data_importacao: %s", exc)

    conn.close()

    _log_recommendations(len(duplicates) > 0, total_duplicated)

    summary: dict[str, object] = {
        "total_records": int(total_records),
        "has_duplicates": len(duplicates) > 0,
        "duplicate_count": total_duplicated,
        "empty_fields": any_empty_fields or int(empty_records) > 0,
        "recent_import_dates": import_dates.to_dict(orient="records"),
    }
    summary["stats_dict"] = summary.copy()
    return summary


def analyze_database_integrity():
    """Backward-compatible alias for legacy callers."""
    return verify_database_integrity()


def repair_database_if_needed(
    report: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run integrity-check + repair flow when issues are detected."""
    current_report = report or verify_database_integrity()
    needs_repair = bool(
        current_report.get("has_duplicates") or current_report.get("empty_fields")
    )
    repaired = False
    if needs_repair:
        repaired = _core_repair_database_if_needed(
            str(_get_db_path()),
            schema_file=str(_get_schema_path()),
            table_name=TABLE_NAME,
        )
    return {
        "needs_repair": needs_repair,
        "repaired": repaired,
        "strategy": "auto_repair_on_demand",
    }


if __name__ == "__main__":
    verify_database_integrity()
    logger.info("=" * 60)
    logger.info("OK Analise concluida!")
