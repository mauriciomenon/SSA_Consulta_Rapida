#!/usr/bin/env python3
"""
Smoke test para GUI apos integracao do mixin.

Testa se a GUI pode ser instanciada e metodos basicos funcionam.
"""

import sys
import os

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _get_qapp():
    """Garante existência de QApplication."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        return app
    except ImportError:
        return None


def test_gui_instantiation():
    """Testa se a GUI pode ser instanciada (modo headless)."""
    print("[TEST] Testando instanciacao da GUI...")

    try:
        # Import em modo headless
        from gui.gui_ssa import SSAMainWindow, QT_AVAILABLE

        print(f"  Qt disponivel: {QT_AVAILABLE}")

        # Garante QApplication
        if QT_AVAILABLE:
            _app = _get_qapp()

        # Tenta criar instancia (modo headless)
        try:
            window = SSAMainWindow()
            print("  [OK] SSAMainWindow instanciada com sucesso")

            # Verifica alguns atributos basicos
            if hasattr(window, 'df_completo'):
                print("  [OK] Atributo 'df_completo' existe")
            if hasattr(window, 'initiate_filtering'):
                print("  [OK] Metodo 'initiate_filtering' acessivel")
            if hasattr(window, '_apply_column_filters'):
                print("  [OK] Metodo '_apply_column_filters' acessivel")

            return True

        except Exception as e:
            print(f"  [ERRO] Falha ao instanciar: {e}")
            return False

    except ImportError as e:
        print(f"  [ERRO] Falha ao importar: {e}")
        return False


def test_mixin_methods_callable():
    """Testa se metodos do mixin sao chamaveis."""
    print("\n[TEST] Testando se metodos do mixin sao chamaveis...")

    try:
        from gui.gui_ssa import SSAMainWindow
        _app = _get_qapp()

        window = SSAMainWindow()

        # Testa alguns metodos do mixin
        filter_methods = [
            'initiate_filtering',
            '_split_search_expression',
            '_apply_column_filters',
            'clear_filter',
        ]

        for method_name in filter_methods:
            if hasattr(window, method_name):
                method = getattr(window, method_name)
                if callable(method):
                    print(f"  [OK] {method_name} e chamavel")
                else:
                    print(f"  [ERRO] {method_name} nao e chamavel")
                    return False
            else:
                print(f"  [ERRO] {method_name} nao existe")
                return False

        return True

    except Exception as e:
        print(f"  [ERRO] Falha: {e}")
        return False


def test_no_method_conflicts():
    """Verifica se nao ha conflitos de metodos."""
    print("\n[TEST] Verificando conflitos de metodos...")

    try:
        from gui.gui_ssa import SSAMainWindow
        from gui.mixins import FilterGUISSAMixin

        # Obtem metodos da classe
        ssa_methods = {name: getattr(SSAMainWindow, name)
                       for name in dir(SSAMainWindow)
                       if not name.startswith('__') and callable(getattr(SSAMainWindow, name, None))}

        # Obtem metodos do mixin
        mixin_methods = {name: getattr(FilterGUISSAMixin, name)
                         for name in dir(FilterGUISSAMixin)
                         if not name.startswith('__') and callable(getattr(FilterGUISSAMixin, name, None))}

        # Verifica se metodos do mixin estao presentes
        mixin_method_names = set(mixin_methods.keys())
        ssa_method_names = set(ssa_methods.keys())

        inherited = mixin_method_names.intersection(ssa_method_names)

        print(f"  Metodos do mixin em SSAMainWindow: {len(inherited)}")

        if len(inherited) == len(mixin_method_names):
            print("  [OK] Todos os metodos do mixin estao presentes")
            return True
        else:
            missing = mixin_method_names - inherited
            print(f"  [ERRO] Metodos faltando: {missing}")
            return False

    except Exception as e:
        print(f"  [ERRO] Falha: {e}")
        return False


def main():
    """Executa todos os smoke tests."""
    print("="*60)
    print("SMOKE TEST: GUI apos integracao do mixin")
    print("="*60)

    all_passed = True

    all_passed &= test_gui_instantiation()
    all_passed &= test_mixin_methods_callable()
    all_passed &= test_no_method_conflicts()

    # Resultado final
    print("\n" + "="*60)
    if all_passed:
        print("[SUCESSO] Todos os smoke tests passaram!")
    else:
        print("[FALHA] Alguns smoke tests falharam.")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
