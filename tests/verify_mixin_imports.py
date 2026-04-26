#!/usr/bin/env python3
# ruff: noqa: F401
"""
Script de verificação completa de imports em mixins.
Detecta imports faltantes que são efeito colateral de separar código em mixins.
"""

import os
import sys

# Ensure correct Python path when running from tests/
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_script_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

errors = []

print("=== VERIFICAÇÃO DE IMPORTS EM MIXINS ===\n")

# 1. Verificar imports básicos do mixin
try:
    from gui.mixins import FilterGUISSAMixin

    print(" FilterGUISSAMixin importado")
except ImportError as e:
    errors.append(f" FilterGUISSAMixin: {e}")

# 2. Verificar acesso a funções helper necessárias
try:
    from gui.helpers.formatting_helpers import (
        format_search_display,
        normalize_chunk_for_parse,
    )

    print(" Funções helper de formatting disponíveis")
except ImportError as e:
    errors.append(f" Formatting helpers: {e}")

# 3. Verificar constantes de core
try:
    from core.config_manager import DEFAULT_DISPLAY_MAPPINGS

    assert isinstance(DEFAULT_DISPLAY_MAPPINGS, dict)
    print(" DEFAULT_DISPLAY_MAPPINGS disponível")
except Exception as e:
    errors.append(f" DEFAULT_DISPLAY_MAPPINGS: {e}")

# 4. Verificar acesso a GUI_MAIN_PREFERENCES
try:
    from gui import gui_ssa

    assert hasattr(gui_ssa, "GUI_MAIN_PREFERENCES")
    assert isinstance(gui_ssa.GUI_MAIN_PREFERENCES, dict)
    print(" GUI_MAIN_PREFERENCES acessível via gui_ssa")
except Exception as e:
    errors.append(f" GUI_MAIN_PREFERENCES: {e}")

# 5. Verificar workers
try:
    from gui.workers import FilterWorker

    print(" FilterWorker disponível")
except ImportError as e:
    errors.append(f" FilterWorker: {e}")

# 6. Verificar widgets opcionais
try:
    from gui.widgets import FilterHelpDialog

    print(" FilterHelpDialog disponível")
except ImportError as e:
    # Este é opcional, então apenas aviso
    print(f"WARN FilterHelpDialog: {e} (opcional)")

# 7. Verificar funções de core/app_logic
try:
    from core.app_logic import filter_dataframe, parse_search_terms

    print(" Funções core.app_logic disponíveis")
except ImportError as e:
    errors.append(f" Core app_logic: {e}")

# 8. Verificar theme helpers
try:
    from utils.themes import get_theme_roles, normalize_theme

    print(" Theme helpers disponíveis")
except ImportError as e:
    errors.append(f" Theme helpers: {e}")

# 9. Teste prático: criar instância do mixin (sem GUI real)
try:
    # Verifica se os métodos existem sem executá-los
    assert hasattr(FilterGUISSAMixin, "initiate_filtering")
    assert hasattr(FilterGUISSAMixin, "_format_search_display")
    assert hasattr(FilterGUISSAMixin, "_normalize_chunk_for_parse")
    assert hasattr(FilterGUISSAMixin, "on_filter_finished")
    print(" Métodos essenciais do mixin presentes")
except Exception as e:
    errors.append(f" Métodos do mixin: {e}")

# 10. Verificar que nenhum import inline está faltando
try:
    # Simula o acesso inline que o mixin faz
    from gui import gui_ssa

    _ = gui_ssa.GUI_MAIN_PREFERENCES.get("gui_settings", {})
    print(" Acesso inline a GUI_MAIN_PREFERENCES funciona")
except Exception as e:
    errors.append(f" Acesso inline: {e}")

print()
if errors:
    print("=== ERROS ENCONTRADOS ===")
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print(" TODOS OS IMPORTS ESTÃO CORRETOS ")
    print("\nResumo:")
    print("  - Funções helper: OK")
    print("  - Constantes core: OK")
    print("  - Variáveis globais de módulo: OK")
    print("  - Workers: OK")
    print("  - Theme helpers: OK")
    print("  - Métodos do mixin: OK")
