#!/usr/bin/env python
"""
Teste de importacoes para validar modulos.
2025-10-31T08:40:00
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

print('=== TESTE DE IMPORTACOES ===')
print()

# Teste 1: core.app_logic
try:
    from core.app_logic import parse_search_terms, filter_dataframe
    print('[OK] core.app_logic: parse_search_terms, filter_dataframe')
except Exception as e:
    print(f'[ERRO] core.app_logic: {e}')

# Teste 2: core.config_manager
try:
    from core.config_manager import DEFAULT_DISPLAY_MAPPINGS
    print('[OK] core.config_manager: DEFAULT_DISPLAY_MAPPINGS')
except Exception as e:
    print(f'[ERRO] core.config_manager: {e}')

# Teste 3: gui.simple_width_manager
try:
    from gui.simple_width_manager import SimpleWidthManager
    print('[OK] gui.simple_width_manager: SimpleWidthManager')
except Exception as e:
    print(f'[ERRO] gui.simple_width_manager: {e}')

# Teste 4: utils.themes
try:
    from utils.themes import get_theme_roles
    print('[OK] utils.themes: get_theme_roles')
except Exception as e:
    print(f'[ERRO] utils.themes: {e}')

print()
print('Verificando que arquivos _dev NAO sao importaveis:')

# Teste 5: app_logic_dev (deve falhar)
try:
    from core.app_logic_dev import parse_search_terms
    print('[ERRO] core.app_logic_dev AINDA ESTA IMPORTAVEL!')
except ImportError:
    print('[OK] core.app_logic_dev nao encontrado (esperado)')
except Exception as e:
    print(f'[WARN] core.app_logic_dev: {e}')

# Teste 6: config_manager_dev (deve falhar)
try:
    from core.config_manager_dev import load_config
    print('[ERRO] core.config_manager_dev AINDA ESTA IMPORTAVEL!')
except ImportError:
    print('[OK] core.config_manager_dev nao encontrado (esperado)')
except Exception as e:
    print(f'[WARN] config_manager_dev: {e}')

print()
print('=== TODOS TESTES CONCLUIDOS ===')
