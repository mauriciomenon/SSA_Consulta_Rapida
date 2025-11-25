#!/usr/bin/env python3
"""
Teste rápido dos executáveis existentes
"""

import os
import subprocess
import time
from pathlib import Path

from version_info import REPO_ROOT, get_current_version

APP_VERSION = get_current_version()
DIST_BASE = REPO_ROOT / "launchers" / "dist"

def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] {level}: {msg}")

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
        log("✅ CLI encontrado")
        # Testar execução
        try:
            result = subprocess.run([str(cli_path), "--help"],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                log("✅ CLI executa corretamente")
            else:
                log(f"❌ CLI erro: {result.stderr}")
        except Exception as e:
            log(f"❌ CLI erro execução: {e}")
    else:
        log("❌ CLI não encontrado")

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
        log("✅ GUI encontrada")
        # Testar se não dá erro de import
        try:
            result = subprocess.run([str(gui_path)],
                                  capture_output=True, text=True, timeout=2)
            # Se não deu erro de módulo, está funcionando
            if "No module named" not in result.stderr:
                log("✅ GUI imports OK")
            else:
                log(f"❌ GUI erro módulo: {result.stderr}")
        except subprocess.TimeoutExpired:
            log("✅ GUI iniciou (timeout normal para GUI)")
        except Exception as e:
            log(f"❌ GUI erro: {e}")
    else:
        log("❌ GUI não encontrada")

def test_imports():
    """Testa imports críticos"""
    log("=== TESTE IMPORTS ===")

    # PoC GUI removida – somente verifica GUI principal se ainda existir
    try:
        from gui.gui_ssa import SSAMainWindow  # type: ignore
        log(f"✅ GUI principal importa OK (classe: {SSAMainWindow.__name__})")
    except Exception as e:  # pragma: no cover - diagnóstico
        log(f"ℹ️ GUI principal não disponível ou erro de import: {e}")

def list_dist_contents():
    """Lista conteúdo da pasta dist"""
    log("=== CONTEÚDO DIST ===")

    dist_path = DIST_BASE / "macos_arm64"
    if dist_path.exists():
        for item in dist_path.iterdir():
            log(f"📁 {item.name}")
    else:
        log("❌ Pasta dist não existe")

def main():
    log(f"TESTE RÁPIDO v{APP_VERSION}")
    list_dist_contents()
    test_imports()
    test_existing_executables()
    log("=== FIM DOS TESTES ===")

if __name__ == "__main__":
    main()
