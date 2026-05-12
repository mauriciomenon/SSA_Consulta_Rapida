#!/usr/bin/env bash
set -euo pipefail

PLATFORM="debian_arm64"
PACKAGE_ARCH="arm64"
MACHINE_LABEL="arm64/aarch64"
DEFAULT_BACKENDS_CSV="nuitka"
DEFAULT_PACKAGES_CSV="deb"

BACKENDS_CSV="${DEFAULT_BACKENDS_CSV}"
PACKAGES_CSV="${DEFAULT_PACKAGES_CSV}"
SSH_HOST=""
SSH_REPO=""
DRY_RUN=0
SKIP_BUILD=0
SKIP_PACKAGE=0
WITH_LOCAL_DATA=0
RELEASE_BACKENDS_CSV=""
RELEASE_PACKAGES_CSV=""
RELEASE_UNSUPPORTED_PAIRS=""

usage() {
  cat <<'USAGE'
Uso: release_debian_arm64.sh [opcoes]

Orquestra build e pacote Debian arm64 de forma deterministica.

Defaults:
  --backend nuitka
  --package deb

Opcoes:
  --backend LIST      lista de backends de release_targets.json ou all
  --package LIST      lista de pacotes de release_targets.json ou all
  --ssh-host HOST     executa remotamente via ssh (ex: user@host)
  --ssh-repo DIR      caminho absoluto do repositorio no host remoto
  --with-local-data   copia dados locais para os artefatos
  --skip-build        nao recompila, apenas valida/empacota artefatos existentes
  --skip-package      nao gera .deb/AppImage/tar; ainda valida artefatos de build
  --dry-run           valida ambiente e mostra plano sem executar build/pacote
  -y, --yes           aceito por paridade com release.sh
  -h, --help          mostra esta ajuda
USAGE
}

log() {
  printf '[release_debian_arm64] %s\n' "$*"
}

die() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}

repo_root() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
  cd -- "${script_dir}/../.." && pwd -P
}

split_csv() {
  local csv="${1%,}"
  local item
  local raw_items=()
  while [[ "${csv}" == *, ]]; do
    csv="${csv%,}"
  done
  IFS=',' read -r -a raw_items <<<"${csv}"
  for item in "${raw_items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    [[ -n "${item}" ]] || die "lista contem item vazio: ${csv}"
    printf '%s\n' "${item}"
  done
}

join_csv() {
  local IFS=,
  printf '%s\n' "$*"
}

release_report_cmd() {
  uv run --python 3.13 python "$(repo_root)/dev_env/build/release_platform_report.py" "$@"
}

release_targets_csv() {
  local kind="$1"
  if [[ "${kind}" == "backends" && -n "${RELEASE_BACKENDS_CSV}" ]]; then
    printf '%s\n' "${RELEASE_BACKENDS_CSV}"
    return 0
  fi
  if [[ "${kind}" == "packages" && -n "${RELEASE_PACKAGES_CSV}" ]]; then
    printf '%s\n' "${RELEASE_PACKAGES_CSV}"
    return 0
  fi
  release_report_cmd release-targets --platform "${PLATFORM}" --kind "${kind}"
}

load_release_target_cache() {
  RELEASE_BACKENDS_CSV="$(release_report_cmd release-targets --platform "${PLATFORM}" --kind backends)"
  RELEASE_PACKAGES_CSV="$(release_report_cmd release-targets --platform "${PLATFORM}" --kind packages)"
  RELEASE_UNSUPPORTED_PAIRS="$(release_report_cmd release-unsupported-pairs --platform "${PLATFORM}")"
  [[ -n "${RELEASE_BACKENDS_CSV}" ]] || die "release_targets.json nao retornou backends ${PLATFORM}"
  [[ -n "${RELEASE_PACKAGES_CSV}" ]] || die "release_targets.json nao retornou packages ${PLATFORM}"
}

csv_contains() {
  local csv="$1"
  local needle="$2"
  local item
  for item in $(split_csv "${csv}"); do
    [[ "${item}" == "${needle}" ]] && return 0
  done
  return 1
}

release_target_supported() {
  local backend="$1"
  local package_kind="$2"
  local unsupported_backend unsupported_package _unused_reason
  csv_contains "${RELEASE_BACKENDS_CSV}" "${backend}" || return 1
  csv_contains "${RELEASE_PACKAGES_CSV}" "${package_kind}" || return 1
  while IFS=$'\t' read -r unsupported_backend unsupported_package _unused_reason; do
    [[ -n "${unsupported_backend}" ]] || continue
    if [[ "${unsupported_backend}" == "${backend}" && "${unsupported_package}" == "${package_kind}" ]]; then
      return 1
    fi
  done <<<"${RELEASE_UNSUPPORTED_PAIRS}"
  return 0
}

release_target_reason() {
  local backend="$1"
  local package_kind="$2"
  local reason
  reason="$(
    printf '%s\n' "${RELEASE_UNSUPPORTED_PAIRS}" |
      awk -F '\t' -v b="${backend}" -v p="${package_kind}" '$1 == b && $2 == p { print $3; found=1; exit } END { if (!found) print "" }'
  )"
  if [[ -n "${reason}" ]]; then
    printf '%s\n' "${reason}"
    return 0
  fi
  printf 'par nao suportado por release_targets.json: %s/%s\n' "${backend}" "${package_kind}"
}

normalize_release_targets() {
  local csv="$1"
  local kind="$2"
  local invalid_error="$3"
  local target
  local valid_csv
  valid_csv="$(release_targets_csv "${kind}")"
  if [[ "${csv}" == "all" ]]; then
    printf '%s\n' "${valid_csv}"
    return 0
  fi
  local items=()
  for target in $(split_csv "${csv}"); do
    items+=("${target}")
  done
  for target in "${items[@]}"; do
    csv_contains "${valid_csv}" "${target}" || die "${invalid_error}: ${target}"
  done
  join_csv "${items[@]}"
}

normalize_backends() {
  normalize_release_targets "$1" "backends" "--backend invalido"
}

normalize_packages() {
  normalize_release_targets "$1" "packages" "--package invalido"
}

assert_tool() {
  local tool="$1"
  command -v "${tool}" >/dev/null 2>&1 || die "comando ausente: ${tool}"
}

assert_ssh_host() {
  local host="$1"
  case "${host}" in
    ""|-*|*@*@*|@*|*@|*[!A-Za-z0-9._@-]*)
      die "--ssh-host invalido. Use apenas user@host ou host sem opcoes ssh."
      ;;
  esac
}

assert_ssh_repo() {
  local repo="$1"
  case "${repo}" in
    /*) ;;
    *)
      die "--ssh-repo invalido. Use caminho absoluto sem espacos/metacaracteres."
      ;;
  esac
  case "${repo}" in
    *[!A-Za-z0-9._/@%+=:,~-]*)
      die "--ssh-repo invalido. Use caminho absoluto sem espacos/metacaracteres."
      ;;
  esac
}

assert_debian_host() {
  local os_name
  [[ "$(uname -s)" == "Linux" ]] || die "este script local deve rodar em Linux (Debian ou Ubuntu)"
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    os_name="$(. /etc/os-release && printf '%s' "${ID:-}")"
    [[ "${os_name}" == "debian" || "${os_name}" == "ubuntu" ]] || die "host Linux nao Debian/Ubuntu: ${os_name}"
  fi
}

assert_debian_arm64() {
  local machine
  machine="$(uname -m)"
  case "${machine}" in
    aarch64 | arm64) ;;
    *) die "este orquestrador e para ${PLATFORM}; arquitetura atual: ${machine}" ;;
  esac
}

assert_clean_release_workspace() {
  local root="$1"
  local staged unstaged untracked
  staged="$(git -C "${root}" diff --cached --name-only)"
  if [[ -n "${staged}" ]]; then
    printf '%s\n' "${staged}" >&2
    die "workspace sujo. Release deterministico exige git limpo."
  fi
  if git -C "${root}" diff --ignore-cr-at-eol --quiet; then
    unstaged=""
  else
    unstaged="$(git -C "${root}" diff --ignore-cr-at-eol --name-only)"
  fi
  untracked="$(git -C "${root}" ls-files --others --exclude-standard)"
  if [[ -n "${unstaged}${untracked}" ]]; then
    {
      printf '%s\n' "${unstaged}"
      printf '%s\n' "${untracked}"
    } | sed '/^$/d' >&2
    die "workspace sujo. Release deterministico exige git limpo."
  fi
}

git_head() {
  git -C "$1" rev-parse HEAD
}

read_app_version() {
  uv run --python 3.13 python "${REPO_ROOT}/dev_env/build/release_platform_report.py" \
    app-version \
    --version-file "${REPO_ROOT}/config/version.json"
}

run_remote_release() {
  [[ -n "${SSH_REPO}" ]] || die "--ssh-repo e obrigatorio com --ssh-host"
  assert_ssh_repo "${SSH_REPO}"
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    die "--with-local-data nao e suportado via SSH; execute localmente no host Debian com os dados ja presentes."
  fi
  local remote_flags=(-y)
  if [[ "${SKIP_BUILD}" == "1" ]]; then
    remote_flags+=(--skip-build)
  fi
  if [[ "${SKIP_PACKAGE}" == "1" ]]; then
    remote_flags+=(--skip-package)
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    remote_flags+=(--dry-run)
  fi
  log "executando remoto via ssh: ${SSH_HOST}"
  ssh "${SSH_HOST}" bash -s -- "${SSH_REPO}" "${BACKENDS_CSV}" "${PACKAGES_CSV}" "${remote_flags[@]}" <<'REMOTE_RELEASE'
set -euo pipefail
repo="$1"
backends="$2"
packages="$3"
shift 3
cd -- "${repo}"
bash dev_env/build/release_debian_arm64.sh --backend "${backends}" --package "${packages}" "$@"
REMOTE_RELEASE
}

# shellcheck source=dev_env/build/release_debian_arm64_backend.sh
source "$(repo_root)/dev_env/build/release_debian_arm64_backend.sh"

write_release_report() {
  local root="$1"
  local report_file="$2"
  local backend_csv="$3"
  local package_csv="$4"
  local app_version="$5"
  local git_commit="$6"
  uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
    write-report \
    --repo-root "${root}" \
    --report-file "${report_file}" \
    --platform "${PLATFORM}" \
    --backends "${backend_csv}" \
    --packages "${package_csv}" \
    --app-version "${app_version}" \
    --git-commit "${git_commit}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --backend)
        BACKENDS_CSV="${2:?valor ausente para --backend}"
        shift 2
        ;;
      --package)
        PACKAGES_CSV="${2:?valor ausente para --package}"
        shift 2
        ;;
      --ssh-host)
        SSH_HOST="${2:?valor ausente para --ssh-host}"
        shift 2
        ;;
      --ssh-repo)
        SSH_REPO="${2:?valor ausente para --ssh-repo}"
        shift 2
        ;;
      --with-local-data)
        WITH_LOCAL_DATA=1
        shift
        ;;
      --skip-build)
        SKIP_BUILD=1
        shift
        ;;
      --skip-package)
        SKIP_PACKAGE=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      -y | --yes)
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        die "opcao desconhecida: $1"
        ;;
    esac
  done
}

resolve_release_options() {
  BACKENDS_CSV="$(normalize_backends "${BACKENDS_CSV}")"
  PACKAGES_CSV="$(normalize_packages "${PACKAGES_CSV}")"
}

assert_local_environment() {
  assert_debian_host
  assert_debian_arm64
  assert_tool git
  assert_tool uv
  assert_tool bash
  if [[ "${PACKAGES_CSV}" == *deb* ]]; then
    assert_tool dpkg-deb
  fi
  if [[ "${PACKAGES_CSV}" == *tar* ]]; then
    assert_tool tar
  fi
  if [[ "${PACKAGES_CSV}" == *appimage* && "${SKIP_PACKAGE}" != "1" ]]; then
    assert_tool appimagetool
  fi
  assert_clean_release_workspace "${REPO_ROOT}"
}

load_release_metadata() {
  GIT_COMMIT="$(git_head "${REPO_ROOT}")"
  APP_VERSION="$(read_app_version)"
  log "repo=${REPO_ROOT}"
  log "git=${GIT_COMMIT}"
  log "versao=${APP_VERSION}"
  log "backends=${BACKENDS_CSV}"
  log "packages=${PACKAGES_CSV}"
  log "machine=${MACHINE_LABEL}"
}

prepare_release_arrays() {
  BACKENDS=()
  PACKAGES=()
  local item
  for item in $(split_csv "${BACKENDS_CSV}"); do
    BACKENDS+=("${item}")
  done
  for item in $(split_csv "${PACKAGES_CSV}"); do
    PACKAGES+=("${item}")
  done
}

log_package_matrix() {
  local backend
  local package_kind
  for backend in "${BACKENDS[@]}"; do
    log "scorecard ${backend}: $(release_report_cmd scorecard --backend "${backend}")"
    for package_kind in "${PACKAGES[@]}"; do
      if is_supported_package_pair "${backend}" "${package_kind}"; then
        log "pacote planejado ${package_kind} ${backend}"
      else
        log "pacote ignorado ${package_kind} ${backend}: $(release_target_reason "${backend}" "${package_kind}")"
      fi
    done
  done
}

run_build_phase() {
  local backend
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "dry-run concluido sem build/pacote"
    return 0
  fi

  for backend in "${BACKENDS[@]}"; do
    if [[ "${SKIP_BUILD}" != "1" ]]; then
      log "build ${backend}"
      run_build_backend "${REPO_ROOT}" "${backend}"
    fi
    validate_build_payload "${REPO_ROOT}" "${backend}" "${APP_VERSION}" "${GIT_COMMIT}"
  done
}

run_validation_phase() {
  local backend
  for backend in "${BACKENDS[@]}"; do
    run_functional_import_smoke "${REPO_ROOT}" "${backend}" "${APP_VERSION}"
  done
}

run_package_phase() {
  local backend
  local package_kind
  if [[ "${SKIP_PACKAGE}" != "1" ]]; then
    for backend in "${BACKENDS[@]}"; do
      for package_kind in "${PACKAGES[@]}"; do
        if ! is_supported_package_pair "${backend}" "${package_kind}"; then
          log "pacote ignorado ${package_kind} ${backend}: $(release_target_reason "${backend}" "${package_kind}")"
          continue
        fi
        log "pacote ${package_kind} ${backend}"
        run_package_backend "${REPO_ROOT}" "${backend}" "${package_kind}"
        validate_package_payload "${REPO_ROOT}" "${backend}" "${package_kind}" "${APP_VERSION}"
      done
    done
  fi
}

run_local_release() {
  REPORT_FILE="${REPO_ROOT}/builds/reports/release_report_${PLATFORM}.json"

  assert_local_environment
  if [[ -z "${RELEASE_BACKENDS_CSV}" || -z "${RELEASE_PACKAGES_CSV}" ]]; then
    load_release_target_cache
  fi
  load_release_metadata
  prepare_release_arrays
  log_package_matrix
  run_build_phase

  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi

  run_validation_phase
  run_package_phase

  write_release_report "${REPO_ROOT}" "${REPORT_FILE}" "${BACKENDS_CSV}" "${PACKAGES_CSV}" "${APP_VERSION}" "${GIT_COMMIT}"
  log "report=${REPORT_FILE}"
  log "release Debian arm64 concluido"
}

main() {
  parse_args "$@"
  REPO_ROOT="$(repo_root)"
  assert_tool uv
  load_release_target_cache
  resolve_release_options

  if [[ -n "${SSH_HOST}" ]]; then
    assert_tool ssh
    assert_ssh_host "${SSH_HOST}"
    run_remote_release
    exit 0
  fi

  run_local_release
}

main "$@"
