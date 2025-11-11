#!/usr/bin/env python3
"""
Teste REAL da GUI - Abre janela, espera, e encerra.

Captura erros reais de execucao.
"""

import sys
import os
import time
import traceback

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("="*60)
print("TESTE REAL DA GUI")
print("="*60)

try:
    print("\n[1/5] Importando PyQt6...")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    print("  [OK] PyQt6 importado")

    print("\n[2/5] Importando gui_ssa...")
    from gui.gui_ssa import SSAMainWindow
    print("  [OK] gui_ssa importado")

    print("\n[3/5] Criando QApplication...")
    app = QApplication(sys.argv)
    print("  [OK] QApplication criada")

    print("\n[4/5] Instanciando SSAMainWindow...")
    window = SSAMainWindow()
    print("  [OK] SSAMainWindow instanciada")

    print("\n[5/5] Mostrando janela...")
    window.show()
    print("  [OK] Janela mostrada")

    print("\n[INFO] Janela aberta com sucesso!")
    print("[INFO] Aguardando 2 segundos antes de fechar...")

    # Timer para fechar apos 2 segundos
    QTimer.singleShot(2000, app.quit)

    # Executa event loop
    app.exec()

    print("\n[INFO] Janela fechada normalmente")
    print("\n" + "="*60)
    print("[SUCESSO] Teste da GUI passou!")
    print("="*60)

    sys.exit(0)

except Exception as e:
    print(f"\n[ERRO] Falha ao executar GUI:")
    print(f"  Tipo: {type(e).__name__}")
    print(f"  Mensagem: {e}")
    print("\n[TRACEBACK]")
    traceback.print_exc()
    print("\n" + "="*60)
    print("[FALHA] Teste da GUI falhou!")
    print("="*60)
    sys.exit(1)
