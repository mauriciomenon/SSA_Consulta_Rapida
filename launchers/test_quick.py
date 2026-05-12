#!/usr/bin/env python3
"""Teste rapido dos executaveis existentes."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ != "launchers":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "launchers"

from .logging_helpers import log_launcher_status  # noqa: E402
from .smoke_validation import (  # noqa: E402
    cli_executable_path,
    detect_build_platform,
    gui_executable_path,
    run_cli_import_smoke,
    run_gui_startup_smoke,
)
from .version_info import REPO_ROOT, get_current_version  # noqa: E402

APP_VERSION = get_current_version()
DIST_BASE = REPO_ROOT / "launchers" / "dist"


def run_functional_cli_smoke(cli_path: Path) -> bool:
    result = run_cli_import_smoke(executable=cli_path, repo_root=REPO_ROOT)
    if not result.ok:
        log_launcher_status(
            f"ERR CLI smoke funcional falhou: {result.details()}",
            "ERROR",
            timestamp=True,
        )
        return False
    log_launcher_status(
        f"OK CLI smoke funcional importou {result.imported_rows} linha(s)",
        timestamp=True,
    )
    return True


def test_existing_executables() -> bool:
    log_launcher_status("=== TESTE EXECUTAVEIS EXISTENTES ===", timestamp=True)
    platform_id = detect_build_platform()

    cli_path = cli_executable_path(REPO_ROOT, APP_VERSION, platform_id)
    log_launcher_status(f"Verificando CLI: {cli_path}", timestamp=True)
    if cli_path.exists():
        log_launcher_status("OK CLI encontrado", timestamp=True)
        cli_ok = run_functional_cli_smoke(cli_path)
    else:
        log_launcher_status("ERR CLI nao encontrado", "ERROR", timestamp=True)
        cli_ok = False

    gui_path = gui_executable_path(REPO_ROOT, APP_VERSION, platform_id)
    log_launcher_status(f"Verificando GUI: {gui_path}", timestamp=True)
    gui_ok = gui_path.exists()
    if gui_ok:
        log_launcher_status("OK GUI encontrada", timestamp=True)
        gui_result = run_gui_startup_smoke(executable=gui_path, repo_root=REPO_ROOT)
        gui_ok = gui_result.ok
        if not gui_ok:
            log_launcher_status(
                f"ERR Smoke GUI falhou: {gui_result.details()}",
                "ERROR",
                timestamp=True,
            )
    else:
        log_launcher_status("ERR GUI nao encontrada", "ERROR", timestamp=True)
    return cli_ok and gui_ok


def test_imports() -> bool:
    log_launcher_status("=== TESTE IMPORTS ===", timestamp=True)
    try:
        from gui.gui_ssa import SSAMainWindow

        log_launcher_status(
            f"OK GUI principal importa OK (classe: {SSAMainWindow.__name__})",
            timestamp=True,
        )
        return True
    except ImportError as exc:  # pragma: no cover - diagnostico
        log_launcher_status(
            f"INFO GUI principal nao disponivel ou erro de import: {exc}",
            timestamp=True,
        )
    except Exception as exc:  # pragma: no cover - diagnostico
        log_launcher_status(
            f"ERR Erro inesperado ao importar GUI principal: {exc}",
            "ERROR",
            timestamp=True,
        )
    return False


def list_dist_contents() -> bool:
    log_launcher_status("=== CONTEUDO DIST ===", timestamp=True)
    dist_path = DIST_BASE / detect_build_platform()
    if not dist_path.exists():
        log_launcher_status("ERR Pasta dist nao existe", "ERROR", timestamp=True)
        return False

    for item in dist_path.iterdir():
        log_launcher_status(f"DIR {item.name}", timestamp=True)
    return True


def main() -> int:
    log_launcher_status(f"TESTE RAPIDO v{APP_VERSION}", timestamp=True)
    results = [list_dist_contents(), test_imports(), test_existing_executables()]
    log_launcher_status("=== FIM DOS TESTES ===", timestamp=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
