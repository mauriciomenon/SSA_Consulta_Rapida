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
            }
        },
    )

    result = create_distribution.create_zip_package("pyinstaller", "1.0.0")

    assert result is not None
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("SSA_GUI_v1_windows_amd64.exe") for name in names)
