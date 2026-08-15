#!/usr/bin/env bash
# Wrapper to keep legacy naming. Usage: source ./activate_env.sh [variant]

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "[activate_env] please source this script: source ./activate_env.sh" >&2
  exit 1
fi

if [[ -n "${1:-}" ]]; then
  export SSA_PYTHON_VARIANT="$1"
fi

# shellcheck disable=SC1090
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/activate_repo.sh"

