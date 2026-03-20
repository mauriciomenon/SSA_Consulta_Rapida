from __future__ import annotations

import main


def test_launch_streamlit_uses_dev_env_script(monkeypatch, tmp_path, capsys) -> None:
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

    monkeypatch.setattr(main.shutil, "which", lambda name: "streamlit" if name == "streamlit" else None)
    monkeypatch.setattr(main.subprocess, "Popen", fake_popen)

    assert main.launch_streamlit(str(project_root), port=8765) is True

    out = capsys.readouterr().out
    assert "Streamlit iniciado em background" in out
    assert "http://localhost:8765/" in out
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

    monkeypatch.setattr(main.shutil, "which", lambda name: "streamlit" if name == "streamlit" else None)

    assert main.launch_streamlit(str(project_root)) is False

    out = capsys.readouterr().out
    assert "Streamlit app nao encontrado em" in out
    assert expected_fragment in out.replace("\\", "/")
