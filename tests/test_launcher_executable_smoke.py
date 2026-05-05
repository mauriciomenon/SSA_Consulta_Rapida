from __future__ import annotations

import subprocess
from pathlib import Path

from launchers import test_executables


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

    assert test_executables._check_executable(exe_path, "CLI") is False
    assert "Timeout ao executar" in capsys.readouterr().out
