#!/usr/bin/env bash
set -euo pipefail

SILENT=0
if [[ "${1:-}" == "--silent" ]]; then
  SILENT=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${REPO_ROOT}/launchers/logs"
LOG_FILE="${LOG_DIR}/build_pyoxidizer_debian_amd64.log"
TARGET_BUILD_DIR="${REPO_ROOT}/builds/pyoxidizer/debian_amd64"

mkdir -p "${LOG_DIR}"
mkdir -p "${REPO_ROOT}/builds/pyoxidizer"

export UV_PYTHON=3.13
export UV_MANAGED_PYTHON=true
export UV_PROJECT_ENVIRONMENT=.venv-linux

PYOX_CMD=(
  uv tool run --python 3.13 --from pyoxidizer pyoxidizer build
  --release
  --var SSA_PROJECT_ROOT "${REPO_ROOT}"
  --path "${REPO_ROOT}"
)

if [[ "${SILENT}" == "1" ]]; then
  echo "[build_pyoxidizer_debian] modo silencioso ativo. log: ${LOG_FILE}"
  "${PYOX_CMD[@]}" >"${LOG_FILE}" 2>&1
else
  echo "Iniciando build PyOxidizer debian_amd64..."
  "${PYOX_CMD[@]}"
fi

SOURCE_INSTALL="${REPO_ROOT}/build/x86_64-unknown-linux-gnu/release/install"
if [[ ! -d "${SOURCE_INSTALL}" ]]; then
  SOURCE_INSTALL="$(find "${REPO_ROOT}/build" -maxdepth 6 -type d -path "*/x86_64-unknown-linux-gnu/*/install" | head -n 1 || true)"
fi
if [[ -z "${SOURCE_INSTALL}" || ! -d "${SOURCE_INSTALL}" ]]; then
  echo "Build PyOxidizer concluiu, mas pasta install Linux nao foi encontrada em build/."
  echo "Veja o log: ${LOG_FILE}"
  exit 1
fi

rm -rf "${TARGET_BUILD_DIR}"
mkdir -p "${TARGET_BUILD_DIR}"
cp -a "${SOURCE_INSTALL}/." "${TARGET_BUILD_DIR}/"

if [[ "${SILENT}" == "1" ]]; then
  uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system pyoxidizer --allow-local-data >>"${LOG_FILE}" 2>&1
else
  uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system pyoxidizer --allow-local-data
fi

echo "Build PyOxidizer Debian concluido com sucesso."
echo "Artefatos em: ${TARGET_BUILD_DIR}"
