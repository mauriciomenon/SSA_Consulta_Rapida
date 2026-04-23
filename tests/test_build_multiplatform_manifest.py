from __future__ import annotations

import json
import plistlib
import os
import subprocess
import sys
from pathlib import Path

from launchers.build_multiplatform import MultiPlatformBuilder


def test_create_manifest_lists_root_artifacts_and_skips_hidden(tmp_path):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    cli_dir = platform_dir / "SSA_CLI_v4.33_macos_arm64"
    cli_dir.mkdir()
    (cli_dir / "SSA_CLI_v4.33_macos_arm64").write_bytes(b"cli-bin")

    gui_app = platform_dir / "SSA_GUI_v4.33_macos_arm64.app"
    gui_app_bin = gui_app / "Contents" / "MacOS" / "SSA_GUI_v4.33_macos_arm64"
    gui_app_bin.parent.mkdir(parents=True)
    gui_app_bin.write_bytes(b"gui-bin")

    (platform_dir / ".DS_Store").write_bytes(b"junk")
    (platform_dir / "notes.txt").write_text("ok", encoding="utf-8")

    builder._create_manifest("macos_arm64", platform_dir)

    manifest_path = platform_dir / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest["executables"]}

    assert ".DS_Store" not in entries
    assert "build_manifest.json" not in entries
    assert entries["SSA_CLI_v4.33_macos_arm64"]["kind"] == "directory"
    assert entries["SSA_GUI_v4.33_macos_arm64.app"]["kind"] == "directory"
    assert entries["notes.txt"]["kind"] == "file"
    assert (
        entries["SSA_GUI_v4.33_macos_arm64.app"]["path"]
        .replace("\\", "/")
        .startswith("macos_arm64/")
    )


def test_build_executable_uses_platform_specific_add_data_separator(
    tmp_path, monkeypatch
):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.launchers_dir = tmp_path / "launchers"
    builder.platforms_dir = builder.launchers_dir / "platforms"

    (builder.launchers_dir / "cli_entry.py").parent.mkdir(parents=True, exist_ok=True)
    (builder.launchers_dir / "cli_entry.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    (builder.base_dir / "config").mkdir(parents=True, exist_ok=True)
    (builder.base_dir / "resources").mkdir(parents=True, exist_ok=True)
    (builder.base_dir / "resources" / "app_icon.ico").write_bytes(b"ico")
    (builder.base_dir / "resources" / "app_icon.icns").write_bytes(b"icns")

    captured_cmds = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        captured_cmds.append(cmd)
        return _Result()

    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    config = {
        "pyinstaller_args": {
            "onefile": True,
            "exclude_modules": [],
            "hidden_imports": [],
        },
        "cli_config": {
            "console": True,
            "icon": "resources/app_icon.ico",
            "name": "SSA_CLI_test",
            "additional_args": [],
        },
    }

    ok = builder.build_executable(
        "windows_amd64", "cli", tmp_path / "python.exe", config
    )
    assert ok is True
    assert captured_cmds, "subprocess.run nao foi chamado"
    windows_cmd = captured_cmds[-1]
    assert "--add-data" in windows_cmd
    add_data_value = windows_cmd[windows_cmd.index("--add-data") + 1]
    assert add_data_value.endswith(";config")

    captured_cmds.clear()
    config["cli_config"]["icon"] = "resources/app_icon.icns"
    ok = builder.build_executable("macos_arm64", "cli", tmp_path / "python3", config)
    assert ok is True
    mac_cmd = captured_cmds[-1]
    assert "--add-data" in mac_cmd
    add_data_value = mac_cmd[mac_cmd.index("--add-data") + 1]
    assert add_data_value.endswith(":config")


def test_post_process_macos_creates_dmg_when_configured(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    app_bin = app_bundle / "Contents" / "MacOS" / app_name.replace(".app", "")
    app_bin.parent.mkdir(parents=True)
    app_bin.write_bytes(b"gui-bin")
    info_plist = app_bundle / "Contents" / "Info.plist"
    with open(info_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "legacy", "CFBundleDisplayName": "legacy"}, plist_file
        )

    captured_cmds = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        captured_cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        lambda name: "/usr/bin/hdiutil" if name == "hdiutil" else None,
    )
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64", {"post_build": {"compress": False, "package": "dmg"}}
    )
    assert ok is True
    assert captured_cmds, "hdiutil nao foi chamado"

    cmd = captured_cmds[-1]
    assert cmd[0] == "/usr/bin/hdiutil"
    assert "create" in cmd
    assert "-srcfolder" in cmd
    assert cmd[cmd.index("-srcfolder") + 1] == str(app_bundle)

    dmg_path = platform_dir / builder._get_macos_dmg_name()
    assert dmg_path.exists()

    with open(info_plist, "rb") as plist_file:
        plist_data = plistlib.load(plist_file)
    assert plist_data["CFBundleName"] == builder.APP_DISPLAY_NAME
    assert plist_data["CFBundleDisplayName"] == builder.APP_DISPLAY_NAME

    manifest = json.loads(
        (platform_dir / "build_manifest.json").read_text(encoding="utf-8")
    )
    names = {entry["name"] for entry in manifest["executables"]}
    assert dmg_path.name in names


def test_post_process_macos_dmg_fails_when_gui_app_missing(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        lambda name: "/usr/bin/hdiutil" if name == "hdiutil" else None,
    )
    ok = builder.post_process(
        "macos_arm64", {"post_build": {"compress": False, "package": "dmg"}}
    )
    assert ok is False


def test_post_process_macos_dmg_cli_only_skips_when_gui_not_requested(
    tmp_path, monkeypatch
):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("hdiutil nao deve ser chamado em build cli-only")

    monkeypatch.setattr("launchers.build_multiplatform.shutil.which", _fail_if_called)

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "package": "dmg"}},
        apps=["cli"],
    )
    assert ok is True


def test_cleanup_online_unnecessary_files_uses_scope_prefix_for_dist(monkeypatch, tmp_path):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.launchers_dir = tmp_path / "launchers"
    builder.platforms_dir = builder.launchers_dir / "platforms"
    builder.dist_dir = builder.launchers_dir / "dist"

    dist_dir = builder.launchers_dir / "dist"
    dist_simple_dir = builder.launchers_dir / "dist_simple"
    build_dir = tmp_path / "build"
    builds_dir = tmp_path / "builds"
    dist_dir.mkdir(parents=True)
    dist_simple_dir.mkdir(parents=True)
    build_dir.mkdir()
    builds_dir.mkdir()

    (dist_dir / "cli").mkdir()
    (dist_dir / "cli" / "SSA_CLI.exe").write_bytes(b"x")
    (dist_dir_simple := dist_simple_dir / "gui").mkdir()
    (dist_dir_simple / "SSA_GUI.exe").write_bytes(b"y")

    (build_dir / "artifact.pyc").write_text("stub", encoding="utf-8")
    (builds_dir / "old.pyo").write_text("stub", encoding="utf-8")

    git_rm_batches: list[list[str]] = []

    class _FakeResult:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, **_kwargs):
        if cmd == ["git", "ls-files"]:
            tracked = [
                "launchers/dist/cli/SSA_CLI.exe",
                "launchers/dist_simple/gui/SSA_GUI.exe",
                "build/artifact.pyc",
                "builds/old.pyo",
                "other/ignored.txt",
            ]
            return _FakeResult(stdout="\n".join(tracked) + "\n")

        if cmd[:2] == ["git", "rm"]:
            git_rm_batches.append(cmd)
            return _FakeResult()

        return _FakeResult(returncode=1)

    monkeypatch.setattr(builder, "_run_command", fake_run)

    ok = builder.cleanup_online_unnecessary_files()
    assert ok is True

    removed: list[str] = []
    for batch in git_rm_batches:
        removed.extend(batch[4:])

    assert "launchers/dist/cli/SSA_CLI.exe" in removed
    assert "launchers/dist_simple/gui/SSA_GUI.exe" in removed
    assert "build/artifact.pyc" in removed
    assert "builds/old.pyo" in removed


def test_build_multiplatform_script_runs_without_explicit_pythonpath():
    """Valida comando de entrada sem dependencia de PYTHONPATH manual."""
    script_path = Path(__file__).resolve().parents[1] / "launchers" / "build_multiplatform.py"
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = ""

    result = subprocess.run(
        [sys.executable, str(script_path), "--list-platforms"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
        timeout=30,
    )

    assert result.returncode == 0
    assert "Plataformas suportadas:" in result.stdout
