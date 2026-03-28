from __future__ import annotations

from gui import gui_ssa


def test_build_about_message_includes_commit_hash(monkeypatch) -> None:
    monkeypatch.setattr(gui_ssa, "resolve_uv_version_text", lambda: "0.0.0-test")
    monkeypatch.setattr(
        gui_ssa, "resolve_git_commit_hash_text", lambda: "abc1234"
    )

    message = gui_ssa.build_about_message("9.9.9")

    assert "Versao app: 9.9.9" in message
    assert "Commit: abc1234" in message
