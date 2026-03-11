#!/usr/bin/env bash
set -euo pipefail

SILENT=0
if [[ "${1:-}" == "--silent" ]]; then
  SILENT=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${REPO_ROOT}/launchers/logs"
LOG_FILE="${LOG_DIR}/build_nuitka_debian_amd64.log"

mkdir -p "${LOG_DIR}"
mkdir -p "${REPO_ROOT}/builds/nuitka/debian_amd64"

export UV_PYTHON=3.13
export UV_MANAGED_PYTHON=true
export UV_PROJECT_ENVIRONMENT=.venv-linux

if ! command -v patchelf >/dev/null 2>&1; then
  if sudo -n true >/dev/null 2>&1; then
    if [[ "${SILENT}" == "1" ]]; then
      sudo -n apt-get update >>"${LOG_FILE}" 2>&1
      sudo -n apt-get install -y patchelf >>"${LOG_FILE}" 2>&1
    else
      echo "Instalando patchelf..."
      sudo -n apt-get update
      sudo -n apt-get install -y patchelf
    fi
  else
    echo "Erro: patchelf ausente e sudo sem permissao nao interativa."
    echo "Execute no WSL: sudo apt-get update && sudo apt-get install -y patchelf"
    exit 1
  fi
fi

APP_VERSION="$(
  uv run --python 3.13 python -c "import json, pathlib; print(json.loads(pathlib.Path('config/version.json').read_text(encoding='utf-8')).get('version_short','0.0'))"
)"

if [[ -z "${APP_VERSION}" ]]; then
  APP_VERSION="0.0"
fi

GUI_DIST="${REPO_ROOT}/builds/nuitka/debian_amd64/gui_entry.dist"
CLI_DIST="${REPO_ROOT}/builds/nuitka/debian_amd64/cli_entry.dist"
rm -rf "${GUI_DIST}" "${CLI_DIST}"

BASE_CMD=(
  uv run --python 3.13 -m nuitka
  --standalone
  --assume-yes-for-downloads
  --follow-imports
  --enable-plugin=pyqt6
  --include-data-dir=config=config
  --include-data-dir=resources=resources
  --output-dir=builds/nuitka/debian_amd64
)

if [[ "${SILENT}" == "1" ]]; then
  "${BASE_CMD[@]}" --output-filename="SSA_GUI_v${APP_VERSION}_debian_amd64" --linux-icon=resources/app_icon.png launchers/gui_entry.py >"${LOG_FILE}" 2>&1
  "${BASE_CMD[@]}" --output-filename="SSA_CLI_v${APP_VERSION}_debian_amd64" launchers/cli_entry.py >>"${LOG_FILE}" 2>&1
  uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system nuitka --allow-local-data >>"${LOG_FILE}" 2>&1
else
  echo "Iniciando build Nuitka debian_amd64..."
  "${BASE_CMD[@]}" --output-filename="SSA_GUI_v${APP_VERSION}_debian_amd64" --linux-icon=resources/app_icon.png launchers/gui_entry.py
  "${BASE_CMD[@]}" --output-filename="SSA_CLI_v${APP_VERSION}_debian_amd64" launchers/cli_entry.py
  uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system nuitka --allow-local-data
fi

echo "Build Nuitka Debian concluido com sucesso."
echo "Artefatos em: ${REPO_ROOT}/builds/nuitka/debian_amd64"
