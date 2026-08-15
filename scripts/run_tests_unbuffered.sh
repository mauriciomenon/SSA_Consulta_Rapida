#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export PYTEST_ADDOPTS="-s -vv"
echo "[run_tests_unbuffered] Using PYTHONUNBUFFERED=$PYTHONUNBUFFERED PYTEST_ADDOPTS=$PYTEST_ADDOPTS"
python -u -m pytest "$@"

