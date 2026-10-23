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


def test_legacy_setup_module_env_is_ignored(tmp_path, monkeypatch):
    """CF-17: SSA_LEGACY_SETUP_MODULE nao executa mais arquivo Python externo."""
    marker = tmp_path / "legacy_marker.txt"
    module_file = tmp_path / "legacy_module.py"
    module_file.write_text(
        f"from pathlib import Path\nPath(r'{marker}').write_text('executed')\n"
        "def legacy_required_dirs():\n    return ['legacy_dir']\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SSA_LEGACY_SETUP_MODULE", str(module_file))
    monkeypatch.setenv("SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE", "1")

    result = setup_project_structure.setup_dirs(base_path=str(tmp_path / "base"))

    assert result.ok
    assert "legacy_dir" not in result.created
    assert not marker.exists()
