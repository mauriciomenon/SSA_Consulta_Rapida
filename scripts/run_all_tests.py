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
import logging
import os
import shlex
import sys
from pathlib import Path

from scripts.pytest_stream_common import run_streaming_pytest, validate_safe_pytest_extra_args

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "test_run.log"


def main() -> int:
    logging.basicConfig(level=logging.INFO)
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

    pytest_target_for_fallback = "tests"
    base_cmd = [sys.executable, "-m", "pytest", "-q", pytest_target_for_fallback]
    if ns.args:
        extra_args = shlex.split(ns.args)
        safe_extra_args = validate_safe_pytest_extra_args(extra_args)
        base_cmd.extend(safe_extra_args)
        pytest_target_for_fallback = shlex.join(safe_extra_args)

    return run_streaming_pytest(
        cmd=base_cmd,
        timeout_s=3600,
        logpath=str(LOG_FILE),
        fallback_to_tee=False,
        test_arg=pytest_target_for_fallback,
        kill_process_tree=True,
        cwd=str(REPO_ROOT),
        env=env,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
