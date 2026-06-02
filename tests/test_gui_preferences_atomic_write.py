import threading
from types import SimpleNamespace
from typing import Any, cast


def _capture_preferences_queue(monkeypatch, gui_ssa):
    calls: list[dict] = []

    def _fake_queue(data):
        calls.append(dict(data))
        return True

    monkeypatch.setattr(
        gui_ssa.ssa_system_controller,
        "queue_gui_preferences_write",
        _fake_queue,
    )
    return calls


def test_persist_gui_preferences_queues_preferences_write(monkeypatch, tmp_path):
    from gui import gui_ssa

    monkeypatch.setattr(gui_ssa, "GUI_MAIN_PREFERENCES", {"x": 1})
    calls = _capture_preferences_queue(monkeypatch, gui_ssa)

    gui_ssa.SSAMainWindow._persist_gui_preferences(cast(Any, object()))

    assert calls == [{"x": 1}]


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

    calls = _capture_preferences_queue(monkeypatch, gui_ssa)

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
    data = calls[0]
    assert data["display_columns"] == ["numero_ssa", "situacao"]
    assert data["hidden_columns"] == ["descricao_ssa", "descricao_localizacao"]


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


def test_preferences_writer_snapshots_before_enqueue():
    from gui.ssa.gui_preferences_persistence import PreferencesWriter

    written: list[dict] = []
    done = threading.Event()

    def _write(data, *, retries):
        written.append(data)
        done.set()
        return True

    writer = PreferencesWriter(_write, debounce_seconds=0.05, retries=0)
    gui_prefs = {
        "gui_settings": {"theme": "light"},
        "display_columns": ["numero_ssa"],
    }

    try:
        assert writer.persist_async(gui_prefs) is True
        gui_prefs["gui_settings"]["theme"] = "dark"
        gui_prefs["display_columns"].append("situacao")
        assert done.wait(1.0)
    finally:
        writer.shutdown(timeout=1.0)

    assert written == [
        {
            "gui_settings": {"theme": "light"},
            "display_columns": ["numero_ssa"],
        }
    ]


def test_persist_gui_preferences_async_restarts_without_blocking_join(monkeypatch):
    from gui.ssa import gui_preferences_persistence

    captured: list[dict] = []

    class _StoppedWriter:
        @property
        def is_stopped(self):
            return True

        def shutdown(self, *, timeout=None):
            raise AssertionError("restart must not join the stopped writer")

    class _NewWriter:
        @property
        def is_stopped(self):
            return False

        def persist_async(self, gui_prefs):
            captured.append(gui_prefs)
            return True

    monkeypatch.setattr(
        gui_preferences_persistence,
        "_GUI_PREFERENCES_WRITER",
        _StoppedWriter(),
    )
    monkeypatch.setattr(
        gui_preferences_persistence,
        "PreferencesWriter",
        lambda *_args, **_kwargs: _NewWriter(),
    )

    assert gui_preferences_persistence.persist_gui_preferences_async({"theme": "dark"})
    assert captured == [{"theme": "dark"}]


def test_theme_dialog_accepting_current_default_does_not_write(monkeypatch):
    from PyQt6 import QtWidgets

    from gui.ssa import gui_theme_dialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    _ = app

    class _Window(QtWidgets.QWidget):
        _current_theme = "gruvbox"

        def __init__(self) -> None:
            super().__init__()
            self.applied: list[str] = []

        def apply_theme(self, theme: str) -> None:
            self.applied.append(theme)

    captured = {}

    def _accept_dialog(dialog):
        combo = dialog.findChild(QtWidgets.QComboBox)
        assert combo is not None
        screen = QtWidgets.QApplication.primaryScreen()
        assert screen is not None
        available = screen.availableGeometry()
        geometry = dialog.frameGeometry()
        captured["combo_style"] = str(combo.styleSheet() or "")
        captured["combo_view_type"] = type(combo.view()).__name__
        captured["inside_screen"] = (
            geometry.left() >= available.left()
            and geometry.top() >= available.top()
            and geometry.right() <= available.right()
            and geometry.bottom() <= available.bottom()
        )
        return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", _accept_dialog)

    persist_calls = []

    def persist(value):
        persist_calls.append(value)
        return True

    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    window = _Window()

    gui_theme_dialog.show_theme_selection_dialog(
        window,
        gui_prefs=prefs,
        theme_items=[("Gruvbox", "gruvbox"), ("Windows 7", "windows7")],
        persist_preferences_async=persist,
    )

    assert window.applied == ["gruvbox"]
    assert persist_calls == []
    assert "combobox-popup: 0" in captured["combo_style"]
    assert captured["combo_view_type"] == "QListView"
    assert captured["inside_screen"] is True

    temporary_window = _Window()
    temporary_window._current_theme = "windows7"
    temporary_prefs = {
        "gui_settings": {"theme": "windows7", "theme_default": "gruvbox"}
    }

    gui_theme_dialog.show_theme_selection_dialog(
        temporary_window,
        gui_prefs=temporary_prefs,
        theme_items=[("Gruvbox", "gruvbox"), ("Windows 7", "windows7")],
        persist_preferences_async=persist,
    )

    assert temporary_window.applied == ["windows7"]
    assert temporary_prefs["gui_settings"]["theme_default"] == "gruvbox"
    assert persist_calls == []


def test_theme_popup_clamp_moves_geometry_inside_screen(monkeypatch):
    from PyQt6.QtCore import QPoint, QRect
    from PyQt6.QtWidgets import QApplication

    from gui.ssa import gui_theme_dialog

    class _FakeScreen:
        def availableGeometry(self):
            return QRect(100, 50, 900, 600)

    class _FakeHandle:
        def __init__(self, screen):
            self._screen = screen

        def screen(self):
            return self._screen

    class _FakeCombo:
        def __init__(self, screen):
            self._screen = screen

        def windowHandle(self):
            return _FakeHandle(self._screen)

        def mapToGlobal(self, point):
            return point

        class _Rect:
            @staticmethod
            def center():
                return QPoint(0, 0)

        def rect(self):
            return self._Rect()

    class _FakePopup:
        def __init__(self):
            self._geometry = QRect(950, 620, 180, 120)

        def adjustSize(self):
            return None

        def frameGeometry(self):
            return QRect(self._geometry)

        def move(self, x, y):
            self._geometry.moveTo(x, y)

    screen = _FakeScreen()
    combo = _FakeCombo(screen)
    popup = _FakePopup()

    monkeypatch.setattr(
        QApplication,
        "screenAt",
        lambda *_args: screen,
    )
    monkeypatch.setattr(
        QApplication,
        "primaryScreen",
        lambda: screen,
    )

    gui_theme_dialog.clamp_theme_popup_to_screen(combo, popup)

    available = screen.availableGeometry()
    moved = popup.frameGeometry()
    assert available.contains(moved)
