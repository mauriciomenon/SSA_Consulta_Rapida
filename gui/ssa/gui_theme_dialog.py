from __future__ import annotations

from collections.abc import Callable, Sequence

from utils.robust_logging import get_robust_logger
from utils.themes import normalize_theme

logger = get_robust_logger().get_logger(__name__, "gui")


def show_theme_selection_dialog(
    window,
    *,
    gui_prefs: dict,
    theme_items: Sequence[tuple[str, str]],
    persist_preferences_async: Callable[[dict], object],
) -> None:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QLabel,
        QVBoxLayout,
    )

    gui_settings = gui_prefs.get("gui_settings", {})
    theme_default = gui_settings.get("theme_default")
    current_theme = normalize_theme(
        getattr(window, "_current_theme", "") or theme_default or "gruvbox"
    )
    is_default_theme = normalize_theme(theme_default or "") == current_theme

    dialog = QDialog(window)
    dialog.setWindowTitle("Selecionar Tema")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    info_label = QLabel("Escolha um tema para a interface.")
    layout.addWidget(info_label)

    theme_combo = QComboBox(dialog)
    selected_index = 0
    for idx, (label, key) in enumerate(theme_items):
        theme_combo.addItem(label, key)
        if normalize_theme(key) == current_theme:
            selected_index = idx
    theme_combo.setCurrentIndex(selected_index)
    layout.addWidget(theme_combo)

    default_checkbox = QCheckBox("Usar tema selecionado como padrao", dialog)
    default_checkbox.setChecked(is_default_theme)
    default_checkbox_changed = False

    def _mark_default_checkbox_changed(*_args) -> None:
        nonlocal default_checkbox_changed
        default_checkbox_changed = True

    default_checkbox.toggled.connect(_mark_default_checkbox_changed)
    layout.addWidget(default_checkbox)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    selected_theme_key = normalize_theme(str(theme_combo.currentData() or "gruvbox"))
    try:
        window.apply_theme(selected_theme_key)
    except Exception as exc:
        logger.warning(
            "Falha ao aplicar tema selecionado '%s': %s", selected_theme_key, exc
        )
        return

    gui_settings = gui_prefs.setdefault("gui_settings", {})
    _persist_theme_default_choice(
        gui_prefs=gui_prefs,
        selected_theme_key=selected_theme_key,
        set_as_default=default_checkbox.isChecked(),
        was_default_theme=is_default_theme,
        default_choice_changed=default_checkbox_changed,
        persist_preferences_async=persist_preferences_async,
    )


def _persist_theme_default_choice(
    *,
    gui_prefs: dict,
    selected_theme_key: str,
    set_as_default: bool,
    was_default_theme: bool,
    default_choice_changed: bool,
    persist_preferences_async: Callable[[dict], object],
) -> bool:
    gui_settings = gui_prefs.setdefault("gui_settings", {})
    previous_default = normalize_theme(str(gui_settings.get("theme_default") or ""))
    if set_as_default:
        if previous_default != selected_theme_key:
            gui_settings["theme_default"] = selected_theme_key
            persist_preferences_async(gui_prefs)
            return True
        return False
    if default_choice_changed and was_default_theme and "theme_default" in gui_settings:
        gui_settings.pop("theme_default", None)
        persist_preferences_async(gui_prefs)
        return True
    return False
