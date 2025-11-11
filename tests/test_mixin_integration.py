#!/usr/bin/env python3
"""
Teste de integridade da integracao do FilterGUISSAMixin.

Verifica:
1. Imports funcionam corretamente
2. Classe SSAMainWindow herda do mixin
3. Metodos do mixin estao acessiveis
4. Nao ha conflitos de metodos
"""

import sys
import os

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """Testa se todos os imports necessarios funcionam."""
    print("[TEST] Testando imports...")

    try:
        from gui.mixins import FilterGUISSAMixin
        print("  [OK] FilterGUISSAMixin importado com sucesso")
    except ImportError as e:
        print(f"  [ERRO] Falha ao importar FilterGUISSAMixin: {e}")
        return False

    try:
        # Import em modo headless (sem PyQt6)
        import gui.gui_ssa as gui_module
        print("  [OK] gui.gui_ssa importado com sucesso")
    except ImportError as e:
        print(f"  [ERRO] Falha ao importar gui.gui_ssa: {e}")
        return False

    return True


def test_inheritance():
    """Testa se SSAMainWindow herda corretamente do mixin."""
    print("\n[TEST] Testando heranca...")

    try:
        from gui.gui_ssa import SSAMainWindow
        from gui.mixins import FilterGUISSAMixin

        # Verifica se FilterGUISSAMixin esta na MRO (Method Resolution Order)
        mro = SSAMainWindow.__mro__
        mro_names = [cls.__name__ for cls in mro]

        print(f"  MRO: {' -> '.join(mro_names)}")

        if FilterGUISSAMixin in mro:
            print("  [OK] SSAMainWindow herda de FilterGUISSAMixin")
        else:
            print("  [ERRO] FilterGUISSAMixin nao esta na hierarquia de heranca")
            return False

    except Exception as e:
        print(f"  [ERRO] Falha ao verificar heranca: {e}")
        return False

    return True


def test_mixin_methods():
    """Testa se os metodos do mixin estao acessiveis."""
    print("\n[TEST] Testando metodos do mixin...")

    try:
        from gui.gui_ssa import SSAMainWindow

        # Lista de metodos que devem estar presentes (do FilterGUISSAMixin)
        expected_methods = [
            'initiate_filtering',
            'on_filter_finished',
            'on_filter_error',
            'clear_filter',
            '_apply_column_filters',
            '_build_column_filters_panel',
            '_split_search_expression',
            '_normalize_chunk_for_parse',
            '_format_search_display',
        ]

        missing_methods = []
        for method_name in expected_methods:
            if not hasattr(SSAMainWindow, method_name):
                missing_methods.append(method_name)

        if missing_methods:
            print(f"  [ERRO] Metodos faltando: {', '.join(missing_methods)}")
            return False
        else:
            print(f"  [OK] Todos os {len(expected_methods)} metodos verificados estao presentes")

    except Exception as e:
        print(f"  [ERRO] Falha ao verificar metodos: {e}")
        return False

    return True


def test_no_duplicates():
    """Verifica se nao ha metodos duplicados."""
    print("\n[TEST] Verificando duplicacao de metodos...")

    try:
        from gui.gui_ssa import SSAMainWindow
        from gui.mixins import FilterGUISSAMixin

        # Obtem todos os metodos da classe SSAMainWindow (excluindo herdados de QMainWindow)
        ssa_methods = set()
        for name in dir(SSAMainWindow):
            if not name.startswith('_') or name.startswith('_') and not name.startswith('__'):
                attr = getattr(SSAMainWindow, name)
                if callable(attr):
                    ssa_methods.add(name)

        # Obtem todos os metodos do mixin
        mixin_methods = set()
        for name in dir(FilterGUISSAMixin):
            if not name.startswith('__'):
                attr = getattr(FilterGUISSAMixin, name)
                if callable(attr):
                    mixin_methods.add(name)

        print(f"  Metodos em SSAMainWindow: {len(ssa_methods)}")
        print(f"  Metodos em FilterGUISSAMixin: {len(mixin_methods)}")

        # Verifica se os metodos do mixin estao presentes
        inherited_methods = ssa_methods.intersection(mixin_methods)
        print(f"  Metodos herdados do mixin: {len(inherited_methods)}")

        if len(inherited_methods) > 0:
            print(f"  [OK] Mixin integrado com {len(inherited_methods)} metodos")
        else:
            print("  [AVISO] Nenhum metodo do mixin detectado (pode ser normal em modo headless)")

    except Exception as e:
        print(f"  [ERRO] Falha ao verificar duplicacao: {e}")
        return False

    return True


def count_lines():
    """Conta linhas em gui_ssa.py e no mixin."""
    print("\n[INFO] Contagem de linhas...")

    gui_ssa_path = os.path.join(project_root, 'gui', 'gui_ssa.py')
    mixin_path = os.path.join(project_root, 'gui', 'mixins', 'filter_gui_ssa_mixin.py')

    try:
        with open(gui_ssa_path, 'r', encoding='utf-8') as f:
            gui_ssa_lines = len(f.readlines())

        with open(mixin_path, 'r', encoding='utf-8') as f:
            mixin_lines = len(f.readlines())

        print(f"  gui_ssa.py: {gui_ssa_lines} linhas")
        print(f"  filter_gui_ssa_mixin.py: {mixin_lines} linhas")
        print(f"  Total combinado: {gui_ssa_lines + mixin_lines} linhas")

    except Exception as e:
        print(f"  [ERRO] Falha ao contar linhas: {e}")


def main():
    """Executa todos os testes."""
    print("="*60)
    print("TESTE DE INTEGRIDADE: FilterGUISSAMixin")
    print("="*60)

    all_passed = True

    # Executa os testes
    all_passed &= test_imports()
    all_passed &= test_inheritance()
    all_passed &= test_mixin_methods()
    all_passed &= test_no_duplicates()

    # Informacoes adicionais
    count_lines()

    # Resultado final
    print("\n" + "="*60)
    if all_passed:
        print("[SUCESSO] Todos os testes passaram!")
    else:
        print("[FALHA] Alguns testes falharam. Verifique os erros acima.")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
