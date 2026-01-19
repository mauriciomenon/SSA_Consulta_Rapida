#!/usr/bin/env python3
"""Teste completo dos executaveis gerados pelo build multiplataforma."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from version_info import REPO_ROOT, get_current_version

APP_VERSION = get_current_version()
DIST_DIR = REPO_ROOT / "launchers" / "dist"


def log(msg, level="INFO"):
    """Log formatado"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")


def run_command(cmd, timeout=30):
    """Executa comando com timeout"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"


def detect_platform():
    """Detecta plataforma atual"""
    import platform

    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "darwin":
        if "arm" in arch or "aarch64" in arch:
            return "macos_arm64"
        else:
            return "macos_x64"
    elif system == "windows":
        return "windows_amd64"
    elif system == "linux":
        return "debian_amd64"
    else:
        return "unknown"


def test_build_system():
    """Testa sistema de build"""
    log("=== TESTE DO SISTEMA DE BUILD ===")

    platform = detect_platform()
    log(f"Plataforma detectada: {platform}")

    # Verificar arquivos essenciais
    essential_files = [
        REPO_ROOT / "launchers" / "build_multiplatform.py",
        REPO_ROOT / "launchers" / "cli_entry.py",
        REPO_ROOT / "launchers" / "gui_entry.py",
        REPO_ROOT / "launchers" / "platforms" / platform / "build_config.json",
        REPO_ROOT / "launchers" / "platforms" / platform / "requirements.txt",
    ]

    missing_files = []
    for file in essential_files:
        if not file.exists():
            missing_files.append(str(file))

    if missing_files:
        log(f"ERRO: Arquivos essenciais faltando: {missing_files}", "ERROR")
        return False

    log("OK Todos os arquivos essenciais presentes")
    return True


def test_cli_build():
    """Testa build do CLI"""
    log("=== TESTE BUILD CLI ===")

    # Build CLI
    log("Construindo CLI...")
    success, stdout, stderr = run_command(
        "python launchers/build_multiplatform.py --apps cli", timeout=300
    )

    if not success:
        log(f"ERRO no build CLI: {stderr}", "ERROR")
        return False

    log("OK CLI construído com sucesso")

    # Verificar executável
    platform = detect_platform()
    cli_dir = DIST_DIR / platform / f"SSA_CLI_v{APP_VERSION}_{platform}"
    cli_path = cli_dir / f"SSA_CLI_v{APP_VERSION}_{platform}"

    if not cli_path.exists():
        log(f"ERRO: Executável CLI não encontrado em {cli_path}", "ERROR")
        return False

    log("OK Executável CLI encontrado")

    # Testar execução
    log("Testando execução do CLI...")
    success, stdout, stderr = run_command(f'"{cli_path}" --help', timeout=10)

    if not success:
        log(f"ERRO na execução CLI: {stderr}", "ERROR")
        return False

    log("OK CLI executa corretamente")
    return True


def test_gui_build():
    """Testa build da GUI"""
    log("=== TESTE BUILD GUI ===")

    # Build GUI
    log("Construindo GUI...")
    success, stdout, stderr = run_command(
        "python launchers/build_multiplatform.py --apps gui", timeout=300
    )

    if not success:
        log(f"ERRO no build GUI: {stderr}", "ERROR")
        return False

    log("OK GUI construída com sucesso")

    # Verificar executável
    platform = detect_platform()

    if platform == "macos_arm64":
        gui_path = (
            DIST_DIR
            / platform
            / f"SSA_GUI_v{APP_VERSION}_{platform}.app"
            / "Contents"
            / "MacOS"
            / f"SSA_GUI_v{APP_VERSION}_{platform}"
        )
    else:
        gui_dir = DIST_DIR / platform / f"SSA_GUI_v{APP_VERSION}_{platform}"
        gui_path = gui_dir / f"SSA_GUI_v{APP_VERSION}_{platform}"

    if not gui_path.exists():
        log(f"ERRO: Executável GUI não encontrado em {gui_path}", "ERROR")
        return False

    log("OK Executável GUI encontrado")

    # Testar importação (sem abrir janela)
    log("Testando imports da GUI...")
    script_lines = [
        "import sys",
        f"sys.path.insert(0, {repr(str(REPO_ROOT))})",
        "try:",
        "    from gui.gui_ssa import SSAMainWindow",
        "    print('OK Import GUI principal OK')",
        "except Exception as e:",
        "    print(f'ERR Erro import GUI: {e}')",
        "    raise",
    ]
    script = "\n".join(script_lines)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        log(f"ERRO: Imports da GUI falharam: {result.stderr or result.stdout}", "ERROR")
        return False

    log("OK Imports da GUI funcionam")
    return True


def test_module_dependencies():
    """Testa dependências de módulos"""
    log("=== TESTE DEPENDÊNCIAS MÓDULOS ===")

    critical_modules = [
        "PyQt6",
        "pandas",
        "openpyxl",
        "sqlite3",
        "secrets",
        "hashlib",
        "uuid",
        "datetime",
    ]

    failed_modules = []
    for module in critical_modules:
        try:
            __import__(module)
            log(f"OK {module}")
        except ImportError as e:
            log(f"ERR {module}: {e}", "ERROR")
            failed_modules.append(module)

    if failed_modules:
        log(f"ERRO: Módulos faltando: {failed_modules}", "ERROR")
        return False

    log("OK Todos os módulos críticos disponíveis")
    return True


def generate_test_report():
    """Gera relatório de teste"""
    log("=== GERANDO RELATÓRIO ===")

    platform = detect_platform()

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "tests": {},
        "build_info": {},
    }

    # Teste sistema de build
    report["tests"]["build_system"] = test_build_system()

    # Teste módulos
    report["tests"]["modules"] = test_module_dependencies()

    # Teste CLI
    report["tests"]["cli_build"] = test_cli_build()

    # Teste GUI
    report["tests"]["gui_build"] = test_gui_build()

    # Informações de build
    manifest_path = DIST_DIR / platform / "build_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            report["build_info"] = json.load(f)

    # Salvar relatório
    reports_dir = REPO_ROOT / "launchers" / "test_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"test_report_{platform}_{int(time.time())}.json"

    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log(f"Relatório salvo: {report_file}")

    # Resumo
    total_tests = len(report["tests"])
    passed_tests = sum(1 for result in report["tests"].values() if result)

    log("=== RESUMO DOS TESTES ===")
    log(f"Total: {total_tests}")
    log(f"Passou: {passed_tests}")
    log(f"Falhou: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        log("OK TODOS OS TESTES PASSARAM!", "SUCCESS")
        return True
    else:
        log("ERR ALGUNS TESTES FALHARAM!", "ERROR")
        return False


def main():
    """Executa todos os testes"""
    log(f"INICIANDO TESTES COMPLETOS v{APP_VERSION}")

    if not (REPO_ROOT / "launchers" / "build_multiplatform.py").exists():
        log("ERRO: Execute no diretório raiz do projeto", "ERROR")
        sys.exit(1)

    success = generate_test_report()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
