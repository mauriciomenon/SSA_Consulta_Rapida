# gui/ssa/gui_filters_advanced_ui.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: builds advanced filters UI and menu wiring.
# Relation: does not apply DataFrame filters directly.

from __future__ import annotations

from time import perf_counter
from typing import Any

import pandas as pd

from gui.qt_stubs import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSignalBlocker,
    QSizePolicy,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
    sip,
)
from utils.robust_logging import get_robust_logger

from .gui_filters_advanced_logic import RESPONSAVEL_FILTER_COLUMN_CANDIDATES
from .gui_filters_advanced_state import DIVISAO_SETORES, SECTOR_TO_DIV

logger = get_robust_logger().get_logger(__name__, "gui")
_DERIVADA_ALL_STE_LABEL = "Derivadas em STE/SES"
_MACRO_BAIXAR_EXCLUDED_STATUSES = ["SAD", "SCA", "SES", "STE"]

# Layout constants
LAYOUT_MIN_VALID_WIDTH = 1
LAYOUT_GRID_MIN_COLS = 1
LAYOUT_GRID_MAX_COLS = 4
LAYOUT_GRID_PREF_COLS = 4
LAYOUT_ADV_PANEL_MIN_HEIGHT = 82
LAYOUT_ADV_PANEL_MAX_HEIGHT = 230
LAYOUT_ADV_CONTROL_HEIGHT = 24
LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT = 40
LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT = 50

# Simple popup guard (golden baseline).
# Keep this switch easy to revert if we want full dynamic width again.
SIMPLE_POPUP_TEXT_CLAMP = True
SIMPLE_POPUP_LABEL_MAX_PX = 300
SIMPLE_POPUP_RIGHT_GUTTER_PX = 10
SIMPLE_POPUP_SCROLLBAR_GUARD_PX = 18


def _get_widget_screen_geometry(widget):
    candidate_widgets = []
    if widget is not None:
        candidate_widgets.append(widget)
        try:
            window = widget.window()
        except Exception:
            window = None
        if window is not None and window is not widget:
            candidate_widgets.append(window)
    for candidate in candidate_widgets:
        try:
            handle = candidate.windowHandle()
            if handle is not None:
                screen = handle.screen()
                if screen is not None:
                    return screen.availableGeometry()
        except Exception as exc:
            logger.debug("Failed to get screen geometry from window handle: %s", exc)
        try:
            screen = QApplication.screenAt(
                candidate.mapToGlobal(candidate.rect().center())
            )
            if screen is not None:
                return screen.availableGeometry()
        except Exception as exc:
            logger.debug("Failed to get screen geometry from widget center: %s", exc)
    try:
        screen = QApplication.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
    except Exception as exc:
        logger.debug("Failed to get primary screen geometry: %s", exc)
    return None


def _flatten_field_box(box: QGroupBox) -> None:
    if box is None:
        return
    try:
        box.setFlat(True)
    except Exception as exc:
        logger.debug("Falha ao achatar box de filtro avancado: %s", exc)


def _apply_advanced_filters_font_policy(self, width: int) -> None:
    group = getattr(self, "adv_filters_group", None) or getattr(
        self, "_adv_filters_group_obj", None
    )
    if group is None:
        return
    base_pt = 10
    try:
        ref_button = getattr(self, "search_button", None)
        ref_font = ref_button.font() if ref_button is not None else group.font()
        current = int(ref_font.pointSize())
        if current > 0:
            base_pt = current
    except Exception as exc:
        logger.debug("Falha ao ler fonte base do grupo de filtros avancados: %s", exc)
    _ = width
    control_pt = max(9, min(12, base_pt))
    title_pt = max(control_pt, min(12, control_pt + 1))
    try:
        boxes = (getattr(self, "_adv_filters_grid_widgets", {}) or {}).values()
    except Exception:
        boxes = []
    for box in boxes:
        if box is None:
            continue
        try:
            bf = box.font()
            bf.setPointSize(title_pt)
            box.setFont(bf)
        except Exception as exc:
            logger.debug("Falha ao ajustar fonte do box de filtro avancado: %s", exc)
    control_types = (QToolButton, QComboBox, QLineEdit)
    try:
        controls = group.findChildren(control_types)
    except Exception:
        controls = []
    for control in controls:
        if control is None:
            continue
        try:
            cf = control.font()
            cf.setPointSize(control_pt)
            control.setFont(cf)
        except Exception as exc:
            logger.debug(
                "Falha ao ajustar fonte de controle no painel avancado: %s", exc
            )


def _is_widget_valid(widget) -> bool:
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except Exception:
        return False


def _safe_combo_item_data(combo: Any):
    try:
        if combo is None:
            return None
        mode_idx = combo.currentIndex()
        return combo.itemData(mode_idx)
    except Exception:
        return None


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except Exception:
        return 0


def _resolve_adv_layout_baseline(self) -> tuple[int, int, int]:
    cell_min = 212
    action_min = 88
    action_max = 134
    width_manager = getattr(self, "width_manager", None)
    if width_manager is None or not hasattr(width_manager, "compute_optimal_widths"):
        return cell_min, action_min, action_max
    try:
        sample_df = pd.DataFrame(
            [
                {
                    "numero_ssa": "",
                    "situacao": "",
                    "setor_executor": "",
                    "setor_emissor": "",
                    "localizacao_codigo": "",
                }
            ]
        )
        width_map = width_manager.compute_optimal_widths(
            sample_df,
            available_width=1200,
            column_order=[
                "#",
                "numero_ssa",
                "situacao",
                "setor_executor",
                "setor_emissor",
                "localizacao_codigo",
            ],
        )
        numero_w = int(width_map.get("numero_ssa", 85))
        situacao_w = int(width_map.get("situacao", 40))
        local_w = int(width_map.get("localizacao_codigo", 65))
        setor_exec_w = int(width_map.get("setor_executor", 45))
        setor_emis_w = int(width_map.get("setor_emissor", 45))

        cell_candidate = (
            numero_w
            + local_w
            + (situacao_w // 2)
            + (setor_exec_w // 2)
            + (setor_emis_w // 2)
        )
        cell_min = max(174, min(284, cell_candidate))

        action_candidate = numero_w + situacao_w
        action_min = max(84, min(118, action_candidate))
        action_max = max(action_min + 28, min(148, action_min + 40))
    except Exception as exc:
        logger.debug(
            "Falha ao calcular baseline de layout avancado via width_manager: %s", exc
        )
    return cell_min, action_min, action_max


def _update_advanced_filters_action_buttons(self, width: int) -> None:
    """Aplica dimensao estavel para botoes de acao do painel avancado."""
    apply_btn = getattr(self, "_adv_filters_apply_btn", None)
    clear_btn = getattr(self, "_adv_filters_clear_btn", None)
    if apply_btn is None or clear_btn is None:
        return
    if not _is_widget_valid(apply_btn) or not _is_widget_valid(clear_btn):
        return
    _ = width
    _, min_width, max_width = _resolve_adv_layout_baseline(self)
    min_width = max(56, min(72, min_width))
    max_width = max(min_width + 6, min(84, max_width))
    try:
        grid_cols = int(
            getattr(self, "_adv_filters_grid_cols", LAYOUT_GRID_PREF_COLS)
            or LAYOUT_GRID_PREF_COLS
        )
    except Exception:
        grid_cols = LAYOUT_GRID_PREF_COLS
    grid_cols = max(1, min(LAYOUT_GRID_MAX_COLS, grid_cols))
    if width > 0:
        cell_width = max(112, int(width // grid_cols))
        pair_budget = max(116, cell_width - 10)
        per_button_budget = max(56, int((pair_budget - 6) // 2))
        max_width = min(max_width, per_button_budget)
        min_width = min(min_width, max_width)
    new_dims = (min_width, max_width)
    if getattr(self, "_adv_filters_action_btn_dims", None) == new_dims:
        return
    self._adv_filters_action_btn_dims = new_dims
    for btn in (apply_btn, clear_btn):
        if not _is_widget_valid(btn):
            continue
        try:
            ref_btn = getattr(self, "search_button", None)
            if ref_btn is not None and _is_widget_valid(ref_btn):
                ref_font = ref_btn.font()
                ref_font.setBold(False)
                btn.setFont(ref_font)
                ref_h = int(
                    ref_btn.height()
                    or ref_btn.sizeHint().height()
                    or LAYOUT_ADV_CONTROL_HEIGHT
                )
                ref_h = max(20, min(24, ref_h))
                btn.setMinimumHeight(ref_h)
                btn.setMaximumHeight(ref_h)
            btn.setMinimumWidth(min_width)
            btn.setMaximumWidth(max_width)
        except Exception as exc:
            logger.debug("Falha ao ajustar largura minima de botao de acao: %s", exc)


def _enforce_advanced_filters_compact_metrics(self) -> None:
    group = getattr(self, "adv_filters_group", None)
    if group is None:
        group = getattr(self, "_adv_filters_group_obj", None)
    if group is None:
        return
    for field_box in (getattr(self, "_adv_filters_grid_widgets", {}) or {}).values():
        if field_box is None:
            continue
        try:
            field_box.setMinimumHeight(LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT)
            field_box.setMaximumHeight(LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT)
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar metrica compacta em box de filtro avancado: %s", exc
            )
        control_types = (QToolButton, QComboBox, QLineEdit, QPushButton)
        try:
            controls = field_box.findChildren(control_types)
        except Exception as exc:
            logger.debug(
                "Falha ao listar controles compactos do filtro avancado: %s", exc
            )
            controls = []
        for control in controls:
            if control is None:
                continue
            try:
                control.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
                control.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar metrica compacta em controle de filtro avancado: %s",
                    exc,
                )


def _compute_adv_grid_cell_min_width(self, visible_widgets) -> int:
    base_cell_min, _, _ = _resolve_adv_layout_baseline(self)
    widths = []
    for _, widget in visible_widgets:
        if widget is None:
            continue
        try:
            widths.append(int(widget.minimumSizeHint().width()))
        except Exception as exc:
            logger.debug("Falha ao medir largura minima de filtro avancado: %s", exc)
            continue
    if not widths:
        return base_cell_min
    widths.sort()
    p75_idx = max(0, min(len(widths) - 1, int((len(widths) - 1) * 0.75)))
    p75 = widths[p75_idx]
    avg = sum(widths) // len(widths)
    dynamic_baseline = max(p75, avg) + 22
    return max(174, min(300, max(base_cell_min, dynamic_baseline)))


def _make_multiselect_box(
    self,
    title: str,
    placeholder: str = "Selecionar",
    with_exclude: bool = True,
    layout_baseline: tuple[int, int, int] | None = None,
):
    box = QGroupBox(title)
    _flatten_field_box(box)
    layout = QHBoxLayout(box)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(2)
    button = QToolButton()
    button.setText(placeholder)
    try:
        button.setProperty("filter_name", title)
    except Exception as exc:
        logger.debug(
            "Falha ao associar nome de filtro no botao multiselect '%s': %s", title, exc
        )
    _, action_min, action_max = layout_baseline or _resolve_adv_layout_baseline(self)
    _ = action_max
    btn_min = max(74, min(96, action_min - 4))
    try:
        button.setMinimumWidth(btn_min)
        button.setMaximumWidth(16777215)
        button.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        button.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug(
            "Falha ao definir size policy do botao multiselect '%s': %s", title, exc
        )
    menu = QMenu(button)
    try:
        menu.setMaximumHeight(320)
    except Exception as exc:
        logger.debug(
            "Falha ao definir altura maxima do menu multiselect '%s': %s", title, exc
        )
    self._attach_multiselect_menu(button, menu)
    button.setToolTip(placeholder)
    try:
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    except Exception as exc:
        logger.debug(
            "Falha ao definir size policy do groupbox multiselect '%s': %s", title, exc
        )
    exclude = None
    if with_exclude:
        exclude = QCheckBox("Diferente")
        try:
            exclude.setVisible(False)
        except Exception as exc:
            logger.debug(
                "Falha ao ocultar checkbox de exclusao no multiselect '%s': %s",
                title,
                exc,
            )
    layout.addWidget(button, 1)
    return box, button, menu, exclude


def _set_menu_pre_show_hook(self, button, callback) -> None:
    if button is None:
        return
    hooks = getattr(self, "_menu_pre_show_hooks", None)
    if not isinstance(hooks, dict):
        hooks = {}
        self._menu_pre_show_hooks = hooks
    hooks[id(button)] = callback


def _run_menu_pre_show_hook(self, button) -> None:
    hooks = getattr(self, "_menu_pre_show_hooks", None)
    if not isinstance(hooks, dict) or button is None:
        return
    callback = hooks.get(id(button))
    if not callable(callback):
        return
    try:
        callback()
    except Exception as exc:
        logger.debug("Falha ao preparar menu antes de abrir: %s", exc)


def _set_checkbox_checked_quietly(self, checkbox, checked: bool) -> bool:
    """Atualiza estado de checkbox sem propagar sinais e sem deixar bloqueio preso."""
    if not _is_widget_valid(checkbox):
        return False
    try:
        desired = bool(checked)
        if bool(checkbox.isChecked()) == desired:
            return False
    except Exception as exc:
        logger.debug(
            "Falha ao ler estado atual de checkbox em _set_checkbox_checked_quietly: %s",
            exc,
        )
        desired = bool(checked)
    manual_blocked = False
    try:
        with QSignalBlocker(checkbox):
            checkbox.setChecked(desired)
            return True
    except Exception:
        try:
            checkbox.blockSignals(True)
            manual_blocked = True
        except Exception as exc:
            logger.debug(
                "Falha ao bloquear sinais de checkbox sem QSignalBlocker: %s", exc
            )
        changed = False
        try:
            checkbox.setChecked(desired)
            changed = True
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar checkbox em _set_checkbox_checked_quietly: %s", exc
            )
            changed = False
        finally:
            if manual_blocked and _is_widget_valid(checkbox):
                try:
                    checkbox.blockSignals(False)
                except Exception as exc:
                    logger.debug(
                        "Falha ao restaurar sinais de checkbox sem QSignalBlocker: %s",
                        exc,
                    )
        return changed


def _sync_responsavel_flags(self) -> None:
    all_prefixes = set(getattr(self, "_responsavel_all_prefixes", ()))
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    built = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    self._responsavel_filters_materialized = bool(
        all_prefixes
    ) and all_prefixes.issubset(built)
    self._responsavel_options_dirty = bool(dirty)


def _mark_responsavel_dirty(self, prefixes=None) -> None:
    all_prefixes = set(getattr(self, "_responsavel_all_prefixes", ()))
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    if prefixes is None:
        dirty |= all_prefixes
    else:
        dirty |= {p for p in prefixes if p in all_prefixes}
    self._responsavel_dirty_prefixes = dirty
    self._sync_responsavel_flags()


def _on_sector_debounce_timeout(self) -> None:
    built = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    target = built & dirty
    if not target:
        return
    try:
        self._refresh_responsavel_options(target_prefixes=target)
    except Exception as exc:
        logger.warning(
            "Falha no refresh de responsaveis apos debounce de setor: %s", exc
        )


def _ensure_responsavel_options_materialized(
    self, target_prefix: str | None = None, force: bool = False
) -> None:
    """Materializa menus de responsaveis sob demanda para reduzir freeze da aba."""
    all_prefixes = set(getattr(self, "_responsavel_all_prefixes", ()))
    if target_prefix:
        if target_prefix not in all_prefixes:
            return
        target_prefixes = {target_prefix}
    else:
        target_prefixes = set(all_prefixes)
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    built = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    if not force and target_prefixes.issubset(built) and not (target_prefixes & dirty):
        return
    if getattr(self, "_responsavel_refreshing", False):
        return
    self._responsavel_refreshing = True
    try:
        self._refresh_responsavel_options(target_prefixes=target_prefixes)
    finally:
        self._responsavel_refreshing = False


def _sync_responsavel_button_summaries(self, only_prefixes=None) -> None:
    """Atualiza resumo dos botões de responsavel sem materializar menus completos."""
    selected_prefixes = None
    if only_prefixes is not None:
        selected_prefixes = {p for p in only_prefixes}
    filters = self._advanced_filters or {}
    pairs = (
        (
            "adv_responsavel_solicitante",
            "adv_responsavel_solicitante_button",
            "solicitante",
            "solicitante_exclude_values",
        ),
        (
            "adv_responsavel_programacao",
            "adv_responsavel_programacao_button",
            "responsavel_programacao",
            "responsavel_programacao_exclude_values",
        ),
        (
            "adv_responsavel_execucao",
            "adv_responsavel_execucao_button",
            "responsavel_execucao",
            "responsavel_execucao_exclude_values",
        ),
    )
    for prefix, button_attr, include_key, exclude_key in pairs:
        if selected_prefixes is not None and prefix not in selected_prefixes:
            continue
        button = getattr(self, button_attr, None)
        if button is None or not _is_widget_valid(button):
            continue
        include_values = [
            str(v) for v in (filters.get(include_key) or []) if str(v).strip()
        ]
        exclude_values = [
            str(v) for v in (filters.get(exclude_key) or []) if str(v).strip()
        ]
        include_text = ", ".join(include_values) if include_values else ""
        exclude_text = ", ".join(exclude_values) if exclude_values else ""
        if include_values and exclude_values:
            candidates = [
                f"Incluir: {include_text} | Diferente: {exclude_text}",
                f"{len(include_values)} incluir, {len(exclude_values)} diferente",
                f"Incluir: {include_text}",
                f"Diferente: {exclude_text}",
            ]
        elif include_values:
            candidates = [
                f"Incluir: {include_text}",
                "1 incluir"
                if len(include_values) == 1
                else f"{len(include_values)} incluir",
            ]
        elif exclude_values:
            candidates = [
                f"Diferente: {exclude_text}",
                "1 diferente"
                if len(exclude_values) == 1
                else f"{len(exclude_values)} diferente",
            ]
        else:
            candidates = ["Selecionar"]
        text = _fit_button_text(button, candidates, candidates[-1])
        try:
            button.setText(text)
            button.setEnabled(True)
            if include_values or exclude_values:
                tooltip = "Incluir: " + ", ".join(include_values)
                if exclude_values:
                    tooltip += "\nDiferente: " + ", ".join(exclude_values)
                button.setToolTip(tooltip)
            else:
                button.setToolTip("Selecionar")
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar resumo de botao de responsavel (%s): %s",
                button_attr,
                exc,
            )


def _attach_multiselect_menu(self, button, menu):
    if button is None or menu is None:
        return

    def _show_menu():
        if not _is_widget_valid(button) or not _is_widget_valid(menu):
            return
        try:
            self._run_menu_pre_show_hook(button)
        except Exception as exc:
            logger.debug("Falha no pre-show do menu multiselect: %s", exc)
        try:
            rect = button.rect()
            pos = button.mapToGlobal(rect.bottomLeft())
            try:
                menu_size = menu.sizeHint()
                screen = _get_widget_screen_geometry(button)
                if (
                    menu_size
                    and screen
                    and pos.y() + menu_size.height() > screen.bottom()
                ):
                    pos = button.mapToGlobal(rect.topLeft())
                    pos.setY(pos.y() - menu_size.height())
                if (
                    menu_size
                    and screen
                    and pos.x() + menu_size.width() > screen.right()
                ):
                    pos.setX(max(screen.left(), screen.right() - menu_size.width() - 4))
                if screen and pos.x() < screen.left():
                    pos.setX(screen.left() + 2)
                if screen and pos.y() < screen.top():
                    pos.setY(screen.top() + 2)
            except Exception as exc:
                logger.debug(
                    "Falha ao ajustar posicao do menu multiselect na tela: %s", exc
                )
            menu.exec(pos)
            return
        except Exception as exc:
            logger.warning("Falha ao abrir menu multiselect: %s", exc)

    try:
        button.clicked.connect(_show_menu)
    except Exception as exc:
        logger.warning("Falha ao conectar abertura de menu multiselect: %s", exc)


def _update_multiselect_button(
    self, button, checks, placeholder: str = "Selecionar", exclude_checks=None
):
    if not _is_widget_valid(button):
        return
    selected = []
    for cb in checks or []:
        try:
            if not _is_widget_valid(cb):
                continue
            if cb.isChecked():
                value = self._checkbox_value(cb)
                if value:
                    selected.append(value)
        except Exception as exc:
            logger.debug(
                "Failed to read include checkbox state in multiselect summary: %s", exc
            )
    excluded = []
    for cb in exclude_checks or []:
        try:
            if not _is_widget_valid(cb):
                continue
            if cb.isChecked():
                value = self._checkbox_value(cb)
                if value:
                    excluded.append(value)
        except Exception as exc:
            logger.debug(
                "Failed to read exclude checkbox state in multiselect summary: %s", exc
            )
    total = len(checks or [])
    include_text = ", ".join(selected) if selected else ""
    exclude_text = ", ".join(excluded) if excluded else ""
    if total == 0:
        candidates = ["Sem dados"]
    elif not selected and not excluded:
        candidates = [placeholder]
    elif len(selected) == total and not excluded:
        candidates = ["Todos", f"Incluir: {include_text}"]
    elif selected and excluded:
        candidates = [
            f"Incluir: {include_text} | Diferente: {exclude_text}",
            f"{len(selected)} incluir, {len(excluded)} diferente",
            f"Incluir: {include_text}",
            f"Diferente: {exclude_text}",
        ]
    elif selected:
        candidates = [
            f"Incluir: {include_text}",
            "1 incluir" if len(selected) == 1 else f"{len(selected)} incluir",
        ]
    elif excluded:
        candidates = [
            f"Diferente: {exclude_text}",
            "1 diferente" if len(excluded) == 1 else f"{len(excluded)} diferente",
        ]
    else:
        candidates = [f"{len(selected)} selecionados"]
    text = _fit_button_text(button, candidates, candidates[-1])
    try:
        button.setText(text)
        # Esmaecimento visual para botoes sem dados
        if total == 0:
            button.setEnabled(False)
        else:
            button.setEnabled(True)
        if selected or excluded:
            button.setToolTip(
                "Incluir: "
                + ", ".join(selected)
                + ("\nDiferente: " + ", ".join(excluded) if excluded else "")
            )
        else:
            button.setToolTip(placeholder if total > 0 else "Nenhum dado disponivel")
    except Exception as exc:
        logger.debug("Falha ao atualizar resumo/tooltip do botao multiselect: %s", exc)


def _fit_button_text(button, candidates, fallback: str) -> str:
    try:
        if not _is_widget_valid(button):
            return str(fallback)
        fm = button.fontMetrics()
        width = _safe_widget_width(button)
        available = max(24, width - 10)
        for text in candidates:
            if text and fm.horizontalAdvance(text) <= available:
                return text
        primary = next((str(item) for item in candidates if item), str(fallback))
        if fm.horizontalAdvance(primary) <= available:
            return primary
        ellipsis = "..."
        if fm.horizontalAdvance(ellipsis) >= available:
            return ellipsis
        trimmed = primary
        while trimmed and fm.horizontalAdvance(trimmed + ellipsis) > available:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis
    except Exception as exc:
        logger.debug("Falha ao ajustar texto de botao ao espaco disponivel: %s", exc)
        return str(fallback)


def _safe_widget_width(widget) -> int:
    if widget is None or not _is_widget_valid(widget):
        return 0
    try:
        width_fn = getattr(widget, "width", None)
        if callable(width_fn):
            value = int(width_fn() or 0)
            if value > 0:
                return value
    except Exception as exc:
        logger.debug("Falha ao medir largura atual de widget: %s", exc)
    try:
        size_hint_fn = getattr(widget, "sizeHint", None)
        if callable(size_hint_fn):
            hint = size_hint_fn()
            if hint is not None:
                value = int(hint.width() or 0)
                if value > 0:
                    return value
    except Exception as exc:
        logger.debug("Falha ao medir sizeHint de widget: %s", exc)
    try:
        minimum_width_fn = getattr(widget, "minimumWidth", None)
        if callable(minimum_width_fn):
            return max(0, int(minimum_width_fn() or 0))
    except Exception as exc:
        logger.debug("Falha ao medir largura minima de widget: %s", exc)
    return 0


def _palette_color_name(widget, palette_attr: str) -> str:
    if widget is None or not _is_widget_valid(widget):
        return ""
    try:
        palette = widget.palette()
        color_group = getattr(palette, palette_attr, None)
        if callable(color_group):
            color = color_group().color()
            name = color.name()
            if isinstance(name, str):
                value = name.strip()
                if value:
                    return value
    except Exception:
        return ""
    return ""


def _resolve_popup_theme_tokens(
    self, button, menu
) -> tuple[str, str, str, str, str, str]:
    roles = getattr(self, "_current_theme_roles", None)
    if not isinstance(roles, dict):
        roles = {}
    popup_bg = (
        roles.get("popup_bg")
        or roles.get("panel_bg")
        or _palette_color_name(menu, "window")
        or _palette_color_name(button, "window")
    )
    popup_text = (
        roles.get("popup_text")
        or roles.get("panel_text")
        or roles.get("label_color")
        or _palette_color_name(menu, "windowText")
        or _palette_color_name(button, "windowText")
    )
    popup_border = (
        roles.get("popup_border")
        or roles.get("panel_border")
        or _palette_color_name(menu, "mid")
        or _palette_color_name(button, "mid")
    )
    checked_bg = (
        roles.get("checkbox_checked_bg")
        or roles.get("accent")
        or _palette_color_name(menu, "highlight")
    )
    checkbox_bg = roles.get("checkbox_bg") or popup_bg
    checkbox_border = roles.get("checkbox_border") or popup_border

    if not popup_bg:
        popup_bg = "palette(window)"
    if not popup_text:
        popup_text = "palette(window-text)"
    if not popup_border:
        popup_border = "palette(mid)"
    if not checked_bg:
        checked_bg = popup_border
    if not checkbox_bg:
        checkbox_bg = popup_bg
    if not checkbox_border:
        checkbox_border = popup_border
    return popup_bg, popup_text, popup_border, checked_bg, checkbox_bg, checkbox_border


def _detect_filter_name_from_button(button) -> str:
    try:
        prop_value = button.property("filter_name") if button is not None else None
        if isinstance(prop_value, str):
            filter_name = prop_value.strip()
            if filter_name:
                return filter_name
    except Exception as exc:
        logger.debug("Falha ao ler propriedade filter_name do botao: %s", exc)
    filter_name = ""
    try:
        parent = button.parent() if button is not None else None
        seen = set()
        for _ in range(50):
            if parent is None:
                break
            pid = id(parent)
            if pid in seen:
                logger.debug(
                    "Ciclo detectado ao subir parent() no menu multiselect; abortando."
                )
                break
            seen.add(pid)
            if isinstance(parent, QGroupBox):
                candidate = parent.title()
                if candidate and candidate not in ("Valores", ""):
                    filter_name = candidate
                    break
            next_parent = getattr(parent, "parent", None)
            parent = next_parent() if callable(next_parent) else None
    except Exception as exc:
        logger.debug("Falha ao detectar nome do filtro para menu multiselect: %s", exc)
    return filter_name


def _compute_multiselect_popup_metrics(
    button, values, filter_name: str, has_exclude_column: bool
):
    valid_values = []
    for raw_val in values or []:
        label_text = (
            str(raw_val[1])
            if isinstance(raw_val, (list, tuple)) and len(raw_val) > 1
            else str(raw_val)
        )
        if label_text and label_text.strip():
            valid_values.append(raw_val)
    try:
        fm = button.fontMetrics() if button is not None else None
    except Exception:
        fm = None
    try:
        if fm is not None:
            max_label_px = max(
                (
                    fm.horizontalAdvance(str(v[1]))
                    if isinstance(v, (list, tuple)) and len(v) > 1
                    else fm.horizontalAdvance(str(v))
                )
                for v in valid_values
            )
        else:
            max_label_px = (
                max(
                    len(str(v[1]))
                    if isinstance(v, (list, tuple)) and len(v) > 1
                    else len(str(v))
                    for v in valid_values
                )
                * 8
            )
    except Exception:
        max_label_px = 64
    # Simple clamp for very long names in responsavel menus.
    # Easy rollback: set SIMPLE_POPUP_TEXT_CLAMP = False.
    if SIMPLE_POPUP_TEXT_CLAMP:
        max_label_px = min(max_label_px, SIMPLE_POPUP_LABEL_MAX_PX)
    content_width = max_label_px + (136 if has_exclude_column else 80)
    if filter_name:
        try:
            header_width = (
                fm.horizontalAdvance(filter_name)
                if fm is not None
                else (len(filter_name) * 8)
            )
        except Exception:
            header_width = len(filter_name) * 8
        header_extra = 170 if has_exclude_column else 34
        content_width = max(content_width, header_width + header_extra)
    include_col_min = 64
    exclude_col_min = 92
    if has_exclude_column and fm is not None:
        include_col_min = max(include_col_min, fm.horizontalAdvance("Conter") + 14)
        exclude_col_min = max(exclude_col_min, fm.horizontalAdvance("Nao conter") + 14)
        exclude_col_min += SIMPLE_POPUP_RIGHT_GUTTER_PX
        content_width = max(content_width, include_col_min + exclude_col_min + 140)
        # Keep a small guard for vertical scrollbar in large lists.
        # Easy rollback: set SIMPLE_POPUP_SCROLLBAR_GUARD_PX = 0.
        if len(valid_values) > 9:
            content_width += SIMPLE_POPUP_SCROLLBAR_GUARD_PX
    popup_max_width = 680
    try:
        screen_geometry = _get_widget_screen_geometry(button)
        if screen_geometry is not None:
            screen_w = int(screen_geometry.width())
            if screen_w > 0:
                popup_max_width = max(420, min(960, int(screen_w * 0.72)))
    except Exception:
        popup_max_width = 680
    popup_width = max(220, min(popup_max_width, content_width))
    return popup_width, include_col_min, exclude_col_min, valid_values


def _notify_multiselect_batch_change(
    self,
    button,
    checks,
    exclude_checks,
    on_toggle,
    on_exclude_toggle,
    *,
    include_changed: bool,
    exclude_changed: bool,
) -> None:
    try:
        self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar resumo de botao apos lote no menu multiselect: %s", exc
        )
    if include_changed and callable(on_toggle):
        on_toggle()
    if exclude_changed and callable(on_exclude_toggle):
        on_exclude_toggle()


def _append_multiselect_batch_controls(
    self,
    *,
    grid,
    row_idx,
    checks,
    exclude_checks,
    cb_style_include: str,
    cb_style_exclude: str,
    apply_checkbox_styles: bool,
    popup_text: str,
    on_toggle,
    on_exclude_toggle,
    button,
):
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    grid.addWidget(separator, row_idx, 0, 1, 3)
    row_idx += 1

    batch_mark_include = QCheckBox()
    batch_clear_include = QCheckBox()
    batch_mark_exclude = QCheckBox()
    batch_clear_exclude = QCheckBox()

    if apply_checkbox_styles:
        for cb in [batch_mark_include, batch_clear_include]:
            cb.setStyleSheet(cb_style_include)
        for cb in [batch_mark_exclude, batch_clear_exclude]:
            cb.setStyleSheet(cb_style_exclude)

    label_mark = QLabel("Selecionar em lote")
    label_clear = QLabel("Limpar selecao em lote")
    try:
        label_mark.setStyleSheet(f"font-size: 11px; color: {popup_text};")
        label_clear.setStyleSheet(f"font-size: 11px; color: {popup_text};")
    except Exception as exc:
        logger.debug(
            "Falha ao estilizar labels de marcacao em lote no menu multiselect: %s", exc
        )

    grid.addWidget(label_mark, row_idx, 0)
    grid.addWidget(
        batch_mark_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    grid.addWidget(
        batch_mark_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    row_idx += 1

    grid.addWidget(label_clear, row_idx, 0)
    grid.addWidget(
        batch_clear_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    grid.addWidget(
        batch_clear_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
    )
    row_idx += 1

    def _batch_set_include(target_state: bool):
        for cb in checks:
            if not _is_widget_valid(cb):
                continue
            cb.blockSignals(True)
            cb.setChecked(target_state)
            cb.blockSignals(False)
        _notify_multiselect_batch_change(
            self,
            button,
            checks,
            exclude_checks,
            on_toggle,
            on_exclude_toggle,
            include_changed=True,
            exclude_changed=False,
        )

    def _batch_set_exclude(target_state: bool):
        for cb in exclude_checks:
            if not _is_widget_valid(cb):
                continue
            cb.blockSignals(True)
            cb.setChecked(target_state)
            cb.blockSignals(False)
        _notify_multiselect_batch_change(
            self,
            button,
            checks,
            exclude_checks,
            on_toggle,
            on_exclude_toggle,
            include_changed=False,
            exclude_changed=True,
        )

    def _reset_batch_toggle(toggle_cb):
        try:
            toggle_cb.blockSignals(True)
            toggle_cb.setChecked(False)
            toggle_cb.blockSignals(False)
        except Exception as exc:
            logger.debug("Falha ao resetar toggle de marcacao em lote: %s", exc)

    try:
        batch_mark_include.toggled.connect(
            lambda checked: (
                _batch_set_include(True),
                _reset_batch_toggle(batch_mark_include),
            )
            if checked
            else None
        )
        batch_clear_include.toggled.connect(
            lambda checked: (
                _batch_set_include(False),
                _reset_batch_toggle(batch_clear_include),
            )
            if checked
            else None
        )
        batch_mark_exclude.toggled.connect(
            lambda checked: (
                _batch_set_exclude(True),
                _reset_batch_toggle(batch_mark_exclude),
            )
            if checked
            else None
        )
        batch_clear_exclude.toggled.connect(
            lambda checked: (
                _batch_set_exclude(False),
                _reset_batch_toggle(batch_clear_exclude),
            )
            if checked
            else None
        )
    except Exception as exc:
        logger.debug(
            "Falha ao conectar acoes de marcacao em lote no menu multiselect: %s", exc
        )
    return row_idx


def _collect_years_from_dates(series):
    """Extrai anos de datas usando operacoes vetorizadas."""
    try:
        ts = pd.to_datetime(series, errors="coerce")
        years = ts.dt.year.dropna().astype(int).unique()
        return sorted(years, reverse=True)
    except Exception:
        return []


def _collect_years_from_weeks(series):
    """Extrai anos de semanas no formato YYYYWW em modo vetorizado."""
    try:
        nums = pd.to_numeric(series, errors="coerce").dropna().astype(int)
        years = (nums // 100).unique()
        return sorted(years, reverse=True)
    except Exception:
        return []


def _populate_advanced_values_cache(self, df, cache) -> None:
    def _unique_sorted(col):
        try:
            vals = df[col].dropna().astype(str).str.strip()
            vals = vals[vals != ""]
            return sorted(set(vals), key=lambda v: v.casefold())
        except Exception:
            return []

    def _sort_sector_values(values):
        try:
            return self._sort_sectors(set(values))
        except Exception:
            return sorted(set(values), key=lambda v: str(v).casefold())

    cache["exec_vals"] = (
        _sort_sector_values(_unique_sorted("setor_executor"))
        if "setor_executor" in df.columns
        else []
    )
    cache["emis_vals"] = (
        _sort_sector_values(_unique_sorted("setor_emissor"))
        if "setor_emissor" in df.columns
        else []
    )
    cache["status_vals"] = (
        _unique_sorted("situacao") if "situacao" in df.columns else []
    )

    emissao_years = []
    if "data_cadastro" in df.columns:
        emissao_years = _collect_years_from_dates(df["data_cadastro"])
    elif "semana_cadastro" in df.columns:
        emissao_years = _collect_years_from_weeks(df["semana_cadastro"])
    cache["emissao_years"] = emissao_years

    execucao_years = []
    if "semana_executada" in df.columns:
        execucao_years = _collect_years_from_weeks(df["semana_executada"])
    cache["execucao_years"] = execucao_years

    cache["prio_emissao_vals"] = (
        _unique_sorted("grau_prioridade_emissao")
        if "grau_prioridade_emissao" in df.columns
        else []
    )
    cache["prio_planejamento_vals"] = (
        _unique_sorted("grau_prioridade_planejamento")
        if "grau_prioridade_planejamento" in df.columns
        else []
    )
    if "num_reprogramacoes" in df.columns:
        try:
            reprog_series = pd.to_numeric(
                df["num_reprogramacoes"], errors="coerce"
            ).dropna()
            reprog_vals = reprog_series.astype(int).unique()
            cache["reprog_vals"] = sorted(reprog_vals, reverse=True)
        except Exception:
            cache["reprog_vals"] = []
    else:
        cache["reprog_vals"] = []


def _rebuild_multiselect_menu(
    self,
    button,
    menu,
    values,
    selected_set,
    on_toggle=None,
    show_footer=None,
    exclude_selected_set=None,
    on_exclude_toggle=None,
):
    try:
        menu.clear()
    except Exception as exc:
        logger.debug("Falha ao limpar menu multiselect antes de reconstruir: %s", exc)
    selected_norm = {str(v).casefold() for v in (selected_set or [])}
    exclude_norm = {str(v).casefold() for v in (exclude_selected_set or [])}
    checks = []
    exclude_checks = []

    # Obter nome do filtro do titulo do GroupBox pai (subindo na hierarquia)
    filter_name = _detect_filter_name_from_button(button)
    has_exclude_column = exclude_selected_set is not None
    popup_width, include_col_min, exclude_col_min, valid_values = (
        _compute_multiselect_popup_metrics(
            button,
            values,
            filter_name,
            has_exclude_column,
        )
    )
    try:
        menu.setMinimumWidth(popup_width)
        menu.setMaximumWidth(popup_width)
    except Exception as exc:
        logger.debug("Falha ao ajustar largura do menu multiselect: %s", exc)

    popup_bg, popup_text, popup_border, checked_bg, checkbox_bg, checkbox_border = (
        _resolve_popup_theme_tokens(
            self,
            button,
            menu,
        )
    )

    container = QWidget()
    grid = QGridLayout(container)
    grid.setContentsMargins(6, 4, 14 + SIMPLE_POPUP_RIGHT_GUTTER_PX, 4)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(4)
    try:
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar grid do menu multiselect no topo: %s", exc)
    if has_exclude_column:
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        grid.setColumnMinimumWidth(1, include_col_min)
        grid.setColumnMinimumWidth(2, exclude_col_min)
    else:
        grid.setColumnStretch(0, 1)
    row_idx = 0

    # Header com nome do filtro (sempre) e colunas == / != (so quando tem exclude)
    if filter_name:
        label_filter = QLabel(filter_name)
        try:
            label_filter.setStyleSheet("font-weight: bold; font-size: 11px;")
        except Exception as exc:
            logger.debug("Failed to style multiselect menu header label: %s", exc)
        grid.addWidget(label_filter, row_idx, 0)

        if exclude_selected_set is not None:
            label_inc = QLabel("Conter")
            label_exc = QLabel("Nao conter")
            try:
                label_style_inc = (
                    "font-size: 10px;"
                    f" color: {popup_text};"
                    f" border: 1px solid {popup_border};"
                    " border-radius: 2px;"
                    " padding: 1px 3px;"
                )
                label_style_exc = (
                    "font-size: 10px;"
                    f" color: {popup_text};"
                    f" border: 1px solid {popup_border};"
                    " border-radius: 2px;"
                    " padding: 1px 7px 1px 3px;"
                )
                label_inc.setStyleSheet(label_style_inc)
                label_exc.setStyleSheet(label_style_exc)
                label_inc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                label_exc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            except Exception as exc:
                logger.debug(
                    "Falha ao estilizar header include/exclude do menu multiselect: %s",
                    exc,
                )
            grid.addWidget(
                label_inc, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter
            )
            grid.addWidget(
                label_exc, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
            )
        row_idx += 1

        # Separador entre header e conteudo
        header_sep = QFrame()
        header_sep.setFrameShape(QFrame.Shape.HLine)
        header_sep.setFrameShadow(QFrame.Shadow.Sunken)
        col_span = 3 if exclude_selected_set is not None else 1
        grid.addWidget(header_sep, row_idx, 0, 1, col_span)
        row_idx += 1

    cb_style_include = ""
    cb_style_exclude = ""
    apply_checkbox_styles = len(valid_values) <= 300
    try:
        cb_style_include = (
            "QCheckBox::indicator {"
            " width:14px; height:14px;"
            f" border:1px solid {checkbox_border};"
            f" background:{checkbox_bg};"
            "}"
            "QCheckBox::indicator:checked {"
            f" border:1px solid {checked_bg};"
            f" background:{checked_bg};"
            "}"
            "QCheckBox::indicator:checked:hover {"
            f" background:{checked_bg};"
            "}"
            "QCheckBox::indicator:disabled {"
            f" border:1px solid {checkbox_border};"
            f" background:{checkbox_bg};"
            "}"
        )
        cb_style_exclude = cb_style_include
    except Exception as exc:
        logger.debug("Falha ao gerar estilo de checkbox do menu multiselect: %s", exc)

    for val in valid_values:
        label_text = (
            str(val[1]) if isinstance(val, (list, tuple)) and len(val) > 1 else str(val)
        )
        label_text_display = label_text
        cb_value = val[0] if isinstance(val, (list, tuple)) and len(val) > 0 else val
        if SIMPLE_POPUP_TEXT_CLAMP:
            try:
                fm_label = button.fontMetrics() if button is not None else None
                if fm_label is not None:
                    label_text_display = fm_label.elidedText(
                        label_text,
                        Qt.TextElideMode.ElideRight,
                        SIMPLE_POPUP_LABEL_MAX_PX,
                    )
            except Exception:
                label_text_display = label_text
        label = QLabel(label_text_display)
        try:
            label.setWordWrap(False)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            label.setStyleSheet(f"font-size: 11px; color: {popup_text};")
            if label_text_display != label_text:
                label.setToolTip(label_text)
        except Exception as exc:
            logger.debug(
                "Falha ao estilizar label do item no menu multiselect: %s", exc
            )
        include_cb = QCheckBox()
        exclude_cb = QCheckBox() if exclude_selected_set is not None else None
        try:
            include_cb.setProperty("value", str(cb_value))
            if apply_checkbox_styles:
                include_cb.setStyleSheet(cb_style_include)
        except Exception as exc:
            logger.debug(
                "Falha ao configurar checkbox include do menu multiselect: %s", exc
            )
        if exclude_cb is not None:
            try:
                exclude_cb.setProperty("value", str(cb_value))
                if apply_checkbox_styles:
                    exclude_cb.setStyleSheet(cb_style_exclude)
            except Exception as exc:
                logger.debug(
                    "Falha ao configurar checkbox exclude do menu multiselect: %s", exc
                )
        try:
            include_cb.setChecked(str(cb_value).casefold() in selected_norm)
        except Exception as exc:
            logger.debug("Falha ao aplicar estado inicial do checkbox include: %s", exc)
        if exclude_cb is not None:
            try:
                exclude_cb.setChecked(str(cb_value).casefold() in exclude_norm)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estado inicial do checkbox exclude: %s", exc
                )
        grid.addWidget(label, row_idx, 0)
        grid.addWidget(include_cb, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        if exclude_cb is not None:
            grid.addWidget(
                exclude_cb, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter
            )
        row_idx += 1
        checks.append(include_cb)
        if exclude_cb is not None:
            exclude_checks.append(exclude_cb)
        if exclude_cb is not None:

            def _toggle_include(checked, other=exclude_cb):
                if not checked or not _is_widget_valid(other):
                    return
                try:
                    if not other.isChecked():
                        return
                    other.blockSignals(True)
                    other.setChecked(False)
                finally:
                    if _is_widget_valid(other):
                        other.blockSignals(False)

            def _toggle_exclude(checked, other=include_cb):
                if not checked or not _is_widget_valid(other):
                    return
                try:
                    if not other.isChecked():
                        return
                    other.blockSignals(True)
                    other.setChecked(False)
                finally:
                    if _is_widget_valid(other):
                        other.blockSignals(False)

            try:
                include_cb.toggled.connect(_toggle_include)
                exclude_cb.toggled.connect(_toggle_exclude)
            except Exception as exc:
                logger.warning(
                    "Falha ao conectar mutual exclusion include/exclude no menu multiselect: %s",
                    exc,
                )
        if on_toggle is not None:
            try:
                include_cb.toggled.connect(on_toggle)
            except Exception as exc:
                logger.warning(
                    "Falha ao conectar callback on_toggle do menu multiselect: %s", exc
                )
        if exclude_cb is not None and on_exclude_toggle is not None:
            try:
                exclude_cb.toggled.connect(on_exclude_toggle)
            except Exception as exc:
                logger.warning(
                    "Falha ao conectar callback on_exclude_toggle do menu multiselect: %s",
                    exc,
                )

    if exclude_selected_set is not None:
        row_idx = _append_multiselect_batch_controls(
            self,
            grid=grid,
            row_idx=row_idx,
            checks=checks,
            exclude_checks=exclude_checks,
            cb_style_include=cb_style_include,
            cb_style_exclude=cb_style_exclude,
            apply_checkbox_styles=apply_checkbox_styles,
            popup_text=popup_text,
            on_toggle=on_toggle,
            on_exclude_toggle=on_exclude_toggle,
            button=button,
        )

    scroll = QScrollArea()
    scroll.setWidget(container)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    try:
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar scroll do menu multiselect no topo: %s", exc)
    try:
        container.setStyleSheet(
            "QWidget {"
            f" background: {popup_bg};"
            f" color: {popup_text};"
            "}"
            "QLabel {"
            " font-size: 11px;"
            f" color: {popup_text};"
            "}"
        )
        scroll.setStyleSheet(
            "QScrollArea {"
            f" border: 1px solid {popup_border};"
            f" background: {popup_bg};"
            "}"
        )
        menu.setStyleSheet(
            "QMenu {"
            f" background: {popup_bg};"
            f" color: {popup_text};"
            f" border: 1px solid {popup_border};"
            "}"
            "QPushButton {"
            f" color: {popup_text};"
            f" background: {popup_bg};"
            f" border: 1px solid {popup_border};"
            " border-radius: 4px;"
            " padding: 2px 8px;"
            "}"
            "QPushButton:hover {"
            f" border: 1px solid {checked_bg};"
            "}"
        )
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar estilo visual do scroll/menu multiselect: %s", exc
        )
    try:
        base_rows = len(valid_values)
        if filter_name:
            base_rows += 2
        if exclude_selected_set is not None:
            base_rows += 2
        visible_rows = max(1, min(9, base_rows))
        target_height = 12 + (visible_rows * 22)
        scroll.setFixedHeight(max(58, min(236, target_height)))
    except Exception as exc:
        logger.debug(
            "Falha ao ajustar altura dinamica do scroll no menu multiselect: %s", exc
        )
    scroll_act = QWidgetAction(menu)
    scroll_act.setDefaultWidget(scroll)
    try:
        menu.addAction(scroll_act)
    except Exception as exc:
        logger.debug("Falha ao adicionar scroll action no menu multiselect: %s", exc)

    # Botoes de fechamento. A aplicacao fica no botao "Aplicar" geral.
    if show_footer is not None:
        close_btn = QPushButton("Fechar")
        close_btn.setFixedWidth(88)
        close_btn.setToolTip("Fechar menu")
        try:
            close_btn.clicked.connect(menu.close)
        except Exception as exc:
            logger.debug(
                "Falha ao conectar botao Fechar no menu multiselect: %s", exc
            )
        ok_row = QWidget()
        ok_layout = QHBoxLayout(ok_row)
        ok_layout.setContentsMargins(8, 4, 8, 6)
        ok_layout.setSpacing(6)
        ok_layout.addStretch()
        ok_layout.addWidget(close_btn)
        ok_layout.addStretch()
        ok_act = QWidgetAction(menu)
        ok_act.setDefaultWidget(ok_row)
        try:
            menu.addAction(ok_act)
        except Exception as exc:
            logger.debug(
                "Falha ao adicionar rodape de acoes no menu multiselect: %s", exc
            )
    self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)
    if exclude_selected_set is not None:
        return checks, exclude_checks
    return checks, []


def _checkbox_value(self, checkbox) -> str:
    try:
        text = checkbox.text()
        if text:
            return text
    except Exception as exc:
        logger.debug("Falha ao obter texto do checkbox em _checkbox_value: %s", exc)
    try:
        value = checkbox.property("value")
        if value is not None:
            return str(value)
    except Exception as exc:
        logger.debug(
            "Falha ao obter propriedade 'value' do checkbox em _checkbox_value: %s", exc
        )
    return ""


def _sync_multiselect_checks(
    self, button, checks, selected, exclude_checks=None, exclude_selected=None
):
    selected_set = {str(v).casefold() for v in (selected or [])}
    for cb in checks or []:
        try:
            cb.setChecked(self._checkbox_value(cb).casefold() in selected_set)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar checkbox include em multiselect: %s", exc
            )
    exclude_set = {str(v).casefold() for v in (exclude_selected or [])}
    for cb in exclude_checks or []:
        try:
            cb.setChecked(self._checkbox_value(cb).casefold() in exclude_set)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar checkbox exclude em multiselect: %s", exc
            )
    self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)


def _build_advanced_filters_panel(self):
    group = QGroupBox("Filtros Avancados")
    self._menu_pre_show_hooks = {}
    try:
        group.setObjectName("adv_filters_group")
    except Exception as exc:
        logger.debug(
            "Falha ao configurar objectName do painel de filtros avancados: %s", exc
        )
    outer = QVBoxLayout(group)
    outer.setContentsMargins(1, 1, 1, 1)
    outer.setSpacing(1)

    grid_container = QWidget()
    grid_container_layout = QVBoxLayout(grid_container)
    grid_container_layout.setContentsMargins(0, 0, 0, 0)
    grid_container_layout.setSpacing(0)

    layout_baseline = _resolve_adv_layout_baseline(self)
    emis_box, emis_button, emis_menu, emis_exclude = self._make_multiselect_box(
        "Emissor",
        layout_baseline=layout_baseline,
    )
    exec_box, exec_button, exec_menu, exec_exclude = self._make_multiselect_box(
        "Executor",
        layout_baseline=layout_baseline,
    )
    status_box, status_button, status_menu, status_exclude = self._make_multiselect_box(
        "Situacao",
        layout_baseline=layout_baseline,
    )
    year_emissao_box, year_emissao_button, year_emissao_menu, _ = (
        self._make_multiselect_box(
            "Ano Emissao",
            with_exclude=False,
            layout_baseline=layout_baseline,
        )
    )
    year_execucao_box, year_execucao_button, year_execucao_menu, _ = (
        self._make_multiselect_box(
            "Ano Execucao",
            with_exclude=False,
            layout_baseline=layout_baseline,
        )
    )

    reprog_box = QGroupBox("Reprogramacoes")
    _flatten_field_box(reprog_box)
    reprog_layout = QGridLayout(reprog_box)
    reprog_layout.setContentsMargins(0, 0, 0, 0)
    reprog_layout.setHorizontalSpacing(4)
    reprog_layout.setVerticalSpacing(0)
    reprog_mode = QComboBox()
    reprog_mode.addItem("= Igual", "eq")
    reprog_mode.addItem("<= Menor ou igual", "lte")
    reprog_mode.addItem(">= Maior ou igual", "gte")
    _, reprog_base_min, reprog_base_max = layout_baseline
    reprog_min = max(70, min(108, reprog_base_min - 8))
    reprog_max = max(reprog_min + 40, min(196, reprog_base_max + 46))
    try:
        mode_min = max(82, min(110, reprog_min + 6))
        mode_max = max(mode_min + 12, min(126, reprog_max + 10))
        reprog_mode.setMinimumWidth(mode_min)
        reprog_mode.setMaximumWidth(mode_max)
        reprog_mode.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        reprog_mode.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        reprog_mode.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug(
            "Falha ao definir largura minima do seletor de reprogramacoes: %s", exc
        )
    reprog_layout.addWidget(reprog_mode, 0, 0)
    _reprog_menu_box, reprog_button, reprog_menu, _ = self._make_multiselect_box(
        "Valores",
        placeholder="Nº",
        with_exclude=False,
        layout_baseline=layout_baseline,
    )
    try:
        btn_min = max(54, min(68, reprog_min - 24))
        btn_max = max(btn_min + 8, min(82, reprog_max - 34))
        reprog_button.setMinimumWidth(btn_min)
        reprog_button.setMaximumWidth(btn_max)
        reprog_button.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        reprog_button.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        reprog_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug(
            "Falha ao definir largura minima do botao de reprogramacoes: %s", exc
        )
    reprog_layout.addWidget(reprog_button, 0, 1)
    try:
        reprog_layout.setColumnStretch(0, 1)
        reprog_layout.setColumnStretch(1, 0)
    except Exception as exc:
        logger.debug("Falha ao ajustar colunas de Reprogramacoes: %s", exc)
    self.adv_reprog_mode = reprog_mode
    self.adv_reprog_button = reprog_button
    self.adv_reprog_menu = reprog_menu
    self.adv_reprog_checks = []

    prio_emis_box, prio_emis_button, prio_emis_menu, _ = self._make_multiselect_box(
        "Prio. Emissao",
        layout_baseline=layout_baseline,
    )
    prio_plan_box, prio_plan_button, prio_plan_menu, _ = self._make_multiselect_box(
        "Prio. Planejamento",
        layout_baseline=layout_baseline,
    )

    deriv_box, deriv_button, deriv_menu, _ = self._make_multiselect_box(
        "Derivadas",
        with_exclude=False,
        layout_baseline=layout_baseline,
    )
    deriv_values = [
        ("has", "Possui Derivadas"),
        ("all_ste", _DERIVADA_ALL_STE_LABEL),
        ("is", "Sou Derivada"),
    ]
    deriv_selected = set()
    current_adv = getattr(self, "_advanced_filters", None) or {}
    if bool(current_adv.get("derivada_has")):
        deriv_selected.add("has")
    if bool(current_adv.get("derivada_all_ste")):
        deriv_selected.add("all_ste")
    if bool(current_adv.get("derivada_is")):
        deriv_selected.add("is")
    deriv_checks, _ = self._rebuild_multiselect_menu(
        deriv_button,
        deriv_menu,
        deriv_values,
        deriv_selected,
        lambda *_: self._update_multiselect_button(
            deriv_button,
            getattr(self, "adv_derivada_checks", None),
        ),
        self._apply_advanced_filters_from_ui,
        None,
        None,
    )
    self.adv_derivada_button = deriv_button
    self.adv_derivada_menu = deriv_menu
    self.adv_derivada_checks = deriv_checks
    self._set_menu_pre_show_hook(
        deriv_button,
        lambda: _refresh_derivadas_menu(
            self,
            getattr(self, "_advanced_filters", None) or {},
            lambda: self._apply_advanced_filters_from_ui(),
            selected_override=_collect_derivadas_selected_from_checks(self),
        ),
    )

    week_emis_box = QGroupBox("Emissao (AnoSemana)")
    _flatten_field_box(week_emis_box)
    week_emis_layout = QHBoxLayout(week_emis_box)
    week_emis_layout.setContentsMargins(0, 0, 0, 0)
    week_emis_layout.setSpacing(2)
    week_emissao_start = QLineEdit()
    week_emissao_start.setPlaceholderText("Ini")
    try:
        week_emissao_start.setMaxLength(6)
        week_emissao_start.setMinimumWidth(64)
        week_emissao_start.setMaximumWidth(108)
        week_emissao_start.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana inicial de emissao: %s", exc)
    week_emissao_end = QLineEdit()
    week_emissao_end.setPlaceholderText("Fim")
    try:
        week_emissao_end.setMaxLength(6)
        week_emissao_end.setMinimumWidth(64)
        week_emissao_end.setMaximumWidth(108)
        week_emissao_end.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana final de emissao: %s", exc)
    week_emissao_exclude = None
    week_emis_layout.addWidget(week_emissao_start)
    week_emis_layout.addWidget(week_emissao_end)

    week_exec_box = QGroupBox("Execucao (AnoSemana)")
    _flatten_field_box(week_exec_box)
    week_exec_layout = QHBoxLayout(week_exec_box)
    week_exec_layout.setContentsMargins(0, 0, 0, 0)
    week_exec_layout.setSpacing(2)
    week_exec_start = QLineEdit()
    week_exec_start.setPlaceholderText("Ini")
    try:
        week_exec_start.setMaxLength(6)
        week_exec_start.setMinimumWidth(64)
        week_exec_start.setMaximumWidth(108)
        week_exec_start.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana inicial de execucao: %s", exc)
    week_exec_end = QLineEdit()
    week_exec_end.setPlaceholderText("Fim")
    try:
        week_exec_end.setMaxLength(6)
        week_exec_end.setMinimumWidth(64)
        week_exec_end.setMaximumWidth(108)
        week_exec_end.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana final de execucao: %s", exc)
    week_exec_exclude = None
    week_exec_layout.addWidget(week_exec_start)
    week_exec_layout.addWidget(week_exec_end)

    macro_box = QGroupBox("Macro")
    _flatten_field_box(macro_box)
    macro_layout = QHBoxLayout(macro_box)
    macro_layout.setContentsMargins(0, 0, 0, 0)
    macro_combo = QComboBox()
    try:
        macro_combo.setMinimumWidth(100)
    except Exception as exc:
        logger.debug("Falha ao definir largura minima do filtro macro: %s", exc)
    macro_combo.addItem("Nenhum", None)
    macro_combo.addItem("Baixar", "ssas_para_baixar")
    macro_combo.currentIndexChanged.connect(self._on_macro_filter_changed)
    macro_layout.addWidget(macro_combo)

    sol_box, sol_button, sol_menu, sol_exclude = self._make_multiselect_box(
        "Solicitante",
        layout_baseline=layout_baseline,
    )
    prog_box, prog_button, prog_menu, prog_exclude = self._make_multiselect_box(
        "Resp Prog",
        layout_baseline=layout_baseline,
    )
    exec_resp_box, exec_resp_button, exec_resp_menu, exec_resp_exclude = (
        self._make_multiselect_box(
            "Resp Exec",
            layout_baseline=layout_baseline,
        )
    )
    self._set_menu_pre_show_hook(
        sol_button,
        lambda prefix="adv_responsavel_solicitante": self._ensure_responsavel_options_materialized(
            target_prefix=prefix
        ),
    )
    self._set_menu_pre_show_hook(
        prog_button,
        lambda prefix="adv_responsavel_programacao": self._ensure_responsavel_options_materialized(
            target_prefix=prefix
        ),
    )
    self._set_menu_pre_show_hook(
        exec_resp_button,
        lambda prefix="adv_responsavel_execucao": self._ensure_responsavel_options_materialized(
            target_prefix=prefix
        ),
    )

    main_grid = QGridLayout()
    main_grid.setContentsMargins(0, 0, 0, 0)
    main_grid.setHorizontalSpacing(4)
    main_grid.setVerticalSpacing(3)
    apply_btn = QPushButton("Aplicar")
    clear_btn = QPushButton("Limpar")
    try:
        apply_btn.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        apply_btn.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        clear_btn.setMinimumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        clear_btn.setMaximumHeight(LAYOUT_ADV_CONTROL_HEIGHT)
        apply_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        clear_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug("Falha ao estilizar botoes de acao dos filtros avancados: %s", exc)
    apply_btn.clicked.connect(self._apply_advanced_filters_from_ui)
    clear_btn.clicked.connect(self._clear_advanced_filters)
    action_box = QGroupBox(" ")
    _flatten_field_box(action_box)
    action_layout = QHBoxLayout(action_box)
    action_layout.setContentsMargins(0, 0, 0, 0)
    action_layout.setSpacing(4)
    action_layout.addWidget(apply_btn)
    action_layout.addWidget(clear_btn)
    grid_container_layout.addLayout(main_grid)
    controls_scroll = QScrollArea()
    controls_scroll.setWidgetResizable(True)
    controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    controls_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    try:
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
    except Exception as exc:
        logger.debug("Falha ao remover borda do scroll de filtros avancados: %s", exc)
    controls_scroll.setWidget(grid_container)
    try:
        controls_scroll.setMinimumHeight(LAYOUT_ADV_PANEL_MIN_HEIGHT)
        controls_scroll.setMaximumHeight(LAYOUT_ADV_PANEL_MAX_HEIGHT)
    except Exception as exc:
        logger.debug(
            "Falha ao aplicar limites de altura no painel de filtros avancados: %s", exc
        )
    outer.addWidget(controls_scroll, 0)

    self._adv_filters_main_grid = main_grid
    self._adv_filters_grid_widgets = {
        "emis_box": emis_box,
        "exec_box": exec_box,
        "status_box": status_box,
        "year_emissao_box": year_emissao_box,
        "year_execucao_box": year_execucao_box,
        "reprog_box": reprog_box,
        "prio_emis_box": prio_emis_box,
        "prio_plan_box": prio_plan_box,
        "deriv_box": deriv_box,
        "macro_box": macro_box,
        "week_emis_box": week_emis_box,
        "week_exec_box": week_exec_box,
        "sol_box": sol_box,
        "prog_box": prog_box,
        "exec_resp_box": exec_resp_box,
        "action_box": action_box,
    }

    self._adv_filters_apply_btn = apply_btn
    self._adv_filters_clear_btn = clear_btn
    self._adv_filters_action_widget = action_box
    self._adv_filters_action_btn_dims = None
    self._adv_filters_controls_scroll = controls_scroll
    self._adv_filters_grid_cols = None
    self._adv_filters_last_widget_count = None
    self._adv_filters_group_obj = group
    if _is_widget_valid(group):
        _update_advanced_filters_action_buttons(self, group.width())
    _enforce_advanced_filters_compact_metrics(self)

    try:
        if _is_widget_valid(group):
            self._reorganize_advanced_filters_grid(group.width())
    except Exception as exc:
        logger.debug("Falha no relayout inicial dos filtros avancados: %s", exc)

    ctx = {
        "adv_filters_group": group,
        "adv_executor_button": exec_button,
        "adv_executor_menu": exec_menu,
        "adv_executor_checks": [],
        "adv_executor_exclude": exec_exclude,
        "adv_emissor_button": emis_button,
        "adv_emissor_menu": emis_menu,
        "adv_emissor_checks": [],
        "adv_emissor_exclude": emis_exclude,
        "adv_status_button": status_button,
        "adv_status_menu": status_menu,
        "adv_status_checks": [],
        "adv_status_exclude": status_exclude,
        "adv_year_emissao_button": year_emissao_button,
        "adv_year_emissao_menu": year_emissao_menu,
        "adv_year_emissao_checks": [],
        "adv_year_execucao_button": year_execucao_button,
        "adv_year_execucao_menu": year_execucao_menu,
        "adv_year_execucao_checks": [],
        "adv_reprog_box": reprog_box,
        "adv_reprog_mode": reprog_mode,
        "adv_reprog_button": reprog_button,
        "adv_reprog_menu": reprog_menu,
        "adv_reprog_checks": [],
        "adv_week_emissao_start": week_emissao_start,
        "adv_week_emissao_end": week_emissao_end,
        "adv_week_emissao_exclude": week_emissao_exclude,
        "adv_week_execucao_start": week_exec_start,
        "adv_week_execucao_end": week_exec_end,
        "adv_week_execucao_exclude": week_exec_exclude,
        "adv_prioridade_emissao_button": prio_emis_button,
        "adv_prioridade_emissao_menu": prio_emis_menu,
        "adv_prioridade_emissao_checks": [],
        "adv_prioridade_planejamento_button": prio_plan_button,
        "adv_prioridade_planejamento_menu": prio_plan_menu,
        "adv_prioridade_planejamento_checks": [],
        "adv_derivada_button": deriv_button,
        "adv_derivada_menu": deriv_menu,
        "adv_derivada_checks": deriv_checks,
        "adv_derivada_has": None,
        "adv_derivada_is": None,
        "adv_responsavel_solicitante_button": sol_button,
        "adv_responsavel_solicitante_menu": sol_menu,
        "adv_responsavel_solicitante_checks": [],
        "adv_responsavel_solicitante_exclude": sol_exclude,
        "adv_responsavel_solicitante_box": sol_box,
        "adv_responsavel_programacao_button": prog_button,
        "adv_responsavel_programacao_menu": prog_menu,
        "adv_responsavel_programacao_checks": [],
        "adv_responsavel_programacao_exclude": prog_exclude,
        "adv_responsavel_programacao_box": prog_box,
        "adv_responsavel_execucao_button": exec_resp_button,
        "adv_responsavel_execucao_menu": exec_resp_menu,
        "adv_responsavel_execucao_checks": [],
        "adv_responsavel_execucao_exclude": exec_resp_exclude,
        "adv_responsavel_execucao_box": exec_resp_box,
        "adv_macro_combo": macro_combo,
    }
    return group, ctx


def _show_derivadas_popup(self):
    """Compatibilidade de facade. Popup de derivadas foi removido."""
    return


def _update_derivadas_button_state(self):
    """Compatibilidade de facade. Nao ha botao de derivadas especificas."""
    return


def _save_advanced_filters_default(self):
    """Compatibilidade de facade. Acao removida da UI."""
    return


def _on_macro_filter_changed(self):
    try:
        choice = self.adv_macro_combo.currentData()
    except Exception:
        choice = None
    if choice == "ssas_para_baixar":
        try:
            self._sync_multiselect_checks(
                getattr(self, "adv_derivada_button", None),
                getattr(self, "adv_derivada_checks", None),
                ["all_ste"],
            )
        except Exception as exc:
            logger.warning(
                "Falha ao aplicar preset de derivadas no macro filtro: %s", exc
            )
        try:
            self._sync_multiselect_checks(
                getattr(self, "adv_status_button", None),
                getattr(self, "adv_status_checks", None),
                [],
                getattr(self, "adv_status_exclude_checks", None),
                _MACRO_BAIXAR_EXCLUDED_STATUSES,
            )
        except Exception as exc:
            logger.warning("Falha ao aplicar preset de status no macro filtro: %s", exc)

def _reorganize_advanced_filters_grid(self, width: int):
    """Reorganiza grid de filtros avancados em distribuicao continua por colunas."""
    if not hasattr(self, "_adv_filters_main_grid") or not hasattr(
        self, "_adv_filters_grid_widgets"
    ):
        return
    _enforce_advanced_filters_compact_metrics(self)

    effective_width = width
    controls_scroll = getattr(self, "_adv_filters_controls_scroll", None)
    max_scroll_h = LAYOUT_ADV_PANEL_MAX_HEIGHT
    try:
        if controls_scroll is not None and hasattr(controls_scroll, "viewport"):
            viewport_w = int(controls_scroll.viewport().width())
            if viewport_w > 0:
                effective_width = min(effective_width, viewport_w)
        if (
            controls_scroll is not None
            and hasattr(self, "adv_filters_group")
            and self.adv_filters_group is not None
        ):
            group_h = int(self.adv_filters_group.height())
            if group_h > 0:
                max_scroll_h = max(
                    80,
                    min(
                        LAYOUT_ADV_PANEL_MAX_HEIGHT,
                        group_h - (LAYOUT_ADV_CONTROL_HEIGHT + 8),
                    ),
                )
    except Exception as exc:
        logger.debug(
            "Falha ao obter largura efetiva do viewport dos filtros avancados: %s", exc
        )

    _update_advanced_filters_action_buttons(self, effective_width)
    _apply_advanced_filters_font_policy(self, effective_width)

    if effective_width < LAYOUT_MIN_VALID_WIDTH:
        return

    grid = self._adv_filters_main_grid
    w = self._adv_filters_grid_widgets
    order = [
        "emis_box",
        "exec_box",
        "status_box",
        "year_emissao_box",
        "year_execucao_box",
        "reprog_box",
        "prio_emis_box",
        "prio_plan_box",
        "macro_box",
        "deriv_box",
        "week_emis_box",
        "week_exec_box",
        "sol_box",
        "prog_box",
        "exec_resp_box",
        "action_box",
    ]
    visible = [(name, widget) for name in order if (widget := w.get(name)) is not None]
    if not visible:
        return

    cell_min_width = _compute_adv_grid_cell_min_width(self, visible)
    try:
        spacing = int(grid.horizontalSpacing())
    except Exception:
        spacing = 0
    try:
        margins = grid.contentsMargins()
        horizontal_padding = int(margins.left() + margins.right())
    except Exception:
        horizontal_padding = 0
    available_for_cells = max(0, int(effective_width) - horizontal_padding)
    cols = 1
    max_try_cols = min(LAYOUT_GRID_MAX_COLS, len(visible))
    preferred_cols = min(LAYOUT_GRID_PREF_COLS, max_try_cols)
    candidate_order = list(range(preferred_cols, 0, -1))
    if max_try_cols > preferred_cols:
        candidate_order = (
            list(range(max_try_cols, preferred_cols - 1, -1)) + candidate_order
        )
    for candidate_cols in candidate_order:
        required_width = (candidate_cols * cell_min_width) + max(
            0, candidate_cols - 1
        ) * spacing
        if required_width <= available_for_cells:
            cols = candidate_cols
            break
    cols = max(LAYOUT_GRID_MIN_COLS, cols)
    cols = min(cols, len(visible))
    rows_for_height = max(1, (len(visible) + cols - 1) // cols)
    try:
        vertical_spacing = int(grid.verticalSpacing())
        margins = grid.contentsMargins()
        content_h = (
            rows_for_height * LAYOUT_ADV_FIELD_BOX_MAX_HEIGHT
            + max(0, rows_for_height - 1) * max(0, vertical_spacing)
            + int(margins.top() + margins.bottom())
            + 2
        )
        min_content_h = (
            int(margins.top() + margins.bottom()) + LAYOUT_ADV_FIELD_BOX_MIN_HEIGHT + 2
        )
        content_h = max(content_h, min_content_h)
        target_scroll_h = max(60, min(max_scroll_h, content_h))
        if controls_scroll is not None:
            controls_scroll.setMinimumHeight(target_scroll_h)
            controls_scroll.setMaximumHeight(target_scroll_h)
    except Exception as exc:
        logger.debug(
            "Falha ao ajustar altura real do scroll de filtros avancados: %s", exc
        )

    if getattr(self, "_adv_filters_grid_cols", None) == cols and getattr(
        self, "_adv_filters_last_widget_count", None
    ) == len(visible):
        return
    self._adv_filters_grid_cols = cols
    self._adv_filters_last_widget_count = len(visible)
    self._adv_filters_layout_mode = f"cols_{cols}"

    # Remove todos os widgets do grid
    while grid.count():
        item = grid.takeAt(0)
        widget = item.widget()
        if widget is not None:
            grid.removeWidget(widget)
            widget.hide()
        del item

    for idx, (_, widget) in enumerate(visible):
        row = idx // cols
        col = idx % cols
        grid.addWidget(widget, row, col)
        widget.show()
    for col in range(0, LAYOUT_GRID_MAX_COLS + 3):
        try:
            grid.setColumnStretch(col, 0)
        except Exception as exc:
            logger.debug("Falha ao resetar stretch de coluna no grid avancado: %s", exc)
    for col in range(cols):
        grid.setColumnStretch(col, 1)


def _on_adv_sector_selection_changed(self, *_):
    if getattr(self, "_adv_sector_syncing", False):
        return
    if getattr(self, "_adv_sector_handler_running", False):
        return
    self._adv_sector_handler_running = True
    try:
        self._apply_divisao_to_setor_checks()
        try:
            self._update_multiselect_button(
                self.adv_executor_button,
                self.adv_executor_checks,
                exclude_checks=getattr(self, "adv_executor_exclude_checks", None),
            )
        except Exception as exc:
            logger.warning("Falha ao atualizar botao de setor executor: %s", exc)
        try:
            self._update_multiselect_button(
                self.adv_emissor_button,
                self.adv_emissor_checks,
                exclude_checks=getattr(self, "adv_emissor_exclude_checks", None),
            )
        except Exception as exc:
            logger.warning("Falha ao atualizar botao de setor emissor: %s", exc)
        self._schedule_sector_options_refresh()
    finally:
        self._adv_sector_handler_running = False


def _on_adv_sector_exclude_changed(self, *_):
    """Atualiza filtros de exclusão de setor com debouncing."""
    if getattr(self, "_adv_sector_syncing", False):
        return
    if getattr(self, "_adv_sector_handler_running", False):
        return
    try:
        self._update_multiselect_button(
            self.adv_executor_button,
            self.adv_executor_checks,
            exclude_checks=getattr(self, "adv_executor_exclude_checks", None),
        )
    except Exception as exc:
        logger.warning("Falha ao atualizar botao de setor executor (exclude): %s", exc)
    try:
        self._update_multiselect_button(
            self.adv_emissor_button,
            self.adv_emissor_checks,
            exclude_checks=getattr(self, "adv_emissor_exclude_checks", None),
        )
    except Exception as exc:
        logger.warning("Falha ao atualizar botao de setor emissor (exclude): %s", exc)
    self._schedule_sector_options_refresh()


def _schedule_sector_options_refresh(self):
    """Agenda refresh de opções dependentes de setor evitando rajadas de sinais."""
    timer = getattr(self, "_sector_debounce_timer", None)
    built = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    if not built:
        self._mark_responsavel_dirty()
        try:
            if timer is not None and _is_widget_valid(timer):
                timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce de setores sem prefixos materializados: %s",
                exc,
            )
        return
    self._mark_responsavel_dirty(prefixes=built)
    if timer is None:
        try:
            self._on_sector_debounce_timeout()
        except Exception as exc:
            logger.warning("Falha no refresh imediato de setores (sem timer): %s", exc)
        return
    try:
        if _is_widget_valid(timer):
            timer.stop()
            timer.start()
            return
    except Exception as exc:
        logger.warning("Falha ao reiniciar timer de debounce de setores: %s", exc)
    try:
        self._on_sector_debounce_timeout()
    except Exception as exc:
        logger.warning("Falha no fallback de refresh de setores: %s", exc)


def _collect_divisao_setores(self, divisao_values):
    setores = set()
    for div in divisao_values or []:
        try:
            setores.update(DIVISAO_SETORES.get(str(div), []))
        except Exception as exc:
            logger.debug("Falha ao coletar setores para divisao %r: %s", div, exc)
    return setores


def _sector_sort_key(self, sector: str):
    div = SECTOR_TO_DIV.get(sector, "")
    # Ordem: SMIN primeiro (0), SMME segundo (1), outras divisoes alfabeticamente (2+)
    if div == "SMIN":
        div_rank = 0
    elif div == "SMME":
        div_rank = 1
    elif div:
        div_rank = 2
    else:
        div_rank = 3
    return (div_rank, div.casefold(), sector.casefold())


def _sort_sectors(self, values):
    return sorted(values, key=self._sector_sort_key)


def _sort_responsavel_values(self, df_subset, values, resp_col: str, df_source=None):
    if not values:
        return []
    source_df = df_source if isinstance(df_source, pd.DataFrame) else df_subset
    sector_cols = [
        c for c in ["setor_executor", "setor_emissor"] if c in source_df.columns
    ]
    sector_counts = {}
    for col in sector_cols:
        try:
            pairs = source_df[[col, resp_col]].dropna().copy()
            pairs[col] = pairs[col].astype("string").fillna("").str.strip()
            pairs[resp_col] = pairs[resp_col].astype("string").fillna("").str.strip()
            pairs = pairs[(pairs[col] != "") & (pairs[resp_col] != "")]
            if pairs.empty:
                continue
            grouped = (
                pairs.groupby([resp_col, col], dropna=False)
                .size()
                .reset_index(name="count")
            )
        except Exception as exc:
            logger.debug(
                "Falha ao montar pares responsavel/setor (%s, %s): %s",
                col,
                resp_col,
                exc,
            )
            continue
        for person_str, sec_str, count in grouped.itertuples(index=False):
            sector_counts.setdefault(person_str, {})
            sector_counts[person_str][sec_str] = sector_counts[person_str].get(
                sec_str, 0
            ) + int(count)

    def _best_sector(person):
        counts = sector_counts.get(person, {})
        if not counts:
            return ""
        return max(counts.items(), key=lambda t: (t[1], -len(t[0]), t[0].casefold()))[0]

    def _key(person):
        sec = _best_sector(person)
        div = SECTOR_TO_DIV.get(sec, "")
        div_rank = 0 if div == "SMIN" else 1 if div else 2
        return (div_rank, div.casefold(), sec.casefold(), person.casefold())

    ordered = sorted(values, key=_key)
    decorated = []
    for person in ordered:
        sec = _best_sector(person)
        div = SECTOR_TO_DIV.get(sec, "")
        prefix = ""
        if div and sec:
            prefix = f"{div} / {sec} - "
        elif sec:
            prefix = f"{sec} - "
        display = f"{prefix}{person}"
        decorated.append((person, display))
    return decorated


def _apply_divisao_to_setor_checks(self):
    """Compatibilidade de facade. Filtro de divisao removido da UI."""
    return


def _refresh_responsavel_options(self, target_prefixes=None):
    all_prefixes = set(getattr(self, "_responsavel_all_prefixes", ()))
    if target_prefixes is None:
        requested_prefixes = set(all_prefixes)
    else:
        requested_prefixes = {p for p in target_prefixes if p in all_prefixes}
    if not requested_prefixes:
        return
    if self.df_completo is None or self.df_completo.empty:
        self._mark_responsavel_dirty(prefixes=requested_prefixes)
        return
    exec_values = self._get_checked_values(getattr(self, "adv_executor_checks", None))
    emis_values = self._get_checked_values(getattr(self, "adv_emissor_checks", None))
    exec_excluded = self._get_checked_values(
        getattr(self, "adv_executor_exclude_checks", None)
    )
    emis_excluded = self._get_checked_values(
        getattr(self, "adv_emissor_exclude_checks", None)
    )
    has_sector = bool(exec_values or emis_values or exec_excluded or emis_excluded)

    def apply_cb():
        return self._apply_advanced_filters_from_ui()

    def _set_enabled(widget, enabled):
        if widget is None:
            return
        try:
            widget.setEnabled(bool(enabled))
        except Exception as exc:
            logger.debug(
                "Falha ao ajustar estado enabled de widget %r: %s", widget, exc
            )

    def _set_visible(widget, visible):
        if widget is None:
            return
        try:
            widget.setVisible(bool(visible))
        except Exception as exc:
            logger.debug("Falha ao ajustar visibilidade de widget %r: %s", widget, exc)

    df = self.df_completo
    exec_col = "setor_executor"
    emis_col = "setor_emissor"
    selected_exec = set(exec_values)
    selected_emis = set(emis_values)
    selected_exec_excluded = set(exec_excluded)
    selected_emis_excluded = set(emis_excluded)

    def _apply_sector_subset(frame):
        subset = frame
        if exec_col in subset.columns:
            allowed = set(selected_exec)
            excluded = set(selected_exec_excluded)
            exec_series = subset[exec_col].astype("string").fillna("")
            if allowed:
                subset = subset[exec_series.isin(allowed)]
            if excluded:
                subset = subset[~exec_series.isin(excluded)]
        if emis_col in subset.columns and selected_emis:
            emis_series = subset[emis_col].astype("string").fillna("")
            subset = subset[emis_series.isin(selected_emis)]
        if emis_col in subset.columns and selected_emis_excluded:
            emis_series = subset[emis_col].astype("string").fillna("")
            subset = subset[~emis_series.isin(selected_emis_excluded)]
        return subset

    if has_sector:
        df = _apply_sector_subset(df)

    def _unique_sorted(col):
        try:
            vals = df[col].dropna().astype(str).str.strip()
            vals = vals[vals != ""]
            vals = [v for v in set(vals) if v]
            return sorted(vals, key=lambda v: v.casefold())
        except Exception:
            return []

    resp_cols = [
        (
            "solicitante",
            "adv_responsavel_solicitante",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["solicitante"],
        ),
        (
            "responsavel_programacao",
            "adv_responsavel_programacao",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["responsavel_programacao"],
        ),
        (
            "responsavel_execucao",
            "adv_responsavel_execucao",
            RESPONSAVEL_FILTER_COLUMN_CANDIDATES["responsavel_execucao"],
        ),
    ]
    processed_prefixes = set()
    for key_name, prefix, candidate_cols in resp_cols:
        if prefix not in requested_prefixes:
            continue
        box = getattr(self, f"{prefix}_box", None)
        button = getattr(self, f"{prefix}_button", None)
        menu = getattr(self, f"{prefix}_menu", None)
        checks_attr = f"{prefix}_checks"
        exclude_checks_attr = f"{prefix}_exclude_checks"
        exclude = getattr(self, f"{prefix}_exclude", None)
        source_col = next(
            (name for name in candidate_cols if name in self.df_completo.columns),
            None,
        )
        col_exists = source_col is not None
        _set_visible(box, col_exists)
        if not col_exists:
            _set_enabled(button, False)
            _set_enabled(exclude, False)
            setattr(self, checks_attr, [])
            setattr(self, exclude_checks_attr, [])
            processed_prefixes.add(prefix)
            continue
        values = _unique_sorted(source_col)
        try:
            values = self._sort_responsavel_values(
                df,
                values,
                source_col,
                df_source=self.df_completo,
            )
        except Exception as exc:
            logger.debug(
                "Failed to sort responsavel values for column '%s': %s",
                source_col,
                exc,
            )
        _set_enabled(button, True)
        _set_enabled(exclude, True)
        selected = set((self._advanced_filters or {}).get(key_name) or [])
        excluded = set(
            (self._advanced_filters or {}).get(f"{key_name}_exclude_values") or []
        )
        include_checks, exclude_checks = self._rebuild_multiselect_menu(
            button,
            menu,
            values,
            selected,
            lambda *_,
            current_button=button,
            current_checks_attr=checks_attr,
            current_exclude_checks_attr=exclude_checks_attr: self._update_multiselect_button(
                current_button,
                getattr(self, current_checks_attr, []),
                exclude_checks=getattr(self, current_exclude_checks_attr, None),
            ),
            True,
            excluded,
            lambda *_,
            current_button=button,
            current_checks_attr=checks_attr,
            current_exclude_checks_attr=exclude_checks_attr: self._update_multiselect_button(
                current_button,
                getattr(self, current_checks_attr, []),
                exclude_checks=getattr(self, current_exclude_checks_attr, None),
            ),
        )
        setattr(self, checks_attr, include_checks)
        setattr(self, exclude_checks_attr, exclude_checks)
        processed_prefixes.add(prefix)

    adv_cache = getattr(self, "_adv_values_cache", {}) or {}
    derivadas_numbers = adv_cache.get("derivadas_vals", [])
    if not derivadas_numbers:
        # Extrai numeros unicos de SSAs derivadas se nao estiver em cache
        try:
            if "derivada_de" in df.columns:
                derivadas_series = self._normalize_ssa_series(df["derivada_de"])
                derivadas_numbers = sorted(
                    {v for v in derivadas_series.unique() if v and str(v).strip()},
                    key=lambda x: str(x).casefold(),
                )
                adv_cache["derivadas_vals"] = derivadas_numbers
                self._adv_values_cache = adv_cache
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar cache de derivadas em filtros avancados: %s", exc
            )
    materialized = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    materialized |= processed_prefixes
    self._responsavel_materialized_prefixes = materialized
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    dirty -= processed_prefixes
    self._responsavel_dirty_prefixes = dirty
    self._sync_responsavel_flags()


def _clear_advanced_filters(self):
    try:
        self._store_last_filter_state()
    except Exception as exc:
        logger.warning(
            "Falha ao salvar estado antes de limpar filtros avancados: %s", exc
        )
    self._advanced_filters = {}
    self._advanced_filters_active = False
    try:
        setattr(self, "_adv_options_dirty", True)
        if hasattr(self, "_schedule_adv_options_refresh"):
            self._schedule_adv_options_refresh()
    except Exception as exc:
        logger.debug("Falha ao agendar refresh apos limpar filtros avancados: %s", exc)
    try:
        self._sync_advanced_filter_ui()
    except Exception as exc:
        logger.warning("Falha ao sincronizar UI apos limpar filtros avancados: %s", exc)
    try:
        if (
            getattr(self, "_active_filter_panel_kind", None) == "advanced"
            and bool(getattr(self, "_adv_options_dirty", False))
            and hasattr(self, "_refresh_advanced_filter_options")
        ):
            self._refresh_advanced_filter_options()
            self._adv_options_dirty = False
    except Exception as exc:
        logger.warning(
            "Falha ao executar refresh imediato de filtros avancados apos limpar: %s",
            exc,
        )
    try:
        self._refresh_after_filter_change()
    except Exception as exc:
        logger.warning("Falha ao reaplicar filtros apos limpeza de avancados: %s", exc)


def _has_active_advanced_filters(self, data: dict) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    list_keys = (
        "setor_executor",
        "setor_emissor",
        "situacao",
        "solicitante",
        "responsavel_programacao",
        "responsavel_execucao",
    )
    for key in list_keys:
        if data.get(key):
            return True
    exclude_list_keys = (
        "setor_executor_exclude_values",
        "setor_emissor_exclude_values",
        "situacao_exclude_values",
        "solicitante_exclude_values",
        "responsavel_programacao_exclude_values",
        "responsavel_execucao_exclude_values",
        "prioridade_emissao_exclude_values",
        "prioridade_planejamento_exclude_values",
    )
    for key in exclude_list_keys:
        if data.get(key):
            return True
    if data.get("ano_emissao") or data.get("ano_execucao"):
        return True
    if data.get("ano_emissao_values") or data.get("ano_execucao_values"):
        return True
    if data.get("ano_emissao_exclude_values") or data.get(
        "ano_execucao_exclude_values"
    ):
        return True
    if data.get("prioridade_emissao_values") or data.get(
        "prioridade_planejamento_values"
    ):
        return True
    if data.get("num_reprogramacoes_mode") and data.get("num_reprogramacoes_values"):
        return True
    if (
        data.get("semana_emissao_inicio") is not None
        or data.get("semana_emissao_fim") is not None
    ):
        return True
    if (
        data.get("semana_execucao_inicio") is not None
        or data.get("semana_execucao_fim") is not None
    ):
        return True
    if (
        data.get("derivada_has")
        or data.get("derivada_all_ste")
        or data.get("derivada_is")
    ):
        return True
    if data.get("macro_filter"):
        return True
    return False


def _apply_advanced_filters_from_ui(self, store_only: bool = False):
    previous_filters = dict(getattr(self, "_advanced_filters", None) or {})
    if not store_only:
        try:
            self._store_last_filter_state()
        except Exception as exc:
            logger.warning(
                "Falha ao salvar estado antes de aplicar filtros avancados: %s", exc
            )
    data = {}

    def _safe_checked(checks_attr: str) -> list[str]:
        try:
            return self._get_checked_values(getattr(self, checks_attr, None))
        except Exception as exc:
            logger.debug("Falha ao coletar valores (%s): %s", checks_attr, exc)
            return []

    def _safe_week_range(
        start_attr: str, end_attr: str
    ) -> tuple[int | None, int | None]:
        try:
            start_widget = getattr(self, start_attr, None)
            end_widget = getattr(self, end_attr, None)
            start_text = start_widget.text() if start_widget is not None else ""
            end_text = end_widget.text() if end_widget is not None else ""
            return self._parse_week(start_text), self._parse_week(end_text)
        except Exception as exc:
            logger.debug(
                "Falha ao coletar faixa de semana (%s/%s): %s",
                start_attr,
                end_attr,
                exc,
            )
            return None, None

    data["setor_executor"] = _safe_checked("adv_executor_checks")
    data["setor_executor_exclude_values"] = _safe_checked("adv_executor_exclude_checks")
    data["setor_emissor"] = _safe_checked("adv_emissor_checks")
    data["setor_emissor_exclude_values"] = _safe_checked("adv_emissor_exclude_checks")
    data["situacao"] = _safe_checked("adv_status_checks")
    data["situacao_exclude_values"] = _safe_checked("adv_status_exclude_checks")
    data["ano_emissao_values"] = _safe_checked("adv_year_emissao_checks")
    data["ano_emissao_exclude_values"] = _safe_checked(
        "adv_year_emissao_exclude_checks"
    )
    data["ano_execucao_values"] = _safe_checked("adv_year_execucao_checks")
    data["ano_execucao_exclude_values"] = _safe_checked(
        "adv_year_execucao_exclude_checks"
    )
    semana_emissao_inicio, semana_emissao_fim = _safe_week_range(
        "adv_week_emissao_start", "adv_week_emissao_end"
    )
    data["semana_emissao_inicio"] = semana_emissao_inicio
    data["semana_emissao_fim"] = semana_emissao_fim
    semana_execucao_inicio, semana_execucao_fim = _safe_week_range(
        "adv_week_execucao_start", "adv_week_execucao_end"
    )
    data["semana_execucao_inicio"] = semana_execucao_inicio
    data["semana_execucao_fim"] = semana_execucao_fim
    data["semana_emissao_exclude"] = False
    data["semana_execucao_exclude"] = False
    derivada_selected = {
        str(v).casefold()
        for v in self._get_checked_values(getattr(self, "adv_derivada_checks", None))
    }
    data["derivada_has"] = "has" in derivada_selected
    data["derivada_all_ste"] = "all_ste" in derivada_selected
    data["derivada_is"] = "is" in derivada_selected
    # derivadas_especificas_values removido - botao Especificas agora e apenas visualizacao
    adv_current = getattr(self, "_advanced_filters", None) or {}
    built_prefixes = set(getattr(self, "_responsavel_materialized_prefixes", set()))

    def _collect_responsavel_values(
        checks_attr: str, key_name: str, prefix: str
    ) -> list[str]:
        if prefix not in built_prefixes:
            return list(adv_current.get(key_name) or [])
        try:
            return self._get_checked_values(getattr(self, checks_attr, None))
        except Exception as exc:
            logger.debug(
                "Falha ao coletar responsavel (%s/%s): %s", key_name, checks_attr, exc
            )
            return []

    data["solicitante"] = _collect_responsavel_values(
        "adv_responsavel_solicitante_checks",
        "solicitante",
        "adv_responsavel_solicitante",
    )
    data["solicitante_exclude_values"] = _collect_responsavel_values(
        "adv_responsavel_solicitante_exclude_checks",
        "solicitante_exclude_values",
        "adv_responsavel_solicitante",
    )
    data["responsavel_programacao"] = _collect_responsavel_values(
        "adv_responsavel_programacao_checks",
        "responsavel_programacao",
        "adv_responsavel_programacao",
    )
    data["responsavel_programacao_exclude_values"] = _collect_responsavel_values(
        "adv_responsavel_programacao_exclude_checks",
        "responsavel_programacao_exclude_values",
        "adv_responsavel_programacao",
    )
    data["responsavel_execucao"] = _collect_responsavel_values(
        "adv_responsavel_execucao_checks",
        "responsavel_execucao",
        "adv_responsavel_execucao",
    )
    data["responsavel_execucao_exclude_values"] = _collect_responsavel_values(
        "adv_responsavel_execucao_exclude_checks",
        "responsavel_execucao_exclude_values",
        "adv_responsavel_execucao",
    )
    data["num_reprogramacoes_values"] = _safe_checked("adv_reprog_checks")
    data["num_reprogramacoes_mode"] = _safe_combo_item_data(
        getattr(self, "adv_reprog_mode", None)
    )
    data["prioridade_emissao_values"] = _safe_checked("adv_prioridade_emissao_checks")
    data["prioridade_emissao_exclude_values"] = _safe_checked(
        "adv_prioridade_emissao_exclude_checks"
    )
    data["prioridade_planejamento_values"] = _safe_checked(
        "adv_prioridade_planejamento_checks"
    )
    data["prioridade_planejamento_exclude_values"] = _safe_checked(
        "adv_prioridade_planejamento_exclude_checks"
    )
    try:
        data["macro_filter"] = self.adv_macro_combo.currentData()
    except Exception as exc:
        logger.debug("Falha ao coletar macro_filter: %s", exc)
        data["macro_filter"] = None

    self._advanced_filters = data
    executor_filters_were_active = bool(
        previous_filters.get("setor_executor")
        or previous_filters.get("setor_executor_exclude_values")
        or data.get("setor_executor")
        or data.get("setor_executor_exclude_values")
    )
    try:
        if hasattr(self, "_sync_active_executor_filter_from_advanced_filters"):
            self._sync_active_executor_filter_from_advanced_filters(
                clear_when_missing=executor_filters_were_active
            )
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar setor executor rapido a partir do painel avancado: %s",
            exc,
        )
    try:
        if hasattr(self, "_sync_quick_setor_executor_combo_from_filters"):
            self._sync_quick_setor_executor_combo_from_filters()
    except Exception as exc:
        logger.debug(
            "Falha ao sincronizar combo rapido de setor executor apos aplicar avancado: %s",
            exc,
        )
    if store_only:
        return
    self._advanced_filters_active = self._has_active_advanced_filters(data)
    notice_box = {"value": None}

    def _capture_notice(value):
        notice_box["value"] = value

    setattr(self, "_adv_notice_callback", _capture_notice)
    try:
        self._refresh_after_filter_change()
    except Exception as exc:
        logger.warning(
            "Falha ao atualizar resultado apos aplicar filtros avancados: %s", exc
        )
    finally:
        setattr(self, "_adv_notice_callback", None)
    notice = notice_box["value"]
    if notice:
        try:
            if hasattr(self, "_set_filtered_count_status"):
                notice_suffix = ""
                if notice == "derivada_all_ste_empty":
                    notice_suffix = (
                        "Aviso: nenhuma derivada STE/SES encontrada para o filtro."
                    )
                elif notice == "derivada_empty":
                    notice_suffix = "Aviso: nenhuma derivada encontrada para o filtro."
                self.update_filter_status_display(
                    filtered_total=(
                        len(self.df_exibido)
                        if hasattr(self, "df_exibido") and self.df_exibido is not None
                        else None
                    ),
                    original_total=(
                        len(self.df_completo)
                        if hasattr(self, "df_completo") and self.df_completo is not None
                        else None
                    ),
                    search_text=None,
                    suffix=notice_suffix,
                )
        except Exception as exc:
            logger.warning(
                "Falha ao atualizar status com aviso de derivadas apos filtro avancado: %s",
                exc,
            )


def _parse_week(self, raw: str):
    s = str(raw or "").strip()
    if not s:
        return None
    if not s.isdigit():
        return None
    if len(s) != 6:
        return None
    return int(s)


def _get_checked_values(self, source):
    values = []
    if source is None:
        return values
    if isinstance(source, list):
        for child in source:
            try:
                if not _is_widget_valid(child):
                    continue
                if child.isChecked():
                    value = self._checkbox_value(child)
                    if value:
                        values.append(value)
            except Exception as exc:
                logger.debug(
                    "Failed to read checkbox from list source in _get_checked_values: %s",
                    exc,
                )
        return values
    if hasattr(source, "findChildren"):
        try:
            children = source.findChildren(QCheckBox)
        except Exception:
            children = []
        for child in children:
            try:
                if not _is_widget_valid(child):
                    continue
                if child.isChecked():
                    value = self._checkbox_value(child)
                    if value:
                        values.append(value)
            except Exception as exc:
                logger.debug(
                    "Failed to read checkbox from widget source in _get_checked_values: %s",
                    exc,
                )
    return values


def _sync_advanced_filter_ui(self):
    data = self._advanced_filters or {}
    self._sync_multiselect_checks(
        getattr(self, "adv_executor_button", None),
        getattr(self, "adv_executor_checks", None),
        data.get("setor_executor"),
        getattr(self, "adv_executor_exclude_checks", None),
        data.get("setor_executor_exclude_values"),
    )
    self._sync_multiselect_checks(
        getattr(self, "adv_emissor_button", None),
        getattr(self, "adv_emissor_checks", None),
        data.get("setor_emissor"),
        getattr(self, "adv_emissor_exclude_checks", None),
        data.get("setor_emissor_exclude_values"),
    )
    self._sync_multiselect_checks(
        getattr(self, "adv_status_button", None),
        getattr(self, "adv_status_checks", None),
        data.get("situacao"),
        getattr(self, "adv_status_exclude_checks", None),
        data.get("situacao_exclude_values"),
    )
    responsavel_cfg = (
        (
            "adv_responsavel_solicitante",
            "adv_responsavel_solicitante_button",
            "adv_responsavel_solicitante_checks",
            "solicitante",
            "adv_responsavel_solicitante_exclude_checks",
            "solicitante_exclude_values",
        ),
        (
            "adv_responsavel_programacao",
            "adv_responsavel_programacao_button",
            "adv_responsavel_programacao_checks",
            "responsavel_programacao",
            "adv_responsavel_programacao_exclude_checks",
            "responsavel_programacao_exclude_values",
        ),
        (
            "adv_responsavel_execucao",
            "adv_responsavel_execucao_button",
            "adv_responsavel_execucao_checks",
            "responsavel_execucao",
            "adv_responsavel_execucao_exclude_checks",
            "responsavel_execucao_exclude_values",
        ),
    )
    built_prefixes = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    unbuilt_prefixes = set()
    for (
        prefix,
        button_attr,
        checks_attr,
        key_name,
        excl_checks_attr,
        excl_key_name,
    ) in responsavel_cfg:
        if prefix in built_prefixes:
            self._sync_multiselect_checks(
                getattr(self, button_attr, None),
                getattr(self, checks_attr, None),
                data.get(key_name),
                getattr(self, excl_checks_attr, None),
                data.get(excl_key_name),
            )
        else:
            unbuilt_prefixes.add(prefix)
    if unbuilt_prefixes:
        self._sync_responsavel_button_summaries(only_prefixes=unbuilt_prefixes)
    self._sync_multiselect_checks(
        getattr(self, "adv_prioridade_emissao_button", None),
        getattr(self, "adv_prioridade_emissao_checks", None),
        data.get("prioridade_emissao_values"),
        getattr(self, "adv_prioridade_emissao_exclude_checks", None),
        data.get("prioridade_emissao_exclude_values"),
    )
    self._sync_multiselect_checks(
        getattr(self, "adv_prioridade_planejamento_button", None),
        getattr(self, "adv_prioridade_planejamento_checks", None),
        data.get("prioridade_planejamento_values"),
        getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
        data.get("prioridade_planejamento_exclude_values"),
    )
    self._sync_multiselect_checks(
        getattr(self, "adv_reprog_button", None),
        getattr(self, "adv_reprog_checks", None),
        data.get("num_reprogramacoes_values"),
    )
    try:
        reprog_mode = getattr(self, "adv_reprog_mode", None)
        if reprog_mode is not None:
            mode_value = data.get("num_reprogramacoes_mode") or "eq"
            idx = reprog_mode.findData(mode_value)
            if idx < 0:
                idx = reprog_mode.findData("eq")
            if idx >= 0:
                reprog_mode.setCurrentIndex(idx)
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar modo de reprogramacoes nos filtros avancados: %s", exc
        )
    try:
        emissao_values = data.get("ano_emissao_values")
        emissao_exclude = data.get("ano_emissao_exclude_values")
        if emissao_values is None and data.get("ano_emissao") is not None:
            emissao_values = [data.get("ano_emissao")]
        if (
            emissao_exclude is None
            and data.get("ano_emissao_exclude")
            and data.get("ano_emissao") is not None
        ):
            emissao_exclude = [data.get("ano_emissao")]
        self._sync_multiselect_checks(
            getattr(self, "adv_year_emissao_button", None),
            getattr(self, "adv_year_emissao_checks", None),
            emissao_values,
            getattr(self, "adv_year_emissao_exclude_checks", None),
            emissao_exclude,
        )
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar filtro avancado de ano de emissao: %s", exc
        )
    try:
        execucao_values = data.get("ano_execucao_values")
        execucao_exclude = data.get("ano_execucao_exclude_values")
        if execucao_values is None and data.get("ano_execucao") is not None:
            execucao_values = [data.get("ano_execucao")]
        if (
            execucao_exclude is None
            and data.get("ano_execucao_exclude")
            and data.get("ano_execucao") is not None
        ):
            execucao_exclude = [data.get("ano_execucao")]
        self._sync_multiselect_checks(
            getattr(self, "adv_year_execucao_button", None),
            getattr(self, "adv_year_execucao_checks", None),
            execucao_values,
            getattr(self, "adv_year_execucao_exclude_checks", None),
            execucao_exclude,
        )
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar filtro avancado de ano de execucao: %s", exc
        )
    try:
        week_fields = (
            ("adv_week_emissao_start", "semana_emissao_inicio"),
            ("adv_week_emissao_end", "semana_emissao_fim"),
            ("adv_week_execucao_start", "semana_execucao_inicio"),
            ("adv_week_execucao_end", "semana_execucao_fim"),
        )
        for attr, key in week_fields:
            widget = getattr(self, attr, None)
            if widget is None:
                continue
            value = data.get(key)
            widget.setText("" if value is None else str(value))
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar intervalo de semanas dos filtros avancados: %s", exc
        )
    try:
        derivada_selected = []
        if bool(data.get("derivada_has")):
            derivada_selected.append("has")
        if bool(data.get("derivada_all_ste")):
            derivada_selected.append("all_ste")
        if bool(data.get("derivada_is")):
            derivada_selected.append("is")
        self._sync_multiselect_checks(
            getattr(self, "adv_derivada_button", None),
            getattr(self, "adv_derivada_checks", None),
            derivada_selected,
        )
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar toggles de derivadas nos filtros avancados: %s", exc
        )
    try:
        if hasattr(self, "adv_macro_combo"):
            self.adv_macro_combo.blockSignals(True)
            idx = self.adv_macro_combo.findData(data.get("macro_filter"))
            self.adv_macro_combo.setCurrentIndex(max(0, idx))
    except Exception as exc:
        logger.warning(
            "Falha ao sincronizar seletor macro dos filtros avancados: %s", exc
        )
    finally:
        try:
            if hasattr(self, "adv_macro_combo"):
                self.adv_macro_combo.blockSignals(False)
        except Exception as exc:
            logger.debug("Falha ao reativar sinais do seletor macro apos sync: %s", exc)


def _refresh_sector_menus(self, exec_vals, emis_vals, status_vals, filters, apply_cb):
    if hasattr(self, "adv_executor_menu"):
        exec_include, exec_exclude = self._rebuild_multiselect_menu(
            self.adv_executor_button,
            self.adv_executor_menu,
            exec_vals,
            set(filters.get("setor_executor") or []),
            self._on_adv_sector_selection_changed,
            True,
            set(filters.get("setor_executor_exclude_values") or []),
            self._on_adv_sector_exclude_changed,
        )
        self.adv_executor_checks = exec_include
        self.adv_executor_exclude_checks = exec_exclude
    if hasattr(self, "adv_emissor_menu"):
        emis_include, emis_exclude = self._rebuild_multiselect_menu(
            self.adv_emissor_button,
            self.adv_emissor_menu,
            emis_vals,
            set(filters.get("setor_emissor") or []),
            self._on_adv_sector_selection_changed,
            True,
            set(filters.get("setor_emissor_exclude_values") or []),
            self._on_adv_sector_exclude_changed,
        )
        self.adv_emissor_checks = emis_include
        self.adv_emissor_exclude_checks = emis_exclude
    if hasattr(self, "adv_status_menu"):
        status_include, status_exclude = self._rebuild_multiselect_menu(
            self.adv_status_button,
            self.adv_status_menu,
            status_vals,
            set(filters.get("situacao") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_status_button,
                getattr(self, "adv_status_checks", None),
                exclude_checks=getattr(self, "adv_status_exclude_checks", None),
            ),
            True,
            set(filters.get("situacao_exclude_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_status_button,
                getattr(self, "adv_status_checks", None),
                exclude_checks=getattr(self, "adv_status_exclude_checks", None),
            ),
        )
        self.adv_status_checks = status_include
        self.adv_status_exclude_checks = status_exclude


def _refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb):
    if hasattr(self, "adv_year_emissao_menu"):
        inc_vals = filters.get("ano_emissao_values")
        exc_vals = filters.get("ano_emissao_exclude_values")
        if inc_vals is None and filters.get("ano_emissao") is not None:
            inc_vals = [filters.get("ano_emissao")]
        if (
            exc_vals is None
            and filters.get("ano_emissao_exclude")
            and filters.get("ano_emissao") is not None
        ):
            exc_vals = [filters.get("ano_emissao")]
        year_values = [str(y) for y in emissao_years if y and str(y).strip()]
        inc_set = {str(v) for v in (inc_vals or [])}
        exc_set = {str(v) for v in (exc_vals or [])}
        year_include, year_exclude = self._rebuild_multiselect_menu(
            self.adv_year_emissao_button,
            self.adv_year_emissao_menu,
            year_values,
            inc_set,
            lambda *_: self._update_multiselect_button(
                self.adv_year_emissao_button,
                getattr(self, "adv_year_emissao_checks", None),
                exclude_checks=getattr(self, "adv_year_emissao_exclude_checks", None),
            ),
            True,
            exc_set,
            lambda *_: self._update_multiselect_button(
                self.adv_year_emissao_button,
                getattr(self, "adv_year_emissao_checks", None),
                exclude_checks=getattr(self, "adv_year_emissao_exclude_checks", None),
            ),
        )
        self.adv_year_emissao_checks = year_include
        self.adv_year_emissao_exclude_checks = year_exclude
    if hasattr(self, "adv_year_execucao_menu"):
        inc_vals = filters.get("ano_execucao_values")
        exc_vals = filters.get("ano_execucao_exclude_values")
        if inc_vals is None and filters.get("ano_execucao") is not None:
            inc_vals = [filters.get("ano_execucao")]
        if (
            exc_vals is None
            and filters.get("ano_execucao_exclude")
            and filters.get("ano_execucao") is not None
        ):
            exc_vals = [filters.get("ano_execucao")]
        year_values = [str(y) for y in execucao_years if y and str(y).strip()]
        inc_set = {str(v) for v in (inc_vals or [])}
        exc_set = {str(v) for v in (exc_vals or [])}
        year_include, year_exclude = self._rebuild_multiselect_menu(
            self.adv_year_execucao_button,
            self.adv_year_execucao_menu,
            year_values,
            inc_set,
            lambda *_: self._update_multiselect_button(
                self.adv_year_execucao_button,
                getattr(self, "adv_year_execucao_checks", None),
                exclude_checks=getattr(self, "adv_year_execucao_exclude_checks", None),
            ),
            True,
            exc_set,
            lambda *_: self._update_multiselect_button(
                self.adv_year_execucao_button,
                getattr(self, "adv_year_execucao_checks", None),
                exclude_checks=getattr(self, "adv_year_execucao_exclude_checks", None),
            ),
        )
        self.adv_year_execucao_checks = year_include
        self.adv_year_execucao_exclude_checks = year_exclude


def _refresh_reprogramacoes_menu(self, reprog_vals, filters, apply_cb):
    if not hasattr(self, "adv_reprog_menu"):
        return
    values = [str(v) for v in (reprog_vals or []) if str(v).strip()]
    selected = {str(v) for v in (filters.get("num_reprogramacoes_values") or [])}
    try:
        include_checks, _ = self._rebuild_multiselect_menu(
            getattr(self, "adv_reprog_button", None),
            getattr(self, "adv_reprog_menu", None),
            values,
            selected,
            lambda *_: self._update_multiselect_button(
                getattr(self, "adv_reprog_button", None),
                getattr(self, "adv_reprog_checks", None),
            ),
            True,
            None,
            None,
        )
        self.adv_reprog_checks = include_checks
    except Exception as exc:
        logger.debug(
            "Failed to rebuild reprogramacoes menu in advanced filter UI: %s", exc
        )
        self.adv_reprog_checks = []
    try:
        mode_combo = getattr(self, "adv_reprog_mode", None)
        if mode_combo is not None:
            mode = filters.get("num_reprogramacoes_mode") or "eq"
            idx = mode_combo.findData(mode)
            if idx < 0:
                idx = mode_combo.findData("eq")
            if idx >= 0:
                mode_combo.setCurrentIndex(idx)
    except Exception as exc:
        logger.debug(
            "Failed to restore reprogramacoes mode in advanced filter UI: %s", exc
        )


def _collect_derivadas_selected_from_checks(self):
    selected = set()
    for value in self._get_checked_values(getattr(self, "adv_derivada_checks", None)):
        norm = str(value or "").strip().casefold()
        if norm in {"has", "all_ste", "is"}:
            selected.add(norm)
    return selected


def _refresh_derivadas_menu(self, filters, apply_cb, selected_override=None):
    if not hasattr(self, "adv_derivada_menu"):
        return
    deriv_values = [
        ("has", "Possui Derivadas"),
        ("all_ste", _DERIVADA_ALL_STE_LABEL),
        ("is", "Sou Derivada"),
    ]
    selected = set()
    if isinstance(selected_override, (set, list, tuple)):
        selected = {
            str(v).strip().casefold()
            for v in selected_override
            if str(v).strip().casefold() in {"has", "all_ste", "is"}
        }
    if not selected:
        if bool(filters.get("derivada_has")):
            selected.add("has")
        if bool(filters.get("derivada_all_ste")):
            selected.add("all_ste")
        if bool(filters.get("derivada_is")):
            selected.add("is")
    try:
        include_checks, _ = self._rebuild_multiselect_menu(
            getattr(self, "adv_derivada_button", None),
            getattr(self, "adv_derivada_menu", None),
            deriv_values,
            selected,
            lambda *_: self._update_multiselect_button(
                getattr(self, "adv_derivada_button", None),
                getattr(self, "adv_derivada_checks", None),
            ),
            True,
            None,
            None,
        )
        self.adv_derivada_checks = include_checks
    except Exception as exc:
        logger.debug("Failed to rebuild derivadas menu in advanced filter UI: %s", exc)
        self.adv_derivada_checks = []


def _refresh_priority_menus(
    self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
):
    if hasattr(self, "adv_prioridade_emissao_menu"):
        prio_include, prio_exclude = self._rebuild_multiselect_menu(
            self.adv_prioridade_emissao_button,
            self.adv_prioridade_emissao_menu,
            prio_emissao_vals,
            set(filters.get("prioridade_emissao_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_emissao_button,
                getattr(self, "adv_prioridade_emissao_checks", None),
                exclude_checks=getattr(
                    self, "adv_prioridade_emissao_exclude_checks", None
                ),
            ),
            True,
            set(filters.get("prioridade_emissao_exclude_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_emissao_button,
                getattr(self, "adv_prioridade_emissao_checks", None),
                exclude_checks=getattr(
                    self, "adv_prioridade_emissao_exclude_checks", None
                ),
            ),
        )
        self.adv_prioridade_emissao_checks = prio_include
        self.adv_prioridade_emissao_exclude_checks = prio_exclude
    if hasattr(self, "adv_prioridade_planejamento_menu"):
        prio_include, prio_exclude = self._rebuild_multiselect_menu(
            self.adv_prioridade_planejamento_button,
            self.adv_prioridade_planejamento_menu,
            prio_planejamento_vals,
            set(filters.get("prioridade_planejamento_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_planejamento_button,
                getattr(self, "adv_prioridade_planejamento_checks", None),
                exclude_checks=getattr(
                    self, "adv_prioridade_planejamento_exclude_checks", None
                ),
            ),
            True,
            set(filters.get("prioridade_planejamento_exclude_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_planejamento_button,
                getattr(self, "adv_prioridade_planejamento_checks", None),
                exclude_checks=getattr(
                    self, "adv_prioridade_planejamento_exclude_checks", None
                ),
            ),
        )
        self.adv_prioridade_planejamento_checks = prio_include
        self.adv_prioridade_planejamento_exclude_checks = prio_exclude


def _refresh_advanced_filter_options(self):
    """Atualiza opcoes de filtros avancados com cache granular otimizado."""
    if self.df_completo is None or self.df_completo.empty:
        logger.debug("_refresh_advanced_filter_options: df_completo vazio ou None")
        return
    start = perf_counter()
    df = self.df_completo
    logger.debug(
        "_refresh_advanced_filter_options: iniciando com %s registros", len(df)
    )
    filters = self._advanced_filters or {}

    def apply_cb():
        return self._apply_advanced_filters_from_ui()

    # Cache granular: permite invalidacao parcial por tipo de filtro
    cache = getattr(self, "_adv_values_cache", None)
    df_key = (
        len(df),
        tuple(df.columns),
        getattr(self, "_data_load_token", None),
    )

    # Verifica se pode reutilizar cache completo
    if (
        cache
        and cache.get("df_key") == df_key
        and not getattr(self, "_adv_options_dirty", False)
    ):
        _refresh_derivadas_menu(self, filters, apply_cb)
        self._adv_options_scheduled = False
        return

    df_id = id(df)

    # Inicializa cache granular se necessário
    if not isinstance(cache, dict) or cache.get("df_id") != df_id:
        cache = {"df_id": df_id, "df_key": df_key}
        self._adv_values_cache = cache

    # Popula cache se necessário (bloco único consolidado) - CORRIGIDO: removida duplicação
    if cache.get("exec_vals") is None:
        _populate_advanced_values_cache(self, df, cache)
        self._adv_values_cache = cache
        logger.debug(
            "_refresh_advanced_filter_options: cache populado - exec=%s, emis=%s, status=%s",
            _safe_len(cache.get("exec_vals", [])),
            _safe_len(cache.get("emis_vals", [])),
            _safe_len(cache.get("status_vals", [])),
        )

    exec_vals = cache.get("exec_vals", [])
    emis_vals = cache.get("emis_vals", [])
    status_vals = cache.get("status_vals", [])
    emissao_years = cache.get("emissao_years", [])
    execucao_years = cache.get("execucao_years", [])
    prio_emissao_vals = cache.get("prio_emissao_vals", [])
    prio_planejamento_vals = cache.get("prio_planejamento_vals", [])
    self._refresh_sector_menus(exec_vals, emis_vals, status_vals, filters, apply_cb)
    self._refresh_year_menus(emissao_years, execucao_years, filters, apply_cb)
    self._refresh_priority_menus(
        prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
    )
    self._refresh_reprogramacoes_menu(cache.get("reprog_vals", []), filters, apply_cb)
    _refresh_derivadas_menu(self, filters, apply_cb)

    self._mark_responsavel_dirty()
    built_prefixes = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    if built_prefixes:
        self._refresh_responsavel_options(target_prefixes=built_prefixes)
    else:
        self._sync_responsavel_button_summaries()
    self._sync_checks_to_tab_context()
    self._sync_advanced_filter_ui()
    try:
        elapsed_ms = (perf_counter() - start) * 1000.0
        logger.debug("Advanced filter options refresh: %.1fms", elapsed_ms)
    except Exception as exc:
        logger.debug("Failed to log advanced filter options refresh timing: %s", exc)
    self._adv_options_scheduled = False
