from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any, cast

from gui import gui_ssa


def test_build_about_message_includes_commit_hash(monkeypatch) -> None:
    monkeypatch.setattr(gui_ssa, "resolve_uv_version_text", lambda: "0.0.0-test")
    monkeypatch.setattr(gui_ssa, "resolve_git_commit_hash_text", lambda: "abc1234")

    message = gui_ssa.build_about_message("9.9.9")

    assert "Versao: 9.9.9" in message
    assert "Autor: Mauricio Menon" in message
    assert "Data ISO: indisponivel" in message
    assert "Commit: abc1234" in message


def test_build_about_message_uses_embedded_build_info(monkeypatch, tmp_path) -> None:
    build_info = tmp_path / "build_info.json"
    build_info.write_text(
        '{"git_commit_short":"def5678","build_datetime":"2026-04-28T06:30:00-03:00","uv_version":"uv 0.9.18","c_compiler_version":"gcc 14.2.0","rustc_version":"rustc 1.90.0"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gui_ssa,
        "_iter_build_info_candidates",
        lambda: (build_info,),
        raising=False,
    )
    monkeypatch.setattr(gui_ssa, "resolve_uv_version_text", lambda: "indisponivel")
    monkeypatch.setattr(
        gui_ssa, "resolve_git_commit_hash_text", lambda: "indisponivel"
    )

    message = gui_ssa.build_about_message("9.9.9")

    assert "Versao: 9.9.9" in message
    assert "Autor: Mauricio Menon" in message
    assert "Commit: def5678" in message
    assert "Data ISO: 2026-04-28T06:30:00-03:00" in message


def test_resolve_uv_version_uses_resolved_executable(monkeypatch) -> None:
    captured = {}

    def _fake_run(cmd, **_kwargs):  # noqa: ANN001
        captured["cmd"] = cmd
        return SimpleNamespace(stdout="uv 0.9.18", stderr="")

    monkeypatch.setattr(gui_ssa.shutil, "which", lambda name: f"/tools/{name}")
    monkeypatch.setattr(gui_ssa.subprocess, "run", _fake_run)

    assert gui_ssa.resolve_uv_version_text() == "uv 0.9.18"
    assert captured["cmd"] == ["/tools/uv", "--version"]


def test_resolve_git_commit_returns_unavailable_without_git(monkeypatch) -> None:
    def _unexpected_run(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("subprocess.run should not be called without git")

    monkeypatch.setattr(gui_ssa.shutil, "which", lambda _name: None)
    monkeypatch.setattr(gui_ssa.subprocess, "run", _unexpected_run)

    assert gui_ssa.resolve_git_commit_hash_text() == "indisponivel"


def test_iter_build_info_candidates_includes_pyinstaller_internal(
    monkeypatch, tmp_path
) -> None:
    runtime_root = tmp_path / "runtime_root"
    bundled_root = tmp_path / "bundle_root"
    runtime_root.mkdir()
    bundled_root.mkdir()
    monkeypatch.setattr(gui_ssa, "project_root", str(runtime_root))
    monkeypatch.setenv("SSA_BUNDLED_ROOT", str(bundled_root))
    monkeypatch.delenv("SSA_CONFIG_DIR", raising=False)

    candidates = list(gui_ssa._iter_build_info_candidates())

    assert os.path.join(str(bundled_root), "config", "build_info.json") in candidates
    assert os.path.join(str(bundled_root), "_internal", "config", "build_info.json") in candidates


def test_open_installation_guide_uses_bundled_internal_docs(
    monkeypatch, tmp_path
) -> None:
    runtime_root = tmp_path / "runtime_root"
    bundled_root = tmp_path / "bundle_root"
    guide_path = (
        bundled_root / "_internal" / "docs" / "GUIA_MIGRACAO_NOVA_INSTALACAO.md"
    )
    runtime_root.mkdir()
    guide_path.parent.mkdir(parents=True)
    guide_path.write_text("guia", encoding="utf-8")
    monkeypatch.setattr(gui_ssa, "project_root", str(runtime_root))
    monkeypatch.setenv("SSA_BUNDLED_ROOT", str(bundled_root))
    monkeypatch.setattr(gui_ssa, "QT_AVAILABLE", False)
    monkeypatch.setattr(
        gui_ssa.SSAMainWindow,
        "_validate_local_open_target",
        staticmethod(lambda path, **_kwargs: path),
    )
    monkeypatch.setattr(
        gui_ssa.ssa_system,
        "resolve_platform_open_command",
        lambda: "fake-open",
    )
    opened = {}

    class _FakeLabel:
        def __init__(self) -> None:
            self.text = ""

        def setText(self, value: str) -> None:
            self.text = value

    class _FakeWindow:
        def __init__(self) -> None:
            self.status_label = _FakeLabel()

    def _fake_popen(cmd, shell=False):  # noqa: ANN001
        opened["cmd"] = list(cmd)
        opened["shell"] = shell

    monkeypatch.setattr(gui_ssa.subprocess, "Popen", _fake_popen)

    result = gui_ssa.SSAMainWindow.open_installation_guide(cast(Any, _FakeWindow()))

    assert result["opened"] is True
    assert result["path"] == os.path.abspath(str(guide_path))
    assert opened["cmd"] == ["fake-open", "--", os.path.abspath(str(guide_path))]
    assert opened["shell"] is False
