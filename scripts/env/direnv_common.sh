#!/usr/bin/env bash
# Shared environment bootstrap used by .envrc and manual activation scripts.

if [[ -n "${SSA_ENV_COMMON_SOURCED:-}" ]]; then
  return 0
fi
export SSA_ENV_COMMON_SOURCED=1

ssa_env__repo_root="${SSA_ENV_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

if [[ -z "${SSA_PYTHON_STABLE_VERSION+x}" ]]; then
  SSA_ENV__STABLE_FROM_ENV=0
else
  SSA_ENV__STABLE_FROM_ENV=1
fi
SSA_PYTHON_STABLE_VERSION="${SSA_PYTHON_STABLE_VERSION:-3.13.7}"
if [[ "${SSA_ENV__STABLE_FROM_ENV:-0}" -eq 0 && -f "${ssa_env__repo_root}/.python-version" ]]; then
  read -r SSA_ENV__FILE_VERSION < "${ssa_env__repo_root}/.python-version" || true
  SSA_ENV__FILE_VERSION=${SSA_ENV__FILE_VERSION%$'\r'}
  if [[ "${SSA_ENV__FILE_VERSION}" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    SSA_PYTHON_STABLE_VERSION="${SSA_ENV__FILE_VERSION}"
  fi
fi
unset SSA_ENV__STABLE_FROM_ENV
unset SSA_ENV__FILE_VERSION

SSA_PYTHON_FT_VERSION="${SSA_PYTHON_FT_VERSION:-3.14-dev}"
ssa_env__log() {
  printf '[env] %s\n' "$*"
}

ssa_env__sanitize_for_name() {
  local raw="$1"
  local lowered
  local sanitized
  lowered=$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')
  sanitized=$(printf '%s' "$lowered" | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//')
  printf '%s' "$sanitized"
}

ssa_env__determine_variant() {
  local requested="${SSA_PYTHON_VARIANT:-}"
  if [[ -n "${SSA_USE_FREE_THREADED:-}" && "${SSA_USE_FREE_THREADED}" != "0" ]]; then
    requested="free-threaded"
  fi
  case "$requested" in
    ''|default|stable|prod|production)
      SSA_ENV_VARIANT="stable"
      SSA_ENV_PY_VERSION="$SSA_PYTHON_STABLE_VERSION"
      SSA_ENV_VENV_DIR=".venv"
      ;;
    ft|free-threaded|free_threaded|freeThreaded|free)
      SSA_ENV_VARIANT="free-threaded"
      SSA_ENV_PY_VERSION="$SSA_PYTHON_FT_VERSION"
      SSA_ENV_VENV_DIR=".venv_ft"
      ;;
    *)
      ssa_env__log "note: unknown SSA_PYTHON_VARIANT '$requested', using stable"
      SSA_ENV_VARIANT="stable"
      SSA_ENV_PY_VERSION="$SSA_PYTHON_STABLE_VERSION"
      SSA_ENV_VENV_DIR=".venv"
      ;;
  esac
  if [[ -n "${SSA_VENV_DIR_OVERRIDE:-}" ]]; then
    SSA_ENV_VENV_DIR="$SSA_VENV_DIR_OVERRIDE"
  fi
  local sanitized
  sanitized=$(ssa_env__sanitize_for_name "$SSA_ENV_PY_VERSION")
  if [[ -z "$sanitized" ]]; then
    sanitized="python"
  fi
  SSA_ENV_PYENV_NAME="ssa_consulta_${SSA_ENV_VARIANT}_${sanitized}"
  export SSA_ENV_VARIANT SSA_ENV_PY_VERSION SSA_ENV_VENV_DIR SSA_ENV_PYENV_NAME
}

ssa_env__init_pyenv() {
  if [[ "${SSA_SKIP_PYENV:-0}" == "1" ]]; then
    SSA_ENV_PYENV_INITIALIZED=1
    SSA_ENV_PYENV_AVAILABLE=0
    SSA_ENV_PYENV_HAS_VIRTUALENV=0
    export SSA_ENV_PYENV_INITIALIZED SSA_ENV_PYENV_AVAILABLE SSA_ENV_PYENV_HAS_VIRTUALENV
    return 1
  fi
  if [[ "${SSA_ENV_PYENV_INITIALIZED:-}" == "1" ]]; then
    [[ "${SSA_ENV_PYENV_AVAILABLE:-0}" == "1" ]]
    return $?
  fi
  SSA_ENV_PYENV_INITIALIZED=1
  if ! command -v pyenv >/dev/null 2>&1; then
    SSA_ENV_PYENV_AVAILABLE=0
    export SSA_ENV_PYENV_INITIALIZED SSA_ENV_PYENV_AVAILABLE SSA_ENV_PYENV_HAS_VIRTUALENV=0
    return 1
  fi
  export PYENV_SHELL=sh

  # Detect pyenv-win (Windows) vs regular pyenv
  local pyenv_root
  if [[ -n "${PYENV_ROOT:-}" ]]; then
    pyenv_root="$PYENV_ROOT"
  else
    # Try multiple locations (Unix and Windows)
    local home_dir="${HOME:-${USERPROFILE:-}}"
    if [[ -z "$home_dir" && -n "${HOMEDRIVE:-}" && -n "${HOMEPATH:-}" ]]; then
      home_dir="${HOMEDRIVE}${HOMEPATH}"
    fi
    # Convert Windows path to Unix-style if needed
    if [[ "$home_dir" =~ ^[A-Za-z]: ]]; then
      home_dir=$(cygpath -u "$home_dir" 2>/dev/null || echo "$home_dir")
    fi
    if [[ -d "$home_dir/.pyenv/pyenv-win" ]]; then
      pyenv_root="$home_dir/.pyenv/pyenv-win"
    elif [[ -d "$home_dir/.pyenv" ]]; then
      pyenv_root="$home_dir/.pyenv"
    fi
  fi

  # Try to run pyenv init (works on Unix, fails on pyenv-win)
  if eval "$(pyenv init -)" >/dev/null 2>&1; then
    # Regular pyenv - init worked
    :
  elif [[ -n "$pyenv_root" && -d "$pyenv_root/shims" ]]; then
    # pyenv-win or init failed - manually prepend shims to PATH
    # Ensure Unix-style paths for bash compatibility
    local shims_path="$pyenv_root/shims"
    local bin_path="$pyenv_root/bin"
    # Convert Windows paths to Unix-style if needed
    if [[ "$shims_path" =~ ^[A-Za-z]:[/\\] ]]; then
      shims_path=$(cygpath -u "$shims_path" 2>/dev/null || echo "$shims_path" | sed -E 's|^([A-Za-z]):|/\L\1|; s|\\|/|g')
    fi
    if [[ "$bin_path" =~ ^[A-Za-z]:[/\\] ]]; then
      bin_path=$(cygpath -u "$bin_path" 2>/dev/null || echo "$bin_path" | sed -E 's|^([A-Za-z]):|/\L\1|; s|\\|/|g')
    fi
    export PATH="$shims_path:$bin_path:$PATH"
  fi

  local has_virtualenv=0
  if pyenv commands 2>/dev/null | grep -qx 'virtualenv'; then
    eval "$(pyenv virtualenv-init -)" >/dev/null 2>&1 || true
    has_virtualenv=1
  fi
  SSA_ENV_PYENV_AVAILABLE=1
  SSA_ENV_PYENV_HAS_VIRTUALENV=$has_virtualenv
  export SSA_ENV_PYENV_INITIALIZED SSA_ENV_PYENV_AVAILABLE SSA_ENV_PYENV_HAS_VIRTUALENV
  return 0
}

ssa_env__ensure_pyenv_env() {
  if [[ "${SSA_ENV_PYENV_AVAILABLE:-0}" -ne 1 ]]; then
    return 1
  fi
  local version="$SSA_ENV_PY_VERSION"
  local env_name="$SSA_ENV_PYENV_NAME"
  if ! pyenv versions --bare 2>/dev/null | grep -Fx "$version" >/dev/null; then
    ssa_env__log "pyenv: installing Python $version (first run may take a while)"
    if ! pyenv install "$version"; then
      ssa_env__log "error: pyenv install $version failed"
      return 1
    fi
  fi
  if [[ "${SSA_ENV_PYENV_HAS_VIRTUALENV:-0}" -eq 1 ]]; then
    if ! pyenv virtualenvs --bare 2>/dev/null | grep -Fx "$env_name" >/dev/null; then
      ssa_env__log "pyenv: creating virtualenv $env_name"
      if ! pyenv virtualenv "$version" "$env_name"; then
        ssa_env__log "error: pyenv virtualenv $env_name failed"
        return 1
      fi
    fi
    if ! pyenv activate "$env_name" >/dev/null 2>&1; then
      ssa_env__log "error: pyenv activate $env_name failed"
      return 1
    fi
    SSA_ENV_SOURCE="pyenv-virtualenv"
  else
    if ! pyenv shell "$version" >/dev/null 2>&1; then
      ssa_env__log "error: pyenv shell $version failed"
      return 1
    fi
    # For pyenv-win compatibility: explicitly set PYENV_VERSION
    export PYENV_VERSION="$version"
    SSA_ENV_SOURCE="pyenv"
  fi
  export SSA_ENV_SOURCE
  return 0
}

ssa_env__activate_local_venv() {
  local dir="$SSA_ENV_VENV_DIR"
  local python_cmd="${SSA_ENV_FALLBACK_PYTHON:-python3}"
  if ! command -v "$python_cmd" >/dev/null 2>&1; then
    python_cmd="python"
  fi
  if [[ ! -d "$dir" ]]; then
    if [[ "$SSA_ENV_VARIANT" == "free-threaded" ]]; then
      ssa_env__log "warn: free-threaded variant requested but pyenv unavailable; using fallback venv $dir"
    else
      ssa_env__log "creating fallback venv $dir"
    fi
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
      ssa_env__log "error: python interpreter not found for fallback venv"
      return 1
    fi
    if ! "$python_cmd" -m venv "$dir"; then
      ssa_env__log "error: failed to create venv $dir"
      return 1
    fi
  fi
  if [[ -f "$dir/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$dir/bin/activate"
    SSA_ENV_SOURCE="venv"
    export SSA_ENV_SOURCE
    return 0
  fi
  ssa_env__log "error: activate script missing in $dir"
  return 1
}

ssa_env__apply_path_exports() {
  export PYTHONUTF8=1
  export PYTHONDONTWRITEBYTECODE=1
  export SSA_ENV_ROOT="$ssa_env__repo_root"
  if [[ -z "${SSA_ENV_PATH_APPLIED:-}" ]]; then
    export PATH="$ssa_env__repo_root/scripts:$ssa_env__repo_root/scripts_manutencao:$PATH"
    SSA_ENV_PATH_APPLIED=1
    export SSA_ENV_PATH_APPLIED
  fi
  export SSA_ENV_ACTIVE=1
}

ssa_env__print_summary() {
  local context="$1"
  local py_version
  py_version=$(python -V 2>/dev/null | awk '{print $2}')
  local source_note="$SSA_ENV_SOURCE"
  if [[ "$SSA_ENV_SOURCE" == "pyenv-virtualenv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_PYENV_NAME"
  elif [[ "$SSA_ENV_SOURCE" == "venv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_VENV_DIR"
  elif [[ "$SSA_ENV_SOURCE" == "pyenv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_PY_VERSION"
  fi
  ssa_env__log "python ${py_version:-unknown} ($SSA_ENV_VARIANT via ${source_note:-unknown})"
  if [[ "$SSA_ENV_VARIANT" == "free-threaded" && "$SSA_ENV_SOURCE" != "pyenv-virtualenv" ]]; then
    ssa_env__log "note: fallback environment may not have the free-threaded build"
  fi
  if [[ "$context" == "direnv" ]]; then
    ssa_env__log "direnv ready (run 'direnv allow' after changing this file)"
  fi
}

ssa_env::apply() {
  local context="${1:-direnv}"
  if [[ -z "${DIRENV_LOG_FORMAT:-}" ]]; then
    export DIRENV_LOG_FORMAT='[direnv] %s'
  fi
  ssa_env__determine_variant
  local used_pyenv=0
  if ssa_env__init_pyenv; then
    if ssa_env__ensure_pyenv_env; then
      used_pyenv=1
    else
      ssa_env__log "warn: pyenv setup failed; falling back to local venv"
    fi
  fi
  if [[ $used_pyenv -eq 0 ]]; then
    if ! ssa_env__activate_local_venv; then
      return 1
    fi
  fi
  ssa_env__apply_path_exports
  ssa_env__print_summary "$context"
  return 0
}

