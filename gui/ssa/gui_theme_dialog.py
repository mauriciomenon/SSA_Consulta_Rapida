from __future__ import annotations

from collections.abc import Callable, Sequence

from utils.robust_logging import get_robust_logger
from utils.themes import normalize_theme

logger = get_robust_logger().get_logger(__name__, "gui")


def _resolve_theme_dialog_screen_geometry(target_widget, dialog):
    from PyQt6.QtWidgets import QApplication

    screen = None
    if target_widget is not None:
        try:
            handle = target_widget.windowHandle()
            if handle is not None:
                screen = handle.screen()
        except Exception as exc:
            logger.debug("Falha ao obter screen do dialogo de tema: %s", exc)
        if screen is None:
            try:
                screen = QApplication.screenAt(target_widget.frameGeometry().center())
            except Exception as exc:
                logger.debug("Falha ao obter screenAt do dialogo de tema: %s", exc)
    if screen is None:
        try:
            screen = dialog.screen()
        except Exception as exc:
            logger.debug("Falha ao obter screen atual do dialogo de tema: %s", exc)
    if screen is None:
        try:
            screen = QApplication.primaryScreen()
        except Exception as exc:
            logger.debug("Falha ao obter screen primario do dialogo de tema: %s", exc)
    if screen is None or not hasattr(screen, "availableGeometry"):
        return None
    return screen.availableGeometry()


def _clamp_theme_popup_to_screen(combo_box, popup) -> None:
    from PyQt6.QtWidgets import QApplication

    screen = None
    try:
        handle = combo_box.windowHandle()
        if handle is not None:
            screen = handle.screen()
    except Exception as exc:
        logger.debug("Falha ao obter screen do seletor de tema: %s", exc)
    if screen is None:
        try:
            screen = QApplication.screenAt(combo_box.mapToGlobal(combo_box.rect().center()))
        except Exception as exc:
            logger.debug("Falha ao obter screenAt do seletor de tema: %s", exc)
    if screen is None:
        try:
            screen = QApplication.primaryScreen()
        except Exception as exc:
            logger.debug("Falha ao obter screen primario do seletor de tema: %s", exc)
    if screen is None or not hasattr(screen, "availableGeometry"):
        return
    available = screen.availableGeometry()
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
        QListView,
        QVBoxLayout,
    )

    gui_settings = gui_prefs.get("gui_settings", {})
    theme_default = gui_settings.get("theme_default")
    current_theme = normalize_theme(
        (getattr(window, "_current_theme", "") if window is not None else "")
        or theme_default
        or "gruvbox"
    )
    is_default_theme = normalize_theme(theme_default or "") == current_theme

    class _ScreenBoundComboBox(QComboBox):
        def __init__(self_nonlocal, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self_nonlocal.setView(QListView(self_nonlocal))

        def showPopup(self_nonlocal) -> None:  # noqa: N802
            from PyQt6.QtCore import QTimer

            def _clamp_popup() -> None:
                try:
                    view = self_nonlocal.view()
                    if view is None:
                        return
                    popup = view.window()
                    if popup is None:
                        return
                    _clamp_theme_popup_to_screen(self_nonlocal, popup)
                except Exception as exc:
                    logger.debug("Falha ao limitar popup do seletor de tema: %s", exc)

            super().showPopup()
            _clamp_popup()
            QTimer.singleShot(0, _clamp_popup)

    dialog = QDialog(window)
    dialog.setWindowTitle("Selecionar Tema")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    info_label = QLabel("Escolha um tema para a interface.")
    layout.addWidget(info_label)

    theme_combo = _ScreenBoundComboBox(dialog)
    theme_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
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

    try:
        _position_theme_dialog_within_screen(
            window if window is not None else dialog,
            dialog,
        )
    except Exception as exc:
        logger.debug("Falha ao limitar geometria do dialogo de tema: %s", exc)

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
        default_choice_changed=default_checkbox_changed,
        persist_preferences_async=persist_preferences_async,
    )


def _persist_theme_default_choice(
    *,
    gui_prefs: dict,
    selected_theme_key: str,
    set_as_default: bool,
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
    if (
        default_choice_changed
        and previous_default == selected_theme_key
        and "theme_default" in gui_settings
    ):
        gui_settings.pop("theme_default", None)
        persist_preferences_async(gui_prefs)
        return True
    return False
