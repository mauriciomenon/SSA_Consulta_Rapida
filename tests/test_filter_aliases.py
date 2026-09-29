from __future__ import annotations

import json
from typing import Any, cast

from gui.ssa import filter_aliases


def test_filter_alias_map_reloads_when_file_signature_changes(tmp_path, monkeypatch):
    alias_path = tmp_path / "filter_aliases.json"
    alias_path.write_text(json.dumps({"first": ["a"]}), encoding="utf-8")
    monkeypatch.setattr(filter_aliases, "_FILTER_ALIASES_PATH", alias_path)
    cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()

    first = filter_aliases.load_filter_alias_map_once()
    alias_path.write_text(json.dumps({"second": ["b", "c"]}), encoding="utf-8")
    second = filter_aliases.load_filter_alias_map_once()

    assert first == {"first": ["a"]}
    assert second == {"second": ["b", "c"]}
    cast(Any, filter_aliases.load_filter_alias_map_once).cache_clear()
