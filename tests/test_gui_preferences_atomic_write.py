import os
from types import SimpleNamespace
from typing import Any, cast


def test_persist_gui_preferences_uses_atomic_writer(monkeypatch, tmp_path):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa, "GUI_MAIN_PREFERENCES", {"x": 1})
    expected_path = tmp_path / "cfg" / "gui_main_preferences.json"

    calls = []

    def _fake_atomic(path, data, *, indent=2, ensure_ascii=False):
        calls.append((path, data, indent, ensure_ascii))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{}")

    monkeypatch.setattr(gui_ssa, "atomic_write_json_file", _fake_atomic)
    monkeypatch.setattr(
        gui_ssa, "get_gui_main_preferences_path", lambda: str(expected_path)
    )

    gui_ssa.SSAMainWindow._persist_gui_preferences(cast(Any, object()))

    assert calls
    path, data, indent, ensure_ascii = calls[0]
    assert path == str(expected_path)
    assert data == {"x": 1}
    assert indent == 2
    assert ensure_ascii is False


def test_persist_visible_columns_order_uses_resolved_gui_config_path(
    monkeypatch, tmp_path
):
    from gui import gui_ssa

    expected_path = tmp_path / "cfg_runtime" / "gui_main_preferences.json"
    monkeypatch.setattr(
        gui_ssa, "get_gui_main_preferences_path", lambda: str(expected_path)
    )
    monkeypatch.setattr(
        gui_ssa,
        "GUI_MAIN_PREFERENCES",
        {
            "display_columns": ["numero_ssa", "situacao", "descricao_ssa"],
            "hidden_columns": ["descricao_localizacao"],
        },
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    calls = []

    def _fake_atomic(path, data, *, indent=2, ensure_ascii=False):
        calls.append((path, data, indent, ensure_ascii))

    monkeypatch.setattr(gui_ssa, "atomic_write_json_file", _fake_atomic)

    fake_window = cast(
        Any,
        SimpleNamespace(
            visible_columns=["numero_ssa", "situacao"],
            default_columns=["numero_ssa", "situacao", "descricao_ssa"],
            display_map={
                "numero_ssa": "Numero SSA",
                "situacao": "Sit.",
                "descricao_ssa": "Descricao da SSA",
                "descricao_localizacao": "Desc. Localizacao",
            },
            column_selector=SimpleNamespace(
                available_columns=[
                    "numero_ssa",
                    "situacao",
                    "descricao_ssa",
                    "descricao_localizacao",
                ]
            ),
        ),
    )

    gui_ssa.SSAMainWindow._persist_visible_columns_order(fake_window)

    assert calls
    path, data, indent, ensure_ascii = calls[0]
    assert path == str(expected_path)
    assert data["display_columns"] == ["numero_ssa", "situacao"]
    assert data["hidden_columns"] == ["descricao_ssa", "descricao_localizacao"]
    assert indent == 2
    assert ensure_ascii is False


def test_theme_persist_uses_resolved_gui_config_path(monkeypatch, tmp_path):
    from gui.ssa import gui_theme

    expected_path = tmp_path / "cfg_theme" / "gui_main_preferences.json"
    monkeypatch.setattr(
        gui_theme, "get_gui_main_preferences_path", lambda: str(expected_path)
    )

    calls = []

    def _fake_atomic(path, data, *, indent=2, ensure_ascii=False):
        calls.append((path, data, indent, ensure_ascii))

    monkeypatch.setattr(gui_theme, "atomic_write_json_file", _fake_atomic)

    ok = gui_theme.persist_gui_preferences(
        {"gui_settings": {"theme": "gruvbox"}},
        "/tmp/ignored-project-root",
    )

    assert ok is True
    assert calls
    path, data, indent, ensure_ascii = calls[0]
    assert path == str(expected_path)
    assert data["gui_settings"]["theme"] == "gruvbox"
    assert indent == 2
    assert ensure_ascii is False
