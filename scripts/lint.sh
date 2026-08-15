#!/usr/bin/env bash
set -euo pipefail
# Script de lint desativado (Ruff removido). Mantido apenas placeholder.
# Uso atual:
#   ./scripts/lint.sh            # informa que lint esta desativado
#   ./scripts/lint.sh fix        # apenas roda black se disponivel

PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$PROJECT_ROOT"

mode="${1:-check}"

if [[ "$mode" == "fix" ]]; then
  echo "[lint] Ruff desativado. Rodando apenas black se instalado." >&2
  if command -v black >/dev/null 2>&1; then
    black . || true
  else
    echo "[lint] Black nao instalado; nada a fazer." >&2
  fi
  exit 0
fi

echo "[lint] Ruff desativado neste projeto. Nenhuma checagem executada." >&2
exit 0
