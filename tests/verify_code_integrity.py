#!/usr/bin/env python3
# ruff: noqa: F401
"""
Script de verificacao de integridade de imports e chamadas cruzadas.
"""

import inspect
import importlib
import os
import sys

# Ensure correct Python path when running from tests/
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_script_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

errors = []

# 1. Verificar imports circulares
try:
    for module_name in (
        "core.app_logic",
        "gui.gui_ssa",
        "gui.helpers",
        "gui.mixins",
        "gui.workers",
    ):
        importlib.import_module(module_name)

    print("OK Imports sem ciclos")
except ImportError as e:
    errors.append(f"ERR Import circular: {e}")

# 2. Verificar funcoes exportadas em helpers
try:
    from gui.helpers import (
        build_central_widget_qss,
        build_global_widget_qss,
        format_search_display,
        highlight_text,
        normalize_chunk_for_parse,
    )

    print("OK Funcoes helper exportadas corretamente")
except ImportError as e:
    errors.append(f"ERR Helper exports: {e}")

# 3. Verificar workers
try:
    from gui.workers import DataLoaderWorker, FilterWorker, RescanWorker

    print("OK Workers exportados corretamente")
except ImportError as e:
    errors.append(f"ERR Worker exports: {e}")

# 4. Verificar funcoes core
try:
    from core.app_logic import filter_dataframe, parse_search_terms, run_importer_logic

    print("OK Funcoes core exportadas corretamente")
except ImportError as e:
    errors.append(f"ERR Core exports: {e}")

# 5. Verificar assinaturas
try:
    import core.app_logic

    sig = inspect.signature(core.app_logic.parse_search_terms)
    params = list(sig.parameters.keys())
    assert "search_terms" in params, "parse_search_terms missing search_terms param"
    assert "default_mode" in params, "parse_search_terms missing default_mode param"
    print("OK Assinaturas de parse_search_terms corretas")

    sig = inspect.signature(core.app_logic.filter_dataframe)
    params = list(sig.parameters.keys())
    assert "df" in params, "filter_dataframe missing df param"
    assert "search_terms" in params, "filter_dataframe missing search_terms param"
    assert "search_columns" in params, "filter_dataframe missing search_columns param"
    print("OK Assinaturas de filter_dataframe corretas")

    sig = inspect.signature(core.app_logic.run_importer_logic)
    params = list(sig.parameters.keys())
    assert "progress_callback" in params, (
        "run_importer_logic missing progress_callback param"
    )
    print("OK Assinaturas de run_importer_logic corretas")

except Exception as e:
    errors.append(f"ERR Assinaturas: {e}")

# 6. Verificar mixins
try:
    from gui.mixins import FilterGUISSAMixin

    assert hasattr(FilterGUISSAMixin, "_format_search_display"), (
        "FilterGUISSAMixin missing _format_search_display"
    )
    assert hasattr(FilterGUISSAMixin, "_normalize_chunk_for_parse"), (
        "FilterGUISSAMixin missing _normalize_chunk_for_parse"
    )
    print("OK Mixins com metodos corretos")
except Exception as e:
    errors.append(f"ERR Mixins: {e}")

# 7. Verificar acesso a GUI_MAIN_PREFERENCES (evitar NameError)
try:
    from gui import gui_ssa

    assert hasattr(gui_ssa, "GUI_MAIN_PREFERENCES"), (
        "gui_ssa missing GUI_MAIN_PREFERENCES"
    )
    assert isinstance(gui_ssa.GUI_MAIN_PREFERENCES, dict), (
        "GUI_MAIN_PREFERENCES should be dict"
    )
    print("OK GUI_MAIN_PREFERENCES acessivel")
except Exception as e:
    errors.append(f"ERR GUI_MAIN_PREFERENCES: {e}")

if errors:
    print("\n=== ERROS ENCONTRADOS ===")
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print("\nOK TODAS AS VERIFICACOES PASSARAM")
