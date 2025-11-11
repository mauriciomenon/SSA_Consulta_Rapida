#!/usr/bin/env python3
"""Script para extrair metodos de filtro de gui_ssa.py para criar FilterGUISSAMixin."""

import re

# Lista de metodos relacionados a filtros (identificados manualmente)
FILTER_METHODS = [
    'initiate_filtering',
    'on_filter_finished',
    'on_filter_error',
    'on_filter_finished_cleanup',
    'clear_filter',
    '_on_search_text_changed',
    'clear_filter_cache',
    'get_filter_cache_stats',
    '_open_add_column_filter_menu',
    '_activate_column_filter',
    '_deactivate_column_filter',
    '_build_column_filters_panel',
    '_apply_filter_widget_theme',
    '_refresh_column_filter_widgets',
    '_clear_single_column_filter',
    '_clear_all_column_filters',
    '_on_exclude_ste_sca_toggled',
    '_clear_all_filters_global',
    '_update_filters_summary',
    '_format_column_filter_display_value',
    '_get_filter_alias_map',
    '_update_col_filter_indicator',
    'show_filter_help',
    '_collect_profile_columns',
    '_initialize_profile_filter_placeholders',
    '_reset_or_groups',
    '_register_or_group',
    '_sync_or_group_values',
    '_apply_column_filters',
    '_refresh_after_filter_change',
    '_apply_search_display',
    '_mark_profile_as_custom',
    '_apply_filter_profile',
    '_apply_initial_filter_profile',
    'on_profile_changed',
    '_build_column_mask',
    '_split_search_expression',
    '_normalize_chunk_for_parse',
    '_format_search_display',
    'filter_data',
    'load_persistent_filters',
    'save_current_filter',
    'update_filter_tags',
    'apply_persistent_filter',
]


def extract_method(lines, start_idx):
    """Extrai um metodo completo comecando na linha start_idx."""
    method_lines = [lines[start_idx]]
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        # Se linha vazia ou comentario, adiciona
        if not line.strip() or line.strip().startswith('#'):
            method_lines.append(line)
            i += 1
            continue

        # Calcula indentacao da linha atual
        current_indent = len(line) - len(line.lstrip())

        # Se indentacao <= metodo e nao e linha vazia, fim do metodo
        if current_indent <= indent and line.strip():
            break

        method_lines.append(line)
        i += 1

    return method_lines, i


def main():
    with open('gui/gui_ssa.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Encontra inicio da classe SSAMainWindow
    class_start = None
    for i, line in enumerate(lines):
        if line.startswith('class SSAMainWindow'):
            class_start = i
            break

    if class_start is None:
        print("ERRO: Classe SSAMainWindow nao encontrada!")
        return

    # Extrai imports necessarios
    imports = []
    for line in lines[:class_start]:
        if line.startswith('import ') or line.startswith('from '):
            imports.append(line)

    # Busca e extrai cada metodo de filtro
    extracted_methods = {}

    for method_name in FILTER_METHODS:
        # Procura pela definicao do metodo
        pattern = rf'^\s+def {re.escape(method_name)}\('
        for i in range(class_start, len(lines)):
            if re.match(pattern, lines[i]):
                method_lines, end_idx = extract_method(lines, i)
                extracted_methods[method_name] = ''.join(method_lines)
                print(f"[OK] Extraido: {method_name} ({len(method_lines)} linhas)")
                break
        else:
            print(f"[ERRO] NAO ENCONTRADO: {method_name}")

    # Gera o arquivo do mixin
    header = '''# gui/mixins/filter_gui_ssa_mixin.py
# Mixin containing all filter-related methods for SSAMainWindow

"""
FilterGUISSAMixin: Mixin para metodos de filtragem.

Extraido de gui_ssa.py para reduzir tamanho do arquivo.
Padrao de nomenclatura: funcao_pai_mixin.py
"""

'''

    output_lines = [header]

    # Adiciona apenas imports relevantes (simplificado)
    output_lines.append("# Imports necessarios\n")
    output_lines.append("import pandas as pd\n")
    output_lines.append("from PyQt6.QtCore import QTimer\n")
    output_lines.append("from PyQt6.QtWidgets import QMessageBox\n")
    output_lines.append("\n\n")

    # Cria a classe mixin
    output_lines.append("class FilterGUISSAMixin:\n")
    output_lines.append("    \"\"\"\n")
    output_lines.append("    Mixin containing all filter-related methods.\n")
    output_lines.append("    \n")
    output_lines.append("    Methods extracted from SSAMainWindow to improve code organization.\n")
    output_lines.append("    \"\"\"\n\n")

    # Adiciona cada metodo extraido
    for method_name in FILTER_METHODS:
        if method_name in extracted_methods:
            output_lines.append(extracted_methods[method_name])
            output_lines.append("\n")

    # Salva o arquivo
    with open('gui/mixins/filter_gui_ssa_mixin.py', 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    total_lines = len(output_lines)
    total_methods = len(extracted_methods)
    print(f"\n{'='*60}")
    print(f"Mixin criado: gui/mixins/filter_gui_ssa_mixin.py")
    print(f"Total de metodos: {total_methods}")
    print(f"Total de linhas: {total_lines}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
