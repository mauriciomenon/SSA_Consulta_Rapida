# gui/ssa/gui_filters_advanced_ui.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: builds advanced filters UI and menu wiring.
# Relation: does not apply DataFrame filters directly.

from __future__ import annotations

from time import perf_counter
from typing import Any

import pandas as pd

from gui.qt_stubs import (
    sip,
    Qt,
    QSignalBlocker,
    QApplication,
    QComboBox,
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
from utils.robust_logging import get_robust_logger
from .gui_filters_advanced_state import DIVISAO_SETORES, SECTOR_TO_DIV

logger = get_robust_logger().get_logger(__name__, "gui")

# Layout breakpoint constants for advanced filters responsive grid
LAYOUT_WIDE_MIN_WIDTH = 1050  # px
LAYOUT_MID_MIN_WIDTH = 650  # px


def _is_widget_valid(widget) -> bool:
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except Exception:
        return False


def _safe_is_checked(widget: Any) -> bool:
    try:
        return bool(widget is not None and widget.isChecked())
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


def _make_multiselect_box(self, title: str, placeholder: str = "Selecionar", with_exclude: bool = True):
    box = QGroupBox(title)
    layout = QHBoxLayout(box)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(2)
    button = QToolButton()
    button.setText(placeholder)
    try:
        button.setMaximumWidth(100)
    except Exception as exc:
        logger.debug("Falha ao definir largura maxima do botao multiselect '%s': %s", title, exc)
    try:
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug("Falha ao definir size policy do botao multiselect '%s': %s", title, exc)
    menu = QMenu(button)
    try:
        menu.setMaximumHeight(360)
    except Exception as exc:
        logger.debug("Falha ao definir altura maxima do menu multiselect '%s': %s", title, exc)
    self._attach_multiselect_menu(button, menu)
    button.setToolTip(placeholder)
    try:
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    except Exception as exc:
        logger.debug("Falha ao definir size policy do groupbox multiselect '%s': %s", title, exc)
    exclude = None
    if with_exclude:
        exclude = QCheckBox("Diferente")
        try:
            exclude.setVisible(False)
        except Exception as exc:
            logger.debug("Falha ao ocultar checkbox de exclusao no multiselect '%s': %s", title, exc)
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
        logger.debug("Falha ao ler estado atual de checkbox em _set_checkbox_checked_quietly: %s", exc)
        desired = bool(checked)
    used_signal_blocker = False
    try:
        QSignalBlocker(checkbox)
        used_signal_blocker = True
    except Exception:
        try:
            checkbox.blockSignals(True)
        except Exception as exc:
            logger.debug("Falha ao bloquear sinais de checkbox sem QSignalBlocker: %s", exc)
    changed = False
    try:
        checkbox.setChecked(desired)
        changed = True
    except Exception as exc:
        logger.debug("Falha ao atualizar checkbox em _set_checkbox_checked_quietly: %s", exc)
        changed = False
    finally:
        if not used_signal_blocker:
            try:
                checkbox.blockSignals(False)
            except Exception as exc:
                logger.debug("Falha ao restaurar sinais de checkbox sem QSignalBlocker: %s", exc)
    return changed

def _sync_responsavel_flags(self) -> None:
    all_prefixes = set(getattr(self, "_responsavel_all_prefixes", ()))
    dirty = set(getattr(self, "_responsavel_dirty_prefixes", set()))
    built = set(getattr(self, "_responsavel_materialized_prefixes", set()))
    self._responsavel_filters_materialized = bool(all_prefixes) and all_prefixes.issubset(built)
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
        logger.warning("Falha no refresh de responsaveis apos debounce de setor: %s", exc)

def _ensure_responsavel_options_materialized(self, target_prefix: str | None = None, force: bool = False) -> None:
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
        if button is None:
            continue
        include_values = [str(v) for v in (filters.get(include_key) or []) if str(v).strip()]
        exclude_values = [str(v) for v in (filters.get(exclude_key) or []) if str(v).strip()]
        if include_values and exclude_values:
            text = f"{len(include_values)} inc, {len(exclude_values)} dif"
        elif include_values:
            text = f"{len(include_values)} incluir"
        elif exclude_values:
            text = f"{len(exclude_values)} diferente"
        else:
            text = "Selecionar"
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
            logger.debug("Falha ao sincronizar resumo de botao de responsavel (%s): %s", button_attr, exc)

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
                screen = QApplication.primaryScreen().geometry()
                if menu_size and screen and pos.y() + menu_size.height() > screen.bottom():
                    pos = button.mapToGlobal(rect.topLeft())
                    pos.setY(pos.y() - menu_size.height())
            except Exception as exc:
                logger.debug("Falha ao ajustar posicao do menu multiselect na tela: %s", exc)
            menu.exec(pos)
            return
        except Exception as exc:
            logger.warning("Falha ao abrir menu multiselect: %s", exc)
    try:
        button.clicked.connect(_show_menu)
    except Exception as exc:
        logger.warning("Falha ao conectar abertura de menu multiselect: %s", exc)

def _update_multiselect_button(self, button, checks, placeholder: str = "Selecionar", exclude_checks=None):
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
            logger.debug("Failed to read include checkbox state in multiselect summary: %s", exc)
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
            logger.debug("Failed to read exclude checkbox state in multiselect summary: %s", exc)
    total = len(checks or [])
    if total == 0:
        text = "Sem dados"
    elif not selected and not excluded:
        text = placeholder
    elif len(selected) == total and not excluded:
        text = "Todos"
    elif selected and excluded:
        text = f"{len(selected)} inc, {len(excluded)} dif"
    elif selected:
        text = f"{len(selected)} incluir"
    elif excluded:
        text = f"{len(excluded)} diferente"
    else:
        text = f"{len(selected)} selecionados"
    try:
        button.setText(text)
        # Esmaecimento visual para botoes sem dados
        if total == 0:
            button.setEnabled(False)
            button.setStyleSheet("color: #888; background-color: #f0f0f0;")
        else:
            button.setEnabled(True)
            button.setStyleSheet("")  # Remove estilo customizado
        if selected or excluded:
            button.setToolTip(
                "Incluir: " + ", ".join(selected) + ("\nDiferente: " + ", ".join(excluded) if excluded else "")
            )
        else:
            button.setToolTip(placeholder if total > 0 else "Nenhum dado disponivel")
    except Exception as exc:
        logger.debug("Falha ao atualizar resumo/tooltip do botao multiselect: %s", exc)

def _rebuild_multiselect_menu(
    self,
    button,
    menu,
    values,
    selected_set,
    on_toggle=None,
    on_apply=None,
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
    filter_name = ""
    try:
        parent = button.parent()
        seen = set()
        for _ in range(50):
            if parent is None:
                break
            pid = id(parent)
            if pid in seen:
                logger.debug("Ciclo detectado ao subir parent() no menu multiselect; abortando.")
                break
            seen.add(pid)
            if isinstance(parent, QGroupBox):
                candidate = parent.title()
                # Ignorar titulos genericos como "Valores"
                if candidate and candidate not in ("Valores", ""):
                    filter_name = candidate
                    break
            parent = parent.parent()
    except Exception as exc:
        logger.debug("Falha ao detectar nome do filtro para menu multiselect: %s", exc)

    try:
        try:
            max_label_len = max((len(str(v)) for v in values), default=4)
        except Exception:
            max_label_len = 4
        computed = max_label_len * 8 + 70
        min_width = max(int(getattr(button, "width", lambda: 0)() or 0), min(360, max(160, computed)))
        menu.setMinimumWidth(min_width)
    except Exception as exc:
        logger.debug("Falha ao ajustar largura minima do menu multiselect: %s", exc)

    container = QWidget()
    grid = QGridLayout(container)
    grid.setContentsMargins(6, 4, 14, 4)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(4)
    try:
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar grid do menu multiselect no topo: %s", exc)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 0)
    grid.setColumnStretch(2, 0)
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
            label_inc = QLabel("==")
            label_exc = QLabel("!=")
            try:
                # == com destaque (borda), != sem destaque (invertido conforme solicitado)
                label_inc.setStyleSheet("font-size: 10px; color: #888; border: 1px solid #aaa; border-radius: 2px; padding: 1px 3px;")
                label_exc.setStyleSheet("font-size: 10px; color: #555;")
                label_inc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                label_exc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            except Exception as exc:
                logger.debug("Falha ao estilizar header include/exclude do menu multiselect: %s", exc)
            grid.addWidget(label_inc, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
            grid.addWidget(label_exc, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
        row_idx += 1

        # Separador entre header e conteudo
        header_sep = QFrame()
        header_sep.setFrameShape(QFrame.Shape.HLine)
        header_sep.setFrameShadow(QFrame.Shadow.Sunken)
        col_span = 3 if exclude_selected_set is not None else 1
        grid.addWidget(header_sep, row_idx, 0, 1, col_span)
        row_idx += 1

    # Estilo para checkboxes com indicacao visual clara quando marcados
    # CORRECAO 2026-01-08: Adicionado estilo :checked para feedback visual
    cb_style_include = """
        QCheckBox::indicator {
            background-color: #f0f0f0;
            border: 1px solid #888;
            border-radius: 2px;
            width: 13px;
            height: 13px;
        }
        QCheckBox::indicator:checked {
            background-color: #4a90d9;
            border: 1px solid #2a70b9;
            image: none;
        }
    """
    cb_style_exclude = """
        QCheckBox::indicator {
            background-color: #f5f5f5;
            border: 1px solid #bbb;
            border-radius: 2px;
            width: 13px;
            height: 13px;
        }
        QCheckBox::indicator:checked {
            background-color: #d94a4a;
            border: 1px solid #b92a2a;
            image: none;
        }
    """

    for val in values:
        label_text = str(val[1]) if isinstance(val, (list, tuple)) and len(val) > 1 else str(val)
        cb_value = val[0] if isinstance(val, (list, tuple)) and len(val) > 0 else val
        # Ignorar valores vazios ou apenas espacos
        if not label_text or not label_text.strip():
            continue
        label = QLabel(label_text)
        try:
            label.setStyleSheet("font-size: 11px;")
        except Exception as exc:
            logger.debug("Falha ao estilizar label do item no menu multiselect: %s", exc)
        include_cb = QCheckBox()
        exclude_cb = QCheckBox() if exclude_selected_set is not None else None
        try:
            include_cb.setProperty("value", str(cb_value))
            include_cb.setStyleSheet(cb_style_include)
        except Exception as exc:
            logger.debug("Falha ao configurar checkbox include do menu multiselect: %s", exc)
        if exclude_cb is not None:
            try:
                exclude_cb.setProperty("value", str(cb_value))
                exclude_cb.setStyleSheet(cb_style_exclude)
            except Exception as exc:
                logger.debug("Falha ao configurar checkbox exclude do menu multiselect: %s", exc)
        try:
            include_cb.setChecked(str(cb_value).casefold() in selected_norm)
        except Exception as exc:
            logger.debug("Falha ao aplicar estado inicial do checkbox include: %s", exc)
        if exclude_cb is not None:
            try:
                exclude_cb.setChecked(str(cb_value).casefold() in exclude_norm)
            except Exception as exc:
                logger.debug("Falha ao aplicar estado inicial do checkbox exclude: %s", exc)
        grid.addWidget(label, row_idx, 0)
        grid.addWidget(include_cb, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        if exclude_cb is not None:
            grid.addWidget(exclude_cb, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
        row_idx += 1
        checks.append(include_cb)
        if exclude_cb is not None:
            exclude_checks.append(exclude_cb)
        if exclude_cb is not None:
            def _toggle_include(checked, other=exclude_cb):
                if checked and _is_widget_valid(other) and other.isChecked():
                    other.blockSignals(True)
                    other.setChecked(False)
                    other.blockSignals(False)
            def _toggle_exclude(checked, other=include_cb):
                if checked and _is_widget_valid(other) and other.isChecked():
                    other.blockSignals(True)
                    other.setChecked(False)
                    other.blockSignals(False)
            try:
                include_cb.toggled.connect(_toggle_include)
                exclude_cb.toggled.connect(_toggle_exclude)
            except Exception as exc:
                logger.warning("Falha ao conectar mutual exclusion include/exclude no menu multiselect: %s", exc)
        if on_toggle is not None:
            try:
                include_cb.toggled.connect(on_toggle)
            except Exception as exc:
                logger.warning("Falha ao conectar callback on_toggle do menu multiselect: %s", exc)
        if exclude_cb is not None and on_exclude_toggle is not None:
            try:
                exclude_cb.toggled.connect(on_exclude_toggle)
            except Exception as exc:
                logger.warning("Falha ao conectar callback on_exclude_toggle do menu multiselect: %s", exc)

    # Separador antes de Selecionar/Desmarcar
    if exclude_selected_set is not None:
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(separator, row_idx, 0, 1, 3)
        row_idx += 1

        # Selecionar/Desmarcar ao fim da lista
        select_all_include = QCheckBox()
        deselect_all_include = QCheckBox()
        select_all_exclude = QCheckBox()
        deselect_all_exclude = QCheckBox()

        for cb in [select_all_include, deselect_all_include]:
            cb.setStyleSheet(cb_style_include)
        for cb in [select_all_exclude, deselect_all_exclude]:
            cb.setStyleSheet(cb_style_exclude)

        label_select = QLabel("Selecionar tudo")
        label_deselect = QLabel("Desmarcar tudo")
        try:
            label_select.setStyleSheet("font-size: 11px;")
            label_deselect.setStyleSheet("font-size: 11px;")
        except Exception as exc:
            logger.debug("Falha ao estilizar labels de selecionar/desmarcar no menu multiselect: %s", exc)

        grid.addWidget(label_select, row_idx, 0)
        grid.addWidget(select_all_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(select_all_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
        row_idx += 1

        grid.addWidget(label_deselect, row_idx, 0)
        grid.addWidget(deselect_all_include, row_idx, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(deselect_all_exclude, row_idx, 2, alignment=Qt.AlignmentFlag.AlignHCenter)
        row_idx += 1

    scroll = QScrollArea()
    scroll.setWidget(container)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    try:
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
    except Exception as exc:
        logger.debug("Falha ao alinhar scroll do menu multiselect no topo: %s", exc)
    try:
        from PyQt6.QtGui import QPalette as _QPal
        pal = (button or scroll).palette()
        border = pal.color(_QPal.ColorRole.Mid).name()
        bg = pal.color(_QPal.ColorRole.Base).name()
        container.setStyleSheet(f"QWidget {{ background: {bg}; }} QLabel {{ font-size: 11px; }}")
        scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {border}; }}")
    except Exception as exc:
        logger.debug("Falha ao aplicar estilo visual do scroll/menu multiselect: %s", exc)
    try:
        scroll.setFixedHeight(320)
    except Exception as exc:
        logger.debug("Falha ao aplicar altura fixa do scroll no menu multiselect: %s", exc)
    scroll_act = QWidgetAction(menu)
    scroll_act.setDefaultWidget(scroll)
    try:
        menu.addAction(scroll_act)
    except Exception as exc:
        logger.debug("Falha ao adicionar scroll action no menu multiselect: %s", exc)

    # Conectar funcionalidade de Selecionar/Desmarcar Tudo com blockSignals
    # CORRECAO 2026-01-08: Reset do checkbox apos acao para feedback visual correto
    if exclude_selected_set is not None:
        def _select_all_include():
            for cb in checks:
                if not _is_widget_valid(cb):
                    continue
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
            # Reset checkbox de acao apos executar
            select_all_include.blockSignals(True)
            select_all_include.setChecked(False)
            select_all_include.blockSignals(False)
            if on_toggle:
                on_toggle()

        def _deselect_all_include():
            for cb in checks:
                if not _is_widget_valid(cb):
                    continue
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
            # Reset checkbox de acao apos executar
            deselect_all_include.blockSignals(True)
            deselect_all_include.setChecked(False)
            deselect_all_include.blockSignals(False)
            if on_toggle:
                on_toggle()

        def _select_all_exclude():
            for cb in exclude_checks:
                if not _is_widget_valid(cb):
                    continue
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
            # Reset checkbox de acao apos executar
            select_all_exclude.blockSignals(True)
            select_all_exclude.setChecked(False)
            select_all_exclude.blockSignals(False)
            if on_exclude_toggle:
                on_exclude_toggle()

        def _deselect_all_exclude():
            for cb in exclude_checks:
                if not _is_widget_valid(cb):
                    continue
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
            # Reset checkbox de acao apos executar
            deselect_all_exclude.blockSignals(True)
            deselect_all_exclude.setChecked(False)
            deselect_all_exclude.blockSignals(False)
            if on_exclude_toggle:
                on_exclude_toggle()

        try:
            select_all_include.toggled.connect(lambda checked: _select_all_include() if checked else None)
            deselect_all_include.toggled.connect(lambda checked: _deselect_all_include() if checked else None)
            select_all_exclude.toggled.connect(lambda checked: _select_all_exclude() if checked else None)
            deselect_all_exclude.toggled.connect(lambda checked: _deselect_all_exclude() if checked else None)
        except Exception as exc:
            logger.debug("Failed to connect select-all toggles in multiselect menu: %s", exc)

    # Botoes OK e Cancelar - OK sempre a direita
    # OTIMIZACAO 2026-01-08: OK apenas fecha o menu, NAO aplica filtro
    # A aplicacao fica para o botao "Aplicar" geral (evita recalculagens por toggle)
    if on_apply is not None:
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFixedWidth(70)
        cancel_btn.setToolTip("Fechar sem aplicar")
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(70)
        ok_btn.setToolTip("Confirmar selecao (use botao Aplicar para filtrar)")
        try:
            cancel_btn.clicked.connect(menu.close)
        except Exception as exc:
            logger.debug("Falha ao conectar botao Cancelar no menu multiselect: %s", exc)
        try:
            ok_btn.clicked.connect(menu.close)
            # REMOVIDO: ok_btn.clicked.connect(on_apply)
            # Agora o filtro so e aplicado pelo botao "Aplicar" geral
        except Exception as exc:
            logger.debug("Falha ao conectar botao OK no menu multiselect: %s", exc)
        ok_row = QWidget()
        ok_layout = QHBoxLayout(ok_row)
        ok_layout.setContentsMargins(6, 4, 6, 6)
        ok_layout.addStretch()
        ok_layout.addWidget(cancel_btn)
        ok_layout.addSpacing(8)
        ok_layout.addWidget(ok_btn)
        ok_act = QWidgetAction(menu)
        ok_act.setDefaultWidget(ok_row)
        try:
            menu.addAction(ok_act)
        except Exception as exc:
            logger.debug("Falha ao adicionar rodape de acoes no menu multiselect: %s", exc)
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
        logger.debug("Falha ao obter propriedade 'value' do checkbox em _checkbox_value: %s", exc)
    return ""

def _sync_multiselect_checks(self, button, checks, selected, exclude_checks=None, exclude_selected=None):
    selected_set = {str(v).casefold() for v in (selected or [])}
    for cb in checks or []:
        try:
            cb.setChecked(self._checkbox_value(cb).casefold() in selected_set)
        except Exception as exc:
            logger.debug("Falha ao sincronizar checkbox include em multiselect: %s", exc)
    exclude_set = {str(v).casefold() for v in (exclude_selected or [])}
    for cb in exclude_checks or []:
        try:
            cb.setChecked(self._checkbox_value(cb).casefold() in exclude_set)
        except Exception as exc:
            logger.debug("Falha ao sincronizar checkbox exclude em multiselect: %s", exc)
    self._update_multiselect_button(button, checks, exclude_checks=exclude_checks)

def _build_advanced_filters_panel(self):
    group = QGroupBox("Filtros Avancados")
    outer = QVBoxLayout(group)
    outer.setContentsMargins(2, 2, 2, 2)
    outer.setSpacing(2)

    grid_container = QWidget()
    grid_container_layout = QVBoxLayout(grid_container)
    grid_container_layout.setContentsMargins(0, 0, 0, 0)
    grid_container_layout.setSpacing(0)

    emis_box, emis_button, emis_menu, emis_exclude = self._make_multiselect_box("Emissor")
    exec_box, exec_button, exec_menu, exec_exclude = self._make_multiselect_box("Executor")
    status_box, status_button, status_menu, status_exclude = self._make_multiselect_box("Situacao")
    year_emissao_box, year_emissao_button, year_emissao_menu, _ = self._make_multiselect_box(
        "Ano Emissao",
        with_exclude=False,
    )
    year_execucao_box, year_execucao_button, year_execucao_menu, _ = self._make_multiselect_box(
        "Ano Execucao",
        with_exclude=False,
    )

    reprog_box = QGroupBox("Reprogramacoes")
    reprog_layout = QHBoxLayout(reprog_box)
    reprog_layout.setContentsMargins(2, 1, 2, 1)
    reprog_layout.setSpacing(2)
    reprog_mode = QComboBox()
    reprog_mode.addItem("= Igual", "eq")
    reprog_mode.addItem("<= Menor", "lte")
    reprog_mode.addItem(">= Maior", "gte")
    try:
        reprog_mode.setFixedWidth(90)
    except Exception as exc:
        logger.debug("Falha ao definir largura fixa do seletor de reprogramacoes: %s", exc)
    reprog_layout.addWidget(reprog_mode)
    reprog_menu_box, reprog_button, reprog_menu, _ = self._make_multiselect_box("Valores", with_exclude=False)
    try:
        reprog_button.setFixedWidth(90)
    except Exception as exc:
        logger.debug("Falha ao definir largura fixa do botao de reprogramacoes: %s", exc)
    reprog_layout.addWidget(reprog_button, 1)
    self.adv_reprog_mode = reprog_mode
    self.adv_reprog_button = reprog_button
    self.adv_reprog_menu = reprog_menu
    self.adv_reprog_checks = []

    prio_emis_box, prio_emis_button, prio_emis_menu, _ = self._make_multiselect_box("Prio. Emissao")
    prio_plan_box, prio_plan_button, prio_plan_menu, _ = self._make_multiselect_box("Prio. Planejamento")

    deriv_box = QGroupBox("Derivadas")
    deriv_layout = QHBoxLayout(deriv_box)
    deriv_layout.setContentsMargins(2, 1, 2, 1)
    deriv_layout.setSpacing(4)
    deriv_has = QCheckBox("Tem")
    deriv_all_ste = QCheckBox("STE")
    deriv_is = QCheckBox("Sou Derivada")
    try:
        deriv_has.toggled.connect(lambda checked: self._on_derivada_has_toggled(checked))
        deriv_all_ste.toggled.connect(lambda checked: self._on_derivada_all_ste_toggled(checked))
    except Exception as exc:
        logger.debug("Falha ao conectar handlers de filtros de derivadas: %s", exc)
    deriv_layout.addWidget(deriv_has)
    deriv_layout.addWidget(deriv_all_ste)
    deriv_layout.addWidget(deriv_is)
    deriv_layout.addStretch()

    week_emis_box = QGroupBox("Emissao (AnoSemana)")
    week_emis_layout = QHBoxLayout(week_emis_box)
    week_emis_layout.setContentsMargins(2, 1, 2, 1)
    week_emis_layout.setSpacing(2)
    week_emissao_start = QLineEdit()
    week_emissao_start.setPlaceholderText("Ini")
    try:
        week_emissao_start.setMaxLength(6)
        week_emissao_start.setFixedWidth(64)
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana inicial de emissao: %s", exc)
    week_emissao_end = QLineEdit()
    week_emissao_end.setPlaceholderText("Fim")
    try:
        week_emissao_end.setMaxLength(6)
        week_emissao_end.setFixedWidth(64)
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana final de emissao: %s", exc)
    week_emissao_exclude = None
    week_emis_layout.addWidget(week_emissao_start)
    week_emis_layout.addWidget(week_emissao_end)

    week_exec_box = QGroupBox("Execucao (AnoSemana)")
    week_exec_layout = QHBoxLayout(week_exec_box)
    week_exec_layout.setContentsMargins(2, 1, 2, 1)
    week_exec_layout.setSpacing(2)
    week_exec_start = QLineEdit()
    week_exec_start.setPlaceholderText("Ini")
    try:
        week_exec_start.setMaxLength(6)
        week_exec_start.setFixedWidth(64)
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana inicial de execucao: %s", exc)
    week_exec_end = QLineEdit()
    week_exec_end.setPlaceholderText("Fim")
    try:
        week_exec_end.setMaxLength(6)
        week_exec_end.setFixedWidth(64)
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana final de execucao: %s", exc)
    week_exec_exclude = None
    week_exec_layout.addWidget(week_exec_start)
    week_exec_layout.addWidget(week_exec_end)

    macro_box = QGroupBox("Macro")
    macro_layout = QHBoxLayout(macro_box)
    macro_layout.setContentsMargins(2, 1, 2, 1)
    macro_combo = QComboBox()
    try:
        macro_combo.setMinimumWidth(100)
    except Exception as exc:
        logger.debug("Falha ao definir largura minima do filtro macro: %s", exc)
    macro_combo.addItem("Nenhum", None)
    macro_combo.addItem("Baixar", "ssas_para_baixar")
    macro_combo.currentIndexChanged.connect(self._on_macro_filter_changed)
    macro_layout.addWidget(macro_combo)

    sol_box, sol_button, sol_menu, sol_exclude = self._make_multiselect_box("Solicitante")
    prog_box, prog_button, prog_menu, prog_exclude = self._make_multiselect_box("Resp Prog")
    exec_resp_box, exec_resp_button, exec_resp_menu, exec_resp_exclude = self._make_multiselect_box("Resp Exec")
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
    main_grid.setHorizontalSpacing(8)
    main_grid.setVerticalSpacing(8)
    main_grid.addWidget(emis_box, 0, 0)
    main_grid.addWidget(exec_box, 0, 1)
    main_grid.addWidget(status_box, 0, 2)
    main_grid.addWidget(year_emissao_box, 0, 3)
    main_grid.addWidget(year_execucao_box, 0, 4)
    main_grid.addWidget(reprog_box, 1, 0)
    main_grid.addWidget(prio_emis_box, 1, 1)
    main_grid.addWidget(prio_plan_box, 1, 2)
    main_grid.addWidget(macro_box, 1, 3)
    main_grid.addWidget(deriv_box, 1, 4)
    main_grid.addWidget(week_emis_box, 2, 0)
    main_grid.addWidget(week_exec_box, 2, 1)
    main_grid.addWidget(sol_box, 2, 2)
    main_grid.addWidget(prog_box, 2, 3)
    main_grid.addWidget(exec_resp_box, 2, 4)
    for col in range(5):
        main_grid.setColumnStretch(col, 1)

    grid_container_layout.addLayout(main_grid)
    outer.addWidget(grid_container, 1)

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
    }

    buttons_row = QHBoxLayout()
    buttons_row.setContentsMargins(0, 2, 0, 0)
    apply_btn = QPushButton("Aplicar")
    clear_btn = QPushButton("Limpar")
    try:
        apply_btn.setMinimumWidth(116)
        clear_btn.setMinimumWidth(116)
        apply_btn.setStyleSheet("font-weight: 600; padding: 4px 12px;")
        clear_btn.setStyleSheet("padding: 4px 12px;")
    except Exception as exc:
        logger.debug("Falha ao estilizar botoes de acao dos filtros avancados: %s", exc)
    apply_btn.clicked.connect(self._apply_advanced_filters_from_ui)
    clear_btn.clicked.connect(self._clear_advanced_filters)
    buttons_row.addStretch()
    buttons_row.addWidget(apply_btn)
    buttons_row.addSpacing(8)
    buttons_row.addWidget(clear_btn)

    outer.addLayout(buttons_row)

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
        "adv_derivada_has": deriv_has,
        "adv_derivada_all_ste": deriv_all_ste,
        "adv_derivada_is": deriv_is,
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

def _on_derivada_has_toggled(self, checked: bool):
    """Quando 'Tem' é desmarcado, 'STE' também deve ser desmarcado."""
    if not checked:
        try:
            if hasattr(self, "adv_derivada_all_ste") and self.adv_derivada_all_ste.isChecked():
                self.adv_derivada_all_ste.setChecked(False)
        except Exception as exc:
            logger.debug("Falha ao desmarcar filtro derivada STE ao desabilitar 'Tem': %s", exc)

def _on_derivada_all_ste_toggled(self, checked: bool):
    if not checked:
        return
    try:
        if hasattr(self, "adv_derivada_has"):
            self.adv_derivada_has.setChecked(True)
    except Exception as exc:
        logger.debug("Falha ao forcar 'Tem derivada' quando STE foi marcado: %s", exc)

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
            if hasattr(self, "adv_derivada_has"):
                self.adv_derivada_has.setChecked(True)
            if hasattr(self, "adv_derivada_all_ste"):
                self.adv_derivada_all_ste.setChecked(True)
        except Exception as exc:
            logger.warning("Falha ao aplicar preset de derivadas no macro filtro: %s", exc)
        try:
            self._sync_multiselect_checks(
                getattr(self, "adv_status_button", None),
                getattr(self, "adv_status_checks", None),
                [],
                getattr(self, "adv_status_exclude_checks", None),
                ["STE", "SCA"],
            )
        except Exception as exc:
            logger.warning("Falha ao aplicar preset de status no macro filtro: %s", exc)
        try:
            if hasattr(self, "adv_executor_button"):
                self.adv_executor_button.showMenu()
        except Exception as exc:
            logger.debug("Falha ao abrir menu de executor apos macro filtro: %s", exc)
    self._apply_advanced_filters_from_ui()

def _reorganize_advanced_filters_grid(self, width: int):
    """Reorganiza grid de filtros avancados baseado na largura disponivel."""
    if not hasattr(self, "_adv_filters_main_grid") or not hasattr(self, "_adv_filters_grid_widgets"):
        return

    # Guard clause para evitar layout colapsado durante inicializacao ou resize minimo (ex: hidden)
    if width < 100:
        return

    # Otimizacao de breakpoints para evitar layout vertical (narrow) em telas comuns
    # Wide (>1050): 5 colunas
    # Mid (>650): 3 colunas
    # Narrow (<=650): 2 colunas
    mode = "wide" if width > LAYOUT_WIDE_MIN_WIDTH else "mid" if width > LAYOUT_MID_MIN_WIDTH else "narrow"

    if getattr(self, "_adv_filters_layout_mode", None) == mode:
        return
    self._adv_filters_layout_mode = mode

    grid = self._adv_filters_main_grid
    w = self._adv_filters_grid_widgets

    # Remove todos os widgets do grid
    while grid.count():
        item = grid.takeAt(0)
        widget = item.widget()
        if widget is not None:
            grid.removeWidget(widget)
            widget.hide()
        del item

    # Largura > LAYOUT_WIDE_MIN_WIDTH px (Wide: 5 colunas)
    if width > LAYOUT_WIDE_MIN_WIDTH:
        grid.addWidget(w["emis_box"], 0, 0)
        w["emis_box"].show()
        grid.addWidget(w["exec_box"], 0, 1)
        w["exec_box"].show()
        grid.addWidget(w["status_box"], 0, 2)
        w["status_box"].show()
        grid.addWidget(w["year_emissao_box"], 0, 3)
        w["year_emissao_box"].show()
        grid.addWidget(w["year_execucao_box"], 0, 4)
        w["year_execucao_box"].show()
        grid.addWidget(w["reprog_box"], 1, 0)
        w["reprog_box"].show()
        grid.addWidget(w["prio_emis_box"], 1, 1)
        w["prio_emis_box"].show()
        grid.addWidget(w["prio_plan_box"], 1, 2)
        w["prio_plan_box"].show()
        grid.addWidget(w["macro_box"], 1, 3)
        w["macro_box"].show()
        grid.addWidget(w["deriv_box"], 1, 4)
        w["deriv_box"].show()
        grid.addWidget(w["week_emis_box"], 2, 0)
        w["week_emis_box"].show()
        grid.addWidget(w["week_exec_box"], 2, 1)
        w["week_exec_box"].show()
        grid.addWidget(w["sol_box"], 2, 2)
        w["sol_box"].show()
        grid.addWidget(w["prog_box"], 2, 3)
        w["prog_box"].show()
        grid.addWidget(w["exec_resp_box"], 2, 4)
        w["exec_resp_box"].show()
        for col in range(5):
            grid.setColumnStretch(col, 1)

    # Largura LAYOUT_MID_MIN_WIDTH-LAYOUT_WIDE_MIN_WIDTH px (Mid: 3 colunas)
    elif width > LAYOUT_MID_MIN_WIDTH:
        grid.addWidget(w["emis_box"], 0, 0)
        w["emis_box"].show()
        grid.addWidget(w["exec_box"], 0, 1)
        w["exec_box"].show()
        grid.addWidget(w["status_box"], 0, 2)
        w["status_box"].show()
        grid.addWidget(w["year_emissao_box"], 1, 0)
        w["year_emissao_box"].show()
        grid.addWidget(w["year_execucao_box"], 1, 1)
        w["year_execucao_box"].show()
        grid.addWidget(w["reprog_box"], 1, 2)
        w["reprog_box"].show()
        grid.addWidget(w["prio_emis_box"], 2, 0)
        w["prio_emis_box"].show()
        grid.addWidget(w["prio_plan_box"], 2, 1)
        w["prio_plan_box"].show()
        grid.addWidget(w["macro_box"], 2, 2)
        w["macro_box"].show()
        grid.addWidget(w["deriv_box"], 3, 0, 1, 2)
        w["deriv_box"].show()
        grid.addWidget(w["sol_box"], 3, 2)
        w["sol_box"].show()
        grid.addWidget(w["week_emis_box"], 4, 0)
        w["week_emis_box"].show()
        grid.addWidget(w["week_exec_box"], 4, 1)
        w["week_exec_box"].show()
        grid.addWidget(w["prog_box"], 4, 2)
        w["prog_box"].show()
        grid.addWidget(w["exec_resp_box"], 5, 0, 1, 3)
        w["exec_resp_box"].show()
        for col in range(3):
            grid.setColumnStretch(col, 1)

    # Largura <= LAYOUT_MID_MIN_WIDTH px (Narrow: 2 colunas)
    else:
        grid.addWidget(w["emis_box"], 0, 0)
        w["emis_box"].show()
        grid.addWidget(w["exec_box"], 0, 1)
        w["exec_box"].show()
        grid.addWidget(w["status_box"], 1, 0)
        w["status_box"].show()
        grid.addWidget(w["year_emissao_box"], 1, 1)
        w["year_emissao_box"].show()
        grid.addWidget(w["year_execucao_box"], 2, 0)
        w["year_execucao_box"].show()
        grid.addWidget(w["reprog_box"], 2, 1)
        w["reprog_box"].show()
        grid.addWidget(w["prio_emis_box"], 3, 0)
        w["prio_emis_box"].show()
        grid.addWidget(w["prio_plan_box"], 3, 1)
        w["prio_plan_box"].show()
        grid.addWidget(w["macro_box"], 4, 0)
        w["macro_box"].show()
        grid.addWidget(w["deriv_box"], 4, 1)
        w["deriv_box"].show()
        grid.addWidget(w["week_emis_box"], 5, 0)
        w["week_emis_box"].show()
        grid.addWidget(w["week_exec_box"], 5, 1)
        w["week_exec_box"].show()
        grid.addWidget(w["sol_box"], 6, 0)
        w["sol_box"].show()
        grid.addWidget(w["prog_box"], 6, 1)
        w["prog_box"].show()
        grid.addWidget(w["exec_resp_box"], 7, 0, 1, 2)
        w["exec_resp_box"].show()
        for col in range(2):
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
            logger.debug("Falha ao parar debounce de setores sem prefixos materializados: %s", exc)
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

def _sort_responsavel_values(self, df_subset, values, resp_col: str):
    if not values:
        return []
    sector_cols = [c for c in ["setor_executor", "setor_emissor"] if c in df_subset.columns]
    sector_counts = {}
    for col in sector_cols:
        try:
            pairs = df_subset[[col, resp_col]].dropna()
        except Exception as exc:
            logger.debug("Falha ao montar pares responsavel/setor (%s, %s): %s", col, resp_col, exc)
            continue
        for sec, person in pairs.itertuples(index=False):
            sec_str = str(sec).strip()
            person_str = str(person).strip()
            if not person_str:
                continue
            sector_counts.setdefault(person_str, {})
            sector_counts[person_str][sec_str] = sector_counts[person_str].get(sec_str, 0) + 1

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
    exec_excluded = self._get_checked_values(getattr(self, "adv_executor_exclude_checks", None))
    emis_excluded = self._get_checked_values(getattr(self, "adv_emissor_exclude_checks", None))
    has_sector = bool(exec_values or emis_values or exec_excluded or emis_excluded)
    def apply_cb():
        return self._apply_advanced_filters_from_ui()

    def _set_enabled(widget, enabled):
        if widget is None:
            return
        try:
            widget.setEnabled(bool(enabled))
        except Exception as exc:
            logger.debug("Falha ao ajustar estado enabled de widget %r: %s", widget, exc)

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
            if allowed:
                subset = subset[subset[exec_col].astype(str).isin(allowed)]
            if excluded:
                subset = subset[~subset[exec_col].astype(str).isin(excluded)]
        if emis_col in subset.columns and selected_emis:
            subset = subset[subset[emis_col].astype(str).isin(selected_emis)]
        if emis_col in subset.columns and selected_emis_excluded:
            subset = subset[~subset[emis_col].astype(str).isin(selected_emis_excluded)]
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
        ("solicitante", "adv_responsavel_solicitante"),
        ("responsavel_programacao", "adv_responsavel_programacao"),
        ("responsavel_execucao", "adv_responsavel_execucao"),
    ]
    processed_prefixes = set()
    for col, prefix in resp_cols:
        if prefix not in requested_prefixes:
            continue
        box = getattr(self, f"{prefix}_box", None)
        button = getattr(self, f"{prefix}_button", None)
        menu = getattr(self, f"{prefix}_menu", None)
        checks_attr = f"{prefix}_checks"
        exclude_checks_attr = f"{prefix}_exclude_checks"
        exclude = getattr(self, f"{prefix}_exclude", None)
        col_exists = col in self.df_completo.columns
        _set_visible(box, col_exists)
        if not col_exists:
            _set_enabled(button, False)
            _set_enabled(exclude, False)
            setattr(self, checks_attr, [])
            setattr(self, exclude_checks_attr, [])
            processed_prefixes.add(prefix)
            continue
        values = _unique_sorted(col)
        try:
            values = self._sort_responsavel_values(df, values, col)
        except Exception as exc:
            logger.debug("Failed to sort responsavel values for column '%s': %s", col, exc)
        _set_enabled(button, True)
        _set_enabled(exclude, True)
        selected = set((self._advanced_filters or {}).get(col) or [])
        excluded = set((self._advanced_filters or {}).get(f"{col}_exclude_values") or [])
        include_checks, exclude_checks = self._rebuild_multiselect_menu(
            button,
            menu,
            values,
            selected,
            lambda *_: self._update_multiselect_button(
                button,
                getattr(self, checks_attr, []),
                exclude_checks=getattr(self, exclude_checks_attr, None),
            ),
            apply_cb,
            excluded,
            lambda *_: self._update_multiselect_button(
                button,
                getattr(self, checks_attr, []),
                exclude_checks=getattr(self, exclude_checks_attr, None),
            ),
        )
        setattr(self, checks_attr, include_checks)
        setattr(self, exclude_checks_attr, exclude_checks)
        processed_prefixes.add(prefix)

    # Reprogramacoes (código duplicado removido)
    reprog_values = getattr(self, "_adv_values_cache", {}).get("reprog_vals", [])
    try:
        include_checks, _ = self._rebuild_multiselect_menu(
            getattr(self, "adv_reprog_button", None),
            getattr(self, "adv_reprog_menu", None),
            reprog_values,
            set((self._advanced_filters or {}).get("num_reprogramacoes_values") or []),
            lambda *_: self._update_multiselect_button(
                getattr(self, "adv_reprog_button", None),
                getattr(self, "adv_reprog_checks", None),
            ),
            lambda *_: self._apply_advanced_filters_from_ui(),
            None,
            None,
        )
        self.adv_reprog_checks = include_checks
        try:
            mode = (self._advanced_filters or {}).get("num_reprogramacoes_mode")
            if mode is not None and getattr(self, "adv_reprog_mode", None):
                idx = getattr(self, "adv_reprog_mode").findData(mode)
                if idx >= 0:
                    getattr(self, "adv_reprog_mode").setCurrentIndex(idx)
        except Exception as exc:
            logger.debug("Failed to restore reprogramacoes mode in advanced filter UI: %s", exc)
    except Exception as exc:
        logger.debug("Failed to rebuild reprogramacoes menu in advanced filter UI: %s", exc)
        self.adv_reprog_checks = []

    # SSAs Derivadas Específicas (novo filtro granular)
    adv_cache = getattr(self, "_adv_values_cache", {}) or {}
    derivadas_numbers = adv_cache.get("derivadas_vals", [])
    if not derivadas_numbers:
        # Extrai numeros unicos de SSAs derivadas se nao estiver em cache
        try:
            if "derivada_de" in df.columns:
                derivadas_series = self._normalize_ssa_series(df["derivada_de"])
                derivadas_numbers = sorted(
                    {v for v in derivadas_series.unique() if v and str(v).strip()},
                    key=lambda x: str(x).casefold()
                )
                adv_cache["derivadas_vals"] = derivadas_numbers
                self._adv_values_cache = adv_cache
        except Exception as exc:
            logger.debug("Falha ao atualizar cache de derivadas em filtros avancados: %s", exc)
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
        logger.warning("Falha ao salvar estado antes de limpar filtros avancados: %s", exc)
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
            getattr(self, "_current_tab_kind", None) == "filters"
            and bool(getattr(self, "_adv_options_dirty", False))
            and hasattr(self, "_refresh_advanced_filter_options")
        ):
            self._refresh_advanced_filter_options()
            self._adv_options_dirty = False
    except Exception as exc:
        logger.warning("Falha ao executar refresh imediato de filtros avancados apos limpar: %s", exc)
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
    if data.get("ano_emissao_exclude_values") or data.get("ano_execucao_exclude_values"):
        return True
    if data.get("prioridade_emissao_values") or data.get("prioridade_planejamento_values"):
        return True
    if data.get("num_reprogramacoes_mode") and data.get("num_reprogramacoes_values"):
        return True
    if data.get("semana_emissao_inicio") is not None or data.get("semana_emissao_fim") is not None:
        return True
    if data.get("semana_execucao_inicio") is not None or data.get("semana_execucao_fim") is not None:
        return True
    if data.get("derivada_has") or data.get("derivada_all_ste") or data.get("derivada_is"):
        return True
    if data.get("macro_filter"):
        return True
    return False

def _apply_advanced_filters_from_ui(self, store_only: bool = False):
    if not store_only:
        try:
            self._store_last_filter_state()
        except Exception as exc:
            logger.warning("Falha ao salvar estado antes de aplicar filtros avancados: %s", exc)
    data = {}
    try:
        data["setor_executor"] = self._get_checked_values(getattr(self, "adv_executor_checks", None))
    except Exception:
        data["setor_executor"] = []
    try:
        data["setor_executor_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_executor_exclude_checks", None)
        )
    except Exception:
        data["setor_executor_exclude_values"] = []
    try:
        data["setor_emissor"] = self._get_checked_values(getattr(self, "adv_emissor_checks", None))
    except Exception:
        data["setor_emissor"] = []
    try:
        data["setor_emissor_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_emissor_exclude_checks", None)
        )
    except Exception:
        data["setor_emissor_exclude_values"] = []
    try:
        data["situacao"] = self._get_checked_values(getattr(self, "adv_status_checks", None))
    except Exception:
        data["situacao"] = []
    try:
        data["situacao_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_status_exclude_checks", None)
        )
    except Exception:
        data["situacao_exclude_values"] = []
    try:
        data["ano_emissao_values"] = self._get_checked_values(
            getattr(self, "adv_year_emissao_checks", None)
        )
    except Exception:
        data["ano_emissao_values"] = []
    try:
        data["ano_emissao_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_year_emissao_exclude_checks", None)
        )
    except Exception:
        data["ano_emissao_exclude_values"] = []
    try:
        data["ano_execucao_values"] = self._get_checked_values(
            getattr(self, "adv_year_execucao_checks", None)
        )
    except Exception:
        data["ano_execucao_values"] = []
    try:
        data["ano_execucao_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_year_execucao_exclude_checks", None)
        )
    except Exception:
        data["ano_execucao_exclude_values"] = []
    try:
        data["semana_emissao_inicio"] = self._parse_week(self.adv_week_emissao_start.text())
        data["semana_emissao_fim"] = self._parse_week(self.adv_week_emissao_end.text())
    except Exception:
        data["semana_emissao_inicio"] = None
        data["semana_emissao_fim"] = None
    try:
        data["semana_execucao_inicio"] = self._parse_week(self.adv_week_execucao_start.text())
        data["semana_execucao_fim"] = self._parse_week(self.adv_week_execucao_end.text())
    except Exception:
        data["semana_execucao_inicio"] = None
        data["semana_execucao_fim"] = None
    data["semana_emissao_exclude"] = False
    data["semana_execucao_exclude"] = False
    data["derivada_has"] = _safe_is_checked(getattr(self, "adv_derivada_has", None))
    data["derivada_all_ste"] = _safe_is_checked(getattr(self, "adv_derivada_all_ste", None))
    if data.get("derivada_all_ste"):
        data["derivada_has"] = True
    data["derivada_is"] = _safe_is_checked(getattr(self, "adv_derivada_is", None))
    # derivadas_especificas_values removido - botao Especificas agora e apenas visualizacao
    adv_current = getattr(self, "_advanced_filters", None) or {}
    built_prefixes = set(getattr(self, "_responsavel_materialized_prefixes", set()))

    def _collect_responsavel_values(checks_attr: str, key_name: str, prefix: str) -> list[str]:
        if prefix not in built_prefixes:
            return list(adv_current.get(key_name) or [])
        try:
            return self._get_checked_values(getattr(self, checks_attr, None))
        except Exception:
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
    try:
        data["num_reprogramacoes_values"] = self._get_checked_values(getattr(self, "adv_reprog_checks", None))
    except Exception:
        data["num_reprogramacoes_values"] = []
    data["num_reprogramacoes_mode"] = _safe_combo_item_data(getattr(self, "adv_reprog_mode", None))
    try:
        data["prioridade_emissao_values"] = self._get_checked_values(
            getattr(self, "adv_prioridade_emissao_checks", None)
        )
    except Exception:
        data["prioridade_emissao_values"] = []
    try:
        data["prioridade_emissao_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_prioridade_emissao_exclude_checks", None)
        )
    except Exception:
        data["prioridade_emissao_exclude_values"] = []
    try:
        data["prioridade_planejamento_values"] = self._get_checked_values(
            getattr(self, "adv_prioridade_planejamento_checks", None)
        )
    except Exception:
        data["prioridade_planejamento_values"] = []
    try:
        data["prioridade_planejamento_exclude_values"] = self._get_checked_values(
            getattr(self, "adv_prioridade_planejamento_exclude_checks", None)
        )
    except Exception:
        data["prioridade_planejamento_exclude_values"] = []
    try:
        data["macro_filter"] = self.adv_macro_combo.currentData()
    except Exception:
        data["macro_filter"] = None

    self._advanced_filters = data
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
        logger.warning("Falha ao atualizar resultado apos aplicar filtros avancados: %s", exc)
    finally:
        setattr(self, "_adv_notice_callback", None)
    notice = notice_box["value"]
    if notice:
        try:
            if notice == "derivada_all_ste_empty":
                self.status_label.setText("Status: Nenhuma derivada STE encontrada para o filtro.")
            elif notice == "derivada_empty":
                self.status_label.setText("Status: Nenhuma derivada encontrada para o filtro.")
        except Exception:
            pass

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
                logger.debug("Failed to read checkbox from list source in _get_checked_values: %s", exc)
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
                logger.debug("Failed to read checkbox from widget source in _get_checked_values: %s", exc)
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
    for prefix, button_attr, checks_attr, key_name, excl_checks_attr, excl_key_name in responsavel_cfg:
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
    try:
        emissao_values = data.get("ano_emissao_values")
        emissao_exclude = data.get("ano_emissao_exclude_values")
        if emissao_values is None and data.get("ano_emissao") is not None:
            emissao_values = [data.get("ano_emissao")]
        if emissao_exclude is None and data.get("ano_emissao_exclude") and data.get("ano_emissao") is not None:
            emissao_exclude = [data.get("ano_emissao")]
        self._sync_multiselect_checks(
            getattr(self, "adv_year_emissao_button", None),
            getattr(self, "adv_year_emissao_checks", None),
            emissao_values,
            getattr(self, "adv_year_emissao_exclude_checks", None),
            emissao_exclude,
        )
    except Exception as exc:
        logger.warning("Falha ao sincronizar filtro avancado de ano de emissao: %s", exc)
    try:
        execucao_values = data.get("ano_execucao_values")
        execucao_exclude = data.get("ano_execucao_exclude_values")
        if execucao_values is None and data.get("ano_execucao") is not None:
            execucao_values = [data.get("ano_execucao")]
        if execucao_exclude is None and data.get("ano_execucao_exclude") and data.get("ano_execucao") is not None:
            execucao_exclude = [data.get("ano_execucao")]
        self._sync_multiselect_checks(
            getattr(self, "adv_year_execucao_button", None),
            getattr(self, "adv_year_execucao_checks", None),
            execucao_values,
            getattr(self, "adv_year_execucao_exclude_checks", None),
            execucao_exclude,
        )
    except Exception as exc:
        logger.warning("Falha ao sincronizar filtro avancado de ano de execucao: %s", exc)
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
        logger.warning("Falha ao sincronizar intervalo de semanas dos filtros avancados: %s", exc)
    try:
        if hasattr(self, "adv_derivada_has"):
            if data.get("derivada_all_ste"):
                self.adv_derivada_has.setChecked(True)
            else:
                self.adv_derivada_has.setChecked(bool(data.get("derivada_has")))
        if hasattr(self, "adv_derivada_all_ste"):
            self.adv_derivada_all_ste.setChecked(bool(data.get("derivada_all_ste")))
        if hasattr(self, "adv_derivada_is"):
            self.adv_derivada_is.setChecked(bool(data.get("derivada_is")))
    except Exception as exc:
        logger.warning("Falha ao sincronizar toggles de derivadas nos filtros avancados: %s", exc)
    try:
        if hasattr(self, "adv_macro_combo"):
            self.adv_macro_combo.blockSignals(True)
            idx = self.adv_macro_combo.findData(data.get("macro_filter"))
            self.adv_macro_combo.setCurrentIndex(max(0, idx))
    except Exception as exc:
        logger.warning("Falha ao sincronizar seletor macro dos filtros avancados: %s", exc)
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
            apply_cb,
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
            apply_cb,
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
            apply_cb,
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
        if exc_vals is None and filters.get("ano_emissao_exclude") and filters.get("ano_emissao") is not None:
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
            apply_cb,
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
        if exc_vals is None and filters.get("ano_execucao_exclude") and filters.get("ano_execucao") is not None:
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
            apply_cb,
            exc_set,
            lambda *_: self._update_multiselect_button(
                self.adv_year_execucao_button,
                getattr(self, "adv_year_execucao_checks", None),
                exclude_checks=getattr(self, "adv_year_execucao_exclude_checks", None),
            ),
        )
        self.adv_year_execucao_checks = year_include
        self.adv_year_execucao_exclude_checks = year_exclude


def _refresh_priority_menus(self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb):
    if hasattr(self, "adv_prioridade_emissao_menu"):
        prio_include, prio_exclude = self._rebuild_multiselect_menu(
            self.adv_prioridade_emissao_button,
            self.adv_prioridade_emissao_menu,
            prio_emissao_vals,
            set(filters.get("prioridade_emissao_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_emissao_button,
                getattr(self, "adv_prioridade_emissao_checks", None),
                exclude_checks=getattr(self, "adv_prioridade_emissao_exclude_checks", None),
            ),
            apply_cb,
            set(filters.get("prioridade_emissao_exclude_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_emissao_button,
                getattr(self, "adv_prioridade_emissao_checks", None),
                exclude_checks=getattr(self, "adv_prioridade_emissao_exclude_checks", None),
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
                exclude_checks=getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
            ),
            apply_cb,
            set(filters.get("prioridade_planejamento_exclude_values") or []),
            lambda *_: self._update_multiselect_button(
                self.adv_prioridade_planejamento_button,
                getattr(self, "adv_prioridade_planejamento_checks", None),
                exclude_checks=getattr(self, "adv_prioridade_planejamento_exclude_checks", None),
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
    logger.debug("_refresh_advanced_filter_options: iniciando com %s registros", len(df))
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
    if cache and cache.get("df_key") == df_key and not getattr(self, "_adv_options_dirty", False):
        self._adv_options_scheduled = False
        return

    df_id = id(df)

    # Inicializa cache granular se necessário
    if not isinstance(cache, dict) or cache.get("df_id") != df_id:
        cache = {"df_id": df_id, "df_key": df_key}
        self._adv_values_cache = cache

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

    # Popula cache se necessário (bloco único consolidado) - CORRIGIDO: removida duplicação
    if cache.get("exec_vals") is None:
        cache["exec_vals"] = (
            _sort_sector_values(_unique_sorted("setor_executor")) if "setor_executor" in df.columns else []
        )
        cache["emis_vals"] = (
            _sort_sector_values(_unique_sorted("setor_emissor")) if "setor_emissor" in df.columns else []
        )
        cache["status_vals"] = _unique_sorted("situacao") if "situacao" in df.columns else []

        def _collect_years_from_dates(series):
            """Extrai anos de datas usando operações vetorizadas (otimizado)."""
            try:
                # Vetorizado: converte diretamente para datetime sem apply()
                ts = pd.to_datetime(series, errors="coerce")
                # Extrai anos e remove NaT
                years = ts.dt.year.dropna().astype(int).unique()
                return sorted(years, reverse=True)
            except Exception:
                return []

        def _collect_years_from_weeks(series):
            """Extrai anos de semanas (formato YYYYWW) vetorizado."""
            try:
                nums = pd.to_numeric(series, errors="coerce").dropna().astype(int)
                # Vetorizado: unique() em vez de tolist() + set() + sorted()
                years = (nums // 100).unique()
                return sorted(years, reverse=True)
            except Exception:
                return []

        emissao_years = []
        if "data_cadastro" in df.columns:
            emissao_years = _collect_years_from_dates(df["data_cadastro"])
        elif "semana_cadastro" in df.columns:
            emissao_years = _collect_years_from_weeks(df["semana_cadastro"])

        execucao_years = []
        if "semana_executada" in df.columns:
            execucao_years = _collect_years_from_weeks(df["semana_executada"])

        cache["emissao_years"] = emissao_years
        cache["execucao_years"] = execucao_years
        cache["prio_emissao_vals"] = (
            _unique_sorted("grau_prioridade_emissao") if "grau_prioridade_emissao" in df.columns else []
        )
        cache["prio_planejamento_vals"] = (
            _unique_sorted("grau_prioridade_planejamento") if "grau_prioridade_planejamento" in df.columns else []
        )
        if "num_reprogramacoes" in df.columns:
            try:
                # Vetorizado: dropna() já remove NaN, sem necessidade de lambda
                reprog_series = pd.to_numeric(df["num_reprogramacoes"], errors="coerce").dropna()
                # unique() evita tolist() + set() + sorted()
                reprog_vals = reprog_series.astype(int).unique()
                cache["reprog_vals"] = sorted(reprog_vals, reverse=True)
            except Exception:
                cache["reprog_vals"] = []
        else:
            cache["reprog_vals"] = []
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
    self._refresh_priority_menus(prio_emissao_vals, prio_planejamento_vals, filters, apply_cb)

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
