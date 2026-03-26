#!/usr/bin/env python3
"""Runner consolidado de testes.

Objetivos:
  * Executar pytest de forma programática
  * Forçar ambiente não interativo
  * Capturar stdout/stderr completos em logs/test_run.log
  * Retornar exit code do pytest

Uso:
  python scripts/run_all_tests.py           # execução padrão
  python scripts/run_all_tests.py --args "-k normalizacao -vv"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "test_run.log"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--args", help="Argumentos extras para pytest (string única)", default=""
    )
    ns = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("SSA_NON_INTERACTIVE", "1")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("DISABLE_AUTO_UPDATE", "true")
    env.setdefault("DISABLE_UPDATE_PROMPT", "true")
    env.setdefault("PAGER", "cat")

    base_cmd = [sys.executable, "-m", "pytest", "-q"]
    if ns.args:
        base_cmd.extend(ns.args.split())

    with LOG_FILE.open("w", encoding="utf-8") as fh:
        fh.write("# Running tests\n")
        fh.write("Command: " + " ".join(base_cmd) + "\n\n")
        fh.flush()
        proc = subprocess.Popen(
            base_cmd,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                fh.write(line)
                fh.flush()
                # também ecoa no stdout para feedback em tempo real
                try:
                    sys.stdout.write(line)
                except KeyboardInterrupt:
                    # Se o usuário interromper enquanto escreve no stdout, ignoramos
                    pass
        except KeyboardInterrupt:
            fh.write(
                "\n# WARNING: KeyboardInterrupt capturado durante leitura do stdout do pytest; aguardando término do processo.\n"
            )
        finally:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                fh.write(
                    "\n# Pytest não finalizou em 10s após interrupção; terminando forçadamente.\n"
                )
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    fh.write("\n# Forçando kill do processo pytest.\n")
                    proc.kill()

            fh.write(f"\nExit code: {proc.returncode}\n")
            return int(proc.returncode or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
