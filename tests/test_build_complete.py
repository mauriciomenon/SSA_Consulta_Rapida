from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from launchers import build_complete


def test_build_complete_executes_default_build_flow(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    fake_argv = ["build_complete.py"]
    monkeypatch.setattr(sys, "argv", fake_argv)

    assert build_complete.main() == 0

    run_cmd = calls[0]
    assert "--auto-cleanup" in run_cmd
    assert "--auto-git" not in run_cmd
    assert "--cleanup-online" not in run_cmd


def test_build_complete_cleanup_only_uses_cleanup_online(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    fake_argv = ["build_complete.py", "--cleanup-only"]
    monkeypatch.setattr(sys, "argv", fake_argv)

    assert build_complete.main() == 0

    assert len(calls) == 1
    run_cmd = calls[0]
    assert "--cleanup-online" in run_cmd
    assert "--auto-cleanup" not in run_cmd


def test_build_complete_rejects_auto_git_with_cleanup_only(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_complete.py", "--cleanup-only", "--auto-git"],
    )

    with pytest.raises(SystemExit) as exc:
        build_complete.main()

    assert exc.value.code == 2
    assert calls == []


def test_build_complete_fails_when_builder_return_is_none(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return None

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    monkeypatch.setattr(sys, "argv", ["build_complete.py"])

    assert build_complete.main() == 1
    assert calls == [["--apps", "cli", "gui", "--auto-cleanup"]]


def test_build_complete_auto_git_requires_explicit_flag(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    monkeypatch.setattr(sys, "argv", ["build_complete.py", "--auto-git"])

    assert build_complete.main() == 0
    assert calls == [["--apps", "cli", "gui", "--auto-cleanup", "--auto-git"]]


def test_build_complete_trims_auto_git_message(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_complete.py", "--auto-git", "--git-message", "  build release  "],
    )

    assert build_complete.main() == 0
    assert calls == [
        [
            "--apps",
            "cli",
            "gui",
            "--auto-cleanup",
            "--auto-git",
            "--git-message",
            "build release",
        ]
    ]


def test_build_complete_rejects_git_message_without_auto_git(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_complete.py", "--git-message", "build release"],
    )

    with pytest.raises(SystemExit) as exc:
        build_complete.main()

    assert exc.value.code == 2


def test_build_complete_rejects_empty_git_message(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_complete.py", "--auto-git", "--git-message", "   "],
    )

    with pytest.raises(SystemExit) as exc:
        build_complete.main()

    assert exc.value.code == 2


def test_build_complete_cleanup_only_fails_when_builder_return_is_none(monkeypatch):
    calls = []

    def fake_execute_builder_script(args):
        calls.append(list(args))
        return None

    monkeypatch.setattr(
        build_complete,
        "_execute_builder_script",
        fake_execute_builder_script,
    )
    monkeypatch.setattr(sys, "argv", ["build_complete.py", "--cleanup-only"])

    assert build_complete.main() == 1
    assert calls == [["--cleanup-online"]]


def test_execute_builder_script_invokes_main_and_restores_argv(monkeypatch):
    previous_argv = ["outer.py", "--flag"]
    observed_args = []

    def fake_import_module(name):
        assert name == "launchers.build_multiplatform"

        def fake_main(args=None):
            observed_args.append(list(args or []))
            return 0

        return SimpleNamespace(main=fake_main)

    monkeypatch.setattr(sys, "argv", previous_argv.copy())
    monkeypatch.setattr(build_complete.importlib, "import_module", fake_import_module)

    assert build_complete._execute_builder_script(["--cleanup-online"]) == 0

    assert observed_args == [["--cleanup-online"]]
    assert sys.argv == previous_argv


def test_execute_builder_script_restores_argv_when_import_fails(monkeypatch):
    previous_argv = ["outer.py", "--flag"]

    def fake_import_module(_name):
        raise RuntimeError("import failed")

    monkeypatch.setattr(sys, "argv", previous_argv.copy())
    monkeypatch.setattr(build_complete.importlib, "import_module", fake_import_module)

    try:
        build_complete._execute_builder_script(["--cleanup-online"])
    except RuntimeError as exc:
        assert str(exc) == "import failed"
    else:
        pytest.fail("expected import failure")

    assert sys.argv == previous_argv
