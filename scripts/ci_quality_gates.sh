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
  while IFS= read -r arg; do
    GATES_ARGS_ARRAY+=("$arg")
  done < <(
    "$PY" -c 'import os, shlex; print(*shlex.split(os.environ["GATES_ARGS"]), sep="\n")'
  )
fi

set +e
OUT=$("$PY" scripts/run_quality_gates.py "${GATES_ARGS_ARRAY[@]}" 2>&1)
CODE=$?
set -e

echo "$OUT" | tail -n 1 > quality_gates_output.jsonl

STATUS="error"
if [ $CODE -eq 0 ] || [ $CODE -eq 1 ]; then
  # tentar extrair
  if jq -e .overall_status >/dev/null 2>&1 < quality_gates_output.jsonl; then
    STATUS=$(jq -r .overall_status < quality_gates_output.jsonl)
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
