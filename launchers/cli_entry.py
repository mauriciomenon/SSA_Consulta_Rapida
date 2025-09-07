#!/usr/bin/env python3
"""
Entry point CLI para executavel v3.10
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
    """Entry point CLI v3.10"""
    try:
        from interface.cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"ERRO: Nao foi possivel importar interface.cli: {e}")
        print(f"Path atual: {sys.path}")
        print(f"App dir: {app_dir}")
        print(f"Arquivos em app_dir: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}")
        sys.exit(1)

if __name__ == "__main__":
    main()
