#!/usr/bin/env bash

require_debian_package_context() {
  : "${DEBIAN_PLATFORM:?DEBIAN_PLATFORM nao definido}"
  : "${DEBIAN_PACKAGE_ARCH:?DEBIAN_PACKAGE_ARCH nao definido}"
  : "${DEBIAN_MACHINE_REGEX:?DEBIAN_MACHINE_REGEX nao definido}"
  : "${DEBIAN_APPIMAGE_ARCH:?DEBIAN_APPIMAGE_ARCH nao definido}"
  : "${DEBIAN_ARCH_LABEL:?DEBIAN_ARCH_LABEL nao definido}"
}

default_package_staging_dir() {
  local package_kind="$1"
  if [[ "${REPO_ROOT}" == /mnt/* ]]; then
    printf '%s\n' "${TMPDIR:-/tmp}/ssa_consulta_rapida_package/package_${DEBIAN_PLATFORM}_${package_kind}"
  else
    printf '%s\n' "${REPO_ROOT}/build/package_${DEBIAN_PLATFORM}_${package_kind}"
  fi
}

read_app_version() {
  local version_file="$1"
  local version=""
  if command -v jq >/dev/null 2>&1; then
    if version="$(jq -er '.version_short // empty' "${version_file}")" && [[ -n "${version}" ]]; then
      printf '%s\n' "${version}"
      return 0
    fi
  fi
  uv run --python 3.13 python - "${version_file}" <<'PY_VERSION'
import json
import pathlib
import sys

version_file = pathlib.Path(sys.argv[1])
payload = json.loads(version_file.read_text(encoding="utf-8"))
version = str(payload.get("version_short") or "").strip()
if not version:
    raise SystemExit(f"version_short ausente em {sys.argv[1]}")
print(version)
PY_VERSION
}

safe_reset_dir() {
  local dir="$1"
  local resolved_dir
  local allowed_build
  local allowed_packages
  local allowed_tmp_package
  resolved_dir="$(realpath -m -- "${dir}")"
  allowed_build="$(realpath -m -- "${REPO_ROOT}/build")"
  allowed_packages="$(realpath -m -- "${REPO_ROOT}/builds/packages")"
  allowed_tmp_package="$(realpath -m -- "${TMPDIR:-/tmp}/ssa_consulta_rapida_package")"
  if [[ -z "${dir}" || "${resolved_dir}" == "/" || "${resolved_dir}" == "${REPO_ROOT}" ]]; then
    echo "Erro: recusa limpar diretorio inseguro: ${dir}" >&2
    exit 1
  fi
  case "${resolved_dir}/" in
    "${allowed_build}/"* | "${allowed_packages}/"* | "${allowed_tmp_package}/"*) ;;
    *)
      echo "Erro: staging fora dos diretorios permitidos: ${resolved_dir}" >&2
      exit 1
      ;;
  esac
  rm -rf -- "${resolved_dir}"
  mkdir -p -- "${resolved_dir}"
  chmod 700 "${resolved_dir}"
}

clean_release_tree() {
  local root="$1"
  find "${root}" \
    \( -type d \( -name venv -o -name .venv -o -name __pycache__ -o -name .git -o -name .hg -o -name .svn -o -name .ssh \) -prune -exec rm -rf -- {} + \) -o \
    \( -type f \( \
      -name '*.bak' -o -name '*.bak-*' -o -name '*.bak.*' -o -name '*.example.bak_*' -o \
      -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o \
      -name '*.xlsx' -o -name '*.xls' -o -name '*.xlsm' -o \
      -name '.env' -o -name '.env.*' \
    \) -exec rm -f -- {} + \)
}

copy_dir_checked() {
  local src="$1"
  local dst="$2"
  if [[ ! -d "${src}" ]]; then
    echo "Erro: artefato esperado nao encontrado: ${src}" >&2
    exit 1
  fi
  mkdir -p -- "$(dirname -- "${dst}")"
  cp -a -- "${src}" "${dst}"
}

require_executable() {
  local executable_path="$1"
  if [[ ! -x "${executable_path}" ]]; then
    echo "Erro: executavel esperado nao encontrado ou sem permissao: ${executable_path}" >&2
    exit 1
  fi
}

first_existing_executable() {
  local candidate
  for candidate in "$@"; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  echo "Erro: nenhum executavel esperado foi encontrado." >&2
  printf 'Candidatos:\n' >&2
  for candidate in "$@"; do
    printf '  %s\n' "${candidate}" >&2
  done
  exit 1
}

write_wrapper() {
  local wrapper_path="$1"
  local target_path="$2"
  local args_text=""
  local arg
  local quoted_arg
  shift 2
  for arg in "$@"; do
    printf -v quoted_arg '%q' "${arg}"
    args_text+=" ${quoted_arg}"
  done
  cat >"${wrapper_path}" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail
exec "${target_path}"${args_text} "\$@"
WRAPPER
  chmod 0755 "${wrapper_path}"
}

assert_debian_machine() {
  local machine
  machine="$(uname -m)"
  if [[ ! "${machine}" =~ ${DEBIAN_MACHINE_REGEX} ]]; then
    echo "Erro: este script deve rodar em Debian ${DEBIAN_ARCH_LABEL}." >&2
    echo "Arquitetura atual: ${machine}" >&2
    exit 1
  fi
}
