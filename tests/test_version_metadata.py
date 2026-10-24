import json
from pathlib import Path

from utils.version import get_app_version


def test_version_file_and_config_match_runtime_version():
    project_root = Path(__file__).resolve().parents[1]
    version_file_value = (project_root / "VERSION").read_text(encoding="utf-8").strip()
    version_config = json.loads(
        (project_root / "config" / "version.json").read_text(encoding="utf-8")
    )

    assert version_config["version_short"] == version_file_value
    assert get_app_version(str(project_root)) == version_file_value




def test_fallback_emergency_scripts_removed():
    """CD-14: sem a falsa importacao de emergencia (banco de 2 SSAs de teste) nem o CLI simplificado."""
    project_root = Path(__file__).resolve().parents[1]
    assert not (project_root / "utils" / "fallback" / "emergency_import.py").exists()
    assert not (project_root / "utils" / "fallback" / "main_simple.py").exists()
