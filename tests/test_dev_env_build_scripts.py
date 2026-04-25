from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_bootstrap_uses_apt_get_update_without_invalid_yes_flag() -> None:
    script = (PROJECT_ROOT / "dev_env" / "bootstrap.sh").read_text(encoding="utf-8")

    assert "sudo apt update -y" not in script
    assert "sudo apt-get update" in script
    assert "sudo apt-get install -y" in script


def test_pyoxidizer_default_project_root_uses_empty_strip_prefix() -> None:
    root_config = PROJECT_ROOT / "pyoxidizer.bzl"
    build_config = PROJECT_ROOT / "dev_env" / "build" / "pyoxidizer.bzl"

    root_text = root_config.read_text(encoding="utf-8")
    build_text = build_config.read_text(encoding="utf-8")

    assert root_text == build_text
    assert 'PROJECT_ROOT in ("", ".")' in root_text
    assert 'strip_prefix=PROJECT_PREFIX' in root_text
