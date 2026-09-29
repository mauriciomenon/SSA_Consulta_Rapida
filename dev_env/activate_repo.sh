#!/usr/bin/env bash
# Manual activation helper for POSIX shells (WSL/macOS/Linux).
# Usage: source ./activate_repo.sh

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "[activate_repo] please source this script: source ./activate_repo.sh" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/env/direnv_common.sh"

ssa_env::apply manual
