"""Guards to prevent generated artifacts from entering release branches."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from dev_env.build import source_protection
from dev_env.build.source_protection import (
    SourceExposureError,
    _artifact_source_name,
    _source_candidates_from_name,
    _tracked_python_sources,
    validate_source_protection,
)
from tests.release_script_assertions import section_between


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


def test_sensitive_input_spreadsheets_are_not_tracked():
    _require_git()
    tracked_result = subprocess.run(
        ["git", "ls-files", "docs_entrada"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked_result.returncode == 0, (
        f"git ls-files falhou: {tracked_result.stderr}"
    )

    tracked_spreadsheets = [
        line.strip()
        for line in tracked_result.stdout.splitlines()
        if line.strip().lower().endswith((".xls", ".xlsx"))
    ]
    assert tracked_spreadsheets == [], (
        "Planilhas reais de docs_entrada nao devem ser versionadas: "
        f"{tracked_spreadsheets[:10]}"
    )


def test_source_protection_rejects_app_py_in_zip(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("bundle/core/app_logic.py", "print('leak')\n")
        archive.writestr("bundle/main.py", "print('leak')\n")
        archive.writestr("bundle/config/build_info.json", "{}")

    with pytest.raises(SourceExposureError, match="core/app_logic.py"):
        validate_source_protection(package)


def test_source_protection_rejects_app_pyc_in_directory(tmp_path: Path) -> None:
    exposed = tmp_path / "bundle" / "gui" / "__pycache__" / "gui_ssa.cpython-313.pyc"
    exposed.parent.mkdir(parents=True)
    exposed.write_bytes(b"pyc")

    with pytest.raises(SourceExposureError, match="gui_ssa.cpython-313.pyc"):
        validate_source_protection(tmp_path / "bundle")


def test_source_protection_rejects_nested_bundle_app_source(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("release/v4.37/bundle/core/app_logic.py", "print('leak')\n")

    with pytest.raises(SourceExposureError, match="core/app_logic.py"):
        validate_source_protection(package)


def test_source_protection_rejects_case_variant_app_source(tmp_path: Path) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("BUNDLE/CORE/APP_LOGIC.PY", "print('leak')\n")

    with pytest.raises(SourceExposureError, match="BUNDLE/CORE/APP_LOGIC.PY"):
        validate_source_protection(package)


def test_source_protection_rejects_app_source_under_internal_prefix(
    tmp_path: Path,
) -> None:
    package = tmp_path / "artifact.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "bundle/_internal/ssa_consulta/core/app_logic.py",
            "print('leak')\n",
        )

    with pytest.raises(SourceExposureError, match="core/app_logic.py"):
        validate_source_protection(package)


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
        archive.writestr("bundle/_internal/pandas/core/app_logic.py", "third party\n")
        archive.writestr("bundle/_internal/example/main.py", "third party\n")
        archive.writestr("bundle/_internal/pkg_resources/_vendor/jaraco/context.py", "")

    validate_source_protection(package)


def test_source_protection_uses_tracked_python_inventory() -> None:
    _require_git()
    tracked = _tracked_python_sources(str(Path.cwd().resolve()))

    assert "core/app_logic.py" in tracked
    assert "dev_env/build/source_protection.py" in tracked


def test_git_backed_source_inventory_tests_require_git_guard() -> None:
    test_source = Path(__file__).read_text(encoding="utf-8")
    needle = "def test_source_protection_uses_tracked_python_inventory() -> None:\n"
    body = section_between(test_source, needle, "\n\ndef ")

    assert "    _require_git()\n" in body


def test_source_protection_rejects_case_ambiguous_git_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Result:
        returncode = 0
        stdout = "core/app_logic.py\nCore/App_Logic.py\n"
        stderr = ""

    monkeypatch.setattr(
        source_protection.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    with pytest.raises(SourceExposureError, match="ambiguos por caixa"):
        source_protection._repo_python_files_from_git(tmp_path)


def test_source_protection_cli_checks_all_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visited = []

    def fake_validate(path: Path, repo_root: Path | None = None) -> None:
        visited.append(path.name)
        raise SourceExposureError("erro")

    monkeypatch.setattr(source_protection, "validate_source_protection", fake_validate)

    assert source_protection.main(["a.zip", "b.zip"]) == 1
    assert visited == ["a.zip", "b.zip"]


def test_source_protection_maps_pyc_to_tracked_source() -> None:
    source_name = _artifact_source_name(
        "bundle/gui/__pycache__/gui_ssa.cpython-313.pyc"
    )
    assert source_name == "bundle/gui/gui_ssa.py"
    candidates = _source_candidates_from_name(source_name)

    assert "gui/gui_ssa.py" in candidates
