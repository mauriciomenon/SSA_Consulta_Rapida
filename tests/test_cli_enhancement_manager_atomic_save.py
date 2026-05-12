import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import interface.cli_enhancement_manager as cli_mgr_mod  # noqa: E402


def test_cli_enhancement_settings_save_is_atomic_on_failure(tmp_path, monkeypatch):
    mgr = cli_mgr_mod.CLIEnhancementManager()
    mgr.settings_file = str(tmp_path / "cli_enhancements.json")

    initial = {"enhanced_table_printer": True}
    original_text = json.dumps(initial, indent=2, ensure_ascii=False)
    with open(mgr.settings_file, "w", encoding="utf-8") as f:
        f.write(original_text)

    base_name = os.path.basename(mgr.settings_file)
    tmp_prefix = f".{base_name}.tmp."

    def bad_dump(_obj, fh, indent=2, ensure_ascii=False):  # noqa: ARG001
        fh.write("{")
        fh.flush()
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_mgr_mod.json, "dump", bad_dump)

    mgr.settings = {"debug_output": True}
    try:
        mgr._save_settings()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "Falha ao persistir configuracoes CLI" in str(exc)

    assert raised

    with open(mgr.settings_file, "r", encoding="utf-8") as f:
        assert f.read() == original_text
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(tmp_prefix)]
    assert leftovers == []


def test_cli_enhancement_settings_save_writes_valid_json(tmp_path):
    mgr = cli_mgr_mod.CLIEnhancementManager()
    mgr.settings_file = str(tmp_path / "cli_enhancements.json")

    mgr.settings = {"debug_output": False, "version": "1.0"}
    mgr._save_settings()

    with open(mgr.settings_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == mgr.settings
