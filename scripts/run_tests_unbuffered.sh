#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 1
ssa_native_guard_tools python || exit 1
cd "$REPO_ROOT"
export PYTHONUNBUFFERED=1
export PYTEST_ADDOPTS="-s -vv"
echo "[run_tests_unbuffered] Using PYTHONUNBUFFERED=$PYTHONUNBUFFERED PYTEST_ADDOPTS=$PYTEST_ADDOPTS"
python -u -m pytest "$@"
