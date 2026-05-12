#!/usr/bin/env python3
"""
Entry point GUI para executavel v3.10
Separado do main.py principal
"""

import os
import sys
from pathlib import Path

try:
    from launchers.runtime_entry_helpers import (
        bootstrap_entry_runtime,
        GUI_SMOKE_OK_MARKER,
        log_launcher_failure,
        seed_runtime_config,
        seed_runtime_data,
        seed_runtime_resources,
        SMOKE_TEST_ENV,
    )
except ModuleNotFoundError as exc:
    if exc.name != "launchers" and not str(exc.name).startswith("launchers."):
        raise
    from runtime_entry_helpers import (  # type: ignore[no-redef]
        bootstrap_entry_runtime,
        GUI_SMOKE_OK_MARKER,
        log_launcher_failure,
        seed_runtime_config,
        seed_runtime_data,
        seed_runtime_resources,
        SMOKE_TEST_ENV,
    )


exe_path: Path | None = None
is_frozen_runtime = False
app_dir = ""
_runtime_prepared = False


def _seed_runtime_config(runtime_dir: Path, bundled_config: Path | None) -> Path:
    return seed_runtime_config(
        runtime_dir,
        bundled_config,
        logger_name="gui_entry",
    )


def _seed_runtime_data(runtime_dir: Path, bundled_data: Path | None) -> Path:
    return seed_runtime_data(
        runtime_dir,
        bundled_data,
        logger_name="gui_entry",
        copy_all=False,
    )


def _seed_runtime_resources(runtime_dir: Path, bundled_resources: Path | None) -> Path:
    return seed_runtime_resources(
        runtime_dir,
        bundled_resources,
        logger_name="gui_entry",
    )


def _bootstrap_runtime() -> str:
    return bootstrap_entry_runtime(
        globals(),
        __file__,
        executable_prefixes=("SSA_GUI_", "SSA_Consulta_Rapida"),
        logger_name="gui_entry",
        include_resources=True,
        copy_all_data=False,
        create_common_dirs=True,
    )


def _smoke_test_exit_code() -> int | None:
    if os.environ.get(SMOKE_TEST_ENV) != "1":
        return None
    try:
        from utils.version import get_app_version

        version = get_app_version()
        print(f"{GUI_SMOKE_OK_MARKER} v{version}")
        return 0
    except Exception as exc:  # pragma: no cover - smoke diagnostic
        print(f"SMOKE_GUI_FAIL {exc}")
        return 1


def main():
    """Entry point GUI v3.10"""
    try:
        _bootstrap_runtime()
        smoke_exit_code = _smoke_test_exit_code()
        if smoke_exit_code is not None:
            sys.exit(smoke_exit_code)

        from PyQt6.QtWidgets import QApplication

        from core.config_manager import ensure_default_settings
        from gui.gui_ssa import SSAMainWindow
        from utils import setup_project_structure

        setup_base_path = os.environ.get("SSA_RUNTIME_ROOT") if is_frozen_runtime else None
        setup_project_structure.setup_dirs(base_path=setup_base_path)
        ensure_default_settings(fail_fast=False)

        app = QApplication(sys.argv)
        app.setApplicationName("Consulta Rapida de SSAs")
        app.setApplicationDisplayName("Consulta Rapida de SSAs")
        window = SSAMainWindow()
        window.show()
        sys.exit(app.exec())
    except ImportError as e:
        log_launcher_failure("gui_entry", "Nao foi possivel importar modulos GUI", e)
        sys.stderr.write(
            "ERRO: Nao foi possivel iniciar a GUI. Consulte os logs da aplicacao.\n"
        )
        sys.stderr.write(
            "Dica: execute novamente pelo terminal para confirmar o ambiente de runtime.\n"
        )
        sys.exit(1)
    except Exception as e:
        log_launcher_failure("gui_entry", "Falha inesperada na GUI", e, include_trace=True)
        sys.stderr.write(
            "ERRO: Falha inesperada ao iniciar a GUI. Consulte os logs da aplicacao.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
