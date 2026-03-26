#!/usr/bin/env python3
"""
Teste rápido dos executáveis existentes
"""

import subprocess
import time

from version_info import REPO_ROOT, get_current_version

from utils.robust_logging import get_robust_logger

APP_VERSION = get_current_version()
DIST_BASE = REPO_ROOT / "launchers" / "dist"
logger = get_robust_logger().get_logger(__name__, "maintenance")


def log(msg, level="INFO"):
    text = f"[{time.strftime('%H:%M:%S')}] {msg}"
    level_norm = str(level or "INFO").upper()
    if level_norm in {"ERR", "ERROR"}:
        logger.error(text)
    elif level_norm in {"WARN", "WARNING"}:
        logger.warning(text)
    elif level_norm in {"DEBUG"}:
        logger.debug(text)
    else:
        logger.info(text)


def test_existing_executables():
    """Testa executáveis já construídos"""
    log("=== TESTE EXECUTÁVEIS EXISTENTES ===")

    platform = "macos_arm64"
    base_path = DIST_BASE / platform

    # Verificar CLI
    cli_dir = base_path / f"SSA_CLI_v{APP_VERSION}_{platform}"
    cli_path = cli_dir / f"SSA_CLI_v{APP_VERSION}_{platform}"
    log(f"Verificando CLI: {cli_path}")

    if cli_path.exists():
        log("OK CLI encontrado")
        # Testar execução
        try:
            result = subprocess.run(
                [str(cli_path), "--help"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                log("OK CLI executa corretamente")
            else:
                log(f"ERR CLI erro: {result.stderr}")
        except Exception as e:
            log(f"ERR CLI erro execução: {e}")
    else:
        log("ERR CLI não encontrado")

    # Verificar GUI
    gui_path = (
        base_path
        / f"SSA_GUI_v{APP_VERSION}_{platform}.app"
        / "Contents"
        / "MacOS"
        / f"SSA_GUI_v{APP_VERSION}_{platform}"
    )
    log(f"Verificando GUI: {gui_path}")

    if gui_path.exists():
        log("OK GUI encontrada")
        # Testar se não dá erro de import
        try:
            result = subprocess.run(
                [str(gui_path)], capture_output=True, text=True, timeout=2
            )
            # Se não deu erro de módulo, está funcionando
            if "No module named" not in result.stderr:
                log("OK GUI imports OK")
            else:
                log(f"ERR GUI erro módulo: {result.stderr}")
        except subprocess.TimeoutExpired:
            log("OK GUI iniciou (timeout normal para GUI)")
        except Exception as e:
            log(f"ERR GUI erro: {e}")
    else:
        log("ERR GUI não encontrada")


def test_imports():
    """Testa imports críticos"""
    log("=== TESTE IMPORTS ===")

    # PoC GUI removida – somente verifica GUI principal se ainda existir
    try:
        from gui.gui_ssa import SSAMainWindow

        log(f"OK GUI principal importa OK (classe: {SSAMainWindow.__name__})")
    except ImportError as e:  # pragma: no cover - diagnostico
        log(f"INFO GUI principal nao disponivel ou erro de import: {e}")
    except Exception as e:  # pragma: no cover - diagnostico
        log(f"ERR Erro inesperado ao importar GUI principal: {e}")


def list_dist_contents():
    """Lista conteúdo da pasta dist"""
    log("=== CONTEÚDO DIST ===")

    dist_path = DIST_BASE / "macos_arm64"
    if dist_path.exists():
        for item in dist_path.iterdir():
            log(f"DIR {item.name}")
    else:
        log("ERR Pasta dist não existe")


def main():
    log(f"TESTE RÁPIDO v{APP_VERSION}")
    list_dist_contents()
    test_imports()
    test_existing_executables()
    log("=== FIM DOS TESTES ===")


if __name__ == "__main__":
    main()
