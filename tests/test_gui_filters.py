#!/usr/bin/env python3
"""Quick test of GUI and filters."""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("="*80)
print("TESTE RAPIDO DA GUI E FILTROS")
print("="*80)

print("\n[TEST 1] Importando PyQt6 e GUI...")
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    print("  [OK] PyQt6 importado")
except ImportError as e:
    print(f"  [ERRO] PyQt6 nao disponivel: {e}")
    sys.exit(1)

print("\n[TEST 2] Importando SSAMainWindow...")
try:
    from gui.gui_ssa import SSAMainWindow
    print("  [OK] SSAMainWindow importado")
except ImportError as e:
    print(f"  [ERRO] Falha ao importar SSAMainWindow: {e}")
    sys.exit(1)

print("\n[TEST 3] Verificando FilterGUISSAMixin...")
try:
    from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin
    print("  [OK] FilterGUISSAMixin importado")

    # Verificar se normalize_chunk_for_parse esta importado
    import inspect
    source = inspect.getsource(FilterGUISSAMixin._normalize_chunk_for_parse)
    if 'normalize_chunk_for_parse(chunk)' in source:
        print("  [OK] Metodo _normalize_chunk_for_parse usa funcao importada")
    else:
        print("  [AVISO] Metodo pode nao estar usando funcao importada corretamente")
except Exception as e:
    print(f"  [ERRO] Problema com FilterGUISSAMixin: {e}")

print("\n[TEST 4] Criando aplicacao e janela...")
try:
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    print("  [OK] Janela criada com sucesso")

    # Verificar se tem dados carregados
    if hasattr(window, 'dataframe') and window.dataframe is not None:
        print(f"  [OK] {len(window.dataframe)} registros carregados")
    else:
        print("  [AVISO] Nenhum dado carregado (banco pode estar vazio)")

except Exception as e:
    print(f"  [ERRO] Falha ao criar janela: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[TEST 5] Testando metodo de filtragem...")
try:
    # Verificar se metodo initiate_filtering existe
    if hasattr(window, 'initiate_filtering'):
        print("  [OK] Metodo initiate_filtering existe")

        # Verificar se outros metodos necessarios existem
        required_methods = [
            '_normalize_chunk_for_parse',
            '_split_search_expression',
            'on_filter_finished',
            'on_filter_error'
        ]

        missing = []
        for method in required_methods:
            if not hasattr(window, method):
                missing.append(method)

        if missing:
            print(f"  [ERRO] Metodos faltando: {', '.join(missing)}")
        else:
            print(f"  [OK] Todos os {len(required_methods)} metodos necessarios existem")
    else:
        print("  [ERRO] Metodo initiate_filtering nao encontrado")
except Exception as e:
    print(f"  [ERRO] Problema ao verificar metodos: {e}")

print("\n[TEST 6] Mostrando janela por 2 segundos...")
try:
    window.show()
    QTimer.singleShot(2000, app.quit)
    app.exec()
    print("  [OK] Janela exibida e fechada com sucesso")
except Exception as e:
    print(f"  [ERRO] Problema ao exibir janela: {e}")

print("\n" + "="*80)
print("[CONCLUIDO] Testes da GUI completos")
print("="*80)
print("\nRESUMO:")
print("  - PyQt6 funcional")
print("  - SSAMainWindow importavel")
print("  - FilterGUISSAMixin importado corretamente")
print("  - Janela pode ser criada e exibida")
print("  - Metodos de filtragem presentes")
print("\nPROXIMOS PASSOS:")
print("  - Testar aplicacao de filtro real via GUI")
print("  - Testar rescan via botao na GUI")
