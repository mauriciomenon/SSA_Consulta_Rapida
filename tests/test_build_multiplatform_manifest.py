from __future__ import annotations

import json

from launchers.build_multiplatform import MultiPlatformBuilder


def test_create_manifest_lists_root_artifacts_and_skips_hidden(tmp_path):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    cli_dir = platform_dir / "SSA_CLI_v4.32_macos_arm64"
    cli_dir.mkdir()
    (cli_dir / "SSA_CLI_v4.32_macos_arm64").write_bytes(b"cli-bin")

    gui_app = platform_dir / "SSA_GUI_v4.32_macos_arm64.app"
    gui_app_bin = gui_app / "Contents" / "MacOS" / "SSA_GUI_v4.32_macos_arm64"
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
    assert entries["SSA_CLI_v4.32_macos_arm64"]["kind"] == "directory"
    assert entries["SSA_GUI_v4.32_macos_arm64.app"]["kind"] == "directory"
    assert entries["notes.txt"]["kind"] == "file"
    assert entries["SSA_GUI_v4.32_macos_arm64.app"]["path"].startswith("macos_arm64/")


def test_build_executable_uses_platform_specific_add_data_separator(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.launchers_dir = tmp_path / "launchers"
    builder.platforms_dir = builder.launchers_dir / "platforms"

    (builder.launchers_dir / "cli_entry.py").parent.mkdir(parents=True, exist_ok=True)
    (builder.launchers_dir / "cli_entry.py").write_text("print('ok')\n", encoding="utf-8")
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

    ok = builder.build_executable("windows_amd64", "cli", tmp_path / "python.exe", config)
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
