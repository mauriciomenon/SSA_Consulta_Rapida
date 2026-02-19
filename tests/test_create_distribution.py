from __future__ import annotations

from pathlib import Path

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
    assert "Executavel nao encontrado para empacotamento" in caplog.text
