#!/usr/bin/env bash
set -euo pipefail

SILENT=0
WITH_LOCAL_DATA=0
for arg in "$@"; do
  case "${arg}" in
    --silent)
      SILENT=1
      ;;
    --with-local-data)
      WITH_LOCAL_DATA=1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$REPO_ROOT" || exit 1
ssa_native_guard_tools uv mkdir || exit 1
LOG_DIR="${REPO_ROOT}/launchers/logs"
LOG_FILE="${LOG_DIR}/build_pyinstaller_debian_amd64.log"

mkdir -p "${LOG_DIR}"

export UV_PYTHON=3.13
export UV_MANAGED_PYTHON=true
export UV_PROJECT_ENVIRONMENT=.venv-linux

COPY_DATA_ARGS=(--build-system pyinstaller)
if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
  COPY_DATA_ARGS+=(--allow-local-data)
fi

if [[ "${SILENT}" == "1" ]]; then
  uv run --python 3.13 "${REPO_ROOT}/launchers/build_multiplatform.py" --platform debian_amd64 --clean >/dev/null 2>&1
  uv run --python 3.13 "${REPO_ROOT}/launchers/build_multiplatform.py" --platform debian_amd64 --apps cli gui >"${LOG_FILE}" 2>&1
  uv run --python 3.13 "${REPO_ROOT}/scripts/sync_pyinstaller_outputs.py" --platform debian_amd64 --quiet >>"${LOG_FILE}" 2>&1
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" "${COPY_DATA_ARGS[@]}" >>"${LOG_FILE}" 2>&1
  else
    echo "[build_pyinstaller_debian] pulando copia de dados locais. Use --with-local-data para habilitar." >>"${LOG_FILE}"
  fi
else
  echo "Limpando artefatos PyInstaller Debian anteriores..."
  uv run --python 3.13 "${REPO_ROOT}/launchers/build_multiplatform.py" --platform debian_amd64 --clean
  echo "Iniciando build PyInstaller debian_amd64..."
  uv run --python 3.13 "${REPO_ROOT}/launchers/build_multiplatform.py" --platform debian_amd64 --apps cli gui
  uv run --python 3.13 "${REPO_ROOT}/scripts/sync_pyinstaller_outputs.py" --platform debian_amd64
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" "${COPY_DATA_ARGS[@]}"
  else
    echo "INFO Pulando copia de dados locais. Use --with-local-data para habilitar."
  fi
fi

echo "Build PyInstaller Debian concluido com sucesso."
echo "Artefatos em: ${REPO_ROOT}/launchers/dist/debian_amd64 e ${REPO_ROOT}/builds/pyinstaller/debian_amd64"
if [[ "${SILENT}" != "1" ]]; then
  read -r -p "Executar cleanup TEMP agora? [s/N]: " DO_CLEANUP
  if [[ "${DO_CLEANUP,,}" == "s" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/cleanup_build_artifacts.py" --scope temp
  fi
fi
