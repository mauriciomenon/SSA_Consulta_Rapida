#!/usr/bin/env python3
"""
Entry point CLI para executavel v3.10
Separado do main.py principal
"""

import os
import sys
from pathlib import Path

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
        _bootstrap_runtime()
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

        setup_base_path = (
            os.environ.get("SSA_RUNTIME_ROOT") if is_frozen_runtime else None
        )
        setup_project_structure.setup_dirs(base_path=setup_base_path)
        ensure_default_settings(fail_fast=False)
        runtime_base = str(
            (os.environ.get("SSA_RUNTIME_ROOT") if is_frozen_runtime else None)
            or app_dir
        )
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
            updated = run_importer_logic(
                docs_dir=docs_dir,
                data_dir=data_dir,
                force_import=True,
                extra_allowed_roots=[runtime_base],
            )
            logger.info("Importacao concluida. resultado=%r", updated)
            sys.stdout.write(f"Importacao concluida. resultado={updated!r}\n")
            sys.exit(0)

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
