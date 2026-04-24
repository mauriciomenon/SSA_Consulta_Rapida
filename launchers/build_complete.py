#!/usr/bin/env python3
"""
Build Completo - SSA Consulta Rapida
Script de conveniencia para build completo com limpeza e git operations.
"""

import argparse
import importlib
import sys
import shlex
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _execute_builder_script(args):
    """Execucao direta do script de build sem subprocess para eliminar argumentos da shell."""
    previous_argv = list(sys.argv)
    base_dir = Path(__file__).parent.parent
    sys.argv = [str(base_dir / "launchers" / "build_multiplatform.py"), *args]
    build_multiplatform = importlib.import_module("launchers.build_multiplatform")

    try:
        return build_multiplatform.main()
    finally:
        sys.argv = previous_argv


def main():
    parser = argparse.ArgumentParser(
        description="Build completo com limpeza automatica e git operations"
    )

    parser.add_argument(
        "--apps",
        nargs="+",
        choices=["cli", "gui"],
        default=["cli", "gui"],
        help="Aplicacoes para construir",
    )

    parser.add_argument(
        "--no-cleanup", action="store_true", help="Pular limpeza automatica"
    )

    parser.add_argument(
        "--no-git", action="store_true", help="Pular operacoes git automaticas"
    )

    parser.add_argument(
        "--git-message", type=str, help="Mensagem personalizada para commit"
    )

    parser.add_argument(
        "--cleanup-only", action="store_true", help="Apenas executar limpeza sem build"
    )

    args = parser.parse_args()

    try:
        script_args = []
        if args.cleanup_only:
            # Apenas limpeza
            print("CLEAN Executando limpeza completa...")
            script_args.append("--cleanup-online")
            result_code = _execute_builder_script(script_args)
            return result_code

        # Build completo
        print("START Iniciando build completo...")
        script_args = ["--apps", *args.apps]

        # Adicionar flags automaticas
        if not args.no_cleanup:
            script_args.append("--auto-cleanup")

        if not args.no_git:
            script_args.append("--auto-git")
            if args.git_message:
                script_args.extend(["--git-message", args.git_message])

        print(f"Executando: {' '.join(shlex.quote(part) for part in script_args)}")
        result_code = _execute_builder_script(script_args)

        if result_code == 0:
            print("OK Build completo concluido com sucesso!")
        else:
            print("ERR Build falhou")

        return result_code

    except KeyboardInterrupt:
        print("\nWARN  Build interrompido pelo usuario")
        return 1
    except Exception as e:
        print(f"ERR Erro: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
