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
    from gui.ssa import gui_preferences_persistence

    expected_path = tmp_path / "cfg_theme" / "gui_main_preferences.json"
    monkeypatch.setattr(
        gui_preferences_persistence,
        "get_gui_main_preferences_path",
        lambda: str(expected_path),
    )

    calls = []

    def _fake_atomic(path, data, *, indent=2, ensure_ascii=False):
        calls.append((path, data, indent, ensure_ascii))

    monkeypatch.setattr(
        gui_preferences_persistence, "atomic_write_json_file", _fake_atomic
    )

    ok = gui_preferences_persistence.persist_gui_preferences(
        {"gui_settings": {"theme": "gruvbox"}},
    )

    assert ok is True
    assert calls
    path, data, indent, ensure_ascii = calls[0]
    assert path == str(expected_path)
    assert data["gui_settings"]["theme"] == "gruvbox"
    assert indent == 2
    assert ensure_ascii is False


def test_theme_dialog_skips_default_preference_write_when_unchanged(monkeypatch):
    from PyQt6 import QtWidgets

    from gui.ssa import gui_preferences_persistence, gui_theme

    class _FakeSignal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

    class _FakeDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def setWindowTitle(self, *_args, **_kwargs) -> None:
            return None

        def setModal(self, *_args, **_kwargs) -> None:
            return None

        def exec(self) -> int:
            return self.DialogCode.Accepted

        def accept(self) -> None:
            return None

        def reject(self) -> None:
            return None

    class _FakeCombo:
        def __init__(self, *_args, **_kwargs) -> None:
            self._items: list[tuple[str, str]] = []
            self._index = 0

        def addItem(self, label: str, value: str) -> None:
            self._items.append((label, value))

        def setCurrentIndex(self, index: int) -> None:
            self._index = int(index)

        def currentData(self) -> str:
            return self._items[self._index][1]

    class _FakeCheckBox:
        def __init__(self, *_args, **_kwargs) -> None:
            self._checked = False

        def setChecked(self, value: bool) -> None:
            self._checked = bool(value)

        def isChecked(self) -> bool:
            return self._checked

    class _FakeDialogButtonBox:
        class StandardButton:
            Ok = 1
            Cancel = 2

        def __init__(self, *_args, **_kwargs) -> None:
            self.accepted = _FakeSignal()
            self.rejected = _FakeSignal()

    class _FakeLabel:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

    class _FakeLayout:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def addWidget(self, *_args, **_kwargs) -> None:
            return None

    class _Window:
        _current_theme = "gruvbox"

        def __init__(self) -> None:
            self.applied: list[str] = []

        def apply_theme(self, theme: str) -> None:
            self.applied.append(theme)

    monkeypatch.setattr(QtWidgets, "QDialog", _FakeDialog)
    monkeypatch.setattr(QtWidgets, "QComboBox", _FakeCombo)
    monkeypatch.setattr(QtWidgets, "QCheckBox", _FakeCheckBox)
    monkeypatch.setattr(QtWidgets, "QDialogButtonBox", _FakeDialogButtonBox)
    monkeypatch.setattr(QtWidgets, "QLabel", _FakeLabel)
    monkeypatch.setattr(QtWidgets, "QVBoxLayout", _FakeLayout)

    persist_calls = []
    monkeypatch.setattr(
        gui_preferences_persistence,
        "persist_gui_preferences_async",
        lambda *args, **kwargs: persist_calls.append((args, kwargs)) or True,
    )

    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    window = _Window()

    gui_theme.show_theme_selection_dialog(
        window,
        gui_prefs=prefs,
        project_root="/tmp/ignored-project-root",
    )

    assert window.applied == ["gruvbox"]
    assert persist_calls == []

    temporary_window = _Window()
    temporary_window._current_theme = "windows7"
    temporary_prefs = {
        "gui_settings": {"theme": "windows7", "theme_default": "gruvbox"}
    }

    gui_theme.show_theme_selection_dialog(
        temporary_window,
        gui_prefs=temporary_prefs,
        project_root="/tmp/ignored-project-root",
    )

    assert temporary_window.applied == ["windows7"]
    assert temporary_prefs["gui_settings"]["theme_default"] == "gruvbox"
    assert persist_calls == []
