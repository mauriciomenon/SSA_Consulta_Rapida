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
            _get_qapp()

        # Tenta criar instancia (modo headless)
        try:
            window = SSAMainWindow()
            print("  [OK] SSAMainWindow instanciada com sucesso")

            # Verifica alguns atributos basicos
            assert hasattr(window, 'df_completo'), "Atributo 'df_completo' nao existe"
            assert hasattr(window, 'initiate_filtering'), "Metodo 'initiate_filtering' nao acessivel"
            assert hasattr(window, '_apply_column_filters'), "Metodo '_apply_column_filters' nao acessivel"

            # Check if cache is working and logging some times (user request)
            if hasattr(window, 'filter_cache_stats'):
                print(f"  [METRIC] Initial Cache Stats: {window.filter_cache_stats}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

    except ImportError as e:
        print(f"  [ERRO] Falha ao importar: {e}")
        raise e


def test_mixin_methods_callable():
    """Testa se metodos do mixin sao chamaveis."""
    print("\n[TEST] Testando se metodos do mixin sao chamaveis...")

    try:
        from gui.gui_ssa import SSAMainWindow
        _get_qapp()

        window = SSAMainWindow()

        # Testa alguns metodos do mixin
        filter_methods = [
            'initiate_filtering',
            '_split_search_expression',
            '_apply_column_filters',
            'clear_filter',
        ]

        for method_name in filter_methods:
            assert hasattr(window, method_name), f"Metodo {method_name} nao existe"
            method = getattr(window, method_name)
            assert callable(method), f"Atributo {method_name} nao e chamavel"

    except Exception as e:
        print(f"  [ERRO] Falha: {e}")
        raise e


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

        missing = mixin_method_names - inherited
        assert not missing, f"Metodos faltando no mixin: {missing}"

    except Exception as e:
        print(f"  [ERRO] Falha: {e}")
        raise e

if __name__ == "__main__":
    try:
        test_gui_instantiation()
        test_mixin_methods_callable()
        test_no_method_conflicts()
        print("\n" + "="*60)
        print("[SUCESSO] Todos os smoke tests passaram!")
        print("="*60)
        sys.exit(0)
    except Exception as e:
        print("[FALHA] Alguns smoke tests falharam.")
        print(f"Errors: {e}")
        sys.exit(1)