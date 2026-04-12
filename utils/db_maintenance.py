# utils/db_maintenance.py
"""
Sistema de manutenção e otimização do banco de dados SSA.

Oferece funcionalidades para:
- Backup automático
- Análise de sanidade dos dados
- Limpeza de colunas duplicadas
- Migração segura de dados
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from armazenamento.identifier_utils import is_valid_identifier

logger = logging.getLogger(__name__)


class DatabaseMaintenanceError(Exception):
    """Erro durante operações de manutenção do banco de dados."""

    pass


class DatabaseAnalyzer:
    """Analisa a estrutura e integridade dos dados no banco."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_backup(self, backup_dir: str = "data/backups") -> str:
        """Cria backup do banco de dados com timestamp."""
        if not os.path.exists(self.db_path):
            raise DatabaseMaintenanceError(
                f"Banco de dados não encontrado: {self.db_path}"
            )

        # Criar diretório de backup se não existir
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        # Nome do backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = Path(self.db_path).stem
        backup_filename = f"{db_name}_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            raise DatabaseMaintenanceError(f"Falha ao criar backup: {e}")

    def analyze_table_structure(self) -> Dict[str, Any]:
        """Analisa a estrutura da tabela identificando duplicações."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Obter informações das colunas
                cursor.execute("PRAGMA table_info(ssas)")
                columns_info = cursor.fetchall()

                # Obter contagem de registros por coluna
                column_counts = {}
                for col_info in columns_info:
                    col_name = col_info[1]
                    if not is_valid_identifier(col_name):
                        logger.warning(
                            "Ignorando coluna com identificador invalido na analise: %s",
                            col_name,
                        )
                        column_counts[col_name] = 0
                        continue
                    try:
                        cursor.execute(
                            f'SELECT COUNT(*) FROM ssas WHERE "{col_name}" IS NOT NULL AND "{col_name}" != ""'
                        )
                        count = cursor.fetchone()[0]
                        column_counts[col_name] = count
                    except Exception as e:
                        logger.warning(f"Erro ao contar coluna '{col_name}': {e}")
                        column_counts[col_name] = 0

                # Identificar duplicações potenciais
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

        # Mapear colunas por conceito básico
        concept_mapping = {
            "numero_ssa": ["Número da SSA", "numero_ssa"],
            "semana_cadastro": ["Semana de Cadastro", "semana_cadastro"],
            "descricao_execucao": ["Descrição Execução", "descricao_execucao"],
            "responsavel_programacao": [
                "Responsável na Programação",
                "responsavel_programacao",
            ],
            "responsavel_execucao": ["Responsável na Execução", "responsavel_execucao"],
            "grau_prioridade_emissao": [
                "Grau de Prioridade Emissão",
                "grau_prioridade_emissao",
            ],
            "grau_prioridade_planejamento": [
                "Grau de Prioridade Planejamento",
                "grau_prioridade_planejamento",
            ],
        }

        for concept, potential_names in concept_mapping.items():
            found_columns = []
            for col_info in columns_info:
                col_name = col_info[1]
                if col_name in potential_names:
                    found_columns.append(
                        {
                            "name": col_name,
                            "type": col_info[2],
                            "count": column_counts.get(col_name, 0),
                            "is_primary": "Número" in col_name
                            or "Semana" in col_name
                            or "Descrição" in col_name
                            or "Responsável" in col_name
                            or "Grau" in col_name,
                        }
                    )

            if len(found_columns) > 1:
                groups[concept] = sorted(
                    found_columns, key=lambda x: x["count"], reverse=True
                )

        return groups

    def perform_sanity_check(self) -> Dict[str, Any]:
        """Executa verificação de sanidade dos dados."""
        issues = {
            "missing_numero_ssa": [],
            "missing_descricao": [],
            "missing_area_emissora": [],
            "missing_localizacao": [],
            "duplicate_numbers": [],
            "invalid_dates": [],
            "empty_records": [],
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM ssas", conn)

                if df.empty:
                    return {"total_records": 0, "issues": issues}

                total_records = len(df)

                # Verificar número da SSA
                numero_cols = ["Número da SSA", "numero_ssa"]
                numero_col = None
                for col in numero_cols:
                    if col in df.columns and df[col].notna().sum() > 0:
                        numero_col = col
                        break

                if numero_col:
                    # SSAs sem número
                    missing_numero = df[df[numero_col].isna() | (df[numero_col] == "")]
                    issues["missing_numero_ssa"] = missing_numero.index.tolist()

                    # Números duplicados
                    valid_numbers = df[df[numero_col].notna() & (df[numero_col] != "")][
                        numero_col
                    ]
                    duplicates = valid_numbers[valid_numbers.duplicated(keep=False)]
                    if not duplicates.empty:
                        issues["duplicate_numbers"] = (
                            duplicates.value_counts().to_dict()
                        )

                # Verificar descrição
                desc_cols = ["descricao_ssa"]
                for col in desc_cols:
                    if col in df.columns:
                        missing_desc = df[df[col].isna() | (df[col] == "")]
                        issues["missing_descricao"] = missing_desc.index.tolist()
                        break

                # Verificar área emissora
                emissor_cols = ["setor_emissor"]
                for col in emissor_cols:
                    if col in df.columns:
                        missing_emissor = df[df[col].isna() | (df[col] == "")]
                        issues["missing_area_emissora"] = missing_emissor.index.tolist()
                        break

                # Verificar localização
                loc_cols = ["localizacao_codigo", "descricao_localizacao"]
                for col in loc_cols:
                    if col in df.columns:
                        missing_loc = df[df[col].isna() | (df[col] == "")]
                        issues["missing_localizacao"] = missing_loc.index.tolist()
                        break

                # Verificar datas inválidas
                date_cols = ["data_cadastro"]
                for col in date_cols:
                    if col in df.columns:
                        try:
                            pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                            invalid_dates = df[
                                pd.to_datetime(df[col], errors="coerce").isna()
                                & df[col].notna()
                            ]
                            issues["invalid_dates"] = invalid_dates.index.tolist()
                        except Exception:
                            pass

                # Registros completamente vazios
                essential_cols = (
                    [numero_col, "descricao_ssa", "setor_emissor"]
                    if numero_col
                    else ["descricao_ssa", "setor_emissor"]
                )
                existing_essential = [
                    col for col in essential_cols if col in df.columns
                ]
                if existing_essential:
                    empty_records = df[df[existing_essential].isna().all(axis=1)]
                    issues["empty_records"] = empty_records.index.tolist()

                return {
                    "total_records": total_records,
                    "issues": issues,
                    "summary": {
                        "missing_numero_ssa": len(issues["missing_numero_ssa"]),
                        "missing_descricao": len(issues["missing_descricao"]),
                        "missing_area_emissora": len(issues["missing_area_emissora"]),
                        "missing_localizacao": len(issues["missing_localizacao"]),
                        "duplicate_numbers": len(issues["duplicate_numbers"]),
                        "invalid_dates": len(issues["invalid_dates"]),
                        "empty_records": len(issues["empty_records"]),
                    },
                }

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro na verificação de sanidade: {e}")

    def generate_report(
        self, output_file: str = "docs_saida/database_analysis_report.md"
    ) -> str:
        """Gera relatório completo de análise do banco de dados."""
        try:
            # Criar backup antes da análise
            backup_path = self.create_backup()

            # Analisar estrutura
            structure_analysis = self.analyze_table_structure()

            # Verificação de sanidade
            sanity_check = self.perform_sanity_check()

            # Gerar relatório
            report_content = self._generate_report_content(
                structure_analysis, sanity_check, backup_path
            )

            # Salvar relatório
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Relatório de análise salvo em: {output_file}")
            return output_file

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro ao gerar relatório: {e}")

    def _generate_report_content(
        self, structure: Dict, sanity: Dict, backup_path: str
    ) -> str:
        """Gera o conteúdo do relatório em markdown."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        content = f"""# Relatório de Análise do Banco de Dados SSA

**Data de Análise:** {timestamp}
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

        content += "\n## Análise de Estrutura\n\n### Colunas Duplicadas Detectadas\n\n"

        duplicated_groups = structure.get("duplicated_groups", {})
        for concept, columns in duplicated_groups.items():
            content += f"#### {concept.replace('_', ' ').title()}\n\n"
            content += "| Nome da Coluna | Tipo | Registros | Status |\n"
            content += "|----------------|------|-----------|--------|\n"

            for col in columns:
                is_primary_with_data = col["is_primary"] and col["count"] > 0
                status = (
                    "OK Primária (com dados)"
                    if is_primary_with_data
                    else "ERR Legado (vazia/poucos dados)"
                )
                content += (
                    f"| {col['name']} | {col['type']} | {col['count']} | {status} |\n"
                )
            content += "\n"

        content += "\n## Distribuição de Dados por Coluna\n\n"
        content += "| Coluna | Registros com Dados |\n"
        content += "|--------|--------------------|\n"

        column_counts = structure.get("column_counts", {})
        sorted_columns = sorted(column_counts.items(), key=lambda x: x[1], reverse=True)

        for col_name, count in sorted_columns:
            content += f"| {col_name} | {count} |\n"

        content += f"""
## Recomendações

### Ações Prioritárias
1. **Consolidação de Colunas Duplicadas:** Migrar dados das colunas com espaços para as versões
   padronizadas
2. **Limpeza de Dados:** Corrigir {sanity.get("summary", {}).get("missing_numero_ssa", 0)} SSAs sem
   número
3. **Validação:** Implementar verificações de integridade para evitar duplicações futuras

### Próximos Passos
1. Executar migração de dados com backup
2. Atualizar schema para versão limpa
3. Ajustar mapeamentos de configuração
4. Validar funcionamento de CLI e GUI

---
*Relatório gerado automaticamente pelo sistema de manutenção do banco de dados.*
"""

        return content


class DatabaseMigrator:
    """Executa migração segura de dados entre esquemas."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.analyzer = DatabaseAnalyzer(db_path)

    def migrate_duplicate_columns(self, dry_run: bool = True) -> Dict[str, Any]:
        """Migra dados de colunas duplicadas para versões padronizadas."""
        if dry_run:
            logger.info("Executando migração em modo dry-run (sem alterações)")

        # Criar backup antes da migração
        backup_path = self.analyzer.create_backup()

        structure = self.analyzer.analyze_table_structure()
        duplicated_groups = structure.get("duplicated_groups", {})

        migration_plan = []

        for concept, columns in duplicated_groups.items():
            if len(columns) < 2:
                continue

            # Ordenar por quantidade de dados (maior para menor)
            sorted_cols = sorted(columns, key=lambda x: x["count"], reverse=True)
            source_col = sorted_cols[0]  # Coluna com mais dados
            target_col = sorted_cols[1]  # Coluna de destino (normalizada)

            # Verificar se target é realmente a versão normalizada
            if source_col["count"] > target_col["count"]:
                migration_plan.append(
                    {
                        "concept": concept,
                        "source": source_col["name"],
                        "target": target_col["name"],
                        "records_to_migrate": source_col["count"],
                    }
                )

        if not dry_run:
            self._execute_migration(migration_plan)

        return {
            "backup_created": backup_path,
            "migration_plan": migration_plan,
            "dry_run": dry_run,
        }

    def _execute_migration(self, migration_plan: List[Dict]) -> None:
        """Executa o plano de migração no banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for migration in migration_plan:
                    source = migration["source"]
                    target = migration["target"]

                    logger.info(f"Migrando dados: '{source}' -> '{target}'")

                    # Atualizar registros onde target está vazio mas source tem dados
                    update_query = f'''
                        UPDATE ssas
                        SET "{target}" = "{source}"
                        WHERE ("{target}" IS NULL OR "{target}" = "")
                        AND ("{source}" IS NOT NULL AND "{source}" != "")
                    '''

                    cursor = conn.cursor()
                    cursor.execute(update_query)
                    affected_rows = cursor.rowcount

                    logger.info(
                        f"Migrados {affected_rows} registros de '{source}' para '{target}'"
                    )

                conn.commit()
                logger.info("Migração concluída com sucesso")

        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro durante migração: {e}")


def main():
    """Função principal para executar análise e manutenção do banco."""
    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado: {db_path}")
        return

    try:
        analyzer = DatabaseAnalyzer(db_path)

        # Gerar relatório de análise
        report_file = analyzer.generate_report()
        print(f"Relatório gerado: {report_file}")

        # Executar verificação de sanidade
        sanity_results = analyzer.perform_sanity_check()
        print("\nResumo da Verificação de Sanidade:")
        for issue, count in sanity_results.get("summary", {}).items():
            if count > 0:
                print(f"- {issue.replace('_', ' ').title()}: {count}")

        # Planejar migração (dry-run)
        migrator = DatabaseMigrator(db_path)
        migration_plan = migrator.migrate_duplicate_columns(dry_run=True)

        if migration_plan["migration_plan"]:
            print("\nPlano de Migração Sugerido:")
            for plan in migration_plan["migration_plan"]:
                print(
                    f"- {plan['source']} -> {plan['target']} ({plan['records_to_migrate']} registros)"
                )

    except Exception as e:
        print(f"Erro durante análise: {e}")


if __name__ == "__main__":
    main()
