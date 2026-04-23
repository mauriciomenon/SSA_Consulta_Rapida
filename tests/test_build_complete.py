from __future__ import annotations

import sys

from launchers import build_complete


def test_build_complete_executes_default_build_flow(monkeypatch):
    calls = []

    class _Result:
        returncode = 0

    def fake_run(cmd, cwd=None, check=False, timeout=None):
        calls.append({"cmd": list(cmd), "cwd": cwd, "check": check, "timeout": timeout})
        return _Result()

    monkeypatch.setattr("launchers.build_complete.subprocess.run", fake_run)
    fake_argv = ["build_complete.py"]
    monkeypatch.setattr(sys, "argv", fake_argv)

    assert build_complete.main() == 0

    run_cmd = calls[0]["cmd"]
    assert "python" in run_cmd[0].lower()
    assert "--auto-cleanup" in run_cmd
    assert "--auto-git" in run_cmd
    assert "--cleanup-online" not in run_cmd
    assert calls[0]["timeout"] == 1800


def test_build_complete_cleanup_only_uses_cleanup_online(monkeypatch):
    calls = []

    class _Result:
        returncode = 0

    def fake_run(cmd, cwd=None, check=False, timeout=None):
        calls.append({"cmd": list(cmd), "timeout": timeout})
        return _Result()

    monkeypatch.setattr("launchers.build_complete.subprocess.run", fake_run)
    fake_argv = ["build_complete.py", "--cleanup-only"]
    monkeypatch.setattr(sys, "argv", fake_argv)

    assert build_complete.main() == 0

    assert len(calls) == 1
    run_cmd = calls[0]["cmd"]
    assert "--cleanup-online" in run_cmd
    assert "--auto-cleanup" not in run_cmd
    assert calls[0]["timeout"] == 300
