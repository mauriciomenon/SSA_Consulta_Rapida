from __future__ import annotations

import importlib.util
import signal
import subprocess
from typing import Any, cast

import pytest

from interface import streamlit_launcher


@pytest.fixture(autouse=True)
def isolate_streamlit_lifecycle(monkeypatch):
    previous = signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(streamlit_launcher, "_STREAMLIT_PROCESSES", [])
    monkeypatch.setattr(streamlit_launcher, "_STREAMLIT_ORIGINAL_SIGTERM_HANDLER", None)
    monkeypatch.setattr(streamlit_launcher, "_STREAMLIT_LAUNCHING", False)
    monkeypatch.setattr(streamlit_launcher, "_STREAMLIT_SIGTERM_PENDING", False)
    yield
    signal.signal(signal.SIGTERM, previous)


def test_launch_streamlit_prefers_current_python_module(
    monkeypatch, tmp_path, capsys
) -> None:
    project_root = tmp_path
    runtime_root = tmp_path / "runtime"
    script_path = project_root / "dev_env" / "streamlit_app.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    captured: dict[str, object] = {}

    class DummyProcess:
        pid = 12345

        def poll(self):
            return None

        def terminate(self):
            return None

    def fake_popen(cmd, stdout, stderr, cwd, **_kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["log_path"] = stdout.name
        return DummyProcess()

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "streamlit" else None,
    )
    monkeypatch.setattr(
        streamlit_launcher.shutil,
        "which",
        lambda name: "streamlit" if name == "streamlit" else None,
    )
    monkeypatch.setattr(streamlit_launcher.subprocess, "Popen", fake_popen)

    assert streamlit_launcher.launch_streamlit(
        str(project_root), port=8765, log_root=str(runtime_root)
    ) is True

    out = capsys.readouterr().out
    assert "Origem do launcher Streamlit: ambiente atual" in out
    assert "Streamlit iniciado em background" in out
    assert "http://localhost:8765/" in out
    assert captured["cwd"] == str(project_root)
    assert captured["log_path"] == str(runtime_root / "logs" / "streamlit.log")
    assert streamlit_launcher._STREAMLIT_PROCESSES
    assert captured["cmd"] == [
        streamlit_launcher.sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.port=8765",
    ]


def test_prune_streamlit_processes_removes_finished_processes() -> None:
    class FinishedProcess:
        def poll(self):
            return 0

    class RunningProcess:
        def poll(self):
            return None

    running = RunningProcess()
    streamlit_launcher._STREAMLIT_PROCESSES[:] = cast(
        Any, [FinishedProcess(), running]
    )

    streamlit_launcher._prune_streamlit_processes()

    assert streamlit_launcher._STREAMLIT_PROCESSES == [running]


def test_launch_streamlit_falls_back_to_path_when_module_missing(
    monkeypatch, tmp_path, capsys
) -> None:
    project_root = tmp_path
    script_path = project_root / "dev_env" / "streamlit_app.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    captured: dict[str, object] = {}

    class DummyProcess:
        pid = 12345

    def fake_popen(cmd, stdout, stderr, cwd, **_kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return DummyProcess()

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    streamlit_exe = str((tmp_path / "tools" / "streamlit.exe").resolve())
    monkeypatch.setattr(
        streamlit_launcher.shutil,
        "which",
        lambda name: streamlit_exe if name == "streamlit" else None,
    )
    monkeypatch.setattr(streamlit_launcher.subprocess, "Popen", fake_popen)

    assert streamlit_launcher.launch_streamlit(str(project_root), port=8765) is True

    out = capsys.readouterr().out
    assert "Origem do launcher Streamlit: PATH" in out
    assert captured["cwd"] == str(project_root)
    assert captured["cmd"] == [
        streamlit_exe,
        "run",
        str(script_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.port=8765",
    ]


def test_launch_streamlit_reports_missing_dev_env_script(
    monkeypatch, tmp_path, capsys
) -> None:
    project_root = tmp_path
    expected_fragment = "dev_env/streamlit_app.py"

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "streamlit" else None,
    )
    monkeypatch.setattr(
        streamlit_launcher.shutil,
        "which",
        lambda name: "streamlit" if name == "streamlit" else None,
    )

    assert streamlit_launcher.launch_streamlit(str(project_root)) is False

    out = capsys.readouterr().out
    assert "Streamlit app nao encontrado em" in out
    assert expected_fragment in out.replace("\\", "/")


def test_launch_streamlit_reports_missing_launcher(
    monkeypatch, tmp_path, capsys
) -> None:
    project_root = tmp_path
    script_path = project_root / "dev_env" / "streamlit_app.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(streamlit_launcher.shutil, "which", lambda name: None)

    assert streamlit_launcher.launch_streamlit(str(project_root)) is False

    out = capsys.readouterr().out
    assert "Streamlit nao encontrado no ambiente atual nem no PATH." in out


def test_failed_launch_restores_sigterm_handler(monkeypatch, tmp_path):
    script = tmp_path / "dev_env" / "streamlit_app.py"
    script.parent.mkdir()
    script.write_text("", encoding="utf-8")
    previous = signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(streamlit_launcher, "_resolve_streamlit_launch_command", lambda: (["streamlit"], "PATH"))

    def fail_popen(*args, **kwargs):
        raise OSError("criacao recusada")

    monkeypatch.setattr(streamlit_launcher.subprocess, "Popen", fail_popen)
    assert streamlit_launcher.launch_streamlit(str(tmp_path)) is False
    assert signal.getsignal(signal.SIGTERM) is previous
    assert not streamlit_launcher._STREAMLIT_PROCESSES
    assert streamlit_launcher._STREAMLIT_LAUNCHING is False


def test_sigterm_during_launch_waits_for_child_registration(monkeypatch, tmp_path):
    script = tmp_path / "dev_env" / "streamlit_app.py"
    script.parent.mkdir()
    script.write_text("", encoding="utf-8")
    terminated = []

    class Process:
        pid = 321

        def poll(self):
            return None

        def terminate(self):
            terminated.append(self.pid)

    process = Process()

    def popen_with_signal(*args, **kwargs):
        assert "preexec_fn" not in kwargs
        streamlit_launcher._terminate_children_and_exit()
        assert terminated == []
        return process

    monkeypatch.setattr(streamlit_launcher, "_resolve_streamlit_launch_command", lambda: (["streamlit"], "PATH"))
    monkeypatch.setattr(streamlit_launcher.subprocess, "Popen", popen_with_signal)
    with pytest.raises(SystemExit) as exc:
        streamlit_launcher.launch_streamlit(str(tmp_path))
    assert exc.value.code == 143
    assert terminated == [321]
    assert streamlit_launcher._STREAMLIT_PROCESSES == [process]


def test_forced_termination_reaps_child():
    calls = []

    class Process:
        def poll(self):
            return None

        def terminate(self):
            calls.append("terminate")

        def wait(self, timeout):
            calls.append("wait")
            if calls.count("wait") == 1:
                raise subprocess.TimeoutExpired("streamlit", timeout)
            return -9

        def kill(self):
            calls.append("kill")

    streamlit_launcher._terminate_process(Process())
    assert calls == ["terminate", "wait", "kill", "wait"]


def test_launch_rejects_worker_thread(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(streamlit_launcher.threading, "current_thread", lambda: object())
    assert streamlit_launcher.launch_streamlit(str(tmp_path)) is False
    assert "thread principal" in capsys.readouterr().out
    assert not streamlit_launcher._STREAMLIT_PROCESSES
