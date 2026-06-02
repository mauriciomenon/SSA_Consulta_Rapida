# gui/ssa/gui_filters_advanced_ui.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: builds advanced filters UI and menu wiring.
# Relation: does not apply DataFrame filters directly.

from __future__ import annotations

from time import perf_counter
from typing import Any

import pandas as pd

from gui.qt_stubs import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from utils.robust_logging import get_robust_logger

from .filter_domain_rules import (
    advanced_macro_filter_preset,
    order_sector_values,
    sector_sort_key,
)
from .gui_filters_advanced_activity import has_active_advanced_filters
from .gui_filters_advanced_grid import (
    enforce_advanced_filters_compact_metrics as _enforce_advanced_filters_compact_metrics,
    reorganize_advanced_filters_grid as _reorganize_advanced_filters_grid_impl,
    resolve_adv_layout_baseline as _resolve_adv_layout_baseline,
    update_advanced_filters_action_buttons as _update_advanced_filters_action_buttons,
)
from .gui_filters_advanced_layout import (
    LAYOUT_ADV_CONTROL_HEIGHT,
    LAYOUT_ADV_PANEL_MAX_HEIGHT,
    LAYOUT_ADV_PANEL_MIN_HEIGHT,
)
from .gui_filters_advanced_panel_state import (
    AdvancedFilterPanelParts,
    AdvancedFilterPanelState,
    advanced_panel_state as _advanced_panel_state,
)
from .gui_filters_advanced_refresh import (
    AdvancedFilterUIState,
    build_advanced_values_cache_key,
    get_cached_advanced_filter_option_values,
)
from .gui_filters_advanced_specs import (
    ADVANCED_RESPONSAVEL_MULTISELECT_SPECS,
    ADVANCED_STANDARD_MULTISELECT_SPECS,
    ADVANCED_YEAR_MULTISELECT_SPECS,
)
from .gui_filters_advanced_sync import sync_advanced_filter_ui
from .gui_filters_multiselect_menu import (
    _build_multiselect_summary_candidates,
    _checked_values_from_checkboxes,
    _fit_button_text,
    _is_not_deleted,
    _sync_include_exclude_multiselect_checks,
    _update_multiselect_button,
)
from .gui_filters_advanced_state_reader import AdvancedFilterStateReader, resolve_year_selection_sets
from .gui_filters_advanced_state import DIVISAO_SETORES, SECTOR_TO_DIV
from .gui_filters_responsavel_refresh import responsavel_options_refresher
from .gui_filters_responsavel_state import responsavel_materialization_state

logger = get_robust_logger().get_logger(__name__, "gui")
_DERIVADA_ALL_STE_LABEL = "Derivadas em STE/SES"
_MACRO_EXECUTADAS_SETOR_KEY = "ssa_executadas_setor"
_MACRO_EXECUTADAS_DIVISAO_KEY = "ssa_executadas_divisao"
_is_widget_valid = _is_not_deleted
_ADVANCED_MULTISELECT_FIELD_DEFS = (
    ("emis", "Emissor", True),
    ("exec", "Executor", True),
    ("status", "Situacao", True),
    ("year_emissao", "Ano Emissao", False),
    ("year_execucao", "Ano Execucao", False),
    ("prio_emis", "Prio. Emissao", True),
    ("prio_plan", "Prio. Planejamento", True),
    ("deriv", "Derivadas", False),
)
_ADVANCED_RESPONSAVEL_FIELD_DEFS = (
    ("sol", "Solicitante"),
    ("prog", "Resp Prog"),
    ("exec_resp", "Resp Exec"),
)


def _attach_multiselect_menu(*args, **kwargs):
    from .gui_filters_multiselect_menu import _attach_multiselect_menu as impl

    return impl(*args, **kwargs)


def _rebuild_multiselect_menu(*args, **kwargs):
    from .gui_filters_multiselect_menu import _rebuild_multiselect_menu as impl

    return impl(*args, **kwargs)


def _sync_multiselect_checks(*args, **kwargs):
    from .gui_filters_multiselect_menu import _sync_multiselect_checks as impl

    return impl(*args, **kwargs)


def _flatten_field_box(box: QGroupBox) -> None:
    if box is None:
        return
    try:
        box.setFlat(True)
    except Exception as exc:
        logger.debug("Falha ao achatar box de filtro avancado: %s", exc)


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except Exception:
        return 0


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
        box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    except Exception as exc:
        logger.debug(
            "Falha ao definir size policy do groupbox multiselect '%s': %s", title, exc
        )
    exclude = None
    if with_exclude:
        exclude = QCheckBox("Diferente")
        layout.addWidget(exclude)
    layout.addWidget(button, 1)
    return box, button, menu, exclude


def _set_menu_pre_show_hook(self, button, callback) -> None:
    if button is None:
        return
    hooks = getattr(self, "_menu_pre_show_hooks", None)
    if not isinstance(hooks, dict):
        hooks = {}
        self._menu_pre_show_hooks = hooks
    key = id(button)
    hooks[key] = callback
    try:
        button.destroyed.connect(lambda *_args, hook_key=key: hooks.pop(hook_key, None))
    except Exception as exc:
        logger.debug("Falha ao registrar cleanup de hook de menu: %s", exc)


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


def _set_checkbox_checked_quietly(self, checkbox, checked: bool) -> None:
    """Atualiza estado de checkbox sem propagar sinais e sem deixar bloqueio preso."""
    if not _is_not_deleted(checkbox):
        return
    try:
        desired = bool(checked)
        if bool(checkbox.isChecked()) == desired:
            return
    except Exception as exc:
        logger.debug(
            "Falha ao ler estado atual de checkbox em _set_checkbox_checked_quietly: %s",
            exc,
        )
        desired = bool(checked)
    try:
        with QSignalBlocker(checkbox):
            checkbox.setChecked(desired)
    except Exception as exc:
        logger.debug(
            "Falha ao atualizar checkbox em _set_checkbox_checked_quietly: %s", exc
        )


def _sync_responsavel_flags(self) -> None:
    responsavel_options_refresher(self)


def _mark_responsavel_dirty(self, prefixes=None) -> None:
    responsavel_options_refresher(self).mark_dirty(prefixes=prefixes)


def _on_sector_debounce_timeout(self) -> None:
    group = getattr(self, "adv_filters_group", None)
    if group is None:
        state = _advanced_panel_state(self)
        group = state.group if state is not None else None
    if group is None or not _is_not_deleted(group):
        return
    target = responsavel_materialization_state(self).stale_built_prefixes()
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
    responsavel_options_refresher(self).ensure_materialized(
        target_prefix=target_prefix,
        force=force,
    )


def _sync_responsavel_button_summaries(self, only_prefixes=None) -> None:
    """Atualiza resumo dos botões de responsavel sem materializar menus completos."""
    selected_prefixes = None
    if only_prefixes is not None:
        selected_prefixes = {p for p in only_prefixes}
    filters = self._advanced_filters or {}
    for spec in ADVANCED_RESPONSAVEL_MULTISELECT_SPECS:
        if selected_prefixes is not None and spec.prefix not in selected_prefixes:
            continue
        button = getattr(self, f"{spec.prefix}_button", None)
        if button is None or not _is_not_deleted(button):
            continue
        include_values = [
            str(v) for v in (filters.get(spec.include_key) or []) if str(v).strip()
        ]
        exclude_values = [
            str(v) for v in (filters.get(spec.exclude_key) or []) if str(v).strip()
        ]
        candidates = _build_multiselect_summary_candidates(
            include_values,
            exclude_values,
            "Selecionar",
        )
        fallback = candidates[1] if len(candidates) > 1 else candidates[-1]
        text = _fit_button_text(button, candidates, fallback)
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
                spec.prefix,
                exc,
            )










































































def _make_reprogramacoes_controls(self, layout_baseline):
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
    return reprog_box, reprog_mode, reprog_button, reprog_menu

def _make_week_range_box(title: str):
    week_box = QGroupBox(title)
    _flatten_field_box(week_box)
    week_layout = QHBoxLayout(week_box)
    week_layout.setContentsMargins(0, 0, 0, 0)
    week_layout.setSpacing(2)
    week_start = QLineEdit()
    week_start.setPlaceholderText("Ini")
    try:
        week_start.setMaxLength(6)
        week_start.setMinimumWidth(64)
        week_start.setMaximumWidth(108)
        week_start.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana inicial %s: %s", title, exc)
    week_end = QLineEdit()
    week_end.setPlaceholderText("Fim")
    try:
        week_end.setMaxLength(6)
        week_end.setMinimumWidth(64)
        week_end.setMaximumWidth(108)
        week_end.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    except Exception as exc:
        logger.debug("Falha ao configurar campo de semana final %s: %s", title, exc)
    week_layout.addWidget(week_start)
    week_layout.addWidget(week_end)
    return week_box, week_start, week_end


def _make_advanced_action_box(self):
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
    return action_box, apply_btn, clear_btn


def _reset_advanced_menu_hooks(self) -> None:
    hooks = getattr(self, "_menu_pre_show_hooks", None)
    if isinstance(hooks, dict):
        hooks.clear()
    self._menu_pre_show_hooks = {}


def _make_advanced_multiselect_fields(self, layout_baseline) -> dict[str, tuple]:
    return {
        key: self._make_multiselect_box(
            title,
            with_exclude=with_exclude,
            layout_baseline=layout_baseline,
        )
        for key, title, with_exclude in _ADVANCED_MULTISELECT_FIELD_DEFS
    }


def _make_advanced_macro_box(self):
    macro_box = QGroupBox("Macro")
    _flatten_field_box(macro_box)
    macro_layout = QHBoxLayout(macro_box)
    macro_layout.setContentsMargins(0, 0, 0, 0)
    macro_combo = QComboBox()
    try:
        macro_combo.setMinimumWidth(100)
        macro_combo.setMaximumWidth(240)
    except Exception as exc:
        logger.debug("Falha ao definir largura minima do filtro macro: %s", exc)
    macro_combo.addItem("Nenhum", None)
    macro_combo.addItem("Baixar", "ssas_para_baixar")
    macro_combo.addItem("SSA Executadas Setor", _MACRO_EXECUTADAS_SETOR_KEY)
    macro_combo.addItem("SSA Executadas Divisao", _MACRO_EXECUTADAS_DIVISAO_KEY)
    macro_combo.currentIndexChanged.connect(self._on_macro_filter_changed)
    macro_layout.addWidget(macro_combo)
    return macro_box, macro_combo


def _macro_sector_filters(self, mode: str) -> tuple[set[str], set[str]]:
    selected_sectors = {
        str(value or "").strip().upper()
        for value in _checked_values_from_checkboxes(
            getattr(self, "adv_executor_checks", [])
        )
        if str(value or "").strip()
    }
    if mode == _MACRO_EXECUTADAS_DIVISAO_KEY:
        prefixes = {value[:3] for value in selected_sectors if len(value) >= 3}
        return set(), prefixes
    return selected_sectors, set()


def _macro_source_dataframe(self, mode: str) -> pd.DataFrame:
    df = getattr(self, "df_completo", None)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    required_cols = {"setor_executor", "semana_executada", "responsavel_execucao"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()
    working = df.copy()
    setor_series = working["setor_executor"].astype("string").fillna("").str.strip().str.upper()
    week_series = working["semana_executada"].astype("string").fillna("").str.strip()
    exec_series = (
        working["responsavel_execucao"].astype("string").fillna("").str.strip()
    )
    working = working.assign(
        _macro_setor=setor_series,
        _macro_week=week_series,
        _macro_executor=exec_series.where(exec_series != "", "-"),
    )
    working = working[(working["_macro_setor"] != "") & (working["_macro_week"] != "")]
    selected_sectors, selected_prefixes = _macro_sector_filters(self, mode)
    if selected_sectors:
        working = working[working["_macro_setor"].isin(selected_sectors)]
    elif selected_prefixes:
        working = working[
            working["_macro_setor"].str[:3].isin(selected_prefixes)
        ]
    return working


def _build_executadas_macro_report(self, mode: str) -> tuple[str, str]:
    df = _macro_source_dataframe(self, mode)
    if df.empty:
        title = (
            "SSA Executadas Divisao"
            if mode == _MACRO_EXECUTADAS_DIVISAO_KEY
            else "SSA Executadas Setor"
        )
        return title, "Nenhum dado executado disponivel para o recorte atual."
    if mode == _MACRO_EXECUTADAS_DIVISAO_KEY:
        title = "SSA Executadas Divisao"
        df = df.assign(_macro_divisao=df["_macro_setor"].str[:3])
        grouped = (
            df.groupby(
                ["_macro_divisao", "_macro_setor", "_macro_week", "_macro_executor"],
                dropna=False,
            )
            .size()
            .to_frame("total")
            .reset_index()
        )
        lines = [title, ""]
        for divisao in sorted(grouped["_macro_divisao"].dropna().unique()):
            lines.append(str(divisao))
            div_df = grouped[grouped["_macro_divisao"] == divisao]
            for setor in sorted(
                div_df["_macro_setor"].dropna().unique(),
                key=lambda value: sector_sort_key(str(value), SECTOR_TO_DIV),
            ):
                lines.append(f"  {setor}")
                setor_df = div_df[div_df["_macro_setor"] == setor]
                for week in sorted(setor_df["_macro_week"].dropna().unique()):
                    lines.append(f"    {week}")
                    week_df = setor_df[setor_df["_macro_week"] == week]
                    ordered_week_df = week_df.sort_values(
                        ["_macro_executor", "total"],
                        ascending=[True, False],
                    )
                    for row in ordered_week_df.to_dict("records"):
                        lines.append(
                            f"      {row['_macro_executor']}: {int(row['total'])}"
                        )
                lines.append("")
        return title, "\n".join(lines).strip()
    title = "SSA Executadas Setor"
    grouped = (
        df.groupby(["_macro_setor", "_macro_week", "_macro_executor"], dropna=False)
        .size()
        .to_frame("total")
        .reset_index()
    )
    lines = [title, ""]
    for setor in sorted(
        grouped["_macro_setor"].dropna().unique(),
        key=lambda value: sector_sort_key(str(value), SECTOR_TO_DIV),
    ):
        lines.append(str(setor))
        setor_df = grouped[grouped["_macro_setor"] == setor]
        for week in sorted(setor_df["_macro_week"].dropna().unique()):
            lines.append(f"  {week}")
            week_df = setor_df[setor_df["_macro_week"] == week]
            ordered_week_df = week_df.sort_values(
                ["_macro_executor", "total"],
                ascending=[True, False],
            )
            for row in ordered_week_df.to_dict("records"):
                lines.append(f"    {row['_macro_executor']}: {int(row['total'])}")
        lines.append("")
    return title, "\n".join(lines).strip()


def _show_executadas_macro_dialog(self, mode: str) -> None:
    title, report_text = _build_executadas_macro_report(self, mode)
    dialog = QDialog(self)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(10, 10, 10, 10)
    intro = QLabel(
        "Resumo agrupado por semana e executor para os setores do recorte atual."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)
    output = QTextEdit()
    output.setReadOnly(True)
    try:
        output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    except Exception as exc:
        logger.debug("Falha ao desativar quebra de linha no relatorio macro: %s", exc)
    output.setPlainText(report_text)
    layout.addWidget(output, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.resize(720, 520)
    dialog.exec()


def _make_advanced_responsavel_fields(self, layout_baseline) -> dict[str, tuple]:
    fields = {
        key: self._make_multiselect_box(title, layout_baseline=layout_baseline)
        for key, title in _ADVANCED_RESPONSAVEL_FIELD_DEFS
    }
    hook_specs = (
        ("sol", "adv_responsavel_solicitante"),
        ("prog", "adv_responsavel_programacao"),
        ("exec_resp", "adv_responsavel_execucao"),
    )
    for field_key, prefix in hook_specs:
        button = fields[field_key][1]
        self._set_menu_pre_show_hook(
            button,
            lambda prefix=prefix: self._ensure_responsavel_options_materialized(
                target_prefix=prefix
            ),
        )
    return fields


def _build_advanced_derivada_field(self, deriv_button, deriv_menu):
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
        lambda *_: _update_multiselect_button(
            self,
            deriv_button,
            getattr(self, "adv_derivada_checks", None),
            "Selecionar",
        ),
        False,
        None,
        None,
    )
    self._set_menu_pre_show_hook(
        deriv_button,
        lambda: _refresh_derivadas_menu(
            self,
            getattr(self, "_advanced_filters", None) or {},
            lambda: self._apply_advanced_filters_from_ui(),
            selected_override=_collect_derivadas_selected_from_checks(self),
        ),
    )
    return deriv_checks


def _configure_advanced_panel_scroll(self, outer, grid_container):
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
    return controls_scroll


def _advanced_filter_metric_controls(
    fields,
    responsavel_fields,
    *,
    reprog_mode,
    reprog_button,
    week_emissao_start,
    week_emissao_end,
    week_exec_start,
    week_exec_end,
    macro_combo,
    apply_btn,
    clear_btn,
):
    return (
        fields["emis"][1],
        fields["exec"][1],
        fields["status"][1],
        fields["year_emissao"][1],
        fields["year_execucao"][1],
        reprog_mode,
        reprog_button,
        fields["prio_emis"][1],
        fields["prio_plan"][1],
        fields["deriv"][1],
        week_emissao_start,
        week_emissao_end,
        week_exec_start,
        week_exec_end,
        macro_combo,
        responsavel_fields["sol"][1],
        responsavel_fields["prog"][1],
        responsavel_fields["exec_resp"][1],
        apply_btn,
        clear_btn,
    )


def _add_multiselect_context(ctx: dict, prefix: str, button, menu, exclude=None) -> None:
    ctx.update(
        {
            f"{prefix}_button": button,
            f"{prefix}_menu": menu,
            f"{prefix}_checks": [],
            f"{prefix}_exclude_checks": [],
        }
    )
    if exclude is not None:
        ctx[f"{prefix}_exclude"] = exclude


def _add_multiselect_specs_context(ctx: dict, specs, fields: dict) -> None:
    for spec in specs:
        _, button, menu, exclude = fields[spec.field_key]
        _add_multiselect_context(ctx, spec.prefix, button, menu, exclude)


def _build_advanced_filters_context_from_parts(parts: AdvancedFilterPanelParts):
    fields = parts.fields
    controls = parts.controls
    ctx = {"adv_filters_group": parts.group}

    _add_multiselect_specs_context(ctx, ADVANCED_STANDARD_MULTISELECT_SPECS[:3], fields)
    _add_multiselect_specs_context(ctx, ADVANCED_YEAR_MULTISELECT_SPECS, fields)

    ctx.update(
        {
            "adv_reprog_box": controls["reprog_box"],
            "adv_reprog_mode": controls["reprog_mode"],
            "adv_reprog_button": controls["reprog_button"],
            "adv_reprog_menu": controls["reprog_menu"],
            "adv_reprog_checks": [],
            "adv_week_emissao_start": controls["week_emissao_start"],
            "adv_week_emissao_end": controls["week_emissao_end"],
            "adv_week_execucao_start": controls["week_exec_start"],
            "adv_week_execucao_end": controls["week_exec_end"],
            "adv_macro_combo": controls["macro_combo"],
        }
    )

    _add_multiselect_specs_context(ctx, ADVANCED_STANDARD_MULTISELECT_SPECS[3:], fields)

    _, deriv_button, deriv_menu, _ = fields["deriv"]
    ctx.update(
        {
            "adv_derivada_button": deriv_button,
            "adv_derivada_menu": deriv_menu,
            "adv_derivada_checks": controls["deriv_checks"],
            "adv_derivada_has": None,
            "adv_derivada_is": None,
        }
    )

    for spec in ADVANCED_RESPONSAVEL_MULTISELECT_SPECS:
        box, button, menu, exclude = controls["responsavel_fields"][spec.field_key]
        _add_multiselect_context(ctx, spec.prefix, button, menu, exclude)
        ctx[f"{spec.prefix}_box"] = box
    return ctx

def _make_advanced_filter_panel_shell(self):
    group = QGroupBox("Filtros Avancados")
    _reset_advanced_menu_hooks(self)
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
    return group, outer, grid_container, grid_container_layout


def _make_advanced_filter_auxiliary_controls(self, fields, responsavel_fields, baseline):
    reprog_box, reprog_mode, reprog_button, reprog_menu = (
        _make_reprogramacoes_controls(self, baseline)
    )
    deriv_box, deriv_button, deriv_menu, _ = fields["deriv"]
    deriv_checks = _build_advanced_derivada_field(self, deriv_button, deriv_menu)
    week_emis_box, week_emissao_start, week_emissao_end = _make_week_range_box(
        "Emissao (AnoSemana)"
    )
    week_exec_box, week_exec_start, week_exec_end = _make_week_range_box(
        "Execucao (AnoSemana)"
    )
    macro_box, macro_combo = _make_advanced_macro_box(self)
    return {
        "reprog_box": reprog_box,
        "reprog_mode": reprog_mode,
        "reprog_button": reprog_button,
        "reprog_menu": reprog_menu,
        "deriv_box": deriv_box,
        "deriv_button": deriv_button,
        "deriv_menu": deriv_menu,
        "deriv_checks": deriv_checks,
        "week_emis_box": week_emis_box,
        "week_emissao_start": week_emissao_start,
        "week_emissao_end": week_emissao_end,
        "week_emissao_exclude": None,
        "week_exec_box": week_exec_box,
        "week_exec_start": week_exec_start,
        "week_exec_end": week_exec_end,
        "week_exec_exclude": None,
        "macro_box": macro_box,
        "macro_combo": macro_combo,
        "responsavel_fields": responsavel_fields,
    }


def _make_advanced_filter_panel_grid(self, outer, grid_container, grid_container_layout):
    main_grid = QGridLayout()
    main_grid.setContentsMargins(0, 0, 0, 0)
    main_grid.setHorizontalSpacing(4)
    main_grid.setVerticalSpacing(3)
    action_box, apply_btn, clear_btn = _make_advanced_action_box(self)
    grid_container_layout.addLayout(main_grid)
    controls_scroll = _configure_advanced_panel_scroll(self, outer, grid_container)
    return main_grid, action_box, apply_btn, clear_btn, controls_scroll


def _advanced_filter_grid_widgets(fields: dict, controls: dict, action_box) -> dict:
    emis_box, _, _, _ = fields["emis"]
    exec_box, _, _, _ = fields["exec"]
    status_box, _, _, _ = fields["status"]
    year_emissao_box, _, _, _ = fields["year_emissao"]
    year_execucao_box, _, _, _ = fields["year_execucao"]
    prio_emis_box, _, _, _ = fields["prio_emis"]
    prio_plan_box, _, _, _ = fields["prio_plan"]
    sol_box, _, _, _ = controls["responsavel_fields"]["sol"]
    prog_box, _, _, _ = controls["responsavel_fields"]["prog"]
    exec_resp_box, _, _, _ = controls["responsavel_fields"]["exec_resp"]
    return {
        "emis_box": emis_box,
        "exec_box": exec_box,
        "status_box": status_box,
        "year_emissao_box": year_emissao_box,
        "year_execucao_box": year_execucao_box,
        "reprog_box": controls["reprog_box"],
        "prio_emis_box": prio_emis_box,
        "prio_plan_box": prio_plan_box,
        "deriv_box": controls["deriv_box"],
        "macro_box": controls["macro_box"],
        "week_emis_box": controls["week_emis_box"],
        "week_exec_box": controls["week_exec_box"],
        "sol_box": sol_box,
        "prog_box": prog_box,
        "exec_resp_box": exec_resp_box,
        "action_box": action_box,
    }


def _advanced_filter_metric_controls_from_parts(parts: AdvancedFilterPanelParts):
    controls = parts.controls
    return _advanced_filter_metric_controls(
        parts.fields,
        controls["responsavel_fields"],
        reprog_mode=controls["reprog_mode"],
        reprog_button=controls["reprog_button"],
        week_emissao_start=controls["week_emissao_start"],
        week_emissao_end=controls["week_emissao_end"],
        week_exec_start=controls["week_exec_start"],
        week_exec_end=controls["week_exec_end"],
        macro_combo=controls["macro_combo"],
        apply_btn=parts.apply_btn,
        clear_btn=parts.clear_btn,
    )


def _register_advanced_filter_panel_state(self, parts: AdvancedFilterPanelParts):
    controls = parts.controls
    for spec in ADVANCED_STANDARD_MULTISELECT_SPECS:
        _, button, menu, exclude = parts.fields[spec.field_key]
        setattr(self, f"{spec.prefix}_button", button)
        setattr(self, f"{spec.prefix}_menu", menu)
        setattr(self, f"{spec.prefix}_checks", [])
        setattr(self, f"{spec.prefix}_exclude_checks", [])
        if exclude is not None:
            setattr(self, f"{spec.prefix}_exclude", exclude)
    self.adv_executor_button = parts.fields["exec"][1]
    self.adv_executor_checks = []
    self.adv_emissor_button = parts.fields["emis"][1]
    self.adv_emissor_checks = []
    self.adv_reprog_mode = controls["reprog_mode"]
    self.adv_reprog_button = controls["reprog_button"]
    self.adv_reprog_menu = controls["reprog_menu"]
    self.adv_reprog_checks = []
    self.adv_derivada_button = controls["deriv_button"]
    self.adv_derivada_menu = controls["deriv_menu"]
    self.adv_derivada_checks = controls["deriv_checks"]

    grid_widgets = _advanced_filter_grid_widgets(
        parts.fields,
        controls,
        parts.action_box,
    )
    metric_controls = _advanced_filter_metric_controls_from_parts(parts)
    state = AdvancedFilterPanelState(
        group=parts.group,
        main_grid=parts.main_grid,
        grid_widgets=grid_widgets,
        grid_order=tuple(grid_widgets),
        apply_btn=parts.apply_btn,
        clear_btn=parts.clear_btn,
        metric_controls=metric_controls,
        action_widget=parts.action_box,
        controls_scroll=parts.controls_scroll,
    )
    self._advanced_filter_panel_state = state

def _finalize_advanced_filter_panel_layout(self, group) -> None:
    if _is_not_deleted(group):
        _update_advanced_filters_action_buttons(self, group.width())
    _enforce_advanced_filters_compact_metrics(self)
    try:
        if _is_not_deleted(group):
            self._reorganize_advanced_filters_grid(group.width())
    except Exception as exc:
        logger.debug("Falha no relayout inicial dos filtros avancados: %s", exc)


def _create_advanced_filter_panel_parts(self) -> AdvancedFilterPanelParts:
    group, outer, grid_container, grid_container_layout = (
        _make_advanced_filter_panel_shell(self)
    )
    layout_baseline = _resolve_adv_layout_baseline(self)
    fields = _make_advanced_multiselect_fields(self, layout_baseline)
    responsavel_fields = _make_advanced_responsavel_fields(self, layout_baseline)
    controls = _make_advanced_filter_auxiliary_controls(
        self, fields, responsavel_fields, layout_baseline
    )
    main_grid, action_box, apply_btn, clear_btn, controls_scroll = (
        _make_advanced_filter_panel_grid(
            self, outer, grid_container, grid_container_layout
        )
    )
    return AdvancedFilterPanelParts(
        group=group,
        fields=fields,
        controls=controls,
        main_grid=main_grid,
        action_box=action_box,
        apply_btn=apply_btn,
        clear_btn=clear_btn,
        controls_scroll=controls_scroll,
    )


def _build_advanced_filters_panel(self):
    parts = _create_advanced_filter_panel_parts(self)
    _register_advanced_filter_panel_state(self, parts)
    _finalize_advanced_filter_panel_layout(self, parts.group)
    return parts.group, _build_advanced_filters_context_from_parts(parts)


def _ensure_macro_status_menu_ready(self) -> tuple[list[Any], list[Any]]:
    if getattr(self, "adv_status_checks", None):
        return (
            list(getattr(self, "adv_status_checks", None) or []),
            list(getattr(self, "adv_status_exclude_checks", None) or []),
        )
    cache = getattr(self, "_adv_values_cache", None)
    values = cache.get("values") if isinstance(cache, dict) else None
    status_values = getattr(values, "status_vals", None)
    if not status_values:
        return [], []
    filters = self._advanced_filters or {}
    _refresh_include_exclude_multiselect(
        self,
        prefix="adv_status",
        values=status_values,
        include_values=filters.get("situacao"),
        exclude_values=filters.get("situacao_exclude_values"),
    )
    return (
        list(getattr(self, "adv_status_checks", None) or []),
        list(getattr(self, "adv_status_exclude_checks", None) or []),
    )


def _show_derivadas_popup(self):
    """Compatibilidade de facade. Popup de derivadas foi removido."""
    return


def _update_derivadas_button_state(self):
    """Compatibilidade de facade. Nao ha botao de derivadas especificas."""
    return


def _save_advanced_filters_default(self):
    """Compatibilidade de facade. Acao removida da UI."""
    return


def _apply_macro_derivada_preset(self, preset: dict[str, tuple[str, ...]]) -> None:
    self._sync_multiselect_checks(
        getattr(self, "adv_derivada_button", None),
        getattr(self, "adv_derivada_checks", None),
        preset["derivada_include_values"],
    )


def _apply_macro_status_preset(self, preset: dict[str, tuple[str, ...]]) -> None:
    status_checks, status_exclude_checks = _ensure_macro_status_menu_ready(self)
    _sync_include_exclude_multiselect_checks(
        self,
        button=getattr(self, "adv_status_button", None),
        include_checks=status_checks,
        include_values=(),
        exclude_checks=status_exclude_checks,
        exclude_values=preset["situacao_exclude_values"],
    )
    _update_multiselect_button(
        self,
        getattr(self, "adv_status_button", None),
        status_checks,
        exclude_checks=status_exclude_checks,
    )


def _apply_advanced_macro_filter_preset(self, preset: dict[str, tuple[str, ...]]) -> None:
    try:
        _apply_macro_derivada_preset(self, preset)
    except Exception as exc:
        logger.warning("Falha ao aplicar preset de derivadas no macro filtro: %s", exc)
    try:
        _apply_macro_status_preset(self, preset)
    except Exception as exc:
        logger.warning("Falha ao aplicar preset de status no macro filtro: %s", exc)


def _on_macro_filter_changed(self):
    try:
        choice = self.adv_macro_combo.currentData()
    except Exception:
        choice = None
    if choice in {_MACRO_EXECUTADAS_SETOR_KEY, _MACRO_EXECUTADAS_DIVISAO_KEY}:
        _show_executadas_macro_dialog(self, str(choice))
        try:
            with QSignalBlocker(self.adv_macro_combo):
                self.adv_macro_combo.setCurrentIndex(0)
        except Exception as exc:
            logger.debug("Falha ao resetar macro de executadas apos abrir relatorio: %s", exc)
        return
    preset = advanced_macro_filter_preset(choice)
    if preset is not None:
        _apply_advanced_macro_filter_preset(self, preset)
        _apply_advanced_filters_from_ui(self)


def _reorganize_advanced_filters_grid(self, width: int):
    _reorganize_advanced_filters_grid_impl(self, width)


def _update_sector_filter_buttons(self, context: str = "") -> None:
    for prefix, label in (
        ("adv_executor", "setor executor"),
        ("adv_emissor", "setor emissor"),
    ):
        try:
            _update_multiselect_button(
                self,
                getattr(self, f"{prefix}_button"),
                getattr(self, f"{prefix}_checks"),
                exclude_checks=getattr(self, f"{prefix}_exclude_checks", None),
            )
        except Exception as exc:
            suffix = f" ({context})" if context else ""
            logger.warning("Falha ao atualizar botao de %s%s: %s", label, suffix, exc)


def _on_adv_sector_selection_changed(self, *_):
    state = _advanced_panel_state(self)
    if state is None:
        return
    if state.sector_syncing:
        return
    if state.sector_handler_running:
        return
    state.sector_handler_running = True
    try:
        self._apply_divisao_to_setor_checks()
        _update_sector_filter_buttons(self)
        self._schedule_sector_options_refresh()
    finally:
        state.sector_handler_running = False


def _on_adv_sector_exclude_changed(self, *_):
    """Atualiza filtros de exclusão de setor com debouncing."""
    state = _advanced_panel_state(self)
    if state is None:
        return
    if state.sector_syncing:
        return
    if state.sector_handler_running:
        return
    _update_sector_filter_buttons(self, context="exclude")
    self._schedule_sector_options_refresh()


def _schedule_sector_options_refresh(self):
    """Agenda refresh de opções dependentes de setor evitando rajadas de sinais."""
    timer = getattr(self, "_sector_debounce_timer", None)
    state = responsavel_materialization_state(self)
    built = state.built_prefixes
    if not built:
        self._mark_responsavel_dirty()
        try:
            if timer is not None and _is_not_deleted(timer):
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
        if _is_not_deleted(timer):
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
    return sector_sort_key(sector, SECTOR_TO_DIV)


def _sort_sectors(self, values):
    return order_sector_values(values, sector_to_div=SECTOR_TO_DIV)


def _sort_responsavel_values(self, df_subset, values, resp_col: str, df_source=None):
    return responsavel_options_refresher(self).sorted_values(
        df_subset,
        values,
        resp_col,
        df_source=df_source,
    )


def _apply_divisao_to_setor_checks(self):
    """Compatibilidade de facade. Filtro de divisao removido da UI."""
    return


def _refresh_responsavel_options(self, target_prefixes=None):
    responsavel_options_refresher(self).refresh(target_prefixes=target_prefixes)


def _clear_advanced_filters(self):
    try:
        self._store_last_filter_state()
    except Exception as exc:
        logger.warning(
            "Falha ao salvar estado antes de limpar filtros avancados: %s", exc
        )
    self._advanced_filters = {}
    self._advanced_filters_active = False
    responsavel_materialization_state(self).reset()
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
    if isinstance(data, dict) and data.get("macro_filter"):
        return True
    return has_active_advanced_filters(data)


def _read_advanced_filters_from_ui(self, previous_filters: dict) -> dict:
    widget_context = getattr(self, "_filter_panel_context", None)
    if not isinstance(widget_context, dict):
        widget_context = getattr(self, "_adv_ctx", None)
    return AdvancedFilterStateReader(
        widget_context=widget_context if isinstance(widget_context, dict) else {},
        current_filters=previous_filters,
        responsavel_state=responsavel_materialization_state(self),
        parse_week=self._parse_week,
    ).collect()


def _sync_quick_executor_from_advanced_filters(
    self, previous_filters: dict, data: dict
) -> None:
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


def _refresh_after_advanced_filters_apply(self) -> str | None:
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
    return notice_box["value"]


def _show_advanced_filter_notice(self, notice: str | None) -> None:
    if not notice:
        return
    try:
        if not hasattr(self, "update_filter_status_display"):
            return
        notice_suffix = ""
        if notice == "derivada_all_ste_empty":
            notice_suffix = "Aviso: nenhuma derivada STE/SES encontrada para o filtro."
        elif notice == "derivada_empty":
            notice_suffix = "Aviso: nenhuma derivada encontrada para o filtro."
        displayed_df = getattr(self, "df_exibido", None)
        complete_df = getattr(self, "df_completo", None)
        self.update_filter_status_display(
            filtered_total=len(displayed_df) if displayed_df is not None else None,
            original_total=len(complete_df) if complete_df is not None else None,
            search_text=None,
            suffix=notice_suffix,
        )
    except Exception as exc:
        logger.warning(
            "Falha ao atualizar status com aviso de derivadas apos filtro avancado: %s",
            exc,
        )


def _apply_advanced_filters_from_ui(self, store_only: bool = False):
    previous_filters = dict(getattr(self, "_advanced_filters", None) or {})
    if not store_only:
        try:
            self._store_last_filter_state()
        except Exception as exc:
            logger.warning(
                "Falha ao salvar estado antes de aplicar filtros avancados: %s", exc
            )
    data = _read_advanced_filters_from_ui(self, previous_filters)
    self._advanced_filters = data
    _sync_quick_executor_from_advanced_filters(self, previous_filters, data)
    self._advanced_filters_active = self._has_active_advanced_filters(data)
    if store_only:
        return
    notice = _refresh_after_advanced_filters_apply(self)
    _show_advanced_filter_notice(self, notice)


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
    if source is None:
        return []
    if isinstance(source, tuple):
        source = list(source)
    if isinstance(source, list):
        return _checked_values_from_checkboxes(source)
    if hasattr(source, "findChildren"):
        try:
            children = source.findChildren(QCheckBox)
        except Exception:
            children = []
        return _checked_values_from_checkboxes(children)
    return []


def _sync_advanced_filter_ui(self):
    sync_advanced_filter_ui(self)


def _refresh_sector_menus(self, exec_vals, emis_vals, status_vals, filters, apply_cb):
    _ = apply_cb
    _refresh_include_exclude_multiselect(
        self,
        prefix="adv_executor",
        values=exec_vals,
        include_values=filters.get("setor_executor"),
        exclude_values=filters.get("setor_executor_exclude_values"),
        on_change=self._on_adv_sector_selection_changed,
    )
    _refresh_include_exclude_multiselect(
        self,
        prefix="adv_emissor",
        values=emis_vals,
        include_values=filters.get("setor_emissor"),
        exclude_values=filters.get("setor_emissor_exclude_values"),
        on_change=self._on_adv_sector_selection_changed,
    )
    _refresh_include_exclude_multiselect(
        self,
        prefix="adv_status",
        values=status_vals,
        include_values=filters.get("situacao"),
        exclude_values=filters.get("situacao_exclude_values"),
    )


def _refresh_include_exclude_multiselect(
    self,
    *,
    prefix: str,
    values,
    include_values,
    exclude_values,
    on_change=None,
) -> bool:
    menu = getattr(self, f"{prefix}_menu", None)
    if menu is None:
        return False
    button = getattr(self, f"{prefix}_button", None)
    checks_attr = f"{prefix}_checks"
    exclude_checks_attr = f"{prefix}_exclude_checks"

    def update_summary(*_):
        _update_multiselect_button(self,
            button,
            getattr(self, checks_attr, None),
            exclude_checks=getattr(self, exclude_checks_attr, None),
        )

    callback = on_change if callable(on_change) else update_summary
    include_checks, exclude_checks = self._rebuild_multiselect_menu(
        button,
        menu,
        values,
        set(include_values or []),
        callback,
        True,
        set(exclude_values or []),
        callback,
    )
    setattr(self, checks_attr, include_checks)
    setattr(self, exclude_checks_attr, exclude_checks)
    callback()
    return True


def _refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb):
    _ = apply_cb
    for prefix, years, values_key, exclude_key, legacy_key, legacy_exclude in (
        (
            "adv_year_emissao",
            emissao_years,
            "ano_emissao_values",
            "ano_emissao_exclude_values",
            "ano_emissao",
            "ano_emissao_exclude",
        ),
        (
            "adv_year_execucao",
            execucao_years,
            "ano_execucao_values",
            "ano_execucao_exclude_values",
            "ano_execucao",
            "ano_execucao_exclude",
        ),
    ):
        year_values = [str(y) for y in years if y and str(y).strip()]
        inc_set, exc_set = resolve_year_selection_sets(
            filters,
            values_key=values_key,
            exclude_values_key=exclude_key,
            legacy_value_key=legacy_key,
            legacy_exclude_key=legacy_exclude,
        )
        _refresh_include_exclude_multiselect(
            self,
            prefix=prefix,
            values=year_values,
            include_values=inc_set,
            exclude_values=exc_set,
        )


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
            lambda *_: _update_multiselect_button(self,
                getattr(self, "adv_reprog_button", None),
                getattr(self, "adv_reprog_checks", None),
            ),
            False,
            None,
            None,
        )
        self.adv_reprog_checks = include_checks
        _update_multiselect_button(
            self,
            getattr(self, "adv_reprog_button", None),
            self.adv_reprog_checks,
        )
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
    if not selected and getattr(self, "adv_derivada_checks", None):
        selected = _collect_derivadas_selected_from_checks(self)
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
            lambda *_: _update_multiselect_button(
                self,
                getattr(self, "adv_derivada_button", None),
                getattr(self, "adv_derivada_checks", None),
                "Selecionar",
            ),
            False,
            None,
            None,
        )
        self.adv_derivada_checks = include_checks
        _update_multiselect_button(
            self,
            getattr(self, "adv_derivada_button", None),
            self.adv_derivada_checks,
            "Selecionar",
        )
    except Exception as exc:
        logger.debug("Failed to rebuild derivadas menu in advanced filter UI: %s", exc)
        self.adv_derivada_checks = []


def _refresh_priority_menus(
    self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
):
    _ = apply_cb
    for prefix, values, include_key, exclude_key in (
        (
            "adv_prioridade_emissao",
            prio_emissao_vals,
            "prioridade_emissao_values",
            "prioridade_emissao_exclude_values",
        ),
        (
            "adv_prioridade_planejamento",
            prio_planejamento_vals,
            "prioridade_planejamento_values",
            "prioridade_planejamento_exclude_values",
        ),
    ):
        _refresh_include_exclude_multiselect(
            self,
            prefix=prefix,
            values=values,
            include_values=filters.get(include_key),
            exclude_values=filters.get(exclude_key),
        )


def _refresh_advanced_filter_options(self):
    """Atualiza opcoes de filtros avancados com cache granular otimizado."""
    try:
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

        ui_state = _read_advanced_filter_ui_state(self, df, filters)
        cache = getattr(self, "_adv_values_cache", {})
        df_key = build_advanced_values_cache_key(df, getattr(self, "_data_load_token", None))

        if (
            cache.get("df_key") == df_key
            and not getattr(self, "_adv_options_dirty", False)
            and cache.get("values") is not None
        ):
            _apply_advanced_filter_ui_state(self, ui_state, apply_cb)
            return

        logger.debug(
            "_refresh_advanced_filter_options: cache pronto - exec=%s, emis=%s, status=%s",
            _safe_len(ui_state.values.exec_vals),
            _safe_len(ui_state.values.emis_vals),
            _safe_len(ui_state.values.status_vals),
        )
        _apply_advanced_filter_ui_state(self, ui_state, apply_cb)
        try:
            elapsed_ms = (perf_counter() - start) * 1000.0
            logger.debug("Advanced filter options refresh: %.1fms", elapsed_ms)
        except Exception as exc:
            logger.debug(
                "Failed to log advanced filter options refresh timing: %s", exc
            )
    finally:
        self._adv_options_scheduled = False


def _read_advanced_filter_ui_state(
    self, df: pd.DataFrame, filters: dict[str, Any]
) -> AdvancedFilterUIState:
    cache = getattr(self, "_adv_values_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        self._adv_values_cache = cache
    values = get_cached_advanced_filter_option_values(
        cache,
        df,
        data_load_token=getattr(self, "_data_load_token", None),
        sort_sectors=lambda values: _sort_sectors(self, values),
    )
    self._adv_values_cache = cache
    return AdvancedFilterUIState(filters=filters, values=values)


def _apply_advanced_filter_ui_state(self, ui_state, apply_cb) -> None:
    values = ui_state.values
    filters = ui_state.filters
    self._refresh_sector_menus(
        values.exec_vals,
        values.emis_vals,
        values.status_vals,
        filters,
        apply_cb,
    )
    self._refresh_year_menus(
        values.emissao_years,
        values.execucao_years,
        filters,
        apply_cb,
    )
    self._refresh_priority_menus(
        values.prio_emissao_vals,
        values.prio_planejamento_vals,
        filters,
        apply_cb,
    )
    self._refresh_reprogramacoes_menu(values.reprog_vals, filters, apply_cb)
    _refresh_derivadas_menu(self, filters, apply_cb)

    self._mark_responsavel_dirty()
    built_prefixes = responsavel_materialization_state(self).built_prefixes
    if built_prefixes:
        self._refresh_responsavel_options(target_prefixes=built_prefixes)
    else:
        self._sync_responsavel_button_summaries()
    self._sync_checks_to_tab_context()
    self._sync_advanced_filter_ui()
