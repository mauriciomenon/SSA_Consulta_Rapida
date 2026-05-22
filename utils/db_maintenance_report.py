"""Markdown rendering for database maintenance reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


def render_database_analysis_report(
    *,
    db_path: str,
    backup_path: str,
    structure: Mapping[str, Any],
    sanity: Mapping[str, Any],
    analysis_timestamp: datetime | None = None,
) -> str:
    """Render the database maintenance analysis as Markdown."""
    timestamp = (analysis_timestamp or datetime.now()).strftime("%d/%m/%Y %H:%M:%S")
    content = f"""# Relatorio de Analise do Banco de Dados SSA

**Data de Analise:** {timestamp}
**Banco Analisado:** {db_path}
**Backup Criado:** {backup_path}

## Resumo Executivo

**Total de Registros:** {sanity.get("total_records", 0)}
**Total de Colunas:** {structure.get("total_columns", 0)}
**Grupos de Colunas Duplicadas:** {len(structure.get("duplicated_groups", {}))}

## Problemas Identificados

### Integridade de Dados
"""

    summary = sanity.get("summary")
    if isinstance(summary, Mapping):
        for issue_type, count in summary.items():
            issue_name = str(issue_type).replace("_", " ").title()
            content += f"- **{issue_name}:** {count} registros\n"

    content += "\n## Analise de Estrutura\n\n### Colunas Duplicadas Detectadas\n\n"

    duplicated_groups = structure.get("duplicated_groups", {})
    if isinstance(duplicated_groups, Mapping):
        for concept, columns in duplicated_groups.items():
            content += f"#### {str(concept).replace('_', ' ').title()}\n\n"
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
    if isinstance(column_counts, Mapping):
        sorted_columns = sorted(column_counts.items(), key=lambda x: x[1], reverse=True)
        for col_name, count in sorted_columns:
            content += f"| {col_name} | {count} |\n"

    missing_numero = 0
    if isinstance(summary, Mapping):
        missing_numero = int(summary.get("missing_numero_ssa", 0))

    content += f"""
## Recomendacoes

### Acoes Prioritarias
1. **Consolidacao de Colunas Duplicadas:** Migrar dados das colunas com espacos para as versoes
   padronizadas
2. **Limpeza de Dados:** Corrigir {missing_numero} SSAs sem
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
