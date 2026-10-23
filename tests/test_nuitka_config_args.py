"""BL-11: o build Nuitka empacota so a config versionada."""

import subprocess
from pathlib import Path

from scripts.nuitka_config_args import REPO_ROOT, tracked_config_files

NUITKA_SCRIPTS = (
    "dev_env/build/build_nuitka_clean.bat",
    "dev_env/build/build_nuitka_debian.sh",
    "dev_env/build/build_nuitka_debian_arm64.sh",
)


def test_only_tracked_config_files_are_listed(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    for name in ("version.json", "__init__.py", "gui_main_preferences.json", "settings.json.bak.1"):
        (config / name).write_text("{}", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "config/version.json", "config/__init__.py"],
        check=True,
    )

    assert tracked_config_files(tmp_path) == ["config/version.json"]


def test_nuitka_scripts_do_not_ship_whole_config_dir() -> None:
    for script in NUITKA_SCRIPTS:
        text = (REPO_ROOT / script).read_text(encoding="utf-8")
        assert "--include-data-dir=config=config" not in text, script
        assert "nuitka_config_args.py" in text, script
