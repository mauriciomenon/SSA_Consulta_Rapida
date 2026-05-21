"""PAI provider backed by the external scrap_report SAM API flow."""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

PAI_SCRAP_REPORT_ROOT_ENV = "SSA_SCRAP_REPORT_ROOT"
PAI_ALLOW_SIBLING_ROOT_ENV = "SSA_ALLOW_SIBLING_SCRAP_REPORT"
PAI_SCRAP_REPORT_RUNNER_ENV = "SSA_SCRAP_REPORT_RUNNER"
PAI_DEFAULT_SCRAP_REPORT_DIRNAME = "scrap_report"
PAI_RUNNER_UV = "uv"
PAI_RUNNER_PYTHONPATH = "pythonpath"
PAI_DEFAULT_PROFILE = "panorama"
PAI_DEFAULT_NUMBER_OF_YEARS = 4
PAI_DEFAULT_LIMIT = 200
PAI_DEFAULT_API_TIMEOUT_SECONDS = 30.0
PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS = 180.0
PAI_OUTPUT_DIRNAME = "pai_api"
PAI_MANIFEST_FILENAME = "pai_sam_api_manifest.json"
PAI_XLSX_FILENAME = "pai_sam_api.xlsx"
PAI_CA_FILENAME = "itaipu_root_ca.pem"
PAI_CA_MANIFEST_FILENAME = "sam_api_cert.json"
PAI_EXPORT_XLSX_KEYS = ("data_xlsx", "xlsx")
PAI_ARTIFACT_FRESHNESS_TOLERANCE_SECONDS = 2.0

CompletedRunner = Callable[..., Any]


@dataclass(frozen=True)
class PaiScrapReportCompleted:
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PaiScrapReportRequest:
    project_root: Path
    output_dir: Path | None = None
    scrap_report_root: Path | None = None
    allow_sibling_scrap_report: bool = False
    runner: str = PAI_RUNNER_UV
    profile: str = PAI_DEFAULT_PROFILE
    executor_sectors: tuple[str, ...] = ()
    emitter_sectors: tuple[str, ...] = ()
    ssa_numbers: tuple[str, ...] = ()
    number_of_years: int = PAI_DEFAULT_NUMBER_OF_YEARS
    limit: int = PAI_DEFAULT_LIMIT
    ca_file: Path | None = None
    include_details: bool = False
    api_timeout_seconds: float = PAI_DEFAULT_API_TIMEOUT_SECONDS
    command_timeout_seconds: float = PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS


@dataclass(frozen=True)
class PaiScrapReportExport:
    command: tuple[str, ...]
    scrap_report_root: Path
    manifest_path: Path
    xlsx_path: Path
    manifest: Mapping[str, Any]
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PaiScrapReportCertificate:
    command: tuple[str, ...]
    scrap_report_root: Path
    ca_file: Path
    manifest_path: Path
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PaiScrapReportExecution:
    command_prefix: tuple[str, ...]
    cwd: Path
    scrap_report_root: Path | None
    env: Mapping[str, str] | None = None


def resolve_scrap_report_root(
    project_root: Path,
    *,
    override: Path | None = None,
    allow_sibling: bool = False,
) -> Path:
    candidate = override
    if candidate is None and allow_sibling:
        candidate = _sibling_scrap_report_root(project_root)
    if candidate is None:
        raise FileNotFoundError("scrap_report root was not provided.")
    root = candidate.expanduser().resolve(strict=False)
    cli_path = root / "src" / "scrap_report" / "cli.py"
    if not (root / "pyproject.toml").is_file() or not cli_path.is_file():
        raise FileNotFoundError(
            "Invalid scrap_report directory; missing pyproject.toml or "
            f"{cli_path}."
        )
    return root


def resolve_scrap_report_execution(
    project_root: Path,
    *,
    override: Path | None = None,
    allow_sibling: bool = False,
    runner: str = PAI_RUNNER_UV,
) -> PaiScrapReportExecution:
    root = _optional_scrap_report_root(
        project_root,
        override=override,
        allow_sibling=allow_sibling,
    )
    if root is not None:
        runner = str(runner or PAI_RUNNER_UV).strip().casefold()
        if runner == PAI_RUNNER_UV:
            uv_path = shutil.which("uv")
            if uv_path:
                return PaiScrapReportExecution(
                    command_prefix=(uv_path, "run", "--project", str(root), "python"),
                    cwd=root,
                    scrap_report_root=root,
                )
            raise FileNotFoundError(
                f"Runner {PAI_RUNNER_UV!r} solicitado, mas o binario uv nao foi encontrado."
            )
        if runner != PAI_RUNNER_PYTHONPATH:
            raise ValueError(
                f"Runner scrap_report invalido em {PAI_SCRAP_REPORT_RUNNER_ENV}: {runner}"
            )
        return PaiScrapReportExecution(
            command_prefix=(sys.executable,),
            cwd=root,
            scrap_report_root=root,
            env=_pythonpath_env(root),
        )
    if find_spec("scrap_report") is None:
        raise FileNotFoundError(
            "scrap_report nao esta instalado. Defina "
            f"{PAI_SCRAP_REPORT_ROOT_ENV} ou instale o pacote."
        )
    project = project_root.expanduser().resolve(strict=False)
    return PaiScrapReportExecution(
        command_prefix=(sys.executable, ),
        cwd=project,
        scrap_report_root=None,
    )


def build_pai_scrap_report_command(
    request: PaiScrapReportRequest,
) -> tuple[tuple[str, ...], PaiScrapReportExecution, Path, Path]:
    execution = resolve_scrap_report_execution(
        request.project_root,
        override=request.scrap_report_root,
        allow_sibling=request.allow_sibling_scrap_report,
        runner=request.runner,
    )
    output_dir = _resolve_output_dir(request)
    manifest_path = output_dir / PAI_MANIFEST_FILENAME
    xlsx_path = output_dir / PAI_XLSX_FILENAME

    command = [
        *execution.command_prefix,
        "-m",
        "scrap_report.cli",
        "sam-api-flow",
        "--profile",
        request.profile,
        "--number-of-years",
        str(request.number_of_years),
        "--limit",
        str(request.limit),
        "--timeout-seconds",
        str(request.api_timeout_seconds),
        "--output-json",
        str(manifest_path),
        "--output-xlsx",
        str(xlsx_path),
    ]
    _append_repeated_args(command, "--executor-sector", request.executor_sectors)
    _append_repeated_args(command, "--emitter-sector", request.emitter_sectors)
    _append_repeated_args(command, "--ssa-number", request.ssa_numbers)
    if request.include_details:
        command.append("--include-details")
    if request.ca_file is not None:
        command.extend(["--ca-file", str(request.ca_file.expanduser())])
    return tuple(command), execution, manifest_path, xlsx_path


def run_pai_scrap_report_export(
    request: PaiScrapReportRequest,
    *,
    runner: CompletedRunner = subprocess.run,
) -> PaiScrapReportExport:
    command, execution, manifest_path, fallback_xlsx_path = (
        build_pai_scrap_report_command(request)
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    command_started_at = time.time()
    for artifact in (manifest_path, fallback_xlsx_path):
        artifact.unlink(missing_ok=True)
    completed = _run_scrap_report_command(
        command,
        execution,
        timeout_seconds=request.command_timeout_seconds,
        runner=runner,
        label="sam-api-flow",
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest PAI nao criado nesta execucao: {manifest_path}")
    manifest = _load_manifest(manifest_path)
    xlsx_path = _resolve_xlsx_from_manifest(manifest, manifest_path, fallback_xlsx_path)
    if xlsx_path.stat().st_mtime < (
        command_started_at - PAI_ARTIFACT_FRESHNESS_TOLERANCE_SECONDS
    ):
        raise FileNotFoundError(f"XLSX PAI nao criado nesta execucao: {xlsx_path}")
    return PaiScrapReportExport(
        command=command,
        scrap_report_root=execution.scrap_report_root or execution.cwd,
        manifest_path=manifest_path,
        xlsx_path=xlsx_path,
        manifest=manifest,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_pai_scrap_report_ca_export(
    request: PaiScrapReportRequest,
    *,
    runner: CompletedRunner = subprocess.run,
) -> PaiScrapReportCertificate:
    execution = resolve_scrap_report_execution(
        request.project_root,
        override=request.scrap_report_root,
        allow_sibling=request.allow_sibling_scrap_report,
        runner=request.runner,
    )
    output_dir = _resolve_output_dir(request)
    output_dir.mkdir(parents=True, exist_ok=True)
    ca_file = output_dir / PAI_CA_FILENAME
    manifest_path = output_dir / PAI_CA_MANIFEST_FILENAME
    for artifact in (ca_file, manifest_path):
        artifact.unlink(missing_ok=True)
    command = (
        *execution.command_prefix,
        "-m",
        "scrap_report.cli",
        "sam-api-cert",
        "--output",
        str(ca_file),
        "--output-json",
        str(manifest_path),
        "--timeout-seconds",
        str(request.api_timeout_seconds),
    )
    completed = _run_scrap_report_command(
        command,
        execution,
        timeout_seconds=request.command_timeout_seconds,
        runner=runner,
        label="sam-api-cert",
    )
    if not ca_file.is_file():
        raise FileNotFoundError(f"CA PAI nao criada: {ca_file}")
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest de CA PAI nao criado nesta execucao: {manifest_path}"
        )
    return PaiScrapReportCertificate(
        command=command,
        scrap_report_root=execution.scrap_report_root or execution.cwd,
        ca_file=ca_file,
        manifest_path=manifest_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _run_scrap_report_command(
    command: tuple[str, ...],
    execution: PaiScrapReportExecution,
    *,
    timeout_seconds: float,
    runner: CompletedRunner,
    label: str,
) -> PaiScrapReportCompleted:
    completed = runner(
        list(command),
        cwd=str(execution.cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=execution.env,
    )
    stdout = str(getattr(completed, "stdout", "") or "")
    stderr = str(getattr(completed, "stderr", "") or "")
    returncode = int(getattr(completed, "returncode", 1))
    if returncode != 0:
        raise RuntimeError(
            f"scrap_report {label} falhou "
            f"(exit={returncode}): {stderr.strip() or stdout.strip()}"
        )
    return PaiScrapReportCompleted(stdout=stdout, stderr=stderr)


def _optional_scrap_report_root(
    project_root: Path,
    *,
    override: Path | None = None,
    allow_sibling: bool = False,
) -> Path | None:
    if override is not None:
        return resolve_scrap_report_root(project_root, override=override)
    sibling = _sibling_scrap_report_root(project_root)
    if allow_sibling and _looks_like_scrap_report_root(sibling):
        return resolve_scrap_report_root(
            project_root,
            override=sibling,
            allow_sibling=True,
        )
    return None


def _sibling_scrap_report_root(project_root: Path) -> Path:
    return project_root.expanduser().resolve(strict=False).parent / PAI_DEFAULT_SCRAP_REPORT_DIRNAME


def _looks_like_scrap_report_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (
        path / "src" / "scrap_report" / "cli.py"
    ).is_file()


def _pythonpath_env(root: Path) -> Mapping[str, str]:
    env = dict(os.environ)
    src_path = str(root / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not current else f"{src_path}{os.pathsep}{current}"
    return env


def _resolve_output_dir(request: PaiScrapReportRequest) -> Path:
    if request.output_dir is not None:
        return request.output_dir.expanduser().resolve(strict=False)
    return (
        request.project_root.expanduser().resolve(strict=False)
        / "tmp"
        / PAI_OUTPUT_DIRNAME
    )


def _append_repeated_args(
    command: list[str],
    option: str,
    values: Sequence[str],
) -> None:
    for value in values:
        clean_value = str(value or "").strip()
        if clean_value:
            command.extend([option, clean_value])


def _load_manifest(manifest_path: Path) -> Mapping[str, Any]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest PAI nao criado: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest PAI invalido: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest PAI nao e objeto JSON: {manifest_path}")
    status = str(payload.get("status", "ok")).casefold()
    if status != "ok":
        raise RuntimeError(f"Manifest PAI retornou status={status}: {manifest_path}")
    return payload


def _resolve_xlsx_from_manifest(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    fallback_xlsx_path: Path,
) -> Path:
    exports = manifest.get("exports")
    if not isinstance(exports, Mapping):
        exports = {}
    raw_xlsx = next(
        (exports.get(key) for key in PAI_EXPORT_XLSX_KEYS if exports.get(key)),
        str(fallback_xlsx_path),
    )
    xlsx_path = Path(str(raw_xlsx)).expanduser()
    if not xlsx_path.is_absolute():
        xlsx_path = manifest_path.parent / xlsx_path
    xlsx_path = xlsx_path.resolve(strict=False)
    expected_dir = manifest_path.parent.resolve(strict=False)
    if not xlsx_path.is_relative_to(expected_dir):
        raise ValueError(f"Export PAI fora do diretorio esperado: {xlsx_path}")
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"XLSX PAI nao criado: {xlsx_path}")
    if xlsx_path.suffix.casefold() != ".xlsx":
        raise ValueError(f"Export PAI nao aponta para XLSX: {xlsx_path}")
    return xlsx_path
