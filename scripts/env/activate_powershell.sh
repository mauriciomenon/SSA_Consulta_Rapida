#!/usr/bin/env bash
# PowerShell activation script for SSA_Consulta_Rapida (Windows)
# This script automatically detects and activates the correct Python environment

# Prevent recursive sourcing
if [[ -n "${SSA_ENV_POWERSHELL_ACTIVE:-}" ]]; then
  return 0
fi
export SSA_ENV_POWERSHELL_ACTIVE=1

# Get script directory (Scripts for Windows, bin for Unix)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source common environment
watch_file "$SCRIPT_DIR/direnv_common.ps1"
watch_file "$REPO_ROOT/.python-version"

# Execute PowerShell bootstrap (emulated in bash)
if [[ -f "$SCRIPT_DIR/direnv_common.ps1" ]]; then
  # Extract key variables from PowerShell script for bash compatibility
  export SSA_ENV_REPO_ROOT="$REPO_ROOT"
  
  # Read Python version
  if [[ -f "$REPO_ROOT/.python-version" ]]; then
    read -r SSA_PYTHON_STABLE_VERSION < "$REPO_ROOT/.python-version" || true
    SSA_PYTHON_STABLE_VERSION="${SSA_PYTHON_STABLE_VERSION%$'\r'}"
  fi
  export SSA_PYTHON_STABLE_VERSION="${SSA_PYTHON_STABLE_VERSION:-3.13.9}"
  export SSA_ENV_VARIANT="stable"
  export SSA_ENV_PY_VERSION="$SSA_PYTHON_STABLE_VERSION"
  export SSA_ENV_VENV_DIR=".venv"
  
  # Windows-specific paths
  if command -v python >/dev/null 2>&1; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo "[env] PowerShell bootstrap: python $PYTHON_VERSION ($SSA_ENV_VARIANT via venv:$SSA_ENV_VENV_DIR)"
  fi
  
  # Environment exports
  export PYTHONUTF8=1
  export PYTHONDONTWRITEBYTECODE=1
  export SSA_ENV_ACTIVE=1
  
  # Add scripts to PATH (Windows format)
  export PATH="$REPO_ROOT/scripts:$REPO_ROOT/scripts_manutencao:$PATH"
  
  echo "[env] PowerShell environment ready for Windows"
else
  echo "[env] Error: PowerShell bootstrap not found"
  return 1
fi