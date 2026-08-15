#!/usr/bin/env bash
set -euo pipefail

DEFAULT_DEBIAN_BACKEND="nuitka"
DEFAULT_DEBIAN_PACKAGE="deb"
DEFAULT_DEBIAN_ARM64_BACKEND="nuitka"
DEFAULT_DEBIAN_ARM64_PACKAGE="deb"
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
  ./release.sh --target debian-arm64
  ./release.sh --target macos-arm64
  ./release.sh --target all --yes

Defaults:
  Debian amd64: backend nuitka, pacote deb
  Debian arm64: backend nuitka, pacote deb
  macOS arm64: backend pyinstaller, pacote dmg

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
    Darwin)
      case "$(uname -m)" in
        arm64 | aarch64) printf 'macos-arm64\n' ;;
        x86_64 | amd64) die "macOS x86_64 ainda nao tem alvo de release neste wrapper." ;;
        *) die "arquitetura macOS nao suportada por release.sh: $(uname -m)" ;;
      esac
      ;;
    Linux)
      case "$(uname -m)" in
        aarch64 | arm64) printf 'debian-arm64\n' ;;
        x86_64 | amd64) printf 'debian\n' ;;
        *) die "arquitetura Linux nao suportada por release.sh: $(uname -m)" ;;
      esac
      ;;
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
    debian | debian-arm64 | macos-arm64 | all) printf '%s\n' "${value}" ;;
    macos)
      printf 'macos-arm64\n'
      ;;
    *) die "--target invalido: ${value}. Use auto, debian, debian-arm64, macos, macos-arm64 ou all." ;;
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

run_debian_arm64_release() {
  local root="$1"
  local backend="${BACKEND:-${DEFAULT_DEBIAN_ARM64_BACKEND}}"
  local package_kind="${PACKAGE_KIND:-${DEFAULT_DEBIAN_ARM64_PACKAGE}}"
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

  bash "${root}/dev_env/build/release_debian_arm64.sh" "${args[@]}"
}

run_macos_release() {
  local root="$1"
  local backend="${BACKEND:-${DEFAULT_MACOS_BACKEND}}"
  local package_kind="${PACKAGE_KIND:-${DEFAULT_MACOS_PACKAGE}}"
  local platform_name="macos_arm64"
  local version
  local dmg_path
  local cli_exe

  [[ "${backend}" == "pyinstaller" ]] || die "macOS hoje suporta backend pyinstaller neste wrapper."
  [[ "${package_kind}" == "dmg" ]] || die "macOS hoje suporta pacote dmg neste wrapper."
  [[ "$(uname -s)" == "Darwin" ]] || die "release macOS arm64 deve rodar em macOS arm64."
  case "$(uname -m)" in
    arm64 | aarch64) ;;
    *) die "release macOS arm64 deve rodar em macOS arm64." ;;
  esac
  version="$(cd "${root}" && uv run --python 3.13 python -c 'import json; print(json.load(open("config/version.json", encoding="utf-8"))["version_short"])')"
  dmg_path="${root}/launchers/dist/${platform_name}/SSA_Consulta_Rapida_v${version}_${platform_name}.dmg"
  cli_exe="${root}/launchers/dist/${platform_name}/SSA_CLI_v${version}_${platform_name}/SSA_CLI_v${version}_${platform_name}"

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[release] dry-run macos: uv run --python 3.13 launchers/build_multiplatform.py --platform %s --apps cli gui\n' "${platform_name}"
    printf '[release] dry-run macos: DMG esperado %s\n' "${dmg_path}"
    printf '[release] dry-run macos: smoke importacao %s\n' "${cli_exe}"
    return 0
  fi

  uv run --python 3.13 "${root}/launchers/build_multiplatform.py" --platform "${platform_name}" --clean
  uv run --python 3.13 "${root}/launchers/build_multiplatform.py" --platform "${platform_name}" --apps cli gui
  [[ -s "${dmg_path}" ]] || die "DMG macOS nao foi gerado: ${dmg_path}"
  [[ -x "${cli_exe}" ]] || die "executavel CLI macOS ausente para smoke: ${cli_exe}"
  uv run --python 3.13 python "${root}/scripts/smoke_cli.py" --executable "${cli_exe}" --json
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
  debian-arm64)
    run_debian_arm64_release "${ROOT}"
    ;;
  macos-arm64)
    run_macos_release "${ROOT}"
    ;;
  all)
    if [[ "$(uname -s)" == "Darwin" ]]; then
      run_macos_release "${ROOT}"
    fi
    if [[ -n "${SSH_HOST}" || -n "${SSH_REPO}" ]]; then
      run_debian_release "${ROOT}"
    elif [[ "$(uname -s)" == "Linux" ]]; then
      case "$(uname -m)" in
        aarch64 | arm64) run_debian_arm64_release "${ROOT}" ;;
        x86_64 | amd64) run_debian_release "${ROOT}" ;;
        *) die "arquitetura Linux nao suportada por release.sh: $(uname -m)" ;;
      esac
    elif [[ "${ALLOW_MISSING_REMOTE}" == "1" ]]; then
      printf '[release] Debian remoto pulado: informe --ssh-host e --ssh-repo para gerar em VM.\n'
    else
      die "Debian remoto indisponivel. Use --ssh-host/--ssh-repo ou --allow-missing-remote."
    fi
    ;;
esac

printf '[release] concluido\n'
