from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from utils.version import get_app_version


def test_version_file_and_config_match_runtime_version():
    project_root = Path(__file__).resolve().parents[1]
    version_file_value = (project_root / "VERSION").read_text(encoding="utf-8").strip()
    version_config = json.loads(
        (project_root / "config" / "version.json").read_text(encoding="utf-8")
    )

    assert version_config["version_short"] == version_file_value
    assert get_app_version(str(project_root)) == version_file_value


def test_standalone_cli_banner_uses_repository_version(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
    (tmp_path / "data").mkdir()
    with closing(sqlite3.connect(tmp_path / "data" / "ssas.db")) as connection:
        connection.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        connection.commit()
    result = subprocess.run(
        [sys.executable, str(project_root / "utils" / "fallback" / "main_simple.py")],
        cwd=tmp_path,
        input="sair\n",
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert f"Pesquisa Rapida de SSAs {version}" in result.stdout
    assert "Base de dados: 0 registros" in result.stdout
    assert not result.stderr
