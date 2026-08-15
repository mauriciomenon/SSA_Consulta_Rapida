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
RELEASE_BACKENDS_CSV=""
RELEASE_PACKAGES_CSV=""
RELEASE_UNSUPPORTED_PAIRS=""

usage() {
  cat <<'USAGE'
Uso: release_debian.sh [opcoes]

Orquestra build e pacote Debian amd64 de forma deterministica.

Opcoes:
  --backend LIST      lista de backends de release_targets.json ou all
  --package LIST      lista de pacotes de release_targets.json ou all (default: deb)
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
  release_report_cmd release-targets --platform debian_amd64 --kind "${kind}"
}

load_release_target_cache() {
  RELEASE_BACKENDS_CSV="$(release_report_cmd release-targets --platform debian_amd64 --kind backends)"
  RELEASE_PACKAGES_CSV="$(release_report_cmd release-targets --platform debian_amd64 --kind packages)"
  RELEASE_UNSUPPORTED_PAIRS="$(release_report_cmd release-unsupported-pairs --platform debian_amd64)"
  [[ -n "${RELEASE_BACKENDS_CSV}" ]] || die "release_targets.json nao retornou backends debian_amd64"
  [[ -n "${RELEASE_PACKAGES_CSV}" ]] || die "release_targets.json nao retornou packages debian_amd64"
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

csv_contains() {
  local csv="$1"
  local needle="$2"
  local item
  for item in $(split_csv "${csv}"); do
    [[ "${item}" == "${needle}" ]] && return 0
  done
  return 1
}

normalize_release_targets() {
  local csv="$1"
  local kind="$2"
  local empty_error="$3"
  local invalid_error="$4"
  local target
  local valid_csv
  valid_csv="$(release_targets_csv "${kind}")"
  if [[ -z "${csv}" ]]; then
    [[ -z "${empty_error}" ]] || die "${empty_error}"
    printf '%s\n' "${valid_csv}"
    return 0
  fi
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
  local csv="$1"
  normalize_release_targets "${csv}" "backends" "backend vazio" "--backend invalido"
}

normalize_packages() {
  local csv="$1"
  normalize_release_targets "${csv}" "packages" "" "--package invalido"
}

select_backend_interactively() {
  local answer
  local valid_csv
  local choices=()
  local backend
  local index=1
  valid_csv="$(release_targets_csv backends)"
  printf '%s\n' "Backends disponiveis:"
  for backend in $(split_csv "${valid_csv}"); do
    choices+=("${backend}")
    printf '  %s) %s\n' "${index}" "${backend}"
    index=$((index + 1))
  done
  printf '  %s) all\n' "${index}"
  cat <<'CHOICES'
Nota resumida:
  Consulte os scorecards detalhados no dry-run antes do build.
CHOICES
  read -r -p "Escolha backend(s) [all]: " answer
  if [[ -z "${answer}" || "${answer}" == "all" || "${answer}" == "${index}" ]]; then
    printf '%s\n' "${valid_csv}"
    return 0
  fi
  case "${answer}" in
    ''|*[!0-9]*)
      printf '%s\n' "${answer}"
      ;;
    *)
      if (( answer >= 1 && answer < index )); then
        printf '%s\n' "${choices[$((answer - 1))]}"
      else
        die "opcao de backend invalida: ${answer}"
      fi
      ;;
  esac
}

get_backend_scorecard() {
  local backend="$1"
  release_report_cmd scorecard --backend "${backend}"
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
  local staged unstaged untracked
  local ps_exe win_root ps_win_root dirty
  ps_exe="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
  if [[ "${root}" == /mnt/[A-Za-z]/* ]] && [[ -x "${ps_exe}" ]] && command -v wslpath >/dev/null 2>&1; then
    win_root="$(wslpath -w "${root}")"
    ps_win_root="$(printf '%s' "${win_root}" | sed "s/'/''/g")"
    if ! dirty="$("${ps_exe}" -NoProfile -NonInteractive -Command "& git -C '${ps_win_root}' status --porcelain=v1" 2>&1 | tr -d '\r')"; then
      printf '%s\n' "${dirty}" >&2
      die "nao foi possivel validar git limpo via Windows."
    fi
    if [[ -n "${dirty}" ]]; then
      printf '%s\n' "${dirty}" >&2
      die "workspace sujo. Release deterministico exige git limpo."
    fi
    return 0
  fi
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
  local root="$1"
  git -C "${root}" rev-parse HEAD
}

read_app_version() {
  local root="$1"
  uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
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
    local payload_root="${bundle_root}"
    if [[ -d "${bundle_root}/_internal" ]]; then
      payload_root="${bundle_root}/_internal"
    fi
    [[ -d "${bundle_root}" ]] || die "bundle ${backend} ausente: ${bundle_root}"
    [[ -f "${payload_root}/config/build_info.json" ]] || die "build_info.json ausente em ${payload_root}"
    [[ -f "${payload_root}/docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md" ]] || die "GUIA_MIGRACAO_NOVA_INSTALACAO.md ausente em ${payload_root}"

    uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
      validate-build-info \
      --build-info "${payload_root}/config/build_info.json" \
      --backend "${backend}" \
      --platform "debian_amd64" \
      --app-version "${app_version}" \
      --git-commit "${git_commit}"
    validate_source_protection "${root}" "${bundle_root}"
  done
}

resolve_import_smoke_executable() {
  local root="$1"
  local backend="$2"
  local app_version="$3"
  local smoke_exe=""
  case "${backend}" in
    pyinstaller)
      smoke_exe="${root}/launchers/dist/debian_amd64/SSA_CLI_v${app_version}_debian_amd64/SSA_CLI_v${app_version}_debian_amd64"
      if [[ ! -x "${smoke_exe}" ]]; then
        smoke_exe="${root}/builds/pyinstaller/debian_amd64/SSA_CLI_v${app_version}_debian_amd64/SSA_CLI_v${app_version}_debian_amd64"
      fi
      ;;
    nuitka)
      smoke_exe="${root}/builds/nuitka/debian_amd64/cli_entry.dist/SSA_CLI_v${app_version}_debian_amd64"
      ;;
    pyoxidizer)
      smoke_exe="${root}/builds/pyoxidizer/debian_amd64/SSA_Consulta_Rapida"
      ;;
    *)
      die "backend sem executavel para smoke de importacao: ${backend}"
      ;;
  esac
  [[ -x "${smoke_exe}" ]] || die "executavel ausente para smoke ${backend}: ${smoke_exe}"
  printf '%s\n' "${smoke_exe}"
}

run_functional_import_smoke() {
  local root="$1"
  local backend="$2"
  local app_version="$3"

  local smoke_exe
  smoke_exe="$(resolve_import_smoke_executable "${root}" "${backend}" "${app_version}")"
  local smoke_json
  local smoke_err
  smoke_json="$(mktemp)"
  smoke_err="$(mktemp)"
  if ! uv run --python 3.13 python "${root}/scripts/smoke_cli.py" --executable "${smoke_exe}" --json >"${smoke_json}" 2>"${smoke_err}"; then
    local stdout_text=""
    local stderr_text=""
    [[ -f "${smoke_json}" ]] && stdout_text="$(cat -- "${smoke_json}")"
    [[ -f "${smoke_err}" ]] && stderr_text="$(cat -- "${smoke_err}")"
    rm -f -- "${smoke_json}" "${smoke_err}"
    die "smoke importacao falhou ${backend}. stdout=${stdout_text} stderr=${stderr_text}"
  fi
  rm -f -- "${smoke_json}" "${smoke_err}"
  log "smoke importacao ${backend}: funcional"
}

validate_source_protection() {
  local root="$1"
  local artifact="$2"
  uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
    source-protection \
    --repo-root "${root}" \
    --artifact "${artifact}"
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
  if ! is_supported_package_pair "${backend}" "${package_kind}"; then
    die "$(release_target_reason "${backend}" "${package_kind}")"
  fi
  case "${package_kind}:${backend}" in
    deb:*)
      bash "${root}/dev_env/build/package_debian_amd64_deb.sh" --build-system "${backend}"
      ;;
    appimage:*)
      bash "${root}/dev_env/build/package_debian_amd64_appimage.sh" --build-system "${backend}"
      ;;
    tar:*)
      write_tar_packages "${root}" "${backend}"
      ;;
    *)
      die "pacote invalido: ${package_kind}:${backend}"
      ;;
  esac
}

write_tar_archive() {
  local source_parent="$1"
  local source_name="$2"
  local output_file="$3"
  local tmp_file="${output_file}.tmp"
  [[ -d "${source_parent}/${source_name}" ]] || die "diretorio para tar ausente: ${source_parent}/${source_name}"
  mkdir -p -- "$(dirname -- "${output_file}")"
  rm -f -- "${tmp_file}"
  tar \
    --sort=name \
    --mtime="UTC 1970-01-01" \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -C "${source_parent}" \
    -cf - \
    "${source_name}" \
    | gzip -n >"${tmp_file}"
  mv -f -- "${tmp_file}" "${output_file}"
}

write_tar_packages() {
  local root="$1"
  local backend="$2"
  local package_dir="${root}/builds/packages/debian_amd64"
  local app_version="${APP_VERSION:?APP_VERSION ausente}"
  case "${backend}" in
    pyinstaller)
      write_tar_archive \
        "${root}/launchers/dist/debian_amd64" \
        "SSA_CLI_v${app_version}_debian_amd64" \
        "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_cli.tar.gz"
      write_tar_archive \
        "${root}/launchers/dist/debian_amd64" \
        "SSA_GUI_v${app_version}_debian_amd64" \
        "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_gui.tar.gz"
      ;;
    nuitka)
      write_tar_archive \
        "${root}/builds/nuitka/debian_amd64" \
        "cli_entry.dist" \
        "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_cli.tar.gz"
      write_tar_archive \
        "${root}/builds/nuitka/debian_amd64" \
        "gui_entry.dist" \
        "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_gui.tar.gz"
      ;;
    pyoxidizer)
      write_tar_archive \
        "${root}/builds/pyoxidizer" \
        "debian_amd64" \
        "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyoxidizer.tar.gz"
      ;;
    *) die "backend invalido para tar: ${backend}" ;;
  esac
}

is_supported_package_pair() {
  local backend="$1"
  local package_kind="$2"
  release_target_supported "${backend}" "${package_kind}"
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
    appimage:*)
      package_file="${package_dir}/SSA_Consulta_Rapida_v${app_version#v}_debian_amd64_${backend}.AppImage"
      [[ -x "${package_file}" ]] || die "AppImage ausente ou sem execucao: ${package_file}"
      ;;
    tar:pyinstaller)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_cli.tar.gz"
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyinstaller_gui.tar.gz"
      ;;
    tar:nuitka)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_cli.tar.gz"
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_nuitka_gui.tar.gz"
      ;;
    tar:pyoxidizer)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_debian_amd64_pyoxidizer.tar.gz"
      ;;
  esac
}

validate_tar_payload() {
  local package_file="$1"
  local package_contents
  [[ -f "${package_file}" ]] || die "pacote tar ausente: ${package_file}"
  validate_source_protection "${REPO_ROOT:?REPO_ROOT ausente}" "${package_file}"
  package_contents="$(tar -tzf "${package_file}")"
  grep -F "GUIA_MIGRACAO_NOVA_INSTALACAO.md" <<<"${package_contents}" >/dev/null || die "guia ausente no tar ${package_file}"
  grep -F "build_info.json" <<<"${package_contents}" >/dev/null || die "build_info ausente no tar ${package_file}"
}

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
    --platform "debian_amd64" \
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
      BACKENDS_CSV="$(release_targets_csv backends)"
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
  APP_VERSION="$(read_app_version "${REPO_ROOT}")"
  log "repo=${REPO_ROOT}"
  log "git=${GIT_COMMIT}"
  log "versao=${APP_VERSION}"
  log "backends=${BACKENDS_CSV}"
  log "packages=${PACKAGES_CSV}"
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

log_backend_scorecards() {
  local backend
  for backend in "${BACKENDS[@]}"; do
    log "scorecard ${backend}: $(get_backend_scorecard "${backend}")"
  done
}

log_package_matrix() {
  local backend
  local package_kind
  for backend in "${BACKENDS[@]}"; do
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
  REPORT_FILE="${REPO_ROOT}/builds/reports/release_report_debian_amd64.json"

  assert_local_environment
  if [[ -z "${RELEASE_BACKENDS_CSV}" || -z "${RELEASE_PACKAGES_CSV}" ]]; then
    load_release_target_cache
  fi
  load_release_metadata
  prepare_release_arrays
  log_backend_scorecards
  log_package_matrix
  run_build_phase

  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi

  run_validation_phase
  run_package_phase

  write_release_report "${REPO_ROOT}" "${REPORT_FILE}" "${BACKENDS_CSV}" "${PACKAGES_CSV}" "${APP_VERSION}" "${GIT_COMMIT}"
  log "report=${REPORT_FILE}"
  log "release Debian amd64 concluido"
}

main() {
  parse_args "$@"
  REPO_ROOT="$(repo_root)"
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
  ssa_native_guard_repo "$REPO_ROOT" || exit 1
  ssa_native_guard_tools uv git || exit 1
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
