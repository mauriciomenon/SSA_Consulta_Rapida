from __future__ import annotations

# ruff: noqa: E402

import argparse
import concurrent.futures
import functools
import hashlib
import json
import pathlib
import platform
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
TARGETS_FILE = pathlib.Path(__file__).with_name("release_targets.json")
DEFAULT_TARGETS: dict[str, Any] = {
    "schema_version": 1,
    "backends": [
        {
            "name": "pyinstaller",
            "order": 1,
            "windows_amd64": True,
            "debian_amd64": True,
            "debian_arm64": True,
        },
        {
            "name": "nuitka",
            "order": 2,
            "windows_amd64": True,
            "debian_amd64": True,
            "debian_arm64": True,
        },
        {
            "name": "pyoxidizer",
            "order": 3,
            "windows_amd64": True,
            "debian_amd64": True,
            "debian_arm64": True,
        },
    ],
    "packages": [
        {"name": "deb", "order": 1, "debian_amd64": True, "debian_arm64": True},
        {
            "name": "appimage",
            "order": 2,
            "debian_amd64": True,
            "debian_arm64": True,
        },
        {"name": "tar", "order": 3, "debian_amd64": True, "debian_arm64": True},
        {"name": "zip", "order": 4, "windows_amd64": True},
    ],
    "unsupported_pairs": [
        {
            "platform": "debian_amd64",
            "backend": "pyoxidizer",
            "package": "appimage",
            "reason": "AppImage pyoxidizer nao suportado pelos scripts atuais.",
        },
        {
            "platform": "debian_arm64",
            "backend": "pyoxidizer",
            "package": "appimage",
            "reason": "AppImage pyoxidizer nao suportado pelos scripts atuais.",
        }
    ],
    "asset_name_templates": {
        "debian_amd64": {
            "deb": "ssa-consulta-rapida-{backend}-amd64_{app_version}_amd64.deb",
            "appimage": "SSA_Consulta_Rapida_v{app_version}_debian_amd64_{backend}.AppImage",
            "tar_split": "SSA_Consulta_Rapida_v{app_version}_debian_amd64_{backend}_{app}.tar.gz",
            "tar_single": "SSA_Consulta_Rapida_v{app_version}_debian_amd64_{backend}.tar.gz",
        },
        "debian_arm64": {
            "deb": "ssa-consulta-rapida-{backend}-arm64_{app_version}_arm64.deb",
            "appimage": "SSA_Consulta_Rapida_v{app_version}_debian_arm64_{backend}.AppImage",
            "tar_split": "SSA_Consulta_Rapida_v{app_version}_debian_arm64_{backend}_{app}.tar.gz",
            "tar_single": "SSA_Consulta_Rapida_v{app_version}_debian_arm64_{backend}.tar.gz",
        },
    },
}
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
PACKAGE_ASSET_SUFFIXES: dict[str, tuple[str, ...]] = {
    "appimage": (".AppImage",),
    "deb": (".deb",),
    "tar": (".tar.gz",),
    "zip": (".zip", ".exe", ".msi"),
}


@functools.lru_cache(maxsize=1)
def _load_scorecards() -> dict[str, dict[str, object]]:
    try:
        payload = json.loads(SCORECARD_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        logger.warning(
            "Falha ao carregar %s; usando defaults: %s",
            SCORECARD_FILE,
            exc,
        )
        return DEFAULT_SCORECARDS
    except (OSError, json.JSONDecodeError) as exc:
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


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseReportError(f"arquivo JSON ausente: {path}") from exc
    except OSError as exc:
        raise ReleaseReportError(f"falha lendo JSON {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseReportError(f"JSON invalido em {path}: {exc}") from exc


def _target_records(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    records = payload.get(key)
    if not isinstance(records, list) or not records:
        raise ReleaseReportError(f"{key} ausente ou invalido em {TARGETS_FILE}")
    checked = []
    names = set()
    for record in records:
        if not isinstance(record, dict):
            raise ReleaseReportError(f"{key} contem item invalido em {TARGETS_FILE}")
        name = str(record.get("name") or "").strip()
        order = record.get("order")
        if not name or not isinstance(order, int):
            raise ReleaseReportError(f"{key} contem nome/order invalido em {TARGETS_FILE}")
        if name in names:
            raise ReleaseReportError(f"{key} contem nome duplicado em {TARGETS_FILE}: {name}")
        names.add(name)
        checked.append(record)
    return sorted(checked, key=lambda item: int(item["order"]))


def _validate_release_targets_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise ReleaseReportError(f"schema_version invalido em {TARGETS_FILE}")
    backends = _target_records(payload, "backends")
    packages = _target_records(payload, "packages")
    backend_names = {str(item["name"]) for item in backends}
    package_names = {str(item["name"]) for item in packages}
    unsupported_pairs = payload.get("unsupported_pairs", [])
    if not isinstance(unsupported_pairs, list):
        raise ReleaseReportError(f"unsupported_pairs invalido em {TARGETS_FILE}")
    for pair in unsupported_pairs:
        if not isinstance(pair, dict):
            raise ReleaseReportError(f"unsupported_pairs contem item invalido em {TARGETS_FILE}")
        backend = str(pair.get("backend") or "")
        package = str(pair.get("package") or "")
        platform_name = str(pair.get("platform") or "")
        reason = str(pair.get("reason") or "")
        if backend not in backend_names or package not in package_names:
            raise ReleaseReportError(
                f"unsupported_pairs referencia alvo desconhecido em {TARGETS_FILE}"
            )
        if not platform_name or not reason:
            raise ReleaseReportError(
                f"unsupported_pairs exige platform e reason em {TARGETS_FILE}"
            )
    templates = payload.get("asset_name_templates", {})
    if templates and not isinstance(templates, dict):
        raise ReleaseReportError(f"asset_name_templates invalido em {TARGETS_FILE}")
    for platform_name, platform_templates in templates.items():
        if not isinstance(platform_name, str) or not isinstance(platform_templates, dict):
            raise ReleaseReportError(f"asset_name_templates contem item invalido em {TARGETS_FILE}")
        for key in ("deb", "appimage", "tar_split", "tar_single"):
            value = platform_templates.get(key)
            if not isinstance(value, str) or not value:
                raise ReleaseReportError(
                    f"asset_name_templates exige {platform_name}.{key} em {TARGETS_FILE}"
                )


def _load_release_targets() -> dict[str, Any]:
    try:
        payload = _read_json(TARGETS_FILE)
        _validate_release_targets_payload(payload)
    except ReleaseReportError as exc:
        logger.warning(
            "Falha ao carregar %s; usando defaults: %s",
            TARGETS_FILE,
            exc,
        )
        payload = DEFAULT_TARGETS
        _validate_release_targets_payload(payload)
    return payload


def _enabled_target_names(
    payload: dict[str, Any],
    key: str,
    platform_name: str,
) -> list[str]:
    return [
        str(record["name"])
        for record in _target_records(payload, key)
        if record.get(platform_name) is True
    ]


def _unsupported_pair_reason(
    payload: dict[str, Any],
    platform_name: str,
    backend: str,
    package: str,
) -> str | None:
    for pair in payload.get("unsupported_pairs", []):
        if not isinstance(pair, dict):
            continue
        if (
            pair.get("platform") == platform_name
            and pair.get("backend") == backend
            and pair.get("package") == package
        ):
            return str(pair["reason"])
    return None


def print_release_targets(args: argparse.Namespace) -> int:
    payload = _load_release_targets()
    key = "backends" if args.kind == "backends" else "packages"
    names = _enabled_target_names(payload, key, args.platform)
    if not names:
        raise ReleaseReportError(f"nenhum target {args.kind} para {args.platform}")
    print(",".join(names))
    return 0


def check_release_target(args: argparse.Namespace) -> int:
    payload = _load_release_targets()
    backend_names = _enabled_target_names(payload, "backends", args.platform)
    if args.backend not in backend_names:
        raise ReleaseReportError(f"backend invalido para {args.platform}: {args.backend}")
    if args.package:
        package_names = _enabled_target_names(payload, "packages", args.platform)
        if args.package not in package_names:
            raise ReleaseReportError(
                f"package invalido para {args.platform}: {args.package}"
            )
        reason = _unsupported_pair_reason(
            payload,
            args.platform,
            args.backend,
            args.package,
        )
        if reason:
            raise ReleaseReportError(reason)
    return 0


def print_release_target_reason(args: argparse.Namespace) -> int:
    payload = _load_release_targets()
    backend_names = _enabled_target_names(payload, "backends", args.platform)
    package_names = _enabled_target_names(payload, "packages", args.platform)
    if args.backend not in backend_names:
        raise ReleaseReportError(f"backend invalido para {args.platform}: {args.backend}")
    if args.package not in package_names:
        raise ReleaseReportError(f"package invalido para {args.platform}: {args.package}")
    reason = _unsupported_pair_reason(
        payload,
        args.platform,
        args.backend,
        args.package,
    )
    if reason:
        print(reason)
        return 0
    print("par backend/package suportado")
    return 0


def print_release_unsupported_pairs(args: argparse.Namespace) -> int:
    payload = _load_release_targets()
    for pair in payload.get("unsupported_pairs", []):
        if not isinstance(pair, dict) or pair.get("platform") != args.platform:
            continue
        print(f"{pair['backend']}\t{pair['package']}\t{pair['reason']}")
    return 0


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
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


def _expected_debian_asset_names(
    backends: list[str],
    packages: list[str],
    app_version: str,
    platform_name: str = "debian_amd64",
    package_arch: str = "amd64",
) -> set[str]:
    templates = _load_release_targets().get("asset_name_templates", {}).get(platform_name, {})
    if not isinstance(templates, dict) or not templates:
        templates = {
            "deb": (
                "ssa-consulta-rapida-{backend}-{package_arch}_"
                "{app_version}_{package_arch}.deb"
            ),
            "appimage": "SSA_Consulta_Rapida_v{app_version}_{platform_name}_{backend}.AppImage",
            "tar_split": (
                "SSA_Consulta_Rapida_v{app_version}_{platform_name}_{backend}_{app}.tar.gz"
            ),
            "tar_single": "SSA_Consulta_Rapida_v{app_version}_{platform_name}_{backend}.tar.gz",
        }
    names: set[str] = set()
    for backend in backends:
        if "deb" in packages:
            names.add(
                templates["deb"].format(
                    app_version=app_version,
                    backend=backend,
                    package_arch=package_arch,
                    platform_name=platform_name,
                )
            )
        if "appimage" in packages and backend != "pyoxidizer":
            names.add(
                templates["appimage"].format(
                    app_version=app_version,
                    backend=backend,
                    package_arch=package_arch,
                    platform_name=platform_name,
                )
            )
        if "tar" in packages:
            if backend in {"pyinstaller", "nuitka"}:
                for app in ("cli", "gui"):
                    names.add(
                        templates["tar_split"].format(
                            app=app,
                            app_version=app_version,
                            backend=backend,
                            package_arch=package_arch,
                            platform_name=platform_name,
                        )
                    )
            else:
                names.add(
                    templates["tar_single"].format(
                        app_version=app_version,
                        backend=backend,
                        package_arch=package_arch,
                        platform_name=platform_name,
                    )
                )
    return names


def _expected_asset_names(
    platform_name: str,
    backends: list[str],
    packages: list[str],
    app_version: str,
) -> set[str] | None:
    if platform_name == "debian_amd64":
        return _expected_debian_asset_names(
            backends,
            packages,
            app_version,
            "debian_amd64",
            "amd64",
        )
    if platform_name == "debian_arm64":
        return _expected_debian_asset_names(
            backends,
            packages,
            app_version,
            "debian_arm64",
            "arm64",
        )
    return None


def cmd_print_app_version(args: argparse.Namespace) -> int:
    payload = _read_json(args.version_file)
    version = str(payload.get("version_short") or "").strip()
    if not version:
        raise ReleaseReportError(f"version_short ausente em {args.version_file}")
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
        validate_source_protection(args.artifact, repo_root=args.repo_root)
    except (SourceExposureError, UnsupportedArtifactError) as exc:
        raise ReleaseReportError(str(exc)) from exc
    return 0


def _asset_suffixes_for_platform(platform_name: str) -> tuple[str, ...]:
    payload = _load_release_targets()
    packages = _enabled_target_names(payload, "packages", platform_name)
    suffixes: list[str] = []
    for package in packages:
        suffixes.extend(PACKAGE_ASSET_SUFFIXES.get(package, (f".{package}",)))
    return tuple(suffix.lower() for suffix in suffixes)


def _split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _asset_suffixes_for_packages(packages: list[str]) -> tuple[str, ...]:
    suffixes: list[str] = []
    for package in packages:
        suffixes.extend(PACKAGE_ASSET_SUFFIXES.get(package, (f".{package}",)))
    return tuple(suffix.lower() for suffix in suffixes)


def write_report(args: argparse.Namespace) -> int:
    backends = _split_csv(args.backends)
    packages = _split_csv(args.packages)
    package_dir = args.repo_root / "builds" / "packages" / args.platform
    assets = []
    if not package_dir.is_dir():
        raise ReleaseReportError(f"diretorio de pacotes ausente: {package_dir}")

    asset_suffixes = _asset_suffixes_for_packages(packages)
    expected_asset_names = _expected_asset_names(
        args.platform,
        backends,
        packages,
        args.app_version,
    )
    asset_paths = [
        path
        for path in sorted(package_dir.iterdir())
        if path.is_file() and path.name.lower().endswith(asset_suffixes)
        and (expected_asset_names is None or path.name in expected_asset_names)
    ]
    if asset_paths:
        workers = min(4, len(asset_paths))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            assets = list(executor.map(_asset_payload, asset_paths))

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

    targets = subparsers.add_parser("release-targets")
    targets.add_argument("--platform", required=True)
    targets.add_argument("--kind", choices=("backends", "packages"), required=True)
    targets.set_defaults(func=print_release_targets)

    check_target = subparsers.add_parser("check-release-target")
    check_target.add_argument("--platform", required=True)
    check_target.add_argument("--backend", required=True)
    check_target.add_argument("--package", default="")
    check_target.set_defaults(func=check_release_target)

    target_reason = subparsers.add_parser("release-target-reason")
    target_reason.add_argument("--platform", required=True)
    target_reason.add_argument("--backend", required=True)
    target_reason.add_argument("--package", required=True)
    target_reason.set_defaults(func=print_release_target_reason)

    unsupported_pairs = subparsers.add_parser("release-unsupported-pairs")
    unsupported_pairs.add_argument("--platform", required=True)
    unsupported_pairs.set_defaults(func=print_release_unsupported_pairs)

    source_protection = subparsers.add_parser("source-protection")
    source_protection.add_argument("--artifact", type=pathlib.Path, required=True)
    source_protection.add_argument("--repo-root", type=pathlib.Path, default=None)
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
