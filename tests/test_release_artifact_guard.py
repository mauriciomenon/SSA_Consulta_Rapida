"""Guards to prevent generated artifacts from entering release branches."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from dev_env.build.source_protection import (
    SourceExposureError,
    validate_source_protection,
)


def _require_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git nao encontrado no ambiente")


def test_gitignore_blocks_sonar_directory():
    gitignore = Path(".gitignore")
    assert gitignore.exists(), ".gitignore deve existir"
    content = gitignore.read_text(encoding="utf-8")
    assert ".sonar/" in content or "\n.sonar\n" in content, (
        ".gitignore deve bloquear artefatos .sonar/"
    )


def test_sonar_directory_is_not_tracked():
    _require_git()
    result = subprocess.run(
        ["git", "ls-files", ".sonar"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git ls-files falhou: {result.stderr}"
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], f".sonar nao deve ter arquivos versionados: {tracked[:5]}"


def test_backup_artifacts_are_not_tracked():
    _require_git()
    tracked_result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked_result.returncode == 0, (
        f"git ls-files falhou: {tracked_result.stderr}"
    )

    tracked_files = {
        line.strip() for line in tracked_result.stdout.splitlines() if line.strip()
    }
    forbidden_tokens = [".backup_", ".py.bak_", ".py.planv", "_bkp_"]
    offenders = [
        path
        for path in sorted(tracked_files)
        if any(token in path for token in forbidden_tokens)
    ]
    assert offenders == [], (
        f"Arquivos de backup nao devem ser versionados: {offenders[:10]}"
    )


def test_source_protection_rejects_app_py_in_zip(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("bundle/core/app_logic.py", "print('leak')\n")
        archive.writestr("bundle/config/build_info.json", "{}")

    with pytest.raises(SourceExposureError, match="core/app_logic.py"):
        validate_source_protection(package)


def test_source_protection_rejects_app_pyc_in_directory(tmp_path: Path) -> None:
    exposed = tmp_path / "bundle" / "gui" / "__pycache__" / "gui_ssa.cpython-313.pyc"
    exposed.parent.mkdir(parents=True)
    exposed.write_bytes(b"pyc")

    with pytest.raises(SourceExposureError, match="gui_ssa.cpython-313.pyc"):
        validate_source_protection(tmp_path / "bundle")


def test_source_protection_allows_non_code_resources(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("bundle/docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md", "doc\n")
        archive.writestr("bundle/config/build_info.json", "{}")
        archive.writestr("bundle/resources/app_icon.ico", b"ico")

    validate_source_protection(package)


def test_source_protection_allows_third_party_package_paths(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("bundle/_internal/pandas/core/frame.py", "third party\n")
        archive.writestr("bundle/_internal/pkg_resources/_vendor/jaraco/context.py", "")

    validate_source_protection(package)
