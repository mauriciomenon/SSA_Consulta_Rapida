from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from utils.robust_logging import get_robust_logger

from .runtime_entry_helpers import GUI_SMOKE_OK_MARKER, SMOKE_TEST_ENV


logger = get_robust_logger().get_logger(__name__, "maintenance")


def _executable_name(base_name: str, platform_id: str) -> str:
    if platform_id == "windows_amd64":
        return f"{base_name}.exe"
    return base_name


@dataclass(frozen=True)
class SmokeValidationResult:
    ok: bool
    imported_rows: int
    returncode: int
    stdout: str = ""
    stderr: str = ""
    error: str = ""

    def details(self, max_chars: int = 500) -> str:
        detail = self.error or self.stderr or self.stdout
        return detail[:max_chars]


def run_cli_import_smoke(
    *,
    executable: Path | None = None,
    timeout: int = 120,
    repo_root: Path | None = None,
) -> SmokeValidationResult:
    root = repo_root or Path(__file__).resolve().parent.parent
    command = [
        sys.executable,
        str(root / "scripts" / "smoke_cli.py"),
        "--json",
    ]
    if executable is not None:
        command.extend(["--executable", str(executable)])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.error("Smoke funcional excedeu timeout de %ss", timeout)
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=124,
            error=f"Timeout ao executar smoke funcional apos {timeout}s",
        )
    except OSError as exc:
        logger.error("Falha ao executar smoke funcional: %s", exc)
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=1,
            error=f"Falha ao executar smoke funcional: {exc}",
        )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0:
        logger.error(
            "Smoke funcional retornou codigo %s: %s",
            result.returncode,
            (stderr or stdout)[:500],
        )
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=result.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    try:
        payload = json.loads(stdout)
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        imported_rows = int(summary.get("imported_rows", 0))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Smoke funcional gerou JSON invalido: %s", exc)
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=result.returncode,
            stdout=stdout,
            stderr=stderr,
            error=f"Saida JSON invalida do smoke funcional: {exc}",
        )

    if imported_rows < 1:
        logger.error("Smoke funcional terminou sem linhas importadas")
        return SmokeValidationResult(
            ok=False,
            imported_rows=imported_rows,
            returncode=result.returncode,
            stdout=stdout,
            stderr=stderr,
            error="Smoke funcional nao importou linhas",
        )
    logger.info("Smoke funcional importou %s linha(s)", imported_rows)
    return SmokeValidationResult(
        ok=True,
        imported_rows=imported_rows,
        returncode=result.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def run_gui_startup_smoke(
    *,
    executable: Path,
    timeout: int = 30,
    repo_root: Path | None = None,
) -> SmokeValidationResult:
    root = repo_root or Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env[SMOKE_TEST_ENV] = "1"
    try:
        result = subprocess.run(
            [str(executable)],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("Smoke GUI excedeu timeout de %ss", timeout)
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=124,
            error=f"Timeout ao executar smoke GUI apos {timeout}s",
        )
    except OSError as exc:
        logger.error("Falha ao executar smoke GUI: %s", exc)
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=1,
            error=f"Falha ao executar smoke GUI: {exc}",
        )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0 or GUI_SMOKE_OK_MARKER not in stdout:
        logger.error(
            "Smoke GUI falhou codigo=%s saida=%s",
            result.returncode,
            (stderr or stdout)[:500],
        )
        return SmokeValidationResult(
            ok=False,
            imported_rows=0,
            returncode=result.returncode,
            stdout=stdout,
            stderr=stderr,
            error="Smoke GUI nao confirmou startup do artefato",
        )
    logger.info("Smoke GUI confirmou startup do artefato")
    return SmokeValidationResult(
        ok=True,
        imported_rows=0,
        returncode=result.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def detect_build_platform() -> str:
    system = platform.system().lower()
    arch = platform.machine().lower()
    if system == "darwin":
        return "macos_arm64" if "arm" in arch or "aarch64" in arch else "macos_x64"
    if system == "windows":
        return "windows_amd64"
    if system == "linux":
        return "debian_arm64" if "arm" in arch or "aarch64" in arch else "debian_amd64"
    return "unknown"


def cli_executable_path(
    repo_root: Path,
    version: str,
    platform_name: str | None = None,
    *,
    simple: bool = False,
) -> Path:
    platform_id = platform_name or detect_build_platform()
    if simple:
        simple_name = _executable_name(f"SSA_CLI_v{version}_SIMPLES", platform_id)
        return (
            repo_root
            / "launchers"
            / "dist_simple"
            / f"SSA_CLI_v{version}_SIMPLES"
            / simple_name
        )
    cli_name = _executable_name(f"SSA_CLI_v{version}_{platform_id}", platform_id)
    return (
        repo_root
        / "launchers"
        / "dist"
        / platform_id
        / f"SSA_CLI_v{version}_{platform_id}"
        / cli_name
    )


def gui_executable_path(
    repo_root: Path,
    version: str,
    platform_name: str | None = None,
) -> Path:
    platform_id = platform_name or detect_build_platform()
    if platform_id.startswith("macos_"):
        return (
            repo_root
            / "launchers"
            / "dist"
            / platform_id
            / f"SSA_GUI_v{version}_{platform_id}.app"
            / "Contents"
            / "MacOS"
            / f"SSA_GUI_v{version}_{platform_id}"
        )
    gui_name = _executable_name(f"SSA_GUI_v{version}_{platform_id}", platform_id)
    return (
        repo_root
        / "launchers"
        / "dist"
        / platform_id
        / f"SSA_GUI_v{version}_{platform_id}"
        / gui_name
    )
