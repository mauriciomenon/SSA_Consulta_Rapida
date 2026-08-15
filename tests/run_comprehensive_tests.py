# tests/run_comprehensive_tests.py
"""Executor principal para testes funcionais e de performance do sistema SSA."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT_BOOTSTRAP = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_BOOTSTRAP))

from launchers.build_complete import _get_project_root  # noqa: E402
from launchers.smoke_validation import run_cli_import_smoke  # noqa: E402
from shared.date_utils import format_current_timestamp  # noqa: E402
from tests.reporting_utils import (  # noqa: E402
    ReportResult,
    render_markdown_report,
    report_status_label,
    report_stats,
    report_success_rate_percent,
    write_report_files,
)
from utils.robust_logging import get_robust_logger  # noqa: E402


PROJECT_ROOT = _get_project_root()
logger = get_robust_logger().get_logger(__name__, "maintenance")


def _log_separator(char: str = "-", width: int = 50) -> None:
    logger.info(char * width)


def run_test_suite(
    test_name: str,
    test_script: str,
    timeout: int = 300,
) -> ReportResult:
    """Executa uma suite de testes especifica."""
    logger.info("START Executando %s", test_name)
    _log_separator()

    start_time = datetime.now()
    test_path = PROJECT_ROOT / test_script

    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.error("TIMEOUT: %s excedeu %ss", test_name, timeout)
        return {
            "test_name": test_name,
            "script": test_script,
            "success": False,
            "duration_seconds": timeout,
            "error": "timeout",
            "timeout_seconds": timeout,
        }
    except OSError as exc:
        logger.error("ERRO: %s - %s", test_name, exc)
        return {
            "test_name": test_name,
            "script": test_script,
            "success": False,
            "error": str(exc),
        }

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if result.stdout:
        logger.info(result.stdout)
    if result.stderr and result.returncode != 0:
        logger.error("ERROS:\n%s", result.stderr)

    success = result.returncode == 0
    status = "OK SUCESSO" if success else "ERR FALHOU"
    logger.info("%s: %s (%.2fs)", test_name, status, duration)

    return {
        "test_name": test_name,
        "script": test_script,
        "success": success,
        "duration_seconds": duration,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


def run_manual_smoke_tests() -> ReportResult:
    """Executa testes basicos de fumaca."""
    logger.info("INFO Executando testes de fumaca basicos")
    _log_separator()

    result = run_cli_import_smoke(repo_root=PROJECT_ROOT)
    logger.info("CLI import: %s", "OK" if result.ok else "ERR")
    smoke_tests: list[ReportResult] = [
        {
            "test": "cli_functional_import",
            "success": result.ok,
            "imported_rows": result.imported_rows,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
        }
    ]

    logger.info("Verificando arquivos essenciais")
    essential_files = [
        "main.py",
        "config/schema.sql",
        "config/column_mappings.json",
        "armazenamento/database.py",
        "core/app_logic.py",
        "gui/gui_ssa.py",
    ]
    missing_files = [
        file_path
        for file_path in essential_files
        if not (PROJECT_ROOT / file_path).exists()
    ]
    files_ok = not missing_files
    logger.info("Arquivos essenciais: %s", "OK" if files_ok else "ERR")
    if missing_files:
        logger.error("Arquivos faltando: %s", missing_files)

    smoke_tests.append(
        {
            "test": "essential_files",
            "success": files_ok,
            "missing_files": missing_files,
            "total_checked": len(essential_files),
        }
    )

    successful_smoke_tests = sum(
        1 for test in smoke_tests if test.get("success", False)
    )
    return {
        "test_name": "smoke_tests",
        "total_tests": len(smoke_tests),
        "successful_tests": successful_smoke_tests,
        "success": successful_smoke_tests == len(smoke_tests),
        "test_details": smoke_tests,
    }


def generate_comprehensive_report(
    all_results: list[ReportResult],
    output_dir: str = "docs_saida",
) -> str:
    """Gera relatorio abrangente de todos os testes."""
    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = format_current_timestamp("%Y%m%d_%H%M%S")
    report_file = output_path / f"comprehensive_test_report_{timestamp}.md"
    stats = report_stats(all_results)
    content = render_markdown_report(all_results, stats, report_file, PROJECT_ROOT)
    write_report_files(report_file, content, all_results, stats)
    return str(report_file)


def _build_test_suites(args: argparse.Namespace) -> list[tuple[str, str]]:
    test_suites = [
        ("Testes Funcionais Automatizados", "tests/automated_system_tests.py")
    ]
    if not args.skip_performance and not args.quick:
        test_suites.append(("Testes de Performance", "tests/performance_tests.py"))
    return test_suites


def main() -> int:
    """Funcao principal do executor de testes abrangentes."""
    parser = argparse.ArgumentParser(
        description="Executor abrangente de testes do sistema SSA"
    )
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="Pular testes de performance",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Executar apenas testes rapidos essenciais",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout em segundos para cada suite",
    )
    args = parser.parse_args()

    logger.info("START SISTEMA DE TESTES ABRANGENTES - SSA CONSULTA RAPIDA")
    _log_separator("=", 70)
    logger.info("Data/Hora: %s", format_current_timestamp("%d/%m/%Y %H:%M:%S"))
    logger.info("Modo: %s", "Rapido" if args.quick else "Completo")
    _log_separator("=", 70)

    all_results = [run_manual_smoke_tests()]
    if not all_results[0].get("success", False):
        logger.warning("Testes de fumaca falharam; mantendo suite como falha critica")

    for test_name, test_script in _build_test_suites(args):
        test_path = PROJECT_ROOT / test_script
        if test_path.exists():
            all_results.append(run_test_suite(test_name, test_script, args.timeout))
        else:
            logger.warning("Script %s nao encontrado", test_script)
            all_results.append(
                {
                    "test_name": test_name,
                    "script": test_script,
                    "success": False,
                    "error": "Script nao encontrado",
                }
            )

    logger.info("FILE Gerando relatorio abrangente")
    report_file = generate_comprehensive_report(all_results)
    stats = report_stats(all_results)
    status_final = report_status_label(stats)

    _log_separator("=", 70)
    logger.info("INFO RESULTADO FINAL:")
    logger.info("Suites Executadas: %s", stats["total_suites"])
    logger.info("Suites Bem-sucedidas: %s", stats["successful_suites"])
    logger.info("Taxa de Sucesso: %.1f%%", report_success_rate_percent(stats))
    logger.info("Status Final: %s", status_final)
    logger.info("Relatorio completo salvo em: %s", report_file)
    _log_separator("=", 70)

    return 0 if stats["overall_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
