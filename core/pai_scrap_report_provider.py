"""PAI provider backed by the external scrap_report SAM API flow."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

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
PAI_SWEEP_DOWNLOAD_DIRNAME = "downloads"
PAI_SWEEP_STAGING_DIRNAME = "staging"
PAI_CA_FILENAME = "itaipu_root_ca.pem"
PAI_CA_MANIFEST_FILENAME = "sam_api_cert.json"
PAI_EXPORT_XLSX_KEYS = ("data_xlsx", "xlsx")
PAI_ARTIFACT_FRESHNESS_TOLERANCE_SECONDS = 2.0
PAI_DATA_SCOPE_CONSULTA = "consulta"
PAI_DATA_SCOPE_EXECUTADAS = "executadas"
PAI_DATA_SCOPE_APROVACAO = "aprovacao"
PAI_REPORT_KIND_EXECUTADAS = "executadas"
PAI_REPORT_KIND_APROVACAO_EMISSAO = "aprovacao_emissao"
PAI_REPORT_KIND_APROVACAO_CANCELAMENTO = "aprovacao_cancelamento"
PAI_SWEEP_SCOPE_MODE_EXECUTOR = "executor"
PAI_SWEEP_RUNTIME_PLAYWRIGHT = "playwright"
PAI_EXACT_SWEEP_REPORT_KINDS = frozenset(
    {
        PAI_REPORT_KIND_EXECUTADAS,
        PAI_REPORT_KIND_APROVACAO_EMISSAO,
        PAI_REPORT_KIND_APROVACAO_CANCELAMENTO,
    }
)

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
    data_scope: str = PAI_DATA_SCOPE_CONSULTA
    report_kind: str | None = None
    base_url: str | None = None
    username: str | None = None
    secret_service: str | None = None
    secure_required: bool = False


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


def run_pai_scrap_report_secret_set(
    *,
    project_root: Path,
    username: str,
    password: str,
    secret_service: str,
    scrap_report_root: Path | None = None,
    allow_sibling_scrap_report: bool = True,
    runner: str = PAI_RUNNER_UV,
    command_timeout_seconds: float = PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS,
    completed_runner: CompletedRunner = subprocess.run,
) -> None:
    execution = resolve_scrap_report_execution(
        project_root,
        override=scrap_report_root,
        allow_sibling=allow_sibling_scrap_report,
        runner=runner,
    )
    command = (
        *execution.command_prefix,
        "-c",
        (
            "import sys; "
            "from scrap_report.secret_provider import build_secret_provider; "
            "provider = build_secret_provider(); "
            "provider.set_secret(sys.argv[1], sys.argv[2], sys.stdin.read());"
        ),
        str(secret_service).strip(),
        str(username).strip(),
    )
    completed = completed_runner(
        list(command),
        cwd=str(execution.cwd),
        capture_output=True,
        text=True,
        timeout=command_timeout_seconds,
        check=False,
        env=execution.env,
        input=str(password),
    )
    stdout = str(getattr(completed, "stdout", "") or "")
    stderr = str(getattr(completed, "stderr", "") or "")
    returncode = int(getattr(completed, "returncode", 1))
    if returncode != 0:
        _raise_scrap_report_failure(
            label="secret set",
            returncode=returncode,
            stderr=stderr,
            stdout=stdout,
        )


def run_pai_scrap_report_secret_validate(
    *,
    project_root: Path,
    username: str,
    secret_service: str,
    scrap_report_root: Path | None = None,
    allow_sibling_scrap_report: bool = True,
    runner: str = PAI_RUNNER_UV,
    command_timeout_seconds: float = PAI_DEFAULT_COMMAND_TIMEOUT_SECONDS,
    completed_runner: CompletedRunner = subprocess.run,
) -> None:
    execution = resolve_scrap_report_execution(
        project_root,
        override=scrap_report_root,
        allow_sibling=allow_sibling_scrap_report,
        runner=runner,
    )
    command = (
        *execution.command_prefix,
        "-c",
        (
            "import sys; "
            "from scrap_report.secret_provider import build_secret_provider; "
            "provider = build_secret_provider(); "
            "provider.get_secret(sys.argv[1], sys.argv[2]);"
        ),
        str(secret_service).strip(),
        str(username).strip(),
    )
    _run_scrap_report_command(
        command,
        execution,
        timeout_seconds=command_timeout_seconds,
        runner=completed_runner,
        label="secret validate",
    )


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
    if not _looks_like_scrap_report_root(root):
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
                    command_prefix=(
                        uv_path,
                        "run",
                        "--active",
                        "--project",
                        str(root),
                        "python",
                    ),
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
    data_scope = _normalized_data_scope(request)
    if data_scope != PAI_DATA_SCOPE_CONSULTA or str(request.report_kind or "").strip():
        command = _build_pai_sweep_run_command(
            request,
            execution=execution,
            manifest_path=manifest_path,
            output_dir=output_dir,
        )
        return command, execution, manifest_path, xlsx_path

    command = [
        *execution.command_prefix,
        "-m",
        "scrap_report.cli",
        "sam-api-flow",
        "--profile",
        request.profile,
        "--base-url",
        str(request.base_url or "").strip() or "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API",
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


def _build_pai_sweep_run_command(
    request: PaiScrapReportRequest,
    *,
    execution: PaiScrapReportExecution,
    manifest_path: Path,
    output_dir: Path,
) -> tuple[str, ...]:
    report_kind = _sweep_report_kind(request)
    username = str(request.username or "").strip()
    if request.secure_required and not username:
        raise ValueError("Usuario SAM obrigatorio para executar xpath seguro.")
    command = [
        *execution.command_prefix,
        "-m",
        "scrap_report.cli",
        "sweep-run",
        "--report-kind",
        report_kind,
        "--scope-mode",
        PAI_SWEEP_SCOPE_MODE_EXECUTOR,
        "--runtime",
        PAI_SWEEP_RUNTIME_PLAYWRIGHT,
        "--number-of-years",
        str(request.number_of_years),
        "--limit",
        str(request.limit),
        "--download-dir",
        str(output_dir / PAI_SWEEP_DOWNLOAD_DIRNAME),
        "--staging-dir",
        str(output_dir / PAI_SWEEP_STAGING_DIRNAME),
        "--output-json",
        str(manifest_path),
    ]
    _append_nargs_args(command, "--setores-executor", request.executor_sectors)
    _append_nargs_args(command, "--setores-emissor", request.emitter_sectors)
    if request.ssa_numbers:
        if len(request.ssa_numbers) > 1:
            raise ValueError("sweep-run aceita apenas um numero de SSA por execucao.")
        command.extend(["--numero-ssa", request.ssa_numbers[0]])
    if username:
        command.extend(["--username", username])
    secret_service = str(request.secret_service or "").strip()
    if secret_service:
        command.extend(["--secret-service", secret_service])
    if request.secure_required:
        command.append("--secure-required")
    return tuple(command)


def _sweep_report_kind(request: PaiScrapReportRequest) -> str:
    report_kind = str(request.report_kind or "").strip()
    if report_kind:
        if report_kind not in PAI_EXACT_SWEEP_REPORT_KINDS:
            raise ValueError(f"report_kind SAM API xpath invalido: {report_kind}")
        return report_kind
    data_scope = _normalized_data_scope(request)
    if data_scope == PAI_DATA_SCOPE_EXECUTADAS:
        return PAI_REPORT_KIND_EXECUTADAS
    if data_scope == PAI_DATA_SCOPE_APROVACAO:
        raise ValueError(
            "Escopo aprovacao exige report_kind explicito: "
            "aprovacao_emissao ou aprovacao_cancelamento."
        )
    raise ValueError(f"Escopo SAM API xpath invalido: {data_scope}")


def _normalized_data_scope(request: PaiScrapReportRequest) -> str:
    return str(request.data_scope or PAI_DATA_SCOPE_CONSULTA).strip().casefold()


def run_pai_scrap_report_export(
    request: PaiScrapReportRequest,
    *,
    runner: CompletedRunner = subprocess.run,
) -> PaiScrapReportExport:
    command, execution, manifest_path, fallback_xlsx_path = (
        build_pai_scrap_report_command(request)
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    for artifact in (manifest_path, fallback_xlsx_path):
        artifact.unlink(missing_ok=True)
    command_started_at = time.time()
    command_label = "sweep-run" if "sweep-run" in command else "sam-api-flow"
    completed = _run_scrap_report_command(
        command,
        execution,
        timeout_seconds=request.command_timeout_seconds,
        runner=runner,
        label=command_label,
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest SAM API nao criado nesta execucao: {manifest_path}"
        )
    manifest = _load_manifest(manifest_path)
    xlsx_path = _resolve_xlsx_from_manifest(manifest, manifest_path, fallback_xlsx_path)
    if (
        xlsx_path.stat().st_mtime
        < command_started_at - PAI_ARTIFACT_FRESHNESS_TOLERANCE_SECONDS
    ):
        raise FileNotFoundError(f"XLSX SAM API nao criado nesta execucao: {xlsx_path}")
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
        *_sam_api_cert_host_args(request.base_url),
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
        raise FileNotFoundError(f"CA SAM API nao criada: {ca_file}")
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest de CA SAM API nao criado nesta execucao: {manifest_path}"
        )
    _load_manifest(manifest_path)
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
        _raise_scrap_report_failure(
            label=label,
            returncode=returncode,
            stderr=stderr,
            stdout=stdout,
        )
    return PaiScrapReportCompleted(stdout=stdout, stderr=stderr)


def _command_failure_detail(*, stderr: str, stdout: str) -> str:
    noise_prefixes = (
        "warning: `virtual_env=",
        "building ",
        "built ",
        "prepared ",
        "resolved ",
        "installed ",
        "uninstalled ",
        "downloaded ",
        "downloading ",
    )
    for raw_text in (stdout, stderr):
        stripped_text = str(raw_text or "").strip()
        if not stripped_text:
            continue
        try:
            payload = json.loads(stripped_text)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            message = " ".join(str(payload.get("message", "") or "").split()).strip()
            if message:
                return message

    for raw_text in (stderr, stdout):
        for raw_line in raw_text.splitlines():
            stripped = " ".join(raw_line.split()).strip()
            if not stripped:
                continue
            lowered = stripped.casefold()
            if lowered.startswith(noise_prefixes):
                continue
            redacted = re.sub(
                r"(?i)\b(password|token|secret|senha)(\s*[:=]\s*)(\S+)",
                r"\1\2<redacted>",
                stripped,
            )
            if len(redacted) > 180:
                return f"{redacted[:177]}..."
            return redacted
    return "sem detalhe textual"


def _raise_scrap_report_failure(
    *,
    label: str,
    returncode: int,
    stderr: str,
    stdout: str,
) -> None:
    stderr_state = "present" if stderr.strip() else "empty"
    stdout_state = "present" if stdout.strip() else "empty"
    failure_detail = _command_failure_detail(stderr=stderr, stdout=stdout)
    raise RuntimeError(
        f"scrap_report {label} falhou "
        f"(exit={returncode}, stderr={stderr_state}, stdout={stdout_state}, "
        f"detail={failure_detail})."
    )


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


def _sam_api_cert_host_args(base_url: str | None) -> tuple[str, ...]:
    base = str(base_url or "").strip()
    if not base:
        return ()
    try:
        host = str(urlparse(base).hostname or "").strip()
    except Exception:
        host = ""
    if not host:
        return ()
    return ("--host", host)


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


def _append_nargs_args(
    command: list[str],
    option: str,
    values: Sequence[str],
) -> None:
    clean_values = [str(value or "").strip() for value in values]
    clean_values = [value for value in clean_values if value]
    if clean_values:
        command.append(option)
        command.extend(clean_values)


def _load_manifest(manifest_path: Path) -> Mapping[str, Any]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest SAM API nao criado: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest SAM API invalido: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest SAM API nao e objeto JSON: {manifest_path}")
    status = str(payload.get("status", "ok")).casefold()
    if status != "ok":
        raise RuntimeError(
            f"Manifest SAM API retornou status={status}: {manifest_path}"
        )
    return payload


def _resolve_xlsx_from_manifest(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    fallback_xlsx_path: Path,
) -> Path:
    manifest_xlsx = next(_iter_manifest_xlsx_candidates(manifest), None)
    if manifest_xlsx is None:
        xlsx_path = fallback_xlsx_path.expanduser()
    else:
        xlsx_path = Path(str(manifest_xlsx)).expanduser()
        if not xlsx_path.is_absolute() and ".." in xlsx_path.parts:
            raise ValueError(
                f"Export SAM API com caminho relativo invalido: {xlsx_path}"
            )
        if not xlsx_path.is_absolute():
            xlsx_path = manifest_path.parent / xlsx_path
    xlsx_path = xlsx_path.resolve(strict=False)
    expected_dir = manifest_path.parent.resolve(strict=False)
    if not xlsx_path.is_relative_to(expected_dir):
        raise ValueError(f"Export SAM API fora do diretorio esperado: {xlsx_path}")
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"XLSX SAM API nao criado: {xlsx_path}")
    if xlsx_path.suffix.casefold() != ".xlsx":
        raise ValueError(f"Export SAM API nao aponta para XLSX: {xlsx_path}")
    return xlsx_path


def _iter_manifest_xlsx_candidates(manifest: Mapping[str, Any]):
    containers: list[Mapping[str, Any]] = []
    exports = manifest.get("exports")
    if isinstance(exports, Mapping):
        containers.append(exports)
    items = manifest.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            reports = item.get("reports")
            artifacts = item.get("available_artifacts")
            if isinstance(reports, Mapping):
                containers.append(reports)
            if isinstance(artifacts, Mapping):
                containers.append(artifacts)
    for container in containers:
        for key in PAI_EXPORT_XLSX_KEYS:
            if container.get(key):
                yield container[key]
