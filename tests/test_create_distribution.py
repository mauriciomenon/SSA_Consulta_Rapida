from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

from scripts import create_distribution


def _configure_fake_distribution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    project_root = tmp_path / "project"
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(create_distribution, "get_version", lambda: "1.0.0")
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/SSA_GUI.exe",
                "base_dir": "builds/fake",
                "internal_dir": None,
            }
        },
    )
    return dist_output


def _run_distribution_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["create_distribution.py", *args])
    return create_distribution.main()


def test_create_zip_package_returns_none_when_exe_missing(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    dist_output = project_root / "dist_packages"
    build_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)
    (build_dir / "manifest.txt").write_text("content", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/missing.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package("fake", "1.0.0")

    assert result is None
    assert "Executavel primario ausente no diretorio" in caplog.text


def test_create_zip_package_logs_temp_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)
    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )
    monkeypatch.setattr(
        create_distribution, "_prepare_package_staging", lambda *_, **__: False
    )

    def fail_rmtree(path):
        assert Path(path).name.startswith("temp_fake_")
        raise PermissionError("locked")

    monkeypatch.setattr(create_distribution.shutil, "rmtree", fail_rmtree)

    with pytest.raises(PermissionError, match="locked"):
        create_distribution.create_zip_package("fake", "1.0.0")

    assert any(
        "Falha ao remover diretorio temporario do pacote" in record.getMessage()
        for record in caplog.records
    )


def test_main_returns_nonzero_when_expected_zip_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_fake_distribution(tmp_path, monkeypatch)
    monkeypatch.setattr(create_distribution, "create_zip_package", lambda *_, **__: None)

    assert (
        _run_distribution_main(
            monkeypatch,
            "--build-system",
            "fake",
            "--skip-installer",
        )
        == 1
    )


def test_main_returns_nonzero_when_installer_script_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist_output = _configure_fake_distribution(tmp_path, monkeypatch)
    zip_path = dist_output / "fake.zip"
    zip_path.write_text("zip", encoding="utf-8")
    monkeypatch.setattr(create_distribution, "create_zip_package", lambda *_, **__: zip_path)
    monkeypatch.setattr(
        create_distribution,
        "create_inno_setup_script",
        lambda *_, **__: None,
    )

    assert _run_distribution_main(monkeypatch, "--build-system", "fake") == 1


def test_main_returns_nonzero_when_installer_compile_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist_output = _configure_fake_distribution(tmp_path, monkeypatch)
    zip_path = dist_output / "fake.zip"
    iss_path = dist_output / "fake.iss"
    zip_path.write_text("zip", encoding="utf-8")
    iss_path.write_text("iss", encoding="utf-8")
    monkeypatch.setattr(create_distribution, "create_zip_package", lambda *_, **__: zip_path)
    monkeypatch.setattr(
        create_distribution,
        "create_inno_setup_script",
        lambda *_, **__: iss_path,
    )
    monkeypatch.setattr(
        create_distribution,
        "compile_installer",
        lambda *_: "failed",
    )

    assert _run_distribution_main(monkeypatch, "--build-system", "fake") == 1


def test_main_allows_missing_inno_when_zip_distribution_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist_output = _configure_fake_distribution(tmp_path, monkeypatch)
    zip_path = dist_output / "fake.zip"
    iss_path = dist_output / "fake.iss"
    zip_path.write_text("zip", encoding="utf-8")
    iss_path.write_text("iss", encoding="utf-8")
    monkeypatch.setattr(create_distribution, "create_zip_package", lambda *_, **__: zip_path)
    monkeypatch.setattr(
        create_distribution,
        "create_inno_setup_script",
        lambda *_, **__: iss_path,
    )
    monkeypatch.setattr(
        create_distribution,
        "compile_installer",
        lambda *_: "missing",
    )

    assert _run_distribution_main(monkeypatch, "--build-system", "fake") == 0


def test_main_returns_nonzero_when_installer_only_is_missing_inno(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist_output = _configure_fake_distribution(tmp_path, monkeypatch)
    iss_path = dist_output / "fake.iss"
    iss_path.write_text("iss", encoding="utf-8")
    monkeypatch.setattr(
        create_distribution,
        "create_inno_setup_script",
        lambda *_, **__: iss_path,
    )
    monkeypatch.setattr(
        create_distribution,
        "compile_installer",
        lambda *_: "missing",
    )

    assert (
        _run_distribution_main(
            monkeypatch,
            "--build-system",
            "fake",
            "--installer-only",
        )
        == 1
    )


def test_main_returns_zero_when_zip_succeeds_and_installer_is_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    dist_output = _configure_fake_distribution(tmp_path, monkeypatch)
    package_dir = dist_output.parent / "builds" / "packages" / "windows_amd64"
    package_dir.mkdir(parents=True)
    zip_path = package_dir / "fake.zip"
    zip_path.write_text("zip", encoding="utf-8")
    monkeypatch.setattr(create_distribution, "create_zip_package", lambda *_, **__: zip_path)

    assert (
        _run_distribution_main(
            monkeypatch,
            "--build-system",
            "fake",
            "--skip-installer",
        )
        == 0
    )
    log_messages = [record.getMessage() for record in caplog.records]
    assert any(message == f"ZIPs salvos em: {package_dir}" for message in log_messages)
    assert all(
        message != f"Pacotes salvos em: {dist_output}" for message in log_messages
    )


def test_copy_build_tree_sanitized_logs_copy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    source_file = source_dir / "artifact.txt"
    source_file.write_text("artifact", encoding="utf-8")
    target_file = target_dir / "artifact.txt"

    def fail_copy(src, dst):
        assert Path(src) == source_file
        assert Path(dst) == target_file
        raise PermissionError("locked")

    monkeypatch.setattr(create_distribution.shutil, "copy2", fail_copy)

    with pytest.raises(PermissionError, match="locked"):
        create_distribution._copy_build_tree_sanitized(source_dir, target_dir)

    log_messages = [record.getMessage() for record in caplog.records]
    assert any(
        "Falha ao copiar item do build para pacote" in message
        and str(source_file) in message
        and str(target_file) in message
        for message in log_messages
    )


def test_create_readme_usuario_points_to_user_runtime_dir(tmp_path: Path) -> None:
    create_distribution.create_readme_usuario(
        tmp_path,
        "pyinstaller",
        "1.0.0",
        "SSA_GUI.exe",
        include_sample_db=False,
    )

    content = (tmp_path / "LEIA-ME-USUARIO.txt").read_text(encoding="utf-8")
    assert r"%APPDATA%\SSA_Consulta_Rapida\docs_entrada" in content
    assert "~/Library/Application Support/SSA_Consulta_Rapida/docs_entrada" in content
    assert "${XDG_DATA_HOME:-~/.local/share}/SSA_Consulta_Rapida/docs_entrada" in content
    assert "Nao use a pasta de instalacao como area de trabalho" in content
    assert "na pasta tecnica SSA_Consulta_Rapida" in content


def test_get_version_reads_config_version_without_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "version.json").write_text(
        '{"version_short": "4.44"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "VERSION_FILE", project_root / "VERSION")

    assert create_distribution.get_version() == "4.44"


def test_get_version_rejects_missing_release_version(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "VERSION_FILE", project_root / "VERSION")

    with pytest.raises(RuntimeError, match="Arquivo de versao ausente"):
        create_distribution.get_version()


def test_get_version_rejects_empty_config_version(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "version.json").write_text(
        '{"version_short": ""}',
        encoding="utf-8",
    )

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "VERSION_FILE", project_root / "VERSION")

    with pytest.raises(RuntimeError, match="version_short ausente"):
        create_distribution.get_version()


def test_create_zip_package_uses_canonical_pyinstaller_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    canonical_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    gui_exe = canonical_dir / "SSA_GUI_v1_windows_amd64.exe"
    gui_exe.write_text("fake exe", encoding="utf-8")
    docs_dir = project_root / "docs"
    docs_dir.mkdir()
    (project_root / "README.md").write_text("readme", encoding="utf-8")
    (docs_dir / "ANTIVIRUS_EXCLUSOES.md").write_text("av", encoding="utf-8")
    (docs_dir / "GUIA_MIGRACAO_NOVA_INSTALACAO.md").write_text(
        "guide",
        encoding="utf-8",
    )

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    result = create_distribution.create_zip_package("pyinstaller", "1.0.0")

    assert result is not None
    assert result.parent == project_root / "builds" / "packages" / "windows_amd64"
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("SSA_GUI_v1_windows_amd64.exe") for name in names)
        assert any(
            name.endswith("docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md")
            for name in names
        )


def test_create_zip_package_returns_none_when_platform_is_not_in_build_path(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "pyinstaller" / "unexpected"
    build_dir.mkdir(parents=True)
    (build_dir / "SSA_Consulta_Rapida.exe").write_text("exe", encoding="utf-8")
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True)
    (project_root / "README.md").write_text("readme", encoding="utf-8")
    (docs_dir / "ANTIVIRUS_EXCLUSOES.md").write_text("av", encoding="utf-8")
    (docs_dir / "GUIA_MIGRACAO_NOVA_INSTALACAO.md").write_text(
        "guide",
        encoding="utf-8",
    )

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/unexpected/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller/unexpected",
                "internal_dir": "_internal",
            }
        },
    )

    result = create_distribution.create_zip_package("pyinstaller", "1.0.0")

    assert result is None
    assert "Nao foi possivel inferir plataforma do build" in caplog.text
    assert not (project_root / "builds" / "packages" / "windows_amd64").exists()


def test_create_zip_package_excludes_local_data_and_excel_from_canonical_pyinstaller(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    canonical_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    (canonical_dir / "SSA_GUI_v1_windows_amd64.exe").write_text(
        "fake exe", encoding="utf-8"
    )
    (canonical_dir / "ssas.db").write_text("db", encoding="utf-8")
    (canonical_dir / "sample.xlsx").write_text("xlsx", encoding="utf-8")
    (canonical_dir / "sample.xls").write_text("xls", encoding="utf-8")
    (canonical_dir / "keep.txt").write_text("ok", encoding="utf-8")
    (canonical_dir / "data").mkdir()
    (canonical_dir / "data" / "should_not_copy.txt").write_text(
        "secret", encoding="utf-8"
    )
    (canonical_dir / "docs_entrada").mkdir()
    (canonical_dir / "docs_entrada" / "input.xlsx").write_text(
        "excel", encoding="utf-8"
    )

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    result = create_distribution.create_zip_package("pyinstaller", "1.0.0")

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("SSA_GUI_v1_windows_amd64.exe") for name in names)
        assert any(name.endswith("keep.txt") for name in names)
        assert not any(name.endswith(".db") for name in names)
        assert not any(name.endswith(".xlsx") for name in names)
        assert not any(name.endswith(".xls") for name in names)
        assert not any(name.endswith("should_not_copy.txt") for name in names)
        assert not any(name.endswith("input.xlsx") for name in names)


def test_create_zip_package_excludes_sensitive_files_from_build_config_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    exe_path = build_dir / "SSA_Consulta_Rapida.exe"
    exe_path.write_text("fake exe", encoding="utf-8")

    config_dir = build_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "keep.txt").write_text("ok", encoding="utf-8")
    (config_dir / "__init__.py").write_text("", encoding="utf-8")
    (config_dir / "settings.json.bak-20260621").write_text("backup", encoding="utf-8")
    (config_dir / "settings.backup").write_text("backup", encoding="utf-8")
    (config_dir / "prefs.backup_20260621").write_text("backup", encoding="utf-8")
    (config_dir / "local.db").write_text("db", encoding="utf-8")
    (config_dir / "entrada.xlsx").write_text("xlsx", encoding="utf-8")
    (config_dir / "entrada.xls").write_text("xls", encoding="utf-8")
    nested_config_dir = config_dir / "vendor" / "lib" / "config"
    nested_config_dir.mkdir(parents=True)
    (nested_config_dir / "__init__.py").write_text("# package", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package("fake", "1.0.0")

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("config/keep.txt") for name in names)
        assert not any(
            name.endswith("SSA_Consulta_Rapida/config/__init__.py") for name in names
        )
        assert any(
            name.endswith("vendor/lib/config/__init__.py") for name in names
        )
        assert not any(".bak" in name for name in names)
        assert not any(".backup" in name for name in names)
        assert not any(name.endswith("config/local.db") for name in names)
        assert not any(name.endswith("config/entrada.xlsx") for name in names)
        assert not any(name.endswith("config/entrada.xls") for name in names)


def test_inno_excludes_match_backup_fragments() -> None:
    excludes = create_distribution._build_inno_excludes_str().split(",")

    assert "*.bak" in excludes
    assert "*.bak*" in excludes
    assert "*.backup" in excludes
    assert "*.backup*" in excludes
    assert "*.backup_*" in excludes


def test_create_zip_package_keeps_sample_db_out_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    sample_db_dir = project_root / "dist_assets" / "sample_db"
    sample_db_dir.mkdir(parents=True)
    (sample_db_dir / "ssas_example.db").write_text("sample db", encoding="utf-8")
    (sample_db_dir / "LEIA-ME.txt").write_text("sample readme", encoding="utf-8")

    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package("fake", "1.0.0")

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("SSA_Consulta_Rapida.exe") for name in names)
        assert not any("BancoExemplo/" in name for name in names)


def test_create_zip_package_includes_fixed_sample_db_only_when_option_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    sample_db_dir = project_root / "dist_assets" / "sample_db"
    sample_db_dir.mkdir(parents=True)
    (sample_db_dir / "ssas_example.db").write_text("sample db", encoding="utf-8")
    (sample_db_dir / "LEIA-ME.txt").write_text("sample readme", encoding="utf-8")

    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")
    (build_dir / "local.db").write_text("local db", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package(
        "fake",
        "1.0.0",
        include_sample_db=True,
    )

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("BancoExemplo/ssas_example.db") for name in names)
        assert any(name.endswith("BancoExemplo/LEIA-ME.txt") for name in names)
        assert not any(name.endswith("local.db") for name in names)


def test_create_zip_package_returns_none_when_sample_db_assets_are_missing(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)
    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package(
        "fake",
        "1.0.0",
        include_sample_db=True,
    )

    assert result is None
    assert "Assets fixos do banco de exemplo ausentes" in caplog.text


def test_create_zip_package_includes_only_selected_local_db_when_option_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)
    local_db_dir = project_root / "data"
    local_db_dir.mkdir(parents=True)

    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")
    selected_local_db = local_db_dir / "ssas.db"
    selected_local_db.write_text("local db", encoding="utf-8")
    (build_dir / "other.db").write_text("other db", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package(
        "fake",
        "1.0.0",
        include_local_db="data/ssas.db",
    )

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("BancoLocal/ssas.db") for name in names)
        assert not any(name.endswith("other.db") for name in names)


def test_create_zip_package_returns_none_when_selected_local_db_is_missing(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake" / "windows_amd64"
    build_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)
    (build_dir / "SSA_Consulta_Rapida.exe").write_text("fake exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/windows_amd64/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/fake/windows_amd64",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package(
        "fake",
        "1.0.0",
        include_local_db="data/inexistente.db",
    )

    assert result is None
    assert "Banco local explicitamente solicitado nao encontrado" in caplog.text


def test_create_zip_package_returns_none_when_canonical_has_no_primary_executable(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    canonical_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    (canonical_dir / "build_manifest.json").write_text("{}", encoding="utf-8")
    (canonical_dir / "keep.txt").write_text("not executable", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    result = create_distribution.create_zip_package("pyinstaller", "1.0.0")

    assert result is None
    assert "Executavel primario ausente em diretorio canonico" in caplog.text


def test_create_zip_package_returns_none_when_build_directory_is_missing(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    project_root = tmp_path / "project"
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/main.exe",
                "base_dir": "builds/fake",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package("fake", "1.0.0")

    assert result is None
    assert "Diretorio de build ausente" in caplog.text


def test_compile_installer_returns_missing_when_iscc_is_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.delenv("INNO_SETUP_COMPILER", raising=False)
    monkeypatch.setattr(create_distribution.shutil, "which", lambda _: None)
    monkeypatch.setattr(create_distribution.os.path, "exists", lambda _: False)

    status = create_distribution.compile_installer(Path("installer.iss"))

    assert status == "missing"


def test_compile_installer_rejects_relative_env_override(monkeypatch, caplog) -> None:
    monkeypatch.setenv("INNO_SETUP_COMPILER", "tools/iscc")
    monkeypatch.setattr(create_distribution.shutil, "which", lambda _: None)
    monkeypatch.setattr(create_distribution.os.path, "exists", lambda _: False)

    status = create_distribution.compile_installer(Path("installer.iss"))

    assert status == "missing"
    assert "caminho nao absoluto" in caplog.text


def test_compile_installer_accepts_absolute_env_override_in_trusted_parent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trusted_iscc = tmp_path / "trusted" / "iscc"
    trusted_iscc.parent.mkdir(parents=True)
    trusted_iscc.write_text("fake", encoding="utf-8")

    monkeypatch.setenv("INNO_SETUP_COMPILER", str(trusted_iscc))
    monkeypatch.setattr(
        create_distribution.shutil, "which", lambda _: str(trusted_iscc)
    )

    recorded_cmd: dict[str, list[str]] = {}

    class _Result:
        returncode = 0
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        recorded_cmd["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(create_distribution.subprocess, "run", _fake_run)

    status = create_distribution.compile_installer(Path("installer.iss"))

    assert status == "success"
    assert recorded_cmd["cmd"][0] == str(trusted_iscc.resolve())


def test_resolve_build_directory_pyinstaller_prefers_canonical_order_over_mtime(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    first_dir = project_root / "launchers" / "dist" / "windows_amd64"
    second_dir = project_root / "launchers" / "dist" / "windows_alt"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    (first_dir / "SSA_GUI.exe").write_text("first", encoding="utf-8")
    (second_dir / "SSA_GUI.exe").write_text("second", encoding="utf-8")
    (second_dir / "touch.txt").write_text("newer", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": [
                    "launchers/dist/windows_amd64",
                    "launchers/dist/windows_alt",
                ],
            }
        },
    )

    resolved = create_distribution._resolve_build_directory("pyinstaller")

    assert resolved == first_dir


def test_resolve_build_directory_pyinstaller_falls_back_to_legacy_when_canonical_invalid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    legacy_dir = project_root / "builds" / "pyinstaller"
    canonical_dir.mkdir(parents=True)
    legacy_dir.mkdir(parents=True)

    (canonical_dir / "manifest.txt").write_text("no exe", encoding="utf-8")
    (legacy_dir / "SSA_Consulta_Rapida.exe").write_text("legacy exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    resolved = create_distribution._resolve_build_directory("pyinstaller")

    assert resolved == legacy_dir


def test_failure_reason_pyinstaller_reports_canonical_missing_primary_executable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    legacy_dir = project_root / "builds" / "pyinstaller"
    canonical_dir.mkdir(parents=True)
    legacy_dir.mkdir(parents=True)

    (canonical_dir / "manifest.txt").write_text("no exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    resolved = create_distribution._resolve_build_directory("pyinstaller")
    reason = create_distribution._resolve_build_directory_failure_reason("pyinstaller")

    assert resolved is None
    assert "Executavel primario ausente em diretorio canonico" in reason


def test_failure_reason_pyinstaller_reports_legacy_missing_primary_executable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    legacy_dir = project_root / "builds" / "pyinstaller"
    legacy_dir.mkdir(parents=True)

    (legacy_dir / "manifest.txt").write_text("no exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    resolved = create_distribution._resolve_build_directory("pyinstaller")
    reason = create_distribution._resolve_build_directory_failure_reason("pyinstaller")

    assert resolved is None
    assert "Executavel primario ausente no diretorio" in reason


def test_detect_primary_executable_name_returns_none_when_package_has_no_binary(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir(parents=True)
    (package_dir / "README.md").write_text("no executable", encoding="utf-8")
    (package_dir / "config.json").write_text("{}", encoding="utf-8")

    detected = create_distribution._detect_primary_executable_name(package_dir)

    assert detected is None


def test_detect_primary_executable_name_accepts_app_bundle_directory(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "package"
    app_dir = package_dir / "SSA_GUI_v3.10_macos_arm64.app"
    app_dir.mkdir(parents=True)

    detected = create_distribution._detect_primary_executable_name(package_dir)

    assert detected == "SSA_GUI_v3.10_macos_arm64.app"


def test_create_inno_setup_script_uses_sourcepath_outputdir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    dist_output = project_root / "dist_packages"
    canonical_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)
    (canonical_dir / "SSA_GUI.exe").write_text("exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    iss_path = create_distribution.create_inno_setup_script("pyinstaller", "1.0.0")

    assert iss_path is not None
    iss_content = iss_path.read_text(encoding="utf-8")
    assert "OutputDir={#SourcePath}" in iss_content
    expected_output = str(dist_output.resolve()).replace("/", "\\")
    expected_source = str(canonical_dir.resolve()).replace("/", "\\")
    assert f'#define SourcePath "{expected_output}"' in iss_content
    assert f'#define SourceDir "{expected_source}"' in iss_content
    assert '#define SourcePathMode "absolute"' in iss_content
    assert 'Source: "{#SourceDir}\\SSA_GUI.exe"' in iss_content


def test_create_inno_setup_script_includes_sample_db_when_option_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    dist_output = project_root / "dist_packages"
    sample_db_dir = project_root / "dist_assets" / "sample_db"
    canonical_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)
    sample_db_dir.mkdir(parents=True)
    (canonical_dir / "SSA_GUI.exe").write_text("exe", encoding="utf-8")
    (sample_db_dir / "ssas_example.db").write_text("sample db", encoding="utf-8")
    (sample_db_dir / "LEIA-ME.txt").write_text("sample readme", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    iss_path = create_distribution.create_inno_setup_script(
        "pyinstaller",
        "1.0.0",
        include_sample_db=True,
    )

    assert iss_path is not None
    iss_content = iss_path.read_text(encoding="utf-8")
    expected_db = str((sample_db_dir / "ssas_example.db").resolve()).replace("/", "\\")
    expected_readme = str((sample_db_dir / "LEIA-ME.txt").resolve()).replace("/", "\\")
    assert 'Name: "{userdocs}\\SSA Consulta Rapida\\BancoExemplo"' in iss_content
    assert (
        f'Source: "{expected_db}"; DestDir: "{{userdocs}}\\SSA Consulta Rapida\\BancoExemplo"; DestName: "ssas_example.db"; Flags: ignoreversion'
        in iss_content
    )
    assert (
        f'Source: "{expected_readme}"; DestDir: "{{userdocs}}\\SSA Consulta Rapida\\BancoExemplo"; DestName: "LEIA-ME.txt"; Flags: ignoreversion'
        in iss_content
    )


def test_create_inno_setup_script_includes_selected_local_db_when_option_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    dist_output = project_root / "dist_packages"
    local_db_dir = project_root / "data"
    canonical_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)
    local_db_dir.mkdir(parents=True)
    (canonical_dir / "SSA_GUI.exe").write_text("exe", encoding="utf-8")
    selected_local_db = local_db_dir / "ssas.db"
    selected_local_db.write_text("local db", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    iss_path = create_distribution.create_inno_setup_script(
        "pyinstaller",
        "1.0.0",
        include_local_db="data/ssas.db",
    )

    assert iss_path is not None
    iss_content = iss_path.read_text(encoding="utf-8")
    expected_db = str(selected_local_db.resolve()).replace("/", "\\")
    assert 'Name: "{userdocs}\\SSA Consulta Rapida\\BancoLocal"' in iss_content
    assert (
        f'Source: "{expected_db}"; DestDir: "{{userdocs}}\\SSA Consulta Rapida\\BancoLocal"; DestName: "ssas.db"; Flags: ignoreversion'
        in iss_content
    )


def test_create_inno_setup_script_uses_absolute_source_when_relpath_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    dist_output = project_root / "dist_packages"
    canonical_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)
    (canonical_dir / "SSA_GUI.exe").write_text("exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyinstaller": {
                "name": "PyInstaller",
                "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyinstaller",
                "internal_dir": "_internal",
                "canonical_dirs": ["launchers/dist/windows_amd64"],
            }
        },
    )

    iss_path = create_distribution.create_inno_setup_script("pyinstaller", "1.0.0")

    assert iss_path is not None
    iss_content = iss_path.read_text(encoding="utf-8")
    expected_abs = str(canonical_dir.resolve()).replace("/", "\\")
    expected_output = str(dist_output.resolve()).replace("/", "\\")
    assert f'#define SourcePath "{expected_output}"' in iss_content
    assert f'#define SourceDir "{expected_abs}"' in iss_content
    assert '#define SourcePathMode "absolute"' in iss_content
    assert 'Source: "{#SourceDir}\\SSA_GUI.exe"' in iss_content


def test_resolve_inno_source_pyoxidizer_uses_exe_path_from_build_info(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    source_dir = project_root / "builds" / "pyoxidizer"
    source_dir.mkdir(parents=True)
    (source_dir / "SSA_Consulta_Rapida.exe").write_text("exe", encoding="utf-8")

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "pyoxidizer": {
                "name": "PyOxidizer",
                "exe_path": "builds/pyoxidizer/SSA_Consulta_Rapida.exe",
                "base_dir": "builds/pyoxidizer",
                "internal_dir": "lib",
            }
        },
    )

    resolved = create_distribution._resolve_inno_source("pyoxidizer")

    assert resolved is not None
    resolved_dir, resolved_exe = resolved
    assert resolved_dir == source_dir
    assert resolved_exe == "SSA_Consulta_Rapida.exe"
