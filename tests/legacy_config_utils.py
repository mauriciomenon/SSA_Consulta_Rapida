from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from tests.legacy_path_utils import resolve_project_path
from tests.legacy_report_utils import emit


REFINEMENT_CONFIG_FILES: dict[str, list[str]] = {
    "config/gui_main_preferences.json": ["display_columns"],
    "config/display_mappings.json": [],
    "config/column_priority.json": [],
}


def validate_json_config(
    config_file: str, required_keys: Sequence[str]
) -> tuple[bool, int]:
    config_path = resolve_project_path(config_file)
    if not config_path.exists():
        emit(f"  FAIL {config_file}: Arquivo nao encontrado")
        return False, 0

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        emit(f"  ERR {config_file}: JSON invalido - {e}")
        return False, 0
    except Exception as e:
        emit(f"  ERR {config_file}: Erro - {e}")
        return False, 0

    entries = len(data) if isinstance(data, dict) else 0
    missing_keys = [
        key for key in required_keys if not isinstance(data, dict) or key not in data
    ]
    if missing_keys:
        emit(f"  FAIL {config_file}: {entries} entradas, faltam: {missing_keys}")
        return False, entries

    emit(f"  OK {config_file}: {entries} entradas validas")
    return True, entries


def validate_refinement_configs(
    config_files: Mapping[str, Sequence[str]] = REFINEMENT_CONFIG_FILES,
) -> tuple[bool, int]:
    all_valid = True
    total_entries = 0

    for config_file, required_keys in config_files.items():
        config_valid, entries = validate_json_config(config_file, required_keys)
        total_entries += entries
        if not config_valid:
            all_valid = False

    return all_valid, total_entries
