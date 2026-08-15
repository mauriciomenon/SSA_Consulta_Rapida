#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 1
ssa_native_guard_tools pytest || exit 1
cd "$REPO_ROOT"

# Usage: scripts/run_import_perf.sh [extra-pytest-args]
# Environment variables:
#   SSA_PERF_ROWS=40000        number of generated rows
#   SSA_PERF_THRESHOLD=12      seconds threshold for xfail
#   ALLOW_SLOW_IMPORT=1        ignore threshold (no xfail)
#   SSA_IMPORT_DEBUG=1         enable debug logs inside importer

echo "[run_import_perf] rows=${SSA_PERF_ROWS:-20000} threshold=${SSA_PERF_THRESHOLD:-15} allow_slow=${ALLOW_SLOW_IMPORT:-0}" >&2
pytest -q -k performance_import ${1:+$@}
echo "--- Last perf report ---" >&2
if [ -f reports/perf_last_import.json ]; then
  cat reports/perf_last_import.json
else
  echo "(reports/perf_last_import.json not found)" >&2
fi
echo "--- Perf history tail ---" >&2
if [ -f reports/perf_history.jsonl ]; then
  tail -n 5 reports/perf_history.jsonl
fi
