#!/usr/bin/env python3
"""
Versão simplificada do main.py para teste
"""

import os
import sys
import argparse

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_app_version():
    try:
        from utils.version import get_app_version as _get_version
        return _get_version()
    except ImportError:
        return "3.0.7"

APP_VERSION = get_app_version()

def main():
    parser = argparse.ArgumentParser(
        description=f"Consulta Rápida de SSAs v{APP_VERSION}",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '--force-rescan', '--rescan',
        dest='force_rescan',
        action='store_true',
        help='Força a reimportação de todos os arquivos Excel, ignorando o cache.'
    )

    args = parser.parse_args()

    print(f"Pesquisa Rápida de SSAs {APP_VERSION}")

    if args.force_rescan:
        print("RESCAN SOLICITADO - implementação pendente")
    else:
        print("Executando sem rescan (correto!)")

    # Simula CLI básica
    print("Digite 'q' para sair:")
    while True:
        try:
            user_input = input(">>> ").strip()
            if user_input.lower() in ['q', 'quit', 'sair']:
                break
            print(f"Você digitou: {user_input}")
        except KeyboardInterrupt:
            break

    print("Programa encerrado.")

if __name__ == "__main__":
    main()
