#!/usr/bin/env python3
"""
Entry point CLI para executavel v3.10
Separado do main.py principal
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, cast

try:
    from launchers.runtime_entry_helpers import (
        bootstrap_entry_runtime,
        log_launcher_failure,
        seed_runtime_config,
        seed_runtime_data,
    )
except ModuleNotFoundError as exc:
    if exc.name != "launchers":
        raise
    from runtime_entry_helpers import (  # type: ignore[no-redef]
        bootstrap_entry_runtime,
        log_launcher_failure,
        seed_runtime_config,
        seed_runtime_data,
    )


exe_path: Path | None = None
is_frozen_runtime = False
app_dir = ""
_runtime_prepared = False


@dataclass
class ImportProgressSummary:
    total_candidates: int = 0
    processed_files: int = 0
    errors: list[object] = field(default_factory=list)


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


def _run_force_rescan_import(
    run_importer_logic: Callable[..., object],
    *,
    docs_dir: str,
    data_dir: str,
    runtime_base: str,
    logger: Any,
) -> int:
    summary = ImportProgressSummary()

    def _summary_count(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int | float):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 0

    def _capture_import_progress(event_type: str, data: dict[str, object]) -> None:
        if not isinstance(data, dict):
            return
        if event_type == "start":
            summary.total_candidates = _summary_count(data.get("total"))
        elif event_type == "file_error":
            summary.errors.append(
                str(data.get("error") or data.get("filename") or "erro")
            )
        elif event_type == "finish":
            summary.total_candidates = _summary_count(
                data.get("total", summary.total_candidates)
            )
            summary.processed_files = _summary_count(data.get("processed"))
            reported_errors = data.get("errors")
            if isinstance(reported_errors, list):
                summary.errors = cast(list[object], reported_errors)

    updated = run_importer_logic(
        docs_dir=docs_dir,
        data_dir=data_dir,
        force_import=True,
        extra_allowed_roots=[runtime_base],
        progress_callback=_capture_import_progress,
    )
    if updated:
        logger.info("Importacao concluida. resultado=%r", updated)
        sys.stdout.write(f"Importacao concluida. resultado={updated!r}\n")
        return 0

    has_errors = bool(summary.errors)
    if summary.total_candidates == 0 and not has_errors:
        logger.info("Importacao concluida sem atualizacoes. resultado=%r", updated)
        sys.stdout.write("Importacao concluida sem atualizacoes.\n")
        return 0

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
    return 1


def main():
    """Entry point CLI v3.10.

    Comportamento especial para smoke test automático: se a variável de ambiente
    SSA_SMOKE_TEST=1 estiver presente, imprime um marcador simples e sai sem
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

    if os.environ.get("SSA_SMOKE_TEST") == "1":
        try:
            from utils.version import get_app_version  # import leve

            version = get_app_version()
            print(f"SMOKE_CLI_OK v{version}")
            sys.exit(0)
        except Exception as exc:  # pragma: no cover - raríssimo
            print(f"SMOKE_CLI_FAIL {exc}")
            sys.exit(1)

    try:
        from core.app_logic import run_importer_logic
        from core.config_manager import ensure_default_settings
        from interface.cli import start_cli_loop
        from utils import setup_project_structure
        from utils.path_safety import ensure_path_is_allowed
        from utils.robust_logging import get_robust_logger

        logger = get_robust_logger().get_logger("ssa.launcher", "cli_entry")

        runtime_root_override = os.environ.get("SSA_RUNTIME_ROOT")
        runtime_base = str(runtime_root_override or app_dir)
        setup_project_structure.setup_dirs(base_path=runtime_base)
        ensure_default_settings(fail_fast=False)
        docs_dir = os.path.join(runtime_base, "docs_entrada")
        data_dir = os.path.join(runtime_base, "data")
        db_path = os.environ.get("SSA_DB_PATH") or os.path.join(
            data_dir, "ssas.db"
        )
        db_path = str(
            ensure_path_is_allowed(
                db_path,
                purpose="cli db path",
                expect_directory=False,
                extra_allowed_roots=[runtime_base],
            )
        )
        os.environ.setdefault("SSA_DB_PATH", db_path)
        table_name = os.environ.get("SSA_TABLE_NAME") or "ssa_table"
        if any(arg in ("--force-rescan", "--rescan") for arg in sys.argv[1:]):
            sys.exit(
                _run_force_rescan_import(
                    run_importer_logic,
                    docs_dir=docs_dir,
                    data_dir=data_dir,
                    runtime_base=runtime_base,
                    logger=logger,
                )
            )

        start_cli_loop(db_path, table_name)
    except ImportError as e:
        if logger is not None:
            logger.error("Nao foi possivel importar interface.cli: %s", e, exc_info=True)
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
