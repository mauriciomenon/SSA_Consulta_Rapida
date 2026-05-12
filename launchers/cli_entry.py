#!/usr/bin/env python3
"""
Entry point CLI para executavel v3.10
Separado do main.py principal
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

try:
    from launchers.runtime_entry_helpers import (
        CLI_SMOKE_OK_MARKER,
        SMOKE_TEST_ENV,
        bootstrap_entry_runtime,
        log_launcher_failure,
        resolve_runtime_home,
        seed_runtime_config,
        seed_runtime_data,
    )
except ModuleNotFoundError as exc:
    if exc.name != "launchers" and not str(exc.name).startswith("launchers."):
        raise
    from runtime_entry_helpers import (  # type: ignore[no-redef]
        CLI_SMOKE_OK_MARKER,
        SMOKE_TEST_ENV,
        bootstrap_entry_runtime,
        log_launcher_failure,
        resolve_runtime_home,
        seed_runtime_config,
        seed_runtime_data,
    )

exe_path: Path | None = None
is_frozen_runtime = False
app_dir = ""
_runtime_prepared = False


@dataclass(frozen=True)
class CliRuntimePaths:
    runtime_base: str
    docs_dir: str
    data_dir: str
    db_path: str


class ImportExecutionStats(TypedDict):
    exit_code: int
    status: str
    updated: object
    total_candidates: int
    processed_files: int
    error_count: int


def _seed_runtime_config(runtime_dir: Path, bundled_config: Path | None) -> Path:
    return seed_runtime_config(
        runtime_dir,
        bundled_config,
        logger_name="cli_entry",
    )


def _seed_runtime_data(runtime_dir: Path, bundled_data: Path | None) -> Path:
    return seed_runtime_data(
        runtime_dir,
        bundled_data,
        logger_name="cli_entry",
        copy_all=True,
    )


def _bootstrap_runtime() -> str:
    return bootstrap_entry_runtime(
        globals(),
        __file__,
        executable_prefixes=("SSA_CLI_", "SSA_Consulta_Rapida"),
        logger_name="cli_entry",
        include_resources=False,
        copy_all_data=True,
        create_common_dirs=False,
    )


def _execute_import_and_report(
    run_importer_logic: Callable[..., object],
    *,
    docs_dir: str,
    data_dir: str,
    runtime_base: str,
    logger: Any,
) -> ImportExecutionStats:
    from core.import_progress import ImportProgressSummary

    summary = ImportProgressSummary()

    updated = run_importer_logic(
        docs_dir=docs_dir,
        data_dir=data_dir,
        force_import=True,
        extra_allowed_roots=[runtime_base],
        progress_callback=summary.capture,
    )
    has_errors = bool(summary.errors)
    stats = ImportExecutionStats(
        exit_code=1,
        status="failed",
        updated=updated,
        total_candidates=summary.total_candidates,
        processed_files=summary.processed_files,
        error_count=len(summary.errors),
    )
    if updated and not has_errors:
        logger.info("Importacao concluida. resultado=%r", updated)
        sys.stdout.write(f"Importacao concluida. resultado={updated!r}\n")
        stats["exit_code"] = 0
        stats["status"] = "success"
        return stats
    if updated and has_errors:
        logger.error(
            "Importacao parcial com erros. resultado=%r total=%s processados=%s erros=%s",
            updated,
            summary.total_candidates,
            summary.processed_files,
            len(summary.errors),
        )
        sys.stderr.write(
            "ERRO: Importacao parcial encontrou falhas em arquivos candidatos. "
            "Consulte os logs da aplicacao.\n"
        )
        stats["status"] = "partial_error"
        return stats

    observed_candidate_work = (
        summary.total_candidates > 0 or summary.processed_files > 0
    )
    if not observed_candidate_work and not has_errors:
        message = f"Importacao concluida sem atualizacoes. resultado={updated!r}"
        logger.info(message)
        sys.stdout.write(f"{message}\n")
        stats["exit_code"] = 0
        stats["status"] = "no_work"
        return stats

    logger.error(
        "Importacao nao gravou atualizacoes. resultado=%r total=%s processados=%s erros=%s",
        updated,
        summary.total_candidates,
        summary.processed_files,
        len(summary.errors),
    )
    sys.stderr.write(
        "ERRO: Importacao nao gravou atualizacoes para arquivos candidatos. "
        "Consulte os logs da aplicacao.\n"
    )
    return stats


def _smoke_test_exit_code() -> int | None:
    if os.environ.get(SMOKE_TEST_ENV) != "1":
        return None
    try:
        from utils.version import get_app_version

        version = get_app_version()
        print(f"{CLI_SMOKE_OK_MARKER} v{version}")
        return 0
    except Exception as exc:  # pragma: no cover - rare smoke diagnostic
        print(f"SMOKE_CLI_FAIL {exc}")
        return 1


def _prepare_cli_runtime_paths(
    *,
    app_directory: str,
    is_frozen: bool,
    setup_project_structure: Any,
    ensure_default_settings: Callable[..., object],
    ensure_path_is_allowed: Callable[..., object],
) -> CliRuntimePaths:
    runtime_root_override = os.environ.get("SSA_RUNTIME_ROOT")
    default_runtime_base = resolve_runtime_home() if is_frozen else Path(app_directory)
    runtime_base = str(runtime_root_override or default_runtime_base)
    setup_project_structure.setup_dirs(base_path=runtime_base)
    ensure_default_settings(fail_fast=False)
    docs_dir = os.path.join(runtime_base, "docs_entrada")
    data_dir = os.path.join(runtime_base, "data")
    db_path_candidate = os.environ.get("SSA_DB_PATH") or os.path.join(
        data_dir,
        "ssas.db",
    )
    db_path = str(
        ensure_path_is_allowed(
            db_path_candidate,
            purpose="cli db path",
            expect_directory=False,
            extra_allowed_roots=[runtime_base],
        )
    )
    os.environ["SSA_DB_PATH"] = db_path
    return CliRuntimePaths(
        runtime_base=runtime_base,
        docs_dir=docs_dir,
        data_dir=data_dir,
        db_path=db_path,
    )


def _should_run_import(argv: list[str]) -> bool:
    return any(arg in ("--force-rescan", "--rescan") for arg in argv[1:])


def main():
    """Entry point CLI v3.10.

    Comportamento especial para smoke test automatico: se a variavel de ambiente
    de smoke estiver presente, imprime um marcador simples e sai sem
    iniciar a interface interativa. Isso permite que scripts de CI validem
    rapidamente a integridade do carregamento sem bloquear esperando input.
    """
    global app_dir, is_frozen_runtime
    logger = None
    try:
        app_dir = _bootstrap_runtime()
    except Exception as e:
        log_launcher_failure(
            "cli_entry",
            "Falha ao preparar runtime CLI",
            e,
            include_trace=True,
        )
        sys.stderr.write(
            "ERRO: Falha ao preparar runtime CLI. Consulte os logs da aplicacao.\n"
        )
        sys.exit(1)

    smoke_exit_code = _smoke_test_exit_code()
    if smoke_exit_code is not None:
        sys.exit(smoke_exit_code)

    try:
        from core.app_logic import run_importer_logic
        from core.config_manager import ensure_default_settings
        from interface.cli import start_cli_loop
        from utils import setup_project_structure
        from utils.path_safety import ensure_path_is_allowed
        from utils.robust_logging import get_robust_logger

        logger = get_robust_logger().get_logger("ssa.launcher", "cli_entry")

        runtime_paths = _prepare_cli_runtime_paths(
            app_directory=app_dir,
            is_frozen=is_frozen_runtime,
            setup_project_structure=setup_project_structure,
            ensure_default_settings=ensure_default_settings,
            ensure_path_is_allowed=ensure_path_is_allowed,
        )
        table_name = os.environ.get("SSA_TABLE_NAME") or "ssa_table"
        if _should_run_import(sys.argv):
            import_stats = _execute_import_and_report(
                run_importer_logic,
                docs_dir=runtime_paths.docs_dir,
                data_dir=runtime_paths.data_dir,
                runtime_base=runtime_paths.runtime_base,
                logger=logger,
            )
            sys.exit(import_stats["exit_code"])

        start_cli_loop(runtime_paths.db_path, table_name)
    except ImportError as e:
        if logger is not None:
            logger.error(
                "Nao foi possivel importar modulos centrais da CLI: %s",
                e,
                exc_info=True,
            )
        sys.stderr.write(
            "ERRO: Nao foi possivel iniciar a CLI. Consulte os logs da aplicacao.\n"
        )
        sys.stderr.write(
            "Dica: execute novamente pelo terminal para confirmar o ambiente de runtime.\n"
        )
        sys.exit(1)
    except Exception as e:
        if logger is not None:
            logger.error("Falha inesperada ao iniciar CLI: %s", e, exc_info=True)
        sys.stderr.write(
            "ERRO: Falha inesperada ao iniciar CLI. Consulte os logs da aplicacao.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
