#!/usr/bin/env bash
set -euo pipefail

DEFAULT_DEBIAN_BACKEND="nuitka"
DEFAULT_DEBIAN_PACKAGE="deb"
DEFAULT_MACOS_BACKEND="pyinstaller"
DEFAULT_MACOS_PACKAGE="dmg"

TARGET="auto"
BACKEND=""
PACKAGE_KIND=""
SSH_HOST=""
SSH_REPO=""
DRY_RUN=0
YES=0
ALLOW_MISSING_REMOTE=0

usage() {
  cat <<'USAGE'
Uso:
  ./release.sh
  ./release.sh --target debian
  ./release.sh --target macos
  ./release.sh --target all --yes

Defaults:
  Debian: backend nuitka, pacote deb
  macOS: backend pyinstaller, pacote dmg

Opcoes uteis:
  --dry-run                    mostra plano sem build/pacote
  -y, --yes                    executa sem prompt quando suportado
  --ssh-host HOST --ssh-repo DIR
                               gera Debian em VM/host remoto
  --allow-missing-remote       em --target all, pula remoto indisponivel
USAGE
}

die() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}

repo_root() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
  cd -- "${script_dir}" && git rev-parse --show-toplevel
}

detect_target() {
  case "$(uname -s)" in
    Darwin) printf 'macos\n' ;;
    Linux) printf 'debian\n' ;;
    *) die "sistema nao suportado por release.sh: $(uname -s)" ;;
  esac
}

normalize_target() {
  local value="$1"
  if [[ "${value}" == "auto" ]]; then
    detect_target
    return 0
  fi
  case "${value}" in
    debian | macos | all) printf '%s\n' "${value}" ;;
    *) die "--target invalido: ${value}. Use auto, debian, macos ou all." ;;
  esac
}

run_debian_release() {
  local root="$1"
  local backend="${BACKEND:-${DEFAULT_DEBIAN_BACKEND}}"
  local package_kind="${PACKAGE_KIND:-${DEFAULT_DEBIAN_PACKAGE}}"
  local args=(--backend "${backend}" --package "${package_kind}")

  if [[ "${YES}" == "1" ]]; then
    args+=(-y)
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    args+=(--dry-run)
  fi
  if [[ -n "${SSH_HOST}" || -n "${SSH_REPO}" ]]; then
    [[ -n "${SSH_HOST}" ]] || die "--ssh-host e obrigatorio com --ssh-repo"
    [[ -n "${SSH_REPO}" ]] || die "--ssh-repo e obrigatorio com --ssh-host"
    args+=(--ssh-host "${SSH_HOST}" --ssh-repo "${SSH_REPO}")
  fi

  bash "${root}/dev_env/build/release_debian.sh" "${args[@]}"
}

run_macos_release() {
  local root="$1"
  local backend="${BACKEND:-${DEFAULT_MACOS_BACKEND}}"
  local package_kind="${PACKAGE_KIND:-${DEFAULT_MACOS_PACKAGE}}"
  local version
  local dmg_path

  [[ "${backend}" == "pyinstaller" ]] || die "macOS hoje suporta backend pyinstaller neste wrapper."
  [[ "${package_kind}" == "dmg" ]] || die "macOS hoje suporta pacote dmg neste wrapper."
  version="$(cd "${root}" && uv run --python 3.13 python -c 'import json; print(json.load(open("config/version.json", encoding="utf-8"))["version_short"])')"
  dmg_path="${root}/launchers/dist/macos_arm64/SSA_Consulta_Rapida_v${version}_macos_arm64.dmg"

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[release] dry-run macos: uv run --python 3.13 launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui\n'
    printf '[release] dry-run macos: DMG esperado %s\n' "${dmg_path}"
    return 0
  fi

  uv run --python 3.13 "${root}/launchers/build_multiplatform.py" --platform macos_arm64 --clean
  uv run --python 3.13 "${root}/launchers/build_multiplatform.py" --platform macos_arm64 --apps cli gui
  [[ -s "${dmg_path}" ]] || die "DMG macOS nao foi gerado: ${dmg_path}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:?valor ausente para --target}"
      shift 2
      ;;
    --backend)
      BACKEND="${2:?valor ausente para --backend}"
      shift 2
      ;;
    --package)
      PACKAGE_KIND="${2:?valor ausente para --package}"
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
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -y | --yes)
      YES=1
      shift
      ;;
    --allow-missing-remote)
      ALLOW_MISSING_REMOTE=1
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

ROOT="$(repo_root)"
TARGET="$(normalize_target "${TARGET}")"

printf '[release] target=%s\n' "${TARGET}"

case "${TARGET}" in
  debian)
    run_debian_release "${ROOT}"
    ;;
  macos)
    run_macos_release "${ROOT}"
    ;;
  all)
    run_macos_release "${ROOT}"
    if [[ -n "${SSH_HOST}" || -n "${SSH_REPO}" || "$(uname -s)" == "Linux" ]]; then
      run_debian_release "${ROOT}"
    elif [[ "${ALLOW_MISSING_REMOTE}" == "1" ]]; then
      printf '[release] Debian remoto pulado: informe --ssh-host e --ssh-repo para gerar em VM.\n'
    else
      die "Debian remoto indisponivel. Use --ssh-host/--ssh-repo ou --allow-missing-remote."
    fi
    ;;
esac

printf '[release] concluido\n'
