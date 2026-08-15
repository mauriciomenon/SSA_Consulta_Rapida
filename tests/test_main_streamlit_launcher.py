from __future__ import annotations

import importlib.util
from typing import Any, cast

from interface import streamlit_launcher


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

    def fake_popen(cmd, stdout, stderr, cwd):
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

    def fake_popen(cmd, stdout, stderr, cwd):
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
