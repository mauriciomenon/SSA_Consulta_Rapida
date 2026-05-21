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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from shared.date_utils import parse_any_date
from shared.numero_ssa import normalize_strict
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
    "({target} IS NULL OR {target} = '') "
    "AND ({source} IS NOT NULL AND {source} != '')"
)


def _quote_sqlite_identifier(identifier: str) -> str:
    """Escapa identificador SQLite vindo do schema local."""
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


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

        # Criar diretorio de backup se nao existir
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        # Nome do backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        db_name = Path(self.db_path).stem
        backup_filename = f"{db_name}_backup_{timestamp}_{uuid.uuid4().hex[:8]}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            raise DatabaseMaintenanceError(f"Falha ao criar backup: {e}")

    def analyze_table_structure(self) -> Dict[str, Any]:
        """Analisa a estrutura da tabela identificando duplicacoes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Obter informacoes das colunas
                cursor.execute("PRAGMA table_info(ssas)")
                columns_info = cursor.fetchall()

                # Obter contagem de registros por coluna
                column_counts = {}
                for col_info in columns_info:
                    col_name = col_info[1]
                    try:
                        quoted_col_name = _quote_sqlite_identifier(col_name)
                        cursor.execute(
                            f"SELECT COUNT(*) FROM ssas WHERE {quoted_col_name} IS NOT NULL "  # nosec B608
                            f"AND {quoted_col_name} != ''"
                        )
                        count = cursor.fetchone()[0]
                        column_counts[col_name] = count
                    except Exception as e:
                        logger.warning(f"Erro ao contar coluna '{col_name}': {e}")
                        column_counts[col_name] = 0

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

    def _identify_duplicate_columns(
        self, columns_info: List[Tuple], column_counts: Dict[str, int]
    ) -> Dict[str, List[Dict]]:
        """Identifica grupos de colunas duplicadas baseado em nomes similares."""
        groups = {}

        # Mapear colunas por conceito basico.
        for concept, potential_names in LEGACY_CONCEPT_COLUMN_MAPPING.items():
            found_columns = []
            for col_info in columns_info:
                col_name = col_info[1]
                if col_name in potential_names:
                    found_columns.append(
                        {
                            "name": col_name,
                            "type": col_info[2],
                            "count": column_counts.get(col_name, 0),
                            "is_legacy": "N\u00famero" in col_name
                            or "Semana" in col_name
                            or "Descri\u00e7\u00e3o" in col_name
                            or "Respons\u00e1vel" in col_name
                            or "Grau" in col_name,
                        }
                    )

            if len(found_columns) > 1:
                groups[concept] = sorted(
                    found_columns, key=lambda x: x["count"], reverse=True
                )

        return groups

    def _check_numero_ssa(self, df: pd.DataFrame, issues: Dict[str, Any]) -> str | None:
        numero_cols = ["N\u00famero da SSA", "numero_ssa"]
        present_cols = [col for col in numero_cols if col in df.columns]
        numero_col = None

        if present_cols:
            numero_col = "numero_ssa" if "numero_ssa" in present_cols else present_cols[0]
            priority_cols = (
                ["numero_ssa"] + [col for col in present_cols if col != "numero_ssa"]
                if "numero_ssa" in present_cols
                else present_cols
            )
            numero_series = (
                df[priority_cols]
                .replace("", pd.NA)
                .T.bfill().T
                .iloc[:, 0]
            )
            missing_numero = df[numero_series.isna()]
            issues["missing_numero_ssa"] = missing_numero.index.tolist()

            valid_numbers = numero_series.dropna()
            duplicates = valid_numbers[valid_numbers.duplicated(keep=False)]
            if not duplicates.empty:
                issues["duplicate_numbers"] = duplicates.value_counts().to_dict()

        return numero_col

    def _check_missing_fields(self, df: pd.DataFrame, issues: Dict[str, Any]) -> None:
        for col in ["descricao_ssa"]:
            if col in df.columns:
                missing_desc = df[df[col].isna() | (df[col] == "")]
                issues["missing_descricao"] = missing_desc.index.tolist()
                break

        for col in ["setor_emissor"]:
            if col in df.columns:
                missing_emissor = df[df[col].isna() | (df[col] == "")]
                issues["missing_area_emissora"] = missing_emissor.index.tolist()
                break

        for col in ["localizacao_codigo", "descricao_localizacao"]:
            if col in df.columns:
                missing_loc = df[df[col].isna() | (df[col] == "")]
                issues["missing_localizacao"] = missing_loc.index.tolist()
                break

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
                issues["invalid_dates"] = invalid_dates.index.tolist()

    def _check_empty_records(
        self,
        df: pd.DataFrame,
        issues: Dict[str, Any],
        numero_col: str | None,
    ) -> None:
        essential_cols = (
            [numero_col, "descricao_ssa", "setor_emissor"]
            if numero_col
            else ["descricao_ssa", "setor_emissor"]
        )
        existing_essential = [col for col in essential_cols if col in df.columns]
        if existing_essential:
            empty_records = df[df[existing_essential].isna().all(axis=1)]
            issues["empty_records"] = empty_records.index.tolist()

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
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM ssas", conn)

                if df.empty:
                    return {
                        "total_records": 0,
                        "issues": issues,
                        "summary": self._build_sanity_summary(issues),
                    }

                total_records = len(df)

                numero_col = self._check_numero_ssa(df, issues)
                self._check_missing_fields(df, issues)
                self._check_invalid_dates(df, issues)
                self._check_empty_records(df, issues, numero_col)

                return {
                    "total_records": total_records,
                    "issues": issues,
                    "summary": self._build_sanity_summary(issues),
                }

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro na verificacao de sanidade: {e}")

    def generate_report(
        self,
        output_file: str = "docs_saida/database_analysis_report.md",
        structure_analysis: Dict[str, Any] | None = None,
        sanity_check: Dict[str, Any] | None = None,
    ) -> str:
        """Gera relatorio completo de analise do banco de dados."""
        try:
            # Criar backup antes da analise
            backup_path = self.create_backup()

            # Analisar estrutura
            if structure_analysis is None:
                structure_analysis = self.analyze_table_structure()

            # Verificar sanidade
            if sanity_check is None:
                sanity_check = self.perform_sanity_check()

            # Gerar relatorio
            report_content = self._generate_report_content(
                structure_analysis, sanity_check, backup_path
            )

            # Salvar relatorio
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Relatorio de analise salvo em: {output_file}")
            return output_file

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro ao gerar relatorio: {e}")

    def _generate_report_content(
        self, structure: Dict, sanity: Dict, backup_path: str
    ) -> str:
        """Gera o conteudo do relatorio em markdown."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        content = f"""# Relatorio de Analise do Banco de Dados SSA

**Data de Analise:** {timestamp}
**Banco Analisado:** {self.db_path}
**Backup Criado:** {backup_path}

## Resumo Executivo

**Total de Registros:** {sanity.get("total_records", 0)}
**Total de Colunas:** {structure.get("total_columns", 0)}
**Grupos de Colunas Duplicadas:** {len(structure.get("duplicated_groups", {}))}

## Problemas Identificados

### Integridade de Dados
"""

        if "summary" in sanity:
            summary = sanity["summary"]
            for issue_type, count in summary.items():
                issue_name = issue_type.replace("_", " ").title()
                content += f"- **{issue_name}:** {count} registros\n"

        content += "\n## Analise de Estrutura\n\n### Colunas Duplicadas Detectadas\n\n"

        duplicated_groups = structure.get("duplicated_groups", {})
        for concept, columns in duplicated_groups.items():
            content += f"#### {concept.replace('_', ' ').title()}\n\n"
            content += "| Nome da Coluna | Tipo | Registros | Status |\n"
            content += "|----------------|------|-----------|--------|\n"

            for col in columns:
                is_legacy_with_data = col["is_legacy"] and col["count"] > 0
                status = (
                    "WARN Legado (com dados)"
                    if is_legacy_with_data
                    else "OK Normalizada ou legado vazio"
                )
                content += (
                    f"| {col['name']} | {col['type']} | {col['count']} | {status} |\n"
                )
            content += "\n"

        content += "\n## Distribuicao de Dados por Coluna\n\n"
        content += "| Coluna | Registros com Dados |\n"
        content += "|--------|--------------------|\n"

        column_counts = structure.get("column_counts", {})
        sorted_columns = sorted(column_counts.items(), key=lambda x: x[1], reverse=True)

        for col_name, count in sorted_columns:
            content += f"| {col_name} | {count} |\n"

        content += f"""
## Recomendacoes

### Acoes Prioritarias
1. **Consolidacao de Colunas Duplicadas:** Migrar dados das colunas com espacos para as versoes
   padronizadas
2. **Limpeza de Dados:** Corrigir {sanity.get("summary", {}).get("missing_numero_ssa", 0)} SSAs sem
   numero
3. **Validacao:** Implementar verificacoes de integridade para evitar duplicacoes futuras

### Proximos Passos
1. Executar migracao de dados com backup
2. Atualizar schema para versao limpa
3. Ajustar mapeamentos de configuracao
4. Validar funcionamento de CLI e GUI

---
*Relatorio gerado automaticamente pelo sistema de manutencao do banco de dados.*
"""

        return content


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

        with sqlite3.connect(self.db_path) as conn:
            for concept, columns in duplicated_groups.items():
                if len(columns) < 2:
                    continue

                normalized_cols = [col for col in columns if not col.get("is_legacy")]
                legacy_cols = [col for col in columns if col.get("is_legacy")]
                if not normalized_cols or not legacy_cols:
                    continue

                target_col = max(normalized_cols, key=lambda x: x["count"])
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
        row = conn.execute(
            f"SELECT {', '.join(count_exprs)} FROM ssas"  # nosec B608
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
            f"FROM ssas WHERE {pending_condition}"  # nosec B608
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
                    f"UPDATE ssas SET {quoted_target} = ? WHERE rowid = ?",  # nosec B608
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
    ) -> Dict[str, Any]:
        pending_condition = PENDING_MIGRATION_CONDITION.format(
            target=quoted_target,
            source=quoted_source,
        )
        update_query = (
            f"UPDATE ssas SET {quoted_target} = {quoted_source} "
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                valid_columns = {
                    row[1]
                    for row in cursor.execute("PRAGMA table_info(ssas)").fetchall()
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
                            f"Coluna de migracao ausente em ssas: {source!r} -> {target!r}"
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
                        )
                    else:
                        normalizer, skipped_counter = normalizer_config
                        migration_stats = self._execute_normalized_migration(
                            conn,
                            source=source,
                            target=target,
                            quoted_source=quoted_source,
                            quoted_target=quoted_target,
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
        report_file = analyzer.generate_report(
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
