from __future__ import annotations

import pytest


def test_main_skip_import_does_not_call_importer(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.app_logic as app_logic
    import interface.cli as cli
    import main

    def unexpected_import(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("run_importer_logic should not be called when --skip-import is set")

    called = {"n": 0}

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:  # noqa: ARG001
        called["n"] += 1

    monkeypatch.setattr(app_logic, "run_importer_logic", unexpected_import)
    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)

    main.main(cli_args=["--skip-import", "--log-level", "CRITICAL"])
    assert called["n"] == 1


def test_main_skip_import_conflicts_with_force_rescan() -> None:
    import main

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--skip-import", "--force-rescan"])

    assert excinfo.value.code == 2

