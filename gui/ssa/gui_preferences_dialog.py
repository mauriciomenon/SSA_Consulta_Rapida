"""Montagem do dialogo de preferencias, separada das regras da janela."""

from __future__ import annotations

import copy
import logging
from collections.abc import Sequence
from functools import partial
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.pai_api_options import (
    PAI_API_ALLOWED_DATA_SCOPES,
    PAI_API_ALLOWED_SECTORS,
    PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES,
    normalize_pai_api_options,
    pai_api_data_scope_label,
)
from gui.gui_config import get_default_column_widths
from gui.ssa import main_window_system_controller as ssa_system_controller

logger = logging.getLogger(__name__)
_LABEL_ALIGNMENT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_IGNORED_SIZE_POLICY = QSizePolicy.Policy.Ignored


def open_preferences_dialog(
    window: Any,
    *,
    preferences: dict[str, Any],
    default_gui_settings: dict[str, Any],
    theme_items: Sequence[tuple[str, str]],
    alignment_labels: dict[str, str],
    default_alignment: str,
    footer_text: str,
) -> None:
    gui_settings = preferences.setdefault("gui_settings", {})
    dialog = QDialog(window)
    dialog.setWindowTitle("Preferencias")
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    content_scroll = QScrollArea()
    content_scroll.setObjectName("preferencesContentScroll")
    content_scroll.setWidgetResizable(True)
    content_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(8)
    content_scroll.setWidget(content_widget)
    layout.addWidget(content_scroll, 1)

    preferences_group_style = (
        "QGroupBox#preferencesInterfaceGroup,"
        "QGroupBox#preferencesBehaviorGroup,"
        "QGroupBox#preferencesPaiApiGroup {"
        "border:1px solid palette(mid);"
        "border-radius:6px;"
        "margin-top:8px;"
        "padding-top:8px;"
        "background:palette(alternate-base);"
        "}"
        "QGroupBox#preferencesTableGroup,"
        "QGroupBox#preferencesColumnWidthsGroup {"
        "border:1px solid palette(mid);"
        "border-radius:6px;"
        "margin-top:8px;"
        "padding-top:8px;"
        "background:palette(base);"
        "}"
        "QGroupBox::title {"
        "subcontrol-origin: margin;"
        "left: 8px;"
        "padding: 0 3px;"
        "}"
    )
    dialog.setStyleSheet(str(dialog.styleSheet() or "") + preferences_group_style)
    theme_roles = dict(getattr(window, "_current_theme_roles", {}) or {})
    support_text_color = (
        str(
            theme_roles.get("support_text_color")
            or theme_roles.get("label_color")
            or theme_roles.get("panel_text")
            or "#d7d9e6"
        ).strip()
        or "#d7d9e6"
    )
    footer_text_color = (
        str(
            theme_roles.get("panel_text")
            or theme_roles.get("label_color")
            or support_text_color
            or "#e6e7ee"
        ).strip()
        or "#e6e7ee"
    )
    state = _build_interface_section(
        window,
        content_layout,
        gui_settings,
        theme_items=theme_items,
        alignment_labels=alignment_labels,
        default_alignment=default_alignment,
    )
    state.update(_build_column_widths_section(window, content_layout, preferences))
    state.update(_build_behavior_section(content_layout, gui_settings))
    state.update(_build_api_section(content_layout, gui_settings, support_text_color))
    default_theme = str(default_gui_settings.get("theme", "classico") or "classico")
    default_search_mode = str(
        default_gui_settings.get("default_filter_mode", "contains") or "contains"
    )
    default_alignment = str(
        default_gui_settings.get("table_cell_alignment", default_alignment)
        or default_alignment
    )
    default_api_options = normalize_pai_api_options(
        default_gui_settings.get("pai_api", {})
    )
    runtime_default_widths = get_default_column_widths()
    neutral_extra_sector_status = (
        "Formato: IEE, MEL1, IEQ1. Somente 3 ou 4 letras/numeros ASCII por token."
    )
    state.update(
        {
            "default_gui_settings": default_gui_settings,
            "default_theme": default_theme,
            "default_search_mode": default_search_mode,
            "default_alignment": default_alignment,
            "default_api_options": default_api_options,
            "runtime_default_widths": runtime_default_widths,
            "neutral_extra_sector_status": neutral_extra_sector_status,
            "support_text_color": support_text_color,
            "gui_settings": gui_settings,
        }
    )
    _add_footer(window, dialog, layout, state, footer_text, footer_text_color)
    _connect_preferences_controls(window, state)

    accepted = window._execute_preferences_dialog(dialog, content_scroll)
    if not accepted:
        return
    if not window._validate_preferences_dialog_before_save(window, state):
        return
    window._apply_preferences_dialog_changes(state)


def _build_interface_section(
    window: Any,
    content_layout: QVBoxLayout,
    gui_settings: dict[str, Any],
    *,
    theme_items: Sequence[tuple[str, str]],
    alignment_labels: dict[str, str],
    default_alignment: str,
) -> dict[str, Any]:
    interface_group = QGroupBox("Interface")
    interface_group.setObjectName("preferencesInterfaceGroup")
    interface_layout = QVBoxLayout(interface_group)
    interface_layout.setContentsMargins(8, 8, 8, 8)
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(8)
    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 0)
    grid.setColumnStretch(3, 1)
    grid.setColumnStretch(4, 0)
    grid.setColumnStretch(5, 1)
    preferences_numeric_field_width = 120
    interface_first_column_field_width = 150
    theme_label = QLabel("Tema")
    grid.addWidget(theme_label, 0, 0, _LABEL_ALIGNMENT)
    theme_combo = QComboBox()
    theme_combo.setView(QListView(theme_combo))
    theme_combo.setObjectName("preferencesThemeCombo")
    theme_combo.setMaxVisibleItems(10)
    theme_combo.setFixedWidth(interface_first_column_field_width)
    theme_combo.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    current_theme = str(getattr(window, "_current_theme", "") or "")
    current_theme_index = -1
    for index, (theme_text, key) in enumerate(theme_items):
        theme_combo.addItem(theme_text, key)
        if key == current_theme:
            current_theme_index = index
    if current_theme_index >= 0:
        theme_combo.setCurrentIndex(current_theme_index)
    grid.addWidget(theme_combo, 0, 1)

    search_mode_label = QLabel("Modo da busca")
    grid.addWidget(search_mode_label, 0, 2, _LABEL_ALIGNMENT)
    search_mode_combo = QComboBox()
    search_mode_combo.setView(QListView(search_mode_combo))
    search_mode_combo.setObjectName("preferencesSearchModeCombo")
    search_mode_combo.setMinimumWidth(120)
    search_mode_combo.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    search_mode_combo.setToolTip(
        "Define como a busca superior interpreta termos sem prefixo explicito"
    )
    mode_items = [
        ("Contem", "contains"),
        ("Comeca com", "prefix"),
        ("Termina com", "suffix"),
        ("Igual", "exact"),
        ("Regex", "regex"),
    ]
    current_search_mode = str(
        gui_settings.get("default_filter_mode", "contains") or "contains"
    ).strip()
    current_search_mode_index = 0
    for index, (mode_text, key) in enumerate(mode_items):
        search_mode_combo.addItem(mode_text, key)
        if key == current_search_mode:
            current_search_mode_index = index
    search_mode_combo.setCurrentIndex(current_search_mode_index)
    grid.addWidget(search_mode_combo, 0, 3)

    debounce_label = QLabel("Debounce ms")
    grid.addWidget(debounce_label, 0, 4, _LABEL_ALIGNMENT)
    debounce_spin = QSpinBox()
    debounce_spin.setObjectName("preferencesDebounceSpin")
    debounce_spin.setMaximumWidth(preferences_numeric_field_width)
    debounce_spin.setToolTip("Atraso antes de aplicar a busca superior")
    debounce_spin.setRange(
        int(getattr(ssa_system_controller, "SEARCH_DEBOUNCE_MIN_MS", 100)),
        int(getattr(ssa_system_controller, "SEARCH_DEBOUNCE_MAX_MS", 5000)),
    )
    debounce_spin.setSingleStep(50)
    debounce_spin.setValue(
        int(
            gui_settings.get(
                "debounce_delay",
                getattr(ssa_system_controller, "SEARCH_DEBOUNCE_DEFAULT_MS", 250),
            )
            or getattr(ssa_system_controller, "SEARCH_DEBOUNCE_DEFAULT_MS", 250)
        )
    )
    grid.addWidget(debounce_spin, 0, 5)

    page_size_label = QLabel("Linhas por pagina")
    grid.addWidget(page_size_label, 1, 0, _LABEL_ALIGNMENT)
    page_size_spin = QSpinBox()
    page_size_spin.setObjectName("preferencesPageSizeSpin")
    page_size_spin.setFixedWidth(interface_first_column_field_width)
    page_size_spin.setRange(10, 500)
    page_size_spin.setSingleStep(10)
    page_size_spin.setValue(int(getattr(window, "_restored_page_size", 50) or 50))
    grid.addWidget(page_size_spin, 1, 1)

    window_width_label = QLabel("Largura da janela")
    grid.addWidget(window_width_label, 1, 2, _LABEL_ALIGNMENT)
    window_width_spin = QSpinBox()
    window_width_spin.setObjectName("preferencesWindowWidthSpin")
    window_width_spin.setMaximumWidth(preferences_numeric_field_width)
    window_width_spin.setRange(960, 2800)
    window_width_spin.setSingleStep(20)
    window_width_spin.setValue(
        int(getattr(window, "_restored_window_width", 1200) or 1200)
    )
    grid.addWidget(window_width_spin, 1, 3)

    window_height_label = QLabel("Altura da janela")
    grid.addWidget(window_height_label, 1, 4, _LABEL_ALIGNMENT)
    window_height_spin = QSpinBox()
    window_height_spin.setObjectName("preferencesWindowHeightSpin")
    window_height_spin.setMaximumWidth(preferences_numeric_field_width)
    window_height_spin.setRange(720, 1800)
    window_height_spin.setSingleStep(20)
    window_height_spin.setValue(
        int(getattr(window, "_restored_window_height", 890) or 890)
    )
    grid.addWidget(window_height_spin, 1, 5)

    alignment_label = QLabel("Alinhamento da tabela")
    grid.addWidget(alignment_label, 2, 0, _LABEL_ALIGNMENT)
    alignment_combo = QComboBox()
    alignment_combo.setView(QListView(alignment_combo))
    alignment_combo.setObjectName("preferencesAlignmentCombo")
    alignment_combo.setFixedWidth(interface_first_column_field_width)
    alignment_combo.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    current_alignment = str(
        gui_settings.get("table_cell_alignment", default_alignment) or default_alignment
    )
    current_alignment_index = 0
    for index, (key, alignment_text) in enumerate(alignment_labels.items()):
        alignment_combo.addItem(alignment_text, key)
        if key == current_alignment:
            current_alignment_index = index
    alignment_combo.setCurrentIndex(current_alignment_index)
    grid.addWidget(alignment_combo, 2, 1)

    cache_size_label = QLabel("Cache de filtros")
    grid.addWidget(cache_size_label, 2, 2, _LABEL_ALIGNMENT)
    cache_size_spin = QSpinBox()
    cache_size_spin.setObjectName("preferencesCacheSizeSpin")
    cache_size_spin.setMaximumWidth(preferences_numeric_field_width)
    cache_size_spin.setRange(10, 500)
    cache_size_spin.setSingleStep(10)
    cache_size_spin.setValue(int(gui_settings.get("filter_cache_size", 50) or 50))
    cache_size_spin.setToolTip(
        "Quantidade maxima de entradas reaproveitadas nos filtros"
    )
    grid.addWidget(cache_size_spin, 2, 3)

    columns_label = QLabel("Colunas exibidas")
    grid.addWidget(columns_label, 2, 4, _LABEL_ALIGNMENT)
    columns_button = QPushButton("Colunas")
    columns_button.setObjectName("preferencesColumnsButton")
    columns_button.setMinimumWidth(100)
    columns_button.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    columns_button.setToolTip(
        "Abrir configuracao de colunas visiveis e larguras da tabela"
    )
    grid.addWidget(columns_button, 2, 5)
    for label in (
        theme_label,
        search_mode_label,
        debounce_label,
        page_size_label,
        window_width_label,
        window_height_label,
        alignment_label,
        cache_size_label,
        columns_label,
    ):
        label.setWordWrap(True)
        label.setSizePolicy(
            _IGNORED_SIZE_POLICY,
            QSizePolicy.Policy.Fixed,
        )
    interface_layout.addLayout(grid)
    content_layout.addWidget(interface_group)
    return {
        "current_theme": current_theme,
        "current_search_mode": current_search_mode,
        "current_alignment": current_alignment,
        "theme_combo": theme_combo,
        "search_mode_combo": search_mode_combo,
        "debounce_spin": debounce_spin,
        "page_size_spin": page_size_spin,
        "window_width_spin": window_width_spin,
        "window_height_spin": window_height_spin,
        "alignment_combo": alignment_combo,
        "cache_size_spin": cache_size_spin,
        "columns_button": columns_button,
    }


def _build_column_widths_section(
    window: Any, content_layout: QVBoxLayout, preferences: dict[str, Any]
) -> dict[str, Any]:
    table_display_columns = list(getattr(window, "_current_display_columns", []) or [])
    current_display_columns = [
        col for col in table_display_columns if str(col or "") != "#"
    ]
    current_column_index = {
        str(col_name): idx
        for idx, col_name in enumerate(table_display_columns)
        if str(col_name or "") != "#"
    }
    persisted_column_widths = preferences.setdefault("column_widths", {})
    width_spinboxes: dict[str, QSpinBox] = {}

    def _current_width_for_column(col_name: str) -> int:
        col_key = str(col_name or "")
        idx = current_column_index.get(col_key)
        if idx is not None and hasattr(window, "table_widget"):
            try:
                width = int(window.table_widget.columnWidth(idx))
                if width > 0:
                    return width
            except Exception as exc:
                logger.debug(
                    "Falha ao ler largura atual da coluna %s nas preferencias: %s",
                    col_key,
                    exc,
                )
        try:
            return int(persisted_column_widths.get(col_key, 120) or 120)
        except Exception:
            return 120

    table_group = QGroupBox("Tabela e colunas exibidas")
    table_group.setObjectName("preferencesTableGroup")
    table_layout = QVBoxLayout(table_group)
    table_layout.setContentsMargins(8, 8, 8, 8)
    table_layout.setSpacing(6)
    widths_group = QGroupBox("Larguras de colunas")
    widths_group.setObjectName("preferencesColumnWidthsGroup")
    widths_layout = QVBoxLayout(widths_group)
    widths_layout.setContentsMargins(8, 8, 8, 8)
    widths_layout.setSpacing(6)
    widths_container = QWidget()
    widths_grid = QGridLayout(widths_container)
    widths_grid.setContentsMargins(0, 0, 0, 0)
    widths_grid.setHorizontalSpacing(8)
    widths_grid.setVerticalSpacing(8)
    for offset, col_name in enumerate(current_display_columns):
        label = QLabel(str(window.internal_to_display.get(col_name, col_name)))
        label.setObjectName(f"preferencesColumnWidthLabel_{col_name}")
        spin = QSpinBox()
        spin.setObjectName(f"preferencesColumnWidthSpin_{col_name}")
        spin.setMaximumWidth(132)
        spin.setRange(30, 1000)
        spin.setSingleStep(5)
        spin.setValue(_current_width_for_column(str(col_name)))
        width_spinboxes[str(col_name)] = spin
        row = offset // 3
        base_col = (offset % 3) * 2
        widths_grid.addWidget(label, row, base_col, _LABEL_ALIGNMENT)
        widths_grid.addWidget(spin, row, base_col + 1)
    for col in (1, 3, 5):
        widths_grid.setColumnStretch(col, 1)
    widths_layout.addWidget(widths_container)
    table_layout.addWidget(widths_group)
    content_layout.addWidget(table_group)
    return {
        "current_column_index": current_column_index,
        "width_spinboxes": width_spinboxes,
    }


def _build_behavior_section(
    content_layout: QVBoxLayout, gui_settings: dict[str, Any]
) -> dict[str, Any]:
    behavior_group = QGroupBox("Cache e comportamento")
    behavior_group.setObjectName("preferencesBehaviorGroup")
    behavior_layout = QVBoxLayout(behavior_group)
    behavior_layout.setContentsMargins(8, 8, 8, 8)
    toggles_layout = QGridLayout()
    toggles_layout.setContentsMargins(0, 6, 0, 0)
    toggles_layout.setSpacing(6)

    auto_load_checkbox = QCheckBox("Carregar dados do banco ao iniciar")
    auto_load_checkbox.setObjectName("preferencesAutoLoadCheck")
    auto_load_checkbox.setChecked(bool(gui_settings.get("auto_load", False)))
    toggles_layout.addWidget(auto_load_checkbox, 0, 0)

    show_progress_checkbox = QCheckBox("Mostrar progresso na barra superior")
    show_progress_checkbox.setObjectName("preferencesShowProgressCheck")
    show_progress_checkbox.setChecked(bool(gui_settings.get("show_progress_bar", True)))
    toggles_layout.addWidget(show_progress_checkbox, 0, 1)

    enable_sort_checkbox = QCheckBox("Permitir ordenacao por clique no cabecalho")
    enable_sort_checkbox.setObjectName("preferencesColumnSortingCheck")
    enable_sort_checkbox.setChecked(
        bool(gui_settings.get("enable_column_sorting", True))
    )
    toggles_layout.addWidget(enable_sort_checkbox, 0, 2)

    show_details_checkbox = QCheckBox("Mostrar detalhes")
    show_details_checkbox.setObjectName("preferencesShowDetailsCheck")
    show_details_checkbox.setChecked(bool(gui_settings.get("show_details_panel", True)))
    toggles_layout.addWidget(show_details_checkbox, 1, 0)

    double_click_checkbox = QCheckBox("Duplo clique abre detalhes")
    double_click_checkbox.setObjectName("preferencesDoubleClickDetailsCheck")
    double_click_checkbox.setChecked(
        bool(gui_settings.get("enable_double_click_details", True))
    )
    toggles_layout.addWidget(double_click_checkbox, 1, 1)

    cache_enabled_checkbox = QCheckBox("Usar cache de filtros")
    cache_enabled_checkbox.setObjectName("preferencesCacheEnabledCheck")
    cache_enabled_checkbox.setChecked(bool(gui_settings.get("cache_enabled", True)))
    toggles_layout.addWidget(cache_enabled_checkbox, 1, 2)

    cache_auto_clear_checkbox = QCheckBox("Limpar cache ao recarregar dados")
    cache_auto_clear_checkbox.setObjectName("preferencesCacheAutoClearCheck")
    cache_auto_clear_checkbox.setChecked(
        bool(gui_settings.get("cache_auto_clear", False))
    )
    toggles_layout.addWidget(cache_auto_clear_checkbox, 2, 0, 1, 2)

    behavior_layout.addLayout(toggles_layout)
    content_layout.addWidget(behavior_group)
    return {
        "auto_load_checkbox": auto_load_checkbox,
        "show_progress_checkbox": show_progress_checkbox,
        "enable_sort_checkbox": enable_sort_checkbox,
        "show_details_checkbox": show_details_checkbox,
        "double_click_checkbox": double_click_checkbox,
        "cache_enabled_checkbox": cache_enabled_checkbox,
        "cache_auto_clear_checkbox": cache_auto_clear_checkbox,
    }


def _build_api_section(
    content_layout: QVBoxLayout, gui_settings: dict[str, Any], support_text_color: str
) -> dict[str, Any]:
    api_group = QGroupBox("SAM API")
    api_group.setObjectName("preferencesPaiApiGroup")
    api_layout = QGridLayout(api_group)
    api_layout.setContentsMargins(8, 8, 8, 8)
    api_layout.setSpacing(6)
    for col in (1, 3, 5):
        api_layout.setColumnStretch(col, 1)
    api_settings = copy.deepcopy(gui_settings.get("pai_api", {}))
    api_options = normalize_pai_api_options(api_settings)

    api_enabled_checkbox = QCheckBox("SAM API habilitada")
    api_enabled_checkbox.setObjectName("preferencesPaiApiEnabledCheck")
    api_enabled_checkbox.setChecked(bool(api_options.enabled))
    api_layout.addWidget(api_enabled_checkbox, 0, 0, 1, 2)

    api_scrap_checkbox = QCheckBox("Consulta via xpath/scrap_report")
    api_scrap_checkbox.setObjectName("preferencesPaiApiScrapCheck")
    api_scrap_checkbox.setChecked(bool(api_options.scrap_report_enabled))
    api_layout.addWidget(api_scrap_checkbox, 0, 2, 1, 2)

    api_auto_refresh_checkbox = QCheckBox("Atualizacao automatica")
    api_auto_refresh_checkbox.setObjectName("preferencesPaiApiAutoRefreshCheck")
    api_auto_refresh_checkbox.setChecked(bool(api_options.auto_refresh_enabled))
    api_layout.addWidget(api_auto_refresh_checkbox, 0, 4, 1, 2)

    api_security_info_text = (
        "Consulta REST nao exige credencial. Cofre do sistema so vale para "
        "escopos via xpath/scrap_report. macOS: Keychain | Windows: "
        "Credential Manager ou DPAPI | Linux: Secret Service."
    )
    api_security_info_warning = (
        api_security_info_text
        + " Aviso: desativar 'Exigir cofre do sistema' reduz a garantia de "
        "armazenamento protegido do segredo."
    )
    api_security_info = QLabel(api_security_info_text)
    api_security_info.setObjectName("preferencesPaiApiSecurityInfoLabel")
    api_security_info.setWordWrap(True)
    api_security_info.setSizePolicy(
        _IGNORED_SIZE_POLICY,
        QSizePolicy.Policy.Fixed,
    )
    api_security_info.setStyleSheet(
        f"color: {support_text_color}; border:1px solid palette(mid);"
        "border-radius:4px; padding:4px 6px;"
    )
    api_layout.addWidget(api_security_info, 1, 0, 1, 6)

    api_layout.addWidget(QLabel("Intervalo (min)"), 2, 0)
    api_interval_spin = QSpinBox()
    api_interval_spin.setObjectName("preferencesPaiApiIntervalSpin")
    api_interval_spin.setRange(1, PAI_API_MAX_AUTO_REFRESH_INTERVAL_MINUTES)
    api_interval_spin.setValue(int(api_options.auto_refresh_interval_minutes))
    api_layout.addWidget(api_interval_spin, 2, 1)

    api_layout.addWidget(QLabel("Limite por setor"), 2, 2)
    api_limit_spin = QSpinBox()
    api_limit_spin.setObjectName("preferencesPaiApiLimitSpin")
    api_limit_spin.setRange(1, 1000)
    api_limit_spin.setValue(int(api_options.limit))
    api_layout.addWidget(api_limit_spin, 2, 3)

    api_layout.addWidget(QLabel("Anos retroativos"), 2, 4)
    api_years_spin = QSpinBox()
    api_years_spin.setObjectName("preferencesPaiApiYearsSpin")
    api_years_spin.setRange(1, 10)
    api_years_spin.setValue(int(api_options.number_of_years))
    api_layout.addWidget(api_years_spin, 2, 5)

    api_layout.addWidget(QLabel("Base URL REST"), 3, 0)
    api_base_url_edit = QLineEdit()
    api_base_url_edit.setObjectName("preferencesPaiApiBaseUrlEdit")
    api_base_url_edit.setText(str(api_options.base_url or ""))
    api_layout.addWidget(api_base_url_edit, 3, 1, 1, 5)

    api_layout.addWidget(QLabel("Usuario SAM"), 4, 0)
    api_username_edit = QLineEdit()
    api_username_edit.setObjectName("preferencesPaiApiUsernameEdit")
    api_username_edit.setText(str(api_options.username or ""))
    api_layout.addWidget(api_username_edit, 4, 1)

    api_layout.addWidget(QLabel("Chave do cofre"), 4, 2)
    api_secret_service_edit = QLineEdit()
    api_secret_service_edit.setObjectName("preferencesPaiApiSecretServiceEdit")
    api_secret_service_edit.setText(str(api_options.secret_service or ""))
    api_layout.addWidget(api_secret_service_edit, 4, 3, 1, 3)

    api_layout.addWidget(QLabel("Senha SAM para gravar no cofre"), 5, 0)
    api_password_edit = QLineEdit()
    api_password_edit.setObjectName("preferencesPaiApiPasswordEdit")
    try:
        api_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
    except Exception as exc:
        logger.debug("Falha ao aplicar modo senha no campo SAM API: %s", exc)
    api_password_edit.setPlaceholderText("Senha apenas para gravar no cofre")
    api_layout.addWidget(api_password_edit, 5, 1, 1, 3)

    api_secure_required_checkbox = QCheckBox("Exigir cofre do sistema")
    api_secure_required_checkbox.setObjectName("preferencesPaiApiSecureRequiredCheck")
    api_secure_required_checkbox.setChecked(bool(api_options.secure_required))
    api_layout.addWidget(api_secure_required_checkbox, 5, 4, 1, 2)

    api_secret_actions = QHBoxLayout()
    api_secret_actions.setContentsMargins(0, 0, 0, 0)
    api_secret_actions.setSpacing(6)
    api_secret_validate_button = QPushButton("Validar segredo no cofre")
    api_secret_validate_button.setObjectName("preferencesPaiApiValidateSecretButton")
    api_secret_store_button = QPushButton("Gravar segredo no cofre")
    api_secret_store_button.setObjectName("preferencesPaiApiStoreSecretButton")
    api_secret_actions.addWidget(api_secret_validate_button)
    api_secret_actions.addWidget(api_secret_store_button)
    api_secret_actions.addStretch(1)
    api_layout.addLayout(api_secret_actions, 6, 0, 1, 6)
    state = {
        "api_enabled_checkbox": api_enabled_checkbox,
        "api_scrap_checkbox": api_scrap_checkbox,
        "api_auto_refresh_checkbox": api_auto_refresh_checkbox,
        "api_security_info": api_security_info,
        "api_security_info_text": api_security_info_text,
        "api_security_info_warning": api_security_info_warning,
        "api_interval_spin": api_interval_spin,
        "api_limit_spin": api_limit_spin,
        "api_years_spin": api_years_spin,
        "api_base_url_edit": api_base_url_edit,
        "api_username_edit": api_username_edit,
        "api_secret_service_edit": api_secret_service_edit,
        "api_secure_required_checkbox": api_secure_required_checkbox,
        "api_secret_validate_button": api_secret_validate_button,
        "api_secret_store_button": api_secret_store_button,
        "api_password_edit": api_password_edit,
    }
    state.update(
        _build_api_scope_selection(api_layout, api_options, support_text_color)
    )
    content_layout.addWidget(api_group)
    return state


def _build_api_scope_selection(
    api_layout: QGridLayout, api_options: Any, support_text_color: str
) -> dict[str, Any]:
    selected_scopes = {value.casefold() for value in api_options.data_scopes}
    scope_checks: dict[str, QCheckBox] = {}
    api_layout.addWidget(QLabel("Tipos de dados"), 7, 0)
    scope_start_row = 8
    for offset, scope in enumerate(PAI_API_ALLOWED_DATA_SCOPES):
        checkbox = QCheckBox(pai_api_data_scope_label(scope))
        checkbox.setObjectName(f"preferencesPaiApiScope_{scope}")
        checkbox.setChecked(scope.casefold() in selected_scopes)
        scope_checks[scope] = checkbox
        api_layout.addWidget(
            checkbox,
            scope_start_row + offset // 3,
            (offset % 3) * 2,
            1,
            2,
        )

    selected_sectors = {value.casefold() for value in api_options.executor_sectors}
    sector_checks: dict[str, QCheckBox] = {}
    scope_rows = max(1, (len(PAI_API_ALLOWED_DATA_SCOPES) + 2) // 3)
    sector_label_row = scope_start_row + scope_rows
    sector_start_row = sector_label_row + 1
    api_layout.addWidget(QLabel("Setores executores"), sector_label_row, 0)
    for offset, sector in enumerate(PAI_API_ALLOWED_SECTORS):
        checkbox = QCheckBox(sector)
        checkbox.setObjectName(f"preferencesPaiApiSector_{sector}")
        checkbox.setChecked(sector.casefold() in selected_sectors)
        sector_checks[sector] = checkbox
        api_layout.addWidget(
            checkbox,
            sector_start_row + offset // 3,
            (offset % 3) * 2,
            1,
            2,
        )

    sector_rows = max(1, (len(PAI_API_ALLOWED_SECTORS) + 2) // 3)
    extras_row = sector_start_row + sector_rows
    api_layout.addWidget(QLabel("Setores extras (SAM API)"), extras_row, 0)
    api_extra_sectors_edit = QLineEdit()
    api_extra_sectors_edit.setObjectName("preferencesPaiApiExtraSectorsEdit")
    api_extra_sectors_edit.setPlaceholderText("Ex.: IEQ1, MEL5")
    api_extra_sectors_edit.setToolTip(
        "Setores adicionais usados apenas pela SAM API. Nao afeta importacao XLS."
    )
    api_extra_sectors_edit.setText(", ".join(api_options.executor_sectors_extra))
    api_layout.addWidget(api_extra_sectors_edit, extras_row, 1, 1, 5)
    api_extra_sectors_status = QLabel(
        "Formato: IEE, MEL1, IEQ1. Somente 3 ou 4 letras/numeros ASCII por token."
    )
    api_extra_sectors_status.setObjectName(
        "preferencesPaiApiExtraSectorsValidationLabel"
    )
    api_extra_sectors_status.setWordWrap(True)
    api_extra_sectors_status.setStyleSheet(
        f"color: {support_text_color}; background: transparent;"
    )
    api_layout.addWidget(api_extra_sectors_status, extras_row + 1, 1, 1, 5)
    return {
        "scope_checks": scope_checks,
        "sector_checks": sector_checks,
        "api_extra_sectors_edit": api_extra_sectors_edit,
        "api_extra_sectors_status": api_extra_sectors_status,
    }


def _add_footer(
    window: Any,
    dialog: QDialog,
    layout: QVBoxLayout,
    state: dict[str, Any],
    footer_text: str,
    footer_text_color: str,
) -> None:
    defaults_button = QPushButton("Restaurar padrao")
    defaults_button.setObjectName("preferencesRestoreDefaultsButton")
    defaults_button.clicked.connect(
        partial(
            window._restore_preferences_dialog_defaults,
            state,
            state["api_password_edit"],
        )
    )
    footer_label = QLabel(footer_text)
    footer_label.setObjectName("preferencesFooterLabel")
    footer_label.setStyleSheet(
        f"color: {footer_text_color}; background: transparent; font-weight:600;"
    )
    footer_label.setWordWrap(True)
    footer_label.setSizePolicy(
        _IGNORED_SIZE_POLICY,
        QSizePolicy.Policy.Fixed,
    )

    button_flags = QDialogButtonBox.StandardButton.Ok
    button_flags = button_flags | QDialogButtonBox.StandardButton.Cancel
    buttons = QDialogButtonBox(button_flags)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    footer_row = QHBoxLayout()
    footer_row.setContentsMargins(0, 6, 0, 0)
    footer_row.setSpacing(8)
    footer_row.addWidget(defaults_button)
    footer_row.addWidget(footer_label, 1)
    footer_row.addWidget(buttons)
    layout.addLayout(footer_row)


def _connect_preferences_controls(window: Any, state: dict[str, Any]) -> None:
    state["api_secret_validate_button"].clicked.connect(
        partial(window._validate_preferences_secret, state)
    )
    state["api_secret_store_button"].clicked.connect(
        partial(
            window._store_preferences_secret,
            state,
            state["api_password_edit"],
        )
    )
    sync_secret_controls = partial(
        window._sync_preferences_api_secret_controls,
        state,
        state["api_password_edit"],
    )
    for checkbox in (
        state["api_scrap_checkbox"],
        state["api_secure_required_checkbox"],
        *state["scope_checks"].values(),
    ):
        checkbox.toggled.connect(sync_secret_controls)
    for line_edit in (state["api_username_edit"], state["api_secret_service_edit"]):
        line_edit.textChanged.connect(sync_secret_controls)
    wheel_guard_widgets = (
        state["theme_combo"],
        state["search_mode_combo"],
        state["debounce_spin"],
        state["page_size_spin"],
        state["window_width_spin"],
        state["window_height_spin"],
        state["alignment_combo"],
        state["cache_size_spin"],
        state["api_interval_spin"],
        state["api_limit_spin"],
        state["api_years_spin"],
        *state["width_spinboxes"].values(),
    )
    window._apply_preferences_wheel_guards(wheel_guard_widgets)
    window._apply_preferences_combo_popup_styles(
        (state["theme_combo"], state["search_mode_combo"], state["alignment_combo"])
    )
    state["api_extra_sectors_edit"].textChanged.connect(
        partial(window._on_preferences_extra_sectors_changed, state)
    )
    window._on_preferences_extra_sectors_changed(state, "")
    window._sync_preferences_api_secret_controls(state, state["api_password_edit"])
    selector = getattr(window, "column_selector", None)
    if selector is not None:
        state["columns_button"].clicked.connect(selector.open_dialog)
    else:
        state["columns_button"].setEnabled(False)
