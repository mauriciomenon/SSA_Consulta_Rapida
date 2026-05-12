#!/usr/bin/env python3
"""Teste completo dos executaveis gerados pelo build multiplataforma."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

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
DIST_DIR = REPO_ROOT / "launchers" / "dist"


def run_command(cmd: str | list[str], timeout: int = 30) -> tuple[bool, str, str]:
    try:
        run_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
        result = subprocess.run(
            run_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"


def validate_cli_functional_import(cli_path: Path) -> tuple[bool, str]:
    result = run_cli_import_smoke(executable=cli_path, repo_root=REPO_ROOT)
    return result.ok, result.details()


def detect_platform() -> str:
    return detect_build_platform()


def test_build_system() -> bool:
    log_launcher_status("=== TESTE DO SISTEMA DE BUILD ===", timestamp=True)
    platform_id = detect_platform()
    log_launcher_status(f"Plataforma detectada: {platform_id}", timestamp=True)

    essential_files = [
        REPO_ROOT / "launchers" / "build_multiplatform.py",
        REPO_ROOT / "launchers" / "cli_entry.py",
        REPO_ROOT / "launchers" / "gui_entry.py",
        REPO_ROOT / "launchers" / "platforms" / platform_id / "build_config.json",
        REPO_ROOT / "launchers" / "platforms" / platform_id / "requirements.txt",
    ]

    missing_files = [str(file_path) for file_path in essential_files if not file_path.exists()]
    if missing_files:
        log_launcher_status(
            f"ERRO: Arquivos essenciais faltando: {missing_files}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK Todos os arquivos essenciais presentes", timestamp=True)
    return True


def test_cli_build() -> bool:
    log_launcher_status("=== TESTE BUILD CLI ===", timestamp=True)
    log_launcher_status("Construindo CLI...", timestamp=True)
    success, _stdout, stderr = run_command(
        [sys.executable, "launchers/build_multiplatform.py", "--apps", "cli"],
        timeout=300,
    )

    if not success:
        log_launcher_status(f"ERRO no build CLI: {stderr}", "ERROR", timestamp=True)
        return False

    log_launcher_status("OK CLI construido com sucesso", timestamp=True)
    platform_id = detect_platform()
    cli_path = cli_executable_path(REPO_ROOT, APP_VERSION, platform_id)

    if not cli_path.exists():
        log_launcher_status(
            f"ERRO: Executavel CLI nao encontrado em {cli_path}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK Executavel CLI encontrado", timestamp=True)
    log_launcher_status("Testando importacao funcional do CLI...", timestamp=True)
    success, details = validate_cli_functional_import(cli_path)

    if not success:
        log_launcher_status(
            f"ERRO no smoke funcional CLI: {details}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK CLI importou XLSX real corretamente", timestamp=True)
    return True


def test_gui_build() -> bool:
    log_launcher_status("=== TESTE BUILD GUI ===", timestamp=True)
    log_launcher_status("Construindo GUI...", timestamp=True)
    success, _stdout, stderr = run_command(
        [sys.executable, "launchers/build_multiplatform.py", "--apps", "gui"],
        timeout=300,
    )

    if not success:
        log_launcher_status(f"ERRO no build GUI: {stderr}", "ERROR", timestamp=True)
        return False

    log_launcher_status("OK GUI construida com sucesso", timestamp=True)
    platform_id = detect_platform()
    gui_path = gui_executable_path(REPO_ROOT, APP_VERSION, platform_id)

    if not gui_path.exists():
        log_launcher_status(
            f"ERRO: Executavel GUI nao encontrado em {gui_path}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK Executavel GUI encontrado", timestamp=True)
    log_launcher_status("Testando smoke GUI do artefato...", timestamp=True)
    result = run_gui_startup_smoke(executable=gui_path, repo_root=REPO_ROOT)
    if not result.ok:
        log_launcher_status(
            f"ERRO: Smoke GUI falhou: {result.details()}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK Smoke GUI do artefato confirmou startup", timestamp=True)
    return True


def test_module_dependencies() -> bool:
    log_launcher_status("=== TESTE DEPENDENCIAS MODULOS ===", timestamp=True)
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
            log_launcher_status(f"OK {module}", timestamp=True)
        except ImportError as exc:
            log_launcher_status(f"ERR {module}: {exc}", "ERROR", timestamp=True)
            failed_modules.append(module)

    if failed_modules:
        log_launcher_status(
            f"ERRO: Modulos faltando: {failed_modules}",
            "ERROR",
            timestamp=True,
        )
        return False

    log_launcher_status("OK Todos os modulos criticos disponiveis", timestamp=True)
    return True


def generate_test_report() -> bool:
    log_launcher_status("=== GERANDO RELATORIO ===", timestamp=True)
    platform_id = detect_platform()
    report: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform_id,
        "tests": {},
        "build_info": {},
    }

    tests = {
        "build_system": test_build_system(),
        "modules": test_module_dependencies(),
        "cli_build": test_cli_build(),
        "gui_build": test_gui_build(),
    }
    report["tests"] = tests

    manifest_path = DIST_DIR / platform_id / "build_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as file:
            report["build_info"] = json.load(file)

    reports_dir = REPO_ROOT / "launchers" / "test_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"test_report_{platform_id}_{int(time.time())}.json"
    with report_file.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    log_launcher_status(f"Relatorio salvo: {report_file}", timestamp=True)
    total_tests = len(tests)
    passed_tests = sum(1 for result in tests.values() if result)

    log_launcher_status("=== RESUMO DOS TESTES ===", timestamp=True)
    log_launcher_status(f"Total: {total_tests}", timestamp=True)
    log_launcher_status(f"Passou: {passed_tests}", timestamp=True)
    log_launcher_status(f"Falhou: {total_tests - passed_tests}", timestamp=True)

    if passed_tests == total_tests:
        log_launcher_status("OK TODOS OS TESTES PASSARAM!", timestamp=True)
        return True

    log_launcher_status("ERR ALGUNS TESTES FALHARAM!", "ERROR", timestamp=True)
    return False


def main() -> None:
    log_launcher_status(f"INICIANDO TESTES COMPLETOS v{APP_VERSION}", timestamp=True)
    if not (REPO_ROOT / "launchers" / "build_multiplatform.py").exists():
        log_launcher_status(
            "ERRO: Execute no diretorio raiz do projeto",
            "ERROR",
            timestamp=True,
        )
        sys.exit(1)

    success = generate_test_report()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
