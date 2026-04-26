#!/usr/bin/env python
"""
Teste de importacoes para validar modulos.
2025-10-31T08:40:00
"""

import importlib
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

print("=== TESTE DE IMPORTACOES ===")
print()

# Teste 1: core.app_logic
try:
    app_logic = importlib.import_module("core.app_logic")
    parse_search_terms = getattr(app_logic, "parse_search_terms")
    filter_dataframe = getattr(app_logic, "filter_dataframe")
    print("[OK] core.app_logic: parse_search_terms, filter_dataframe")
except Exception as e:
    print(f"[ERRO] core.app_logic: {e}")

# Teste 2: core.config_manager
try:
    config_manager = importlib.import_module("core.config_manager")
    default_display_mappings = getattr(config_manager, "DEFAULT_DISPLAY_MAPPINGS")
    print("[OK] core.config_manager: DEFAULT_DISPLAY_MAPPINGS")
except Exception as e:
    print(f"[ERRO] core.config_manager: {e}")

# Teste 3: gui.simple_width_manager
try:
    simple_width_manager = importlib.import_module("gui.simple_width_manager")
    simple_width_manager_cls = getattr(simple_width_manager, "SimpleWidthManager")
    print("[OK] gui.simple_width_manager: SimpleWidthManager")
except Exception as e:
    print(f"[ERRO] gui.simple_width_manager: {e}")

# Teste 4: utils.themes
try:
    themes_module = importlib.import_module("utils.themes")
    get_theme_roles = getattr(themes_module, "get_theme_roles")
    print("[OK] utils.themes: get_theme_roles")
except Exception as e:
    print(f"[ERRO] utils.themes: {e}")

print()
print("Verificando que arquivos _dev NAO sao importaveis:")

# Teste 5: app_logic_dev (deve falhar)
try:
    app_logic_dev = importlib.import_module("core.app_logic_dev")
    parse_search_terms_dev = getattr(app_logic_dev, "parse_search_terms")
    print("[ERRO] core.app_logic_dev AINDA ESTA IMPORTAVEL!")
except ImportError:
    print("[OK] core.app_logic_dev nao encontrado (esperado)")
except Exception as e:
    print(f"[WARN] core.app_logic_dev: {e}")

# Teste 6: config_manager_dev (deve falhar)
try:
    config_manager_dev = importlib.import_module("core.config_manager_dev")
    load_config_dev = getattr(config_manager_dev, "load_config")
    print("[ERRO] core.config_manager_dev AINDA ESTA IMPORTAVEL!")
except ImportError:
    print("[OK] core.config_manager_dev nao encontrado (esperado)")
except Exception as e:
    print(f"[WARN] config_manager_dev: {e}")

print()
print("=== TODOS TESTES CONCLUIDOS ===")
