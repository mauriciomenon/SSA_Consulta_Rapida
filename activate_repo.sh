#!/usr/bin/env bash
# activate_repo.sh
# Apply the same environment changes as .envrc for bash/zsh (WSL, macOS)
# Usage: source ./activate_repo.sh

# Protect against multiple sourcing
if [[ -n "${ACTIVATE_REPO_SOURCED:-}" ]]; then
  return 0
fi
export ACTIVATE_REPO_SOURCED=1

# If pyenv is available, try to initialize and activate virtualenv from .python-version
if command -v pyenv >/dev/null 2>&1; then
  export PYENV_SHELL=sh
  # initialize pyenv (safe: won't fail if not configured)
  eval "$(pyenv init -)" 2>/dev/null || true
  eval "$(pyenv virtualenv-init -)" 2>/dev/null || true
fi

# If .python-version exists, try to activate that pyenv virtualenv
if [[ -f .python-version ]] && command -v pyenv >/dev/null 2>&1; then
  venv_name=$(tr -d '\r\n' < .python-version)
  if pyenv virtualenvs --bare | grep -qx "$venv_name"; then
    if [[ -z "${VIRTUAL_ENV:-}" || "${VIRTUAL_ENV##*/}" != "$venv_name" ]]; then
      pyenv activate "$venv_name" >/dev/null 2>&1 || true
    fi
  fi
fi

# Fallback: if .venv exists, source it
if [[ -z "${VIRTUAL_ENV:-}" && -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Export common env vars
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1

# Prepend project scripts to PATH
proj_dir="$(pwd)"
if [[ -d "$proj_dir/scripts" ]]; then
  export PATH="$proj_dir/scripts:$PATH"
fi
if [[ -d "$proj_dir/scripts_manutencao" ]]; then
  export PATH="$proj_dir/scripts_manutencao:$PATH"
fi

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "[activate_repo] Ambiente ativo: $(python -V 2>/dev/null | awk '{print $2}') ($(basename "$VIRTUAL_ENV"))"
else
  echo "[activate_repo] Nenhum ambiente virtual ativo (pyenv/.venv)"
fi
