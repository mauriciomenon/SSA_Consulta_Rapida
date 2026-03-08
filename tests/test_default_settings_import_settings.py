from __future__ import annotations

import json
from pathlib import Path


def test_default_settings_declares_import_settings_contract() -> None:
    settings_path = Path("config/default_settings.json")
    data = json.loads(settings_path.read_text(encoding="utf-8"))

    import_settings = data.get("import_settings")
    assert isinstance(import_settings, dict)

    expected_keys = {
        "include_processadas_in_full_rescan",
        "processadas_subdir",
        "ignore_nosurvivor_in_full_rescan",
        "nosurvivor_subdir",
        "move_processed_after_import",
        "route_zero_survivor_to_nosurvivor",
        "upsert_short_circuit_policy",
    }
    assert expected_keys.issubset(import_settings.keys())
