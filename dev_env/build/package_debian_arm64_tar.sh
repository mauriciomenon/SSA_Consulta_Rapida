#!/usr/bin/env bash
set -Eeuo pipefail

BUILD_SYSTEM="pyinstaller"
OUTPUT_DIR=""

usage() {
  cat <<'USAGE'
Uso: package_debian_arm64_tar.sh [opcoes]

Gera pacote tar.gz Debian arm64 a partir dos artefatos Linux ja criados.

Opcoes:
  --build-system NAME   pyinstaller, nuitka ou pyoxidizer (default: pyinstaller)
  --output-dir DIR      diretorio final dos pacotes (default: builds/packages/debian_arm64)
  -h, --help            mostra esta ajuda
USAGE
}

die() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 1
ssa_native_guard_tools uv tar rm mkdir || exit 1
PLATFORM="debian_arm64"

read_app_version() {
  uv run --python 3.13 python "${REPO_ROOT}/dev_env/build/release_platform_report.py" \
    app-version \
    --version-file "${REPO_ROOT}/config/version.json"
}

validate_source_protection() {
  local artifact="$1"
  uv run --python 3.13 python "${REPO_ROOT}/dev_env/build/release_platform_report.py" \
    source-protection \
    --repo-root "${REPO_ROOT}" \
    --artifact "${artifact}"
}

assert_debian_arm64() {
  case "$(uname -m)" in
    aarch64 | arm64) ;;
    *) die "este empacotador e para ${PLATFORM}; arquitetura atual: $(uname -m)" ;;
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-system)
      BUILD_SYSTEM="${2:?valor ausente para --build-system}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?valor ausente para --output-dir}"
      shift 2
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

case "${BUILD_SYSTEM}" in
  pyinstaller | nuitka | pyoxidizer) ;;
  *) die "--build-system deve ser pyinstaller, nuitka ou pyoxidizer." ;;
esac

assert_debian_arm64
APP_VERSION="$(read_app_version)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/builds/packages/${PLATFORM}}"

case "${BUILD_SYSTEM}" in
  pyinstaller)
    write_tar_archive \
      "${REPO_ROOT}/launchers/dist/${PLATFORM}" \
      "SSA_CLI_v${APP_VERSION}_${PLATFORM}" \
      "${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_pyinstaller_cli.tar.gz"
    write_tar_archive \
      "${REPO_ROOT}/launchers/dist/${PLATFORM}" \
      "SSA_GUI_v${APP_VERSION}_${PLATFORM}" \
      "${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_pyinstaller_gui.tar.gz"
    ;;
  nuitka)
    write_tar_archive \
      "${REPO_ROOT}/builds/nuitka/${PLATFORM}" \
      "cli_entry.dist" \
      "${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_nuitka_cli.tar.gz"
    write_tar_archive \
      "${REPO_ROOT}/builds/nuitka/${PLATFORM}" \
      "gui_entry.dist" \
      "${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_nuitka_gui.tar.gz"
    ;;
  pyoxidizer)
    write_tar_archive \
      "${REPO_ROOT}/builds/pyoxidizer" \
      "${PLATFORM}" \
      "${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${PLATFORM}_pyoxidizer.tar.gz"
    ;;
esac

for artifact in "${OUTPUT_DIR}"/SSA_Consulta_Rapida_v"${APP_VERSION}"_"${PLATFORM}"_"${BUILD_SYSTEM}"*.tar.gz; do
  [[ -f "${artifact}" ]] || continue
  validate_source_protection "${artifact}"
done

printf 'Pacote tar gerado em: %s\n' "${OUTPUT_DIR}"
