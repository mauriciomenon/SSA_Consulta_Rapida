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
        # PyInstaller - usar diretorio do executavel, NAO _MEIPASS (pasta temporaria)
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_dir = os.path.dirname(sys.executable)
else:
    # Script Python normal
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, app_dir)

def main():
    """Entry point CLI v3.10.

    Comportamento especial para smoke test automático: se a variável de ambiente
    SSA_SMOKE_TEST=1 estiver presente, imprime um marcador simples e sai sem
    iniciar a interface interativa. Isso permite que scripts de CI validem
    rapidamente a integridade do carregamento sem bloquear esperando input.
    """
    if os.environ.get("SSA_SMOKE_TEST") == "1":
        try:
            from utils.version import get_app_version  # import leve
            version = get_app_version()
            print(f"SMOKE_CLI_OK v{version}")
            sys.exit(0)
        except Exception as exc:  # pragma: no cover - raríssimo
            print(f"SMOKE_CLI_FAIL {exc}")
            sys.exit(1)

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
