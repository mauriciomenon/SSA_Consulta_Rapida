from __future__ import annotations

import subprocess

import scripts.preflight_snyk as preflight_snyk


def test_preflight_snyk_accepts_executable_cli(monkeypatch, capsys):
    monkeypatch.setattr(preflight_snyk.shutil, "which", lambda _name: "/bin/snyk")

    def _run(*_args, **_kwargs):
        return subprocess.CompletedProcess(["snyk", "--version"], 0, "1.1304.2\n", "")

    monkeypatch.setattr(preflight_snyk.subprocess, "run", _run)

    assert preflight_snyk.main() == 0
    assert "OK snyk preflight ok: /bin/snyk (1.1304.2)" in capsys.readouterr().out


def test_preflight_snyk_fails_when_version_command_fails(monkeypatch, capsys):
    monkeypatch.setattr(preflight_snyk.shutil, "which", lambda _name: "/bin/snyk")

    def _run(*_args, **_kwargs):
        return subprocess.CompletedProcess(["snyk", "--version"], 127, "", "missing node")

    monkeypatch.setattr(preflight_snyk.subprocess, "run", _run)

    assert preflight_snyk.main() == 2
    output = capsys.readouterr().out
    assert "ERR snyk --version falhou." in output
    assert "missing node" in output
