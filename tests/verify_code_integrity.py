#!/usr/bin/env python3
"""
Script de verificacao de integridade de imports e chamadas cruzadas.
"""
import sys
import inspect

errors = []

# 1. Verificar imports circulares
try:
    import core.app_logic
    import gui.gui_ssa
    import gui.mixins
    import gui.workers
    import gui.helpers
    print('✓ Imports sem ciclos')
except ImportError as e:
    errors.append(f'✗ Import circular: {e}')

# 2. Verificar funcoes exportadas em helpers
try:
    from gui.helpers import (
        normalize_chunk_for_parse, 
        format_search_display,
        format_value_for_display,
        highlight_text,
        build_global_widget_qss,
        build_central_widget_qss
    )
    print('✓ Funcoes helper exportadas corretamente')
except ImportError as e:
    errors.append(f'✗ Helper exports: {e}')

# 3. Verificar workers
try:
    from gui.workers import DataLoaderWorker, FilterWorker, RescanWorker
    print('✓ Workers exportados corretamente')
except ImportError as e:
    errors.append(f'✗ Worker exports: {e}')

# 4. Verificar funcoes core
try:
    from core.app_logic import filter_dataframe, parse_search_terms, run_importer_logic
    print('✓ Funcoes core exportadas corretamente')
except ImportError as e:
    errors.append(f'✗ Core exports: {e}')

# 5. Verificar assinaturas
try:
    import core.app_logic
    sig = inspect.signature(core.app_logic.parse_search_terms)
    params = list(sig.parameters.keys())
    assert 'search_terms' in params, 'parse_search_terms missing search_terms param'
    assert 'default_mode' in params, 'parse_search_terms missing default_mode param'
    print('✓ Assinaturas de parse_search_terms corretas')
    
    sig = inspect.signature(core.app_logic.filter_dataframe)
    params = list(sig.parameters.keys())
    assert 'df' in params, 'filter_dataframe missing df param'
    assert 'search_terms' in params, 'filter_dataframe missing search_terms param'
    assert 'search_columns' in params, 'filter_dataframe missing search_columns param'
    print('✓ Assinaturas de filter_dataframe corretas')
    
    sig = inspect.signature(core.app_logic.run_importer_logic)
    params = list(sig.parameters.keys())
    assert 'progress_callback' in params, 'run_importer_logic missing progress_callback param'
    print('✓ Assinaturas de run_importer_logic corretas')
    
except Exception as e:
    errors.append(f'✗ Assinaturas: {e}')

# 6. Verificar mixins
try:
    from gui.mixins import FilterGUISSAMixin
    assert hasattr(FilterGUISSAMixin, '_format_search_display'), 'FilterGUISSAMixin missing _format_search_display'
    assert hasattr(FilterGUISSAMixin, '_normalize_chunk_for_parse'), 'FilterGUISSAMixin missing _normalize_chunk_for_parse'
    print('✓ Mixins com metodos corretos')
except Exception as e:
    errors.append(f'✗ Mixins: {e}')

# 7. Verificar acesso a GUI_MAIN_PREFERENCES (evitar NameError)
try:
    from gui import gui_ssa
    assert hasattr(gui_ssa, 'GUI_MAIN_PREFERENCES'), 'gui_ssa missing GUI_MAIN_PREFERENCES'
    assert isinstance(gui_ssa.GUI_MAIN_PREFERENCES, dict), 'GUI_MAIN_PREFERENCES should be dict'
    print('✓ GUI_MAIN_PREFERENCES acessivel')
except Exception as e:
    errors.append(f'✗ GUI_MAIN_PREFERENCES: {e}')

if errors:
    print('\n=== ERROS ENCONTRADOS ===')
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print('\n✓✓✓ TODAS AS VERIFICACOES PASSARAM ✓✓✓')
