#!/usr/bin/env python3
"""
Teste de Performance e Interacao da GUI (Headless/Simulado).

Mede tempos de carregamento, filtragem e troca de abas.
Simula interacoes do usuario via chamadas de metodos e sinais.
"""

import os
import sys
import time

from PyQt6.QtWidgets import QApplication, QTabWidget

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importa a GUI
try:
    from gui.gui_ssa import SSAMainWindow
except ImportError:
    print("ERRO: Nao foi possivel importar gui.gui_ssa")
    sys.exit(1)

_app_ref = None


def _get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_gui_load_time():
    """Mede o tempo de instanciacao da janela principal."""
    # Mantenha referencia global ao app para evitar GC prematuro
    global _app_ref
    _app_ref = _get_qapp()

    start_time = time.perf_counter()
    window = SSAMainWindow()
    end_time = time.perf_counter()

    # Mantenha a janela viva explicitamente
    window.show()
    _app_ref.processEvents()

    load_time = end_time - start_time
    print(f"\n[PERF] Tempo de carregamento da GUI: {load_time:.4f}s")

    # Assert que carrega em tempo razoavel (ex: < 2s para teste headless)
    # Nota: Em ambiente real com DB grande pode ser maior, mas headless deve ser rapido
    assert load_time < 5.0, f"Tempo de carregamento muito alto: {load_time:.4f}s"
    return window


def test_filtering_performance(window):
    """Mede o tempo para aplicar um filtro simples."""
    print("\n[PERF] Iniciando teste de filtragem...")

    # Simula texto na busca
    window.search_input.setText("TESTE_PERFORMANCE")

    start_time = time.perf_counter()
    # Chama o metodo de filtragem diretamente (simula clique em Aplicar/Enter)
    window.initiate_filtering()

    # Espera threads se houver (mas initiate_filtering pode ser async)
    # Como estamos testando a logica de disparo e processamento inicial:
    app = QApplication.instance()
    app.processEvents()  # Processa eventos pendentes

    end_time = time.perf_counter()
    filter_time = end_time - start_time

    print(f"[PERF] Tempo de disparo de filtragem: {filter_time:.4f}s")
    assert filter_time < 1.0, f"Disparo de filtragem lento: {filter_time:.4f}s"


def test_tab_switching_performance(window):
    """Mede o tempo de troca de abas (onde o usuario reclamou de lentidao)."""
    print("\n[PERF] Iniciando teste de troca de abas...")

    tabs = window.findChild(QTabWidget, "main_tabs")
    if not tabs:
        print(
            "  [WARN] QTabWidget 'main_tabs' nao encontrado. Tentando localizar manualmente."
        )
        # Fallback se o nome nao estiver setado
        for child in window.findChildren(QTabWidget):
            tabs = child
            break

    assert tabs is not None, "Nao foi possivel encontrar as abas para teste"

    # Troca para aba 1 (SSAs)
    start_time = time.perf_counter()
    window._on_tab_changed(1)  # Simula sinal
    app = QApplication.instance()
    app.processEvents()
    end_time = time.perf_counter()

    switch_time_1 = end_time - start_time
    print(f"[PERF] Troca para aba 1: {switch_time_1:.4f}s")

    # Troca para aba 2 (Filtros)
    start_time = time.perf_counter()
    window._on_tab_changed(2)
    app.processEvents()
    end_time = time.perf_counter()

    switch_time_2 = end_time - start_time
    print(f"[PERF] Troca para aba 2: {switch_time_2:.4f}s")

    # Troca de volta para aba 1 (deve usar cache agora)
    start_time = time.perf_counter()
    window._on_tab_changed(1)
    app.processEvents()
    end_time = time.perf_counter()

    switch_time_cache = end_time - start_time
    print(f"[PERF] Troca para aba 1 (Cache): {switch_time_cache:.4f}s")

    assert switch_time_cache < 0.5, "Troca de aba com cache esta lenta!"


def run_performance_suite():
    print("=" * 60)
    print("TESTE DE PERFORMANCE GUI (SIMULADO)")
    print("=" * 60)

    try:
        window = test_gui_load_time()

        # Injeta um DataFrame fake se est estiver vazio, para ter o que filtrar
        if window.df_completo is None or window.df_completo.empty:
            import pandas as pd

            print("  [INFO] Injetando DataFrame mock para teste...")
            window.df_completo = pd.DataFrame(
                {
                    "numero_ssa": [f"SSA-{i}" for i in range(1000)],
                    "situacao": ["ABERTA"] * 1000,
                    "setor_executor": ["ENG"] * 1000,
                    "descricao_ssa": [
                        "Teste performance linha " + str(i) for i in range(1000)
                    ],
                }
            )
            window.df_exibido = window.df_completo.copy()

        test_filtering_performance(window)
        test_tab_switching_performance(window)

        print("\n" + "=" * 60)
        print("[SUCESSO] Testes de performance concluidos com sucesso.")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FALHA] Teste de performance falhou: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro durante teste: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_performance_suite()
