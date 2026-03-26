from __future__ import annotations

import pytest


def test_main_skip_import_does_not_call_importer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.app_logic as app_logic
    import interface.cli as cli
    import main

    def unexpected_import(*args, **kwargs):  # noqa: ARG001
        raise AssertionError(
            "run_importer_logic should not be called when --skip-import is set"
        )

    called = {"n": 0}

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:  # noqa: ARG001
        called["n"] += 1

    monkeypatch.setattr(app_logic, "run_importer_logic", unexpected_import)
    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)

    main.main(cli_args=["--skip-import", "--log-level", "CRITICAL"])
    assert called["n"] == 1


def test_main_force_rescan_overrides_skip_import_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.app_logic as app_logic
    import interface.cli as cli
    import main

    calls = {"importer": 0, "cli": 0}

    def fake_run_importer_logic(*, force_import: bool = False):
        calls["importer"] += 1
        assert force_import is True
        return False

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:  # noqa: ARG001
        calls["cli"] += 1

    monkeypatch.setattr(app_logic, "run_importer_logic", fake_run_importer_logic)
    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)

    main.main(cli_args=["--skip-import", "--force-rescan", "--log-level", "CRITICAL"])

    assert calls["importer"] == 1
    assert calls["cli"] == 1
