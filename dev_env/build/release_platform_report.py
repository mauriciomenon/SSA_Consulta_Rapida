from __future__ import annotations

import argparse
import concurrent.futures
import functools
import hashlib
import json
import pathlib
import platform

try:
    from dev_env.build.source_protection import (
        SourceExposureError,
        UnsupportedArtifactError,
        validate_source_protection,
    )
except ModuleNotFoundError:
    from source_protection import (  # type: ignore[no-redef]
        SourceExposureError,
        UnsupportedArtifactError,
        validate_source_protection,
    )

from utils.robust_logging import get_robust_logger


logger = get_robust_logger().get_logger(__name__, "build")


class ReleaseReportError(RuntimeError):
    pass


SCORECARD_FILE = pathlib.Path(__file__).with_name("backend_scorecards.json")
DEFAULT_SCORECARDS: dict[str, dict[str, object]] = {
    "nuitka": {
        "easy_user_dirs_score": 4,
        "note": "Melhor protecao do codigo protegido por compilacao nativa; build mais lento.",
        "package_size_score": 3,
        "protected_release": True,
        "security_score": 4,
        "source_protection_score": 4,
    },
    "pyinstaller": {
        "easy_user_dirs_score": 5,
        "note": "Alta compatibilidade; nao e artefato protegido sem obfuscation.",
        "package_size_score": 4,
        "protected_release": False,
        "security_score": 2,
        "source_protection_score": 2,
    },
    "pyoxidizer": {
        "easy_user_dirs_score": 3,
        "note": "Empacotamento forte, mas requer embedding sem fonte Python exposta.",
        "package_size_score": 2,
        "protected_release": False,
        "security_score": 3,
        "source_protection_score": 3,
    },
}


@functools.lru_cache(maxsize=1)
def _load_scorecards() -> dict[str, dict[str, object]]:
    try:
        payload = json.loads(SCORECARD_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "Falha ao carregar %s; usando defaults: %s",
            SCORECARD_FILE,
            exc,
        )
        return DEFAULT_SCORECARDS
    if not isinstance(payload, dict):
        logger.warning("%s invalido; usando defaults.", SCORECARD_FILE)
        return DEFAULT_SCORECARDS
    return payload


def _read_json(path: pathlib.Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseReportError(f"arquivo JSON ausente: {path}") from exc
    except OSError as exc:
        raise ReleaseReportError(f"falha lendo JSON {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseReportError(f"JSON invalido em {path}: {exc}") from exc


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_payload(path: pathlib.Path) -> dict[str, object]:
    try:
        return {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }
    except OSError as exc:
        raise ReleaseReportError(f"falha lendo asset {path}: {exc}") from exc


def cmd_print_app_version(args: argparse.Namespace) -> int:
    payload = _read_json(args.version_file)
    version = str(payload.get("version_short") or "").strip()
    if not version:
        raise ReleaseReportError("version_short ausente em config/version.json")
    print(version)
    return 0


def validate_build_info(args: argparse.Namespace) -> int:
    payload = _read_json(args.build_info)
    errors = []
    expected = {
        "build_system": args.backend,
        "platform": args.platform,
        "app_version": args.app_version,
        "git_commit": args.git_commit,
    }
    for key, value in expected.items():
        if str(payload.get(key)) != value:
            errors.append(f"{key}={payload.get(key)!r}")
    if errors:
        joined = ", ".join(errors)
        raise ReleaseReportError(f"build_info invalido em {args.build_info}: {joined}")
    return 0


def print_scorecard(args: argparse.Namespace) -> int:
    scorecards = _load_scorecards()
    try:
        scorecard = scorecards[args.backend]
    except KeyError as exc:
        raise ReleaseReportError(f"backend desconhecido: {args.backend}") from exc
    print(json.dumps(scorecard, ensure_ascii=True, sort_keys=True))
    return 0


def validate_source_protection_command(args: argparse.Namespace) -> int:
    try:
        validate_source_protection(args.artifact)
    except (SourceExposureError, UnsupportedArtifactError) as exc:
        raise ReleaseReportError(str(exc)) from exc
    return 0


def write_report(args: argparse.Namespace) -> int:
    package_dir = args.repo_root / "builds" / "packages" / args.platform
    assets = []
    if package_dir.is_dir():
        asset_paths = [
            path
            for path in sorted(package_dir.iterdir())
            if path.is_file()
            and (
                path.suffix in {".AppImage", ".deb", ".exe", ".msi", ".zip"}
                or path.name.endswith(".tar.gz")
            )
        ]
        if asset_paths:
            workers = min(4, len(asset_paths))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                assets = list(executor.map(_asset_payload, asset_paths))

    backends = [item for item in args.backends.split(",") if item]
    packages = [item for item in args.packages.split(",") if item]
    scorecards = _load_scorecards()
    unknown_backends = [backend for backend in backends if backend not in scorecards]
    if unknown_backends:
        joined = ", ".join(unknown_backends)
        raise ReleaseReportError(f"backend desconhecido no report: {joined}")
    payload = {
        "platform": args.platform,
        "host_os": platform.platform(),
        "machine": platform.machine(),
        "app_version": args.app_version,
        "git_commit": args.git_commit,
        "backends": backends,
        "packages": packages,
        "scorecards": {backend: scorecards[backend] for backend in backends},
        "assets": assets,
    }
    args.report_file.parent.mkdir(parents=True, exist_ok=True)
    args.report_file.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    app_version = subparsers.add_parser("app-version")
    app_version.add_argument("--version-file", type=pathlib.Path, required=True)
    app_version.set_defaults(func=cmd_print_app_version)

    validate = subparsers.add_parser("validate-build-info")
    validate.add_argument("--build-info", type=pathlib.Path, required=True)
    validate.add_argument("--backend", required=True)
    validate.add_argument("--platform", required=True)
    validate.add_argument("--app-version", required=True)
    validate.add_argument("--git-commit", required=True)
    validate.set_defaults(func=validate_build_info)

    scorecard = subparsers.add_parser("scorecard")
    scorecard.add_argument("--backend", required=True)
    scorecard.set_defaults(func=print_scorecard)

    source_protection = subparsers.add_parser("source-protection")
    source_protection.add_argument("--artifact", type=pathlib.Path, required=True)
    source_protection.set_defaults(func=validate_source_protection_command)

    report = subparsers.add_parser("write-report")
    report.add_argument("--repo-root", type=pathlib.Path, required=True)
    report.add_argument("--report-file", type=pathlib.Path, required=True)
    report.add_argument("--platform", required=True)
    report.add_argument("--backends", required=True)
    report.add_argument("--packages", required=True)
    report.add_argument("--app-version", required=True)
    report.add_argument("--git-commit", required=True)
    report.set_defaults(func=write_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ReleaseReportError as exc:
        logger.error("Erro: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
