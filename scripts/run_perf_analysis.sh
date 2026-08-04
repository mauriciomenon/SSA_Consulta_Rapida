#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 1
ssa_native_guard_tools python sed || exit 1
cd "$REPO_ROOT"
python scripts/analyze_perf_history.py
echo '--- Weekly summary ---'
sed -n '1,120p' reports/perf_weekly_summary.json || true
