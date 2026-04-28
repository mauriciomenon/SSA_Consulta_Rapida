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
LOG_FILE="${LOG_DIR}/build_nuitka_debian_arm64.log"
VENV_DIR="${REPO_ROOT}/launchers/platforms/debian_arm64/venv"
PYTHON_EXE="${VENV_DIR}/bin/python"
REQUIREMENTS_FILE="${REPO_ROOT}/launchers/platforms/debian_arm64/requirements.txt"

mkdir -p "${LOG_DIR}"
FINAL_BUILD_DIR="${REPO_ROOT}/builds/nuitka/debian_arm64"
mkdir -p "${FINAL_BUILD_DIR}"
BUILD_WORK_DIR=""

cleanup_build_work_dir() {
  if [[ -n "${BUILD_WORK_DIR}" && "${KEEP_NUITKA_WORK_DIR:-0}" != "1" ]]; then
    rm -rf -- "${BUILD_WORK_DIR}"
  fi
}

trap cleanup_build_work_dir EXIT
cd "${REPO_ROOT}"

export UV_PYTHON=3.13
export UV_MANAGED_PYTHON=true
export UV_PROJECT_ENVIRONMENT=.venv-linux

LAST_STEP=""

on_error() {
  local exit_code=$?
  echo "Erro no build Nuitka Debian arm64 (step: ${LAST_STEP:-unknown}, exit: ${exit_code})."
  echo "Log: ${LOG_FILE}"
  if [[ "${SILENT}" == "1" ]] && [[ -f "${LOG_FILE}" ]]; then
    echo "------ tail do log ------"
    tail -n 80 "${LOG_FILE}" || true
    echo "-------------------------"
  fi
  exit "${exit_code}"
}

trap on_error ERR

if ! command -v patchelf >/dev/null 2>&1; then
  if sudo -n true >/dev/null 2>&1; then
    mkdir -p "${TMPDIR:-/tmp}/ssa_build_locks"
    APT_LOCK_FILE="${TMPDIR:-/tmp}/ssa_build_locks/patchelf_install.lock"
    exec 9>"${APT_LOCK_FILE}"
    if command -v flock >/dev/null 2>&1; then
      flock 9
    fi
    if ! command -v patchelf >/dev/null 2>&1; then
      if [[ "${SILENT}" == "1" ]]; then
        sudo -n apt-get update 2>&1 | tee -a "${LOG_FILE}" >/dev/null
        sudo -n apt-get install -y patchelf 2>&1 | tee -a "${LOG_FILE}" >/dev/null
      else
        echo "Instalando patchelf..."
        sudo -n apt-get update
        sudo -n apt-get install -y patchelf
      fi
    fi
  else
    echo "Erro: patchelf ausente e sudo sem permissao nao interativa."
    echo "Execute no WSL: sudo apt-get update && sudo apt-get install -y patchelf"
    exit 1
  fi
fi

VERSION_FILE="${REPO_ROOT}/config/version.json"
if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "Erro: version.json nao encontrado: ${VERSION_FILE}"
  exit 1
fi
APP_VERSION="$(
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
)"

BUILD_INFO_FILE="${REPO_ROOT}/builds/metadata/build_info_debian_arm64_nuitka.json"
mkdir -p "$(dirname "${BUILD_INFO_FILE}")"
LAST_STEP="write_build_info"
uv run --python 3.13 python - "${REPO_ROOT}" "${BUILD_INFO_FILE}" "nuitka" "debian_arm64" "${APP_VERSION}" <<'PY_BUILD_INFO'
import datetime
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
build_system = sys.argv[3]
platform_name = sys.argv[4]
app_version = sys.argv[5]

def run(args):
    result = subprocess.run(args, cwd=str(root), text=True, capture_output=True, check=False)
    return (result.stdout or "").strip() if result.returncode == 0 else ""

commit = run(["git", "rev-parse", "HEAD"])
payload = {
    "app_version": app_version,
    "build_datetime": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "build_system": build_system,
    "git_commit": commit,
    "git_commit_datetime": run(["git", "log", "-1", "--format=%cI"]),
    "git_commit_short": commit[:7] if commit else "",
    "git_commit_title": run(["git", "log", "-1", "--format=%s"]),
    "platform": platform_name,
    "uv_version": run(["uv", "--version"]),
}
output.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY_BUILD_INFO

GUI_DIST="${FINAL_BUILD_DIR}/gui_entry.dist"
CLI_DIST="${FINAL_BUILD_DIR}/cli_entry.dist"
rm -rf "${GUI_DIST}" "${CLI_DIST}"

if [[ ! -x "${PYTHON_EXE}" ]]; then
  LAST_STEP="create_venv"
  uv venv --python 3.13 "${VENV_DIR}"
fi

LAST_STEP="install_requirements"
uv pip install --python "${PYTHON_EXE}" -r "${REQUIREMENTS_FILE}"

WORK_PARENT="${SSA_NUITKA_WORK_ROOT:-${TMPDIR:-/tmp}/ssa_nuitka_build}"
if [[ "${REPO_ROOT}" == /mnt/* ]]; then
  mkdir -p "${WORK_PARENT}"
  BUILD_WORK_DIR="$(mktemp -d "${WORK_PARENT}/debian_arm64.XXXXXX")"
  NUITKA_OUTPUT_DIR="${BUILD_WORK_DIR}"
else
  NUITKA_OUTPUT_DIR="${FINAL_BUILD_DIR}"
fi

GUI_CMD=(
  "${PYTHON_EXE}" -m nuitka
  --standalone
  --assume-yes-for-downloads
  --follow-imports
  --enable-plugin=pyqt6
  --include-data-dir=config=config
  --include-data-dir=resources=resources
  --include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md
  --include-data-file="${BUILD_INFO_FILE}=config/build_info.json"
  --output-dir="${NUITKA_OUTPUT_DIR}"
)

CLI_CMD=(
  "${PYTHON_EXE}" -m nuitka
  --standalone
  --assume-yes-for-downloads
  --follow-imports
  --include-data-dir=config=config
  --include-data-file="${BUILD_INFO_FILE}=config/build_info.json"
  --output-dir="${NUITKA_OUTPUT_DIR}"
)

if [[ "${SILENT}" == "1" ]]; then
  LAST_STEP="nuitka_gui"
  "${GUI_CMD[@]}" --output-filename="SSA_GUI_v${APP_VERSION}_debian_arm64" --linux-icon=resources/app_icon.png launchers/gui_entry.py >"${LOG_FILE}" 2>&1
  LAST_STEP="nuitka_cli"
  "${CLI_CMD[@]}" --output-filename="SSA_CLI_v${APP_VERSION}_debian_arm64" launchers/cli_entry.py >>"${LOG_FILE}" 2>&1
  if [[ "${NUITKA_OUTPUT_DIR}" != "${FINAL_BUILD_DIR}" ]]; then
    LAST_STEP="copy_nuitka_dist"
    cp -a "${NUITKA_OUTPUT_DIR}/gui_entry.dist" "${GUI_DIST}"
    cp -a "${NUITKA_OUTPUT_DIR}/cli_entry.dist" "${CLI_DIST}"
  fi
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    LAST_STEP="copy_data_to_builds"
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system nuitka --allow-local-data >>"${LOG_FILE}" 2>&1
  else
    echo "[build_nuitka_debian_arm64] pulando copia de dados locais. Use --with-local-data para habilitar." >>"${LOG_FILE}"
  fi
else
  echo "Iniciando build Nuitka debian_arm64..."
  LAST_STEP="nuitka_gui"
  "${GUI_CMD[@]}" --output-filename="SSA_GUI_v${APP_VERSION}_debian_arm64" --linux-icon=resources/app_icon.png launchers/gui_entry.py
  LAST_STEP="nuitka_cli"
  "${CLI_CMD[@]}" --output-filename="SSA_CLI_v${APP_VERSION}_debian_arm64" launchers/cli_entry.py
  if [[ "${NUITKA_OUTPUT_DIR}" != "${FINAL_BUILD_DIR}" ]]; then
    LAST_STEP="copy_nuitka_dist"
    cp -a "${NUITKA_OUTPUT_DIR}/gui_entry.dist" "${GUI_DIST}"
    cp -a "${NUITKA_OUTPUT_DIR}/cli_entry.dist" "${CLI_DIST}"
  fi
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    LAST_STEP="copy_data_to_builds"
    uv run --python 3.13 "${REPO_ROOT}/scripts/copy_data_to_builds.py" --build-system nuitka --allow-local-data
  else
    echo "INFO Pulando copia de dados locais. Use --with-local-data para habilitar."
  fi
fi

echo "Build Nuitka Debian arm64 concluido com sucesso."
echo "Artefatos em: ${REPO_ROOT}/builds/nuitka/debian_arm64"
if [[ "${SILENT}" != "1" ]]; then
  read -r -p "Executar cleanup TEMP agora? [s/N]: " DO_CLEANUP
  if [[ "${DO_CLEANUP,,}" == "s" ]]; then
    uv run --python 3.13 "${REPO_ROOT}/scripts/cleanup_build_artifacts.py" --scope temp
  fi
fi
