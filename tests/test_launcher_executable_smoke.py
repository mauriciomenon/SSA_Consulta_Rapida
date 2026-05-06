from __future__ import annotations

import subprocess
from pathlib import Path

from launchers import smoke_validation
from launchers import test_executables
from launchers.runtime_entry_helpers import GUI_SMOKE_OK_MARKER, SMOKE_TEST_ENV


def test_executable_path_helpers_use_windows_extension(tmp_path: Path) -> None:
    cli_path = smoke_validation.cli_executable_path(
        tmp_path,
        "4.37",
        "windows_amd64",
    )
    simple_path = smoke_validation.cli_executable_path(
        tmp_path,
        "4.37",
        "windows_amd64",
        simple=True,
    )
    gui_path = smoke_validation.gui_executable_path(
        tmp_path,
        "4.37",
        "windows_amd64",
    )

    assert cli_path.name == "SSA_CLI_v4.37_windows_amd64.exe"
    assert simple_path.name == "SSA_CLI_v4.37_SIMPLES.exe"
    assert gui_path.name == "SSA_GUI_v4.37_windows_amd64.exe"
    assert (
        smoke_validation.cli_executable_path(
            tmp_path,
            "4.37",
            "debian_amd64",
            simple=True,
        ).name
        == "SSA_CLI_v4.37_SIMPLES"
    )


def test_check_executable_timeout_is_failure(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    exe_path = tmp_path / "SSA_CLI"
    exe_path.write_text("", encoding="utf-8")

    def _fake_run(cmd, **kwargs):
        if cmd[0] == "file":
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=float(kwargs.get("timeout") or 0))

    monkeypatch.setattr(test_executables.subprocess, "run", _fake_run)
    monkeypatch.setattr(smoke_validation.subprocess, "run", _fake_run)

    assert test_executables._check_executable(exe_path, "CLI") is False
    capsys.readouterr()


def test_gui_startup_smoke_executes_artifact_with_smoke_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    exe_path = tmp_path / "SSA_GUI"
    exe_path.write_text("", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def _fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs["env"]))
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=f"{GUI_SMOKE_OK_MARKER} v4.37\n",
            stderr="",
        )

    monkeypatch.setattr(smoke_validation.subprocess, "run", _fake_run)

    result = smoke_validation.run_gui_startup_smoke(
        executable=exe_path,
        repo_root=tmp_path,
    )

    assert result.ok is True
    assert calls[0][0] == [str(exe_path)]
    assert calls[0][1][SMOKE_TEST_ENV] == "1"
