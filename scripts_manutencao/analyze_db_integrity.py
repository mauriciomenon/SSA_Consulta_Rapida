import sqlite3

import pandas as pd

from armazenamento.database_integrity import repair_database_if_needed as _core_repair_database_if_needed
from utils.robust_logging import get_robust_logger

TABLE_NAME = "ssa_table"
logger = get_robust_logger().get_logger(__name__, "maintenance")


def _query_core_metrics(
    conn: sqlite3.Connection,
    critical_fields: list[str],
) -> tuple[int, dict[str, int], int]:
    select_parts = [
        f"SUM(CASE WHEN {field} IS NULL OR {field} = '' OR {field} = '-' THEN 1 ELSE 0 END) AS {field}"
        for field in critical_fields
    ]
    query = f"""
    SELECT
        COUNT(*) AS total_records,
        {', '.join(select_parts)},
        SUM(
            CASE
                WHEN (numero_ssa IS NULL OR numero_ssa = '')
                 AND (situacao IS NULL OR situacao = '')
                 AND (descricao_ssa IS NULL OR descricao_ssa = '')
                THEN 1 ELSE 0
            END
        ) AS empty_records
    FROM {TABLE_NAME}
    """
    result_df = pd.read_sql_query(query, conn)
    if result_df.empty:
        return 0, {field: 0 for field in critical_fields}, 0
    row = result_df.iloc[0]
    total_records = int(row["total_records"] or 0)
    empty_counts = {field: int(row[field] or 0) for field in critical_fields}
    empty_records = int(row["empty_records"] or 0)
    return total_records, empty_counts, empty_records


def _query_duplicates(conn: sqlite3.Connection) -> tuple[pd.DataFrame, int]:
    duplicates_query = f"""
    WITH dupes AS (
        SELECT numero_ssa, COUNT(*) AS count
        FROM {TABLE_NAME}
        WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
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
    duplicates = pd.read_sql_query(duplicates_query, conn)
    total_duplicated = int(duplicates.iloc[0]["total_duplicated"]) if len(duplicates) > 0 else 0
    return duplicates, total_duplicated


def _log_duplicates(duplicates: pd.DataFrame, total_duplicated: int) -> None:
    if len(duplicates) > 0:
        logger.warning("ERR DUPLICATAS ENCONTRADAS:")
        logger.warning("   %s numeros de SSA duplicados", len(duplicates))
        logger.warning("   Top 10 mais duplicados:")
        for _, row in duplicates.iterrows():
            logger.warning("     SSA %s: %s copias", row["numero_ssa"], row["count"])
        logger.warning("   Total de registros duplicados para remocao: %s", f"{total_duplicated:,}")
        return
    logger.info("OK Nenhuma duplicata encontrada por numero_ssa")


def _table_has_column(conn: sqlite3.Connection, column_name: str) -> bool:
    table_info = pd.read_sql_query(f"PRAGMA table_info({TABLE_NAME})", conn)
    return column_name in set(table_info["name"].tolist())


def _log_import_dates(conn: sqlite3.Connection) -> None:
    if not _table_has_column(conn, "data_importacao"):
        logger.warning("WARN Campo data_importacao nao encontrado")
        return
    try:
        import_dates = pd.read_sql_query(
            f"""
            SELECT DATE(data_importacao) as date, COUNT(*) as count
            FROM {TABLE_NAME}
            WHERE data_importacao IS NOT NULL
            GROUP BY DATE(data_importacao)
            ORDER BY date DESC
            LIMIT 5
            """,
            conn,
        )
        if len(import_dates) > 0:
            logger.info("INFO IMPORTACOES RECENTES:")
            for _, row in import_dates.iterrows():
                logger.info("   %s: %s registros", row["date"], f"{row['count']:,}")
    except Exception as exc:
        logger.debug("DEBUG Detalhe da consulta data_importacao: %s", exc)
        logger.warning("WARN Campo data_importacao nao encontrado")


def _log_recommendations(has_duplicates: bool, total_duplicated: int) -> None:
    logger.info("FIX RECOMENDACOES:")
    if has_duplicates:
        logger.info("   1. Remover %s registros duplicados", f"{total_duplicated:,}")
    logger.info("   2. Implementar verificacao de duplicatas antes da insercao")
    logger.info("   3. Validar campos obrigatorios na importacao")
    logger.info("   4. Adicionar indices unicos para prevenir duplicatas futuras")


def verify_database_integrity():
    """Analisa a integridade do banco e identifica problemas."""

    conn = sqlite3.connect('data/ssas.db')

    logger.info("INFO ANALISE DE INTEGRIDADE DO BANCO DE DADOS")
    logger.info("=" * 60)

    critical_fields = [
        "numero_ssa",
        "situacao",
        "descricao_ssa",
        "localizacao_codigo",
        "setor_executor",
        "semana_cadastro",
    ]
    total_records, empty_counts, empty_records = _query_core_metrics(conn, critical_fields)
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
            logger.warning("   ERR %s: %s vazios (%.1f%%)", field, f"{empty_count:,}", percentage)
        else:
            logger.info("   OK %s: Todos preenchidos", field)

    if empty_records > 0:
        logger.warning("ERR REGISTROS VAZIOS: %s registros sem dados essenciais", f"{empty_records:,}")

    _log_import_dates(conn)

    conn.close()

    _log_recommendations(len(duplicates) > 0, total_duplicated)

    summary = {
        'total_records': int(total_records),
        'has_duplicates': len(duplicates) > 0,
        'duplicate_count': total_duplicated,
        'empty_fields': any_empty_fields or int(empty_records) > 0
    }
    summary["stats_dict"] = summary.copy()
    return summary


def analyze_database_integrity():
    """Backward-compatible alias for legacy callers."""
    return verify_database_integrity()


def repair_database_if_needed(report: dict[str, object] | None = None) -> dict[str, object]:
    """Run integrity-check + repair flow when issues are detected."""
    current_report = report or verify_database_integrity()
    needs_repair = bool(current_report.get("has_duplicates") or current_report.get("empty_fields"))
    repaired = False
    if needs_repair:
        repaired = _core_repair_database_if_needed(
            "data/ssas.db",
            schema_file="config/schema_unified.sql",
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
