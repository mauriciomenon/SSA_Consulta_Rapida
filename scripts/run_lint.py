#!/usr/bin/env python3
"""Runner unificado para lint.

Modos:
  --quiet      Saída resumida (apenas contagem e códigos)
  --strict     Falha em qualquer aviso (flake8 padrão) + mypy (se disponível)
  --files f1 f2 ...  Lista explícita de paths (default = projeto inteiro)
  --no-mypy    Desativa mypy mesmo em modo strict
  --verbose    Força saída completa (ignora --quiet)

Exit codes:
  0 => Sucesso sem violações
  1 => Violações flake8
  2 => Erros mypy
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], quiet: bool = False) -> int:
    if not quiet:
        print("+", " ".join(cmd))
    try:
        completed = subprocess.run(cmd, cwd=ROOT, check=False)
        return completed.returncode
    except FileNotFoundError:
        print(f"[ERROR] Comando nao encontrado: {cmd[0]}")
        return 127


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--files", nargs="*", default=None)
    parser.add_argument("--no-mypy", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    quiet = args.quiet and not args.verbose
    targets = args.files or ["."]

    # Base flake8 command (config via .flake8)
    exclude = ".git,__pycache__,.venv,.direnv,.trunk"
    flake_cmd = [sys.executable, "-m", "flake8", f"--exclude={exclude}", *targets]
    if quiet:
        # Remove flags de detalhamento adicionadas em .flake8 via env override
        pass

    code_flake = run(flake_cmd, quiet=quiet)

    code_mypy = 0
    if args.strict and not args.no_mypy:
        mypy_cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", "--scripts-are-modules", "core", "utils", "scripts"]
        code_mypy = run(mypy_cmd, quiet=quiet)

    if code_flake != 0:
        return 1
    if code_mypy != 0:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
