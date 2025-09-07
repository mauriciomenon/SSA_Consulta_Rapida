#!/usr/bin/env python3
"""
Entry point GUI para executavel v3.10
Separado do main.py principal
"""

import os
import sys

# Adicionar diretorio raiz ao path CORRETAMENTE
if getattr(sys, 'frozen', False):
    # Executavel PyInstaller - buscar na raiz dos dados empacotados
    if hasattr(sys, '_MEIPASS'):
        app_dir = sys._MEIPASS
    else:
        app_dir = os.path.dirname(sys.executable)
else:
    # Script Python normal
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, app_dir)

def main():
    """Entry point GUI v3.10"""
    try:
        from PyQt6.QtWidgets import QApplication
        from gui.gui_ssa import SSAMainWindow
        
        app = QApplication(sys.argv)
        window = SSAMainWindow()
        window.show()
        sys.exit(app.exec())
    except ImportError as e:
        print(f"ERRO: Nao foi possivel importar modulos GUI: {e}")
        print(f"Path atual: {sys.path}")
        print(f"App dir: {app_dir}")
        print(f"Arquivos em app_dir: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}")
        sys.exit(1)
        
    except ImportError as e:
        print(f"ERRO: PyQt6 nao encontrado: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERRO na GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
