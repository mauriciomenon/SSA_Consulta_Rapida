#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$PROJECT_ROOT" || exit 1
ssa_native_guard_tools git || exit 1
cd "$PROJECT_ROOT"

export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
PYENV_GIT_REF="${PYENV_GIT_REF:-v2.6.11}"
PYENV_VIRTUALENV_GIT_REF="${PYENV_VIRTUALENV_GIT_REF:-v1.2.4}"

VENV_NAME=$(cat .python-version 2>/dev/null || true)
if [[ -z "${VENV_NAME:-}" ]]; then
  echo "[info] .python-version nao encontrado; usarei nome padrao ssa_consulta_rapida_py313"
  VENV_NAME="ssa_consulta_rapida_py313"
fi

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
  if [[ "${OSTYPE:-}" == darwin* ]]; then echo mac; return; fi
  if [[ -f /etc/debian_version ]]; then echo debian; return; fi
  uname_s=$(uname -s 2>/dev/null || echo unknown)
  case "$uname_s" in
    Linux) echo linux;;
    Darwin) echo mac;;
    *) echo linux;;
  esac
}

OS=$(detect_os)
echo "[info] OS detectado: $OS"

ensure_build_deps() {
  case "$OS" in
    debian)
      :
      ;;
    mac)
      if have_cmd brew; then
        echo "[info] Instalando ferramentas via Homebrew (pyenv, pyenv-virtualenv, direnv)"
        if ! brew install pyenv pyenv-virtualenv direnv; then
          echo "[aviso] Homebrew nao instalou todas as ferramentas; continuarei com fallbacks disponiveis"
        fi
      else
        echo "[aviso] Homebrew nao encontrado. Instale Homebrew ou pyenv manualmente: https://github.com/pyenv/pyenv"
      fi
      ;;
    *) ;;
  esac
}

ensure_pyenv_clone_deps() {
  if [[ "$OS" != "debian" ]] || ! have_cmd apt; then
    return 0
  fi
  if ! have_cmd sudo; then
    echo "[aviso] sudo nao encontrado; seguindo para fallback .venv sem bootstrap do pyenv"
    return 1
  fi
  echo "[info] Instalando dependencias de build para pyenv (sudo pode ser solicitado)"
  sudo apt-get update
  sudo apt-get install -y build-essential git libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev curl llvm tk-dev libncursesw5-dev xz-utils libffi-dev liblzma-dev ca-certificates
}

ensure_pyenv() {
  if ! have_cmd pyenv && [[ -x "$PYENV_ROOT/bin/pyenv" ]]; then
    export PATH="$PYENV_ROOT/bin:$PATH"
  fi
  if have_cmd pyenv && pyenv virtualenv --version >/dev/null 2>&1; then
    echo "[ok] pyenv encontrado"
    return
  fi
  if ! have_cmd git; then
    echo "[erro] git nao encontrado; instale git para bootstrap seguro do pyenv"
    return 1
  fi
  if have_cmd pyenv; then
    echo "[aviso] pyenv encontrado sem pyenv-virtualenv; instalando plugin fixado"
  else
    ensure_pyenv_clone_deps || return 1
    if [[ -x "$PYENV_ROOT/bin/pyenv" ]]; then
      echo "[info] Reutilizando instalacao existente de pyenv em $PYENV_ROOT"
    elif [[ -d "$PYENV_ROOT/.git" ]]; then
      echo "[erro] PYENV_ROOT tem repositorio git mas nao possui binario pyenv valido: $PYENV_ROOT"
      return 1
    elif [[ -d "$PYENV_ROOT" ]] && [[ -z "$(find "$PYENV_ROOT" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
      echo "[info] Instalando pyenv de refs fixadas"
      rmdir "$PYENV_ROOT"
      git clone --branch "$PYENV_GIT_REF" --depth 1 https://github.com/pyenv/pyenv.git "$PYENV_ROOT"
    elif [[ -e "$PYENV_ROOT" ]]; then
      echo "[erro] PYENV_ROOT ja existe mas nao parece uma instalacao valida de pyenv: $PYENV_ROOT"
      return 1
    else
      echo "[info] Instalando pyenv de refs fixadas"
      git clone --branch "$PYENV_GIT_REF" --depth 1 https://github.com/pyenv/pyenv.git "$PYENV_ROOT"
    fi
  fi
  if [[ ! -d "$PYENV_ROOT/plugins/pyenv-virtualenv" ]]; then
    mkdir -p "$PYENV_ROOT/plugins"
    git clone --branch "$PYENV_VIRTUALENV_GIT_REF" --depth 1 \
      https://github.com/pyenv/pyenv-virtualenv.git \
      "$PYENV_ROOT/plugins/pyenv-virtualenv"
  fi
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
}

ensure_direnv() {
  if have_cmd direnv; then
    echo "[ok] direnv encontrado"
  else
    case "$OS" in
      debian)
        if have_cmd apt; then
          echo "[info] Instalando direnv via apt (sudo pode ser solicitado)"
          if ! sudo apt install -y direnv; then
            echo "[aviso] apt nao instalou direnv; continuarei sem ativacao automatica"
          fi
        fi
        ;;
      mac)
        # já tentamos brew acima
        :
        ;;
      *) : ;;
    esac
  fi
}

init_pyenv_shell() {
  if have_cmd pyenv; then
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
  fi
}

create_virtualenv_if_missing() {
  if ! have_cmd pyenv; then
    echo "[aviso] pyenv nao disponivel; criando fallback .venv com python do sistema"
    if ! have_cmd python3; then
      echo "[erro] python3 nao encontrado para criar fallback .venv"
      exit 1
    fi
    if ! python3 -m venv --help >/dev/null 2>&1 || ! python3 -m ensurepip --version >/dev/null 2>&1; then
      echo "[erro] venv/ensurepip indisponivel no python3 atual; instale python3-venv"
      exit 1
    fi
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -U pip
    python -m pip install -r requirements.txt
    echo "[ok] Ambiente .venv criado (fallback)."
    return
  fi

  if pyenv virtualenvs --bare | grep -qx "$VENV_NAME"; then
    echo "[ok] Virtualenv pyenv '$VENV_NAME' ja existe"
  else
    echo "[info] Criando virtualenv pyenv '$VENV_NAME'"
    # Prefer 3.13.x; fallback to 3.12/3.11/3.10 if needed.
    PYENV_LIST=$(pyenv install -l | sed 's/^[[:space:]]*//')
    PY_VER=""
    for MAJOR in 3.13 3.12 3.11 3.10; do
      CANDIDATE=$(printf "%s\n" "$PYENV_LIST" | sed -n "s/^\\(${MAJOR}\\.[0-9]\\+\\)$/\\1/p" | tail -1)
      if [[ -n "${CANDIDATE:-}" ]]; then
        PY_VER="$CANDIDATE"
        break
      fi
    done
    if [[ -z "${PY_VER:-}" ]]; then
      echo "[erro] Nao foi possivel descobrir versao Python suportada (3.13-3.10) no pyenv."
      exit 1
    fi
    if ! pyenv install -s "$PY_VER"; then
      echo "[erro] Falha ao instalar Python $PY_VER via pyenv."
      exit 1
    fi
    if ! pyenv virtualenv "$PY_VER" "$VENV_NAME"; then
      echo "[erro] Falha ao criar virtualenv $VENV_NAME."
      exit 1
    fi
  fi

  # Ativa sem mexer em .python-version
  pyenv activate "$VENV_NAME"
  python -m pip install -U pip
  python -m pip install -r requirements.txt
}

configure_direnv_hint() {
  if have_cmd direnv; then
    echo "[dica] Rode 'direnv allow' na raiz do projeto para ativacao automatica."
  fi
}

echo "[1/4] Checando dependências de build"
ensure_build_deps
echo "[2/4] Checando/instalando pyenv"
ensure_pyenv || true
echo "[3/4] Inicializando shell do pyenv"
init_pyenv_shell
echo "[4/4] Checando direnv"
ensure_direnv || true

create_virtualenv_if_missing
configure_direnv_hint

echo "[ok] Ambiente pronto."
