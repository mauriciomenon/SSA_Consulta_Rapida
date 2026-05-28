from gui.ssa.gui_theme_dialog import _update_theme_default_choice


def test_theme_default_choice_removes_current_default_when_unchecked():
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    persist_calls = []

    changed = _update_theme_default_choice(
        gui_prefs=prefs,
        selected_theme_key="gruvbox",
        set_as_default=False,
        default_choice_changed=True,
    )

    assert changed is True
    assert "theme_default" not in prefs["gui_settings"]
    assert persist_calls == []


def test_theme_default_choice_keeps_default_when_checkbox_did_not_change():
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    persist_calls = []

    changed = _update_theme_default_choice(
        gui_prefs=prefs,
        selected_theme_key="gruvbox",
        set_as_default=False,
        default_choice_changed=False,
    )

    assert changed is False
    assert prefs["gui_settings"]["theme_default"] == "gruvbox"
    assert persist_calls == []


def test_theme_default_choice_clears_old_default_when_switching_theme():
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    persist_calls = []

    changed = _update_theme_default_choice(
        gui_prefs=prefs,
        selected_theme_key="windows7",
        set_as_default=False,
        default_choice_changed=True,
    )

    assert changed is True
    assert "theme_default" not in prefs["gui_settings"]
    assert persist_calls == []


def test_show_theme_selection_dialog_persists_theme_without_window(monkeypatch):
    from PyQt6 import QtWidgets

    from gui.ssa import gui_theme_dialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    _ = app

    def _accept_dialog(dialog):
        combo = dialog.findChild(QtWidgets.QComboBox)
        assert combo is not None
        combo.setCurrentIndex(1)
        return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", _accept_dialog)

    persist_calls = []
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}

    gui_theme_dialog.show_theme_selection_dialog(
        None,
        gui_prefs=prefs,
        theme_items=[("Gruvbox", "gruvbox"), ("Windows 7", "windows7")],
        persist_preferences_async=lambda value: persist_calls.append(value) or True,
    )

    assert prefs["gui_settings"]["theme"] == "windows7"
    assert prefs["gui_settings"]["theme_default"] == "windows7"
    assert persist_calls == [prefs]
