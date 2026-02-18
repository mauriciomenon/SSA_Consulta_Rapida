import os
from typing import Any, cast


def test_persist_gui_preferences_uses_atomic_writer(monkeypatch, tmp_path):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa, "project_root", str(tmp_path))
    monkeypatch.setattr(gui_ssa, "GUI_MAIN_PREFERENCES", {"x": 1})

    calls = []

    def _fake_atomic(path, data, *, indent=2, ensure_ascii=False):
        calls.append((path, data, indent, ensure_ascii))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{}")

    monkeypatch.setattr(gui_ssa, "atomic_write_json_file", _fake_atomic)

    gui_ssa.SSAMainWindow._persist_gui_preferences(cast(Any, object()))

    assert calls
    path, data, indent, ensure_ascii = calls[0]
    assert path == os.path.join(str(tmp_path), "config", "gui_main_preferences.json")
    assert data == {"x": 1}
    assert indent == 2
    assert ensure_ascii is False
