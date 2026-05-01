#!/usr/bin/env bash
set -euo pipefail

BACKENDS_CSV=""
PACKAGES_CSV="deb"
SSH_HOST=""
SSH_REPO=""
DRY_RUN=0
SKIP_BUILD=0
SKIP_PACKAGE=0
WITH_LOCAL_DATA=0
ASSUME_YES=0

usage() {
  cat <<'USAGE'
Uso: release_debian.sh [opcoes]

Orquestra build e pacote Debian amd64 de forma deterministica.

Opcoes:
  --backend LIST      pyinstaller,nuitka,pyoxidizer ou all
  --package LIST      deb,appimage ou all (default: deb)
  --ssh-host HOST     executa remotamente via ssh (ex: user@host)
  --ssh-repo DIR      caminho absoluto do repositorio no host remoto
  --with-local-data   copia dados locais para os artefatos
  --skip-build        nao recompila, apenas valida/empacota artefatos existentes
  --skip-package      nao gera .deb/AppImage; ainda valida artefatos de build
  --dry-run           valida ambiente e mostra plano sem executar build/pacote
  -y, --yes           nao perguntar interativamente
  -h, --help          mostra esta ajuda

Sem --backend, o script pergunta quais backends usar.
Com -y/--yes e sem --backend, usa todos os backends.
USAGE
}

log() {
  printf '[release_debian] %s\n' "$*"
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
  local -n output="$2"
  local item
  local raw_items=()
  while [[ "${csv}" == *, ]]; do
    csv="${csv%,}"
  done
  IFS=',' read -r -a raw_items <<<"${csv}"
  output=()
  for item in "${raw_items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    [[ -n "${item}" ]] || die "lista contem item vazio: ${csv}"
    output+=("${item}")
  done
}

join_csv() {
  local IFS=,
  printf '%s\n' "$*"
}

normalize_backends() {
  local csv="$1"
  local backend
  if [[ -z "${csv}" ]]; then
    die "backend vazio"
  fi
  if [[ "${csv}" == "all" ]]; then
    printf '%s\n' "pyinstaller,nuitka,pyoxidizer"
    return 0
  fi
  local items=()
  split_csv "${csv}" items
  for backend in "${items[@]}"; do
    case "${backend}" in
      pyinstaller | nuitka | pyoxidizer) ;;
      *) die "--backend invalido: ${backend}" ;;
    esac
  done
  join_csv "${items[@]}"
}

normalize_packages() {
  local csv="$1"
  local package_kind
  if [[ -z "${csv}" || "${csv}" == "all" ]]; then
    printf '%s\n' "deb,appimage"
    return 0
  fi
  local items=()
  split_csv "${csv}" items
  for package_kind in "${items[@]}"; do
    case "${package_kind}" in
      deb | appimage) ;;
      *) die "--package invalido: ${package_kind}" ;;
    esac
  done
  join_csv "${items[@]}"
}

select_backend_interactively() {
  local answer
  cat <<'CHOICES'
Backends disponiveis:
  1) pyinstaller
  2) nuitka
  3) pyoxidizer
  4) all

Nota resumida:
  pyinstaller: seguranca media, codigo Python mais exposto, boa compatibilidade.
  nuitka: seguranca maior, codigo menos exposto, build mais pesado.
  pyoxidizer: seguranca media/alta, runtime mais fechado, maior risco operacional.
CHOICES
  read -r -p "Escolha backend(s) [all]: " answer
  case "${answer:-all}" in
    1 | pyinstaller) printf '%s\n' "pyinstaller" ;;
    2 | nuitka) printf '%s\n' "nuitka" ;;
    3 | pyoxidizer) printf '%s\n' "pyoxidizer" ;;
    4 | all) printf '%s\n' "pyinstaller,nuitka,pyoxidizer" ;;
    *) printf '%s\n' "${answer}" ;;
  esac
}

get_backend_scorecard() {
  local backend="$1"
  uv run --python 3.13 python "$(repo_root)/dev_env/build/release_debian_report.py" \
    scorecard \
    --backend "${backend}"
}

assert_tool() {
  local tool="$1"
  command -v "${tool}" >/dev/null 2>&1 || die "comando ausente: ${tool}"
}

assert_ssh_host() {
  local host="$1"
  if [[ ! "${host}" =~ ^([A-Za-z0-9._-]+@)?[A-Za-z0-9._-]+$ ]]; then
    die "--ssh-host invalido. Use apenas user@host ou host sem opcoes ssh."
  fi
}

assert_ssh_repo() {
  local repo="$1"
  if [[ ! "${repo}" =~ ^/[A-Za-z0-9._/@%+=:,~-]+$ ]]; then
    die "--ssh-repo invalido. Use caminho absoluto sem espacos/metacaracteres."
  fi
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

assert_debian_amd64() {
  local machine
  machine="$(uname -m)"
  case "${machine}" in
    x86_64 | amd64) ;;
    *) die "este orquestrador e para debian_amd64; arquitetura atual: ${machine}" ;;
  esac
}

assert_clean_release_workspace() {
  local root="$1"
  local dirty
  dirty="$(git -C "${root}" status --porcelain)"
  if [[ -n "${dirty}" ]]; then
    printf '%s\n' "${dirty}" >&2
    die "workspace sujo. Release deterministico exige git limpo."
  fi
}

git_head() {
  local root="$1"
  git -C "${root}" rev-parse HEAD
}

read_app_version() {
  local root="$1"
  uv run --python 3.13 python "${root}/dev_env/build/release_debian_report.py" \
    app-version \
    --version-file "${root}/config/version.json"
}

run_remote_release() {
  [[ -n "${SSH_REPO}" ]] || die "--ssh-repo e obrigatorio com --ssh-host"
  assert_ssh_repo "${SSH_REPO}"
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    die "--with-local-data nao e suportado via SSH; execute localmente no host Debian com os dados ja presentes."
  fi
  local remote_flags=()
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
bash dev_env/build/release_debian.sh --backend "${backends}" --package "${packages}" -y "$@"
REMOTE_RELEASE
}

validate_build_payload() {
  local root="$1"
  local backend="$2"
  local app_version="$3"
  local git_commit="$4"
  local build_root=""
  local bundle_root=""
  local bundle_roots=()

  case "${backend}" in
    pyinstaller)
      build_root="${root}/launchers/dist/debian_amd64"
      [[ -d "${build_root}" ]] || build_root="${root}/builds/pyinstaller/debian_amd64"
      bundle_roots=(
        "${build_root}/SSA_CLI_v${app_version}_debian_amd64"
        "${build_root}/SSA_GUI_v${app_version}_debian_amd64"
      )
      ;;
    nuitka)
      build_root="${root}/builds/nuitka/debian_amd64"
      bundle_roots=(
        "${build_root}/cli_entry.dist"
        "${build_root}/gui_entry.dist"
      )
      ;;
    pyoxidizer)
      build_root="${root}/builds/pyoxidizer/debian_amd64"
      bundle_roots=("${build_root}")
      ;;
  esac

  [[ -d "${build_root}" ]] || die "artefato ${backend} nao encontrado: ${build_root}"

  for bundle_root in "${bundle_roots[@]}"; do
    [[ -d "${bundle_root}" ]] || die "bundle ${backend} ausente: ${bundle_root}"
    [[ -f "${bundle_root}/config/build_info.json" ]] || die "build_info.json ausente em ${bundle_root}"
    [[ -f "${bundle_root}/docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md" ]] || die "GUIA_MIGRACAO_NOVA_INSTALACAO.md ausente em ${bundle_root}"

    uv run --python 3.13 python "${root}/dev_env/build/release_debian_report.py" \
      validate-build-info \
      --build-info "${bundle_root}/config/build_info.json" \
      --backend "${backend}" \
      --platform "debian_amd64" \
      --app-version "${app_version}" \
      --git-commit "${git_commit}"
  done
}

run_build_backend() {
  local root="$1"
  local backend="$2"
  local args=(--silent)
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    args+=(--with-local-data)
  fi
  case "${backend}" in
    pyinstaller) bash "${root}/dev_env/build/build_pyinstaller_debian.sh" "${args[@]}" ;;
    nuitka) bash "${root}/dev_env/build/build_nuitka_debian.sh" "${args[@]}" ;;
    pyoxidizer) bash "${root}/dev_env/build/build_pyoxidizer_debian.sh" "${args[@]}" ;;
    *) die "backend desconhecido: ${backend}" ;;
  esac
}

run_package_backend() {
  local root="$1"
  local backend="$2"
  local package_kind="$3"
  case "${package_kind}:${backend}" in
    deb:*)
      bash "${root}/dev_env/build/package_debian_amd64_deb.sh" --build-system "${backend}"
      ;;
    appimage:pyinstaller | appimage:nuitka)
      bash "${root}/dev_env/build/package_debian_amd64_appimage.sh" --build-system "${backend}"
      ;;
    appimage:pyoxidizer)
      die "AppImage pyoxidizer nao suportado pelos scripts atuais. Use --package deb para pyoxidizer."
      ;;
    *)
      die "pacote invalido: ${package_kind}:${backend}"
      ;;
  esac
}

validate_package_payload() {
  local root="$1"
  local backend="$2"
  local package_kind="$3"
  local app_version="$4"
  local package_dir="${root}/builds/packages/debian_amd64"
  local package_contents=""
  local package_file=""
  case "${package_kind}:${backend}" in
    deb:*)
      package_file="${package_dir}/ssa-consulta-rapida-${backend}-amd64_${app_version}_amd64.deb"
      [[ -f "${package_file}" ]] || die "pacote .deb ausente: ${package_file}"
      package_contents="$(dpkg-deb -c "${package_file}")"
      grep -F "GUIA_MIGRACAO_NOVA_INSTALACAO.md" <<<"${package_contents}" >/dev/null || die "guia ausente no .deb ${backend}"
      grep -F "build_info.json" <<<"${package_contents}" >/dev/null || die "build_info ausente no .deb ${backend}"
      ;;
    appimage:pyinstaller | appimage:nuitka)
      package_file="${package_dir}/SSA_Consulta_Rapida_v${app_version#v}_debian_amd64_${backend}.AppImage"
      [[ -x "${package_file}" ]] || die "AppImage ausente ou sem execucao: ${package_file}"
      ;;
    appimage:pyoxidizer)
      die "AppImage pyoxidizer nao suportado pelos scripts atuais. Use --package deb para pyoxidizer."
      ;;
  esac
}

write_release_report() {
  local root="$1"
  local report_file="$2"
  local backend_csv="$3"
  local package_csv="$4"
  local app_version="$5"
  local git_commit="$6"
  uv run --python 3.13 python "${root}/dev_env/build/release_debian_report.py" \
    write-report \
    --repo-root "${root}" \
    --report-file "${report_file}" \
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
        ASSUME_YES=1
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
  if [[ -z "${BACKENDS_CSV}" ]]; then
    if [[ "${ASSUME_YES}" == "1" ]]; then
      BACKENDS_CSV="pyinstaller,nuitka,pyoxidizer"
    elif [[ ! -t 0 ]]; then
      die "--backend e obrigatorio em ambiente nao interativo. Use --backend LIST ou -y."
    else
      BACKENDS_CSV="$(select_backend_interactively)"
    fi
  fi
  BACKENDS_CSV="$(normalize_backends "${BACKENDS_CSV}")"
  PACKAGES_CSV="$(normalize_packages "${PACKAGES_CSV}")"
}

assert_local_environment() {
  assert_debian_host
  assert_debian_amd64
  assert_tool git
  assert_tool uv
  assert_tool bash
  if [[ "${PACKAGES_CSV}" == *deb* ]]; then
    assert_tool dpkg-deb
  fi
  if [[ "${PACKAGES_CSV}" == *appimage* && "${SKIP_PACKAGE}" != "1" ]]; then
    assert_tool appimagetool
  fi
  assert_clean_release_workspace "${REPO_ROOT}"
}

load_release_metadata() {
  GIT_COMMIT="$(git_head "${REPO_ROOT}")"
  APP_VERSION="$(read_app_version "${REPO_ROOT}")"
  log "repo=${REPO_ROOT}"
  log "git=${GIT_COMMIT}"
  log "versao=${APP_VERSION}"
  log "backends=${BACKENDS_CSV}"
  log "packages=${PACKAGES_CSV}"
}

prepare_release_arrays() {
  split_csv "${BACKENDS_CSV}" BACKENDS
  split_csv "${PACKAGES_CSV}" PACKAGES
}

log_backend_scorecards() {
  local backend
  for backend in "${BACKENDS[@]}"; do
    log "scorecard ${backend}: $(get_backend_scorecard "${backend}")"
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

run_package_phase() {
  local backend
  local package_kind
  if [[ "${SKIP_PACKAGE}" != "1" ]]; then
    for backend in "${BACKENDS[@]}"; do
      for package_kind in "${PACKAGES[@]}"; do
        log "pacote ${package_kind} ${backend}"
        run_package_backend "${REPO_ROOT}" "${backend}" "${package_kind}"
        validate_package_payload "${REPO_ROOT}" "${backend}" "${package_kind}" "${APP_VERSION}"
      done
    done
  fi
}

run_local_release() {
  REPO_ROOT="$(repo_root)"
  REPORT_FILE="${REPO_ROOT}/builds/reports/release_report_debian_amd64.json"

  assert_local_environment
  load_release_metadata
  prepare_release_arrays
  log_backend_scorecards
  run_build_phase

  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi

  run_package_phase

  write_release_report "${REPO_ROOT}" "${REPORT_FILE}" "${BACKENDS_CSV}" "${PACKAGES_CSV}" "${APP_VERSION}" "${GIT_COMMIT}"
  log "report=${REPORT_FILE}"
  log "release Debian amd64 concluido"
}

main() {
  parse_args "$@"
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
