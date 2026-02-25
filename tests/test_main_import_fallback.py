from __future__ import annotations

import pytest


def test_main_no_automatic_legacy_retry_when_optimized_runtime_fails_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import armazenamento.database_optimized as db_opt
    import core.app_logic as app_logic
    import main

    calls = {"importer": 0, "disable": 0}

    def fake_enable() -> None:
        return None

    def fake_disable() -> None:
        calls["disable"] += 1

    def fake_run_importer_logic(*, force_import: bool = False):  # noqa: ARG001
        calls["importer"] += 1
        raise RuntimeError("optimized runtime failure")

    monkeypatch.setattr(db_opt, "enable_optimized_import", fake_enable)
    monkeypatch.setattr(db_opt, "disable_optimized_import", fake_disable)
    monkeypatch.setattr(app_logic, "run_importer_logic", fake_run_importer_logic)

    with pytest.raises(SystemExit) as excinfo:
        main.main(cli_args=["--log-level", "CRITICAL"])
    assert excinfo.value.code == 1

    assert calls["importer"] == 1
    assert calls["disable"] == 1
