"""Guard test to ensure setup_project_structure remains available.

Prevents silent removal/regression of the utility required by main.py.
"""

from __future__ import annotations

from utils import setup_project_structure


def test_setup_project_structure_basics(tmp_path):
    r = setup_project_structure.setup_dirs(base_path=str(tmp_path))
    # Must succeed without fatal errors
    assert r.ok
    # At least one directory should have been created on a fresh tmp
    assert r.created, "Esperado que crie diretórios em ambiente novo"
    assert setup_project_structure.validate(str(tmp_path))


def test_legacy_setup_module_outside_project_blocked(tmp_path, monkeypatch):
    marker = tmp_path / "legacy_marker.txt"
    module_file = tmp_path / "legacy_module.py"
    module_file.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                f"Path(r'{marker}').write_text('executed', encoding='utf-8')",
                "",
                "def legacy_required_dirs():",
                "    return ['legacy_dir']",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SSA_LEGACY_SETUP_MODULE", str(module_file))
    monkeypatch.delenv("SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE", raising=False)

    loaded = setup_project_structure._load_legacy_required_dirs()

    assert loaded == []
    assert not marker.exists()


def test_legacy_setup_module_outside_project_allowed_with_opt_in(tmp_path, monkeypatch):
    marker = tmp_path / "legacy_marker_optin.txt"
    module_file = tmp_path / "legacy_module_optin.py"
    module_file.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                f"Path(r'{marker}').write_text('executed', encoding='utf-8')",
                "",
                "def legacy_required_dirs():",
                "    return ['legacy_dir_optin']",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SSA_LEGACY_SETUP_MODULE", str(module_file))
    monkeypatch.setenv("SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE", "1")

    loaded = setup_project_structure._load_legacy_required_dirs()

    assert loaded == ["legacy_dir_optin"]
    assert marker.exists()
