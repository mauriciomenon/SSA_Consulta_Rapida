#!/usr/bin/env bash
# Shared environment bootstrap used by .envrc and manual activation scripts.

if [[ -n "${SSA_ENV_COMMON_SOURCED:-}" ]]; then
  return 0
fi
SSA_ENV_COMMON_SOURCED=1

ssa_env__repo_root="${SSA_ENV_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

if [[ -z "${SSA_PYTHON_STABLE_VERSION+x}" ]]; then
  SSA_ENV__STABLE_FROM_ENV=0
else
  SSA_ENV__STABLE_FROM_ENV=1
fi
SSA_PYTHON_STABLE_VERSION="${SSA_PYTHON_STABLE_VERSION:-3.13.12}"
if [[ "${SSA_ENV__STABLE_FROM_ENV:-0}" -eq 0 && -f "${ssa_env__repo_root}/.python-version" ]]; then
  read -r SSA_ENV__FILE_VERSION < "${ssa_env__repo_root}/.python-version" || true
  SSA_ENV__FILE_VERSION=${SSA_ENV__FILE_VERSION%$'\r'}
  SSA_ENV__PYTHON_VERSION_RE='^[0-9]+\.[0-9]+(\.[0-9]+)?$'
  if [[ "${SSA_ENV__FILE_VERSION}" =~ $SSA_ENV__PYTHON_VERSION_RE ]]; then
    SSA_PYTHON_STABLE_VERSION="${SSA_ENV__FILE_VERSION}"
  fi
fi
unset SSA_ENV__STABLE_FROM_ENV
unset SSA_ENV__FILE_VERSION
unset SSA_ENV__PYTHON_VERSION_RE

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

ssa_env__python_version_matches() {
  local requested="$1"
  local actual="$2"
  if [[ -z "$requested" || -z "$actual" ]]; then
    return 1
  fi
  if [[ "$requested" =~ ^[0-9]+\.[0-9]+$ ]]; then
    [[ "$actual" == "${requested}."* ]]
    return $?
  fi
  [[ "$actual" == "$requested" ]]
}

ssa_env__ensure_venv_pip() {
  local dir="$1"
  local venv_python="$dir/bin/python"

  if [[ ! -x "$venv_python" ]]; then
    ssa_env__log "error: python executable missing in $dir"
    return 1
  fi

  if "$venv_python" -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  ssa_env__log "venv: pip missing in $dir; bootstrapping with ensurepip"
  if ! "$venv_python" -m ensurepip --upgrade >/dev/null 2>&1; then
    ssa_env__log "error: failed to bootstrap pip in $dir"
    return 1
  fi

  if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
    ssa_env__log "error: pip still unavailable in $dir after ensurepip"
    return 1
  fi

  return 0
}

ssa_env__refresh_command_cache() {
  # Refresh shell command hash table after PATH changes (notably for zsh/bash).
  if command -v rehash >/dev/null 2>&1; then
    rehash >/dev/null 2>&1 || true
    return
  fi
  if command -v hash >/dev/null 2>&1; then
    hash -r >/dev/null 2>&1 || true
  fi
}

ssa_env__activate_uv_venv() {
  if [[ "${SSA_SKIP_UV:-0}" == "1" ]]; then
    return 1
  fi
  if ! command -v uv >/dev/null 2>&1; then
    return 1
  fi

  local dir="$SSA_ENV_VENV_DIR"
  local requested="$SSA_ENV_PY_VERSION"
  local current_version=""
  local needs_recreate=0
  local uv_python_arg="$requested"
  local managed_python_path=""

  if [[ -x "$dir/bin/python" ]]; then
    current_version=$("$dir/bin/python" -V 2>/dev/null | awk '{print $2}')
    if ! ssa_env__python_version_matches "$requested" "$current_version"; then
      ssa_env__log "uv: recreating $dir (current $current_version, wanted $requested)"
      needs_recreate=1
    fi
  else
    needs_recreate=1
  fi

  if [[ ! -f "$dir/bin/activate" ]]; then
    needs_recreate=1
  fi

  if [[ "$needs_recreate" -eq 1 ]]; then
    if uv python install "$requested" >/dev/null 2>&1; then
      managed_python_path=$(uv python find --no-project --managed-python "$requested" 2>/dev/null || true)
      if [[ -n "$managed_python_path" ]]; then
        uv_python_arg="$managed_python_path"
      fi
    fi

    if ! uv venv --seed --clear --python "$uv_python_arg" "$dir" >/dev/null 2>&1; then
      # Last resort: let uv resolve through any available interpreter.
      if ! uv venv --seed --clear --python "$requested" "$dir" >/dev/null 2>&1; then
        ssa_env__log "error: uv failed to provision venv $dir for Python $requested"
        return 1
      fi
    fi
  fi

  if [[ -f "$dir/bin/activate" ]]; then
    if ! ssa_env__ensure_venv_pip "$dir"; then
      return 1
    fi
    # shellcheck disable=SC1091
    source "$dir/bin/activate"
    ssa_env__refresh_command_cache
    SSA_ENV_SOURCE="uv-venv"
    export SSA_ENV_SOURCE
    return 0
  fi

  ssa_env__log "error: activate script missing in $dir"
  return 1
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
    # Use pyenv local instead of shell to avoid session pollution
    if ! pyenv local "$version" >/dev/null 2>&1; then
      ssa_env__log "error: pyenv local $version failed"
      return 1
    fi
    # Ensure no session override remains
    pyenv shell --unset >/dev/null 2>&1 || true
    unset PYENV_VERSION
    # Let pyenv manage version via .python-version
    SSA_ENV_SOURCE="pyenv-local"
  fi
  export SSA_ENV_SOURCE
  return 0
}

ssa_env__activate_local_venv() {
  local dir="$SSA_ENV_VENV_DIR"
  local python_cmd="${SSA_ENV_FALLBACK_PYTHON:-python3}"

  if command -v uv >/dev/null 2>&1; then
    local uv_system_python=""
    uv_system_python=$(uv python find --no-project --system "$SSA_ENV_PY_VERSION" 2>/dev/null || true)
    if [[ -n "$uv_system_python" ]]; then
      python_cmd="$uv_system_python"
    fi
  fi

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
    if ! ssa_env__ensure_venv_pip "$dir"; then
      return 1
    fi
    # shellcheck disable=SC1091
    source "$dir/bin/activate"
    ssa_env__refresh_command_cache
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

  if [[ -n "${VIRTUAL_ENV:-}" && -d "${VIRTUAL_ENV}/bin" ]]; then
    case ":$PATH:" in
      *":${VIRTUAL_ENV}/bin:"*) ;;
      *) export PATH="${VIRTUAL_ENV}/bin:${PATH}" ;;
    esac
  fi

  if [[ -z "${SSA_ENV_PATH_APPLIED:-}" ]]; then
    export PATH="$ssa_env__repo_root/scripts:$ssa_env__repo_root/scripts_manutencao:$PATH"
    SSA_ENV_PATH_APPLIED=1
    export SSA_ENV_PATH_APPLIED
  fi
  ssa_env__refresh_command_cache
  export SSA_ENV_ACTIVE=1
}

ssa_env__print_summary() {
  local context="$1"
  local py_version
  py_version=$(python -V 2>/dev/null | awk '{print $2}')
  local source_note="$SSA_ENV_SOURCE"
  if [[ "$SSA_ENV_SOURCE" == "pyenv-virtualenv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_PYENV_NAME"
  elif [[ "$SSA_ENV_SOURCE" == "pyenv-local" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_PY_VERSION"
  elif [[ "$SSA_ENV_SOURCE" == "uv-venv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_VENV_DIR"
  elif [[ "$SSA_ENV_SOURCE" == "venv" ]]; then
    source_note="$SSA_ENV_SOURCE:$SSA_ENV_VENV_DIR"
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
  local env_ready=0

  if ssa_env__activate_uv_venv; then
    env_ready=1
  else
    ssa_env__log "warn: uv setup failed; trying pyenv/local fallback"
  fi

  if [[ $env_ready -eq 0 ]] && ssa_env__init_pyenv; then
    if ssa_env__ensure_pyenv_env; then
      env_ready=1
    else
      ssa_env__log "warn: pyenv setup failed; falling back to local venv"
    fi
  fi

  if [[ $env_ready -eq 0 ]]; then
    if ! ssa_env__activate_local_venv; then
      return 1
    fi
  fi
  ssa_env__apply_path_exports
  ssa_env__print_summary "$context"
  return 0
}
