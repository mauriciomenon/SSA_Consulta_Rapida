from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from shared.date_utils import format_current_timestamp

ReportResult = dict[str, Any]
ReportStats = dict[str, bool | int | float]


def report_stats(all_results: list[ReportResult]) -> ReportStats:
    total_suites = len(all_results)
    successful_suites = sum(
        1 for result in all_results if result.get("success", False)
    )
    total_duration = sum(
        float(result.get("duration_seconds", 0)) for result in all_results
    )
    success_rate = successful_suites / total_suites if total_suites else 0.0
    return {
        "overall_success": successful_suites == total_suites,
        "success_rate": success_rate,
        "total_suites": total_suites,
        "successful_suites": successful_suites,
        "total_duration_seconds": total_duration,
    }


def report_status_label(stats: ReportStats) -> str:
    return (
        "OK SISTEMA APROVADO"
        if bool(stats["overall_success"])
        else "ERR SISTEMA COM PROBLEMAS"
    )


def report_success_rate_percent(stats: ReportStats) -> float:
    return float(stats["success_rate"]) * 100


def _render_result_sections(all_results: list[ReportResult]) -> str:
    sections: list[str] = []
    for result in all_results:
        test_name = result.get("test_name", "Teste Desconhecido")
        success = bool(result.get("success", False))
        duration = float(result.get("duration_seconds", 0))
        status_icon = "OK" if success else "ERR"

        section = [f"#### {test_name} {status_icon}", ""]
        section.append(f"**Duracao:** {duration:.2f}s")
        if not success:
            error = result.get("error", result.get("stderr", "Erro desconhecido"))
            section.append(f"**Erro:** {error}")
        details = result.get("test_details")
        if isinstance(details, list):
            section.append("")
            section.append("**Detalhes:**")
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                detail_name = detail.get("test", "teste")
                detail_success = bool(detail.get("success", False))
                detail_icon = "OK" if detail_success else "ERR"
                section.append(f"- {detail_name}: {detail_icon}")
        sections.append("\n".join(section))
    return "\n\n".join(sections)


def render_markdown_report(
    all_results: list[ReportResult],
    stats: ReportStats,
    report_file: Path,
    project_root: Path,
) -> str:
    overall_success = bool(stats["overall_success"])
    status = report_status_label(stats)
    tested_sections = _render_result_sections(all_results)
    recommendation = (
        """
**OK SISTEMA APROVADO PARA USO**

O sistema SSA Consulta Rapida passou em todos os testes criticos.
"""
        if overall_success
        else """
**WARN SISTEMA REQUER ATENCAO**

Alguns testes falharam. O sistema pode ter problemas que impedem o uso seguro em
producao.

**Acoes Imediatas Necessarias:**
1. INFO Investigar falhas nos testes
2. FIX Corrigir problemas identificados
3. TEST Re-executar testes apos correcoes
4. INFO Validar funcionalidades criticas manualmente
"""
    )
    return f"""# Relatorio Abrangente de Testes - Sistema SSA Consulta Rapida

**Data dos Testes:** {format_current_timestamp("%d/%m/%Y %H:%M:%S")}
**Duracao Total:** {float(stats["total_duration_seconds"]):.2f} segundos
**Status Geral:** {status}

## Resumo Executivo

- **Total de Suites de Teste:** {stats["total_suites"]}
- **Suites Bem-sucedidas:** {stats["successful_suites"]}
- **Taxa de Sucesso:** {float(stats["success_rate"]):.1%}
- **Tempo Total de Execucao:** {float(stats["total_duration_seconds"]):.2f}s

### Status por Categoria

{tested_sections}

## Analise de Resultados

### Funcionalidades Testadas

1. **Criacao e Inicializacao do Banco de Dados**
2. **Importacao de Dados**
3. **Interfaces do Sistema**
4. **Funcionalidades Principais**
5. **Performance e Estabilidade**

### Criterios de Aprovacao

O sistema e considerado **APROVADO** quando:
- OK Todas as suites de teste passam
- OK Todas as funcionalidades criticas funcionam
- OK Performance esta dentro dos limites aceitaveis
- OK Nenhum erro critico e detectado

### Recomendacoes

{recommendation}

---

## Informacoes Tecnicas

**Ambiente de Teste:**
- Python: {sys.version.split()[0]}
- Diretorio de Trabalho: {project_root}

**Arquivos de Log:**
- Relatorio detalhado: `{report_file}`
- Logs de performance: `docs_saida/performance_tests_*.json`
- Logs de testes funcionais: `docs_saida/automated_tests_report_*.md`

---
*Relatorio gerado automaticamente pelo sistema de testes abrangentes.*
"""


def write_report_files(
    report_file: Path,
    content: str,
    all_results: list[ReportResult],
    stats: ReportStats,
) -> None:
    report_file.write_text(content, encoding="utf-8")
    json_file = report_file.with_suffix(".json")
    json_file.write_text(
        json.dumps(
            {
                "timestamp": format_current_timestamp(),
                **stats,
                "test_results": all_results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
