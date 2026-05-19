"""Application menu construction for the SSA main window."""

from __future__ import annotations

import os
from typing import Any

from core.pai_api_options import (
    PAI_API_ALLOWED_SECTORS,
    PAI_API_SETTINGS_KEY,
    normalize_pai_api_options,
)


def setup_app_menus(
    window: Any,
    *,
    action_cls: Any,
    preferences: dict[str, Any],
    project_root: str,
    default_table_alignment: str,
    table_alignment_labels: dict[str, str],
) -> None:
    menu_bar_getter = getattr(window, "menuBar", None)
    if not callable(menu_bar_getter):
        return
    menu_bar = menu_bar_getter()
    if menu_bar is None or not hasattr(menu_bar, "addMenu"):
        return

    arquivo_menu = menu_bar.addMenu("Arquivo")
    importacao_menu = menu_bar.addMenu("Importacao")
    db_menu = menu_bar.addMenu("Database")
    opcoes_menu = menu_bar.addMenu("Opcoes")
    ajuda_menu = menu_bar.addMenu("Ajuda")

    _add_action(arquivo_menu, action_cls, window, "Exportar lista", window._export_current_list_txt)
    _add_action(arquivo_menu, action_cls, window, "Sair", window.close)

    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Importar XLSX externo",
        window.import_external_excel_files,
    )
    _add_action(importacao_menu, action_cls, window, "Atualizar Dados", window.rescan_diff_data)
    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Reescaneamento Completo",
        window.rescan_full_data,
    )
    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Abrir Pasta de Arquivos",
        window.open_docs_folder,
        status_tip=f"Pasta atual de entrada: {os.path.join(project_root, 'docs_entrada')}",
    )
    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Abrir Pasta Arquivos Processados",
        window.open_processadas_folder,
    )
    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Abrir Pasta Arquivos Redundantes",
        window.open_nosurvivor_folder,
    )
    _add_action(
        importacao_menu,
        action_cls,
        window,
        "Consolidar arquivos de entrada",
        window.consolidate_input_files,
    )

    _add_action(db_menu, action_cls, window, "Reescanear", window.rescan_data)
    _add_action(
        db_menu,
        action_cls,
        window,
        "Atualizar derivadas",
        window.update_derivadas_from_sources,
    )
    _add_action(db_menu, action_cls, window, "Carregar outro DB", window.load_other_database)
    _add_action(db_menu, action_cls, window, "Compactar DB", window.run_vacuum_analyze)

    _add_action(
        opcoes_menu,
        action_cls,
        window,
        "Abrir arquivo de opcoes",
        window.open_settings_file_with_backup,
    )
    _add_action(
        opcoes_menu,
        action_cls,
        window,
        "Restaurar opcoes padrao",
        window.reset_settings_to_defaults,
    )
    _add_action(opcoes_menu, action_cls, window, "Limpar Filtros", window._hard_reset_filters_state)

    _add_alignment_menu(
        window,
        opcoes_menu,
        action_cls=action_cls,
        preferences=preferences,
        default_table_alignment=default_table_alignment,
        table_alignment_labels=table_alignment_labels,
    )

    _add_pai_api_menu(window, opcoes_menu, action_cls, preferences=preferences)

    _add_action(opcoes_menu, action_cls, window, "Selecionar Tema", window.toggle_theme_menu)
    _add_action(ajuda_menu, action_cls, window, "Instalacao", window.open_installation_guide)
    _add_action(ajuda_menu, action_cls, window, "Ajuda", window.show_filter_help)

    about_handler = getattr(window, "show_about_dialog", None)
    if callable(about_handler):
        _add_action(ajuda_menu, action_cls, window, "Sobre", about_handler)


def _add_action(
    menu: Any,
    action_cls: Any,
    window: Any,
    label: str,
    callback: Any,
    *,
    status_tip: str | None = None,
) -> Any:
    action = action_cls(label, window)
    if status_tip:
        set_status_tip = getattr(action, "setStatusTip", None)
        if callable(set_status_tip):
            set_status_tip(status_tip)
    action.triggered.connect(callback)
    menu.addAction(action)
    return action


def _add_alignment_menu(
    window: Any,
    opcoes_menu: Any,
    *,
    action_cls: Any,
    preferences: dict[str, Any],
    default_table_alignment: str,
    table_alignment_labels: dict[str, str],
) -> None:
    alignment_menu = opcoes_menu.addMenu("Alinhamento da tabela")
    current_alignment = str(
        preferences.get("gui_settings", {})
        .get("table_cell_alignment", default_table_alignment)
        .strip()
        .lower()
    )
    window._table_cell_alignment_actions = {}
    for alignment_name, label in table_alignment_labels.items():
        alignment_action = action_cls(label, window)
        alignment_action.setCheckable(True)
        alignment_action.setChecked(alignment_name == current_alignment)
        alignment_action.triggered.connect(
            lambda _checked, name=alignment_name: (
                window._apply_table_cell_alignment_preference(name)
            )
        )
        alignment_menu.addAction(alignment_action)
        window._table_cell_alignment_actions[alignment_name] = alignment_action


def _add_pai_api_menu(
    window: Any,
    opcoes_menu: Any,
    action_cls: Any,
    *,
    preferences: dict[str, Any],
) -> None:
    pai_menu = opcoes_menu.addMenu("API PAI")
    settings = preferences.get("gui_settings", {}).get(PAI_API_SETTINGS_KEY, {})
    options = normalize_pai_api_options(settings)

    api_action = action_cls("API habilitada", window)
    api_action.setCheckable(True)
    api_action.setChecked(options.enabled)
    api_action.triggered.connect(window.set_pai_api_enabled)
    pai_menu.addAction(api_action)

    scrap_action = action_cls("Busca via scrap_report", window)
    scrap_action.setCheckable(True)
    scrap_action.setChecked(options.scrap_report_enabled)
    scrap_action.triggered.connect(window.set_pai_api_scrap_enabled)
    pai_menu.addAction(scrap_action)

    auto_action = action_cls("Atualizacao automatica (10 min)", window)
    auto_action.setCheckable(True)
    auto_action.setChecked(options.auto_refresh_enabled)
    auto_action.triggered.connect(window.set_pai_api_auto_refresh_enabled)
    pai_menu.addAction(auto_action)

    sector_menu = pai_menu.addMenu("Setores executores")
    selected_sectors = {value.casefold() for value in options.executor_sectors}
    for sector in PAI_API_ALLOWED_SECTORS:
        sector_action = action_cls(sector, window)
        sector_action.setCheckable(True)
        sector_action.setChecked(sector.casefold() in selected_sectors)
        sector_action.triggered.connect(
            lambda checked, value=sector: window.set_pai_api_sector_enabled(
                value,
                checked,
            )
        )
        sector_menu.addAction(sector_action)
