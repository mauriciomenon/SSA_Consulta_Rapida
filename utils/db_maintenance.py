# utils/db_maintenance.py
"""
Sistema de manutencao e otimizacao do banco de dados SSA.

Oferece funcionalidades para:
- Backup automatico
- Analise de sanidade dos dados
- Limpeza de colunas duplicadas
- Migracao segura de dados
"""

import os
import shutil
import sqlite3
import uuid
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from shared.date_utils import parse_any_date
from shared.db_names import CANONICAL_SSA_TABLE, LEGACY_SSA_TABLE_ALIASES
from shared.numero_ssa import normalize_strict
from utils.db_maintenance_report import render_database_analysis_report
from utils.path_safety import ensure_path_is_allowed
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "maintenance")

LEGACY_CONCEPT_COLUMN_MAPPING = {
    "numero_ssa": ["N\u00famero da SSA", "numero_ssa"],
    "semana_cadastro": ["Semana de Cadastro", "semana_cadastro"],
    "descricao_execucao": [
        "Descri\u00e7\u00e3o Execu\u00e7\u00e3o",
        "descricao_execucao",
    ],
    "responsavel_programacao": [
        "Respons\u00e1vel na Programa\u00e7\u00e3o",
        "responsavel_programacao",
    ],
    "responsavel_execucao": [
        "Respons\u00e1vel na Execu\u00e7\u00e3o",
        "responsavel_execucao",
    ],
    "grau_prioridade_emissao": [
        "Grau de Prioridade Emiss\u00e3o",
        "grau_prioridade_emissao",
    ],
    "grau_prioridade_planejamento": [
        "Grau de Prioridade Planejamento",
        "grau_prioridade_planejamento",
    ],
}

PENDING_MIGRATION_CONDITION = (
    "({target} IS NULL OR TRIM(CAST({target} AS TEXT)) = '') "
    "AND ({source} IS NOT NULL AND TRIM(CAST({source} AS TEXT)) != '')"
)


def _quote_sqlite_identifier(identifier: str) -> str:
    """Escapa identificador SQLite vindo do schema local."""
    safe_identifier = str(identifier)
    if "\x00" in safe_identifier:
        raise ValueError(f"Identificador SQLite invalido: {identifier!r}")
    return f'"{safe_identifier.replace(chr(34), chr(34) * 2)}"'


def _resolve_maintenance_table(
    conn: sqlite3.Connection,
    *,
    require_table: bool = False,
) -> str:
    """Resolve an SSA table or read-only view for maintenance operations."""
    candidate_names = (CANONICAL_SSA_TABLE, *LEGACY_SSA_TABLE_ALIASES)
    placeholders = ", ".join("?" for _name in candidate_names)
    rows = conn.execute(  # nosemgrep
        f"SELECT name, type FROM sqlite_master WHERE name IN ({placeholders})",  # nosec B608
        candidate_names,
    ).fetchall()
    objects = {str(name): str(object_type) for name, object_type in rows}
    if objects.get(CANONICAL_SSA_TABLE) == "table":
        return CANONICAL_SSA_TABLE
    for alias in LEGACY_SSA_TABLE_ALIASES:
        if objects.get(alias) == "table":
            return alias
    if not require_table:
        if objects.get(CANONICAL_SSA_TABLE) == "view":
            return CANONICAL_SSA_TABLE
        for view_alias in LEGACY_SSA_TABLE_ALIASES:
            if objects.get(view_alias) == "view":
                return view_alias
    raise DatabaseMaintenanceError("Tabela SSA nao encontrada para manutencao")


class DatabaseMaintenanceError(Exception):
    """Erro durante operacoes de manutencao do banco de dados."""

    pass


class DatabaseAnalyzer:
    """Analisa a estrutura e integridade dos dados no banco."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_backup(self, backup_dir: str = "data/backups") -> str:
        """Cria backup do banco de dados com timestamp."""
        if not os.path.exists(self.db_path):
            raise DatabaseMaintenanceError(
                f"Banco de dados nao encontrado: {self.db_path}"
            )

        backup_dir_path = ensure_path_is_allowed(
            backup_dir,
            must_exist=False,
            expect_directory=True,
        )
        backup_dir_path.mkdir(parents=True, exist_ok=True)

        # Nome do backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        db_name = Path(self.db_path).stem
        backup_filename = f"{db_name}_backup_{timestamp}_{uuid.uuid4().hex[:8]}.db"
        backup_path = str(backup_dir_path / backup_filename)

        try:
            with closing(sqlite3.connect(self.db_path)) as source_conn:
                with closing(sqlite3.connect(backup_path)) as backup_conn:
                    source_conn.backup(backup_conn, pages=1000)
            try:
                shutil.copystat(self.db_path, backup_path)
            except OSError as exc:
                logger.warning("Backup criado sem preservar metadata: %s", exc)
            logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            raise DatabaseMaintenanceError(f"Falha ao criar backup: {e}")

    def analyze_table_structure(self) -> Dict[str, Any]:
        """Analisa a estrutura da tabela identificando duplicacoes."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                table_name = _resolve_maintenance_table(conn)
                quoted_table = _quote_sqlite_identifier(table_name)

                # Obter informacoes das colunas
                cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                    f"PRAGMA table_info({quoted_table})"
                )
                columns_info = cursor.fetchall()

                column_counts = self._count_populated_columns(
                    cursor, columns_info, quoted_table
                )

                # Identificar duplicacoes potenciais
                duplicated_groups = self._identify_duplicate_columns(
                    columns_info, column_counts
                )

                return {
                    "total_columns": len(columns_info),
                    "columns_info": columns_info,
                    "column_counts": column_counts,
                    "duplicated_groups": duplicated_groups,
                }

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro ao analisar estrutura: {e}")

    def _count_populated_columns(
        self,
        cursor: sqlite3.Cursor,
        columns_info: List[Tuple],
        quoted_table: str,
    ) -> Dict[str, int]:
        column_names = [col_info[1] for col_info in columns_info]
        if not column_names:
            return {}

        select_exprs = [
            "SUM(CASE WHEN {column} IS NOT NULL "
            "AND TRIM(CAST({column} AS TEXT)) != '' THEN 1 ELSE 0 END)".format(
                column=_quote_sqlite_identifier(col_name)
            )
            for col_name in column_names
        ]
        cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            f"SELECT {', '.join(select_exprs)} FROM {quoted_table}"  # nosec B608
        )
        counts = cursor.fetchone() or []
        return {
            col_name: int(count or 0)
            for col_name, count in zip(column_names, counts, strict=True)
        }

    def _identify_duplicate_columns(
        self, columns_info: List[Tuple], column_counts: Dict[str, int]
    ) -> Dict[str, List[Dict]]:
        """Identifica grupos de colunas duplicadas baseado em nomes similares."""
        groups = {}

        # Mapear colunas por conceito basico.
        for concept, potential_names in LEGACY_CONCEPT_COLUMN_MAPPING.items():
            found_columns = []
            legacy_names = set(potential_names[:-1])
            target_name = potential_names[-1]
            for col_info in columns_info:
                col_name = col_info[1]
                if col_name in potential_names:
                    found_columns.append(
                        {
                            "name": col_name,
                            "type": col_info[2],
                            "count": column_counts.get(col_name, 0),
                            "is_legacy": col_name in legacy_names,
                            "is_target": col_name == target_name,
                        }
                    )

            if len(found_columns) > 1:
                groups[concept] = sorted(
                    found_columns, key=lambda x: x["count"], reverse=True
                )

        return groups

    def _coalesced_numero_series(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.Series | None, str | None]:
        numero_cols = LEGACY_CONCEPT_COLUMN_MAPPING["numero_ssa"]
        target_col = numero_cols[-1]
        present_cols = [col for col in numero_cols if col in df.columns]
        if not present_cols:
            return None, None

        numero_col = target_col if target_col in present_cols else present_cols[0]
        priority_cols = (
            [target_col] + [col for col in present_cols if col != target_col]
            if target_col in present_cols
            else present_cols
        )
        numero_values = df[priority_cols]
        numero_series = numero_values.bfill(axis=1).iloc[:, 0]
        return numero_series, numero_col

    def _check_numero_ssa(
        self,
        df: pd.DataFrame,
        issues: Dict[str, Any],
    ) -> tuple[str | None, pd.Series | None]:
        numero_series, numero_col = self._coalesced_numero_series(df)
        if numero_series is None:
            return None, None

        missing_numero = df[numero_series.isna()]
        issues["missing_numero_ssa"].extend(missing_numero.index.tolist())

        return numero_col, numero_series

    def _check_missing_fields(self, df: pd.DataFrame, issues: Dict[str, Any]) -> None:
        for col in ["descricao_ssa"]:
            if col in df.columns:
                missing_desc = df[df[col].isna()]
                issues["missing_descricao"].extend(missing_desc.index.tolist())

        for col in ["setor_emissor"]:
            if col in df.columns:
                missing_emissor = df[df[col].isna()]
                issues["missing_area_emissora"].extend(missing_emissor.index.tolist())

        location_cols = [
            col
            for col in ["localizacao_codigo", "descricao_localizacao"]
            if col in df.columns
        ]
        if location_cols:
            location_values = df[location_cols]
            missing_loc = df[location_values.isna().all(axis=1)]
            issues["missing_localizacao"].extend(missing_loc.index.tolist())

    def _check_invalid_dates(self, df: pd.DataFrame, issues: Dict[str, Any]) -> None:
        for col in ["data_cadastro"]:
            if col in df.columns:
                try:
                    series = df[col]
                    parsed_dates = series.map(parse_any_date)
                except Exception as exc:
                    logger.warning("Falha ao validar datas em '%s': %s", col, exc)
                    continue
                invalid_dates = df[
                    parsed_dates.isna() & series.notna() & (series != "")
                ]
                issues["invalid_dates"].extend(invalid_dates.index.tolist())

    def _check_empty_records(
        self,
        df: pd.DataFrame,
        issues: Dict[str, Any],
        numero_col: str | None,
    ) -> None:
        numero_cols = [
            col for col in LEGACY_CONCEPT_COLUMN_MAPPING["numero_ssa"] if col in df.columns
        ]
        essential_groups = []
        if numero_cols:
            essential_groups.append(numero_cols)
        elif numero_col and numero_col in df.columns:
            essential_groups.append([numero_col])
        essential_groups.extend(
            [col] for col in ["descricao_ssa", "setor_emissor"] if col in df.columns
        )
        if not essential_groups:
            return

        group_missing_masks = []
        for columns in essential_groups:
            group_missing_masks.append(df[columns].isna().all(axis=1))
        empty_mask = pd.concat(group_missing_masks, axis=1).all(axis=1)
        issues["empty_records"].extend(df[empty_mask].index.tolist())

    def _build_sanity_summary(self, issues: Dict[str, Any]) -> Dict[str, int]:
        return {
            "missing_numero_ssa": len(issues["missing_numero_ssa"]),
            "missing_descricao": len(issues["missing_descricao"]),
            "missing_area_emissora": len(issues["missing_area_emissora"]),
            "missing_localizacao": len(issues["missing_localizacao"]),
            "duplicate_numbers": sum(
                int(count) for count in issues["duplicate_numbers"].values()
            ),
            "invalid_dates": len(issues["invalid_dates"]),
            "empty_records": len(issues["empty_records"]),
        }

    def perform_sanity_check(self) -> Dict[str, Any]:
        """Executa verificacao de sanidade dos dados."""
        issues = {
            "missing_numero_ssa": [],
            "missing_descricao": [],
            "missing_area_emissora": [],
            "missing_localizacao": [],
            "duplicate_numbers": {},
            "invalid_dates": [],
            "empty_records": [],
        }

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                table_name = _resolve_maintenance_table(conn)
                quoted_table = _quote_sqlite_identifier(table_name)
                chunks = pd.read_sql_query(
                    f"SELECT * FROM {quoted_table}",  # nosec B608 # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
                    conn,
                    chunksize=5000,
                )

                total_records = 0
                number_counts: Counter[str] = Counter()
                for df in chunks:
                    if df.empty:
                        continue
                    df.index = range(total_records, total_records + len(df))
                    normalized_df = df.replace(r"^\s*$", pd.NA, regex=True)
                    total_records += len(df)

                    numero_col, numero_series = self._check_numero_ssa(
                        normalized_df,
                        issues,
                    )
                    if numero_series is not None:
                        normalized_numbers = numero_series.map(normalize_strict).dropna()
                        number_counts.update(
                            str(value) for value in normalized_numbers
                        )
                    self._check_missing_fields(normalized_df, issues)
                    self._check_invalid_dates(normalized_df, issues)
                    self._check_empty_records(normalized_df, issues, numero_col)

                if total_records == 0:
                    return {
                        "total_records": 0,
                        "issues": issues,
                        "summary": self._build_sanity_summary(issues),
                    }

                issues["duplicate_numbers"] = {
                    number: count for number, count in number_counts.items() if count > 1
                }

                return {
                    "total_records": total_records,
                    "issues": issues,
                    "summary": self._build_sanity_summary(issues),
                }

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro na verificacao de sanidade: {e}")


class DatabaseMigrator:
    """Executa migracao segura de dados entre esquemas."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.analyzer = DatabaseAnalyzer(db_path)

    def migrate_duplicate_columns(self, dry_run: bool = True) -> Dict[str, Any]:
        """Migra dados de colunas duplicadas para versoes padronizadas."""
        if dry_run:
            logger.info("Executando migracao em modo dry-run (sem alteracoes)")

        backup_path = None
        if not dry_run:
            # Criar backup somente antes de alteracao real.
            backup_path = self.analyzer.create_backup()

        structure = self.analyzer.analyze_table_structure()
        duplicated_groups = structure.get("duplicated_groups", {})

        migration_plan = []

        with closing(sqlite3.connect(self.db_path)) as conn:
            table_name = _resolve_maintenance_table(conn, require_table=True)
            quoted_table = _quote_sqlite_identifier(table_name)
            for concept, columns in duplicated_groups.items():
                if len(columns) < 2:
                    continue

                normalized_cols = [col for col in columns if not col.get("is_legacy")]
                legacy_cols = [col for col in columns if col.get("is_legacy")]
                if not normalized_cols or not legacy_cols:
                    continue

                target_col = next(
                    (col for col in normalized_cols if col.get("is_target")),
                    normalized_cols[0],
                )
                migration_sources = [
                    source_col
                    for source_col in legacy_cols
                    if source_col["count"] > 0
                    and source_col["name"] != target_col["name"]
                ]
                pending_counts = self._count_pending_migration_records(
                    conn,
                    [source_col["name"] for source_col in migration_sources],
                    target_col["name"],
                    quoted_table,
                )

                # Migrar somente de coluna legado para coluna normalizada.
                for source_col in migration_sources:
                    records_to_migrate = pending_counts.get(source_col["name"], 0)
                    if records_to_migrate <= 0:
                        continue
                    migration_plan.append(
                        {
                            "concept": concept,
                            "source": source_col["name"],
                            "target": target_col["name"],
                            "records_to_migrate": records_to_migrate,
                        }
                    )

        migration_stats = {
            "updated_rows": 0,
            "skipped_invalid_records": 0,
            "skipped_invalid_numero_ssa": 0,
            "migrations": [],
        }
        if not dry_run:
            migration_stats = self._execute_migration(migration_plan)

        return {
            "backup_created": backup_path,
            "migration_plan": migration_plan,
            "migration_stats": migration_stats,
            "dry_run": dry_run,
        }

    def _count_pending_migration_records(
        self,
        conn: sqlite3.Connection,
        sources: List[str],
        target: str,
        quoted_table: str,
    ) -> Dict[str, int]:
        if not sources:
            return {}
        quoted_target = _quote_sqlite_identifier(target)
        count_exprs = []
        for index, source in enumerate(sources):
            quoted_source = _quote_sqlite_identifier(source)
            pending_condition = PENDING_MIGRATION_CONDITION.format(
                target=quoted_target,
                source=quoted_source,
            )
            count_exprs.append(
                f"""
                SUM(
                    CASE
                        WHEN {pending_condition}
                        THEN 1
                        ELSE 0
                    END
                ) AS pending_{index}
                """
            )
        row = conn.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            f"SELECT {', '.join(count_exprs)} FROM {quoted_table}"  # nosec B608
        ).fetchone()
        if row is None:
            return {source: 0 for source in sources}
        return {source: int(row[index] or 0) for index, source in enumerate(sources)}

    def _execute_normalized_migration(
        self,
        conn: sqlite3.Connection,
        *,
        source: str,
        target: str,
        quoted_source: str,
        quoted_target: str,
        quoted_table: str,
        normalizer,
    ) -> Dict[str, Any]:
        select_cursor = conn.cursor()
        update_cursor = conn.cursor()
        pending_condition = PENDING_MIGRATION_CONDITION.format(
            target=quoted_target,
            source=quoted_source,
        )
        select_query = (
            f"SELECT rowid, {quoted_source} "
            f"FROM {quoted_table} WHERE {pending_condition}"  # nosec B608
        )
        select_cursor.execute(select_query)
        affected_rows = 0
        skipped_invalid = 0
        while True:
            rows = select_cursor.fetchmany(1000)
            if not rows:
                break
            updates = []
            for rowid, raw_value in rows:
                normalized = normalizer(raw_value)
                if normalized is None:
                    skipped_invalid += 1
                    continue
                updates.append((normalized, rowid))
            if updates:
                update_cursor.executemany(
                    f"UPDATE {quoted_table} SET {quoted_target} = ? WHERE rowid = ?",  # nosec B608
                    updates,
                )
                affected_rows += len(updates)
        return {
            "source": source,
            "target": target,
            "updated_rows": affected_rows,
            "skipped_invalid_records": skipped_invalid,
        }

    def _execute_direct_migration(
        self,
        cursor: sqlite3.Cursor,
        *,
        source: str,
        target: str,
        quoted_source: str,
        quoted_target: str,
        quoted_table: str,
    ) -> Dict[str, Any]:
        pending_condition = PENDING_MIGRATION_CONDITION.format(
            target=quoted_target,
            source=quoted_source,
        )
        update_query = (
            f"UPDATE {quoted_table} SET {quoted_target} = {quoted_source} "
            f"WHERE {pending_condition}"  # nosec B608
        )
        cursor.execute(update_query)
        return {
            "source": source,
            "target": target,
            "updated_rows": cursor.rowcount,
            "skipped_invalid_records": 0,
        }

    def _execute_migration(self, migration_plan: List[Dict]) -> Dict[str, Any]:
        """Executa o plano de migracao no banco de dados."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                table_name = _resolve_maintenance_table(conn, require_table=True)
                quoted_table = _quote_sqlite_identifier(table_name)
                valid_columns = {
                    row[1]
                    for row in cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                        f"PRAGMA table_info({quoted_table})"
                    ).fetchall()
                }
                stats: Dict[str, Any] = {
                    "updated_rows": 0,
                    "skipped_invalid_records": 0,
                    "skipped_invalid_numero_ssa": 0,
                    "migrations": [],
                }
                normalizers = {
                    "numero_ssa": (normalize_strict, "skipped_invalid_numero_ssa")
                }
                for _normalizer, skipped_counter in normalizers.values():
                    stats.setdefault(skipped_counter, 0)

                for migration in migration_plan:
                    source = migration["source"]
                    target = migration["target"]
                    if source not in valid_columns or target not in valid_columns:
                        raise ValueError(
                            f"Coluna de migracao ausente em {table_name}: {source!r} -> {target!r}"
                        )
                    quoted_source = _quote_sqlite_identifier(source)
                    quoted_target = _quote_sqlite_identifier(target)

                    logger.info(f"Migrando dados: '{source}' -> '{target}'")
                    normalizer_config = normalizers.get(target)
                    skipped_counter = None
                    if normalizer_config is None:
                        migration_stats = self._execute_direct_migration(
                            cursor,
                            source=source,
                            target=target,
                            quoted_source=quoted_source,
                            quoted_target=quoted_target,
                            quoted_table=quoted_table,
                        )
                    else:
                        normalizer, skipped_counter = normalizer_config
                        migration_stats = self._execute_normalized_migration(
                            conn,
                            source=source,
                            target=target,
                            quoted_source=quoted_source,
                            quoted_target=quoted_target,
                            quoted_table=quoted_table,
                            normalizer=normalizer,
                        )

                    stats["updated_rows"] += migration_stats["updated_rows"]
                    skipped_invalid_records = migration_stats["skipped_invalid_records"]
                    stats["skipped_invalid_records"] += skipped_invalid_records
                    if skipped_counter is not None:
                        stats[skipped_counter] += skipped_invalid_records
                    stats["migrations"].append(migration_stats)
                    if skipped_counter == "skipped_invalid_numero_ssa" and (
                        skipped_invalid_records
                    ):
                        logger.warning(
                            "Ignorados %s valores invalidos de numero_ssa em '%s'",
                            skipped_invalid_records,
                            source,
                        )

                    logger.info(
                        "Migrados %s registros de '%s' para '%s'",
                        migration_stats["updated_rows"],
                        source,
                        target,
                    )

                conn.commit()
                logger.info("Migracao concluida com sucesso")
                return stats

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro durante migracao: {e}")


class DatabaseMaintenanceReportService:
    """Coordinates database maintenance report generation."""

    def __init__(self, analyzer: DatabaseAnalyzer):
        self.analyzer = analyzer

    def generate_report(
        self,
        output_file: str = "docs_saida/database_analysis_report.md",
        structure_analysis: Dict[str, Any] | None = None,
        sanity_check: Dict[str, Any] | None = None,
    ) -> str:
        try:
            backup_path = self.analyzer.create_backup()
            if structure_analysis is None:
                structure_analysis = self.analyzer.analyze_table_structure()
            if sanity_check is None:
                sanity_check = self.analyzer.perform_sanity_check()

            report_content = render_database_analysis_report(
                db_path=self.analyzer.db_path,
                backup_path=backup_path,
                structure=structure_analysis,
                sanity=sanity_check,
            )

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Relatorio de analise salvo em: {output_file}")
            return output_file
        except Exception as e:
            logger.exception("Falha ao gerar relatorio de manutencao")
            raise DatabaseMaintenanceError(f"Erro ao gerar relatorio: {e}")


def main():
    """Funcao principal para executar analise e manutencao do banco."""
    try:
        db_path = str(
            ensure_path_is_allowed(
                os.environ.get("SSA_DB_PATH") or "data/ssas.db",
                purpose="maintenance_db_path",
                expect_directory=False,
            )
        )
    except Exception as e:
        logger.error("Caminho do banco invalido: %s", e)
        return

    if not os.path.exists(db_path):
        print(f"Banco de dados nao encontrado: {db_path}")
        return

    try:
        analyzer = DatabaseAnalyzer(db_path)

        structure_analysis = analyzer.analyze_table_structure()
        sanity_results = analyzer.perform_sanity_check()

        # Gerar relatorio de analise
        report_service = DatabaseMaintenanceReportService(analyzer)
        report_file = report_service.generate_report(
            structure_analysis=structure_analysis,
            sanity_check=sanity_results,
        )
        print(f"Relatorio gerado: {report_file}")

        print("\nResumo da Verificacao de Sanidade:")
        for issue, count in sanity_results.get("summary", {}).items():
            if count > 0:
                print(f"- {issue.replace('_', ' ').title()}: {count}")

        # Planejar migracao (dry-run)
        migrator = DatabaseMigrator(db_path)
        migration_plan = migrator.migrate_duplicate_columns(dry_run=True)

        if migration_plan["migration_plan"]:
            print("\nPlano de Migracao Sugerido:")
            for plan in migration_plan["migration_plan"]:
                print(
                    f"- {plan['source']} -> {plan['target']} ({plan['records_to_migrate']} registros)"
                )

    except Exception as e:
        print(f"Erro durante analise: {e}")


if __name__ == "__main__":
    main()
