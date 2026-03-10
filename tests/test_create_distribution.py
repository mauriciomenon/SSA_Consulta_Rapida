from __future__ import annotations

from pathlib import Path
import zipfile

from scripts import create_distribution


def test_create_zip_package_returns_none_when_exe_missing(tmp_path: Path, monkeypatch, caplog) -> None:
    project_root = tmp_path / "project"
    build_dir = project_root / "builds" / "fake"
    dist_output = project_root / "dist_packages"
    build_dir.mkdir(parents=True)
    dist_output.mkdir(parents=True)

    monkeypatch.setattr(create_distribution, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(create_distribution, "DIST_OUTPUT", dist_output)
    monkeypatch.setattr(
        create_distribution,
        "BUILD_SYSTEMS",
        {
            "fake": {
                "name": "Fake",
                "exe_path": "builds/fake/missing.exe",
                "base_dir": "builds/fake",
                "internal_dir": None,
            }
        },
    )

    result = create_distribution.create_zip_package("fake", "1.0.0")

    assert result is None
    assert "Diretorio de build ou executavel principal nao encontrado" in caplog.text


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


def test_create_zip_package_excludes_local_data_and_excel_from_canonical_pyinstaller(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    canonical_dir = project_root / "launchers" / "dist" / "windows_amd64"
    canonical_dir.mkdir(parents=True)
    dist_output = project_root / "dist_packages"
    dist_output.mkdir(parents=True)

    (canonical_dir / "SSA_GUI_v1_windows_amd64.exe").write_text("fake exe", encoding="utf-8")
    (canonical_dir / "ssas.db").write_text("db", encoding="utf-8")
    (canonical_dir / "sample.xlsx").write_text("xlsx", encoding="utf-8")
    (canonical_dir / "sample.xls").write_text("xls", encoding="utf-8")
    (canonical_dir / "keep.txt").write_text("ok", encoding="utf-8")
    (canonical_dir / "data").mkdir()
    (canonical_dir / "data" / "should_not_copy.txt").write_text("secret", encoding="utf-8")
    (canonical_dir / "docs_entrada").mkdir()
    (canonical_dir / "docs_entrada" / "input.xlsx").write_text("excel", encoding="utf-8")

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
    assert "Diretorio de build ou executavel principal nao encontrado" in caplog.text


def test_compile_installer_returns_missing_when_iscc_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("INNO_SETUP_COMPILER", raising=False)
    monkeypatch.setattr(create_distribution.shutil, "which", lambda _: None)
    monkeypatch.setattr(create_distribution.os.path, "exists", lambda _: False)

    status = create_distribution.compile_installer(Path("installer.iss"))

    assert status == "missing"


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
