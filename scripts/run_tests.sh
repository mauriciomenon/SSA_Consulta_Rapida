#!/usr/bin/env bash
set -euo pipefail

# Simple unified test runner for SSA_Consulta_Rapida
# Usage:
#   ./scripts/run_tests.sh              # fast quiet mode
#   ./scripts/run_tests.sh full         # verbose full run
#   ./scripts/run_tests.sh cov          # run with coverage (creates .coverage + htmlcov)
#   ./scripts/run_tests.sh debug        # verbose + show stdout
#   env PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh
#
# The script auto-clears pytest cache to avoid stale references after file deletions.

PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$PROJECT_ROOT" || exit 1
ssa_native_guard_tools python || exit 1
cd "$PROJECT_ROOT"

if [[ ! -f pyproject.toml ]]; then
  echo "[run_tests] ERROR: run from project root" >&2
  exit 1
fi

mode="${1:-quiet}"

base_cmd=(python -m pytest --cache-clear)

case "$mode" in
  quiet)
    base_cmd+=( -q )
    ;;
  full)
    base_cmd+=( -vv )
    ;;
  cov)
    base_cmd+=( -vv --maxfail=1 --cov=./ --cov-report=term-missing )
    ;;
  debug)
    base_cmd+=( -vv -s )
    ;;
  *)
    echo "[run_tests] Unknown mode '$mode' (use quiet|full|cov|debug)" >&2
    exit 2
    ;;
esac

# Allow user extra opts via PYTEST_ADDOPTS
pytest_extra_opts=()
if [[ -n "${PYTEST_ADDOPTS:-}" ]]; then
  echo "[run_tests] Extra opts: $PYTEST_ADDOPTS"
  parsed_pytest_addopts="$(
    python - "$PYTEST_ADDOPTS" <<'PY'
import shlex
import sys

try:
    args = shlex.split(sys.argv[1])
except ValueError as exc:
    print(f"[run_tests] ERROR: invalid PYTEST_ADDOPTS: {exc}", file=sys.stderr)
    sys.exit(2)

for arg in args:
    print(arg)
PY
  )" || exit 2
  if [[ -n "$parsed_pytest_addopts" ]]; then
    while IFS= read -r pytest_arg; do
      pytest_extra_opts+=( "$pytest_arg" )
    done <<< "$parsed_pytest_addopts"
  fi
fi

set -x
"${base_cmd[@]}" "${pytest_extra_opts[@]}"
