from __future__ import annotations

import importlib.util

import main


def test_launch_streamlit_prefers_current_python_module(monkeypatch, tmp_path, capsys) -> None:
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

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object() if name == "streamlit" else None)
    monkeypatch.setattr(main.shutil, "which", lambda name: "streamlit" if name == "streamlit" else None)
    monkeypatch.setattr(main.subprocess, "Popen", fake_popen)

    assert main.launch_streamlit(str(project_root), port=8765) is True

    out = capsys.readouterr().out
    assert "Origem do launcher Streamlit: ambiente atual" in out
    assert "Streamlit iniciado em background" in out
    assert "http://localhost:8765/" in out
    assert captured["cwd"] == str(project_root)
    assert captured["cmd"] == [
        main.sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script_path),
        "--server.headless=true",
        "--server.port=8765",
    ]


def test_launch_streamlit_falls_back_to_path_when_module_missing(monkeypatch, tmp_path, capsys) -> None:
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
    monkeypatch.setattr(main.shutil, "which", lambda name: "streamlit" if name == "streamlit" else None)
    monkeypatch.setattr(main.subprocess, "Popen", fake_popen)

    assert main.launch_streamlit(str(project_root), port=8765) is True

    out = capsys.readouterr().out
    assert "Origem do launcher Streamlit: PATH" in out
    assert captured["cwd"] == str(project_root)
    assert captured["cmd"] == [
        "streamlit",
        "run",
        str(script_path),
        "--server.headless=true",
        "--server.port=8765",
    ]


def test_launch_streamlit_reports_missing_dev_env_script(monkeypatch, tmp_path, capsys) -> None:
    project_root = tmp_path
    expected_fragment = "dev_env/streamlit_app.py"

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object() if name == "streamlit" else None)
    monkeypatch.setattr(main.shutil, "which", lambda name: "streamlit" if name == "streamlit" else None)

    assert main.launch_streamlit(str(project_root)) is False

    out = capsys.readouterr().out
    assert "Streamlit app nao encontrado em" in out
    assert expected_fragment in out.replace("\\", "/")


def test_launch_streamlit_reports_missing_launcher(monkeypatch, tmp_path, capsys) -> None:
    project_root = tmp_path
    script_path = project_root / "dev_env" / "streamlit_app.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(main.shutil, "which", lambda name: None)

    assert main.launch_streamlit(str(project_root)) is False

    out = capsys.readouterr().out
    assert "Streamlit nao encontrado no ambiente atual nem no PATH." in out
