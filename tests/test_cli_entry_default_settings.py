from __future__ import annotations

import core.config_manager as config_manager
import interface.cli as cli
import launchers.cli_entry as cli_entry


def test_cli_entry_initializes_default_settings_before_cli_loop(monkeypatch, tmp_path):
    calls = []

    def fake_ensure_default_settings(*, fail_fast: bool = True):
        calls.append(("settings", fail_fast))
        return []

    def fake_start_cli_loop(db_path: str, table_name: str) -> None:
        calls.append(("cli", db_path, table_name))

    db_path = tmp_path / "ssas.db"

    monkeypatch.setattr(
        config_manager,
        "ensure_default_settings",
        fake_ensure_default_settings,
    )
    monkeypatch.setattr(cli, "start_cli_loop", fake_start_cli_loop)
    monkeypatch.setenv("SSA_DB_PATH", str(db_path))
    monkeypatch.setenv("SSA_TABLE_NAME", "ssa_table_test")

    cli_entry.main()

    assert calls == [
        ("settings", False),
        ("cli", str(db_path), "ssa_table_test"),
    ]
