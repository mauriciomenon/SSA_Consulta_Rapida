from gui.ssa.gui_theme_dialog import _persist_theme_default_choice


def test_theme_default_choice_removes_current_default_when_unchecked():
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    persist_calls = []

    changed = _persist_theme_default_choice(
        gui_prefs=prefs,
        selected_theme_key="gruvbox",
        set_as_default=False,
        was_default_theme=True,
        default_choice_changed=True,
        persist_preferences_async=lambda value: persist_calls.append(value) or True,
    )

    assert changed is True
    assert "theme_default" not in prefs["gui_settings"]
    assert persist_calls == [prefs]


def test_theme_default_choice_keeps_default_when_checkbox_did_not_change():
    prefs = {"gui_settings": {"theme": "gruvbox", "theme_default": "gruvbox"}}
    persist_calls = []

    changed = _persist_theme_default_choice(
        gui_prefs=prefs,
        selected_theme_key="gruvbox",
        set_as_default=False,
        was_default_theme=True,
        default_choice_changed=False,
        persist_preferences_async=lambda value: persist_calls.append(value) or True,
    )

    assert changed is False
    assert prefs["gui_settings"]["theme_default"] == "gruvbox"
    assert persist_calls == []
