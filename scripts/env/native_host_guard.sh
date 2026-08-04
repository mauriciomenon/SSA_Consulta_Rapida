#!/usr/bin/env bash

ssa_native_guard_fail() {
  printf '[native-guard] BLOCKED: %s\n' "$*" >&2
  return 1
}

ssa_native_guard_realpath() {
  local path="$1"
  local resolved=""

  if [[ -x /usr/bin/readlink ]]; then
    resolved=$(/usr/bin/readlink -f -- "$path" 2>/dev/null || true)
  fi
  if [[ -z "$resolved" ]] && command -v realpath >/dev/null 2>&1; then
    resolved=$(realpath "$path" 2>/dev/null || true)
  fi
  [[ -n "$resolved" ]] || return 1
  printf '%s\n' "$resolved"
}

ssa_native_guard_repo() {
  local repo_root="$1"
  local expected_wsl_root="${2:-${HOME}/gitlab_repo/ssa_consulta_rapida_pyqt6}"
  local windows_link_root="${HOME}/gitlab"
  local resolved_root=""
  local os_release=""
  local fs_type=""

  [[ -d "$repo_root" ]] || ssa_native_guard_fail "repo inexistente: $repo_root" || return 1
  [[ ! -L "$repo_root" ]] || ssa_native_guard_fail "repo nao pode ser symlink: $repo_root" || return 1
  resolved_root=$(cd -- "$repo_root" 2>/dev/null && pwd -P) || {
    ssa_native_guard_fail "nao foi possivel resolver o repo: $repo_root"
    return 1
  }

  case "$resolved_root" in
    /mnt/*|"${windows_link_root}"|"${windows_link_root}"/*|[A-Za-z]:*)
      ssa_native_guard_fail "filesystem Windows proibido para harness POSIX: $resolved_root"
      return 1
      ;;
  esac

  case "${OSTYPE:-}" in
    msys*|cygwin*|win32*)
      ssa_native_guard_fail "use PowerShell nativo para o repo Windows"
      return 1
      ;;
  esac

  if [[ -r /proc/sys/kernel/osrelease ]]; then
    IFS= read -r os_release < /proc/sys/kernel/osrelease || true
  fi
  if [[ "${os_release,,}" == *microsoft* ]]; then
    [[ "$resolved_root" == "$expected_wsl_root" ]] || {
      ssa_native_guard_fail "clone WSL invalido: $resolved_root; esperado: $expected_wsl_root"
      return 1
    }
    fs_type=$(/usr/bin/stat -f -c %T -- "$resolved_root" 2>/dev/null || true)
    [[ "$fs_type" == "ext2/ext3" ]] || {
      ssa_native_guard_fail "filesystem WSL invalido: ${fs_type:-desconhecido}; esperado: ext4"
      return 1
    }
    export TMPDIR=/tmp
    export TMP=/tmp
    export TEMP=/tmp
  fi
}

ssa_native_guard_tool() {
  local name="$1"
  local depth="${2:-0}"
  local path=""
  local resolved=""
  local signature=""
  local first_line=""
  local interpreter=""
  local token=""
  local windows_link_root="${HOME}/gitlab"
  local -a shebang_parts=()

  ((depth <= 4)) || {
    ssa_native_guard_fail "cadeia de interpretes excedeu o limite: $name"
    return 1
  }

  if [[ "$name" == */* ]]; then
    path="$name"
  else
    path=$(type -P -- "$name" 2>/dev/null || true)
  fi
  [[ -n "$path" && -x "$path" ]] || {
    ssa_native_guard_fail "ferramenta ausente ou nao executavel: $name"
    return 1
  }

  resolved=$(ssa_native_guard_realpath "$path") || {
    ssa_native_guard_fail "nao foi possivel resolver a ferramenta: $path"
    return 1
  }
  case "${resolved,,}" in
    /mnt/*|"${windows_link_root}"/*|*.exe|[a-z]:*)
      ssa_native_guard_fail "ferramenta Windows proibida no POSIX: $name -> $resolved"
      return 1
      ;;
  esac

  LC_ALL=C IFS= read -r -n 2 signature < "$resolved" || true
  [[ "$signature" != "MZ" ]] || {
    ssa_native_guard_fail "binario PE/Windows proibido no POSIX: $name -> $resolved"
    return 1
  }
  if [[ "$signature" == '#!' ]]; then
    IFS= read -r first_line < "$resolved" || true
    read -r -a shebang_parts <<< "${first_line#\#!}"
    interpreter="${shebang_parts[0]:-}"
    [[ -n "$interpreter" ]] || {
      ssa_native_guard_fail "shebang invalido: $resolved"
      return 1
    }
    ssa_native_guard_tool "$interpreter" "$((depth + 1))" || return 1
    if [[ "${interpreter##*/}" == "env" ]]; then
      for token in "${shebang_parts[@]:1}"; do
        [[ "$token" == -* ]] && continue
        ssa_native_guard_tool "$token" "$((depth + 1))" || return 1
        break
      done
    fi
  fi
}

ssa_native_guard_tools() {
  local tool
  for tool in "$@"; do
    ssa_native_guard_tool "$tool" || return 1
  done
}

ssa_native_guard_path() {
  local candidate="$1"
  local base_dir="${2:-$PWD}"
  local probe=""
  local resolved=""
  local windows_link_root="${HOME}/gitlab"

  case "$candidate" in
    /mnt/*|"${windows_link_root}"|"${windows_link_root}"/*|[A-Za-z]:*)
      ssa_native_guard_fail "caminho Windows proibido para escrita POSIX: $candidate"
      return 1
      ;;
  esac
  if [[ "$candidate" != /* ]]; then
    candidate="$base_dir/$candidate"
  fi

  probe="$candidate"
  while [[ ! -e "$probe" && "$probe" != "/" ]]; do
    probe="${probe%/*}"
    [[ -n "$probe" ]] || probe="/"
  done
  if [[ -e "$candidate" ]]; then
    resolved=$(ssa_native_guard_realpath "$candidate") || return 1
  elif [[ -d "$probe" ]]; then
    resolved=$(cd -- "$probe" 2>/dev/null && pwd -P) || return 1
  else
    ssa_native_guard_fail "nao foi possivel resolver o caminho: $candidate"
    return 1
  fi
  case "$resolved" in
    /mnt/*|"${windows_link_root}"|"${windows_link_root}"/*)
      ssa_native_guard_fail "destino resolve para filesystem Windows: $candidate -> $resolved"
      return 1
      ;;
  esac
}

ssa_native_guard_venv() {
  local venv_dir="$1"
  local config_line=""

  [[ -e "$venv_dir" ]] || return 0
  [[ -d "$venv_dir" && ! -L "$venv_dir" ]] || {
    ssa_native_guard_fail "venv invalida ou symlink: $venv_dir"
    return 1
  }
  [[ ! -e "$venv_dir/Scripts/python.exe" ]] || {
    ssa_native_guard_fail "venv Windows detectada no clone Linux: $venv_dir"
    return 1
  }
  [[ -x "$venv_dir/bin/python" && -f "$venv_dir/bin/activate" ]] || {
    ssa_native_guard_fail "venv incompleta; mova-a para quarentena e recrie: $venv_dir"
    return 1
  }
  if [[ -f "$venv_dir/pyvenv.cfg" ]]; then
    while IFS= read -r config_line; do
      case "$config_line" in
        home\ =\ [A-Za-z]:*|executable\ =\ [A-Za-z]:*)
          ssa_native_guard_fail "pyvenv.cfg aponta para Windows: $venv_dir"
          return 1
          ;;
      esac
    done < "$venv_dir/pyvenv.cfg"
  fi
  ssa_native_guard_tool "$venv_dir/bin/python"
}
