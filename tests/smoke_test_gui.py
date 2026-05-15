#!/usr/bin/env python3
"""Smoke tests de sanidade da GUI principal em modo headless."""

import inspect
import os
import sys
from contextlib import suppress
from unittest.mock import patch

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication  # noqa: E402

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Garante QApplication única para evitar aborts de Qt no pytest."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window():
    """Instancia janela sem auto-load assíncrono para smoke determinístico."""
    from gui.gui_ssa import SSAMainWindow  # noqa: E402

    with patch.object(SSAMainWindow, "load_data", lambda self: None):
        win = SSAMainWindow()
        win.show()
        QApplication.processEvents()
        try:
            yield win
        finally:
            with suppress(Exception):
                win.close()


def test_gui_instantiation(window):
    """Testa se a GUI pode ser instanciada (modo headless)."""
    print("[TEST] Testando instanciacao da GUI...")

    try:
        # Import em modo headless
        from gui.gui_ssa import QT_AVAILABLE, SSAMainWindow

        print(f"  Qt disponivel: {QT_AVAILABLE}")

        assert isinstance(window, SSAMainWindow)
        print("  [OK] SSAMainWindow instanciada com sucesso")

        # Verifica alguns atributos basicos
        assert hasattr(window, "df_completo"), "Atributo 'df_completo' ausente"
        print("  [OK] Atributo 'df_completo' existe")
        assert hasattr(window, "initiate_filtering"), (
            "Metodo 'initiate_filtering' ausente"
        )
        print("  [OK] Metodo 'initiate_filtering' acessivel")
        assert hasattr(window, "_apply_column_filters"), (
            "Metodo '_apply_column_filters' ausente"
        )
        print("  [OK] Metodo '_apply_column_filters' acessivel")

    except ImportError as e:
        pytest.fail(f"Falha ao importar: {e}")


def test_mixin_methods_callable(window):
    """Testa se metodos do mixin sao chamaveis."""
    print("\n[TEST] Testando se metodos do mixin sao chamaveis...")

    filter_methods = [
        "initiate_filtering",
        "_prepare_search_chunks",
        "_apply_column_filters",
        "clear_filter",
    ]

    for method_name in filter_methods:
        assert hasattr(window, method_name), f"{method_name} nao existe"
        method = getattr(window, method_name)
        assert callable(method), f"{method_name} nao e chamavel"
        print(f"  [OK] {method_name} e chamavel")


def test_no_method_conflicts():
    """Verifica se nao ha conflitos de metodos."""
    print("\n[TEST] Verificando conflitos de metodos...")

    try:
        from gui.gui_ssa import SSAMainWindow
        from gui.mixins import FilterGUISSAMixin

        # Obtem metodos da classe
        ssa_methods = {
            name: getattr(SSAMainWindow, name)
            for name in dir(SSAMainWindow)
            if not name.startswith("__")
            and callable(getattr(SSAMainWindow, name, None))
        }

        # Obtem metodos do mixin
        mixin_methods = {
            name: getattr(FilterGUISSAMixin, name)
            for name in dir(FilterGUISSAMixin)
            if not name.startswith("__")
            and callable(getattr(FilterGUISSAMixin, name, None))
        }

        # Verifica se metodos do mixin estao presentes
        mixin_method_names = set(mixin_methods.keys())
        ssa_method_names = set(ssa_methods.keys())

        inherited = mixin_method_names.intersection(ssa_method_names)

        print(f"  Metodos do mixin em SSAMainWindow: {len(inherited)}")

        if len(inherited) == len(mixin_method_names):
            print("  [OK] Todos os metodos do mixin estao presentes")
        else:
            missing = mixin_method_names - inherited
            pytest.fail(f"Metodos faltando: {missing}")

        signature_mismatch = []
        for method_name in sorted(inherited):
            mixin_sig = inspect.signature(mixin_methods[method_name])
            ssa_sig = inspect.signature(ssa_methods[method_name])
            if str(mixin_sig) != str(ssa_sig):
                signature_mismatch.append((method_name, str(mixin_sig), str(ssa_sig)))

        if signature_mismatch:
            details = "; ".join(
                f"{name}: mixin={mixin_sig} ssa={ssa_sig}"
                for name, mixin_sig, ssa_sig in signature_mismatch
            )
            pytest.fail(f"Assinaturas divergentes em metodos herdados: {details}")

    except Exception as e:
        pytest.fail(f"Falha: {e}")


def main():
    """Permite executar este arquivo diretamente via pytest."""
    return pytest.main([__file__, "-q"])


if __name__ == "__main__":
    sys.exit(main())
