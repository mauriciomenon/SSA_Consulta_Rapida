#!/usr/bin/env python3
"""
Build Completo - SSA Consulta Rapida
Script de conveniencia para build completo com limpeza e git operations.
"""

import argparse
import subprocess
import sys
from pathlib import Path


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

    base_dir = Path(__file__).parent.parent
    build_script = base_dir / "launchers" / "build_multiplatform.py"

    try:
        if args.cleanup_only:
            # Apenas limpeza
            print("CLEAN Executando limpeza completa...")
            cmd = [sys.executable, str(build_script), "--cleanup-online"]
            result = subprocess.run(cmd, cwd=str(base_dir), check=False, timeout=300)
            return result.returncode

        # Build completo
        print("START Iniciando build completo...")

        cmd = [sys.executable, str(build_script), "--apps"] + args.apps

        # Adicionar flags automaticas
        if not args.no_cleanup:
            cmd.append("--auto-cleanup")

        if not args.no_git:
            cmd.append("--auto-git")
            if args.git_message:
                cmd.extend(["--git-message", args.git_message])

        print(f"Executando: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(base_dir), check=False, timeout=1800)

        if result.returncode == 0:
            print("OK Build completo concluido com sucesso!")
        else:
            print("ERR Build falhou")

        return result.returncode

    except KeyboardInterrupt:
        print("\nWARN  Build interrompido pelo usuario")
        return 1
    except Exception as e:
        print(f"ERR Erro: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
