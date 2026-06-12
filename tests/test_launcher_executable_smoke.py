from __future__ import annotations

import subprocess
from pathlib import Path

from launchers import build_simple
from launchers import smoke_validation
from launchers import test_executables
from launchers.runtime_entry_helpers import GUI_SMOKE_OK_MARKER, SMOKE_TEST_ENV


def test_executable_path_helpers_use_windows_extension(tmp_path: Path) -> None:
    cli_path = smoke_validation.cli_executable_path(
        tmp_path,
        "4.42",
        "windows_amd64",
    )
    simple_path = smoke_validation.cli_executable_path(
        tmp_path,
        "4.42",
        "windows_amd64",
        simple=True,
    )
    gui_path = smoke_validation.gui_executable_path(
        tmp_path,
        "4.42",
        "windows_amd64",
    )

    assert cli_path.name == "SSA_CLI_v4.42_windows_amd64.exe"
    assert simple_path.name == "SSA_CLI_v4.42_SIMPLES.exe"
    assert gui_path.name == "SSA_GUI_v4.42_windows_amd64.exe"
    assert (
        smoke_validation.cli_executable_path(
            tmp_path,
            "4.42",
            "debian_amd64",
            simple=True,
        ).name
        == "SSA_CLI_v4.42_SIMPLES"
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
            stdout=f"{GUI_SMOKE_OK_MARKER} v4.42\n",
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


def test_build_simple_validates_functional_import_smoke(
    tmp_path: Path,
    monkeypatch,
) -> None:
    version = "9.99"
    monkeypatch.setattr(build_simple, "APP_VERSION", version)
    monkeypatch.setattr(build_simple, "REPO_ROOT", tmp_path)
    exe_path = smoke_validation.cli_executable_path(tmp_path, version, simple=True)
    subprocess_calls: list[list[str]] = []
    smoke_calls: list[Path] = []

    def _fake_run(cmd, **_kwargs):
        subprocess_calls.append(list(cmd))
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        exe_path.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def _fake_smoke(*, executable, repo_root, timeout=120):
        smoke_calls.append(executable)
        assert repo_root == tmp_path
        assert timeout == 120
        return smoke_validation.SmokeValidationResult(
            ok=True,
            imported_rows=1,
            returncode=0,
        )

    monkeypatch.setattr(build_simple.subprocess, "run", _fake_run)
    monkeypatch.setattr(build_simple, "run_cli_import_smoke", _fake_smoke)

    assert build_simple.main() == 0
    assert smoke_calls == [exe_path]
    assert all("--help" not in call for call in subprocess_calls)


def test_manual_executable_runner_requires_all_expected_artifacts(monkeypatch) -> None:
    monkeypatch.setattr(
        test_executables,
        "_executable_specs",
        lambda: [
            {"name": "CLI Multi-Plataforma", "path": Path("cli")},
            {"name": "CLI Simples", "path": Path("simple")},
        ],
    )
    monkeypatch.setattr(
        test_executables,
        "_check_executable",
        lambda _path, name: name == "CLI Multi-Plataforma",
    )

    assert test_executables.main() == 1
