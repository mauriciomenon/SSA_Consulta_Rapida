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


def test_build_complete_fails_when_builder_return_is_none(monkeypatch, caplog):
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
    assert any(
        record.getMessage() == "ERR Build wrapper recebeu exit code ausente"
        for record in caplog.records
    )


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

    assert build_complete._execute_builder_script(["--clean"]) == 0

    assert observed_args == [["--clean"]]
    assert sys.argv == previous_argv


def test_execute_builder_script_restores_argv_when_import_fails(monkeypatch):
    previous_argv = ["outer.py", "--flag"]

    def fake_import_module(_name):
        raise RuntimeError("import failed")

    monkeypatch.setattr(sys, "argv", previous_argv.copy())
    monkeypatch.setattr(build_complete.importlib, "import_module", fake_import_module)

    try:
        build_complete._execute_builder_script(["--clean"])
    except RuntimeError as exc:
        assert str(exc) == "import failed"
    else:
        pytest.fail("expected import failure")

    assert sys.argv == previous_argv


@pytest.mark.parametrize("flag", ["--auto-git", "--cleanup-only", "--git-message=x"])
def test_build_complete_has_no_git_operations(monkeypatch, flag):
    """CD-39: build nao faz git add/commit/push nem git rm por conta propria."""
    monkeypatch.setattr(sys, "argv", ["build_complete.py", flag])
    with pytest.raises(SystemExit) as exc:
        build_complete.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("flag", ["--auto-git", "--cleanup-online"])
def test_build_multiplatform_has_no_git_operations(flag):
    from launchers import build_multiplatform

    with pytest.raises(SystemExit) as exc:
        build_multiplatform.main([flag])
    assert exc.value.code == 2
    assert not hasattr(build_multiplatform.MultiPlatformBuilder, "git_add_commit_push")
