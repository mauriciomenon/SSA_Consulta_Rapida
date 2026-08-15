from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypedDict

from utils.robust_logging import get_robust_logger
from utils.themes import normalize_theme

logger = get_robust_logger().get_logger(__name__, "gui")


class _ThemeDialogState(TypedDict):
    changed: bool


def _resolve_widget_screen_geometry(target_widget):
    from PyQt6.QtWidgets import QApplication

    screen = None
    if target_widget is not None:
        try:
            handle = target_widget.windowHandle()
            if handle is not None:
                screen = handle.screen()
        except Exception as exc:
            logger.debug("Falha ao obter screen do widget de tema: %s", exc)
        if screen is None:
            try:
                screen = QApplication.screenAt(target_widget.mapToGlobal(target_widget.rect().center()))
            except Exception as exc:
                logger.debug("Falha ao obter screenAt do widget de tema: %s", exc)
    if screen is None:
        try:
            screen = QApplication.primaryScreen()
        except Exception as exc:
            logger.debug("Falha ao obter screen primario do widget de tema: %s", exc)
    if screen is None or not hasattr(screen, "availableGeometry"):
        return None
    return screen.availableGeometry()


def _resolve_theme_dialog_screen_geometry(target_widget, dialog):
    from PyQt6.QtWidgets import QApplication

    available = _resolve_widget_screen_geometry(target_widget)
    if available is not None:
        return available
    try:
        screen = dialog.screen()
    except Exception as exc:
        logger.debug("Falha ao obter screen atual do dialogo de tema: %s", exc)
        screen = None
    if screen is None or not hasattr(screen, "availableGeometry"):
        primary_screen_getter = getattr(QApplication, "primaryScreen", None)
        screen = primary_screen_getter() if callable(primary_screen_getter) else None
    if screen is None or not hasattr(screen, "availableGeometry"):
        return None
    return screen.availableGeometry()


def clamp_theme_popup_to_screen(combo_box, popup) -> None:
    available = _resolve_widget_screen_geometry(combo_box)
    if available is None:
        return
    try:
        popup.setMaximumHeight(max(180, int(available.height()) - 12))
    except Exception as exc:
        logger.debug("Falha ao limitar altura do popup de tema: %s", exc)
    popup.adjustSize()
    geometry = popup.frameGeometry()
    max_x = available.right() - geometry.width() + 1
    max_y = available.bottom() - geometry.height() + 1
    target_x = max(available.left(), min(geometry.x(), max_x))
    target_y = max(available.top(), min(geometry.y(), max_y))
    if target_x != geometry.x() or target_y != geometry.y():
        popup.move(target_x, target_y)


def _position_theme_dialog_within_screen(target_widget, dialog) -> None:
    available = _resolve_theme_dialog_screen_geometry(target_widget, dialog)
    if available is None:
        return
    dialog.adjustSize()
    geometry = dialog.frameGeometry()
    size_hint = dialog.sizeHint()
    max_width = max(1, int(available.width()) - 24)
    max_height = max(1, int(available.height()) - 24)
    target_width = min(
        max(int(geometry.width()), int(size_hint.width())),
        max_width,
    )
    target_height = min(
        max(int(geometry.height()), int(size_hint.height())),
        max_height,
    )
    dialog.resize(
        max(1, target_width),
        max(1, target_height),
    )
    geometry = dialog.frameGeometry()
    center = (
        target_widget.frameGeometry().center()
        if target_widget is not None
        else available.center()
    )
    target_x = center.x() - (geometry.width() // 2)
    target_y = center.y() - (geometry.height() // 2)
    max_x = available.right() - geometry.width() + 1
    max_y = available.bottom() - geometry.height() + 1
    dialog.move(
        max(available.left(), min(target_x, max_x)),
        max(available.top(), min(target_y, max_y)),
    )


def _resolve_theme_selection_state(window, gui_prefs: dict) -> tuple[str, bool]:
    gui_settings = gui_prefs.get("gui_settings", {})
    theme_default = gui_settings.get("theme_default")
    persisted_theme = gui_settings.get("theme")
    current_theme = normalize_theme(
        (getattr(window, "_current_theme", "") if window is not None else "")
        or persisted_theme
        or theme_default
        or "gruvbox"
    )
    return current_theme, normalize_theme(theme_default or "") == current_theme


def _build_screen_bound_theme_combo(dialog, theme_items, current_theme):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QComboBox, QListView

    class _ScreenBoundComboBox(QComboBox):
        def __init__(self_nonlocal, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self_nonlocal.setView(QListView(self_nonlocal))

        def showPopup(self_nonlocal) -> None:  # noqa: N802
            def _clamp_popup() -> None:
                try:
                    view = self_nonlocal.view()
                    if view is None:
                        return
                    popup = view.window()
                    if popup is None:
                        return
                    clamp_theme_popup_to_screen(self_nonlocal, popup)
                except Exception as exc:
                    logger.debug("Falha ao limitar popup do seletor de tema: %s", exc)

            super().showPopup()
            QTimer.singleShot(80, _clamp_popup)

    theme_combo = _ScreenBoundComboBox(dialog)
    theme_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
    selected_index = 0
    for idx, (label, key) in enumerate(theme_items):
        theme_combo.addItem(label, key)
        if normalize_theme(key) == current_theme:
            selected_index = idx
    theme_combo.setCurrentIndex(selected_index)
    return theme_combo


def _build_theme_selection_dialog(window, theme_items, current_theme, is_default_theme):
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QLabel,
        QVBoxLayout,
    )

    dialog = QDialog(window)
    dialog.setWindowTitle("Selecionar Tema")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    info_label = QLabel("Escolha um tema para a interface.")
    layout.addWidget(info_label)

    theme_combo = _build_screen_bound_theme_combo(dialog, theme_items, current_theme)
    layout.addWidget(theme_combo)

    default_checkbox = QCheckBox("Usar tema selecionado como padrao", dialog)
    default_checkbox.setChecked(is_default_theme)
    dialog_state: _ThemeDialogState = {"changed": False}

    def _mark_default_checkbox_changed(*_args) -> None:
        dialog_state["changed"] = True

    default_checkbox.toggled.connect(_mark_default_checkbox_changed)
    layout.addWidget(default_checkbox)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return dialog, theme_combo, default_checkbox, dialog_state


def _apply_theme_selection(
    window,
    *,
    gui_prefs: dict,
    theme_combo,
    default_checkbox,
    default_choice_changed: bool,
    persist_preferences_async: Callable[[dict], object],
) -> None:
    gui_settings = gui_prefs.setdefault("gui_settings", {})
    selected_theme_key = normalize_theme(str(theme_combo.currentData() or "gruvbox"))
    persisted_theme = normalize_theme(str(gui_settings.get("theme") or ""))
    theme_changed = persisted_theme != selected_theme_key
    if window is not None:
        try:
            window.apply_theme(selected_theme_key)
        except Exception as exc:
            logger.warning(
                "Falha ao aplicar tema selecionado '%s': %s", selected_theme_key, exc
            )
            return
    if theme_changed:
        gui_settings["theme"] = selected_theme_key

    default_changed = _update_theme_default_choice(
        gui_prefs=gui_prefs,
        selected_theme_key=selected_theme_key,
        set_as_default=default_checkbox.isChecked(),
        default_choice_changed=default_choice_changed,
    )
    if theme_changed or default_changed:
        persist_preferences_async(gui_prefs)


def show_theme_selection_dialog(
    window,
    *,
    gui_prefs: dict,
    theme_items: Sequence[tuple[str, str]],
    persist_preferences_async: Callable[[dict], object],
) -> None:
    current_theme, is_default_theme = _resolve_theme_selection_state(window, gui_prefs)
    dialog, theme_combo, default_checkbox, dialog_state = _build_theme_selection_dialog(
        window,
        theme_items,
        current_theme,
        is_default_theme,
    )

    try:
        _position_theme_dialog_within_screen(
            window,
            dialog,
        )
    except Exception as exc:
        logger.debug("Falha ao limitar geometria do dialogo de tema: %s", exc)

    if dialog.exec() != dialog.DialogCode.Accepted:
        return

    _apply_theme_selection(
        window,
        gui_prefs=gui_prefs,
        theme_combo=theme_combo,
        default_checkbox=default_checkbox,
        default_choice_changed=bool(dialog_state.get("changed")),
        persist_preferences_async=persist_preferences_async,
    )


def _update_theme_default_choice(
    *,
    gui_prefs: dict,
    selected_theme_key: str,
    set_as_default: bool,
    default_choice_changed: bool,
) -> bool:
    gui_settings = gui_prefs.setdefault("gui_settings", {})
    previous_default = normalize_theme(str(gui_settings.get("theme_default") or ""))
    if set_as_default:
        if previous_default != selected_theme_key:
            gui_settings["theme_default"] = selected_theme_key
            return True
        return False
    if default_choice_changed and "theme_default" in gui_settings:
        gui_settings.pop("theme_default", None)
        return True
    return False
