import json

from core.config_manager import load_column_mappings_integrity


def test_column_mappings_integrity_restores_defaults(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    # Point loader to temp config dir
    monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

    # 1) Missing file -> should create with defaults
    mappings = load_column_mappings_integrity()
    assert isinstance(mappings, dict) and mappings
    path = cfg_dir / "column_mappings.json"
    assert path.exists()

    # 2) Corrupted file -> should restore defaults
    path.write_text("[]", encoding="utf-8")  # invalid structure
    mappings2 = load_column_mappings_integrity()
    assert isinstance(mappings2, dict) and mappings2

    # 3) Minimal valid structure should be returned as-is
    minimal = {"numero_ssa": ["Nº SSA"]}
    path.write_text(json.dumps(minimal, ensure_ascii=False), encoding="utf-8")
    mappings3 = load_column_mappings_integrity()
    assert mappings3 == minimal
