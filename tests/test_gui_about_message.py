from __future__ import annotations

from gui import gui_ssa


def test_build_about_message_includes_commit_hash(monkeypatch) -> None:
    monkeypatch.setattr(gui_ssa, "resolve_uv_version_text", lambda: "0.0.0-test")
    monkeypatch.setattr(gui_ssa, "resolve_git_commit_hash_text", lambda: "abc1234")

    message = gui_ssa.build_about_message("9.9.9")

    assert "Versao app: 9.9.9" in message
    assert "Commit: abc1234" in message


def test_build_about_message_uses_embedded_build_info(monkeypatch, tmp_path) -> None:
    build_info = tmp_path / "build_info.json"
    build_info.write_text(
        '{"git_commit_short":"def5678","build_datetime":"2026-04-28T06:30:00-03:00","uv_version":"uv 0.9.18"}',
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

    assert "uv: uv 0.9.18" in message
    assert "Commit: def5678" in message
    assert "Build: 2026-04-28T06:30:00-03:00" in message
