"""CLI adapter for configuration commands."""

from __future__ import annotations

import os
import sys

from core.config_update import ALLOWED_FILTER_MODES
from core.config_update import CLEAR_DEFAULT_FILTERS_INPUT
from core.config_update import apply_settings_updates
from core.config_update import resolve_config_command_changes
from core.config_manager import load_settings, save_settings


def handle_config_command() -> bool:
    """Handle '-c' or 'config' in the CLI settings file.

    The command reloads the latest settings, applies the collected changes for
    user_preferences.filter_mode_default and default_filters, then saves the
    resulting settings payload.
    """
    try:
        settings = load_settings()
    except Exception as e:
        print(f"Erro ao carregar configurações: {e}")
        return False
    if not sys.stdin.isatty() and not os.environ.get("PYTEST_CURRENT_TEST"):
        print("Comando config requer terminal interativo.")
        return False

    changes = _collect_config_changes(settings)
    return _save_config_changes(*changes)


def _collect_config_changes(
    settings: dict,
) -> tuple[bool, str | None, bool, list[str] | None]:
    user_prefs = dict(settings.get("user_preferences") or {})
    current_mode = user_prefs.get("filter_mode_default", "contains")
    print("\n--- Configurações ---")
    print("1) Modo de filtro padrão (aplicado a termos SEM marcador):")
    print("   - Valores permitidos:", ", ".join(ALLOWED_FILTER_MODES))
    print(f"   - Atual: {current_mode}")
    new_mode = input("   > Novo valor (Enter para manter): ").strip().lower()

    print("\n2) Substituir filtros padrao (opcional):")
    print("   - Digite termos separados por virgula para substituir a lista inteira;")
    print(f"   - Digite {CLEAR_DEFAULT_FILTERS_INPUT} para limpar a lista;")
    print("   - Deixe em branco para manter a lista atual.")
    print(f"   - Atual: {settings.get('default_filters', [])}")
    new_filters_raw = input(
        "   > Nova lista (ex.: adm, ~^mel, !$2025) [Enter p/ manter]: "
    ).strip()
    changes = resolve_config_command_changes(
        current_filter_mode=str(current_mode),
        raw_filter_mode=new_mode,
        raw_default_filters=new_filters_raw if new_filters_raw else None,
    )
    if changes["invalid_filter_mode"]:
        print("Valor invalido. Nenhuma alteracao aplicada ao modo padrao.")
    if changes["changed_filter_mode"]:
        print(f"Modo padrao atualizado para: {changes['new_filter_mode']}")
    unsafe_filters = changes["unsafe_filters"]
    if unsafe_filters:
        print(f"Filtros padrao rejeitados por regex inseguro: {unsafe_filters}")
    elif changes["changed_default_filters"]:
        new_default_filters = changes["new_default_filters"]
        if new_default_filters:
            print(f"Filtros padrao atualizados: {new_default_filters}")
        else:
            print("Filtros padrao serao limpos.")

    return (
        bool(changes["changed_filter_mode"]),
        changes["new_filter_mode"],
        bool(changes["changed_default_filters"]),
        changes["new_default_filters"],
    )


def _save_config_changes(
    changed_filter_mode: bool,
    new_filter_mode: str | None,
    changed_default_filters: bool,
    new_default_filters: list[str] | None,
) -> bool:

    try:
        if not changed_filter_mode and not changed_default_filters:
            print("Nenhuma alteracao de configuracao para salvar.")
            return False
        latest_settings = load_settings()
        settings = apply_settings_updates(
            latest_settings,
            filter_mode=new_filter_mode if changed_filter_mode else None,
            default_filters=new_default_filters if changed_default_filters else None,
        )
        save_settings(settings)
        print(
            "Configuracoes salvas. Reinicie fluxos ja abertos para garantir que usem os novos valores."
        )
        return True
    except Exception as e:
        print(f"Falha ao salvar configuracoes: {e}")
        return False
