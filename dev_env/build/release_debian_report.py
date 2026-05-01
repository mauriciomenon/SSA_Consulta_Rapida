from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import platform
import sys


class ReleaseReportError(RuntimeError):
    pass


SCORECARDS = {
    "pyinstaller": {
        "security_score": 3,
        "python_source_exposure_score": 2,
        "easy_user_dirs_score": 5,
        "package_size_score": 4,
    },
    "nuitka": {
        "security_score": 4,
        "python_source_exposure_score": 4,
        "easy_user_dirs_score": 4,
        "package_size_score": 3,
    },
    "pyoxidizer": {
        "security_score": 4,
        "python_source_exposure_score": 3,
        "easy_user_dirs_score": 3,
        "package_size_score": 4,
    },
}


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
    try:
        scorecard = SCORECARDS[args.backend]
    except KeyError as exc:
        raise ReleaseReportError(f"backend desconhecido: {args.backend}") from exc
    print(json.dumps(scorecard, ensure_ascii=True, sort_keys=True))
    return 0


def write_report(args: argparse.Namespace) -> int:
    package_dir = args.repo_root / "builds" / "packages" / "debian_amd64"
    assets = []
    if package_dir.is_dir():
        asset_paths = [
            path
            for path in sorted(package_dir.iterdir())
            if path.is_file()
            and (path.suffix in {".deb", ".AppImage"} or path.name.endswith(".tar.gz"))
        ]
        if asset_paths:
            workers = min(4, len(asset_paths))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                assets = list(executor.map(_asset_payload, asset_paths))

    backends = [item for item in args.backends.split(",") if item]
    packages = [item for item in args.packages.split(",") if item]
    unknown_backends = [backend for backend in backends if backend not in SCORECARDS]
    if unknown_backends:
        joined = ", ".join(unknown_backends)
        raise ReleaseReportError(f"backend desconhecido no report: {joined}")
    payload = {
        "platform": "debian_amd64",
        "host_os": platform.platform(),
        "machine": platform.machine(),
        "app_version": args.app_version,
        "git_commit": args.git_commit,
        "backends": backends,
        "packages": packages,
        "scorecards": {backend: SCORECARDS[backend] for backend in backends},
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

    report = subparsers.add_parser("write-report")
    report.add_argument("--repo-root", type=pathlib.Path, required=True)
    report.add_argument("--report-file", type=pathlib.Path, required=True)
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
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
