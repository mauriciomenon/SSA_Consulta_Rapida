#!/usr/bin/env python3
"""
Teste direto dos executaveis versionados.
"""

import subprocess
import sys
from pathlib import Path

import pytest

if __package__ != "launchers":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "launchers"

from .logging_helpers import log_launcher_status  # noqa: E402
from .smoke_validation import (  # noqa: E402
    cli_executable_path,
    detect_build_platform,
    run_cli_import_smoke,
)
from .version_info import REPO_ROOT, get_current_version  # noqa: E402


APP_VERSION = get_current_version()


def _executable_specs() -> list[dict[str, Path | str]]:
    platform_name = detect_build_platform()
    return [
        {
            "name": "CLI Multi-Plataforma",
            "path": cli_executable_path(REPO_ROOT, APP_VERSION, platform_name),
        },
        {
            "name": "CLI Simples",
            "path": cli_executable_path(REPO_ROOT, APP_VERSION, simple=True),
        },
    ]


# --- Fixtures -----------------------------------------------------------------
@pytest.fixture(params=_executable_specs())
def executable_spec(request):
    """Provides spec for each expected executable."""
    return request.param


@pytest.fixture
def exe_path(executable_spec):
    return executable_spec["path"]


@pytest.fixture
def name(executable_spec):
    return executable_spec["name"]


# --- Helper -------------------------------------------------------------------
def _check_executable(exe_path: Path, name: str) -> bool:
    log_launcher_status(f"=== Testando {name} ===")
    log_launcher_status(f"Path: {exe_path}")
    if not exe_path.exists():
        log_launcher_status(f"Executavel nao encontrado: {exe_path}", "WARN")
        return False
    # Verificar tipo (best-effort)
    try:
        result = subprocess.run(
            ["file", str(exe_path)], capture_output=True, text=True, timeout=3
        )
        if result.stdout:
            log_launcher_status(f"Tipo: {result.stdout.strip()}")
    except Exception as exc:
        log_launcher_status(f"Nao foi possivel identificar tipo: {exc}", "WARN")
    # Verificar tamanho do binario sem varrer diretorios externos.
    try:
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        log_launcher_status(f"Tamanho executavel: {size_mb:.1f}M")
    except OSError as exc:
        log_launcher_status(
            f"Nao foi possivel calcular tamanho do executavel: {exc}",
            "WARN",
        )
    log_launcher_status("Testando importacao funcional...")
    result = run_cli_import_smoke(executable=exe_path, repo_root=REPO_ROOT)
    log_launcher_status(f"Exit code: {result.returncode}")
    if result.stdout:
        log_launcher_status(f"STDOUT: {result.stdout[:200]}...")
    if result.stderr:
        log_launcher_status(f"STDERR: {result.stderr[:200]}...")
    if not result.ok:
        log_launcher_status(result.details(), "ERROR")
        return False
    log_launcher_status(f"OK Smoke funcional importou {result.imported_rows} linha(s)")
    return True


# --- Tests --------------------------------------------------------------------
@pytest.mark.smoke
def test_executable(exe_path, name):
    ok = _check_executable(exe_path, name)
    assert ok, f"Executable '{name}' ausente ou falhou no smoke funcional"


# Retem main for manual execution ------------------------------------------------
def main():  # pragma: no cover
    base_dir = Path(__file__).parent.parent
    log_launcher_status(f"=== Teste de Executaveis v{APP_VERSION} ===")
    log_launcher_status(f"Base: {base_dir}")
    results = []
    for spec in _executable_specs():
        n = str(spec["name"])
        p = Path(spec["path"])
        results.append((n, _check_executable(p, n)))
    log_launcher_status("=== RESUMO ===")
    for n, r in results:
        log_launcher_status(f"{n}: {'OK OK' if r else 'ERR ERRO'}")
    ok_all = all(r for _, r in results)
    if ok_all:
        log_launcher_status("DONE Todos os executaveis esperados funcionaram!")
        return 0
    log_launcher_status("Um ou mais executaveis falharam!", "ERROR")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
