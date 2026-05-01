#!/usr/bin/env bash
set -Eeuo pipefail

BUILD_SYSTEM="pyinstaller"
OUTPUT_DIR=""
STAGING_DIR=""
KEEP_STAGING=0

usage() {
  cat <<USAGE
Uso: $(basename "$0") [opcoes]

Gera pacote .deb Debian ${DEBIAN_ARCH_LABEL} a partir dos artefatos Linux ja criados.

Opcoes:
  --build-system NAME   pyinstaller, nuitka ou pyoxidizer (default: pyinstaller)
  --output-dir DIR      diretorio final dos pacotes (default: builds/packages/${DEBIAN_PLATFORM})
  --staging-dir DIR     diretorio temporario (default: build/package_${DEBIAN_PLATFORM}_deb)
  --keep-staging        nao remove staging ao terminar
  -h, --help            mostra esta ajuda

Pre-requisitos:
  - rodar no Debian ${DEBIAN_ARCH_LABEL}
  - dpkg-deb instalado
  - artefatos em launchers/dist/${DEBIAN_PLATFORM} ou builds/<sistema>/${DEBIAN_PLATFORM}
USAGE
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
# shellcheck source=dev_env/build/package_debian_common.sh
source "${SCRIPT_DIR}/package_debian_common.sh"
require_debian_package_context

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
    --staging-dir)
      STAGING_DIR="${2:?valor ausente para --staging-dir}"
      shift 2
      ;;
    --keep-staging)
      KEEP_STAGING=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Erro: opcao desconhecida: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/builds/packages/${DEBIAN_PLATFORM}}"
if [[ -z "${STAGING_DIR}" ]]; then
  STAGING_DIR="$(default_package_staging_dir deb)"
fi
APP_ID="ssa-consulta-rapida"
APP_DISPLAY_NAME="SSA Consulta Rapida"
APP_MAINTAINER="SSA Consulta Rapida <noreply@example.invalid>"
CLI_TARGET=""
GUI_TARGET=""

case "${BUILD_SYSTEM}" in
  pyinstaller | nuitka | pyoxidizer) ;;
  *)
    echo "Erro: --build-system deve ser pyinstaller, nuitka ou pyoxidizer." >&2
    exit 2
    ;;
esac

assert_debian_machine

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Erro: dpkg-deb nao encontrado. Instale com: sudo apt-get install -y dpkg-dev" >&2
  exit 1
fi

VERSION_FILE="${REPO_ROOT}/config/version.json"
APP_VERSION="$(read_app_version "${VERSION_FILE}")"

PACKAGE_NAME="${APP_ID}-${BUILD_SYSTEM}-${DEBIAN_PACKAGE_ARCH}"
PACKAGE_ROOT="${STAGING_DIR}/${PACKAGE_NAME}"
INSTALL_ROOT="${PACKAGE_ROOT}/usr/lib/${APP_ID}/${BUILD_SYSTEM}"
BIN_DIR="${PACKAGE_ROOT}/usr/bin"
DEBIAN_DIR="${PACKAGE_ROOT}/DEBIAN"
PACKAGE_FILE="${OUTPUT_DIR}/${PACKAGE_NAME}_${APP_VERSION}_${DEBIAN_PACKAGE_ARCH}.deb"

safe_reset_dir "${STAGING_DIR}"
mkdir -p -- "${OUTPUT_DIR}" "${INSTALL_ROOT}" "${BIN_DIR}" "${DEBIAN_DIR}"

case "${BUILD_SYSTEM}" in
  pyinstaller)
    SOURCE_ROOT="${REPO_ROOT}/launchers/dist/${DEBIAN_PLATFORM}"
    [[ -d "${SOURCE_ROOT}" ]] || SOURCE_ROOT="${REPO_ROOT}/builds/pyinstaller/${DEBIAN_PLATFORM}"
    copy_dir_checked "${SOURCE_ROOT}/SSA_CLI_v${APP_VERSION}_${DEBIAN_PLATFORM}" "${INSTALL_ROOT}/cli"
    copy_dir_checked "${SOURCE_ROOT}/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" "${INSTALL_ROOT}/gui"
    CLI_TARGET="$(first_existing_executable "${INSTALL_ROOT}/cli/SSA_CLI_v${APP_VERSION}_${DEBIAN_PLATFORM}")"
    GUI_TARGET="$(first_existing_executable "${INSTALL_ROOT}/gui/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}")"
    write_wrapper "${BIN_DIR}/${APP_ID}-cli" "${CLI_TARGET#"${PACKAGE_ROOT}"}"
    write_wrapper "${BIN_DIR}/${APP_ID}-gui" "${GUI_TARGET#"${PACKAGE_ROOT}"}"
    ;;
  nuitka)
    copy_dir_checked "${REPO_ROOT}/builds/nuitka/${DEBIAN_PLATFORM}/cli_entry.dist" "${INSTALL_ROOT}/cli"
    copy_dir_checked "${REPO_ROOT}/builds/nuitka/${DEBIAN_PLATFORM}/gui_entry.dist" "${INSTALL_ROOT}/gui"
    CLI_TARGET="$(
      first_existing_executable \
        "${INSTALL_ROOT}/cli/SSA_CLI_v${APP_VERSION}_${DEBIAN_PLATFORM}" \
        "${INSTALL_ROOT}/cli/cli_entry"
    )"
    GUI_TARGET="$(
      first_existing_executable \
        "${INSTALL_ROOT}/gui/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" \
        "${INSTALL_ROOT}/gui/gui_entry"
    )"
    write_wrapper "${BIN_DIR}/${APP_ID}-cli" "${CLI_TARGET#"${PACKAGE_ROOT}"}"
    write_wrapper "${BIN_DIR}/${APP_ID}-gui" "${GUI_TARGET#"${PACKAGE_ROOT}"}"
    ;;
  pyoxidizer)
    copy_dir_checked "${REPO_ROOT}/builds/pyoxidizer/${DEBIAN_PLATFORM}" "${INSTALL_ROOT}/runtime"
    CLI_TARGET="$(first_existing_executable "${INSTALL_ROOT}/runtime/SSA_Consulta_Rapida")"
    GUI_TARGET="${CLI_TARGET}"
    write_wrapper "${BIN_DIR}/${APP_ID}-cli" "${CLI_TARGET#"${PACKAGE_ROOT}"}"
    write_wrapper "${BIN_DIR}/${APP_ID}-gui" "${GUI_TARGET#"${PACKAGE_ROOT}"}" "--gui"
    ;;
esac

clean_release_tree "${PACKAGE_ROOT}"

cat >"${DEBIAN_DIR}/control" <<CONTROL
Package: ${PACKAGE_NAME}
Version: ${APP_VERSION}
Section: utils
Priority: optional
Architecture: ${DEBIAN_PACKAGE_ARCH}
Maintainer: ${APP_MAINTAINER}
Depends: libc6, libstdc++6, zlib1g
Description: ${APP_DISPLAY_NAME} (${BUILD_SYSTEM}, Debian ${DEBIAN_ARCH_LABEL})
 Pacote local gerado a partir dos artefatos Debian ${DEBIAN_ARCH_LABEL} do projeto.
CONTROL

chmod -R go-w "${PACKAGE_ROOT}"
dpkg-deb --build --root-owner-group "${PACKAGE_ROOT}" "${PACKAGE_FILE}"

if [[ "${KEEP_STAGING}" != "1" ]]; then
  rm -rf -- "${STAGING_DIR}"
fi

echo "Pacote .deb gerado: ${PACKAGE_FILE}"
