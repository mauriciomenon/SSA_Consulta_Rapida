#!/usr/bin/env bash
set -euo pipefail
echo "[run_perf_no_direnv] Limpando variáveis relacionadas a direnv/pyenv para execução isolada" >&2
unset DIRENV_DIR 2>/dev/null || true
unset DIRENV_WATCHES 2>/dev/null || true
unset PYENV_VERSION 2>/dev/null || true
SSA_PERF_VERBOSE=1 SSA_PERF_FAST=1 python scripts/generate_perf_artifacts.py
echo "[run_perf_no_direnv] Feito. Verifique reports/perf_last_import.json" >&2