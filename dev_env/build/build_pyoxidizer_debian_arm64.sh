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
LOG_DIR="${REPO_ROOT}/launchers/logs"
LOG_FILE="${LOG_DIR}/build_pyoxidizer_debian_arm64.log"
TARGET_BUILD_DIR="${REPO_ROOT}/builds/pyoxidizer/debian_arm64"
PYOX_CONFIG="${REPO_ROOT}/pyoxidizer.bzl"

mkdir -p "${LOG_DIR}"
mkdir -p "${REPO_ROOT}/builds/pyoxidizer"

if [[ ! -f "${PYOX_CONFIG}" ]]; then
  echo "Erro: pyoxidizer.bzl nao encontrado na raiz do repositorio: ${PYOX_CONFIG}"
  exit 1
fi

export UV_PYTHON=3.13
export UV_MANAGED_PYTHON=true
export UV_PROJECT_ENVIRONMENT=.venv-linux

VERSION_FILE="${REPO_ROOT}/config/version.json"
if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "Erro: version.json nao encontrado: ${VERSION_FILE}"
  exit 1
fi

BUILD_INFO_FILE="${REPO_ROOT}/config/build_info.json"
BUILD_INFO_BACKUP=""
if [[ -f "${BUILD_INFO_FILE}" ]]; then
  BUILD_INFO_BACKUP_CANDIDATE="$(mktemp "${BUILD_INFO_FILE}.XXXXXX")"
  if ! cp -p "${BUILD_INFO_FILE}" "${BUILD_INFO_BACKUP_CANDIDATE}"; then
    rm -f "${BUILD_INFO_BACKUP_CANDIDATE}"
    echo "Erro: falha ao criar backup temporario de ${BUILD_INFO_FILE}" >&2
    exit 1
  fi
  BUILD_INFO_BACKUP="${BUILD_INFO_BACKUP_CANDIDATE}"
fi

cleanup_build_info() {
  if [[ -n "${BUILD_INFO_BACKUP}" && -f "${BUILD_INFO_BACKUP}" ]]; then
    mv -f "${BUILD_INFO_BACKUP}" "${BUILD_INFO_FILE}"
  else
    rm -f "${BUILD_INFO_FILE}"
  fi
}
trap cleanup_build_info EXIT

if ! APP_VERSION="$(
  uv run --python 3.13 python - "${VERSION_FILE}" <<'PY_VERSION'
import json
import pathlib
import sys

version_file = pathlib.Path(sys.argv[1])
payload = json.loads(version_file.read_text(encoding="utf-8"))
version = str(payload.get("version_short") or "").strip()
if not version:
    raise SystemExit("version_short ausente em config/version.json")
print(version)
PY_VERSION
)"; then
  echo "Erro: falha ao extrair version_short de config/version.json" >&2
  exit 1
fi
if [[ -z "${APP_VERSION}" ]]; then
  echo "Erro: version_short vazio em config/version.json" >&2
  exit 1
fi
uv run --python 3.13 "${REPO_ROOT}/dev_env/build/write_build_info.py" \
  --repo-root "${REPO_ROOT}" \
  --output "${BUILD_INFO_FILE}" \
  --build-system pyoxidizer \
  --platform debian_arm64 \
  --app-version "${APP_VERSION}"
if [[ ! -s "${BUILD_INFO_FILE}" ]]; then
  echo "Erro: falha ao gerar build_info.json para PyOxidizer debian_arm64" >&2
  exit 1
fi
PYOX_CMD=(
  uv tool run --python 3.13 --from pyoxidizer pyoxidizer build
  --release
  --var SSA_PROJECT_ROOT "${REPO_ROOT}"
  --path "${REPO_ROOT}"
)

COPY_DATA_ARGS=(--build-system pyoxidizer)
if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
  COPY_DATA_ARGS+=(--allow-local-data)
fi

if [[ "${SILENT}" == "1" ]]; then
  echo "[build_pyoxidizer_debian_arm64] modo silencioso ativo. log: ${LOG_FILE}"
  echo "[build_pyoxidizer_debian_arm64] usando pyoxidizer.bzl da raiz: ${PYOX_CONFIG}" >>"${LOG_FILE}"
  "${PYOX_CMD[@]}" >"${LOG_FILE}" 2>&1
else
  echo "Iniciando build PyOxidizer debian_arm64..."
  echo "Usando pyoxidizer.bzl da raiz: ${PYOX_CONFIG}"
  "${PYOX_CMD[@]}"
fi

SOURCE_INSTALL_ROOT="${REPO_ROOT}/build/aarch64-unknown-linux-gnu"
SOURCE_INSTALL="${SOURCE_INSTALL_ROOT}/release/install"
if [[ ! -d "${SOURCE_INSTALL}" && -d "${SOURCE_INSTALL_ROOT}" ]]; then
  SOURCE_INSTALL="$(find "${SOURCE_INSTALL_ROOT}" -maxdepth 4 -type d -path "*/install" | head -n 1 || true)"
fi
if [[ -z "${SOURCE_INSTALL}" || ! -d "${SOURCE_INSTALL}" ]]; then
  echo "Build PyOxidizer concluiu, mas pasta install Linux nao foi encontrada em build/."
  echo "Veja o log: ${LOG_FILE}"
  exit 1
fi

rm -rf "${TARGET_BUILD_DIR}"
mkdir -p "${TARGET_BUILD_DIR}"
cp -a "${SOURCE_INSTALL}/." "${TARGET_BUILD_DIR}/"

mkdir -p "${TARGET_BUILD_DIR}/config"
cp -f "${VERSION_FILE}" "${TARGET_BUILD_DIR}/config/version.json"

if [[ -d "${TARGET_BUILD_DIR}/lib" && ! -e "${TARGET_BUILD_DIR}/lib/python3.10" ]]; then
  ln -s . "${TARGET_BUILD_DIR}/lib/python3.10"
fi

if [[ "${SILENT}" == "1" ]]; then
  UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-linux \
  uv run --python 3.10 --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 \
    python "${REPO_ROOT}/scripts/sync_pyoxidizer_runtime_libs.py" --target "${TARGET_BUILD_DIR}/lib" >>"${LOG_FILE}" 2>&1
else
  UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-linux \
  uv run --python 3.10 --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 \
    python "${REPO_ROOT}/scripts/sync_pyoxidizer_runtime_libs.py" --target "${TARGET_BUILD_DIR}/lib"
fi

if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
  if [[ "${SILENT}" == "1" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" "${COPY_DATA_ARGS[@]}" >>"${LOG_FILE}" 2>&1
  else
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" "${COPY_DATA_ARGS[@]}"
  fi
elif [[ "${SILENT}" == "1" ]]; then
  echo "[build_pyoxidizer_debian_arm64] pulando copia de dados locais. Use --with-local-data para habilitar." >>"${LOG_FILE}"
else
  echo "INFO Pulando copia de dados locais. Use --with-local-data para habilitar."
fi

echo "Build PyOxidizer Debian concluido com sucesso."
echo "Artefatos em: ${TARGET_BUILD_DIR}"
if [[ "${SILENT}" != "1" ]]; then
  read -r -p "Executar cleanup TEMP agora? [s/N]: " DO_CLEANUP
  if [[ "${DO_CLEANUP,,}" == "s" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/cleanup_build_artifacts.py" --scope temp
  fi
fi
