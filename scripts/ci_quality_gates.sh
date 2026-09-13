#!/usr/bin/env bash
set -euo pipefail
# Script auxiliar para executar quality gates + smoke tests.
# Uso:
#   ./scripts/ci_quality_gates.sh              # gates + smoke (-m smoke)
#   GATES_ARGS="--skip check_docs" ./scripts/ci_quality_gates.sh
# Retornos:
#   0 -> tudo ok
#   1 -> falha em gates ou smoke
#   2 -> erro estrutural (ex.: script ausente)

GATES_ARGS=${GATES_ARGS:-}
PY=${PYTHON:-python}
GATES_ARGS_ARRAY=()
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 2
ssa_native_guard_tools "$PY" || exit 2
cd "$REPO_ROOT"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python nao encontrado" >&2
  exit 2
fi

if [ -n "$GATES_ARGS" ]; then
  parsed_gates_args_file=$(mktemp "${TMPDIR:-/tmp}/ssa-gates-args.XXXXXX") || exit 2
  trap 'rm -f "$parsed_gates_args_file"' EXIT
  "$PY" - "$GATES_ARGS" > "$parsed_gates_args_file" <<'PY' || exit 2
import shlex
import sys

try:
    args = shlex.split(sys.argv[1])
except ValueError as exc:
    print(f"[ci_quality_gates] GATES_ARGS invalido: {exc}", file=sys.stderr)
    sys.exit(2)

for arg in args:
    print(arg, end="\0")
PY
  while IFS= read -r -d '' arg; do
    GATES_ARGS_ARRAY+=("$arg")
  done < "$parsed_gates_args_file"
  rm -f "$parsed_gates_args_file"
  trap - EXIT
fi

set +e
# Bash 3.2 com nounset exige esta expansao para arrays vazios.
OUT=$("$PY" scripts/run_quality_gates.py ${GATES_ARGS_ARRAY[@]+"${GATES_ARGS_ARRAY[@]}"} 2>&1)
CODE=$?
set -e

QUALITY_GATES_JSONL="${QUALITY_GATES_JSONL:-quality_gates_output.jsonl}"
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | tail -n 1 > "$QUALITY_GATES_JSONL"

STATUS="error"
if [ $CODE -eq 0 ] || [ $CODE -eq 1 ]; then
  # tentar extrair
  if jq -e .overall_status >/dev/null 2>&1 < "$QUALITY_GATES_JSONL"; then
    STATUS=$(jq -r .overall_status < "$QUALITY_GATES_JSONL")
  fi
fi

echo "[ci_quality_gates] overall_status=${STATUS} (exit=${CODE})"

SMOKE_STATUS="ok"
set +e
"$PY" -m pytest -m "smoke" -q
SMOKE_CODE=$?
set -e
[ $SMOKE_CODE -eq 0 ] || SMOKE_STATUS="fail"

echo "[ci_quality_gates] smoke=${SMOKE_STATUS}"

if [ "${STATUS}" != "ok" ] || [ "${SMOKE_STATUS}" != "ok" ]; then
  exit 1
fi
exit 0
