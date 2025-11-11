#!/usr/bin/env python3
"""
Script para remover metodos duplicados de gui_ssa.py.

Remove os 44 metodos que foram extraidos para FilterGUISSAMixin.
Cria um backup antes de modificar.
"""

import re
import shutil
from datetime import datetime

# Lista de metodos a serem removidos (ja estao no FilterGUISSAMixin)
METHODS_TO_REMOVE = [
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

    return i  # Retorna indice da primeira linha apos o metodo


def remove_methods_from_file(input_file, output_file, methods_to_remove):
    """Remove metodos especificados do arquivo."""
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Encontra inicio da classe SSAMainWindow
    class_start = None
    for i, line in enumerate(lines):
        if line.startswith('class SSAMainWindow'):
            class_start = i
            break

    if class_start is None:
        print("[ERRO] Classe SSAMainWindow nao encontrada!")
        return False

    # Marca linhas para remocao
    lines_to_remove = set()
    methods_removed = []

    for method_name in methods_to_remove:
        pattern = rf'^\s+def {re.escape(method_name)}\('
        for i in range(class_start, len(lines)):
            if re.match(pattern, lines[i]):
                # Marca inicio do metodo
                start_line = i
                # Encontra fim do metodo
                end_line = extract_method(lines, i)

                # Marca todas as linhas do metodo para remocao
                for line_num in range(start_line, end_line):
                    lines_to_remove.add(line_num)

                methods_removed.append(method_name)
                print(f"  [OK] Marcado para remocao: {method_name} (linhas {start_line+1}-{end_line})")
                break

    # Verifica se todos os metodos foram encontrados
    missing_methods = set(methods_to_remove) - set(methods_removed)
    if missing_methods:
        print(f"\n[AVISO] Metodos nao encontrados: {', '.join(missing_methods)}")

    # Remove linhas marcadas e escreve novo arquivo
    print(f"\n[INFO] Removendo {len(lines_to_remove)} linhas...")
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    # Estatisticas
    original_lines = len(lines)
    new_lines_count = len(new_lines)
    removed_lines = original_lines - new_lines_count

    print(f"\n[INFO] Estatisticas:")
    print(f"  Linhas originais: {original_lines}")
    print(f"  Linhas no novo arquivo: {new_lines_count}")
    print(f"  Linhas removidas: {removed_lines}")
    print(f"  Reducao: {removed_lines / original_lines * 100:.1f}%")
    print(f"  Metodos removidos: {len(methods_removed)}/{len(methods_to_remove)}")

    return True


def main():
    """Executa a remocao de metodos duplicados."""
    print("="*60)
    print("REMOCAO DE METODOS DUPLICADOS")
    print("="*60)

    input_file = 'gui/gui_ssa.py'
    output_file = 'gui/gui_ssa.py'

    # Cria backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'gui/gui_ssa.py.backup_{timestamp}'

    print(f"\n[INFO] Criando backup: {backup_file}")
    shutil.copy2(input_file, backup_file)
    print("  [OK] Backup criado")

    # Remove metodos duplicados
    print(f"\n[INFO] Removendo metodos duplicados...")
    success = remove_methods_from_file(input_file, output_file, METHODS_TO_REMOVE)

    if success:
        print("\n[SUCESSO] Metodos removidos com sucesso!")
        print(f"\n[INFO] Backup disponivel em: {backup_file}")
    else:
        print("\n[ERRO] Falha ao remover metodos!")
        return 1

    # Valida sintaxe do arquivo modificado
    print("\n[INFO] Validando sintaxe do arquivo modificado...")
    import py_compile
    try:
        py_compile.compile(output_file, doraise=True)
        print("  [OK] Sintaxe valida!")
    except py_compile.PyCompileError as e:
        print(f"  [ERRO] Erro de sintaxe: {e}")
        print("\n[INFO] Restaurando backup...")
        shutil.copy2(backup_file, output_file)
        print("  [OK] Backup restaurado")
        return 1

    print("\n" + "="*60)
    print("[CONCLUIDO] Processo finalizado com sucesso!")
    print("="*60)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
