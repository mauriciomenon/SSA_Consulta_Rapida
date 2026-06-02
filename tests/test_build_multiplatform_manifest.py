from __future__ import annotations

import json
import plistlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from launchers.build_multiplatform import MultiPlatformBuilder
from dev_env.build import write_build_info


_MACOS_TOOL_PATHS = {
    "codesign": "/usr/bin/codesign",
    "hdiutil": "/usr/bin/hdiutil",
}


def _macos_tool_path(name):
    return _MACOS_TOOL_PATHS.get(name)


def test_load_version_rejects_missing_version_json(tmp_path: Path) -> None:
    builder = MultiPlatformBuilder.__new__(MultiPlatformBuilder)
    builder.base_dir = tmp_path

    with pytest.raises(RuntimeError, match="Arquivo de versao ausente"):
        builder._load_version()


def test_load_version_rejects_empty_release_version(tmp_path: Path) -> None:
    version_file = tmp_path / "config" / "version.json"
    version_file.parent.mkdir()
    version_file.write_text('{"version_short": ""}', encoding="utf-8")
    builder = MultiPlatformBuilder.__new__(MultiPlatformBuilder)
    builder.base_dir = tmp_path

    with pytest.raises(RuntimeError, match="version_short ausente"):
        builder._load_version()


def test_command_stdout_logs_metadata_command_failure(monkeypatch):
    builder = MultiPlatformBuilder()
    warnings = []

    def fake_run_command(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            ["git", "bad"],
            returncode=7,
            stdout="stdout detail",
            stderr="stderr detail",
        )

    monkeypatch.setattr(builder, "_run_command", fake_run_command)
    monkeypatch.setattr(
        "launchers.build_multiplatform.logger.warning",
        lambda *args, **_kwargs: warnings.append(args),
    )

    assert builder._command_stdout(["git", "bad"]) == ""
    assert warnings
    assert "Metadata command failed" in warnings[0][0]
    assert "stderr detail" in "".join(str(item) for item in warnings[0])


def test_build_info_payload_includes_toolchain_versions(monkeypatch):
    builder = MultiPlatformBuilder()

    outputs: dict[tuple[str, ...], str] = {
        ("git", "rev-parse", "HEAD"): "abcdef123456",
        ("git", "log", "-1", "--format=%cI"): "2026-05-03T22:48:02-03:00",
        ("git", "log", "-1", "--format=%s"): "STABILITY_PATCH",
        ("uv", "--version"): "uv 0.9.18",
        ("cc", "--version"): "gcc 14.2.0",
        ("rustc", "--version"): "rustc 1.90.0",
    }

    def fake_run(cmd, cwd, require_success):  # noqa: ANN001, ARG001
        return outputs.get(tuple(str(item) for item in cmd), "")

    monkeypatch.setattr(write_build_info, "_run_output", fake_run)

    payload = builder._build_info_payload("pyinstaller", "windows_amd64")

    assert payload["c_compiler_version"] == "gcc 14.2.0"
    assert payload["rustc_version"] == "rustc 1.90.0"


def test_build_info_payload_uses_msvc_environment_fallback(monkeypatch):
    builder = MultiPlatformBuilder()
    outputs: dict[tuple[str, ...], str] = {
        ("git", "rev-parse", "HEAD"): "abcdef123456",
        ("git", "log", "-1", "--format=%cI"): "2026-05-03T22:48:02-03:00",
        ("git", "log", "-1", "--format=%s"): "STABILITY_PATCH",
        ("uv", "--version"): "uv 0.9.18",
        ("rustc", "--version"): "rustc 1.90.0",
    }

    def fake_run(cmd, cwd, require_success):  # noqa: ANN001, ARG001
        return outputs.get(tuple(str(item) for item in cmd), "")

    monkeypatch.setattr(write_build_info, "_run_output", fake_run)
    monkeypatch.setenv("VCToolsVersion", "14.44.35207")

    payload = builder._build_info_payload("pyinstaller", "windows_amd64")

    assert payload["c_compiler_version"] == "MSVC 14.44.35207"


def test_write_build_info_payload_includes_toolchain_versions(monkeypatch, tmp_path):
    outputs = {
        ("git", "rev-parse", "HEAD"): "abcdef123456",
        ("git", "log", "-1", "--format=%cI"): "2026-05-03T22:48:02-03:00",
        ("git", "log", "-1", "--format=%s"): "STABILITY_PATCH",
        ("uv", "--version"): "uv 0.9.18",
        ("cc", "--version"): "gcc 14.2.0",
        ("rustc", "--version"): "rustc 1.90.0",
    }

    def fake_run(args, cwd, require_success):  # noqa: ANN001, FBT001
        return outputs.get(tuple(args), "")

    monkeypatch.setattr(write_build_info, "_run_output", fake_run)

    payload = write_build_info.build_payload(
        tmp_path,
        "nuitka",
        "debian_amd64",
        "4.37",
    )

    assert payload["c_compiler_version"] == "gcc 14.2.0"
    assert payload["rustc_version"] == "rustc 1.90.0"


def test_write_build_info_logs_required_metadata_command_failure(
    capsys,
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"],
            returncode=128,
            stdout="",
            stderr="not a git repo",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert write_build_info._run_output(
        ["git", "rev-parse", "HEAD"],
        tmp_path,
        require_success=True,
    ) == ""
    assert "Metadata command failed" in capsys.readouterr().err


def test_write_build_info_ignores_optional_command_stderr_on_failure(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            ["cc", "--version"],
            returncode=1,
            stdout="",
            stderr="compiler error detail",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert write_build_info._run_output(
        ["cc", "--version"],
        tmp_path,
        require_success=False,
    ) == ""


def test_write_build_info_main_reports_output_write_errors(
    capsys,
    monkeypatch,
    tmp_path,
) -> None:
    output_dir = tmp_path / "output-dir"
    output_dir.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "write_build_info.py",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(output_dir),
            "--build-system",
            "nuitka",
            "--platform",
            "debian_amd64",
            "--app-version",
            "4.37",
        ],
    )
    monkeypatch.setattr(
        write_build_info,
        "build_payload",
        lambda *_args: {"app_version": "4.37"},
    )

    assert write_build_info.main() == 1
    assert "Failed to write build info" in capsys.readouterr().err


def test_write_build_info_main_writes_valid_json(monkeypatch, tmp_path) -> None:
    output = tmp_path / "build_info.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "write_build_info.py",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(output),
            "--build-system",
            "nuitka",
            "--platform",
            "debian_amd64",
            "--app-version",
            "4.37",
        ],
    )
    monkeypatch.setattr(
        write_build_info,
        "build_payload",
        lambda *_args: {"app_version": "4.37"},
    )

    assert write_build_info.main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {"app_version": "4.37"}


def test_pyinstaller_build_info_write_logs_before_raising(monkeypatch) -> None:
    builder = MultiPlatformBuilder()
    errors = []

    def fail_write(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", fail_write)
    monkeypatch.setattr(
        "launchers.build_multiplatform.logger.error",
        lambda *args, **_kwargs: errors.append(args),
    )

    with pytest.raises(OSError):
        builder._write_build_info_file("pyinstaller", "windows_amd64")

    assert errors
    assert "Failed to write build info" in errors[0][0]


def test_upx_contract_uses_system_binary_not_python_package():
    repo_root = Path(__file__).resolve().parents[1]
    build_script = repo_root / "launchers" / "build_multiplatform.py"
    requirements_files = [
        repo_root / "requirements_build.txt",
        repo_root / "launchers" / "platforms" / "windows_amd64" / "requirements_windows_build.txt",
    ]

    assert "shutil.which(\"upx\")" in build_script.read_text(encoding="utf-8")
    for requirements_file in requirements_files:
        assert "upx4py" not in requirements_file.read_text(encoding="utf-8")


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
    (builder.base_dir / "docs").mkdir(parents=True, exist_ok=True)
    (builder.base_dir / "docs" / "GUIA_MIGRACAO_NOVA_INSTALACAO.md").write_text(
        "guide",
        encoding="utf-8",
    )
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
    assert any(
        value.endswith(";docs")
        and "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in value
        for idx, value in enumerate(windows_cmd)
        if idx > 0 and windows_cmd[idx - 1] == "--add-data"
    )
    assert any(
        value.endswith(";config") and "build_info.json" in value
        for idx, value in enumerate(windows_cmd)
        if idx > 0 and windows_cmd[idx - 1] == "--add-data"
    )
    assert "--icon" in windows_cmd
    icon_value = windows_cmd[windows_cmd.index("--icon") + 1]
    assert icon_value.replace("\\", "/").endswith("resources/app_icon.ico")
    assert "--version-file" in windows_cmd
    version_file_value = Path(windows_cmd[windows_cmd.index("--version-file") + 1])
    version_file_text = version_file_value.read_text(encoding="utf-8")
    version_tuple = builder._windows_version_tuple(builder.version)
    version_text = ".".join(str(part) for part in version_tuple)
    assert f"filevers={version_tuple}" in version_file_text
    assert f"prodvers={version_tuple}" in version_file_text
    assert f"StringStruct('FileVersion', '{version_text}')" in version_file_text
    assert f"StringStruct('ProductVersion', '{version_text}')" in version_file_text
    assert "StringStruct('ProductName', 'SSA Consulta Rapida')" in version_file_text
    assert "SSA_CLI_test.exe" in version_file_text

    captured_cmds.clear()
    config["cli_config"]["icon"] = "resources/app_icon.icns"
    ok = builder.build_executable("macos_arm64", "cli", tmp_path / "python3", config)
    assert ok is True
    mac_cmd = captured_cmds[-1]
    assert "--add-data" in mac_cmd
    add_data_value = mac_cmd[mac_cmd.index("--add-data") + 1]
    assert add_data_value.endswith(":config")
    assert any(
        value.endswith(":docs")
        and "GUIA_MIGRACAO_NOVA_INSTALACAO.md" in value
        for idx, value in enumerate(mac_cmd)
        if idx > 0 and mac_cmd[idx - 1] == "--add-data"
    )
    assert "--version-file" not in mac_cmd


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
        if "hdiutil" in str(cmd[0]):
            Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "sign": True, "package": "dmg"}},
    )
    assert ok is True
    assert captured_cmds, "hdiutil nao foi chamado"

    assert captured_cmds[0][:5] == [
        "/usr/bin/codesign",
        "--force",
        "--deep",
        "--sign",
        "-",
    ]
    assert captured_cmds[1][:5] == [
        "/usr/bin/codesign",
        "--verify",
        "--deep",
        "--strict",
        "--verbose=2",
    ]

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


def test_post_process_macos_fails_when_codesign_verify_fails(
    tmp_path, monkeypatch, caplog
):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
    with open(info_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "legacy", "CFBundleDisplayName": "legacy"}, plist_file
        )

    class _Result:
        def __init__(self, returncode=0, stderr=""):
            self.returncode = returncode
            self.stdout = ""
            self.stderr = stderr

    def _fake_run(cmd, **_kwargs):
        if "hdiutil" in str(cmd[0]):
            raise AssertionError("hdiutil nao deve rodar quando codesign falha")
        if "--verify" in cmd:
            return _Result(returncode=1, stderr="signature invalid")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)
    caplog.set_level("ERROR", logger="launchers.build_multiplatform")

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "sign": True, "package": "dmg"}},
    )

    assert ok is False
    assert not (platform_dir / builder._get_macos_dmg_name()).exists()
    assert "Falha ao verificar assinatura do bundle macOS" in caplog.text


def test_post_process_macos_fails_when_hdiutil_returns_error(
    tmp_path, monkeypatch, caplog
):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
    with open(info_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "legacy", "CFBundleDisplayName": "legacy"}, plist_file
        )

    class _Result:
        def __init__(self, returncode=0, stderr=""):
            self.returncode = returncode
            self.stdout = ""
            self.stderr = stderr

    def _fake_run(cmd, **_kwargs):
        if "hdiutil" in str(cmd[0]):
            return _Result(returncode=1, stderr="hdiutil error")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)
    caplog.set_level("ERROR", logger="launchers.build_multiplatform")

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "sign": True, "package": "dmg"}},
    )

    assert ok is False
    assert not (platform_dir / builder._get_macos_dmg_name()).exists()
    assert "Falha ao gerar DMG" in caplog.text


def test_post_process_macos_allows_null_gui_config_name(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
    with open(info_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "legacy", "CFBundleDisplayName": "legacy"}, plist_file
        )

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        if "hdiutil" in str(cmd[0]):
            Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64",
        {"gui_config": {"name": None}, "post_build": {"compress": False, "package": "dmg"}},
    )

    assert ok is True
    assert (platform_dir / builder._get_macos_dmg_name()).exists()


def test_post_process_macos_uses_configured_codesign_identity(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
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
        if "hdiutil" in str(cmd[0]):
            Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setenv("MACOS_CODESIGN_IDENTITY", "Developer ID Application: Example")
    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "sign": True, "package": "dmg"}},
    )

    assert ok is True
    assert captured_cmds[0][4] == "Developer ID Application: Example"


def test_post_process_macos_skips_codesign_when_sign_disabled(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"SSA_GUI_v{builder.version}_macos_arm64.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
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
        if "hdiutil" in str(cmd[0]):
            Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64",
        {"post_build": {"compress": False, "sign": False, "package": "dmg"}},
    )

    assert ok is True
    assert captured_cmds
    assert all("codesign" not in str(cmd[0]) for cmd in captured_cmds)
    assert captured_cmds[-1][0] == "/usr/bin/hdiutil"


def test_post_process_macos_uses_configured_gui_bundle_name(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.base_dir = tmp_path
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    app_name = f"Custom_GUI_v{builder.version}.app"
    app_bundle = platform_dir / app_name
    info_plist = app_bundle / "Contents" / "Info.plist"
    info_plist.parent.mkdir(parents=True)
    with open(info_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "legacy", "CFBundleDisplayName": "legacy"}, plist_file
        )

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        if "hdiutil" in str(cmd[0]):
            Path(cmd[-1]).write_bytes(b"dmg-content")
        return _Result()

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Darwin")
    monkeypatch.setattr("launchers.build_multiplatform.subprocess.run", _fake_run)

    ok = builder.post_process(
        "macos_arm64",
        {
            "gui_config": {"name": "Custom_GUI_v{version}"},
            "post_build": {"compress": False, "package": "dmg"},
        },
    )

    assert ok is True
    with open(info_plist, "rb") as plist_file:
        plist_data = plistlib.load(plist_file)
    assert plist_data["CFBundleName"] == builder.APP_DISPLAY_NAME


def test_post_process_macos_dmg_fails_when_gui_app_missing(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "launchers.build_multiplatform.shutil.which",
        _macos_tool_path,
    )
    ok = builder.post_process(
        "macos_arm64", {"post_build": {"compress": False, "package": "dmg"}}
    )
    assert ok is False


def test_post_process_macos_dmg_rejects_stale_gui_app_fallback(tmp_path, monkeypatch):
    builder = MultiPlatformBuilder()
    builder.dist_dir = tmp_path / "dist"
    platform_dir = builder.dist_dir / "macos_arm64"
    platform_dir.mkdir(parents=True)

    stale_app = platform_dir / "SSA_GUI_v0.00_macos_arm64.app"
    stale_plist = stale_app / "Contents" / "Info.plist"
    stale_plist.parent.mkdir(parents=True)
    with open(stale_plist, "wb") as plist_file:
        plistlib.dump(
            {"CFBundleName": "stale", "CFBundleDisplayName": "stale"}, plist_file
        )

    def _fail_if_called(_name):
        raise AssertionError("hdiutil lookup nao deve ocorrer com app stale")

    monkeypatch.setattr("launchers.build_multiplatform.shutil.which", _fail_if_called)

    ok = builder.post_process(
        "macos_arm64", {"post_build": {"compress": False, "package": "dmg"}}
    )

    assert ok is False
    assert not (platform_dir / builder._get_macos_dmg_name()).exists()


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
    assert "debian_arm64: Linux aarch64" in result.stdout


def test_detect_current_platform_maps_linux_arm64(monkeypatch):
    builder = MultiPlatformBuilder()

    monkeypatch.setattr("launchers.build_multiplatform.platform.system", lambda: "Linux")
    monkeypatch.setattr(
        "launchers.build_multiplatform.platform.machine", lambda: "aarch64"
    )

    assert builder.detect_current_platform() == "debian_arm64"
