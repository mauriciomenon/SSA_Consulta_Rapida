#!/usr/bin/env python3
"""
Build Completo - SSA Consulta Rapida
Script de conveniencia para build completo com limpeza e git operations.
"""

import argparse
import importlib
import shlex
import sys
from pathlib import Path


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT_DIR = _get_project_root()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BUILD_SCRIPT_PATH = ROOT_DIR / "launchers" / "build_multiplatform.py"

from utils.robust_logging import get_robust_logger  # noqa: E402

logger = get_robust_logger().get_logger(__name__, "maintenance")


def _execute_builder_script(args):
    """Execucao direta do script de build sem subprocess para eliminar argumentos da shell."""
    logger.info(
        "Executando: %s %s",
        shlex.quote(str(BUILD_SCRIPT_PATH)),
        " ".join(shlex.quote(part) for part in args),
    )
    build_multiplatform = importlib.import_module("launchers.build_multiplatform")
    return build_multiplatform.main(args)


def _coerce_builder_exit_code(result_code):
    if result_code is None:
        logger.error("ERR Build wrapper recebeu exit code ausente")
        return 1
    return int(result_code)


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
        "--auto-git",
        action="store_true",
        help="Executar commit e push automaticos apos build bem-sucedido",
    )

    parser.add_argument(
        "--git-message", type=str, help="Mensagem personalizada para commit"
    )

    parser.add_argument(
        "--cleanup-only", action="store_true", help="Apenas executar limpeza sem build"
    )

    args = parser.parse_args()
    git_message = args.git_message.strip() if args.git_message is not None else None
    if args.git_message is not None and not args.auto_git:
        parser.error("--git-message requer --auto-git")
    if args.git_message is not None and not git_message:
        parser.error("--git-message nao pode ser vazio")
    if args.cleanup_only and args.auto_git:
        parser.error("--auto-git nao pode ser usado com --cleanup-only")
    args.git_message = git_message

    try:
        script_args = []
        if args.cleanup_only:
            # Apenas limpeza
            logger.info("CLEAN Executando limpeza completa...")
            script_args.append("--cleanup-online")
            result_code = _execute_builder_script(script_args)
            return _coerce_builder_exit_code(result_code)

        # Build completo
        logger.info("START Iniciando build completo...")
        script_args = ["--apps", *args.apps]

        # Adicionar flags automaticas
        if not args.no_cleanup:
            script_args.append("--auto-cleanup")

        if args.auto_git:
            script_args.append("--auto-git")
            if args.git_message:
                script_args.extend(["--git-message", args.git_message])

        result_code = _execute_builder_script(script_args)
        exit_code = _coerce_builder_exit_code(result_code)

        if exit_code == 0:
            logger.info("OK Build completo concluido com sucesso!")
        else:
            logger.error("ERR Build falhou")

        return exit_code

    except KeyboardInterrupt:
        logger.warning("WARN Build interrompido pelo usuario")
        return 1
    except Exception:
        logger.exception("ERR Erro inesperado no build")
        return 1


if __name__ == "__main__":
    sys.exit(main())
