"""CF-11: cli_enhancements.json so com a flag que tem efeito (enhanced_table_printer)."""

from __future__ import annotations

import json
from pathlib import Path

from interface import cli
from interface.cli_enhancement_manager import CLIEnhancementManager


def test_debug_commands_removed_from_cli():
    assert "debug" not in cli.COMMAND_HANDLERS
    assert "toggle-debug" not in cli.COMMAND_HANDLERS
    assert "toggle-debug" not in cli._build_cli_plain_help_text(detailed=True)


def test_status_report_lists_only_live_flag():
    report = CLIEnhancementManager().get_status_report()

    assert "Enhanced Table Printer" in report
    assert "Debug Output" not in report
    assert "Configuração Unificada:" not in report


def test_versioned_file_has_only_live_flag():
    data = json.loads(Path("config/cli_enhancements.json").read_text(encoding="utf-8"))
    assert data == {"enhanced_table_printer": True, "version": "1.0"}


def test_enhancements_path_env_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("SSA_CLI_ENHANCEMENTS_PATH", str(tmp_path / "outro.json"))
    monkeypatch.setenv("SSA_CONFIG_DIR", str(tmp_path))

    manager = CLIEnhancementManager()

    assert manager.settings_file == str(tmp_path / "cli_enhancements.json")
