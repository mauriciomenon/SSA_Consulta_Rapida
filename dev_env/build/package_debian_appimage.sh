#!/usr/bin/env bash
set -Eeuo pipefail

BUILD_SYSTEM="pyinstaller"
OUTPUT_DIR=""
STAGING_DIR=""
APPIMAGETOOL_BIN="${APPIMAGETOOL:-}"
KEEP_STAGING=0
PREPARE_ONLY=0

usage() {
  cat <<USAGE
Uso: $(basename "$0") [opcoes]

Gera AppImage Debian ${DEBIAN_ARCH_LABEL} a partir do artefato GUI Linux.

Opcoes:
  --build-system NAME   pyinstaller ou nuitka (default: pyinstaller)
  --output-dir DIR      diretorio final (default: builds/packages/${DEBIAN_PLATFORM})
  --staging-dir DIR     diretorio temporario (default: build/package_${DEBIAN_PLATFORM}_appimage)
  --appimagetool PATH   caminho do appimagetool ${DEBIAN_APPIMAGE_ARCH}
  --prepare-only        prepara AppDir sem chamar appimagetool
  --keep-staging        nao remove AppDir ao terminar
  -h, --help            mostra esta ajuda

Pre-requisitos:
  - rodar no Debian ${DEBIAN_ARCH_LABEL}
  - appimagetool ${DEBIAN_APPIMAGE_ARCH} no PATH ou informado por --appimagetool
  - artefato GUI em launchers/dist/${DEBIAN_PLATFORM} ou builds/nuitka/${DEBIAN_PLATFORM}
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
    --appimagetool)
      APPIMAGETOOL_BIN="${2:?valor ausente para --appimagetool}"
      shift 2
      ;;
    --prepare-only)
      PREPARE_ONLY=1
      shift
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
  STAGING_DIR="$(default_package_staging_dir appimage)"
fi
APPDIR="${STAGING_DIR}/SSA_Consulta_Rapida.AppDir"
APP_ID="ssa-consulta-rapida"
APP_DISPLAY_NAME="SSA Consulta Rapida"
APP_EXEC=""

case "${BUILD_SYSTEM}" in
  pyinstaller | nuitka) ;;
  *)
    echo "Erro: --build-system deve ser pyinstaller ou nuitka para AppImage GUI." >&2
    exit 2
    ;;
esac

assert_debian_machine

VERSION_FILE="${REPO_ROOT}/config/version.json"
APP_VERSION="$(read_app_version "${VERSION_FILE}")"

safe_reset_dir "${STAGING_DIR}"
mkdir -p -- "${APPDIR}/opt/${APP_ID}" "${APPDIR}/usr/share/applications" "${APPDIR}/usr/share/icons/hicolor/256x256/apps" "${OUTPUT_DIR}"

case "${BUILD_SYSTEM}" in
  pyinstaller)
    SOURCE_ROOT="${REPO_ROOT}/launchers/dist/${DEBIAN_PLATFORM}"
    [[ -d "${SOURCE_ROOT}" ]] || SOURCE_ROOT="${REPO_ROOT}/builds/pyinstaller/${DEBIAN_PLATFORM}"
    copy_dir_checked "${SOURCE_ROOT}/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" "${APPDIR}/opt/${APP_ID}/runtime"
    APP_EXEC="$(
      first_existing_executable \
        "${APPDIR}/opt/${APP_ID}/runtime/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}"
    )"
    ;;
  nuitka)
    copy_dir_checked "${REPO_ROOT}/builds/nuitka/${DEBIAN_PLATFORM}/gui_entry.dist" "${APPDIR}/opt/${APP_ID}/runtime"
    APP_FALLBACK_EXEC="$(
      find "${APPDIR}/opt/${APP_ID}/runtime" -maxdepth 1 -type f -executable -print -quit
    )"
    APP_EXEC="$(
      first_existing_executable \
        "${APPDIR}/opt/${APP_ID}/runtime/SSA_GUI_v${APP_VERSION}_${DEBIAN_PLATFORM}" \
        "${APPDIR}/opt/${APP_ID}/runtime/gui_entry" \
        "${APP_FALLBACK_EXEC}"
    )"
    ;;
esac

require_executable "${APP_EXEC}"
APP_REL_EXEC="${APP_EXEC#"${APPDIR}"}"

clean_release_tree "${APPDIR}"

if [[ -f "${REPO_ROOT}/resources/app_icon.png" ]]; then
  cp -a -- "${REPO_ROOT}/resources/app_icon.png" "${APPDIR}/${APP_ID}.png"
  cp -a -- "${REPO_ROOT}/resources/app_icon.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_ID}.png"
fi

cat >"${APPDIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_DISPLAY_NAME}
Exec=AppRun
Icon=${APP_ID}
Categories=Utility;
Terminal=false
DESKTOP
cp -a -- "${APPDIR}/${APP_ID}.desktop" "${APPDIR}/usr/share/applications/${APP_ID}.desktop"

cat >"${APPDIR}/AppRun" <<APPRUN
#!/usr/bin/env bash
set -euo pipefail
HERE="\$(cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")" && pwd -P)"
exec "\${HERE}${APP_REL_EXEC}" "\$@"
APPRUN
chmod 0755 "${APPDIR}/AppRun"

if [[ "${PREPARE_ONLY}" == "1" ]]; then
  echo "AppDir preparado: ${APPDIR}"
  exit 0
fi

if [[ -z "${APPIMAGETOOL_BIN}" ]]; then
  APPIMAGETOOL_BIN="$(command -v appimagetool || true)"
fi
if [[ -z "${APPIMAGETOOL_BIN}" || ! -x "${APPIMAGETOOL_BIN}" ]]; then
  echo "Erro: appimagetool ${DEBIAN_APPIMAGE_ARCH} nao encontrado." >&2
  echo "Informe com --appimagetool /caminho/appimagetool-${DEBIAN_APPIMAGE_ARCH}.AppImage ou APPIMAGETOOL=/caminho." >&2
  exit 1
fi

OUTPUT_FILE="${OUTPUT_DIR}/SSA_Consulta_Rapida_v${APP_VERSION}_${DEBIAN_PLATFORM}_${BUILD_SYSTEM}.AppImage"
ARCH="${DEBIAN_APPIMAGE_ARCH}" "${APPIMAGETOOL_BIN}" "${APPDIR}" "${OUTPUT_FILE}"
chmod 0755 "${OUTPUT_FILE}"

if [[ "${KEEP_STAGING}" != "1" ]]; then
  rm -rf -- "${STAGING_DIR}"
fi

echo "AppImage gerado: ${OUTPUT_FILE}"
